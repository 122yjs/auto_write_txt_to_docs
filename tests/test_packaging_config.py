import tomllib
import unittest
from pathlib import Path


class PackagingConfigTests(unittest.TestCase):
    def setUp(self):
        self.pyproject_data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        self.requirements = Path("requirements.txt").read_text(encoding="utf-8").splitlines()
        self.main_gui_source = Path("main_gui.py").read_text(encoding="utf-8")

    def test_console_script_points_to_real_entrypoint(self):
        scripts = self.pyproject_data["project"]["scripts"]
        self.assertEqual(scripts["auto_write_gui"], "main_gui:main")
        self.assertIn("def main():", self.main_gui_source)

    def test_project_dependencies_include_runtime_packages(self):
        dependencies = self.pyproject_data["project"]["dependencies"]
        self.assertIn("psutil>=5.9.5", dependencies)
        self.assertIn("pystray>=0.19.0", dependencies)

    def test_setuptools_configuration_includes_main_gui_module(self):
        setuptools_config = self.pyproject_data["tool"]["setuptools"]
        package_find_config = setuptools_config["packages"]["find"]

        self.assertEqual(setuptools_config["py-modules"], ["main_gui"])
        self.assertEqual(package_find_config["include"], ["src*"])
        self.assertTrue(package_find_config["namespaces"])

    def test_requirements_file_keeps_psutil_and_pystray_separate(self):
        self.assertIn("psutil>=5.9.5", self.requirements)
        self.assertTrue(any(line.startswith("pystray") for line in self.requirements))
        self.assertTrue(all("psutil" not in line or "pystray" not in line for line in self.requirements))


if __name__ == "__main__":
    unittest.main()
