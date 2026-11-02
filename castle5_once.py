"""One-shot authorized Castle 4 -> 5. No retries on ambiguous output."""
import asyncio
import json
import os
import re
import urllib.parse
import urllib.request
from aiohttp import ClientSession

HOST = os.environ.get('KINGSAGE_HOST', '')
VILLAGE = os.environ.get('KINGSAGE_VILLAGE', '')
PORT = 9224
EXPECTED_COST = {'wood': 129, 'stone': 159, 'iron': 120}


def validate_target():
    if not re.fullmatch(r's[0-9]+-[a-z]{2}\.kingsage\.gameforge\.com', HOST):
        raise ValueError('Set KINGSAGE_HOST to a KingsAge world host')
    if not re.fullmatch(r'[0-9]+', VILLAGE):
        raise ValueError('Set KINGSAGE_VILLAGE to the numeric village ID')


def resource_debit_confirmed(before, after, costs):
    def number(x):
        if not isinstance(x, str) or not re.fullmatch(r'[0-9]+', x):
            raise ValueError('Missing numeric resource in postcheck')
        return int(x)
    return all(before[k] - number(after[k]) >= costs[k] for k in costs)


def page():
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list', timeout=4) as response:
        pages = json.load(response)
    matching = []
    for item in pages:
        url = urllib.parse.urlsplit(item.get('url', ''))
        q = urllib.parse.parse_qs(url.query)
        if (item.get('type') == 'page' and url.scheme == 'https'
                and url.hostname == HOST and q.get('village') == [VILLAGE]
                and q.get('s') == ['build_main']):
            matching.append(item)
    if len(matching) != 1:
        raise ValueError('Expected precisely one authenticated build_main tab')
    ws = urllib.parse.urlsplit(matching[0]['webSocketDebuggerUrl'])
    if ws.scheme != 'ws' or not ws.path.startswith('/devtools/page/'):
        raise ValueError('Invalid local debugger target')
    return urllib.parse.urlunsplit(('ws', f'127.0.0.1:{PORT}', ws.path, ws.query, ''))


async def command(ws, number, method, params):
    await ws.send_json({'id': number, 'method': method, 'params': params})
    while True:
        message = await ws.receive(timeout=10)
        if message.type.name != 'TEXT':
            raise ValueError('Browser disconnected (never retry an action)')
        data = json.loads(message.data)
        if data.get('id') == number:
            if data.get('error') or data.get('result', {}).get('exceptionDetails'):
                raise ValueError('Browser command ambiguous or failed (never retry)')
            return data.get('result', {})


PRECONDITION = r'''(() => {
  const q = new URLSearchParams(location.search);
  const cards = [...document.querySelectorAll('.mainBuildList .box')];
  const stone = cards.find(e => (e.innerText || '').replace(/\s+/g, ' ').trim().startsWith('Castelo (Nível 4)'));
  const a = [...(stone?.querySelectorAll('a[href]') || [])]
    .find(a => new URL(a.href).searchParams.get('a') === 'buildBuilding');
  const text = e => (e?.innerText || e?.textContent || '').replace(/\s+/g, ' ').trim();
  const worker = [...document.querySelectorAll('img[title]')]
    .find(e => e.title === 'Colonos livres');
  return {
    host: location.hostname, village: q.get('village'), page: q.get('s'),
    marker: !!document.querySelector('#build_main'), ready: document.readyState,
    queue_active: [...document.querySelectorAll('.borderlist')].some(e => /cancelar/i.test(text(e))),
    castle_level: stone ? 4 : null,
    cost: {wood:text(stone?.querySelector('.res1')), stone:text(stone?.querySelector('.res2')),
      iron:text(stone?.querySelector('.res3'))},
    available: {wood:text(document.getElementById('wood')),
      stone:text(document.getElementById('stone')), iron:text(document.getElementById('iron'))},
    free_workers: text(worker?.parentElement?.parentElement),
    needed_workers: text(stone?.querySelector('.workers')),
    action: a?.href || null
  };
})()'''

POSTCHECK = r'''(() => {
  const text = e => (e?.innerText || e?.textContent || '').replace(/\s+/g, ' ').trim();
  const cards = [...document.querySelectorAll('.mainBuildList .box')];
  const stone = cards.find(e => text(e).startsWith('Castelo (Nível '));
  const queue = [...document.querySelectorAll('.borderlist')].map(text).filter(x => /cancelar/i.test(x));
  return {
    host: location.hostname, village:new URLSearchParams(location.search).get('village'),
    page:new URLSearchParams(location.search).get('s'), marker:!!document.querySelector('#build_main'),
    castle_level: Number(text(stone).match(/^Castelo \(Nível (\d+)\)/)?.[1] || 0),
    resources: {wood:text(document.getElementById('wood')),
      stone:text(document.getElementById('stone')), iron:text(document.getElementById('iron'))},
    queue_active:queue.length>0,
    castle5_queued:queue.some(x=>/Castelo\s*\(Nível\s*5\)/i.test(x)),
    queue_excerpt:queue.map(x=>x.replace(/\d{1,2}:\d{2}:\d{2}/g,'[tempo]').slice(0,100))
  };
})()'''


async def main():
    validate_target()
    socket_url = page()
    async with ClientSession() as session:
        async with session.ws_connect(socket_url, timeout=5) as ws:
            # Resources update client-side, but the build button is rendered
            # server-side: refresh once, using a fixed read-only page URL.
            await command(ws, 1, 'Page.navigate',
                          {'url': f'https://{HOST}/?village={VILLAGE}&s=build_main'})
            await asyncio.sleep(1)
            raw = await command(ws, 2, 'Runtime.evaluate',
                                {'expression': PRECONDITION, 'returnByValue': True})
            value = raw.get('result', {}).get('value')
            if not isinstance(value, dict):
                raise ValueError('Missing live precondition')
            if (value.get('host') != HOST or value.get('village') != VILLAGE
                    or value.get('page') != 'build_main' or value.get('marker') is not True
                    or value.get('ready') != 'complete' or value.get('queue_active') is not False
                    or value.get('castle_level') != 4):
                raise ValueError('Live world, level or queue precondition failed')
            def number(x):
                if not isinstance(x, str) or not re.fullmatch(r'[0-9]+', x):
                    raise ValueError('Missing numeric field')
                return int(x)
            costs = {k: number(value['cost'][k]) for k in EXPECTED_COST}
            available = {k: number(value['available'][k]) for k in EXPECTED_COST}
            if costs != EXPECTED_COST or any(available[k] < costs[k] for k in costs):
                raise ValueError('Costs changed or resources insufficient')
            if number(value['free_workers']) < number(value['needed_workers']):
                raise ValueError('Workers insufficient')
            link = value.get('action')
            if not isinstance(link, str):
                raise ValueError('Build button disabled')
            url = urllib.parse.urlsplit(link)
            q = urllib.parse.parse_qs(url.query)
            if (url.scheme != 'https' or url.hostname != HOST or url.path != '/'
                    or set(q) != {'village', 's', 'a', 'p', 'build'}
                    or q.get('village') != [VILLAGE] or q.get('s') != ['build_main']
                    or q.get('a') != ['buildBuilding'] or q.get('build') != ['main']
                    or len(q.get('p', [])) != 1 or not q['p'][0]):
                raise ValueError('Target build link fails allowlist')
            print('precondition_ok=castle_4_to_5 cost_wood_129_stone_159_iron_120 queue_empty')
            # Exactly one browser action. Do not repeat on error, timeout or redirect.
            try:
                await command(ws, 3, 'Page.navigate', {'url': link})
            except Exception as e:
                print('submission_uncertain_no_retry=', type(e).__name__, str(e))
                return
            print('action_submitted_once=true')
            await asyncio.sleep(1.2)
            try:
                raw = await command(ws, 4, 'Runtime.evaluate',
                                    {'expression': POSTCHECK, 'returnByValue': True})
                post = raw.get('result', {}).get('value')
                if (not isinstance(post, dict) or post.get('host') != HOST
                        or post.get('village') != VILLAGE or post.get('page') != 'build_main'
                        or post.get('marker') is not True):
                    raise ValueError('Post-action browser page not verified')
                if post.get('castle5_queued') is not True and post.get('castle_level') != 5:
                    raise ValueError('Castle upgrade not confirmed; never retry')
                if not resource_debit_confirmed(available, post['resources'], costs):
                    raise ValueError('Resource debit not confirmed; never retry')
                safe = {k: post.get(k) for k in ('castle_level', 'resources',
                                                'queue_active', 'castle5_queued', 'queue_excerpt')}
                print('postcheck=', json.dumps(safe, ensure_ascii=False))
            except Exception as e:
                print('postcheck_uncertain_no_retry=', type(e).__name__, str(e))


if __name__ == '__main__':
    asyncio.run(main())
