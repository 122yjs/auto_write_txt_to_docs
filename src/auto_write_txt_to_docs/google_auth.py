import os
import json
import logging
from datetime import datetime
# 구글 인증 관련 라이브러리들
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ⭐ path_utils 에서 필요한 주소 정보 가져오기 ⭐
try:
    # BUNDLED_CREDENTIALS_FILE_STR: 프로그램 신분증 주소
    # TOKEN_FILE_STR: 사용자 출입 허가증 저장 주소
    from src.auto_write_txt_to_docs.path_utils import BUNDLED_CREDENTIALS_FILE_STR, TOKEN_FILE_STR
except ImportError:
    try:
        # 상대 import 시도 (패키지 내에서 실행될 때)
        from .path_utils import BUNDLED_CREDENTIALS_FILE_STR, TOKEN_FILE_STR
    except ImportError:
        # path_utils 파일이 없는 비상 상황 대비
        print("오류: path_utils.py 파일을 찾을 수 없습니다. Google 인증이 작동하지 않습니다.")
        BUNDLED_CREDENTIALS_FILE_STR = None
        TOKEN_FILE_STR = 'token.json'  # 임시 경로

# 프로그램이 구글 문서에 접근할 수 있도록 '권한 범위(Scope)' 설정
SCOPES = [
    'https://www.googleapis.com/auth/documents',  # Docs 읽기/쓰기 권한
    'https://www.googleapis.com/auth/drive.file',  # Docs 파일 생성/접근에 필요할 수 있음 (선택적 추가 가능)
]

# 로깅 설정
def setup_google_auth_logging():
    logger = logging.getLogger('google_auth')
    if not logger.hasHandlers():
        # 파일 및 콘솔 핸들러 설정 (기존 코드 내용)
        pass
    logger.setLevel(logging.INFO)
    return logger

# ⭐ credentials_path 인자 제거 ⭐
def authenticate(log_func):
    """
    Google API 인증을 수행하고 '출입 허가증'(Credentials 객체)을 돌려줍니다.
    - 사용자 컴퓨터에 유효한 token.json(출입 허가증)이 있으면 그것을 사용합니다.
    - 없거나 만료되었으면, 프로그램에 포함된 credentials.json(신분증)을 이용해
      사용자에게 브라우저로 허락을 받고 새 token.json을 발급받아 저장합니다.
    """
    auth_logger = logging.getLogger('google_auth')
    creds = None  # 출입 허가증을 담을 변수 초기화

    # ⭐ 1. 프로그램 신분증 파일 주소 가져오기 (path_utils에서) ⭐
    credentials_path = BUNDLED_CREDENTIALS_FILE_STR
    # ⭐ 2. 사용자 출입 허가증 저장 파일 주소 가져오기 (path_utils에서) ⭐
    token_path = TOKEN_FILE_STR

    # 신분증 파일이 실제로 존재하는지 확인
    if not credentials_path or not os.path.exists(credentials_path):
        error_msg = f"오류: 프로그램에 포함된 인증 파일({credentials_path})을 찾을 수 없습니다. 개발자에게 문의하세요."
        log_func(error_msg)
        auth_logger.error(error_msg)
        return None  # 신분증 없이는 진행 불가

    auth_logger.info(f"인증 시작 - 토큰 경로: {token_path}, 신분증 경로: {credentials_path}")
    log_func(f"백엔드: Google 인증 확인 중... (토큰 저장소: {token_path})")

    # ⭐ 3. 기존 출입 허가증(token.json)이 있는지 확인하고 불러오기 ⭐
    if os.path.exists(token_path):
        try:
            # 파일에서 출입 허가증 정보 로드 (권한 범위 SCOPES도 맞는지 확인)
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            log_func("백엔드: 저장된 Google 사용자 인증 정보(토큰) 로드 성공.")
            auth_logger.info("기존 토큰 파일 로드 성공")
        except Exception as e:
            log_func(f"경고: 기존 인증 정보(토큰) 파일 로드 실패: {e}. 다시 인증이 필요합니다.")
            auth_logger.warning(f"기존 토큰 파일 로드 실패: {e}")
            creds = None  # 실패 시 없는 것으로 간주

    # ⭐ 4. 출입 허가증이 없거나, 있더라도 유효하지 않은 경우 처리 ⭐
    # creds.valid : 출입 허가증이 유효한가?
    # creds.expired : 출입 허가증이 만료되었는가?
    # creds.refresh_token : 만료 시 갱신할 수 있는 특별한 토큰이 있는가?
    if not creds or not creds.valid:
        # 4-1. 만료되었지만 갱신 토큰이 있으면, 조용히 갱신 시도
        if creds and creds.expired and creds.refresh_token:
            log_func("백엔드: 인증 정보(토큰) 만료됨. 자동 갱신 시도...")
            auth_logger.info("토큰 만료됨. 갱신 시도.")
            try:
                creds.refresh(Request())  # 갱신!
                log_func("백엔드: 인증 정보(토큰) 갱신 성공.")
                auth_logger.info("토큰 갱신 성공.")
            except Exception as e:
                log_func(f"경고: 인증 정보(토큰) 갱신 실패: {e}. 다시 인증이 필요합니다.")
                auth_logger.warning(f"토큰 갱신 실패: {e}")
                creds = None  # 갱신 실패 시, 새로 발급받아야 함

        # 4-2. 갱신에 실패했거나, 애초에 출입 허가증이 없으면 -> 사용자 허락받기(새 인증)
        if not creds:
            auth_logger.info("새로운 인증 플로우 시작 (사용자 브라우저 확인 필요)")
            try:
                log_func("백엔드: ⚠️ Google 계정 인증 필요! 웹 브라우저 창을 확인하고 로그인 및 접근을 '허용' 해주세요. ⚠️")
                # ⭐ 프로그램 신분증(credentials_path)을 이용해 사용자 허락 절차(flow) 시작 ⭐
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                # 브라우저를 열고, 사용자가 허락할 때까지 기다림 (port=0 은 사용 가능한 아무 포트나 사용)
                creds = flow.run_local_server(port=0)
                log_func("백엔드: ✅ Google 계정 사용자 인증 성공!")
                auth_logger.info("새로운 사용자 인증 완료")
            except Exception as e:
                log_func(f"오류: Google 계정 인증 중 오류 발생 - {e}")
                auth_logger.error(f"새로운 인증 실패: {e}", exc_info=True)
                return None  # 인증 실패

        # ⭐ 5. 새로 발급/갱신된 출입 허가증(creds)을 token.json 파일에 저장 ⭐
        # (다음에 실행할 때는 다시 허락받지 않기 위해)
        try:
            # 토큰 파일이 저장될 폴더가 없으면 만들기 (path_utils가 해주지만 안전하게)
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'w', encoding='utf-8') as token:
                token.write(creds.to_json())  # 출입 허가증 정보를 JSON 형태로 파일에 쓰기
            log_func(f"백엔드: 새 인증 정보(토큰) 저장 완료: {token_path}")
            auth_logger.info(f"토큰 저장 완료: {token_path}")
        except Exception as e:
            log_func(f"경고: 새 인증 정보({token_path}) 저장 실패 - {e}")
            auth_logger.error(f"토큰 저장 실패: {e}")
    else:
        # 3번에서 로드한 기존 출입 허가증이 유효한 경우
        auth_logger.info("기존 토큰이 유효함.")
        log_func("백엔드: 기존 Google 인증 정보(토큰)가 유효합니다.")

    return creds  # 최종적으로 유효한 출입 허가증 반환

# ⭐ credentials_path 인자 제거 ⭐
def get_google_services(log_func):
    """ 인증을 수행하고, 구글 문서 서비스 객체(API 통로)를 만들어 반환합니다. """
    auth_logger = setup_google_auth_logging()
    auth_logger.info("Google 서비스 생성 시작")

    # ⭐ authenticate() 함수 호출 시 credentials_path 안 넘김 ⭐
    creds = authenticate(log_func)  # 위에서 만든 인증 함수 호출 (출입 허가증 받아오기)
    if not creds:
        # 출입 허가증 받기 실패
        log_func("오류: Google API 인증 실패. 서비스 객체를 생성할 수 없습니다.")
        auth_logger.error("Google API 인증 실패")
        return None

    services = {}
    try:
        log_func("백엔드: Google Docs 서비스 객체 생성 시도...")
        # Docs 서비스만 생성
        services['docs'] = build('docs', 'v1', credentials=creds)
        # 필요시 Drive 서비스도 추가 가능
        # services['drive'] = build('drive', 'v3', credentials=creds)
        log_func("백엔드: Google Docs 서비스 객체 생성 완료.")
        auth_logger.info("Google 서비스 객체 생성 완료")
        return services
    except HttpError as error:
        log_func(f"오류: Google 서비스 객체 생성 중 API 오류 발생 - {error}")
        auth_logger.error(f"Google 서비스 객체 생성 중 API 오류: {error}")
        return None
    except Exception as e:
        log_func(f"오류: Google 서비스 객체 생성 중 예외 발생 - {e}")
        auth_logger.error(f"Google 서비스 객체 생성 중 예외: {e}", exc_info=True)
        return None