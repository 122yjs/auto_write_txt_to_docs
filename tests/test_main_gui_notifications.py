import unittest

from main_gui import extract_docs_update_line_count, extract_filename_from_log_message


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


if __name__ == "__main__":
    unittest.main()
