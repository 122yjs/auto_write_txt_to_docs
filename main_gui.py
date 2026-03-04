# main_gui.py (아이콘 생성 + Docs 기록 + 트레이 기능 버전)
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
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

class MessengerDocsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("메신저 Docs 자동 기록 (트레이)")
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
        self.watch_folder = ctk.StringVar()
        self.docs_input = ctk.StringVar()
        self.docs_target_locked = tk.BooleanVar(value=False)
        self.docs_target_status_var = ctk.StringVar(value="문서를 지정하면 여기서 고정 상태를 확인할 수 있습니다.")
        self.show_help_on_startup = tk.BooleanVar(value=True)  # 도움말 표시 여부

        # 파일 필터링 관련 변수
        self.file_extensions = ctk.StringVar(value=".txt")  # 기본값: .txt 파일만 감시
        self.use_regex_filter = tk.BooleanVar(value=False)  # 정규식 필터 사용 여부
        self.regex_pattern = ctk.StringVar(value="")  # 정규식 패턴

        self.is_monitoring = False
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()

        self.tray_icon = None
        self.tray_thread = None
        self.icon_image = None # 아이콘 이미지 객체 저장
        
        # 상태 표시 변수
        self.status_var = ctk.StringVar(value="준비")
        
        # 로깅 시스템 초기화
        self.setup_logging()
        
        # 설정 변수 변경 감지를 위한 추적
        self.watch_folder.trace('w', self.on_setting_changed)
        self.docs_input.trace('w', self.on_setting_changed)
        self.show_help_on_startup.trace('w', self.on_setting_changed)
        self.settings_changed = False

        # --- 아이콘 이미지 생성 또는 로드 ---
        self.create_or_load_icon() # 함수 이름 변경

        # --- 위젯 생성 ---
        self.create_widgets()

        # --- 설정 로드 ---
        self.load_config()
        self.settings_changed = False  # 로드 후 변경 플래그 초기화

        # --- 로그 큐 처리 ---
        self.root.after(100, self.process_log_queue)
        
        # --- 메모리 사용량 모니터링 시작 ---
        self.root.after(1000, self.check_memory_usage)

        # --- 창 닫기(X) 버튼 누르면 숨기도록 설정 ---
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window) # 변경 없음

        # --- 트레이 아이콘 설정 및 시작 ---
        if self.icon_image: # 아이콘 준비 완료 시
            self.setup_tray_icon()
            self.start_tray_thread()
        else:
             self.log("오류: 아이콘 이미지를 준비할 수 없어 트레이 기능을 시작할 수 없습니다.")
        
        # --- 초기화 완료 로그 ---
        self.log("애플리케이션 초기화 완료.")
        self.log("설정을 확인하고 '감시 시작' 버튼을 클릭하세요.")

        # --- 인증 파일 확인 ---
        self.check_credentials_file()
        
        # --- 도움말 표시 (설정에 따라) ---
        if self.show_help_on_startup.get():
            self.root.after(800, self.show_help_dialog)  # 0.8초 후 도움말 표시


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

    def create_or_load_icon(self):
        """ 아이콘 파일을 로드하거나 없으면 기본 아이콘 생성 """
        icon_path_temp = "icon.png" # 임시로 파일명 지정 (로드 시도용)
        try:
            # 1. 파일 로드 시도 (기존 로직 유지)
            self.icon_image = Image.open(icon_path_temp)
            self.log(f"아이콘 파일 로드 성공: {icon_path_temp}")
        except FileNotFoundError:
            # 2. 파일이 없으면 기본 아이콘 생성
            self.log(f"정보: 아이콘 파일({icon_path_temp}) 없음. 기본 아이콘을 생성합니다.")
            self.icon_image = self.create_default_icon()
        except Exception as e:
            # 3. 로드/생성 중 기타 오류 발생
            messagebox.showerror("아이콘 오류", f"아이콘 준비 중 오류 발생:\n{e}", parent=self.root)
            self.log(f"오류: 아이콘 준비 실패 - {e}")
            self.icon_image = None # 오류 시 아이콘 없음 처리
    
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
    
    def update_status(self, status_text, detail_text=None):
        """상태 표시 업데이트 (상세 내용 추가 가능)"""
        if detail_text:
            full_status = f"{status_text} ({detail_text})"
        else:
            full_status = status_text
        self.status_var.set(full_status)
        self.root.update_idletasks()

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
                "file_extensions": self.file_extensions,
                "docs_input": self.docs_input,
                "docs_target_status_var": self.docs_target_status_var,
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
                "open_log_folder": lambda: self.open_folder_in_explorer(LOG_DIR_STR),
                "show_log_search_dialog": self.show_log_search_dialog,
                "clear_log": self.clear_log,
            },
            ctk_module=ctk,
            font_family="Malgun Gothic",
        )

        for widget_name, widget_value in widget_refs.items():
            setattr(self, widget_name, widget_value)

        self.refresh_docs_target_ui()

    # --- 트레이 아이콘 설정 및 제어 함수 (이전과 동일) ---
    def setup_tray_icon(self):
        menu = (pystray.MenuItem('보이기/숨기기', self.toggle_window), pystray.MenuItem('종료', self.exit_application))
        self.tray_icon = pystray.Icon("MessengerDocsApp", self.icon_image, "메신저 Docs 자동 기록", menu)

    def run_tray_icon(self):
        if self.tray_icon: self.tray_icon.run()

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
                self.tray_icon.notify(title, message)
                self.log(f"트레이 알림 표시: {title}")
            except Exception as e:
                self.log(f"트레이 알림 표시 실패: {e}")
        else:
            self.log("트레이 아이콘이 초기화되지 않아 알림을 표시할 수 없습니다.")

    def hide_window(self): # X 버튼 클릭 시 호출됨
        """ 메인 창 숨기기 """
        self.root.withdraw()
        self.log("창 숨김. 트레이 아이콘 우클릭으로 메뉴 사용.")

    def show_window(self):
        """ 숨겨진 메인 창 보이기 """
        self.root.deiconify(); self.root.lift(); self.root.focus_force()
        self.log("창 보임.")

    def toggle_window(self): # 트레이 메뉴에서 호출됨
        """ 창 보이기/숨기기 토글 """
        if self.root.winfo_exists(): # 창 존재 확인
            if self.root.state() == 'withdrawn': self.root.after(0, self.show_window)
            else: self.root.after(0, self.hide_window)

    def exit_application(self): # 트레이 메뉴 '종료'에서 호출됨
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
    def log(self, message):
        try:
            # GUI 로그 출력
            if self.root.winfo_exists():
                self.log_text.configure(state='normal')
                
                # 로그 텍스트 크기 제한 (메모리 최적화)
                self.optimize_log_memory()
                
                # 새 로그 추가
                self.log_text.insert(ctk.END, message + '\n')
                self.log_text.configure(state='disabled')
                self.log_text.see(ctk.END)
            
            # 파일 로그 출력
            if hasattr(self, 'logger'):
                self.logger.info(message)
        except Exception: pass
        
    def optimize_log_memory(self):
        """로그 텍스트 크기가 너무 커지면 오래된 로그 삭제 (메모리 최적화)"""
        try:
            # 현재 로그 텍스트 내용 가져오기
            log_content = self.log_text.get("1.0", ctk.END)
            lines = log_content.split('\n')
            
            # 로그 라인이 1000줄 이상이면 오래된 로그 삭제
            max_lines = 1000
            if len(lines) > max_lines:
                # 오래된 로그 삭제 (절반 정도 삭제)
                lines_to_keep = lines[len(lines) - max_lines // 2:]
                
                # 로그 텍스트 지우고 유지할 라인만 다시 삽입
                self.log_text.delete("1.0", ctk.END)
                self.log_text.insert("1.0", "\n".join(lines_to_keep) + "\n")
                
                # 메모리 최적화 메시지 추가
                self.log_text.insert("1.0", "--- 오래된 로그 항목이 메모리에서 정리되었습니다 ---\n\n")
        except Exception as e:
            # 오류 발생 시 조용히 무시 (로깅 시스템 자체에서 오류가 발생하므로 로그 출력 안 함)
            print(f"로그 메모리 최적화 오류: {e}")
    def log_threadsafe(self, message): self.log_queue.put(message)
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
                    self.update_status("처리 중", filename)
                elif "처리 완료:" in msg: # 파일 처리 완료 후 다시 감시 중 상태로
                    self.update_status("감시 중", f"마지막 확인: {current_time_str}")
                elif "Google Docs 업데이트 완료" in msg:
                    self.update_status("Docs 업데이트 완료", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    # 잠시 후 다시 감시 중 상태로 변경 (is_monitoring 확인 추가)
                    if self.is_monitoring:
                        self.root.after(2000, lambda: self.update_status("감시 중", f"마지막 업데이트 후 대기: {datetime.now().strftime('%H:%M:%S')}"))
                    
                    # 트레이 알림 표시
                    if "줄 추가" in msg:
                        try:
                            # 추가된 줄 수 추출
                            import re
                            match = re.search(r'(\d+)줄 추가', msg)
                            lines_count = match.group(1) if match else "새로운"
                            
                            # 알림 표시
                            notification_title = "메신저 Docs 자동 기록"
                            notification_message = f"{lines_count}줄의 새 내용이 Google Docs에 추가되었습니다."
                            self.show_tray_notification(notification_title, notification_message)
                        except Exception as e:
                            self.log(f"알림 처리 중 오류: {e}")
                
                # 오류 메시지 처리 강화
                error_detail = None
                if "오류: Google API 인증 실패" in msg or "오류: Google 서비스 초기화 예외" in msg or "인증 정보(토큰) 갱신 실패" in msg:
                    error_detail = "Google 인증 오류"
                elif "오류: Docs 업데이트 API 오류" in msg:
                    error_detail = "Docs API 오류"
                elif "오류: 파일 처리 중 사라짐" in msg:
                    error_detail = "파일 접근 오류"
                elif "감시 실패" in msg: # 일반적인 감시 실패
                    error_detail = "감시 시스템 오류"
                elif "오류:" in msg and "Google" in msg: # 기타 구글 관련 오류
                    error_detail = "Google 연동 중 일반 오류"

                if error_detail:
                    self.update_status("오류 발생", error_detail)
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
    def save_config(self):
        if not save_app_config:
            messagebox.showerror("저장 오류", "설정 저장 모듈을 불러오지 못했습니다.", parent=self.root)
            return

        config_data = self.get_current_config_data()
        try:
            save_app_config(config_data, config_path=CONFIG_FILE_STR)
            self.log("설정 저장 완료.")
            self.settings_changed = False  # 설정 저장 후 변경 플래그 초기화
        except Exception as e: messagebox.showerror("저장 오류", f"설정 저장 실패:\n{e}", parent=self.root); self.log(f"오류: 설정 저장 실패 - {e}")

    def get_current_config_data(self):
        """현재 UI 상태를 설정 딕셔너리로 변환한다."""
        return {
            "watch_folder": self.watch_folder.get(), 
            "docs_input": self.docs_input.get(),
            "show_help_on_startup": self.show_help_on_startup.get(),
            # 파일 필터링 설정 추가
            "file_extensions": self.file_extensions.get(),
            "use_regex_filter": self.use_regex_filter.get(),
            "regex_pattern": self.regex_pattern.get(),
            # 테마 설정 추가
            "appearance_mode": self.appearance_mode.get()
        }

    def apply_config_data(self, config_data):
        """설정 딕셔너리를 UI 상태에 반영한다."""
        normalized_config = normalize_config_data(config_data) if normalize_config_data else config_data
        self.watch_folder.set(normalized_config.get("watch_folder", ""))
        self.docs_input.set(normalized_config.get("docs_input", ""))
        self.docs_target_locked.set(bool(normalized_config.get("docs_input", "").strip()))
        self.show_help_on_startup.set(normalized_config.get("show_help_on_startup", True))
        self.file_extensions.set(normalized_config.get("file_extensions", ".txt"))
        self.use_regex_filter.set(normalized_config.get("use_regex_filter", False))
        self.regex_pattern.set(normalized_config.get("regex_pattern", ""))

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
                self.log("저장된 설정 파일 없음.")
                return

            applied_config = self.apply_config_data(config_data)
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
        
        watch_folder = self.watch_folder.get().strip()
        docs_input_val = self.docs_input.get().strip()
        docs_id = extract_google_id_from_url(docs_input_val)
        
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
            "regex_pattern": self.regex_pattern.get() if self.use_regex_filter.get() else ""
        }
        
        self.monitoring_thread = threading.Thread(
            target=run_monitoring, 
            args=(current_config, self.log_threadsafe, self.stop_event), 
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
    root = ctk.CTk()
    MessengerDocsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
