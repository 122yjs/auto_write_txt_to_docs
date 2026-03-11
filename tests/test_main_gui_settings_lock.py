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
        self.children = []
        self.focused = False
        self.cursor_position = None

    def configure(self, **kwargs):
        self.config.update(kwargs)

    def cget(self, option):
        return self.config.get(option)

    @property
    def state(self):
        return self.config.get("state")

    def winfo_children(self):
        return list(self.children)

    def winfo_exists(self):
        return True

    def focus_set(self):
        self.focused = True

    def icursor(self, position):
        self.cursor_position = position


class FakeFrame(FakeWidget):
    pass


class FakeButton(FakeWidget):
    pass


class FakeEntry(FakeWidget):
    pass


class FakeLabel(FakeWidget):
    pass


class FakeRoot:
    def winfo_exists(self):
        return True


class MainGuiTestBase(unittest.TestCase):
    def setUp(self):
        self.fake_ctk = types.SimpleNamespace(
            CTkFrame=FakeFrame,
            CTkButton=FakeButton,
            CTkEntry=FakeEntry,
            END="end",
            set_appearance_mode=Mock(),
        )

    def build_app(self):
        app = main_gui.MessengerDocsApp.__new__(main_gui.MessengerDocsApp)
        app.root = FakeRoot()
        app.settings_frame = FakeFrame()
        app.first_run = FakeVar(True)
        app.launch_on_windows_startup = FakeVar(False)
        app.watch_folder = FakeVar("")
        app.docs_input = FakeVar("")
        app.docs_target_locked = FakeVar(False)
        app.show_help_on_startup = FakeVar(True)
        app.show_success_notifications = FakeVar(True)
        app.play_event_sounds = FakeVar(True)
        app.file_extensions = FakeVar(".txt")
        app.use_regex_filter = FakeVar(False)
        app.regex_pattern = FakeVar("")
        app.appearance_mode = FakeVar("System")
        app.max_cache_size = FakeVar("10000")
        app.docs_target_status_var = FakeVar("")
        app.log = Mock()
        app.update_status = Mock()
        app.update_windows_startup_ui_state = Mock()
        app.is_monitoring = False
        app.monitoring_thread = None

        app.watch_folder_entry = FakeEntry()
        app.watch_folder_browse_button = FakeButton("폴더 선택")
        app.watch_folder_open_button = FakeButton("열기")

        app.create_doc_button = FakeButton("새 문서 만들기")
        app.manual_doc_input_button = FakeButton("기존 문서 주소 입력")
        app.select_doc_button = FakeButton("문서 목록")
        app.docs_input_entry = FakeEntry()
        app.docs_lock_button = FakeButton("문서 경로 확정")
        app.docs_target_status_label = FakeLabel()
        app.start_button = FakeButton("감시 시작")
        app.stop_button = FakeButton("감시 중지", state="disabled")
        other_button = FakeButton("다른 버튼")

        folder_row = FakeFrame()
        folder_row.children = [
            app.watch_folder_entry,
            app.watch_folder_browse_button,
            app.watch_folder_open_button,
        ]
        docs_action_row = FakeFrame()
        docs_action_row.children = [
            app.create_doc_button,
            app.manual_doc_input_button,
            app.select_doc_button,
        ]
        docs_input_row = FakeFrame()
        docs_input_row.children = [app.docs_input_entry]
        docs_lock_row = FakeFrame()
        docs_lock_row.children = [app.docs_target_status_label, app.docs_lock_button, other_button]
        app.settings_frame.children = [folder_row, docs_action_row, docs_input_row, docs_lock_row]
        app.other_button = other_button
        return app


class MainGuiSettingsLockTests(MainGuiTestBase):
    def test_disable_settings_widgets_keeps_watch_folder_open_button_enabled(self):
        app = self.build_app()

        with patch.object(main_gui, "ctk", self.fake_ctk):
            app.disable_settings_widgets()

        self.assertEqual(app.watch_folder_entry.state, "disabled")
        self.assertEqual(app.watch_folder_browse_button.state, "disabled")
        self.assertEqual(app.watch_folder_open_button.state, "normal")
        self.assertEqual(app.create_doc_button.state, "disabled")
        self.assertEqual(app.docs_input_entry.state, "disabled")
        self.assertEqual(app.other_button.state, "disabled")

    def test_enable_settings_widgets_restores_states_and_runs_followup_sync(self):
        app = self.build_app()

        with patch.object(main_gui, "ctk", self.fake_ctk):
            app.disable_settings_widgets()
            app.enable_settings_widgets()

        self.assertEqual(app.watch_folder_entry.state, "normal")
        self.assertEqual(app.watch_folder_browse_button.state, "normal")
        self.assertEqual(app.watch_folder_open_button.state, "normal")
        self.assertEqual(app.create_doc_button.state, "normal")
        self.assertEqual(app.docs_input_entry.state, "normal")
        self.assertEqual(app.other_button.state, "normal")
        app.update_windows_startup_ui_state.assert_called_once()


class MainGuiDocsTargetTests(MainGuiTestBase):
    def test_apply_config_data_keeps_saved_document_editable(self):
        app = self.build_app()
        config_data = {
            "watch_folder": "C:/watch",
            "docs_input": "https://docs.google.com/document/d/EXAMPLE_ID/edit",
            "appearance_mode": "Light",
        }

        with patch.object(main_gui, "ctk", self.fake_ctk):
            app.apply_config_data(config_data)

        self.assertFalse(app.docs_target_locked.get())
        self.assertEqual(app.docs_input_entry.state, "normal")
        self.assertEqual(app.create_doc_button.state, "normal")
        self.assertEqual(app.manual_doc_input_button.state, "normal")
        self.assertEqual(app.select_doc_button.state, "normal")
        self.assertEqual(
            app.docs_target_status_var.get(),
            "문서가 입력되어 있습니다. 감시 시작 시 이 문서를 자동으로 확정합니다.",
        )
        self.fake_ctk.set_appearance_mode.assert_called_once_with("Light")

    def test_validate_inputs_accepts_editable_document_without_manual_lock(self):
        app = self.build_app()
        app.watch_folder.set("C:/watch")
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_ID/edit")
        app.parse_max_cache_size = Mock(return_value=10000)

        with patch.object(main_gui.os.path, "exists", return_value=True), patch.object(
            main_gui.os.path,
            "isdir",
            return_value=True,
        ):
            errors = app.validate_inputs()

        self.assertEqual(errors, [])

    def test_lock_and_focus_existing_docs_input_restore_editable_state(self):
        app = self.build_app()
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_ID/edit")

        with patch.object(main_gui, "ctk", self.fake_ctk):
            self.assertTrue(app.lock_docs_target(source_label="직접 입력"))
            self.assertTrue(app.docs_target_locked.get())
            self.assertEqual(app.docs_input_entry.state, "disabled")
            self.assertEqual(app.create_doc_button.state, "disabled")
            self.assertEqual(app.manual_doc_input_button.state, "disabled")
            self.assertEqual(app.select_doc_button.state, "disabled")

            app.focus_existing_docs_input()

        self.assertFalse(app.docs_target_locked.get())
        self.assertEqual(app.docs_input_entry.state, "normal")
        self.assertEqual(app.create_doc_button.state, "normal")
        self.assertEqual(app.manual_doc_input_button.state, "normal")
        self.assertEqual(app.select_doc_button.state, "normal")
        self.assertTrue(app.docs_input_entry.focused)
        self.assertEqual(app.docs_input_entry.cursor_position, "end")
        app.log.assert_any_call("대상 문서 경로 고정됨: 직접 입력")
        app.log.assert_any_call("기존 Google Docs 주소/ID 직접 입력 모드.")

    def test_on_monitoring_stopped_unlocks_document_controls(self):
        app = self.build_app()
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_ID/edit")
        app.docs_target_locked.set(True)
        app.is_monitoring = True
        app.monitoring_thread = object()

        with patch.object(main_gui, "ctk", self.fake_ctk):
            app.refresh_docs_target_ui()
            app.on_monitoring_stopped()

        self.assertFalse(app.docs_target_locked.get())
        self.assertFalse(app.is_monitoring)
        self.assertIsNone(app.monitoring_thread)
        self.assertEqual(app.start_button.state, "normal")
        self.assertEqual(app.stop_button.state, "disabled")
        self.assertEqual(app.docs_input_entry.state, "normal")
        self.assertEqual(app.create_doc_button.state, "normal")
        self.assertEqual(app.manual_doc_input_button.state, "normal")
        self.assertEqual(app.select_doc_button.state, "normal")
        self.assertEqual(app.watch_folder_open_button.state, "normal")
        app.update_status.assert_called_once_with("준비")
        app.update_windows_startup_ui_state.assert_called_once()
        app.log.assert_any_call("감시 중지로 대상 문서 고정이 해제되었습니다.")
        app.log.assert_any_call("감시 중지됨.")

    def test_start_monitoring_auto_locks_document_before_background_run(self):
        app = self.build_app()
        app.watch_folder.set("C:/watch")
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_ID/edit")
        app.settings_changed = False
        app.stop_event = Mock()
        app.parse_max_cache_size = Mock(return_value=10000)
        app.verify_google_services_before_monitoring = Mock(return_value={"docs": object()})
        app.log_threadsafe = Mock()
        app.extracted_result_threadsafe = Mock()
        app.disable_settings_widgets = Mock()
        fake_thread = Mock()

        with patch.object(main_gui, "ctk", self.fake_ctk), patch.object(
            main_gui,
            "run_monitoring",
            Mock(),
        ), patch.object(main_gui.os.path, "exists", return_value=True), patch.object(
            main_gui.os.path,
            "isdir",
            return_value=True,
        ), patch.object(main_gui.threading, "Thread", return_value=fake_thread):
            app.start_monitoring()

        self.assertTrue(app.docs_target_locked.get())
        self.assertEqual(app.docs_input_entry.state, "disabled")
        self.assertEqual(app.create_doc_button.state, "disabled")
        self.assertEqual(app.manual_doc_input_button.state, "disabled")
        self.assertEqual(app.select_doc_button.state, "disabled")
        self.assertEqual(app.start_button.state, "disabled")
        self.assertEqual(app.stop_button.state, "normal")
        app.verify_google_services_before_monitoring.assert_called_once()
        app.stop_event.clear.assert_called_once()
        app.disable_settings_widgets.assert_called_once()
        fake_thread.start.assert_called_once()
        app.log.assert_any_call("감시 시작을 위해 대상 문서를 자동으로 확정했습니다.")


if __name__ == "__main__":
    unittest.main()
