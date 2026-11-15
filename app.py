"""Task API — Flask + SQLite.

A deliberately small CRUD service used for the Phase 2 backend exercise.

Endpoints
---------
GET    /api/tasks          list tasks
POST   /api/tasks          create a task
PUT    /api/tasks/<id>     update a task (bonus)
DELETE /api/tasks/<id>     delete a task

Every response, including errors, uses the same envelope:
    {"code": <http status>, "data": <payload|null>, "msg": "<message>"}
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TASKS_DB", BASE_DIR / "data" / "tasks.db"))

app = Flask(__name__)
app.json.ensure_ascii = False  # return readable Chinese instead of \uXXXX


@app.after_request
def add_cors_headers(response):
    """Allow the separate frontend origin to call this API.

    The fix for a CORS failure belongs on the server: the browser must see
    Access-Control-Allow-* headers on both the real response and OPTIONS.
    Do not disable web security in the browser instead.
    """
    origin = request.headers.get("Origin")
    response.headers["Access-Control-Allow-Origin"] = origin or "*"
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response


class ApiError(Exception):
    """A business error that should be rendered as a JSON envelope."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(str(DB_PATH), timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect()) as connection, connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL,
                done       INTEGER NOT NULL DEFAULT 0,
                created_at TEXT    NOT NULL
            )
            """
        )


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def row_to_task(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"]),
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def envelope(data, msg: str = "ok", status: int = 200):
    return jsonify(code=status, data=data, msg=msg), status


def fail(status: int, msg: str):
    return envelope(None, msg, status)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def read_json_object() -> dict:
    if not request.is_json:
        raise ApiError(400, "Content-Type 必须是 application/json")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(400, "请求体必须是合法的 JSON 对象")
    return payload


def clean_title(value) -> str:
    if not isinstance(value, str):
        raise ApiError(400, "title 必须是字符串")
    title = value.strip()
    if not title:
        raise ApiError(400, "title 不能为空")
    if len(title) > 80:
        raise ApiError(400, "title 长度不能超过 80 个字符")
    return title


def clean_done(value) -> bool:
    # bool is a subclass of int, so compare the exact type.
    if type(value) is not bool:
        raise ApiError(400, "done 必须是布尔值 true/false")
    return value


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/tasks")
def list_tasks():
    with closing(connect()) as connection:
        rows = connection.execute(
            "SELECT id, title, done, created_at FROM tasks ORDER BY id DESC"
        ).fetchall()
    return envelope([row_to_task(row) for row in rows])


@app.post("/api/tasks")
def create_task():
    payload = read_json_object()
    if "title" not in payload:
        raise ApiError(400, "缺少字段: title")

    title = clean_title(payload["title"])
    done = clean_done(payload.get("done", False))
    created_at = now_iso()

    with closing(connect()) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, done, created_at) VALUES (?, ?, ?)",
            (title, int(done), created_at),
        )
        task_id = int(cursor.lastrowid)
        row = connection.execute(
            "SELECT id, title, done, created_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    return envelope(row_to_task(row), "创建成功", 201)


@app.put("/api/tasks/<int:task_id>")
def update_task(task_id: int):
    with closing(connect()) as connection:
        row = connection.execute(
            "SELECT id, title, done, created_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            raise ApiError(404, f"任务 {task_id} 不存在")

        payload = read_json_object()
        if "title" not in payload and "done" not in payload:
            raise ApiError(400, "至少提供 title 或 done 中的一个字段")

        title = clean_title(payload["title"]) if "title" in payload else row["title"]
        done = clean_done(payload["done"]) if "done" in payload else bool(row["done"])

        with connection:
            connection.execute(
                "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
                (title, int(done), task_id),
            )
        updated = connection.execute(
            "SELECT id, title, done, created_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    return envelope(row_to_task(updated), "更新成功")


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id: int):
    with closing(connect()) as connection:
        row = connection.execute(
            "SELECT id FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            raise ApiError(404, f"任务 {task_id} 不存在")

        with connection:
            connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    return envelope({"id": task_id}, "删除成功")


# ---------------------------------------------------------------------------
# Global error handling: never return Flask's HTML error page
# ---------------------------------------------------------------------------

@app.errorhandler(ApiError)
def handle_api_error(error: ApiError):
    return fail(error.status, error.message)


@app.errorhandler(HTTPException)
def handle_http_error(error: HTTPException):
    messages = {
        400: "请求参数错误",
        404: "接口不存在",
        405: "请求方法不允许",
    }
    status = error.code or 500
    return fail(status, messages.get(status, error.description or "请求失败"))


@app.errorhandler(Exception)
def handle_unexpected_error(error: Exception):
    app.logger.exception("Unhandled exception: %s", error)
    return fail(500, "服务器内部错误")


init_db()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
