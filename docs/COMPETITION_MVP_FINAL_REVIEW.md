# 观茶比赛版最终独立复审

- 审查角色：`FINAL_REVIEWER`（只读；本文件是本次唯一审查写入）
- 分支：`codex/phase10-6-competition-mvp-concentrated-closeout`
- 复审对象：当前未提交的 competition MVP closeout 变更
- 复审日期：2026-08-08
- 结论：**READY_FOR_FINAL_E2E（PASS）**

## 结论

本次复审未发现会阻断比赛主旅程的 P0 或 P1。此前两个阻断项均已闭环：

1. `POST /api/v1/selection-sessions/{session_id}/rejudge` 现在是无客户端选择输入的 aggregate action。`CreateRejudgeRequest` 是空对象，`ContractModel(extra="forbid")` 会拒绝旧的 `merchant_reply_id`；OpenAPI 中也不再公开该字段。服务端通过当前 decision 下的已保存回复集合选择内部 audit anchor，避免回到“单条回复驱动整体复判”。
2. 本次已提供并核对真实本地浏览器执行证据：在本地 FastAPI + FakeProvider 环境，实际新建 A/B/C 三个候选、各上传一张真实本地测试截图、启动“三款茶”分析、展示中文 Answer V2 且不出现 `fixture`、暂时加入茶仓、标记已买到、确认并刷新；刷新后茶仓仍保留“安溪铁观音”。这补足了此前只存在 ASGI/Node 合同测试、缺少真实 DOM/页面跳转/刷新操作证据的问题。

**P0 = 0，P1 = 0，故判定 PASS。** `READY_FOR_FINAL_E2E` 表示可以进行最后一次经明确授权的真实 MiMo 人工烟测；自动测试与日常本地演示仍使用 FakeProvider，不应消耗真实 API。

## 实测证据

在专用 `guancha_test` PostgreSQL 数据库上执行（凭据未读取、未输出、未写入仓库）：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
node --test frontend\tests\*.test.js
backend\.venv\Scripts\python.exe -m pytest `
  backend\tests\test_competition_acceptance_flow.py `
  backend\tests\test_phase4_decision_api.py `
  backend\tests\test_phase6_merchant_rejudgement.py -q
backend\.venv\Scripts\python.exe -c "from guancha_api.main import create_app; print(len(create_app().openapi()['paths']))"
node --check app.js
node --check frontend/api-client.js
git diff --check
```

| 验证项 | 结果 |
| --- | --- |
| 后端全量（真实 PostgreSQL） | **243 passed，0 failed，0 skipped** |
| 前端 Node 合同测试 | **15 passed，0 failed，0 skipped** |
| 当前关键 Decision / replies / aggregate rejudge 回归 | **16 passed** |
| OpenAPI 生成 | 成功，26 paths |
| rejudge 公共 contract | 不含 `merchant_reply_id` |
| JavaScript 语法与 diff whitespace | 通过 |
| 真实浏览器本地流程 | 已执行并通过（A/B/C、上传、分析、Answer V2、茶仓、刷新） |

后端仍输出 955 条 Python 3.16 / pytest-asyncio / Starlette 弃用警告；它们不改变本轮功能测试结果，列为 P2。

## 旅程逐项核对

| 目标节点 | 代码与测试证据 | 判定 |
| --- | --- | --- |
| Need | `Phase2ExtractionService` 的会话创建与 PostgreSQL API 回归 | PASS |
| 1–5 Candidates | `backend/tests/test_competition_acceptance_flow.py` 的 A/B/C 真实数据库流程；产品上限继续由合同约束 | PASS |
| 每候选 1–2 图片 | `analysis_jobs.input_image_ids`；验收测试覆盖 A(2)/B(2)/C(1) 并保持来源隔离 | PASS |
| MiMo / Fake 边界 | `main.py:_provider_from_environment()`：未配置 Provider 为失败路径，Fake 仅显式选择；无运行时 `DemoFallback` 成功回退 | PASS |
| Evidence | 图片来源的 Evidence 保持冻结的 `product-claim` / `unverified` 边界；同候选双图写入 `source_image_ids` / 索引 | PASS |
| Decision V1 与 Answer V2 | Decision API、`answer_contract.py` 与 `test_phase4_decision_api.py`；正常页面走 Answer V2 | PASS |
| 决策价值 Questions | Question service 和 Phase 5 回归；不把工程内部字段作为普通用户答案 | PASS |
| Merchant reply | 前端按 `followup_question_id` 保存；服务端 append-only reply / claim | PASS |
| 一次 aggregate rejudge | `merchant_reply_service.py:rejudge()` 通过 `aggregate_rejudge_anchor()` 聚合当前决策的完整回复集；关键真实 PostgreSQL 回归通过 | PASS |
| DecisionDelta / 当前相对最优 | `complete_aggregate_merchant_rejudgement()` 原子写入 V2、Delta 与完成 Job；Answer 映射读取当前 Decision | PASS |
| 硬刷新恢复 | `selection_snapshot_for_client()` 返回 questions、replies、rejudge job、delta；`app.js:resumeLiveBackendState()` 以服务端 snapshot 恢复 terminal `completed`，不再由 localStorage 决定 | PASS |
| 茶仓与刷新 | `GuanchaStores.localPostPurchase` 的持久化测试，以及本次真实浏览器“加入 → 已买到 → 确认 → 刷新”执行记录 | PASS |

## 本次针对旧问题的确认

### 服务端 snapshot 是恢复事实源

`backend/src/guancha_api/repositories/postgres.py:selection_snapshot_for_client()` 同时读取 session、candidates、V1 questions、merchant replies、最近 rejudge job 和 V2 delta。对于 aggregate rejudge 已完成的情形，它会沿 immutable parent decision 取回问题与回复；`app.js` 据此恢复 `completed`，不会在硬刷新后错误回到 `ready`。

### 多问题按 question 粒度完成

`app.js` 对一个候选的所有未答 question 分别创建 reply，并以所有 `followup_question_id` 是否已保存判断是否可进入 aggregate rejudge。Repository 的 gate 也以 question 集合验证，不再把“某候选已有一条回复”误当成全部完成。

### 公共 rejudge 不再信任客户端挑选输入

`backend/src/guancha_api/schemas/contracts.py:CreateRejudgeRequest` 没有字段；`ContractModel` 使用 `extra="forbid"`。路由只把 session、client 和 idempotency key 交给应用服务。内部 `merchant_reply_id` 仅作为既有数据库审计/唯一性锚点保存，客户端无法指定它。

### 默认 Fake 不再泄漏 fixture 文案

`main.py` 的未配置 Provider 分支是显式失败，不会静默回退成功；显式 Fake 分支的展示数据不再使用 `fixture` 文案。正常结果页消费 Answer V2；`legacyResultDataForDebugOnly()` 没有调用点。

## 问题分级

### P0

无。

### P1

无。

### P2（不阻塞比赛验收）

1. `app.js` 仍保留无调用点的 `legacyResultDataForDebugOnly()`。建议在后续清理，避免未来误接回硬编码展示数据。
2. 前端仍缓存部分 bridge 状态以改善交互；恢复时已经由服务端 snapshot 覆盖，因此不是业务事实源。后续可继续缩小该缓存面。
3. Python 3.16 环境的 asyncio / pytest-asyncio / Starlette 弃用警告共 955 条，需要在比赛后统一升级/迁移，但当前不影响测试、API 或浏览器主路径。
4. 比赛版茶仓为 local-first，无登录/跨设备同步；这是已知 MVP 边界，不影响当前演示。

## 最终限制与下一步

本审查没有执行真实 MiMo 网络调用，也没有读取任何 API Key。自动回归与本地浏览器验收保持 FakeProvider；下一步仅应在用户明确授权后，用固定 A/B/C 截图执行一次受控 MiMo 人工烟测，核对真实 Provider 的输出质量和超时/重试体验。
