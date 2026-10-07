import sqlite3

import pytest

from scripts.database_maintenance import backup_database, restore_database, verify_database


def make_database(path, value):
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE sample (value TEXT)")
    connection.execute("INSERT INTO sample VALUES (?)", (value,))
    connection.commit()
    connection.close()


def test_backup_verifies_and_restores_without_losing_database_content(tmp_path):
    database = tmp_path / "live.db"
    make_database(database, "before")

    backup = backup_database(database, tmp_path / "backups")
    assert verify_database(backup)
    make_database_result = sqlite3.connect(backup).execute("SELECT value FROM sample").fetchone()[0]
    assert make_database_result == "before"

    restore_database(backup, database)
    restored_value = sqlite3.connect(database).execute("SELECT value FROM sample").fetchone()[0]
    assert restored_value == "before"


def test_restore_rejects_corrupt_backup_without_replacing_destination(tmp_path):
    database = tmp_path / "live.db"
    make_database(database, "keep")
    corrupt_backup = tmp_path / "corrupt.db"
    corrupt_backup.write_bytes(b"not a sqlite database")

    with pytest.raises(sqlite3.DatabaseError):
        restore_database(corrupt_backup, database)
    current_value = sqlite3.connect(database).execute("SELECT value FROM sample").fetchone()[0]
    assert current_value == "keep"
