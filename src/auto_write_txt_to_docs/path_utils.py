"""경로 관리 유틸리티 모듈

배포 환경에서도 안전하게 동작하는 경로 설정을 제공합니다.
- PyInstaller 빌드 환경 지원
- 크로스 플랫폼 호환성
- 사용자별 설정 디렉토리 지원
"""

import sys
import os
from pathlib import Path


def get_project_root():
    """프로젝트 루트 디렉토리를 안전하게 찾기
    
    Returns:
        Path: 프로젝트 루트 디렉토리 경로
    """
    if getattr(sys, 'frozen', False):  # PyInstaller로 빌드된 경우
        # 실행 파일이 있는 디렉토리를 프로젝트 루트로 사용
        return Path(sys.executable).parent
    else:
        # 개발 환경: 현재 파일에서 3단계 위로 (src/auto_write_txt_to_docs -> src -> 프로젝트 루트)
        return Path(__file__).parent.parent.parent


def get_user_config_dir(app_name="auto_write_txt_to_docs"):
    """사용자별 설정 디렉토리 경로 반환
    
    Args:
        app_name (str): 애플리케이션 이름
        
    Returns:
        Path: 사용자 설정 디렉토리 경로
    """
    if sys.platform == "win32":
        # Windows: %APPDATA%\app_name
        config_dir = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / app_name
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/app_name
        config_dir = Path.home() / 'Library' / 'Application Support' / app_name
    else:
        # Linux: ~/.config/app_name
        config_dir = Path.home() / '.config' / app_name
    
    # 디렉토리가 없으면 생성
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_safe_config_path(filename="config.json", use_user_dir=False):
    """안전한 설정 파일 경로 반환
    
    Args:
        filename (str): 설정 파일명
        use_user_dir (bool): True면 사용자 디렉토리, False면 프로젝트 루트 사용
        
    Returns:
        Path: 설정 파일 경로
    """
    if use_user_dir:
        return get_user_config_dir() / filename
    else:
        return get_project_root() / filename


def get_safe_cache_path(filename="added_lines_cache.json", use_user_dir=False):
    """안전한 캐시 파일 경로 반환
    
    Args:
        filename (str): 캐시 파일명
        use_user_dir (bool): True면 사용자 디렉토리, False면 프로젝트 루트 사용
        
    Returns:
        Path: 캐시 파일 경로
    """
    if use_user_dir:
        return get_user_config_dir() / filename
    else:
        return get_project_root() / filename


# 환경 변수로 오버라이드 가능한 설정
PROJECT_ROOT = Path(os.environ.get('AUTO_WRITE_ROOT', get_project_root()))
CONFIG_FILE = Path(os.environ.get('AUTO_WRITE_CONFIG', get_safe_config_path()))
CACHE_FILE = Path(os.environ.get('AUTO_WRITE_CACHE', get_safe_cache_path()))

# 하위 호환성을 위한 문자열 버전
PROJECT_ROOT_STR = str(PROJECT_ROOT)
CONFIG_FILE_STR = str(CONFIG_FILE)
CACHE_FILE_STR = str(CACHE_FILE)