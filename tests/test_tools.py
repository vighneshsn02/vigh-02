"""
Unit tests for File, Search, and Edit Tools.
"""

import tempfile
import unittest
from pathlib import Path

from vigh_agent.tools.file_tools import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from vigh_agent.tools.search_tools import SearchCodeTool, OutlineSymbolsTool
from vigh_agent.utils.diff_utils import undo_manager


class TestTools(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_and_read_file(self):
        writer = WriteFileTool()
        reader = ReadFileTool()

        write_res = writer.run(
            path="sub/folder/hello.py",
            content="print('Hello VIGH-02!')\nline2 = 123\n",
            workspace_root=str(self.workspace)
        )
        self.assertTrue(write_res["success"])
        self.assertTrue(write_res["is_new"])

        read_res = reader.run(
            path="sub/folder/hello.py",
            workspace_root=str(self.workspace)
        )
        self.assertTrue(read_res["success"])
        self.assertIn("Hello VIGH-02", read_res["content"])
        self.assertEqual(read_res["total_lines"], 2)

    def test_edit_file_and_undo(self):
        writer = WriteFileTool()
        editor = EditFileTool()

        # Create initial file
        writer.run(
            path="math_ops.py",
            content="def add(a, b):\n    return a + b\n",
            workspace_root=str(self.workspace)
        )

        # Edit function
        edit_res = editor.run(
            path="math_ops.py",
            target_snippet="return a + b",
            replacement_snippet="return a + b + 0  # optimized",
            workspace_root=str(self.workspace)
        )
        self.assertTrue(edit_res["success"])
        self.assertIn("+", edit_res["diff"])

        # Verify content
        reader = ReadFileTool()
        read_res = reader.run(path="math_ops.py", workspace_root=str(self.workspace))
        self.assertIn("# optimized", read_res["content"])

        # Test Undo
        undo_ok, undo_msg = undo_manager.undo_last()
        self.assertTrue(undo_ok)

        # Verify reverted content
        read_reverted = reader.run(path="math_ops.py", workspace_root=str(self.workspace))
        self.assertNotIn("# optimized", read_reverted["content"])
        self.assertIn("return a + b", read_reverted["content"])

    def test_search_and_outline_symbols(self):
        writer = WriteFileTool()
        writer.run(
            path="calculator.py",
            content="""
class Calculator:
    def multiply(self, x, y):
        return x * y

    async def async_divide(self, x, y):
        return x / y
""",
            workspace_root=str(self.workspace)
        )

        searcher = SearchCodeTool()
        search_res = searcher.run(query="multiply", workspace_root=str(self.workspace))
        self.assertTrue(search_res["success"])
        self.assertEqual(search_res["total_matches"], 1)

        outliner = OutlineSymbolsTool()
        outline_res = outliner.run(path="calculator.py", workspace_root=str(self.workspace))
        self.assertTrue(outline_res["success"])
        symbol_names = [s["name"] for s in outline_res["symbols"]]
        self.assertIn("Calculator", symbol_names)
        self.assertIn("multiply", symbol_names)
        self.assertIn("async_divide", symbol_names)


if __name__ == "__main__":
    unittest.main()
