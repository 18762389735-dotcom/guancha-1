# 真实 Provider 手动烟测

> 本脚本仅覆盖 OpenAI。当前服务端也支持 MiMo（`GUANCHA_PROVIDER=mimo`、`MIMO_API_KEY`、`GUANCHA_MIMO_MODEL`），但仓库内尚无 MiMo 专用烟测脚本；可按 [MVP_RUNBOOK.md](MVP_RUNBOOK.md) 启动服务后从现有前端手动验证。两种 Provider 都不得由 pytest 或 CI 调用。

这是唯一允许调用真实多模态模型的手动入口；普通 pytest 和 CI 始终使用 FakeProvider。

## 准备

```powershell
backend\.venv\Scripts\python.exe -m pip install -e "backend[openai]"
$env:GUANCHA_PROVIDER = 'openai'
$env:GUANCHA_OPENAI_MODEL = '<vision-model-name>'
$env:OPENAI_API_KEY = '<set-locally-only>'
```

## 执行

```powershell
backend\.venv\Scripts\python.exe backend\scripts\smoke_openai_extraction.py <path-to-product.png>
```

成功时只会输出茶名、类别、产地、价格、风险和 Evidence 数量的摘要。每次执行只调用一次模型，不打印密钥、原始模型回复或图片内容。

## 常见失败

- 缺少环境变量：脚本会提示所需变量名，不会显示其值。
- 图片不是 JPEG/PNG：脚本拒绝执行。
- 超时、限流或 Provider 不可用：请求失败；Web Job 会进入 `failed`，不会写入半成品版本。
- 结构化输出不合法：Web Job 会进入 `failed`，不会猜测或补全字段。
