import base64
import unittest
from unittest.mock import AsyncMock
from aiohttp.test_utils import TestClient, TestServer

from login_viewer import CDP_KEY, STATE, create_app, is_allowed_peer, safe_event


class ViewerSafetyTests(unittest.TestCase):
    def test_can_construct_before_event_loop_starts(self):
        app = create_app('test-ticket' * 5, '192.168.68.0/24', 'http://127.0.0.1:9223')
        self.assertFalse(app[STATE]['ticket_used'])

    def test_lan_only(self):
        self.assertTrue(is_allowed_peer('192.168.68.15', '192.168.68.0/24'))
        self.assertFalse(is_allowed_peer('192.168.69.15', '192.168.68.0/24'))
        self.assertFalse(is_allowed_peer('not-an-ip', '192.168.68.0/24'))

    def test_reject_malformed_and_unbounded_inputs(self):
        self.assertTrue(safe_event({'type': 'mouse', 'action': 'down', 'x': 120, 'y': 40, 'button': 0}))
        self.assertFalse(safe_event({'type': 'mouse', 'action': 'down', 'x': -1, 'y': 40, 'button': 0}))
        self.assertFalse(safe_event({'type': 'text', 'text': 'a' * 1001}))
        self.assertFalse(safe_event({'type': 'command', 'method': 'Runtime.evaluate'}))
        self.assertTrue(safe_event({'type': 'key', 'key': 'Enter', 'code': 'Enter'}))


class ViewerAccessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = create_app('secret-token' * 5, '192.168.68.0/24', 'http://127.0.0.1:9223')
        self.client = TestClient(TestServer(self.app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_ticket_is_single_use_and_cookie_is_required(self):
        response = await self.client.get('/', allow_redirects=False)
        self.assertEqual(response.status, 200)
        self.assertIn('Informe o código', await response.text())
        response = await self.client.get('/?ticket=' + 'secret-token' * 5, allow_redirects=False)
        self.assertEqual(response.status, 200)
        self.assertIn('Entrar no navegador', await response.text())
        response = await self.client.get('/?ticket=' + 'secret-token' * 5, allow_redirects=False)
        self.assertEqual(response.status, 200)
        origin = f'https://127.0.0.1:{self.client.server.port}'
        response = await self.client.post('/activate', data={'ticket': 'secret-token' * 5},
                                          headers={'Origin': origin}, allow_redirects=False)
        self.assertEqual(response.status, 303)
        self.assertIn('Secure', response.headers['Set-Cookie'])
        self.assertIn('SameSite=Lax', response.headers['Set-Cookie'])
        response = await self.client.get('/?ticket=' + 'secret-token' * 5, allow_redirects=False)
        self.assertEqual(response.status, 200)
        self.assertIn('Informe o código', await response.text())
        response = await self.client.get('/', headers={'Cookie': 'viewer=' + self.app[STATE]['cookie']})
        self.assertEqual(response.status, 200)

    async def test_post_with_opaque_origin_requires_valid_ticket(self):
        response = await self.client.post('/activate', data={'ticket': 'wrong-ticket'},
                                          headers={'Origin': 'null'}, allow_redirects=False)
        self.assertEqual(response.status, 403)
        self.assertFalse(self.app[STATE]['ticket_used'])
        response = await self.client.post('/activate', data={'ticket': 'secret-token' * 5},
                                          headers={'Origin': 'null'}, allow_redirects=False)
        self.assertEqual(response.status, 303)
        self.assertTrue(self.app[STATE]['ticket_used'])

    async def test_manual_entry_rejects_wrong_ticket(self):
        origin = f'https://127.0.0.1:{self.client.server.port}'
        response = await self.client.post('/activate', data={'ticket': 'not-the-ticket'},
                                          headers={'Origin': origin}, allow_redirects=False)
        self.assertEqual(response.status, 403)
        self.assertFalse(self.app[STATE]['ticket_used'])

    async def test_ws_rejects_missing_capability_before_chrome_access(self):
        response = await self.client.get('/ws', headers={'Cookie': 'viewer=' + self.app[STATE]['cookie']})
        self.assertEqual(response.status, 403)

    async def test_viewer_contains_ws_capability_only_after_cookie(self):
        response = await self.client.get('/')
        self.assertNotIn(self.app[STATE]['ws_token'], await response.text())
        response = await self.client.get('/', headers={'Cookie': 'viewer=' + self.app[STATE]['cookie']})
        self.assertIn('/ws?k=' + self.app[STATE]['ws_token'], await response.text())

    async def test_ws_with_cookie_and_capability_streams_with_opaque_origin(self):
        self.app[CDP_KEY].command = AsyncMock(return_value={'data': base64.b64encode(b'jpeg-frame').decode()})
        ws = await self.client.ws_connect('/ws?k=' + self.app[STATE]['ws_token'], headers={
            'Cookie': 'viewer=' + self.app[STATE]['cookie'], 'Origin': 'null'})
        message = await ws.receive(timeout=2)
        self.assertEqual(message.data, b'jpeg-frame')
        await ws.close()


if __name__ == '__main__':
    unittest.main()
