# 固定演示缓存降级

阶段 8 只为项目自有的 A/B/C PNG fixture 提供可靠演示降级。上传仍先经过同一图片安全管线；只有已配置的真实 Provider 失败、规范化后的图片集合 SHA-256 精确匹配 manifest、且 fixture 标记为批准时，才会生成 `cache-fallback` ExtractionVersion。

这不是通用图片识别，也不会根据文件名、候选名、OCR 文本或近似图片匹配。任意非 fixture 图片在 Provider 失败时会正常失败。

处理模式可在受 `ADMIN_API_TOKEN` 保护的 `/api/v1/admin/jobs` 与 `/api/v1/admin/ai-calls` 查看：`live-ai`、`cache-fallback`、`test-fixture` 与 `fake-provider` 保持可区分。自动测试只使用 FakeProvider，不读取或调用真实 OpenAI。

离线演示前可运行：

```powershell
$env:PYTHONPATH = 'backend/src'
backend/.venv/Scripts/python.exe backend/scripts/demo_preflight.py
```

该脚本只报告环境变量是否存在，绝不输出其值。
