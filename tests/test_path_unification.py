import unittest
from pathlib import Path

from src.auto_write_txt_to_docs import path_utils


class PathUnificationTests(unittest.TestCase):
    def test_path_utils_uses_user_config_for_active_files(self):
        user_config_dir = path_utils.get_user_config_dir()

        self.assertEqual(path_utils.CONFIG_FILE.parent, user_config_dir)
        self.assertEqual(path_utils.CONFIG_FILE.name, "config.json")
        self.assertEqual(path_utils.CACHE_FILE.parent, user_config_dir / "cache")
        self.assertEqual(path_utils.CACHE_FILE.name, "added_lines_cache.json")

    def test_path_utils_exposes_legacy_project_paths(self):
        self.assertEqual(path_utils.LEGACY_CONFIG_FILE, path_utils.PROJECT_ROOT / "config.json")
        self.assertEqual(path_utils.LEGACY_CACHE_FILE, path_utils.PROJECT_ROOT / "added_lines_cache.json")

    def test_main_gui_uses_shared_path_constants(self):
        source = Path("main_gui.py").read_text(encoding="utf-8")

        self.assertIn("CONFIG_FILE_STR", source)
        self.assertIn("LOG_DIR_STR", source)
        self.assertNotIn('PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))', source)
        self.assertNotIn('CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")', source)

    def test_backend_processor_uses_shared_path_constants(self):
        source = Path("src/auto_write_txt_to_docs/backend_processor.py").read_text(encoding="utf-8")

        self.assertIn("from .path_utils import CACHE_FILE_STR, LEGACY_CACHE_FILE_STR, LOG_DIR_STR", source)
        self.assertIn("LINE_CACHE_FILE = CACHE_FILE_STR", source)
        self.assertNotIn("PROJECT_ROOT = os.path.dirname", source)


if __name__ == "__main__":
    unittest.main()
