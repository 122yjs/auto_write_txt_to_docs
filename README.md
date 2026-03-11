# Auto Write Txt To Docs

특정 폴더의 텍스트 파일 변화를 감시하고, 새로 추가된 내용을 Google Docs 문서에 자동으로 기록하는 데스크톱 GUI 애플리케이션입니다.

## 개요

이 프로젝트는 메신저 로그나 텍스트 덤프 파일처럼 계속 누적되는 `.txt` 파일을 감시하면서, 새로 들어온 줄만 골라 Google Docs 문서 끝에 자동으로 추가합니다.

주요 흐름은 다음과 같습니다.

1. 감시 폴더와 대상 Google Docs 문서를 지정합니다.
2. 파일 생성/수정 이벤트를 감지합니다.
3. 마지막 처리 바이트 오프셋 이후의 변경분만 읽습니다.
4. 전역 라인 캐시와 파일별 해시로 중복을 제거합니다.
5. 새 텍스트를 Google Docs 문서 끝에 추가합니다.

## 주요 기능

- Google Docs 대상 선택
  - 새 문서 만들기
  - 기존 Google Docs URL 또는 문서 ID 직접 입력
  - 현재 권한 범위에서 접근 가능한 문서 목록 조회
  - 현재 연결된 문서를 브라우저에서 열기
- 폴더 감시
  - 단일 폴더 감시
  - 기본 `.txt` 확장자 필터
  - 쉼표 구분 다중 확장자 지정
  - 정규식 기반 파일명 필터
- 텍스트 처리
  - 바이트 오프셋 기반 증분 읽기
  - 파일 크기 감소 시 전체 재읽기
  - `utf-8`, `cp949`, `utf-8-sig`, `euc-kr` 순서 인코딩 시도
  - 전역 라인 캐시 및 파일별 해시 기반 중복 제거
- 사용자 기능
  - CustomTkinter 기반 GUI
  - 시스템 트레이 상주
  - 로그 패널 및 최근 추출 결과 미리보기
  - 설정 저장/로드, 백업/복원
  - 메모리 사용량 표시 및 수동 정리
- 배포
  - Windows용 PyInstaller `onedir` 빌드 스크립트 제공
  - portable zip 생성 지원

## 프로젝트 구조

```text
.
├── main_gui.py
├── scripts/
│   └── build_release.ps1
├── src/
│   └── auto_write_txt_to_docs/
│       ├── app_dialogs.py
│       ├── autostart_utils.py
│       ├── backend_processor.py
│       ├── config_manager.py
│       ├── google_auth.py
│       ├── main_window_ui.py
│       ├── path_utils.py
│       └── ui_helpers.py
└── tests/
```

핵심 역할은 다음과 같습니다.

- `main_gui.py`: 앱 진입점, 상태 관리, UI 이벤트, 트레이 제어
- `backend_processor.py`: 파일 감시, 증분 읽기, 중복 제거, Google Docs 업데이트
- `google_auth.py`: OAuth 인증, Docs/Drive 서비스 생성, 문서 생성/조회
- `path_utils.py`: 설정/캐시/로그/토큰 저장 경로 관리

## 요구 사항

- Python 3.7 이상
- Google Docs API 사용 가능한 Google 계정
- 새 문서 만들기/문서 목록 기능을 사용할 경우 Google Drive API도 필요

## 설치

```bash
git clone https://github.com/122yjs/auto_write_txt_to_docs
cd auto_write_txt_to_docs
python -m venv venv
source venv/bin/activate
pip install -e .
```

Windows에서는 가상환경 활성화에 아래 명령을 사용합니다.

```powershell
venv\Scripts\activate
```

`requirements.txt`로 설치하려면 아래 명령을 사용할 수도 있습니다.

```bash
pip install -r requirements.txt
```

## 실행

패키지 엔트리포인트:

```bash
auto_write_gui
```

또는 직접 실행:

```bash
python main_gui.py
```

## Google 인증 설정

일반 사용자는 Google Cloud Console을 직접 만질 필요가 없도록 설계되어 있습니다. 앱에 번들된 OAuth 클라이언트 JSON이 있으면 그 설정을 사용하고, 필요하면 사용자 지정 인증 파일로 덮어쓸 수 있습니다.

일반적인 사용 순서는 다음과 같습니다.

1. 프로그램을 실행합니다.
2. 대상 문서를 아래 세 가지 중 한 가지 방식으로 지정합니다.
3. `감시 시작`을 누릅니다.
4. 브라우저가 열리면 사용할 Google 계정으로 로그인합니다.
5. 접근 권한 요청에 동의하면 `token.json`이 생성되고 이후 재사용됩니다.

문서 지정 방식:

- `새 문서 만들기`: 새 Google Docs 문서를 만들고 즉시 연결합니다.
- `기존 주소 입력`: 문서 URL 전체 또는 문서 ID만 입력할 수 있습니다.
- `문서 목록`: 이 앱이 생성했거나 이 앱 권한 범위에서 접근 가능한 문서만 표시됩니다.

API 관련 주의사항:

- `새 문서 만들기`, `문서 목록` 기능은 Google Drive API가 활성화되어 있어야 합니다.
- Google Docs API만 켜져 있고 Drive API가 꺼져 있으면 403 `accessNotConfigured` 오류가 발생할 수 있습니다.
- 같은 Google Cloud 프로젝트에서 아래 두 API가 모두 활성화되어 있어야 합니다.
  - Google Docs API
  - Google Drive API

개발자/배포자용 설정:

1. Google Cloud Console에서 데스크톱 앱용 OAuth 2.0 클라이언트 ID를 생성합니다.
2. JSON 파일 이름을 `developer_credentials.json`으로 맞춥니다.
3. 개발 환경에서는 `src/auto_write_txt_to_docs/assets/developer_credentials.json` 위치에 둡니다.
4. 사용자가 GUI의 인증 마법사에서 별도 JSON을 지정하면 사용자 설정 폴더의 파일이 우선 사용됩니다.

주의:

- `developer_credentials.json`과 `token.json`은 공개 저장소에 올리면 안 됩니다.
- 실제 앱 동작은 새 텍스트를 문서 맨 위가 아니라 문서 끝에 추가합니다.

## 저장 경로

설정과 캐시는 프로젝트 루트가 아니라 사용자별 애플리케이션 데이터 폴더 아래에 저장됩니다.

- Windows: `%APPDATA%\MessengerDocsAutoWriter\`
- macOS: `~/Library/Application Support/MessengerDocsAutoWriter/`
- Linux: `${XDG_CONFIG_HOME:-~/.config}/MessengerDocsAutoWriter/`

주요 파일:

- `config.json`: 앱 설정
- `cache/added_lines_cache.json`: 전역 중복 제거 캐시
- `cache/processed_state.json`: 파일별 마지막 처리 위치
- `cache/token.json`: Google OAuth 토큰
- `logs/`: 실행 로그

## 테스트

이 저장소는 `unittest` 기반 테스트를 사용합니다.

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

현재 로컬 기준으로 위 명령은 49개 테스트가 통과합니다.

## Windows 배포

Windows 기준으로는 PyInstaller `onedir` 빌드가 권장됩니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

빌드 결과:

- 실행 폴더: `dist\MessengerDocsAutoWriter\`
- 배포 zip: `release\MessengerDocsAutoWriter-win64-portable.zip`

배포물에는 다음 파일이 포함됩니다.

- 실행 파일 및 런타임 의존성
- `assets\developer_credentials.json`
- `README.md`
- `config.json.example`
- `added_lines_cache.json.example`

배포 전 확인:

- 배포용 `developer_credentials.json`이 올바른 Google Cloud 프로젝트용인지 확인합니다.
- `새 문서 만들기`와 `문서 목록` 기능을 사용할 경우 Google Drive API도 활성화되어 있어야 합니다.

## 개발 메모

- 패키지 엔트리포인트는 `pyproject.toml`의 `auto_write_gui = "main_gui:main"` 입니다.
- 테스트 일부는 실제 동작보다 문자열 존재 여부를 검증하는 방식이 포함되어 있습니다.
- 백업 성격의 코드가 `backup/` 디렉토리에 남아 있지만 현재 주 실행 경로에는 직접 연결되지 않습니다.

## 라이선스

MIT License
