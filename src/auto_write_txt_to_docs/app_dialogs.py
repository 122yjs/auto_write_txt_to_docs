def _resolve_ctk(ctk_module=None):
    """대화상자 생성에 사용할 customtkinter 모듈을 반환한다."""
    if ctk_module is not None:
        return ctk_module

    import customtkinter as ctk

    return ctk


def _center_dialog_window(window, center_window_func=None):
    """대화상자를 화면 중앙에 배치한다."""
    if center_window_func:
        center_window_func(window)
        return

    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


# ---------------------------------------------------------------------------
#  도움말 (시작 가이드) 대화상자
# ---------------------------------------------------------------------------

def _get_help_sections():
    """도움말 대화상자에 표시할 섹션 목록을 반환한다.

    각 섹션은 (아이콘, 제목, 본문_리스트) 튜플이다.
    본문_리스트의 각 항목은 한 줄로 표시된다.
    """
    return [
        (
            "\U0001F4CB",  # 📋
            "이 프로그램이 하는 일",
            [
                "지정한 폴더에서 텍스트 파일(.txt)의 변경을 감지하고,",
                "새 내용을 Google Docs 문서에 자동으로 이어 기록합니다.",
            ],
        ),
        (
            "\U0001F527",  # 🔧
            "시작 전 준비 \u2014 3단계",
            [
                "\u2460 감시 폴더  \u279C  '폴더 선택' 버튼으로 txt 파일이 저장될 폴더 지정",
                "\u2461 문서 연결  \u279C  Google Docs URL/ID 입력, 또는 '새 문서 만들기'",
                "\u2462 설정 저장  \u279C  '설정 저장' 클릭 (다음 실행 시에도 유지)",
            ],
        ),
        (
            "\U0001F680",  # 🚀
            "사용 흐름",
            [
                "'감시 시작' 클릭 \u2192 폴더 내 파일 변경 자동 감지",
                "새 내용은 타임스탬프와 함께 Docs 끝에 추가",
                "'감시 중지' 클릭으로 언제든 중단 가능",
            ],
        ),
        (
            "\U0001F514",  # 🔔
            "트레이 아이콘",
            [
                "창을 닫아도 트레이에서 계속 실행됩니다.",
                "트레이 아이콘 우클릭 \u2192 창 열기 / 종료",
            ],
        ),
        (
            "\u2753",  # ❓
            "문제가 생겼을 때",
            [
                "인증 오류 \u2192 인증 파일(developer_credentials.json) 확인",
                "연결 오류 \u2192 인터넷 연결 상태 확인",
                "권한 오류 \u2192 Google 계정의 문서 편집 권한 확인",
                "하단 로그 창 또는 '로그 폴더 열기'에서 상세 내역 확인",
            ],
        ),
    ]


def build_help_guide_text():
    """도움말 대화상자 본문 텍스트를 반환한다 (하위 호환용 폴백)."""
    lines = []
    for icon, title, body in _get_help_sections():
        lines.append(f"{icon} {title}")
        for item in body:
            lines.append(f"  {item}")
        lines.append("")
    return "\n".join(lines).strip()


def _build_help_section_card(parent_frame, icon, title, body_lines, ctk, ui_font_family=None):
    """도움말 섹션 하나를 카드 형태 프레임으로 생성한다."""
    card = ctk.CTkFrame(parent_frame, corner_radius=10)
    card.pack(fill="x", padx=4, pady=(0, 10))

    # 헤더: 아이콘 + 제목
    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=14, pady=(12, 4))

    ctk.CTkLabel(
        header,
        text=icon,
        font=ctk.CTkFont(family=ui_font_family, size=22),
        width=28,
    ).pack(side="left", padx=(0, 6))

    ctk.CTkLabel(
        header,
        text=title,
        font=ctk.CTkFont(family=ui_font_family, size=15, weight="bold"),
        anchor="w",
    ).pack(side="left", fill="x", expand=True)

    # 본문
    body_frame = ctk.CTkFrame(card, fg_color="transparent")
    body_frame.pack(fill="x", padx=20, pady=(0, 12))

    for line in body_lines:
        ctk.CTkLabel(
            body_frame,
            text=line,
            font=ctk.CTkFont(family=ui_font_family, size=13),
            anchor="w",
            justify="left",
            wraplength=580,
        ).pack(fill="x", anchor="w", pady=1)


def show_help_dialog(parent, show_help_on_startup, ui_font_family=None, on_window_close=None, ctk_module=None, center_window_func=None):
    """도움말 대화상자를 생성해 표시한다."""
    ctk = _resolve_ctk(ctk_module)

    help_window = ctk.CTkToplevel(parent)
    help_window.title("시작 가이드")
    help_window.geometry("680x560")
    help_window.minsize(580, 480)
    help_window.transient(parent)
    help_window.grab_set()

    # -- 외곽 컨테이너 --
    outer = ctk.CTkFrame(help_window, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=16, pady=16)

    # 제목
    ctk.CTkLabel(
        outer,
        text="메신저 Docs 자동 기록",
        font=ctk.CTkFont(family=ui_font_family, size=22, weight="bold"),
    ).pack(pady=(0, 2))

    ctk.CTkLabel(
        outer,
        text="빠른 시작 가이드",
        font=ctk.CTkFont(family=ui_font_family, size=14),
        text_color="gray",
    ).pack(pady=(0, 12))

    # -- 스크롤 영역: 섹션 카드들 --
    scroll_area = ctk.CTkScrollableFrame(outer, corner_radius=8)
    scroll_area.pack(fill="both", expand=True)

    for icon, title, body_lines in _get_help_sections():
        _build_help_section_card(scroll_area, icon, title, body_lines, ctk, ui_font_family=ui_font_family)

    # -- 하단 바: 체크박스 + 닫기 --
    bottom_bar = ctk.CTkFrame(outer, fg_color="transparent")
    bottom_bar.pack(fill="x", pady=(12, 0))

    ctk.CTkCheckBox(
        bottom_bar,
        text="시작할 때 이 가이드 표시",
        variable=show_help_on_startup,
        onvalue=True,
        offvalue=False,
        font=ctk.CTkFont(family=ui_font_family, size=13),
    ).pack(side="left")

    ctk.CTkButton(
        bottom_bar,
        text="닫기",
        command=help_window.destroy,
        width=90,
    ).pack(side="right")

    def handle_window_close():
        if on_window_close:
            on_window_close()
        help_window.destroy()

    help_window.protocol("WM_DELETE_WINDOW", handle_window_close)
    _center_dialog_window(help_window, center_window_func=center_window_func)
    return help_window


# ---------------------------------------------------------------------------
#  오류 대화상자
# ---------------------------------------------------------------------------

def get_error_solution_text(error_type):
    """오류 유형별 해결 방법 텍스트를 반환한다."""
    if "Google 인증 오류" in error_type:
        return """1. 인터넷 연결 상태를 확인하세요.
2. 'developer_credentials.json' 파일이 올바른 위치에 있는지 확인하세요.
3. Google 계정에 로그인이 되어 있는지 확인하세요.
4. 브라우저에서 Google 계정에 로그인한 후 다시 시도하세요.
5. 토큰이 만료되었다면, 프로그램을 재시작하여 새로운 인증을 시도하세요.
6. 계속 문제가 발생한다면, 'token.json' 파일을 삭제하고 다시 시도하세요."""

    if "Docs API 오류" in error_type:
        return """1. Google Docs 문서 ID가 올바른지 확인하세요.
2. 해당 Google Docs 문서에 대한 편집 권한이 있는지 확인하세요.
3. Google API 할당량이 초과되었을 수 있습니다. 잠시 후 다시 시도하세요.
4. 인터넷 연결 상태를 확인하세요.
5. 브라우저에서 해당 문서에 직접 접근이 가능한지 확인하세요."""

    if "파일 접근 오류" in error_type:
        return """1. 감시 중인 폴더가 존재하는지 확인하세요.
2. 폴더에 대한 읽기 권한이 있는지 확인하세요.
3. 다른 프로그램이 파일을 사용 중인지 확인하세요.
4. 파일이 이동되거나 삭제되었을 수 있습니다. 파일 존재 여부를 확인하세요.
5. 파일 경로에 특수 문자가 포함되어 있는지 확인하세요."""

    if "감시 시스템 오류" in error_type:
        return """1. 감시 폴더가 올바르게 설정되었는지 확인하세요.
2. 폴더 경로가 너무 길거나 특수 문자를 포함하고 있는지 확인하세요.
3. 프로그램을 재시작하여 감시 시스템을 초기화하세요.
4. 시스템 리소스(메모리, CPU)가 부족하지 않은지 확인하세요."""

    return """1. 인터넷 연결 상태를 확인하세요.
2. 프로그램 설정이 올바른지 확인하세요.
3. 프로그램을 재시작하여 다시 시도하세요.
4. 오류가 계속되면 로그 파일을 확인하여 더 자세한 정보를 얻으세요.
5. 필요한 경우 개발자에게 문의하세요."""


def get_credentials_wizard_guide_text():
    """인증 설정 마법사 안내 텍스트를 반환한다."""
    return (
        "1) 'Google Cloud Console 열기'를 눌러 API를 활성화하고\n"
        "   OAuth 데스크톱 애플리케이션 자격 증명(JSON)을 다운로드하세요.\n\n"
        "2) 'JSON 파일 선택'을 눌러 다운로드한 파일을 선택하면\n"
        "   프로그램이 사용자 설정 폴더의 developer_credentials.json 으로 복사합니다.\n\n"
        "3) 복사 후 '테스트' 결과가 성공이면 창을 닫고\n"
        "   프로그램을 다시 실행하거나 감시를 시작하세요."
    )


def show_enhanced_error_dialog(
    parent,
    error_type,
    error_message,
    on_open_logs,
    ctk_module=None,
    center_window_func=None,
):
    """오류 유형별 해결 방법이 포함된 대화상자를 생성해 표시한다."""
    ctk = _resolve_ctk(ctk_module)

    error_window = ctk.CTkToplevel(parent)
    error_window.title("오류 발생")
    error_window.geometry("750x550")
    error_window.minsize(750, 550)
    error_window.transient(parent)
    error_window.grab_set()

    main_frame = ctk.CTkFrame(error_window)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.pack(fill="x", pady=(0, 15))

    title_label = ctk.CTkLabel(
        header_frame,
        text=f"오류 발생: {error_type}",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#FF5252",
    )
    title_label.pack(pady=(0, 5))

    separator = ctk.CTkFrame(main_frame, height=2, fg_color="#CCCCCC")
    separator.pack(fill="x", pady=(0, 15))

    content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    content_frame.pack(fill="both", expand=True)

    error_label = ctk.CTkLabel(
        content_frame,
        text="오류 내용:",
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    )
    error_label.pack(fill="x", anchor="w")

    error_text = ctk.CTkTextbox(content_frame, height=80)
    error_text.pack(fill="x", pady=(5, 15))
    error_text.insert("1.0", error_message)
    error_text.configure(state="disabled")

    solution_label = ctk.CTkLabel(
        content_frame,
        text="해결 방법:",
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    )
    solution_label.pack(fill="x", anchor="w")

    solution_text = ctk.CTkTextbox(content_frame, height=150)
    solution_text.pack(fill="both", expand=True, pady=(5, 15))
    solution_text.insert("1.0", get_error_solution_text(error_type))
    solution_text.configure(state="disabled")

    button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    button_frame.pack(fill="x", pady=(15, 0))

    log_button = ctk.CTkButton(
        button_frame,
        text="로그 폴더 열기",
        command=on_open_logs,
        width=120,
    )
    log_button.pack(side="left", padx=10)

    close_button = ctk.CTkButton(
        button_frame,
        text="닫기",
        command=error_window.destroy,
        width=120,
    )
    close_button.pack(side="right", padx=10)

    _center_dialog_window(error_window, center_window_func=center_window_func)
    return error_window


# ---------------------------------------------------------------------------
#  테마 설정 대화상자
# ---------------------------------------------------------------------------

def show_theme_settings_dialog(
    parent,
    current_mode,
    on_apply_theme,
    ctk_module=None,
    center_window_func=None,
):
    """테마 설정 대화상자를 생성해 표시한다."""
    ctk = _resolve_ctk(ctk_module)

    theme_window = ctk.CTkToplevel(parent)
    theme_window.title("테마 설정")
    theme_window.geometry("500x300")
    theme_window.minsize(500, 300)
    theme_window.transient(parent)
    theme_window.grab_set()

    main_frame = ctk.CTkFrame(theme_window)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    title_label = ctk.CTkLabel(
        main_frame,
        text="테마 설정",
        font=ctk.CTkFont(size=16, weight="bold"),
    )
    title_label.pack(pady=(0, 15))

    mode_frame = ctk.CTkFrame(main_frame)
    mode_frame.pack(fill="x", pady=(0, 15))

    ctk.CTkLabel(
        mode_frame,
        text="테마 모드:",
        font=ctk.CTkFont(weight="bold"),
    ).pack(anchor="w", pady=(0, 5))

    mode_var = ctk.StringVar(value=current_mode)
    modes = [("시스템 설정 따름", "System"), ("라이트 모드", "Light"), ("다크 모드", "Dark")]

    for text, value in modes:
        radio = ctk.CTkRadioButton(
            mode_frame,
            text=text,
            value=value,
            variable=mode_var,
        )
        radio.pack(anchor="w", pady=5, padx=10)

    preview_frame = ctk.CTkFrame(main_frame)
    preview_frame.pack(fill="x", pady=(0, 15))

    ctk.CTkLabel(
        preview_frame,
        text="미리보기:",
        font=ctk.CTkFont(weight="bold"),
    ).pack(anchor="w", pady=(0, 5))

    preview_elements = ctk.CTkFrame(preview_frame)
    preview_elements.pack(fill="x", pady=5, padx=10)

    ctk.CTkButton(
        preview_elements,
        text="버튼",
        width=80,
    ).pack(side="left", padx=(0, 10))

    ctk.CTkEntry(
        preview_elements,
        width=120,
        placeholder_text="입력 필드",
    ).pack(side="left")

    button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    button_frame.pack(fill="x", pady=(15, 0))

    def apply_theme():
        on_apply_theme(mode_var.get())
        theme_window.destroy()

    apply_button = ctk.CTkButton(
        button_frame,
        text="적용",
        command=apply_theme,
        width=100,
    )
    apply_button.pack(side="right", padx=(5, 0))

    cancel_button = ctk.CTkButton(
        button_frame,
        text="취소",
        command=theme_window.destroy,
        width=100,
        fg_color="gray",
    )
    cancel_button.pack(side="right", padx=5)

    _center_dialog_window(theme_window, center_window_func=center_window_func)
    return theme_window


# ---------------------------------------------------------------------------
#  Google 인증 설정 마법사 대화상자
# ---------------------------------------------------------------------------

def show_credentials_wizard_dialog(
    parent,
    credentials_target_text,
    on_open_console,
    on_select_json,
    ctk_module=None,
    center_window_func=None,
):
    """Google 인증 설정 마법사 대화상자를 생성해 표시한다."""
    ctk = _resolve_ctk(ctk_module)

    wizard = ctk.CTkToplevel(parent)
    wizard.title("Google 인증 설정 마법사")
    wizard.geometry("700x500")
    wizard.minsize(700, 500)
    wizard.transient(parent)
    wizard.grab_set()

    frame = ctk.CTkFrame(wizard)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    info_label = ctk.CTkLabel(
        frame,
        text=get_credentials_wizard_guide_text(),
        justify="left",
        wraplength=540,
    )
    info_label.pack(fill="x", pady=(0, 15))

    btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
    btn_frame.pack(fill="x", pady=(0, 10))

    console_btn = ctk.CTkButton(
        btn_frame,
        text="Google Cloud Console 열기",
        command=on_open_console,
    )
    console_btn.pack(fill="x", pady=5)

    result_label = ctk.CTkLabel(
        frame,
        text=f"JSON 파일을 아직 선택하지 않았습니다.\n복사 대상: {credentials_target_text}",
    )
    result_label.pack(fill="x", pady=(10, 5))

    def update_status(text, text_color=None):
        configure_kwargs = {"text": text}
        if text_color is not None:
            configure_kwargs["text_color"] = text_color
        result_label.configure(**configure_kwargs)
        wizard.update_idletasks()

    json_btn = ctk.CTkButton(
        btn_frame,
        text="JSON 파일 선택",
        command=lambda: on_select_json(update_status),
    )
    json_btn.pack(fill="x", pady=5)

    close_btn = ctk.CTkButton(frame, text="닫기", command=wizard.destroy)
    close_btn.pack(pady=(20, 0))

    _center_dialog_window(wizard, center_window_func=center_window_func)
    return wizard
