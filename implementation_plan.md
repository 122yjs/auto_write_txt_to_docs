# UX 개선 구현 계획 — 높음·중간 우선순위

> **근거**: [UX 평가 보고서](file:///C:/Users/JSD3/.gemini/antigravity/brain/a68abd65-6e40-43f7-98b6-fa207d81b416/ux_evaluation.md)  
> **대상 브랜치**: `main` → `feat/ux-improvements` (신규 생성)  
> **영향 파일**: `main_gui.py`, `main_window_ui.py`, 아이콘 에셋

---

## User Review Required

> [!IMPORTANT]
> 아래 5개 항목 모두 `main_gui.py` 수정이 포함됩니다. 이 파일이 4,328줄로 매우 커서, 한 번에 모든 항목을 반영하면 회귀 위험이 있습니다. **항목별 순차 커밋** 전략을 권장합니다.

> [!WARNING]
> **항목 3(첫 실행 모달 통합)**은 `run_startup_prompts` + `show_first_run_wizard` + `show_help_dialog` + `check_credentials_file`의 흐름을 변경합니다. 기존 첫 실행 경험이 크게 바뀌므로 충분한 수동 테스트가 필요합니다.

---

## Proposed Changes

### 항목 1: 앱 종료 시 미저장 설정 확인 🔴

**문제**: 현재 `exit_application()` (L2595)에서 `settings_changed`가 `True`이면 **사용자 확인 없이 자동 저장**합니다. 또한 `hide_window()` (L2575)로 창을 숨길 때는 아무 검사도 하지 않습니다. 사용자가 의도하지 않은 설정 변경을 되돌리고 싶어도 이미 저장되는 문제가 있습니다.

**변경 방향**: 저장 여부를 사용자에게 물어보는 흐름으로 전환합니다.

---

#### [MODIFY] [main_gui.py](file:///e:/PYTHONWORKSPACE/auto_write_txt_to_docs/main_gui.py)

**1-a. `exit_application()` 수정 (L2595~2651)**

현재:
```python
# 3. 설정 자동 저장 (변경사항이 있는 경우)
if hasattr(self, 'settings_changed') and self.settings_changed:
    try:
        self.save_config()
        self.log("종료 시 설정 자동 저장 완료.")
    except Exception as e:
        self.log(f"종료 시 설정 저장 실패: {e}")
```

변경:
```python
# 3. 미저장 설정 확인 (사용자에게 선택권 부여)
if hasattr(self, 'settings_changed') and self.settings_changed:
    try:
        # 창이 숨겨진 상태라면 먼저 보여준다
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
        answer = messagebox.askyesnocancel(
            "설정 저장 확인",
            "저장되지 않은 설정 변경사항이 있습니다.\n\n"
            "저장하시겠습니까?\n"
            "• 예: 저장 후 종료\n"
            "• 아니오: 저장하지 않고 종료\n"
            "• 취소: 종료 취소",
            parent=self.root,
        )
        if answer is None:  # 취소
            self.log("종료 취소됨 (미저장 설정 보존)")
            return
        if answer:  # 예
            self.save_config()
            self.log("종료 시 설정 저장 완료.")
    except Exception as e:
        self.log(f"종료 시 설정 저장 확인 중 오류: {e}")
```

**핵심**: `askyesnocancel`으로 3가지 선택지 제공 — "예(저장 후 종료)", "아니오(버리고 종료)", "취소(종료 안 함)"

**1-b. `hide_window()` 수정 (L2575~2582)**

트레이로 숨길 때는 설정 저장을 강제하지 않되, 감시 중이 아닌 상태에서 미저장 설정이 있으면 간단한 알림을 남깁니다.

```python
def hide_window(self):
    if not self.tray_icon:
        self.log("트레이 아이콘이 없어 창 숨김 대신 종료를 진행합니다.")
        self.exit_application()
        return
    if self.settings_changed and not self.is_monitoring:
        self.log("알림: 저장되지 않은 설정이 있습니다. 트레이 '종료' 시 저장 여부를 확인합니다.")
    self.root.withdraw()
    self.log("창 숨김. 트레이 아이콘 우클릭으로 메뉴 사용.")
```

---

### 항목 2: 핵심 모듈 import 실패 시 시각적 경고 🔴

**문제**: `run_monitoring`, `get_google_services`, `build_main_window_ui` 등 핵심 모듈이 `None`으로 폴백되면 앱이 실행되지만 기능이 동작하지 않습니다. 사용자는 "왜 안 되지?"라고 혼란을 겪습니다.

**변경 방향**: 앱 초기화 시 누락 모듈을 검사하고, 누락이 발견되면 메인 UI 상단에 눈에 띄는 경고 배너를 표시합니다.

---

#### [MODIFY] [main_gui.py](file:///e:/PYTHONWORKSPACE/auto_write_txt_to_docs/main_gui.py)

**2-a. 누락 모듈 검사 함수 추가 (import 구문 뒤, L156 부근)**

```python
def get_missing_critical_modules():
    """필수 모듈의 누락 여부를 검사하고 목록을 반환한다."""
    checks = [
        (run_monitoring, "백엔드 처리(backend_processor)"),
        (get_google_services, "Google 인증(google_auth)"),
        (build_main_window_ui, "메인 UI(main_window_ui)"),
        (load_app_config, "설정 관리(config_manager)"),
    ]
    return [name for module, name in checks if module is None]
```

**2-b. `MessengerDocsApp.__init__()` 수정 — 위젯 생성 직후 배너 삽입**

`create_widgets()` 직후(L566 부근)에 누락 모듈 배너를 조건부로 표시:

```python
# --- 위젯 생성 ---
self.create_widgets()

# --- 누락 모듈 경고 배너 ---
self.missing_modules = get_missing_critical_modules()
if self.missing_modules:
    self.show_missing_module_banner()
```

**2-c. 배너 표시 메서드 신규 추가**

```python
def show_missing_module_banner(self):
    """핵심 모듈 누락 시 메인 화면 상단에 경고 배너를 표시한다."""
    banner = ctk.CTkFrame(self.root, fg_color=("#FEE2E2", "#7F1D1D"), corner_radius=12, height=56)
    banner.pack(fill="x", padx=14, pady=(8, 0), before=self.main_frame)

    module_list = ", ".join(self.missing_modules)
    ctk.CTkLabel(
        banner,
        text=f"⚠️ 일부 핵심 모듈을 불러오지 못했습니다: {module_list}",
        font=self.build_ui_font(13, "bold"),
        text_color=("#991B1B", "#FCA5A5"),
        wraplength=700,
        justify="left",
        anchor="w",
    ).pack(fill="x", padx=16, pady=12)
    self.missing_module_banner = banner
```

#### [MODIFY] [main_window_ui.py](file:///e:/PYTHONWORKSPACE/auto_write_txt_to_docs/src/auto_write_txt_to_docs/main_window_ui.py)

변경 없음 — 배너는 `build_main_window_ui`가 반환한 `main_frame` **앞**에 삽입하므로 UI 빌더 변경 불필요.

---

### 항목 3: 첫 실행 모달 통합 🟡

**문제**: 첫 실행 시 `run_startup_prompts()` (L654)에서 최대 4개의 모달이 순차적으로 뜹니다:
1. `show_first_run_wizard` (400ms 후)
2. `check_credentials_file` → 인증 파일 누락 시 `credentials_wizard`
3. `show_help_dialog` (400ms 후, first_run이 아닐 때)
4. `check_for_updates_async` (900ms 후)

**변경 방향**: 첫 실행(`first_run=True`) 시에는 **기존 3스텝 마법사 안에 인증 파일 확인을 통합**하고, 마법사 완료 후에만 업데이트 확인을 실행하도록 순서를 정리합니다.

---

#### [MODIFY] [main_gui.py](file:///e:/PYTHONWORKSPACE/auto_write_txt_to_docs/main_gui.py)

**3-a. `run_startup_prompts()` 리팩터링 (L654~664)**

현재:
```python
def run_startup_prompts(self):
    if self.first_run.get():
        self.root.after(400, self.show_first_run_wizard)
        return   # ← 여기서 return하므로 인증 확인, 도움말, 업데이트가 실행 안 됨

    self.check_credentials_file()
    if self.show_help_on_startup.get():
        self.root.after(400, self.show_help_dialog)
    if self.check_updates_on_startup.get():
        self.root.after(900, lambda: self.check_for_updates_async(user_initiated=False))
```

변경:
```python
def run_startup_prompts(self):
    if self.first_run.get():
        # 첫 실행 마법사가 인증 확인까지 통합 처리
        # 마법사 완료 콜백에서 업데이트 확인 실행
        self.root.after(400, self.show_first_run_wizard)
        return

    self.check_credentials_file()
    # 도움말과 업데이트 확인은 하나의 딜레이로 통합
    self.root.after(400, self._show_post_startup_prompts)

def _show_post_startup_prompts(self):
    """첫 실행이 아닐 때, 도움말과 업데이트 확인을 순차적으로 실행한다."""
    if self.show_help_on_startup.get():
        self.show_help_dialog()
    if self.check_updates_on_startup.get():
        # 도움말이 표시된 경우 잠시 지연 후 실행
        delay = 600 if self.show_help_on_startup.get() else 0
        self.root.after(delay, lambda: self.check_for_updates_async(user_initiated=False))
```

**3-b. `show_first_run_wizard` → `finish_wizard()` 에 인증 확인 + 업데이트 확인 추가 (L3403)**

현재:
```python
def finish_wizard():
    release_wizard_traces()
    self.first_run.set(False)
    self.save_config()
    self.log("첫 실행 설정 마법사 완료.")
    self.first_run_wizard = None
    wizard.destroy()
```

변경:
```python
def finish_wizard():
    release_wizard_traces()
    self.first_run.set(False)
    self.save_config()
    self.log("첫 실행 설정 마법사 완료.")
    self.first_run_wizard = None
    wizard.destroy()
    # 마법사 완료 후 인증 파일 확인 및 업데이트 확인
    self.root.after(300, self.check_credentials_file)
    if self.check_updates_on_startup.get():
        self.root.after(800, lambda: self.check_for_updates_async(user_initiated=False))
```

**효과**: 첫 실행 시 마법사 1개만 뜨고, 나머지는 마법사 완료 후에 자연스럽게 이어집니다.

---

### 항목 4: Google 연결 사전 테스트 버튼 🟡

**문제**: 사용자가 감시 시작 CTA를 눌러야 비로소 Google 인증이 진행됩니다. 설정만 해놓고 "이게 제대로 연결되는지"를 미리 확인할 수 없어 불안합니다.

**변경 방향**: 설정 영역의 Google 인증 관련 UI 근처에 **"Google 연결 테스트"** 버튼을 추가합니다. 기존 `begin_google_service_request`를 재활용하되, purpose를 `"connection_test"`로 구분합니다.

---

#### [MODIFY] [main_window_ui.py](file:///e:/PYTHONWORKSPACE/auto_write_txt_to_docs/src/auto_write_txt_to_docs/main_window_ui.py)

**4-a. `_build_control_panel()` 내부에 "연결 테스트" 버튼 추가**

기존 "Google 계정 재연결" 버튼(`reauth_button`) 옆에 테스트 버튼을 배치:

```python
test_connection_button = ctk.CTkButton(
    button_row,
    text="연결 테스트",
    width=110,
    height=34,
    corner_radius=10,
    command=callbacks["test_google_connection"],
    font=_font(ctk, 12, "bold", family=font_family),
    fg_color=("gray85", "gray28"),
    hover_color=("gray78", "gray34"),
    text_color=("gray20", "gray92"),
)
test_connection_button.pack(side="right", padx=(0, 8))
```

`widget_refs`에 `"test_connection_button": test_connection_button` 추가.

#### [MODIFY] [main_gui.py](file:///e:/PYTHONWORKSPACE/auto_write_txt_to_docs/main_gui.py)

**4-b. 콜백 메서드 및 결과 처리 추가**

```python
def test_google_connection(self):
    """Google 연결을 사전에 테스트하고 결과를 알려준다."""
    self.begin_google_service_request(
        purpose="connection_test",
        require_drive=False,
        on_success=self._on_connection_test_success,
    )

def _on_connection_test_success(self, google_services):
    """연결 테스트 성공 시 안내를 표시한다."""
    self.google_auth_operation_in_progress = False
    if hasattr(self, "google_connection_status_var"):
        self.google_connection_status_var.set("✅ 연결 확인됨")
    self.update_status("준비", "Google 연결 테스트 성공")
    self.update_monitoring_action_ui()
    messagebox.showinfo(
        "연결 테스트 성공",
        "Google Docs 서비스에 정상적으로 연결되었습니다.\n감시를 시작할 수 있습니다.",
        parent=self.root,
    )
```

**4-c. `callbacks` 딕셔너리에 `"test_google_connection"` 추가**

`create_widgets()` 내 callbacks 전달 시 해당 키를 추가.

**4-d. `describe_google_request_purpose()` 에 `"connection_test"` 케이스 추가**

```python
elif purpose == "connection_test":
    return "인증 연결 테스트"
```

---

### 항목 5: 앱 전용 아이콘 생성 및 번들 🟡

**문제**: 별도 `icon.png`가 없으면 64×64 파란색 사각형 아이콘이 생성되어 다른 앱 트레이 아이콘과 구별이 어렵습니다. 현재 프로젝트 어디에도 `.png` 아이콘 파일이 없습니다.

**변경 방향**: 앱 아이덴티티를 나타내는 전용 아이콘을 AI 이미지 생성 도구로 제작하고, 프로젝트에 포함합니다.

---

#### [NEW] `assets/icon.png`

- 이미지 생성 도구를 사용해 **"문서 자동 기록"** 컨셉의 전용 앱 아이콘을 제작합니다
- 128×128px, 투명 배경, 파란/초록 톤의 문서+펜 아이콘
- 트레이(64px), 타이틀바(32px)에서 모두 잘 보이도록 미니멀 디자인

#### [MODIFY] [main_gui.py](file:///e:/PYTHONWORKSPACE/auto_write_txt_to_docs/main_gui.py)

**5-a. `create_or_load_icon()` 수정 (L875)**

아이콘 검색 경로를 프로젝트 `assets/` 폴더도 포함하도록 확장:

```python
def create_or_load_icon(self):
    icon_candidates = [
        os.path.join(os.path.dirname(__file__), "assets", "icon.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png"),
        "icon.png",
    ]
    for icon_path in icon_candidates:
        if os.path.exists(icon_path):
            try:
                self.base_icon_image = Image.open(icon_path)
                self.log(f"아이콘 파일 로드 성공: {icon_path}")
                break
            except Exception as e:
                self.log(f"경고: 아이콘 로드 실패 ({icon_path}): {e}")
    else:
        self.log("정보: 아이콘 파일 없음. 기본 아이콘을 생성합니다.")
        self.base_icon_image = self.create_default_icon()

    self.icon_image = self.build_tray_status_icon("ready") or self.base_icon_image
```

---

## Open Questions

> [!IMPORTANT]
> **항목 1 관련**: 트레이에서 바로 "종료"를 누를 때도 미저장 설정 확인 대화상자를 표시할지, 아니면 트레이 종료는 즉시 종료로 할지 결정이 필요합니다. 현재 계획은 **트레이 종료도 동일하게 확인**하는 방향입니다.

> [!IMPORTANT]
> **항목 5 관련**: 아이콘 디자인 방향에 대해 선호하는 스타일이 있으시면 알려주세요. (미니멀, 3D, 플랫 등) 기본 방향은 Google Material 스타일의 플랫 아이콘입니다.

---

## Verification Plan

### Automated Tests

각 항목별 동작 확인을 위한 수동 시나리오:

| 항목 | 검증 시나리오 |
|---|---|
| 1 | 설정 변경 → X 닫기 → 트레이에서 종료 → "예/아니오/취소" 각각 검증 |
| 2 | `backend_processor.py`를 임시로 이름 변경 → 앱 시작 → 배너 표시 확인 |
| 3 | `config.json` 삭제(first_run=True) → 앱 시작 → 마법사만 뜨는지, 완료 후 인증/업데이트 확인 순서 확인 |
| 4 | 설정 완료 → "연결 테스트" 클릭 → 성공/실패 메시지 확인 |
| 5 | `assets/icon.png` 배치 → 트레이 아이콘이 기본 사각형이 아닌 전용 아이콘인지 확인 |

### Manual Verification

- 각 항목 커밋 후 `python main_gui.py`로 실제 실행 확인
- 라이트/다크 모드 모두에서 배너·버튼·대화상자 색상 확인
- `settings_changed` 플래그가 정확하게 추적되는지 시나리오별 확인
