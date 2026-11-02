"""Read-only KingsAge state from the user's forwarded, dedicated Chrome tab.

Never requests game actions, cookies, page HTML or session-bearing URLs.
"""
import argparse
import asyncio
import json
import re
from urllib.parse import parse_qs, urlsplit, urlunsplit
from urllib.request import urlopen

from aiohttp import ClientSession


DOM_OBSERVATION = r'''(() => {
  const text = e => (e?.innerText || e?.textContent || '').replace(/\s+/g, ' ').trim();
  const cards = [...document.querySelectorAll('.mainBuildList .box')];
  const card = label => cards.find(e => text(e).startsWith(label + ' (Nível '));
  const level = e => Number(text(e).match(/^\S+\s*\(Nível\s+(\d+)\)/)?.[1] || 0);
  const castle = card('Castelo');
  const resources = {}, capacity = {}, production = {};
  for (const key of ['wood', 'stone', 'iron']) {
    const el = document.getElementById(key);
    resources[key] = text(el);
    capacity[key] = el?.getAttribute('max') || '';
    production[key] = el?.getAttribute('prod') || '';
  }
  const workerIcon = [...document.querySelectorAll('img[title]')]
    .find(e => e.title === 'Colonos livres');
  const workerCount = text(workerIcon?.parentElement?.parentElement);
  const cardCost = key => text(castle?.querySelector('.res' + key));
  const active = [...document.querySelectorAll('.borderlist')]
    .map(text).filter(t => /cancelar/i.test(t)).map(t => {
      const found = t.match(/Castelo\s*\(Nível\s+(\d+)\)/i);
      return found ? {building:'castle',level:Number(found[1])} : {building:'other'};
    });
  const enabled = [...(castle?.querySelectorAll('a[href]') || [])].some(a => {
    const p = new URL(a.href).searchParams;
    return p.get('a') === 'buildBuilding' && p.get('build') === 'main';
  });
  return {
    host:location.hostname,
    village:new URLSearchParams(location.search).get('village'),
    page:new URLSearchParams(location.search).get('s'),
    page_marker:!!document.querySelector('#build_main'),
    resources,capacity,production,free_workers:workerCount,queue:active,
    buildings:{castle:level(castle),warehouse:level(card('Armazém')),farm:level(card('Moinho'))},
    next_castle:{level:level(castle)+1,cost:{wood:cardCost(1),stone:cardCost(2),iron:cardCost(3)},workers:text(castle?.querySelector('.workers')),enabled}
  };
})()'''


def state_from_observation(observed, expected_host, expected_village):
    """Fail closed on absent, redirected or inconsistent game observations."""
    if (observed.get('host') != expected_host or observed.get('village') != expected_village
            or observed.get('page') != 'build_main' or observed.get('page_marker') is not True):
        raise ValueError('World, village or authenticated build page does not match')

    def integer(value):
        if not isinstance(value, (str, int)) or not re.fullmatch(r'[0-9]+', str(value)):
            raise ValueError('Missing or invalid numeric observation')
        return int(value)

    resources = {k: integer(observed['resources'][k]) for k in ('wood', 'stone', 'iron')}
    capacities = [integer(observed['capacity'][k]) for k in ('wood', 'stone', 'iron')]
    if len(set(capacities)) != 1 or capacities[0] < max(resources.values()):
        raise ValueError('Inconsistent storage capacity')
    buildings = {k: integer(observed['buildings'][k]) for k in ('castle', 'warehouse', 'farm')}
    next_castle = observed['next_castle']
    if integer(next_castle['level']) != buildings['castle'] + 1:
        raise ValueError('Next level does not match current castle')
    cost = {k: integer(next_castle['cost'][k]) for k in resources}
    queue = observed['queue']
    if not isinstance(queue, list) or any(not isinstance(item, dict) for item in queue):
        raise ValueError('Unknown build queue')
    if not isinstance(next_castle['enabled'], bool):
        raise ValueError('Unknown button state')
    return {
        'world': expected_host, 'village': expected_village, 'resources': resources,
        'production': {k: integer(observed['production'][k]) for k in resources},
        'capacity': capacities[0], 'free_workers': integer(observed['free_workers']),
        'buildings': buildings, 'queue': queue,
        'next_levels': {'castle': {'level': integer(next_castle['level']),
                                   'cost': cost, 'workers': integer(next_castle['workers']),
                                   'enabled': next_castle['enabled']}},
        'commands': 'disabled',
    }


async def observe(host, village, port):
    if not (isinstance(port, int) and 0 < port < 65536):
        raise ValueError('Invalid local CDP port')
    with urlopen(f'http://127.0.0.1:{port}/json/list', timeout=5) as response:
        pages = json.load(response)
    matches = [p for p in pages if p.get('type') == 'page'
               and (u := urlsplit(p.get('url', ''))).scheme == 'https'
               and u.hostname == host
               and parse_qs(u.query).get('village') == [village]
               and parse_qs(u.query).get('s') == ['build_main']]
    if len(matches) != 1:
        raise ValueError('Expected exactly one build_main tab for the selected world/village')
    target = urlsplit(matches[0]['webSocketDebuggerUrl'])
    if target.scheme != 'ws' or not target.path.startswith('/devtools/page/'):
        raise ValueError('Invalid page debugger target')
    socket_url = urlunsplit(('ws', f'127.0.0.1:{port}', target.path, target.query, ''))
    async with ClientSession() as session:
        async with session.ws_connect(socket_url, timeout=5) as socket:
            await socket.send_json({'id': 1, 'method': 'Runtime.evaluate',
                                    'params': {'expression': DOM_OBSERVATION, 'returnByValue': True}})
            while True:
                message = await socket.receive(timeout=8)
                if message.type.name != 'TEXT':
                    raise ValueError('Browser evaluation disconnected')
                reply = json.loads(message.data)
                if reply.get('id') == 1:
                    if reply.get('error') or reply.get('result', {}).get('exceptionDetails'):
                        raise ValueError('Browser evaluation failed')
                    result = reply['result']['result']
                    if result.get('type') != 'object' or not isinstance(result.get('value'), dict):
                        raise ValueError('Browser did not return a state object')
                    return state_from_observation(result['value'], host, village)


def main():
    parser = argparse.ArgumentParser(description='Read-only state via forwarded local Chrome CDP')
    parser.add_argument('--host', required=True, help='KingsAge world hostname')
    parser.add_argument('--village', required=True, help='Numeric village ID')
    parser.add_argument('--port', type=int, default=9224)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(observe(args.host, args.village, args.port)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
