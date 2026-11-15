"""Unit tests for the Task API.

Run with:
    python -m unittest discover -s tests -v
"""

import os
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
TEST_DB = BASE_DIR / ".tmp" / "tasks-test.db"
TEST_DB.parent.mkdir(parents=True, exist_ok=True)
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["TASKS_DB"] = str(TEST_DB)

import app as api  # noqa: E402  (must come after TASKS_DB is set)


class TaskApiTest(unittest.TestCase):
    def setUp(self):
        with closing(sqlite3.connect(api.DB_PATH)) as connection, connection:
            connection.execute("DELETE FROM tasks")
            try:
                connection.execute("DELETE FROM sqlite_sequence WHERE name = 'tasks'")
            except sqlite3.OperationalError:
                pass
        self.client = api.app.test_client()

    def assert_envelope(self, response, status: int, code: int):
        self.assertEqual(response.status_code, status)
        self.assertTrue(response.is_json)
        body = response.get_json()
        self.assertEqual(set(body.keys()), {"code", "data", "msg"})
        self.assertEqual(body["code"], code)
        return body

    def create(self, **payload):
        return self.client.post("/api/tasks", json=payload)

    # ------------------------------------------------------------------
    # happy path
    # ------------------------------------------------------------------

    def test_empty_list(self):
        body = self.assert_envelope(self.client.get("/api/tasks"), 200, 200)
        self.assertEqual(body["data"], [])

    def test_create_and_list(self):
        body = self.assert_envelope(self.create(title="  学习 Flask  "), 201, 201)
        task = body["data"]
        self.assertEqual(task["title"], "学习 Flask")
        self.assertIs(task["done"], False)
        self.assertIsInstance(task["id"], int)
        self.assertIn("created_at", task)

        listed = self.assert_envelope(self.client.get("/api/tasks"), 200, 200)
        self.assertEqual(len(listed["data"]), 1)
        self.assertEqual(listed["data"][0]["id"], task["id"])

    def test_update(self):
        task_id = self.create(title="旧标题").get_json()["data"]["id"]
        body = self.assert_envelope(
            self.client.put(f"/api/tasks/{task_id}", json={"title": "新标题", "done": True}),
            200,
            200,
        )
        self.assertEqual(body["data"]["title"], "新标题")
        self.assertIs(body["data"]["done"], True)

    def test_delete(self):
        task_id = self.create(title="待删除").get_json()["data"]["id"]
        body = self.assert_envelope(self.client.delete(f"/api/tasks/{task_id}"), 200, 200)
        self.assertEqual(body["data"], {"id": task_id})
        self.assert_envelope(self.client.delete(f"/api/tasks/{task_id}"), 404, 404)

    # ------------------------------------------------------------------
    # validation: 400, not 500
    # ------------------------------------------------------------------

    def test_missing_title(self):
        body = self.assert_envelope(self.create(done=True), 400, 400)
        self.assertIsNone(body["data"])
        self.assertIn("title", body["msg"])

    def test_title_wrong_type(self):
        body = self.assert_envelope(self.create(title=123), 400, 400)
        self.assertIn("字符串", body["msg"])

    def test_title_too_long(self):
        body = self.assert_envelope(self.create(title="x" * 81), 400, 400)
        self.assertIn("80", body["msg"])

    def test_done_wrong_type(self):
        body = self.assert_envelope(self.create(title="合法标题", done="yes"), 400, 400)
        self.assertIn("布尔", body["msg"])

    def test_broken_json(self):
        response = self.client.post(
            "/api/tasks",
            data="{not json",
            content_type="application/json",
        )
        self.assert_envelope(response, 400, 400)

    def test_missing_content_type(self):
        response = self.client.post("/api/tasks", data='{"title": "x"}')
        self.assert_envelope(response, 400, 400)

    def test_update_without_fields(self):
        task_id = self.create(title="标题").get_json()["data"]["id"]
        self.assert_envelope(self.client.put(f"/api/tasks/{task_id}", json={}), 400, 400)

    # ------------------------------------------------------------------
    # global error handling and persistence
    # ------------------------------------------------------------------

    def test_unknown_route_is_json(self):
        response = self.client.get("/api/not-found")
        self.assert_envelope(response, 404, 404)

    def test_wrong_method_is_json(self):
        response = self.client.post("/api/tasks/1")
        self.assert_envelope(response, 405, 405)

    def test_cors_headers_on_normal_response(self):
        origin = "https://lihaoze-star.github.io"
        response = self.client.get("/api/tasks", headers={"Origin": origin})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)
        self.assertIn("POST", response.headers["Access-Control-Allow-Methods"])
        self.assertIn("Content-Type", response.headers["Access-Control-Allow-Headers"])

    def test_cors_headers_on_error_response(self):
        origin = "https://lihaoze-star.github.io"
        response = self.client.get("/api/not-found", headers={"Origin": origin})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)

    def test_cors_preflight(self):
        origin = "https://lihaoze-star.github.io"
        response = self.client.options(
            "/api/tasks",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertIn(response.status_code, (200, 204))
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)
        self.assertIn("POST", response.headers["Access-Control-Allow-Methods"])
        self.assertIn("Content-Type", response.headers["Access-Control-Allow-Headers"])

    def test_unexpected_error_is_json(self):
        with patch.object(api, "connect", side_effect=RuntimeError("boom")):
            response = self.client.get("/api/tasks")
        self.assert_envelope(response, 500, 500)

    def test_data_is_persisted_in_sqlite(self):
        task_id = self.create(title="落盘任务").get_json()["data"]["id"]
        with closing(sqlite3.connect(api.DB_PATH)) as connection:
            row = connection.execute(
                "SELECT title FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        self.assertEqual(row[0], "落盘任务")


if __name__ == "__main__":
    unittest.main()
