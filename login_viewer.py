"""Temporary LAN-only HTTPS viewer for a dedicated headless Chrome profile.

No game credentials are accepted by this service: keystrokes go to the browser
through loopback-only Chrome DevTools Protocol. Stop the viewer after handoff.
"""

import argparse
import asyncio
import base64
import hmac
import html
import ipaddress
import json
import secrets
import time
from pathlib import Path

from aiohttp import ClientSession, WSMsgType, web

HTML = r'''<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Navegador isolado · KingsAge</title>
<style>body{margin:0;background:#171a20;color:#eee;font:15px system-ui}
header{padding:10px 16px;background:#292e38}#screen{display:block;max-width:100%;height:auto;
margin:auto;outline:0;cursor:default}p{margin:8px 16px}</style>
<header>Navegador isolado — sessão de login. Não compartilhe este endereço.</header>
<p id="status">Conectando…</p><img id="screen" tabindex="0" alt="Tela do navegador">
<script>
const s=document.getElementById('screen'), status=document.getElementById('status');
const ws=new WebSocket(`wss://${location.host}/ws?k=__WS_TOKEN__`); ws.binaryType='blob';
let prior=null; ws.onmessage=e=>{if(prior)URL.revokeObjectURL(prior);prior=URL.createObjectURL(e.data);
s.src=prior;status.textContent='Tela ao vivo — clique na imagem e digite no navegador.'};
ws.onclose=()=>status.textContent='Conexão encerrada. Peça um novo acesso ao agente.';
const send=x=>{if(ws.readyState===1)ws.send(JSON.stringify(x))};
const xy=e=>({x:Math.round(e.offsetX*s.naturalWidth/s.clientWidth),
y:Math.round(e.offsetY*s.naturalHeight/s.clientHeight)});
s.onmousedown=e=>{s.focus();send({type:'mouse',action:'down',button:e.button,...xy(e)});e.preventDefault()};
s.onmouseup=e=>{send({type:'mouse',action:'up',button:e.button,...xy(e)});e.preventDefault()};
s.oncontextmenu=e=>e.preventDefault();
s.onwheel=e=>{send({type:'wheel',dx:e.deltaX,dy:e.deltaY,...xy(e)});e.preventDefault()};
s.onkeydown=e=>{if(e.key==='Tab'||e.key==='Enter'||e.key==='Backspace'||e.key==='Delete'||
e.key==='Escape'||e.key.startsWith('Arrow')||e.ctrlKey||e.metaKey){send({type:'key',key:e.key,code:e.code,
ctrl:e.ctrlKey,shift:e.shiftKey,alt:e.altKey,meta:e.metaKey});e.preventDefault()}else if(e.key.length===1){send({type:'text',text:e.key});e.preventDefault()}};
s.onpaste=e=>{send({type:'text',text:e.clipboardData.getData('text').slice(0,1000)});e.preventDefault()};
</script></html>'''


def is_allowed_peer(peer: str, lan: str) -> bool:
    try:
        return ipaddress.ip_address(peer) in ipaddress.ip_network(lan, strict=False)
    except ValueError:
        return False


def safe_event(event: dict) -> bool:
    if not isinstance(event, dict):
        return False
    kind = event.get('type')
    if kind == 'mouse':
        return event.get('action') in ('down', 'up') and event.get('button') in (0, 1, 2) and all(
            isinstance(event.get(k), int) and 0 <= event[k] <= 2000 for k in ('x', 'y'))
    if kind == 'wheel':
        return all(isinstance(event.get(k), (int, float)) and abs(event[k]) <= 2000
                   for k in ('x', 'y', 'dx', 'dy'))
    if kind == 'text':
        return isinstance(event.get('text'), str) and 0 < len(event['text']) <= 1000
    if kind == 'key':
        return isinstance(event.get('key'), str) and len(event['key']) <= 20 and isinstance(event.get('code'), str) and len(event['code']) <= 32
    return False


class CDP:
    def __init__(self, browser_http):
        self.browser_http = browser_http
        self.ws = None
        self.current_target = None
        self.lock = asyncio.Lock()
        self.http = None
        self.sequence = 0

    async def close(self):
        if self.ws:
            await self.ws.close()
        if self.http:
            await self.http.close()

    async def target(self):
        if self.http is None:
            self.http = ClientSession()
        async with self.http.get(self.browser_http + '/json/list') as response:
            response.raise_for_status()
            pages = [t for t in await response.json() if t.get('type') == 'page']
        if not pages:
            raise RuntimeError('Nenhuma aba disponível')
        # Chrome lists the most recently opened target first.
        page = pages[0]
        if page['id'] != self.current_target:
            if self.ws:
                await self.ws.close()
            self.ws = await self.http.ws_connect(page['webSocketDebuggerUrl'], heartbeat=20)
            self.current_target = page['id']
        return self.ws

    async def command(self, method, params=None):
        async with self.lock:
            ws = await self.target()
            self.sequence += 1
            number = self.sequence
            await ws.send_json({'id': number, 'method': method, 'params': params or {}})
            while True:
                message = await ws.receive(timeout=12)
                if message.type != WSMsgType.TEXT:
                    raise RuntimeError('Chrome desconectou')
                data = json.loads(message.data)
                if data.get('id') == number:
                    if 'error' in data:
                        raise RuntimeError(data['error'].get('message', 'Erro CDP'))
                    return data.get('result', {})


STATE = web.AppKey('state', dict)
CDP_KEY = web.AppKey('cdp', CDP)


async def event_to_cdp(cdp, event):
    kind = event['type']
    if kind == 'text':
        await cdp.command('Input.insertText', {'text': event['text']})
    elif kind == 'key':
        key, code = event['key'], event['code']
        special = {'Enter': 13, 'Tab': 9, 'Backspace': 8, 'Delete': 46, 'Escape': 27,
                   'ArrowLeft': 37, 'ArrowUp': 38, 'ArrowRight': 39, 'ArrowDown': 40}
        modifiers = (1 if event.get('alt') else 0) | (2 if event.get('ctrl') else 0) | (4 if event.get('meta') else 0) | (8 if event.get('shift') else 0)
        data = {'key': key, 'code': code, 'windowsVirtualKeyCode': special.get(key, ord(key.upper()) if len(key) == 1 else 0), 'modifiers': modifiers}
        for state in ('rawKeyDown', 'keyUp'):
            await cdp.command('Input.dispatchKeyEvent', {'type': state, **data})
    elif kind == 'mouse':
        buttons = {0: 'left', 1: 'middle', 2: 'right'}
        await cdp.command('Input.dispatchMouseEvent', {'type': 'mousePressed' if event['action'] == 'down' else 'mouseReleased',
                          'x': event['x'], 'y': event['y'], 'button': buttons[event['button']], 'clickCount': 1})
    else:
        await cdp.command('Input.dispatchMouseEvent', {'type': 'mouseWheel', 'x': event['x'], 'y': event['y'],
                          'deltaX': event['dx'], 'deltaY': event['dy']})


def create_app(token, lan, browser_http, ttl=1800):
    app = web.Application(client_max_size=4096)
    app[STATE] = {'token': token, 'ticket_used': False, 'cookie': secrets.token_urlsafe(32),
                  'ws_token': secrets.token_urlsafe(32),
                  'expires': time.monotonic() + ttl, 'viewer_active': False}
    app[CDP_KEY] = CDP(browser_http)
    state = app[STATE]

    @web.middleware
    async def access(request, handler):
        peer = request.remote or ''
        if not (is_allowed_peer(peer, lan) or peer in ('127.0.0.1', '::1')) or time.monotonic() > state['expires']:
            print(f'viewer peer={peer} path={request.path} denied=network-or-expiry', flush=True)
            raise web.HTTPForbidden()
        try:
            response = await handler(request)
            print(f'viewer peer={peer} path={request.path} status={response.status}', flush=True)
            return response
        except web.HTTPException as exc:
            print(f'viewer peer={peer} path={request.path} status={exc.status}', flush=True)
            raise

    app.middlewares.append(access)

    async def entry(request):
        if hmac.compare_digest(request.cookies.get('viewer', ''), state['cookie']):
            response = web.Response(text=HTML.replace('__WS_TOKEN__', state['ws_token']), content_type='text/html')
        elif (not state['ticket_used'] and request.query.get('ticket') and
              hmac.compare_digest(request.query['ticket'], state['token'])):
            # A link preview may GET the URL before the user does. Only a human
            # confirmation POST consumes the one-time ticket.
            ticket = html.escape(state['token'], quote=True)
            response = web.Response(text=(
                '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
                '<title>Acesso ao navegador isolado</title>'
                '<p>Este acesso controla o navegador isolado do agente.</p>'
                '<form method="post" action="/activate"><input type="hidden" name="ticket" value="'
                + ticket + '"><button>Entrar no navegador</button></form></html>'), content_type='text/html')
        else:
            # Some clients open only the origin, dropping the query string from
            # a copied link. Offer a manual ticket entry without weakening auth.
            response = web.Response(text=(
                '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
                '<title>Acesso ao navegador isolado</title>'
                '<p>Informe o código de acesso fornecido pelo agente para abrir o navegador do jogo.</p>'
                '<form method="post" action="/activate">'
                '<input type="text" name="ticket" autocomplete="off" required>'
                '<button>Entrar no navegador</button></form></html>'), content_type='text/html')
        response.headers.update({'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
            'X-Frame-Options': 'DENY', 'Content-Security-Policy': "default-src 'none'; img-src blob:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'self'"})
        return response

    async def activate(request):
        # A browser can report an opaque/missing Origin after the user accepts
        # a self-signed certificate. The one-time random ticket is the CSRF
        # secret; a foreign page cannot read it from our landing page.
        fields = await request.post()
        if state['ticket_used'] or not hmac.compare_digest(fields.get('ticket', ''), state['token']):
            raise web.HTTPForbidden(text='Ingresso inválido ou já utilizado')
        state['ticket_used'] = True
        response = web.Response(status=303, headers={'Location': '/', 'Cache-Control': 'no-store'})
        response.set_cookie('viewer', state['cookie'], secure=True, httponly=True, samesite='Lax', max_age=ttl)
        return response

    async def screen(request):
        if not hmac.compare_digest(request.cookies.get('viewer', ''), state['cookie']):
            raise web.HTTPForbidden()
        # The per-session secret embedded in the authenticated HTML prevents
        # cross-site WebSocket hijacking even when Origin is opaque or absent.
        if not hmac.compare_digest(request.query.get('k', ''), state['ws_token']):
            raise web.HTTPForbidden()
        if state['viewer_active']:
            raise web.HTTPConflict(text='Já existe um espectador conectado')
        state['viewer_active'] = True
        ws = web.WebSocketResponse(heartbeat=20, max_msg_size=2048)
        await ws.prepare(request)

        async def frames():
            while not ws.closed:
                result = await app[CDP_KEY].command('Page.captureScreenshot', {'format': 'jpeg', 'quality': 65, 'captureBeyondViewport': False})
                await ws.send_bytes(base64.b64decode(result['data']))
                await asyncio.sleep(0.6)
        job = asyncio.create_task(frames())
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        event = json.loads(msg.data)
                        if safe_event(event):
                            await event_to_cdp(app[CDP_KEY], event)
                    except (ValueError, RuntimeError, asyncio.TimeoutError):
                        pass
        finally:
            job.cancel()
            await asyncio.gather(job, return_exceptions=True)
            state['viewer_active'] = False
        return ws

    async def cleanup(app):
        await app[CDP_KEY].close()

    app.router.add_get('/', entry)
    app.router.add_post('/activate', activate)
    app.router.add_get('/ws', screen)
    app.on_cleanup.append(cleanup)
    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', required=True, help='LAN IPv4 address, never 0.0.0.0')
    parser.add_argument('--lan', required=True, help='Allowed client subnet (CIDR)')
    parser.add_argument('--cert', type=Path, required=True)
    parser.add_argument('--key', type=Path, required=True)
    parser.add_argument('--ticket-file', type=Path, required=True)
    parser.add_argument('--cdp', default='http://127.0.0.1:9223')
    args = parser.parse_args()
    if ipaddress.ip_address(args.bind) not in ipaddress.ip_network(args.lan, strict=False):
        parser.error('Bind address is not on allowed LAN')
    if args.bind == '0.0.0.0':
        parser.error('Public bind forbidden')
    token = args.ticket_file.read_text().strip()
    if len(token) < 40:
        parser.error('Ticket too short')
    args.ticket_file.unlink()
    import ssl
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(args.cert, args.key)
    web.run_app(create_app(token, args.lan, args.cdp), host=args.bind, port=8443,
                ssl_context=ctx, access_log=None, print=None)


if __name__ == '__main__':
    main()
