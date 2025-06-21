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

## 설정

1.  **Google API 인증 정보 준비 (`developer_credentials.json`)**:
    *   Google Cloud Console ([https://console.cloud.google.com/](https://console.cloud.google.com/))에서 새 프로젝트를 생성하거나 기존 프로젝트를 선택합니다.
    *   "API 및 서비스" > "사용 설정된 API 및 서비스"에서 "+ API 및 서비스 사용 설정"을 클릭하여 "Google Docs API"와 "Google Drive API"를 검색하여 사용 설정합니다. (Drive API는 파일 생성/관리에 필요할 수 있습니다.)
    *   "API 및 서비스" > "사용자 인증 정보"에서 "+ 사용자 인증 정보 만들기"를 클릭하고 "OAuth 클라이언트 ID"를 선택합니다.
    *   애플리케이션 유형을 "데스크톱 앱"으로 선택하고 이름을 지정한 후 "만들기"를 클릭합니다.
    *   생성된 OAuth 2.0 클라이언트 ID 목록에서 해당 인증 정보를 클릭한 후, 오른쪽 상단의 "JSON 다운로드" 버튼을 클릭하여 인증 정보 파일을 다운로드합니다.
    *   다운로드한 파일의 이름을 `developer_credentials.json`으로 변경합니다.
    *   **파일 위치**:
        *   **개발 환경**: 프로젝트 내의 `src/auto_write_txt_to_docs/assets/` 폴더에 이 파일을 위치시킵니다. 만약 `assets` 폴더가 없다면 직접 생성해주세요. (전체 경로 예: `auto_write_txt_to_docs/src/auto_write_txt_to_docs/assets/developer_credentials.json`)
        *   **빌드된 애플리케이션 (PyInstaller 등)**: PyInstaller로 빌드할 때 `developer_credentials.json` 파일이 `assets` 폴더에 포함되도록 `--add-data` 옵션을 사용해야 합니다. (예: `--add-data "src/auto_write_txt_to_docs/assets:assets"`) 프로그램은 실행 파일 내부의 `assets` 폴더에서 이 파일을 찾습니다.

2.  **프로그램 실행 및 설정**:
    *   프로그램을 처음 실행하면 Google 계정으로 로그인하여 프로그램에 권한을 부여하라는 메시지가 웹 브라우저에 나타날 수 있습니다. 안내에 따라 진행해주세요. 인증이 성공하면 `token.json` 파일이 사용자 디렉토리에 자동으로 생성되어 다음 실행부터는 이 과정이 생략됩니다.
    *   프로그램의 GUI 창에서 다음을 설정합니다:
        *   **감시할 폴더 경로 설정**: 텍스트 파일이 저장되는 폴더를 지정합니다.
        *   **Google Docs 문서 URL 또는 ID 설정**: 텍스트 내용을 기록할 Google Docs 문서의 전체 URL 또는 문서 ID를 입력합니다.

    *참고*: `developer_credentials.json` 파일이 올바른 위치에 없거나 유효하지 않으면, 프로그램 실행 시 또는 "감시 시작" 시 오류 메시지가 나타날 수 있습니다.

## 라이선스

MIT License
