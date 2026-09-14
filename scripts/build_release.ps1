param(
    [string]$PythonExe = "python",
    [string]$AppName = "MessengerDocsAutoWriter",
    [switch]$ExcludeBundledCredentials,
    [switch]$SkipInstaller,
    [switch]$SkipPyInstallerInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BuildRoot = Join-Path $ProjectRoot "build_release"
$DistRoot = Join-Path $ProjectRoot "dist"
$ReleaseRoot = Join-Path $ProjectRoot "release"
$AppDistDir = Join-Path $DistRoot $AppName
$ZipPath = Join-Path $ReleaseRoot "$AppName-win64-portable.zip"
$OneFilePath = Join-Path $ReleaseRoot "$AppName-standalone.exe"
$PyprojectPath = Join-Path $ProjectRoot "pyproject.toml"
$AppVersion = (Select-String -Path $PyprojectPath -Pattern '^version = "([^"]+)"').Matches.Groups[1].Value
$InstallerBaseName = "MessengerDocsAutoWriterSetup-v$AppVersion"
$InstallerPath = Join-Path $ReleaseRoot "$InstallerBaseName.exe"
$InstallerScript = Join-Path $PSScriptRoot "MessengerDocsAutoWriter.iss"
$AssetSource = Join-Path $ProjectRoot "src\auto_write_txt_to_docs\assets"
$StagedAssetDir = Join-Path $BuildRoot "assets_runtime"
$EntryScript = Join-Path $ProjectRoot "main_gui.py"
$BundledCredentialsPath = Join-Path $AssetSource "developer_credentials.json"
$IncludeBundledCredentials = -not $ExcludeBundledCredentials

Write-Host "[1/6] Preparing build directories"
if (Test-Path $BuildRoot) { Remove-Item $BuildRoot -Recurse -Force }
if (Test-Path $AppDistDir) { Remove-Item $AppDistDir -Recurse -Force }
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
if (Test-Path $InstallerPath) { Remove-Item $InstallerPath -Force }
New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
New-Item -ItemType Directory -Path $ReleaseRoot -Force | Out-Null
New-Item -ItemType Directory -Path $StagedAssetDir -Force | Out-Null

Write-Host "[1.1/6] Staging bundled assets"
Get-ChildItem -Path $AssetSource -File | Where-Object { $IncludeBundledCredentials -or $_.Name -ne "developer_credentials.json" } | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $StagedAssetDir $_.Name) -Force
}

if ($IncludeBundledCredentials) {
    if (-not (Test-Path $BundledCredentialsPath)) {
        throw "Bundled developer_credentials.json not found. Use -ExcludeBundledCredentials to build without it."
    }
    Write-Host "  - Default build: bundled developer credentials included"
} else {
    Write-Host "  - Credentials-excluded build: bundled developer credentials omitted"
}

Write-Host "[2/6] Preparing PyInstaller"
if (-not $SkipPyInstallerInstall) {
    & $PythonExe -m pip install --upgrade pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller installation failed." }
}

Write-Host "[3/6] Running PyInstaller"
$PyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--onedir",
    "--name", $AppName,
    "--distpath", $DistRoot,
    "--workpath", $BuildRoot,
    "--specpath", $BuildRoot,
    "--add-data", "$StagedAssetDir;assets",
    "--collect-all", "customtkinter",
    "--collect-all", "tkinterdnd2",
    "--collect-submodules", "googleapiclient",
    "--collect-submodules", "google_auth_oauthlib",
    "--collect-submodules", "google.auth",
    "--collect-submodules", "PIL",
    "--hidden-import", "pystray._win32",
    "--hidden-import", "watchdog.observers.winapi",
    "--hidden-import", "watchdog.observers.read_directory_changes",
    $EntryScript
)
& $PythonExe @PyInstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

Write-Host "[4/6] Copying support files"
Copy-Item (Join-Path $ProjectRoot "README.md") (Join-Path $AppDistDir "README.md") -Force
Copy-Item (Join-Path $ProjectRoot "config.json.example") (Join-Path $AppDistDir "config.json.example") -Force
Copy-Item (Join-Path $ProjectRoot "added_lines_cache.json.example") (Join-Path $AppDistDir "added_lines_cache.json.example") -Force
Copy-Item (Join-Path $ProjectRoot "src\auto_write_txt_to_docs\assets\developer_credentials.json.example") (Join-Path $AppDistDir "developer_credentials.json.example") -Force

Write-Host "[5/6] Creating portable zip, onefile standalone, and installer"
Compress-Archive -Path (Join-Path $AppDistDir "*") -DestinationPath $ZipPath -Force

if (-not $SkipInstaller) {
    $InnoCompiler = Get-Command iscc -ErrorAction SilentlyContinue
    if (-not $InnoCompiler) {
        throw "Inno Setup compiler (iscc) not found. Install Inno Setup or use -SkipInstaller."
    }

    Write-Host "  - Running Inno Setup installer build"
    $env:MDAW_APP_NAME = $AppName
    $env:MDAW_APP_VERSION = $AppVersion
    $env:MDAW_SOURCE_DIR = $AppDistDir
    $env:MDAW_OUTPUT_DIR = $ReleaseRoot
    $env:MDAW_OUTPUT_BASE_FILENAME = $InstallerBaseName
    & $InnoCompiler.Source $InstallerScript
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup installer build failed." }
}

Write-Host "  - Running PyInstaller for onefile deployment"
$PyInstallerArgsOneFile = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--onefile",
    "--name", "$AppName-standalone",
    "--distpath", $ReleaseRoot,
    "--workpath", $BuildRoot,
    "--specpath", $BuildRoot,
    "--add-data", "$StagedAssetDir;assets",
    "--collect-all", "customtkinter",
    "--collect-all", "tkinterdnd2",
    "--collect-submodules", "googleapiclient",
    "--collect-submodules", "google_auth_oauthlib",
    "--collect-submodules", "google.auth",
    "--collect-submodules", "PIL",
    "--hidden-import", "pystray._win32",
    "--hidden-import", "watchdog.observers.winapi",
    "--hidden-import", "watchdog.observers.read_directory_changes",
    $EntryScript
)
& $PythonExe @PyInstallerArgsOneFile
if ($LASTEXITCODE -ne 0) { throw "PyInstaller onefile build failed." }

Write-Host "[6/6] Cleaning temporary build files"
try {
    if (Test-Path $BuildRoot) { Remove-Item $BuildRoot -Recurse -Force }
} catch {
    Write-Warning "temporary build cleanup failed: $($_.Exception.Message)"
}

Write-Host "Done"
Write-Host "EXE folder: $AppDistDir"
Write-Host "ZIP file: $ZipPath"
Write-Host "Standalone EXE file: $OneFilePath"
if (Test-Path $InstallerPath) {
    Write-Host "Installer EXE file: $InstallerPath"
} elseif ($SkipInstaller) {
    Write-Host "Installer build skipped: $InstallerPath"
}
