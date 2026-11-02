"""Security invariants for the Windows-side browser handoff launcher."""
import pathlib
import unittest


class LocalBrowserLauncherTests(unittest.TestCase):
    def test_dedicated_profile_and_loopback_only(self):
        script = pathlib.Path(__file__).resolve().parents[1].joinpath('start-local-browser.ps1').read_text()
        self.assertIn('KingsAge-Agent', script)
        self.assertIn('--user-data-dir=', script)
        self.assertIn('--remote-debugging-address=127.0.0.1', script)
        self.assertIn('--remote-debugging-port=9222', script)
        self.assertNotIn('--remote-debugging-address=0.0.0.0', script)

    def test_reverse_tunnel_is_guest_loopback_only(self):
        script = pathlib.Path(__file__).resolve().parents[1].joinpath('start-local-browser.ps1').read_text()
        self.assertIn('127.0.0.1:9224:127.0.0.1:9222', script)
        self.assertIn('ExitOnForwardFailure=yes', script)
        self.assertIn('StrictHostKeyChecking=ask', script)
        self.assertIn('VmTarget', script)
        self.assertIn('VmFingerprint', script)
        self.assertNotIn('hermes@', script)


if __name__ == '__main__':
    unittest.main()
