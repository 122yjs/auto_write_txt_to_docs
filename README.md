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

1. Google Cloud Console에서 프로젝트 생성 및 API 인증 정보 설정
2. 프로그램 실행 후 설정 창에서:
   - 감시할 폴더 경로 설정
   - Google API 인증 파일 경로 설정
   - Google Docs 문서 ID 설정

## 라이선스

MIT License
