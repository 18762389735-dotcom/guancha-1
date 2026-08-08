# 观茶项目工作约定

## 项目定位

比赛演示原型：用户可创建一次选茶会话，添加最多 5 个候选茶、每个候选最多 2 张 JPEG/PNG 商品截图，完成截图提取、候选比较、追问和商家回复复判。

## 常用命令

```powershell
$env:GUANCHA_DATABASE_URL = '<local-postgresql-url>'
$env:GUANCHA_PROVIDER = 'fake'
backend\.venv\Scripts\python.exe backend\scripts\run_local.py
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
node --check app.js
node --test frontend/tests/*.test.js
```

真实 Provider 只能通过环境变量启用；自动测试始终使用 `fake`，不得读取或提交任何 API Key。

## 目录与边界

- `app.js`、`styles.css`、`index.html`：已验收的高保真前端基线。
- `frontend/`：唯一允许替换 mock/调用 API 的前端边界。
- `backend/src/guancha_api/`：FastAPI、PostgreSQL、Provider、任务和私有图片存储。
- `docs/CURRENT_STATE.md`：当前能力与运行方式的唯一简明说明；旧阶段文档仅作历史对照。

## 不可违反的约定

- 不得顺手改变页面结构、CSS、视觉资产、按钮文案、跳转路径或既有交互。
- 候选卡可在上传后用实际截图预览替代占位插图；单个候选的“补充截图”加号是唯一已授权的局部 UI 调整。
- 不得把 Provider Key、数据库 URL、用户截图、日志或本机绝对路径提交到 Git。
- 不接入真实 Supabase；真实 Provider 调用必须是用户明确发起的人工烟测。
