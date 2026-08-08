# 观茶比赛版集中收口计划

> 状态：审查完成，等待按工作包实施。  
> 基线分支：`codex/phase10-6-competition-mvp-concentrated-closeout`  
> 依据：`docs/COMPETITION_MVP_CONSOLIDATED_AUDIT_2026-08-08.md` 与 `audit/` 下五份只读审查。  
> 目标：收束一条可验证的比赛旅程，而非继续修补单个截图现象。

---

## 1. 统一裁决

### 1.1 根因，不是 Bug 清单

| 根因 | 当前表现 | 必须建立的边界 |
| --- | --- | --- |
| **运行模式没有产品合同** | 未设置环境变量时直接进入 FakeProvider，普通用户看到 `fixture` | 比赛运行时只能显式使用 MiMo；Fake 只允许测试注入或明确内部模式，真实 Provider 失败必须失败且可重试 |
| **浏览器与服务器同时拥有业务事实** | 刷新后候选、图片、Job、Decision 漂移；已完成任务可能不展示 | 服务端拥有 session/candidate/image/job/extraction/decision/questions/replies；浏览器只保留匿名 Client ID、未上传文件、纯 UI 临时状态和茶仓本地记录 |
| **图片集合没有版本语义** | A2 上传后仍展示仅来自 A1 的旧结果；双图来源图错误 | Candidate 图片集合变化立即使 extraction 与 decision stale；同候选 A1+A2 必须成为一次联合请求、一个 current ExtractionVersion，Evidence 必须标明来源图 |
| **后端事实直接作为用户答案** | `fixture`、snake_case、`product-claim / unverified` 等工程细节出现在结果页 | 新增纯映射层 Answer Contract V2；不改 Evidence 数据合同，但普通用户只看到自然语言的结论、依据、不确定项、风险和下一步 |
| **商家回复按“单条即时复判”实现** | 回答 price 等问题却不更新；首条回复使其他候选无法提交 | 每候选分别保存回复，回答本轮真正被问到的候选后，用户显式触发一次汇总复判；生成 V2 与可追溯 Delta |
| **没有固定浏览器验收链路** | 单元测试通过，但用户点击路径反复暴露串线、失效和伪失败 | 以 A/B/C（A 双图、B 双图、C 单图）建立 Fake 自动 E2E 与一次受控 MiMo 人工烟测，作为唯一交付门禁 |

### 1.2 冻结的产品决定

1. 正常比赛用户旅程使用**真实 MiMo**；FakeProvider 仅自动测试和明确内部开发模式使用。
2. 一个 Selection 可有 **1–5 个 Candidate**；每个 Candidate 可有 **1–2 张 JPEG/PNG**。
3. 同 Candidate 的两张图必须在一条 Provider 请求中联合理解；不同 Candidate 的提取严格隔离。
4. 未知字段不等于“无法判断”。只要相对证据足够，仍必须给出“当前相对更适合”的暂定结论，并说明关键不确定项。
5. 商家回复先分别保存；仅对本轮有追问的 Candidate 收齐回复或用户明确跳过后，才显示“更新判断”。
6. UI、视觉资源、页面结构与既有交互路径是基线；本轮只修改数据来源、状态、结果内容组织和必要行为，不重做视觉体系。

---

## 2. 工作包与顺序

实施必须按 `WP1 → WP2 → WP3 → WP4 → WP5`。不能并行修改下列共享文件：

- `app.js`
- `backend/src/guancha_api/application/decision_service.py`
- `backend/src/guancha_api/application/merchant_reply_service.py`

### WP1 — Runtime & Server State Authority

**目标**：消除 Fake-as-live 和浏览器覆盖服务端事实的问题。

**主要文件**：

- `backend/src/guancha_api/main.py`
- `backend/src/guancha_api/api/v1/routes.py`（仅在恢复合同需要时）
- `backend/src/guancha_api/repositories/postgres.py`
- `backend/src/guancha_api/schemas/contracts.py`
- `app.js`
- `api-client.js`
- `stores.js`
- `backend/tests/test_*runtime*`、`frontend/tests/*`

**实施裁决**：

1. `GUANCHA_PROVIDER` 不能静默默认为 Fake；测试通过显式依赖注入 Fake。
2. 实现服务端聚合恢复读取：session → candidates → images → jobs → current extraction → current decision → questions/replies。
3. 前端首次进入选茶页先恢复服务器状态；LocalStorage 只做 UI 缓存，不能覆盖服务器对象。
4. 轮询网络错误应显示网络可重试状态，不得写成业务 `failed`。
5. 删除 Candidate/Image 时取消关联 poller，防止旧回调写回已删除对象。

**验收门禁**：

- 未设置真实 Provider 的比赛模式不能生成 fixture 成功结果。
- 刷新页面后，服务端 completed Job、Extraction、Decision 仍正确恢复。
- 断网轮询不改变服务端 Job 业务终态。

### WP2 — Multi-candidate / Multi-image Pipeline

**目标**：让图片集合、联合提取、Evidence 来源和 stale 语义成为可证明的链路。

**主要文件**：

- `backend/src/guancha_api/providers/openai.py`
- `backend/src/guancha_api/providers/mimo.py`
- `backend/src/guancha_api/application/phase2_service.py`
- `backend/src/guancha_api/application/job_runner.py`
- `backend/src/guancha_api/repositories/postgres.py`
- `backend/src/guancha_api/schemas/contracts.py`
- 对应迁移（仅当当前权威迁移无法表达必要字段时）
- `backend/tests/test_phase3_multi_candidate_multi_image.py`
- `backend/tests/test_mimo_provider.py`

**实施裁决**：

1. Provider 输出合同必须有受约束的 `source_image_index` 或等价图片引用；无法归属的 Evidence 不得伪造为第一张图。
2. 图片集合变化后，旧 current extraction 和 session current decision 同步 stale；联合 Job 失败也不能回退并展示旧集合结论。
3. A1+A2 只产生一个用于当前集合的联合 Provider 调用和一个 current ExtractionVersion。上传图与发起集合提取必须具备明确界限，避免“先单图、后双图”被当作当前联合结果。
4. 每个 Candidate 的 input image IDs、Evidence、ExtractionVersion 和 Decision 输入严格隔离。

**验收门禁**：

- A(2图)、B(2图)、C(1图) 同时存在；每个 Extraction 只读取本 Candidate 图片。
- MiMo adapter 离线测试断言一次请求中带入两张对应图。
- A2 补图后 A1-only Extraction 与 Decision 不可作为 current。

### WP3 — Answer Contract & Decision Presentation

**目标**：恢复“选茶助手”的用户答案组织，而不复制旧系统的 Provider、Prompt、数据库或 UI。

**历史参考**：

- `OLD_WEB_REFERENCE_PATH`: `C:/Users/QQ/Documents/New project/guancha-agent-v0.1/frontend/`
- `OLD_WEB_REFERENCE_COMMIT`: `c4587695735c34871cb9defb0d0a65a95c1a8f38`
- 详细比较：`audit/answer-contract-old-vs-new.md`
- 映射合同：`audit/ANSWER_CONTRACT_V2.md`

**主要文件**：

- `backend/src/guancha_api/application/decision_service.py`
- 新增或既有的 presentation mapper（不得混入 Evidence 持久化层）
- `backend/src/guancha_api/schemas/contracts.py`
- `app.js`（只换数据映射与文案组织，不改页面视觉结构）
- `backend/tests/test_*decision*`、前端结果映射测试

**用户答案最小合同**：

1. 当前结论：如“当前更值得继续考虑”“问清楚再买”“建议先试饮”“暂不建议”。
2. 为什么：最多三条直接关联当前 Need 的理由。
3. 已知事实：3–5 条自然语言事实。
4. 关键不确定项：最多三条、仅保留会改变 Decision 的项。
5. 风险/冲突：自然中文，不泄露内部字段。
6. 下一步：至多一个有 Decision Value 的动作/问题。

**禁止进入普通用户页面**：`fixture`、Provider 名称、raw enum、snake_case、internal score、`product-claim`、`unverified`、原始 Schema 字段名。

**验收门禁**：

- 结果页没有裸工程字段。
- `insufficient-information` 只在真的无区分证据时出现。
- 长文本只在既有滚动区域滚动，不撑坏高保真卡片。

### WP4 — Merchant Reply & Aggregate Rejudgement

**目标**：将“问—答—证据—复判—变化”收束为多候选公平且可追溯的一次复判。

**主要文件**：

- `backend/src/guancha_api/application/question_service.py`
- `backend/src/guancha_api/providers/merchant_reply.py`
- `backend/src/guancha_api/application/merchant_reply_service.py`
- `backend/src/guancha_api/application/decision_service.py`
- `backend/src/guancha_api/repositories/postgres.py`
- `backend/src/guancha_api/schemas/contracts.py`
- `backend/src/guancha_api/api/v1/routes.py`
- `app.js`
- `backend/tests/test_phase6_merchant_rejudgement.py` 及新增聚合测试

**唯一字段注册表**：`price`、`weight_grams`、`tea_subtype`、`aroma_style`、`roast_level`、`season`、`origin_text`、`sample_available`、`return_policy` 必须统一定义：问题文本、可接受答复语义、normalizer、Evidence 映射、Decision 影响。

**实施裁决**：

1. 保存回复不立即使 parent Decision 失效，也不立即全局复判。
2. 每一条回复不可变；解析后追加 `merchant-claim / unverified` Evidence，不能覆盖 `product-claim`。
3. 当本轮有追问的 Candidate 都已回答或明确跳过，才允许一次 aggregate rejudge。
4. aggregate rejudge 在一个明确事务中生成新的 immutable DecisionVersion 和一个可追溯 DecisionDelta（关联本次使用的全部回复）。
5. 结论不变也必须返回自然语言变化说明。

**验收门禁**：

- 上述九个字段皆可问、可解析/标注未答、可规范化并影响或明确不影响 Decision。
- A、B 的回复都能保存；第一条不阻断第二条。
- V1、回复、V2 均不可变；V2 和 Delta 可追溯。

### WP5 — Browser E2E Acceptance

**目标**：把模块测试转换成唯一可复现的比赛验收旅程。

**主要文件**：

- `backend/tests/` 中的真实 PostgreSQL 流程测试
- `frontend/tests/` 中的状态/呈现测试
- 新增受控浏览器 E2E 测试与运行说明（不引入不必要测试框架）
- `docs/` 中的验收运行记录

**固定链路**：

`Need → A(2图)/B(2图)/C(1图) → 全部 Job completed → Extraction → Decision V1 → Questions → A/B（必要时 C）保存回复 → Aggregate Rejudge → Decision V2 → Delta → 当前相对最合适 → 茶仓 → 刷新恢复`

**测试模式**：

- 自动化：明确注入 FakeProvider，0 次真实 MiMo 调用。
- 人工烟测：仅在自动回归全绿后，显式 `GUANCHA_PROVIDER=mimo`，固定 A/B/C 样本且记录 provider/model/processing_mode/image_count/job/version；不记录 Key。

**最终门禁**：

- 后端：真实 `guancha_test`，0 failed、0 skipped。
- 前端：0 failed、JS 语法检查通过。
- 应用导入、OpenAPI、`git diff --check` 通过。
- 最终独立 Reviewer：P0=0、P1=0。

---

## 3. 实施职责与不可并行边界

| 工作包 | 主责任 | 可以并行的只读/测试工作 | 不可并行修改 |
| --- | --- | --- | --- |
| WP1 | Orchestrator | 恢复合同测试、前端状态测试 | `app.js`、`main.py`、`stores.js` |
| WP2 | Orchestrator | MiMo adapter 离线测试 | `phase2_service.py`、`job_runner.py`、`postgres.py`、`contracts.py` |
| WP3 | Orchestrator | 旧版答案映射对照测试 | `app.js`、`decision_service.py` |
| WP4 | Orchestrator | 字段注册表用例与 DB 事务测试 | `merchant_reply_service.py`、`decision_service.py`、`contracts.py` |
| WP5 | Orchestrator | 最终只读 Reviewer | 不改业务文件，只补测试/验收记录 |

每完成一个工作包：只暂存相关文件、运行该包门禁、提交小而可回滚的本地提交；不 push，不 squash 审查历史。

---

## 4. 当前裁决

当前状态是：`NOT_READY_FOR_FINAL_E2E`。

不是因为缺少模型或数据库，而是上述五个根因尚未统一收口。先完成 WP1 和 WP2，才能可信地进入用户答案和汇总复判；否则继续调 UI 或单条回复只会重复制造“已上传、却无法分析/更新”的现象。
