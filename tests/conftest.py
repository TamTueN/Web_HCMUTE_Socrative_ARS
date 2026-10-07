import os
import sys
import tempfile
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
_test_database_directory = tempfile.TemporaryDirectory(prefix="hcmute-ars-tests-")
os.environ["DATABASE_PATH"] = str(Path(_test_database_directory.name) / "test.db")
os.environ["APP_ENV"] = "testing"
os.environ["FLASK_SECRET_KEY"] = "test-only-secret-key-that-is-long-enough"

import app as classroom


@pytest.fixture
def room_client():
    import secrets

    suffix = secrets.token_hex(4)
    email = f"teacher-{suffix}@example.test"
    room_code = f"T{suffix.upper()}"
    conn = classroom.get_db_connection()
    cursor = conn.execute(
        "INSERT INTO teacher_accounts (name, email, password_hash) VALUES (?, ?, ?)",
        ("Test Teacher", email, classroom.generate_password_hash("test-password")),
    )
    teacher_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO rooms (room_code, password_hash, teacher_id) VALUES (?, ?, ?)",
        (room_code, "test", teacher_id),
    )
    conn.commit()
    conn.close()

    client = classroom.app.test_client()
    with client.session_transaction() as session:
        session.update({"role": "teacher", "teacher_id": teacher_id, "room_code": room_code})
    return client, room_code, teacher_id


@pytest.fixture
def post_headers():
    return {"Origin": "http://localhost"}
