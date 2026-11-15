# Task API 接口文档

- **Base URL**：`http://127.0.0.1:5000`
- **数据格式**：请求与响应均为 JSON，请求头需要 `Content-Type: application/json`
- **Windows PowerShell 注意**：`-d '{"title":"..."}'` 的双引号会被 PowerShell 吞掉，实际会发成 `{title:...}`。PowerShell 下请用 `'{"title":"..."}' | curl.exe ... --data-binary "@-"`，或改用 Git Bash 执行本文的 `curl` 示例。
- **统一返回结构**：

```json
{
  "code": 200,
  "data": {},
  "msg": "ok"
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | number | 与 HTTP 状态码一致：200 / 201 / 400 / 404 / 405 / 500 |
| `data` | any | 成功时为业务数据，失败时为 `null` |
| `msg` | string | 成功提示或失败原因，前端可直接展示 |

> 所有接口（包括 404、405、500）都返回这一结构，不会返回 Flask 的 HTML 报错页。

---

## 接口总表

| 方法 | 路径 | 参数 | 返回示例 |
| --- | --- | --- | --- |
| `GET` | `/api/tasks` | 无 | `{"code":200,"data":[{"id":1,"title":"学习 Flask","done":false,"created_at":"..."}],"msg":"ok"}` |
| `POST` | `/api/tasks` | body：`title`（string，必填，1–80 字）、`done`（boolean，可选） | `{"code":201,"data":{"id":1,"title":"学习 Flask","done":false,"created_at":"..."},"msg":"创建成功"}` |
| `PUT` | `/api/tasks/{id}` | path：`id`（int）；body：`title` / `done` 至少一个 | `{"code":200,"data":{"id":1,"title":"新标题","done":true,"created_at":"..."},"msg":"更新成功"}` |
| `DELETE` | `/api/tasks/{id}` | path：`id`（int） | `{"code":200,"data":{"id":1},"msg":"删除成功"}` |

---

## 1. 获取任务列表

- **方法**：`GET`
- **路径**：`/api/tasks`
- **参数**：无

**返回示例（HTTP 200）**

```json
{
  "code": 200,
  "data": [
    {
      "id": 2,
      "title": "写接口文档",
      "done": false,
      "created_at": "2026-11-15T12:05:47+08:00"
    },
    {
      "id": 1,
      "title": "学习 Flask",
      "done": false,
      "created_at": "2026-11-15T12:05:47+08:00"
    }
  ],
  "msg": "ok"
}
```

```bash
curl -s http://127.0.0.1:5000/api/tasks
```

---

## 2. 新增任务

- **方法**：`POST`
- **路径**：`/api/tasks`
- **参数**：

| 字段 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `title` | body | string | 是 | 任务标题，去除首尾空格后 1–80 个字符 |
| `done` | body | boolean | 否 | 是否完成，默认 `false` |

**返回示例（HTTP 201）**

```json
{
  "code": 201,
  "data": {
    "id": 1,
    "title": "学习 Flask",
    "done": false,
    "created_at": "2026-11-15T12:05:47+08:00"
  },
  "msg": "创建成功"
}
```

**失败示例（HTTP 400）**

```json
{
  "code": 400,
  "data": null,
  "msg": "缺少字段: title"
}
```

```bash
curl -s -X POST http://127.0.0.1:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"学习 Flask","done":false}'
```

---

## 3. 修改任务（加分项）

- **方法**：`PUT`
- **路径**：`/api/tasks/{id}`
- **参数**：

| 字段 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | integer | 是 | 任务 ID |
| `title` | body | string | 二选一 | 新标题，1–80 个字符 |
| `done` | body | boolean | 二选一 | 新的完成状态 |

`title` 与 `done` 至少提供一个；两个都不传返回 400。

**返回示例（HTTP 200）**

```json
{
  "code": 200,
  "data": {
    "id": 1,
    "title": "新标题",
    "done": true,
    "created_at": "2026-11-15T12:05:47+08:00"
  },
  "msg": "更新成功"
}
```

```bash
curl -s -X PUT http://127.0.0.1:5000/api/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"新标题","done":true}'
```

---

## 4. 删除任务

- **方法**：`DELETE`
- **路径**：`/api/tasks/{id}`
- **参数**：

| 字段 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | integer | 是 | 要删除的任务 ID |

**返回示例（HTTP 200）**

```json
{
  "code": 200,
  "data": {
    "id": 1
  },
  "msg": "删除成功"
}
```

**任务不存在（HTTP 404）**

```json
{
  "code": 404,
  "data": null,
  "msg": "任务 999 不存在"
}
```

```bash
curl -s -X DELETE http://127.0.0.1:5000/api/tasks/1
```

---

## 参数校验规则

| 场景 | HTTP 状态码 | `msg` 示例 |
| --- | --- | --- |
| 请求体不是 JSON / JSON 格式错误 | 400 | `请求体必须是合法的 JSON 对象` |
| `Content-Type` 不是 `application/json` | 400 | `Content-Type 必须是 application/json` |
| 缺少 `title` | 400 | `缺少字段: title` |
| `title` 不是字符串 | 400 | `title 必须是字符串` |
| `title` 为空或只有空格 | 400 | `title 不能为空` |
| `title` 超过 80 个字符 | 400 | `title 长度不能超过 80 个字符` |
| `done` 不是布尔值 | 400 | `done 必须是布尔值 true/false` |
| `PUT` 时既没有 `title` 也没有 `done` | 400 | `至少提供 title 或 done 中的一个字段` |
| 任务不存在 / 路由不存在 | 404 | `任务 999 不存在` / `接口不存在` |
| 请求方法不允许 | 405 | `请求方法不允许` |
| 未捕获的服务端异常 | 500 | `服务器内部错误`（不返回堆栈、不返回 HTML） |

校验失败只影响当前请求，不会让服务退出；校验之后继续调用 `GET /api/tasks` 仍然是 200。

---

## 快速验收

```bash
# 1. 列表
curl -s http://127.0.0.1:5000/api/tasks

# 2. 新增
curl -s -X POST http://127.0.0.1:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"学习 Flask","done":false}'

# 3. 删除
curl -s -X DELETE http://127.0.0.1:5000/api/tasks/1

# 4. 故意少传 title，确认是 400 而不是 500
curl -s -X POST http://127.0.0.1:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"done":true}'
```

实测截图与原始终端记录见：

- [三个接口联调](screenshots/api-success.png)
- [参数校验 400](screenshots/api-validation-400.png)
- [重启后数据仍在](screenshots/api-persistence.png)
- 原始文本：[api-success.txt](transcripts/api-success.txt) · [api-validation-400.txt](transcripts/api-validation-400.txt) · [api-persistence.txt](transcripts/api-persistence.txt)
