#!/usr/bin/env python3
"""Create, verify, and restore SQLite backups without copying live WAL files."""

import argparse
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DATABASE = Path(
    os.environ.get("DATABASE_PATH", Path(__file__).resolve().parents[1] / "database.db")
)


def verify_database(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Database file not found: {path}")
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        connection.close()
    if result != "ok":
        raise sqlite3.DatabaseError(f"SQLite integrity check failed: {result}")
    return True


def _copy_database(source, target):
    source_connection = sqlite3.connect(
        f"file:{Path(source).resolve().as_posix()}?mode=ro", uri=True
    )
    target_connection = sqlite3.connect(str(target))
    try:
        source_connection.backup(target_connection)
        result = target_connection.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise sqlite3.DatabaseError(f"SQLite integrity check failed: {result}")
    finally:
        target_connection.close()
        source_connection.close()


def backup_database(database, backup_directory):
    database = Path(database).resolve()
    verify_database(database)
    backup_directory = Path(backup_directory)
    backup_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        backup_directory.chmod(0o700)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = backup_directory / f"{database.stem}-{timestamp}.sqlite3"
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        _copy_database(database, temporary)
        if os.name != "nt":
            temporary.chmod(0o600)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def restore_database(backup, database):
    backup = Path(backup).resolve()
    database = Path(database).resolve()
    verify_database(backup)
    if backup == database:
        raise ValueError("Backup source and database destination must be different files.")
    database.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{database.name}.restore-", suffix=".tmp", dir=database.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        _copy_database(backup, temporary)
        if os.name != "nt":
            temporary.chmod(0o600)
        temporary.replace(database)
    finally:
        temporary.unlink(missing_ok=True)
    return database


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    backup_parser = commands.add_parser("backup", help="Create a verified SQLite backup.")
    backup_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    backup_parser.add_argument("--directory", type=Path)

    verify_parser = commands.add_parser("verify", help="Verify a database or backup.")
    verify_parser.add_argument("path", type=Path)

    restore_parser = commands.add_parser("restore", help="Restore a verified backup.")
    restore_parser.add_argument("backup", type=Path)
    restore_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)

    args = parser.parse_args()
    if args.command == "backup":
        directory = args.directory or args.database.parent / "backups"
        print(backup_database(args.database, directory))
    elif args.command == "verify":
        verify_database(args.path)
        print(f"Verified: {args.path}")
    else:
        print(restore_database(args.backup, args.database))


if __name__ == "__main__":
    main()
