import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from planner import decide


class PlannerTests(unittest.TestCase):
    def test_builds_only_next_castle_level_when_affordable(self):
        state = {
            "buildings": {"castle": 7, "warehouse": 2},
            "resources": {"wood": 100, "stone": 100, "ore": 100},
            "capacity": 200,
            "queue": [],
            "next_levels": {
                "castle": {"level": 8, "cost": {"wood": 30, "stone": 40, "ore": 20}, "requires": {}}
            },
        }
        result = decide(state, mode="autonomous")
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["action"], {"building": "castle", "level": 8})

    def test_waits_for_queued_building_before_sending_another(self):
        state = {
            "buildings": {"castle": 7},
            "resources": {"wood": 100},
            "capacity": 200,
            "queue": [{"building": "castle", "level": 8}],
            "next_levels": {"castle": {"level": 8, "cost": {"wood": 30}, "requires": {}}},
        }
        self.assertEqual(decide(state, "autonomous")["status"], "waiting")

    def test_resolves_building_prerequisite_before_castle(self):
        state = {
            "buildings": {"castle": 7, "warehouse": 2},
            "resources": {"wood": 100},
            "capacity": 200,
            "queue": [],
            "next_levels": {
                "castle": {"level": 8, "cost": {"wood": 40}, "requires": {"warehouse": 3}},
                "warehouse": {"level": 3, "cost": {"wood": 20}, "requires": {}},
            },
        }
        self.assertEqual(decide(state, "autonomous")["action"], {"building": "warehouse", "level": 3})

    def test_upgrades_warehouse_if_castle_cost_exceeds_storage(self):
        state = {
            "buildings": {"castle": 7, "warehouse": 2},
            "resources": {"wood": 80, "stone": 80},
            "capacity": 100,
            "queue": [],
            "next_levels": {
                "castle": {"level": 8, "cost": {"wood": 120, "stone": 50}, "requires": {}},
                "warehouse": {"level": 3, "cost": {"wood": 60, "stone": 30}, "requires": {}},
            },
        }
        self.assertEqual(decide(state, "autonomous")["action"], {"building": "warehouse", "level": 3})

    def test_planning_mode_requires_approval_even_when_affordable(self):
        state = {
            "buildings": {"castle": 7}, "resources": {"wood": 100},
            "capacity": 200, "queue": [],
            "next_levels": {"castle": {"level": 8, "cost": {"wood": 30}, "requires": {}}},
        }
        result = decide(state, "planning")
        self.assertEqual(result["status"], "approval_required")
        self.assertEqual(result["action"], {"building": "castle", "level": 8})

    def test_blocks_when_cost_not_observed(self):
        state = {
            "buildings": {"castle": 7}, "resources": {"wood": 100},
            "capacity": 200, "queue": [],
            "next_levels": {"castle": {"level": 8, "requires": {}}},
        }
        self.assertEqual(decide(state, "autonomous")["status"], "blocked")

    def test_autonomous_mode_stops_for_unapproved_prerequisite(self):
        state = {
            "buildings": {"castle": 7, "barracks": 1},
            "resources": {"wood": 100}, "capacity": 200, "queue": [],
            "next_levels": {
                "castle": {"level": 8, "cost": {"wood": 30}, "requires": {"barracks": 2}},
                "barracks": {"level": 2, "cost": {"wood": 10}, "requires": {}},
            },
        }
        result = decide(state, "autonomous")
        self.assertEqual(result["status"], "approval_required")
        self.assertEqual(result["action"], {"building": "barracks", "level": 2})

    def test_blocks_live_upgrade_when_button_is_disabled(self):
        state = {
            "buildings": {"castle": 4}, "resources": {"wood": 200, "stone": 200, "iron": 200},
            "capacity": 1000, "free_workers": 50, "queue": [],
            "next_levels": {"castle": {"level": 5, "cost": {"wood": 129, "stone": 159, "iron": 120},
                                       "workers": 0, "enabled": False}},
        }
        self.assertEqual(decide(state, "autonomous")["status"], "blocked")

    def test_waits_when_live_upgrade_needs_more_workers(self):
        state = {
            "buildings": {"castle": 5}, "resources": {"wood": 200, "stone": 200, "iron": 200},
            "capacity": 1000, "free_workers": 0, "queue": [],
            "next_levels": {"castle": {"level": 6, "cost": {"wood": 150, "stone": 186, "iron": 139},
                                       "workers": 1, "enabled": True}},
        }
        self.assertEqual(decide(state, "autonomous")["status"], "waiting")

    def test_cli_reads_state_file_and_outputs_decision(self):
        state = {
            "buildings": {"castle": 10}, "resources": {},
            "capacity": 100, "queue": [], "next_levels": {},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(json.dumps(state), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "planner.py", str(path), "--mode", "autonomous"],
                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "complete")


if __name__ == "__main__":
    unittest.main()
