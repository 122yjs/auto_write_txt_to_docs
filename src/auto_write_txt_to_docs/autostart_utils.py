import os
import sys
from pathlib import Path


APP_NAME = "MessengerDocsAutoWriter"


def supports_windows_startup(platform_name=None):
    """현재 환경에서 Windows 시작 프로그램 연동이 가능한지 반환한다."""
    return (platform_name or sys.platform) == "win32"


def get_windows_startup_dir(appdata=None, platform_name=None):
    """Windows 시작프로그램 폴더 경로를 반환한다."""
    if not supports_windows_startup(platform_name=platform_name):
        return None

    base_dir = Path(appdata or os.environ.get("APPDATA", Path.home()))
    return base_dir / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def get_startup_launcher_path(app_name=APP_NAME, appdata=None, platform_name=None):
    """자동 실행용 CMD 런처 파일 경로를 반환한다."""
    startup_dir = get_windows_startup_dir(appdata=appdata, platform_name=platform_name)
    if startup_dir is None:
        return None
    return startup_dir / f"{app_name}.cmd"


def build_windows_startup_launcher_contents(script_path=None, executable_path=None, frozen=None):
    """시작프로그램 폴더에 둘 CMD 런처 내용을 생성한다."""
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    executable = Path(executable_path or sys.executable)

    if is_frozen:
        command = f'start "" "{executable}"'
    else:
        main_script = Path(script_path) if script_path is not None else Path(__file__).resolve().parents[2] / "main_gui.py"
        command = f'"{executable}" "{main_script}"'

    return f"@echo off\n{command}\n"


def is_windows_startup_enabled(launcher_path=None):
    """자동 실행 런처 파일이 존재하는지 확인한다."""
    target_path = Path(launcher_path) if launcher_path is not None else get_startup_launcher_path()
    return bool(target_path and target_path.exists())


def set_windows_startup_enabled(enabled, launcher_path=None, launcher_contents=None):
    """Windows 시작프로그램 폴더의 자동 실행 런처를 생성하거나 제거한다."""
    target_path = Path(launcher_path) if launcher_path is not None else get_startup_launcher_path()
    if target_path is None:
        return False

    if enabled:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        content = launcher_contents or build_windows_startup_launcher_contents()
        target_path.write_text(content, encoding="utf-8")
        return True

    if target_path.exists():
        target_path.unlink()
    return False
