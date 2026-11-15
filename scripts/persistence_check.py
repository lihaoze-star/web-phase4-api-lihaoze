"""Prove that data survives a real server restart.

Starts the app on port 5001 with a throwaway SQLite file, creates a task,
stops the process, starts a new process, then lists the tasks again.

Usage:
    python scripts/persistence_check.py
"""

from __future__ import annotations

import os
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
DB = ROOT / ".tmp" / "persistence-check.db"
BASE = "http://127.0.0.1:5001"
CURL = "curl.exe"
WRITE = r"\n[HTTP %{http_code}]\n"


def start_server() -> subprocess.Popen:
    env = os.environ.copy()
    env["PORT"] = "5001"
    env["TASKS_DB"] = str(DB)
    process = subprocess.Popen(
        [str(PYTHON), "app.py"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            urllib.request.urlopen(f"{BASE}/api/tasks", timeout=0.5).read()
            return process
        except Exception:
            time.sleep(0.2)
    process.terminate()
    raise RuntimeError("server did not start")


def stop_server(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def curl(args: list[str]) -> str:
    result = subprocess.run(
        [CURL, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )
    return (result.stdout + result.stderr).strip()


def request(method: str, path: str, body: str | None = None) -> str:
    args = ["-s", "-w", WRITE, "-X", method, BASE + path]
    if body is not None:
        args += ["-H", "Content-Type: application/json", "-d", body]
    return curl(args)


def main() -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()

    body = '{"title":"重启服务后还在"}'
    process = start_server()
    created = request("POST", "/api/tasks", body)
    stop_server(process)

    process = start_server()
    listed = request("GET", "/api/tasks")
    stop_server(process)

    transcript = (
        '$ curl.exe -s -w "\\n[HTTP %{http_code}]\\n" -X POST http://127.0.0.1:5001/api/tasks '
        f"-H \"Content-Type: application/json\" -d '{body}'\n"
        f"{created}\n\n"
        "# 停止服务：Ctrl+C（或结束 python 进程）\n"
        "# 重新启动：python app.py\n\n"
        '$ curl.exe -s -w "\\n[HTTP %{http_code}]\\n" http://127.0.0.1:5001/api/tasks\n'
        f"{listed}\n"
    )

    out = ROOT / "docs" / "transcripts" / "api-persistence.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(transcript, encoding="utf-8")
    print(transcript)


if __name__ == "__main__":
    main()
