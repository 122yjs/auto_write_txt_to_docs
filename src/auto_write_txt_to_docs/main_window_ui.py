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


def _build_status_panel(ctk, parent, state_vars, callbacks, font_family):
    """상단 상태 패널을 생성한다."""
    status_card = ctk.CTkFrame(parent, corner_radius=14)
    status_card.pack(fill="x", pady=(0, 14))

    header_frame = ctk.CTkFrame(status_card, fg_color="transparent")
    header_frame.pack(fill="x", padx=18, pady=(16, 8))

    title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    title_frame.pack(side="left", fill="both", expand=True)

    ctk.CTkLabel(
        title_frame,
        text="Messenger Docs Workspace",
        font=_font(ctk, 20, "bold", family=font_family),
    ).pack(anchor="w")
    ctk.CTkLabel(
        title_frame,
        text="폴더 변경을 감지하고 Google Docs에 자동으로 기록합니다.",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray35", "gray70"),
    ).pack(anchor="w", pady=(4, 0))

    state_pill = ctk.CTkFrame(header_frame, corner_radius=999, fg_color=("gray90", "gray20"))
    state_pill.pack(side="right", padx=(12, 0))
    ctk.CTkLabel(
        state_pill,
        text="현재 상태",
        font=_font(ctk, 11, "bold", family=font_family),
        text_color=("gray35", "gray80"),
    ).pack(side="left", padx=(12, 6), pady=8)
    status_label = ctk.CTkLabel(
        state_pill,
        textvariable=state_vars["status_var"],
        font=_font(ctk, 13, "bold", family=font_family),
    )
    status_label.pack(side="left", padx=(0, 12), pady=8)

    metrics_frame = ctk.CTkFrame(status_card, fg_color="transparent")
    metrics_frame.pack(fill="x", padx=18, pady=(0, 16))

    left_metrics = ctk.CTkFrame(metrics_frame, fg_color="transparent")
    left_metrics.pack(side="left", fill="x", expand=True)

    memory_label = ctk.CTkLabel(
        left_metrics,
        textvariable=state_vars["memory_usage"],
        font=_font(ctk, 13, family=font_family),
    )
    memory_label.pack(side="left")

    memory_optimize_button = ctk.CTkButton(
        left_metrics,
        text="메모리 정리",
        width=92,
        height=30,
        corner_radius=10,
        command=callbacks["optimize_memory"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    memory_optimize_button.pack(side="left", padx=(10, 0))

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
    }


def _build_settings_panel(ctk, parent, state_vars, callbacks, font_family):
    """중앙 작업 설정 패널을 생성한다."""
    settings_frame = ctk.CTkFrame(parent, corner_radius=14)
    settings_frame.pack(fill="x", pady=(0, 14))
    validate_command = (
        settings_frame.register(callbacks["validate_positive_integer_input"]),
        "%P",
    )

    title_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
    title_frame.pack(fill="x", padx=18, pady=(16, 6))

    ctk.CTkLabel(
        title_frame,
        text="작업 설정",
        font=_font(ctk, 16, "bold", family=font_family),
    ).pack(anchor="w")
    ctk.CTkLabel(
        title_frame,
        text="감시 폴더, 필터, 대상 문서를 지정한 뒤 바로 실행할 수 있습니다.",
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
    auth_notice.pack(fill="x", padx=18, pady=(0, 10))

    folder_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    folder_row.pack(fill="x", padx=18, pady=6)
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
        height=36,
        font=_font(ctk, 13, family=font_family),
    )
    watch_folder_entry.pack(side="left", fill="x", expand=True, padx=4)
    ctk.CTkButton(
        folder_row,
        text="폴더 선택",
        width=92,
        height=36,
        corner_radius=10,
        command=callbacks["browse_folder"],
        font=_font(ctk, 12, "bold", family=font_family),
    ).pack(side="left", padx=(8, 0))
    ctk.CTkButton(
        folder_row,
        text="열기",
        width=64,
        height=36,
        corner_radius=10,
        command=callbacks["open_watch_folder"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    ).pack(side="left", padx=(8, 0))

    folder_hint_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    folder_hint_row.pack(fill="x", padx=18, pady=(0, 6))
    watch_folder_drop_hint_label = ctk.CTkLabel(
        folder_hint_row,
        textvariable=state_vars["watch_folder_drop_hint"],
        font=_font(ctk, 11, family=font_family),
        text_color=("gray45", "gray70"),
        anchor="w",
        justify="left",
    )
    watch_folder_drop_hint_label.pack(fill="x", padx=(118, 0))

    filter_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    filter_row.pack(fill="x", padx=18, pady=6)
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
        height=36,
        font=_font(ctk, 13, family=font_family),
    ).pack(side="left", padx=4)
    ctk.CTkLabel(
        filter_row,
        text="쉼표로 구분 (예: .txt,.log)",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray45", "gray72"),
    ).pack(side="left", padx=(8, 0))
    ctk.CTkButton(
        filter_row,
        text="고급 필터",
        width=92,
        height=36,
        corner_radius=10,
        command=callbacks["show_filter_settings"],
        font=_font(ctk, 12, "bold", family=font_family),
    ).pack(side="right")

    max_cache_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    max_cache_row.pack(fill="x", padx=18, pady=6)
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
        height=36,
        font=_font(ctk, 13, family=font_family),
        validate="key",
        validatecommand=validate_command,
    )
    max_cache_size_entry.pack(side="left", padx=4)
    ctk.CTkLabel(
        max_cache_row,
        text="중복 비교용 전역 라인 캐시에 유지할 최대 항목 수",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray45", "gray72"),
    ).pack(side="left", padx=(8, 0))

    notification_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    notification_row.pack(fill="x", padx=18, pady=6)
    ctk.CTkLabel(
        notification_row,
        text="작업 성공 알림",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    notification_checkbox = ctk.CTkCheckBox(
        notification_row,
        text="Google Docs 기록 성공 시 트레이 알림 표시",
        variable=state_vars["show_success_notifications"],
        onvalue=True,
        offvalue=False,
        font=_font(ctk, 12, family=font_family),
    )
    notification_checkbox.pack(side="left", padx=4)

    autostart_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    autostart_row.pack(fill="x", padx=18, pady=6)
    ctk.CTkLabel(
        autostart_row,
        text="Windows 자동 실행",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    autostart_checkbox = ctk.CTkCheckBox(
        autostart_row,
        text="Windows 로그인 시 자동으로 실행",
        variable=state_vars["launch_on_windows_startup"],
        onvalue=True,
        offvalue=False,
        font=_font(ctk, 12, family=font_family),
    )
    autostart_checkbox.pack(side="left", padx=4)

    autostart_hint_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    autostart_hint_row.pack(fill="x", padx=18, pady=(0, 6))
    autostart_hint_label = ctk.CTkLabel(
        autostart_hint_row,
        textvariable=state_vars["autostart_hint"],
        font=_font(ctk, 11, family=font_family),
        text_color=("gray45", "gray70"),
        anchor="w",
        justify="left",
    )
    autostart_hint_label.pack(fill="x", padx=(118, 0))

    doc_title_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    doc_title_row.pack(fill="x", padx=18, pady=(10, 4))
    ctk.CTkLabel(
        doc_title_row,
        text="문서 작업",
        width=110,
        anchor="w",
        font=_font(ctk, 13, "bold", family=font_family),
    ).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(
        doc_title_row,
        text="생성, 직접 입력, 목록 선택 중 하나를 사용하세요.",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray45", "gray72"),
    ).pack(side="left")

    docs_action_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    docs_action_row.pack(fill="x", padx=18, pady=6)
    create_doc_button = ctk.CTkButton(
        docs_action_row,
        text="새 문서 만들기",
        width=122,
        height=38,
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
        width=152,
        height=38,
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
        width=92,
        height=38,
        corner_radius=12,
        command=callbacks["select_google_doc"],
        font=_font(ctk, 12, "bold", family=font_family),
    )
    select_doc_button.pack(side="left", padx=(8, 0))

    docs_input_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    docs_input_row.pack(fill="x", padx=18, pady=(6, 18))
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
        height=36,
        font=_font(ctk, 13, family=font_family),
        placeholder_text="예: https://docs.google.com/document/d/문서ID/edit 또는 문서 ID",
    )
    docs_input_entry.pack(side="left", fill="x", expand=True, padx=4)

    docs_lock_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
    docs_lock_row.pack(fill="x", padx=18, pady=(0, 18))

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
        width=124,
        height=36,
        corner_radius=10,
        command=callbacks["toggle_docs_target_lock"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color="#1A73E8",
        hover_color="#1765CC",
    )
    docs_lock_button.pack(side="right", padx=(10, 0))

    return {
        "settings_frame": settings_frame,
        "watch_folder_entry": watch_folder_entry,
        "watch_folder_drop_hint_label": watch_folder_drop_hint_label,
        "max_cache_size_entry": max_cache_size_entry,
        "notification_checkbox": notification_checkbox,
        "autostart_checkbox": autostart_checkbox,
        "autostart_hint_label": autostart_hint_label,
        "docs_input_entry": docs_input_entry,
        "create_doc_button": create_doc_button,
        "manual_doc_input_button": manual_doc_input_button,
        "select_doc_button": select_doc_button,
        "docs_target_status_label": docs_target_status_label,
        "docs_lock_button": docs_lock_button,
    }


def _build_control_panel(ctk, parent, callbacks, font_family):
    """실행 및 보조 액션 패널을 생성한다."""
    control_card = ctk.CTkFrame(parent, corner_radius=14)
    control_card.pack(fill="x", pady=(0, 14))

    row = ctk.CTkFrame(control_card, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=16)

    start_button = ctk.CTkButton(
        row,
        text="감시 시작",
        command=callbacks["start_monitoring"],
        width=128,
        height=40,
        corner_radius=12,
        font=_font(ctk, 13, "bold", family=font_family),
        fg_color="#0F9D58",
        hover_color="#0B8043",
    )
    start_button.pack(side="left")

    stop_button = ctk.CTkButton(
        row,
        text="감시 중지",
        command=callbacks["stop_monitoring"],
        width=128,
        height=40,
        corner_radius=12,
        state="disabled",
        font=_font(ctk, 13, "bold", family=font_family),
        fg_color="#C62828",
        hover_color="#B71C1C",
    )
    stop_button.pack(side="left", padx=(10, 0))

    open_docs_button = ctk.CTkButton(
        row,
        text="Docs 웹에서 열기",
        command=callbacks["open_docs_in_browser"],
        width=140,
        height=40,
        corner_radius=12,
        font=_font(ctk, 13, "bold", family=font_family),
        fg_color="#4285F4",
        hover_color="#3367D6",
    )
    open_docs_button.pack(side="left", padx=(10, 0))

    log_popup_button = ctk.CTkButton(
        row,
        text="로그 팝업",
        command=callbacks["show_log_popup"],
        width=102,
        height=40,
        corner_radius=12,
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    log_popup_button.pack(side="left", padx=(10, 0))

    ctk.CTkFrame(row, fg_color="transparent").pack(side="left", fill="x", expand=True)

    ctk.CTkButton(
        row,
        text="테마 설정",
        command=callbacks["show_theme_settings"],
        width=96,
        height=40,
        corner_radius=12,
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    ).pack(side="right")

    ctk.CTkButton(
        row,
        text="백업/복원",
        command=callbacks["show_backup_restore_dialog"],
        width=96,
        height=40,
        corner_radius=12,
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    ).pack(side="right", padx=(0, 10))

    ctk.CTkButton(
        row,
        text="설정 저장",
        command=callbacks["save_config"],
        width=108,
        height=40,
        corner_radius=12,
        font=_font(ctk, 12, "bold", family=font_family),
    ).pack(side="right", padx=(0, 10))

    return {
        "start_button": start_button,
        "stop_button": stop_button,
        "open_docs_button": open_docs_button,
        "log_popup_button": log_popup_button,
    }


def _build_log_panel(ctk, parent, callbacks, font_family):
    """로그 패널을 생성한다."""
    log_card = ctk.CTkFrame(parent, corner_radius=14)
    log_card.pack(fill="both", expand=True)

    header_frame = ctk.CTkFrame(log_card, fg_color="transparent")
    header_frame.pack(fill="x", padx=18, pady=(16, 8))

    header_title = ctk.CTkFrame(header_frame, fg_color="transparent")
    header_title.pack(side="left", fill="x", expand=True)

    ctk.CTkLabel(
        header_title,
        text="작업 로그",
        font=_font(ctk, 16, "bold", family=font_family),
    ).pack(anchor="w")
    ctk.CTkLabel(
        header_title,
        text="실행 결과와 오류를 여기서 바로 확인합니다.",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray40", "gray72"),
    ).pack(anchor="w", pady=(4, 0))

    ctk.CTkLabel(
        header_title,
        text="기본 창이 좁으면 '로그 팝업' 버튼으로 별도 창에서 볼 수 있습니다.",
        font=_font(ctk, 11, family=font_family),
        text_color=("gray45", "gray68"),
    ).pack(anchor="w", pady=(4, 0))

    log_folder_button = ctk.CTkButton(
        header_frame,
        text="로그 폴더 열기",
        width=110,
        height=34,
        corner_radius=10,
        command=callbacks["open_log_folder"],
        font=_font(ctk, 12, "bold", family=font_family),
    )
    log_folder_button.pack(side="right")

    log_search_button = ctk.CTkButton(
        header_frame,
        text="로그 검색",
        width=84,
        height=34,
        corner_radius=10,
        command=callbacks["show_log_search_dialog"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    log_search_button.pack(side="right", padx=(0, 8))

    log_clear_button = ctk.CTkButton(
        header_frame,
        text="로그 지우기",
        width=90,
        height=34,
        corner_radius=10,
        command=callbacks["clear_log"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    log_clear_button.pack(side="right", padx=(0, 8))

    log_text = ctk.CTkTextbox(
        log_card,
        state="disabled",
        wrap="word",
        height=210,
        font=_font(ctk, 12, family=font_family),
        corner_radius=12,
    )
    log_text.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    return {
        "log_folder_button": log_folder_button,
        "log_search_button": log_search_button,
        "log_clear_button": log_clear_button,
        "log_text": log_text,
    }


def _build_result_panel(ctk, parent, callbacks, font_family):
    """최근 추출 결과 미리보기 패널을 생성한다."""
    result_card = ctk.CTkFrame(parent, corner_radius=14)
    result_card.pack(fill="both", expand=False, pady=(0, 14))

    header_frame = ctk.CTkFrame(result_card, fg_color="transparent")
    header_frame.pack(fill="x", padx=18, pady=(16, 8))

    title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    title_frame.pack(side="left", fill="x", expand=True)

    ctk.CTkLabel(
        title_frame,
        text="최근 추출 결과",
        font=_font(ctk, 16, "bold", family=font_family),
    ).pack(anchor="w")
    ctk.CTkLabel(
        title_frame,
        text="로그 파일을 열지 않아도 최근 추출 내용을 바로 확인할 수 있습니다.",
        font=_font(ctk, 12, family=font_family),
        text_color=("gray40", "gray72"),
    ).pack(anchor="w", pady=(4, 0))

    result_clear_button = ctk.CTkButton(
        header_frame,
        text="미리보기 지우기",
        width=112,
        height=34,
        corner_radius=10,
        command=callbacks["clear_extraction_preview"],
        font=_font(ctk, 12, "bold", family=font_family),
        fg_color=("gray85", "gray28"),
        hover_color=("gray78", "gray34"),
        text_color=("gray20", "gray92"),
    )
    result_clear_button.pack(side="right")

    result_preview_text = ctk.CTkTextbox(
        result_card,
        state="disabled",
        wrap="word",
        width=320,
        height=92,
        font=_font(ctk, 12, family=font_family),
        corner_radius=12,
    )
    result_preview_text.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    return {
        "result_preview_text": result_preview_text,
        "result_clear_button": result_clear_button,
    }


def build_main_window_ui(parent, state_vars, callbacks, ctk_module=None, font_family=None):
    """메인 창 UI를 생성하고 필요한 위젯 참조를 반환한다."""
    ctk = _resolve_ctk(ctk_module)

    main_frame = ctk.CTkFrame(parent, fg_color="transparent")
    main_frame.pack(padx=18, pady=18, fill="both", expand=True)

    widget_refs = {}
    widget_refs.update(_build_status_panel(ctk, main_frame, state_vars, callbacks, font_family))
    widget_refs.update(_build_settings_panel(ctk, main_frame, state_vars, callbacks, font_family))
    widget_refs.update(_build_control_panel(ctk, main_frame, callbacks, font_family))

    workspace_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    workspace_frame.pack(fill="both", expand=True)

    result_column = ctk.CTkFrame(workspace_frame, fg_color="transparent")
    result_column.pack(side="left", fill="both", expand=False, padx=(0, 14))

    log_column = ctk.CTkFrame(workspace_frame, fg_color="transparent")
    log_column.pack(side="left", fill="both", expand=True)

    widget_refs.update(_build_result_panel(ctk, result_column, callbacks, font_family))
    widget_refs.update(_build_log_panel(ctk, log_column, callbacks, font_family))
    widget_refs["main_frame"] = main_frame
    widget_refs["workspace_frame"] = workspace_frame
    return widget_refs
