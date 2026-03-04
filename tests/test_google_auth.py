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


if __name__ == "__main__":
    unittest.main()
