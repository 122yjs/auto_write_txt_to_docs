import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.auto_write_txt_to_docs import google_auth


class FakeCredentials:
    def __init__(self):
        self.valid = True

    def to_json(self):
        return '{"token": "test-token"}'


class FakeFlow:
    def __init__(self, credentials):
        self._credentials = credentials

    def run_local_server(self, port=0):
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
    def test_authenticate_uses_user_override_credentials_path_when_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            user_credentials_path = temp_root / "user" / "developer_credentials.json"
            bundled_credentials_path = temp_root / "assets" / "developer_credentials.json"
            token_path = temp_root / "cache" / "token.json"

            user_credentials_path.parent.mkdir(parents=True, exist_ok=True)
            bundled_credentials_path.parent.mkdir(parents=True, exist_ok=True)
            user_credentials_path.write_text('{"installed": {}}', encoding="utf-8")
            bundled_credentials_path.write_text('{"installed": {}}', encoding="utf-8")

            fake_credentials = FakeCredentials()
            captured = {}
            log_messages = []

            def fake_from_client_secrets_file(path, scopes):
                captured["path"] = path
                captured["scopes"] = list(scopes)
                return FakeFlow(fake_credentials)

            with patch.object(google_auth, "get_effective_credentials_path", return_value=user_credentials_path), \
                 patch.object(google_auth, "USER_CREDENTIALS_FILE_STR", str(user_credentials_path)), \
                 patch.object(google_auth, "BUNDLED_CREDENTIALS_FILE_STR", str(bundled_credentials_path)), \
                 patch.object(google_auth, "TOKEN_FILE_STR", str(token_path)), \
                 patch.object(google_auth.InstalledAppFlow, "from_client_secrets_file", side_effect=fake_from_client_secrets_file):
                credentials = google_auth.authenticate(log_messages.append)
                token_exists = token_path.exists()
                token_content = token_path.read_text(encoding="utf-8")

        self.assertIs(credentials, fake_credentials)
        self.assertEqual(captured["path"], str(user_credentials_path))
        self.assertEqual(captured["scopes"], google_auth.SCOPES)
        self.assertTrue(token_exists)
        self.assertIn("test-token", token_content)
        self.assertIn("백엔드: ✅ Google 계정 인증에 성공했습니다!", log_messages)

    def test_get_google_services_builds_docs_and_drive_services(self):
        fake_creds = object()
        built_services = {}

        def fake_build(service_name, version, credentials):
            built_services[service_name] = (version, credentials)
            return f"{service_name}-service"

        with patch.object(google_auth, "authenticate", return_value=fake_creds), \
             patch.object(google_auth, "build", side_effect=fake_build):
            services = google_auth.get_google_services(lambda _msg: None)

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
