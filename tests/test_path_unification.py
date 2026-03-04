import unittest
from pathlib import Path
import tempfile

from src.auto_write_txt_to_docs import path_utils


class PathUnificationTests(unittest.TestCase):
    def test_path_utils_uses_user_config_for_active_files(self):
        user_config_dir = path_utils.get_user_config_dir()

        self.assertEqual(path_utils.CONFIG_FILE.parent, user_config_dir)
        self.assertEqual(path_utils.CONFIG_FILE.name, "config.json")
        self.assertEqual(path_utils.CACHE_FILE.parent, user_config_dir / "cache")
        self.assertEqual(path_utils.CACHE_FILE.name, "added_lines_cache.json")
        self.assertEqual(path_utils.USER_CREDENTIALS_FILE.parent, user_config_dir)
        self.assertEqual(path_utils.USER_CREDENTIALS_FILE.name, "developer_credentials.json")

    def test_path_utils_exposes_legacy_project_paths(self):
        self.assertEqual(path_utils.LEGACY_CONFIG_FILE, path_utils.PROJECT_ROOT / "config.json")
        self.assertEqual(path_utils.LEGACY_CACHE_FILE, path_utils.PROJECT_ROOT / "added_lines_cache.json")

    def test_main_gui_uses_shared_path_constants(self):
        source = Path("main_gui.py").read_text(encoding="utf-8")

        self.assertIn("CONFIG_FILE_STR", source)
        self.assertIn("LOG_DIR_STR", source)
        self.assertIn("USER_CREDENTIALS_FILE_STR", source)
        self.assertIn("get_effective_credentials_path", source)
        self.assertNotIn('PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))', source)
        self.assertNotIn('CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")', source)

    def test_backend_processor_uses_shared_path_constants(self):
        source = Path("src/auto_write_txt_to_docs/backend_processor.py").read_text(encoding="utf-8")

        self.assertIn("CACHE_FILE_STR", source)
        self.assertIn("LEGACY_CACHE_FILE_STR", source)
        self.assertIn("LOG_DIR_STR", source)
        self.assertIn("PROCESSED_STATE_FILE_STR", source)
        self.assertIn("LINE_CACHE_FILE = CACHE_FILE_STR", source)
        self.assertNotIn("PROJECT_ROOT = os.path.dirname", source)

    def test_effective_credentials_path_prefers_user_override(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            user_path = Path(temp_dir) / "user_credentials.json"
            bundled_path = Path(temp_dir) / "bundled_credentials.json"
            user_path.write_text("user", encoding="utf-8")
            bundled_path.write_text("bundled", encoding="utf-8")

            effective_path = path_utils.get_effective_credentials_path(
                user_credentials_path=user_path,
                bundled_credentials_path=bundled_path,
            )

        self.assertEqual(effective_path, user_path)

    def test_effective_credentials_path_falls_back_to_bundled_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            user_path = Path(temp_dir) / "missing_user_credentials.json"
            bundled_path = Path(temp_dir) / "bundled_credentials.json"
            bundled_path.write_text("bundled", encoding="utf-8")

            effective_path = path_utils.get_effective_credentials_path(
                user_credentials_path=user_path,
                bundled_credentials_path=bundled_path,
            )

        self.assertEqual(effective_path, bundled_path)


if __name__ == "__main__":
    unittest.main()
