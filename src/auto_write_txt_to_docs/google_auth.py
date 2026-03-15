import json
import logging
import os
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    from src.auto_write_txt_to_docs.path_utils import (
        BUNDLED_CREDENTIALS_FILE_STR,
        TOKEN_FILE_STR,
        USER_CREDENTIALS_FILE_STR,
        get_effective_credentials_path,
    )
except ImportError:
    try:
        from .path_utils import (
            BUNDLED_CREDENTIALS_FILE_STR,
            TOKEN_FILE_STR,
            USER_CREDENTIALS_FILE_STR,
            get_effective_credentials_path,
        )
    except ImportError:
        print("오류: path_utils.py 파일을 찾을 수 없습니다. Google 인증이 작동하지 않습니다.")
        BUNDLED_CREDENTIALS_FILE_STR = None
        USER_CREDENTIALS_FILE_STR = None
        TOKEN_FILE_STR = "token.json"
        get_effective_credentials_path = None


SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]


class GoogleAuthActionRequired(Exception):
    """사용자 전면 작업이 필요한 인증 상태를 나타낸다."""

    def __init__(self, reason_code, user_message, quarantined_token_path=None):
        super().__init__(user_message)
        self.reason_code = reason_code
        self.user_message = user_message
        self.quarantined_token_path = quarantined_token_path


def setup_google_auth_logging():
    logger = logging.getLogger("google_auth")
    if not logger.hasHandlers():
        pass
    logger.setLevel(logging.INFO)
    return logger


def _resolve_auth_paths():
    credentials_path = str(get_effective_credentials_path()) if get_effective_credentials_path else BUNDLED_CREDENTIALS_FILE_STR
    token_path = TOKEN_FILE_STR
    return credentials_path, token_path


def _validate_credentials_path(credentials_path, log_func, auth_logger):
    if not credentials_path:
        error_msg = "오류: Google API 인증에 필요한 필수 설정이 누락되었습니다. 프로그램 제작자에게 문의하세요."
        log_func(error_msg)
        auth_logger.critical("BUNDLED_CREDENTIALS_FILE_STR is missing in path_utils.py")
        return False

    if not os.path.exists(credentials_path):
        error_msg = (
            f"오류: Google 인증 파일({os.path.basename(credentials_path)})을 찾을 수 없습니다. "
            f"사용자 설정 경로({USER_CREDENTIALS_FILE_STR}) 또는 기본 번들 경로({BUNDLED_CREDENTIALS_FILE_STR})를 확인해 주세요."
        )
        log_func(error_msg)
        auth_logger.critical(f"Credentials file missing at: {credentials_path}")
        return False

    return True


def _get_expected_client_id(credentials_path):
    with open(credentials_path, "r", encoding="utf-8") as credentials_file:
        client_config = json.load(credentials_file)
    return client_config.get("installed", {}).get("client_id") or client_config.get("web", {}).get("client_id")


def _save_token(credentials, token_path, log_func, auth_logger):
    try:
        token_dir = os.path.dirname(token_path)
        if token_dir:
            os.makedirs(token_dir, exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(credentials.to_json())
        log_func(f"백엔드: 새 인증 정보(토큰) 저장 완료: {token_path}")
        auth_logger.info(f"토큰 저장 완료: {token_path}")
    except Exception as exc:
        log_func(f"경고: 새 인증 정보({token_path}) 저장 실패 - {exc}")
        auth_logger.error(f"토큰 저장 실패: {exc}")


def quarantine_token_file(log_func, reason_code="manual_reset"):
    """현재 토큰 파일을 격리 보관하고 경로를 반환한다."""
    auth_logger = setup_google_auth_logging()
    _credentials_path, token_path = _resolve_auth_paths()
    if not token_path or not os.path.exists(token_path):
        return None

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    token_dir = os.path.dirname(token_path) or "."
    quarantined_path = os.path.join(token_dir, f"token.invalid.{timestamp}.json")
    suffix = 1
    while os.path.exists(quarantined_path):
        quarantined_path = os.path.join(token_dir, f"token.invalid.{timestamp}.{suffix}.json")
        suffix += 1

    try:
        os.replace(token_path, quarantined_path)
        log_func(f"백엔드: 기존 Google 토큰을 격리했습니다. 사유={reason_code}, 경로={quarantined_path}")
        auth_logger.warning(f"토큰 격리 완료 - 사유={reason_code}, 경로={quarantined_path}")
        return quarantined_path
    except Exception as exc:
        auth_logger.error(f"토큰 격리 실패 - 사유={reason_code}, 오류={exc}")
        log_func(f"경고: 기존 토큰 격리 실패 - {exc}")
        return None


def _raise_auth_action_required(log_func, auth_logger, reason_code, user_message, quarantined_token_path=None):
    auth_logger.warning(f"사용자 조치 필요 - 사유={reason_code}, 격리={quarantined_token_path}")
    log_func(f"오류: Google 재인증 필요 - 사유={reason_code}. {user_message}")
    raise GoogleAuthActionRequired(reason_code, user_message, quarantined_token_path=quarantined_token_path)


def run_interactive_auth(log_func, *, timeout_seconds=180):
    """사용자 브라우저를 이용해 대화형 인증을 수행한다."""
    auth_logger = setup_google_auth_logging()
    credentials_path, token_path = _resolve_auth_paths()

    if not _validate_credentials_path(credentials_path, log_func, auth_logger):
        return None

    credential_source = "사용자 지정 인증 파일" if USER_CREDENTIALS_FILE_STR and credentials_path == USER_CREDENTIALS_FILE_STR else "번들 인증 파일"
    auth_logger.info(f"대화형 인증 시작 - 신분증 경로: {credentials_path} ({credential_source})")

    try:
        log_func("백엔드: 브라우저 기반 Google 계정 재인증을 시작합니다.")
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        credentials = flow.run_local_server(port=0, timeout_seconds=timeout_seconds, open_browser=True)
        log_func("백엔드: ✅ Google 계정 인증에 성공했습니다!")
        auth_logger.info("대화형 인증 성공")
        _save_token(credentials, token_path, log_func, auth_logger)
        return credentials
    except Exception as exc:
        error_text = str(exc).lower()
        if "timed out" in error_text or isinstance(exc, TimeoutError):
            log_func("오류: Google 계정 인증 대기 시간이 초과되었습니다.")
            auth_logger.warning("대화형 인증 시간 초과")
            raise GoogleAuthActionRequired("timeout", "브라우저 승인 시간이 초과되었습니다. 다시 시도해 주세요.")
        log_func(f"오류: Google 계정 인증 중 오류 발생 - {exc}")
        auth_logger.error(f"대화형 인증 실패: {exc}", exc_info=True)
        raise GoogleAuthActionRequired("interactive_failed", f"브라우저 인증을 완료하지 못했습니다: {exc}")


def authenticate(log_func, *, interactive_allowed=False):
    """
    토큰 로드 및 자동 갱신까지만 수행한다.
    브라우저를 여는 작업은 사용자가 허용한 foreground 경로에서만 실행한다.
    """
    auth_logger = setup_google_auth_logging()
    credentials_path, token_path = _resolve_auth_paths()
    creds = None

    if not _validate_credentials_path(credentials_path, log_func, auth_logger):
        return None

    credential_source = "사용자 지정 인증 파일" if USER_CREDENTIALS_FILE_STR and credentials_path == USER_CREDENTIALS_FILE_STR else "번들 인증 파일"
    auth_logger.info(f"인증 시작 - 토큰 경로: {token_path}, 신분증 경로: {credentials_path} ({credential_source})")
    log_func(f"백엔드: Google 인증 확인 중... (토큰 저장소: {token_path})")

    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as exc:
            quarantined_path = quarantine_token_file(log_func, reason_code="token_parse_failed")
            user_message = f"기존 Google 토큰을 읽지 못했습니다. 다시 연결이 필요합니다. ({exc})"
            if interactive_allowed:
                return run_interactive_auth(log_func)
            _raise_auth_action_required(
                log_func,
                auth_logger,
                "missing_token",
                user_message,
                quarantined_token_path=quarantined_path,
            )

        try:
            expected_client_id = _get_expected_client_id(credentials_path)
            if expected_client_id and creds.client_id != expected_client_id:
                quarantined_path = quarantine_token_file(log_func, reason_code="client_id_mismatch")
                if interactive_allowed:
                    return run_interactive_auth(log_func)
                _raise_auth_action_required(
                    log_func,
                    auth_logger,
                    "client_id_mismatch",
                    "앱에 연결된 Google 인증 정보가 현재 설정과 다릅니다. 계정을 다시 연결해 주세요.",
                    quarantined_token_path=quarantined_path,
                )
        except GoogleAuthActionRequired:
            raise
        except Exception as exc:
            auth_logger.error(f"client_id 검증 실패: {exc}")

        if creds and creds.valid:
            log_func("백엔드: 저장된 Google 사용자 인증 정보(토큰) 로드 성공.")
            auth_logger.info("기존 토큰 파일 로드 성공")
            return creds

        if creds and creds.expired and creds.refresh_token:
            log_func("백엔드: 인증 정보(토큰) 만료됨. 자동 갱신 시도...")
            auth_logger.info("토큰 만료됨. 갱신 시도.")
            try:
                creds.refresh(Request())
                log_func("백엔드: 인증 정보(토큰) 갱신 성공.")
                auth_logger.info("토큰 갱신 성공")
                _save_token(creds, token_path, log_func, auth_logger)
                return creds
            except Exception as exc:
                quarantined_path = quarantine_token_file(log_func, reason_code="refresh_failed")
                if interactive_allowed:
                    return run_interactive_auth(log_func)
                _raise_auth_action_required(
                    log_func,
                    auth_logger,
                    "refresh_failed",
                    f"저장된 Google 인증 정보를 갱신하지 못했습니다. 계정을 다시 연결해 주세요. ({exc})",
                    quarantined_token_path=quarantined_path,
                )

        if interactive_allowed:
            return run_interactive_auth(log_func)
        _raise_auth_action_required(
            log_func,
            auth_logger,
            "missing_token",
            "Google 계정 연결이 필요합니다. 계정을 다시 연결한 뒤 시도해 주세요.",
        )

    if interactive_allowed:
        return run_interactive_auth(log_func)
    _raise_auth_action_required(
        log_func,
        auth_logger,
        "missing_token",
        "Google 계정 연결이 아직 완료되지 않았습니다. 계정을 연결한 뒤 다시 시도해 주세요.",
    )


def get_google_services(log_func, *, require_drive=True, interactive_allowed=False):
    """인증 후 Google 서비스 객체를 생성한다."""
    auth_logger = setup_google_auth_logging()
    auth_logger.info("Google 서비스 생성 시작")

    creds = authenticate(log_func, interactive_allowed=interactive_allowed)
    if not creds:
        log_func("오류: Google API 인증 실패. 서비스 객체를 생성할 수 없습니다.")
        auth_logger.error("Google API 인증 실패")
        return None

    services = {}
    try:
        log_func("백엔드: Google Docs 서비스 객체 생성 시도...")
        services["docs"] = build("docs", "v1", credentials=creds)
        if require_drive:
            log_func("백엔드: Google Drive 서비스 객체 생성 시도...")
            services["drive"] = build("drive", "v3", credentials=creds)
        log_func("백엔드: 필요한 Google 서비스 객체 생성 완료.")
        auth_logger.info(f"Google 서비스 객체 생성 완료 - drive 포함={require_drive}")
        return services
    except HttpError as error:
        log_func(f"오류: Google 서비스 객체 생성 중 API 오류 발생 - {error}")
        auth_logger.error(f"Google 서비스 객체 생성 중 API 오류: {error}")
        return None
    except Exception as exc:
        log_func(f"오류: Google 서비스 객체 생성 중 예외 발생 - {exc}")
        auth_logger.error(f"Google 서비스 객체 생성 중 예외: {exc}", exc_info=True)
        return None


def create_google_document(log_func, title, services=None):
    """현재 권한 범위에서 새 Google Docs 문서를 생성한다."""
    auth_logger = setup_google_auth_logging()
    google_services = services or get_google_services(log_func, require_drive=True, interactive_allowed=False)

    if not google_services or "drive" not in google_services:
        log_func("오류: Google Drive 서비스를 사용할 수 없어 새 문서를 만들 수 없습니다.")
        auth_logger.error("새 문서 생성 실패 - Drive 서비스 없음")
        return None

    document_title = (title or "").strip() or f"메신저 자동 기록 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    request_body = {
        "name": document_title,
        "mimeType": "application/vnd.google-apps.document",
    }

    try:
        created_document = google_services["drive"].files().create(
            body=request_body,
            fields="id, name, webViewLink",
        ).execute()
        log_func(f"백엔드: 새 Google Docs 문서 생성 완료 - {created_document.get('name')} ({created_document.get('id')})")
        auth_logger.info(f"새 Google Docs 문서 생성 완료: {created_document}")
        return created_document
    except HttpError as error:
        log_func(f"오류: 새 Google Docs 문서 생성 중 API 오류 발생 - {error}")
        auth_logger.error(f"새 Google Docs 문서 생성 API 오류: {error}")
        return None
    except Exception as error:
        log_func(f"오류: 새 Google Docs 문서 생성 중 예외 발생 - {error}")
        auth_logger.error(f"새 Google Docs 문서 생성 예외: {error}", exc_info=True)
        return None


def list_accessible_google_documents(log_func, services=None, page_size=20):
    """현재 권한 범위(drive.file)에서 접근 가능한 Google Docs 문서 목록을 조회한다."""
    auth_logger = setup_google_auth_logging()
    google_services = services or get_google_services(log_func, require_drive=True, interactive_allowed=False)

    if not google_services or "drive" not in google_services:
        log_func("오류: Google Drive 서비스를 사용할 수 없어 문서 목록을 가져올 수 없습니다.")
        auth_logger.error("문서 목록 조회 실패 - Drive 서비스 없음")
        return None

    try:
        response = google_services["drive"].files().list(
            q="mimeType='application/vnd.google-apps.document' and trashed=false",
            orderBy="modifiedTime desc",
            pageSize=page_size,
            spaces="drive",
            fields="files(id, name, webViewLink, modifiedTime)",
        ).execute()
        documents = response.get("files", [])
        log_func(f"백엔드: 접근 가능한 Google Docs 문서 {len(documents)}개 조회 완료.")
        auth_logger.info(f"접근 가능한 Google Docs 문서 조회 완료: {len(documents)}개")
        return documents
    except HttpError as error:
        log_func(f"오류: Google Docs 문서 목록 조회 중 API 오류 발생 - {error}")
        auth_logger.error(f"Google Docs 문서 목록 조회 API 오류: {error}")
        return None
    except Exception as error:
        log_func(f"오류: Google Docs 문서 목록 조회 중 예외 발생 - {error}")
        auth_logger.error(f"Google Docs 문서 목록 조회 예외: {error}", exc_info=True)
        return None
