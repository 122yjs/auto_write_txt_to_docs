# 릴리즈 정책

이 문서는 `Messenger Docs Auto Writer`를 배포할 때, 어떤 파일을 넣어도 되고 어떤 파일은 절대 넣으면 안 되는지 빠르게 판단하기 위한 기준입니다.

초보자 기준으로 가장 중요한 규칙은 아래 한 줄입니다.

`token.json`은 어떤 경우에도 배포물이나 저장소에 넣지 않습니다.

## 1. 공개용과 내부용의 차이

### 공개용 릴리즈

공개용 릴리즈는 GitHub 공개 저장소, 외부 고객, 외부 사용자에게 전달할 수 있는 배포물입니다.

넣어도 되는 것:

- 실행 파일
- `README.md`
- `config.json.example`
- `added_lines_cache.json.example`
- `developer_credentials.json.example`

넣으면 안 되는 것:

- 실제 `developer_credentials.json`
- `token.json`
- 개인 PC에서 생성된 설정 파일
- 개인 로그 파일

### 내부용 릴리즈

내부용 릴리즈는 팀 내부 테스트, 사내 배포, 운영자용 배포처럼 제한된 범위에서만 쓰는 배포물입니다.

넣어도 되는 것:

- 공개용 릴리즈에 들어가는 파일 전체
- 실제 `developer_credentials.json`

넣으면 안 되는 것:

- `token.json`
- 특정 사용자 PC에서 생성된 `config.json`
- 특정 사용자 PC의 캐시 파일
- 특정 사용자 PC의 로그 파일

## 2. 파일별 판단 기준

### `developer_credentials.json`

이 파일은 프로그램의 Google OAuth 클라이언트 정보입니다.

- 공개용 릴리즈: 포함 금지
- 내부용 릴리즈: 포함 가능
- 공개 저장소 커밋: 포함 금지

### `developer_credentials.json.example`

이 파일은 예시 파일입니다.

- 공개용 릴리즈: 포함 가능
- 내부용 릴리즈: 포함 가능
- 공개 저장소 커밋: 포함 가능

### `token.json`

이 파일은 특정 사용자의 로그인 결과로 생기는 토큰입니다.

- 공개용 릴리즈: 포함 금지
- 내부용 릴리즈: 포함 금지
- 공개 저장소 커밋: 포함 금지
- 사내 공유 폴더 업로드: 포함 금지

즉, 어떤 경우에도 배포 대상에 넣지 않습니다.

## 3. 실제 빌드 명령

### 공개용 빌드

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

이 명령은 실제 `developer_credentials.json`을 제외하고 빌드합니다.

### 내부용 빌드

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1 -IncludeBundledCredentials
```

이 명령은 실제 `developer_credentials.json`을 포함할 수 있습니다.

## 4. 릴리즈 전에 확인할 것

공개용 릴리즈 체크리스트:

- `developer_credentials.json`이 포함되지 않았는지 확인
- `developer_credentials.json.example`만 들어 있는지 확인
- `token.json`이 전혀 없는지 확인
- 로그와 개인 설정 파일이 들어 있지 않은지 확인

내부용 릴리즈 체크리스트:

- 실제 `developer_credentials.json`이 필요한 대상에게만 전달되는지 확인
- `token.json`이 없는지 확인
- 사용자별 `config.json`, 캐시, 로그가 빠졌는지 확인
- 외부 공개 위치에 올리지 않는지 확인

## 5. 저장소 운영 원칙

저장소에는 아래만 남기는 것이 원칙입니다.

- 코드
- 테스트
- 예시 설정 파일
- 예시 자격증명 파일
- 초보자용 문서

저장소에 남기지 않는 것:

- 실제 자격증명
- 사용자 토큰
- 개인 로그
- 개인 캐시
- 개인 설정 파일

## 6. 관련 문서

- [프로젝트 메인 README](../README.md)
- [보관 문서: task나누기](archive/task나누기.md)
