# Messenger Docs Auto Writer

메신저나 업무 시스템이 만든 `.txt` 파일을 감시해서, 새로 생긴 내용만 Google Docs 문서에 자동으로 기록하는 Windows용 데스크톱 앱입니다.

이 프로젝트는 아래 상황에 맞게 만들어졌습니다.

- 특정 폴더에 텍스트 파일이 계속 생성되거나 수정됨
- 파일 내용을 수동 복사하지 않고 Google Docs에 모아두고 싶음
- 이미 기록한 줄은 다시 넣고 싶지 않음
- 작업 결과를 화면, 로그, 알림으로 바로 확인하고 싶음

## 한눈에 보기

이 앱으로 할 수 있는 일은 아래와 같습니다.

- 감시할 폴더 지정
- 새 Google Docs 문서 만들기
- 기존 Google Docs 주소 또는 문서 ID 입력
- 접근 가능한 문서 목록에서 선택
- 새 줄만 추려서 문서 끝에 자동 추가
- 전부 중복이면 파일명만 기록하거나 중복 알림 표시
- 작업 결과 알림과 효과음 확인
- 설정 저장, 백업/복원, 로그 확인

## 처음 쓰는 분을 위한 빠른 시작

### 1. 준비물

- Windows 10 또는 Windows 11
- Python 3.7 이상
- Google 계정
- Google Docs에 기록할 권한

### 2. 프로젝트 받기

GitHub에서 소스를 받았다면 PowerShell에서 아래처럼 이동합니다.

```powershell
git clone https://github.com/122yjs/auto_write_txt_to_docs
cd auto_write_txt_to_docs
```

이미 압축 파일이나 릴리즈 zip을 받았다면, 압축을 푼 뒤 해당 폴더에서 진행하면 됩니다.

### 3. 가상환경 만들기

처음 Python 프로젝트를 다룬다면, 가상환경을 쓰는 것이 가장 안전합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

실행 정책 때문에 활성화가 막히면 아래 명령을 한 번만 실행한 뒤 다시 시도합니다.

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 4. 필요한 패키지 설치

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. 앱 실행

가장 간단한 실행 방법은 아래 둘 중 하나입니다.

```powershell
python main_gui.py
```

또는

```powershell
auto_write_gui
```

## 첫 실행 때 무엇을 하면 되나요?

앱을 켜면 아래 순서로 진행하면 됩니다.

1. 감시할 폴더를 고릅니다.
2. 기록할 Google Docs 문서를 정합니다.
3. 필요하면 작업 결과 알림과 효과음을 켭니다.
4. `감시 시작` 버튼을 누릅니다.
5. 브라우저가 열리면 Google 로그인과 권한 승인을 마칩니다.

권한 승인이 끝나면 앱이 토큰을 저장하므로, 이후에는 같은 PC에서 다시 로그인하지 않아도 되는 경우가 많습니다.

## Google 문서는 어떻게 선택하나요?

문서는 아래 3가지 방법으로 정할 수 있습니다.

### 새 문서 만들기

앱이 새 Google Docs 문서를 만들고 바로 연결합니다.

### 기존 문서 주소 입력

브라우저 주소창의 전체 URL을 그대로 붙여 넣어도 되고, 문서 ID만 넣어도 됩니다.

예시:

```text
https://docs.google.com/document/d/문서ID/edit
```

또는

```text
문서ID만입력
```

### 문서 목록에서 선택

현재 계정으로 접근 가능한 문서 목록을 불러와서 고를 수 있습니다.

## 공개용 릴리즈와 내부용 릴리즈의 차이

이 저장소는 배포 목적에 따라 두 가지 빌드 방식을 사용합니다.

### 공개용 릴리즈

- 공식 GitHub 릴리즈 기준으로 실제 `developer_credentials.json`을 포함합니다.
- 일반 사용자는 별도 자격증명 파일을 준비하지 않아도 바로 실행할 수 있습니다.
- 공개 GitHub 저장소나 외부 배포에 적합합니다.

### 내부용 릴리즈

- 실제 `developer_credentials.json`을 포함합니다.
- 사내 테스트나 내부 배포용으로만 사용해야 합니다.
- 외부 공개 저장소에 그대로 올리면 안 됩니다.

릴리즈를 만들 때 어떤 자격증명을 넣어도 되는지 헷갈리면 아래 문서를 먼저 확인하세요.

- [릴리즈 정책 문서](docs/release-policy.md)

## `developer_credentials.json`은 꼭 필요한가요?

상황에 따라 다릅니다.

### GitHub 릴리즈 실행

보통은 필요하지 않습니다. 공식 릴리즈에는 실제 `developer_credentials.json`이 함께 들어가므로 바로 실행할 수 있습니다.

### 소스 실행 또는 직접 빌드

네, 필요합니다. 아래 두 방법 중 하나로 준비하면 됩니다.

- 앱의 인증 마법사에서 직접 파일을 선택
- 개발 환경에서 `src\auto_write_txt_to_docs\assets\developer_credentials.json` 위치에 배치

### 내부용 빌드

내부용으로 만든 빌드도 실제 `developer_credentials.json`을 포함합니다. 차이는 배포 대상과 공유 범위입니다.

## 절대 저장소에 커밋하면 안 되는 파일

아래 파일은 개인 계정이나 프로젝트 인증 정보가 들어 있으므로 공개 저장소에는 올리면 안 됩니다.

- `developer_credentials.json`
- `token.json`

저장소에는 예시 파일만 포함되어 있습니다.

- `src\auto_write_txt_to_docs\assets\developer_credentials.json.example`

## 이 앱은 실제로 어떻게 동작하나요?

초보자 기준으로 단순하게 설명하면 이렇습니다.

1. 앱이 감시 폴더를 지켜봅니다.
2. 새 파일이 생기거나 파일이 수정되면 해당 파일만 처리합니다.
3. 이미 문서에 넣었던 줄과 비교해서 새 줄만 골라냅니다.
4. 새 줄이 있으면 Google Docs 문서 끝에 추가합니다.
5. 성공, 중복, 실패 결과를 로그와 알림으로 보여줍니다.

중요한 점:

- 파일 하나가 바뀌었다고 해서 감시 폴더 전체를 매번 다시 읽는 구조는 아닙니다.
- 대신 처리 상태를 저장하는 파일이 있기 때문에, 앱을 껐다 켜도 이어서 동작할 수 있습니다.

## 중복 처리는 어떻게 되나요?

이 부분은 처음 쓰는 분이 가장 헷갈리기 쉬워서 따로 적습니다.

- 이미 기록한 줄은 다시 Google Docs에 넣지 않으려고 전역 라인 캐시를 사용합니다.
- 파일 이름이 달라도 본문 줄이 완전히 같으면 중복으로 판단될 수 있습니다.
- 전부 중복이면 "추가 본문 없음" 형태로 파일명만 기록하거나, 중복 알림만 표시할 수 있습니다.
- 성공, 중복, 실패 결과는 작업 로그에서 다시 확인할 수 있습니다.

## 알림은 어떻게 보이나요?

현재 버전에서는 작업 결과를 아래 방식으로 알려줍니다.

- 트레이 알림
- Windows 시스템 효과음
- 작업 로그
- 최근 추출 결과 미리보기

알림에는 가능한 경우 아래 정보가 함께 들어갑니다.

- 파일명
- 몇 줄이 추가되었는지
- 미리보기 2줄
- 남은 줄 수 요약

실패 시에는 미리보기 대신 오류 요약을 보여줍니다.

## 설정, 로그, 캐시는 어디에 저장되나요?

Windows에서는 프로젝트 폴더가 아니라 사용자 프로필 아래에 저장됩니다.

기본 위치:

```text
%APPDATA%\MessengerDocsAutoWriter\
```

주요 파일:

- `config.json`: 앱 설정
- `cache\added_lines_cache.json`: 이미 기록한 줄 캐시
- `cache\processed_state.json`: 파일별 마지막 처리 상태
- `cache\token.json`: Google 로그인 토큰
- `logs\`: 실행 로그

예시 실제 경로:

```text
C:\Users\사용자이름\AppData\Roaming\MessengerDocsAutoWriter\
```

## 문제 해결

### 1. Google 로그인은 되는데 문서 목록이 안 보임

대개 Google Drive API가 꺼져 있을 때 발생합니다.

확인할 것:

- Google Docs API 활성화
- Google Drive API 활성화
- 사용 중인 OAuth 클라이언트가 올바른 프로젝트에 연결되어 있는지 확인

### 2. 감시는 되는데 문서에 추가되지 않음

아래를 차례대로 확인합니다.

- 대상 Google Docs 문서가 올바르게 선택되었는지
- 새로 들어온 줄이 정말 있는지
- 전부 중복이라서 추가가 생략된 것은 아닌지
- 작업 로그에 실패 메시지가 없는지

### 3. 인증을 다시 받고 싶음

아래 파일을 지우고 앱을 다시 실행하면 보통 다시 로그인 절차가 시작됩니다.

```text
%APPDATA%\MessengerDocsAutoWriter\cache\token.json
```

## 개발 환경에서 실행하는 방법

### 의존성 설치

```powershell
pip install -r requirements.txt
```

### 앱 실행

```powershell
python main_gui.py
```

### 자동 테스트 실행

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

`tests\` 폴더에는 UI 문자열, 알림 흐름, 설정 저장, 빌드 스크립트, 백엔드 처리 로직 검증이 포함되어 있습니다.

## Windows용 배포 파일 만들기

PowerShell에서 아래 명령을 실행합니다.

### 공개용 빌드

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

이 빌드는 현재 정책상 실제 `developer_credentials.json`을 기본 포함합니다.

### 내부용 빌드

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

현재 정책상 공개용과 내부용 모두 기본적으로 실제 `developer_credentials.json`을 포함합니다. 차이는 배포 대상과 공유 범위입니다.

### 자격증명 제외 빌드가 필요할 때

실제 자격증명을 뺀 배포물을 따로 확인해야 한다면 아래 명령을 사용합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1 -ExcludeBundledCredentials
```

### 빌드 결과 위치

- 실행 폴더: `dist\MessengerDocsAutoWriter\`
- 배포 zip: `release\MessengerDocsAutoWriter-win64-portable.zip`

## 프로젝트 구조

```text
.
├── main_gui.py
├── requirements.txt
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

핵심 파일 역할:

- `main_gui.py`: 메인 화면, 알림, 트레이, 사용자 입력 처리
- `backend_processor.py`: 파일 감시, 새 줄 추출, 중복 제거, Google Docs 기록
- `google_auth.py`: Google 로그인과 문서 접근
- `config_manager.py`: 설정 저장과 백업/복원
- `path_utils.py`: 설정, 캐시, 로그 저장 경로 관리

## 자주 묻는 질문

### Q. `.txt` 외의 파일도 감시할 수 있나요?

네. 확장자 설정을 바꾸면 됩니다. 기본값은 `.txt`입니다.

### Q. 알림 소리를 끌 수 있나요?

네. 설정에서 작업 결과 효과음을 끌 수 있습니다.

### Q. 로그는 어디서 확인하나요?

앱의 `로그 폴더 열기` 기능이나 `%APPDATA%\MessengerDocsAutoWriter\logs\` 경로에서 확인할 수 있습니다.

### Q. 문서가 여러 개인데 하나씩 바꿔가며 쓸 수 있나요?

네. 주소 직접 입력, 문서 목록 선택, 새 문서 만들기 중 원하는 방식으로 바꿀 수 있습니다.

## 라이선스

MIT License
