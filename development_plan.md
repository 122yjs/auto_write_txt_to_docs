# Messenger Docs Auto Writer — 새로운 개발 계획

> **대상 버전**: v1.0.4 기준  
> **작성 목적**: 현재까지의 개발 상태와 장단점을 평가하고, 근본적인 페인포인트를 중심으로 중장기 개발 방향을 수립  
> **근거 문서**: `README.md`, `ux_evaluation.md`, `implementation_plan.md`, 소스 코드 정적 분석

---

## 1. 현재 개발 상태 요약

### 1.1 프로젝트 개요
- **형태**: Python 기반 Windows 데스크톱 GUI 애플리케이션
- **핵심 기능**: 특정 폴터의 `.txt` 파일을 감시 → 새로 추가된 줄만 추출 → Google Docs 문서 끝에 자동 기록
- **GUI 프레임워크**: `customtkinter` (라이트/다크 모드 지원)
- **주요 의존성**: `watchdog`, `google-api-python-client`, `pystray`, `psutil`, `Pillow`

### 1.2 코드 규모 및 구조

| 파일 | 라인 수 | 역할 |
|---|---|---|
| `main_gui.py` | **4,441** | 메인 윈도우, 상태 관리, 알림, 트레이, 이벤트 핸들러 |
| `src/.../backend_processor.py` | 1,048 | 파일 감시, 새 줄 추출, 중복 제거, Google Docs 기록 |
| `src/.../main_window_ui.py` | 1,040 | UI 위젯 빌더 (상태 패널, 설정 패널, 컨트롤 패널) |
| `src/.../app_dialogs.py` | 509 | 각종 다이얼로그 (마법사, 도움말, 오류, 설정) |
| `src/.../result_popup.py` | 359 | 화면 우하단 결과 팝업 (OS 작업 영역/DPI 고려) |
| `src/.../google_auth.py` | 355 | Google OAuth, Docs/Drive API 클라이언트 |
| `src/.../path_utils.py` | 157 | 설정/캐시/로그/인증 파일 경로 관리 |
| `src/.../config_manager.py` | 128 | 설정 읽기/쓰기, 백업/복원, 마이그레이션 |
| `tests/` | 16개 파일 | UI, 백엔드, 인증, 설정, 빌드 스크립트 등 단위 테스트 |

**총합**: 약 8,200라인 (테스트 제외)

### 1.3 CI/CD 및 배포
- GitHub Actions 기반 릴리즈 워크플로우 2개 (`release-windows.yml`, `internal-bundled-release.yml`)
- PowerShell 빌드 스크립트 (`scripts/build_release.ps1`)
- `pyproject.toml` + `setuptools` 기반 패키징
- 버전 관리: v1.0.0 → v1.0.4 (4차 릴리즈)

### 1.4 문서화 수준
- `README.md`: 상세한 사용법, FAQ, 문제 해결 가이드
- `ux_evaluation.md`: 코드 기반 정적 UX 평가 보고서 (5영역 × 강점/약점)
- `implementation_plan.md`: 높음·중간 우선순위 UX 개선 구현 계획 (5개 항목)
- `docs/release-notes-*.md`: 버전별 릴리즈 노트
- **→ 문서화가 매우 양호하며, 초보 사용자 친화적**

---

## 2. 장점 (Strengths)

### 2.1 사용자 경험 (UX) 설계
- **단계적 온볼딩**: `first_run` 플래그 → 첫 실행 마법사 → 인증 파일 확인 → 시작 가이드
- **4채널 알림 아키텍처**: 화면 팝업 + 트레이 알림 + Windows 효과음 + 인앱 로그
- **결과 팝업 품질**: OS 작업 영역·DPI 스케일·멀티모니터 고려, 라이트/다크 모드 색상 분리
  - 구체 구현: `MonitorFromWindow` + `GetMonitorInfo`로 작업 표시줄 영역 계산, `_get_window_scaling`으로 DPI 보정
- **준비도 체계**: 폴터/문서ID/정규식/캐시 크기를 종합 검증 후 CTA 활성화
- **중복 알림 Debounce**: 동일 오류 2초 내 반복 시 알림 억제
  - 구체 구현: `build_failure_notification_signature` + `should_emit_debounced_failure_notification`으로 `(file_path, error_type)` 해시 비교

### 2.2 신뢰성 및 안전성
- **토큰 격리(Quarantine)**: 잘못된 토큰을 삭제하지 않고 보존 (`token.invalid.{timestamp}.json`)
- **인증 예외 체계**: `GoogleAuthActionRequired`에 `reason_code` + `user_message` 포함
  - 구체 구현: `reason_code` (`TOKEN_EXPIRED`, `CREDENTIALS_MISSING`, `SCOPE_INSUFFICIENT`)에 따라 GUI에서 다른 안내 메시지 분기
- **자동 재시도**: Docs 기록 실패 시 5초 후 재시도 + 중복 큐잉 방지
  - 구체 구현: `schedule_retry`가 `threading.Timer`로 예약, `pending_retries` 집합으로 중복 방지
- **백업/복원**: JSON 기반 + `backup_date`/`backup_version` 메타데이터
- **레거시 마이그레이션**: 기존 `config.json` 자동 인식 및 이전

### 2.3 시스템 통합
- **트레이 상주**: 창 닫아도 트레이로 숨겨지며 감시 지속
- **트레이 상태 시각화**: ready/monitoring/processing/stopped/error 색상 점 표현
  - 구체 구현: `build_tray_status_icon`이 `PIL.ImageDraw.ellipse`로 16×16 색상 점 오버레이
- **Windows 시작 프로그램 연동**: `autostart_utils.py`로 시작 프로그램 폴터에 `.lnk` 생성/삭제
- **메모리 모니터링**: `psutil` 기반 10초 간격 메모리 표시 + 수동 GC 버튼

### 2.4 테스트 및 품질 관리
- 16개 테스트 파일로 UI, 백엔드, 인증, 설정, 빌드 스크립트 등 다영역 커버
  - 구체 목록: `test_main_window_ui.py`, `test_backend_processor.py`, `test_google_auth.py`, `test_config_manager.py`, `test_release_build_script.py` 등
- 릴리즈 전 정책 문서 (`release-policy.md`) 및 버전 메타데이터 관리

---

## 3. 페인포인트 및 단점 (Pain Points & Weaknesses)

### 3.1 🔴 치명적: 아키텍처 및 유지보수성

#### [P1] `main_gui.py`의 과도한 비대 (4,441줄)
- **문제**: 모든 사용자 인터랙션, 상태 관리, 비동기 처리, 알림, 트레이 로직이 단일 파일에 집중
- **영향**:
  - 기능 추가 시 충돌 위험 급증
  - 코드 리뷰 및 디버깅 비용 증가
  - 신규 기여자 진입 장벽 상승
- **근거**: `ux_evaluation.md` 7장 — "상태 관리 복잡성", "경쟁 조건 가능성", "일관성 문제" 모두 이 파일에서 유발
- **구체 코드**: `main_gui.py` L2595 `exit_application()`, L2575 `hide_window()`, L654 `run_startup_prompts()`, L875 `create_or_load_icon()` 등 서로 다른 도메인(생명주기/트레이/온볼딩/아이콘)이 하나의 클래스(`MessengerDocsApp`)에 몰려 있음

#### [P2] 수동 상태 관리의 복잡성
- **문제**: `is_monitoring`, `settings_changed`, `docs_target_locked`, `google_auth_operation_in_progress`, `first_run`, `show_help_on_startup` 등 7개 이상의 상태 플래그가 개별 변수로 산재
- **영향**: UI 갱신 메서드(`update_readiness_ui`, `update_monitoring_action_ui`, `update_runtime_summary_ui` 등)가 분산되어 있어 일부만 호출되면 UI 불일치 발생
- **근거**: `ux_evaluation.md` 7장 표 참조
- **구체 코드**: `main_gui.py`에서 `self.is_monitoring = True` 설정 후 `self.update_monitoring_action_ui()`는 호출되지만, `self.update_runtime_summary_ui()`나 `self.update_status()` 누락 시 상단 배지와 하단 상태바 불일치

#### [P3] 백그라운드 스레드 ↔ UI 스레드 동기화 미흡
- **문제**: `queue.Queue` + `root.after(0, ...)`로 통신하나, 경쟁 상태(race condition) 방어가 불완전
- **영향**: 간헐적인 UI 멈춤 또는 상태 표시 불일치 가능성
- **구체 코드**: `backend_processor.py`의 `file_queue`에 파일이 여러 개 동시에 들어올 때, `process_file` 낶에서 `docs_writer` 호출 → `main_gui.py`의 `queue.get()` 처리 후 `root.after(0, ...)`로 UI 업데이트. 이때 `self.is_monitoring`이 `False`로 바뀌어도 큐에 남은 파일은 계속 처리되어 "중지" 상태와 "처리 중" UI가 공존

### 3.2 🔴 치명적: 기능적 한계

#### [P4] 단일 문서 대상 제한
- **문제**: 여러 폴더를 감시하거나, 여러 Google Docs 문서에 동시 기록 불가
- **영향**: 사용자가 업무를 분리하고 싶을 때(예: 팀A 메신저 → 문서A, 팀B 메신저 → 문서B) 수동으로 문서를 번갈아 설정해야 함
- **근거**: `ux_evaluation.md` 2.2.3 — "단일 문서 대상만 지원"

#### [P5] 단일 파일 확장자 필터
- **문제**: `.txt` 외 확장자는 설정 가능하나, 하나의 확장자만 지정 가능
- **영향**: `.log`, `.md`, `.csv` 등 혼합된 파일 감시 불가

#### [P6] 감시 시작 시에야 Google 인증 발생
- **문제**: 모든 설정 완료 후 CTA 클릭 시점에 인증 흐름이 시작됨
- **영향**: 인증 실패 시 "다 준비했는데 안 되네" 실망감 + 설정→시작→실패→재설정 반복
- **근거**: `ux_evaluation.md` 2.2.1, `implementation_plan.md` 항목 4

### 3.3 🟡 중간: 사용자 경험 (UX) 마찰

#### [P7] 첫 실행 모달 폭포
- **문제**: 첫 실행 시 마법사 → 인증 확인 → 도움말 → 업데이트 확인이 순차적으로 뜸
- **영향**: 연속 모달 피로, "또 뭔가 떴다" 인상
- **근거**: `ux_evaluation.md` 1.2.1, `implementation_plan.md` 항목 3

#### [P8] 앱 종료 시 미저장 설정 자동 저장
- **문제**: `exit_application()`에서 `settings_changed`가 `True`면 사용자 확인 없이 자동 저장
- **영향**: 의도하지 않은 설정 변경을 되돌릴 수 없음
- **근거**: `ux_evaluation.md` 5.2.1, `implementation_plan.md` 항목 1

#### [P9] 핵심 모듈 import 실패 시 무음 폴백
- **문제**: `backend_processor`, `google_auth` 등이 `None`으로 폴백되어도 UI는 정상처럼 보임
- **영향**: 사용자가 "왜 동작 안 하지?" 혼란
- **근거**: `ux_evaluation.md` 4.2.2, `implementation_plan.md` 항목 2

#### [P10] 설정 유효성 검증 분산
- **문제**: 정규식 검증(입력 시), 캐시 크기(저장 시), 문서ID(시작 시)가 각각 다른 시점에 발동
- **영향**: 사용자가 언제 오류를 알게 되는지 예측 불가

### 3.4 🟡 중간: 브랜딩 및 시각적 완성도

#### [P11] 기본 아이콘 사용
- **문제**: `icon.png`가 없으면 64×64 파란색 사각형 생성
- **영향**: 트레이에서 다른 앱과 구별 어려움, 전문성 저하
- **근거**: `ux_evaluation.md` 6.2.1, `implementation_plan.md` 항목 5

#### [P12] 팝업 유지 시간 짧음
- **문제**: 성공 4초 / 실패 6초 후 팝업 사라짐
- **영향**: 다른 작업 중 결과 놓침, 히스토리 확인을 위해 로그 탭 이동 필요

### 3.5 🟢 낮음: 기타

#### [P13] 최근 결과 카드 3개 제한
- **문제**: `RECENT_RESULT_CARD_LIMIT = 3`으로 고정
- **영향**: 자리 비운 사이 많은 파일 처리 시 초기 결과 확인 불가

#### [P14] 트레이 호버 시 상태 텍스트 미표시
- **문제**: 아이콘 색상 점만으로 상태 파악해야 함
- **영향**: 색맹 사용자 또는 빠른 상태 확인 어려움

---

## 4. 새로운 개발 계획

> **방향성**: UX 개선(`implementation_plan.md`의 5개 항목)은 **단기(1~2주)**에 수행하고,  
> **근본적인 아키텍처 리팩토링과 기능 확장**은 **중기(1~2개월)**에 집중합니다.

---

### Phase 1: 단기 (1~2주) — UX 긴급 개선

이미 `implementation_plan.md`에 상세히 기술된 5개 항목을 우선 구현합니다.

| 우선순위 | 항목 | 기대 효과 | 관련 페인포인트 |
|:---:|---|---|---|
| 🔴 | **항목 1**: 앱 종료 시 미저장 설정 확인 (예/아니오/취소) | 설정 유실 방지 | P8 |
| 🔴 | **항목 2**: 핵심 모듈 import 실패 시 시각적 경고 배너 | 오동작 인지 불가 방지 | P9 |
| 🟡 | **항목 3**: 첫 실행 모달 통합 (스텝 위자드 1개로) | 모달 피로 감소 | P7 |
| 🟡 | **항목 4**: Google 연결 사전 테스트 버튼 | "시작해야 알 수 있는" 불안 해소 | P6 |
| 🟡 | **항목 5**: 앱 전용 아이콘 파일 번들 | 트레이 구별성 향상 | P11 |

**구현 전략**:
- `main_gui.py`가 4,400줄이므로 **항목별 순차 커밋** (회귀 방지)
- 각 항목 구현 후 `python main_gui.py` 수동 실행 검증
- 라이트/다크 모드 모두에서 색상 확인

---

### Phase 2: 중기 (3~6주) — 아키텍처 리팩토링

#### 2.1 [R1] `main_gui.py` 모듈화 분리

**목표**: 4,400줄의 단일 파일을 책임별로 분리하여 유지보수성과 테스트 용이성 확보

**분리 방안**:

```
src/auto_write_txt_to_docs/
├── main.py                    # 앱 진입점 (기존 if __name__ == "__main__")
├── app.py                     # MessengerDocsApp 클래스 (핵심 상태 + 위젯 바인딩, 300~500줄 목표)
├── controllers/
│   ├── lifecycle_controller.py     # 앱 생명주기 (종료, 트레이 최소화, 시작프롬프트)
│   ├── monitoring_controller.py    # 감시 시작/중지, 백엔드 스레드 관리
│   ├── google_auth_controller.py   # 인증 흐름, 서비스 요청, 토큰 관리
│   ├── settings_controller.py      # 설정 변경 추적, 저장, 백업/복원
│   └── notification_controller.py  # 팝업, 트레이, 효과음, 디바운스
├── models/
│   ├── app_state.py           # 상태 머신 (READY, MONITORING, PROCESSING, ERROR, AUTH_REQUIRED)
│   └── config_model.py        # 설정 데이터 클래스 + 유효성 검증
├── views/
│   ├── main_window.py         # 메인 윈도우 조립 (기존 create_widgets 흐름)
│   ├── tray_manager.py        # 트레이 아이콘, 메뉴, 상태 아이콘 생성
│   └── dialogs/               # 기존 app_dialogs.py 확장
├── services/
│   ├── file_watcher.py        # watchdog 래퍼 (기존 backend_processor의 감시 부분)
│   ├── docs_writer.py         # Google Docs 기록 (기존 backend_processor의 기록 부분)
│   └── cache_manager.py       # 전역 라인 캐시, processed_state 관리
└── utils/
    ├── ui_helpers.py          # 기존 유지
    ├── path_utils.py          # 기존 유지
    └── notification_helpers.py # 팝업 포맷, 미리보기 압축
```

**메서드 이동 계획 (구체적)**:

| 현재 위치 (main_gui.py) | 이동 대상 | 메서드명 |
|---|---|---|
| L2595 | `controllers/lifecycle_controller.py` | `exit_application()` |
| L2575 | `controllers/lifecycle_controller.py` | `hide_window()`, `show_window()` |
| L654 | `controllers/lifecycle_controller.py` | `run_startup_prompts()` |
| L875 | `views/tray_manager.py` | `create_or_load_icon()`, `build_tray_status_icon()` |
| 감시 CTA 핸들러 | `controllers/monitoring_controller.py` | `start_monitoring()`, `stop_monitoring()` |
| 설정 저장/복원 | `controllers/settings_controller.py` | `save_config()`, `load_config()`, `backup_settings()` |
| Google 인증 흐름 | `controllers/google_auth_controller.py` | `begin_google_service_request()`, `reauth_google()` |
| 결과 팝업 | `controllers/notification_controller.py` | `show_result_popup()`, `show_tray_notification()` |
| 상태 UI 갱신 | `views/main_window.py` | `update_readiness_ui()`, `update_monitoring_action_ui()` |

**상태 머신 도입**:
```python
# models/app_state.py
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional

class AppState(Enum):
    READY = "ready"
    AUTH_REQUIRED = "auth_required"
    MONITORING = "monitoring"
    PROCESSING = "processing"
    ERROR = "error"
    STOPPED = "stopped"

@dataclass
class AppContext:
    state: AppState = AppState.READY
    settings_changed: bool = False
    docs_target_locked: bool = False
    google_auth_in_progress: bool = False
    last_error: Optional[str] = None
    current_workspace_id: Optional[str] = None

    def transition_to(self, new_state: AppState) -> None:
        old_state = self.state
        self.state = new_state
        # TODO: 이벤트 버스로 상태 변경 알림
        print(f"State transition: {old_state.value} -> {new_state.value}")
```

- 상태 전환 시 자동으로 UI 갱신 메서드 일괄 호출 (Observer 패턴)
- `is_monitoring`, `settings_changed` 등 개별 플래그를 `AppContext`로 통합
- `AppContext.transition_to(AppState.MONITORING)` 호출 시, `MonitoringController`가 백엔드 스레드 시작 + `MainWindow`가 CTA 버튼 상태 변경 + `TrayManager`가 아이콘 색상 변경 — 한 곳에서 일괄 조정

**기대 효과**:
- 단일 파일 라인 수 4,400 → 300~500줄 (app.py)
- 기능 추가 시 영향 범위 명확화
- 단위 테스트 작성 용이성 향상

---

#### 2.2 [R2] 다중 폴더/문서 매핑 (Workspace 개념 도입)

**목표**: 단일 문서 제한을 해제하고, "워크스페이스" 단위로 여러 폴더-문서 쌍을 관리

**개념 정의**:
```python
# models/workspace.py
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import uuid

@dataclass
class Workspace:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "새 워크스페이스"
    watch_folders: List[str] = field(default_factory=list)
    docs_target: str = ""                    # Google Docs ID 또는 "new"
    file_extensions: List[str] = field(default_factory=lambda: [".txt"])
    regex_filter: Optional[str] = None
    is_active: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def validate(self) -> tuple[bool, Optional[str]]:
        """워크스페이스 설정 유효성 검증."""
        if not self.watch_folders:
            return False, "감시 폴터가 지정되지 않았습니다."
        if not self.docs_target:
            return False, "Google Docs 문서가 지정되지 않았습니다."
        for folder in self.watch_folders:
            if not os.path.isdir(folder):
                return False, f"감시 폴터를 찾을 수 없습니다: {folder}"
        if self.regex_filter:
            try:
                re.compile(self.regex_filter)
            except re.error as e:
                return False, f"정규식 오류: {e}"
        return True, None
```

**데이터 저장 방식**:
- **설정 파일**: 기존 `config.json`은 **앱 전역 설정**만 담당 (테마, 시작 프로그램, 업데이트 확인 등)
- **워크스페이스 파일**: `%APPDATA%\MessengerDocsAutoWriter\workspaces\` 폴터에 개별 JSON 저장
  - 파일명: `{workspace_id}.json`
  - 내용: `Workspace` dataclass를 JSON으로 직렬화
- **마이그레이션**: 기존 `config.json`의 `watch_folder`, `docs_input`, `file_extensions` 등을 읽어 `default` 워크스페이스 1개 자동 생성

**UI 변경**:
- **좌측 사이드바** (`customtkinter.CTkScrollableFrame`, 폭 200px):
  - 워크스페이스 목록 (이름 + 상태 아이콘)
  - 활성 워크스페이스는 테두리 강조
  - 우클릭 컨텍스트 메뉴: 편집, 복제, 삭제
  - 하단 "+ 새 워크스페이스" 버튼
- **메인 영역**:
  - 상단: 워크스페이스 이름 표시 (클릭 시 편집)
  - 설정 패널: 해당 워크스페이스의 폴터(다중 선택 가능), 문서, 확장자, 정규식
  - CTA 버튼: "이 워크스페이스 감시 시작"
- **동시 감시 지원**:
  - 여러 워크스페이스를 동시에 `MONITORING` 상태로 둘 수 있음
  - 각 워크스페이스별 독립적인 `watchdog.Observer` 스레드
  - 상태바에 "N개 워크스페이스 감시 중" 표시

**기대 효과**:
- 팀/프로젝트별 문서 분리 가능
- 하나의 앱 인스턴스로 여러 업무 동시 처리
- 관련 페인포인트: P4, P5

---

#### 2.3 [R3] 설정 시스템 개선

**a) 자동 저장 옵션 도입**:
- "설정 자동 저장" 토글 추가 (기본값: ON)
- ON일 때 설정 변경 즉시 저장 (Debounced, 500ms)
  - 구현: `SettingsController`가 각 설정 변수의 `trace_add("write")` 콜백에서 `after_cancel` + `after(500, self._save)` 호출
- OFF일 때 현재처럼 수동 저장 + 종료 시 확인
  - 이때 `settings_changed` 배지를 더 눈에 띄게 (노란색 깜빡임 효과)

**b) 유효성 검증 통합**:
- 설정 모델 레벨에서 `pydantic` 또는 `dataclass` + `__post_init__` 검증
  - 의존성 추가: `pydantic>=2.0` (JSON Schema 생성 및 유효성 검증 표준화)
- 입력 필드 `focusout` 시점에 검증 + 빨간 테두리 표시
  - 구현: 각 입력 위젯에 `<FocusOut>` 바인딩 → `SettingsController.validate_field(name, value)` → 오류 시 `widget.configure(border_color="#EF4444")` + 툴팁으로 오류 메시지
- 저장/시작 시점이 아닌 **입력 시점**에 즉시 피드백
  - 예: 정규식 필드에 `[invalid` 입력 → `FocusOut` 시 "정규식 오류: unterminated character set" 즉시 표시

**c) 설정 납부내기/가져오기**:
- JSON 파일로 설정 납부내기 (워크스페이스 포함)
  - 구조: `{"app_settings": {...}, "workspaces": [{...}, {...}]}`
  - 파일명: `messenger-docs-backup-{YYYY-MM-DD}.json`
- 다른 PC에서 설정 가져오기로 동일 환경 복제
  - 가져오기 시 워크스페이스 ID 충돌 방지를 위해 새 UUID 재생성

**기대 효과**:
- 설정 유실 방지, 사용자 예측 가능성 향상
- 관련 페인포인트: P8, P10

---

### Phase 3: 중기 (4~8주) — 기능 확장 및 고도화

#### 3.1 [E1] 사전 연결 테스트 및 상태 표시 강화

**이미 `implementation_plan.md` 항목 4에 기술됨. 추가 확장**:
- 상단 상태 배지에 Google 연결 상태 표시 (● 초록/노랑/빨강)
- 마지막 연결 테스트 시점 표시
- 주기적 연결 헬스체크 (감시 중일 때 5분 간격)

---

#### 3.2 [E2] 알림 시스템 고도화

**a) 팝업 히스토리 패널**:
- 최근 결과 카드 3개 제한 해제 → 스크롤 가능한 히스토리 패널
- 성공/중복/실패 필터링 가능
- 각 항목 클릭 시 상세 보기 (파일명, 추가된 줄 전체, 타임스탬프)

**b) 팝업 유지 시간 사용자 설정**:
- "알림 표시 시간" 슬라이더 (2초 ~ 30초, 기본 6초)
- "알림 유지" 옵션 (사용자가 닫을 때까지 유지)

**c) 이메일/웹훅 알림 (고급)**:
- 감시 폴더에 장시간(예: 1시간) 변경 없음 → 이메일 알림
- 처리 실패 N회 연속 발생 → 웹훅/이메일 알림

**기대 효과**:
- 장시간 자리 비움에도 결과 놓치지 않음
- 관련 페인포인트: P12, P13

---

#### 3.3 [E3] 로그 및 모니터링 대시보드

**a) 실행 로그 개선**:
- 구조화된 로그 (JSON Lines 형식) + 사람이 읽기 쉬운 텍스트 로그 병행
- 로그 레벨 필터 (DEBUG, INFO, WARNING, ERROR)
- 로그 파일 자동 순환 (1일 1파일, 7일 보관)

**b) 대시보드 탭 추가**:
- 시간대별 처리 파일 수 그래프
- 성공/중복/실패 비율 파이 차트
- 상위 N개 처리 파일 목록
- Google API 호출 횟수 및 지연 시간

**기대 효과**:
- 운영 가시성 확보, 장애 원인 분석 용이

---

#### 3.4 [E4] 플러그인/확장 시스템 (장기)

**목표**: 파일 처리 파이프라인을 플러그인화하여 사용자 정의 로직 주입 가능

**파이프라인 단계**:
```
[파일 감지] → [전처리 플러그인] → [중복 필터] → [후처리 플러그인] → [Docs 기록]
```

**예시 플러그인**:
- `MarkdownFormatterPlugin`: `.md` 파일의 마크다운 서식을 Google Docs 스타일로 변환
- `KeywordFilterPlugin`: 특정 키워드 포함 줄만 기록
- `TranslationPlugin`: 외국어 줄을 번역 후 기록
- `SummarizationPlugin`: 긴 내용을 요약 후 기록 (LLM 연동)

**구현 방식**:
- `plugins/` 폼더에 Python 파일 배치 → 앱 시작 시 자동 로드
  - 로드 순서: `plugins/__init__.py`가 없어도 `importlib.util.spec_from_file_location`으로 동적 임포트
- `BasePlugin` 추상 클래스 정의:

```python
# plugins/base.py
from abc import ABC, abstractmethod
from typing import List

class BasePlugin(ABC):
    name: str = "Unnamed Plugin"
    version: str = "1.0.0"
    description: str = ""

    @abstractmethod
    def preprocess(self, lines: List[str], file_path: str) -> List[str]:
        """중복 필터 전, 파일 내용 가공."""
        return lines

    @abstractmethod
    def postprocess(self, lines: List[str], file_path: str) -> List[str]:
        """중복 필터 후, Docs 기록 직전 가공."""
        return lines

# plugins/markdown_formatter.py
import re
from .base import BasePlugin

class MarkdownFormatterPlugin(BasePlugin):
    name = "Markdown Formatter"
    description = "마크다운 서식을 Google Docs 스타일 텍스트로 변환"

    def preprocess(self, lines, file_path):
        if not file_path.endswith(".md"):
            return lines
        result = []
        for line in lines:
            # ## 헤딩 → 【헤딩】
            line = re.sub(r"^##\s+(.*)", r"【\1】", line)
            # **볼드** → [볼드]
            line = re.sub(r"\*\*(.*?)\*\*", r"[\1]", line)
            result.append(line)
        return result

    def postprocess(self, lines, file_path):
        return lines
```

- 설정 UI에서 플러그인 ON/OFF 및 순서 조정
  - `plugins/enabled.json`에 `{"markdown_formatter": true, "keyword_filter": false}` 저장
  - 드래그 앤 드롭으로 실행 순서 변경

**기대 효과**:
- 커뮤니티 기여 가능성
- 특수한 업무 요구사항 자체 해결

---

#### 3.5 [E5] 크로스 플랫폼 지원 (장기)

**현재**: Windows 전용 (`winsound`, `pystray` Windows API, `autostart_utils` 레지스트리)

**단계적 확장**:
1. **macOS 지원**: `winsound` → `playsound` 또는 `pygame.mixer`, `autostart_utils` → `launchd`/`LoginItems`
2. **Linux 지원**: `pystray` AppIndicator, `autostart_utils` → `.desktop` 파일
3. **플랫폼 추상화 레이어**: `platform_services.py`로 OS별 구현 분리

**구체적 구현 (`platform_services.py`)**:
```python
import platform
import sys
from abc import ABC, abstractmethod

class PlatformService(ABC):
    @abstractmethod
    def play_sound(self, sound_type: str) -> None: ...
    @abstractmethod
    def set_autostart(self, enabled: bool) -> None: ...
    @abstractmethod
    def get_app_data_path(self) -> str: ...
    @abstractmethod
    def show_notification(self, title: str, message: str) -> None: ...

class WindowsService(PlatformService):
    def play_sound(self, sound_type):
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION if sound_type == "error" else winsound.MB_OK)
    def set_autostart(self, enabled):
        # 기존 autostart_utils.py 로직 재사용
        ...

class MacOSService(PlatformService):
    def play_sound(self, sound_type):
        import os
        os.system(f"afplay /System/Library/Sounds/{'Basso' if sound_type == 'error' else 'Glass'}.aiff")
    def set_autostart(self, enabled):
        # osascript로 LoginItems 추가/제거
        ...

class LinuxService(PlatformService):
    def play_sound(self, sound_type):
        import os
        os.system(f"paplay /usr/share/sounds/freedesktop/stereo/{'dialog-error' if sound_type == 'error' else 'complete'}.oga")
    def set_autostart(self, enabled):
        # ~/.config/autostart/ .desktop 파일 생성/삭제
        ...

def get_platform_service() -> PlatformService:
    system = platform.system()
    if system == "Windows":
        return WindowsService()
    elif system == "Darwin":
        return MacOSService()
    else:
        return LinuxService()
```

---

### Phase 4: 지속적 개선 (상시)

| 항목 | 활동 | 지표 |
|---|---|---|
| **성능** | 메모리 누수 모니터링, 캐시 효율화 | 메모리 사용량 24시간 추이 |
| **안정성** | Sentry 또는 유사 도구로 크래시 리포트 수집 | 크래시 발생률 |
| **사용자 피드백** | 앱 내 "피드백 보내기" 버튼 → GitHub Issue 자동 생성 | 월별 Issue 수 |
| **문서화** | 사용자 가이드 영상, 위키 확장 | 문서 페이지뷰 |
| **커뮤니티** | Discord/카카오톡 오픈채팅방 운영 | 참여자 수 |

---

## 5. 로드맵 시각화 (Week별 상세 Task Breakdown)

> **가정**: 1인 개발자 (Python 중급, customtkinter 경험 있음), 주 20시간 투자

```
2024년
├── 1월 (Week 1-2):  Phase 1 — UX 긴급 개선 5개 항목 구현
│                      └── v1.0.5 릴리즈
│   Week 1 (월-일):
│   ├── Day 1-2: 항목 1 (종료 시 미저장 설정 확인) 구현
│   │            → `exit_application()` 수정, `askyesnocancel` 추가
│   │            → `hide_window()` 알림 로직 추가
│   │            → 수동 테스트: 설정 변경 → X 닫기 → 트레이 종료 각 시나리오
│   ├── Day 3-4: 항목 2 (핵심 모듈 누락 배너) 구현
│   │            → `get_missing_critical_modules()` 추가
│   │            → `show_missing_module_banner()` 구현 (CTkFrame, fg_color 분기)
│   │            → 수동 테스트: `backend_processor.py` 임시 이름 변경 → 앱 시작
│   └── Day 5-7: 항목 3 (첫 실행 모달 통합) 구현
│                → `run_startup_prompts()` 리팩토링
│                → `_show_post_startup_prompts()` 신규
│                → `finish_wizard()`에 인증/업데이트 확인 추가
│                → 수동 테스트: `config.json` 삭제 → 앱 시작 → 마법사만 뜨는지 확인
│   Week 2 (월-일):
│   ├── Day 1-2: 항목 4 (Google 연결 테스트 버튼) 구현
│   │            → `main_window_ui.py`에 버튼 추가
│   │            → `test_google_connection()`, `_on_connection_test_success()` 추가
│   │            → `describe_google_request_purpose()`에 `"connection_test"` 케이스 추가
│   ├── Day 3-4: 항목 5 (전용 아이콘 생성) 구현
│   │            → AI 이미지 생성 (128×128, 투명 배경, 문서+펜 컨셉)
│   │            → `create_or_load_icon()` 경로 확장
│   │            → 트레이/타이틀바 아이콘 적용 확인
│   └── Day 5-7: 통합 테스트, README 업데이트, v1.0.5 릴리즈
│                → 기존 16개 테스트 실행 (회귀 방지)
│                → `docs/release-notes-v1.0.5.md` 작성
│                → GitHub Actions 릴리즈 워크플로우 실행
│
├── 1월~2월 (Week 3-6): Phase 2.1 — main_gui.py 모듈화 분리
│                          └── 상태 머신 도입, 컨트롤러/뷰 분리
│                          └── v1.1.0-alpha
│   Week 3 (월-일):
│   ├── Day 1-2: 디렉토리 구조 생성, `models/app_state.py` 구현
│   │            → `AppState` Enum, `AppContext` dataclass
│   │            → 단위 테스트: `test_app_state.py` (상태 전환, 컨텍스트 직렬화)
│   ├── Day 3-4: `controllers/` 생성 및 `LifecycleController` 이전
│   │            → `exit_application()`, `hide_window()`, `run_startup_prompts()` 이동
│   │            → `test_lifecycle_controller.py` 작성
│   └── Day 5-7: `MonitoringController` 이전
│                → `start_monitoring()`, `stop_monitoring()`, 백그라운드 스레드 관리
│                → `test_monitoring_controller.py` 작성 (Mock 사용)
│   Week 4 (월-일):
│   ├── Day 1-2: `GoogleAuthController` 이전
│   │            → `begin_google_service_request()`, `reauth_google()` 이동
│   │            → `test_google_auth_controller.py` 작성
│   ├── Day 3-4: `SettingsController` 이전
│   │            → `save_config()`, `load_config()`, `backup_settings()` 이동
│   │            → 자동 저장 Debounce 로직 구현
│   └── Day 5-7: `NotificationController` 이전
│                → `show_result_popup()`, `show_tray_notification()` 이동
│                → `test_notification_controller.py` 작성
│   Week 5-6 (월-일):
│   ├── `views/` 생성: `main_window.py`, `tray_manager.py`
│   ├── `app.py` 리팩토링: 300~500줄 목표
│   ├── 기존 `main_gui.py`와 병행 실행 (기능 동일성 검증)
│   └── 기존 16개 테스트 + 신규 테스트 모두 통과 확인
│
├── 2월~3월 (Week 7-10): Phase 2.2 — Workspace(다중 폴터/문서) 지원
│                           └── v1.1.0-beta
│   Week 7 (월-일):
│   ├── Day 1-2: `models/workspace.py` 구현
│   │            → `Workspace` dataclass, `validate()` 메서드
│   │            → `test_workspace.py` 작성
│   ├── Day 3-4: Workspace 저장/로드 (`workspace_manager.py`)
│   │            → `%APPDATA%\MessengerDocsAutoWriter\workspaces\` 폴터 관리
│   │            → JSON 직렬화/역직렬화
│   └── Day 5-7: 기존 설정 마이그레이션
│                → `config.json` → `default` Workspace 자동 생성
│                → 마이그레이션 테스트: v1.0.5 설정 → v1.1.0-beta 로드
│   Week 8-9 (월-일):
│   ├── 좌측 사이드바 UI 구현 (`customtkinter.CTkScrollableFrame`)
│   ├── 워크스페이스 CRUD (생성, 편집, 복제, 삭제)
│   ├── 워크스페이스 전환 시 설정 영역 업데이트
│   └── 다중 `watchdog.Observer` 관리 (워크스페이스별 독립 스레드)
│   Week 10 (월-일):
│   ├── 통합 테스트: 2개 이상 워크스페이스 동시 감시
│   ├── 성능 테스트: 메모리 사용량 측정 (워크스페이스 5개 기준)
│   └── v1.1.0-beta 릴리즈
│
├── 3월 (Week 11-12): Phase 2.3 — 설정 시스템 개선 (자동저장, 검증 통합)
│                      └── v1.1.0 릴리즈
│   Week 11 (월-일):
│   ├── Day 1-2: `pydantic` 도입
│   │            → `ConfigModel` Pydantic BaseModel 정의
│   │            → 각 필드별 `Field(..., description=...)` 추가
│   ├── Day 3-4: 입력 시점 유효성 검증 구현
│   │            → `<FocusOut>` 바인딩 → `SettingsController.validate_field()`
│   │            → 오류 시 `border_color="#EF4444"` + 툴팁
│   └── Day 5-7: 설정 납부내기/가져오기 구현
│                → JSON 형식 정의, 파일 선택 대화상자
│                → 가져오기 시 UUID 충돌 방지
│   Week 12 (월-일):
│   ├── 통합 테스트: 자동 저장 ON/OFF 각 시나리오
│   ├── UI 테스트: FocusOut 시 오류 표시 확인
│   ├── 기존 사용자 설정 호환성 검증 (마이그레이션)
│   └── v1.1.0 정식 릴리즈
│
├── 4월~5월 (Week 13-20): Phase 3 — 알림 고도화, 로그 대시보드
│                            └── v1.2.0 릴리즈
│   Week 13-14: 팝업 히스토리 패널 구현
│   Week 15-16: 알림 유지 시간 설정 + 이메일/웹훅 알림 프로토타입
│   Week 17-18: 구조화된 로그 (JSON Lines) + 대시보드 탭
│   Week 19-20: 통합 테스트, 성능 최적화, v1.2.0 릴리즈
│
└── 6월~ (Week 21+): Phase 4 — 플러그인 시스템, 크로스 플랫폼
                      └── v2.0.0 로드맵 수립
    Week 21-24: `BasePlugin` 추상 클래스, 동적 로드, UI 설정 패널
    Week 25-28: `platform_services.py` 추상화, macOS/Linux 구현
    Week 29+:   커뮤니티 피드백 수집, v2.0.0 기능 스펙 확정
```

**리소스 요구사항**:
| 항목 | 내용 | 예산/조건 |
|---|---|---|
| **인력** | Python 중급 개발자 1인 | - |
| **개발 환경** | Windows 10/11, Python 3.10+, VS Code | - |
| **디자인** | 앱 아이콘 1개 (128×128) | AI 이미지 생성 도구 또는 디자이너 외주 (~$50) |
| **테스트 환경** | Windows 가상 머신 1대 (Clean Install 테스트용) | VirtualBox 또는 VMware |
| **모니터링** | Sentry 무료 플랜 (오류 리포팅) | $0 |
| **배포** | GitHub Actions (Windows Runner) | $0 (공개 저장소) |
2024년
├── 1월 (Week 1-2):  Phase 1 — UX 긴급 개선 5개 항목 구현
│                      └── v1.0.5 릴리즈
│
├── 1월~2월 (Week 3-6): Phase 2.1 — main_gui.py 모듈화 분리
│                          └── 상태 머신 도입, 컨트롤러/뷰 분리
│                          └── v1.1.0-alpha
│
├── 2월~3월 (Week 7-10): Phase 2.2 — Workspace(다중 폴더/문서) 지원
│                           └── v1.1.0-beta
│
├── 3월 (Week 11-12): Phase 2.3 — 설정 시스템 개선 (자동저장, 검증 통합)
│                      └── v1.1.0 릴리즈
│
├── 4월~5월 (Week 13-20): Phase 3 — 알림 고도화, 로그 대시보드
│                            └── v1.2.0 릴리즈
│
└── 6월~ (Week 21+): Phase 4 — 플러그인 시스템, 크로스 플랫폼
                      └── v2.0.0 로드맵 수립
```

---

## 6. 마일스톤 및 검증 기준

### Milestone 1: v1.0.5 (Phase 1 완료)
- [ ] **종료 시 미저장 설정 확인 대화상자 구현**
  - **검증 시나리오 1a**: 설정 변경 → 메인 창 X 버튼 클릭 → "예" 선택 → 설정 저장 + 종료 확인
  - **검증 시나리오 1b**: 설정 변경 → 트레이 우클릭 → "종료" 선택 → "아니오" 선택 → 설정 저장 없이 종료 확인
  - **검증 시나리오 1c**: 설정 변경 → "취소" 선택 → 앱 종료되지 않고 상태 유지 확인
- [ ] **핵심 모듈 누락 시 경고 배너 구현**
  - **검증 시나리오 2**: `src/auto_write_txt_to_docs/backend_processor.py`를 `backend_processor.py.bak`로 이름 변경 → 앱 시작 → 상단 빨간 배너 "백엔드 처리(backend_processor) 모듈 누락" 표시 확인 → 원래 이름 복원 후 배너 사라짐 확인
- [ ] **첫 실행 모달 통합 (1개 마법사)**
  - **검증 시나리오 3**: `%APPDATA%\MessengerDocsAutoWriter\config.json` 삭제 → 앱 시작 → 첫 실행 마법사 1개만 표시 → 마법사 완료 후 300ms 후 인증 파일 확인 대화상자 → 800ms 후 업데이트 확인 (설정 ON 시) 순서 확인
- [ ] **Google 연결 테스트 버튼 추가**
  - **검증 시나리오 4**: 설정 패널에서 "연결 테스트" 클릭 → 성공 시 "✅ 연결 확인됨" 배지 + `messagebox.showinfo` 확인
- [ ] **전용 아이콘 번들**
  - **검증 시나리오 5**: `assets/icon.png` 배치 → 앱 시작 → 트레이 아이콘이 기본 파란 사각형이 아닌 전용 아이콘인지 확인 (64×64 픽셀 비교)
- [ ] **회귀 테스트**: 기존 16개 `unittest` 전체 통과

### Milestone 2: v1.1.0 (Phase 2 완료)
- [ ] **`main_gui.py` < 500줄, 책임별 모듈 분리 완료**
  - **검증 기준**: `wc -l main_gui.py` → 500줄 이하. `controllers/`, `views/`, `models/`, `services/` 폴터에 각각 2개 이상 파일 존재
  - **검증 기준**: `pylint` 또는 `flake8`로 순환 의존성(circular import) 없음 확인
- [ ] **상태 머신 (`AppState`) 도입 및 모든 상태 전환 테스트**
  - **검증 시나리오**: `test_app_state.py`에서 `READY → MONITORING → PROCESSING → READY`, `READY → ERROR → STOPPED → READY` 등 모든 상태 전환 경로 테스트
  - **검증 기준**: 상태 전환 시 Observer 콜백이 정확히 1회 호출되는지 `mock`으로 검증
- [ ] **Workspace CRUD (생성, 조회, 수정, 삭제) 기능**
  - **검증 시나리오**: "+ 새 워크스페이스" → 이름 "팀A" → 폴터 선택 → 저장 → 좌측 사이드바에 "팀A" 표시 → 이름 "팀B"로 수정 → 우클릭 "삭제" → 목록에서 제거
  - **검증 기준**: `%APPDATA%\MessengerDocsAutoWriter\workspaces\` 폴터에 JSON 파일 생성/수정/삭제 동기화 확인
- [ ] **다중 폴터/문서 매핑 동작 확인**
  - **검증 시나리오**: 워크스페이스1(폴터A→문서A), 워크스페이스2(폴터B→문서B) 생성 → 둘 다 감시 시작 → 폴터A에 `.txt` 추가 → 문서A에만 기록 → 폴터B에 `.txt` 추가 → 문서B에만 기록
  - **검증 기준**: `psutil`로 `watchdog` Observer 스레드가 2개 이상 실행 중인지 확인
- [ ] **설정 자동 저장 및 유효성 검증 통합**
  - **검증 시나리오**: 정규식 필드에 `[invalid` 입력 → 필드 밖 클릭 → 테두리 빨간색 + 툴팁 "정규식 오류" 표시 → 올바른 정규식 입력 → 테두리 정상 복귀
  - **검증 시나리오**: 자동 저장 ON → 설정 변경 → 500ms 대기 → `config.json`에 자동 반영 확인
- [ ] **기존 16개 테스트 + 신규 테스트 모두 통과**
  - **검증 기준**: `python -m unittest discover -s tests -p "test_*.py"` → Exit code 0, Coverage ≥ 70%

### Milestone 3: v1.2.0 (Phase 3 완료)
- [ ] **팝업 히스토리 패널 및 유지 시간 설정**
  - **검증 시나리오**: 5개 파일 연속 처리 → 히스토리 패널에 5개 항목 모두 표시 → "성공" 필터 클릭 → 성공 항목만 표시 → "유지 시간" 30초로 설정 → 팝업이 30초 후 사라짐 확인
- [ ] **구조화된 로그 + 대시보드 탭**
  - **검증 시나리오**: 앱 실행 1시간 → `%APPDATA%\...\logs\YYYY-MM-DD.jsonl` 파일에 JSON Lines 형식으로 기록 확인 → 대시보드 탭 클릭 → 시간대별 처리 파일 수 그래프 표시 확인
- [ ] **주기적 연결 헬스체크**
  - **검증 시나리오**: 감시 시작 → 5분 대기 → 백그라운드에서 Google API `documents.get` 호출 → 실패 시 상태바 "⚠️ Google 연결 끊김" 표시 → 자동 재연결 시도 → 성공 시 "준비" 복귀
- [ ] **사용자 정의 알림 (이메일/웹훅) 프로토타입**
  - **검증 시나리오**: 웹훅 URL 입력 → 처리 실패 3회 연속 발생 → 지정 URL로 JSON Payload `{"event": "failure_streak", "count": 3, ...}` POST 전송 확인 (Mock 서버 사용)

---

## 7. 리스크 및 대응

### 7.1 리스크 매트릭스

| 리스크 | 발생 가능성 | 영향 심각도 | 종합 위험도 | 대응 전략 |
|---|---|:---:|---|---|
| **main_gui.py 분리 중 회귀** | 중간 | 높음 | 🔴 **높음** | 기능별 브랜치 분리, 기존 16개 테스트 유지, 단계적 리팩토링 (Big Bang 금지) |
| **Google API 할당량 초과** | 낮음 | 중간 | 🟡 **중간** | API 호출 최소화 (캐싱, 배치 쓰기), 사용자별 자격증명 권장 |
| **사용자 설정 마이그레이션 실패** | 중간 | 중간 | 🟡 **중간** | `normalize_config_data` 강화, v1.0.x → v1.1.0 자동 마이그레이션 테스트 |
| **customtkinter 한계** | 낮음 | 낮음 | 🟢 **낮음** | 향후 PyQt/PySide 마이그레이션을 염두에 두고 뷰 레이어 완전 분리 |
| **Windows 외 플랫폼 복잡도** | 낮음 | 중간 | 🟢 **낮음** | Phase 4로 지연, 플랫폼 추상화 레이어 설계부터 시작 |
| **신규 버그로 인한 사용자 이탈** | 중간 | 높음 | 🔴 **높음** | Canary 릴리즈 채널 도입, 핵심 사용자 그룹 베타 테스트 |

### 7.2 구체적 대응 절차

#### 리스크 1: `main_gui.py` 분리 중 회귀

**예방**:
1. **브랜치 전략**: `feat/refactor-lifecycle`, `feat/refactor-monitoring` 등 기능별 브랜치로 분리. 각 브랜치는 독립적으로 PR 생성.
2. **Big Bang 금지**: 한 번에 모든 코드를 옮기지 않고, 한 개의 Controller씩 이전. 각 이전 후 `python main_gui.py`로 수동 실행 확인.
3. **테스트 유지**: 기존 16개 테스트가 깨지지 않도록, 이전 대상 메서드의 **시그니처(인자/반환값)**는 변경하지 않음.

**감지**:
- 각 PR마다 GitHub Actions로 `unittest discover` 자동 실행
- PR 리뷰어는 반드시 "기존 테스트 통과 + 수동 실행 확인" 코멘트 필수

**복구 (롤백)**:
- 문제 발생 시 해당 기능 브랜치만 `git revert` → `main`은 안정 상태 유지
- 롤백 후 문제 브랜치에서 디버깅, 재시도

#### 리스크 2: 사용자 설정 마이그레이션 실패

**예방**:
1. **마이그레이션 코드 분리**: `migrations/v1_0_5_to_v1_1_0.py`에 마이그레이션 로직 격리
2. **설정 백업 자동 생성**: 마이그레이션 실행 전 `config.json`을 `config.json.backup.{timestamp}`로 자동 복사
3. **점진적 롤아웃**: v1.1.0-alpha를 소수 베타 사용자(5명)에게 배포 후 피드백 수집

**감지**:
- 앱 시작 시 마이그레이션 결과 로깅: `"migration_status": "success"` 또는 `"failed_reason": ...`
- Sentry에 마이그레이션 예외 자동 리포트

**복구**:
- 마이그레이션 실패 감지 → 자동으로 백업 파일 복원 → 사용자에게 "설정 복원 완료" 알림
- 수동 복구 가이드: `%APPDATA%\MessengerDocsAutoWriter\`에서 `config.json.backup.*`을 `config.json`으로 이름 변경

#### 리스크 3: 신규 버그로 인한 사용자 이탈

**예방**:
1. **Canary 릴리즈**: `v1.1.0-canary.1`, `v1.1.0-canary.2` 등 사전 릴리즈 태그로 1~2주간 핵심 사용자 테스트
2. **자동 업데이트 OFF 유지**: 현재 정책대로 자동 업데이트는 하지 않고, 다운로드 페이지 안낧만 제공

**감지**:
- GitHub Issues에서 "버그" 라벨 이슈 주간 모니터링
- Sentry 크래시 리포트 알림 (Slack 또는 이메일)

**복구**:
- 치명적 버그 발견 시 이전 안정 버전(v1.0.5 또는 v1.1.0)으로 릴리즈 노트에 롤백 권장 공지
- `docs/hotfix-rollback-guide.md`에 롤백 절차 문서화 (설치 폴터 삭제 → 이전 버전 재설치)

### 7.3 모니터링 지표 및 임계값

| 지표 | 측정 방법 | 정상 범위 | 경고 임계값 | 치명 임계값 |
|---|---|---|---|---|
| **앱 시작 성공률** | Sentry 세션 수 / 릴리즈 다운로드 수 | ≥ 95% | < 90% | < 80% |
| **Google API 오류율** | `google_auth.py` 로그 분석 | < 1% | ≥ 5% | ≥ 10% |
| **메모리 사용량** | `psutil.Process().memory_info().rss` | < 150MB | ≥ 200MB | ≥ 300MB |
| **마이그레이션 실패율** | Sentry 이벤트 + 사용자 피드백 | 0% | ≥ 1건 | ≥ 3건 |
| **UI 응답 지연** | 수동 측정 (CTA 클릭 ~ 팝업 표시) | < 2초 | ≥ 3초 | ≥ 5초 |

**조치**:
- 경고 임계값 도달: GitHub Issue 생성, 다음 주 개발 일정에 버그 수정 우선 배정
- 치명 임계값 도달: 즉시 핫픽스 브랜치 생성, Canary 채널 중단, 안정 버전 롤백 권장

---

## 8. 결론

이 프로젝트는 **"파일 감시 → Google Docs 자동 기록"**이라는 단일 흐름을 매우 잘 구현했으며, 초보 사용자를 위한 안내 구조와 다채널 알림 시스템은 데스크톱 앱의 모범 사례에 가깝습니다.

그러나 **4,400줄의 단일 파일**과 **수동 상태 관리**, **단일 문서 제한**은 기능 확장의 명백한 병목입니다. `implementation_plan.md`의 5개 UX 개선 항목을 먼저 적용하여 즉각적인 사용자 만족도를 높인 후, **Phase 2의 아키텍처 리팩토링과 Workspace 개념 도입**을 통해 프로젝트의 천장을 높여야 합니다.

**핵심 성공 지표**:
1. `main_gui.py` 라인 수 < 500줄 (3개월 내)
2. 사용자가 2개 이상의 워크스페이스를 생성하여 사용 (릴리즈 후 1개월)
3. GitHub Issue 중 "왜 동작 안 하나요?" → 0건 (항목 2 배너 적용 후)

> **다음 행동**: `feat/ux-improvements` 브랜치를 생성하여 Phase 1 항목 1부터 순차 구현을 시작합니다.
