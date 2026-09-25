import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from infra.postgresql.connection import _build_database_url


class DatabaseUrlTest(unittest.TestCase):
    def test_aliases_for_database_and_user(self):
        values = {
            "DB_HOST": "127.0.0.1",
            "DB_PORT": "5432",
            "DB_DATABASE": "rsa_test",
            "DB_USERNAME": "reader",
            "DB_PASSWORD": "example",
        }
        with patch.dict(os.environ, values):
            with patch.dict(os.environ, {"DB_NAME": "", "DB_USER": ""}):
                url = _build_database_url()
        self.assertEqual(url.database, "rsa_test")
        self.assertEqual(url.username, "reader")
        self.assertEqual(url.host, "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
