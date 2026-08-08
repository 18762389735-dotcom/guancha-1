# 观茶比赛版运行说明

> 当前范围为最多 5 个候选茶、每个候选最多 2 张截图。本文替代早期“单候选/单图”描述；完整当前状态见 [CURRENT_STATE.md](CURRENT_STATE.md)。

## 1. 本地 Fake 模式

Fake 模式仅用于本地开发和离线演示：不读取 API Key、不访问外网。

```powershell
$env:GUANCHA_DATABASE_URL = '<local-postgresql-url>'
$env:GUANCHA_PROVIDER = 'fake'
backend\.venv\Scripts\python.exe backend\scripts\run_local.py
```

打开 `http://127.0.0.1:8000`。应用同源提供现有静态前端。

## 2. 本地真实 Provider 模式

真实模式只用于手动验证或比赛公网版本。安装可选依赖并在服务端终端设置：

```powershell
backend\.venv\Scripts\python.exe -m pip install -e "backend[openai]"
$env:GUANCHA_DATABASE_URL = '<postgresql-url>'
$env:GUANCHA_PROVIDER = 'openai'
$env:GUANCHA_OPENAI_MODEL = '<vision-model-name>'
$env:OPENAI_API_KEY = '<set-locally-only>'
backend\.venv\Scripts\python.exe backend\scripts\run_local.py
```

每个 Job 只会发起一次多模态模型调用。自动测试始终使用 FakeProvider。详细的单次烟测命令见 [REAL_PROVIDER_SMOKE.md](REAL_PROVIDER_SMOKE.md)。

MiMo 使用同一可选 SDK 依赖，但配置为：

```powershell
backend\.venv\Scripts\python.exe -m pip install -e "backend[openai]"
$env:GUANCHA_DATABASE_URL = '<postgresql-url>'
$env:GUANCHA_PROVIDER = 'mimo'
$env:GUANCHA_MIMO_MODEL = 'mimo-v2.5'
$env:MIMO_API_KEY = '<set-locally-only>'
backend\.venv\Scripts\python.exe backend\scripts\run_local.py
```

不要把任何变量值写入前端、Git、截图或日志。

## 2.1 固定演示降级模式

若真实 Provider 超时、不可用或返回不合格结构化结果，服务只会对项目自有、已批准且经安全预处理后 SHA-256 **精确命中**的 A/B/C 固定图片使用 `cache-fallback`。它不是任何图片的通用识别结果，也不会把 FakeProvider 伪装成实时 AI。管理员可用 `ADMIN_API_TOKEN` 查看 Job 与调用日志中的处理模式；演示前运行 `backend/scripts/demo_preflight.py` 检查 fixture 完整性。

## 3. 生产启动

仓库提供单一托管入口 [Procfile](../Procfile)：

```text
uvicorn guancha_api.main:app --app-dir backend/src --host 0.0.0.0 --port $PORT
```

托管平台需要设置：`PORT`、`GUANCHA_DATABASE_URL`、`GUANCHA_PROVIDER`；使用 OpenAI 时还需 `GUANCHA_OPENAI_MODEL` 与 `OPENAI_API_KEY`，使用 MiMo 时还需 `GUANCHA_MIMO_MODEL` 与 `MIMO_API_KEY`。不要将它们写入部署文件或 Git。

## 4. 点击路径

1. 首页填写最小偏好；
2. 添加 1–5 个候选茶；每个候选上传 1–2 张 JPEG/PNG 商品截图；
3. 点击“开始分析”，等待每个候选的提取 Job 完成；
4. 查看候选比较、基本信息、风险提示和商品页证据；
5. 必要时发起追问、提交商家回复并查看复判变化；
6. 点击“加入茶仓”，在茶仓页面确认本地记录；
7. 刷新页面，茶仓记录仍保存在浏览器本地存储。

## 5. 常见错误

- 图片不合格：选择 JPEG/PNG，且单张不超过 5MB。
- 分析失败：检查后端、数据库与 Provider 后重试；不应把本地预览误认为分析成功。
- 网络或服务不可用：确认后端与数据库可访问，再重试。

## 6. 当前比赛版限制

- 最多 5 个候选、每个候选最多 2 张图片；不支持第三张图片、独立 OCR 或云端账户。
- 茶仓仅保存在浏览器本地，不支持账号或跨设备同步。
- 临时私有图片使用进程内存存储；服务重启后，正在处理或可重试的上传可能丢失。这是比赛版 P2 限制，不适合生产。
