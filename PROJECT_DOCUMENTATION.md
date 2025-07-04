# Project Documentation: auto_write_txt_to_docs

## 1. 프로젝트 개요 (Project Overview)

이 프로젝트는 지정된 폴더에 있는 텍스트 파일 (`.txt`)의 내용을 읽어와 구글 문서(Google Docs)에 자동으로 작성해주는 파이썬 애플리케이션입니다. 사용자는 GUI(그래픽 사용자 인터페이스)를 통해 손쉽게 폴더를 선택하고, 구글 인증을 거쳐 텍스트 파일의 내용을 구글 문서에 추가할 수 있습니다.

주요 목표는 반복적인 복사-붙여넣기 작업을 자동화하여 사용자의 생산성을 높이는 것입니다.

## 2. 주요 기능 (Features)

*   **GUI 제공:** `Tkinter` 라이브러리를 사용하여 사용자가 쉽게 프로그램을 조작할 수 있는 GUI를 제공합니다.
*   **폴더 선택:** 사용자는 GUI를 통해 텍스트 파일이 들어있는 폴더를 직접 선택할 수 있습니다.
*   **구글 인증:** `Google Cloud Platform`의 `OAuth 2.0`을 사용하여 안전하게 구글 계정 인증을 수행합니다. 최초 인증 후에는 인증 정보가 저장되어 다음 실행 시에는 자동으로 인증됩니다.
*   **자동 텍스트 처리:** 지정된 폴더 내의 모든 `.txt` 파일을 감지하고, 각 파일의 내용을 읽어옵니다.
*   **구글 문서에 내용 추가:** 읽어온 텍스트 파일의 내용을 지정된 구글 문서의 맨 아래에 순서대로 추가합니다.
*   **중복 방지:** 이미 처리된 텍스트 라인은 기록하여, 프로그램 재실행 시 중복해서 구글 문서에 추가되는 것을 방지합니다.
*   **로그 기능:** 프로그램의 작동 상태, 오류 등을 로그 파일에 기록하여 문제가 발생했을 때 원인을 파악하기 용이하게 합니다.

## 3. 시작하기 (Getting Started)

### 3.1. 사전 준비 (Prerequisites)

*   **Python 3.x:** 파이썬이 설치되어 있어야 합니다.
*   **Google Cloud Platform (GCP) 프로젝트:** 구글 API를 사용하기 위한 GCP 프로젝트가 필요합니다.
*   **OAuth 2.0 클라이언트 ID:** GCP 프로젝트에서 `OAuth 2.0 클라이언트 ID`를 생성하고, `credentials.json` (또는 `developer_credentials.json`) 파일을 다운로드해야 합니다. 이 파일에는 클라이언트 ID, 클라이언트 시크릿 등 인증에 필요한 정보가 들어있습니다.
    *   **API 사용 설정:** GCP 프로젝트에서 `Google Docs API`와 `Google Drive API`를 활성화해야 합니다.

### 3.2. 설치 (Installation)

1.  **프로젝트 복제:**
    ```bash
    git clone https://github.com/your-repository/auto_write_txt_to_docs.git
    cd auto_write_txt_to_docs
    ```

2.  **필요한 라이브러리 설치:**
    `requirements.txt` 파일에 명시된 라이브러리들을 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```
    설치되는 주요 라이브러리는 다음과 같습니다.
    *   `google-api-python-client`: 구글 API를 사용하기 위한 클라이언트 라이브러리
    *   `google-auth-httplib2`: 구글 인증 관련 라이브러리
    *   `google-auth-oauthlib`: OAuth 2.0 인증 흐름을 도와주는 라이브러리
    *   `requests`: HTTP 요청을 보내기 위한 라이브러리

### 3.3. 설정 (Configuration)

1.  **구글 인증 정보 파일:**
    다운로드한 `OAuth 2.0 클라이언트 ID` 파일의 이름을 `developer_credentials.json`으로 변경하고, `src/auto_write_txt_to_docs/assets/` 폴더 안에 위치시킵니다.

2.  **설정 파일 (`config.json`):**
    프로젝트 루트 디렉토리에 있는 `config.json.example` 파일의 복사본을 만들어 `config.json`으로 이름을 변경하고, 아래와 같이 내용을 수정합니다.

    ```json
    {
        "DOCUMENT_ID": "여기에_구글_문서_ID를_입력하세요",
        "TARGET_DIR": "C:/Users/YourUser/Desktop/MyTxtFiles",
        "CACHE_FILE": "added_lines_cache.json",
        "LOG_FILE": "logs/app.log"
    }
    ```
    *   `DOCUMENT_ID`: 텍스트를 추가할 구글 문서의 ID입니다. 구글 문서 URL의 `.../d/` 와 `/edit` 사이의 긴 문자열입니다.
    *   `TARGET_DIR`: 텍스트 파일을 읽어올 폴더의 경로입니다.
    *   `CACHE_FILE`: 중복 추가를 방지하기 위해 사용되는 캐시 파일의 이름입니다.
    *   `LOG_FILE`: 로그를 기록할 파일의 경로입니다.

## 4. 작동 방식 (How it Works - Architecture)

이 프로젝트는 크게 **GUI 부분**과 **백엔드 로직 부분**으로 나뉩니다.

### 4.1. `main_gui.py` - GUI

*   **역할:** 사용자와의 상호작용을 담당하는 진입점(Entry Point)입니다.
*   **주요 기능:**
    *   `Tkinter`를 사용하여 메인 윈도우, 버튼, 텍스트 박스(로그 표시용) 등을 생성합니다.
    *   **[폴더 선택]** 버튼: 클릭 시 `filedialog.askdirectory()`를 호출하여 사용자가 텍스트 파일이 있는 폴더를 선택하게 하고, 선택된 경로를 `config.json` 파일에 저장합니다.
    *   **[실행]** 버튼: 클릭 시 `BackendProcessor`의 `run` 메소드를 스레드(Thread)로 실행합니다. 스레드를 사용하는 이유는 GUI가 멈추는 현상(freezing) 없이 백그라운드에서 텍스트 처리 및 구글 문서 작업을 수행하기 위함입니다.
    *   **로그 표시:** 백엔드에서 발생하는 로그 메시지를 GUI의 텍스트 박스에 실시간으로 표시하여 사용자에게 진행 상황을 알려줍니다.

### 4.2. `src/auto_write_txt_to_docs/backend_processor.py` - 백엔드 로직

*   **역할:** 실제 텍스트 파일을 처리하고 구글 문서에 쓰는 핵심 로직을 담당합니다.
*   **주요 기능:**
    *   `__init__`: 설정 파일(`config.json`)을 읽어 구글 문서 ID, 대상 폴더 경로 등의 설정을 초기화합니다. `GoogleAuth` 객체를 생성하여 구글 인증을 준비합니다.
    *   `run`: **[실행]** 버튼을 눌렀을 때 호출되는 메인 메소드입니다.
        1.  `google_auth.get_credentials()`를 통해 구글 인증을 수행하고, API 서비스 객체를 생성합니다.
        2.  `_load_added_lines_cache()`를 호출하여 이전에 처리했던 텍스트 라인 목록을 불러옵니다.
        3.  `_read_and_process_files()`를 호출하여 대상 폴더의 `.txt` 파일들을 처리합니다.
    *   `_read_and_process_files`:
        1.  지정된 폴더 내의 모든 `.txt` 파일을 찾습니다.
        2.  각 파일을 열어 한 줄씩 읽습니다.
        3.  각 줄에 대해 `_is_line_added()`를 사용하여 이전에 추가된 라인인지 확인합니다.
        4.  새로운 라인인 경우, `_write_to_google_doc()`을 호출하여 구글 문서에 내용을 추가하고, 캐시에 해당 라인을 기록한 후 `_update_added_lines_cache()`로 캐시 파일을 업데이트합니다.
    *   `_write_to_google_doc`: `Google Docs API`를 사용하여 텍스트를 문서의 끝에 추가하는 요청을 보냅니다.
    *   `_load_added_lines_cache`, `_update_added_lines_cache`, `_is_line_added`: 중복 처리를 방지하기 위한 캐시 관리 메소드들입니다.

### 4.3. `src/auto_write_txt_to_docs/google_auth.py` - 구글 인증

*   **역할:** 구글 API 사용에 필요한 인증(Authentication) 및 권한 부여(Authorization)를 처리합니다.
*   **주요 기능:**
    *   `__init__`: 인증에 필요한 정보(자격 증명 파일 경로, 필요한 API 스코프 등)를 설정합니다. `token.json` 파일이 저장될 경로도 지정합니다.
    *   `get_credentials`:
        1.  `token.json` 파일이 있는지 확인합니다. 이 파일은 사용자가 한번 인증에 성공하면 생성되며, 유효한 토큰 정보가 저장되어 있습니다.
        2.  `token.json`이 있고 유효하다면, 그 정보를 사용하여 바로 인증 객체를 반환합니다. (자동 로그인)
        3.  `token.json`이 없거나 만료되었다면, `developer_credentials.json` 파일을 사용하여 새로운 인증 절차를 시작합니다.
        4.  `InstalledAppFlow.run_local_server()`를 호출하여 사용자에게 웹 브라우저를 통해 구글 계정으로 로그인하고 권한을 부여하도록 요청합니다.
        5.  인증이 성공적으로 완료되면, 새로운 `token.json` 파일을 생성하여 다음 실행을 위해 인증 정보를 저장합니다.

## 5. 워크플로우 로직 (Workflow Logic)

사용자가 프로그램을 실행했을 때부터 구글 문서에 내용이 추가되기까지의 과정은 다음과 같습니다.

1.  **프로그램 시작:** 사용자가 `main_gui.py`를 실행하면 GUI 창이 나타납니다.
2.  **폴더 선택:** 사용자가 **[폴더 선택]** 버튼을 눌러 텍스트 파일이 있는 폴더를 지정합니다. 이 경로는 `config.json`에 저장됩니다.
3.  **실행:** 사용자가 **[실행]** 버튼을 누릅니다.
4.  **백엔드 스레드 시작:** `main_gui`는 `BackendProcessor`의 `run` 메소드를 새로운 스레드에서 실행합니다.
5.  **구글 인증:** `BackendProcessor`는 `GoogleAuth`를 통해 구글 인증을 시도합니다.
    *   기존 `token.json`이 있으면, 해당 토큰으로 즉시 인증됩니다.
    *   없으면, 웹 브라우저가 열리고 사용자는 구글 계정으로 로그인하여 권한을 부여해야 합니다. 성공 시 `token.json`이 생성됩니다.
6.  **캐시 로드:** `added_lines_cache.json` 파일에서 이전에 처리된 텍스트 라인 목록을 불러옵니다.
7.  **파일 스캔 및 처리:**
    *   `config.json`에 지정된 폴더에서 모든 `.txt` 파일을 찾습니다.
    *   각 파일의 내용을 한 줄씩 읽어, 캐시에 없는 새로운 라인인지 확인합니다.
8.  **구글 문서에 쓰기:**
    *   새로운 라인이 발견되면, `Google Docs API`를 호출하여 해당 내용을 구글 문서의 끝에 추가합니다.
    *   성공적으로 추가되면, 해당 라인을 캐시에 추가하고 `added_lines_cache.json` 파일을 업데이트합니다.
9.  **로그 업데이트:** 모든 과정(인증, 파일 처리, 문서 쓰기, 오류 등)은 로그 파일과 GUI의 로그 창에 기록됩니다.
10. **프로세스 완료:** 모든 파일 처리가 끝나면 스레드가 종료되고, 프로그램은 다음 실행을 대기합니다.

## 6. 프로젝트 의존성 (Dependencies)

`requirements.txt` 파일에 명시된 이 프로젝트의 주요 외부 라이브러리는 다음과 같습니다.

*   `google-api-python-client`: Google API와 상호작용하기 위한 핵심 라이브러리.
*   `google-auth-httplib2`: Google 인증을 위한 HTTP 클라이언트 라이브러리.
*   `google-auth-oauthlib`: OAuth 2.0 인증 흐름을 간소화하는 라이브러리.
*   `requests`: 백엔드 프로세서에서 사용될 수 있는 HTTP 요청 라이브러리.

## 7. 향후 개발 계획 (Future Development)

`task나누기.md` 파일에 프로젝트의 향후 개발 및 개선 아이디어가 정리되어 있습니다. 주요 내용은 다음과 같습니다.

*   **기능 개선:**
    *   하위 폴더의 텍스트 파일까지 재귀적으로 탐색하는 기능 추가.
    *   `.txt` 외에 `.md`, `.docx` 등 다른 형식의 파일 지원.
    *   구글 문서의 특정 위치(예: 맨 위, 특정 제목 아래)에 텍스트를 추가하는 옵션 제공.
*   **UI/UX 개선:**
    *   진행률 표시줄(Progress Bar) 추가.
    *   처리된 파일 목록을 GUI에 표시.
*   **안정성 및 예외 처리 강화:**
    *   네트워크 오류, API 할당량 초과 등 다양한 예외 상황에 대한 처리 로직 보강.
    *   더욱 상세한 로그 레벨(Debug, Info, Warning, Error) 관리.

이 문서를 통해 프로젝트의 전반적인 구조와 흐름을 이해하는 데 도움이 되기를 바랍니다.
