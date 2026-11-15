"""Render curl transcripts as terminal-style HTML pages for screenshots."""

from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS = ROOT / "docs" / "transcripts"
DOCS = ROOT / "docs"

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #0b0d12;
    --panel: #12151c;
    --line: #262b36;
    --text: #d8dee9;
    --muted: #7c8798;
    --green: #7ee787;
    --orange: #ffa657;
    --red: #ff7b72;
    --blue: #79c0ff;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); }}
  body {{
    padding: 40px;
    color: var(--text);
    font-family: "Cascadia Mono", "Consolas", "Microsoft YaHei", monospace;
  }}
  .page {{ max-width: 1500px; margin: 0 auto; }}
  .meta {{
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 24px; margin: 0 4px 16px;
    color: var(--muted); font-size: 13px; letter-spacing: .08em;
  }}
  .meta strong {{ color: var(--text); font-weight: 600; letter-spacing: 0; }}
  .terminal {{
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--panel);
    box-shadow: 0 24px 70px rgba(0, 0, 0, .45);
  }}
  .titlebar {{
    display: flex; align-items: center; gap: 14px;
    height: 44px; padding: 0 18px;
    border-bottom: 1px solid var(--line);
    background: #171b24;
  }}
  .dots {{ display: flex; gap: 7px; }}
  .dot {{ width: 11px; height: 11px; border-radius: 50%; }}
  .dot-r {{ background: #ff5f57; }}
  .dot-y {{ background: #febc2e; }}
  .dot-g {{ background: #28c840; }}
  .title {{ color: #aab4c3; font-size: 12.5px; letter-spacing: .02em; }}
  .title b {{ color: #e6edf3; font-weight: 600; }}
  .body {{ padding: 24px 28px 28px; }}
  pre {{
    margin: 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font-size: 15px;
    line-height: 1.62;
    tab-size: 2;
  }}
  .prompt {{ color: var(--green); font-weight: 700; }}
  .cmd {{ color: #e6edf3; }}
  .json {{ color: #b9c7da; }}
  .ok {{ color: var(--green); font-weight: 700; }}
  .bad {{ color: var(--red); font-weight: 700; }}
  .comment {{ color: var(--muted); font-style: italic; }}
  .footer {{
    display: flex; justify-content: space-between; gap: 24px;
    margin: 12px 4px 0; color: var(--muted); font-size: 12px;
  }}
  .blink {{ color: var(--green); }}
</style>
</head>
<body>
  <div class="page">
    <div class="meta">
      <div><strong>{title}</strong>　·　{note}</div>
      <div>{stamp}</div>
    </div>
    <div class="terminal">
      <div class="titlebar">
        <div class="dots"><span class="dot dot-r"></span><span class="dot dot-y"></span><span class="dot dot-g"></span></div>
        <div class="title">Terminal — <b>{window_title}</b></div>
      </div>
      <div class="body">
<pre>{body}</pre>
      </div>
    </div>
    <div class="footer">
      <span>{footer_left}</span>
      <span>{footer_right}</span>
    </div>
  </div>
</body>
</html>
"""


def colorize(text: str) -> str:
    out: list[str] = []
    for line in text.splitlines():
        escaped = html.escape(line)
        if line.startswith("$ "):
            out.append(
                '<span class="prompt">$</span> '
                f'<span class="cmd">{html.escape(line[2:])}</span>'
            )
        elif line.startswith("[HTTP"):
            cls = "ok" if " 2" in line else "bad"
            out.append(f'<span class="{cls}">{escaped}</span>')
        elif line.startswith("#"):
            out.append(f'<span class="comment">{escaped}</span>')
        elif not line.strip():
            out.append("")
        else:
            out.append(f'<span class="json">{escaped}</span>')
    return "\n".join(out)


def render(
    transcript_name: str,
    output_name: str,
    title: str,
    note: str,
    window_title: str,
    footer_left: str,
    footer_right: str,
) -> None:
    transcript = (TRANSCRIPTS / transcript_name).read_text(encoding="utf-8").strip("\n")
    body = colorize(transcript)
    page = TEMPLATE.format(
        title=html.escape(title),
        note=html.escape(note),
        stamp="2026-11-15 · Asia/Shanghai",
        window_title=html.escape(window_title),
        body=body,
        footer_left=html.escape(footer_left),
        footer_right=html.escape(footer_right),
    )
    (DOCS / output_name).write_text(page, encoding="utf-8")
    print(f"wrote docs/{output_name}")


def main() -> None:
    render(
        "api-success.txt",
        "api-success.html",
        "任务 2 · 三个接口联调",
        "GET / POST / DELETE 全部返回 JSON",
        "curl 验收 · 3 个接口",
        "Flask 3.1.3 · SQLite 落盘 · http://127.0.0.1:5000",
        "终端样式渲染，内容为实际 curl 返回",
    )
    render(
        "api-validation-400.txt",
        "api-validation-400.html",
        "任务 2 · 参数校验",
        "缺字段 / 类型错误都返回 400",
        "curl 验收 · 400 而不是 500",
        "返回体仍然是 {code, data, msg}",
        "服务没有崩，最后一条 GET 仍返回 200",
    )
    render(
        "api-persistence.txt",
        "api-persistence.html",
        "任务 2 · 数据落盘",
        "停止服务并重新启动后数据仍在",
        "curl 验收 · 重启后还在",
        "SQLite 落盘（测试库：.tmp/persistence-check.db）",
        "重启前后的两次请求都来自真实进程",
    )


if __name__ == "__main__":
    main()
