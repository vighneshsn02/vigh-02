"""
Unit tests for CodeScannerTool and path utilities.
"""

import tempfile
import unittest
from pathlib import Path

from vigh_agent.tools.code_scanner import CodeScannerTool
from vigh_agent.utils.path_utils import detect_language, is_binary_file, resolve_path


class TestCodeScanner(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

        # Create sample codebase
        (self.workspace / "src").mkdir()
        
        # Python file with TODO and function
        py_file = self.workspace / "src" / "app.py"
        py_file.write_text("""
# TODO: Implement user caching
def compute_metrics(x: int) -> int:
    # BUG: edge case with zero
    return x * 42
""", encoding="utf-8")

        # Security risk test file
        sec_file = self.workspace / "src" / "auth.py"
        sec_file.write_text("""
API_KEY = "sk-1234567890abcdef1234567890abcdef"
def run_dynamic(cmd):
    eval(cmd)
""", encoding="utf-8")

        # JavaScript file
        js_file = self.workspace / "index.js"
        js_file.write_text("""
function startServer() {
  console.log("Starting...");
}
""", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_detect_language(self):
        self.assertEqual(detect_language(Path("test.py")), "python")
        self.assertEqual(detect_language(Path("test.js")), "javascript")
        self.assertEqual(detect_language(Path("test.ts")), "typescript")
        self.assertEqual(detect_language(Path("Dockerfile")), "dockerfile")

    def test_scanner_full_run(self):
        scanner = CodeScannerTool()
        result = scanner.run(path=".", workspace_root=str(self.workspace))

        self.assertTrue(result["success"])
        self.assertGreater(result["total_files"], 0)
        self.assertGreater(result["total_lines_of_code"], 0)

        # Check languages detected
        lang_names = [l["language"] for l in result["languages"]]
        self.assertIn("python", lang_names)
        self.assertIn("javascript", lang_names)

        # Check TODOs extracted
        todos = result["todos"]
        self.assertTrue(any("Implement user caching" in t["comment"] for t in todos))
        self.assertTrue(any("edge case with zero" in t["comment"] for t in todos))

        # Check Security Findings
        sec_findings = result["security_findings"]
        self.assertTrue(len(sec_findings) >= 2)  # Hardcoded key + eval
        self.assertTrue(any("eval" in f["description"].lower() for f in sec_findings))


if __name__ == "__main__":
    unittest.main()
