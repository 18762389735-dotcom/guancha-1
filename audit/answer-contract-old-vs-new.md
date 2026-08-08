# Answer Contract 审查：旧版拖图选茶网页 vs 当前比赛版

> 审查范围：只读代码追溯与合同设计；不复制旧 Provider、OCR、数据库、fixture、密钥或 API Schema。
>
> 审查日期：2026-08-08。行号以本地工作树为准，后续提交可能变化。

## 结论

用户记忆中的“直接拖/上传商品截图后，看到像选茶助手一样的完整答案”的版本已定位，不是按目录名猜测：

| 项目 | 定位证据 |
|---|---|
| `OLD_WEB_REFERENCE_PATH` | `C:/Users/QQ/Documents/New project/guancha-agent-v0.1/frontend/` |
| `OLD_WEB_REFERENCE_COMMIT` | `c4587695735c34871cb9defb0d0a65a95c1a8f38`（该仓库当前 HEAD；含被审查的 `frontend/index.html`、`frontend/app.js`） |
| 拖/上传入口 | `frontend/index.html:76-96` 的截图模式、`multiple` 文件输入；`frontend/app.js:740-762` 的 `dragover/drop`；`764-815` 的提交流程 |
| 旧版结果页 | `frontend/index.html:105-132`；`frontend/app.js:240-360` 的排序摘要与信任卡；`400-610` 的追问、商家回复、复判卡 |
| 旧版 Prompt | `backend/app/services/provider_client.py:14-78` 的 `EXTRACTION_PROMPT`；它只抽取截图事实，不作购买建议 |
| 旧版答案/规则组织 | `backend/app/services/llm_extractor.py:385-517` 的优点、缺口、用户摘要；`backend/app/routers/run_compare.py:77-122` 把摘要、理由和追问写成一次比较结果 |

**核心判断：旧版更像“选茶助手”不是因为模型更强，而是它把工程事实重新组织成了用户决策语言：先给结论，再给与偏好的关系、风险、缺口和下一步；当前版已经具备更严格的 Evidence / Decision 后端能力，却把原始 Evidence 展示直接搬到结果页。**

## 旧版为什么更像选茶助手

| 用户问题 | 旧版表达与证据 | 当前版表达与证据 | 影响 |
|---|---|---|---|
| 先看到什么？ | 比较结果顶部先给 `优先考虑 / 建议先问清 / 可先试小样 / 暂不推荐` 与排序，`old frontend/app.js:250-265` | 当前卡片虽有行动标签，但先后紧接“匹配理由 / 识别信息 / 风险提示 / 信息来源”，`current app.js:741-745` | 当前信息层级把结论与底层字段并列，用户很难知道此刻该做什么。 |
| 已知事实怎么组织？ | 只显示与判断相关的优点、可信证据、试饮政策，`old frontend/app.js:300-310` | 把每个 Evidence 展开为“字段名 + 值 + source / verification / information status”，`current app.js:157-183, 740` | `product-claim / unverified / explicit` 对普通用户是数据血缘，不是答案。 |
| 偏好如何关联？ | `generate_summary()`先复述偏好，再说明哪个候选为何更适合，`old llm_extractor.py:449-491` | Decision 引擎已读取 `need` 并生成 `reasons`，`current backend/.../decision.py:42-101`，但前端只把 reasons 原样列出，`current app.js:258-264` | 现有能力没有形成“与你有什么关系”的自然语言层。 |
| 风险怎么表达？ | 把高/中严重规则翻为“主要风险”，并说明会影响什么购买风险，`old frontend/app.js:313-359` | `risk_flags` 被映射成短句，`current app.js:185-192,739` | 当前可读，但缺少“风险会改变什么决定”的关联。 |
| unknown 怎么表达？ | 只把有意义的缺口列为“缺失信息”，`old frontend/app.js:322-327`；摘要只在关键缺口时建议追问，`old llm_extractor.py:488-515` | `missing_critical_fields` 已在 Decision 中存在，`current contracts.py:384-396`，但结果页没有将其按决策价值过滤、解释或转成一句问题 | 用户看到很多字段时会误以为“缺任何字段都不能买”。 |
| 什么时候可考虑/问清/试饮？ | 明确 tier → 行动文案，`old frontend/app.js:330-337` | 已有 ActionBucket 与排序，`current decision.py:12-18,70-101`；前端仅从桶名映射按钮，`current app.js:741-745` | 需要一个面向用户的答案层，把行动、依据和不确定性捆绑。 |
| 追问如何选择？ | 每款最多两条，按必须/应该优先级，并可复制，`old frontend/app.js:407-456` | 后端已按反事实影响、用户相关度、可答性计算问题，`current backend/.../question_service.py:60-106` | 当前后端比旧版更严谨；缺的是结果页将“为什么问”和“问后会怎样”转成可理解文案。 |
| 商家回复后怎么办？ | 旧版展示复判后偏好、与初判对比和补全缺口，`old frontend/app.js:570-610` | 当前已经有不可变 DecisionVersion、DecisionDelta 合同，`current contracts.py:373-467` | 现有前端把单条回复即时复判，且 Delta 文案有硬编码示例，不能体现真实统一复判。 |

## 当前能力不是“没有”，而是“没有被正确呈现”

当前后端已有的可信基础：

- Evidence 的来源、核验、状态、强度和图片溯源在 `backend/src/guancha_api/schemas/contracts.py:340-359`；这应继续保留为**后端事实合同**。
- Decision 按候选的 `action_bucket`、排序、理由、风险和关键缺口持久化，在 `contracts.py:373-400` 与 `application/decision_service.py:18-50`。
- Question Service 不是随机问问题：它用需求、影响、未知性、可答性和交互成本排序，`application/question_service.py:60-106`。
- 当前 API 已提供 Decision、问题、商家回复、复判、Delta，`api/v1/routes.py:221-272`。

因此，Answer Contract V2 的目标不是退回旧项目，也不是把旧规则、旧 Prompt 或旧 API 移过来；而是在**现有 Evidence 与 Decision 之上新增一个 presentation mapper**。

## 当前问题分级（只针对 Answer Contract）

### P0：结果页直接泄露工程 Evidence 语义

- **证据**：`app.js:740` 直接输出 `sourceLabel · verificationLabel · statusLabel`；标签来自 `app.js:164-183`。
- **失败场景**：用户看到“商品页面声明 · 未核验 · 页面明确写明”或 `fixture`，误解为系统没有识别、或将“未核验”理解为无效。
- **为什么阻塞比赛演示**：用户的核心任务是比较并决定，不是审计模型数据血缘；这与本轮目标的“普通用户页面不以工程 Evidence 字段为主体”冲突。
- **修复方向**：普通结果页只显示自然语言“商品页可见信息”“商家后续补充”“尚待确认”；把完整 Evidence 仅放 debug/admin。

### P0：用户答案没有独立的合同边界

- **证据**：`mvpDecision()`只是将 `candidate.decision.reasons` 截断至 3 条，`app.js:258-264`；`renderResult()`在同一模板拼接工程事实、风险、来源，`728-745`。
- **失败场景**：每次后端增加 Evidence 字段、枚举或内部评分，前端都会直接受到影响；结果页无法保证“结论—理由—不确定项—下一步”的稳定结构。
- **修复方向**：定义下文的 `ANSWER_CONTRACT_V2`；由服务端或明确的前端 adapter 创建，而不是让页面读原始 schema。

### P1：当前“信息不足”仍太像终态

- **证据**：Decision 引擎将缺价格直接加入 `ASK_BEFORE_BUYING`，`backend/src/guancha_api/domain/tieguanyin/decision.py:64-68`；前端把 `insufficient-information` 直接当主行动状态，`app.js:743-745`。
- **失败场景**：仍有相对比较依据时，用户得到“信息还不够”而非“当前相对更适合 A，但价格/焙火仍需确认”。
- **修复方向**：Answer 层应区分 `relative_recommendation` 与 `insufficient_information`：只有不能形成区分性依据时才使用后者。

### P1：DecisionDelta 的示例文案不是服务端事实

- **证据**：`app.js:673-687` 的 `renderRejudgeData()` 写死“原判断：当前优先关注・先问再买 → 更新后：本轮推荐”等示意文字。
- **失败场景**：商家回复并未改变排序时，用户仍可能看到仿真的变化说明。
- **修复方向**：由真实 `DecisionDelta` 及新旧 DecisionVersion 生成“结论改变 / 结论未变但为何未变”的中文摘要。

### P2：旧版本身不可直接复用

- **证据**：旧 Prompt 接受 GIF/WebP、2–3 图，`old frontend/index.html:83-89`；旧答案直接依赖旧 `tiers`、`rule_matches` 和 `comparison_results`，`old run_compare.py:77-122`。
- **结论**：只能借鉴答案信息架构；不得复制旧 Provider、OCR、数据库或 response schema。

## 明确不复用的旧内容

- 不复用 `guancha-agent-v0.1/backend/app/services/provider_client.py` 的 Provider 调用、base64 处理、旧 Prompt 或旧模型配置。
- 不复用 `llm_extractor.py` 的旧 `unknown` / `evidence_level` 枚举、规则、数据库表或分档规则。
- 不复用旧 `/compare-sessions/*` API、`comparison_results`、`rule_matches`、`follow_up_questions` 数据模型。
- 不复用旧版让单条商家回复立即全局复判的交互。

## 建议的最小迁移方式

1. 保持现有 `/decision-versions/{id}`、`/questions`、`/merchant-replies`、`/rejudge` 的底层数据合同不变。
2. 增加一个**纯映射层**，输入 `SelectionNeed + ExtractionVersion + CandidateDecision + FollowupQuestion + DecisionDelta`，输出 Answer Contract V2。
3. 现有高保真 UI 只把数据读取点换到该映射层；不重做页面、CSS、SVG、按钮路径。
4. 新增快照测试：答案中不得出现 `fixture`、`snake_case`、`source_type`、`verification_status`、`internal_score`、Provider 名称或原始 schema 枚举。
