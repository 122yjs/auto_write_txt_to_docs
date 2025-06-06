## 🚀 프로젝트 개선: Google 인증 과정 쉽게 만들기 (credentials.json 자동화)

안녕하세요! 10년 차 개발자이자 교육자입니다. 😊
초보 개발자분이 Google API 인증 과정에서 겪는 어려움을 시원하게 해결해 드리고자 합니다. 사용자가 복잡한 설정 없이 프로그램을 바로 사용할 수 있도록, 인증 파일을 프로그램에 포함하는 방법을 단계별로 아주 쉽게 설명해 드릴게요. 마치 블록 쌓기처럼 하나씩 따라오시면 됩니다!

최종 결과물은 사용자가 직접 `credentials.json` 파일을 만들거나 선택할 필요 없이, 프로그램 실행 후 뜨는 구글 로그인 창에서 '허용'만 클릭하면 되도록 만드는 것입니다.

핵심 용어는 초등학생도 이해할 수 있게 풀어서 설명해 드릴게요. 자, 시작해볼까요?

---

### 1단계: 목표 이해하기 및 개념 정리

우리가 하려는 것은 무엇이고, 왜 필요할까요?

**🤔 현재 문제점:**
*   프로그램을 사용하는 모든 사람이 각자 구글 클라우드 프로젝트를 만들고, API를 활성화하고, `credentials.json` 파일을 다운로드 받아서 프로그램에 등록해야 합니다.
*   개발자가 아닌 일반 사용자에게는 이 과정이 너무 복잡하고 어렵습니다. (마치 게임을 하려면 게임기를 직접 조립하라고 하는 것과 같아요!)

**✨ 개선 목표:**
*   개발자가 미리 `credentials.json` 파일(프로그램 신분증)을 만들어 프로그램 안에 '포함'(번들링)시켜 배포합니다.
*   사용자는 프로그램을 실행하고, 브라우저에서 본인의 구글 계정으로 로그인 후 "이 프로그램이 내 구글 문서에 접근하는 것을 허락합니다" 버튼만 누르면 됩니다.
*   사용자는 `credentials.json` 파일의 존재조차 몰라도 됩니다! (개발자가 미리 조립해둔 게임기를 받아서, 전원만 켜고 로그인해서 바로 게임하는 것과 같아요!)

**✅ 핵심 용어 쉽게 알기:**

1.  **Google API (구글 에이피아이):**
    *   우리 프로그램이 구글 문서(Google Docs)와 서로 대화할 수 있게 해주는 '통역사' 또는 '연결 통로'입니다. 구글 문서에게 "이 내용 좀 써줘!"라고 부탁하려면 API를 통해야 해요.
2.  **OAuth 2.0 (오어스 2.0):**
     *    안전한 '출입 허가' 절차입니다. 우리 프로그램이 사용자 대신 사용자의 구글 문서에 접근해야 하는데, 사용자 몰래 접근하면 안 되겠죠? 사용자에게 직접 "이 프로그램이 당신의 구글 문서에 접근해도 될까요?"라고 물어보고 '허락'을 받는 안전한 과정입니다.
3.  **`credentials.json` (크레덴셜.json / 자격증명 파일):**
    *   우리 **'프로그램'의 신분증**입니다. 구글에게 "안녕하세요, 저는 XXX 라는 프로그램입니다." 라고 자신을 소개하는 파일입니다.
    *   **중요:** 이것은 사용자의 신분증이 아니라, '프로그램 자체'의 신분증입니다.
    *   개발자가 딱 한 번 만들어서 프로그램에 넣어둡니다.
4.  **`token.json` (토큰.json / 인증 토큰 파일):**
    *   **사용자의 '출입 허가증'** 입니다.
    *   사용자가 브라우저에서 로그인하고 '허락' 버튼을 누르면, 구글이 발급해 주는 임시 출입증입니다.
    *   프로그램은 이 `token.json` (출입 허가증)을 가지고 있어야만 사용자의 구글 문서에 접근할 수 있습니다.
    *   이 파일은 프로그램에 포함되지 않고, 각 사용자 컴퓨터의 안전한 장소에 따로 저장됩니다. (사용자마다 출입 허가증은 달라야 하니까요!)
5.  **Scope (스코프 / 권한 범위):**
    *   프로그램이 사용자 대신 할 수 있는 일의 '범위'입니다. "구글 문서 읽기/쓰기만 허용", "구글 메일 읽기는 불허" 처럼 어디까지 허락할지 정하는 것입니다.
6.   **번들링 (Bundling):**
	*   프로그램 실행 파일, 아이콘, 설정 파일, 그리고 `credentials.json` 같은 필요한 파일들을 모두 모아 하나의 꾸러미로 '포장'하는 작업입니다. 사용자는 이 포장된 것 하나만 받아서 실행하면 됩니다. (예: PyInstaller)

**👍 개선 방식의 흐름:**
프로그램 실행 ➡️ 사용자 컴퓨터에 `token.json`(출입 허가증)이 있는지 확인 ➡️
*   **없거나 만료됨:** 프로그램에 포함된 `credentials.json`(프로그램 신분증) 사용 ➡️ 브라우저 열림 ➡️ 사용자 로그인 및 허락 ➡️ 구글이 `token.json`(출입 허가증) 발급 ➡️ 사용자 컴퓨터에 `token.json` 저장 ➡️ 출입 허가증으로 구글 문서 접근!
*   **있고 유효함:** 저장된 `token.json`(출입 허가증)을 바로 사용 ➡️ 구글 문서 접근! (다시 로그인/허락 필요 없음)

---

### 2단계: 사전 준비 (개발자가 할 일)

코드를 수정하기 전에 딱 한 가지, 개발자가 해야 할 일이 있습니다.

1.  **Google Cloud Console 접속:** [https://console.cloud.google.com/](https://console.cloud.google.com/)
2.  **프로젝트 선택 또는 생성:** API를 사용할 프로젝트를 만듭니다.
3.  **API 및 서비스 활성화:** 'API 및 서비스' > '라이브러리' 에서 `Google Docs API`를 찾아 '사용 설정' 합니다.
4.  **OAuth 동의 화면 구성:** 사용자에게 허락을 구할 때 보여줄 화면(앱 이름, 로고 등)을 설정합니다.
5.  **사용자 인증 정보 만들기:**
    *   'API 및 서비스' > '사용자 인증 정보' > '+ 사용자 인증 정보 만들기' > 'OAuth 클라이언트 ID' 선택
    *   **애플리케이션 유형:** ⭐**데스크톱 앱**⭐ 을 반드시 선택합니다. (가장 중요!)
    *   이름 입력 후 '만들기' 클릭.
6.  **`credentials.json` 다운로드:**
    *   생성된 '데스크톱 앱' 클라이언트 ID 목록에서 다운로드 버튼(⬇️)을 눌러 JSON 파일을 받습니다.
7.  **파일 이름 변경 및 배치:**
    *   다운로드한 파일 이름을 `developer_credentials.json` 으로 변경합니다.
    *   프로젝트 폴더 안에 `src/auto_write_txt_to_docs/assets/` 폴더를 만들고, 그 안에 `developer_credentials.json` 파일을 넣습니다.
    ```
     (프로젝트 루트)
     └── src
         └── auto_write_txt_to_docs
             ├── assets  <-- 이 폴더 생성
             │   └── developer_credentials.json  <-- 여기에 파일 넣기!
             ├── __init__.py
             ├── backend_processor.py
             ├── google_auth.py
             ├── main_gui.py
             └── path_utils.py
    ```

이제 프로그램의 '신분증' 준비가 끝났습니다! 코드를 수정하러 가볼까요?

---

### 3단계: 코드 수정 - `path_utils.py` (주소 알려주기)

프로그램에게 새로 넣어둔 `developer_credentials.json` 파일(프로그램 신분증)이 어디 있는지 정확한 '주소'를 알려줘야 합니다.

*   **목표:** `developer_credentials.json` 파일의 경로를 찾아주는 함수 만들기. (개발 환경과, 나중에 exe 파일로 포장(번들링)했을 때 모두 작동하도록!)

```python
# path_utils.py
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
     elif sys.platform == "darwin": # macOS
         base_dir = Path.home() / "Library" / "Application Support"
     else: # Linux / other
         base_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
     config_dir = base_dir / app_name
     try:
         config_dir.mkdir(parents=True, exist_ok=True) # 폴더가 없으면 만들기
     except OSError as e:
         logging.warning(f"사용자 설정 디렉토리 생성 실패 ({config_dir}): {e}. 기본 경로 사용.")
         return get_project_root() # 실패 시 프로젝트 루트 반환
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
CONFIG_FILE = get_safe_config_path("config.json", use_user_dir=True) # 설정 파일은 사용자 폴더에
CACHE_FILE = get_safe_cache_path("line_cache.json", use_user_dir=True) # 캐시 파일도 사용자 폴더에
PROCESSED_STATE_FILE = get_safe_cache_path("processed_state.json", use_user_dir=True) # 처리 상태도 사용자 폴더에
LOG_DIR = PROJECT_ROOT / "logs" # 로그는 프로그램 폴더에 (또는 사용자 폴더로 변경 가능)

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
TOKEN_FILE_PATH = get_safe_cache_path("token.json", use_user_dir=True) # ⭐token.json은 반드시 사용자 폴더에!⭐
TOKEN_FILE_STR = str(TOKEN_FILE_PATH)
```
**💡 설명:**
*   `get_bundled_credentials_path` 함수를 새로 만들었습니다.
*   이 함수는 프로그램이 `.py`로 실행 중인지, 아니면 `.exe` 파일로 묶여서(번들링되어) 실행 중인지를 확인(`sys._MEIPASS`)합니다.
*   각 상황에 맞게 `developer_credentials.json` 파일이 있는 정확한 '주소'를 찾아서 돌려줍니다.
*   `BUNDLED_CREDENTIALS_FILE_STR` 변수에 이 주소를 저장해서 다른 파일들이 쉽게 가져다 쓸 수 있게 합니다.
*   `token.json`(사용자 출입 허가증)은 프로그램 폴더가 아닌, 각 사용자의 개인 폴더(`AppData` 등)에 안전하게 저장되도록 `get_safe_cache_path("token.json", use_user_dir=True)`를 사용하고 `TOKEN_FILE_STR` 변수에 저장했습니다.

---

### 4단계: 코드 수정 - `google_auth.py` (신분증 사용하기)

이제 인증을 담당하는 파일에서, GUI로부터 경로를 입력받는 대신 `path_utils.py`가 알려준 '주소'에 있는 프로그램 신분증 파일을 사용하도록 수정합니다.

*   **목표:**
    *   `authenticate` 함수 등에서 `credentials_path` 인자(파라미터) 제거.
    *   `path_utils`에서 정의한 `BUNDLED_CREDENTIALS_FILE_STR` (프로그램 신분증 주소)와 `TOKEN_FILE_STR` (사용자 출입 허가증 주소) 사용.

```python
# google_auth.py
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
    from .path_utils import BUNDLED_CREDENTIALS_FILE_STR, TOKEN_FILE_STR
except ImportError:
    # path_utils 파일이 없는 비상 상황 대비
    print("오류: path_utils.py 파일을 찾을 수 없습니다. Google 인증이 작동하지 않습니다.")
    BUNDLED_CREDENTIALS_FILE_STR = None
    TOKEN_FILE_STR = 'token.json' # 임시 경로

# 프로그램이 구글 문서에 접근할 수 있도록 '권한 범위(Scope)' 설정
SCOPES = ['https://www.googleapis.com/auth/documents']

# 로깅 설정 (그대로 유지)
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
    creds = None # 출입 허가증을 담을 변수 초기화

    # ⭐ 1. 프로그램 신분증 파일 주소 가져오기 (path_utils에서) ⭐
    credentials_path = BUNDLED_CREDENTIALS_FILE_STR
    # ⭐ 2. 사용자 출입 허가증 저장 파일 주소 가져오기 (path_utils에서) ⭐
    token_path = TOKEN_FILE_STR

    # 신분증 파일이 실제로 존재하는지 확인
    if not credentials_path or not os.path.exists(credentials_path):
         error_msg = f"오류: 프로그램에 포함된 인증 파일({credentials_path})을 찾을 수 없습니다. 개발자에게 문의하세요."
         log_func(error_msg)
         auth_logger.error(error_msg)
         return None # 신분증 없이는 진행 불가

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
            creds = None # 실패 시 없는 것으로 간주

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
                 creds.refresh(Request()) # 갱신!
                 log_func("백엔드: 인증 정보(토큰) 갱신 성공.")
                 auth_logger.info("토큰 갱신 성공.")
            except Exception as e:
                 log_func(f"경고: 인증 정보(토큰) 갱신 실패: {e}. 다시 인증이 필요합니다.")
                 auth_logger.warning(f"토큰 갱신 실패: {e}")
                 creds = None # 갱신 실패 시, 새로 발급받아야 함

        # 4-2. 갱신에 실패했거나, 애초에 출입 허가증이 없으면 -> 사용자 허락받기(새 인증)
        if not creds:
            auth_logger.info("새로운 인증 플로우 시작 (사용자 브라우저 확인 필요)")
            try:
                log_func("백엔드: ⚠️ Google 계정 인증 필요! 웹 브라우저 창을 확인하고 로그 및 접근을 '허용' 해주세요. ⚠️")
                # ⭐ 프로그램 신분증(credentials_path)을 이용해 사용자 허락 절차(flow) 시작 ⭐
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                # 브라우저를 열고, 사용자가 허락할 때까지 기다림 (port=0 은 사용 가능한 아무 포트나 사용)
                creds = flow.run_local_server(port=0)
                log_func("백엔드: ✅ Google 계정 사용자 인증 성공!")
                auth_logger.info("새로운 사용자 인증 완료")
            except Exception as e:
                log_func(f"오류: Google 계정 인증 중 오류 발생 - {e}")
                auth_logger.error(f"새로운 인증 실패: {e}", exc_info=True)
                return None # 인증 실패

        # ⭐ 5. 새로 발급/갱신된 출입 허가증(creds)을 token.json 파일에 저장 ⭐
        # (다음에 실행할 때는 다시 허락받지 않기 위해)
        try:
            # 토큰 파일이 저장될 폴더가 없으면 만들기 (path_utils가 해주지만 안전하게)
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'w', encoding='utf-8') as token:
                token.write(creds.to_json()) # 출입 허가증 정보를 JSON 형태로 파일에 쓰기
            log_func(f"백엔드: 새 인증 정보(토큰) 저장 완료: {token_path}")
            auth_logger.info(f"토큰 저장 완료: {token_path}")
        except Exception as e:
            log_func(f"경고: 새 인증 정보({token_path}) 저장 실패 - {e}")
            auth_logger.error(f"토큰 저장 실패: {e}")
    else:
         # 3번에서 로드한 기존 출입 허가증이 유효한 경우
        auth_logger.info("기존 토큰이 유효함.")
        log_func("백엔드: 기존 Google 인증 정보(토큰)가 유효합니다.")


    return creds # 최종적으로 유효한 출입 허가증 반환

# ⭐ credentials_path 인자 제거 ⭐
def get_google_services(log_func):
    """ 인증을 수행하고, 구글 문서 서비스 객체(API 통로)를 만들어 반환합니다. """
    auth_logger = setup_google_auth_logging()
    auth_logger.info("Google 서비스 생성 시작")

    # ⭐ authenticate() 함수 호출 시 credentials_path 안 넘김 ⭐
    creds = authenticate(log_func) # 위에서 만든 인증 함수 호출 (출입 허가증 받아오기)
    if not creds:
        # 출입 허가증 받기 실패
        log_func("오류: Google API 인증 실패. 서비스 객체를 생성할 수 없습니다.")
        auth_logger.error("Google API 인증 실패")
        return None

    auth_logger.info("Google 인증 성공, 서비스 객체 생성 시도")
    services = {}
    try:
        log_func("백엔드: Google Docs 서비스 연결 중...")
        # 받아온 출입 허가증(creds)을 이용해서 구글 문서 서비스와 연결 통로(docs) 만들기
        services['docs'] = build('docs', 'v1', credentials=creds)
        log_func("백엔드: Google Docs 서비스 연결 완료.")
        auth_logger.info("Google Docs 서비스 객체 생성 완료")
        return services
    except HttpError as error:
        log_func(f"오류: Google 서비스 연결 중 API 오류 발생 - {error}")
        auth_logger.error(f"Google 서비스 객체 생성 중 API 오류: {error}", exc_info=True)
        return None
    except Exception as e:
        log_func(f"오류: Google 서비스 연결 중 예외 발생 - {e}")
        auth_logger.error(f"Google 서비스 객체 생성 중 예외: {e}", exc_info=True)
        return None
```
**💡 설명:**
*   함수 `authenticate`와 `get_google_services`에서 `credentials_path`를 입력받는 부분을 모두 제거했습니다.
*   `path_utils`에서 가져온 `BUNDLED_CREDENTIALS_FILE_STR`(신분증 주소)와 `TOKEN_FILE_STR`(출입 허가증 주소)를 직접 사용합니다.
*   사용자 허락이 필요한 경우, `InstalledAppFlow.from_client_secrets_file`에 `credentials_path` (우리가 넣어준 프로그램 신분증 주소)를 사용하여 인증 절차를 시작합니다.
*   인증 성공 후 발급된 `token.json`(출입 허가증)은 `TOKEN_FILE_STR` 경로(사용자 개인 폴더)에 안전하게 저장됩니다.

---
### 5단계: 코드 수정 - `backend_processor.py` (연결 고리 수정)

백엔드 처리 부분에서 `google_auth.py`의 함수를 호출할 때, 더 이상 `credentials_path`를 넘겨주지 않도록 수정합니다.

*   **목표:** `get_google_services` 함수 호출 방식 변경.

```python
# backend_processor.py

# ... (다른 import 및 코드들은 그대로 유지) ...
import os
import logging
# watchdog, queue 등 필요한 import

# ⭐ google_auth 모듈 임포트 ⭐
try:
    # google_auth 에서 get_google_services 함수 가져오기
    from .google_auth import get_google_services
    from .path_utils import CACHE_FILE_STR, PROCESSED_STATE_FILE_STR # 캐시 파일 경로 등
except ImportError:
     print("오류: google_auth 또는 path_utils 모듈을 찾을 수 없습니다.")
     get_google_services = None
     CACHE_FILE_STR = 'line_cache.json'
     PROCESSED_STATE_FILE_STR = 'processed_state.json'


# ... (전역 변수, 로깅, 캐시 로드/저장, EventHandler 등 기존 코드 유지) ...
# 예: setup_backend_logging, load_line_cache, save_line_cache, TxtFileEventHandler, process_file 등


# --- 메인 모니터링 함수 ---
def run_monitoring(config, log_func_threadsafe, stop_event):
    """ 백그라운드에서 폴더 감시 및 파일 처리를 실행하는 메인 루프 """
    watch_folder = config.get('watch_folder')
    # ⭐ config에서 credentials_path 가져오는 부분 제거 ⭐
    # credentials_path = config.get('credentials_path') # 이제 필요 없음!

    # 백엔드 로깅 시스템 초기화 (기존 코드 유지)
    backend_logger = logging.getLogger('backend') # setup_backend_logging() 등으로 초기화 되었다고 가정
    backend_logger.info(f"감시 시작 - 폴더: {watch_folder}")
    log_func_threadsafe(f"백엔드: 감시 시작 - 폴더: {watch_folder}")

    # 캐시 및 상태 로드 (기존 코드 유지)
    # load_line_cache(log_func_threadsafe)
    # load_processed_state(log_func_threadsafe)
    backend_logger.info("캐시 및 처리 상태 로드 완료")

    google_services = None
    # Google API 서비스 로드
    if get_google_services: # google_auth.py 가 성공적으로 import 되었는지 확인
        try:
            backend_logger.info("Google API 서비스 로드 시도")
            # ⭐ get_google_services 호출 시 credentials_path 인자 제거! ⭐
            # 이전: google_services = get_google_services(credentials_path, log_func_threadsafe)
            google_services = get_google_services(log_func_threadsafe) # 이제 로그 함수만 넘겨줌

            if google_services and 'docs' in google_services:
                log_func_threadsafe("백엔드: Google Docs 서비스 준비 완료.")
                backend_logger.info("Google Docs 서비스 준비 완료")
                 # Docs ID 유효성 검사 코드 (필요 시 유지)
            else:
                 log_func_threadsafe("경고: Google 서비스 로드 실패 (인증 오류 등). Google Docs 기록 기능이 비활성화됩니다.")
                 backend_logger.error("Google 서비스 로드 실패")
        except Exception as e:
            log_func_threadsafe(f"오류: Google 서비스 초기화 중 예외 발생 - {e}")
            backend_logger.error(f"Google 서비스 초기화 예외: {e}", exc_info=True)
    else:
         log_func_threadsafe("경고: Google 연동 모듈 로드 실패. Google Docs 기록 기능이 비활성화됩니다.")

    # 폴더 감시자 설정 및 실행 (기존 코드 유지)
    # ... observer, event_handler 설정 ...
    # ... try...except...finally 블록 (observer.start(), while not stop_event.is_set(), time.sleep, observer.stop(), observer.join()) ...
    # ... process_file 호출 시 google_services 객체는 그대로 넘겨줌 ...
    # finally:
    #    save_line_cache(log_func_threadsafe) # 종료 전 저장
    #    save_processed_state(log_func_threadsafe)

```
**💡 설명:**
*   GUI에서 설정한 `config` 딕셔너리에서 `credentials_path`를 읽어오는 코드를 제거했습니다.
*   `get_google_services` 함수를 호출할 때, 더 이상 `credentials_path`를 넘겨주지 않습니다. 이제 `google_auth.py`가 스스로 `path_utils.py`를 통해 경로를 알아내기 때문입니다.

---
### 6단계: 코드 수정 - `main_gui.py` (화면 정리 및 설정 변경)

사용자 화면(GUI)에서 `credentials.json` 파일을 선택하는 입력창과 버튼을 모두 없애고, 설정 저장/불러오기 기능에서도 해당 항목을 제거합니다.

*   **목표:**
    *   Credentials 파일 선택 UI 요소(Label, Entry, Button) 제거.
    *   `self.credentials_path` 변수 제거.
    *   `save_config`, `load_config`에서 `credentials_path` 항목 제거.
    *   `start_monitoring`, `validate_inputs`에서 `credentials_path` 관련 로직 제거.

```python
# main_gui.py

# ... (기존 임포트 유지: tkinter, customtkinter, os, json, threading, queue, logging, pystray 등) ...
import customtkinter as ctk
import os
import json
import threading
import queue
import sys
from tkinter import messagebox, filedialog

# path_utils에서 설정 파일, 로그 폴더 주소 가져오기
from src.auto_write_txt_to_docs.path_utils import PROJECT_ROOT_STR, CONFIG_FILE_STR, LOG_DIR_STR
# 백엔드 실행 함수 가져오기
try:
     from src.auto_write_txt_to_docs.backend_processor import run_monitoring
except ImportError:
     print("백엔드 모듈 로드 실패")
     run_monitoring = None

# ... (extract_google_id_from_url, get_icon_path 등 유틸 함수 유지) ...

class MessengerDocsApp:
    def __init__(self, root):
        # ... (root, title, geometry, appearance 설정 유지) ...
        self.root = root
        self.root.title("메신저 Docs 자동 기록")

        # --- 변수 선언 ---
        self.watch_folder = ctk.StringVar()
        # ⭐ self.credentials_path 변수 제거 ⭐
        # self.credentials_path = ctk.StringVar() # 이제 GUI에서 입력받지 않음!
        self.docs_input = ctk.StringVar()

        # ... (is_monitoring, thread, stop_event, log_queue, tray, status_var 등 유지) ...
        self.is_monitoring = False
        self.log_queue = queue.Queue()
        self.status_var = ctk.StringVar(value="준비")


        # 로깅 설정 (유지)
        self.setup_logging()

        # 설정 변수 변경 감지 추적
        self.watch_folder.trace('w', self.on_setting_changed)
        # ⭐ self.credentials_path 추적 제거 ⭐
        # self.credentials_path.trace('w', self.on_setting_changed)
        self.docs_input.trace('w', self.on_setting_changed)
        self.settings_changed = False

        # ... (아이콘, 위젯 생성, 설정 로드, 큐 처리, 트레이 설정 등 유지) ...
        self.create_widgets()
        self.load_config()
        self.settings_changed = False # 로드 후 초기화
        self.root.after(100, self.process_log_queue)
        # ...

    # ... (setup_logging, log, log_threadsafe, process_log_queue, on_setting_changed, update_status 등 유지) ...

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)
        # ... (상태 표시 프레임, 설정 프레임 Label 등 유지) ...
        settings_frame = ctk.CTkFrame(main_frame)
        settings_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(settings_frame, text="설정", font=ctk.CTkFont(weight="bold")).pack(pady=(5,10))


        # 감시 폴더 설정 (⭐ 그대로 유지 ⭐)
        folder_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        folder_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(folder_frame, text="감시 폴더:", width=120).pack(side="left", padx=(0,5))
        ctk.CTkEntry(folder_frame, textvariable=self.watch_folder).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(folder_frame, text="폴더 선택...", width=80, command=self.browse_folder).pack(side="left", padx=(5,0))
        # ... (폴더 열기 버튼 등)

        # ⭐⭐⭐ Credentials 파일 설정 UI 전체 제거 ⭐⭐⭐
        # cred_frame = ctk.CTkFrame(settings_frame, fg_color="transparent"); cred_frame.pack(fill="x", padx=10, pady=5)
        # ctk.CTkLabel(cred_frame, text="Credentials 파일:", width=120).pack(side="left", padx=(0,5))
        # ctk.CTkEntry(cred_frame, textvariable=self.credentials_path).pack(side="left", fill="x", expand=True, padx=5)
        # ctk.CTkButton(cred_frame, text="파일 선택...", width=80, command=self.browse_credentials).pack(side="left", padx=(5,0))
        # ... (파일 열기 버튼 등)
        # ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐

        # Google Docs URL/ID 설정 (⭐ 그대로 유지 ⭐)
        docs_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        docs_frame.pack(fill="x", padx=10, pady=(5,10))
        ctk.CTkLabel(docs_frame, text="Google Docs URL/ID:", width=120).pack(side="left", padx=(0,5))
        ctk.CTkEntry(docs_frame, textvariable=self.docs_input).pack(side="left", fill="x", expand=True, padx=5)

        # ... (제어 버튼, 로그 프레임 등 나머지 UI 유지) ...
        control_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        control_frame.pack(pady=10, fill="x")
        self.start_button = ctk.CTkButton(control_frame, text="감시 시작", command=self.start_monitoring) # command 확인
        self.stop_button = ctk.CTkButton(control_frame, text="감시 중지", command=self.stop_monitoring, state="disabled")
        ctk.CTkButton(control_frame, text="설정 저장", command=self.save_config).pack(side="right", padx=10)
        self.start_button.pack(side="left", padx=10)
        self.stop_button.pack(side="left", padx=10)


    def browse_folder(self):
         # 폴더 선택 기능 (유지)
         folder = filedialog.askdirectory(parent=self.root)
         if folder:
             self.watch_folder.set(folder)

    # ⭐ browse_credentials 함수 완전히 제거 ⭐
    # def browse_credentials(self): ...

    # ⭐ save_config 함수 수정: credentials_path 저장 안 함 ⭐
    def save_config(self):
        config_data = {
            "watch_folder": self.watch_folder.get(),
            # "credentials_path": self.credentials_path.get(), # 👈 저장 제거
            "docs_input": self.docs_input.get()
        }
        try:
            # path_utils 의 CONFIG_FILE_STR 사용
            with open(CONFIG_FILE_STR, 'w', encoding='utf-8') as f:
                 json.dump(config_data, f, indent=4, ensure_ascii=False)
            self.log("설정 저장 완료.")
            self.settings_changed = False
        except Exception as e:
             messagebox.showerror("저장 오류", f"설정 저장 실패:\n{e}", parent=self.root)
             self.log(f"오류: 설정 저장 실패 - {e}")

    # ⭐ load_config 함수 수정: credentials_path 불러오지 않음 ⭐
    def load_config(self):
         # path_utils 의 CONFIG_FILE_STR 사용
        if os.path.exists(CONFIG_FILE_STR):
            try:
                with open(CONFIG_FILE_STR, 'r', encoding='utf-8') as f:
                     config_data = json.load(f)
                self.watch_folder.set(config_data.get("watch_folder", ""))
                # self.credentials_path.set(config_data.get("credentials_path", "")) # 👈 로드 제거
                self.docs_input.set(config_data.get("docs_input", ""))
                self.log("저장된 설정 로드 완료.")
            except Exception as e:
                 self.log(f"경고: 설정 파일 로드 실패 - {e}")
        else:
             self.log(f"저장된 설정 파일 없음: {os.path.basename(CONFIG_FILE_STR)}")


    # ⭐ validate_inputs 함수 수정: credentials_path 검사 안 함 ⭐
    def validate_inputs(self):
        """입력값 유효성 검사"""
        watch_folder = self.watch_folder.get().strip()
        # credentials_path = self.credentials_path.get().strip() # 👈 제거
        docs_input_val = self.docs_input.get().strip()
        errors = []

        # 감시 폴더 검사 (유지)
        if not watch_folder: errors.append("감시 폴더를 선택해주세요.")
        elif not os.path.isdir(watch_folder): errors.append(f"감시 폴더가 존재하지 않거나 폴더가 아닙니다: {watch_folder}")

        # ⭐ Credentials 파일 검사 로직 전체 제거 ⭐
        # if not credentials_path: errors.append("Credentials 파일을 선택해주세요.")
        # elif not os.path.isfile(credentials_path): errors.append(f"Credentials 파일이 존재하지 않거나 파일이 아닙니다: {credentials_path}")
        # ...

        # Google Docs URL/ID 검사 (유지)
        if not docs_input_val:
             errors.append("Google Docs URL 또는 ID를 입력해주세요.")
        # else: ... (ID 추출 및 유효성 검사 로직 유지)

        return errors

    # ⭐ start_monitoring 함수 수정: config 에 credentials_path 안 넣음 ⭐
    def start_monitoring(self):
         if not run_monitoring:
              messagebox.showerror("실행 오류", "백엔드 모듈을 로드할 수 없습니다.", parent=self.root)
              return

         validation_errors = self.validate_inputs() # 수정된 검사 함수 호출
         if validation_errors:
              # 에러 메시지 표시 (유지)
              messagebox.showerror("입력 오류", "\n".join(validation_errors), parent=self.root)
              return

         # ... (입력값 가져오기, ID 추출 등 유지) ...
         watch_folder = self.watch_folder.get().strip()
         docs_input_val = self.docs_input.get().strip()
         # docs_id = extract_google_id_from_url(docs_input_val) # ID 추출 함수 필요

         self.log("감시 시작 요청...")
         self.update_status("감시 시작 중...")
         self.is_monitoring = True
         self.stop_event.clear()

         # ⭐ 백엔드로 넘겨줄 설정(config)에서 credentials_path 제거 ⭐
         current_config = {
             "watch_folder": watch_folder,
             # "credentials_path": self.credentials_path.get().strip(), # 👈 제거
             "docs_id": "YOUR_DOCS_ID" # docs_id # 👈 docs_id는 필요함!
         }

         # 백엔드 스레드 시작 (유지)
         self.monitoring_thread = threading.Thread(
             target=run_monitoring,
             # ⭐ run_monitoring 은 config, log_func, stop_event 를 받음 ⭐
             args=(current_config, self.log_threadsafe, self.stop_event),
             daemon=True
         )
         self.monitoring_thread.start()

         # 버튼 상태 변경 등 (유지)
         self.start_button.configure(state="disabled")
         self.stop_button.configure(state="normal")
         # self.disable_settings_widgets() # 위젯 비활성화 함수도 credentials 부분 제거 확인
         self.update_status("감시 중")


    # ⭐ disable_settings_widgets, enable_settings_widgets 함수 수정 ⭐
    # : Credentials 관련 위젯을 비활성화/활성화 하는 코드가 있다면 모두 제거해야 합니다.
    # (create_widgets에서 이미 UI를 제거했으므로, 이 함수들 내에서 해당 프레임/위젯에 접근하려 하면 오류 발생)

    # ... (stop_monitoring, hide_window, show_window, quit_app, on_closing, 트레이 관련 함수 등 유지) ...

# --- 애플리케이션 실행 --- (유지)
if __name__ == "__main__":
     # 로그 폴더 생성 시도 (path_utils 경로 사용)
     try:
         os.makedirs(LOG_DIR_STR, exist_ok=True)
     except Exception as e:
         print(f"로그 폴더 생성 실패: {e}")
     root = ctk.CTk()
     app = MessengerDocsApp(root)
     root.mainloop()

```
**💡 설명:**
*   화면 구성(`create_widgets`), 변수(`__init__`), 파일 선택 함수(`browse_credentials`), 설정 저장/로드(`save_config`, `load_config`), 유효성 검사(`validate_inputs`), 감시 시작(`start_monitoring`) 등 모든 곳에서 `credentials_path`와 관련된 부분을 깨끗하게 제거했습니다.
*   이제 사용자는 화면에서 Credentials 파일과 관련된 어떤 것도 볼 수 없습니다!

---
### 7단계: 번들링 (EXE 파일 만들기 - 참고)

나중에 PyInstaller 등으로 실행 파일(`.exe`)을 만들 때, `assets` 폴더(우리가 `developer_credentials.json`을 넣어둔 곳)가 실행 파일 안에 포함되도록 옵션을 주어야 합니다. 그래야 `path_utils.py`의 `sys._MEIPASS` 부분이 제대로 작동합니다.

*   **PyInstaller 명령어 예시:**
    ```bash
    pyinstaller --windowed --onefile \
    --add-data "src/auto_write_txt_to_docs/assets:assets" \
    --add-data "assets/icon.png:assets" \
     main_gui.py
    ```
    *   `--add-data "원본폴더경로;묶음내부경로"` : `src/.../assets` 폴더 전체를 실행 파일 내부의 `assets` 라는 이름의 폴더로 포함시키라는 뜻입니다. (세미콜론`;` 대신 콜론`:`을 사용하는 OS도 있습니다. 보통 Windows는 `;`, Linux/Mac은 `:`)

---
### 🎉 마무리

축하합니다! 이제 사용자가 훨씬 편리하게 사용할 수 있는 프로그램이 되었습니다.
변경된 흐름을 다시 한번 정리해 볼까요?

1.  사용자가 `감시 시작` 버튼 클릭.
2.  `backend_processor`의 `run_monitoring` 시작.
3.  `google_auth`의 `get_google_services` 호출.
4.  `authenticate` 함수가 `path_utils`를 통해 `token.json`(사용자 출입 허가증) 위치 확인.
5.  `token.json`이 없거나 만료되었다면, `path_utils`를 통해 `developer_credentials.json`(프로그램 신분증) 위치 확인.
6.  신분증을 이용해 브라우저 창을 띄우고 사용자에게 로그인 및 '허용' 요청.
7.  사용자가 허용하면, `token.json`을 발급받아 사용자 폴더에 저장.
8.  유효한 `token.json`을 이용해 구글 문서 서비스에 접속.
9.  감시 및 문서 쓰기 작업 시작!

이제 사용자는 복잡한 설정 없이, 프로그램 첫 실행 시 브라우저에서 '허용' 버튼 클릭 한 번으로 모든 인증 과정을 마칠 수 있습니다.

어떠신가요? 차근차근 따라오니 어렵지 않죠? 😉
개발 과정에서 궁금한 점이 있다면 언제든지 다시 질문해주세요! 항상 응원합니다!
