import unittest
from src.auto_write_txt_to_docs.block_parser import StructuredBlockParser, StructuredBlock


class StructuredBlockParserTests(unittest.TestCase):
    def test_parse_simple_block(self):
        parser = StructuredBlockParser(
            field_patterns={
                "sender": r"^송신:(.+)",
                "time": r"^시간:(.+)",
                "title": r"^제목:(.+)",
                "body": r"^내용:(.+)",
            }
        )
        content = (
            "송신:이슬아\n"
            "시간:2026-03-18 13:04:58:000\n"
            "제목:감사합니다\n"
            "내용:감사합니다\n"
        )
        blocks = parser.parse(content, source_file="test.txt")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].fields["sender"], "이슬아")
        self.assertEqual(blocks[0].fields["time"], "2026-03-18 13:04:58:000")
        self.assertEqual(blocks[0].fields["title"], "감사합니다")
        self.assertEqual(blocks[0].fields["body"], "감사합니다")
        self.assertEqual(blocks[0].source_file, "test.txt")

    def test_parse_removes_blank_lines_and_redundant_title_from_output_text(self):
        parser = StructuredBlockParser(
            field_patterns={
                "sender": r"^송신:(.+)",
                "time": r"^시간:(.+)",
                "title": r"^제목:(.+)",
                "body": r"^내용:(.+)",
            }
        )
        content = (
            "송신:이슬아\n"
            "\n"
            "시간:2026-03-18 13:04:58:000\n"
            "제목:감사합니다\n"
            "내용:감사합니다\n"
            "\n"
            "본문 둘째 줄\n"
            "   \n"
        )

        blocks = parser.parse(content, source_file="test.txt")

        self.assertEqual(
            blocks[0].raw_text,
            "송신:이슬아\n시간:2026-03-18 13:04:58:000\n내용:감사합니다\n본문 둘째 줄",
        )
        self.assertEqual(blocks[0].fields["title"], "감사합니다")
        self.assertEqual(blocks[0].fields["body"], "감사합니다")

    def test_parse_keeps_title_when_it_differs_from_body(self):
        parser = StructuredBlockParser()
        content = (
            "송신:이슬아\n"
            "제목:업무 공유\n"
            "내용:회의 자료 확인했습니다\n"
        )

        blocks = parser.parse(content)

        self.assertEqual(
            blocks[0].raw_text,
            "송신:이슬아\n제목:업무 공유\n내용:회의 자료 확인했습니다",
        )

    def test_parse_removes_embedded_reply_original_message(self):
        parser = StructuredBlockParser(
            field_patterns={
                "sender": r"^송신:(.+)",
                "time": r"^시간:(.+)",
                "title": r"^제목:(.+)",
                "body": r"^내용:(.+)",
            }
        )
        content = (
            "송신:김민정\n"
            "시간:2026-03-18 13:10:00:000\n"
            "제목:답장드립니다\n"
            "내용:확인했습니다. 그대로 진행하겠습니다.\n"
            "\n"
            "----- 원문 메시지 -----\n"
            "송신:이슬아\n"
            "시간:2026-03-18 13:04:58:000\n"
            "제목:요청사항\n"
            "내용:자료 확인 부탁드립니다.\n"
        )

        blocks = parser.parse(content)

        self.assertEqual(
            blocks[0].raw_text,
            "송신:김민정\n시간:2026-03-18 13:10:00:000\n제목:답장드립니다\n내용:확인했습니다. 그대로 진행하겠습니다.",
        )

    def test_parse_removes_embedded_original_even_without_marker(self):
        parser = StructuredBlockParser()
        content = (
            "송신:김민정\n"
            "시간:2026-03-18 13:10:00:000\n"
            "제목:답장드립니다\n"
            "내용:확인했습니다.\n"
            "송신:이슬아\n"
            "시간:2026-03-18 13:04:58:000\n"
            "제목:요청사항\n"
            "내용:자료 확인 부탁드립니다.\n"
        )

        blocks = parser.parse(content)

        self.assertEqual(
            blocks[0].raw_text,
            "송신:김민정\n시간:2026-03-18 13:10:00:000\n제목:답장드립니다\n내용:확인했습니다.",
        )

    def test_parse_multiple_blocks_with_separator(self):
        parser = StructuredBlockParser(
            block_separator="-" * 15,
            field_patterns={
                "sender": r"^송신:(.+)",
                "body": r"^내용:(.+)",
            }
        )
        content = (
            "송신:이슬아\n내용:감사합니다\n"
            "---------------\n"
            "송신:김민정\n내용:확인했습니다\n"
        )
        blocks = parser.parse(content)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].fields["sender"], "이슬아")
        self.assertEqual(blocks[1].fields["sender"], "김민정")

    def test_fingerprint_consistency(self):
        parser = StructuredBlockParser(
            field_patterns={"sender": r"^송신:(.+)", "body": r"^내용:(.+)"}
        )
        content = "송신:이슬아\n내용:감사합니다\n"
        blocks = parser.parse(content)
        fp1 = blocks[0].get_fingerprint()
        fp2 = blocks[0].get_fingerprint()
        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 64)

    def test_fingerprint_differs_by_context(self):
        parser = StructuredBlockParser(
            field_patterns={"sender": r"^송신:(.+)", "body": r"^내용:(.+)"}
        )
        content = "송신:이슬아\n내용:감사합니다\n"
        blocks = parser.parse(content)
        fp_received = blocks[0].get_fingerprint(context="받은쪽지함")
        fp_sent = blocks[0].get_fingerprint(context="병은쪽지함")
        self.assertNotEqual(fp_received, fp_sent)

    def test_fingerprint_uses_raw_text_when_no_fields_are_configured(self):
        parser = StructuredBlockParser(block_separator="-" * 15)
        blocks = parser.parse("송신:이슬아\n내용:감사합니다\n---------------\n송신:김민정\n내용:확인했습니다")

        self.assertNotEqual(blocks[0].get_fingerprint(), blocks[1].get_fingerprint())

    def test_validate_block_detects_missing_fields(self):
        parser = StructuredBlockParser(
            field_patterns={"sender": r"^송신:(.+)", "body": r"^내용:(.+)"}
        )
        block = StructuredBlock(fields={"sender": "이슬아"}, raw_text="송신:이슬아")
        valid, error = parser.validate_block(block)
        self.assertFalse(valid)
        self.assertIn("body", error)

    def test_validate_block_passes_complete_fields(self):
        parser = StructuredBlockParser(
            field_patterns={"sender": r"^송신:(.+)", "body": r"^내용:(.+)"}
        )
        block = StructuredBlock(
            fields={"sender": "이슬아", "body": "감사합니다"},
            raw_text="송신:이슬아\n내용:감사합니다",
        )
        valid, error = parser.validate_block(block)
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_parse_empty_content(self):
        parser = StructuredBlockParser(field_patterns={"sender": r"^송신:(.+)"})
        self.assertEqual(parser.parse(""), [])
        self.assertEqual(parser.parse("   "), [])


if __name__ == "__main__":
    unittest.main()
