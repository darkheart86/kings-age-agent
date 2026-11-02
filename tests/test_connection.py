import unittest
from unittest.mock import Mock

from connection import probe


class ConnectionProbeTests(unittest.TestCase):
    def test_detects_lobby_redirect_instead_of_claiming_account_status(self):
        session = Mock()
        session.get.side_effect = [
            Mock(status_code=200, url="https://s16-br.kingsage.gameforge.com/help.php?m=buildings", text="<h1>Edifícios</h1>"),
            Mock(status_code=200, url="https://lobby.kingsage.gameforge.com", text="<html>Lobby</html>"),
        ]
        result = probe("https://s16-br.kingsage.gameforge.com/", session=session)
        self.assertEqual(result["account_status"], "authentication_required")
        self.assertEqual(result["public_help"], "available")
        self.assertNotIn("resources", result)

    def test_accepts_village_url_without_exposing_query_to_network(self):
        session = Mock()
        session.get.side_effect = [
            Mock(status_code=200, url="https://s99-br.kingsage.gameforge.com/help.php?m=buildings"),
            Mock(status_code=200, url="https://lobby.kingsage.gameforge.com"),
        ]
        result = probe("https://s99-br.kingsage.gameforge.com/?village=1234", session=session)
        self.assertEqual(result["village"], "1234")
        self.assertEqual(session.get.call_args_list[1].args[0], "https://s99-br.kingsage.gameforge.com/game.php?screen=main")

    def test_rejects_non_world_urls_before_any_request(self):
        session = Mock()
        for url in ("http://s16-br.kingsage.gameforge.com/", "https://evil-kingsage.gameforge.com.attacker.test/", "https://lobby.kingsage.gameforge.com/", "https://s16-br.kingsage.gameforge.com/?token=abc"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                probe(url, session=session)
        session.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
