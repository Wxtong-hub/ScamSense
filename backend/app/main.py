import asyncio
import hashlib
import hmac
import json
import os
import secrets
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from app.db import Training, Turn, database_url, engine_for, now
from app.services.training import ROLES, analyze, is_sensitive, make_report
from fastapi import FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

PREFIX = "/api/v1/sessions"
TTL = 7 * 24 * 3600
Auth = Annotated[str | None, Header(alias="Authorization")]


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Chat(Input):
    client_message_id: UUID
    text: str = Field(min_length=1, max_length=500)


class End(Input):
    request_id: UUID
    expected_version: int = Field(ge=0)


class Decision(End):
    choice: Literal["continue", "decline", "defer", "verify_more"]
    reason: str = Field(default="", max_length=500)


def date_string(timestamp):
    return datetime.fromtimestamp(timestamp, UTC).isoformat()


def public(s):
    return {
        "session_id": s.id,
        "phase": s.phase,
        "status": s.status,
        "version": s.version,
        "roles": ROLES,
        "expires_at": date_string(s.created_at + TTL),
        "report_ready": s.report is not None,
    }


def checked_role(rid):
    if not any(r["id"] == rid for r in ROLES):
        raise ApiError(404, "not_found", "没有这个对话角色。")


def protect_text(value):
    if is_sensitive(value):
        raise ApiError(
            422, "private_input", "内容可能包含个人资料，请改用虚构称呼后再发送。"
        )


def owned(db, sid, auth):
    if not auth or not auth.startswith("Bearer ") or len(auth) > 160:
        raise ApiError(401, "unauthorized", "请重新进入训练。")
    item = db.get(Training, sid)
    digest = hashlib.sha256(auth[7:].encode()).hexdigest()
    if (
        not item
        or not hmac.compare_digest(item.token_digest, digest)
        or item.created_at + TTL <= now()
    ):
        raise ApiError(404, "session_unavailable", "该训练不存在或凭证已过期。")
    return item


def serialized(turn, sender):
    return {
        "id": turn.user_id if sender == "user" else turn.reply_id,
        "role_id": turn.role_id,
        "sender": sender,
        "content": turn.user_text if sender == "user" else turn.reply,
        "status": "complete",
        "created_at": date_string(turn.created_at),
    }


def create_app(url: str | None = None):
    engine = engine_for(url or database_url())

    @asynccontextmanager
    async def lifespan(_):
        yield
        engine.dispose()

    app = FastAPI(title="ScamSense · 拆招", version="0.1.0", lifespan=lifespan)
    origins = os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            o.strip() for o in origins.split(",") if o.strip() and o.strip() != "*"
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
        allow_credentials=False,
    )

    @app.exception_handler(ApiError)
    async def api_error(_, err):
        return JSONResponse(
            {"error": {"code": err.code, "message": err.message}},
            status_code=err.status,
            headers={"Cache-Control": "no-store"},
        )

    @app.exception_handler(RequestValidationError)
    async def invalid(_, err):
        return await api_error(
            None, ApiError(422, "invalid_input", "请求格式不正确或超出字数限制。")
        )

    @app.exception_handler(OperationalError)
    async def database_failure(_, err):
        return await api_error(
            None,
            ApiError(
                503, "storage_unavailable", "存储暂不可用，请确认已迁移数据库后重试。"
            ),
        )

    @app.middleware("http")
    async def no_cache(request: Request, call_next):
        result = await call_next(request)
        result.headers["Cache-Control"] = "no-store"
        return result

    @contextmanager
    def transaction(write=False):
        with Session(engine, expire_on_commit=False) as db:
            # Acquire SQLite's write lock before checking a request key or session version.
            if write:
                db.execute(text("BEGIN IMMEDIATE"))
            yield db
            if write:
                db.commit()

    @app.get("/healthz")
    def health():
        with transaction() as db:
            db.scalar(select(Training.id).limit(1))
        return {"status": "ok", "mode": "local-rules"}

    @app.post(PREFIX, status_code=201)
    def start():
        timestamp = now()
        with transaction(True) as db:
            db.execute(delete(Training).where(Training.created_at <= timestamp - TTL))
            if (
                db.scalar(
                    select(func.count())
                    .select_from(Training)
                    .where(Training.created_at > timestamp - 3600)
                )
                >= 120
            ):
                raise ApiError(
                    429, "capacity", "本小时的演示名额暂时用完，请稍后再试。"
                )
            token = secrets.token_urlsafe(32)
            s = Training(
                id=str(uuid4()),
                token_digest=hashlib.sha256(token.encode()).hexdigest(),
                created_at=timestamp,
            )
            db.add(s)
            db.flush()
            return {**public(s), "session_token": token}

    @app.get(PREFIX + "/{sid}")
    def state(sid: str, authorization: Auth = None):
        with transaction() as db:
            return public(owned(db, sid, authorization))

    chat_path = PREFIX + "/{sid}/roles/{rid}/messages"

    @app.get(chat_path)
    def history(sid: str, rid: str, authorization: Auth = None):
        with transaction() as db:
            owned(db, sid, authorization)
            checked_role(rid)
            rows = db.scalars(
                select(Turn)
                .where(Turn.session_id == sid, Turn.role_id == rid)
                .order_by(Turn.seq)
            )
            return {
                "items": [
                    serialized(t, sender) for t in rows for sender in ("user", "role")
                ],
                "next_cursor": None,
            }

    @app.post(chat_path)
    def chat(sid: str, rid: str, payload: Chat, authorization: Auth = None):
        with transaction(True) as db:
            s = owned(db, sid, authorization)
            checked_role(rid)
            protect_text(payload.text)
            key = str(payload.client_message_id)
            turn = db.scalar(
                select(Turn).where(Turn.session_id == sid, Turn.client_id == key)
            )
            if turn is not None:
                if turn.role_id != rid or turn.user_text != payload.text:
                    raise ApiError(
                        409, "idempotency_conflict", "此消息编号已用于其他内容。"
                    )
            else:
                if s.status != "active":
                    raise ApiError(409, "ended", "训练已结束，可前往复盘。")
                if (
                    db.scalar(
                        select(func.count())
                        .select_from(Turn)
                        .where(Turn.session_id == sid)
                    )
                    >= 48
                ):
                    raise ApiError(
                        429,
                        "turn_limit",
                        "本场已达 48 次提问上限，请提交决定或提前复盘。",
                    )
                facts = analyze(rid, payload.text, s.phase)
                reply = facts.pop("reply")
                facts["from_phase"] = s.phase
                s.phase, s.version = facts["next_phase"], s.version + 1
                turn = Turn(
                    session_id=sid,
                    client_id=key,
                    user_id=str(uuid4()),
                    reply_id=str(uuid4()),
                    role_id=rid,
                    user_text=payload.text,
                    reply=reply,
                    facts=facts,
                    created_at=now(),
                )
                db.add(turn)
            message_id, reply, version = turn.reply_id, turn.reply, s.version

        async def frames():
            seq = 0

            def frame(kind, **fields):
                nonlocal seq
                seq += 1
                data = json.dumps(
                    {"message_id": message_id, **fields}, ensure_ascii=False
                )
                return f"id: {message_id}:{seq}\nevent: {kind}\ndata: {data}\n\n"

            yield frame("start", role_id=rid)
            for offset in range(0, len(reply), 12):
                yield frame("delta", text=reply[offset : offset + 12])
                await asyncio.sleep(0.025)
            yield frame("complete", session_version=version)

        return StreamingResponse(
            frames(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )

    @app.post(PREFIX + "/{sid}/messages/{mid}/seen", status_code=204)
    def seen(sid: str, mid: str, authorization: Auth = None):
        with transaction(True) as db:
            s = owned(db, sid, authorization)
            turn = db.scalar(
                select(Turn).where(Turn.session_id == sid, Turn.reply_id == mid)
            )
            if not turn:
                raise ApiError(404, "not_found", "找不到这条角色消息。")
            if s.status == "active":
                turn.presented = True
        return Response(status_code=204)

    def finish(sid, authorization, payload, decision):
        with transaction(True) as db:
            s = owned(db, sid, authorization)
            receipt = {
                "request_id": str(payload.request_id),
                "decision": decision,
                "expected_version": payload.expected_version,
            }
            if s.final_request == receipt:
                return public(s)
            if s.status != "active" or s.version != payload.expected_version:
                raise ApiError(409, "state_conflict", "训练状态已更新，请刷新后查看。")
            records = db.scalars(
                select(Turn).where(Turn.session_id == sid).order_by(Turn.seq)
            )
            turns = [
                dict(
                    message_id=t.user_id,
                    reply_id=t.reply_id,
                    role_id=t.role_id,
                    text=t.user_text,
                    presented=t.presented,
                    **t.facts,
                )
                for t in records
            ]
            s.report = make_report(turns, decision)
            s.final_request = receipt
            s.phase, s.status, s.version = (
                "S6",
                "completed" if decision else "ended_early",
                s.version + 1,
            )
            return public(s)

    @app.post(PREFIX + "/{sid}/decision")
    def decide(sid: str, payload: Decision, authorization: Auth = None):
        protect_text(payload.reason)
        return finish(
            sid,
            authorization,
            payload,
            {"choice": payload.choice, "reason": payload.reason},
        )

    @app.post(PREFIX + "/{sid}/end")
    def end(sid: str, payload: End, authorization: Auth = None):
        return finish(sid, authorization, payload, None)

    @app.get(PREFIX + "/{sid}/report")
    def report(sid: str, authorization: Auth = None):
        with transaction() as db:
            s = owned(db, sid, authorization)
            if s.report is None:
                raise ApiError(409, "report_not_ready", "请先提交决定或提前结束。")
            return s.report

    return app


app = create_app()
