def _resolve_ctk(ctk_module=None):
    """UI 생성에 사용할 customtkinter 모듈을 반환한다."""
    if ctk_module is not None:
        return ctk_module

    import customtkinter as ctk

    return ctk


def _font(ctk, size, weight="normal", family=None):
    """플랫폼별 기본 UI 폰트 또는 지정 폰트를 생성한다."""
    font_kwargs = {
        "size": size,
        "weight": weight,
    }
    if family:
        font_kwargs["family"] = family
    return ctk.CTkFont(**font_kwargs)


def _attach_tooltip(widget, text, delay_ms=450, wraplength=280):
    """위젯에 마우스 오버 툴팁을 연결한다."""
    import tkinter as tk

    tooltip_window = None
    scheduled_job = None

    def hide_tooltip(_event=None):
        nonlocal tooltip_window, scheduled_job
        if scheduled_job is not None:
            widget.after_cancel(scheduled_job)
            scheduled_job = None
        if tooltip_window is not None and tooltip_window.winfo_exists():
            tooltip_window.destroy()
        tooltip_window = None

    def show_tooltip():
        nonlocal tooltip_window, scheduled_job
        scheduled_job = None
        if tooltip_window is not None or not widget.winfo_exists():
            return

        tooltip_window = tk.Toplevel(widget)
        tooltip_window.wm_overrideredirect(True)
        tooltip_window.attributes("-topmost", True)

        x_pos = widget.winfo_rootx() + widget.winfo_width() + 10
        y_pos = widget.winfo_rooty() + max(6, widget.winfo_height() // 2)
        tooltip_window.wm_geometry(f"+{x_pos}+{y_pos}")

        tooltip_label = tk.Label(
            tooltip_window,
            text=text,
            justify="left",
            background="#111827",
            foreground="#F9FAFB",
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=6,
            wraplength=wraplength,
        )
        tooltip_label.pack()

    def schedule_tooltip(_event=None):
        nonlocal scheduled_job
        hide_tooltip()
        scheduled_job = widget.after(delay_ms, show_tooltip)

    widget.bind("<Enter>", schedule_tooltip, add="+")
    widget.bind("<Leave>", hide_tooltip, add="+")
    widget.bind("<ButtonPress>", hide_tooltip, add="+")
    widget.bind("<Destroy>", hide_tooltip, add="+")


def _build_status_panel(ctk, parent, state_vars, callbacks, font_family):
    """상단 상태 패널을 생성한다."""
    status_card = ctk.CTkFrame(parent, corner_radius=16)
    status_card.pack(fill="x", pady=(0, 10))

    header_frame = ctk.CTkFrame(status_card, fg_color="transparent")
    header_frame.pack(fill="x", padx=16, pady=(14, 10))

    title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    title_frame.pack(side="left", fill="both", expand=True)

    ctk.CTkLabel(
        title_frame,
        text="Messenger Docs Workspace",
        font=_font(ctk, 18, "bold", family=font_family),
    ).pack(anchor="w")
    ctk.CTkLabel(
        title_frame,
        text="설정 준비 상태와 최근 작업 흐름을 한 화면에서 확인합니다.",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray35", "gray70"),
    ).pack(anchor="w", pady=(4, 0))

    badge_group = ctk.CTkFrame(header_frame, fg_color="transparent")
    badge_group.pack(side="right", padx=(12, 0))

    unsaved_changes_badge = ctk.CTkLabel(
        badge_group,
        textvariable=state_vars["save_state_var"],
        font=_font(ctk, 11, "bold", family=font_family),
        corner_radius=999,
        fg_color=("gray90", "gray22"),
        text_color=("gray35", "gray82"),
        padx=12,
        pady=6,
    )
    unsaved_changes_badge.pack(side="right")

    state_pill = ctk.CTkFrame(badge_group, corner_radius=999, fg_color=("gray90", "gray20"))
    state_pill.pack(side="right", padx=(0, 8))
    ctk.CTkLabel(
        state_pill,
        text="현재 상태",
        font=_font(ctk, 11, "bold", family=font_family),
        text_color=("gray35", "gray80"),
    ).pack(side="left", padx=(10, 4), pady=6)
    status_label = ctk.CTkLabel(
        state_pill,
        textvariable=state_vars["status_var"],
        font=_font(ctk, 12, "bold", family=font_family),
    )
    status_label.pack(side="left", padx=(0, 10), pady=6)

    summary_row = ctk.CTkFrame(status_card, fg_color="transparent")
    summary_row.pack(fill="x", padx=16, pady=(0, 10))

    for label_text, variable_name in (
        ("현재 처리", "current_activity_var"),
        ("마지막 성공", "last_success_var"),
        ("마지막 결과", "last_result_var"),
    ):
        summary_card = ctk.CTkFrame(summary_row, corner_radius=12, fg_color=("gray96", "gray18"))
        summary_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(
            summary_card,
            text=label_text,
            font=_font(ctk, 11, "bold", family=font_family),
            text_color=("gray45", "gray68"),
        ).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            summary_card,
            textvariable=state_vars[variable_name],
            font=_font(ctk, 12, family=font_family),
            anchor="w",
            justify="left",
            wraplength=240,
        ).pack(fill="x", padx=12, pady=(0, 10))

    metrics_frame = ctk.CTkFrame(status_card, fg_color="transparent")
    metrics_frame.pack(fill="x", padx=16, pady=(0, 14))

    left_metrics = ctk.CTkFrame(metrics_frame, fg_color="transparent")
    left_metrics.pack(side="left", fill="x", expand=True)

    memory_label = ctk.CTkLabel(
        left_metrics,
        textvariable=state_vars["memory_usage"],
        font=_font(ctk, 12, family=font_family),
    )
    memory_label.pack(side="left")

    memory_optimize_button = ctk.CTkButton(
        left_metrics,
        text="메모리 정리",
        width=84,
        height=30,
        corner_radius=10,
        command=callbacks["optimize_memory"],
        font=_font(ctk, 11, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    memory_optimize_button.pack(side="left", padx=(10, 0))
    _attach_tooltip(
        memory_optimize_button,
        "현재 앱 메모리 사용량을 점검하고 가능한 정리 작업을 실행합니다.",
    )

    right_metrics = ctk.CTkFrame(metrics_frame, fg_color="transparent")
    right_metrics.pack(side="right")

    folder_info_var = ctk.StringVar(value="폴더: 설정되지 않음")
    folder_info_label = ctk.CTkLabel(
        right_metrics,
        textvariable=folder_info_var,
        font=_font(ctk, 12, family=font_family),
        text_color=("gray35", "gray75"),
        anchor="e",
    )
    folder_info_label.pack(anchor="e")

    docs_info_var = ctk.StringVar(value="문서: 설정되지 않음")
    docs_info_label = ctk.CTkLabel(
        right_metrics,
        textvariable=docs_info_var,
        font=_font(ctk, 12, family=font_family),
        text_color=("gray35", "gray75"),
        anchor="e",
    )
    docs_info_label.pack(anchor="e", pady=(4, 0))

    return {
        "status_label": status_label,
        "memory_label": memory_label,
        "memory_optimize_button": memory_optimize_button,
        "folder_info_var": folder_info_var,
        "folder_info_label": folder_info_label,
        "docs_info_var": docs_info_var,
        "docs_info_label": docs_info_label,
        "unsaved_changes_badge": unsaved_changes_badge,
    }


def _build_basic_settings_rows(ctk, parent, state_vars, callbacks, font_family):
    """기본 설정 행을 생성한다."""
    folder_row = ctk.CTkFrame(parent, fg_color="transparent")
    folder_row.pack(fill="x", padx=14, pady=4)
    ctk.CTkLabel(
        folder_row,
        text="감시 폴더",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    watch_folder_entry = ctk.CTkEntry(
        folder_row,
        textvariable=state_vars["watch_folder"],
        height=34,
        font=_font(ctk, 13, family=font_family),
    )
    watch_folder_entry.pack(side="left", fill="x", expand=True, padx=4)
    watch_folder_browse_button = ctk.CTkButton(
        folder_row,
        text="폴더 선택",
        width=88,
        height=34,
        corner_radius=10,
        command=callbacks["browse_folder"],
        font=_font(ctk, 12, "bold", family=font_family),
    )
    watch_folder_browse_button.pack(side="left", padx=(8, 0))
    watch_folder_open_button = ctk.CTkButton(
        folder_row,
        text="열기",
        width=60,
        height=34,
        corner_radius=10,
        command=callbacks["open_watch_folder"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    watch_folder_open_button.pack(side="left", padx=(8, 0))

    folder_hint_row = ctk.CTkFrame(parent, fg_color="transparent")
    folder_hint_row.pack(fill="x", padx=14, pady=(0, 6))
    watch_folder_drop_hint_label = ctk.CTkLabel(
        folder_hint_row,
        textvariable=state_vars["watch_folder_drop_hint"],
        font=_font(ctk, 11, family=font_family),
        text_color=("gray45", "gray70"),
        anchor="w",
        justify="left",
    )
    watch_folder_drop_hint_label.pack(fill="x", padx=(118, 0))

    doc_title_row = ctk.CTkFrame(parent, fg_color="transparent")
    doc_title_row.pack(fill="x", padx=14, pady=(8, 3))
    ctk.CTkLabel(
        doc_title_row,
        text="문서 작업",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(
        doc_title_row,
        text="새 문서 생성, 주소 입력, 목록 선택 중 하나를 사용하세요.",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray45", "gray72"),
    ).pack(side="left")

    docs_action_row = ctk.CTkFrame(parent, fg_color="transparent")
    docs_action_row.pack(fill="x", padx=14, pady=4)
    create_doc_button = ctk.CTkButton(
        docs_action_row,
        text="새 문서 만들기",
        width=112,
        height=34,
        corner_radius=12,
        command=callbacks["create_new_google_doc"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color="#0F9D58",
        hover_color="#0B8043",
    )
    create_doc_button.pack(side="left")
    manual_doc_input_button = ctk.CTkButton(
        docs_action_row,
        text="기존 문서 주소 입력",
        width=140,
        height=34,
        corner_radius=12,
        command=callbacks["focus_existing_docs_input"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    manual_doc_input_button.pack(side="left", padx=(8, 0))
    select_doc_button = ctk.CTkButton(
        docs_action_row,
        text="문서 목록",
        width=84,
        height=34,
        corner_radius=12,
        command=callbacks["select_google_doc"],
        font=_font(ctk, 12, "bold", family=font_family),
    )
    select_doc_button.pack(side="left", padx=(8, 0))
    _attach_tooltip(
        select_doc_button,
        "현재 계정에서 접근 가능한 Google Docs 목록을 불러와 작업 문서를 선택합니다.",
    )

    docs_input_row = ctk.CTkFrame(parent, fg_color="transparent")
    docs_input_row.pack(fill="x", padx=14, pady=(4, 6))
    ctk.CTkLabel(
        docs_input_row,
        text="기존 문서 주소/ID",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    docs_input_entry = ctk.CTkEntry(
        docs_input_row,
        textvariable=state_vars["docs_input"],
        height=34,
        font=_font(ctk, 13, family=font_family),
        placeholder_text="예: https://docs.google.com/document/d/문서ID/edit 또는 문서 ID",
    )
    docs_input_entry.pack(side="left", fill="x", expand=True, padx=4)

    docs_lock_row = ctk.CTkFrame(parent, fg_color="transparent")
    docs_lock_row.pack(fill="x", padx=14, pady=(0, 4))

    docs_target_status_label = ctk.CTkLabel(
        docs_lock_row,
        textvariable=state_vars["docs_target_status_var"],
        font=_font(ctk, 12, "bold", family=font_family),
        text_color=("#1A73E8", "#8AB4F8"),
        anchor="w",
        justify="left",
    )
    docs_target_status_label.pack(side="left", fill="x", expand=True)

    docs_lock_button = ctk.CTkButton(
        docs_lock_row,
        text="문서 경로 확정",
        width=118,
        height=32,
        corner_radius=10,
        command=callbacks["toggle_docs_target_lock"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color="#1A73E8",
        hover_color="#1765CC",
    )
    docs_lock_button.pack(side="right", padx=(10, 0))
    _attach_tooltip(
        docs_lock_button,
        "현재 입력된 문서를 작업 대상으로 고정해 감시 시작 전에 다시 바뀌지 않게 합니다.",
    )

    return {
        "watch_folder_entry": watch_folder_entry,
        "watch_folder_browse_button": watch_folder_browse_button,
        "watch_folder_open_button": watch_folder_open_button,
        "watch_folder_drop_hint_label": watch_folder_drop_hint_label,
        "docs_input_entry": docs_input_entry,
        "create_doc_button": create_doc_button,
        "manual_doc_input_button": manual_doc_input_button,
        "select_doc_button": select_doc_button,
        "docs_target_status_label": docs_target_status_label,
        "docs_lock_button": docs_lock_button,
    }


def _build_advanced_settings_rows(ctk, parent, state_vars, callbacks, font_family):
    """고급 설정 행을 생성한다."""
    validate_command = (
        parent.register(callbacks["validate_positive_integer_input"]),
        "%P",
    )

    filter_row = ctk.CTkFrame(parent, fg_color="transparent")
    filter_row.pack(fill="x", pady=4)
    ctk.CTkLabel(
        filter_row,
        text="파일 필터",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    ctk.CTkEntry(
        filter_row,
        textvariable=state_vars["file_extensions"],
        width=130,
        height=32,
        font=_font(ctk, 13, family=font_family),
    ).pack(side="left", padx=4)
    ctk.CTkLabel(
        filter_row,
        text="쉼표로 구분 (예: .txt,.log)",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray45", "gray72"),
    ).pack(side="left", padx=(8, 0))
    advanced_filter_button = ctk.CTkButton(
        filter_row,
        text="고급 필터",
        width=86,
        height=32,
        corner_radius=10,
        command=callbacks["show_filter_settings"],
        font=_font(ctk, 12, "bold", family=font_family),
    )
    advanced_filter_button.pack(side="right")
    _attach_tooltip(
        advanced_filter_button,
        "확장자 외에 정규식과 세부 필터 조건을 추가로 설정합니다.",
    )

    max_cache_row = ctk.CTkFrame(parent, fg_color="transparent")
    max_cache_row.pack(fill="x", pady=4)
    ctk.CTkLabel(
        max_cache_row,
        text="라인 캐시 크기",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    max_cache_size_entry = ctk.CTkEntry(
        max_cache_row,
        textvariable=state_vars["max_cache_size"],
        width=130,
        height=32,
        font=_font(ctk, 13, family=font_family),
        validate="key",
        validatecommand=validate_command,
    )
    max_cache_size_entry.pack(side="left", padx=4)
    cache_folder_button = ctk.CTkButton(
        max_cache_row,
        text="캐시 폴더 열기",
        width=112,
        height=32,
        corner_radius=10,
        command=callbacks["open_cache_folder"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    cache_folder_button.pack(side="right")
    _attach_tooltip(
        cache_folder_button,
        "전역 라인 캐시와 처리 상태 파일이 저장된 폴더를 Windows 탐색기에서 엽니다.",
    )
    ctk.CTkLabel(
        max_cache_row,
        text="중복 비교용 전역 라인 캐시에 유지할 최대 항목 수",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray45", "gray72"),
    ).pack(side="left", padx=(8, 12))

    notification_row = ctk.CTkFrame(parent, fg_color="transparent")
    notification_row.pack(fill="x", pady=4)
    ctk.CTkLabel(
        notification_row,
        text="작업 결과 알림",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    notification_checkbox = ctk.CTkCheckBox(
        notification_row,
        text="작업 결과 알림 표시",
        variable=state_vars["show_success_notifications"],
        onvalue=True,
        offvalue=False,
        font=_font(ctk, 12, family=font_family),
    )
    notification_checkbox.pack(side="left", padx=4)

    sound_row = ctk.CTkFrame(parent, fg_color="transparent")
    sound_row.pack(fill="x", pady=4)
    ctk.CTkLabel(
        sound_row,
        text="작업 결과 효과음",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    sound_checkbox = ctk.CTkCheckBox(
        sound_row,
        text="작업 결과 효과음 재생",
        variable=state_vars["play_event_sounds"],
        onvalue=True,
        offvalue=False,
        font=_font(ctk, 12, family=font_family),
    )
    sound_checkbox.pack(side="left", padx=4)

    autostart_row = ctk.CTkFrame(parent, fg_color="transparent")
    autostart_row.pack(fill="x", pady=4)
    ctk.CTkLabel(
        autostart_row,
        text="Windows 자동 실행",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    autostart_switch = ctk.CTkSwitch(
        autostart_row,
        text="Windows 로그인 시 자동으로 실행",
        variable=state_vars["launch_on_windows_startup"],
        onvalue=True,
        offvalue=False,
        font=_font(ctk, 12, family=font_family),
    )
    autostart_switch.pack(side="left", padx=4)
    _attach_tooltip(
        autostart_switch,
        "스위치를 바꾸면 Windows 시작프로그램 폴더의 자동 실행 상태가 바로 변경됩니다.",
    )

    autostart_hint_label = ctk.CTkLabel(
        parent,
        textvariable=state_vars["autostart_hint"],
        font=_font(ctk, 11, family=font_family),
        text_color=("gray45", "gray70"),
        anchor="w",
        justify="left",
    )
    autostart_hint_label.pack(fill="x", padx=(118, 0), pady=(0, 4))

    return {
        "max_cache_size_entry": max_cache_size_entry,
        "cache_folder_button": cache_folder_button,
        "notification_checkbox": notification_checkbox,
        "autostart_switch": autostart_switch,
        "autostart_hint_label": autostart_hint_label,
        "advanced_filter_button": advanced_filter_button,
    }


def _build_settings_panel(ctk, parent, state_vars, callbacks, font_family):
    """기본 설정과 고급 설정을 포함한 설정 패널을 생성한다."""
    settings_frame = ctk.CTkFrame(parent, corner_radius=16)
    settings_frame.pack(fill="x", pady=(0, 10))

    title_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
    title_frame.pack(fill="x", padx=14, pady=(14, 4))

    ctk.CTkLabel(
        title_frame,
        text="작업 설정",
        font=_font(ctk, 16, "bold", family=font_family),
    ).pack(anchor="w")
    ctk.CTkLabel(
        title_frame,
        text="기본 설정을 먼저 마치고, 필요할 때만 고급 설정을 펼쳐 세부 동작을 조정합니다.",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray40", "gray72"),
    ).pack(anchor="w", pady=(4, 0))

    auth_notice = ctk.CTkLabel(
        settings_frame,
        text="Google API 인증은 번들 또는 사용자 설정 폴더의 developer_credentials.json을 사용합니다.",
        font=_font(ctk, 11, family=font_family),
        justify="left",
        text_color=("gray45", "gray70"),
    )
    auth_notice.pack(fill="x", padx=14, pady=(0, 8))

    widget_refs = {"settings_frame": settings_frame}
    widget_refs.update(_build_basic_settings_rows(ctk, settings_frame, state_vars, callbacks, font_family))

    advanced_toggle_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    advanced_toggle_row.pack(fill="x", padx=14, pady=(10, 4))
    ctk.CTkLabel(
        advanced_toggle_row,
        text="고급 설정",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(
        advanced_toggle_row,
        text="필터, 캐시, 알림, Windows 자동 실행",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray45", "gray70"),
    ).pack(side="left")
    advanced_settings_toggle_button = ctk.CTkButton(
        advanced_toggle_row,
        textvariable=state_vars["advanced_settings_toggle_text"],
        width=118,
        height=32,
        corner_radius=10,
        command=callbacks["toggle_advanced_settings"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    advanced_settings_toggle_button.pack(side="right")

    advanced_settings_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
    advanced_settings_frame.pack(fill="x", padx=14, pady=(0, 8))
    widget_refs.update(_build_advanced_settings_rows(ctk, advanced_settings_frame, state_vars, callbacks, font_family))
    advanced_settings_frame.pack_forget()

    widget_refs["advanced_settings_frame"] = advanced_settings_frame
    widget_refs["advanced_settings_toggle_button"] = advanced_settings_toggle_button
    return widget_refs


def _build_control_panel(ctk, parent, callbacks, font_family):
    """보조 액션 패널을 생성한다."""
    control_card = ctk.CTkFrame(parent, corner_radius=16)
    control_card.pack(fill="x", pady=(0, 10))

    row = ctk.CTkFrame(control_card, fg_color="transparent")
    row.pack(fill="x", padx=14, pady=10)

    open_docs_button = ctk.CTkButton(
        row,
        text="Docs 웹에서 열기",
        command=callbacks["open_docs_in_browser"],
        width=128,
        height=34,
        corner_radius=12,
        font=_font(ctk, 13, "bold", family=font_family),
        fg_color="#4285F4",
        hover_color="#3367D6",
    )
    open_docs_button.pack(side="left")

    save_button = ctk.CTkButton(
        row,
        text="설정 저장",
        command=callbacks["save_config"],
        width=100,
        height=34,
        corner_radius=12,
        font=_font(ctk, 12, "bold", family=font_family),
    )
    save_button.pack(side="left", padx=(10, 0))

    backup_restore_button = ctk.CTkButton(
        row,
        text="백업/복원",
        command=callbacks["show_backup_restore_dialog"],
        width=92,
        height=34,
        corner_radius=12,
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    backup_restore_button.pack(side="right")
    _attach_tooltip(
        backup_restore_button,
        "현재 설정을 백업 파일로 저장하거나 이전 백업 설정을 불러옵니다.",
    )

    theme_button = ctk.CTkButton(
        row,
        text="테마 설정",
        command=callbacks["show_theme_settings"],
        width=88,
        height=34,
        corner_radius=12,
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    theme_button.pack(side="right", padx=(0, 10))

    return {
        "open_docs_button": open_docs_button,
        "backup_restore_button": backup_restore_button,
        "theme_button": theme_button,
        "save_button": save_button,
    }


def _build_result_tab(ctk, tab_frame, state_vars, font_family):
    """최근 추출 결과 탭을 구성한다."""
    header = ctk.CTkFrame(tab_frame, fg_color="transparent")
    header.pack(fill="x", padx=14, pady=(14, 8))

    title_frame = ctk.CTkFrame(header, fg_color="transparent")
    title_frame.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(
        title_frame,
        text="최근 추출 결과",
        font=_font(ctk, 16, "bold", family=font_family),
    ).pack(anchor="w")
    ctk.CTkLabel(
        title_frame,
        textvariable=state_vars["current_activity_var"],
        font=_font(ctk, 12, family=font_family),
        text_color=("gray40", "gray72"),
        anchor="w",
    ).pack(anchor="w", pady=(4, 0))

    result_cards_frame = ctk.CTkScrollableFrame(
        tab_frame,
        fg_color="transparent",
        corner_radius=0,
        height=320,
    )
    result_cards_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    return {
        "result_cards_frame": result_cards_frame,
    }


def _build_log_tab(ctk, tab_frame, callbacks, font_family):
    """작업 로그 탭을 구성한다."""
    header_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
    header_frame.pack(fill="x", padx=14, pady=(14, 8))

    header_title = ctk.CTkFrame(header_frame, fg_color="transparent")
    header_title.pack(side="left", fill="x", expand=True)

    ctk.CTkLabel(
        header_title,
        text="작업 로그",
        font=_font(ctk, 16, "bold", family=font_family),
    ).pack(anchor="w")
    ctk.CTkLabel(
        header_title,
        text="오류 발생 시 이 탭으로 자동 전환되며, 로그 팝업으로 분리해서 볼 수도 있습니다.",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray40", "gray72"),
    ).pack(anchor="w", pady=(4, 0))

    header_actions = ctk.CTkFrame(header_frame, fg_color="transparent")
    header_actions.pack(side="right", padx=(10, 0))

    log_popup_button = ctk.CTkButton(
        header_actions,
        text="로그 팝업",
        width=94,
        height=30,
        corner_radius=10,
        command=callbacks["show_log_popup"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    log_popup_button.pack(side="right")
    _attach_tooltip(
        log_popup_button,
        "작업 로그를 별도 창으로 열어 좁은 화면에서도 편하게 확인합니다.",
    )

    log_folder_button = ctk.CTkButton(
        header_actions,
        text="폴더 열기",
        width=90,
        height=30,
        corner_radius=10,
        command=callbacks["open_log_folder"],
        font=_font(ctk, 12, "bold", family=font_family),
    )
    log_folder_button.pack(side="right", padx=(0, 8))

    log_search_button = ctk.CTkButton(
        header_actions,
        text="검색",
        width=60,
        height=30,
        corner_radius=10,
        command=callbacks["show_log_search_dialog"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    log_search_button.pack(side="right", padx=(0, 8))

    log_clear_button = ctk.CTkButton(
        header_actions,
        text="지우기",
        width=64,
        height=30,
        corner_radius=10,
        command=callbacks["clear_log"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    log_clear_button.pack(side="right", padx=(0, 8))
    _attach_tooltip(
        log_clear_button,
        "화면에 표시된 로그만 지우며 저장된 로그 파일은 삭제하지 않습니다.",
    )

    log_text = ctk.CTkTextbox(
        tab_frame,
        state="disabled",
        wrap="word",
        height=320,
        font=_font(ctk, 12, family=font_family),
        corner_radius=12,
    )
    log_text.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    return {
        "log_popup_button": log_popup_button,
        "log_folder_button": log_folder_button,
        "log_search_button": log_search_button,
        "log_clear_button": log_clear_button,
        "log_text": log_text,
    }


def _build_activity_panel(ctk, parent, state_vars, callbacks, font_family):
    """활동 탭 패널을 생성한다."""
    activity_card = ctk.CTkFrame(parent, corner_radius=16)
    activity_card.pack(fill="both", expand=True, pady=(0, 10))

    activity_header = ctk.CTkFrame(activity_card, fg_color="transparent")
    activity_header.pack(fill="x", padx=14, pady=(14, 6))

    title_frame = ctk.CTkFrame(activity_header, fg_color="transparent")
    title_frame.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(
        title_frame,
        text="활동",
        font=_font(ctk, 16, "bold", family=font_family),
    ).pack(anchor="w")
    ctk.CTkLabel(
        title_frame,
        text="최근 결과와 작업 로그를 같은 영역에서 전환하며 확인합니다.",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray40", "gray72"),
    ).pack(anchor="w", pady=(4, 0))

    activity_tabview = ctk.CTkTabview(
        activity_card,
        corner_radius=14,
        height=390,
        command=callbacks["on_activity_tab_changed"],
        segmented_button_selected_color="#1A73E8",
        segmented_button_selected_hover_color="#1765CC",
    )
    activity_tabview.pack(fill="both", expand=True, padx=14, pady=(0, 14))
    result_tab = activity_tabview.add("최근 추출 결과")
    log_tab = activity_tabview.add("작업 로그")
    activity_tabview.set("최근 추출 결과")

    widget_refs = {
        "activity_tabview": activity_tabview,
    }
    widget_refs.update(_build_result_tab(ctk, result_tab, state_vars, font_family))
    widget_refs.update(_build_log_tab(ctk, log_tab, callbacks, font_family))
    return widget_refs


def _build_cta_footer(ctk, parent, state_vars, callbacks, font_family):
    """하단 고정 CTA 푸터를 생성한다."""
    footer_frame = ctk.CTkFrame(parent, corner_radius=16)
    footer_frame.pack(fill="x", pady=(0, 0))

    top_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
    top_row.pack(fill="x", padx=16, pady=(14, 6))

    readiness_label = ctk.CTkLabel(
        top_row,
        textvariable=state_vars["readiness_var"],
        font=_font(ctk, 12, "bold", family=font_family),
        anchor="w",
        justify="left",
    )
    readiness_label.pack(side="left", fill="x", expand=True)

    ctk.CTkLabel(
        footer_frame,
        textvariable=state_vars["google_connection_status_var"],
        font=_font(ctk, 11, family=font_family),
        text_color=("gray45", "gray70"),
        anchor="w",
        justify="left",
    ).pack(fill="x", padx=16, pady=(0, 10))

    cta_stack_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
    cta_stack_frame.pack(fill="x", padx=16, pady=(0, 16))
    cta_stack_frame.grid_columnconfigure(0, weight=1)

    start_cta_button = ctk.CTkButton(
        cta_stack_frame,
        text="감시 시작",
        command=callbacks["start_monitoring"],
        height=60,
        corner_radius=16,
        font=_font(ctk, 18, "bold", family=font_family),
        fg_color="#16A34A",
        hover_color="#15803D",
    )
    start_cta_button.grid(row=0, column=0, sticky="ew")

    stop_cta_button = ctk.CTkButton(
        cta_stack_frame,
        text="감시 중지",
        command=callbacks["stop_monitoring"],
        height=60,
        corner_radius=16,
        font=_font(ctk, 18, "bold", family=font_family),
        fg_color="#DC2626",
        hover_color="#B91C1C",
    )
    stop_cta_button.grid(row=0, column=0, sticky="ew")
    stop_cta_button.grid_remove()

    return {
        "cta_footer_frame": footer_frame,
        "cta_stack_frame": cta_stack_frame,
        "readiness_label": readiness_label,
        "start_button": start_cta_button,
        "stop_button": stop_cta_button,
        "start_cta_button": start_cta_button,
        "stop_cta_button": stop_cta_button,
    }


def build_main_window_ui(parent, state_vars, callbacks, ctk_module=None, font_family=None):
    """메인 창 UI를 생성하고 필요한 위젯 참조를 반환한다."""
    ctk = _resolve_ctk(ctk_module)

    main_frame = ctk.CTkFrame(parent, fg_color="transparent")
    main_frame.pack(padx=14, pady=14, fill="both", expand=True)

    main_scroll_frame = ctk.CTkScrollableFrame(
        main_frame,
        fg_color="transparent",
        corner_radius=0,
    )
    main_scroll_frame.pack(fill="both", expand=True)

    widget_refs = {}
    widget_refs.update(_build_status_panel(ctk, main_scroll_frame, state_vars, callbacks, font_family))
    widget_refs.update(_build_settings_panel(ctk, main_scroll_frame, state_vars, callbacks, font_family))
    widget_refs.update(_build_control_panel(ctk, main_scroll_frame, callbacks, font_family))
    widget_refs.update(_build_activity_panel(ctk, main_scroll_frame, state_vars, callbacks, font_family))
    widget_refs.update(_build_cta_footer(ctk, main_frame, state_vars, callbacks, font_family))
    widget_refs["main_frame"] = main_frame
    widget_refs["main_scroll_frame"] = main_scroll_frame
    return widget_refs
