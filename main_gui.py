# main_gui.py (아이콘 생성 + Docs 기록 + 트레이 기능 버전)
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
import threading
import queue
import re
import time
import subprocess
import platform
import logging
from datetime import datetime

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

# --- 기본 설정 ---
# 현재 파일(main_gui.py)의 디렉토리 -> 프로젝트 루트
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")
# ICON_PATH = "icon.png" # 더 이상 필요 없음

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
        self.root.geometry("700x500")

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # --- 변수 선언 ---
        self.watch_folder = ctk.StringVar()
        self.docs_input = ctk.StringVar()

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
            # logs 폴더 생성 (절대 경로 사용)
            # PROJECT_ROOT는 파일 상단에 정의되어 있음
            current_dir = PROJECT_ROOT # 프로젝트 루트를 기준으로 logs 폴더 생성
            log_dir = os.path.join(current_dir, "logs")
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
        """설정 변경 감지"""
        self.settings_changed = True
    
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
    
    def update_status(self, status_text):
        """상태 표시 업데이트"""
        self.status_var.set(status_text)
        self.root.update_idletasks()

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self.root); main_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # 상태 표시 프레임
        status_frame = ctk.CTkFrame(main_frame); status_frame.pack(pady=(0,10), padx=10, fill="x")
        ctk.CTkLabel(status_frame, text="상태:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(10,5), pady=5)
        self.status_label = ctk.CTkLabel(status_frame, textvariable=self.status_var, font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(side="left", padx=5, pady=5)
        
        settings_frame = ctk.CTkFrame(main_frame); settings_frame.pack(pady=10, padx=10, fill="x"); settings_frame.configure(border_width=1)
        ctk.CTkLabel(settings_frame, text="설정", font=ctk.CTkFont(weight="bold")).pack(pady=(5,10))
        
        # 감시 폴더 설정
        folder_frame = ctk.CTkFrame(settings_frame, fg_color="transparent"); folder_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(folder_frame, text="감시 폴더:", width=120).pack(side="left", padx=(0,5))
        ctk.CTkEntry(folder_frame, textvariable=self.watch_folder).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(folder_frame, text="폴더 선택...", width=80, command=self.browse_folder).pack(side="left", padx=(5,0))
        ctk.CTkButton(folder_frame, text="열기", width=50, command=lambda: self.open_folder_in_explorer(self.watch_folder.get())).pack(side="left", padx=(5,0))
        
        # Credentials 파일은 이제 자동으로 path_utils에서 관리됩니다
        
        # Google Docs URL/ID 설정
        docs_frame = ctk.CTkFrame(settings_frame, fg_color="transparent"); docs_frame.pack(fill="x", padx=10, pady=(5,10))
        ctk.CTkLabel(docs_frame, text="Google Docs URL/ID:", width=120).pack(side="left", padx=(0,5))
        ctk.CTkEntry(docs_frame, textvariable=self.docs_input).pack(side="left", fill="x", expand=True, padx=5)
        
        # 제어 버튼 프레임
        control_frame = ctk.CTkFrame(main_frame, fg_color="transparent"); control_frame.pack(pady=10, fill="x")
        self.start_button = ctk.CTkButton(control_frame, text="감시 시작", command=self.start_monitoring, width=120); self.start_button.pack(side="left", padx=10)
        self.stop_button = ctk.CTkButton(control_frame, text="감시 중지", command=self.stop_monitoring, width=120, state="disabled"); self.stop_button.pack(side="left", padx=10)
        ctk.CTkFrame(control_frame, fg_color="transparent").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(control_frame, text="설정 저장", command=self.save_config, width=120).pack(side="right", padx=10)
        
        # 로그 프레임
        log_frame = ctk.CTkFrame(main_frame); log_frame.pack(pady=10, padx=10, fill="both", expand=True); log_frame.configure(border_width=1)
        ctk.CTkLabel(log_frame, text="로그", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
        self.log_text = ctk.CTkTextbox(log_frame, state='disabled', wrap='word', height=150); self.log_text.pack(fill="both", expand=True, padx=10, pady=(0,10))

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
                self.log_text.configure(state='normal'); self.log_text.insert(ctk.END, message + '\n'); self.log_text.configure(state='disabled'); self.log_text.see(ctk.END)
            
            # 파일 로그 출력
            if hasattr(self, 'logger'):
                self.logger.info(message)
        except Exception: pass
    def log_threadsafe(self, message): self.log_queue.put(message)
    def process_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log(msg)
                
                # 상태 메시지에 따른 상태 표시 업데이트
                if "백엔드: 감시 시작" in msg:
                    self.update_status("감시 중")
                elif "백엔드: 중지 신호 수신" in msg or "백엔드: 모든 작업 완료" in msg:
                    self.update_status("중지됨")
                elif "처리 시작:" in msg:
                    filename = msg.split("처리 시작:")[-1].strip()
                    self.update_status(f"처리 중: {filename}")
                elif "처리 완료:" in msg:
                    self.update_status("감시 중")
                elif "Google Docs 업데이트 완료" in msg:
                    self.update_status("업데이트 완료")
                    # 잠시 후 다시 감시 중 상태로 변경
                    self.root.after(2000, lambda: self.update_status("감시 중") if self.is_monitoring else None)
                
                # 감시 실패 메시지 감지 시 팝업 표시
                if "감시 실패" in msg or ("오류" in msg and "Google" in msg):
                    try:
                        messagebox.showerror("감시 실패", msg, parent=self.root)
                        self.update_status("오류 발생")
                    except Exception:
                        pass
        except queue.Empty:
            pass
        except Exception:
            pass
        finally:
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.after(100, self.process_log_queue)
    def save_config(self):
        config_data = { "watch_folder": self.watch_folder.get(), "docs_input": self.docs_input.get() }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(config_data, f, indent=4, ensure_ascii=False)
            self.log("설정 저장 완료.")
        except Exception as e: messagebox.showerror("저장 오류", f"설정 저장 실패:\n{e}", parent=self.root); self.log(f"오류: 설정 저장 실패 - {e}")
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: config_data = json.load(f)
                self.watch_folder.set(config_data.get("watch_folder", "")); self.docs_input.set(config_data.get("docs_input", ""))
                self.log("저장된 설정 로드 완료.")
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
            error_message = "\n".join([f"• {error}" for error in validation_errors])
            messagebox.showerror("입력 오류", f"다음 문제를 해결해주세요:\n\n{error_message}", parent=self.root)
            self.update_status("준비")
            return
        
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
            "docs_id": docs_id 
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
                           if isinstance(widget, (ctk.CTkEntry, ctk.CTkButton)): widget.configure(state="disabled")
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

    def on_closing(self): # 창 닫기(X) 버튼 클릭 시 호출됨
        """ 창의 X 버튼 클릭 시 창 숨기기 """
        self.hide_window()


# --- 애플리케이션 실행 ---
if __name__ == "__main__":
    root = ctk.CTk()
    app = MessengerDocsApp(root)
    root.mainloop()