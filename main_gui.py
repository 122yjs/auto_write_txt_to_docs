# main_gui.py (아이콘 생성 + Docs 기록 + 트레이 기능 버전)
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import font as tkfont
import os
import json
import threading
import queue
import re
import time
import subprocess
import platform
import logging
import webbrowser
from datetime import datetime
import psutil  # 메모리 사용량 모니터링용
import shutil
from pathlib import Path

# --- 트레이 아이콘 관련 라이브러리 임포트 ---
from PIL import Image, ImageDraw # Pillow에서 ImageDraw 추가
import pystray

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None

# backend_processor 임포트
try:
    # Docs 기록 기능 버전의 backend_processor 임포트
    from src.auto_write_txt_to_docs.backend_processor import run_monitoring
except ImportError:
    # ⚠️ 수정: 모듈 레벨에서 root 없이 messagebox 호출하면 불안정 → logging으로 교체
    logging.error("백엔드 처리 모듈(backend_processor.py)을 찾을 수 없습니다.")
    run_monitoring = None  # 함수 부재 처리

try:
    from src.auto_write_txt_to_docs.google_auth import (
        create_google_document,
        get_google_services,
        list_accessible_google_documents,
    )
except ImportError:
    logging.error("Google 인증 모듈(google_auth.py)을 찾을 수 없습니다.")
    create_google_document = None
    get_google_services = None
    list_accessible_google_documents = None

# path_utils 임포트 (공통 경로 정책 사용)
try:
    from src.auto_write_txt_to_docs.path_utils import (
        BUNDLED_CREDENTIALS_FILE_STR,
        CONFIG_FILE_STR,
        USER_CREDENTIALS_FILE_STR,
        LEGACY_CONFIG_FILE_STR,
        LOG_DIR_STR,
        get_effective_credentials_path,
    )
except ImportError:
    logging.error("경로 유틸리티 모듈(path_utils.py)을 찾을 수 없습니다.")
    BUNDLED_CREDENTIALS_FILE_STR = None
    CONFIG_FILE_STR = "config.json"
    USER_CREDENTIALS_FILE_STR = "developer_credentials.json"
    LEGACY_CONFIG_FILE_STR = "config.json"
    LOG_DIR_STR = "logs"
    get_effective_credentials_path = None

try:
    from src.auto_write_txt_to_docs.config_manager import (
        load_app_config,
        load_backup_config,
        normalize_config_data,
        save_app_config,
        save_backup_config,
    )
except ImportError:
    logging.error("설정 관리 모듈(config_manager.py)을 찾을 수 없습니다.")
    load_app_config = None
    load_backup_config = None
    normalize_config_data = None
    save_app_config = None
    save_backup_config = None

try:
    from src.auto_write_txt_to_docs.autostart_utils import (
        is_windows_startup_enabled,
        set_windows_startup_enabled,
        supports_windows_startup,
    )
except ImportError:
    logging.error("자동 실행 유틸리티 모듈(autostart_utils.py)을 찾을 수 없습니다.")
    is_windows_startup_enabled = None
    set_windows_startup_enabled = None
    supports_windows_startup = None

try:
    from src.auto_write_txt_to_docs.ui_helpers import center_window, show_backup_restore_dialog
except ImportError:
    logging.error("UI 헬퍼 모듈(ui_helpers.py)을 찾을 수 없습니다.")
    center_window = None
    show_backup_restore_dialog = None

try:
    from src.auto_write_txt_to_docs.main_window_ui import build_main_window_ui
except ImportError:
    logging.error("메인 창 UI 모듈(main_window_ui.py)을 찾을 수 없습니다.")
    build_main_window_ui = None

try:
    from src.auto_write_txt_to_docs.app_dialogs import (
        show_credentials_wizard_dialog,
        show_enhanced_error_dialog as show_enhanced_error_dialog_window,
        show_help_dialog as show_help_dialog_window,
        show_theme_settings_dialog,
    )
except ImportError:
    logging.error("대화상자 UI 모듈(app_dialogs.py)을 찾을 수 없습니다.")
    show_credentials_wizard_dialog = None
    show_enhanced_error_dialog_window = None
    show_help_dialog_window = None
    show_theme_settings_dialog = None


if TkinterDnD:
    class DnDCompatibleTk(ctk.CTk, TkinterDnD.DnDWrapper):
        """customtkinter 루트에 tkinterdnd2 지원을 결합한다."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    DnDCompatibleTk = ctk.CTk

# --- Helper Function: URL에서 ID 추출 ---
def extract_google_id_from_url(url_or_id):
    """ Google Docs URL에서 ID 추출 """
    if not url_or_id or not isinstance(url_or_id, str): return url_or_id
    match_docs = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url_or_id)
    return match_docs.group(1) if match_docs else url_or_id


def format_google_modified_time(modified_time_text):
    """Google Drive 수정 시각 문자열을 사용자에게 읽기 쉬운 형식으로 변환한다."""
    if not modified_time_text:
        return "수정 시각 정보 없음"

    try:
        normalized_text = modified_time_text.replace("Z", "+00:00")
        parsed_time = datetime.fromisoformat(normalized_text)
        return parsed_time.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return modified_time_text

def detect_ui_font_family(root):
    """현재 플랫폼에서 사용 가능한 한글 친화 UI 폰트를 선택한다."""
    platform_candidates = {
        "Windows": ("Malgun Gothic", "맑은 고딕", "Segoe UI"),
        "Darwin": ("Apple SD Gothic Neo", "AppleGothic", "Arial Unicode MS"),
        "Linux": ("Noto Sans CJK KR", "Noto Sans KR", "Noto Sans", "Arial Unicode MS"),
    }

    try:
        available_families = {str(name) for name in tkfont.families(root)}
    except tk.TclError:
        return None

    for candidate in platform_candidates.get(platform.system(), ()):
        if candidate in available_families:
            return candidate

    return None

def extract_docs_update_line_count(message):
    """Docs 업데이트 관련 로그에서 줄 수를 추출한다."""
    if not isinstance(message, str):
        return None

    match = re.search(r'(\d+)줄 추가', message)
    if not match:
        return None

    try:
        return int(match.group(1))
    except ValueError:
        return None


def extract_filename_from_log_message(message):
    """백엔드 로그 메시지에서 파일명을 추출한다."""
    if not isinstance(message, str):
        return None

    explicit_match = re.search(r'파일:\s*([^,\)]+)', message)
    if explicit_match:
        return explicit_match.group(1).strip()

    start_match = re.search(r'처리 시작:\s*(.+)$', message)
    if start_match:
        return start_match.group(1).strip()

    complete_match = re.search(r'처리 완료:\s*(.+)$', message)
    if complete_match:
        return complete_match.group(1).strip()

    return None

class MessengerDocsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("메신저 Docs 자동 기록 (트레이)")
        self.ui_font_family = detect_ui_font_family(self.root)
        # 초기 창 크기를 충분히 크게 설정하고, 최소 크기도 지정하여 버튼이 잘리는 현상 방지
        self.root.geometry("900x750")
        self.root.minsize(900, 750)

        # --- 상단 메뉴바 생성 ---
        self._create_menubar()

        # 테마 설정 (⚠️ 수정: 중복 선언이었던 L137의 두 번째 선언 제거)
        self.appearance_mode = ctk.StringVar(value="System")  # 기본값: 시스템 설정 따름
        ctk.set_appearance_mode(self.appearance_mode.get())
        ctk.set_default_color_theme("blue")

        # 메모리 모니터링 관련 변수
        self.memory_usage = ctk.StringVar(value="메모리: 확인 중...")
        self.memory_check_interval = 10000  # 10초마다 메모리 사용량 확인

        # --- 변수 선언 ---
        self.first_run = tk.BooleanVar(value=True)
        self.launch_on_windows_startup = tk.BooleanVar(value=False)
        self.watch_folder = ctk.StringVar()
        self.watch_folder_drop_hint = ctk.StringVar(value="폴더를 여기로 끌어다 놓거나 '폴더 선택' 버튼을 사용하세요.")
        self.autostart_hint = ctk.StringVar(value="Windows 로그인 시 자동 실행 여부를 저장합니다.")
        self.docs_input = ctk.StringVar()
        self.docs_target_locked = tk.BooleanVar(value=False)
        self.docs_target_status_var = ctk.StringVar(value="문서를 지정하면 여기서 고정 상태를 확인할 수 있습니다.")
        self.show_help_on_startup = tk.BooleanVar(value=True)  # 도움말 표시 여부
        self.show_success_notifications = tk.BooleanVar(value=True)

        # 파일 필터링 관련 변수
        self.file_extensions = ctk.StringVar(value=".txt")  # 기본값: .txt 파일만 감시
        self.use_regex_filter = tk.BooleanVar(value=False)  # 정규식 필터 사용 여부
        self.regex_pattern = ctk.StringVar(value="")  # 정규식 패턴
        self.max_cache_size = ctk.StringVar(value="10000")

        self.is_monitoring = False
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.log_popup_window = None
        self.log_popup_text = None

        self.tray_icon = None
        self.tray_thread = None
        self.base_icon_image = None
        self.icon_image = None # 아이콘 이미지 객체 저장
        self.pending_docs_update_line_count = None
        self.current_processing_filename = None
        
        # 상태 표시 변수
        self.status_var = ctk.StringVar(value="준비")
        
        # 로깅 시스템 초기화
        self.setup_logging()
        
        # 설정 변수 변경 감지를 위한 추적
        self.first_run.trace_add("write", self.on_setting_changed)
        self.launch_on_windows_startup.trace_add("write", self.on_setting_changed)
        self.watch_folder.trace_add("write", self.on_setting_changed)
        self.docs_input.trace_add("write", self.on_setting_changed)
        self.show_help_on_startup.trace_add("write", self.on_setting_changed)
        self.show_success_notifications.trace_add("write", self.on_setting_changed)
        self.max_cache_size.trace_add("write", self.on_setting_changed)
        self.settings_changed = False

        # --- 아이콘 이미지 생성 또는 로드 ---
        self.create_or_load_icon() # 함수 이름 변경

        # --- 위젯 생성 ---
        self.create_widgets()

        # --- 설정 로드 ---
        self.load_config()
        self.settings_changed = False  # 로드 후 변경 플래그 초기화
        self.root.after(50, self.present_main_window)

        # --- 로그 큐 처리 ---
        self.root.after(100, self.process_log_queue)
        self.root.after(100, self.process_result_queue)
        
        # --- 메모리 사용량 모니터링 시작 ---
        self.root.after(1000, self.check_memory_usage)

        # --- 창 닫기(X) 버튼 누르면 숨기도록 설정 ---
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window) # 변경 없음

        # --- 트레이 아이콘 설정 및 시작 ---
        if self.icon_image: # 아이콘 준비 완료 시
            self.setup_tray_icon()
            self.start_tray_icon()
        else:
             self.log("오류: 아이콘 이미지를 준비할 수 없어 트레이 기능을 시작할 수 없습니다.")
        
        # --- 초기화 완료 로그 ---
        self.log("애플리케이션 초기화 완료.")
        self.log("설정을 확인하고 '감시 시작' 버튼을 클릭하세요.")

        # --- 초기 안내/검사 대화상자는 메인 창 표시 후 실행 ---
        self.root.after(250, self.run_startup_prompts)

    def build_ui_font(self, size, weight="normal"):
        """현재 플랫폼에 맞는 UI 폰트를 생성한다."""
        font_kwargs = {
            "size": size,
            "weight": weight,
        }
        if self.ui_font_family:
            font_kwargs["family"] = self.ui_font_family
        return ctk.CTkFont(**font_kwargs)

    def present_main_window(self):
        """메인 창을 화면 중앙에 배치하고 전면으로 올린다."""
        if center_window:
            center_window(self.root)
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except tk.TclError:
            pass

    def run_startup_prompts(self):
        """메인 창이 그려진 뒤 초기 안내 대화상자를 순차적으로 표시한다."""
        if self.first_run.get():
            self.root.after(400, self.show_first_run_wizard)
            return

        self.check_credentials_file()
        if self.show_help_on_startup.get():
            self.root.after(400, self.show_help_dialog)


    def check_credentials_file(self):
        """ Google API 인증 파일 (developer_credentials.json) 존재 여부 확인 및 안내 """
        if not BUNDLED_CREDENTIALS_FILE_STR and not USER_CREDENTIALS_FILE_STR:
            self.log("오류: 인증 파일 경로 상수가 설정되지 않았습니다. path_utils.py를 확인하세요.")
            messagebox.showwarning(
                "설정 오류",
                "프로그램 내부 설정(인증 파일 경로)에 문제가 있습니다.\n개발자에게 문의하세요.",
                parent=self.root
            )
            return

        credentials_path = str(get_effective_credentials_path()) if get_effective_credentials_path else BUNDLED_CREDENTIALS_FILE_STR
        credential_source = "사용자 설정 폴더" if USER_CREDENTIALS_FILE_STR and credentials_path == USER_CREDENTIALS_FILE_STR else "기본 번들 경로"

        self.log(f"확인 중인 인증 파일 경로: {credentials_path} ({credential_source})")

        if not os.path.exists(credentials_path):
            self.log(f"경고: 인증 파일({credentials_path})을 찾을 수 없습니다.")
            open_wizard = messagebox.askyesno(
                "인증 파일 누락",
                "Google API 인증을 위한 'developer_credentials.json' 파일을 찾을 수 없습니다.\n\n"
                f"사용자 설정 경로: {USER_CREDENTIALS_FILE_STR}\n"
                f"기본 번들 경로: {BUNDLED_CREDENTIALS_FILE_STR}\n\n"
                "프로그램 사용을 위해서는 이 파일이 필요합니다.\n"
                "README.md 파일의 '설정' 섹션을 참고하거나,\n"
                "바로 이어서 'Google 인증 설정 마법사'를 통해 사용자 설정 폴더에 복사할 수 있습니다.\n\n"
                "설정 마법사를 지금 열어 파일을 준비하시겠습니까?",
                parent=self.root
            )
            if open_wizard:
                self.show_credentials_wizard()
        else:
            self.log(f"정보: 인증 파일({credentials_path}) 확인 완료.")


    def create_default_icon(self):
        """ Pillow를 사용하여 기본 아이콘 이미지 생성 """
        width = 64
        height = 64
        # 파란색 배경의 아이콘 생성 (원하는 색상으로 변경 가능)
        color1 = (20, 20, 160) # RGB 색상 (진한 파랑)
        color2 = (80, 80, 220) # RGB 색상 (밝은 파랑 - 그라데이션 효과용)

        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        # 간단한 그라데이션 효과 (선택적)
        dc.rectangle([(0,0), (width, height//2)], fill=color2)
        # 간단한 문자 추가 (선택적)
        # try:
        #     # 폰트 로드 시도 (시스템에 따라 경로 다름, 없을 수 있음)
        #     from PIL import ImageFont
        #     font = ImageFont.truetype("arial.ttf", 40)
        #     dc.text((10, 5), "A", font=font, fill=(255, 255, 255))
        # except ImportError: pass # ImageFont 없으면 무시
        # except OSError: pass # 폰트 파일 없으면 무시

        self.log("기본 아이콘 이미지 생성 완료.")
        return image

    def get_tray_state_key(self, tray_status_text):
        """트레이에 표시할 현재 상태 키를 계산한다."""
        status_text = str(tray_status_text or "").strip()
        if "오류" in status_text or "기록 불가" in status_text:
            return "error"
        if "처리 중" in status_text:
            return "processing"
        if "감시 중" in status_text or "업데이트 완료" in status_text:
            return "monitoring"
        if "중지" in status_text:
            return "stopped"
        return "ready"

    def build_tray_status_icon(self, state_key):
        """기본 아이콘 위에 상태 점을 덧씌운 트레이 아이콘 이미지를 생성한다."""
        base_image = self.base_icon_image or self.icon_image
        if base_image is None:
            return None

        status_palette = {
            "ready": ("#1A73E8", "#8AB4F8"),
            "monitoring": ("#0F9D58", "#81C995"),
            "processing": ("#FB8C00", "#FBC02D"),
            "stopped": ("#6B7280", "#9CA3AF"),
            "error": ("#C62828", "#F28B82"),
        }
        outer_color, inner_color = status_palette.get(state_key, status_palette["ready"])

        icon_image = base_image.convert("RGBA").copy()
        draw = ImageDraw.Draw(icon_image)
        diameter = max(14, icon_image.width // 3)
        margin = 4
        left = icon_image.width - diameter - margin
        top = icon_image.height - diameter - margin
        right = left + diameter
        bottom = top + diameter
        draw.ellipse((left, top, right, bottom), fill=outer_color, outline=(255, 255, 255, 235), width=2)
        draw.ellipse((left + 4, top + 4, right - 4, bottom - 4), fill=inner_color)
        return icon_image

    def create_or_load_icon(self):
        """ 아이콘 파일을 로드하거나 없으면 기본 아이콘 생성 """
        icon_path_temp = "icon.png" # 임시로 파일명 지정 (로드 시도용)
        try:
            # 1. 파일 로드 시도 (기존 로직 유지)
            self.base_icon_image = Image.open(icon_path_temp)
            self.log(f"아이콘 파일 로드 성공: {icon_path_temp}")
        except FileNotFoundError:
            # 2. 파일이 없으면 기본 아이콘 생성
            self.log(f"정보: 아이콘 파일({icon_path_temp}) 없음. 기본 아이콘을 생성합니다.")
            self.base_icon_image = self.create_default_icon()
        except Exception as e:
            # 3. 로드/생성 중 기타 오류 발생
            messagebox.showerror("아이콘 오류", f"아이콘 준비 중 오류 발생:\n{e}", parent=self.root)
            self.log(f"오류: 아이콘 준비 실패 - {e}")
            self.icon_image = None # 오류 시 아이콘 없음 처리
            self.base_icon_image = None
            return

        self.icon_image = self.build_tray_status_icon("ready") or self.base_icon_image
    
    def setup_logging(self):
        """로깅 시스템 설정"""
        try:
            # 공통 경로 정책(path_utils)의 로그 디렉토리 사용
            log_dir = LOG_DIR_STR
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                print(f"로그 디렉토리 생성: {log_dir}")
            
            # 로그 파일명 (날짜별)
            log_filename = os.path.join(log_dir, f"messenger_docs_{datetime.now().strftime('%Y%m%d')}.log")
            print(f"로그 파일 경로: {log_filename}")
            
            # 기존 로거 완전 초기화
            logger_name = 'MessengerDocsApp'
            if logger_name in logging.Logger.manager.loggerDict:
                del logging.Logger.manager.loggerDict[logger_name]
            
            # 새로운 로거 생성
            self.logger = logging.getLogger(logger_name)
            self.logger.setLevel(logging.INFO)
            self.logger.handlers.clear()  # 모든 핸들러 제거
            
            # 파일 핸들러 생성 (mode='a'로 추가 모드 사용)
            file_handler = logging.FileHandler(log_filename, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 포맷터 설정
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            
            # 핸들러 추가
            self.logger.addHandler(file_handler)
            
            # 로깅 시작 메시지 (즉시 기록)
            self.logger.info("애플리케이션 시작 - 로깅 시스템 초기화 완료")
            
            # 강제 flush
            file_handler.flush()
            
            print("로깅 시스템 초기화 완료")
            
            # 로그 파일 내용 확인
            if os.path.exists(log_filename):
                file_size = os.path.getsize(log_filename)
                print(f"로그 파일 생성 확인: {log_filename} (크기: {file_size} bytes)")
            else:
                print(f"로그 파일 생성 실패: {log_filename}")
            
        except Exception as e:
            print(f"로깅 설정 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    
    def on_setting_changed(self, *args):
        """설정 변경 감지 및 상태 표시 업데이트"""
        self.settings_changed = True
        
        # 감시 폴더 정보 업데이트
        folder_path = self.watch_folder.get().strip()
        if folder_path:
            folder_name = os.path.basename(folder_path) or folder_path
            self.folder_info_var.set(f"폴더: {folder_name}")
        else:
            self.folder_info_var.set("폴더: 설정되지 않음")
            
        # Docs 문서 정보 업데이트
        docs_input = self.docs_input.get().strip()
        if docs_input:
            # URL에서 ID 추출
            docs_id = extract_google_id_from_url(docs_input)
            if len(docs_id) > 12:  # ID가 너무 길면 줄임
                docs_id_display = docs_id[:10] + "..."
            else:
                docs_id_display = docs_id
            self.docs_info_var.set(f"문서: {docs_id_display}")
        else:
            self.docs_info_var.set("문서: 설정되지 않음")

        self.refresh_docs_target_ui()

    def refresh_docs_target_ui(self):
        """문서 대상 고정 상태에 따라 입력/선택 UI를 갱신한다."""
        docs_input_val = self.docs_input.get().strip()
        locked = bool(self.docs_target_locked.get() and docs_input_val)

        if self.docs_target_locked.get() != locked:
            self.docs_target_locked.set(locked)

        if locked:
            status_text = "대상 문서가 고정되었습니다. 감시 시작 시 이 문서로 기록합니다."
            status_color = ("#0F9D58", "#81C995")
            lock_button_text = "문서 경로 변경"
            lock_button_color = ("gray85", "gray28")
            lock_button_hover = ("gray78", "gray34")
            lock_button_text_color = ("gray20", "gray92")
        elif docs_input_val:
            status_text = "문서 입력 중입니다. '문서 경로 확정' 버튼을 눌러 고정하세요."
            status_color = ("#1A73E8", "#8AB4F8")
            lock_button_text = "문서 경로 확정"
            lock_button_color = "#1A73E8"
            lock_button_hover = "#1765CC"
            lock_button_text_color = None
        else:
            status_text = "문서를 지정하면 여기서 고정 상태를 확인할 수 있습니다."
            status_color = ("gray40", "gray70")
            lock_button_text = "문서 경로 확정"
            lock_button_color = "#1A73E8"
            lock_button_hover = "#1765CC"
            lock_button_text_color = None

        self.docs_target_status_var.set(status_text)

        if hasattr(self, "docs_target_status_label"):
            self.docs_target_status_label.configure(text_color=status_color)

        if hasattr(self, "docs_lock_button"):
            configure_kwargs = {
                "text": lock_button_text,
                "fg_color": lock_button_color,
                "hover_color": lock_button_hover,
            }
            if lock_button_text_color is not None:
                configure_kwargs["text_color"] = lock_button_text_color
            else:
                configure_kwargs["text_color"] = ("white", "white")
            self.docs_lock_button.configure(**configure_kwargs)

        entry_state = "disabled" if locked else "normal"
        if hasattr(self, "docs_input_entry"):
            self.docs_input_entry.configure(state=entry_state)

        selection_state = "disabled" if locked else "normal"
        for widget_name in ("create_doc_button", "manual_doc_input_button", "select_doc_button"):
            if hasattr(self, widget_name):
                getattr(self, widget_name).configure(state=selection_state)

    def lock_docs_target(self, source_label="직접 입력"):
        """현재 입력된 문서를 대상 문서로 고정한다."""
        docs_input_val = self.docs_input.get().strip()
        if not docs_input_val:
            messagebox.showwarning("문서 경로 미지정", "먼저 문서 주소 또는 문서 ID를 입력해주세요.", parent=self.root)
            return False

        self.docs_target_locked.set(True)
        self.refresh_docs_target_ui()
        self.log(f"대상 문서 경로 고정됨: {source_label}")
        return True

    def unlock_docs_target(self, focus_entry=False):
        """대상 문서 고정을 해제하고 수정 모드로 전환한다."""
        was_locked = self.docs_target_locked.get()
        self.docs_target_locked.set(False)
        self.refresh_docs_target_ui()
        if was_locked:
            self.log("대상 문서 경로 고정 해제됨. 문서 변경 가능.")
        else:
            self.log("문서 직접 입력 모드로 전환됨.")

        if focus_entry and hasattr(self, "docs_input_entry"):
            self.docs_input_entry.focus_set()
            self.docs_input_entry.icursor(ctk.END)

    def toggle_docs_target_lock(self):
        """대상 문서 경로의 고정/수정 상태를 전환한다."""
        if self.docs_target_locked.get():
            self.unlock_docs_target(focus_entry=True)
            return

        self.lock_docs_target(source_label="직접 입력")

    def validate_positive_integer_input(self, proposed_value):
        """캐시 크기 입력란에서 숫자만 허용한다."""
        return proposed_value == "" or proposed_value.isdigit()

    def parse_max_cache_size(self, fallback=None):
        """현재 캐시 크기 입력값을 정수로 변환한다."""
        raw_value = self.max_cache_size.get().strip()

        if not raw_value:
            if fallback is not None:
                return fallback
            raise ValueError("라인 캐시 크기를 입력해주세요.")

        try:
            parsed_value = int(raw_value)
        except ValueError as error:
            if fallback is not None:
                return fallback
            raise ValueError("라인 캐시 크기는 숫자만 입력할 수 있습니다.") from error

        if parsed_value <= 0:
            if fallback is not None:
                return fallback
            raise ValueError("라인 캐시 크기는 1 이상의 정수여야 합니다.")

        return parsed_value
    
    def validate_inputs(self):
        """입력값 유효성 검사"""
        watch_folder = self.watch_folder.get().strip()
        docs_input_val = self.docs_input.get().strip()
        
        errors = []
        
        # 감시 폴더 검사
        if not watch_folder:
            errors.append("감시 폴더를 선택해주세요.")
        elif not os.path.exists(watch_folder):
            errors.append("감시 폴더가 존재하지 않습니다.")
        elif not os.path.isdir(watch_folder):
            errors.append("감시 폴더 경로가 폴더가 아닙니다.")
        
        # Credentials 파일은 path_utils에서 자동으로 관리됩니다
        
        # Google Docs URL/ID 검사
        if not docs_input_val:
            errors.append("Google Docs URL/ID를 입력하거나 '새 문서 만들기' 또는 '문서 목록'으로 문서를 지정해주세요.")
        else:
            docs_id = extract_google_id_from_url(docs_input_val)
            if not docs_id:
                errors.append("유효한 Google Docs URL 또는 ID를 입력해주세요.")
            elif not self.docs_target_locked.get():
                errors.append("대상 문서를 확정하려면 '문서 경로 확정' 버튼을 눌러주세요.")

        try:
            self.parse_max_cache_size()
        except ValueError as error:
            errors.append(str(error))
        
        return errors
    
    def open_folder_in_explorer(self, folder_path):
        """폴더를 윈도우 탐색기에서 열기"""
        self.log(f"open_folder_in_explorer 호출됨. 전달된 경로: {folder_path}")
        
        # 경로가 비어있는 경우 처리
        if not folder_path or folder_path.strip() == "":
            self.log("경고: 빈 경로가 전달됨")
            messagebox.showwarning("경고", "폴더 경로가 설정되지 않았습니다.", parent=self.root)
            return
            
        # 경로 정규화
        normalized_path = os.path.normpath(folder_path)
        self.log(f"정규화된 경로: {normalized_path}")
        
        try:
            if os.path.exists(normalized_path):
                if platform.system() == "Windows":
                    # Windows에서는 경로를 절대경로로 변환
                    abs_path = os.path.abspath(normalized_path)
                    self.log(f"절대경로로 변환: {abs_path}")
                    subprocess.run(["explorer", abs_path])
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", normalized_path])
                else:  # Linux
                    subprocess.run(["xdg-open", normalized_path])
                self.log(f"폴더 열기 성공: {normalized_path}")
            else:
                self.log(f"경고: 폴더가 존재하지 않음 - {normalized_path}")
                messagebox.showwarning("경고", f"폴더가 존재하지 않습니다:\n{normalized_path}", parent=self.root)
        except Exception as e:
            self.log(f"오류: 폴더 열기 실패 - {e}")
            messagebox.showerror("오류", f"폴더 열기 실패:\n{e}", parent=self.root)
            
    def open_docs_in_browser(self):
        """Google Docs 문서를 웹브라우저에서 열기"""
        docs_input_val = self.docs_input.get().strip()
        
        if not docs_input_val:
            self.log("경고: Google Docs URL/ID가 설정되지 않았습니다.")
            messagebox.showwarning("경고", "Google Docs URL 또는 ID를 먼저 입력해주세요.", parent=self.root)
            return
            
        # URL인지 ID인지 확인
        docs_id = extract_google_id_from_url(docs_input_val)
        
        if not docs_id:
            self.log("경고: 유효한 Google Docs URL/ID가 아닙니다.")
            messagebox.showwarning("경고", "유효한 Google Docs URL 또는 ID를 입력해주세요.", parent=self.root)
            return
            
        # Google Docs URL 형식으로 변환
        docs_url = f"https://docs.google.com/document/d/{docs_id}/edit"
        
        try:
            # 웹브라우저 열기
            webbrowser.open(docs_url)
            self.log(f"Google Docs 문서 열기 성공: {docs_url}")
        except Exception as e:
            self.log(f"오류: Google Docs 문서 열기 실패 - {e}")
            messagebox.showerror("오류", f"Google Docs 문서 열기 실패:\n{e}", parent=self.root)

    def focus_existing_docs_input(self):
        """기존 Google Docs URL/ID를 직접 입력할 수 있도록 입력칸에 포커스를 준다."""
        self.unlock_docs_target(focus_entry=True)
        self.log("기존 Google Docs 주소/ID 직접 입력 모드.")

    def get_google_services_for_ui(self):
        """GUI에서 문서 생성/선택에 사용할 Google 서비스 객체를 준비한다."""
        if not get_google_services:
            messagebox.showerror("모듈 오류", "Google 인증 모듈을 불러오지 못했습니다.", parent=self.root)
            return None

        self.log("Google Docs/Drive 서비스 연결 확인 중...")
        services = get_google_services(self.log)
        if not services:
            messagebox.showerror(
                "Google 연결 오류",
                "Google 인증 또는 서비스 초기화에 실패했습니다.\n로그를 확인한 뒤 다시 시도하세요.",
                parent=self.root
            )
            return None

        if 'docs' not in services or 'drive' not in services:
            messagebox.showerror(
                "Google 연결 오류",
                "문서 생성/선택에 필요한 Google Docs 또는 Drive 서비스가 준비되지 않았습니다.",
                parent=self.root
            )
            return None

        return services

    def verify_google_services_before_monitoring(self):
        """감시 시작 전에 Google Docs 기록 가능 여부를 확인한다."""
        if not get_google_services:
            self.log("오류: Google 인증 모듈을 불러오지 못해 감시를 시작할 수 없습니다.")
            self.update_status("⚠️ 기록 불가", "Google 인증 모듈 오류", tray_status_text="오류 상태")
            messagebox.showerror(
                "Google 연결 오류",
                "Google 인증 모듈을 불러오지 못해 감시를 시작하지 않습니다.",
                parent=self.root,
            )
            return None

        self.log("감시 시작 전 Google Docs 연결 확인 중...")
        self.update_status("Google 연결 확인 중...")
        services = get_google_services(self.log)

        if not services or 'docs' not in services:
            self.log("오류: Google Docs 연결 확인 실패. 감시를 시작하지 않습니다.")
            self.update_status("⚠️ 기록 불가", "Google 연결 실패", tray_status_text="오류 상태")
            messagebox.showerror(
                "Google 연결 오류",
                "Google Docs 연결 확인에 실패하여 감시를 시작하지 않습니다.\n로그를 확인한 뒤 다시 시도하세요.",
                parent=self.root,
            )
            return None

        self.log("감시 시작 전 Google Docs 연결 확인 완료.")
        return services

    def create_new_google_doc(self):
        """현재 권한 범위에서 새 Google Docs 문서를 만들고 자동으로 선택한다."""
        if not create_google_document:
            messagebox.showerror("모듈 오류", "문서 생성 기능을 불러오지 못했습니다.", parent=self.root)
            return

        title_dialog = ctk.CTkInputDialog(
            text="새 Google Docs 문서 제목을 입력하세요.\n비워두면 자동 제목을 사용합니다.",
            title="새 Google Docs 문서 만들기"
        )
        document_title = title_dialog.get_input()
        if document_title is None:
            return

        services = self.get_google_services_for_ui()
        if not services:
            return

        created_document = create_google_document(self.log, document_title, services=services)
        if not created_document:
            messagebox.showerror("문서 생성 실패", "새 Google Docs 문서를 만들지 못했습니다.\n로그를 확인하세요.", parent=self.root)
            return

        document_id = created_document.get("id", "")
        document_name = created_document.get("name", "새 Google Docs 문서")
        self.docs_input.set(document_id)
        self.lock_docs_target(source_label=f"새 문서 생성: {document_name}")
        self.log(f"새 문서를 현재 대상 문서로 설정했습니다: {document_name} ({document_id})")

        open_created_document = messagebox.askyesno(
            "문서 생성 완료",
            f"새 문서가 생성되었습니다.\n\n제목: {document_name}\n문서 ID: {document_id}\n\n지금 브라우저에서 열까요?",
            parent=self.root
        )
        if open_created_document and created_document.get("webViewLink"):
            webbrowser.open(created_document["webViewLink"])

    def select_google_doc(self):
        """현재 권한(drive.file)에서 접근 가능한 Google Docs 문서 목록을 표시한다."""
        if not list_accessible_google_documents:
            messagebox.showerror("모듈 오류", "문서 목록 기능을 불러오지 못했습니다.", parent=self.root)
            return

        services = self.get_google_services_for_ui()
        if not services:
            return

        documents = list_accessible_google_documents(self.log, services=services, page_size=20)
        if documents is None:
            messagebox.showerror("문서 목록 오류", "Google Docs 문서 목록을 불러오지 못했습니다.\n로그를 확인하세요.", parent=self.root)
            return

        if not documents:
            messagebox.showinfo(
                "표시할 문서 없음",
                "현재 권한(drive.file) 기준으로 이 앱이 접근 가능한 Google Docs 문서가 없습니다.\n"
                "먼저 '새 문서 만들기'로 문서를 생성하면 이 목록에 표시됩니다.",
                parent=self.root
            )
            return

        selector_window = ctk.CTkToplevel(self.root)
        selector_window.title("Google Docs 문서 목록")
        selector_window.geometry("760x520")
        selector_window.minsize(760, 520)
        selector_window.transient(self.root)
        selector_window.grab_set()

        main_frame = ctk.CTkFrame(selector_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            main_frame,
            text="Google Docs 문서 목록",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(
            main_frame,
            text=(
                "현재 권한(drive.file) 기준으로 이 앱이 만들었거나 이 앱이 이미 접근 가능한 문서만 표시됩니다.\n"
                "기존 Drive 전체 문서는 모두 보이지 않을 수 있습니다."
            ),
            justify="left",
            wraplength=700
        ).pack(anchor="w", fill="x", pady=(0, 12))

        list_frame = ctk.CTkScrollableFrame(main_frame)
        list_frame.pack(fill="both", expand=True)

        def choose_document(document_info):
            document_id = document_info.get("id", "")
            document_name = document_info.get("name", "이름 없는 문서")
            self.docs_input.set(document_id)
            self.lock_docs_target(source_label=f"문서 목록 선택: {document_name}")
            self.log(f"문서 목록에서 선택 완료: {document_name} ({document_id})")
            selector_window.destroy()

        for document_info in documents:
            row_frame = ctk.CTkFrame(list_frame)
            row_frame.pack(fill="x", padx=4, pady=4)

            info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)

            document_name = document_info.get("name", "이름 없는 문서")
            modified_time = format_google_modified_time(document_info.get("modifiedTime"))
            ctk.CTkLabel(
                info_frame,
                text=document_name,
                font=ctk.CTkFont(weight="bold"),
                anchor="w",
                justify="left"
            ).pack(anchor="w", fill="x")
            ctk.CTkLabel(
                info_frame,
                text=f"최근 수정: {modified_time}\n문서 ID: {document_info.get('id', '')}",
                justify="left",
                anchor="w"
            ).pack(anchor="w", fill="x", pady=(2, 0))

            ctk.CTkButton(
                row_frame,
                text="선택",
                width=70,
                command=lambda doc=document_info: choose_document(doc)
            ).pack(side="right", padx=(6, 10), pady=10)

            if document_info.get("webViewLink"):
                ctk.CTkButton(
                    row_frame,
                    text="열기",
                    width=70,
                    command=lambda url=document_info["webViewLink"]: webbrowser.open(url)
                ).pack(side="right", padx=6, pady=10)

        ctk.CTkButton(
            main_frame,
            text="닫기",
            width=100,
            command=selector_window.destroy
        ).pack(anchor="e", pady=(12, 0))

        if center_window:
            center_window(selector_window)
        else:
            selector_window.update_idletasks()
            width = selector_window.winfo_width()
            height = selector_window.winfo_height()
            x = (selector_window.winfo_screenwidth() // 2) - (width // 2)
            y = (selector_window.winfo_screenheight() // 2) - (height // 2)
            selector_window.geometry(f"{width}x{height}+{x}+{y}")
    
    def update_tray_status(self, tray_status_text, detail_text=None, state_key=None):
        """트레이 툴팁에 현재 상태를 반영한다."""
        if not self.tray_icon:
            return

        resolved_state_key = state_key or self.get_tray_state_key(tray_status_text)
        icon_image = self.build_tray_status_icon(resolved_state_key)
        if icon_image is not None:
            self.icon_image = icon_image
            try:
                self.tray_icon.icon = icon_image
            except Exception:
                pass

        title_parts = ["메신저 Docs 자동 기록"]
        if tray_status_text:
            title_parts.append(str(tray_status_text).strip())
        if detail_text:
            compact_detail = str(detail_text).replace("\n", " ").strip()
            if len(compact_detail) > 40:
                compact_detail = compact_detail[:37] + "..."
            title_parts.append(compact_detail)

        try:
            self.tray_icon.title = " · ".join(part for part in title_parts if part)
        except Exception:
            pass

    def update_status(self, status_text, detail_text=None, tray_status_text=None):
        """상태 표시 업데이트 (상세 내용 추가 가능)"""
        if detail_text:
            full_status = f"{status_text} ({detail_text})"
        else:
            full_status = status_text
        self.status_var.set(full_status)
        self.update_tray_status(tray_status_text or status_text, detail_text)
        self.root.update_idletasks()

    def configure_log_tags(self, target_widget):
        """로그 텍스트 위젯에 상태별 색상 태그를 적용한다."""
        target_widget.tag_config("log_info", foreground="#D1D5DB")
        target_widget.tag_config("log_success", foreground="#34D399")
        target_widget.tag_config("log_warning", foreground="#FBBF24")
        target_widget.tag_config("log_error", foreground="#F87171")

    def get_log_tag_name(self, message):
        """로그 메시지 내용에 따라 강조 색상 태그를 선택한다."""
        normalized_message = str(message)
        if "오류" in normalized_message or "실패" in normalized_message or "기록 불가" in normalized_message:
            return "log_error"
        if "경고" in normalized_message or "보류" in normalized_message:
            return "log_warning"
        if "완료" in normalized_message or "성공" in normalized_message or "시작됨" in normalized_message:
            return "log_success"
        return "log_info"

    def append_log_to_widget(self, target_widget, message):
        """로그 메시지를 색상 태그와 함께 텍스트 위젯에 추가한다."""
        target_widget.insert(ctk.END, message + '\n', self.get_log_tag_name(message))

    def render_log_lines(self, target_widget, lines):
        """로그 위젯 내용을 주어진 라인 목록으로 다시 그린다."""
        target_widget.configure(state='normal')
        target_widget.delete("1.0", ctk.END)
        for line in lines:
            if line:
                self.append_log_to_widget(target_widget, line)
        target_widget.configure(state='disabled')
        target_widget.see(ctk.END)

    def create_widgets(self):
        if not build_main_window_ui:
            messagebox.showerror("UI 오류", "메인 창 UI 모듈을 불러오지 못했습니다.", parent=self.root)
            return

        widget_refs = build_main_window_ui(
            self.root,
            state_vars={
                "status_var": self.status_var,
                "memory_usage": self.memory_usage,
                "watch_folder": self.watch_folder,
                "watch_folder_drop_hint": self.watch_folder_drop_hint,
                "launch_on_windows_startup": self.launch_on_windows_startup,
                "autostart_hint": self.autostart_hint,
                "file_extensions": self.file_extensions,
                "max_cache_size": self.max_cache_size,
                "show_success_notifications": self.show_success_notifications,
                "docs_input": self.docs_input,
                "docs_target_status_var": self.docs_target_status_var,
                "show_success_notifications": self.show_success_notifications,
            },
            callbacks={
                "optimize_memory": self.optimize_memory,
                "browse_folder": self.browse_folder,
                "open_watch_folder": lambda: self.open_folder_in_explorer(self.watch_folder.get()),
                "show_filter_settings": self.show_filter_settings,
                "create_new_google_doc": self.create_new_google_doc,
                "focus_existing_docs_input": self.focus_existing_docs_input,
                "select_google_doc": self.select_google_doc,
                "toggle_docs_target_lock": self.toggle_docs_target_lock,
                "start_monitoring": self.start_monitoring,
                "stop_monitoring": self.stop_monitoring,
                "open_docs_in_browser": self.open_docs_in_browser,
                "show_theme_settings": self.show_theme_settings,
                "show_backup_restore_dialog": self.show_backup_restore_dialog,
                "save_config": self.save_config,
                "clear_extraction_preview": self.clear_extraction_preview,
                "open_log_folder": lambda: self.open_folder_in_explorer(LOG_DIR_STR),
                "show_log_popup": self.show_log_popup,
                "show_log_search_dialog": self.show_log_search_dialog,
                "clear_log": self.clear_log,
                "validate_positive_integer_input": self.validate_positive_integer_input,
            },
            ctk_module=ctk,
            font_family=self.ui_font_family,
        )

        for widget_name, widget_value in widget_refs.items():
            setattr(self, widget_name, widget_value)

        if hasattr(self, "log_text"):
            self.configure_log_tags(self.log_text)
        self.refresh_docs_target_ui()
        self.update_windows_startup_ui_state()
        self.setup_watch_folder_drag_and_drop()

    def update_windows_startup_ui_state(self):
        """현재 플랫폼에 맞게 Windows 자동 실행 UI를 조정한다."""
        autostart_supported = bool(
            supports_windows_startup
            and supports_windows_startup()
            and is_windows_startup_enabled
            and set_windows_startup_enabled
        )

        if autostart_supported:
            self.autostart_hint.set("Windows 로그인 시 이 앱을 자동으로 실행합니다. 설정 저장 시 시작프로그램 폴더를 갱신합니다.")
            if hasattr(self, "autostart_checkbox"):
                self.autostart_checkbox.configure(state="normal")
            return

        self.autostart_hint.set("현재 OS에서는 Windows 자동 실행을 지원하지 않습니다.")
        if hasattr(self, "autostart_checkbox"):
            self.autostart_checkbox.configure(state="disabled")

    def refresh_windows_startup_setting_from_system(self):
        """Windows 실제 자동 실행 상태를 UI 설정값에 반영한다."""
        autostart_supported = bool(
            supports_windows_startup
            and supports_windows_startup()
            and is_windows_startup_enabled
        )
        if not autostart_supported:
            return

        try:
            self.launch_on_windows_startup.set(is_windows_startup_enabled())
        except Exception as error:
            self.log(f"경고: Windows 자동 실행 상태 확인 실패 - {error}")

    def sync_windows_startup_setting(self):
        """저장된 UI 설정을 Windows 시작프로그램 폴더와 동기화한다."""
        autostart_supported = bool(
            supports_windows_startup
            and supports_windows_startup()
            and is_windows_startup_enabled
            and set_windows_startup_enabled
        )
        if not autostart_supported:
            return

        desired_state = self.launch_on_windows_startup.get()
        if desired_state:
            set_windows_startup_enabled(True)
            self.log("Windows 자동 실행 등록 완료.")
            return

        if is_windows_startup_enabled():
            set_windows_startup_enabled(False)
            self.log("Windows 자동 실행 해제 완료.")

    def setup_watch_folder_drag_and_drop(self):
        """감시 폴더 입력란에 드래그 앤 드롭을 연결한다."""
        if not hasattr(self, "watch_folder_drop_hint"):
            return

        if not DND_FILES or not hasattr(self, "watch_folder_entry"):
            self.watch_folder_drop_hint.set("드래그 앤 드롭을 사용하려면 tkinterdnd2 설치가 필요합니다. 없으면 '폴더 선택' 버튼을 사용하세요.")
            return

        try:
            self.watch_folder_entry.drop_target_register(DND_FILES)
            self.watch_folder_entry.dnd_bind("<<Drop>>", self.on_watch_folder_drop)
            self.watch_folder_drop_hint.set("폴더를 여기로 끌어다 놓거나 '폴더 선택' 버튼을 사용하세요.")
            self.log("감시 폴더 드래그 앤 드롭이 준비되었습니다.")
        except Exception as error:
            self.watch_folder_drop_hint.set("드래그 앤 드롭 초기화에 실패했습니다. '폴더 선택' 버튼을 사용하세요.")
            self.log(f"경고: 감시 폴더 드래그 앤 드롭 초기화 실패 - {error}")

    def on_watch_folder_drop(self, event):
        """드롭된 폴더 경로를 감시 폴더 입력값에 반영한다."""
        if not event or not getattr(event, "data", ""):
            return

        try:
            dropped_items = self.root.tk.splitlist(event.data)
        except tk.TclError:
            dropped_items = [str(event.data)]

        if not dropped_items:
            return

        dropped_path = str(dropped_items[0]).strip()
        if not dropped_path:
            return

        if os.path.isdir(dropped_path):
            self.watch_folder.set(dropped_path)
            self.log(f"감시 폴더 드래그 앤 드롭 설정됨: {dropped_path}")
            return

        self.log(f"경고: 드래그 앤 드롭된 경로가 폴더가 아닙니다 - {dropped_path}")
        messagebox.showwarning("폴더 선택 오류", "감시 폴더로 사용할 디렉터리를 끌어다 놓아주세요.", parent=self.root)

    # --- 트레이 아이콘 설정 및 제어 함수 (이전과 동일) ---
    def build_tray_menu(self):
        """트레이 우클릭 메뉴를 구성한다."""
        return (
            pystray.MenuItem('보이기/숨기기', self.toggle_window),
            pystray.MenuItem('감시 일시 정지/재개', self.toggle_monitoring_from_tray),
            pystray.MenuItem('Docs 웹에서 열기', self.open_docs_in_browser_from_tray),
            pystray.MenuItem('로그 보기', self.show_log_popup_from_tray),
            pystray.MenuItem('종료', self.exit_application),
        )

    def setup_tray_icon(self):
        menu = self.build_tray_menu()
        self.tray_icon = pystray.Icon("MessengerDocsApp", self.icon_image, "메신저 Docs 자동 기록", menu)
        self.update_tray_status("준비")

    def run_tray_icon(self):
        if self.tray_icon: self.tray_icon.run()

    def start_tray_icon(self):
        """플랫폼에 맞는 방식으로 트레이 아이콘 이벤트 루프를 시작한다."""
        if not self.tray_icon:
            return

        if platform.system() == "Darwin":
            try:
                self.tray_icon.run_detached()
                self.log("macOS 트레이 아이콘 분리 모드 시작됨.")
            except Exception as e:
                self.log(f"macOS 트레이 아이콘 시작 실패: {e}")
                self.tray_icon = None
            return

        self.start_tray_thread()

    def start_tray_thread(self):
        if self.tray_icon and not self.tray_thread:
            self.tray_thread = threading.Thread(target=self.run_tray_icon, daemon=True)
            self.tray_thread.start()
            self.log("트레이 아이콘 스레드 시작됨.")
            
    def show_tray_notification(self, title, message):
        """트레이 아이콘에 알림 표시"""
        if self.tray_icon and hasattr(self.tray_icon, 'notify'):
            try:
                # 트레이 아이콘이 실행 중이고 notify 메서드가 있는 경우
                self.tray_icon.notify(message, title)
                self.log(f"트레이 알림 표시: {title}")
            except Exception as e:
                self.log(f"트레이 알림 표시 실패: {e}")
        else:
            self.log("트레이 아이콘이 초기화되지 않아 알림을 표시할 수 없습니다.")

    def toggle_monitoring_from_tray(self, *args):
        """트레이 메뉴에서 감시를 일시 정지하거나 재개한다."""
        if not hasattr(self, "root") or not self.root.winfo_exists():
            return
        if self.is_monitoring:
            self.root.after(0, self.stop_monitoring)
        else:
            self.root.after(0, self.start_monitoring)

    def open_docs_in_browser_from_tray(self, *args):
        """트레이 메뉴에서 현재 Docs 문서를 연다."""
        if hasattr(self, "root") and self.root.winfo_exists():
            self.root.after(0, self.open_docs_in_browser)

    def show_log_popup_from_tray(self, *args):
        """트레이 메뉴에서 로그 팝업을 연다."""
        if not hasattr(self, "root") or not self.root.winfo_exists():
            return
        self.root.after(0, self.show_window)
        self.root.after(0, self.show_log_popup)

    def hide_window(self): # X 버튼 클릭 시 호출됨
        """ 메인 창 숨기기 """
        if not self.tray_icon:
            self.log("트레이 아이콘이 없어 창 숨김 대신 종료를 진행합니다.")
            self.exit_application()
            return
        self.root.withdraw()
        self.log("창 숨김. 트레이 아이콘 우클릭으로 메뉴 사용.")

    def show_window(self):
        """ 숨겨진 메인 창 보이기 """
        self.root.deiconify(); self.root.lift(); self.root.focus_force()
        self.log("창 보임.")

    def toggle_window(self, *args): # 트레이 메뉴에서 호출됨
        """ 창 보이기/숨기기 토글 """
        if self.root.winfo_exists(): # 창 존재 확인
            if self.root.state() == 'withdrawn': self.root.after(0, self.show_window)
            else: self.root.after(0, self.hide_window)

    def exit_application(self, *args): # 트레이 메뉴 '종료'에서 호출됨
        """ 애플리케이션 완전 종료 """
        self.log("애플리케이션 종료 시작...")
        
        # 1. 트레이 아이콘 먼저 중지 (GUI 이벤트 루프에 덜 의존적일 수 있음)
        if self.tray_icon:
            self.log("트레이 아이콘 중지 시도...")
            try:
                self.tray_icon.stop()
            except Exception as e:
                self.log(f"트레이 아이콘 중지 중 오류: {e}") # 오류 발생해도 계속 진행

        # 2. 감시 스레드 중지 요청 및 대기
        if self.is_monitoring:
            self.log("감시 스레드 중지 시도...")
            self.stop_event.set()
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                try:
                    self.monitoring_thread.join(timeout=5) # 5초 대기
                    if self.monitoring_thread.is_alive():
                        self.log("경고: 감시 스레드가 시간 내에 종료되지 않음.")
                except Exception as e:
                    self.log(f"감시 스레드 join 중 오류: {e}")
            self.log("감시 스레드 중지 시도 완료.")
        self.is_monitoring = False # 확실히 상태 업데이트

        # 3. 설정 자동 저장 (변경사항이 있는 경우)
        if hasattr(self, 'settings_changed') and self.settings_changed:
            try:
                self.save_config()
                self.log("종료 시 설정 자동 저장 완료.")
            except Exception as e:
                self.log(f"종료 시 설정 저장 실패: {e}")
        
        # 4. 메인 창 종료 (모든 백그라운드 작업 정리 후)
        self.log("메인 창 종료 시도...")
        # root.after를 사용하여 메인 루프에서 안전하게 destroy 호출 시도
        if hasattr(self, 'root') and self.root:
             try:
                 # destroy 를 즉시 호출하지 않고 after 로 예약하면
                 # 현재 진행중인 다른 Tkinter 콜백이 완료될 시간을 벌 수 있음
                 self.root.after(50, self.root.destroy)
                 self.log("메인 창 종료 예약됨.")
             except Exception as e:
                 self.log(f"메인 창 종료 예약 중 오류: {e}")
                 try:
                     self.root.destroy() # 예약 실패 시 즉시 시도
                 except Exception as final_e:
                     self.log(f"메인 창 즉시 종료 중 오류: {final_e}")
        else:
            self.log("메인 창 참조 없음. 종료.")

    # --- 기존 메소드들 (log, log_threadsafe, process_log_queue 등은 동일하게 유지) ---
    def browse_folder(self):
        foldername = filedialog.askdirectory(title="감시할 폴더 선택")
        if foldername: self.watch_folder.set(foldername); self.log(f"감시 폴더: {foldername}")
    # browse_credentials 함수는 더 이상 필요하지 않습니다 (path_utils에서 자동 관리)

    def close_log_popup(self):
        """별도 로그 팝업 창을 닫고 참조를 정리한다."""
        popup_window = self.log_popup_window
        self.log_popup_text = None
        self.log_popup_window = None

        if popup_window and popup_window.winfo_exists():
            popup_window.destroy()

    def sync_log_popup_content(self):
        """메인 로그 내용을 로그 팝업 창과 동기화한다."""
        if not (
            self.log_popup_window
            and self.log_popup_window.winfo_exists()
            and self.log_popup_text
            and self.root.winfo_exists()
            and hasattr(self, "log_text")
        ):
            return

        try:
            log_content = self.log_text.get("1.0", ctk.END)
            self.render_log_lines(self.log_popup_text, log_content.splitlines())
        except Exception:
            pass

    def show_log_popup(self):
        """작업 로그를 별도 창으로 분리해 표시한다."""
        if self.log_popup_window and self.log_popup_window.winfo_exists():
            self.log_popup_window.deiconify()
            self.log_popup_window.lift()
            self.log_popup_window.focus_force()
            self.sync_log_popup_content()
            return

        popup_window = ctk.CTkToplevel(self.root)
        popup_window.title("작업 로그 팝업")
        popup_window.geometry("860x560")
        popup_window.minsize(720, 420)
        popup_window.transient(self.root)
        popup_window.protocol("WM_DELETE_WINDOW", self.close_log_popup)

        main_frame = ctk.CTkFrame(popup_window)
        main_frame.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            main_frame,
            text="작업 로그",
            font=self.build_ui_font(17, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            main_frame,
            text="기본 창이 좁을 때도 로그를 넓게 확인할 수 있는 별도 창입니다.",
            font=self.build_ui_font(12),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", pady=(4, 10))

        button_row = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_row.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            button_row,
            text="로그 지우기",
            width=98,
            height=34,
            corner_radius=10,
            command=self.clear_log,
            font=self.build_ui_font(12, "bold"),
            fg_color=("gray85", "gray28"),
            hover_color=("gray78", "gray34"),
            text_color=("gray20", "gray92"),
        ).pack(side="right")

        ctk.CTkButton(
            button_row,
            text="닫기",
            width=82,
            height=34,
            corner_radius=10,
            command=self.close_log_popup,
            font=self.build_ui_font(12, "bold"),
        ).pack(side="right", padx=(0, 8))

        self.log_popup_text = ctk.CTkTextbox(
            main_frame,
            state="disabled",
            wrap="word",
            font=self.build_ui_font(12),
            corner_radius=12,
        )
        self.log_popup_text.pack(fill="both", expand=True)
        self.configure_log_tags(self.log_popup_text)

        self.log_popup_window = popup_window
        self.sync_log_popup_content()

        if center_window:
            center_window(popup_window)

    def log(self, message):
        try:
            # GUI 로그 출력
            if self.root.winfo_exists():
                self.log_text.configure(state='normal')
                
                # 로그 텍스트 크기 제한 (메모리 최적화)
                self.optimize_log_memory()
                
                # 새 로그 추가
                self.append_log_to_widget(self.log_text, message)
                self.log_text.configure(state='disabled')
                self.log_text.see(ctk.END)

                if self.log_popup_window and self.log_popup_window.winfo_exists() and self.log_popup_text:
                    self.log_popup_text.configure(state='normal')
                    self.optimize_log_memory(self.log_popup_text)
                    self.append_log_to_widget(self.log_popup_text, message)
                    self.log_popup_text.configure(state='disabled')
                    self.log_popup_text.see(ctk.END)
            
            # 파일 로그 출력
            if hasattr(self, 'logger'):
                self.logger.info(message)
        except Exception: pass
        
    def optimize_log_memory(self, target_widget=None):
        """로그 텍스트 크기가 너무 커지면 오래된 로그 삭제 (메모리 최적화)"""
        try:
            if target_widget is None:
                target_widget = self.log_text

            max_lines = 1000
            current_line_count = int(target_widget.index("end-1c").split('.')[0])
            if current_line_count > max_lines:
                lines_to_remove = current_line_count - max_lines
                target_widget.delete("1.0", f"{lines_to_remove + 1}.0")
        except Exception as e:
            # 오류 발생 시 조용히 무시 (로깅 시스템 자체에서 오류가 발생하므로 로그 출력 안 함)
            print(f"로그 메모리 최적화 오류: {e}")
    def log_threadsafe(self, message): self.log_queue.put(message)
    def extracted_result_threadsafe(self, result_payload): self.result_queue.put(result_payload)

    def clear_extraction_preview(self):
        """최근 추출 결과 미리보기를 초기화합니다."""
        if hasattr(self, "result_preview_text") and self.root.winfo_exists():
            try:
                self.result_preview_text.configure(state='normal')
                self.result_preview_text.delete("1.0", ctk.END)
                self.result_preview_text.configure(state='disabled')
            except Exception:
                pass

    def append_extraction_preview(self, result_payload):
        """최근 추출 결과를 GUI 미리보기 패널에 표시합니다."""
        if not hasattr(self, "result_preview_text") or not self.root.winfo_exists():
            return

        file_title = result_payload.get("file_title", "이름 없는 파일")
        extracted_time = result_payload.get("extracted_time", "시간 정보 없음")
        line_count = int(result_payload.get("line_count", 0))
        preview_text = result_payload.get("preview_text", "").strip()
        preview_line_count = len([line for line in preview_text.splitlines() if line.strip()])
        remaining_lines = max(0, line_count - preview_line_count)

        preview_block = (
            f"[본래 파일 제목] {file_title}\n"
            f"[추출된 시간] {extracted_time}\n"
            f"[추출 줄 수] {line_count}줄\n"
        )
        if preview_text:
            preview_block += f"{preview_text}\n"
        if remaining_lines > 0:
            preview_block += f"... 외 {remaining_lines}줄\n"
        preview_block += f"{'-' * 44}\n"

        try:
            self.result_preview_text.configure(state='normal')
            existing_text = self.result_preview_text.get("1.0", ctk.END).strip()
            new_text = preview_block if not existing_text else preview_block + existing_text + "\n"
            self.result_preview_text.delete("1.0", ctk.END)
            self.result_preview_text.insert("1.0", new_text)

            lines = self.result_preview_text.get("1.0", ctk.END).splitlines()
            if len(lines) > 28:
                self.result_preview_text.delete("1.0", ctk.END)
                self.result_preview_text.insert("1.0", "\n".join(lines[:28]) + "\n")

            self.result_preview_text.configure(state='disabled')
            self.result_preview_text.see("1.0")
        except Exception:
            pass

    def process_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log(msg)
                
                # 상태 메시지에 따른 상태 표시 업데이트
                current_time_str = datetime.now().strftime('%H:%M:%S')
                if "백엔드: 감시 시작" in msg:
                    self.update_status("감시 중", f"시작 시간: {current_time_str}")
                elif "백엔드: 중지 신호 수신" in msg or "백엔드: 모든 작업 완료" in msg:
                    self.update_status("중지됨", f"중지 시간: {current_time_str}")
                elif "처리 시작:" in msg:
                    filename = msg.split("처리 시작:")[-1].strip()
                    self.current_processing_filename = filename
                    self.update_status("처리 중", filename)
                elif "처리 완료:" in msg: # 파일 처리 완료 후 다시 감시 중 상태로
                    self.update_status("감시 중", f"마지막 확인: {current_time_str}")
                    self.current_processing_filename = None
                elif "Google Docs에" in msg and "줄 추가 시도" in msg:
                    self.pending_docs_update_line_count = extract_docs_update_line_count(msg)
                elif "Google Docs 업데이트 완료" in msg:
                    self.update_status("Docs 업데이트 완료", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    # 잠시 후 다시 감시 중 상태로 변경 (is_monitoring 확인 추가)
                    if self.is_monitoring:
                        self.root.after(2000, lambda: self.update_status("감시 중", f"마지막 업데이트 후 대기: {datetime.now().strftime('%H:%M:%S')}"))
                    
                    # 실제 성공 시점에만 트레이 알림 표시
                    lines_count = extract_docs_update_line_count(msg) or self.pending_docs_update_line_count
                    self.pending_docs_update_line_count = None
                    if self.show_success_notifications.get():
                        try:
                            notification_title = "메신저 Docs 자동 기록"
                            file_label = extract_filename_from_log_message(msg) or self.current_processing_filename
                            if lines_count:
                                notification_message = f"{file_label}: {lines_count}줄의 새 내용이 Google Docs에 추가되었습니다." if file_label else f"{lines_count}줄의 새 내용이 Google Docs에 추가되었습니다."
                            else:
                                notification_message = f"{file_label}: 새 내용이 Google Docs에 추가되었습니다." if file_label else "새 내용이 Google Docs에 추가되었습니다."
                            self.show_tray_notification(notification_title, notification_message)
                        except Exception as e:
                            self.log(f"알림 처리 중 오류: {e}")
                elif "Google Docs 중복 파일명 기록 완료" in msg:
                    duplicate_filename = extract_filename_from_log_message(msg) or self.current_processing_filename
                    self.update_status("중복 파일명 기록", duplicate_filename or "파일명 기록 완료")
                    if self.show_success_notifications.get():
                        try:
                            notification_title = "메신저 Docs 자동 기록"
                            if duplicate_filename:
                                notification_message = f"{duplicate_filename}: 본문은 중복이라 생략하고 파일명만 기록했습니다."
                            else:
                                notification_message = "본문은 중복이라 생략하고 파일명만 기록했습니다."
                            self.show_tray_notification(notification_title, notification_message)
                        except Exception as e:
                            self.log(f"알림 처리 중 오류: {e}")
                elif "중복 내용만 감지되어 Google Docs 기록 생략" in msg:
                    duplicate_filename = extract_filename_from_log_message(msg) or self.current_processing_filename
                    self.update_status("중복으로 기록 안 함", duplicate_filename or "중복 내용")
                    if self.show_success_notifications.get():
                        try:
                            notification_title = "메신저 Docs 자동 기록"
                            if duplicate_filename:
                                notification_message = f"{duplicate_filename}: 모든 내용이 중복되어 추가 기록이 없습니다."
                            else:
                                notification_message = "모든 내용이 중복되어 추가 기록이 없습니다."
                            self.show_tray_notification(notification_title, notification_message)
                        except Exception as e:
                            self.log(f"알림 처리 중 오류: {e}")
                
                # 오류 메시지 처리 강화
                error_detail = None
                if (
                    "오류: Google API 인증 실패" in msg
                    or "오류: Google 서비스 초기화 예외" in msg
                    or "오류: Google 서비스 초기화 중 예외 발생" in msg
                    or "오류: Google 서비스 로드 실패" in msg
                    or "오류: Google 계정 인증 중 오류 발생" in msg
                    or "인증 정보(토큰) 갱신 실패" in msg
                ):
                    error_detail = "Google 인증 오류"
                elif "오류: Docs 업데이트 API 오류" in msg or "오류: Docs 업데이트 중 예외 발생" in msg:
                    self.pending_docs_update_line_count = None
                    error_detail = "Docs API 오류"
                elif "오류: 파일 처리 중 사라짐" in msg:
                    error_detail = "파일 접근 오류"
                elif "감시 실패" in msg: # 일반적인 감시 실패
                    error_detail = "감시 시스템 오류"
                elif "오류:" in msg and "Google" in msg: # 기타 구글 관련 오류
                    error_detail = "Google 연동 중 일반 오류"

                if error_detail:
                    if error_detail in {"Google 인증 오류", "Docs API 오류", "Google 연동 중 일반 오류"}:
                        self.update_status("⚠️ 기록 불가", error_detail, tray_status_text="오류 상태")
                    else:
                        self.update_status("오류 발생", error_detail, tray_status_text="오류 상태")
                    # 팝업은 한 번만 띄우거나, 특정 심각한 오류에만 띄우도록 조정 가능
                    try:
                        if "messagebox" not in msg.lower(): # 로그 자체에 messagebox 호출이 없는 경우만
                            self.show_enhanced_error_dialog(error_detail, msg)
                    except Exception:
                        pass # messagebox 호출 중 오류 발생 시 무시
        except queue.Empty:
            pass
        except Exception:
            pass
        finally:
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.after(100, self.process_log_queue)

    def process_result_queue(self):
        """백엔드에서 전달된 추출 결과 미리보기를 처리합니다."""
        try:
            while True:
                result_payload = self.result_queue.get_nowait()
                self.append_extraction_preview(result_payload)
        except queue.Empty:
            pass
        except Exception:
            pass
        finally:
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.after(100, self.process_result_queue)
    def save_config(self):
        if not save_app_config:
            messagebox.showerror("저장 오류", "설정 저장 모듈을 불러오지 못했습니다.", parent=self.root)
            return

        config_data = self.get_current_config_data()
        try:
            save_app_config(config_data, config_path=CONFIG_FILE_STR)
            self.max_cache_size.set(str(config_data["max_cache_size"]))
            try:
                self.sync_windows_startup_setting()
            except Exception as autostart_error:
                self.log(f"경고: Windows 자동 실행 설정 적용 실패 - {autostart_error}")
                messagebox.showwarning(
                    "Windows 자동 실행",
                    f"설정 파일은 저장되었지만 Windows 자동 실행 적용에는 실패했습니다.\n{autostart_error}",
                    parent=self.root,
                )
            self.log("설정 저장 완료.")
            self.settings_changed = False  # 설정 저장 후 변경 플래그 초기화
        except Exception as e: messagebox.showerror("저장 오류", f"설정 저장 실패:\n{e}", parent=self.root); self.log(f"오류: 설정 저장 실패 - {e}")

    def get_current_config_data(self):
        """현재 UI 상태를 설정 딕셔너리로 변환한다."""
        return {
            "first_run": self.first_run.get(),
            "launch_on_windows_startup": self.launch_on_windows_startup.get(),
            "watch_folder": self.watch_folder.get(), 
            "docs_input": self.docs_input.get(),
            "show_help_on_startup": self.show_help_on_startup.get(),
            "show_success_notifications": self.show_success_notifications.get(),
            # 파일 필터링 설정 추가
            "file_extensions": self.file_extensions.get(),
            "use_regex_filter": self.use_regex_filter.get(),
            "regex_pattern": self.regex_pattern.get(),
            # 테마 설정 추가
            "appearance_mode": self.appearance_mode.get(),
            "max_cache_size": self.parse_max_cache_size(fallback=10000),
        }

    def apply_config_data(self, config_data):
        """설정 딕셔너리를 UI 상태에 반영한다."""
        normalized_config = normalize_config_data(config_data) if normalize_config_data else config_data
        self.first_run.set(normalized_config.get("first_run", True))
        self.launch_on_windows_startup.set(normalized_config.get("launch_on_windows_startup", False))
        self.watch_folder.set(normalized_config.get("watch_folder", ""))
        self.docs_input.set(normalized_config.get("docs_input", ""))
        self.docs_target_locked.set(bool(normalized_config.get("docs_input", "").strip()))
        self.show_help_on_startup.set(normalized_config.get("show_help_on_startup", True))
        self.show_success_notifications.set(normalized_config.get("show_success_notifications", True))
        self.file_extensions.set(normalized_config.get("file_extensions", ".txt"))
        self.use_regex_filter.set(normalized_config.get("use_regex_filter", False))
        self.regex_pattern.set(normalized_config.get("regex_pattern", ""))
        self.max_cache_size.set(str(normalized_config.get("max_cache_size", 10000)))

        appearance_mode = normalized_config.get("appearance_mode", "System")
        self.appearance_mode.set(appearance_mode)
        ctk.set_appearance_mode(appearance_mode)
        self.refresh_docs_target_ui()
        return normalized_config

    def load_config(self):
        if not load_app_config:
            messagebox.showwarning("로드 오류", "설정 로드 모듈을 불러오지 못했습니다.", parent=self.root)
            return

        try:
            config_data, config_path, loaded_from_legacy, config_found = load_app_config(
                config_path=CONFIG_FILE_STR,
                legacy_config_path=LEGACY_CONFIG_FILE_STR,
            )
            if loaded_from_legacy:
                self.log(f"레거시 설정 파일을 불러옵니다: {config_path}")

            if not config_found:
                self.refresh_windows_startup_setting_from_system()
                self.log("저장된 설정 파일 없음.")
                return

            applied_config = self.apply_config_data(config_data)
            self.refresh_windows_startup_setting_from_system()
            self.log(f"테마 설정 로드: {applied_config.get('appearance_mode', 'System')} 모드")
            self.log("저장된 설정 로드 완료.")

            # 설정 로드 후 상태 표시 업데이트
            self.on_setting_changed()
        except Exception as e: messagebox.showwarning("로드 오류", f"설정 파일 로드 실패:\n{e}", parent=self.root); self.log(f"경고: 설정 파일 로드 실패 - {e}")
    def start_monitoring(self):
        if not run_monitoring: 
            messagebox.showerror("실행 오류", "백엔드 모듈 로드 불가.", parent=self.root)
            return
        
        # 입력값 유효성 검사
        self.update_status("입력값 검증 중...")
        validation_errors = self.validate_inputs()
        if validation_errors:
            error_intro = "입력값에 다음 문제들이 있습니다. 확인 후 다시 시도해주세요:\n"
            error_details = "\n".join([f"  - {error}" for error in validation_errors])
            full_error_message = f"{error_intro}\n{error_details}"
            messagebox.showerror("입력 오류", full_error_message, parent=self.root)
            self.update_status("준비", "입력값 오류")
            return
        
        # 설정 변경 사항이 있는 경우 저장 여부 확인
        if self.settings_changed:
            save_confirm = messagebox.askyesno(
                "설정 저장 확인", 
                "설정이 변경되었지만 저장되지 않았습니다.\n저장하시겠습니까?",
                parent=self.root
            )
            if save_confirm:
                self.save_config()
                self.log("감시 시작 전 설정 자동 저장됨.")

        google_services = self.verify_google_services_before_monitoring()
        if not google_services:
            return
        
        watch_folder = self.watch_folder.get().strip()
        docs_input_val = self.docs_input.get().strip()
        docs_id = extract_google_id_from_url(docs_input_val)
        max_cache_size = self.parse_max_cache_size()
        
        self.log(f"처리할 Docs ID: {docs_id}")
        self.log("감시 시작 요청...")
        self.update_status("감시 시작 중...")
        
        self.is_monitoring = True
        self.stop_event.clear()
        
        current_config = { 
            "watch_folder": watch_folder, 
            "docs_id": docs_id,
            # 파일 필터링 설정 추가
            "file_extensions": self.file_extensions.get(),
            "use_regex_filter": self.use_regex_filter.get(),
            "regex_pattern": self.regex_pattern.get() if self.use_regex_filter.get() else "",
            "max_cache_size": max_cache_size,
        }
        
        self.monitoring_thread = threading.Thread(
            target=run_monitoring, 
            args=(current_config, self.log_threadsafe, self.stop_event),
            kwargs={
                "extracted_result_callback": self.extracted_result_threadsafe,
                "preloaded_services": google_services,
            },
            daemon=True
        )
        self.monitoring_thread.start()
        
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.disable_settings_widgets()
        self.update_status("감시 중")
        self.log("백그라운드 감시 시작됨.")
    def stop_monitoring(self):
        if self.is_monitoring and self.monitoring_thread and self.monitoring_thread.is_alive():
            self.log("감시 중지 요청...")
            self.update_status("감시 중지 중...")
            self.stop_event.set()
            self.stop_button.configure(state="disabled")
            # 스레드가 종료될 때까지 기다린 후 상태 복구
            def wait_and_finalize():
                self.monitoring_thread.join(timeout=5)
                self.root.after(0, self.on_monitoring_stopped)
            threading.Thread(target=wait_and_finalize, daemon=True).start()
        else:
            self.log("현재 감시 중 아님.")
            self.on_monitoring_stopped()
    def on_monitoring_stopped(self):
         self.is_monitoring = False
         self.monitoring_thread = None
         if hasattr(self, 'root') and self.root.winfo_exists():
             try: 
                 self.start_button.configure(state="normal")
                 self.stop_button.configure(state="disabled")
                 self.enable_settings_widgets()
                 self.update_status("준비")
                 self.log("감시 중지됨.")
             except Exception: pass # 위젯 파괴 후 예외 무시
    def disable_settings_widgets(self):
        # ⚠️ 수정: winfo_children()[0] 인덱스 접근 → self.settings_frame 직접 참조로 안전하게 변경
        try:
            if not hasattr(self, 'settings_frame') or not self.settings_frame.winfo_exists():
                return
            for child in self.settings_frame.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for widget in child.winfo_children():
                        # 웹에서 문서를 바로 열어보는 버튼은 감시 중에도 유지
                        if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "Docs 웹에서 열기":
                            continue
                        elif isinstance(widget, (ctk.CTkEntry, ctk.CTkButton)):
                            widget.configure(state="disabled")
        except AttributeError:
            pass  # 위젯 파괴 후 예외 무시

    def enable_settings_widgets(self):
        # ⚠️ 수정: winfo_children()[0] 인덱스 접근 → self.settings_frame 직접 참조로 안전하게 변경
        try:
            if not self.root.winfo_exists():
                return
            if not hasattr(self, 'settings_frame') or not self.settings_frame.winfo_exists():
                return
            for child in self.settings_frame.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for widget in child.winfo_children():
                        if isinstance(widget, (ctk.CTkEntry, ctk.CTkButton)):
                            widget.configure(state="normal")
            self.refresh_docs_target_ui()
        except AttributeError:
            pass

    def show_help_dialog(self):
        """초기 실행 시 도움말 표시"""
        if not show_help_dialog_window:
            messagebox.showerror("UI 오류", "도움말 대화상자 모듈을 불러오지 못했습니다.", parent=self.root)
            return

        def on_help_close():
            self.settings_changed = True

        show_help_dialog_window(
            self.root,
            show_help_on_startup=self.show_help_on_startup,
            on_window_close=on_help_close,
            ctk_module=ctk,
            center_window_func=center_window,
        )

    def show_first_run_wizard(self):
        """처음 실행 시 단계별 설정 마법사를 표시한다."""
        if hasattr(self, "first_run_wizard") and self.first_run_wizard and self.first_run_wizard.winfo_exists():
            self.first_run_wizard.deiconify()
            self.first_run_wizard.lift()
            self.first_run_wizard.focus_force()
            return

        wizard = ctk.CTkToplevel(self.root)
        wizard.title("처음 실행 설정 마법사")
        wizard.geometry("760x540")
        wizard.minsize(720, 500)
        wizard.transient(self.root)
        self.first_run_wizard = wizard

        step_index = tk.IntVar(value=0)
        step_frames = []
        step_title_var = ctk.StringVar(value="")
        step_desc_var = ctk.StringVar(value="")
        folder_status_var = ctk.StringVar(value="")
        docs_status_var = ctk.StringVar(value="")
        summary_var = ctk.StringVar(value="")
        wizard_trace_ids = []

        def refresh_wizard_state(*_args):
            watch_folder = self.watch_folder.get().strip()
            docs_value = self.docs_input.get().strip()
            folder_status_var.set(watch_folder or "아직 감시 폴더를 선택하지 않았습니다.")
            docs_status_var.set(docs_value or "아직 대상 문서를 지정하지 않았습니다.")
            summary_var.set(
                "\n".join(
                    [
                        f"감시 폴더: {watch_folder or '미설정'}",
                        f"대상 문서: {docs_value or '미설정'}",
                        f"시작 시 도움말: {'표시' if self.show_help_on_startup.get() else '숨김'}",
                        f"성공 알림: {'표시' if self.show_success_notifications.get() else '숨김'}",
                        f"Windows 자동 실행: {'사용' if self.launch_on_windows_startup.get() else '사용 안 함'}",
                    ]
                )
            )

        def release_wizard_traces():
            for variable, trace_id in wizard_trace_ids:
                try:
                    variable.trace_remove("write", trace_id)
                except Exception:
                    pass

        def close_later():
            release_wizard_traces()
            self.log("첫 실행 설정 마법사를 나중에 다시 표시하도록 유지했습니다.")
            self.first_run_wizard = None
            wizard.destroy()

        def finish_wizard():
            release_wizard_traces()
            self.first_run.set(False)
            self.save_config()
            self.log("첫 실행 설정 마법사 완료.")
            self.first_run_wizard = None
            wizard.destroy()

        def update_step():
            step_data = (
                ("1. 감시 폴더 선택", "먼저 텍스트 파일이 쌓이는 폴더를 지정합니다. 이후 이 위치를 기준으로 자동 감시가 시작됩니다."),
                ("2. Google Docs 연결", "기록할 문서를 정합니다. 새 문서를 만들거나, 기존 주소를 붙여넣거나, 접근 가능한 목록에서 선택할 수 있습니다."),
                ("3. 알림 및 마무리", "처음 실행 후 보여줄 안내와 성공 알림 여부를 고르고 설정을 저장합니다."),
            )
            current_step = step_index.get()
            step_title_var.set(step_data[current_step][0])
            step_desc_var.set(step_data[current_step][1])

            for index, frame in enumerate(step_frames):
                if index == current_step:
                    frame.pack(fill="both", expand=True, pady=(12, 0))
                else:
                    frame.pack_forget()

            back_button.configure(state="normal" if current_step > 0 else "disabled")
            next_button.configure(text="완료" if current_step == len(step_frames) - 1 else "다음")
            refresh_wizard_state()

        def go_back():
            if step_index.get() > 0:
                step_index.set(step_index.get() - 1)
                update_step()

        def go_next():
            if step_index.get() >= len(step_frames) - 1:
                finish_wizard()
                return
            step_index.set(step_index.get() + 1)
            update_step()

        wizard.protocol("WM_DELETE_WINDOW", close_later)

        container = ctk.CTkFrame(wizard)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        header_frame = ctk.CTkFrame(container, corner_radius=14)
        header_frame.pack(fill="x")

        ctk.CTkLabel(
            header_frame,
            text="Messenger Docs 시작 마법사",
            font=self.build_ui_font(19, "bold"),
        ).pack(anchor="w", padx=18, pady=(16, 4))

        ctk.CTkLabel(
            header_frame,
            textvariable=step_title_var,
            font=self.build_ui_font(16, "bold"),
            text_color=("#1A73E8", "#8AB4F8"),
        ).pack(anchor="w", padx=18)

        ctk.CTkLabel(
            header_frame,
            textvariable=step_desc_var,
            justify="left",
            wraplength=660,
            font=self.build_ui_font(12),
            text_color=("gray40", "gray72"),
        ).pack(anchor="w", fill="x", padx=18, pady=(6, 16))

        body_frame = ctk.CTkFrame(container, corner_radius=14)
        body_frame.pack(fill="both", expand=True, pady=(14, 0))

        step_one = ctk.CTkFrame(body_frame, fg_color="transparent")
        ctk.CTkLabel(
            step_one,
            text="감시할 폴더를 먼저 선택하세요.",
            font=self.build_ui_font(14, "bold"),
        ).pack(anchor="w", pady=(6, 10))
        ctk.CTkLabel(
            step_one,
            text="현재 선택",
            font=self.build_ui_font(12, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            step_one,
            textvariable=folder_status_var,
            justify="left",
            wraplength=640,
            font=self.build_ui_font(12),
            text_color=("gray40", "gray72"),
        ).pack(anchor="w", pady=(4, 14))
        ctk.CTkButton(
            step_one,
            text="감시 폴더 선택",
            width=140,
            height=38,
            command=self.browse_folder,
            font=self.build_ui_font(12, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            step_one,
            text="이 단계는 필수는 아니지만, 나중에 감시 시작 전에 반드시 지정해야 합니다.",
            font=self.build_ui_font(12),
            text_color=("gray45", "gray72"),
        ).pack(anchor="w", pady=(12, 0))

        step_two = ctk.CTkFrame(body_frame, fg_color="transparent")
        ctk.CTkLabel(
            step_two,
            text="Google 인증과 대상 문서 선택을 순서대로 진행하세요.",
            font=self.build_ui_font(14, "bold"),
        ).pack(anchor="w", pady=(6, 10))
        ctk.CTkLabel(
            step_two,
            text="현재 문서 상태",
            font=self.build_ui_font(12, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            step_two,
            textvariable=docs_status_var,
            justify="left",
            wraplength=640,
            font=self.build_ui_font(12),
            text_color=("gray40", "gray72"),
        ).pack(anchor="w", pady=(4, 14))

        step_two_buttons = ctk.CTkFrame(step_two, fg_color="transparent")
        step_two_buttons.pack(anchor="w", pady=(0, 10))
        ctk.CTkButton(
            step_two_buttons,
            text="Google 인증 설정",
            width=150,
            height=38,
            command=self.show_credentials_wizard,
            font=self.build_ui_font(12, "bold"),
        ).pack(side="left")
        ctk.CTkButton(
            step_two_buttons,
            text="새 문서 만들기",
            width=126,
            height=38,
            command=self.create_new_google_doc,
            font=self.build_ui_font(12, "bold"),
            fg_color="#0F9D58",
            hover_color="#0B8043",
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            step_two_buttons,
            text="문서 목록",
            width=96,
            height=38,
            command=self.select_google_doc,
            font=self.build_ui_font(12, "bold"),
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            step_two,
            text="기존 문서 주소 직접 입력",
            width=188,
            height=38,
            command=self.focus_existing_docs_input,
            font=self.build_ui_font(12, "bold"),
            fg_color=("gray85", "gray28"),
            hover_color=("gray78", "gray34"),
            text_color=("gray20", "gray92"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            step_two,
            text="문서를 나중에 지정해도 되지만, 감시를 시작하기 전에는 대상 문서가 필요합니다.",
            font=self.build_ui_font(12),
            text_color=("gray45", "gray72"),
        ).pack(anchor="w", pady=(12, 0))

        step_three = ctk.CTkFrame(body_frame, fg_color="transparent")
        ctk.CTkLabel(
            step_three,
            text="기본 동작을 확인하고 저장합니다.",
            font=self.build_ui_font(14, "bold"),
        ).pack(anchor="w", pady=(6, 10))
        ctk.CTkCheckBox(
            step_three,
            text="프로그램 시작 시 도움말 표시",
            variable=self.show_help_on_startup,
            onvalue=True,
            offvalue=False,
            font=self.build_ui_font(12),
        ).pack(anchor="w", pady=4)
        ctk.CTkCheckBox(
            step_three,
            text="Google Docs 기록 성공 시 트레이 알림 표시",
            variable=self.show_success_notifications,
            onvalue=True,
            offvalue=False,
            font=self.build_ui_font(12),
        ).pack(anchor="w", pady=4)
        wizard_autostart_checkbox = ctk.CTkCheckBox(
            step_three,
            text="Windows 로그인 시 자동으로 실행",
            variable=self.launch_on_windows_startup,
            onvalue=True,
            offvalue=False,
            font=self.build_ui_font(12),
        )
        wizard_autostart_checkbox.pack(anchor="w", pady=4)
        if not (supports_windows_startup and supports_windows_startup()):
            wizard_autostart_checkbox.configure(state="disabled")
        ctk.CTkLabel(
            step_three,
            text="현재 설정 요약",
            font=self.build_ui_font(12, "bold"),
        ).pack(anchor="w", pady=(18, 6))
        ctk.CTkLabel(
            step_three,
            textvariable=summary_var,
            justify="left",
            wraplength=640,
            font=self.build_ui_font(12),
            text_color=("gray40", "gray72"),
        ).pack(anchor="w")

        step_frames.extend((step_one, step_two, step_three))

        footer_frame = ctk.CTkFrame(container, fg_color="transparent")
        footer_frame.pack(fill="x", pady=(14, 0))

        ctk.CTkButton(
            footer_frame,
            text="나중에",
            width=92,
            height=38,
            command=close_later,
            font=self.build_ui_font(12, "bold"),
            fg_color=("gray85", "gray28"),
            hover_color=("gray78", "gray34"),
            text_color=("gray20", "gray92"),
        ).pack(side="left")

        back_button = ctk.CTkButton(
            footer_frame,
            text="이전",
            width=92,
            height=38,
            command=go_back,
            font=self.build_ui_font(12, "bold"),
            fg_color=("gray85", "gray28"),
            hover_color=("gray78", "gray34"),
            text_color=("gray20", "gray92"),
        )
        back_button.pack(side="right")

        next_button = ctk.CTkButton(
            footer_frame,
            text="다음",
            width=92,
            height=38,
            command=go_next,
            font=self.build_ui_font(12, "bold"),
        )
        next_button.pack(side="right", padx=(0, 8))

        wizard_trace_ids.append((self.watch_folder, self.watch_folder.trace_add("write", refresh_wizard_state)))
        wizard_trace_ids.append((self.docs_input, self.docs_input.trace_add("write", refresh_wizard_state)))
        wizard_trace_ids.append((self.show_help_on_startup, self.show_help_on_startup.trace_add("write", refresh_wizard_state)))
        wizard_trace_ids.append((self.show_success_notifications, self.show_success_notifications.trace_add("write", refresh_wizard_state)))
        wizard_trace_ids.append((self.launch_on_windows_startup, self.launch_on_windows_startup.trace_add("write", refresh_wizard_state)))

        update_step()
        refresh_wizard_state()
        if center_window:
            center_window(wizard)

    def show_enhanced_error_dialog(self, error_type, error_message):
        """
        개선된 오류 대화 상자를 표시합니다.
        오류 유형에 따라 단계별 해결 방법을 제공합니다.
        """
        if not show_enhanced_error_dialog_window:
            messagebox.showerror(error_type, error_message, parent=self.root)
            return

        show_enhanced_error_dialog_window(
            self.root,
            error_type=error_type,
            error_message=error_message,
            on_open_logs=lambda: self.open_folder_in_explorer(LOG_DIR_STR),
            ctk_module=ctk,
            center_window_func=center_window,
        )

    def clear_log(self):
        """로그 텍스트 지우기"""
        try:
            self.log_text.configure(state='normal')
            self.log_text.delete("1.0", ctk.END)
            self.log_text.configure(state='disabled')

            if self.log_popup_window and self.log_popup_window.winfo_exists() and self.log_popup_text:
                self.log_popup_text.configure(state='normal')
                self.log_popup_text.delete("1.0", ctk.END)
                self.log_popup_text.configure(state='disabled')

            self.log("로그 내용을 지웠습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"로그 지우기 실패: {e}", parent=self.root)
    
    def show_log_search_dialog(self):
        """로그 검색 대화 상자 표시"""
        search_window = ctk.CTkToplevel(self.root)
        search_window.title("로그 검색")
        search_window.geometry("500x200")
        search_window.minsize(500, 200)
        search_window.transient(self.root)  # 부모 창 위에 표시
        search_window.grab_set()  # 모달 창으로 설정
        
        # 메인 프레임
        main_frame = ctk.CTkFrame(search_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 검색어 입력
        search_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(search_frame, text="검색어:").pack(side="left", padx=(0, 10))
        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, textvariable=search_var, width=250)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.focus_set()  # 포커스 설정
        
        # 검색 옵션
        options_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        options_frame.pack(fill="x", pady=(0, 15))
        
        case_sensitive_var = ctk.BooleanVar(value=False)
        case_sensitive_check = ctk.CTkCheckBox(
            options_frame, 
            text="대소문자 구분", 
            variable=case_sensitive_var
        )
        case_sensitive_check.pack(side="left", padx=(0, 15))
        
        # 버튼 프레임
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 0))
        
        # 검색 함수
        def search_log():
            search_text = search_var.get()
            if not search_text:
                messagebox.showinfo("알림", "검색어를 입력하세요.", parent=search_window)
                return
            
            self.log_text.tag_remove("search", "1.0", ctk.END)  # 기존 검색 결과 제거
            
            # 대소문자 구분 옵션
            if case_sensitive_var.get():
                search_text = search_text  # 그대로 사용
            else:
                search_text = search_text.lower()  # 소문자로 변환
            
            self.log_text.configure(state='normal')
            
            # 검색 시작
            start_pos = "1.0"
            found_count = 0
            
            while True:
                if not case_sensitive_var.get():
                    # 대소문자 구분 없이 검색
                    current_text = self.log_text.get("1.0", ctk.END).lower()
                    pos = current_text.find(search_text, self.log_text.index(start_pos).split('.')[0])
                else:
                    # 대소문자 구분하여 검색
                    pos = self.log_text.search(search_text, start_pos, stopindex=ctk.END)
                
                if not pos:
                    break
                
                line, char = pos.split('.')
                end_pos = f"{line}.{int(char) + len(search_text)}"
                
                # 검색 결과 강조 표시
                self.log_text.tag_add("search", pos, end_pos)
                self.log_text.tag_config("search", background="yellow", foreground="black")
                
                # 다음 검색 위치 설정
                start_pos = end_pos
                found_count += 1
            
            self.log_text.configure(state='disabled')
            
            # 검색 결과 표시
            if found_count > 0:
                messagebox.showinfo("검색 결과", f"{found_count}개의 결과를 찾았습니다.", parent=search_window)
                # 첫 번째 검색 결과로 스크롤
                self.log_text.see("search.first")
            else:
                messagebox.showinfo("검색 결과", "검색 결과가 없습니다.", parent=search_window)
        
        # 검색 버튼
        search_button = ctk.CTkButton(
            button_frame,
            text="검색",
            command=search_log,
            width=100
        )
        search_button.pack(side="left", padx=(0, 10))
        
        # 닫기 버튼
        close_button = ctk.CTkButton(
            button_frame,
            text="닫기",
            command=search_window.destroy,
            width=100
        )
        close_button.pack(side="right")
        
        # 엔터 키로 검색 실행
        search_window.bind("<Return>", lambda event: search_log())
        
        # 창 중앙 배치
        search_window.update_idletasks()
        width = search_window.winfo_width()
        height = search_window.winfo_height()
        x = (search_window.winfo_screenwidth() // 2) - (width // 2)
        y = (search_window.winfo_screenheight() // 2) - (height // 2)
        search_window.geometry(f"{width}x{height}+{x}+{y}")

    def show_filter_settings(self):
        """고급 파일 필터 설정 대화 상자"""
        filter_window = ctk.CTkToplevel(self.root)
        filter_window.title("고급 파일 필터 설정")
        filter_window.geometry("650x450")
        filter_window.minsize(650, 450)
        filter_window.transient(self.root)  # 부모 창 위에 표시
        filter_window.grab_set()  # 모달 창으로 설정
        
        # 메인 프레임
        main_frame = ctk.CTkFrame(filter_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 파일 확장자 필터 섹션
        ext_frame = ctk.CTkFrame(main_frame)
        ext_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            ext_frame, 
            text="파일 확장자 필터", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 5))
        
        ctk.CTkLabel(
            ext_frame,
            text="감시할 파일 확장자를 쉼표로 구분하여 입력하세요.\n예: .txt,.log,.md"
        ).pack(anchor="w", pady=(0, 5))
        
        ext_entry = ctk.CTkEntry(ext_frame, textvariable=self.file_extensions)
        ext_entry.pack(fill="x", pady=5)
        
        # 미리 정의된 확장자 선택 버튼들
        preset_frame = ctk.CTkFrame(ext_frame, fg_color="transparent")
        preset_frame.pack(fill="x", pady=5)
        
        def add_extension(ext):
            current = self.file_extensions.get().strip()
            if not current:
                self.file_extensions.set(ext)
            else:
                exts = [e.strip() for e in current.split(",")]
                if ext not in exts:
                    exts.append(ext)
                    self.file_extensions.set(",".join(exts))
        
        ctk.CTkButton(
            preset_frame, 
            text=".txt", 
            width=60,
            command=lambda: add_extension(".txt")
        ).pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(
            preset_frame, 
            text=".log", 
            width=60,
            command=lambda: add_extension(".log")
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            preset_frame, 
            text=".md", 
            width=60,
            command=lambda: add_extension(".md")
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            preset_frame, 
            text=".csv", 
            width=60,
            command=lambda: add_extension(".csv")
        ).pack(side="left", padx=5)
        
        # 정규식 필터 섹션
        regex_frame = ctk.CTkFrame(main_frame)
        regex_frame.pack(fill="x", pady=(0, 15))
        
        regex_header = ctk.CTkFrame(regex_frame, fg_color="transparent")
        regex_header.pack(fill="x")
        
        ctk.CTkLabel(
            regex_header, 
            text="정규식 필터", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", pady=(0, 5))
        
        regex_check = ctk.CTkCheckBox(
            regex_header,
            text="정규식 필터 사용",
            variable=self.use_regex_filter,
            onvalue=True,
            offvalue=False
        )
        regex_check.pack(side="right")
        
        ctk.CTkLabel(
            regex_frame,
            text="파일 이름에 적용할 정규식 패턴을 입력하세요.\n예: ^log_\\d{8}\\.txt$ (log_날짜8자리.txt 형식 파일만 매칭)"
        ).pack(anchor="w", pady=(0, 5))
        
        regex_entry = ctk.CTkEntry(regex_frame, textvariable=self.regex_pattern)
        regex_entry.pack(fill="x", pady=5)
        
        # 테스트 섹션
        test_frame = ctk.CTkFrame(main_frame)
        test_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            test_frame, 
            text="필터 테스트", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 5))
        
        test_input_frame = ctk.CTkFrame(test_frame, fg_color="transparent")
        test_input_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(test_input_frame, text="파일 이름:").pack(side="left", padx=(0, 5))
        
        test_filename_var = ctk.StringVar(value="example.txt")
        test_filename_entry = ctk.CTkEntry(test_input_frame, textvariable=test_filename_var, width=200)
        test_filename_entry.pack(side="left", fill="x", expand=True)
        
        test_result_var = ctk.StringVar(value="")
        
        def test_filter():
            filename = test_filename_var.get().strip()
            if not filename:
                test_result_var.set("파일 이름을 입력하세요")
                return
                
            # 확장자 필터 테스트
            extensions = [ext.strip() for ext in self.file_extensions.get().split(",") if ext.strip()]
            ext_match = any(filename.lower().endswith(ext.lower()) for ext in extensions) if extensions else True
            
            # 정규식 필터 테스트
            regex_match = True
            if self.use_regex_filter.get() and self.regex_pattern.get().strip():
                try:
                    import re
                    pattern = re.compile(self.regex_pattern.get())
                    regex_match = bool(pattern.search(filename))
                except re.error:
                    test_result_var.set("정규식 패턴 오류!")
                    return
            
            # 최종 결과
            if ext_match and regex_match:
                test_result_var.set("✅ 매칭됨: 이 파일은 감시 대상입니다")
            else:
                test_result_var.set("❌ 매칭 안됨: 이 파일은 무시됩니다")
        
        ctk.CTkButton(
            test_input_frame,
            text="테스트",
            width=80,
            command=test_filter
        ).pack(side="right", padx=(5, 0))
        
        test_result_label = ctk.CTkLabel(
            test_frame,
            textvariable=test_result_var,
            font=ctk.CTkFont(weight="bold")
        )
        test_result_label.pack(fill="x", pady=5)
        
        # 버튼 프레임
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(15, 0))
        
        # 확인 버튼
        ok_button = ctk.CTkButton(
            button_frame,
            text="확인",
            command=filter_window.destroy,
            width=100
        )
        ok_button.pack(side="right")
        
        # 창 중앙 배치
        filter_window.update_idletasks()
        width = filter_window.winfo_width()
        height = filter_window.winfo_height()
        x = (filter_window.winfo_screenwidth() // 2) - (width // 2)
        y = (filter_window.winfo_screenheight() // 2) - (height // 2)
        filter_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 초기 테스트 실행
        filter_window.after(500, test_filter)

    def toggle_theme(self):
        """테마 모드 전환 (라이트/다크)"""
        current_mode = ctk.get_appearance_mode()
        new_mode = "Dark" if current_mode == "Light" else "Light"
        ctk.set_appearance_mode(new_mode)
        self.appearance_mode.set(new_mode)
        self.log(f"테마 변경: {new_mode} 모드")
        self.settings_changed = True
    
    def show_theme_settings(self):
        """테마 설정 대화 상자"""
        if not show_theme_settings_dialog:
            messagebox.showerror("UI 오류", "테마 설정 대화상자 모듈을 불러오지 못했습니다.", parent=self.root)
            return

        def apply_theme(new_mode):
            if new_mode != self.appearance_mode.get():
                self.appearance_mode.set(new_mode)
                ctk.set_appearance_mode(new_mode)
                self.log(f"테마 변경: {new_mode} 모드")
                self.settings_changed = True

        show_theme_settings_dialog(
            self.root,
            current_mode=self.appearance_mode.get(),
            on_apply_theme=apply_theme,
            ctk_module=ctk,
            center_window_func=center_window,
        )

    def backup_settings(self):
        """현재 설정을 백업 파일로 저장"""
        # 백업 파일 저장 대화 상자
        backup_path = filedialog.asksaveasfilename(
            title="설정 백업 저장",
            defaultextension=".json",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
            initialfile=f"messenger_docs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if not backup_path:
            return  # 사용자가 취소함
        
        if not save_backup_config:
            messagebox.showerror("백업 실패", "설정 백업 모듈을 불러오지 못했습니다.", parent=self.root)
            return

        try:
            # 백업 파일 저장
            save_backup_config(backup_path, self.get_current_config_data())
            
            self.log(f"설정 백업 완료: {backup_path}")
            messagebox.showinfo("백업 완료", f"설정이 성공적으로 백업되었습니다.\n{backup_path}", parent=self.root)
        except Exception as e:
            self.log(f"설정 백업 실패: {e}")
            messagebox.showerror("백업 실패", f"설정 백업 중 오류가 발생했습니다.\n{e}", parent=self.root)
    
    def restore_settings(self):
        """백업 파일에서 설정 복원"""
        # 백업 파일 선택 대화 상자
        backup_path = filedialog.askopenfilename(
            title="설정 백업 파일 선택",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")]
        )
        
        if not backup_path:
            return  # 사용자가 취소함

        if not load_backup_config:
            messagebox.showerror("복원 실패", "설정 복원 모듈을 불러오지 못했습니다.", parent=self.root)
            return
        
        try:
            # 백업 파일 로드
            restored_config, backup_data = load_backup_config(backup_path)
            
            # 백업 버전 확인
            if "backup_version" not in backup_data:
                self.log("경고: 백업 파일에 버전 정보가 없습니다.")
            
            # 설정 복원 전 확인
            confirm = messagebox.askyesno(
                "설정 복원 확인",
                f"백업 파일({os.path.basename(backup_path)})에서 설정을 복원하시겠습니까?\n\n"
                f"백업 날짜: {backup_data.get('backup_date', '정보 없음')}\n\n"
                "현재 설정이 모두 덮어쓰기됩니다.",
                parent=self.root
            )
            
            if not confirm:
                return
            
            # 설정 복원
            self.apply_config_data(restored_config)
            
            # 설정 변경 플래그 설정 및 상태 업데이트
            self.settings_changed = True
            self.on_setting_changed()
            
            self.log(f"설정 복원 완료: {backup_path}")
            messagebox.showinfo("복원 완료", "설정이 성공적으로 복원되었습니다.", parent=self.root)
        except json.JSONDecodeError:
            self.log(f"설정 복원 실패: 잘못된 JSON 형식 - {backup_path}")
            messagebox.showerror("복원 실패", "유효하지 않은 백업 파일입니다. JSON 형식이 올바르지 않습니다.", parent=self.root)
        except Exception as e:
            self.log(f"설정 복원 실패: {e}")
            messagebox.showerror("복원 실패", f"설정 복원 중 오류가 발생했습니다.\n{e}", parent=self.root)
    
    def show_backup_restore_dialog(self):
        """백업 및 복원 대화 상자"""
        if not show_backup_restore_dialog:
            messagebox.showerror("UI 오류", "백업/복원 대화상자 모듈을 불러오지 못했습니다.", parent=self.root)
            return

        show_backup_restore_dialog(
            self.root,
            on_backup=self.backup_settings,
            on_restore=self.restore_settings,
            ctk_module=ctk,
        )

    def check_memory_usage(self):
        """현재 프로세스의 메모리 사용량을 확인하고 표시"""
        try:
            # 현재 프로세스의 메모리 사용량 확인
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # MB 단위로 변환
            memory_usage_mb = memory_info.rss / 1024 / 1024
            
            # 메모리 사용량 표시 업데이트
            self.memory_usage.set(f"메모리: {memory_usage_mb:.1f} MB")
            
            # 메모리 사용량이 너무 높으면 경고
            if memory_usage_mb > 200:  # 200MB 이상이면 경고
                self.log(f"경고: 메모리 사용량이 높습니다 ({memory_usage_mb:.1f} MB). 프로그램을 재시작하는 것이 좋습니다.")
                
                # 메모리 사용량이 매우 높으면 자동 최적화 시도
                if memory_usage_mb > 300:  # 300MB 이상이면 강제 최적화
                    self.log("메모리 사용량이 매우 높습니다. 자동 최적화를 시도합니다.")
                    self.optimize_memory()
        except Exception as e:
            print(f"메모리 사용량 확인 중 오류: {e}")
        finally:
            # 주기적으로 메모리 사용량 확인
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.after(self.memory_check_interval, self.check_memory_usage)
    
    def optimize_memory(self):
        """메모리 사용량 최적화 시도"""
        try:
            # 1. 로그 텍스트 최적화
            if hasattr(self, 'log_text') and self.root.winfo_exists():
                self.log_text.configure(state='normal')
                # 로그 텍스트를 더 적극적으로 정리 (최근 200줄만 유지)
                log_content = self.log_text.get("1.0", ctk.END)
                lines = log_content.split('\n')
                if len(lines) > 200:
                    lines_to_keep = lines[-200:]
                    self.log_text.delete("1.0", ctk.END)
                    self.log_text.insert("1.0", "\n".join(lines_to_keep) + "\n")
                    self.log_text.insert("1.0", "--- 메모리 최적화: 로그가 정리되었습니다 ---\n\n")
                self.log_text.configure(state='disabled')
            
            # 2. 가비지 컬렉션 강제 실행
            import gc
            gc.collect()
            
            # 3. 최적화 후 메모리 사용량 다시 확인
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_usage_mb = memory_info.rss / 1024 / 1024
            self.log(f"메모리 최적화 완료. 현재 메모리 사용량: {memory_usage_mb:.1f} MB")
            
            # 메모리 사용량 표시 업데이트
            self.memory_usage.set(f"메모리: {memory_usage_mb:.1f} MB")
        except Exception as e:
            print(f"메모리 최적화 중 오류: {e}")

    def on_closing(self): # 창 닫기(X) 버튼 클릭 시 호출됨
        """ 창의 X 버튼 클릭 시 창 숨기기 """
        self.hide_window()

    # --- 새로 추가: Google 인증 설정 마법사 ---
    def show_credentials_wizard(self):
        """Google Cloud Console 안내 및 credentials.json 복사를 돕는 설정 마법사"""
        if not USER_CREDENTIALS_FILE_STR:
            messagebox.showerror(
                "경로 오류",
                "인증 파일 저장 경로가 설정되어 있지 않습니다.\n프로그램을 다시 실행하거나 개발자에게 문의하세요.",
                parent=self.root,
            )
            return

        if not show_credentials_wizard_dialog:
            messagebox.showerror("UI 오류", "인증 설정 마법사 모듈을 불러오지 못했습니다.", parent=self.root)
            return

        credentials_target = Path(str(USER_CREDENTIALS_FILE_STR))

        def select_and_copy_json(update_status):
            file_path = filedialog.askopenfilename(
                title="credentials.json 선택",
                filetypes=[("JSON 파일", "*.json")],
            )
            if not file_path:
                return

            try:
                credentials_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(file_path, credentials_target)
                self.log(f"인증 파일 복사 완료: {credentials_target}")
                update_status("복사 완료! 테스트 중...", "green")

                if credentials_target.exists():
                    update_status("테스트 성공! ✅ 인증 파일이 준비되었습니다.", "green")
                    self.check_credentials_file()
                else:
                    update_status("테스트 실패 ❌ 파일을 찾을 수 없습니다.", "red")
            except Exception as e:
                self.log(f"인증 파일 복사 실패: {e}")
                messagebox.showerror("복사 실패", str(e), parent=self.root)
                update_status("복사 실패 ❌", "red")

        show_credentials_wizard_dialog(
            self.root,
            credentials_target_text=USER_CREDENTIALS_FILE_STR,
            on_open_console=lambda: webbrowser.open("https://console.cloud.google.com/"),
            on_select_json=select_and_copy_json,
            ctk_module=ctk,
            center_window_func=center_window,
        )

    # ---------------- 메뉴바 생성 ----------------
    def _create_menubar(self):
        """Tkinter 기본 Menu 위젯을 사용해 상단 메뉴바(설정)를 추가"""
        menubar = tk.Menu(self.root)

        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="감시 폴더 선택", command=self.browse_folder)
        settings_menu.add_command(label="Google 인증 설정 마법사", command=self.show_credentials_wizard)
        settings_menu.add_separator()
        settings_menu.add_command(label="설정 저장", command=self.save_config)
        settings_menu.add_command(label="설정 백업/복원", command=self.show_backup_restore_dialog)
        settings_menu.add_command(label="테마 설정", command=self.show_theme_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="프로그램 종료", command=self.exit_application)

        menubar.add_cascade(label="설정", menu=settings_menu)

        # 추후 도움말 메뉴 등 추가 가능
        self.root.config(menu=menubar)


# --- 애플리케이션 실행 ---
def main():
    """GUI 애플리케이션 진입점."""
    root = DnDCompatibleTk()
    MessengerDocsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
