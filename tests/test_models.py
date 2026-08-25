"""
Unit tests for Model Registry, Ollama Provider, and Tool Registry.
"""

import unittest
from vigh_agent.models.registry import model_registry
from vigh_agent.tools.registry import tool_registry


class TestModelsAndRegistry(unittest.TestCase):

    def test_tool_schemas_generated(self):
        schemas = tool_registry.get_schemas()
        self.assertGreater(len(schemas), 5)
        names = [s["function"]["name"] for s in schemas]
        self.assertIn("read_file", names)
        self.assertIn("write_file", names)
        self.assertIn("edit_file", names)
        self.assertIn("scan_folder", names)
        self.assertIn("search_code", names)

    def test_fallback_tool_call_parser(self):
        sample_text = """
I will now read the file to check its contents:
<tool_call>
{"name": "read_file", "arguments": {"path": "main.py"}}
</tool_call>
"""
        calls = tool_registry.parse_fallback_tool_calls(sample_text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "read_file")
        self.assertEqual(calls[0][1]["path"], "main.py")

    def test_auto_detect_model(self):
        provider, model = model_registry.auto_detect_best_model()
        self.assertIsNotNone(provider)
        self.assertIsNotNone(model)
        self.assertTrue(len(model) > 0)


if __name__ == "__main__":
    unittest.main()
