import unittest
from pathlib import Path


class MainWindowUiTests(unittest.TestCase):
    def setUp(self):
        self.source = Path("src/auto_write_txt_to_docs/main_window_ui.py").read_text(encoding="utf-8")

    def test_main_window_ui_exposes_builder_function(self):
        self.assertIn("def build_main_window_ui", self.source)
        self.assertIn("_build_status_panel", self.source)
        self.assertIn("_build_settings_panel", self.source)
        self.assertIn("_build_control_panel", self.source)
        self.assertIn("_build_result_panel", self.source)
        self.assertIn("_build_log_panel", self.source)

    def test_main_window_ui_keeps_font_helper_and_workspace_copy(self):
        self.assertIn("def _font", self.source)
        self.assertIn("if family:", self.source)
        self.assertIn("Messenger Docs Workspace", self.source)
        self.assertIn("작업 설정", self.source)
        self.assertIn("watch_folder_drop_hint", self.source)
        self.assertIn("라인 캐시 크기", self.source)
        self.assertIn("작업 성공 알림", self.source)
        self.assertIn("최근 추출 결과", self.source)
        self.assertIn("작업 로그", self.source)
        self.assertIn("로그 팝업", self.source)
        self.assertIn("placeholder_text=", self.source)
        self.assertIn("docs_target_status_var", self.source)
        self.assertIn("validate_positive_integer_input", self.source)

    def test_main_window_ui_keeps_docs_actions_and_primary_controls(self):
        self.assertIn('text="새 문서 만들기"', self.source)
        self.assertIn('text="기존 문서 주소 입력"', self.source)
        self.assertIn('text="문서 목록"', self.source)
        self.assertIn('text="문서 경로 확정"', self.source)
        self.assertIn('Google Docs 기록 성공 시 트레이 알림 표시', self.source)
        self.assertIn('text="미리보기 지우기"', self.source)
        self.assertIn("기본 창이 좁으면 '로그 팝업' 버튼으로 별도 창에서 볼 수 있습니다.", self.source)
        self.assertIn('text="감시 시작"', self.source)
        self.assertIn('text="감시 중지"', self.source)
        self.assertIn('text="Docs 웹에서 열기"', self.source)
        self.assertIn("watch_folder_entry", self.source)
        self.assertIn('textvariable=state_vars["watch_folder_drop_hint"]', self.source)
        self.assertIn("문서 ID", self.source)


if __name__ == "__main__":
    unittest.main()
