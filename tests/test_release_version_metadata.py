import re
import unittest
from pathlib import Path


class ReleaseVersionMetadataTests(unittest.TestCase):
    def test_release_version_is_consistent_across_project_files(self):
        pyproject_source = Path("pyproject.toml").read_text(encoding="utf-8")
        package_init_source = Path("src/__init__.py").read_text(encoding="utf-8")
        workflow_source = Path(".github/workflows/release-windows.yml").read_text(encoding="utf-8")

        pyproject_match = re.search(r'version = "([^"]+)"', pyproject_source)
        package_match = re.search(r"__version__ = '([^']+)'", package_init_source)
        workflow_match = re.search(r"default: v([0-9]+\.[0-9]+\.[0-9]+)", workflow_source)

        self.assertIsNotNone(pyproject_match)
        self.assertIsNotNone(package_match)
        self.assertIsNotNone(workflow_match)
        self.assertEqual(pyproject_match.group(1), package_match.group(1))
        self.assertEqual(pyproject_match.group(1), workflow_match.group(1))


if __name__ == "__main__":
    unittest.main()
