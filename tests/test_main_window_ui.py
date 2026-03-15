import unittest
from pathlib import Path


class MainWindowUiTests(unittest.TestCase):
    def setUp(self):
        self.source = Path("src/auto_write_txt_to_docs/main_window_ui.py").read_text(encoding="utf-8")

    def test_main_window_ui_exposes_builder_function(self):
        self.assertIn("def build_main_window_ui", self.source)
        self.assertIn("def _build_status_panel", self.source)
        self.assertIn("def _build_settings_panel", self.source)
        self.assertIn("def _build_autostart_row", self.source)
        self.assertIn("def _build_control_panel", self.source)
        self.assertIn("def _build_activity_panel", self.source)
        self.assertIn("def _build_cta_footer", self.source)
        self.assertIn("def _attach_tooltip", self.source)

    def test_main_window_ui_contains_tabbed_activity_and_footer_cta(self):
        self.assertIn("CTkTabview(", self.source)
        self.assertIn('activity_tabview.add("최근 추출 결과")', self.source)
        self.assertIn('activity_tabview.add("작업 로그")', self.source)
        self.assertIn('activity_tabview.set("최근 추출 결과")', self.source)
        self.assertIn('text="로그 팝업"', self.source)
        self.assertIn('text="감시 시작"', self.source)
        self.assertIn('text="감시 중지"', self.source)
        self.assertIn("height=60", self.source)
        self.assertIn("stop_cta_button.grid_remove()", self.source)
        self.assertIn('"activity_tabview": activity_tabview', self.source)
        self.assertIn('"start_button": start_cta_button', self.source)
        self.assertIn('"stop_button": stop_cta_button', self.source)

    def test_main_window_ui_contains_basic_and_advanced_settings(self):
        self.assertIn('text="작업 설정"', self.source)
        self.assertIn('text="고급 설정"', self.source)
        self.assertIn('text="Windows 자동 실행"', self.source)
        self.assertIn('textvariable=state_vars["advanced_settings_toggle_text"]', self.source)
        self.assertIn("advanced_settings_frame.pack_forget()", self.source)
        self.assertIn('text="새 문서 만들기"', self.source)
        self.assertIn('text="기존 문서 주소 입력"', self.source)
        self.assertIn('text="문서 목록"', self.source)
        self.assertIn('text="문서 경로 확정"', self.source)
        self.assertIn('text="라인 캐시 크기"', self.source)
        self.assertIn('text="캐시 폴더 열기"', self.source)
        self.assertIn('text="작업 결과 알림 표시"', self.source)
        self.assertIn('text="작업 결과 효과음 재생"', self.source)
        self.assertIn('text="Windows 로그인 시 자동으로 실행"', self.source)
        self.assertIn('text="필터, 캐시, 알림"', self.source)

    def test_main_window_ui_contains_new_status_and_readiness_bindings(self):
        self.assertIn('textvariable=state_vars["save_state_var"]', self.source)
        self.assertIn('textvariable=state_vars["current_activity_var"]', self.source)
        self.assertIn('"last_success_var"', self.source)
        self.assertIn('"last_result_var"', self.source)
        self.assertIn('textvariable=state_vars["readiness_var"]', self.source)
        self.assertIn('textvariable=state_vars["google_connection_status_var"]', self.source)
        self.assertIn('main_frame.pack(padx=14, pady=14, fill="both", expand=True)', self.source)
        self.assertIn('main_scroll_frame.pack(fill="both", expand=True)', self.source)
        self.assertIn("result_cards_frame", self.source)
        self.assertIn('text="활동"', self.source)


if __name__ == "__main__":
    unittest.main()
