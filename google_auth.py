# google_auth.py (Docs 기능 버전)
import os
import json
import logging
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json # token.json 사용 위해

# Google API 스코프 설정
SCOPES = ['https://www.googleapis.com/auth/documents']

# 로깅 설정
def setup_google_auth_logging():
    """Google 인증 로깅 시스템 설정"""
    logger = logging.getLogger('google_auth')
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # logs 폴더 생성 (없는 경우)
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # 파일 핸들러 설정
    log_filename = os.path.join(logs_dir, f"google_auth_log_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    return logger

# 토큰 저장 파일 경로
TOKEN_PATH = 'token.json'

def authenticate(credentials_path, log_func):
    """Google API 인증을 수행하고 Credentials 객체를 반환합니다."""
    auth_logger = logging.getLogger('google_auth')
    
    creds = None
    token_path = TOKEN_PATH
    
    auth_logger.info(f"인증 시작 - token_path: {token_path}, credentials_path: {credentials_path}")
    
    # 기존 토큰 파일이 있으면 로드
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            log_func("기존 토큰 파일 로드 완료.")
            auth_logger.info("기존 토큰 파일 로드 완료")
        except Exception as e:
            log_func(f"기존 토큰 파일 로드 실패: {e}")
            auth_logger.warning(f"기존 토큰 파일 로드 실패: {e}")
            creds = None

    if not creds or not creds.valid:
        auth_logger.info("토큰 갱신 또는 새 인증 필요")
        
        if creds and creds.expired and creds.refresh_token:
            try:
                log_func("백엔드: 만료된 인증 정보 갱신 시도...")
                creds.refresh(Request())
                log_func("백엔드: 인증 정보 갱신 완료.")
                auth_logger.info("토큰 갱신 완료")
            except Exception as e:
                log_func(f"오류: 인증 정보 갱신 실패 - {e}")
                auth_logger.warning(f"토큰 갱신 실패: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists(credentials_path):
                log_func(f"오류: Credentials 파일({credentials_path})을 찾을 수 없습니다.")
                auth_logger.error(f"Credentials 파일을 찾을 수 없음: {credentials_path}")
                return None
            
            auth_logger.info("새로운 인증 플로우 시작")
            try:
                log_func("백엔드: Google 계정 인증 필요. 브라우저를 확인하세요.")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                log_func("백엔드: Google 계정 인증 성공.")
                auth_logger.info("새로운 인증 완료")
            except Exception as e:
                log_func(f"오류: Google 계정 인증 중 오류 발생 - {e}")
                auth_logger.error(f"새로운 인증 실패: {e}", exc_info=True)
                return None

        try:
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
            log_func(f"백엔드: 새로운 인증 정보({TOKEN_PATH}) 저장됨.")
            auth_logger.info(f"토큰 저장 완료: {TOKEN_PATH}")
        except Exception as e:
            log_func(f"경고: 새로운 인증 정보({TOKEN_PATH}) 저장 실패 - {e}")
            auth_logger.error(f"토큰 저장 실패: {e}")
    else:
        auth_logger.info("기존 토큰이 유효함")

    return creds

def get_google_services(credentials_path, log_func):
    """ 인증을 수행하고 필요한 Google 서비스 객체(Docs)를 딕셔너리로 반환합니다. """
    # 로깅 시스템 초기화
    auth_logger = setup_google_auth_logging()
    auth_logger.info(f"Google 서비스 생성 시작 - credentials: {credentials_path}")
    
    creds = authenticate(credentials_path, log_func)
    if not creds:
        log_func("오류: Google API 인증 실패. 서비스 객체를 생성할 수 없습니다.")
        auth_logger.error("Google API 인증 실패")
        return None

    auth_logger.info("Google 인증 성공")
    
    services = {}
    try:
        log_func("백엔드: Google Docs 서비스 객체 생성 시도...")
        # Docs 서비스만 생성
        services['docs'] = build('docs', 'v1', credentials=creds)
        # 필요시 Drive 서비스도 추가 가능
        # services['drive'] = build('drive', 'v3', credentials=creds)
        log_func("백엔드: Google Docs 서비스 객체 생성 완료.")
        auth_logger.info("Google Docs 서비스 객체 생성 완료")
        return services
    except HttpError as error:
        log_func(f"오류: Google 서비스 객체 생성 중 API 오류 발생 - {error}")
        auth_logger.error(f"Google 서비스 객체 생성 중 API 오류: {error}", exc_info=True)
        return None
    except Exception as e:
        log_func(f"오류: Google 서비스 객체 생성 중 예외 발생 - {e}")
        auth_logger.error(f"Google 서비스 객체 생성 중 예외: {e}", exc_info=True)
        return None