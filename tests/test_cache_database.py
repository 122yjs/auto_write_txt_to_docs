import os
import tempfile
import unittest
from src.auto_write_txt_to_docs.cache_database import CacheDatabase


class CacheDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_db = os.path.join(tempfile.mkdtemp(), "cache.db")
        self.db = CacheDatabase(self.temp_db)

    def test_init_creates_tables(self):
        self.assertTrue(os.path.exists(self.temp_db))

    def test_is_duplicate_false_for_new_hash(self):
        self.assertFalse(self.db.is_duplicate("abc123"))

    def test_is_duplicate_true_after_add(self):
        self.db.add_line("abc123", "test line")
        self.assertTrue(self.db.is_duplicate("abc123"))

    def test_add_line_increments_count(self):
        self.db.add_line("abc123", "test line")
        self.db.add_line("abc123", "test line")
        stats = self.db.get_duplicate_stats(limit=1)
        self.assertEqual(stats[0][2], 2)

    def test_get_duplicate_stats_sorted(self):
        self.db.add_line("rare", "rare line")
        self.db.add_line("common", "common line")
        self.db.add_line("common", "common line")
        self.db.add_line("common", "common line")
        stats = self.db.get_duplicate_stats(limit=2)
        self.assertEqual(stats[0][0], "common")
        self.assertEqual(stats[0][2], 3)
        self.assertEqual(stats[1][0], "rare")
        self.assertEqual(stats[1][2], 1)

    def test_migrate_from_json_dict(self):
        cache_file = os.path.join(tempfile.mkdtemp(), "cache.json")
        with open(cache_file, "w", encoding="utf-8") as f:
            import json
            json.dump({"hash1": "line 1", "hash2": "line 2"}, f)
        
        self.db.migrate_from_json(cache_file)
        self.assertTrue(self.db.is_duplicate("hash1"))
        self.assertTrue(self.db.is_duplicate("hash2"))
        self.assertEqual(self.db.get_cache_size(), 2)

    def test_get_cache_size(self):
        self.assertEqual(self.db.get_cache_size(), 0)
        self.db.add_line("a", "line a")
        self.assertEqual(self.db.get_cache_size(), 1)


if __name__ == "__main__":
    unittest.main()
