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
    def __init__(self):
        self.after_calls = []
        self.window_shown = False

    def after(self, delay, callback):
        self.after_calls.append((delay, callback))
        return len(self.after_calls)

    def winfo_exists(self):
        return True

    def deiconify(self):
        self.window_shown = True

    def lift(self):
        self.window_shown = True

    def focus_force(self):
        self.window_shown = True


class ImmediateThread:
    def __init__(self, target=None, args=None, kwargs=None, daemon=None):
        self.target = target
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.daemon = daemon

    def start(self):
        if self.target:
            self.target(*self.args, **self.kwargs)


class MainGuiTestBase(unittest.TestCase):
    def setUp(self):
        self.fake_ctk = types.SimpleNamespace(
            CTkFrame=FakeFrame,
            CTkButton=FakeButton,
            CTkEntry=FakeEntry,
            CTkSwitch=FakeButton,
            END="end",
            set_appearance_mode=Mock(),
        )

    def build_app(self):
        app = main_gui.MessengerDocsApp.__new__(main_gui.MessengerDocsApp)
        app.root = FakeRoot()
        app.settings_frame = FakeFrame()
        app.first_run = FakeVar(True)
        app.launch_on_windows_startup = FakeVar(False)
        app.check_updates_on_startup = FakeVar(True)
        app.watch_folder = FakeVar("")
        app.update_check_status = FakeVar("")
        app.docs_input = FakeVar("")
        app.docs_target_user_locked = FakeVar(False)
        app.docs_target_runtime_locked = FakeVar(False)
        app.docs_target_locked = FakeVar(False)
        app.readiness_var = FakeVar("")
        app.google_connection_status_var = FakeVar("")
        app.save_state_var = FakeVar("저장됨")
        app.current_activity_var = FakeVar("")
        app.last_success_var = FakeVar("")
        app.last_result_var = FakeVar("")
        app.advanced_settings_toggle_text = FakeVar("고급 설정 펼치기")
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
        app.log_threadsafe = Mock()
        app.update_status = Mock()
        app.update_windows_startup_ui_state = Mock()
        app.is_monitoring = False
        app.monitoring_thread = None
        app.latest_release_info = None
        app._update_check_in_progress = False
        app.google_auth_operation_in_progress = False
        app.last_result_summary = "아직 없음"
        app.last_success_timestamp = None
        app.readiness_state = {"ready": False, "message": "", "advanced_invalid": False}
        app.pending_activity_counts = {
            main_gui.ACTIVITY_RESULT_TAB: 0,
            main_gui.ACTIVITY_LOG_TAB: 0,
        }
        app.current_activity_tab = main_gui.ACTIVITY_RESULT_TAB

        app.watch_folder_entry = FakeEntry()
        app.watch_folder_browse_button = FakeButton("폴더 선택")
        app.watch_folder_open_button = FakeButton("열기")
        app.cache_folder_button = FakeButton("캐시 폴더 열기")
        app.autostart_switch = FakeButton("Windows 자동 실행")

        app.create_doc_button = FakeButton("새 문서 만들기")
        app.manual_doc_input_button = FakeButton("기존 문서 주소 입력")
        app.select_doc_button = FakeButton("문서 목록")
        app.reauth_button = FakeButton("Google 계정 다시 연결")
        app.reset_auth_button = FakeButton("인증 초기화")
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
        cache_row = FakeFrame()
        cache_row.children = [app.cache_folder_button]
        docs_action_row = FakeFrame()
        docs_action_row.children = [
            app.create_doc_button,
            app.manual_doc_input_button,
            app.select_doc_button,
            app.reauth_button,
            app.reset_auth_button,
        ]
        docs_input_row = FakeFrame()
        docs_input_row.children = [app.docs_input_entry]
        docs_lock_row = FakeFrame()
        docs_lock_row.children = [app.docs_target_status_label, app.docs_lock_button, other_button]
        app.settings_frame.children = [folder_row, cache_row, docs_action_row, docs_input_row, docs_lock_row]
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
        self.assertEqual(app.cache_folder_button.state, "normal")
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
        self.assertEqual(app.cache_folder_button.state, "normal")
        self.assertEqual(app.create_doc_button.state, "normal")
        self.assertEqual(app.docs_input_entry.state, "normal")
        self.assertEqual(app.other_button.state, "normal")
        app.update_windows_startup_ui_state.assert_called_once()


class MainGuiHelperFunctionTests(unittest.TestCase):
    def test_extract_google_id_from_url_accepts_valid_id_and_docs_url(self):
        self.assertEqual(
            main_gui.extract_google_id_from_url("https://docs.google.com/document/d/EXAMPLE_DOC_ID_12345/edit"),
            "EXAMPLE_DOC_ID_12345",
        )
        self.assertEqual(
            main_gui.extract_google_id_from_url("EXAMPLE_DOC_ID_12345"),
            "EXAMPLE_DOC_ID_12345",
        )

    def test_extract_google_id_from_url_rejects_invalid_input(self):
        self.assertIsNone(main_gui.extract_google_id_from_url(""))
        self.assertIsNone(main_gui.extract_google_id_from_url("https://example.com/document/d/EXAMPLE_DOC_ID_12345/edit"))
        self.assertIsNone(main_gui.extract_google_id_from_url("not-a-valid-doc-id"))

    def test_validate_regex_pattern_input_rejects_empty_or_invalid_pattern_when_enabled(self):
        self.assertEqual(
            main_gui.validate_regex_pattern_input(True, ""),
            "정규식 필터를 사용할 때는 패턴을 입력해주세요.",
        )
        self.assertIn(
            "정규식 패턴이 올바르지 않습니다",
            main_gui.validate_regex_pattern_input(True, "[unclosed"),
        )
        self.assertIsNone(main_gui.validate_regex_pattern_input(False, "[unclosed"))


class MainGuiDocsTargetTests(MainGuiTestBase):
    def test_apply_config_data_keeps_saved_document_editable(self):
        app = self.build_app()
        config_data = {
            "watch_folder": "C:/watch",
            "docs_input": "https://docs.google.com/document/d/EXAMPLE_DOC_ID_12345/edit",
            "appearance_mode": "Light",
        }

        with patch.object(main_gui, "ctk", self.fake_ctk):
            app.apply_config_data(config_data)

        self.assertFalse(app.docs_target_user_locked.get())
        self.assertFalse(app.docs_target_runtime_locked.get())
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
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_DOC_ID_12345/edit")
        app.parse_max_cache_size = Mock(return_value=10000)

        with patch.object(main_gui.os.path, "exists", return_value=True), patch.object(
            main_gui.os.path,
            "isdir",
            return_value=True,
        ):
            errors = app.validate_inputs()

        self.assertEqual(errors, [])

    def test_validate_inputs_rejects_invalid_document_url(self):
        app = self.build_app()
        app.watch_folder.set("C:/watch")
        app.docs_input.set("https://example.com/document/d/EXAMPLE_DOC_ID_12345/edit")
        app.parse_max_cache_size = Mock(return_value=10000)

        with patch.object(main_gui.os.path, "exists", return_value=True), patch.object(
            main_gui.os.path,
            "isdir",
            return_value=True,
        ):
            errors = app.validate_inputs()

        self.assertIn("유효한 Google Docs URL 또는 ID를 입력해주세요.", errors)

    def test_validate_inputs_rejects_invalid_regex_pattern(self):
        app = self.build_app()
        app.watch_folder.set("C:/watch")
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_DOC_ID_12345/edit")
        app.use_regex_filter.set(True)
        app.regex_pattern.set("[unclosed")
        app.parse_max_cache_size = Mock(return_value=10000)

        with patch.object(main_gui.os.path, "exists", return_value=True), patch.object(
            main_gui.os.path,
            "isdir",
            return_value=True,
        ):
            errors = app.validate_inputs()

        self.assertEqual(len(errors), 1)
        self.assertIn("정규식 패턴이 올바르지 않습니다", errors[0])

    def test_update_readiness_ui_disables_start_button_for_invalid_document_url(self):
        app = self.build_app()
        app.watch_folder.set("C:/watch")
        app.docs_input.set("https://example.com/document/d/EXAMPLE_DOC_ID_12345/edit")
        app.parse_max_cache_size = Mock(return_value=10000)

        with patch.object(main_gui, "ctk", self.fake_ctk), patch.object(
            main_gui.os.path,
            "exists",
            return_value=True,
        ), patch.object(main_gui.os.path, "isdir", return_value=True):
            app.update_readiness_ui()

        self.assertFalse(app.readiness_state["ready"])
        self.assertEqual(app.start_button.state, "disabled")
        self.assertIn("Google Docs URL", app.readiness_var.get())

    def test_lock_and_focus_existing_docs_input_restore_editable_state(self):
        app = self.build_app()
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_DOC_ID_12345/edit")

        with patch.object(main_gui, "ctk", self.fake_ctk):
            self.assertTrue(app.lock_docs_target(source_label="직접 입력"))
            self.assertTrue(app.docs_target_user_locked.get())
            self.assertFalse(app.docs_target_runtime_locked.get())
            self.assertTrue(app.docs_target_locked.get())
            self.assertEqual(app.docs_input_entry.state, "disabled")
            self.assertEqual(app.create_doc_button.state, "disabled")
            self.assertEqual(app.manual_doc_input_button.state, "disabled")
            self.assertEqual(app.select_doc_button.state, "disabled")

            app.focus_existing_docs_input()

        self.assertFalse(app.docs_target_user_locked.get())
        self.assertFalse(app.docs_target_runtime_locked.get())
        self.assertFalse(app.docs_target_locked.get())
        self.assertEqual(app.docs_input_entry.state, "normal")
        self.assertEqual(app.create_doc_button.state, "normal")
        self.assertEqual(app.manual_doc_input_button.state, "normal")
        self.assertEqual(app.select_doc_button.state, "normal")
        self.assertTrue(app.docs_input_entry.focused)
        self.assertEqual(app.docs_input_entry.cursor_position, "end")
        app.log.assert_any_call("대상 문서 경로 고정됨: 직접 입력")
        app.log.assert_any_call("기존 Google Docs 주소/ID 직접 입력 모드.")

    def test_lock_docs_target_rejects_invalid_document_input(self):
        app = self.build_app()
        app.docs_input.set("https://example.com/document/d/EXAMPLE_DOC_ID_12345/edit")

        with patch.object(main_gui.messagebox, "showwarning") as show_warning:
            locked = app.lock_docs_target(source_label="직접 입력")

        self.assertFalse(locked)
        self.assertFalse(app.docs_target_locked.get())
        show_warning.assert_called_once()

    def test_on_monitoring_stopped_unlocks_runtime_document_controls(self):
        app = self.build_app()
        app.watch_folder.set("C:/watch")
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_DOC_ID_12345/edit")
        app.docs_target_runtime_locked.set(True)
        app.sync_docs_target_lock_state()
        app.is_monitoring = True
        app.monitoring_thread = object()

        with patch.object(main_gui, "ctk", self.fake_ctk), patch.object(
            main_gui.os.path,
            "exists",
            return_value=True,
        ), patch.object(main_gui.os.path, "isdir", return_value=True):
            app.refresh_docs_target_ui()
            app.on_monitoring_stopped()

        self.assertFalse(app.docs_target_user_locked.get())
        self.assertFalse(app.docs_target_runtime_locked.get())
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
        app.log.assert_any_call("감시 중 자동 잠금이 해제되었습니다.")
        app.log.assert_any_call("감시 중지됨.")

    def test_on_monitoring_stopped_keeps_manual_lock_after_runtime_unlock(self):
        app = self.build_app()
        app.watch_folder.set("C:/watch")
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_DOC_ID_12345/edit")
        app.docs_target_user_locked.set(True)
        app.docs_target_runtime_locked.set(True)
        app.sync_docs_target_lock_state()
        app.is_monitoring = True
        app.monitoring_thread = object()

        with patch.object(main_gui, "ctk", self.fake_ctk), patch.object(
            main_gui.os.path,
            "exists",
            return_value=True,
        ), patch.object(main_gui.os.path, "isdir", return_value=True):
            app.refresh_docs_target_ui()
            app.on_monitoring_stopped()

        self.assertTrue(app.docs_target_user_locked.get())
        self.assertFalse(app.docs_target_runtime_locked.get())
        self.assertTrue(app.docs_target_locked.get())
        self.assertEqual(app.docs_input_entry.state, "disabled")
        self.assertEqual(app.create_doc_button.state, "disabled")
        self.assertEqual(app.manual_doc_input_button.state, "disabled")
        self.assertEqual(app.select_doc_button.state, "disabled")
        app.log.assert_any_call("감시 중 자동 잠금이 해제되었고 수동 고정은 유지됩니다.")

    def test_update_readiness_ui_disables_start_button_until_required_inputs_exist(self):
        app = self.build_app()

        with patch.object(main_gui, "ctk", self.fake_ctk):
            app.update_readiness_ui()

        self.assertEqual(app.start_button.state, "disabled")
        self.assertIn("감시 폴더", app.readiness_var.get())

    def test_register_activity_event_auto_switches_to_log_tab_for_errors(self):
        app = self.build_app()
        app.activity_tabview = Mock()

        app.register_activity_event(main_gui.ACTIVITY_LOG_TAB, auto_switch=True)

        self.assertEqual(app.current_activity_tab, main_gui.ACTIVITY_LOG_TAB)
        self.assertEqual(app.pending_activity_counts[main_gui.ACTIVITY_LOG_TAB], 0)

    def test_start_monitoring_requests_google_services_before_background_run(self):
        app = self.build_app()
        app.watch_folder.set("C:/watch")
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_DOC_ID_12345/edit")
        app.settings_changed = False
        app.parse_max_cache_size = Mock(return_value=10000)
        app.begin_google_service_request = Mock()

        with patch.object(main_gui, "ctk", self.fake_ctk), patch.object(main_gui.os.path, "exists", return_value=True), patch.object(
            main_gui.os.path,
            "isdir",
            return_value=True,
        ):
            app.start_monitoring()

        app.begin_google_service_request.assert_called_once()
        call_kwargs = app.begin_google_service_request.call_args.kwargs
        self.assertEqual(call_kwargs["purpose"], "monitoring")
        self.assertFalse(call_kwargs["require_drive"])

    def test_start_monitoring_with_services_auto_locks_document_before_background_run(self):
        app = self.build_app()
        app.watch_folder.set("C:/watch")
        app.docs_input.set("https://docs.google.com/document/d/EXAMPLE_DOC_ID_12345/edit")
        app.settings_changed = False
        app.stop_event = Mock()
        app.parse_max_cache_size = Mock(return_value=10000)
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
            app._start_monitoring_with_services({"docs": object()})

        self.assertFalse(app.docs_target_user_locked.get())
        self.assertTrue(app.docs_target_runtime_locked.get())
        self.assertTrue(app.docs_target_locked.get())
        self.assertEqual(app.docs_input_entry.state, "disabled")
        self.assertEqual(app.create_doc_button.state, "disabled")
        self.assertEqual(app.manual_doc_input_button.state, "disabled")
        self.assertEqual(app.select_doc_button.state, "disabled")
        self.assertEqual(app.start_button.state, "disabled")
        self.assertEqual(app.stop_button.state, "normal")
        app.stop_event.clear.assert_called_once()
        app.disable_settings_widgets.assert_called_once()
        fake_thread.start.assert_called_once()
        app.log.assert_any_call("감시 시작을 위해 대상 문서를 자동으로 확정했습니다.")

    def test_handle_google_auth_action_required_requests_foreground_reauth_on_confirm(self):
        app = self.build_app()
        app._start_google_service_worker = Mock()
        auth_error = main_gui.GoogleAuthActionRequired(
            "missing_token",
            "Google 계정 연결이 필요합니다.",
            quarantined_token_path="C:/cache/token.invalid.json",
        )

        with patch.object(main_gui.messagebox, "askyesno", return_value=True):
            app._handle_google_auth_action_required("monitoring", False, Mock(), auth_error)

        self.assertEqual(app.google_connection_status_var.get(), "브라우저에서 승인 대기 중")
        self.assertTrue(app.root.window_shown)
        app._start_google_service_worker.assert_called_once()
        worker_kwargs = app._start_google_service_worker.call_args.kwargs
        self.assertTrue(worker_kwargs["interactive"])
        self.assertEqual(worker_kwargs["purpose"], "monitoring")

    def test_begin_google_service_request_prompts_reauth_without_opening_browser_automatically(self):
        app = self.build_app()
        on_success = Mock()
        auth_error = main_gui.GoogleAuthActionRequired("missing_token", "다시 인증이 필요합니다.")

        def fake_get_google_services(*_args, **_kwargs):
            raise auth_error

        with patch.object(main_gui, "get_google_services", side_effect=fake_get_google_services), \
             patch.object(main_gui.threading, "Thread", ImmediateThread), \
             patch.object(main_gui.messagebox, "askyesno", return_value=False), \
             patch.object(main_gui, "run_interactive_auth", Mock()) as run_interactive_auth_mock, \
             patch.object(main_gui, "ctk", self.fake_ctk):
            app.begin_google_service_request("monitoring", False, on_success)
            for _delay, callback in list(app.root.after_calls):
                callback()

        self.assertEqual(app.google_connection_status_var.get(), "재인증 필요")
        self.assertFalse(app.google_auth_operation_in_progress)
        run_interactive_auth_mock.assert_not_called()
        on_success.assert_not_called()

    def test_prompt_google_reauthentication_forces_interactive_browser_flow(self):
        app = self.build_app()
        app.begin_google_service_request_with_options = Mock()

        with patch.object(main_gui, "run_interactive_auth", Mock()):
            app.prompt_google_reauthentication()

        app.begin_google_service_request_with_options.assert_called_once_with(
            purpose="manual_reauth",
            require_drive=False,
            on_success=app._finish_manual_google_reauthentication,
            force_interactive=True,
            quarantine_before_interactive=True,
        )

    def test_begin_google_service_request_with_force_interactive_quarantines_token_and_starts_browser_flow(self):
        app = self.build_app()
        app._start_google_service_worker = Mock()
        on_success = Mock()

        with patch.object(main_gui, "quarantine_token_file", return_value="C:/cache/token.invalid.json"):
            app.begin_google_service_request_with_options(
                purpose="manual_reauth",
                require_drive=False,
                on_success=on_success,
                force_interactive=True,
                quarantine_before_interactive=True,
            )

        self.assertTrue(app.google_auth_operation_in_progress)
        self.assertEqual(app.google_connection_status_var.get(), "브라우저에서 승인 대기 중")
        app._start_google_service_worker.assert_called_once_with(
            purpose="manual_reauth",
            require_drive=False,
            on_success=on_success,
            interactive=True,
        )
        app.log.assert_any_call("수동 재연결을 위해 기존 토큰을 격리했습니다: C:/cache/token.invalid.json")

    def test_start_google_service_worker_runs_interactive_auth_before_service_check(self):
        app = self.build_app()
        call_order = []

        def fake_run_interactive_auth(*_args, **_kwargs):
            call_order.append("interactive")

        def fake_get_google_services(*_args, **_kwargs):
            call_order.append("services")
            return {"docs": object()}

        with patch.object(main_gui, "run_interactive_auth", side_effect=fake_run_interactive_auth), patch.object(
            main_gui,
            "get_google_services",
            side_effect=fake_get_google_services,
        ), patch.object(main_gui.threading, "Thread", ImmediateThread):
            app._start_google_service_worker(
                purpose="manual_reauth",
                require_drive=False,
                on_success=Mock(),
                interactive=True,
            )
            for _delay, callback in list(app.root.after_calls):
                callback()

        self.assertEqual(call_order, ["interactive", "services"])

    def test_apply_filter_settings_snapshot_keeps_original_state_until_apply(self):
        app = self.build_app()
        original_snapshot = app.build_filter_settings_snapshot()
        edited_snapshot = {
            "file_extensions": ".txt,.log",
            "use_regex_filter": True,
            "regex_pattern": "^log_\\d+\\.txt$",
        }

        self.assertEqual(app.file_extensions.get(), original_snapshot["file_extensions"])
        self.assertEqual(app.use_regex_filter.get(), original_snapshot["use_regex_filter"])
        self.assertEqual(app.regex_pattern.get(), original_snapshot["regex_pattern"])

        with patch.object(main_gui, "ctk", self.fake_ctk), patch.object(
            main_gui.os.path,
            "exists",
            return_value=False,
        ):
            app.apply_filter_settings_snapshot(edited_snapshot)

        self.assertEqual(app.file_extensions.get(), ".txt,.log")
        self.assertTrue(app.use_regex_filter.get())
        self.assertEqual(app.regex_pattern.get(), "^log_\\d+\\.txt$")
        self.assertTrue(app.settings_changed)

    def test_apply_filter_settings_snapshot_if_valid_rejects_invalid_regex_without_mutation(self):
        app = self.build_app()
        filter_error_var = FakeVar("")
        test_result_var = FakeVar("")
        close_callback = Mock()

        applied = app.apply_filter_settings_snapshot_if_valid(
            {
                "file_extensions": ".txt",
                "use_regex_filter": True,
                "regex_pattern": "[unclosed",
            },
            filter_error_var=filter_error_var,
            test_result_var=test_result_var,
            close_callback=close_callback,
        )

        self.assertFalse(applied)
        self.assertEqual(app.file_extensions.get(), ".txt")
        self.assertFalse(app.use_regex_filter.get())
        self.assertEqual(app.regex_pattern.get(), "")
        self.assertIn("정규식 패턴이 올바르지 않습니다", filter_error_var.get())
        self.assertEqual(test_result_var.get(), "정규식 패턴 오류")
        close_callback.assert_not_called()

    def test_apply_filter_settings_snapshot_if_valid_applies_snapshot_and_closes(self):
        app = self.build_app()
        filter_error_var = FakeVar("기존 오류")
        test_result_var = FakeVar("")
        close_callback = Mock()

        applied = app.apply_filter_settings_snapshot_if_valid(
            {
                "file_extensions": " .txt,.log ",
                "use_regex_filter": True,
                "regex_pattern": " ^log_\\d+\\.txt$ ",
            },
            filter_error_var=filter_error_var,
            test_result_var=test_result_var,
            close_callback=close_callback,
        )

        self.assertTrue(applied)
        self.assertEqual(app.file_extensions.get(), ".txt,.log")
        self.assertTrue(app.use_regex_filter.get())
        self.assertEqual(app.regex_pattern.get(), "^log_\\d+\\.txt$")
        self.assertEqual(filter_error_var.get(), "")
        close_callback.assert_called_once()

    def test_evaluate_filter_settings_snapshot_reports_matching_result(self):
        app = self.build_app()

        matched = app.evaluate_filter_settings_snapshot(
            {
                "file_extensions": ".txt,.log",
                "use_regex_filter": True,
                "regex_pattern": "^log_\\d+\\.txt$",
            },
            "log_123.txt",
        )
        not_matched = app.evaluate_filter_settings_snapshot(
            {
                "file_extensions": ".txt,.log",
                "use_regex_filter": True,
                "regex_pattern": "^log_\\d+\\.txt$",
            },
            "note.md",
        )

        self.assertTrue(matched["matches"])
        self.assertEqual(matched["message"], "매칭됨: 이 파일은 감시 대상입니다")
        self.assertFalse(not_matched["matches"])
        self.assertEqual(not_matched["message"], "매칭 안됨: 이 파일은 무시됩니다")

    def test_save_config_blocks_invalid_regex_pattern(self):
        app = self.build_app()
        app.use_regex_filter.set(True)
        app.regex_pattern.set("[unclosed")

        with patch.object(main_gui, "save_app_config") as save_config, patch.object(
            main_gui.messagebox,
            "showerror",
        ) as show_error:
            app.save_config()

        save_config.assert_not_called()
        show_error.assert_called_once()


class MainGuiAutostartTests(MainGuiTestBase):
    def test_apply_update_check_result_updates_status_for_latest_version(self):
        app = self.build_app()

        app.apply_update_check_result(
            {
                "current_version": "0.6.0",
                "latest_version": "0.6.0",
                "update_available": False,
                "release_url": "https://example.com/releases/v0.6.0",
            }
        )

        self.assertEqual(app.update_check_status.get(), "현재 최신 버전(v0.6.0)을 사용 중입니다.")

    def test_apply_config_data_reflects_disabled_startup_update_check_hint(self):
        app = self.build_app()

        with patch.object(main_gui, "ctk", self.fake_ctk):
            app.apply_config_data({"check_updates_on_startup": False})

        self.assertEqual(
            app.update_check_status.get(),
            "시작 시 최신 버전 확인이 꺼져 있습니다. '지금 확인'으로 수동 검사할 수 있습니다.",
        )

    def test_apply_update_check_result_opens_release_page_when_user_confirms(self):
        app = self.build_app()

        with patch.object(main_gui.messagebox, "askyesno", return_value=True), patch.object(
            main_gui.webbrowser,
            "open",
        ) as open_browser:
            app.apply_update_check_result(
                {
                    "current_version": "0.6.0",
                    "latest_version": "0.6.1",
                    "update_available": True,
                    "release_url": "https://example.com/releases/v0.6.1",
                },
                user_initiated=True,
            )

        open_browser.assert_called_once_with("https://example.com/releases/v0.6.1")
        self.assertIn("새 버전 v0.6.1 사용 가능", app.update_check_status.get())

    def test_apply_update_check_error_offers_release_page_when_user_requests_manual_check(self):
        app = self.build_app()

        with patch.object(main_gui.messagebox, "askyesno", return_value=True), patch.object(
            main_gui.webbrowser,
            "open",
        ) as open_browser:
            app.apply_update_check_error("네트워크 오류", user_initiated=True)

        open_browser.assert_called_once()
        self.assertEqual(app.update_check_status.get(), "최신 버전 확인 실패: 네트워크 오류")

    def test_on_windows_startup_setting_changed_applies_immediately_and_persists_preference(self):
        app = self.build_app()
        app.settings_changed = False
        app.launch_on_windows_startup.set(True)

        with patch.object(main_gui, "supports_windows_startup", return_value=True), patch.object(
            main_gui,
            "is_windows_startup_enabled",
            return_value=False,
        ), patch.object(main_gui, "set_windows_startup_enabled") as set_enabled, patch.object(
            main_gui,
            "load_app_config",
            return_value=({"watch_folder": "C:/saved", "launch_on_windows_startup": False}, "config.json", False, True),
        ), patch.object(main_gui, "save_app_config") as save_config, patch.object(
            main_gui.messagebox,
            "showwarning",
        ) as show_warning:
            app.on_windows_startup_setting_changed()

        set_enabled.assert_called_once_with(True)
        save_config.assert_called_once()
        persisted_config = save_config.call_args.args[0]
        self.assertEqual(persisted_config["watch_folder"], "C:/saved")
        self.assertTrue(persisted_config["launch_on_windows_startup"])
        self.assertFalse(app.settings_changed)
        show_warning.assert_not_called()

    def test_on_windows_startup_setting_changed_rolls_back_ui_when_apply_fails(self):
        app = self.build_app()
        app.launch_on_windows_startup.set(True)

        with patch.object(main_gui, "supports_windows_startup", return_value=True), patch.object(
            main_gui,
            "is_windows_startup_enabled",
            return_value=False,
        ), patch.object(
            main_gui,
            "set_windows_startup_enabled",
            side_effect=RuntimeError("권한 부족"),
        ), patch.object(main_gui.messagebox, "showwarning") as show_warning:
            app.on_windows_startup_setting_changed()

        self.assertFalse(app.launch_on_windows_startup.get())
        show_warning.assert_called_once()

    def test_save_config_no_longer_syncs_windows_startup_setting(self):
        app = self.build_app()
        app.settings_changed = True
        app.get_current_config_data = Mock(
            return_value={
                "first_run": True,
                "launch_on_windows_startup": False,
                "check_updates_on_startup": True,
                "watch_folder": "",
                "docs_input": "",
                "show_help_on_startup": True,
                "show_success_notifications": True,
                "play_event_sounds": True,
                "file_extensions": ".txt",
                "use_regex_filter": False,
                "regex_pattern": "",
                "appearance_mode": "System",
                "max_cache_size": 10000,
            }
        )
        app.sync_windows_startup_setting = Mock(side_effect=AssertionError("호출되면 안 됩니다."))

        with patch.object(main_gui, "save_app_config") as save_config:
            app.save_config()

        save_config.assert_called_once()
        self.assertFalse(app.settings_changed)


if __name__ == "__main__":
    unittest.main()
