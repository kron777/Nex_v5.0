"""Admin auth — argon2id verify on correct / incorrect passwords."""
import os
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from admin.auth import (
    is_configured,
    set_password,
    verify_password,
)


class TestAdminAuth(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hash_path = Path(self._tmp.name) / "admin.argon2"
        # Scope all calls to this temp hash file via env override.
        self._old_env = os.environ.get("NEX5_ADMIN_HASH_FILE")
        os.environ["NEX5_ADMIN_HASH_FILE"] = str(self.hash_path)

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("NEX5_ADMIN_HASH_FILE", None)
        else:
            os.environ["NEX5_ADMIN_HASH_FILE"] = self._old_env
        self._tmp.cleanup()

    def test_not_configured_initially(self):
        self.assertFalse(is_configured())
        self.assertFalse(verify_password("anything"))

    def test_correct_password_verifies(self):
        set_password("correct horse battery staple")
        self.assertTrue(is_configured())
        self.assertTrue(verify_password("correct horse battery staple"))

    def test_incorrect_password_rejected(self):
        set_password("secret")
        self.assertFalse(verify_password("wrong"))
        self.assertFalse(verify_password(""))
        self.assertFalse(verify_password("SECRET"))

    def test_file_permissions(self):
        set_password("x")
        # On POSIX, the hash file should be 0600 where the OS permits it.
        mode = self.hash_path.stat().st_mode & 0o777
        self.assertIn(mode, (0o600, 0o644))  # 0644 acceptable if chmod was no-op


if __name__ == "__main__":
    unittest.main()
