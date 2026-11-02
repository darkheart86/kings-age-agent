import json
import unittest

from snapshot import interpret


class SnapshotTests(unittest.TestCase):
    def test_parses_nested_json_strings_from_browser_snapshot(self):
        raw = {
            "host": "s99-br.kingsage.gameforge.com",
            "page": "/",
            "hints": json.dumps([
                {"id": "build_main", "text": "Ajuda Fórum Logout"},
                {"id": "", "text": "100  300  400  1.000"},
                {"id": "stone", "text": "300"},
                {"id": "wood", "text": "500"},
                {"id": "iron", "text": "400"},
                {"id": "", "text": "Castelo\n(Nível 2)\nO castelo é o coração da sua aldeia."},
            ], ensure_ascii=False),
            "forms": "[]",
            "controls": json.dumps([{"text": "Construir", "path": "/"}]),
        }
        result = interpret(raw)
        self.assertEqual(result["resources"], {"wood": 500, "stone": 300, "iron": 400})
        self.assertEqual(result["buildings"], {"castle": 2})
        self.assertEqual(result["observation_status"], "partial")
        self.assertIn("queue", result["unknown"])
        self.assertIn("capacity", result["unknown"])
        self.assertIn("workers", result["unknown"])
        self.assertIn("next_level_cost", result["unknown"])
        self.assertEqual(result["commands"], "disabled")


if __name__ == "__main__":
    unittest.main()
