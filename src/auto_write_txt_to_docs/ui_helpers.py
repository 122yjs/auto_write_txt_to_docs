def build_center_geometry(width, height, screen_width, screen_height):
    """주어진 크기를 화면 중앙에 배치할 geometry 문자열을 반환한다."""
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    return f"{width}x{height}+{x}+{y}"


def center_window(window):
    """Tk 계열 창을 화면 중앙에 배치한다."""
    window.update_idletasks()
    geometry = build_center_geometry(
        window.winfo_width(),
        window.winfo_height(),
        window.winfo_screenwidth(),
        window.winfo_screenheight(),
    )
    window.geometry(geometry)
    return geometry


def show_backup_restore_dialog(parent, on_backup, on_restore, ctk_module=None):
    """설정 백업/복원 대화상자를 생성해 표시한다."""
    ctk = ctk_module
    if ctk is None:
        import customtkinter as ctk

    backup_window = ctk.CTkToplevel(parent)
    backup_window.title("설정 백업 및 복원")
    backup_window.geometry("550x400")
    backup_window.minsize(550, 400)
    backup_window.transient(parent)
    backup_window.grab_set()

    main_frame = ctk.CTkFrame(backup_window)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    title_label = ctk.CTkLabel(
        main_frame,
        text="설정 백업 및 복원",
        font=ctk.CTkFont(size=16, weight="bold"),
    )
    title_label.pack(pady=(0, 15))

    description = ctk.CTkLabel(
        main_frame,
        text="현재 설정을 백업하거나 이전에 백업한 설정을 복원할 수 있습니다.",
        wraplength=350,
    )
    description.pack(pady=(0, 20))

    backup_frame = ctk.CTkFrame(main_frame)
    backup_frame.pack(fill="x", pady=(0, 15))

    ctk.CTkLabel(
        backup_frame,
        text="설정 백업",
        font=ctk.CTkFont(weight="bold"),
    ).pack(anchor="w", pady=(5, 10), padx=10)

    ctk.CTkLabel(
        backup_frame,
        text="현재 설정을 파일로 저장합니다.",
        wraplength=350,
    ).pack(anchor="w", padx=10)

    ctk.CTkButton(
        backup_frame,
        text="설정 백업",
        command=lambda: [backup_window.destroy(), on_backup()],
        width=120,
    ).pack(anchor="w", pady=10, padx=10)

    restore_frame = ctk.CTkFrame(main_frame)
    restore_frame.pack(fill="x", pady=(0, 15))

    ctk.CTkLabel(
        restore_frame,
        text="설정 복원",
        font=ctk.CTkFont(weight="bold"),
    ).pack(anchor="w", pady=(5, 10), padx=10)

    ctk.CTkLabel(
        restore_frame,
        text="백업 파일에서 설정을 불러옵니다.",
        wraplength=350,
    ).pack(anchor="w", padx=10)

    ctk.CTkButton(
        restore_frame,
        text="설정 복원",
        command=lambda: [backup_window.destroy(), on_restore()],
        width=120,
    ).pack(anchor="w", pady=10, padx=10)

    close_button = ctk.CTkButton(
        main_frame,
        text="닫기",
        command=backup_window.destroy,
        width=100,
    )
    close_button.pack(side="right", pady=(10, 0))

    center_window(backup_window)
    return backup_window
