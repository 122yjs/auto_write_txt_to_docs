import unittest
from src.auto_write_txt_to_docs.batch_optimizer import BatchDeduplicationOptimizer


class BatchDeduplicationOptimizerTests(unittest.TestCase):
    def test_initial_interval_is_default(self):
        opt = BatchDeduplicationOptimizer()
        self.assertEqual(opt.get_next_interval(), 0.5)

    def test_increases_interval_when_high_duplicate_ratio(self):
        opt = BatchDeduplicationOptimizer(threshold=0.95)
        for _ in range(10):
            opt.record_result(100, 96)
        interval = opt.get_next_interval()
        self.assertEqual(interval, 1.0)

    def test_doubles_interval_repeatedly(self):
        opt = BatchDeduplicationOptimizer(threshold=0.95, max_interval=8.0)
        for _ in range(10):
            opt.record_result(100, 96)
        self.assertEqual(opt.get_next_interval(), 1.0)
        self.assertEqual(opt.get_next_interval(), 2.0)
        self.assertEqual(opt.get_next_interval(), 4.0)
        self.assertEqual(opt.get_next_interval(), 8.0)
        self.assertEqual(opt.get_next_interval(), 8.0)

    def test_decreases_interval_when_low_duplicate_ratio(self):
        opt = BatchDeduplicationOptimizer(threshold=0.95)
        for _ in range(10):
            opt.record_result(100, 96)
        opt.get_next_interval()  # 1.0
        opt.batch_results.clear()
        opt.record_result(100, 10)
        interval = opt.get_next_interval()
        self.assertEqual(interval, 0.5)

    def test_respects_max_interval(self):
        opt = BatchDeduplicationOptimizer(max_interval=2.0)
        for _ in range(10):
            opt.record_result(100, 96)
        opt.get_next_interval()  # 1.0
        opt.get_next_interval()  # 2.0
        self.assertEqual(opt.get_next_interval(), 2.0)


if __name__ == "__main__":
    unittest.main()
