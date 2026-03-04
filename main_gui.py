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
    messagebox.showerror("모듈 오류", "백엔드 처리 모듈(backend_processor.py)을 찾을 수 없습니다.")
    run_monitoring = None # 함수 부재 처리

# path_utils 임포트 (공통 경로 정책 사용)
try:
    from src.auto_write_txt_to_docs.path_utils import (
        BUNDLED_CREDENTIALS_FILE_STR,
        CONFIG_FILE_STR,
        LEGACY_CONFIG_FILE_STR,
        LOG_DIR_STR,
    )
except ImportError:
    messagebox.showerror("모듈 오류", "경로 유틸리티 모듈(path_utils.py)을 찾을 수 없습니다.")
    BUNDLED_CREDENTIALS_FILE_STR = None
    CONFIG_FILE_STR = "config.json"
    LEGACY_CONFIG_FILE_STR = "config.json"
    LOG_DIR_STR = "logs"

# --- Helper Function: URL에서 ID 추출 ---
def extract_google_id_from_url(url_or_id):
    """ Google Docs URL에서 ID 추출 """
    if not url_or_id or not isinstance(url_or_id, str): return url_or_id
    match_docs = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url_or_id)
    return match_docs.group(1) if match_docs else url_or_id

class MessengerDocsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("메신저 Docs 자동 기록 (트레이)")
        # 초기 창 크기를 충분히 크게 설정하고, 최소 크기도 지정하여 버튼이 잘리는 현상 방지
        self.root.geometry("900x750")
        self.root.minsize(900, 750)

        # --- 상단 메뉴바 생성 ---
        self._create_menubar()

        # 테마 설정
        self.appearance_mode = ctk.StringVar(value="System")
        ctk.set_appearance_mode(self.appearance_mode.get())
        ctk.set_default_color_theme("blue")
        
        # 메모리 모니터링 관련 변수
        self.memory_usage = ctk.StringVar(value="메모리: 확인 중...")
        self.memory_check_interval = 10000  # 10초마다 메모리 사용량 확인

        # --- 변수 선언 ---
        self.watch_folder = ctk.StringVar()
        self.docs_input = ctk.StringVar()
        self.show_help_on_startup = tk.BooleanVar(value=True)  # 도움말 표시 여부
        
        # 파일 필터링 관련 변수
        self.file_extensions = ctk.StringVar(value=".txt")  # 기본값: .txt 파일만 감시
        self.use_regex_filter = tk.BooleanVar(value=False)  # 정규식 필터 사용 여부
        self.regex_pattern = ctk.StringVar(value="")  # 정규식 패턴
        
        # 테마 관련 변수
        self.appearance_mode = ctk.StringVar(value="System")  # 기본값: 시스템 설정 따름

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
        if not BUNDLED_CREDENTIALS_FILE_STR:
            self.log("오류: BUNDLED_CREDENTIALS_FILE_STR이 설정되지 않았습니다. path_utils.py를 확인하세요.")
            messagebox.showwarning(
                "설정 오류",
                "프로그램 내부 설정(인증 파일 경로)에 문제가 있습니다.\n개발자에게 문의하세요.",
                parent=self.root
            )
            return

        # 실제 파일 존재 여부 확인
        # BUNDLED_CREDENTIALS_FILE_STR은 절대 경로일 수도, 상대 경로일 수도 있습니다.
        # path_utils.py의 get_bundled_credentials_path() 로직에 따라 결정됩니다.
        # 여기서는 해당 경로 문자열을 그대로 사용합니다.
        credentials_path = BUNDLED_CREDENTIALS_FILE_STR

        # path_utils.py에서 get_bundled_credentials_path 함수가 print 하므로, 여기서도 로그를 남깁니다.
        self.log(f"확인 중인 인증 파일 경로: {credentials_path}")

        if not os.path.exists(credentials_path):
            self.log(f"경고: 인증 파일({credentials_path})을 찾을 수 없습니다.")
            open_wizard = messagebox.askyesno(
                "인증 파일 누락",
                f"Google API 인증을 위한 'developer_credentials.json' 파일을 찾을 수 없습니다.\n\n"
                f"예상 경로: {credentials_path}\n\n"
                "프로그램 사용을 위해서는 이 파일이 필요합니다.\n"
                "README.md 파일의 '설정' 섹션을 참고하거나,\n"
                "바로 이어서 'Google 인증 설정 마법사'를 통해 준비할 수 있습니다.\n\n"
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
            errors.append("Google Docs URL 또는 ID를 입력해주세요.")
        else:
            docs_id = extract_google_id_from_url(docs_input_val)
            if not docs_id:
                errors.append("유효한 Google Docs URL 또는 ID를 입력해주세요.")
        
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
    
    def update_status(self, status_text, detail_text=None):
        """상태 표시 업데이트 (상세 내용 추가 가능)"""
        if detail_text:
            full_status = f"{status_text} ({detail_text})"
        else:
            full_status = status_text
        self.status_var.set(full_status)
        self.root.update_idletasks()

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self.root); main_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # 상태 표시 프레임
        status_frame = ctk.CTkFrame(main_frame); status_frame.pack(pady=(0,10), padx=10, fill="x")
        
        # 상태 표시 (왼쪽)
        status_left_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        status_left_frame.pack(side="left", fill="y", padx=10, pady=5)
        ctk.CTkLabel(status_left_frame, text="상태:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0,5))
        self.status_label = ctk.CTkLabel(status_left_frame, textvariable=self.status_var, font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(side="left", padx=5)
        
        # 메모리 사용량 표시 (중앙)
        memory_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        memory_frame.pack(side="left", fill="y", padx=10, pady=5)
        self.memory_label = ctk.CTkLabel(memory_frame, textvariable=self.memory_usage, font=ctk.CTkFont(size=12))
        self.memory_label.pack(side="left", padx=5)
        
        # 메모리 최적화 버튼
        self.memory_optimize_button = ctk.CTkButton(
            memory_frame,
            text="최적화",
            width=60,
            height=20,
            command=self.optimize_memory,
            font=ctk.CTkFont(size=11)
        )
        self.memory_optimize_button.pack(side="left", padx=(5,0))
        
        # 현재 감시 정보 표시 (오른쪽)
        status_right_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        status_right_frame.pack(side="right", fill="y", padx=10, pady=5)
        
        # 감시 폴더 표시
        self.folder_info_var = ctk.StringVar(value="폴더: 설정되지 않음")
        self.folder_info_label = ctk.CTkLabel(status_right_frame, textvariable=self.folder_info_var, 
                                             font=ctk.CTkFont(size=12))
        self.folder_info_label.pack(side="top", anchor="e")
        
        # Docs 문서 표시
        self.docs_info_var = ctk.StringVar(value="문서: 설정되지 않음")
        self.docs_info_label = ctk.CTkLabel(status_right_frame, textvariable=self.docs_info_var, 
                                           font=ctk.CTkFont(size=12))
        self.docs_info_label.pack(side="top", anchor="e")
        
        settings_frame = ctk.CTkFrame(main_frame); settings_frame.pack(pady=10, padx=10, fill="x"); settings_frame.configure(border_width=1)
        ctk.CTkLabel(settings_frame, text="설정", font=ctk.CTkFont(weight="bold")).pack(pady=(5,0)) # pady 변경

        # 인증 파일 안내 라벨 추가
        auth_file_info_label = ctk.CTkLabel(
            settings_frame,
            text="Google API 인증을 위해 'developer_credentials.json' 파일이 필요합니다.\n"
                 "자세한 내용은 README.md 파일을 참고하세요.",
            font=ctk.CTkFont(size=10),
            justify="left",
            text_color="gray" # 흐린 색상으로 표시
        )
        auth_file_info_label.pack(pady=(0,10), padx=10, anchor="w")
        
        # 감시 폴더 설정
        folder_frame = ctk.CTkFrame(settings_frame, fg_color="transparent"); folder_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(folder_frame, text="감시 폴더:", width=120).pack(side="left", padx=(0,5))
        ctk.CTkEntry(folder_frame, textvariable=self.watch_folder).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(folder_frame, text="폴더 선택...", width=80, command=self.browse_folder).pack(side="left", padx=(5,0))
        ctk.CTkButton(folder_frame, text="열기", width=50, command=lambda: self.open_folder_in_explorer(self.watch_folder.get())).pack(side="left", padx=(5,0))
        
        # 파일 필터 설정
        filter_frame = ctk.CTkFrame(settings_frame, fg_color="transparent"); filter_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(filter_frame, text="파일 필터:", width=120).pack(side="left", padx=(0,5))
        
        # 파일 확장자 입력
        ext_entry = ctk.CTkEntry(filter_frame, textvariable=self.file_extensions, width=120)
        ext_entry.pack(side="left", padx=5)
        ctk.CTkLabel(filter_frame, text="(쉼표로 구분, 예: .txt,.log)").pack(side="left", padx=(0,5))
        
        # 필터 설정 버튼
        ctk.CTkButton(filter_frame, text="고급 필터...", width=80, command=self.show_filter_settings).pack(side="right", padx=(5,0))
        
        # Credentials 파일은 이제 자동으로 path_utils에서 관리됩니다
        
        # Google Docs URL/ID 설정
        docs_frame = ctk.CTkFrame(settings_frame, fg_color="transparent"); docs_frame.pack(fill="x", padx=10, pady=(5,10))
        ctk.CTkLabel(docs_frame, text="Google Docs URL/ID:", width=120).pack(side="left", padx=(0,5))
        ctk.CTkEntry(docs_frame, textvariable=self.docs_input).pack(side="left", fill="x", expand=True, padx=5)
        
        # 웹에서 열기 버튼 (아이콘 추가 및 스타일 개선)
        docs_button = ctk.CTkButton(
            docs_frame, 
            text="문서 열기", 
            width=80, 
            command=self.open_docs_in_browser,
            fg_color="#4285F4",  # Google 파란색
            hover_color="#3367D6"  # 어두운 파란색
        )
        docs_button.pack(side="left", padx=(5,0))
        
        # 제어 버튼 프레임
        control_frame = ctk.CTkFrame(main_frame, fg_color="transparent"); control_frame.pack(pady=10, fill="x")
        self.start_button = ctk.CTkButton(control_frame, text="감시 시작", command=self.start_monitoring, width=120); self.start_button.pack(side="left", padx=10)
        self.stop_button = ctk.CTkButton(control_frame, text="감시 중지", command=self.stop_monitoring, width=120, state="disabled"); self.stop_button.pack(side="left", padx=10)
        
        # 웹에서 열기 버튼 (제어 프레임에도 추가)
        self.open_docs_button = ctk.CTkButton(
            control_frame, 
            text="Docs 웹에서 열기", 
            command=self.open_docs_in_browser, 
            width=120,
            fg_color="#4285F4",  # Google 파란색
            hover_color="#3367D6"  # 어두운 파란색
        )
        self.open_docs_button.pack(side="left", padx=10)
        
        ctk.CTkFrame(control_frame, fg_color="transparent").pack(side="left", fill="x", expand=True)
        
        # 테마 버튼
        theme_button = ctk.CTkButton(
            control_frame,
            text="테마 설정",
            command=self.show_theme_settings,
            width=100
        )
        theme_button.pack(side="right", padx=10)
        
        # 백업/복원 버튼
        backup_button = ctk.CTkButton(
            control_frame,
            text="백업/복원",
            command=self.show_backup_restore_dialog,
            width=100
        )
        backup_button.pack(side="right", padx=10)
        
        # 설정 저장 버튼
        ctk.CTkButton(control_frame, text="설정 저장", command=self.save_config, width=120).pack(side="right", padx=10)
        
        # 로그 프레임
        log_frame = ctk.CTkFrame(main_frame); log_frame.pack(pady=10, padx=10, fill="both", expand=True); log_frame.configure(border_width=1)

        log_header_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(log_header_frame, text="로그", font=ctk.CTkFont(weight="bold")).pack(side="left")

        # 로그 폴더 열기 버튼 추가
        self.log_folder_button = ctk.CTkButton(
            log_header_frame,
            text="로그 폴더 열기",
            width=100,
            command=lambda: self.open_folder_in_explorer(LOG_DIR_STR)
        )
        self.log_folder_button.pack(side="right", padx=(5,0)) # 오른쪽 정렬
        
        # 로그 검색 버튼 추가
        self.log_search_button = ctk.CTkButton(
            log_header_frame,
            text="로그 검색",
            width=80,
            command=self.show_log_search_dialog
        )
        self.log_search_button.pack(side="right", padx=5) # 오른쪽 정렬
        
        # 로그 지우기 버튼 추가
        self.log_clear_button = ctk.CTkButton(
            log_header_frame,
            text="로그 지우기",
            width=80,
            command=self.clear_log
        )
        self.log_clear_button.pack(side="right", padx=5) # 오른쪽 정렬

        self.log_text = ctk.CTkTextbox(log_frame, state='disabled', wrap='word', height=150); self.log_text.pack(fill="both", expand=True, padx=10, pady=(0,10))

        # --- 경로 저장 버튼 (설정 섹션 내부, 빠른 수동 저장) ---
        path_save_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        path_save_frame.pack(fill="x", padx=10, pady=(0,10))

        ctk.CTkButton(
            path_save_frame,
            text="경로 저장",
            width=120,
            command=self.save_config,
            fg_color="#4CAF50",  # 녹색
            hover_color="#45A049"
        ).pack(side="right")

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
        config_data = { 
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
        try:
            with open(CONFIG_FILE_STR, 'w', encoding='utf-8') as f: json.dump(config_data, f, indent=4, ensure_ascii=False)
            self.log("설정 저장 완료.")
            self.settings_changed = False  # 설정 저장 후 변경 플래그 초기화
        except Exception as e: messagebox.showerror("저장 오류", f"설정 저장 실패:\n{e}", parent=self.root); self.log(f"오류: 설정 저장 실패 - {e}")
    def load_config(self):
        config_path = CONFIG_FILE_STR
        if not os.path.exists(config_path) and LEGACY_CONFIG_FILE_STR != CONFIG_FILE_STR and os.path.exists(LEGACY_CONFIG_FILE_STR):
            config_path = LEGACY_CONFIG_FILE_STR
            self.log(f"레거시 설정 파일을 불러옵니다: {config_path}")

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f: config_data = json.load(f)
                self.watch_folder.set(config_data.get("watch_folder", ""))
                self.docs_input.set(config_data.get("docs_input", ""))
                self.show_help_on_startup.set(config_data.get("show_help_on_startup", True))
                
                # 파일 필터링 설정 로드
                self.file_extensions.set(config_data.get("file_extensions", ".txt"))
                self.use_regex_filter.set(config_data.get("use_regex_filter", False))
                self.regex_pattern.set(config_data.get("regex_pattern", ""))
                
                # 테마 설정 로드 및 적용
                appearance_mode = config_data.get("appearance_mode", "System")
                self.appearance_mode.set(appearance_mode)
                ctk.set_appearance_mode(appearance_mode)
                self.log(f"테마 설정 로드: {appearance_mode} 모드")
                
                self.log("저장된 설정 로드 완료.")
                
                # 설정 로드 후 상태 표시 업데이트
                self.on_setting_changed()
            except Exception as e: messagebox.showwarning("로드 오류", f"설정 파일 로드 실패:\n{e}", parent=self.root); self.log(f"경고: 설정 파일 로드 실패 - {e}")
        else: self.log("저장된 설정 파일 없음.")
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
        try:
            settings_frame = self.root.winfo_children()[0].winfo_children()[0]
            for child in settings_frame.winfo_children():
                 if isinstance(child, ctk.CTkFrame):
                      for widget in child.winfo_children():
                           # "웹에서 열기" 버튼은 항상 활성화 상태로 유지
                           if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "웹에서 열기":
                               continue
                           elif isinstance(widget, (ctk.CTkEntry, ctk.CTkButton)):
                               widget.configure(state="disabled")
        except (IndexError, AttributeError): pass # 위젯 구조 변경 또는 창 파괴 시 오류 무시
    def enable_settings_widgets(self):
        try:
             if not self.root.winfo_exists(): return
             settings_frame = self.root.winfo_children()[0].winfo_children()[0]
             for child in settings_frame.winfo_children():
                  if isinstance(child, ctk.CTkFrame):
                       for widget in child.winfo_children():
                            if isinstance(widget, (ctk.CTkEntry, ctk.CTkButton)): widget.configure(state="normal")
        except (IndexError, AttributeError): pass

    def show_help_dialog(self):
        """초기 실행 시 도움말 표시"""
        help_window = ctk.CTkToplevel(self.root)
        help_window.title("메신저 Docs 자동 기록 - 시작 가이드")
        help_window.geometry("750x650")
        help_window.minsize(750, 650)
        help_window.transient(self.root)  # 부모 창 위에 표시
        help_window.grab_set()  # 모달 창으로 설정
        
        # 메인 프레임
        main_frame = ctk.CTkFrame(help_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 제목
        title_label = ctk.CTkLabel(
            main_frame, 
            text="메신저 Docs 자동 기록 사용 가이드", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(0, 15))
        
        # 스크롤 가능한 텍스트 영역
        help_text = ctk.CTkTextbox(main_frame, wrap="word", height=350)
        help_text.pack(fill="both", expand=True, padx=10, pady=10)
        help_text.insert("1.0", """
📋 프로그램 개요
이 프로그램은 특정 폴더에 저장되는 텍스트 파일(.txt)의 내용을 자동으로 감지하여 Google Docs 문서에 기록해주는 도구입니다.

🔧 기본 설정 방법
1. 감시 폴더: '폴더 선택...' 버튼을 클릭하여 텍스트 파일이 저장될 폴더를 지정합니다.
   - 이 폴더에 새로운 .txt 파일이 생성되거나 기존 파일이 수정될 때 내용을 감지합니다.

2. Google Docs URL/ID: 내용을 기록할 Google Docs 문서의 URL이나 ID를 입력합니다.
   - 전체 URL(https://docs.google.com/document/d/문서ID/edit)을 붙여넣거나
   - 문서 ID만 직접 입력할 수 있습니다.
   - '웹에서 열기' 버튼을 클릭하면 현재 설정된 문서를 웹 브라우저에서 확인할 수 있습니다.

3. 설정 저장: 설정을 완료한 후 '설정 저장' 버튼을 클릭하면 다음 실행 시에도 같은 설정이 유지됩니다.

🚀 사용 방법
1. '감시 시작' 버튼을 클릭하면 지정된 폴더의 감시가 시작됩니다.
2. 감시 중에는 폴더 내 .txt 파일의 변경이 자동으로 감지됩니다.
3. 감지된 새 내용은 Google Docs 문서의 맨 위에 타임스탬프와 함께 추가됩니다.
4. '감시 중지' 버튼을 클릭하면 감시가 중단됩니다.

🔔 트레이 아이콘 기능
- 창을 닫아도 프로그램은 트레이 아이콘으로 계속 실행됩니다.
- 트레이 아이콘을 우클릭하여 창 보이기/숨기기 또는 프로그램 종료가 가능합니다.

📝 로그 확인
- 프로그램 하단의 로그 창에서 실시간 작업 내역을 확인할 수 있습니다.
- '로그 폴더 열기' 버튼을 클릭하면 상세 로그 파일이 저장된 폴더를 열 수 있습니다.

❓ 문제 해결
- Google 인증 오류: 인증 파일이 올바르게 설치되었는지 확인하세요.
- 연결 오류: 인터넷 연결 상태를 확인하세요.
- 권한 오류: Google 계정에 문서 편집 권한이 있는지 확인하세요.
        """)
        help_text.configure(state="disabled")  # 읽기 전용으로 설정
        
        # 체크박스 (다음에 표시 여부)
        checkbox_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        checkbox_frame.pack(fill="x", pady=(10, 0))
        
        show_on_startup_checkbox = ctk.CTkCheckBox(
            checkbox_frame, 
            text="프로그램 시작 시 이 도움말 표시",
            variable=self.show_help_on_startup,
            onvalue=True,
            offvalue=False
        )
        show_on_startup_checkbox.pack(side="left", padx=10)
        
        # 닫기 버튼
        close_button = ctk.CTkButton(
            main_frame, 
            text="닫기", 
            command=help_window.destroy,
            width=100
        )
        close_button.pack(pady=(10, 0))
        
        # 창이 닫힐 때 설정 저장
        def on_help_close():
            self.settings_changed = True  # 설정 변경 플래그 설정
            help_window.destroy()
        
        help_window.protocol("WM_DELETE_WINDOW", on_help_close)
        
        # 창 중앙 배치
        help_window.update_idletasks()
        width = help_window.winfo_width()
        height = help_window.winfo_height()
        x = (help_window.winfo_screenwidth() // 2) - (width // 2)
        y = (help_window.winfo_screenheight() // 2) - (height // 2)
        help_window.geometry(f"{width}x{height}+{x}+{y}")

    def show_enhanced_error_dialog(self, error_type, error_message):
        """
        개선된 오류 대화 상자를 표시합니다.
        오류 유형에 따라 단계별 해결 방법을 제공합니다.
        """
        error_window = ctk.CTkToplevel(self.root)
        error_window.title("오류 발생")
        error_window.geometry("750x550")
        error_window.minsize(750, 550)
        error_window.transient(self.root)  # 부모 창 위에 표시
        error_window.grab_set()  # 모달 창으로 설정
        
        # 메인 프레임
        main_frame = ctk.CTkFrame(error_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 오류 아이콘 및 제목
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))
        
        # 오류 제목
        title_label = ctk.CTkLabel(
            header_frame, 
            text=f"오류 발생: {error_type}", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FF5252"  # 빨간색
        )
        title_label.pack(pady=(0, 5))
        
        # 구분선
        separator = ctk.CTkFrame(main_frame, height=2, fg_color="#CCCCCC")
        separator.pack(fill="x", pady=(0, 15))
        
        # 오류 내용 프레임
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)
        
        # 오류 메시지
        error_label = ctk.CTkLabel(
            content_frame,
            text="오류 내용:",
            font=ctk.CTkFont(weight="bold"),
            anchor="w"
        )
        error_label.pack(fill="x", anchor="w")
        
        # 오류 메시지 텍스트 박스
        error_text = ctk.CTkTextbox(content_frame, height=80)
        error_text.pack(fill="x", pady=(5, 15))
        error_text.insert("1.0", error_message)
        error_text.configure(state="disabled")  # 읽기 전용
        
        # 해결 방법 제목
        solution_label = ctk.CTkLabel(
            content_frame,
            text="해결 방법:",
            font=ctk.CTkFont(weight="bold"),
            anchor="w"
        )
        solution_label.pack(fill="x", anchor="w")
        
        # 해결 방법 텍스트 박스
        solution_text = ctk.CTkTextbox(content_frame, height=150)
        solution_text.pack(fill="both", expand=True, pady=(5, 15))
        
        # 오류 유형에 따른 해결 방법
        solution = ""
        if "Google 인증 오류" in error_type:
            solution = """1. 인터넷 연결 상태를 확인하세요.
2. 'developer_credentials.json' 파일이 올바른 위치에 있는지 확인하세요.
3. Google 계정에 로그인이 되어 있는지 확인하세요.
4. 브라우저에서 Google 계정에 로그인한 후 다시 시도하세요.
5. 토큰이 만료되었다면, 프로그램을 재시작하여 새로운 인증을 시도하세요.
6. 계속 문제가 발생한다면, 'token.json' 파일을 삭제하고 다시 시도하세요."""
        elif "Docs API 오류" in error_type:
            solution = """1. Google Docs 문서 ID가 올바른지 확인하세요.
2. 해당 Google Docs 문서에 대한 편집 권한이 있는지 확인하세요.
3. Google API 할당량이 초과되었을 수 있습니다. 잠시 후 다시 시도하세요.
4. 인터넷 연결 상태를 확인하세요.
5. 브라우저에서 해당 문서에 직접 접근이 가능한지 확인하세요."""
        elif "파일 접근 오류" in error_type:
            solution = """1. 감시 중인 폴더가 존재하는지 확인하세요.
2. 폴더에 대한 읽기 권한이 있는지 확인하세요.
3. 다른 프로그램이 파일을 사용 중인지 확인하세요.
4. 파일이 이동되거나 삭제되었을 수 있습니다. 파일 존재 여부를 확인하세요.
5. 파일 경로에 특수 문자가 포함되어 있는지 확인하세요."""
        elif "감시 시스템 오류" in error_type:
            solution = """1. 감시 폴더가 올바르게 설정되었는지 확인하세요.
2. 폴더 경로가 너무 길거나 특수 문자를 포함하고 있는지 확인하세요.
3. 프로그램을 재시작하여 감시 시스템을 초기화하세요.
4. 시스템 리소스(메모리, CPU)가 부족하지 않은지 확인하세요."""
        else:
            solution = """1. 인터넷 연결 상태를 확인하세요.
2. 프로그램 설정이 올바른지 확인하세요.
3. 프로그램을 재시작하여 다시 시도하세요.
4. 오류가 계속되면 로그 파일을 확인하여 더 자세한 정보를 얻으세요.
5. 필요한 경우 개발자에게 문의하세요."""
        
        solution_text.insert("1.0", solution)
        solution_text.configure(state="disabled")  # 읽기 전용
        
        # 버튼 프레임
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(15, 0))
        
        # 로그 보기 버튼
        log_button = ctk.CTkButton(
            button_frame,
            text="로그 폴더 열기",
            command=lambda: self.open_folder_in_explorer(LOG_DIR_STR),
            width=120
        )
        log_button.pack(side="left", padx=10)
        
        # 닫기 버튼
        close_button = ctk.CTkButton(
            button_frame,
            text="닫기",
            command=error_window.destroy,
            width=120
        )
        close_button.pack(side="right", padx=10)
        
        # 창 중앙 배치
        error_window.update_idletasks()
        width = error_window.winfo_width()
        height = error_window.winfo_height()
        x = (error_window.winfo_screenwidth() // 2) - (width // 2)
        y = (error_window.winfo_screenheight() // 2) - (height // 2)
        error_window.geometry(f"{width}x{height}+{x}+{y}")

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
        theme_window = ctk.CTkToplevel(self.root)
        theme_window.title("테마 설정")
        theme_window.geometry("500x300")
        theme_window.minsize(500, 300)
        theme_window.transient(self.root)  # 부모 창 위에 표시
        theme_window.grab_set()  # 모달 창으로 설정
        
        # 메인 프레임
        main_frame = ctk.CTkFrame(theme_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 제목
        title_label = ctk.CTkLabel(
            main_frame, 
            text="테마 설정", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 15))
        
        # 테마 모드 선택 프레임
        mode_frame = ctk.CTkFrame(main_frame)
        mode_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            mode_frame, 
            text="테마 모드:", 
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", pady=(0, 5))
        
        # 라디오 버튼 변수
        mode_var = ctk.StringVar(value=self.appearance_mode.get())
        
        # 라디오 버튼 생성
        modes = [("시스템 설정 따름", "System"), ("라이트 모드", "Light"), ("다크 모드", "Dark")]
        
        for text, value in modes:
            radio = ctk.CTkRadioButton(
                mode_frame,
                text=text,
                value=value,
                variable=mode_var
            )
            radio.pack(anchor="w", pady=5, padx=10)
        
        # 미리보기 프레임
        preview_frame = ctk.CTkFrame(main_frame)
        preview_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            preview_frame,
            text="미리보기:",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", pady=(0, 5))
        
        # 미리보기 요소들
        preview_elements = ctk.CTkFrame(preview_frame)
        preview_elements.pack(fill="x", pady=5, padx=10)
        
        ctk.CTkButton(
            preview_elements,
            text="버튼",
            width=80
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkEntry(
            preview_elements,
            width=120,
            placeholder_text="입력 필드"
        ).pack(side="left")
        
        # 버튼 프레임
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(15, 0))
        
        # 적용 버튼
        def apply_theme():
            new_mode = mode_var.get()
            if new_mode != self.appearance_mode.get():
                self.appearance_mode.set(new_mode)
                ctk.set_appearance_mode(new_mode)
                self.log(f"테마 변경: {new_mode} 모드")
                self.settings_changed = True
            theme_window.destroy()
        
        apply_button = ctk.CTkButton(
            button_frame,
            text="적용",
            command=apply_theme,
            width=100
        )
        apply_button.pack(side="right", padx=(5, 0))
        
        # 취소 버튼
        cancel_button = ctk.CTkButton(
            button_frame,
            text="취소",
            command=theme_window.destroy,
            width=100,
            fg_color="gray"
        )
        cancel_button.pack(side="right", padx=5)
        
        # 창 중앙 배치
        theme_window.update_idletasks()
        width = theme_window.winfo_width()
        height = theme_window.winfo_height()
        x = (theme_window.winfo_screenwidth() // 2) - (width // 2)
        y = (theme_window.winfo_screenheight() // 2) - (height // 2)
        theme_window.geometry(f"{width}x{height}+{x}+{y}")

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
        
        try:
            # 현재 설정 데이터 수집
            config_data = {
                "watch_folder": self.watch_folder.get(),
                "docs_input": self.docs_input.get(),
                "show_help_on_startup": self.show_help_on_startup.get(),
                "file_extensions": self.file_extensions.get(),
                "use_regex_filter": self.use_regex_filter.get(),
                "regex_pattern": self.regex_pattern.get(),
                "appearance_mode": self.appearance_mode.get(),
                # 백업 메타데이터
                "backup_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "backup_version": "1.0"
            }
            
            # 백업 파일 저장
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
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
        
        try:
            # 백업 파일 로드
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
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
            if "watch_folder" in backup_data:
                self.watch_folder.set(backup_data["watch_folder"])
            
            if "docs_input" in backup_data:
                self.docs_input.set(backup_data["docs_input"])
            
            if "show_help_on_startup" in backup_data:
                self.show_help_on_startup.set(backup_data["show_help_on_startup"])
            
            if "file_extensions" in backup_data:
                self.file_extensions.set(backup_data["file_extensions"])
            
            if "use_regex_filter" in backup_data:
                self.use_regex_filter.set(backup_data["use_regex_filter"])
            
            if "regex_pattern" in backup_data:
                self.regex_pattern.set(backup_data["regex_pattern"])
            
            if "appearance_mode" in backup_data:
                appearance_mode = backup_data["appearance_mode"]
                self.appearance_mode.set(appearance_mode)
                ctk.set_appearance_mode(appearance_mode)
            
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
        backup_window = ctk.CTkToplevel(self.root)
        backup_window.title("설정 백업 및 복원")
        backup_window.geometry("550x400")
        backup_window.minsize(550, 400)
        backup_window.transient(self.root)  # 부모 창 위에 표시
        backup_window.grab_set()  # 모달 창으로 설정
        
        # 메인 프레임
        main_frame = ctk.CTkFrame(backup_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 제목
        title_label = ctk.CTkLabel(
            main_frame, 
            text="설정 백업 및 복원", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 15))
        
        # 설명
        description = ctk.CTkLabel(
            main_frame,
            text="현재 설정을 백업하거나 이전에 백업한 설정을 복원할 수 있습니다.",
            wraplength=350
        )
        description.pack(pady=(0, 20))
        
        # 백업 섹션
        backup_frame = ctk.CTkFrame(main_frame)
        backup_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            backup_frame,
            text="설정 백업",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", pady=(5, 10), padx=10)
        
        ctk.CTkLabel(
            backup_frame,
            text="현재 설정을 파일로 저장합니다.",
            wraplength=350
        ).pack(anchor="w", padx=10)
        
        ctk.CTkButton(
            backup_frame,
            text="설정 백업",
            command=lambda: [backup_window.destroy(), self.backup_settings()],
            width=120
        ).pack(anchor="w", pady=10, padx=10)
        
        # 복원 섹션
        restore_frame = ctk.CTkFrame(main_frame)
        restore_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            restore_frame,
            text="설정 복원",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", pady=(5, 10), padx=10)
        
        ctk.CTkLabel(
            restore_frame,
            text="백업 파일에서 설정을 불러옵니다.",
            wraplength=350
        ).pack(anchor="w", padx=10)
        
        ctk.CTkButton(
            restore_frame,
            text="설정 복원",
            command=lambda: [backup_window.destroy(), self.restore_settings()],
            width=120
        ).pack(anchor="w", pady=10, padx=10)
        
        # 닫기 버튼
        close_button = ctk.CTkButton(
            main_frame,
            text="닫기",
            command=backup_window.destroy,
            width=100
        )
        close_button.pack(side="right", pady=(10, 0))
        
        # 창 중앙 배치
        backup_window.update_idletasks()
        width = backup_window.winfo_width()
        height = backup_window.winfo_height()
        x = (backup_window.winfo_screenwidth() // 2) - (width // 2)
        y = (backup_window.winfo_screenheight() // 2) - (height // 2)
        backup_window.geometry(f"{width}x{height}+{x}+{y}")

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
        wizard = ctk.CTkToplevel(self.root)
        wizard.title("Google 인증 설정 마법사")
        wizard.geometry("700x500")
        wizard.minsize(700, 500)
        wizard.transient(self.root)
        wizard.grab_set()

        # 메인 프레임
        frame = ctk.CTkFrame(wizard)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 안내 라벨
        info_label = ctk.CTkLabel(
            frame,
            text=(
                "1) 'Google Cloud Console 열기'를 눌러 API를 활성화하고\n"
                "   OAuth 데스크톱 애플리케이션 자격 증명(JSON)을 다운로드하세요.\n\n"
                "2) 'JSON 파일 선택'을 눌러 다운로드한 파일을 선택하면\n"
                "   프로그램이 자동으로 developer_credentials.json 으로 복사합니다.\n\n"
                "3) 복사 후 '테스트' 결과가 성공이면 창을 닫고\n"
                "   프로그램을 다시 실행하거나 감시를 시작하세요."
            ),
            justify="left",
            wraplength=540
        )
        info_label.pack(fill="x", pady=(0, 15))

        # 버튼 영역
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 10))

        # Google Console 열기
        console_btn = ctk.CTkButton(
            btn_frame,
            text="Google Cloud Console 열기",
            command=lambda: webbrowser.open("https://console.cloud.google.com/")
        )
        console_btn.pack(fill="x", pady=5)

        # 결과 라벨 (상태 표시)
        result_label = ctk.CTkLabel(frame, text="JSON 파일을 아직 선택하지 않았습니다.")
        result_label.pack(fill="x", pady=(10, 5))

        # BUNDLED_CREDENTIALS_FILE_STR 이 None 일 가능성 대비
        if not BUNDLED_CREDENTIALS_FILE_STR:
            messagebox.showerror(
                "경로 오류",
                "인증 파일 기본 경로가 설정되어 있지 않습니다.\n프로그램을 다시 실행하거나 개발자에게 문의하세요.",
                parent=wizard
            )
            wizard.destroy()
            return

        credentials_target = Path(str(BUNDLED_CREDENTIALS_FILE_STR))

        # JSON 선택 → 복사
        def select_and_copy_json():
            file_path = filedialog.askopenfilename(
                title="credentials.json 선택",
                filetypes=[("JSON 파일", "*.json")]
            )
            if not file_path:
                return
            try:
                credentials_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(file_path, credentials_target)
                self.log(f"인증 파일 복사 완료: {credentials_target}")
                result_label.configure(text="복사 완료! 테스트 중...", text_color="green")
                wizard.update_idletasks()
                # 복사 후 바로 테스트
                if credentials_target.exists():
                    result_label.configure(text="테스트 성공! ✅ 인증 파일이 준비되었습니다.", text_color="green")
                    # 즉시 재확인하여 메인 상태도 반영
                    self.check_credentials_file()
                else:
                    result_label.configure(text="테스트 실패 ❌ 파일을 찾을 수 없습니다.", text_color="red")
            except Exception as e:
                self.log(f"인증 파일 복사 실패: {e}")
                messagebox.showerror("복사 실패", str(e), parent=wizard)
                result_label.configure(text="복사 실패 ❌", text_color="red")

        json_btn = ctk.CTkButton(
            btn_frame,
            text="JSON 파일 선택",
            command=select_and_copy_json
        )
        json_btn.pack(fill="x", pady=5)

        # 닫기 버튼
        close_btn = ctk.CTkButton(frame, text="닫기", command=wizard.destroy)
        close_btn.pack(pady=(20, 0))

        # 창 중앙 배치
        wizard.update_idletasks()
        w, h = wizard.winfo_width(), wizard.winfo_height()
        x = (wizard.winfo_screenwidth() // 2) - (w // 2)
        y = (wizard.winfo_screenheight() // 2) - (h // 2)
        wizard.geometry(f"{w}x{h}+{x}+{y}")

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
if __name__ == "__main__":
    root = ctk.CTk()
    app = MessengerDocsApp(root)
    root.mainloop()
