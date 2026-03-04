import unittest

from src.auto_write_txt_to_docs import app_dialogs


class AppDialogsTests(unittest.TestCase):
    def test_build_help_guide_text_includes_current_docs_flow(self):
        help_text = app_dialogs.build_help_guide_text()

        self.assertIn("새 문서 만들기", help_text)
        self.assertIn("기존 주소 입력", help_text)
        self.assertIn("문서 목록", help_text)
        self.assertIn("Docs 웹에서 열기", help_text)

    def test_get_error_solution_text_returns_specific_google_auth_guidance(self):
        solution = app_dialogs.get_error_solution_text("Google 인증 오류")

        self.assertIn("developer_credentials.json", solution)
        self.assertIn("token.json", solution)
        self.assertIn("Google 계정", solution)

    def test_get_error_solution_text_returns_default_guidance_for_unknown_error(self):
        solution = app_dialogs.get_error_solution_text("알 수 없는 오류")

        self.assertIn("프로그램을 재시작", solution)
        self.assertIn("개발자에게 문의", solution)

    def test_get_credentials_wizard_guide_text_mentions_user_copy_flow(self):
        guide_text = app_dialogs.get_credentials_wizard_guide_text()

        self.assertIn("Google Cloud Console", guide_text)
        self.assertIn("JSON 파일 선택", guide_text)
        self.assertIn("developer_credentials.json", guide_text)


if __name__ == "__main__":
    unittest.main()
