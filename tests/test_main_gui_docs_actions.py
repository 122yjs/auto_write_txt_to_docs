import types
import unittest
from unittest.mock import Mock, patch

import main_gui


class FakeVar:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeWidget:
    def __init__(self, text=None, state="normal"):
        self.config = {"text": text, "state": state}
        self.focused = False
        self.cursor_position = None

    def configure(self, **kwargs):
        self.config.update(kwargs)

    @property
    def state(self):
        return self.config.get("state")

    def focus_set(self):
        self.focused = True

    def icursor(self, position):
        self.cursor_position = position


class FakeButton(FakeWidget):
    pass


class FakeEntry(FakeWidget):
    pass


class FakeLabel(FakeWidget):
    pass


class FakeRoot:
    def __init__(self):
        self.after_calls = []

    def after(self, delay, callback):
        self.after_calls.append((delay, callback))
        return len(self.after_calls)

    def winfo_exists(self):
        return True


class MainGuiDocsActionsTests(unittest.TestCase):
    def setUp(self):
        self.fake_ctk = types.SimpleNamespace(
            CTkFrame=FakeWidget,
            CTkButton=FakeButton,
            CTkEntry=FakeEntry,
            END="end",
        )

    def build_app(self):
        app = main_gui.MessengerDocsApp.__new__(main_gui.MessengerDocsApp)
        app.root = FakeRoot()
        app.docs_input = FakeVar("")
        app.docs_target_user_locked = FakeVar(False)
        app.docs_target_runtime_locked = FakeVar(False)
        app.docs_target_locked = FakeVar(False)
        app.docs_target_status_var = FakeVar("")
        app.docs_input_entry = FakeEntry()
        app.create_doc_button = FakeButton("새 문서 만들기")
        app.manual_doc_input_button = FakeButton("기존 문서 주소 입력")
        app.select_doc_button = FakeButton("문서 목록")
        app.docs_lock_button = FakeButton("문서 경로 확정")
        app.docs_target_status_label = FakeLabel()
        app.start_button = FakeButton("감시 시작")
        app.stop_button = FakeButton("감시 중지", state="disabled")
        app.log = Mock()
        app.is_monitoring = False
        return app

    def test_toggle_docs_target_lock_updates_manual_lock_state(self):
        app = self.build_app()
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_DOC_ID_12345/edit")

        with patch.object(main_gui, "ctk", self.fake_ctk):
            app.toggle_docs_target_lock()

        self.assertTrue(app.docs_target_user_locked.get())
        self.assertFalse(app.docs_target_runtime_locked.get())
        self.assertTrue(app.docs_target_locked.get())
        self.assertEqual(app.docs_input_entry.state, "disabled")

        with patch.object(main_gui, "ctk", self.fake_ctk):
            app.toggle_docs_target_lock()

        self.assertFalse(app.docs_target_user_locked.get())
        self.assertFalse(app.docs_target_runtime_locked.get())
        self.assertFalse(app.docs_target_locked.get())
        self.assertEqual(app.docs_input_entry.state, "normal")
        self.assertTrue(app.docs_input_entry.focused)
        self.assertEqual(app.docs_input_entry.cursor_position, "end")

    def test_open_docs_in_browser_opens_normalized_url_for_valid_id(self):
        app = self.build_app()
        app.docs_input.set("EXAMPLE_DOC_ID_12345")

        with patch.object(main_gui.webbrowser, "open") as open_browser, patch.object(
            main_gui.messagebox,
            "showwarning",
        ) as show_warning:
            app.open_docs_in_browser()

        open_browser.assert_called_once_with("https://docs.google.com/document/d/EXAMPLE_DOC_ID_12345/edit")
        show_warning.assert_not_called()

    def test_open_docs_in_browser_rejects_invalid_document_url(self):
        app = self.build_app()
        app.docs_input.set("https://example.com/document/d/EXAMPLE_DOC_ID_12345/edit")

        with patch.object(main_gui.webbrowser, "open") as open_browser, patch.object(
            main_gui.messagebox,
            "showwarning",
        ) as show_warning:
            app.open_docs_in_browser()

        open_browser.assert_not_called()
        show_warning.assert_called_once()

    def test_toggle_monitoring_from_tray_routes_to_start_and_stop(self):
        app = self.build_app()
        app.start_monitoring = Mock()
        app.stop_monitoring = Mock()

        app.toggle_monitoring_from_tray()
        self.assertEqual(len(app.root.after_calls), 1)
        _delay, callback = app.root.after_calls.pop()
        callback()
        app.start_monitoring.assert_called_once()

        app.is_monitoring = True
        app.toggle_monitoring_from_tray()
        self.assertEqual(len(app.root.after_calls), 1)
        _delay, callback = app.root.after_calls.pop()
        callback()
        app.stop_monitoring.assert_called_once()

    def test_open_docs_in_browser_from_tray_schedules_open_action(self):
        app = self.build_app()
        app.open_docs_in_browser = Mock()

        app.open_docs_in_browser_from_tray()

        self.assertEqual(len(app.root.after_calls), 1)
        _delay, callback = app.root.after_calls.pop()
        callback()
        app.open_docs_in_browser.assert_called_once()


if __name__ == "__main__":
    unittest.main()
