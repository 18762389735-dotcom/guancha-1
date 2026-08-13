# 观茶当前工程事实审计

审计日期：2026-08-13  
代码边界：`cabc959`  
Phase 15 报告边界：`84f1435`

## 结论

当前代码门可判定为通过，但发布门仍依赖数据库和浏览器验收。工程结论为：`PASS_WITH_DB_BROWSER_VALIDATION_REQUIRED`。

## 当前架构

当前系统不是一条“图片 → MiMo → 推荐”的简单直线，而是两条相交管线：

1. **证据管线**：图片上传 → extraction job → 结构化字段/evidence → 感官解释。
2. **决策管线**：Selection Need + 当前证据 + 有边界偏好 → 规则行动档位/排序 → Question counterfactual → MerchantReply parse/claim merge → aggregate rejudge → Delta。

前端为轻量静态应用；后端为 FastAPI；持久业务状态使用 PostgreSQL repository；图片采用临时存储，不写入数据库。任务执行支持 in-process/manual runner，进程内按 job ID 去重，但不是多实例持久队列。

## Architecture Layers

| Layer | Current responsibility | Must not do | Status |
|---|---|---|---|
| Frontend | Need/候选输入、展示、业务动作 | 不持久敏感树或伪造 server outcome | `IMPLEMENTED_VERIFIED` |
| FastAPI | 合同、所有权、任务与复判编排 | 不让 telemetry 失败改变业务 | `IMPLEMENTED_VERIFIED` |
| Provider / Extraction | 结构化理解图片/自然语言 | 不直接排序、写库或确认营销词 | `IMPLEMENTED_PARTIALLY_VERIFIED` |
| Evidence | 来源、状态、验证、冲突 | 不混淆 product/merchant/inference | `IMPLEMENTED_VERIFIED` |
| Sensory / Personal Fit | 受控感官语言、Need-first 适配 | 不预测必然喝感或让偏好越权 | `IMPLEMENTED_VERIFIED` |
| Decision | 规则档位与同档排序 | 不输出伪 AI 总分 | `IMPLEMENTED_VERIFIED` |
| Question / MerchantReply | 反事实问题价值、逐题回复解析 | 不把完整度当价值或声明当事实 | `IMPLEMENTED_PARTIALLY_VERIFIED` |
| Rejudge / Version / Delta | 聚合证据、V1/V2 与变化 | 不做一答一推荐或称整行 immutable | `IMPLEMENTED_PARTIALLY_VERIFIED` |
| Persistence / PostgreSQL | 权威业务状态与 lineage | 不存图片；不由 localStorage 掌权威 | `IMPLEMENTED_PARTIALLY_VERIFIED` |
| Analytics | 匿名、闭集、fail-open 事件 | 不参与 Decision 或冒充真实使用 | `IMPLEMENTED_VERIFIED` |

## Provider 事实

- extraction 代码支持 unavailable、fake、OpenAI、MiMo 兼容配置。
- 当前文档目标偏向 MiMo，但实际运行时 provider/model 未核验。
- Question 与 MerchantReply 默认实现是确定性的 fake/rule provider，不应描述为所有环节均调用生成式模型。
- Phase 15 没有真实 provider 调用；历史 smoke 不能替代当前 commit 验证。

## 数据与版本

主要实体包括 clients、selection sessions、candidates、candidate images、analysis jobs、extractions、evidence、AI call logs、decision versions、candidate decisions、question generation runs、follow-up questions、merchant replies、merchant claims、decision deltas、brew feedback replay 和 migrations。

CandidateDecision 内容按版本保存。旧 DecisionVersion 的 `status`/`is_current` 等生命周期字段可以变化，因此准确说法是“决策内容形成可追溯快照”，而不是“整行绝对不可变”。

## 状态权威与恢复

- 服务端 snapshot/current decision/answer/delta 是活跃选择流程的恢复权威。
- 浏览器 localStorage 只保存闭集、安全的 anchor，不保存 Need 原文、完整商家回复、提取证据、问题树、Answer 或 Delta 树。
- selection bridge schema v3、UI session、preference evidence 和 post-purchase store 均按字段投影。
- IndexedDB 用于待上传图片临时缓存；当前没有 TTL/eviction，属于 P2。
- active candidate 使用稳定 candidate identity，而不是只保存数组索引。
- 正常 reopen 回 Home；active reload 根据权威 snapshot 恢复。

## 幂等与可观测性

- create session/candidate/image 的 `created` edge 传递到事件层，避免 replay 产生重复 server event。
- task runner 对 pending/active job ID 做进程内去重；shutdown 会释放集合。
- session decision、merchant reply 和 rejudge 的事件由真实创建/终态边界触发。
- 数据库 same-key replay 与并发 exactly-once 仍因缺少测试数据库而 BLOCKED。
- Product Analytics 有 13 个 client interaction 与 13 个 server-authoritative 事件；严格 allowlist，默认 JSONL/stdout，可选文件，fail-open，不写业务表、不影响决策。

## 部署与运行

- 本地默认后端端口为 8000。
- Dockerfile 以 Python 3.13 构建，容器默认读取 `PORT`，缺省 8080；启动前运行 migrations，再启动 uvicorn。
- Procfile 使用 `$PORT`。
- 这些文件说明部署形态兼容容器/进程平台，但不能据此确认当前平台是 Render、Vercel 或其他服务。
- 当前实际 platform、port、provider、model、数据库 host 和 deployed commit 均为 `UNCONFIRMED`。

## 当前测试矩阵

| Gate | 当前证据 | 状态 |
|---|---:|---|
| Frontend tests | 61/61 | PASS |
| Backend tests | 228 PASS / 76 SKIP | PARTIAL；DB SKIP |
| AI Eval | 26 PASS / 0 FAIL / 4 BLOCKED | PARTIAL；DB BLOCKED |
| Privacy focused | 26/26，P0/P1=0 | PASS |
| Node syntax / Python AST | 通过 | PASS |
| `git diff --check` | 通过 | PASS |
| PostgreSQL full chain | 未运行 | BLOCKED |
| Browser full E2E | 未运行成功 | BLOCKED |
| Live provider on current commit | 0 calls | UNCONFIRMED |

## 当前 P2 与限制

- IndexedDB 图片缓存无 TTL/eviction。
- 临时图片存储和 in-process runner 对进程重启、多实例不耐久。
- Analytics retention/rotation 未配置。
- Merchant draft/ask overlay 不做持久恢复。
- 隐私优先迁移会丢弃旧自由文本 history 名称。
- 演示 seed 可能被误读为真实用户数据。
- 旧浏览器审计记录过短屏遮挡、触控尺寸、装饰层重叠、favicon/public config 404 和大 PNG；这些在当前 commit 尚未重新核验，只能列作待复验 P2，不能写成当前已确认缺陷或已修复。

## 工程非目标

- 不建设登录、支付、生产级权限和多租户。
- 不建设高并发、多实例持久任务平台。
- 不把 analytics 用作安全审计日志或决策输入。
- 不建设第三方 BI、A/B 平台或用户画像。
- 不承诺图片永久保存、跨设备同步或生产级灾备。

## 未决工程事实

1. 实际部署环境与 commit。
2. 当前运行 provider/model。
3. 当前数据库托管商与 schema 状态。
4. PostgreSQL 真实状态矩阵与 exactly-once。
5. 浏览器端 active reload、主链和移动端表现。
