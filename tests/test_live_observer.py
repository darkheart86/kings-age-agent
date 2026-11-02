"""Tests for the read-only live CDP state boundary."""
import unittest

from live_observer import state_from_observation


class LiveObserverTests(unittest.TestCase):
    def test_normalizes_verified_world_state_for_planner(self):
        observed = {
            "host": "s99-br.kingsage.gameforge.com", "village": "1234",
            "page": "build_main", "page_marker": True,
            "resources": {"wood": "500", "stone": "200", "iron": "300"},
            "capacity": {"wood": "1000", "stone": "1000", "iron": "1000"},
            "production": {"wood": "100", "stone": "100", "iron": "100"},
            "free_workers": "50", "queue": [],
            "buildings": {"castle": 4, "warehouse": 2, "farm": 2},
            "next_castle": {"level": 5, "cost": {"wood": "129", "stone": "159", "iron": "120"}, "workers": "0", "enabled": False},
        }
        state = state_from_observation(observed, "s99-br.kingsage.gameforge.com", "1234")
        self.assertEqual(state["next_levels"]["castle"]["cost"], {"wood": 129, "stone": 159, "iron": 120})
        self.assertEqual(state["capacity"], 1000)
        self.assertEqual(state["free_workers"], 50)
        self.assertEqual(state["buildings"]["castle"], 4)
        self.assertEqual(state["queue"], [])
        self.assertFalse(state["next_levels"]["castle"]["enabled"])

    def test_rejects_redirected_lobby_instead_of_claiming_game_access(self):
        with self.assertRaisesRegex(ValueError, "World, village or authenticated"):
            state_from_observation({"host": "lobby.kingsage.gameforge.com"},
                                   "s99-br.kingsage.gameforge.com", "1234")


if __name__ == "__main__":
    unittest.main()
