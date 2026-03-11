import json
import unittest
from unittest.mock import patch

from src.auto_write_txt_to_docs.update_checker import (
    REPOSITORY_RELEASES_URL,
    check_for_new_release,
    fetch_latest_release_metadata,
    is_newer_version,
    normalize_version_tag,
    parse_version_tuple,
)


class FakeHttpResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class UpdateCheckerTests(unittest.TestCase):
    def test_normalize_version_tag_trims_prefixes(self):
        self.assertEqual(normalize_version_tag("v0.6.1"), "0.6.1")
        self.assertEqual(normalize_version_tag("refs/tags/v0.6.2"), "0.6.2")
        self.assertEqual(normalize_version_tag("release-0.6.3"), "0.6.3")

    def test_parse_version_tuple_extracts_numeric_parts(self):
        self.assertEqual(parse_version_tuple("v1.2.10"), (1, 2, 10))
        self.assertEqual(parse_version_tuple("1.2.0-beta.1"), (1, 2, 0, 1))

    def test_is_newer_version_compares_padded_semver(self):
        self.assertTrue(is_newer_version("0.6.1", current_version="0.6.0"))
        self.assertFalse(is_newer_version("0.6.0", current_version="0.6.0"))
        self.assertFalse(is_newer_version("0.5.9", current_version="0.6.0"))

    def test_fetch_latest_release_metadata_reads_github_payload(self):
        payload = json.dumps({"tag_name": "v0.6.1", "html_url": "https://example.com/release"}).encode("utf-8")

        with patch("src.auto_write_txt_to_docs.update_checker.urlopen", return_value=FakeHttpResponse(payload)):
            metadata = fetch_latest_release_metadata()

        self.assertEqual(metadata["tag_name"], "v0.6.1")
        self.assertEqual(metadata["html_url"], "https://example.com/release")

    def test_check_for_new_release_marks_update_available(self):
        payload = json.dumps(
            {
                "tag_name": "v0.6.1",
                "name": "v0.6.1",
                "html_url": "https://example.com/release",
                "published_at": "2026-03-11T12:00:00Z",
            }
        ).encode("utf-8")

        with patch("src.auto_write_txt_to_docs.update_checker.urlopen", return_value=FakeHttpResponse(payload)):
            release_info = check_for_new_release(current_version="0.6.0")

        self.assertTrue(release_info["update_available"])
        self.assertEqual(release_info["latest_version"], "0.6.1")
        self.assertEqual(release_info["release_url"], "https://example.com/release")

    def test_check_for_new_release_falls_back_to_repository_releases_url(self):
        payload = json.dumps({"tag_name": "v0.6.0"}).encode("utf-8")

        with patch("src.auto_write_txt_to_docs.update_checker.urlopen", return_value=FakeHttpResponse(payload)):
            release_info = check_for_new_release(current_version="0.6.0")

        self.assertFalse(release_info["update_available"])
        self.assertEqual(release_info["release_url"], REPOSITORY_RELEASES_URL)


if __name__ == "__main__":
    unittest.main()
