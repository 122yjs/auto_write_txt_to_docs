import os
import tempfile
import unittest
from datetime import datetime
from src.auto_write_txt_to_docs.dual_output import DualOutputManager, get_dual_output_manager


class DualOutputManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DualOutputManager(self.temp_dir)

    def test_creates_directories(self):
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "raw")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "deduped")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "html")))

    def test_write_raw_appends_content(self):
        self.manager.write_raw("/tmp/test.txt", ["line 1", "line 2"])
        files = os.listdir(os.path.join(self.temp_dir, "raw"))
        self.assertEqual(len(files), 1)
        with open(os.path.join(self.temp_dir, "raw", files[0]), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("line 1", content)
        self.assertIn("line 2", content)
        self.assertIn("test.txt", content)

    def test_write_deduped_appends_content(self):
        self.manager.write_deduped("/tmp/test.txt", ["line 1"], duplicate_count=5)
        files = os.listdir(os.path.join(self.temp_dir, "deduped"))
        self.assertEqual(len(files), 1)
        with open(os.path.join(self.temp_dir, "deduped", files[0]), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("line 1", content)
        self.assertIn("중복 제거: 5줄", content)

    def test_generate_html_creates_file(self):
        self.manager.write_raw("/tmp/test.txt", ["line 1", "line 2"])
        self.manager.write_deduped("/tmp/test.txt", ["line 1"], duplicate_count=1)
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        html_path = self.manager.generate_html(date_str)
        
        self.assertTrue(os.path.exists(html_path))
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("메신저 문서 리포트", content)
        self.assertIn("line 1", content)

    def test_get_dual_output_manager_disabled(self):
        config = {"dual_output_enabled": False}
        manager = get_dual_output_manager(config)
        self.assertIsNone(manager)

    def test_get_dual_output_manager_enabled(self):
        config = {"dual_output_enabled": True, "dual_output_dir": self.temp_dir}
        manager = get_dual_output_manager(config)
        self.assertIsNotNone(manager)
        self.assertEqual(manager.output_dir, self.temp_dir)


if __name__ == "__main__":
    unittest.main()
