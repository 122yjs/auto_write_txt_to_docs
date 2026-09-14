import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.auto_write_txt_to_docs.config_manager import (
    BACKUP_VERSION,
    build_backup_payload,
    get_default_config,
    load_app_config,
    load_backup_config,
    normalize_config_data,
    save_app_config,
    save_backup_config,
)


class ConfigManagerTests(unittest.TestCase):
    def test_normalize_config_data_uses_defaults_and_known_keys_only(self):
        config_data = normalize_config_data({
            "watch_folder": "E:/logs",
            "use_regex_filter": True,
            "max_cache_size": "5000",
            "unknown_key": "ignore",
        })

        self.assertEqual(config_data["watch_folder"], "E:/logs")
        self.assertTrue(config_data["use_regex_filter"])
        self.assertTrue(config_data["first_run"])
        self.assertFalse(config_data["launch_on_windows_startup"])
        self.assertTrue(config_data["check_updates_on_startup"])
        self.assertTrue(config_data["show_success_notifications"])
        self.assertTrue(config_data["play_event_sounds"])
        self.assertEqual(config_data["file_extensions"], ".txt")
        self.assertEqual(config_data["max_cache_size"], 5000)
        self.assertTrue(config_data["dual_output_enabled"])
        self.assertIn("MessengerDocsAutoWriter", config_data["dual_output_dir"])
        self.assertEqual(config_data["content_parsing_mode"], "line")
        self.assertFalse(config_data["flexible_dedup"]["enabled"])
        self.assertEqual(config_data["flexible_dedup"]["ignore_fields"], [])
        self.assertNotIn("unknown_key", config_data)

    def test_normalize_config_data_preserves_v12_settings(self):
        config_data = normalize_config_data({
            "dual_output_enabled": False,
            "dual_output_dir": "E:/exports",
            "content_parsing_mode": "block",
            "block_separator": "---",
            "field_patterns": {"time": "^시간:(.+)"},
            "flexible_dedup": {"enabled": True, "ignore_fields": ["time", "timestamp"]},
        })

        self.assertFalse(config_data["dual_output_enabled"])
        self.assertEqual(config_data["dual_output_dir"], "E:/exports")
        self.assertEqual(config_data["content_parsing_mode"], "block")
        self.assertEqual(config_data["block_separator"], "---")
        self.assertEqual(config_data["field_patterns"], {"time": "^시간:(.+)"})
        self.assertEqual(
            config_data["flexible_dedup"],
            {"enabled": True, "ignore_fields": ["time", "timestamp"]},
        )

    def test_normalize_config_data_falls_back_to_default_for_invalid_cache_size(self):
        config_data = normalize_config_data({
            "max_cache_size": "-10",
        })

        self.assertEqual(config_data["max_cache_size"], get_default_config()["max_cache_size"])

    def test_save_and_load_app_config_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            saved_config = save_app_config({
                "watch_folder": "E:/chat",
                "docs_input": "docs-id",
                "appearance_mode": "Dark",
                "first_run": False,
                "launch_on_windows_startup": True,
                "check_updates_on_startup": False,
                "show_success_notifications": False,
                "play_event_sounds": False,
                "max_cache_size": "7500",
                "dual_output_enabled": False,
                "dual_output_dir": "E:/exports",
                "content_parsing_mode": "block",
                "block_separator": "---",
                "field_patterns": {"sender": "^송신:(.+)"},
                "flexible_dedup": {"enabled": True, "ignore_fields": ["time"]},
            }, config_path=str(config_path))

            loaded_config, used_path, loaded_from_legacy, config_found = load_app_config(
                config_path=str(config_path),
                legacy_config_path=str(Path(temp_dir) / "legacy.json"),
            )

        self.assertTrue(config_found)
        self.assertFalse(loaded_from_legacy)
        self.assertEqual(used_path, str(config_path))
        self.assertEqual(loaded_config, saved_config)
        self.assertFalse(loaded_config["first_run"])
        self.assertTrue(loaded_config["launch_on_windows_startup"])
        self.assertFalse(loaded_config["check_updates_on_startup"])
        self.assertFalse(loaded_config["show_success_notifications"])
        self.assertFalse(loaded_config["play_event_sounds"])
        self.assertEqual(loaded_config["max_cache_size"], 7500)
        self.assertFalse(loaded_config["dual_output_enabled"])
        self.assertEqual(loaded_config["dual_output_dir"], "E:/exports")
        self.assertEqual(loaded_config["content_parsing_mode"], "block")
        self.assertEqual(loaded_config["field_patterns"], {"sender": "^송신:(.+)"})
        self.assertEqual(loaded_config["flexible_dedup"]["ignore_fields"], ["time"])

    def test_load_app_config_falls_back_to_legacy_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            primary_path = Path(temp_dir) / "config.json"
            legacy_path = Path(temp_dir) / "legacy_config.json"
            legacy_payload = get_default_config()
            legacy_payload.pop("first_run", None)
            legacy_payload["watch_folder"] = "E:/legacy"

            with legacy_path.open("w", encoding="utf-8") as legacy_file:
                json.dump(legacy_payload, legacy_file, indent=4, ensure_ascii=False)

            loaded_config, used_path, loaded_from_legacy, config_found = load_app_config(
                config_path=str(primary_path),
                legacy_config_path=str(legacy_path),
            )

        self.assertTrue(config_found)
        self.assertTrue(loaded_from_legacy)
        self.assertEqual(used_path, str(legacy_path))
        self.assertFalse(loaded_config["first_run"])
        self.assertEqual(loaded_config["watch_folder"], "E:/legacy")

    def test_load_backup_config_defaults_first_run_to_false_for_legacy_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "backup.json"
            legacy_payload = {
                "watch_folder": "E:/chat",
                "backup_date": "2026-03-07 10:00:00",
                "backup_version": BACKUP_VERSION,
            }

            with backup_path.open("w", encoding="utf-8") as backup_file:
                json.dump(legacy_payload, backup_file, indent=4, ensure_ascii=False)

            restored_config, backup_data = load_backup_config(str(backup_path))

        self.assertEqual(backup_data["backup_version"], BACKUP_VERSION)
        self.assertFalse(restored_config["first_run"])
        self.assertEqual(restored_config["watch_folder"], "E:/chat")

    def test_save_and_load_backup_config_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "backup.json"
            backup_time = datetime(2026, 3, 4, 22, 30, 0)
            saved_payload = save_backup_config(
                str(backup_path),
                {
                    "watch_folder": "E:/chat",
                    "file_extensions": ".txt,.log",
                },
                backup_time=backup_time,
            )
            restored_config, backup_data = load_backup_config(str(backup_path))

        self.assertEqual(saved_payload["backup_version"], BACKUP_VERSION)
        self.assertEqual(saved_payload["backup_date"], "2026-03-04 22:30:00")
        self.assertEqual(backup_data["backup_version"], BACKUP_VERSION)
        self.assertEqual(restored_config["watch_folder"], "E:/chat")
        self.assertEqual(restored_config["file_extensions"], ".txt,.log")

    def test_build_backup_payload_includes_metadata(self):
        payload = build_backup_payload(
            {"watch_folder": "E:/chat"},
            backup_time=datetime(2026, 3, 4, 8, 15, 0),
        )

        self.assertEqual(payload["watch_folder"], "E:/chat")
        self.assertEqual(payload["backup_version"], BACKUP_VERSION)
        self.assertEqual(payload["backup_date"], "2026-03-04 08:15:00")


if __name__ == "__main__":
    unittest.main()
