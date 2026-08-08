# 观茶比赛版原型

这是一个本地优先的比赛演示原型：匿名用户可建立一次选茶会话，添加 1–5 个候选茶、每个候选上传 1–2 张 JPEG/PNG 商品截图，并分别生成可追溯的提取任务与证据结果。

当前实现使用 FastAPI、PostgreSQL、私有临时图片存储边界和 FakeProvider。自动测试不会访问外部模型；真实 `openai` 或 `mimo` Provider 只能由服务端环境变量显式启用。

当前能力、运行方式、前端基线和已知限制见 [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)。旧阶段文档保留作历史对照，不应覆盖当前代码事实。

## 当前能力

- 候选数量：每个会话最多 5 个；每个候选最多 2 张截图。
- 第二张同候选截图会生成新的联合提取任务；旧 ExtractionVersion 保留，新版本才是当前结果。
- 多候选相互隔离；证据始终绑定到本次任务输入图片，并强制标记为 `product-claim` / `unverified`。
- 已删除图片或候选不会继续作为当前提取结果。
- 候选提取完成后可生成当前比较结果、最小追问、商家回复与一次聚合复判；复判结果以 Delta 形式保留，不覆盖原始证据。
- 前端保留既有界面，只接通候选、图片、状态与结果数据；茶仓仍是本地优先功能。

## 本地运行

先建立后端虚拟环境并安装项目声明的开发依赖：

```powershell
py -3.14 -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -e "./backend[dev]"
```

设置本地测试或开发数据库 URL 后，以 FakeProvider 启动：

```powershell
$env:GUANCHA_DATABASE_URL="postgresql://<user>:<password>@127.0.0.1:5432/<database>"
$env:GUANCHA_PROVIDER="fake"
backend/.venv/Scripts/python -m uvicorn guancha_api.main:app --app-dir backend/src --host 127.0.0.1 --port 8000
```

浏览器访问 `http://127.0.0.1:8000/`；健康检查与 OpenAPI 分别位于 `/health`、`/openapi.json`。

运行测试时，`TEST_DATABASE_URL` 必须指向一个可安全重建 schema 的独立 PostgreSQL 测试数据库：

```powershell
$env:TEST_DATABASE_URL="postgresql://<user>:<password>@127.0.0.1:5432/<test_database>"
$env:GUANCHA_DATABASE_URL=$env:TEST_DATABASE_URL
backend/.venv/Scripts/python -m pytest backend/tests -q
node --check app.js
node --test frontend/tests/mvp-client.test.js
```

## 目录

- `app.js`、`index.html`、`styles.css`：现有比赛版界面。
- `frontend/`：API Client、Adapter、状态与本地存储边界。
- `backend/src/guancha_api/`：FastAPI、应用服务、Repository、Provider、任务执行器与图片存储接口。
- `supabase/migrations/`：仅用于本地 PostgreSQL 测试和未来迁移的 SQL；当前不连接真实 Supabase。
- `backend/tests/`：合同、Repository、图片管线、任务与多候选/双图回归测试。

## 已知限制

- 当前仅覆盖铁观音比赛范围；不做登录、云端茶仓、独立 OCR、第三张以上图片、跨会话长期账号数据、泡茶日记或买后分析。
- 自动测试只使用 FakeProvider，不会读取或请求 OpenAI Key。
- 私有规范化图片会保留到用户删除对应图片或候选，以便第二张图能与第一张图联合提取；没有生产级过期清理器。
- 尚未连接真实 Supabase、云对象存储或生产队列。
