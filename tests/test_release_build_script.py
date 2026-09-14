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
        self.assertIn("[switch]$ExcludeBundledCredentials", self.script_source)
        self.assertIn("--collect-all", self.script_source)
        self.assertIn("customtkinter", self.script_source)
        self.assertIn("tkinterdnd2", self.script_source)
        self.assertIn("--collect-submodules", self.script_source)
        self.assertIn("googleapiclient", self.script_source)
        self.assertIn("google_auth_oauthlib", self.script_source)
        self.assertIn("google.auth", self.script_source)
        self.assertIn('$IncludeBundledCredentials = -not $ExcludeBundledCredentials', self.script_source)
        self.assertIn('Where-Object { $IncludeBundledCredentials -or $_.Name -ne "developer_credentials.json" }', self.script_source)
        self.assertIn('Use -ExcludeBundledCredentials to build without it.', self.script_source)

    def test_build_script_copies_support_files_and_creates_zip(self):
        self.assertIn("README.md", self.script_source)
        self.assertIn("config.json.example", self.script_source)
        self.assertIn("added_lines_cache.json.example", self.script_source)
        self.assertIn("developer_credentials.json.example", self.script_source)
        self.assertIn("Compress-Archive", self.script_source)
        self.assertIn("portable.zip", self.script_source)
        self.assertIn("MessengerDocsAutoWriterSetup", self.script_source)
        self.assertIn("iscc", self.script_source)
        self.assertIn("Remove-Item $BuildRoot -Recurse -Force", self.script_source)
        self.assertIn("Write-Warning", self.script_source)
        self.assertIn("temporary build cleanup failed", self.script_source)

    def test_release_workflows_upload_installer_asset(self):
        public_workflow = Path(".github/workflows/release-windows.yml").read_text(encoding="utf-8")
        internal_workflow = Path(".github/workflows/internal-bundled-release.yml").read_text(encoding="utf-8")

        self.assertIn("Inno Setup", public_workflow)
        self.assertIn("MessengerDocsAutoWriterSetup-v", public_workflow)
        self.assertIn("MessengerDocsAutoWriterSetup-v", internal_workflow)


if __name__ == "__main__":
    unittest.main()
