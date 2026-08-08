# 商家回复与统一复判只读审查

审查日期：2026-08-08  
审查范围：`question_service`、商家回复解析 Provider、`merchant_reply_service`、Merchant Evidence 追加、`DecisionVersion` 与 `DecisionDelta`。  
审查方式：只读代码与迁移审查；**没有调用真实 MiMo、没有修改业务代码或既有文档**。

## 结论

现有实现具备“**一条回复 → 解析 → 立刻重判 → 新 DecisionVersion / DecisionDelta**”的最小技术链路，但它不是比赛流程需要的“**分别保存各候选回复 → 收齐本轮需要的回复（或明确跳过）→ 一次统一复判**”。

更关键的是，`FakeMerchantReplyReasoningProvider` 只真正识别 `roast_level`、`season`、`sample_available` 三类字段；而提问层可以问价格、香型、退换、产地、净含量等。于是用户回答“到手价 128 元”时，当前代码通常把它归为 `partially-answered`，不追加 Merchant Evidence，也不生成新判断。这与浏览器中“已提交但判断没有更新”的现象一致。

## 当前链路（代码证据）

```text
QuestionGenerationService.generate()
  → followup_questions（最多 3 条）
  → POST /selection-sessions/{session}/merchant-replies
  → merchant_replies（仅保存 raw_text）
  → POST /selection-sessions/{session}/rejudge { merchant_reply_id }
  → 每条 reply 独立创建 analysis_jobs(job_kind=merchant_rejudgement)
  → FakeMerchantReplyReasoningProvider.parse_merchant_reply()
  → complete_merchant_rejudgement()
     → merchant_claims + evidence_items（追加到旧 ExtractionVersion）
     → V1 stale；新建 DecisionVersion V2
     → 新建一个 DecisionDelta（只关联一条 reply）
```

关键位置：

- `backend/src/guancha_api/application/question_service.py:13-24`：允许提问的字段标签。
- `backend/src/guancha_api/domain/tieguanyin/questioning.py:10-20`：可做反事实模拟的 `ANSWER_BRANCHES`。
- `backend/src/guancha_api/application/merchant_reply_service.py:31-46`：重判 API 的输入就是单个 `reply_id`。
- `backend/src/guancha_api/application/merchant_reply_service.py:51-109`：每个 Job 只 claim / parse 一条回复，并立即计算新判断。
- `backend/src/guancha_api/providers/merchant_reply.py:29-41`：当前 Fake 解析器的实际覆盖范围。
- `backend/src/guancha_api/repositories/postgres.py:1012-1087`：一个事务内创建 Merchant Claim、追加 Evidence、废弃旧 Decision、创建新 Decision / Delta、完成 Job。
- `supabase/migrations/20260805140000_phase6_merchant_rejudgement.sql:8-55`：当前表与单回复 Delta 约束。

## QUESTION → REPLY → EVIDENCE → DECISION 覆盖矩阵

说明：

- “能问”是指字段在当前候选生成规则中有声明；实际是否被问仍取决于反事实价值、当前 Evidence、最多 3 问限制。
- “解析”仅指当前实际运行的 `FakeMerchantReplyReasoningProvider`，不是设想中的未来真实解析器。
- “证据”指在 Parser 真正返回 claim 的前提下，Repository 是否能以 `merchant-claim / unverified` 写入。
- “影响判断”指 `evaluate_candidate()` 或规则是否读取该字段，而不是“理论上可能有意义”。

| 字段 | 能问 | 当前解析 / 规范化 | 可写 `merchant-claim / unverified` | 当前能影响 Decision | 审查结论 |
|---|---|---|---|---|---|
| `price` | 是 | **否**；没有价格数值提取或币种/单位校验 | 机制上可以，实际 Parser 不会产出 claim | 是；`decision.py:64-68,81,175-179` 使用真实可转 Decimal 的价格 | **P0**：最常问、最影响预算，却无法闭环 |
| `weight_grams` | 是 | **否**；没有克/斤/盒数规范化 | 机制上可以，实际不会写入 | 否；当前规则和评分未读取 | **P1**：可问但对当前 Decision 没有可证明影响 |
| `tea_subtype` | **否**；系统内部用的是 `tea_type` | 否 | 否；Phase 6 DB check 不接受 `tea_subtype` | 否；核心字段是 `tea_type` | **P1**：契约命名不一致，不能把“具体茶类”作为闭环字段 |
| `aroma_style` | 是 | **否**；无清香/浓香/陈香等映射 | 机制上可以，实际不会写入 | 是；`decision.py:77,160` | **P0**：可问却无法用于偏好匹配 |
| `roast_level` | 是 | 是；仅识别轻/中/足火 → `light/medium/heavy` | 是；显式、merchant-claim、unverified、medium | 是；`decision.py:78,157-158` | 当前唯一完整的体验关键字段链路之一 |
| `season` | 是 | 是；仅识别春茶/秋茶 → `spring/autumn` | 是 | 是；核心完整性字段 | 当前可闭环，但分支没有对“其他季节”做自然语言解析 |
| `origin_text` | 是 | **否** | 机制上可以，实际不会写入 | 否；当前规则不读取 | **P1**：可问不可解析，且对 Decision 无显式规则 |
| `sample_available` | 是 | 是；仅识别“小样”/“试饮” → `true` | 是 | 是；探索型用户与预算风险读取 | 基本可闭环；不能可靠解析“不提供/无小样” → `false` |
| `return_policy` | 是 | **否** | 机制上可以，实际不会写入 | 否；当前规则不读取 | **P1**：提问价值配置称其重要，但判断函数完全忽略 |

补充不一致：

1. `question_service.py` 的 `FIELD_LABELS` 和数据库 `merchant_claims.field_key` 支持 `price`、`weight_grams` 等；但 `merchant_reply.py:35` 的 `values` 仅列出三项。
2. `ANSWER_BRANCHES` 有 `aroma_style`、`price`、`return_policy` 等，模拟时可算“影响”；真实回复解析时却不能达到对应分支。这会导致“问题看起来有价值，真实回答却无法改变判断”。
3. `tea_subtype` 是视觉/提取层常见字段名，但决策层的核心字段是 `tea_type`；没有显式映射。它不是同一字段的可互换别名。

## 已存在的正确边界

以下部分值得保留，不能在后续收口中退化：

1. **原始回复可追溯**：`merchant_replies.raw_text` 保存原文，按匿名 Client 与 follow-up question 做幂等。
2. **证据可信度未被错误提升**：`complete_merchant_rejudgement()` 强制写入 `source_type='merchant-claim'`、`verification_status='unverified'`；与产品证据原则一致。
3. **冲突不覆盖商品页声明**：与既有 `product-claim` 同字段值不同，会新增 `information_status='conflict'`，并关联 `conflicts_with_evidence_id`，而非覆盖原证据。
4. **单条完成事务具备原子性**：当前 `complete_merchant_rejudgement()` 在一个 PostgreSQL transaction 内写 Claim、Evidence、DecisionVersion、CandidateDecision、DecisionDelta、Reply / Job 终态；异常不会留下该条回复的半成品 V2。
5. **历史 Decision 有父链**：迁移已提供 `parent_decision_version_id`、`trigger_type`、`trigger_resource_id`；可用于扩展成汇总复判而不推翻版本血缘。

## P0：阻止比赛流程正确性的缺陷

### P0-1：大部分已提问题无法被实际解析，提交后自然不会更新判断

**证据**：

```python
# providers/merchant_reply.py:35
values = {
  'roast_level': [...],
  'season': [...],
  'sample_available': [...],
}
```

而 `question_service.py:14-23` 还可以生成 `aroma_style`、`price`、`return_policy`、`origin_text`、`weight_grams` 等问题。对于这些字段，`matched is None` 后解析器返回：

```python
MerchantReplyParse('partially-answered', (), (), (field_key,), (), 0, 1, False)
```

随后 `merchant_reply_service.py:58-60` 调用 `complete_nonrejudgable_merchant_reply()`，Job 被标为 failed，旧 Decision 保持不变。

**用户影响**：用户填了实际到手价、净含量、产地、退换承诺或香型，页面却显示“提交并更新判断”而没有实际更新。

**修复方向**：建立唯一字段注册表（字段、问题文案、可接受语义、normalizer、证据映射、Decision effect），再让 Question 生成和 Reply Parser 共用它；对 P0 字段至少实现闭环，不支持的字段不应被作为“可改变判断”的问题发给用户。

### P0-2：复判粒度与多候选产品流程相反

**证据**：`CreateRejudgeRequest` 只有 `merchant_reply_id`（`schemas/contracts.py:470-471`）；`MerchantReplyService.rejudge()` 的 request hash 也只包含单 reply ID（`merchant_reply_service.py:35`）。一条回复立即生成一轮 V2 / Delta。

**用户影响**：三个候选分别回答后，会产生多次串行重判。第一个候选的回复先改变全局当前 Decision，后续候选的回复因其绑定的旧 Decision 已 stale，可能被拒绝；这正是“应先分别提交、最后统一更新判断”的反面。

**修复方向**：回复保存和解析与统一复判拆分。单条 reply 成功只进入 `parsed`，不创建 DecisionVersion。由一次 session-level aggregate rejudge 从同一轮 DecisionVersion 收集所有 eligible reply 生成一个 V2 与一个 Delta。

### P0-3：当前单回复设计会让同轮其他回复因父 Decision stale 而失效

**证据**：

- `complete_merchant_rejudgement()`：`update decision_versions set is_current=false,status='stale' where id=%s`（`postgres.py:1056` 附近）。
- `create_merchant_rejudgement_job()`：要求 reply 所属 decision `is_current` 且 `status='completed'`（`postgres.py:924-926` 附近）。

即：同一 V1 上的 A 回复完成后，B/C 仍指向 V1 的回复无法再重判。

**修复方向**：以“复判轮次 / decision snapshot”为单位聚合，不得让单条 reply 自行 stale 整个轮次。

## P1：提交前应消除的正确性与可解释性问题

### P1-1：商家 Evidence 被追加到既有 ExtractionVersion，破坏“提取版本不可变”的语义

**证据**：`complete_merchant_rejudgement()` 向 `evidence_items` 插入时使用旧 `state["extraction_version_id"]`（`postgres.py:1047-1052`）。`ExtractionVersion` 的 schema 注释却明确说“Immutable extraction snapshot”（`contracts.py:361-371`）。

**风险**：历史 V1 的商品截图提取内容会在随后商家回复后变样；用户无法区分“截图识别所得”和“商家后来补充”。

**修复方向**：不修改原 ExtractionVersion；商家 Claim 应归属于回复/Decision 输入快照，或在新的 DecisionVersion 关联的 Evidence snapshot 中读取。若产品决定保留同一 Evidence 表，至少新增明确的 decision-scoped evidence linkage，而不是向 extraction snapshot 追加。

### P1-2：`DecisionDelta` 的模型只能表达一条回复，不可追溯一次汇总复判

**证据**：`decision_deltas.merchant_reply_id uuid not null`、`unique(merchant_reply_id)`（Phase 6 migration）；DTO 也只有单 `merchant_reply_id`（`contracts.py:451-466`）。

**风险**：即使 Service 后续在内存中收集了多个回复，数据库仍不能如实说明“本次 V2 使用了哪些商家回复”。

**修复方向**：新增 `decision_rejudge_runs`（或等价的 session-level aggregate resource）与 `decision_rejudge_run_replies` 关联表；`DecisionDelta` 指向 run，而非单 reply。版本血缘仍使用现有 `parent_decision_version_id`。

### P1-3：字段“能问”不等于字段“能改变判断”

`weight_grams`、`origin_text`、`return_policy` 被纳入问题价值配置（`question_value_v1.yaml:8-11`），但 `evaluate_candidate()` 没有读取这些值。当前反事实模拟通常不会把它们选入前三问；即便生成/解析成功，也没有直接的 Decision effect。

**修复方向**：二选一并写进字段注册表：

1. 让这些字段具有明确的 P0 决策规则与测试；或
2. 先从“可影响本轮判断”的提问候选中移除，只作为用户可选补充信息。

### P1-4：`tea_subtype` 与 `tea_type` 命名漂移

提取/展示可能使用 `tea_subtype`；决策缺失核心检查固定使用 `tea_type`（`decision.py:148-149`）；merchant claim DB check 未接受 `tea_subtype`（Phase 6 migration）。这会造成用户答“具体茶类”也不能补足决策核心字段。

**修复方向**：冻结一个权威字段名，并在 Provider/DTO 边缘做一次显式映射；禁止静默别名。

### P1-5：解析失败被统一标成 `ai_schema_invalid`

`merchant_reply_service.py:108-110` 捕获所有异常，统一调用 `fail_merchant_rejudgement(... AI_SCHEMA_INVALID)`。网络、数据库、规则输入和解析契约错误都变成相同失败码，影响恢复与诊断。

**修复方向**：至少分出 parser contract、provider unavailable、repository failure、stale parent；不要向用户暴露内部错误，但状态码必须保持可诊断。

### P1-6：`sample_available=false` 无法被解析

Parser 仅匹配“小样”/“试饮”得到 `true`。回复“没有试饮”“不提供小样”不会产生 `false` claim，可能错误保留未知状态。

## P2：不应阻塞当前收口

- 当前 `MerchantReply` DTO 没有返回 parsed claims / coverage / warnings；可在调试或后续结果映射中补充。
- `DecisionDelta.explanation` 是固定英文技术句（`merchant_reply_service.py:102`），不能直接作为用户结果文案。
- `merchant_rejudgement` Job 当前固定 `processing_mode='test-fixture'`（`postgres.py:960-966`），容易在真实运行结果上留下错误运行来源。
- `parse()` 与 `run_rejudge()` 两条路径职责重叠；汇总流程设计时再收束为“保存后异步解析”和“统一复判”两阶段。

## 建议的目标语义：保存回复优先，再一次汇总复判

### 用户/API 语义

```text
每个被追问的候选：保存商家回复
  → 服务端只验证、解析、追加 immutable MerchantClaim
  → 返回 parsed / partially-answered / evasive / not-answered / conflicting

当本轮“真正有追问”的候选均已 answered / partially-answered / 明确跳过：
  → 前端才启用“更新判断”
  → 一次 session-level aggregate rejudge
  → 一个新 DecisionVersion + 一个 DecisionDelta
```

没有被追问的 Candidate 不应被要求填写回复。`partially-answered` 是否允许进入汇总，应由产品定义为“已尽力回答，可继续更新”，而不是默默把它当失败。

### 推荐事务边界

1. **保存回复短事务**：锁定 follow-up question 与所属当前 decision；幂等插入 `merchant_replies`，状态 `submitted/queued`。不创建 Decision。
2. **解析回复短事务**：单条回复 claim 后执行 parser；以一个事务写 MerchantClaim、回复 `parse_status` 与其解析完成状态。冲突写为 append-only `merchant-claim/unverified/conflict`，绝不覆盖 product claim。
3. **统一复判短事务**：
   - 锁定父 `DecisionVersion` / session 的 aggregate run；
   - 查询父版本下、目标 Candidate 的所有本轮可用 MerchantClaim；
   - 验证本轮 required question 已达到终态或用户明确跳过；
   - 用**固定输入快照**运行一次决定函数；
   - 原子插入新的 immutable DecisionVersion、全部 CandidateDecision、一个 aggregate DecisionDelta、run/reply 关联；
   - 最后把父版本 stale、新版本 current。

Provider 调用、浏览器等待、外部 I/O 不可置于上述锁持有事务内。

### 建议的 stale 规则

| 事件 | 旧 Decision | 已保存的回复 | 当前轮是否可复判 |
|---|---|---|---|
| 本轮某条回复解析完成 | 仍 current | 保留、可继续收集 | 可以，但不自动触发 |
| 第一次 aggregate rejudge 成功 | 父 V1 stale，新 V2 current | V1 关联回复 immutable | 不可再用 V1 的 run；需以 V2 重新生成问题 |
| 上传/删除候选图片、候选集变化、Need 修改 | 当前 decision stale | 历史回复保留但不自动套用 | 必须基于新 DecisionVersion 再生成问题 |
| 同一轮重复点“更新判断” | 不产生 V3 | 不改回复 | 应按 aggregate-run request hash 重放同一个 V2 / Job |

### 最小数据模型调整（设计建议，非本次改动）

```text
decision_rejudge_runs
  id, selection_session_id, parent_decision_version_id,
  idempotency_key, request_hash, status,
  new_decision_version_id, created_at, completed_at

decision_rejudge_run_replies
  rejudge_run_id, merchant_reply_id
  unique (rejudge_run_id, merchant_reply_id)

decision_deltas
  将 merchant_reply_id 替换为 rejudge_run_id
  或短期兼容：新增 rejudge_run_id，允许旧单回复 lineage 读取
```

这保留：V1、回复、V2、Delta 全部不可变且可追溯；也能准确解释“本次结论未变，但哪些关键未知项已被补足”。

## 验收用例（后续实现必须补）

1. 三个候选各有一条问题；分别保存三条回复后，仍只有 V1；最后一次 aggregate rejudge 只创建 V2 与一个 Delta。
2. 第一条回复解析后不得使 V1 stale；B/C 的同轮回复继续可保存、可解析。
3. 价格“到手 128 元”、净含量“500g”、清香型、无小样、支持七天退换等 P0 语义均有字段级规范化测试。
4. 商品页称“清香”、商家回复“浓香”时：product claim 保留；新增 merchant claim 为 conflict/unverified；Decision 的风险与 Delta 可追溯。
5. 同一 aggregate idempotency key 并发调用只产生一个 V2 与一个 Delta。
6. aggregate transaction 任一步失败，不能产生半个 V2、孤立 CandidateDecision 或 current 指针漂移。
7. 未被提问的 Candidate 不阻塞“更新判断”；已提问但用户选择跳过的 Candidate 按明确状态参与。

## 审查结论

- **P0：3 项**（字段解析闭环、单条即时复判、同轮 stale 阻断）。
- **P1：6 项**（Extraction 不可变语义、Delta 单回复模型、问题价值与 Decision 脱节、字段命名、错误码、否定样本语义）。
- **P2：3 项**（DTO 可观测性、用户文案、运行模式标注、职责收束）。

在 P0 修正前，不应把“提交并更新判断”描述为已完成的多候选商家复判功能。
