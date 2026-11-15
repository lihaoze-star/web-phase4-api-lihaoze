# web-phase4-api-lihaoze · Task API

任务 2：用 **Flask + SQLite** 写 3 个接口，并把数据落盘。

- **技术栈**：Python 3.10+ / Flask 3.1.3 / SQLite（Python 标准库 `sqlite3`）
- **接口数量**：3 个必做（GET / POST / DELETE）+ 1 个加分项（PUT）
- **统一返回**：`{ "code", "data", "msg" }`，错误也返回 JSON
- **数据文件**：`data/tasks.db`，关掉服务再启动数据仍在
- **仓库**：<https://github.com/lihaoze-star/web-phase4-api-lihaoze>
- **接口文档**：[docs/api.md](docs/api.md)

---

## 快速启动

需要 Python 3.10 或更高版本，不需要 Node、不需要数据库服务。

```bash
cd web-phase4-api-lihaoze

# 1. 创建虚拟环境
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动
python app.py
```

看到下面的输出就说明启动成功：

```text
 * Running on http://127.0.0.1:5000
```

打开 <http://127.0.0.1:5000/api/tasks>，第一次会得到：

```json
{"code":200,"data":[],"msg":"ok"}
```

> 端口被占用时可以用 `PORT=5001 python app.py`（Windows PowerShell 用 `$env:PORT=5001; python app.py`）。
> 首次启动会自动创建 `data/tasks.db` 和 `tasks` 表，不需要手动建库。
> Windows PowerShell 里建议写 `curl.exe`，避免 `curl` 被解析成 `Invoke-WebRequest`；macOS / Linux 用 `curl` 即可。

---

## 接口一览

| 方法 | 路径 | 说明 | 成功状态码 |
| --- | --- | --- | --- |
| `GET` | `/api/tasks` | 获取任务列表 | 200 |
| `POST` | `/api/tasks` | 新增任务 | 201 |
| `PUT` | `/api/tasks/{id}` | 修改任务（加分项） | 200 |
| `DELETE` | `/api/tasks/{id}` | 删除任务 | 200 |

每个接口的参数、返回示例和错误说明见 **[docs/api.md](docs/api.md)**。

统一返回结构：

```json
{
  "code": 200,
  "data": {},
  "msg": "ok"
}
```

- `code` 与 HTTP 状态码一致。
- `data` 成功时是业务数据，失败时是 `null`。
- `msg` 失败时直接说明原因，前端可以展示。

---

## 验收截图

### 1. 三个接口依次调通（GET / POST / DELETE）

![三个接口联调](docs/screenshots/api-success.png)

### 2. 故意少传字段，返回 400 而不是 500

![参数校验 400](docs/screenshots/api-validation-400.png)

覆盖的情况：缺少 `title`、`title` 类型错误、`title` 只有空格。三次都是 400，最后一条 `GET` 仍是 200，说明服务没有崩。

### 3. 数据落盘：停止服务、重新启动，数据还在

![重启后数据仍在](docs/screenshots/api-persistence.png)

截图里的两次请求来自两个真实的 Python 进程：第一次进程创建任务后被终止，第二次进程启动后仍能读到同一条数据。

原始 curl 输出保存在：

- [docs/transcripts/api-success.txt](docs/transcripts/api-success.txt)
- [docs/transcripts/api-validation-400.txt](docs/transcripts/api-validation-400.txt)
- [docs/transcripts/api-persistence.txt](docs/transcripts/api-persistence.txt)

> 截图是用真实的 curl 输出渲染的终端样式图（原始文本在上面），不是手写结果。

---

## 参数校验与错误处理

校验在写库之前完成，任何不合法的请求都不会产生半条数据：

- 请求体不是 JSON → 400 `请求体必须是合法的 JSON 对象`
- `Content-Type` 不是 `application/json` → 400
- 缺少 `title` → 400 `缺少字段: title`
- `title` 不是字符串 / 为空 / 超过 80 字 → 400
- `done` 不是布尔值 → 400 `done 必须是布尔值 true/false`
- 删除或修改不存在的任务 → 404 `任务 999 不存在`
- 路由不存在 → 404 `接口不存在`
- 方法不允许 → 405 `请求方法不允许`
- 未捕获异常 → 500 `服务器内部错误`，不返回 HTML 堆栈

全局错误处理在 `app.py` 的 `errorhandler` 中统一收口，因此浏览器直接访问不存在的路径也不会看到 Flask 默认的 HTML 报错页。

---

## 数据落盘

- 默认数据库：`data/tasks.db`（SQLite 单文件）。
- 建表在 `app.py` 的 `init_db()` 中，使用 `CREATE TABLE IF NOT EXISTS`，重复启动不会丢数据。
- 每次请求使用独立连接，写操作在 `with connection:` 事务中提交。

手动验证持久化（PowerShell）：

```powershell
# 1. 创建一条
'{"title":"重启后还在"}' | curl.exe -s -X POST http://127.0.0.1:5000/api/tasks -H "Content-Type: application/json" --data-binary "@-"

# 2. Ctrl+C 停止服务，再执行 python app.py

# 3. 再查一次，刚才的数据还在
curl.exe -s http://127.0.0.1:5000/api/tasks
```

> Git Bash / macOS / Linux 可以把 `'{"title":"重启后还在"}' | curl.exe ... --data-binary "@-"` 换成常见的 `curl -s -X POST ... -d '{"title":"重启后还在"}'`。

想清空数据时，停止服务后删除 `data/tasks.db`，再启动即可。

---

## 测试

```bash
python -m unittest discover -s tests -v
```

当前结果：**15 个测试全部通过**，覆盖：

- 空列表、创建、查询、修改、删除
- 缺字段、类型错误、空标题、超长标题、坏 JSON、错误 Content-Type
- 404 / 405 / 500 都返回 JSON
- SQLite 中确实写入了数据

测试使用独立的 `.tmp/tasks-test.db`，不会污染演示数据。

---

## 目录结构

```text
web-phase4-api-lihaoze/
├── app.py                       # Flask 应用：路由、校验、全局错误处理、SQLite
├── requirements.txt             # Flask==3.1.3
├── README.md
├── data/
│   └── tasks.db                 # 运行时自动生成（已 gitignore）
├── docs/
│   ├── api.md                   # 接口文档（方法 / 路径 / 参数 / 返回示例）
│   ├── transcripts/             # 原始 curl 输出
│   └── screenshots/             # 验收截图
├── scripts/
│   ├── make_transcripts.py      # 生成三个接口 + 400 的真实 curl 记录
│   ├── persistence_check.py     # 自动完成“启动 → 写入 → 重启 → 再读”
│   ├── render_terminal.py       # 把记录渲染成终端样式 HTML
│   └── capture_terminal.mjs     # 用 Edge 截图
├── tests/
│   └── test_api.py              # 15 个 unittest
└── .gitignore
```

---

## curl 验收命令

> **Windows PowerShell 注意**：`-d '{"title":"..."}'` 里的双引号会被 PowerShell 吞掉，实际发出去会变成 `{title:...}`，服务会返回 400。  
> PowerShell 下请把 JSON 通过管道交给 `curl.exe --data-binary "@-"`，也就是下面第一段写法。

### Windows PowerShell

```powershell
# 1. 列表
curl.exe -s http://127.0.0.1:5000/api/tasks

# 2. 新增
'{"title":"学习 Flask","done":false}' | curl.exe -s -X POST http://127.0.0.1:5000/api/tasks -H "Content-Type: application/json" --data-binary "@-"

# 3. 删除（把 1 换成上一步返回的 id）
curl.exe -s -X DELETE http://127.0.0.1:5000/api/tasks/1

# 4. 故意少传 title，应该是 400，不是 500
'{"done":true}' | curl.exe -s -X POST http://127.0.0.1:5000/api/tasks -H "Content-Type: application/json" --data-binary "@-"
```

### Git Bash / macOS / Linux

```bash
# 1. 列表
curl -s http://127.0.0.1:5000/api/tasks

# 2. 新增
curl -s -X POST http://127.0.0.1:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"学习 Flask","done":false}'

# 3. 删除（把 1 换成上一步返回的 id）
curl -s -X DELETE http://127.0.0.1:5000/api/tasks/1

# 4. 故意少传 title，应该是 400，不是 500
curl -s -X POST http://127.0.0.1:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"done":true}'
```

成功响应示例：

```json
{"code":201,"data":{"id":1,"title":"学习 Flask","done":false,"created_at":"2026-11-15T12:05:47+08:00"},"msg":"创建成功"}
```

失败响应示例：

```json
{"code":400,"data":null,"msg":"缺少字段: title"}
```

---

## 说明

- 这是任务 2 的提交版本，重点是「接口能调通、错误是 JSON、数据真的落盘」。
- 没有引入 ORM、蓝图、鉴权等额外内容，保持一周作业的可读范围。
- 所有接口的 `code` 与 HTTP 状态码保持一致，便于用 `curl -i` 或浏览器 Network 面板核对。
