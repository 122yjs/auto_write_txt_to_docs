"""경로 관리 유틸리티 모듈

배포 환경에서도 안전하게 동작하는 경로 설정을 제공합니다.
- PyInstaller 빌드 환경 지원
- 크로스 플랫폼 호환성
- 사용자별 설정 디렉토리 지원
- 개발자 자격 증명 파일 경로 관리
"""

import sys
import os
from pathlib import Path
import logging


# --- 기존 코드 시작 (예시) ---
# 프로젝트의 가장 꼭대기 폴더(루트) 주소를 찾는 함수
def get_project_root() -> Path:
    """프로젝트 루트 디렉토리 경로를 반환합니다."""
    # 현재 파일(__file__) 기준으로 위로 올라가서 루트 찾기
    return Path(__file__).parent.parent.parent


# 사용자별 설정/캐시 파일을 저장할 안전한 폴더 주소를 찾는 함수 (예: C:\Users\사용자이름\AppData\Roaming\프로그램이름)
def get_user_config_dir(app_name="MessengerDocsAutoWriter") -> Path:
    """운영체제에 맞는 사용자별 애플리케이션 데이터 디렉토리를 반환합니다."""
    if sys.platform == "win32":
        base_dir = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":  # macOS
        base_dir = Path.home() / "Library" / "Application Support"
    else:  # Linux / other
        base_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    
    config_dir = base_dir / app_name
    try:
        config_dir.mkdir(parents=True, exist_ok=True)  # 폴더가 없으면 만들기
    except OSError as e:
        logging.warning(f"사용자 설정 디렉토리 생성 실패 ({config_dir}): {e}. 기본 경로 사용.")
        return get_project_root()  # 실패 시 프로젝트 루트 반환
    return config_dir


# 설정 파일을 어디 저장할지 결정하는 함수
def get_safe_config_path(filename="config.json", use_user_dir=True) -> Path:
    """설정 파일의 안전한 경로를 반환합니다."""
    if use_user_dir:
        return get_user_config_dir() / filename
    else:
        # 사용자 폴더를 안 쓰면 프로그램 폴더에 저장 (권장 안 함)
        return get_project_root() / filename


# 캐시 파일(token.json, cache.json 등)을 어디 저장할지 결정하는 함수
def get_safe_cache_path(filename="cache.json", use_user_dir=True) -> Path:
    """캐시 파일의 안전한 경로를 반환합니다. token.json 등에 사용."""
    if use_user_dir:
        # 사용자별 폴더 아래 cache 서브 폴더 사용
        cache_dir = get_user_config_dir() / "cache"
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # 실패 시 사용자 폴더 바로 아래 저장
            return get_user_config_dir() / filename
        return cache_dir / filename
    else:
        return get_project_root() / filename


# --- 기존 코드 끝 ---


# ⭐⭐⭐ 아래 코드 추가 ⭐⭐⭐
# 개발자 자격 증명 파일(프로그램 신분증) 경로 찾기
def get_bundled_credentials_path(filename="developer_credentials.json"):
    """
    프로그램에 포함된(번들링된) 개발자 자격 증명 파일(credentials.json)의 주소를 알려줍니다.
    """
    # PyInstaller 등으로 exe 파일을 만들면, sys._MEIPASS 라는 특별한 임시 폴더 주소가 생깁니다.
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # 실행 파일(exe)로 실행 중인 경우:
        # PyInstaller 로 포장할 때 assets 폴더를 포함시켰다고 가정합니다.
        # 예: PyInstaller 실행 시 --add-data "src/auto_write_txt_to_docs/assets:assets" 옵션 사용
        print("실행 파일 환경: 번들된 인증서 경로 탐색")
        base_path = Path(sys._MEIPASS)
        return base_path / "assets" / filename
    else:
        # 개발 환경 (.py 파일을 직접 실행하는 경우):
        # 프로젝트 루트/src/auto_write_txt_to_docs/assets/developer_credentials.json 주소를 찾습니다.
        print("개발 환경: 소스코드 기준 인증서 경로 탐색")
        base_path = get_project_root()
        return base_path / "src" / "auto_write_txt_to_docs" / "assets" / filename


# --- 기존 코드 (환경 변수 및 기본 설정) 유지 ---
PROJECT_ROOT = get_project_root()
CONFIG_FILE = get_safe_config_path("config.json", use_user_dir=True)  # 설정 파일은 사용자 폴더에
CACHE_FILE = get_safe_cache_path("line_cache.json", use_user_dir=True)  # 캐시 파일도 사용자 폴더에
PROCESSED_STATE_FILE = get_safe_cache_path("processed_state.json", use_user_dir=True)  # 처리 상태도 사용자 폴더에
LOG_DIR = PROJECT_ROOT / "logs"  # 로그는 프로그램 폴더에 (또는 사용자 폴더로 변경 가능)

# 다른 파일에서 쉽게 쓰기 위해 문자열(str) 버전도 만듦
PROJECT_ROOT_STR = str(PROJECT_ROOT)
CONFIG_FILE_STR = str(CONFIG_FILE)
CACHE_FILE_STR = str(CACHE_FILE)
PROCESSED_STATE_FILE_STR = str(PROCESSED_STATE_FILE)
LOG_DIR_STR = str(LOG_DIR)

# ⭐⭐⭐ 아래 코드 추가 ⭐⭐⭐
# 프로그램 신분증 파일의 최종 주소 (문자열 버전)
BUNDLED_CREDENTIALS_FILE_STR = str(get_bundled_credentials_path())
# token.json (사용자 출입 허가증) 저장 경로도 명확히 정의 (google_auth.py 에서 사용)
TOKEN_FILE_PATH = get_safe_cache_path("token.json", use_user_dir=True)  # ⭐token.json은 반드시 사용자 폴더에!⭐
TOKEN_FILE_STR = str(TOKEN_FILE_PATH)