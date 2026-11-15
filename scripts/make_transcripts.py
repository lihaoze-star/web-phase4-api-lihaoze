"""Run real curl commands against the local API and save terminal transcripts.

Usage:
    python scripts/make_transcripts.py

The server must already be running on http://127.0.0.1:5000.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

BASE = "http://127.0.0.1:5000"
CURL = "curl.exe"
OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "transcripts"
WRITE = r"\n[HTTP %{http_code}]\n"


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


def request(method: str, path: str, body: str | None = None) -> tuple[str, str]:
    args = ["-s", "-w", WRITE, "-X", method, BASE + path]
    if body is not None:
        args += ["-H", "Content-Type: application/json", "-d", body]
    return curl(args), args


def line(display: str, output: str) -> str:
    return f"$ {display}\n{output}\n"


def body_of(output: str) -> str:
    return output.split("[HTTP", 1)[0].strip()


def success_transcript() -> str:
    parts: list[str] = []

    out, _ = request("GET", "/api/tasks")
    parts.append(line('curl.exe -s -w "\\n[HTTP %{http_code}]\\n" http://127.0.0.1:5000/api/tasks', out))

    body = '{"title":"学习 Flask","done":false}'
    out, _ = request("POST", "/api/tasks", body)
    parts.append(line(
        "curl.exe -s -w \"\\n[HTTP %{http_code}]\\n\" -X POST http://127.0.0.1:5000/api/tasks "
        f"-H \"Content-Type: application/json\" -d '{body}'",
        out,
    ))
    first_id = json.loads(body_of(out))["data"]["id"]

    body = '{"title":"写接口文档"}'
    out, _ = request("POST", "/api/tasks", body)
    parts.append(line(
        "curl.exe -s -w \"\\n[HTTP %{http_code}]\\n\" -X POST http://127.0.0.1:5000/api/tasks "
        f"-H \"Content-Type: application/json\" -d '{body}'",
        out,
    ))

    out, _ = request("GET", "/api/tasks")
    parts.append(line('curl.exe -s -w "\\n[HTTP %{http_code}]\\n" http://127.0.0.1:5000/api/tasks', out))

    out, _ = request("DELETE", f"/api/tasks/{first_id}")
    parts.append(line(
        f'curl.exe -s -w "\\n[HTTP %{{http_code}}]\\n" -X DELETE http://127.0.0.1:5000/api/tasks/{first_id}',
        out,
    ))

    out, _ = request("GET", "/api/tasks")
    parts.append(line('curl.exe -s -w "\\n[HTTP %{http_code}]\\n" http://127.0.0.1:5000/api/tasks', out))

    return "\n".join(parts)


def validation_transcript() -> str:
    parts: list[str] = []

    body = '{"done":true}'
    out, _ = request("POST", "/api/tasks", body)
    parts.append(line(
        "curl.exe -s -w \"\\n[HTTP %{http_code}]\\n\" -X POST http://127.0.0.1:5000/api/tasks "
        f"-H \"Content-Type: application/json\" -d '{body}'",
        out,
    ))

    body = '{"title":123}'
    out, _ = request("POST", "/api/tasks", body)
    parts.append(line(
        "curl.exe -s -w \"\\n[HTTP %{http_code}]\\n\" -X POST http://127.0.0.1:5000/api/tasks "
        f"-H \"Content-Type: application/json\" -d '{body}'",
        out,
    ))

    body = '{"title":"   "}'
    out, _ = request("POST", "/api/tasks", body)
    parts.append(line(
        "curl.exe -s -w \"\\n[HTTP %{http_code}]\\n\" -X POST http://127.0.0.1:5000/api/tasks "
        f"-H \"Content-Type: application/json\" -d '{body}'",
        out,
    ))

    out, _ = request("GET", "/api/tasks")
    parts.append(line('curl.exe -s -w "\\n[HTTP %{http_code}]\\n" http://127.0.0.1:5000/api/tasks', out))

    return "\n".join(parts)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    success = success_transcript()
    validation = validation_transcript()
    (OUT_DIR / "api-success.txt").write_text(success, encoding="utf-8")
    (OUT_DIR / "api-validation-400.txt").write_text(validation, encoding="utf-8")
    print(success)
    print("=" * 78)
    print(validation)


if __name__ == "__main__":
    main()
