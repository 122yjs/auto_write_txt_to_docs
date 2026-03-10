param(
    [string]$PythonExe = "python",
    [string]$AppName = "MessengerDocsAutoWriter",
    [switch]$IncludeBundledCredentials,
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
$AssetSource = Join-Path $ProjectRoot "src\auto_write_txt_to_docs\assets"
$StagedAssetDir = Join-Path $BuildRoot "assets_runtime"
$EntryScript = Join-Path $ProjectRoot "main_gui.py"

Write-Host "[1/6] Preparing build directories"
if (Test-Path $BuildRoot) { Remove-Item $BuildRoot -Recurse -Force }
if (Test-Path $AppDistDir) { Remove-Item $AppDistDir -Recurse -Force }
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
New-Item -ItemType Directory -Path $ReleaseRoot -Force | Out-Null
New-Item -ItemType Directory -Path $StagedAssetDir -Force | Out-Null

Write-Host "[1.1/6] Staging bundled assets"
Get-ChildItem -Path $AssetSource -File | Where-Object { $_.Name -ne "developer_credentials.json" } | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $StagedAssetDir $_.Name) -Force
}

if ($IncludeBundledCredentials) {
    $BundledCredentialsPath = Join-Path $AssetSource "developer_credentials.json"
    if (-not (Test-Path $BundledCredentialsPath)) {
        throw "Bundled developer_credentials.json not found."
    }
    Copy-Item $BundledCredentialsPath (Join-Path $StagedAssetDir "developer_credentials.json") -Force
    Write-Host "  - Internal build: bundled developer credentials included"
} else {
    Write-Host "  - Public build: bundled developer credentials excluded"
}

Write-Host "[2/6] Preparing PyInstaller"
if (-not $SkipPyInstallerInstall) {
    & $PythonExe -m pip install --upgrade pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller installation failed." }
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

Write-Host "[5/6] Creating portable zip and onefile standalone"
Compress-Archive -Path (Join-Path $AppDistDir "*") -DestinationPath $ZipPath -Force

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
if (Test-Path $BuildRoot) { Remove-Item $BuildRoot -Recurse -Force }

Write-Host "Done"
Write-Host "EXE folder: $AppDistDir"
Write-Host "ZIP file: $ZipPath"
Write-Host "Standalone EXE file: $OneFilePath"
