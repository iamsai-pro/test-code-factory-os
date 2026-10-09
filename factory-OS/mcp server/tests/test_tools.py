import json
import tempfile
import unittest
from pathlib import Path

from tools.calculator import calculate
from tools.json_tools import get_json_value, set_json_value, delete_json_value
from tools.filesystem import resolve_workspace_path

class ToolTests(unittest.TestCase):
    def test_calculator(self):
        self.assertEqual(calculate("25 * 18 + 100"), 550)
        self.assertAlmostEqual(calculate("sin(pi / 2)"), 1.0)

    def test_calculator_rejects_code(self):
        with self.assertRaises((ValueError, SyntaxError)):
            calculate("__import__('os').system('whoami')")

    def test_json_nested(self):
        data = '{"user":{"skills":["Python","AI"]}}'
        self.assertEqual(get_json_value(data, "user.skills.0"), {"found": True, "value": "Python"})
        updated = set_json_value(data, "user.city", '"Nellore"')
        self.assertEqual(json.loads(updated)["user"]["city"], "Nellore")
        deleted = delete_json_value(updated, "user.city")
        self.assertNotIn("city", json.loads(deleted)["user"])

    def test_workspace_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            resolve_workspace_path("../../secrets.txt")

if __name__ == "__main__":
    unittest.main()
