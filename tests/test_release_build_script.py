import unittest
from pathlib import Path


class ReleaseBuildScriptTests(unittest.TestCase):
    def setUp(self):
        self.script_source = Path("scripts/build_release.ps1").read_text(encoding="utf-8")

    def test_build_script_includes_required_pyinstaller_options(self):
        self.assertIn("--windowed", self.script_source)
        self.assertIn("--onedir", self.script_source)
        self.assertIn("--add-data", self.script_source)
        self.assertIn('$AssetSource = Join-Path $ProjectRoot "src\\auto_write_txt_to_docs\\assets"', self.script_source)
        self.assertIn('$StagedAssetDir = Join-Path $BuildRoot "assets_runtime"', self.script_source)
        self.assertIn('"$StagedAssetDir;assets"', self.script_source)
        self.assertIn("[switch]$IncludeBundledCredentials", self.script_source)
        self.assertIn("--collect-all", self.script_source)
        self.assertIn("customtkinter", self.script_source)
        self.assertIn("tkinterdnd2", self.script_source)
        self.assertIn("--collect-submodules", self.script_source)
        self.assertIn("googleapiclient", self.script_source)
        self.assertIn("google_auth_oauthlib", self.script_source)
        self.assertIn("google.auth", self.script_source)
        self.assertIn('Where-Object { $_.Name -ne "developer_credentials.json" }', self.script_source)
        self.assertIn('Copy-Item $BundledCredentialsPath', self.script_source)

    def test_build_script_copies_support_files_and_creates_zip(self):
        self.assertIn("README.md", self.script_source)
        self.assertIn("config.json.example", self.script_source)
        self.assertIn("added_lines_cache.json.example", self.script_source)
        self.assertIn("developer_credentials.json.example", self.script_source)
        self.assertIn("Compress-Archive", self.script_source)
        self.assertIn("portable.zip", self.script_source)
        self.assertIn("Remove-Item $BuildRoot -Recurse -Force", self.script_source)


if __name__ == "__main__":
    unittest.main()
