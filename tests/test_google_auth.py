import json
import tempfile
import types
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

try:
    from google.auth.transport.requests import Request  # noqa: F401
    from google.oauth2.credentials import Credentials  # noqa: F401
    from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: F401
    from googleapiclient.discovery import build  # noqa: F401
    from googleapiclient.errors import HttpError  # noqa: F401
except ModuleNotFoundError:
    google_module = types.ModuleType("google")
    google_auth_module = types.ModuleType("google.auth")
    google_auth_transport_module = types.ModuleType("google.auth.transport")
    google_auth_requests_module = types.ModuleType("google.auth.transport.requests")
    google_oauth2_module = types.ModuleType("google.oauth2")
    google_oauth2_credentials_module = types.ModuleType("google.oauth2.credentials")
    google_auth_oauthlib_module = types.ModuleType("google_auth_oauthlib")
    google_auth_oauthlib_flow_module = types.ModuleType("google_auth_oauthlib.flow")
    googleapiclient_module = types.ModuleType("googleapiclient")
    googleapiclient_discovery_module = types.ModuleType("googleapiclient.discovery")
    googleapiclient_errors_module = types.ModuleType("googleapiclient.errors")

    class DummyRequest:
        pass

    class DummyCredentials:
        valid = False
        expired = False
        refresh_token = None
        client_id = None

        @classmethod
        def from_authorized_user_file(cls, *_args, **_kwargs):
            return cls()

        def refresh(self, _request):
            self.valid = True

        def to_json(self):
            return "{}"

    class DummyInstalledAppFlow:
        @classmethod
        def from_client_secrets_file(cls, *_args, **_kwargs):
            return cls()

        def run_local_server(self, port=0, timeout_seconds=None, open_browser=True):
            return DummyCredentials()

    class DummyHttpError(Exception):
        pass

    def dummy_build(*_args, **_kwargs):
        return object()

    google_auth_requests_module.Request = DummyRequest
    google_oauth2_credentials_module.Credentials = DummyCredentials
    google_auth_oauthlib_flow_module.InstalledAppFlow = DummyInstalledAppFlow
    googleapiclient_discovery_module.build = dummy_build
    googleapiclient_errors_module.HttpError = DummyHttpError

    sys.modules.setdefault("google", google_module)
    sys.modules.setdefault("google.auth", google_auth_module)
    sys.modules.setdefault("google.auth.transport", google_auth_transport_module)
    sys.modules.setdefault("google.auth.transport.requests", google_auth_requests_module)
    sys.modules.setdefault("google.oauth2", google_oauth2_module)
    sys.modules.setdefault("google.oauth2.credentials", google_oauth2_credentials_module)
    sys.modules.setdefault("google_auth_oauthlib", google_auth_oauthlib_module)
    sys.modules.setdefault("google_auth_oauthlib.flow", google_auth_oauthlib_flow_module)
    sys.modules.setdefault("googleapiclient", googleapiclient_module)
    sys.modules.setdefault("googleapiclient.discovery", googleapiclient_discovery_module)
    sys.modules.setdefault("googleapiclient.errors", googleapiclient_errors_module)

from src.auto_write_txt_to_docs import google_auth


class FakeCredentials:
    def __init__(self, *, valid=True, expired=False, refresh_token=None, client_id="expected-client"):
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.refreshed = False

    def refresh(self, _request):
        self.valid = True
        self.expired = False
        self.refreshed = True

    def to_json(self):
        return '{"token": "test-token"}'


class FakeFlow:
    def __init__(self, credentials):
        self._credentials = credentials
        self.last_kwargs = None

    def run_local_server(self, **kwargs):
        self.last_kwargs = kwargs
        return self._credentials


class FakeExecuteRequest:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class FakeDriveFilesApi:
    def __init__(self, created_payload=None, listed_payload=None):
        self.created_payload = created_payload or {}
        self.listed_payload = listed_payload or {"files": []}
        self.last_create_kwargs = None
        self.last_list_kwargs = None

    def create(self, **kwargs):
        self.last_create_kwargs = kwargs
        return FakeExecuteRequest(self.created_payload)

    def list(self, **kwargs):
        self.last_list_kwargs = kwargs
        return FakeExecuteRequest(self.listed_payload)


class FakeDriveService:
    def __init__(self, files_api):
        self._files_api = files_api

    def files(self):
        return self._files_api


class GoogleAuthTests(unittest.TestCase):
    def test_run_interactive_auth_uses_user_override_credentials_path_when_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            user_credentials_path = temp_root / "user" / "developer_credentials.json"
            bundled_credentials_path = temp_root / "assets" / "developer_credentials.json"
            token_path = temp_root / "cache" / "token.json"

            user_credentials_path.parent.mkdir(parents=True, exist_ok=True)
            bundled_credentials_path.parent.mkdir(parents=True, exist_ok=True)
            user_credentials_path.write_text('{"installed": {"client_id": "expected-client"}}', encoding="utf-8")
            bundled_credentials_path.write_text('{"installed": {"client_id": "expected-client"}}', encoding="utf-8")

            fake_credentials = FakeCredentials()
            fake_flow = FakeFlow(fake_credentials)
            log_messages = []

            with patch.object(google_auth, "get_effective_credentials_path", return_value=user_credentials_path), \
                 patch.object(google_auth, "USER_CREDENTIALS_FILE_STR", str(user_credentials_path)), \
                 patch.object(google_auth, "BUNDLED_CREDENTIALS_FILE_STR", str(bundled_credentials_path)), \
                 patch.object(google_auth, "TOKEN_FILE_STR", str(token_path)), \
                 patch.object(google_auth.InstalledAppFlow, "from_client_secrets_file", return_value=fake_flow):
                credentials = google_auth.run_interactive_auth(log_messages.append, timeout_seconds=180)

            self.assertIs(credentials, fake_credentials)
            self.assertEqual(fake_flow.last_kwargs["timeout_seconds"], 180)
            self.assertTrue(token_path.exists())
            self.assertIn("test-token", token_path.read_text(encoding="utf-8"))
            self.assertIn("백엔드: ✅ Google 계정 인증에 성공했습니다!", log_messages)

    def test_authenticate_raises_action_required_when_token_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            credentials_path = temp_root / "developer_credentials.json"
            credentials_path.write_text('{"installed": {"client_id": "expected-client"}}', encoding="utf-8")
            token_path = temp_root / "cache" / "token.json"

            with patch.object(google_auth, "get_effective_credentials_path", return_value=credentials_path), \
                 patch.object(google_auth, "TOKEN_FILE_STR", str(token_path)):
                with self.assertRaises(google_auth.GoogleAuthActionRequired) as exc_info:
                    google_auth.authenticate(lambda _msg: None)

            self.assertEqual(exc_info.exception.reason_code, "missing_token")
            self.assertIsNone(exc_info.exception.quarantined_token_path)

    def test_run_interactive_auth_raises_timeout_action_required(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            credentials_path = temp_root / "developer_credentials.json"
            credentials_path.write_text('{"installed": {"client_id": "expected-client"}}', encoding="utf-8")

            failing_flow = types.SimpleNamespace(run_local_server=lambda **_kwargs: (_ for _ in ()).throw(TimeoutError("timed out")))

            with patch.object(google_auth, "get_effective_credentials_path", return_value=credentials_path), \
                 patch.object(google_auth.InstalledAppFlow, "from_client_secrets_file", return_value=failing_flow):
                with self.assertRaises(google_auth.GoogleAuthActionRequired) as exc_info:
                    google_auth.run_interactive_auth(lambda _msg: None, timeout_seconds=180)

        self.assertEqual(exc_info.exception.reason_code, "timeout")

    def test_authenticate_refreshes_expired_token_without_browser(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            credentials_path = temp_root / "developer_credentials.json"
            credentials_path.write_text('{"installed": {"client_id": "expected-client"}}', encoding="utf-8")
            token_path = temp_root / "cache" / "token.json"
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text('{"token": "old"}', encoding="utf-8")
            fake_credentials = FakeCredentials(valid=False, expired=True, refresh_token="refresh-token")

            with patch.object(google_auth, "get_effective_credentials_path", return_value=credentials_path), \
                 patch.object(google_auth, "TOKEN_FILE_STR", str(token_path)), \
                 patch.object(google_auth.Credentials, "from_authorized_user_file", return_value=fake_credentials):
                credentials = google_auth.authenticate(lambda _msg: None)

            self.assertIs(credentials, fake_credentials)
            self.assertTrue(fake_credentials.refreshed)
            self.assertIn("test-token", token_path.read_text(encoding="utf-8"))

    def test_authenticate_quarantines_token_when_client_id_mismatches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            credentials_path = temp_root / "developer_credentials.json"
            credentials_path.write_text('{"installed": {"client_id": "expected-client"}}', encoding="utf-8")
            token_path = temp_root / "cache" / "token.json"
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text('{"token": "stale"}', encoding="utf-8")
            fake_credentials = FakeCredentials(valid=True, client_id="other-client")

            with patch.object(google_auth, "get_effective_credentials_path", return_value=credentials_path), \
                 patch.object(google_auth, "TOKEN_FILE_STR", str(token_path)), \
                 patch.object(google_auth.Credentials, "from_authorized_user_file", return_value=fake_credentials):
                with self.assertRaises(google_auth.GoogleAuthActionRequired) as exc_info:
                    google_auth.authenticate(lambda _msg: None)

            self.assertEqual(exc_info.exception.reason_code, "client_id_mismatch")
            self.assertFalse(token_path.exists())
            quarantined_path = Path(exc_info.exception.quarantined_token_path)
            self.assertTrue(quarantined_path.exists())
            self.assertEqual(quarantined_path.read_text(encoding="utf-8"), '{"token": "stale"}')

    def test_get_google_services_builds_docs_only_when_drive_not_required(self):
        fake_creds = object()
        built_services = {}

        def fake_build(service_name, version, credentials):
            built_services[service_name] = (version, credentials)
            return f"{service_name}-service"

        with patch.object(google_auth, "authenticate", return_value=fake_creds), \
             patch.object(google_auth, "build", side_effect=fake_build):
            services = google_auth.get_google_services(lambda _msg: None, require_drive=False)

        self.assertEqual(services["docs"], "docs-service")
        self.assertNotIn("drive", services)
        self.assertEqual(built_services["docs"], ("v1", fake_creds))

    def test_get_google_services_builds_docs_and_drive_services(self):
        fake_creds = object()
        built_services = {}

        def fake_build(service_name, version, credentials):
            built_services[service_name] = (version, credentials)
            return f"{service_name}-service"

        with patch.object(google_auth, "authenticate", return_value=fake_creds), \
             patch.object(google_auth, "build", side_effect=fake_build):
            services = google_auth.get_google_services(lambda _msg: None, require_drive=True)

        self.assertEqual(services["docs"], "docs-service")
        self.assertEqual(services["drive"], "drive-service")
        self.assertEqual(built_services["docs"], ("v1", fake_creds))
        self.assertEqual(built_services["drive"], ("v3", fake_creds))

    def test_create_google_document_uses_drive_service_and_returns_document(self):
        created_payload = {
            "id": "doc-123",
            "name": "테스트 문서",
            "webViewLink": "https://docs.google.com/document/d/doc-123/edit",
        }
        files_api = FakeDriveFilesApi(created_payload=created_payload)
        services = {"drive": FakeDriveService(files_api)}

        created_document = google_auth.create_google_document(
            lambda _msg: None,
            "테스트 문서",
            services=services,
        )

        self.assertEqual(created_document, created_payload)
        self.assertEqual(
            files_api.last_create_kwargs["body"]["mimeType"],
            "application/vnd.google-apps.document",
        )
        self.assertEqual(files_api.last_create_kwargs["body"]["name"], "테스트 문서")
        self.assertEqual(files_api.last_create_kwargs["fields"], "id, name, webViewLink")

    def test_list_accessible_google_documents_returns_drive_file_list(self):
        listed_payload = {
            "files": [
                {
                    "id": "doc-1",
                    "name": "문서 1",
                    "webViewLink": "https://docs.google.com/document/d/doc-1/edit",
                    "modifiedTime": "2026-03-04T10:00:00Z",
                }
            ]
        }
        files_api = FakeDriveFilesApi(listed_payload=listed_payload)
        services = {"drive": FakeDriveService(files_api)}

        documents = google_auth.list_accessible_google_documents(
            lambda _msg: None,
            services=services,
            page_size=10,
        )

        self.assertEqual(documents, listed_payload["files"])
        self.assertIn("mimeType='application/vnd.google-apps.document'", files_api.last_list_kwargs["q"])
        self.assertEqual(files_api.last_list_kwargs["pageSize"], 10)
        self.assertEqual(files_api.last_list_kwargs["orderBy"], "modifiedTime desc")


if __name__ == "__main__":
    unittest.main()
