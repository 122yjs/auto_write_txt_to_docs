# Auto Write

메신저 앱의 텍스트를 자동으로 Google Docs에 기록하는 프로그램입니다.

## 기능

- 지정된 폴더의 텍스트 파일 모니터링
- 새로운 텍스트 내용을 Google Docs에 자동 기록
- 시스템 트레이 지원으로 백그라운드 실행
- 중복 내용 필터링

## 설치 방법

1. 프로젝트 클론
```bash
git clone https://github.com/122yjs/auto_write_txt_to_docs
cd auto_write
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 패키지 설치
```bash
pip install -e .
```

## 실행 방법

```bash
# GUI 실행
auto_write_gui
```

## 🔑 Google 인증 설정 (중요)

본 프로그램은 사용자가 직접 Google Cloud Console을 만질 필요가 없도록 설계되었습니다. **이미 인증 정보가 프로그램에 내장되어 있습니다.**

### 👤 일반 사용자 사용법
1. 프로그램을 실행합니다.
2. 대상 문서는 아래 3가지 방식 중 하나로 지정합니다.
   - **`새 문서 만들기`**: 현재 권한 범위에서 새 Google Docs 문서를 만들고 자동으로 연결합니다.
   - **`기존 주소 입력`**: 기존 Google Docs URL 또는 문서 ID를 직접 입력합니다.
   - **`문서 목록`**: 이 앱이 이미 접근 가능한 문서 목록에서 선택합니다.
3. **`감시 시작`** 버튼을 누릅니다.
4. 웹 브라우저가 자동으로 열리면 사용하실 **Google 계정으로 로그인**합니다.
5. "이 프로그램이 Google Docs에 접근하려고 합니다"라는 메시지가 나오면 **`허용`**을 눌러주세요.
6. 한 번만 인증하면 이후에는 자동으로 작동합니다. (`token.json` 파일이 생성됩니다)

### 📝 문서 지정 방식 안내
- **`새 문서 만들기`**: 가장 간단한 방식입니다. 새 문서를 만든 뒤 자동으로 현재 대상 문서로 설정합니다.
- **`기존 주소 입력`**: 이미 쓰고 있는 Google Docs 문서가 있으면 URL 전체 또는 문서 ID만 붙여넣을 수 있습니다.
- **`문서 목록`**: 현재 OAuth 권한이 `drive.file`이므로, **이 앱이 만들었거나 이 앱이 이미 접근한 문서만** 표시됩니다. 내 Google Drive의 모든 문서가 보이는 것은 아닙니다.
- **`Docs 웹에서 열기`**: 현재 선택된 문서를 브라우저에서 바로 엽니다.

### ⚠️ 문서 생성/문서 목록 기능 추가 조건
- **`새 문서 만들기`** 와 **`문서 목록`** 기능은 **Google Drive API**가 활성화되어 있어야 합니다.
- Google Docs API만 켜져 있고 Drive API가 꺼져 있으면 403 오류(`accessNotConfigured`)가 발생합니다.
- 같은 Google Cloud 프로젝트에서 아래 두 API가 모두 활성화되어 있어야 합니다.
  - Google Docs API
  - Google Drive API

### 💻 개발자/배포자 설정
프로그램을 새로 빌드하거나 다른 프로젝트로 배포하려는 경우에만 이 단계를 따르세요.

1.  **인증 정보 파일 준비**:
    *   Google Cloud Console에서 **데스크톱 앱** 유형의 OAuth 2.0 클라이언트 ID를 생성합니다.
    *   JSON 파일을 다운로드하여 이름을 `developer_credentials.json`으로 변경합니다.
2.  **파일 위치**:
    *   **소스 실행 시**: `src/auto_write_txt_to_docs/assets/developer_credentials.json` 에 배치합니다.
    *   **일반 사용자 override**: 사용자가 GUI의 인증 마법사로 JSON을 다시 지정하면 사용자 설정 폴더(`AppData\\Roaming\\MessengerDocsAutoWriter`)에 별도 저장되어 그 파일이 우선 사용됩니다.
    *   **빌드 시**: 패키징 결과물에 `src/auto_write_txt_to_docs/assets/*.json` 이 포함되도록 유지해야 합니다.
3.  **주의**: `developer_credentials.json`과 생성된 `token.json`은 절대 공개된 저장소(GitHub 등)에 공유하지 마세요. (이미 `.gitignore`에 등록되어 있습니다.)

---

## 🚀 실행 방법

## 라이선스

MIT License
