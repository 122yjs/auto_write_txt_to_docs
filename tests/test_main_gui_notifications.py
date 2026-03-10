import unittest

from main_gui import extract_docs_update_line_count


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


if __name__ == "__main__":
    unittest.main()
