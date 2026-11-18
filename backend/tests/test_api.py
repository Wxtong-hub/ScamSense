from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.db import Training, Turn, engine_for, now
from app.main import TTL, create_app
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@pytest.fixture
def api(tmp_path, monkeypatch):
    url = "sqlite:///" + (tmp_path / "training.sqlite3").as_posix()
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    with TestClient(create_app(url)) as client:
        yield client, url


def open_session(client):
    res = client.post("/api/v1/sessions", json={})
    assert res.status_code == 201
    s = res.json()
    return "/api/v1/sessions/" + s["session_id"], {
        "Authorization": "Bearer " + s["session_token"]
    }


def message(value):
    return {"client_message_id": str(uuid4()), "text": value}


def test_full_flow_and_boundaries(api):
    c, url = api
    assert c.get("/healthz").json()["status"] == "ok"
    root, auth = open_session(c)
    _, other = open_session(c)
    assert c.get(root).status_code == 401
    assert c.get(root, headers=other).status_code == 404
    assert "session_token" not in c.get(root, headers=auth).json()
    assert c.get(root + "/report", headers=auth).status_code == 409
    path = root + "/roles/wang/messages"
    msg = message("你亲自核实过吗？")
    response = c.post(path, headers=auth, json=msg)
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [line for line in response.text.splitlines() if line.startswith("event:")]
    assert (
        events[0] == "event: start"
        and events[-1] == "event: complete"
        and events.count("event: delta") > 1
    )
    assert c.post(path, headers=auth, json=msg).status_code == 200
    assert (
        c.post(path, headers=auth, json={**msg, "text": "其他内容"}).status_code == 409
    )
    items = c.get(path, headers=auth).json()["items"]
    assert [m["sender"] for m in items] == ["user", "role"]
    assert c.get(root + "/roles/lin/messages", headers=auth).json()["items"] == []
    assert (
        c.post(root + "/messages/" + items[1]["id"] + "/seen", headers=auth).status_code
        == 204
    )
    assert (
        c.post(
            path, headers=auth, json=message("群里只是转述，不能证明授权。")
        ).status_code
        == 200
    )
    decision = {
        "request_id": str(uuid4()),
        "expected_version": 0,
        "choice": "defer",
        "reason": "群消息缺少授权证据。",
    }
    assert c.post(root + "/decision", headers=auth, json=decision).status_code == 409
    decision["expected_version"] = c.get(root, headers=auth).json()["version"]
    finished = c.post(root + "/decision", headers=auth, json=decision)
    assert finished.json()["report_ready"] and finished.json()["phase"] == "S6"
    assert (
        c.post(root + "/decision", headers=auth, json=decision).json()
        == finished.json()
    )
    assert c.post(path, headers=auth, json=message("再开一条消息")).status_code == 409
    report = c.get(root + "/report", headers=auth).json()
    assert report["dimensions"][1]["evidence"][0]["message_id"] == items[0]["id"]
    assert c.get(root + "/report", headers=other).status_code == 404
    with TestClient(create_app(url)) as restarted:
        assert restarted.get(root + "/report", headers=auth).json() == report


def test_rejected_input_not_recorded_and_early_finish(api):
    c, _ = api
    root, auth = open_session(c)
    path = root + "/roles/chen/messages"
    for text in ["contact@example.invalid", " ", "a" * 501]:
        response = c.post(path, headers=auth, json=message(text))
        assert response.status_code == 422 and "example.invalid" not in response.text
    assert not c.get(path, headers=auth).json()["items"]
    body = {"request_id": str(uuid4()), "expected_version": 0}
    assert (
        c.post(
            root + "/decision",
            headers=auth,
            json={**body, "choice": "decline", "reason": "contact@example.invalid"},
        ).status_code
        == 422
    )
    assert (
        c.post(root + "/end", headers=auth, json=body).json()["status"] == "ended_early"
    )
    report = c.get(root + "/report", headers=auth).json()
    assert report["decision"] is None and report["total"] is None


def test_concurrent_replay_only_persists_one_turn(api):
    c, _ = api
    root, auth = open_session(c)
    path = root + "/roles/lin/messages"
    payload = message("这个岗位的流程是什么？")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: c.post(path, headers=auth, json=payload).status_code, range(2)
            )
        )
    assert results == [200, 200]
    assert len(c.get(path, headers=auth).json()["items"]) == 2
    assert c.get(root, headers=auth).json()["version"] == 1


def test_expiry_and_cascade_cleanup(api):
    c, url = api
    root, auth = open_session(c)
    assert (
        c.post(
            root + "/roles/lin/messages", headers=auth, json=message("你好")
        ).status_code
        == 200
    )
    engine = engine_for(url)
    with Session(engine) as db:
        db.get(Training, root.split("/")[-1]).created_at = now() - TTL - 1
        db.commit()
    assert c.get(root, headers=auth).status_code == 404
    open_session(c)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Turn)) == 0
    engine.dispose()
