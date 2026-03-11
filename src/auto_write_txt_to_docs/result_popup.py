import ctypes
from ctypes import wintypes


DEFAULT_POPUP_WIDTH = 260
POPUP_X_MARGIN = 12
POPUP_Y_MARGIN = 12
POPUP_RIGHT_SAFE_INSET = 0
POPUP_MIN_HEIGHT = 96
SUCCESS_POPUP_DURATION_MS = 4000
FAILURE_POPUP_DURATION_MS = 6000
MONITOR_DEFAULTTONEAREST = 2
SPI_GETWORKAREA = 0x0030


class RECT(ctypes.Structure):
    """Windows API 작업 영역 좌표를 담는 구조체."""

    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MONITORINFO(ctypes.Structure):
    """Windows 모니터 정보 조회용 구조체."""

    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class ResultPopupPresenter:
    """작업 결과를 화면 우하단 소형 팝업으로 표시한다."""

    LEVEL_STYLE = {
        "success": {
            "background": ("#F0FDF4", "#0B1F14"),
            "border": ("#86EFAC", "#166534"),
            "accent": ("#15803D", "#4ADE80"),
            "title": ("#14532D", "#DCFCE7"),
            "message": ("#166534", "#BBF7D0"),
        },
        "duplicate": {
            "background": ("#FFFBEB", "#221A07"),
            "border": ("#FCD34D", "#A16207"),
            "accent": ("#B45309", "#FBBF24"),
            "title": ("#78350F", "#FEF3C7"),
            "message": ("#92400E", "#FDE68A"),
        },
        "failure": {
            "background": ("#FEF2F2", "#2A0F12"),
            "border": ("#FCA5A5", "#B91C1C"),
            "accent": ("#DC2626", "#F87171"),
            "title": ("#7F1D1D", "#FEE2E2"),
            "message": ("#991B1B", "#FECACA"),
        },
    }

    def __init__(self, root, ctk_module=None, logger=None):
        self.root = root
        self.ctk = ctk_module
        if self.ctk is None:
            import customtkinter as ctk

            self.ctk = ctk
        self.logger = logger
        self.popup_window = None
        self.close_after_id = None
        self.last_payload = None

    def show(self, title, message, level):
        """현재 팝업을 최신 이벤트로 교체해 표시한다."""
        if not self.root or not self._root_exists():
            return False

        normalized_level = self._normalize_level(level)
        normalized_title = self._normalize_title(title)
        normalized_message = self._normalize_message(message)
        if not normalized_message:
            return False

        self.close()
        popup_window = self.ctk.CTkToplevel(self.root)
        popup_window.title(normalized_title)
        self._configure_window(popup_window)

        style = self.LEVEL_STYLE[normalized_level]
        container = self.ctk.CTkFrame(
            popup_window,
            corner_radius=14,
            fg_color=style["background"],
            border_width=1,
            border_color=style["border"],
        )
        container.pack(fill="both", expand=True, padx=1, pady=1)

        accent_bar = self.ctk.CTkFrame(
            container,
            width=8,
            corner_radius=14,
            fg_color=style["accent"],
        )
        accent_bar.pack(side="left", fill="y", padx=(0, 8), pady=0)

        content_frame = self.ctk.CTkFrame(container, fg_color="transparent")
        content_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        header_frame = self.ctk.CTkFrame(content_frame, fg_color="transparent")
        header_frame.pack(fill="x")

        self.ctk.CTkLabel(
            header_frame,
            text=normalized_title,
            anchor="w",
            justify="left",
            text_color=style["title"],
            font=self._build_font(size=13, weight="bold"),
        ).pack(side="left", fill="x", expand=True)

        self.ctk.CTkButton(
            header_frame,
            text="닫기",
            width=38,
            height=24,
            corner_radius=999,
            command=self.close,
            fg_color=style["accent"],
            hover_color=style["border"],
            text_color=("#F9FAFB", "#111827"),
            border_width=1,
            border_color=style["border"],
            font=self._build_font(size=10, weight="bold"),
        ).pack(side="right", padx=(6, 0))

        self.ctk.CTkLabel(
            content_frame,
            text=normalized_message,
            anchor="w",
            justify="left",
            wraplength=DEFAULT_POPUP_WIDTH - 84,
            text_color=style["message"],
            font=self._build_font(size=11),
        ).pack(fill="x", pady=(6, 0))

        try:
            popup_window.deiconify()
            popup_window.lift()
            popup_window.update_idletasks()
        except Exception:
            pass

        self._place_popup(popup_window)
        try:
            popup_window.after(0, lambda: self._refresh_popup_geometry(popup_window))
        except Exception:
            pass

        self.popup_window = popup_window
        self.last_payload = {
            "title": normalized_title,
            "message": normalized_message,
            "level": normalized_level,
        }
        self.close_after_id = self.root.after(
            self._resolve_duration_ms(normalized_level),
            self.close,
        )
        return True

    def close(self):
        """표시 중인 팝업과 자동 닫힘 타이머를 정리한다."""
        if self.close_after_id and self._root_exists():
            try:
                self.root.after_cancel(self.close_after_id)
            except Exception:
                pass
        self.close_after_id = None

        popup_window = self.popup_window
        self.popup_window = None
        if popup_window is not None and self._window_exists(popup_window):
            try:
                popup_window.destroy()
            except Exception:
                pass

    def _configure_window(self, popup_window):
        """팝업 창의 공통 속성을 지정한다."""
        try:
            popup_window.resizable(False, False)
        except Exception:
            pass
        try:
            popup_window.attributes("-topmost", True)
        except Exception:
            pass
        try:
            popup_window.overrideredirect(True)
        except Exception:
            pass
        try:
            popup_window.configure(fg_color=("gray95", "gray10"))
        except Exception:
            pass

    def _place_popup(self, popup_window):
        """현재 화면의 작업 가능 영역 우하단으로 팝업 위치를 맞춘다."""
        popup_width, popup_height = self._get_popup_dimensions(popup_window)
        work_area_left, work_area_top, work_area_right, work_area_bottom = self._get_work_area_bounds(popup_window)
        window_scaling = self._get_window_scaling()
        scaled_popup_width = int(round(popup_width * window_scaling))
        scaled_popup_height = int(round(popup_height * window_scaling))
        x_pos = max(work_area_left, work_area_right - scaled_popup_width - POPUP_X_MARGIN - POPUP_RIGHT_SAFE_INSET)
        y_pos = max(work_area_top, work_area_bottom - scaled_popup_height - POPUP_Y_MARGIN)
        popup_window.geometry(f"{popup_width}x{popup_height}+{x_pos}+{y_pos}")

    def _get_popup_dimensions(self, popup_window):
        """현재 레이아웃이 요구하는 실제 팝업 크기를 계산한다."""
        try:
            requested_width = int(popup_window.winfo_reqwidth())
        except Exception:
            requested_width = 0

        try:
            requested_height = int(popup_window.winfo_reqheight())
        except Exception:
            requested_height = 0

        popup_width = max(DEFAULT_POPUP_WIDTH, requested_width)
        popup_height = max(POPUP_MIN_HEIGHT, requested_height)
        return popup_width, popup_height

    def _refresh_popup_geometry(self, popup_window):
        """초기 렌더링 직후 한 번 더 실제 크기로 재배치한다."""
        if not self._window_exists(popup_window):
            return

        try:
            popup_window.update_idletasks()
        except Exception:
            pass
        self._place_popup(popup_window)

    def _get_work_area_bounds(self, popup_window):
        """팝업을 붙일 작업 영역 좌표를 계산한다."""
        work_area_bounds = self._get_windows_work_area(popup_window)
        if work_area_bounds is not None:
            return work_area_bounds

        screen_width = int(self.root.winfo_screenwidth())
        screen_height = int(self.root.winfo_screenheight())
        return 0, 0, screen_width, screen_height

    def _get_windows_work_area(self, popup_window):
        """Windows 작업 표시줄을 제외한 작업 가능 영역을 구한다."""
        windll = getattr(ctypes, "windll", None)
        if windll is None:
            return None

        try:
            user32 = windll.user32
            hwnd = self._get_window_handle(popup_window) or self._get_window_handle(self.root)
            if hwnd:
                monitor_handle = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
                if monitor_handle:
                    monitor_info = MONITORINFO()
                    monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
                    if user32.GetMonitorInfoW(monitor_handle, ctypes.byref(monitor_info)):
                        return (
                            int(monitor_info.rcWork.left),
                            int(monitor_info.rcWork.top),
                            int(monitor_info.rcWork.right),
                            int(monitor_info.rcWork.bottom),
                        )

            work_area = RECT()
            if user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(work_area), 0):
                return (
                    int(work_area.left),
                    int(work_area.top),
                    int(work_area.right),
                    int(work_area.bottom),
                )
        except Exception:
            return None

        return None

    def _resolve_duration_ms(self, level):
        """알림 유형별 자동 닫힘 시간을 계산한다."""
        if level == "failure":
            return FAILURE_POPUP_DURATION_MS
        return SUCCESS_POPUP_DURATION_MS

    def _normalize_level(self, level):
        """지원되지 않는 레벨을 안전한 기본값으로 정리한다."""
        if level in self.LEVEL_STYLE:
            return level
        return "success"

    def _normalize_title(self, title):
        """제목을 한 줄 텍스트로 압축한다."""
        normalized_title = str(title or "").strip()
        if not normalized_title:
            normalized_title = "작업 결과 알림"
        return normalized_title.replace("\n", " ")

    def _normalize_message(self, message):
        """본문을 최대 3줄로 정리해 팝업에 맞춘다."""
        lines = [line.strip() for line in str(message or "").splitlines() if line.strip()]
        if not lines:
            return ""
        visible_lines = lines[:3]
        hidden_line_count = len(lines) - len(visible_lines)
        if hidden_line_count > 0:
            visible_lines[-1] = f"{visible_lines[-1]}  외 {hidden_line_count}줄"
        return "\n".join(visible_lines)

    def _build_font(self, size, weight="normal"):
        """customtkinter 폰트 팩토리를 사용할 수 있으면 활용한다."""
        font_factory = getattr(self.ctk, "CTkFont", None)
        if font_factory is None:
            return None
        return font_factory(size=size, weight=weight)

    def _get_window_handle(self, window):
        """Tk 창 객체에서 Windows HWND를 꺼낸다."""
        try:
            return int(window.winfo_id())
        except Exception:
            return None

    def _get_window_scaling(self):
        """customtkinter 창 스케일을 안전하게 읽어온다."""
        try:
            scaling_value = float(self.root._get_window_scaling())
            return scaling_value if scaling_value > 0 else 1.0
        except Exception:
            return 1.0

    def _root_exists(self):
        """루트 창이 아직 살아 있는지 확인한다."""
        try:
            return bool(self.root.winfo_exists())
        except Exception:
            return False

    def _window_exists(self, window):
        """팝업 창이 아직 살아 있는지 확인한다."""
        try:
            return bool(window.winfo_exists())
        except Exception:
            return False
