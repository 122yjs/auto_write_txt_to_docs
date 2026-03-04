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
2. **'감시 시작'** 버튼을 누릅니다.
3. 웹 브라우저가 자동으로 열리면 사용하실 **Google 계정으로 로그인**합니다.
4. "이 프로그램이 Google Docs에 접근하려고 합니다"라는 메시지가 나오면 **'허용'**을 눌러주세요.
5. 한 번만 인증하면 이후에는 자동으로 작동합니다. (`token.json` 파일이 생성됩니다)

### 💻 개발자/배포자 설정
프로그램을 새로 빌드하거나 다른 프로젝트로 배포하려는 경우에만 이 단계를 따르세요.

1.  **인증 정보 파일 준비**:
    *   Google Cloud Console에서 **데스크톱 앱** 유형의 OAuth 2.0 클라이언트 ID를 생성합니다.
    *   JSON 파일을 다운로드하여 이름을 `developer_credentials.json`으로 변경합니다.
2.  **파일 위치**:
    *   **소스 실행 시**: `src/auto_write_txt_to_docs/assets/developer_credentials.json` 에 배치합니다.
    *   **빌드 시**: PyInstaller 등 빌드 도구를 사용할 때 `assets` 폴더가 포함되도록 설정합니다. (예: `--add-data "src/auto_write_txt_to_docs/assets:assets"`)
3.  **주의**: `developer_credentials.json`과 생성된 `token.json`은 절대 공개된 저장소(GitHub 등)에 공유하지 마세요. (이미 `.gitignore`에 등록되어 있습니다.)

---

## 🚀 실행 방법

## 라이선스

MIT License
