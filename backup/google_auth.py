# google_auth.py (Docs 기능 버전)
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json # token.json 사용 위해

# 필요한 API 범위 (Scope) 정의 - Docs 사용에 필요한 최소 범위
SCOPES = [
    'https://www.googleapis.com/auth/documents', # Docs 읽기/쓰기 권한
    'https://www.googleapis.com/auth/drive.file', # Docs 파일 생성/접근에 필요할 수 있음 (선택적 추가 가능)
]

# 토큰 저장 파일 경로
TOKEN_PATH = 'token.json'

def authenticate(credentials_path, log_func):
    """ Google API 인증을 수행하고 Credentials 객체를 반환합니다. """
    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            # log_func(f"백엔드: 저장된 인증 정보({TOKEN_PATH}) 로드됨.") # 로그 간소화
        except Exception as e:
            log_func(f"경고: 저장된 인증 정보({TOKEN_PATH}) 로드 실패 - {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                log_func("백엔드: 만료된 인증 정보 갱신 시도...")
                creds.refresh(Request())
                log_func("백엔드: 인증 정보 갱신 완료.")
            except Exception as e:
                log_func(f"오류: 인증 정보 갱신 실패 - {e}")
                creds = None
        else:
            if not os.path.exists(credentials_path):
                log_func(f"오류: Credentials 파일({credentials_path})을 찾을 수 없습니다.")
                return None
            try:
                log_func("백엔드: Google 계정 인증 필요. 브라우저를 확인하세요.")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                log_func("백엔드: Google 계정 인증 성공.")
            except Exception as e:
                log_func(f"오류: Google 계정 인증 중 오류 발생 - {e}")
                return None

        try:
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
            log_func(f"백엔드: 새로운 인증 정보({TOKEN_PATH}) 저장됨.")
        except Exception as e:
            log_func(f"경고: 새로운 인증 정보({TOKEN_PATH}) 저장 실패 - {e}")

    return creds

def get_google_services(credentials_path, log_func):
    """ 인증을 수행하고 필요한 Google 서비스 객체(Docs)를 딕셔너리로 반환합니다. """
    creds = authenticate(credentials_path, log_func)
    if not creds:
        log_func("오류: Google API 인증 실패. 서비스 객체를 생성할 수 없습니다.")
        return None

    services = {}
    try:
        log_func("백엔드: Google Docs 서비스 객체 생성 시도...")
        # Docs 서비스만 생성
        services['docs'] = build('docs', 'v1', credentials=creds)
        # 필요시 Drive 서비스도 추가 가능
        # services['drive'] = build('drive', 'v3', credentials=creds)
        log_func("백엔드: Google Docs 서비스 객체 생성 완료.")
        return services
    except HttpError as error:
        log_func(f"오류: Google 서비스 객체 생성 중 API 오류 발생 - {error}")
        return None
    except Exception as e:
        log_func(f"오류: Google 서비스 객체 생성 중 예외 발생 - {e}")
        return None