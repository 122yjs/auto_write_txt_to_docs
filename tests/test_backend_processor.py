import json
import os
import queue
import sys
import tempfile
import types
import unittest
import logging
from unittest.mock import patch

try:
    from watchdog.observers import Observer  # noqa: F401
    from watchdog.events import FileSystemEventHandler  # noqa: F401
except ModuleNotFoundError:
    watchdog_module = types.ModuleType("watchdog")
    watchdog_observers_module = types.ModuleType("watchdog.observers")
    watchdog_events_module = types.ModuleType("watchdog.events")

    class DummyObserver:
        pass

    class DummyFileSystemEventHandler:
        pass

    watchdog_observers_module.Observer = DummyObserver
    watchdog_events_module.FileSystemEventHandler = DummyFileSystemEventHandler
    sys.modules["watchdog"] = watchdog_module
    sys.modules["watchdog.observers"] = watchdog_observers_module
    sys.modules["watchdog.events"] = watchdog_events_module

try:
    from googleapiclient.errors import HttpError  # noqa: F401
except ModuleNotFoundError:
    googleapiclient_module = types.ModuleType("googleapiclient")
    googleapiclient_errors_module = types.ModuleType("googleapiclient.errors")

    class DummyHttpError(Exception):
        pass

    googleapiclient_errors_module.HttpError = DummyHttpError
    sys.modules["googleapiclient"] = googleapiclient_module
    sys.modules["googleapiclient.errors"] = googleapiclient_errors_module

_original_google_auth_module = sys.modules.get("src.auto_write_txt_to_docs.google_auth")
if _original_google_auth_module is None:
    google_auth_stub = types.ModuleType("src.auto_write_txt_to_docs.google_auth")
    google_auth_stub.get_google_services = None
    sys.modules["src.auto_write_txt_to_docs.google_auth"] = google_auth_stub

from src.auto_write_txt_to_docs import backend_processor

if _original_google_auth_module is None:
    sys.modules.pop("src.auto_write_txt_to_docs.google_auth", None)


class FakeTimer:
    instances = []

    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.daemon = False
        self.cancelled = False
        FakeTimer.instances.append(self)

    def start(self):
        return None

    def cancel(self):
        self.cancelled = True


class FakeDocsService:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.calls = []

    def documents(self):
        return self

    def batchUpdate(self, documentId, body):
        self.calls.append((documentId, body))
        return self

    def execute(self):
        if self.should_fail:
            raise RuntimeError("테스트용 Docs 실패")
        return {}


class BackendProcessorTests(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        backend_processor.processed_file_states.clear()
        backend_processor.file_encodings.clear()
        backend_processor.added_lines_cache.clear()
        backend_processor.file_queue = queue.Queue()
        backend_processor.processed_state_dirty = False
        backend_processor.processed_state_save_timer = None
        FakeTimer.instances.clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_processed_state_file = backend_processor.PROCESSED_STATE_FILE
        self.original_line_cache_file = backend_processor.LINE_CACHE_FILE
        self.original_max_global_cache_size = backend_processor.MAX_GLOBAL_CACHE_SIZE
        backend_processor.PROCESSED_STATE_FILE = os.path.join(self.temp_dir.name, "processed_state.json")
        backend_processor.LINE_CACHE_FILE = os.path.join(self.temp_dir.name, "added_lines_cache.json")
        self.timer_patcher = patch.object(backend_processor.threading, "Timer", FakeTimer)
        self.timer_patcher.start()

    def tearDown(self):
        self.timer_patcher.stop()
        backend_processor.PROCESSED_STATE_FILE = self.original_processed_state_file
        backend_processor.LINE_CACHE_FILE = self.original_line_cache_file
        backend_processor.MAX_GLOBAL_CACHE_SIZE = self.original_max_global_cache_size
        backend_processor.processed_state_dirty = False
        backend_processor.processed_state_save_timer = None
        logging.disable(logging.NOTSET)

    def create_temp_file(self, content):
        temp_file = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", newline="")
        self.addCleanup(lambda: os.path.exists(temp_file.name) and os.remove(temp_file.name))
        temp_file.write(content)
        temp_file.close()
        return temp_file.name

    def create_named_file(self, filename, content):
        filepath = os.path.join(self.temp_dir.name, filename)
        with open(filepath, "w", encoding="utf-8", newline="") as target_file:
            target_file.write(content)
        return filepath

    def create_temp_bytes_file(self, raw_content):
        temp_file = tempfile.NamedTemporaryFile("wb", delete=False)
        self.addCleanup(lambda: os.path.exists(temp_file.name) and os.remove(temp_file.name))
        temp_file.write(raw_content)
        temp_file.close()
        return temp_file.name

    def test_read_file_with_multiple_encodings_uses_utf8_byte_offset(self):
        initial = "가나다\n"
        appended = "라마바\n"
        filepath = self.create_temp_file(initial + appended)

        content = backend_processor.read_file_with_multiple_encodings(
            filepath,
            len(initial.encode("utf-8")),
            lambda _message: None,
        )

        self.assertEqual(content, appended)
        self.assertEqual(backend_processor.file_encodings[filepath], "utf-8")

    def test_read_file_with_multiple_encodings_uses_cp949_byte_offset(self):
        initial = "한글첫줄\n"
        appended = "한글둘째줄\n"
        filepath = self.create_temp_bytes_file((initial + appended).encode("cp949"))

        content = backend_processor.read_file_with_multiple_encodings(
            filepath,
            len(initial.encode("cp949")),
            lambda _message: None,
        )

        self.assertEqual(content, appended)
        self.assertEqual(backend_processor.file_encodings[filepath], "cp949")

    def test_global_cache_keeps_only_recent_n_lines(self):
        backend_processor.MAX_GLOBAL_CACHE_SIZE = 3

        backend_processor.remember_global_lines(["첫줄", "둘줄", "셋줄"])
        backend_processor.remember_global_lines(["둘줄", "넷줄"])

        self.assertEqual(
            list(backend_processor.added_lines_cache.keys()),
            ["셋줄", "둘줄", "넷줄"],
        )

        backend_processor.save_line_cache(lambda _message: None)
        backend_processor.added_lines_cache.clear()
        backend_processor.load_line_cache(lambda _message: None)

        self.assertEqual(
            list(backend_processor.added_lines_cache.keys()),
            ["셋줄", "둘줄", "넷줄"],
        )

    def test_configure_max_global_cache_size_applies_configured_limit_before_cache_load(self):
        logs = []
        with open(backend_processor.LINE_CACHE_FILE, "w", encoding="utf-8") as cache_file:
            cache_file.write('["첫줄", "둘줄", "셋줄", "넷줄"]')

        configured_size = backend_processor.configure_max_global_cache_size(
            {"max_cache_size": "2"},
            logs.append,
        )
        backend_processor.load_line_cache(logs.append)

        self.assertEqual(configured_size, 2)
        self.assertEqual(backend_processor.MAX_GLOBAL_CACHE_SIZE, 2)
        self.assertEqual(
            list(backend_processor.added_lines_cache.keys()),
            ["셋줄", "넷줄"],
        )
        self.assertTrue(any("라인 캐시 최대 크기 설정 - 2개" in message for message in logs))

    def test_configure_max_global_cache_size_uses_default_for_invalid_values(self):
        logs = []

        configured_size = backend_processor.configure_max_global_cache_size(
            {"max_cache_size": "-10"},
            logs.append,
        )

        self.assertEqual(configured_size, backend_processor.DEFAULT_MAX_GLOBAL_CACHE_SIZE)
        self.assertEqual(backend_processor.MAX_GLOBAL_CACHE_SIZE, backend_processor.DEFAULT_MAX_GLOBAL_CACHE_SIZE)
        self.assertTrue(any("기본값" in message for message in logs))

    def test_build_extraction_record_includes_file_title_and_extracted_time(self):
        filepath = os.path.join(self.temp_dir.name, "대화로그.txt")

        record = backend_processor.build_extraction_record(
            filepath,
            ["첫 줄", "둘째 줄", "셋째 줄", "넷째 줄"],
            extracted_at=backend_processor.datetime(2026, 3, 5, 9, 30, 15),
        )

        self.assertEqual(record["file_title"], "대화로그.txt")
        self.assertEqual(record["extracted_time"], "2026-03-05 09:30:15")
        self.assertIn("본래 파일 제목: 대화로그.txt", record["document_text"])
        self.assertIn("추출된 시간: 2026-03-05 09:30:15", record["document_text"])
        self.assertEqual(record["preview_text"], "첫 줄\n둘째 줄\n셋째 줄")

    def test_build_duplicate_only_record_mentions_file_title_and_skip_reason(self):
        filepath = os.path.join(self.temp_dir.name, "중복로그.txt")

        record = backend_processor.build_duplicate_only_record(
            filepath,
            7,
            extracted_at=backend_processor.datetime(2026, 3, 10, 21, 30, 0),
        )

        self.assertEqual(record["file_title"], "중복로그.txt")
        self.assertEqual(record["line_count"], 7)
        self.assertTrue(record["duplicate_only"])
        self.assertIn("중복 내용으로 본문 추가 없음", record["document_text"])
        self.assertIn("내용 7줄은 기존 기록과 모두 중복", record["preview_text"])

    def test_missing_docs_service_keeps_size_and_schedules_retry(self):
        filepath = self.create_temp_file("새 데이터 한 줄\n")
        logs = []

        backend_processor.process_file(filepath, {"docs_id": "doc-1"}, None, logs.append)

        state = backend_processor.processed_file_states[filepath]
        self.assertNotIn("size", state)
        self.assertNotIn("last_byte_offset", state)
        self.assertTrue(state.get("retry_scheduled"))
        self.assertEqual(len(FakeTimer.instances), 2)
        self.assertIn(
            backend_processor.PROCESSED_STATE_SAVE_DEBOUNCE_SECONDS,
            [timer.interval for timer in FakeTimer.instances],
        )
        self.assertIn(
            backend_processor.RETRY_DELAY,
            [timer.interval for timer in FakeTimer.instances],
        )
        self.assertTrue(any("Google Docs 기록 보류" in message for message in logs))

        retry_timer = next(timer for timer in FakeTimer.instances if timer.interval == backend_processor.RETRY_DELAY)
        retry_timer.callback()
        self.assertEqual(backend_processor.file_queue.get_nowait(), filepath)
        self.assertNotIn("retry_scheduled", backend_processor.processed_file_states[filepath])

    def test_docs_update_exception_keeps_size_and_schedules_retry(self):
        filepath = self.create_temp_file("예외 발생 테스트\n")
        logs = []
        fake_docs_service = FakeDocsService(should_fail=True)

        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-2"},
            {"docs": fake_docs_service},
            logs.append,
        )

        state = backend_processor.processed_file_states[filepath]
        self.assertNotIn("size", state)
        self.assertNotIn("last_byte_offset", state)
        self.assertTrue(state.get("retry_scheduled"))
        self.assertEqual(len(FakeTimer.instances), 2)
        self.assertEqual(len(fake_docs_service.calls), 1)
        self.assertTrue(any("Docs 업데이트 중 예외 발생" in message for message in logs))

    def test_successful_docs_update_marks_file_processed(self):
        filepath = self.create_temp_file("정상 처리 테스트\n")
        logs = []
        fake_docs_service = FakeDocsService()
        extracted_results = []

        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-3"},
            {"docs": fake_docs_service},
            logs.append,
            extracted_result_callback=extracted_results.append,
        )

        state = backend_processor.processed_file_states[filepath]
        self.assertEqual(state["last_byte_offset"], os.path.getsize(filepath))
        self.assertEqual(state["size"], os.path.getsize(filepath))
        self.assertFalse(state.get("retry_scheduled"))
        self.assertIn(
            backend_processor.hash_line_for_dedupe("정상 처리 테스트"),
            state["seen_line_hashes"],
        )
        self.assertIn("정상 처리 테스트", backend_processor.added_lines_cache)
        self.assertEqual(len(fake_docs_service.calls), 1)
        inserted_text = fake_docs_service.calls[0][1]["requests"][0]["insertText"]["text"]
        self.assertIn("본래 파일 제목:", inserted_text)
        self.assertIn("추출된 시간:", inserted_text)
        self.assertEqual(len(extracted_results), 1)
        self.assertEqual(extracted_results[0]["file_title"], os.path.basename(filepath))
        self.assertIn("정상 처리 테스트", extracted_results[0]["full_text"])
        self.assertTrue(any("처리 완료" in message for message in logs))

    def test_duplicate_only_new_file_records_filename_to_docs(self):
        filepath = self.create_temp_file("중복 줄\n")
        logs = []
        fake_docs_service = FakeDocsService()
        extracted_results = []

        backend_processor.remember_global_lines(["중복 줄"])
        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-duplicate"},
            {"docs": fake_docs_service},
            logs.append,
            extracted_result_callback=extracted_results.append,
        )

        self.assertEqual(len(fake_docs_service.calls), 1)
        inserted_text = fake_docs_service.calls[0][1]["requests"][0]["insertText"]["text"]
        self.assertIn("본래 파일 제목:", inserted_text)
        self.assertIn("중복 내용으로 본문 추가 없음", inserted_text)
        self.assertTrue(any("파일명 기록 시도" in message for message in logs))
        self.assertTrue(any("중복 파일명 기록 완료" in message for message in logs))
        self.assertEqual(len(extracted_results), 1)
        self.assertTrue(extracted_results[0]["duplicate_only"])

    def test_duplicate_only_existing_file_skips_docs_and_logs_reason(self):
        filepath = self.create_temp_file("같은 줄\n")
        first_docs_service = FakeDocsService()

        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-5"},
            {"docs": first_docs_service},
            lambda _message: None,
        )

        backend_processor.processed_file_states[filepath]["last_attempt_time"] = 0
        with open(filepath, "a", encoding="utf-8", newline="") as source_file:
            source_file.write("같은 줄\n")

        logs = []
        second_docs_service = FakeDocsService()
        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-5"},
            {"docs": second_docs_service},
            logs.append,
        )

        self.assertEqual(len(second_docs_service.calls), 0)
        self.assertTrue(any("중복 내용만 감지되어 Google Docs 기록 생략" in message for message in logs))
        self.assertTrue(any("처리 완료" in message for message in logs))

    def test_created_event_resets_existing_state_and_records_duplicate_filename(self):
        filepath = self.create_named_file("같은이름.txt", "중복 줄\n")
        first_docs_service = FakeDocsService()

        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-reset"},
            {"docs": first_docs_service},
            lambda _message: None,
        )

        backend_processor.remember_global_lines(["중복 줄"])
        with open(filepath, "w", encoding="utf-8", newline="") as rewritten_file:
            rewritten_file.write("중복 줄\n")

        logs = []
        second_docs_service = FakeDocsService()
        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-reset"},
            {"docs": second_docs_service},
            logs.append,
            event_type="created",
        )

        self.assertEqual(len(second_docs_service.calls), 1)
        inserted_text = second_docs_service.calls[0][1]["requests"][0]["insertText"]["text"]
        self.assertIn("중복 내용으로 본문 추가 없음", inserted_text)
        self.assertTrue(any("처리 상태를 초기화합니다" in message for message in logs))
        self.assertTrue(any("중복 파일명 기록 완료" in message for message in logs))

    def test_empty_created_file_does_not_consume_attempt_before_real_write(self):
        filepath = self.create_named_file("초기빈파일.txt", "")
        logs = []
        docs_service = FakeDocsService()

        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-empty"},
            {"docs": docs_service},
            logs.append,
            event_type="created",
        )

        self.assertNotIn(filepath, backend_processor.processed_file_states)

        with open(filepath, "w", encoding="utf-8", newline="") as target_file:
            target_file.write("이제 내용이 생김\n")

        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-empty"},
            {"docs": docs_service},
            logs.append,
            event_type="modified",
        )

        self.assertEqual(len(docs_service.calls), 1)
        self.assertTrue(any("처리 완료" in message for message in logs))

    def test_save_and_load_processed_state_persists_last_byte_offset(self):
        filepath = self.create_temp_file("상태 저장 테스트\n")
        backend_processor.processed_file_states[filepath] = {
            "last_byte_offset": 24,
            "size": 24,
            "last_attempt_time": 1234.5,
            "seen_line_hashes": {"hash-a", "hash-b"},
            "retry_scheduled": True,
            "file_ctime_ns": 111,
            "file_mtime_ns": 222,
        }

        backend_processor.save_processed_state(lambda _message: None)
        backend_processor.processed_file_states.clear()
        backend_processor.load_processed_state(lambda _message: None)

        state = backend_processor.processed_file_states[filepath]
        self.assertEqual(state["last_byte_offset"], 24)
        self.assertEqual(state["size"], 24)
        self.assertEqual(state["last_attempt_time"], 1234.5)
        self.assertEqual(state["seen_line_hashes"], {"hash-a", "hash-b"})
        self.assertFalse(state["retry_scheduled"])
        self.assertEqual(state["file_ctime_ns"], 111)
        self.assertEqual(state["file_mtime_ns"], 222)

    def test_file_level_dedupe_state_survives_restart(self):
        filepath = self.create_temp_file("같은 줄\n")
        first_logs = []
        first_docs_service = FakeDocsService()

        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-4"},
            {"docs": first_docs_service},
            first_logs.append,
        )

        backend_processor.save_processed_state(lambda _message: None)
        backend_processor.processed_file_states.clear()
        backend_processor.added_lines_cache.clear()
        backend_processor.load_processed_state(lambda _message: None)
        backend_processor.processed_file_states[filepath]["last_attempt_time"] = 0

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.write("같은 줄\n같은 줄\n")

        second_logs = []
        second_docs_service = FakeDocsService()
        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-4"},
            {"docs": second_docs_service},
            second_logs.append,
        )

        self.assertEqual(len(first_docs_service.calls), 1)
        self.assertEqual(len(second_docs_service.calls), 0)
        self.assertEqual(
            backend_processor.processed_file_states[filepath]["last_byte_offset"],
            os.path.getsize(filepath),
        )

    def test_schedule_processed_state_save_debounces_multiple_changes(self):
        filepath = self.create_temp_file("상태 저장 디바운스\n")
        logs = []

        backend_processor.mark_file_processed(filepath, 10, 1.0)
        backend_processor.schedule_processed_state_save(logs.append)
        backend_processor.mark_file_processed(filepath, 20, 2.0)
        backend_processor.schedule_processed_state_save(logs.append)

        self.assertEqual(len(FakeTimer.instances), 2)
        self.assertTrue(FakeTimer.instances[0].cancelled)
        self.assertFalse(os.path.exists(backend_processor.PROCESSED_STATE_FILE))

        FakeTimer.instances[-1].callback()

        with open(backend_processor.PROCESSED_STATE_FILE, "r", encoding="utf-8") as saved_file:
            saved_state = json.load(saved_file)

        self.assertEqual(saved_state[filepath]["last_byte_offset"], 20)
        self.assertFalse(backend_processor.processed_state_dirty)

    def test_flush_processed_state_save_writes_pending_state_immediately(self):
        filepath = self.create_temp_file("종료 플러시 테스트\n")
        logs = []

        backend_processor.mark_file_processed(filepath, 15, 3.0)
        backend_processor.schedule_processed_state_save(logs.append)

        self.assertTrue(backend_processor.flush_processed_state_save(logs.append))
        self.assertTrue(os.path.exists(backend_processor.PROCESSED_STATE_FILE))
        self.assertTrue(FakeTimer.instances[-1].cancelled)

        with open(backend_processor.PROCESSED_STATE_FILE, "r", encoding="utf-8") as saved_file:
            saved_state = json.load(saved_file)

        self.assertEqual(saved_state[filepath]["last_byte_offset"], 15)
        self.assertFalse(backend_processor.processed_state_dirty)


if __name__ == "__main__":
    unittest.main()
