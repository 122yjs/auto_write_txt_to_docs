import unittest
from pathlib import Path


class MainGuiDocsActionsTests(unittest.TestCase):
    def setUp(self):
        self.source = Path("main_gui.py").read_text(encoding="utf-8")

    def test_main_gui_contains_doc_creation_and_selection_actions(self):
        self.assertIn("def create_new_google_doc", self.source)
        self.assertIn("def select_google_doc", self.source)
        self.assertIn('text="새 문서 만들기"', self.source)
        self.assertIn('text="기존 주소 입력"', self.source)
        self.assertIn('text="문서 목록"', self.source)
        self.assertIn("create_google_document", self.source)
        self.assertIn("list_accessible_google_documents", self.source)


if __name__ == "__main__":
    unittest.main()
