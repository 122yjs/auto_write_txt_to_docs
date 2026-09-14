import tempfile
import unittest
from pathlib import Path

from src.auto_write_txt_to_docs.autostart_utils import (
    APP_NAME,
    build_windows_startup_launcher_contents,
    get_startup_launcher_path,
    get_windows_startup_dir,
    is_windows_startup_stale,
    is_windows_startup_enabled,
    set_windows_startup_enabled,
    startup_launcher_matches_current,
    supports_windows_startup,
)


class AutostartUtilsTests(unittest.TestCase):
    def test_supports_windows_startup_checks_platform_name(self):
        self.assertTrue(supports_windows_startup(platform_name="win32"))
        self.assertFalse(supports_windows_startup(platform_name="darwin"))

    def test_get_windows_startup_dir_returns_expected_path_on_windows(self):
        startup_dir = get_windows_startup_dir(appdata="C:/Users/test/AppData/Roaming", platform_name="win32")

        self.assertEqual(
            startup_dir,
            Path("C:/Users/test/AppData/Roaming") / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
        )

    def test_get_startup_launcher_path_returns_none_off_windows(self):
        self.assertIsNone(get_startup_launcher_path(platform_name="darwin"))

    def test_build_windows_startup_launcher_contents_uses_script_mode_by_default(self):
        launcher_contents = build_windows_startup_launcher_contents(
            script_path="C:/apps/auto_write/main_gui.py",
            executable_path="C:/Python/python.exe",
            frozen=False,
        )
        normalized_contents = launcher_contents.replace("\\", "/")

        self.assertIn("@echo off", launcher_contents)
        self.assertIn('"C:/Python/python.exe" "C:/apps/auto_write/main_gui.py"', normalized_contents)

    def test_set_windows_startup_enabled_creates_and_removes_launcher_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            launcher_path = Path(temp_dir) / f"{APP_NAME}.cmd"

            enabled_result = set_windows_startup_enabled(
                True,
                launcher_path=launcher_path,
                launcher_contents='@echo off\n"python" "main_gui.py"\n',
            )
            launcher_exists_after_enable = is_windows_startup_enabled(launcher_path=launcher_path)

            disabled_result = set_windows_startup_enabled(False, launcher_path=launcher_path)
            launcher_exists_after_disable = is_windows_startup_enabled(launcher_path=launcher_path)

        self.assertTrue(enabled_result)
        self.assertTrue(launcher_exists_after_enable)
        self.assertFalse(disabled_result)
        self.assertFalse(launcher_exists_after_disable)

    def test_startup_launcher_matches_current_frozen_executable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            launcher_path = Path(temp_dir) / f"{APP_NAME}.cmd"
            launcher_path.write_text('@echo off\nstart "" "C:\\Apps\\New\\MessengerDocsAutoWriter.exe"\n', encoding="utf-8")

            self.assertTrue(
                startup_launcher_matches_current(
                    launcher_path=launcher_path,
                    executable_path="C:/Apps/New/MessengerDocsAutoWriter.exe",
                    frozen=True,
                )
            )
            self.assertFalse(
                startup_launcher_matches_current(
                    launcher_path=launcher_path,
                    executable_path="C:/Apps/Old/MessengerDocsAutoWriter.exe",
                    frozen=True,
                )
            )

    def test_stale_startup_launcher_detects_previous_portable_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            launcher_path = Path(temp_dir) / f"{APP_NAME}.cmd"
            launcher_path.write_text(
                '@echo off\nstart "" "E:\\MessengerDocsAutoWriter-win64-portable (1)\\MessengerDocsAutoWriter.exe"\n',
                encoding="utf-8",
            )

            self.assertTrue(
                is_windows_startup_stale(
                    launcher_path=launcher_path,
                    executable_path="C:/Program Files/MessengerDocsAutoWriter/MessengerDocsAutoWriter.exe",
                    frozen=True,
                )
            )


if __name__ == "__main__":
    unittest.main()
