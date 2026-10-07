from io import BytesIO

from openpyxl import load_workbook

from app import get_db_connection


def test_notes_persist_and_export_as_class_roster(room_client, post_headers):
    client, room_code, _teacher_id = room_client
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO room_students (room_code, student_id, name, roll_number) VALUES (?, ?, ?, ?)",
        (room_code, "SV001", "Nguyen An", 1),
    )
    conn.commit()
    conn.close()

    response = client.post(
        "/api/rooms/roster/note",
        json={"student_id": "SV001", "note": "Can ho tro"},
        headers=post_headers,
    )
    assert response.status_code == 200
    assert client.get("/api/rooms/gradebook").get_json()["students"][0]["note"] == "Can ho tro"

    export = client.get("/api/rooms/roster.xlsx")
    assert export.status_code == 200
    sheet = load_workbook(BytesIO(export.data), data_only=True).active
    assert [cell.value for cell in sheet[1]] == ["STT", "Họ và tên", "MSSV", "Ghi chú"]
    assert [cell.value for cell in sheet[2]] == [1, "Nguyen An", "SV001", "Can ho tro"]
    assert client.get("/api/rooms/gradebook.xlsx").status_code == 200


def test_legacy_roster_import_does_not_clear_saved_note(room_client, post_headers):
    client, room_code, _teacher_id = room_client
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO room_students (room_code, student_id, name, roll_number, note) VALUES (?, ?, ?, ?, ?)",
        (room_code, "SV001", "Nguyen An", 1, "Ghi chu giu lai"),
    )
    conn.commit()
    conn.close()

    upload = {
        "file": (
            BytesIO("STT,Họ và tên,MSSV\n1,Nguyen An,SV001\n".encode("utf-8-sig")),
            "roster.csv",
        )
    }
    response = client.post("/api/rooms/roster/import", data=upload, headers=post_headers)
    assert response.status_code == 200
    assert client.get("/api/rooms/gradebook").get_json()["students"][0]["note"] == "Ghi chu giu lai"


def test_note_update_rejects_missing_student_and_oversized_note(room_client, post_headers):
    client, _room_code, _teacher_id = room_client
    missing = client.post(
        "/api/rooms/roster/note",
        json={"student_id": "UNKNOWN", "note": "note"},
        headers=post_headers,
    )
    too_long = client.post(
        "/api/rooms/roster/note",
        json={"student_id": "UNKNOWN", "note": "x" * 1001},
        headers=post_headers,
    )
    assert missing.status_code == 404
    assert too_long.status_code == 400


def test_exam_question_pool_is_validated_and_stored(room_client, post_headers):
    client, room_code, _teacher_id = room_client
    conn = get_db_connection()
    question_ids = []
    for index in range(3):
        cursor = conn.execute(
            "INSERT INTO questions (room_code, position, text, options_json, correct) "
            "VALUES (?, ?, ?, ?, ?)",
            (room_code, index + 1, f"Question {index + 1}", '{"A":"a","B":"b","C":"c","D":"d"}', "A"),
        )
        question_ids.append(cursor.lastrowid)
    conn.commit()
    conn.close()

    created = client.post(
        "/api/rooms/exams",
        json={
            "title": "Targeted exam",
            "duration_minutes": 15,
            "question_count": 1,
            "question_ids": question_ids[:2],
        },
        headers=post_headers,
    )
    assert created.status_code == 201
    conn = get_db_connection()
    pool = conn.execute("SELECT question_pool_json FROM exams WHERE room_code = ?", (room_code,)).fetchone()
    conn.close()
    import json

    assert json.loads(pool["question_pool_json"]) == question_ids[:2]

    invalid_count = client.post(
        "/api/rooms/exams",
        json={
            "title": "Invalid exam",
            "duration_minutes": 15,
            "question_count": 3,
            "question_ids": question_ids[:2],
        },
        headers=post_headers,
    )
    assert invalid_count.status_code == 400


def test_guest_cannot_read_roster(room_client):
    _teacher_client, _room_code, _teacher_id = room_client
    from app import app

    guest = app.test_client()
    assert guest.get("/api/rooms/gradebook").status_code == 403
