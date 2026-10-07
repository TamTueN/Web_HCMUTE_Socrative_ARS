def test_health_endpoints_and_privacy_page():
    from app import app

    test_client = app.test_client()
    live = test_client.get("/health/live")
    ready = test_client.get("/health/ready")
    privacy = test_client.get("/privacy")

    assert live.status_code == 200
    assert live.get_json() == {"status": "alive"}
    assert ready.status_code == 200
    assert ready.get_json() == {"status": "ready", "checks": {"database": "ok"}}
    assert privacy.status_code == 200
    assert "quyền riêng tư" in privacy.get_data(as_text=True).lower()


def test_public_views_and_frontend_assets_are_self_hosted():
    from app import app

    test_client = app.test_client()
    pages = [
        test_client.get("/"),
        test_client.get("/exam"),
        test_client.get("/projector/TEST01"),
        test_client.get("/privacy"),
    ]
    assert all(page.status_code == 200 for page in pages)
    for page in pages:
        html = page.get_data(as_text=True).lower()
        assert "cdn.tailwindcss.com" not in html
        assert "cdnjs.cloudflare.com" not in html
        assert "fonts.googleapis.com" not in html

    assert test_client.get("/static/css/app.css").status_code == 200
    assert test_client.get("/static/vendor/fontawesome/all.min.css").status_code == 200
    assert test_client.get("/static/vendor/chart.umd.js").status_code == 200

    css = test_client.get("/static/css/app.css").get_data(as_text=True)
    assert all(
        f"{utility} {{" in css
        for utility in (".hidden", ".bg-blue-600", ".rounded-2xl")
    )


def test_mqtt_status_does_not_expose_payload_or_student_identifiers(room_client, monkeypatch):
    from app import MQTT_STATE

    client, _room_code, _teacher_id = room_client
    monkeypatch.setitem(MQTT_STATE, "last_message_ok", False)
    monkeypatch.setitem(MQTT_STATE, "last_message_result", "student id SV-SECRET was rejected")
    monkeypatch.setitem(MQTT_STATE, "last_error", "student id SV-SECRET was rejected")
    payload = client.get("/api/teacher/mqtt-status").get_json()
    serialized = str(payload)

    assert "SV-SECRET" not in serialized
    assert "last_payload" not in payload
    assert "last_error" not in payload
    assert payload["last_message_result"] == "Bản tin gần nhất không được xử lý."
