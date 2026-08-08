# 产品合同与用户旅程审查

> 审查日期：2026-08-08  
> 审查范围：只读核对 PRD、当前集中审查报告、运行说明、OpenAPI 路由、后端服务及浏览器主流程。  
> 审查分支：`codex/phase10-6-competition-mvp-concentrated-closeout`  
> 结论：**NOT_READY_FOR_FINAL_E2E**。当前代码具备旅程中的大多数后端节点，但“多候选 + 多图 + 真实识别 + 汇总复判 + 刷新恢复”的比赛用户旅程尚未闭环。

本文件不修改任何业务代码，不包含密码、API Key、用户图片内容或私有对象路径。

## 1. 判定依据

### 当前有效的产品边界

1. `docs/PRD_SOURCE_OF_TRUTH.md:3-7` 指向用户指定的 P0 后端 PRD；该 PRD及集中审查报告均要求一次选择可有 **1–5 个候选**、每候选 **1–2 张**商品截图。
2. `docs/CURRENT_STATE.md:5-11` 明确当前目标能力为候选、双图、提取、比较、追问、商家回复/复判 Delta、茶仓及反馈。
3. `docs/COMPETITION_MVP_CONSOLIDATED_AUDIT_2026-08-08.md:24-35` 明确：同候选双图联合理解、候选间独立理解；正常比赛流程不能把 Fake 输出当作真实识别；商家回复应“分别保存、汇总后统一复判”。
4. 浏览器视觉和交互是基线。`docs/CURRENT_STATE.md:31-35` 要求后端接入不能重写既有页面、样式、文案或导航；审查不把视觉重做列为解决方案。

### 审查标记

- **已有**：后端与前端链路均存在，且当前代码能够直接调用。
- **部分**：存在接口或局部交互，但未满足当前旅程语义、恢复语义或验收条件。
- **错误**：当前实现直接违反已冻结的比赛流程或会展示错误事实。
- **断链**：前、后端任一端缺少连接，用户无法完成该节点。

## 2. 完整用户旅程状态表

| 节点 | 后端/合同 | 浏览器接入 | 当前状态 | 证据 | 审查判断 |
| --- | --- | --- | --- | --- | --- |
| Need（本次需求） | `POST/PATCH /selection-sessions` 已有 | `apiNeed()` 将口味、用途、预算映射到 DTO | **部分** | `routes.py:166-179`；`app.js:143-149, 277-289` | 首次创建/更新可用；`risk_attitude_text` 恒为 `null`，并且刷新优先读 localStorage，不先从服务器恢复。 |
| Candidate（1–5 候选） | 创建、列表、删除均有 | 候选卡可新增/删除、编号重排 | **部分** | `routes.py:181-193`；`app.js:114-122, 290-299, 1068` | 多候选 API 已有，但进入页面没有 `get session + list candidates` 的服务器恢复；本地旧状态可主导展示。 |
| Images（1–2 图/候选） | 上传、读取元数据、删除、重试 Job 已有 | 第一图与“小加号”补第二图均可暂存和上传 | **部分** | `routes.py:195-214, 285-290`；`app.js:632-640, 934-967` | 图片安全与数量限制存在；候选卡预览依赖本地 `Blob`/`previewUrl`，刷新后无法从服务器读取可显示缩略图。 |
| Extraction（每候选独立提取） | Job、轮询、当前 Extraction 已有 | 上传后轮询并读取 current extraction | **部分** | `routes.py:216-219, 274-283`；`app.js:329-350` | 单个 Job 完成链路存在；恢复时不从服务器枚举 candidate images/jobs，依赖缓存的 `jobId` 与 `extractionStatus`。 |
| Evidence（产品证据） | ExtractionVersion/Evidence DTO、所有权与枚举已有 | 结果页把 Evidence 映射为中文标签 | **部分** | `contracts.py:335-359`；`app.js:151-183, 736-745` | 数据合同正确，但用户页面仍直接展示工程式字段结构；Fake 固定 `fixture` 能到达普通结果页。 |
| Decision（初判/比较） | 会话 Decision Job、DecisionVersion、CandidateDecision 已有 | 所有候选 extraction 完成后自动发起分析 | **部分** | `routes.py:221-236,268-272`；`decision_service.py:18-53`；`app.js:373-391` | 后端比较、排序版本存在；浏览器只能在本地所有候选状态都标为 completed 时发起，刷新/失步会阻断。 |
| Answer（用户可读结论） | 后端返回 `action_bucket/reasons/risk_flags` | 页面按卡片显示“匹配理由/识别信息/风险提示/信息来源” | **错误** | `contracts.py:384-400`；`app.js:157-183, 728-753` | 结果主页面仍展示 `product-claim`、`unverified` 等 Evidence 工程元数据；没有独立的用户 Answer Contract，且存在历史静态回退话术。 |
| Questions（1–3 个关键追问） | DecisionVersion questions API 与价值计算已有 | 结果页可获取/生成、按当前候选显示 | **部分** | `routes.py:238-244`；`question_service.py:13-24, 32-106`；`app.js:394-404, 887-895` | 问题生成基于 Decision Value，最多 3 条；但前端只在当前候选的 sheet 里处理一个问题，不能显式跟踪“哪些候选需要回复/已跳过”。 |
| Merchant Reply（分别保存） | Merchant reply 创建、查询、幂等已实现 | 前端提交回复 | **部分** | `routes.py:246-252`；`merchant_reply_service.py:19-29`；`app.js:406-414` | 回复确实被保存；但提交后立即触发复判，未按当前产品决定停留在“保存回复”。 |
| Rejudge（汇总复判） | 单 reply 触发的 rejudge Job 已实现 | 一条回复后立即轮询 rejudge | **错误** | `routes.py:254-260`；`merchant_reply_service.py:31-107`；`app.js:411-431` | 接口强制 `merchant_reply_id`；服务仅把该 reply 的 claims 加到一个候选输入中。没有本轮全部回复汇总、没有“保存后再更新判断”的统一动作。 |
| Delta（V1→V2 变化） | DecisionDelta DTO、读取接口、持久化存在 | 页面可拉取并显示部分字段 | **部分** | `contracts.py:451-467`；`routes.py:262-266`；`app.js:704-726` | 单条回复复判时可产生 Delta；这不是汇总 V1/V2 的语义。页面仍保留静态历史分支，可能呈现未基于服务器的变化文案。 |
| Tea Stock（茶仓） | 仅 feedback bridge；无云端茶仓 | 本地 localStorage 茶仓、从选择结果加入 | **已有（比赛本地版）** | `contracts.py:485-490`；`stores.js:56-79`；`app.js:55-64, 1078-1100, 1139` | 与当前“比赛版本地优先、无登录”边界一致；不是服务器事实来源，应在文档中维持这一限制。 |
| Feedback（泡茶反馈） | `/brew-feedback/analyze` 与重放支持 | 本地记录、可选后端分析、偏好证据回写本地 | **已有（比赛本地版）** | `routes.py:109-164`；`api-client.js:78`；`app.js:856-871, 1176-1193` | 该节点在比赛本地版可用；它不应反向覆盖服务器 Selection/Decision 事实。 |

## 3. 关键断链与根因

### P0-1：运行模式没有成为用户旅程合同，Fake 结果可进入普通页面

**失败场景**：服务端未显式设置真实 MiMo 时，`GUANCHA_PROVIDER` 默认 `fake`；真实商品截图会显示固定“安溪铁观音”“fixture”等预设值。

**代码证据**：

```python
# backend/src/guancha_api/main.py:45-63
mode = os.getenv("GUANCHA_PROVIDER", "fake").lower()
if mode == "fake":
    return FakeProvider(extraction_response={
        "product_name": "安溪铁观音",
        # ...
        "evidence": [{"raw_text": "fixture", ...}],
    })
```

`app.js:736-745` 随后将 Evidence 直接放入用户结果页；没有运行模式标识、也没有“Fake 不可用于比赛识别”的页面级保护。

**影响**：用户无法分辨“识别失败”与“测试 fixture”；价格、重量、包装等真实截图信息不会出现，却可能继续生成比较、追问与入库行为。

**要求**：比赛 runtime 必须显式选择 MiMo；真实 Provider 失败必须是 `failed → 可重试`，不得成功降级到 fixture。Fake 只能被自动测试或明确内部演示入口使用。

### P0-2：商家回复字段合同断裂，询问能力大于解析能力

`question_service.py:13-24` 可以生成 `price`、`return_policy`、`origin_text`、`weight_grams`、`process_text` 等问题；但 `FakeMerchantReplyReasoningProvider` 只识别三类：

```python
# backend/src/guancha_api/providers/merchant_reply.py:35-38
values = {
    "roast_level": [...],
    "season": [...],
    "sample_available": [...],
}
```

因此，对“到手价”“净含量”“退换规则”“产地”“具体茶型”等用户真实回答，解析通常走 `partially-answered`/`not-answered`，`MerchantReplyService.run_rejudge()` 在 `merchant_reply_service.py:58-60` 直接结束，不创建可影响判断的 merchant claim。

**影响**：页面提示“提交并更新判断”，但实际没有可用证据和新判断，正是用户已经反复观察到的现象。

**要求**：以一个字段注册表统一“问题文本 → 接受语义 → 规范化 → `merchant-claim/unverified` Evidence → Decision 影响”，至少闭合价格、重量、具体茶型、香型、焙火、季节、产地、小样、退换。

### P0-3：复判实现为“单条即时”，与多候选比较语义冲突

当前浏览器代码：

```javascript
// app.js:411-415
const reply = await apiClient.createMerchantReply(state.sessionId, {...});
const job = await apiClient.rejudgeMerchantReply(state.sessionId, reply.id);
```

后端同样把 `reply_id` 作为 rejudge 的核心输入（`merchant_reply_service.py:31-44`），并且仅把此 reply 的 claims 注入该候选的 evidence（`merchant_reply_service.py:61-72`）。`DecisionDelta` 也只记录单一 `merchant_reply_id`（`contracts.py:451-456`）。

**影响**：候选 A 先回复就使初判 V1 stale；候选 B/C 尚未保存的回复没有进入同一轮比较。用户无法完成“各候选分别保存 → 一次统一更新判断”的产品流程。

**要求**：保存回复与复判分离；后端最终一次读取当前 DecisionVersion 的本轮全部有效回复、追加 claims、生成不可变 V2 和一个汇总 Delta。没有追问的候选不能被强迫提交回复。

### P0-4：服务器并非实际唯一事实来源，刷新恢复依赖浏览器缓存

`app.js:67-80` 在加载时组合 `uiSession`、`selectionBridge`、`localPostPurchase`；`app.js:138-141` 又把 session、candidates、job、questions、delta 写回 localStorage。`resumeLiveBackendState()`（`app.js:352-371`）仅遍历这些已缓存的 candidates/jobs，不会先调用：

```text
GET /selection-sessions/{id}
GET /selection-sessions/{id}/candidates
GET /candidate-images/{id}
GET /jobs/{id}
```

**已出现表现**：旧 `sessionId` 导致 `selection_session_not_found`；本地显示“已暂存”但服务器没有有效图片；删除/补图后候选字母、图片、Job 与结果不同步。

**要求**：服务器是 Selection、Candidate、Image、Job、Extraction、Decision、Questions、Merchant Reply 的唯一事实来源。浏览器只保存匿名 client ID、尚未上传的 File、纯 UI 临时状态、比赛版本地茶仓/反馈；localStorage 不能覆盖服务器回读结果。

## 4. P1：前端低于后端合同或历史阶段污染

### P1-1：双图的“联合提取”后端合同存在，浏览器和验收未证明它发生

后端 DTO 支持 `source_image_ids` 为 1–2（`contracts.py:351-359`），当前 extraction/repository 也记录输入图片集合；但前端在上传时逐图调用上传接口（`app.js:300-310`），并且只保存最后一个 `candidate.jobId`。候选卡只把第一图作为主缩略图（`app.js:632-640`）。

无法从浏览器代码证明：补第二图后，旧 extraction/decision 被 stale、Provider 同时收到 A1+A2、只产生一个新的联合 ExtractionVersion，且 B/C 不串图。

**建议验收**：固定 A(2图)/B(2图)/C(1图)，断言每次 Provider request 的 `image_count`、`candidate_id`、`source_image_ids`、旧版 stale、decision stale。

### P1-2：结果展示没有独立 Answer Contract，工程字段成为普通用户语言

`app.js:157-183` 虽有中文映射，`app.js:740` 仍向普通用户展示：

```html
<small>商品页面声明 · 未核验 · 页面明确写明</small>
```

这类信息适合作为“来源说明”折叠层，不该是主要结果。`app.js:258-264` 只把 `action_bucket` 和最多 3 条 reasons 映射为短文本，缺少清晰的“当前结论 / 为什么与我有关 / 关键不确定项 / 下一步”用户回答结构。

此外，`app.js:683-702` 仍保留不基于服务器数据的历史静态 rejudge 分支（例如“确认：2026 年春茶”“支持 10g 试饮装”）。即使当前通常不走该分支，它是未来状态丢失时错误展示的风险来源。

### P1-3：文档范围已部分收束，但 README 仍残留历史否定声明

`docs/CURRENT_STATE.md:5-11` 把比较、追问、商家回复/复判 Delta、反馈列为已实现；`README.md:47-50` 却仍写“当前仅覆盖……不做候选排名、推荐分档、追问、商家复判、泡茶日记或买后分析”。

这会污染后续开发：一方按当前 1–5 候选闭环修复，另一方可能根据 README 的单候选 P0 历史限制撤掉比较或复判。必须以一份现行的产品状态/范围文件为准，并将 README 的旧限制改为历史说明或链接。

### P1-4：前端把业务状态、DOM、网络与本地持久化混在同一文件

`app.js` 同时负责状态归一化（`67-141`）、API 编排（`277-448`）、DOM 模板（`625-753`）、页面导航（`1043-1153`）、茶仓与反馈（`1154-1205`）。这解释了为什么修上传状态时会影响候选卡、修复判时又影响结果页。

这不是要求重写 UI；应新增薄的 server-state adapter，保留既有 render/样式，只替换状态读取与动作调用边界。

### P1-5：当前问题/回复 UI 没有“等待汇总”的状态模型

`app.js:887-895` 仅渲染当前 candidate 的问题。`app.js:666-670` 动态插入的表单按钮文案恒为“提交并更新判断”。没有：

```text
每候选问题状态（待回答 / 已保存 / 跳过）
本轮可复判条件
统一“更新判断”按钮
统一复判中的加载状态
```

这会在改成汇总复判后成为前端断链，必须与后端 aggregate 语义一并设计，但不得重做页面视觉结构。

## 5. 旅程节点的详细合同核对

### Need → Candidate

- 后端合同完整：`CreateSelectionSessionRequest`、`SelectionSession`、`CreateCandidateRequest` 及路由位于 `routes.py:166-189`。
- 前端首次分析才创建服务器 session/candidate（`app.js:277-299`），而不是在“候选创建时”持久化。因此在上传前、刷新后，候选仅为本地草稿；这是允许的，但 UI 必须明确为“尚未提交”，不能标成“已暂存到服务端”。
- `normalizeCandidate()` 会在无 completed extraction 时把名称强制改为“候选茶 A/B/C”（`app.js:82-100`），符合用户不愿显示假识别名称的要求；编号重排实现存在（`114-122`），但仅依赖本地数组。

### Candidate → Images → Extraction

- 上传路由在读取上限处限制 multipart（`routes.py:195-202`）；后端服务承担真实图片安全检查。
- 前端 `validateImageFiles()` 只做 MIME/大小预检查（`app.js:897-905`），并不替代后端签名/解码检查。
- `hasUsableCandidateImages()` 当前只要求每候选 **至少一张**可用图片（`app.js:969-988`），第二张为可选，这已纠正过去“可选第二图阻塞分析”的问题。
- 但 `candidate.serverImageId` 是单值（`app.js:305,452-461`），而 `candidate.images[index].serverImageId` 才是多图真实映射；删除/重试路径使用单值，存在多图时删错或仅处理最后一张图的风险。

### Extraction → Evidence → Decision

- `applyExtraction()` 从 Evidence 填充候选名称、类型和风险（`app.js:202-215`）；没有从服务端回读 images 元数据，因此“图已完成但预览丢失”的刷新体验未闭合。
- `SessionDecisionService` 在同一 session 上先确认每候选都有 current completed extraction，再创建 Decision Job（`decision_service.py:18-33`）；其核心比较为确定性规则函数（`35-50`）。
- `app.js:373-380` 自动启动 Decision 的条件是浏览器中所有 candidate 的 `extractionStatus === completed`。服务器实际上是权威，但当前自动逻辑是本地缓存作为闸门。

### Decision → Answer → Questions

- 服务端 `CandidateDecision` 包含 action bucket、相对排序、理由、风险和缺失关键字段（`contracts.py:384-396`），这是 Answer Contract 的原始数据，不应直接等同于用户页面结构。
- `QuestionGenerationService` 以缺失字段与反事实影响选择问题（`question_service.py:60-96`），逻辑目标正确；但问题字段和回复解析字段没有共享注册表，导致 P0-2。

### Questions → Merchant Reply → Rejudge → Delta

- 当前 `MerchantReply` 能持久化 raw reply 以及 parse status（`contracts.py:418-434`）。
- 当前 `DecisionDelta` 是“单 reply → 新 version”的模型：`merchant_reply_id` 必填（`451-456`）。它不能自然证明 aggregate round 已完成。
- 当前 rejudge 的异常统一落入 `AI_SCHEMA_INVALID`（`merchant_reply_service.py:108-110`），这会把网络、持久化、字段不支持等不同错误混为 schema 问题，降低用户可重试和排查的正确性。

### Tea Stock → Feedback → Refresh

- 茶仓、泡茶记录、近期偏好证据均被设计为比赛本地优先状态；`stores.js:56-79` 给出 localStorage/IndexedDB 边界，`app.js:1176-1193` 再可选调用 feedback API。
- 这与“无需登录、非云端茶仓”的当前比赛边界一致，但不得被误称为服务器可跨设备恢复的数据。
- Selection 结果和 Tea Stock 的桥接仅从当前内存 `candidate` 添加历史/茶仓；若刷新后 server restoration 不完整，用户仍可能看到茶仓存在、但选茶来源无法追溯。

## 6. 文档与接口的冲突清单

| 冲突 | 证据 | 风险 | 优先级 |
| --- | --- | --- | --- |
| 当前状态说比较/追问/复判已实现，README 说这些“不做” | `docs/CURRENT_STATE.md:5-11` vs `README.md:47-50` | 开发按错误范围回退；答辩说明自相矛盾 | P1 |
| 当前产品决定要求汇总复判，OpenAPI/DTO 强制单 `merchant_reply_id` | 集中审查报告 §4 P0-3；`contracts.py:451-471`; `routes.py:254-260` | 无法实现多候选公平比较 | P0 |
| 后端可记录 1–2 image IDs，浏览器以单 `serverImageId` 支持删除/重试 | `contracts.py:351-359`; `app.js:305,452-461` | 第二张图可丢失或与旧 Job 串联 | P1 |
| Evidence 作为严谨数据合同，普通结果页把它当主展示 | `contracts.py:335-348`; `app.js:736-745` | 用户看到 fixture、raw enums/来源状态，而非可决策答案 | P1 |
| README 称 Fake 是当前实现，当前集中审查要求真实 MiMo 为正常比赛路径 | `README.md:1-10`; 集中审查报告 §4 P0-1 | 运行命令会启动错误模式并误导演示 | P0 |

## 7. 历史阶段限制对当前 P0 的污染

以下内容不是“当前还缺的功能”，而是过去阶段残留使当前用户旅程被错误收缩：

1. **单候选/单图阶段语义**：`reuploadMvpAnalysis()` 的注释和实现明确“replace its single P0 image only”（`app.js:450-463`），与当前每候选两图不一致。
2. **Fake 默认模式**：`main.py:45-64` 从单图离线开发阶段延续到当前正常启动路径，不能再作为比赛页面的隐式默认。
3. **静态结果原型**：`app.js:683-702` 的固定“春茶/小样/本轮推荐”内容是早期高保真展示遗留，不能作为真实复判的回退答案。
4. **README 旧限制**：见上节，继续把已实现的比较、追问、复判、反馈表述成“不做”。

## 8. 建议的后续修复顺序（仅供 Orchestrator 裁决）

1. **WP1：运行模式与服务器事实来源**
   - 先固定 Fake/真实 MiMo 边界，恢复时 server-first。
   - 影响文件：`main.py`、`app.js`、`frontend/api-client.js`、可能的 server state adapter。
   - 验收：真实失败不会生成 fixture；刷新后 A/B/C、图、Job、Extraction、Decision 以服务器回读为准。

2. **WP2：多候选/双图管线**
   - 用数组而不是 `candidate.serverImageId` 单值处理图片；证明第二图触发同候选联合 extraction、旧 extraction/decision stale。
   - 验收：A1/A2、B1/B2、C1 绝不串图，Provider input image_count 正确。

3. **WP3：Answer Contract V2**
   - 将后端 Evidence/Decision 数据映射成“当前结论、为什么、已知事实、关键不确定、风险、下一步”，不在普通页面展示 raw field/enum/fixture。
   - 视觉只做最小内容映射，不重做页面体系。

4. **WP4：商家回复保存与汇总复判**
   - 建字段注册表，分离 save reply 和 aggregate rejudge，生成 V2/Delta，解释结论改变或不变。
   - 最后才修改 `app.js` 的按钮语义和状态显示。

5. **WP5：浏览器 E2E 验收**
   - 固定 A(2图)/B(2图)/C(1图) → V1 → 追问 → 分别保存回复 → 一次 V2/Delta → 茶仓 → 刷新。
   - 自动测试使用 Fake；真实 MiMo 仅一次受控人工烟测。

## 9. 当前验收结论

| 验收目标 | 结果 |
| --- | --- |
| 单模块：会话/候选/图片/Job/Extraction | 基础能力存在 |
| 单模块：Decision/Questions/单条 Merchant Reply/Rejudge | 基础能力存在 |
| 用户旅程：多候选 + 1–2 图 + 真实结果 | 未充分验证 |
| 用户旅程：分别保存回复后统一复判 | **未实现** |
| 用户旅程：普通用户不见 fixture/工程 Evidence | **未达到** |
| 用户旅程：刷新后服务器恢复为唯一事实 | **未达到** |
| 茶仓/反馈本地比赛闭环 | 基础可用 |

**最终判定：NOT_READY_FOR_FINAL_E2E。**

在 WP1–WP5 完成、并通过固定 A/B/C 浏览器验收前，不应继续将当前版本描述为“完整比赛闭环已完成”。
