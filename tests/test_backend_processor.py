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

google_auth_stub = types.ModuleType("src.auto_write_txt_to_docs.google_auth")
google_auth_stub.get_google_services = None
sys.modules.setdefault("src.auto_write_txt_to_docs.google_auth", google_auth_stub)

from src.auto_write_txt_to_docs import backend_processor


class FakeTimer:
    instances = []

    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.daemon = False
        FakeTimer.instances.append(self)

    def start(self):
        return None


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
        FakeTimer.instances.clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_processed_state_file = backend_processor.PROCESSED_STATE_FILE
        backend_processor.PROCESSED_STATE_FILE = os.path.join(self.temp_dir.name, "processed_state.json")

    def tearDown(self):
        backend_processor.PROCESSED_STATE_FILE = self.original_processed_state_file
        logging.disable(logging.NOTSET)

    def create_temp_file(self, content):
        temp_file = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", newline="")
        self.addCleanup(lambda: os.path.exists(temp_file.name) and os.remove(temp_file.name))
        temp_file.write(content)
        temp_file.close()
        return temp_file.name

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

    def test_missing_docs_service_keeps_size_and_schedules_retry(self):
        filepath = self.create_temp_file("새 데이터 한 줄\n")
        logs = []

        with patch.object(backend_processor.threading, "Timer", FakeTimer):
            backend_processor.process_file(filepath, {"docs_id": "doc-1"}, None, logs.append)

        state = backend_processor.processed_file_states[filepath]
        self.assertNotIn("size", state)
        self.assertNotIn("last_byte_offset", state)
        self.assertTrue(state.get("retry_scheduled"))
        self.assertEqual(len(FakeTimer.instances), 1)
        self.assertEqual(FakeTimer.instances[0].interval, backend_processor.RETRY_DELAY)
        self.assertTrue(any("Google Docs 기록 보류" in message for message in logs))

        FakeTimer.instances[0].callback()
        self.assertEqual(backend_processor.file_queue.get_nowait(), filepath)
        self.assertNotIn("retry_scheduled", backend_processor.processed_file_states[filepath])

    def test_docs_update_exception_keeps_size_and_schedules_retry(self):
        filepath = self.create_temp_file("예외 발생 테스트\n")
        logs = []
        fake_docs_service = FakeDocsService(should_fail=True)

        with patch.object(backend_processor.threading, "Timer", FakeTimer):
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
        self.assertEqual(len(FakeTimer.instances), 1)
        self.assertEqual(len(fake_docs_service.calls), 1)
        self.assertTrue(any("Docs 업데이트 중 예외 발생" in message for message in logs))

    def test_successful_docs_update_marks_file_processed(self):
        filepath = self.create_temp_file("정상 처리 테스트\n")
        logs = []
        fake_docs_service = FakeDocsService()

        backend_processor.process_file(
            filepath,
            {"docs_id": "doc-3"},
            {"docs": fake_docs_service},
            logs.append,
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
        self.assertTrue(any("처리 완료" in message for message in logs))

    def test_save_and_load_processed_state_persists_last_byte_offset(self):
        filepath = self.create_temp_file("상태 저장 테스트\n")
        backend_processor.processed_file_states[filepath] = {
            "last_byte_offset": 24,
            "size": 24,
            "last_attempt_time": 1234.5,
            "seen_line_hashes": {"hash-a", "hash-b"},
            "retry_scheduled": True,
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


if __name__ == "__main__":
    unittest.main()
