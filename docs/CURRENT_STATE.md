# 观茶比赛版当前状态

更新日期：2026-08-08。本文是当前能力、运行方式和开发边界的简明权威说明；阶段计划、旧审计和历史 PRD 溯源文档只用于对照，不覆盖本文。

## 已实现

- 匿名选茶会话、最多 5 个候选茶、每个候选最多 2 张 JPEG/PNG 商品截图。
- 安全图片预处理、私有临时存储、持久化 Job、Extraction/Evidence、候选比较、追问、商家回复与复判 Delta。
- 候选卡在当前浏览会话中优先显示已上传截图预览；未上传时才使用原有插图占位。
- FastAPI、PostgreSQL、同源静态前端，以及 FakeProvider 的离线可测闭环。
- 可选真实 Provider：`openai` 和 `mimo`。自动测试不会读取 Key，也不会访问外网。

## 运行方式

本地 Fake 演示：

```powershell
$env:GUANCHA_DATABASE_URL = '<local-postgresql-url>'
$env:GUANCHA_PROVIDER = 'fake'
backend\.venv\Scripts\python.exe backend\scripts\run_local.py
```

浏览器访问 `http://127.0.0.1:8000/`。

真实 MiMo 演示需在服务端环境设置 `GUANCHA_PROVIDER=mimo`、`MIMO_API_KEY`、`GUANCHA_MIMO_MODEL`；真实 OpenAI 演示需设置 `GUANCHA_PROVIDER=openai`、`OPENAI_API_KEY`、`GUANCHA_OPENAI_MODEL`。不要将变量值写入文件、Git、前端或日志。

## 验证命令

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
node --check app.js
node --test frontend/tests/*.test.js
```

后端测试会重建由 `TEST_DATABASE_URL` 指向的测试数据库 schema；只能指向独立测试库。

## 固定边界

- 前端视觉与交互是基线。后端接入只能替换 `frontend/` 的数据读取与动作调用，不得重写页面、样式、文案或导航。
- 已授权的局部视觉行为仅包括：上传后候选卡使用真实截图预览，以及同一候选“补充截图”的小加号入口。
- 不实现登录、云端茶仓、独立 OCR、第三次以上图片、超出 5 个候选的比较、真实 Supabase 或生产级队列。

## 已知限制

- 临时图片存储为进程内实现；服务重启会影响尚未完成或仍可重试的 Job。
- 真实 Provider 是手动、付费且依赖网络的能力；本地离线演示使用 FakeProvider。
- 旧阶段文档中出现的“单候选/单图/仅 OpenAI”描述已经过时，以本文和代码为准。
