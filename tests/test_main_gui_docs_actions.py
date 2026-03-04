import unittest
from pathlib import Path


class MainGuiDocsActionsTests(unittest.TestCase):
    def setUp(self):
        self.main_gui_source = Path("main_gui.py").read_text(encoding="utf-8")
        self.main_window_ui_source = Path("src/auto_write_txt_to_docs/main_window_ui.py").read_text(encoding="utf-8")

    def test_main_gui_contains_doc_creation_and_selection_actions(self):
        self.assertIn("def create_new_google_doc", self.main_gui_source)
        self.assertIn("def select_google_doc", self.main_gui_source)
        self.assertIn("def toggle_docs_target_lock", self.main_gui_source)
        self.assertIn("def lock_docs_target", self.main_gui_source)
        self.assertIn("def unlock_docs_target", self.main_gui_source)
        self.assertIn("create_google_document", self.main_gui_source)
        self.assertIn("list_accessible_google_documents", self.main_gui_source)
        self.assertIn("build_main_window_ui", self.main_gui_source)
        self.assertIn("docs_target_locked", self.main_gui_source)
        self.assertIn('text="새 문서 만들기"', self.main_window_ui_source)
        self.assertIn('text="기존 문서 주소 입력"', self.main_window_ui_source)
        self.assertIn('text="문서 목록"', self.main_window_ui_source)
        self.assertIn('text="문서 경로 확정"', self.main_window_ui_source)


if __name__ == "__main__":
    unittest.main()
