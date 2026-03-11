import unittest
from unittest.mock import patch

from main_gui import (
    MessengerDocsApp,
    build_error_notification_summary,
    build_work_result_notification,
    extract_docs_update_line_count,
    extract_filename_from_log_message,
    should_emit_debounced_failure_notification,
)


class FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakePopupPresenter:
    def __init__(self):
        self.calls = []

    def show(self, title, message, level):
        self.calls.append((title, message, level))
        return True


class MainGuiNotificationTests(unittest.TestCase):
    def test_extract_docs_update_line_count_from_attempt_log(self):
        self.assertEqual(
            extract_docs_update_line_count("  - Google Docs에 12줄 추가 시도 (ID: sample-doc-id)..."),
            12,
        )

    def test_extract_docs_update_line_count_from_success_log(self):
        self.assertEqual(
            extract_docs_update_line_count("Google Docs 업데이트 완료: 3줄 추가"),
            3,
        )

    def test_extract_docs_update_line_count_returns_none_without_line_count(self):
        self.assertIsNone(extract_docs_update_line_count("  - Google Docs 업데이트 완료."))

    def test_extract_filename_from_log_message_uses_explicit_file_marker(self):
        self.assertEqual(
            extract_filename_from_log_message("  - 중복 내용만 감지되어 Google Docs 기록 생략 (파일: sample.txt, 중복 4줄)"),
            "sample.txt",
        )

    def test_extract_filename_from_log_message_reads_processing_start(self):
        self.assertEqual(
            extract_filename_from_log_message("처리 시작: sample.txt"),
            "sample.txt",
        )

    def test_build_work_result_notification_includes_preview_summary(self):
        _title, message = build_work_result_notification(
            "success",
            filename="sample.txt",
            line_count=5,
            preview_text="첫 줄\n둘째 줄\n셋째 줄",
        )

        self.assertIn("sample.txt · 5줄 추가됨", message)
        self.assertIn("첫 줄", message)
        self.assertIn("둘째 줄", message)
        self.assertIn("... 외 3줄", message)

    def test_build_duplicate_recorded_notification_uses_summary_text(self):
        _title, message = build_work_result_notification(
            "duplicate_recorded",
            filename="sample.txt",
            preview_text="이 파일의 내용 7줄은 기존 기록과 모두 중복되어 본문 추가를 생략했습니다.",
        )

        self.assertIn("sample.txt · 본문 중복, 파일명만 기록됨", message)
        self.assertIn("본문 추가를 생략했습니다.", message)

    def test_build_failure_notification_uses_error_summary(self):
        summary = build_error_notification_summary("Docs API 오류", "오류: Docs 업데이트 API 오류 - 403 quota exceeded")
        _title, message = build_work_result_notification(
            "failure",
            filename="sample.txt",
            error_summary=summary,
        )

        self.assertIn("sample.txt · 작업 실패", message)
        self.assertIn("Docs API 오류 - Docs 업데이트 API 오류 - 403 quota exceeded", message)

    def test_should_emit_debounced_failure_notification_suppresses_repeat(self):
        recent_failures = {}

        self.assertTrue(
            should_emit_debounced_failure_notification(
                "sample.txt|Docs API 오류",
                recent_failures,
                current_time=10.0,
            )
        )
        self.assertFalse(
            should_emit_debounced_failure_notification(
                "sample.txt|Docs API 오류",
                recent_failures,
                current_time=11.0,
            )
        )
        self.assertTrue(
            should_emit_debounced_failure_notification(
                "sample.txt|Docs API 오류",
                recent_failures,
                current_time=12.5,
            )
        )

    def test_show_result_popup_notification_maps_duplicate_event_to_duplicate_level(self):
        app = MessengerDocsApp.__new__(MessengerDocsApp)
        presenter = FakePopupPresenter()
        app.result_popup_presenter = presenter
        app.log = lambda _message: None

        result = app.show_result_popup_notification(
            "메신저 Docs 자동 기록",
            "sample.txt · 모든 내용이 중복",
            "duplicate_skipped",
        )

        self.assertTrue(result)
        self.assertEqual(
            presenter.calls,
            [("메신저 Docs 자동 기록", "sample.txt · 모든 내용이 중복", "duplicate")],
        )

    def test_notify_background_event_uses_popup_before_tray_when_enabled(self):
        app = MessengerDocsApp.__new__(MessengerDocsApp)
        app.show_success_notifications = FakeVar(True)
        app.play_event_sounds = FakeVar(True)
        app.recent_failure_notifications = {}
        call_order = []
        sound_calls = []
        app.show_result_popup_notification = lambda title, message, event_type: call_order.append(
            ("popup", title, message, event_type)
        ) or True
        app.show_tray_notification = lambda title, message: call_order.append(("tray", title, message)) or True
        app.play_event_sound = lambda event_type: sound_calls.append(event_type)
        app.log = lambda _message: None

        result = app.notify_background_event(
            "success",
            filename="sample.txt",
            line_count=2,
            preview_text="첫 줄\n둘째 줄",
        )

        self.assertTrue(result)
        self.assertEqual(call_order[0][0], "popup")
        self.assertEqual(call_order[1][0], "tray")
        self.assertEqual(sound_calls, ["success"])

    def test_notify_background_event_skips_popup_and_tray_when_notifications_disabled(self):
        app = MessengerDocsApp.__new__(MessengerDocsApp)
        app.show_success_notifications = FakeVar(False)
        app.play_event_sounds = FakeVar(True)
        app.recent_failure_notifications = {}
        popup_calls = []
        tray_calls = []
        sound_calls = []
        app.show_result_popup_notification = lambda title, message, event_type: popup_calls.append(
            (title, message, event_type)
        ) or True
        app.show_tray_notification = lambda title, message: tray_calls.append((title, message))
        app.play_event_sound = lambda event_type: sound_calls.append(event_type)
        app.log = lambda _message: None

        app.notify_background_event(
            "success",
            filename="sample.txt",
            line_count=2,
            preview_text="첫 줄\n둘째 줄",
        )

        self.assertEqual(popup_calls, [])
        self.assertEqual(tray_calls, [])
        self.assertEqual(sound_calls, ["success"])

    def test_notify_background_event_suppresses_duplicate_failures(self):
        app = MessengerDocsApp.__new__(MessengerDocsApp)
        app.show_success_notifications = FakeVar(True)
        app.play_event_sounds = FakeVar(True)
        app.recent_failure_notifications = {}
        popup_calls = []
        tray_calls = []
        sound_calls = []
        app.show_result_popup_notification = lambda title, message, event_type: popup_calls.append(
            (title, message, event_type)
        ) or True
        app.show_tray_notification = lambda title, message: tray_calls.append((title, message))
        app.play_event_sound = lambda event_type: sound_calls.append(event_type)
        app.log = lambda _message: None

        with patch("main_gui.time.monotonic", side_effect=[10.0, 10.5]):
            first_result = app.notify_background_event(
                "failure",
                filename="sample.txt",
                error_summary="Docs API 오류 - quota exceeded",
            )
            second_result = app.notify_background_event(
                "failure",
                filename="sample.txt",
                error_summary="Docs API 오류 - quota exceeded",
            )

        self.assertTrue(first_result)
        self.assertFalse(second_result)
        self.assertEqual(len(popup_calls), 1)
        self.assertEqual(len(tray_calls), 1)
        self.assertEqual(sound_calls, ["failure"])


if __name__ == "__main__":
    unittest.main()
