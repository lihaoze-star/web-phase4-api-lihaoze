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

    # ------------------------------------------------------------------
    # streaming chat
    # ------------------------------------------------------------------

    def test_chat_requires_messages(self):
        response = self.client.post("/api/chat", json={})
        self.assert_envelope(response, 400, 400)

    def test_chat_rejects_bad_role(self):
        response = self.client.post(
            "/api/chat",
            json={"messages": [{"role": "system", "content": "x"}]},
        )
        self.assert_envelope(response, 400, 400)

    def test_chat_last_message_must_be_user(self):
        response = self.client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "在"}]},
        )
        self.assert_envelope(response, 400, 400)

    def test_chat_mock_stream(self):
        with patch.dict(os.environ, {"CHAT_MOCK": "1"}, clear=False):
            response = self.client.post(
                "/api/chat",
                json={"messages": [{"role": "user", "content": "用一句话介绍 fetch"}]},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.mimetype.startswith("text/event-stream"))
        text = response.get_data(as_text=True)
        self.assertIn('"delta"', text)
        self.assertIn('"done": true', text)

    def test_chat_accepts_text_plain_body(self):
        with patch.dict(os.environ, {"CHAT_MOCK": "1"}, clear=False):
            response = self.client.post(
                "/api/chat",
                data='{"messages":[{"role":"user","content":"你好"}]}',
                content_type="text/plain",
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('"delta"', response.get_data(as_text=True))

    def test_chat_without_key_is_readable_json(self):
        with patch.dict(os.environ, {"CHAT_MOCK": "0", "LLM_API_KEY": ""}, clear=False):
            response = self.client.post(
                "/api/chat",
                json={"messages": [{"role": "user", "content": "你好"}]},
            )
        body = self.assert_envelope(response, 500, 500)
        self.assertIn("LLM_API_KEY", body["msg"])

    def test_trim_context_drops_oldest(self):
        messages = [
            {"role": "user", "content": "u" * 80},
            {"role": "assistant", "content": "a" * 80},
            {"role": "user", "content": "v" * 80},
            {"role": "assistant", "content": "b" * 80},
            {"role": "user", "content": "最新的问题"},
        ]
        kept = api.trim_context(messages, 200)
        self.assertLessEqual(sum(len(item["content"]) for item in kept), 200)
        self.assertEqual(kept[0]["role"], "user")
        self.assertEqual(kept[-1]["content"], "最新的问题")

    def test_chat_401_is_readable(self):
        class FakeResponse:
            status_code = 401
            def close(self):
                pass

        with patch.dict(os.environ, {"CHAT_MOCK": "0", "LLM_API_KEY": "test", "LLM_MODEL": "test"}, clear=False):
            with patch.object(api.requests, "post", return_value=FakeResponse()):
                response = self.client.post(
                    "/api/chat",
                    json={"messages": [{"role": "user", "content": "你好"}]},
                )
        self.assertEqual(response.status_code, 200)
        self.assertIn("API Key 无效", response.get_data(as_text=True))

    def test_chat_429_is_readable(self):
        class FakeResponse:
            status_code = 429
            def close(self):
                pass

        with patch.dict(os.environ, {"CHAT_MOCK": "0", "LLM_API_KEY": "test", "LLM_MODEL": "test"}, clear=False):
            with patch.object(api.requests, "post", return_value=FakeResponse()):
                response = self.client.post(
                    "/api/chat",
                    json={"messages": [{"role": "user", "content": "你好"}]},
                )
        self.assertIn("429", response.get_data(as_text=True))

    def test_chat_timeout_is_readable(self):
        with patch.dict(os.environ, {"CHAT_MOCK": "0", "LLM_API_KEY": "test", "LLM_MODEL": "test"}, clear=False):
            with patch.object(api.requests, "post", side_effect=api.requests.Timeout()):
                response = self.client.post(
                    "/api/chat",
                    json={"messages": [{"role": "user", "content": "你好"}]},
                )
        self.assertIn("超时", response.get_data(as_text=True))

    # ------------------------------------------------------------------
    # tools
    # ------------------------------------------------------------------

    def test_add_item_tool_writes_database(self):
        result = api.execute_tool("add_item", {"title": "明天交实验报告"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["item"]["title"], "明天交实验报告")
        listed = self.client.get("/api/tasks").get_json()["data"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["title"], "明天交实验报告")

    def test_query_items_tool_filters(self):
        api.execute_tool("add_item", {"title": "写实验报告"})
        api.execute_tool("add_item", {"title": "复习 CORS", "done": True})
        result = api.execute_tool(
            "query_items", {"status": "todo", "keyword": "实验"}
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["title"], "写实验报告")

    def test_add_item_tool_validation(self):
        missing = api.execute_tool("add_item", {})
        self.assertFalse(missing["ok"])
        self.assertIn("title", missing["error"])
        bad_done = api.execute_tool("add_item", {"title": "x", "done": "yes"})
        self.assertFalse(bad_done["ok"])

    def test_query_items_tool_validation(self):
        bad_status = api.execute_tool("query_items", {"status": "未完成"})
        self.assertFalse(bad_status["ok"])
        self.assertIn("status", bad_status["error"])
        unknown = api.execute_tool("delete_item", {})
        self.assertFalse(unknown["ok"])


if __name__ == "__main__":
    unittest.main()
