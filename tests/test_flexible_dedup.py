import unittest
from src.auto_write_txt_to_docs.block_parser import StructuredBlock
from src.auto_write_txt_to_docs.flexible_dedup import FlexibleDeduplicationStrategy, get_flexible_strategy
from collections import OrderedDict


class FlexibleDeduplicationTests(unittest.TestCase):
    def test_same_block_same_fingerprint(self):
        strategy = FlexibleDeduplicationStrategy()
        block = StructuredBlock(fields={"sender": "이슬아", "body": "감사합니다"})
        fp1 = strategy.compute_fingerprint(block)
        fp2 = strategy.compute_fingerprint(block)
        self.assertEqual(fp1, fp2)

    def test_ignore_field_changes_fingerprint(self):
        strategy = FlexibleDeduplicationStrategy(ignore_fields=["time"])
        block1 = StructuredBlock(fields={"sender": "이슬아", "time": "10:00", "body": "감사합니다"})
        block2 = StructuredBlock(fields={"sender": "이슬아", "time": "11:00", "body": "감사합니다"})
        
        fp1 = strategy.compute_fingerprint(block1)
        fp2 = strategy.compute_fingerprint(block2)
        self.assertEqual(fp1, fp2)

    def test_different_content_different_fingerprint(self):
        strategy = FlexibleDeduplicationStrategy(ignore_fields=["time"])
        block1 = StructuredBlock(fields={"sender": "이슬아", "body": "감사합니다"})
        block2 = StructuredBlock(fields={"sender": "김민정", "body": "확인했습니다"})
        
        fp1 = strategy.compute_fingerprint(block1)
        fp2 = strategy.compute_fingerprint(block2)
        self.assertNotEqual(fp1, fp2)

    def test_fingerprint_uses_raw_text_when_fields_are_empty(self):
        strategy = FlexibleDeduplicationStrategy()
        block1 = StructuredBlock(raw_text="송신:이슬아\n내용:감사합니다")
        block2 = StructuredBlock(raw_text="송신:김민정\n내용:확인했습니다")

        fp1 = strategy.compute_fingerprint(block1)
        fp2 = strategy.compute_fingerprint(block2)

        self.assertNotEqual(fp1, fp2)

    def test_get_new_blocks_filters_duplicates(self):
        strategy = FlexibleDeduplicationStrategy()
        cache = OrderedDict()
        block1 = StructuredBlock(fields={"sender": "이슬아", "body": "감사합니다"})
        block2 = StructuredBlock(fields={"sender": "이슬아", "body": "감사합니다"})
        
        new_blocks = strategy.get_new_blocks([block1], cache)
        self.assertEqual(len(new_blocks), 1)
        strategy.remember_blocks([block1], cache)
        
        new_blocks = strategy.get_new_blocks([block2], cache)
        self.assertEqual(len(new_blocks), 0)

    def test_context_changes_fingerprint(self):
        strategy = FlexibleDeduplicationStrategy()
        block = StructuredBlock(fields={"sender": "이슬아", "body": "감사합니다"})
        
        fp1 = strategy.compute_fingerprint(block, context="받은쪽지함")
        fp2 = strategy.compute_fingerprint(block, context="병은쪽지함")
        self.assertNotEqual(fp1, fp2)

    def test_get_flexible_strategy_disabled(self):
        config = {"flexible_dedup": {"enabled": False}}
        strategy = get_flexible_strategy(config)
        self.assertIsNone(strategy)

    def test_get_flexible_strategy_enabled(self):
        config = {"flexible_dedup": {"enabled": True, "ignore_fields": ["time"]}}
        strategy = get_flexible_strategy(config)
        self.assertIsNotNone(strategy)
        self.assertIn("time", strategy.ignore_fields)


if __name__ == "__main__":
    unittest.main()
