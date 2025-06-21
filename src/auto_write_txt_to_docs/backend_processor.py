# backend_processor.py (Docs 기록 기능 버전)

import time
import os
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import queue
import threading
from googleapiclient.errors import HttpError
import traceback
import logging
from datetime import datetime # Docs 헤더에 타임스탬프 사용 위해 유지

# google_auth 모듈 임포트
try:
    from .google_auth import get_google_services
except ImportError:
    print("오류: google_auth.py 모듈을 찾을 수 없습니다. Google API 인증 기능이 작동하지 않습니다.")
    get_google_services = None

# --- 전역 변수 및 상수 정의 ---
file_queue = queue.Queue()
processed_file_states = {} # 파일별 마지막 처리 상태 (크기, 시간) - 메모리 기반
file_encodings = {}  # 파일별 성공한 인코딩 저장
PROCESSING_DELAY = 1.0

# 로깅 설정
def setup_backend_logging():
    """백엔드 로깅 시스템 설정"""
    logger = logging.getLogger('backend_processor')
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # logs 폴더 생성 (없는 경우)
    # PROJECT_ROOT는 파일 하단에 정의되어 있음 (CACHE_FILE 설정 시)
    # 해당 정의를 이곳에서도 활용하거나, 여기서 다시 정의할 수 있습니다.
    # 간결성을 위해 여기서 PROJECT_ROOT를 다시 정의합니다.
    project_root_for_log = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logs_dir = os.path.join(project_root_for_log, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # 파일 핸들러 설정
    log_filename = os.path.join(logs_dir, f"backend_log_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    return logger

# 라인 캐시 관련 설정
added_lines_cache = set() # Docs에 추가된 라인 저장 (중복 방지)
# 현재 파일(backend_processor.py)의 디렉토리 -> src/auto_write_txt_to_docs
# src/auto_write_txt_to_docs의 부모의 부모 디렉토리 -> 프로젝트 루트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_FILE = os.path.join(PROJECT_ROOT, "added_lines_cache.json") # 라인 캐시 파일명

# --- 캐시 관리 함수 (라인 캐시 전용) ---
def load_line_cache(log_func):
    """ 프로그램 시작 시 라인 캐시 파일을 로드합니다. """
    global added_lines_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                added_lines_cache = set(json.load(f))
            log_func(f"백엔드: 라인 캐시({CACHE_FILE}) 로드됨 ({len(added_lines_cache)}개).")
            
            # 캐시 크기 제한 (메모리 최적화)
            optimize_cache_size(log_func)
        except json.JSONDecodeError:
            log_func(f"경고: 라인 캐시 파일({CACHE_FILE}) 형식이 잘못됨. 빈 캐시로 시작.")
            added_lines_cache = set()
        except Exception as e:
            log_func(f"경고: 라인 캐시 로드 실패 - {e}")
            added_lines_cache = set()
    else:
        log_func(f"백엔드: 라인 캐시 파일({CACHE_FILE}) 없음. 새로 시작합니다.")
        added_lines_cache = set()

def optimize_cache_size(log_func):
    """ 라인 캐시 크기가 너무 크면 일부 항목을 제거합니다. (메모리 최적화) """
    global added_lines_cache
    
    # 최대 캐시 크기 설정 (라인 수)
    MAX_CACHE_SIZE = 10000
    
    if len(added_lines_cache) > MAX_CACHE_SIZE:
        # 캐시가 너무 크면 일부 항목 제거 (최대 크기의 70%만 유지)
        target_size = int(MAX_CACHE_SIZE * 0.7)
        items_to_remove = len(added_lines_cache) - target_size
        
        # 캐시는 set이므로 순서가 없음. 임의의 항목을 제거
        items_to_keep = list(added_lines_cache)[-target_size:]
        added_lines_cache = set(items_to_keep)
        
        log_func(f"백엔드: 라인 캐시 크기 최적화 - {items_to_remove}개 항목 제거됨 (현재 {len(added_lines_cache)}개)")
        
        # 최적화된 캐시 즉시 저장
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(added_lines_cache), f, ensure_ascii=False)
            log_func("백엔드: 최적화된 라인 캐시 저장 완료")
        except Exception as e:
            log_func(f"경고: 최적화된 라인 캐시 저장 실패 - {e}")

def save_line_cache(log_func):
    """ 프로그램 종료 시 라인 캐시 데이터를 파일에 저장합니다. """
    global added_lines_cache
    log_func(f"백엔드: 라인 캐시 저장 시도 ({len(added_lines_cache)}개)...")
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            # Set은 JSON 직렬화 안되므로 List로 변환
            json.dump(list(added_lines_cache), f, ensure_ascii=False, indent=4)
        log_func(f"백엔드: 라인 캐시 저장 완료 ({CACHE_FILE}).")
    except Exception as e:
        log_func(f"오류: 라인 캐시 저장 실패 - {e}")

# --- 파일 읽기 헬퍼 함수 ---
def read_file_with_multiple_encodings(filepath, start_offset, log_func):
    """ 파일을 여러 인코딩으로 읽기 시도하여 성공하는 내용을 반환 """
    backend_logger = logging.getLogger('backend_processor')
    
    # 기본 인코딩 목록
    default_encodings = ['utf-8', 'cp949', 'utf-8-sig', 'euc-kr']
    
    # 이전에 성공한 인코딩이 있으면 먼저 시도
    if filepath in file_encodings:
        known_encoding = file_encodings[filepath]
        encodings = [known_encoding] + [enc for enc in default_encodings if enc != known_encoding]
        backend_logger.debug(f"파일 '{os.path.basename(filepath)}'에 이전 성공 인코딩 사용: {known_encoding}")
    else:
        encodings = default_encodings
    
    content = None
    successful_encoding = None
    
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                if start_offset > 0:
                    file_size = os.path.getsize(filepath) # 파일 끝 넘어가지 않도록 확인
                    if start_offset >= file_size: 
                        content = ""
                        successful_encoding = enc
                        break
                    f.seek(start_offset)
                content = f.read()
            backend_logger.debug(f"파일 읽기 성공 ({enc}): {os.path.basename(filepath)}")
            successful_encoding = enc
            break # 읽기 성공 시 종료
        except (UnicodeDecodeError, FileNotFoundError, OSError, Exception) as e:
            backend_logger.debug(f"인코딩 {enc} 실패: {e}")
            continue # 실패 시 다음 인코딩 시도
    
    # 성공한 인코딩 저장
    if successful_encoding:
        file_encodings[filepath] = successful_encoding
        backend_logger.debug(f"파일 '{os.path.basename(filepath)}'의 인코딩으로 {successful_encoding} 저장됨")
    
    if content is None:
        log_func(f"오류: 파일 '{os.path.basename(filepath)}' 읽기 최종 실패.")
        backend_logger.error(f"파일 읽기 최종 실패: {filepath}")
    
    return content

# --- 파일 변경 이벤트 핸들러 ---
class FileEventHandler(FileSystemEventHandler):
    """ 설정된 필터에 맞는 파일의 생성 또는 수정 이벤트만 감지하여 큐에 넣음 """
    def __init__(self, log_func, config):
        super().__init__()
        self.log_func = log_func
        self.backend_logger = logging.getLogger('backend_processor')
        self.config = config
        
        # 파일 필터링 설정 가져오기
        self.file_extensions = [ext.strip().lower() for ext in config.get('file_extensions', '.txt').split(',') if ext.strip()]
        self.use_regex_filter = config.get('use_regex_filter', False)
        self.regex_pattern = config.get('regex_pattern', '')
        
        # 정규식 컴파일 (사용하는 경우)
        self.regex = None
        if self.use_regex_filter and self.regex_pattern:
            try:
                import re
                self.regex = re.compile(self.regex_pattern)
                self.log_func(f"정규식 패턴 컴파일 완료: {self.regex_pattern}")
            except re.error as e:
                self.log_func(f"정규식 패턴 오류: {e}. 정규식 필터가 비활성화됩니다.")
                self.backend_logger.error(f"정규식 패턴 컴파일 오류: {e}")
                self.use_regex_filter = False
        
        # 로그 출력
        if self.file_extensions:
            self.log_func(f"파일 확장자 필터 설정됨: {', '.join(self.file_extensions)}")
        else:
            self.log_func("파일 확장자 필터 없음: 모든 파일이 감시됩니다.")
            
        if self.use_regex_filter and self.regex:
            self.log_func(f"정규식 필터 활성화: {self.regex_pattern}")
    
    def is_file_match(self, filepath):
        """파일이 필터 조건에 맞는지 확인"""
        filename = os.path.basename(filepath)
        
        # 확장자 필터 확인
        if self.file_extensions:
            ext_match = any(filepath.lower().endswith(ext) for ext in self.file_extensions)
            if not ext_match:
                return False
        
        # 정규식 필터 확인
        if self.use_regex_filter and self.regex:
            if not self.regex.search(filename):
                return False
        
        return True
    
    def process(self, event):
        if event.is_directory: 
            return
            
        filepath = os.path.abspath(event.src_path)
        
        # 파일이 필터 조건에 맞는지 확인
        if not self.is_file_match(filepath):
            self.backend_logger.debug(f"필터링됨: {filepath}")
            return
            
        self.log_func(f"파일 감지됨 ({event.event_type}): {os.path.basename(filepath)}")
        self.backend_logger.info(f"파일 감지됨 ({event.event_type}): {filepath}")
        file_queue.put(filepath) # 처리 큐에 파일 경로 추가
        
    def on_created(self, event): self.process(event)
    def on_modified(self, event): self.process(event)

# --- 핵심 파일 처리 함수 (Docs 기록 버전) ---
def process_file(filepath, config, services, log_func):
    """ 감지된 파일을 읽고, 중복 제거 후 Google Docs에 기록 """
    # 백엔드 로거 가져오기
    backend_logger = logging.getLogger('backend_processor')
    
    # 처리 시작 시간 기록 및 중복 실행 방지
    current_time = time.time()
    last_processed_time = processed_file_states.get(filepath, {}).get('timestamp', 0)
    if current_time - last_processed_time < PROCESSING_DELAY:
        backend_logger.debug(f"짧은 시간 내 재처리 방지: {os.path.basename(filepath)}")
        return # 짧은 시간 내 재처리 방지

    log_func(f"처리 시작: {os.path.basename(filepath)}")
    backend_logger.info(f"파일 처리 시작: {filepath}")
    # 필요한 서비스 및 설정 가져오기
    docs_service = services.get('docs') if services else None
    docs_id = config.get('docs_id')

    try:
        # --- 1. 새로운 내용 식별 ---
        current_size = os.path.getsize(filepath)
        last_size = processed_file_states.get(filepath, {}).get('size', 0)
        new_raw_content = None

        if current_size > last_size:
            new_raw_content = read_file_with_multiple_encodings(filepath, last_size, log_func)
        elif current_size < last_size:
            log_func(f"  - 파일 크기 감소 감지. 전체 내용 다시 읽기...")
            # 파일이 다시 작성되었을 가능성이 있으므로 인코딩 정보 초기화
            if filepath in file_encodings:
                backend_logger.info(f"파일 크기 감소로 인해 '{os.path.basename(filepath)}'의 인코딩 정보 초기화")
                del file_encodings[filepath]
            new_raw_content = read_file_with_multiple_encodings(filepath, 0, log_func)
            last_size = 0 # 크기 감소 시, 다음번 비교 위해 last_size 초기화
        else: # 크기 변경 없음
            processed_file_states.setdefault(filepath, {})['timestamp'] = current_time # 시간만 갱신
            return

        # 파일 읽기 실패 또는 빈 내용 처리
        if new_raw_content is None or not new_raw_content.strip():
            backend_logger.debug(f"파일 내용 없음 또는 읽기 실패: {os.path.basename(filepath)}")
            processed_file_states.setdefault(filepath, {})['size'] = current_size
            processed_file_states[filepath]['timestamp'] = current_time
            return

        new_lines = [line.strip() for line in new_raw_content.strip().split('\n') if line.strip()]
        if not new_lines:
             backend_logger.debug(f"처리할 새 라인 없음: {os.path.basename(filepath)}")
             processed_file_states.setdefault(filepath, {})['size'] = current_size
             processed_file_states[filepath]['timestamp'] = current_time
             return

        # --- 2. 라인 캐시 기반 중복 제거 ---
        global added_lines_cache
        truly_new_lines = [line for line in new_lines if line not in added_lines_cache]

        if not truly_new_lines: # 추가할 새 라인 없음
            backend_logger.debug(f"라인 캐시 비교 후 추가할 내용 없음: {os.path.basename(filepath)}")
            processed_file_states.setdefault(filepath, {})['size'] = current_size
            processed_file_states[filepath]['timestamp'] = current_time
            return

        filtered_content = "\n".join(truly_new_lines) # Docs에 추가할 실제 내용

        # --- 3. Google Docs 업데이트 ---
        docs_update_successful = False
        if docs_id and docs_service:
            timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S')
            # 강조된 헤더 준비
            header = (f"\n{'#' * 60}\n# 새 업데이트: {timestamp_str}\n{'#' * 60}\n")
            text_to_insert = header + filtered_content + "\n\n" # 헤더 + 내용 + 공백

            log_func(f"  - Google Docs에 {len(truly_new_lines)}줄 추가 시도 (ID: {docs_id})...")
            try:
                # 단일 insertText 요청 사용
                requests = [{'insertText': {'endOfSegmentLocation': {'segmentId': ''}, 'text': text_to_insert}}]
                docs_service.documents().batchUpdate(documentId=docs_id, body={'requests': requests}).execute()
                log_func(f"  - Google Docs 업데이트 완료.")
                backend_logger.info(f"Google Docs 업데이트 완료: {len(truly_new_lines)}줄 추가")
                docs_update_successful = True
            except HttpError as error:
                log_func(f"오류: Docs 업데이트 API 오류 - {error}")
                backend_logger.error(f"Docs 업데이트 API 오류: {error}")
                # Docs 업데이트 실패 시, 라인 캐시 및 파일 상태 업데이트 안 함 (다음번 재시도 유도)
                return
            except Exception as e:
                log_func(f"오류: Docs 업데이트 중 예외 발생 - {e}")
                backend_logger.error(f"Docs 업데이트 중 예외 발생: {e}", exc_info=True)
                log_func(traceback.format_exc())
                return
        else:
             log_func("  - Google Docs 업데이트를 건너<0xEB><0x9A><0x8D>니다 (ID 또는 서비스 없음).")
             # Docs 사용 안 할 경우, 이후 처리를 계속할지 결정 필요. 여기서는 일단 종료.
             # 만약 Docs 외 다른 작업(로깅 등)이 중요하다면 여기서 return 제거.

        # --- 4. 라인 캐시 업데이트 (Docs 업데이트 성공 시) ---
        if docs_update_successful:
            backend_logger.debug(f"라인 캐시에 새로운 {len(truly_new_lines)}줄 추가")
            for line in truly_new_lines:
                added_lines_cache.add(line)

        # --- 5. 최종 상태 업데이트 ---
        processed_file_states.setdefault(filepath, {})['size'] = current_size
        processed_file_states[filepath]['timestamp'] = current_time # 처리 완료 시간
        log_func(f"처리 완료: {os.path.basename(filepath)}")
        backend_logger.info(f"파일 처리 완료: {os.path.basename(filepath)}")

    except FileNotFoundError:
         log_func(f"오류: 파일 처리 중 사라짐 - {os.path.basename(filepath)}")
         backend_logger.warning(f"파일 처리 중 사라짐: {filepath}")
         if filepath in processed_file_states: del processed_file_states[filepath] # 상태 정보 제거
         if filepath in file_encodings: del file_encodings[filepath] # 인코딩 정보 제거
    except Exception as e:
        log_func(f"오류: {os.path.basename(filepath)} 처리 중 예기치 않은 예외 - {e}")
        backend_logger.error(f"파일 처리 중 예기치 않은 예외: {filepath} - {e}", exc_info=True)
        log_func(traceback.format_exc())


# --- 메인 모니터링 함수 ---
def run_monitoring(config, log_func_threadsafe, stop_event):
    """ 백그라운드에서 폴더 감시 및 파일 처리를 실행하는 메인 루프 """
    watch_folder = config.get('watch_folder'); credentials_path = config.get('credentials_path')
    
    # 백엔드 로깅 시스템 초기화
    backend_logger = setup_backend_logging()
    backend_logger.info(f"감시 시작 - 폴더: {watch_folder}")
    
    log_func_threadsafe(f"백엔드: 감시 시작 - 폴더: {watch_folder}")

    load_line_cache(log_func_threadsafe) # 라인 캐시 로드
    backend_logger.info(f"라인 캐시 로드 완료 - 캐시된 라인 수: {len(added_lines_cache)}")

    google_services = None
    # Google API 서비스 로드 (Docs만 필수)
    if get_google_services:
        try:
            # get_google_services는 내부적으로 필요한 모든 서비스(Docs 포함)를 로드 시도할 수 있음
            # path_utils에서 자동으로 credentials 경로를 찾아서 사용
            backend_logger.info("Google API 서비스 로드 시도")
            google_services = get_google_services(log_func_threadsafe)
            if google_services and 'docs' in google_services:
                log_func_threadsafe("백엔드: Google Docs 서비스 로드 완료.")
                backend_logger.info("Google Docs 서비스 로드 완료.")
            elif google_services: # Docs 서비스는 있지만 'docs' 키가 없는 경우 (일반적으로 발생하지 않음)
                 log_func_threadsafe("경고: Google Docs 특정 서비스 로드 실패. API 설정 확인 필요.")
                 backend_logger.warning("Google Docs 특정 서비스 로드 실패 (docs 키 부재).")
                 # Docs 사용 불가이므로, 감시를 계속할지 여부 결정 필요. 여기서는 일단 진행.
            else: # google_services 자체가 None인 경우 (인증 실패 등)
                error_msg = "오류: Google 서비스 로드 실패. Google API 인증에 문제가 있을 수 있습니다. "\
                            "'developer_credentials.json' 파일이 올바르지 않거나, 네트워크 연결, 또는 Google 계정 권한을 확인해주세요."
                log_func_threadsafe(error_msg)
                backend_logger.error("Google 서비스 로드 실패 (google_services is None). 인증 또는 네트워크 문제 가능성.")
                # Google 서비스 없이 파일 감시만 계속할 수도 있지만, 이 프로그램의 핵심 기능이므로
                # 사용자에게 명확히 알리고, 여기서는 Docs 업데이트 없이 감시만 진행될 수 있음을 인지시켜야 함.
                # 또는, 여기서 감시를 시작하지 않고 종료할 수도 있습니다.
                # 현재는 Docs 서비스 없이 계속 진행하도록 되어있으므로, process_file 함수에서 docs_service가 None일 때의 처리가 중요합니다.
        except Exception as e: # get_google_services() 호출 중 발생한 예외
            error_msg = f"오류: Google 서비스 초기화 중 예외 발생 - {e}. "\
                        "인증 설정, 네트워크 연결 또는 API 할당량을 확인하세요."
            log_func_threadsafe(error_msg)
            backend_logger.error(f"Google 서비스 초기화 중 예외: {e}", exc_info=True)
    else: # get_google_services 함수 자체가 없는 경우 (ImportError 등)
        log_func_threadsafe("경고: Google 연동 기능 비활성화됨 (google_auth 모듈 로드 실패).")
        backend_logger.warning("Google 연동 기능 비활성화 (google_auth 모듈 로드 실패).")

    # Docs 서비스가 준비되지 않았다면, 사용자에게 알리고 처리를 어떻게 할지 명확히 해야 합니다.
    # 예를 들어, Docs ID가 설정되어 있는데 Docs 서비스가 없다면 경고를 더 강하게 표시할 수 있습니다.
    if config.get('docs_id') and (not google_services or 'docs' not in google_services):
        log_func_threadsafe("경고: Google Docs ID가 설정되어 있으나, Docs 서비스에 연결할 수 없습니다. 기록이 비활성화됩니다.")
        backend_logger.warning("Docs ID는 있으나 Docs 서비스 연결 불가. 기록 비활성화.")


    # 파일 필터링 설정 로그
    if 'file_extensions' in config:
        log_func_threadsafe(f"백엔드: 파일 확장자 필터 - {config.get('file_extensions')}")
    if config.get('use_regex_filter') and config.get('regex_pattern'):
        log_func_threadsafe(f"백엔드: 정규식 필터 - {config.get('regex_pattern')}")
    
    # 이벤트 핸들러 생성 (필터링 설정 포함)
    event_handler = FileEventHandler(log_func_threadsafe, config)
    observer = Observer()
    try:
        observer.schedule(event_handler, watch_folder, recursive=False); observer.start()
        log_func_threadsafe("백엔드: 파일 시스템 감시자 시작됨.")
    except Exception as e:
        log_func_threadsafe(f"오류: 감시자 시작 실패 - {e}")
        save_line_cache(log_func_threadsafe) # 종료 전 캐시 저장
        return

    # --- 메인 루프 ---
    try:
        while not stop_event.is_set():
            try:
                filepath = file_queue.get_nowait()
                # 파일 처리 함수 호출
                backend_logger.info(f"파일 처리 시작: {os.path.basename(filepath)}")
                process_file(filepath, config, google_services, log_func_threadsafe)
                backend_logger.info(f"파일 처리 완료: {os.path.basename(filepath)}")
                file_queue.task_done() # 큐 작업 완료 알림
            except queue.Empty:
                stop_event.wait(timeout=0.5) # 큐 비었으면 CPU 사용 줄이며 대기
            except Exception as e: # 개별 파일 처리 오류가 루프 중단시키지 않도록
                 log_func_threadsafe(f"오류: 파일 처리 루프 내 예외 - {e}\n{traceback.format_exc()}")
                 backend_logger.error(f"파일 처리 루프 내 예외: {e}", exc_info=True)
        log_func_threadsafe("백엔드: 중지 신호 수신됨.")
        backend_logger.info("중지 신호 수신됨")
    except Exception as e: # 루프 자체의 치명적 오류 (예: Observer 오류)
        log_func_threadsafe(f"오류: 메인 모니터링 루프 예외 - {e}\n{traceback.format_exc()}")
        backend_logger.error(f"메인 모니터링 루프 예외: {e}", exc_info=True)
    finally:
        # --- 종료 처리 ---
        log_func_threadsafe("백엔드: 종료 처리 시작...")
        backend_logger.info("종료 처리 시작")
        observer.stop()
        try: observer.join(timeout=2) # Observer 스레드 종료 대기 (선택적)
        except Exception as e: 
            log_func_threadsafe(f"경고: Observer 스레드 join 중 오류 - {e}")
            backend_logger.warning(f"Observer 스레드 join 중 오류: {e}")
        log_func_threadsafe("백엔드: 감시자 종료 완료.")
        backend_logger.info("감시자 종료 완료")
        save_line_cache(log_func_threadsafe) # 최종 라인 캐시 저장
        log_func_threadsafe("백엔드: 모든 작업 완료.")
        backend_logger.info("모든 작업 완료")