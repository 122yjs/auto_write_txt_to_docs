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
import hashlib
from collections import OrderedDict
from datetime import datetime # Docs 헤더에 타임스탬프 사용 위해 유지

# google_auth 모듈 임포트
try:
    from .google_auth import get_google_services
except ImportError:
    print("오류: google_auth.py 모듈을 찾을 수 없습니다. Google API 인증 기능이 작동하지 않습니다.")
    get_google_services = None

try:
    from .path_utils import (
        CACHE_FILE_STR,
        LEGACY_CACHE_FILE_STR,
        LOG_DIR_STR,
        PROCESSED_STATE_FILE_STR,
    )
except ImportError:
    project_root_fallback = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    CACHE_FILE_STR = os.path.join(project_root_fallback, "added_lines_cache.json")
    LEGACY_CACHE_FILE_STR = CACHE_FILE_STR
    LOG_DIR_STR = os.path.join(project_root_fallback, "logs")
    PROCESSED_STATE_FILE_STR = os.path.join(project_root_fallback, "processed_state.json")

# --- 전역 변수 및 상수 정의 ---
file_queue = queue.Queue()
processed_file_states = {} # 파일별 마지막 처리 상태 (성공 바이트 오프셋, 최근 시도 시간) - 메모리 기반
file_encodings = {}  # 파일별 성공한 인코딩 저장
PROCESSING_DELAY = 1.0
RETRY_DELAY = 5.0
DEFAULT_MAX_GLOBAL_CACHE_SIZE = 10000
MAX_GLOBAL_CACHE_SIZE = DEFAULT_MAX_GLOBAL_CACHE_SIZE
PROCESSED_STATE_SAVE_DEBOUNCE_SECONDS = 1.0
processed_state_lock = threading.RLock()
processed_state_dirty = False
processed_state_save_timer = None

# 로깅 설정
def setup_backend_logging():
    """백엔드 로깅 시스템 설정"""
    logger = logging.getLogger('backend_processor')
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 공통 경로 정책(path_utils)의 로그 디렉토리 사용
    logs_dir = LOG_DIR_STR
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
added_lines_cache = OrderedDict() # 최근 N개 전역 라인 캐시 (중복 방지)
LINE_CACHE_FILE = CACHE_FILE_STR
PROCESSED_STATE_FILE = PROCESSED_STATE_FILE_STR


def configure_max_global_cache_size(config, log_func=None):
    """실행 중 사용할 전역 라인 캐시 최대 크기를 설정합니다."""
    global MAX_GLOBAL_CACHE_SIZE

    requested_size = DEFAULT_MAX_GLOBAL_CACHE_SIZE
    if isinstance(config, dict):
        requested_size = config.get('max_cache_size', DEFAULT_MAX_GLOBAL_CACHE_SIZE)

    try:
        resolved_size = int(str(requested_size).strip())
        if resolved_size <= 0:
            raise ValueError
    except (TypeError, ValueError):
        resolved_size = DEFAULT_MAX_GLOBAL_CACHE_SIZE
        if log_func:
            log_func(
                f"경고: 유효하지 않은 라인 캐시 크기 설정({requested_size})입니다. 기본값 {DEFAULT_MAX_GLOBAL_CACHE_SIZE}을 사용합니다."
            )

    MAX_GLOBAL_CACHE_SIZE = resolved_size
    if log_func:
        log_func(f"백엔드: 라인 캐시 최대 크기 설정 - {MAX_GLOBAL_CACHE_SIZE}개")
    return MAX_GLOBAL_CACHE_SIZE


def build_extraction_record(filepath, extracted_lines, extracted_at=None):
    """Google Docs 기록 문자열과 GUI 미리보기용 메타데이터를 생성합니다."""
    extracted_datetime = extracted_at or datetime.now()
    extracted_time_text = extracted_datetime.strftime('%Y-%m-%d %H:%M:%S')
    file_title = os.path.basename(filepath)
    preview_lines = extracted_lines[:3]
    preview_text = "\n".join(preview_lines)

    header = (
        f"\n{'#' * 60}\n"
        f"# 본래 파일 제목: {file_title}\n"
        f"# 추출된 시간: {extracted_time_text}\n"
        f"{'#' * 60}\n"
    )

    return {
        'file_title': file_title,
        'extracted_time': extracted_time_text,
        'line_count': len(extracted_lines),
        'preview_text': preview_text,
        'full_text': "\n".join(extracted_lines),
        'document_text': header + "\n".join(extracted_lines) + "\n\n",
    }


def build_duplicate_only_record(filepath, duplicate_line_count, extracted_at=None):
    """내용이 전부 중복인 새 파일의 파일명만 기록하는 문자열을 생성합니다."""
    extracted_datetime = extracted_at or datetime.now()
    extracted_time_text = extracted_datetime.strftime('%Y-%m-%d %H:%M:%S')
    file_title = os.path.basename(filepath)
    duplicate_line_count = max(0, int(duplicate_line_count))
    summary_text = (
        f"이 파일의 내용 {duplicate_line_count}줄은 기존 기록과 모두 중복되어 "
        "본문 추가를 생략했습니다."
    )

    header = (
        f"\n{'#' * 60}\n"
        f"# 본래 파일 제목: {file_title}\n"
        f"# 추출된 시간: {extracted_time_text}\n"
        f"# 처리 결과: 중복 내용으로 본문 추가 없음\n"
        f"{'#' * 60}\n"
    )

    return {
        'file_title': file_title,
        'extracted_time': extracted_time_text,
        'line_count': duplicate_line_count,
        'preview_text': summary_text,
        'full_text': summary_text,
        'document_text': header + summary_text + "\n\n",
        'duplicate_only': True,
    }


def get_file_state(filepath):
    """파일별 처리 상태 딕셔너리를 반환합니다."""
    with processed_state_lock:
        return processed_file_states.setdefault(filepath, {})


def build_file_identity_from_stat(stat_result):
    """현재 파일의 생성/수정 시각 식별자를 정규화합니다."""
    ctime_ns = getattr(stat_result, 'st_ctime_ns', int(stat_result.st_ctime * 1_000_000_000))
    mtime_ns = getattr(stat_result, 'st_mtime_ns', int(stat_result.st_mtime * 1_000_000_000))
    return {
        'file_ctime_ns': max(0, int(ctime_ns)),
        'file_mtime_ns': max(0, int(mtime_ns)),
    }


def detect_file_reset_reason(filepath, current_identity, event_type=None):
    """이전 상태를 초기화해야 하는 파일 재생성/교체 상황인지 판정합니다."""
    with processed_state_lock:
        state = processed_file_states.get(filepath)
        if not state:
            return None

        last_byte_offset = int(state.get('last_byte_offset', state.get('size', 0)) or 0)
        seen_hashes = state.get('seen_line_hashes') or set()
        has_previous_progress = last_byte_offset > 0 or bool(seen_hashes)
        if not has_previous_progress:
            return None

        if event_type == 'created':
            return "created_event"

        stored_ctime_ns = state.get('file_ctime_ns')
        current_ctime_ns = current_identity.get('file_ctime_ns')
        try:
            stored_ctime_ns = int(stored_ctime_ns)
            current_ctime_ns = int(current_ctime_ns)
        except (TypeError, ValueError):
            return None

        if stored_ctime_ns > 0 and current_ctime_ns > 0 and stored_ctime_ns != current_ctime_ns:
            return "ctime_changed"

        return None


def hash_line_for_dedupe(line):
    """라인 문자열을 파일별 중복 판정용 해시로 변환합니다."""
    return hashlib.sha256(line.encode('utf-8')).hexdigest()


def get_file_seen_hashes(filepath):
    """파일별로 이미 처리한 라인 해시 집합을 반환합니다."""
    with processed_state_lock:
        state = get_file_state(filepath)
        seen_hashes = state.get('seen_line_hashes')

        if isinstance(seen_hashes, set):
            return seen_hashes

        if isinstance(seen_hashes, list):
            seen_hashes = {str(item) for item in seen_hashes if item}
        else:
            seen_hashes = set()

        state['seen_line_hashes'] = seen_hashes
        return seen_hashes


def remember_file_lines(filepath, lines):
    """현재 파일에서 확인한 라인들을 파일별 중복 상태에 기록합니다."""
    if not lines:
        return

    with processed_state_lock:
        seen_hashes = get_file_seen_hashes(filepath)
        for line in lines:
            seen_hashes.add(hash_line_for_dedupe(line))


def remember_global_lines(lines):
    """최근 N개 범위만 유지하는 전역 라인 캐시에 기록합니다."""
    if not lines:
        return

    for line in lines:
        normalized_line = str(line)
        if normalized_line in added_lines_cache:
            added_lines_cache.move_to_end(normalized_line)
        else:
            added_lines_cache[normalized_line] = None

    optimize_cache_size(None)


def get_last_attempt_time(filepath):
    """최근 처리 시도 시간을 반환합니다. (레거시 timestamp 키도 호환)"""
    with processed_state_lock:
        state = processed_file_states.get(filepath, {})
    return state.get('last_attempt_time', state.get('timestamp', 0))


def get_last_successful_offset(filepath):
    """마지막으로 안전하게 처리된 바이트 오프셋을 반환합니다."""
    with processed_state_lock:
        state = processed_file_states.get(filepath, {})
    return state.get('last_byte_offset', state.get('size', 0))


def mark_processing_attempt(filepath, current_time):
    """처리 시도 시각만 갱신합니다."""
    with processed_state_lock:
        state = get_file_state(filepath)
        state['last_attempt_time'] = current_time
        if 'timestamp' in state:
            del state['timestamp']


def reset_file_processing_state(filepath):
    """같은 경로의 새 파일이 감지되면 이전 처리 상태를 초기화합니다."""
    with processed_state_lock:
        state = get_file_state(filepath)
        state.pop('last_byte_offset', None)
        state.pop('size', None)
        state.pop('last_attempt_time', None)
        state.pop('retry_scheduled', None)
        state.pop('file_ctime_ns', None)
        state.pop('file_mtime_ns', None)
        state['seen_line_hashes'] = set()
        if 'timestamp' in state:
            del state['timestamp']

    if filepath in file_encodings:
        del file_encodings[filepath]


def mark_file_processed(filepath, current_byte_offset, current_time, file_identity=None):
    """파일이 안전하게 처리된 후 바이트 오프셋 상태를 확정합니다."""
    with processed_state_lock:
        state = get_file_state(filepath)
        state['last_byte_offset'] = current_byte_offset
        state['size'] = current_byte_offset
        state['last_attempt_time'] = current_time
        state['retry_scheduled'] = False
        if file_identity:
            state['file_ctime_ns'] = int(file_identity.get('file_ctime_ns', 0) or 0)
            state['file_mtime_ns'] = int(file_identity.get('file_mtime_ns', 0) or 0)
        if 'timestamp' in state:
            del state['timestamp']


def schedule_retry(filepath, log_func, reason, current_time=None):
    """Google Docs 반영 실패 시 같은 파일을 다시 큐에 넣습니다."""
    backend_logger = logging.getLogger('backend_processor')
    if current_time is None:
        current_time = time.time()

    with processed_state_lock:
        state = get_file_state(filepath)
        state['last_attempt_time'] = current_time
        if 'timestamp' in state:
            del state['timestamp']

        if state.get('retry_scheduled'):
            backend_logger.debug(f"이미 재시도 예약됨: {filepath}")
            return

        state['retry_scheduled'] = True
    log_func(f"  - Google Docs 기록 보류: {reason}. {int(RETRY_DELAY)}초 후 재시도합니다.")
    backend_logger.warning(f"Google Docs 기록 보류 - 재시도 예약: {filepath} / 사유: {reason}")
    schedule_processed_state_save(log_func)

    def requeue_file():
        with processed_state_lock:
            retry_state = processed_file_states.get(filepath)
            if not retry_state:
                return
            if not retry_state.pop('retry_scheduled', False):
                return
        file_queue.put(filepath)
        backend_logger.info(f"재시도 큐 등록 완료: {filepath}")
        schedule_processed_state_save(log_func)

    retry_timer = threading.Timer(RETRY_DELAY, requeue_file)
    retry_timer.daemon = True
    retry_timer.start()


def remove_file_processing_state(filepath):
    """파일 처리 상태와 인코딩 캐시를 함께 제거합니다."""
    with processed_state_lock:
        processed_file_states.pop(filepath, None)
    file_encodings.pop(filepath, None)


def _build_serializable_processed_state():
    """현재 처리 상태를 JSON 저장용 딕셔너리로 변환합니다."""
    with processed_state_lock:
        serializable_state = {}
        for filepath, state in processed_file_states.items():
            serializable_state[filepath] = {
                'last_byte_offset': int(state.get('last_byte_offset', state.get('size', 0))),
                'size': int(state.get('last_byte_offset', state.get('size', 0))),
                'last_attempt_time': float(state.get('last_attempt_time', state.get('timestamp', 0))),
                'seen_line_hashes': sorted(
                    str(item) for item in state.get('seen_line_hashes', set()) if item
                ),
                'file_ctime_ns': int(state.get('file_ctime_ns', 0) or 0),
                'file_mtime_ns': int(state.get('file_mtime_ns', 0) or 0),
            }
        return serializable_state


def _cancel_processed_state_save_timer_locked():
    """예약된 처리 상태 저장 타이머를 정리합니다."""
    global processed_state_save_timer

    if processed_state_save_timer is not None and hasattr(processed_state_save_timer, 'cancel'):
        try:
            processed_state_save_timer.cancel()
        except Exception:
            pass
    processed_state_save_timer = None


def _write_processed_state_snapshot(serializable_state, log_func):
    """직렬화된 처리 상태 스냅샷을 파일에 기록합니다."""
    try:
        target_dir = os.path.dirname(PROCESSED_STATE_FILE)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        with open(PROCESSED_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable_state, f, ensure_ascii=False, indent=2)
        if log_func:
            log_func(f"백엔드: 처리 상태 저장 완료 ({PROCESSED_STATE_FILE}, {len(serializable_state)}개).")
    except Exception as e:
        if log_func:
            log_func(f"오류: 처리 상태 저장 실패 - {e}")


def schedule_processed_state_save(log_func):
    """처리 상태 저장을 1초 디바운스로 예약합니다."""
    global processed_state_dirty, processed_state_save_timer

    def flush_callback():
        save_processed_state(log_func)

    with processed_state_lock:
        processed_state_dirty = True
        _cancel_processed_state_save_timer_locked()
        processed_state_save_timer = threading.Timer(PROCESSED_STATE_SAVE_DEBOUNCE_SECONDS, flush_callback)
        processed_state_save_timer.daemon = True
        processed_state_save_timer.start()

    if log_func:
        log_func(f"백엔드: 처리 상태 저장 예약 ({PROCESSED_STATE_SAVE_DEBOUNCE_SECONDS:.1f}초 후).")


def flush_processed_state_save(log_func):
    """예약된 처리 상태 저장이 있으면 즉시 강제 저장합니다."""
    global processed_state_dirty

    with processed_state_lock:
        has_pending_save = processed_state_dirty or processed_state_save_timer is not None
        if not has_pending_save:
            return False
        _cancel_processed_state_save_timer_locked()
        serializable_state = _build_serializable_processed_state()
        processed_state_dirty = False

    _write_processed_state_snapshot(serializable_state, log_func)
    return True


def load_processed_state(log_func):
    """이전 실행에서 저장된 파일 처리 상태를 로드합니다."""
    global processed_file_states, processed_state_dirty

    with processed_state_lock:
        _cancel_processed_state_save_timer_locked()

    if not os.path.exists(PROCESSED_STATE_FILE):
        log_func(f"백엔드: 처리 상태 파일({PROCESSED_STATE_FILE}) 없음. 새로 시작합니다.")
        with processed_state_lock:
            processed_file_states = {}
            processed_state_dirty = False
        return

    try:
        with open(PROCESSED_STATE_FILE, 'r', encoding='utf-8') as f:
            loaded_state = json.load(f)

        if not isinstance(loaded_state, dict):
            raise ValueError("처리 상태 파일 최상위 구조가 dict가 아닙니다.")

        sanitized_state = {}
        for filepath, state in loaded_state.items():
            if not isinstance(filepath, str) or not isinstance(state, dict):
                continue

            byte_offset = state.get('last_byte_offset', state.get('size', 0))
            last_attempt_time = state.get('last_attempt_time', state.get('timestamp', 0))

            try:
                byte_offset = max(0, int(byte_offset))
            except (TypeError, ValueError):
                byte_offset = 0

            try:
                last_attempt_time = float(last_attempt_time)
            except (TypeError, ValueError):
                last_attempt_time = 0

            sanitized_state[filepath] = {
                'last_byte_offset': byte_offset,
                'size': byte_offset,
                'last_attempt_time': last_attempt_time,
                'seen_line_hashes': {
                    str(item) for item in state.get('seen_line_hashes', []) if item
                },
                'retry_scheduled': False,
                'file_ctime_ns': int(state.get('file_ctime_ns', 0) or 0),
                'file_mtime_ns': int(state.get('file_mtime_ns', 0) or 0),
            }

        with processed_state_lock:
            processed_file_states = sanitized_state
            processed_state_dirty = False
        log_func(f"백엔드: 처리 상태({PROCESSED_STATE_FILE}) 로드됨 ({len(sanitized_state)}개).")
    except json.JSONDecodeError:
        log_func(f"경고: 처리 상태 파일({PROCESSED_STATE_FILE}) 형식이 잘못됨. 빈 상태로 시작합니다.")
        with processed_state_lock:
            processed_file_states = {}
            processed_state_dirty = False
    except Exception as e:
        log_func(f"경고: 처리 상태 로드 실패 - {e}")
        with processed_state_lock:
            processed_file_states = {}
            processed_state_dirty = False


def save_processed_state(log_func):
    """현재 파일 처리 상태를 디스크에 저장합니다."""
    global processed_state_dirty

    with processed_state_lock:
        _cancel_processed_state_save_timer_locked()
        serializable_state = _build_serializable_processed_state()
        processed_state_dirty = False

    _write_processed_state_snapshot(serializable_state, log_func)

# --- 캐시 관리 함수 (라인 캐시 전용) ---
def load_line_cache(log_func):
    """ 프로그램 시작 시 라인 캐시 파일을 로드합니다. """
    global added_lines_cache
    cache_path = LINE_CACHE_FILE
    if not os.path.exists(cache_path) and LEGACY_CACHE_FILE_STR != LINE_CACHE_FILE and os.path.exists(LEGACY_CACHE_FILE_STR):
        cache_path = LEGACY_CACHE_FILE_STR
        log_func(f"백엔드: 레거시 라인 캐시를 불러옵니다 ({cache_path}).")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                loaded_lines = json.load(f)
            added_lines_cache = OrderedDict()
            if isinstance(loaded_lines, list):
                remember_global_lines(loaded_lines)
            log_func(f"백엔드: 라인 캐시({cache_path}) 로드됨 ({len(added_lines_cache)}개).")
            
            # 캐시 크기 제한 (메모리 최적화)
            optimize_cache_size(log_func)
        except json.JSONDecodeError:
            log_func(f"경고: 라인 캐시 파일({cache_path}) 형식이 잘못됨. 빈 캐시로 시작.")
            added_lines_cache = OrderedDict()
        except Exception as e:
            log_func(f"경고: 라인 캐시 로드 실패 - {e}")
            added_lines_cache = OrderedDict()
    else:
        log_func(f"백엔드: 라인 캐시 파일({LINE_CACHE_FILE}) 없음. 새로 시작합니다.")
        added_lines_cache = OrderedDict()

def optimize_cache_size(log_func):
    """ 라인 캐시 크기가 너무 크면 일부 항목을 제거합니다. (메모리 최적화) """
    items_to_remove = len(added_lines_cache) - MAX_GLOBAL_CACHE_SIZE
    if items_to_remove <= 0:
        return

    for _ in range(items_to_remove):
        added_lines_cache.popitem(last=False)

    if log_func:
        log_func(f"백엔드: 라인 캐시 크기 최적화 - 가장 오래된 {items_to_remove}개 항목 제거됨 (현재 {len(added_lines_cache)}개)")
        try:
            with open(LINE_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(added_lines_cache.keys()), f, ensure_ascii=False)
            log_func("백엔드: 최적화된 라인 캐시 저장 완료")
        except Exception as e:
            log_func(f"경고: 최적화된 라인 캐시 저장 실패 - {e}")

def save_line_cache(log_func):
    """ 프로그램 종료 시 라인 캐시 데이터를 파일에 저장합니다. """
    log_func(f"백엔드: 라인 캐시 저장 시도 ({len(added_lines_cache)}개)...")
    try:
        with open(LINE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(added_lines_cache.keys()), f, ensure_ascii=False, indent=4)
        log_func(f"백엔드: 라인 캐시 저장 완료 ({LINE_CACHE_FILE}).")
    except Exception as e:
        log_func(f"오류: 라인 캐시 저장 실패 - {e}")

# --- 파일 읽기 헬퍼 함수 ---
def read_file_with_multiple_encodings(filepath, start_byte_offset, log_func):
    """파일을 바이트 오프셋 기준으로 읽고, 여러 인코딩으로 디코딩을 시도합니다."""
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
    
    try:
        file_size = os.path.getsize(filepath)
        if start_byte_offset >= file_size:
            return ""

        with open(filepath, 'rb') as f:
            if start_byte_offset > 0:
                f.seek(start_byte_offset)
            raw_content = f.read()
    except FileNotFoundError:
        raise
    except OSError as e:
        log_func(f"오류: 파일 '{os.path.basename(filepath)}' 바이트 읽기 실패 - {e}")
        backend_logger.error(f"파일 바이트 읽기 실패: {filepath} - {e}")
        return None

    if raw_content == b"":
        return ""

    content = None
    successful_encoding = None
    
    for enc in encodings:
        try:
            content = raw_content.decode(enc)
            backend_logger.debug(f"파일 디코딩 성공 ({enc}): {os.path.basename(filepath)}")
            successful_encoding = enc
            break # 읽기 성공 시 종료
        except UnicodeDecodeError as e:
            backend_logger.debug(f"인코딩 {enc} 실패: {e}")
            continue # 실패 시 다음 인코딩 시도
        except Exception as e:
            backend_logger.debug(f"인코딩 {enc} 처리 중 예외: {e}")
            continue
    
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
        file_queue.put((filepath, event.event_type)) # 처리 큐에 파일 경로 추가
        
    def on_created(self, event): self.process(event)
    def on_modified(self, event): self.process(event)

# --- 핵심 파일 처리 함수 (Docs 기록 버전) ---
def process_file(filepath, config, services, log_func, extracted_result_callback=None, event_type=None):
    """ 감지된 파일을 읽고, 중복 제거 후 Google Docs에 기록 """
    # 백엔드 로거 가져오기
    backend_logger = logging.getLogger('backend_processor')
    # 필요한 서비스 및 설정 가져오기
    docs_service = services.get('docs') if services else None
    docs_id = config.get('docs_id')

    try:
        # --- 1. 새로운 내용 식별 ---
        current_time = time.time()
        current_stat = os.stat(filepath)
        current_identity = build_file_identity_from_stat(current_stat)
        reset_reason = detect_file_reset_reason(filepath, current_identity, event_type=event_type)
        if reset_reason:
            reset_file_processing_state(filepath)
            file_title = os.path.basename(filepath)
            if reset_reason == "created_event":
                log_func(f"  - 같은 경로의 새 파일 생성이 감지되어 이전 처리 상태를 초기화합니다: {file_title}")
                backend_logger.info(f"같은 경로의 새 파일 생성 감지 - 처리 상태 초기화: {filepath}")
            else:
                log_func(f"  - 파일 재생성이 감지되어 이전 처리 상태를 초기화합니다: {file_title}")
                backend_logger.info(f"파일 재생성 감지 - 처리 상태 초기화: {filepath}")

        current_byte_size = current_stat.st_size
        last_byte_offset = get_last_successful_offset(filepath)
        new_raw_content = None

        if current_byte_size > last_byte_offset:
            last_processed_time = get_last_attempt_time(filepath)
            if current_time - last_processed_time < PROCESSING_DELAY:
                backend_logger.debug(f"짧은 시간 내 재처리 방지: {os.path.basename(filepath)}")
                return # 짧은 시간 내 재처리 방지

            mark_processing_attempt(filepath, current_time)
            log_func(f"처리 시작: {os.path.basename(filepath)}")
            backend_logger.info(f"파일 처리 시작: {filepath}")
            new_raw_content = read_file_with_multiple_encodings(filepath, last_byte_offset, log_func)
        elif current_byte_size < last_byte_offset:
            last_processed_time = get_last_attempt_time(filepath)
            if current_time - last_processed_time < PROCESSING_DELAY:
                backend_logger.debug(f"짧은 시간 내 재처리 방지: {os.path.basename(filepath)}")
                return # 짧은 시간 내 재처리 방지

            mark_processing_attempt(filepath, current_time)
            log_func(f"처리 시작: {os.path.basename(filepath)}")
            backend_logger.info(f"파일 처리 시작: {filepath}")
            log_func(f"  - 파일 크기 감소 감지. 전체 내용 다시 읽기...")
            backend_logger.info(f"파일 크기 감소로 인해 '{os.path.basename(filepath)}'의 처리 상태 초기화")
            reset_file_processing_state(filepath)
            last_byte_offset = 0
            new_raw_content = read_file_with_multiple_encodings(filepath, 0, log_func)
        else: # 크기 변경 없음
            return

        # 파일 읽기 실패 또는 빈 내용 처리
        if new_raw_content is None or not new_raw_content.strip():
            backend_logger.debug(f"파일 내용 없음 또는 읽기 실패: {os.path.basename(filepath)}")
            mark_file_processed(filepath, current_byte_size, current_time, file_identity=current_identity)
            schedule_processed_state_save(log_func)
            return

        new_lines = [line.strip() for line in new_raw_content.strip().split('\n') if line.strip()]
        if not new_lines:
            backend_logger.debug(f"처리할 새 라인 없음: {os.path.basename(filepath)}")
            mark_file_processed(filepath, current_byte_size, current_time, file_identity=current_identity)
            schedule_processed_state_save(log_func)
            return

        # --- 2. 라인 캐시 기반 중복 제거 ---
        global added_lines_cache
        file_seen_hashes = get_file_seen_hashes(filepath)
        should_record_duplicate_file_marker = last_byte_offset == 0 and not file_seen_hashes
        truly_new_lines = [
            line for line in new_lines
            if line not in added_lines_cache and hash_line_for_dedupe(line) not in file_seen_hashes
        ]

        if not truly_new_lines: # 추가할 새 라인 없음
            duplicate_line_count = len(new_lines)
            file_title = os.path.basename(filepath)
            if should_record_duplicate_file_marker:
                if not docs_id:
                    schedule_retry(filepath, log_func, "중복 새 파일의 파일명 기록을 위한 Google Docs 문서 ID가 없습니다", current_time)
                    return

                if not docs_service:
                    schedule_retry(filepath, log_func, "중복 새 파일의 파일명 기록을 위한 Google Docs 서비스가 준비되지 않았습니다", current_time)
                    return

                log_func(
                    f"  - 중복 내용만 감지됨. 파일명 기록 시도 (파일: {file_title}, 중복 {duplicate_line_count}줄)"
                )
                duplicate_record = build_duplicate_only_record(filepath, duplicate_line_count)
                try:
                    requests = [{'insertText': {'endOfSegmentLocation': {'segmentId': ''}, 'text': duplicate_record['document_text']}}]
                    docs_service.documents().batchUpdate(documentId=docs_id, body={'requests': requests}).execute()
                    log_func(
                        f"  - Google Docs 중복 파일명 기록 완료 (파일: {file_title}, 중복 {duplicate_line_count}줄)"
                    )
                    backend_logger.info(
                        f"Google Docs 중복 파일명 기록 완료: {file_title} / 중복 {duplicate_line_count}줄"
                    )
                    if extracted_result_callback:
                        try:
                            extracted_result_callback(duplicate_record)
                        except Exception as callback_error:
                            backend_logger.warning(f"추출 결과 콜백 처리 실패: {callback_error}")
                except HttpError as error:
                    log_func(f"오류: Docs 업데이트 API 오류 - {error}")
                    backend_logger.error(f"Docs 업데이트 API 오류: {error}")
                    schedule_retry(filepath, log_func, "중복 새 파일 파일명 기록 중 Google Docs API 오류", current_time)
                    return
                except Exception as e:
                    log_func(f"오류: Docs 업데이트 중 예외 발생 - {e}")
                    backend_logger.error(f"Docs 업데이트 중 예외 발생: {e}", exc_info=True)
                    log_func(traceback.format_exc())
                    schedule_retry(filepath, log_func, "중복 새 파일 파일명 기록 중 Google Docs 업데이트 예외", current_time)
                    return
            else:
                log_func(
                    f"  - 중복 내용만 감지되어 Google Docs 기록 생략 (파일: {file_title}, 중복 {duplicate_line_count}줄)"
                )
                backend_logger.info(
                    f"중복 내용만 감지되어 Google Docs 기록 생략: {file_title} / 중복 {duplicate_line_count}줄"
                )

            remember_global_lines(new_lines)
            remember_file_lines(filepath, new_lines)
            mark_file_processed(filepath, current_byte_size, current_time, file_identity=current_identity)
            schedule_processed_state_save(log_func)
            log_func(f"처리 완료: {os.path.basename(filepath)}")
            backend_logger.info(f"파일 처리 완료: {os.path.basename(filepath)}")
            return

        filtered_content = "\n".join(truly_new_lines) # Docs에 추가할 실제 내용

        # --- 3. Google Docs 업데이트 ---
        if not docs_id:
            schedule_retry(filepath, log_func, "Google Docs 문서 ID가 없습니다", current_time)
            return

        if not docs_service:
            schedule_retry(filepath, log_func, "Google Docs 서비스가 준비되지 않았습니다", current_time)
            return

        extraction_record = build_extraction_record(filepath, truly_new_lines)
        text_to_insert = extraction_record['document_text']

        log_func(
            f"  - Google Docs에 {len(truly_new_lines)}줄 추가 시도 (파일: {os.path.basename(filepath)}, ID: {docs_id})..."
        )
        try:
            # 단일 insertText 요청 사용
            requests = [{'insertText': {'endOfSegmentLocation': {'segmentId': ''}, 'text': text_to_insert}}]
            docs_service.documents().batchUpdate(documentId=docs_id, body={'requests': requests}).execute()
            log_func(
                f"  - Google Docs 업데이트 완료 (파일: {os.path.basename(filepath)}, {len(truly_new_lines)}줄 추가)"
            )
            backend_logger.info(
                f"Google Docs 업데이트 완료: {os.path.basename(filepath)} / {len(truly_new_lines)}줄 추가"
            )
        except HttpError as error:
            log_func(f"오류: Docs 업데이트 API 오류 - {error}")
            backend_logger.error(f"Docs 업데이트 API 오류: {error}")
            schedule_retry(filepath, log_func, "Google Docs API 오류", current_time)
            return
        except Exception as e:
            log_func(f"오류: Docs 업데이트 중 예외 발생 - {e}")
            backend_logger.error(f"Docs 업데이트 중 예외 발생: {e}", exc_info=True)
            log_func(traceback.format_exc())
            schedule_retry(filepath, log_func, "Google Docs 업데이트 예외", current_time)
            return

        # --- 4. 라인 캐시 업데이트 (Docs 업데이트 성공 시) ---
        backend_logger.debug(f"라인 캐시에 새로운 {len(truly_new_lines)}줄 추가")
        remember_global_lines(new_lines)
        remember_file_lines(filepath, new_lines)

        if extracted_result_callback:
            try:
                extracted_result_callback(extraction_record)
            except Exception as callback_error:
                backend_logger.warning(f"추출 결과 콜백 처리 실패: {callback_error}")

        # --- 5. 최종 상태 업데이트 ---
        mark_file_processed(filepath, current_byte_size, current_time, file_identity=current_identity)
        schedule_processed_state_save(log_func)
        log_func(f"처리 완료: {os.path.basename(filepath)}")
        backend_logger.info(f"파일 처리 완료: {os.path.basename(filepath)}")

    except FileNotFoundError:
         log_func(f"오류: 파일 처리 중 사라짐 - {os.path.basename(filepath)}")
         backend_logger.warning(f"파일 처리 중 사라짐: {filepath}")
         remove_file_processing_state(filepath)
         schedule_processed_state_save(log_func)
    except Exception as e:
        log_func(f"오류: {os.path.basename(filepath)} 처리 중 예기치 않은 예외 - {e}")
        backend_logger.error(f"파일 처리 중 예기치 않은 예외: {filepath} - {e}", exc_info=True)
        log_func(traceback.format_exc())


# --- 메인 모니터링 함수 ---
def run_monitoring(
    config,
    log_func_threadsafe,
    stop_event,
    extracted_result_callback=None,
    preloaded_services=None,
):
    """ 백그라운드에서 폴더 감시 및 파일 처리를 실행하는 메인 루프 """
    watch_folder = config.get('watch_folder')
    
    # 백엔드 로깅 시스템 초기화
    backend_logger = setup_backend_logging()
    backend_logger.info(f"감시 시작 - 폴더: {watch_folder}")
    
    log_func_threadsafe(f"백엔드: 감시 시작 - 폴더: {watch_folder}")
    resolved_max_cache_size = configure_max_global_cache_size(config, log_func_threadsafe)
    backend_logger.info(f"라인 캐시 최대 크기 적용 완료: {resolved_max_cache_size}")

    load_line_cache(log_func_threadsafe) # 라인 캐시 로드
    backend_logger.info(f"라인 캐시 로드 완료 - 캐시된 라인 수: {len(added_lines_cache)}")
    load_processed_state(log_func_threadsafe) # 처리 상태 로드
    backend_logger.info(f"처리 상태 로드 완료 - 추적 파일 수: {len(processed_file_states)}")

    google_services = preloaded_services
    if google_services and 'docs' in google_services:
        log_func_threadsafe("백엔드: 감시 시작 전 확인된 Google Docs 서비스를 재사용합니다.")
        backend_logger.info("사전 확인된 Google Docs 서비스 재사용")

    # Google API 서비스 로드 (Docs만 필수)
    if not google_services and get_google_services:
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
    elif not google_services: # get_google_services 함수 자체가 없는 경우 (ImportError 등)
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
                queue_item = file_queue.get_nowait()
                if isinstance(queue_item, tuple):
                    filepath, event_type = queue_item
                else:
                    filepath = queue_item
                    event_type = None
                # 파일 처리 함수 호출
                backend_logger.info(f"파일 처리 시작: {os.path.basename(filepath)}")
                process_file(
                    filepath,
                    config,
                    google_services,
                    log_func_threadsafe,
                    extracted_result_callback=extracted_result_callback,
                    event_type=event_type,
                )
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
        flush_processed_state_save(log_func_threadsafe) # 최종 처리 상태 저장
        log_func_threadsafe("백엔드: 모든 작업 완료.")
        backend_logger.info("모든 작업 완료")
