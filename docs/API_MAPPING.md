# 观茶前后端 API 映射

> 状态：阶段 0 映射草案，等待审查  
> 合同权威：阶段 1 起以 FastAPI OpenAPI 为唯一事实源  
> 说明：本文区分“PRD 已冻结”与“建议字段草案”；未确认字段不得先写死在前端

## 1. 总原则

1. Base Path：`/api/v1`；`GET /health` 例外；
2. 前端不计算排名、行动分档、问题价值、证据强度或回复是否有效；
3. 创建型请求发送 `Idempotency-Key: <uuid>`；
4. 前端保存资源 ID 和版本 ID，不复制服务端事实作为新的事实源；
5. 任务只通过 Job 状态推进，不用固定 `setTimeout` 冒充分析；
6. 证据变化后当前决策必须变为 `stale`；
7. OpenAPI 变更后生成/同步前端类型，再改调用；
8. 后端错误统一归一化，页面只接收稳定错误码和可恢复动作。

## 2. 当前前端动作到目标 API

### 2.1 启动与会话

| 当前动作/函数 | 目标 API | 前端发送 | 前端保存/展示 |
| --- | --- | --- | --- |
| 应用启动 | `GET /api/v1/config/public` | 无 | 文件限制、候选上限、轮询参数等公共配置 |
| `start-task` | `POST /api/v1/selection-sessions` | 本次需求、偏好快照、近期低置信度证据摘要 | `sessionId`、状态、服务端版本 |
| 刷新/继续 | `GET /api/v1/selection-sessions/{session_id}` | session ID | 恢复候选、图片、当前 Job/Decision 引用 |
| `save-needs` | `PATCH /api/v1/selection-sessions/{session_id}` | 变更后的本次需求 | 新的 evidence/context version；旧决策 stale |

当前 `state.need`：

```js
{ taste, purpose, budget }
```

建议请求 DTO（待 OpenAPI 确认）：

```ts
type SelectionNeedInput = {
  tasteText?: string
  purpose?: string
  budgetMin?: number
  budgetMax?: number
  riskAttitude?: string
}
```

当前预算是自由文本，不能由前端自行可靠解析；阶段 1 要么由表单改为结构化字段，要么把原文交后端解析并返回归一化值。UI 冻结期间优先保留原文并由后端处理。

### 2.2 候选与图片

| 当前动作 | 目标 API | 必要结果 | 本地状态变化 |
| --- | --- | --- | --- |
| 添加新候选 | `POST /selection-sessions/{session_id}/candidates` | `candidate_id`、顺序、状态 | 新增候选 ViewModel |
| 加载候选列表 | `GET /selection-sessions/{session_id}/candidates` | 候选及当前图片/抽取引用 | 覆盖服务端资源部分，不覆盖 UI 临时态 |
| 删除候选 | `DELETE /candidates/{candidate_id}` | 当前 session 版本、stale 标志 | 停止相关轮询，移除候选 |
| 上传第 1/2 张 | `POST /candidates/{candidate_id}/images` | `image_id`、`job_id`、校验结果 | 图片进入 queued/processing |
| 删除单图 | `DELETE /candidate-images/{image_id}` | 新证据版本、stale 标志 | 仅移除目标图片 |
| 重试失败图片 | `POST /candidate-images/{image_id}/retry` | 新 `job_id` | 保留其他成功候选 |

上传合同已冻结：

- 1–5 个候选；
- 每候选最多 2 张；
- JPEG/PNG；
- 单张最大 5MB；
- 后端检查 MIME 与真实文件签名；
- 上传后立即创建候选抽取 Job；
- 补第 2 张后重新联合抽取并产生新 ExtractionVersion。

建议候选 ViewModel：

```ts
type CandidateViewModel = {
  id: string
  label: string
  displayName: string
  images: Array<{
    id: string
    status: 'queued' | 'processing' | 'completed' | 'failed'
    errorCode?: string
  }>
  extractionVersionId?: string
  extractionStatus: 'empty' | 'queued' | 'processing' | 'completed' | 'failed' | 'stale'
}
```

`displayName` 只是展示字段，不能再用 A/B 字母或数组下标作为服务端身份。

### 2.3 分析任务与决策

| 当前动作 | 目标 API | 前端处理 |
| --- | --- | --- |
| `start-analysis` | `POST /selection-sessions/{session_id}/analyze` | 发送幂等键，保存 `job_id`，进入真实 loading |
| 轮询 | `GET /jobs/{job_id}` | 按 PRD 1s/2s/后台 5s；完成/失败停止 |
| 打开结果 | `GET /decision-versions/{version_id}` | 适配成当前结果卡 ViewModel |
| 恢复当前结果 | `GET /selection-sessions/{session_id}/current-decision` | 检查是否 stale，不盲目使用 localStorage 文案 |
| 查看问题 | `GET /decision-versions/{version_id}/questions` | 展示后端给出的 0–3 问及原因 |

`GET /jobs/{id}` 按 PRD 只返回：

```ts
type JobStatus = {
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'stale'
  progress?: number
  error_code?: string
  result_resource?: string
  result_version_id?: string
  processing_mode?: 'live-ai' | 'cache-fallback' | 'test-fixture'
}
```

普通用户不必看到 `processing_mode`，但前端调试日志不得把缓存结果说成实时 AI。

### 2.4 商家回复与复判

| 当前动作 | 目标 API | 前端处理 |
| --- | --- | --- |
| 粘贴回复 | `POST /selection-sessions/{session_id}/merchant-replies` | 发送原问题/问题 ID、候选 ID、原文、当前 DecisionVersion ID |
| 查看解析 | `GET /merchant-replies/{reply_id}` | 展示 answered/partial/evasive/not-answered/conflicting |
| `submit-rejudge` | `POST /selection-sessions/{session_id}/rejudge` | 保存新 Job 或新 DecisionVersion 引用，禁止本地假复判 |
| 展示差异 | `GET /decision-deltas/{delta_id}` | 展示新增事实、未解决字段、风险与排名/分档变化 |

建议提交 DTO（待 OpenAPI 确认）：

```ts
type MerchantReplyCreate = {
  candidateId: string
  decisionVersionId: string
  questionIds: string[]
  rawReply: string
}
```

前端不得发送自行解析的 claims 作为默认路径，也不得用“回复非空”代表回答有效。

### 2.5 买后反馈桥接

| 当前动作 | 目标 API | 所有权 |
| --- | --- | --- |
| 保存泡茶记录 | 先写本地 `BrewSession` | localStorage 是 P0 主存储 |
| 分析反馈 | `POST /api/v1/brew-feedback/analyze` | 后端只接收最小必要上下文 |
| 保存返回 | 本地保存 `BrewImpact` 与 `PreferenceEvidence` | 不上传完整茶仓或全部历史 |
| 下一次选茶 | 创建 SelectionSession 时提交近期证据摘要 | 后端只作低权重上下文 |

PRD 冻结返回：

```ts
type BrewFeedbackAnalysis = {
  attribution: 'tea' | 'brewing' | 'uncertain'
  next_brew_adjustment?: unknown
  preference_evidence?: PreferenceEvidence
  impact_explanation: string
}
```

`next_brew_adjustment` 的结构尚未冻结，阶段 1 不应先把它写成任意字符串。建议后端返回单一变量调整：字段、方向、幅度、依据和用户文案。

## 3. 当前前端字段映射

### 3.1 本次需求与偏好

| 当前字段 | 目标字段/位置 | 处理 |
| --- | --- | --- |
| `o1` | preference snapshot / raw lifestyle references | 保留原始选择，后端映射领域变量 |
| `o2.sweetness` | preference sweetness hypothesis | 0–100 UI 值不能直接当科学权重 |
| `o2.flavors` | preference flavor tags | 后端白名单归一化 |
| `need.taste` | session need raw text | 本次需求优先于长期偏好 |
| `need.purpose` | purpose | 枚举/原文合同待定 |
| `need.budget` | budget raw text | 后端解析并保留原文 |

### 3.2 候选与证据

| 当前字段 | 目标字段 | 结论 |
| --- | --- | --- |
| `candidate.letter` | 前端显示 label | 不作为 ID |
| `candidate.images` 数字 | `candidate_images[]` | 必须改为资源数组 |
| `candidate.name` | ProductIdentity candidate | 由抽取结果返回，可为空/低置信 |
| `candidate.type` | `tea_type` + `aroma_style` | 不再用拼接字符串 |
| `candidate.fields` | Evidence/unknown/conflict summaries | 不再用单一展示字符串 |

目标核心字段：

```text
tea_type, aroma_style, roast_level, season, origin_text,
year_or_batch, process_text, price, weight_grams, unit_price,
sample_available, return_policy, marketing_claims,
missing_fields, conflicts
```

每条证据还必须带：

```text
information_status + source_type + verification_status
+ source_image_id + source_location + evidence_strength
```

### 3.3 茶仓与日记

| 当前字段 | 目标对象 | 差距 |
| --- | --- | --- |
| `warehouse[]` | `TeaStockItem[]` | 缺 sourceDecisionId、购买快照和稳定枚举 |
| `brew.plan` | `suggestedPlan` + `actualPlan` | 当前只有一份且会被下一泡修改 |
| `brew.completed[]` | `InfusionRecord[]` | 需标准字段和完成时间 |
| `feedback.taste` | `liking` | 中文 → `like/neutral/dislike/unsure` |
| `feedback.strength` | `strength` | 中文 → `light/balanced/strong/unsure` |
| `feedback.source` | `issueSource` | 中文 → `tea/brewing/both/unsure`；后端归因为三类 |
| `feedback.tags` | `feelingTags` | 白名单映射并保留互斥规则 |
| `feedback.aroma` | `aromas` | 最多 3，含排他值 |
| `feedback.advanced` | `SensoryRecord` | 需五个稳定 key，不能用中文 key 作为长期合同 |
| `record.suggestion` | `BrewImpact.nextBrewSuggestion` | 应来自后端或明确本地规则版本 |

## 4. 行动分档唯一映射

| 后端枚举 | 前端中文 | 是否允许前端推断 |
| --- | --- | --- |
| `currently-selectable` | 当前可选 | 否 |
| `ask-before-buying` | 先问清再买 | 否 |
| `sample-first` | 建议先试小样 | 否 |
| `not-recommended-now` | 暂不建议 | 否 |
| `insufficient-information` | 信息不足，无法判断 | 否 |

旧后端映射只用于迁移：

| 旧枚举 | 新枚举 | 备注 |
| --- | --- | --- |
| `prefer` | `currently-selectable` | 需重新跑新规则 |
| `ask_first` | `ask-before-buying` | 可直接概念映射 |
| `sample_first` | `sample-first` | 可直接概念映射 |
| `avoid_now` | `not-recommended-now` | 不含“信息不足”语义 |
| 无 | `insufficient-information` | 新增，不能并入 `avoid_now` |

## 5. 错误与恢复映射

以下为建议错误合同，需在 OpenAPI 中确认，不是已实现事实：

| 场景 | 建议 error_code | 前端恢复动作 |
| --- | --- | --- |
| 非 JPEG/PNG | `invalid_image_type` | 保留候选，重新选图 |
| 超过 5MB | `image_too_large` | 压缩提示或重新选图 |
| 解码/签名失败 | `unsafe_or_corrupt_image` | 删除该图并重传 |
| 低清 | `image_too_low_resolution` | 提示补清晰图，不冒充高置信 |
| 候选超过 5 | `candidate_limit_exceeded` | 禁止创建，不改变现有数据 |
| 单候选超过 2 图 | `candidate_image_limit_exceeded` | 禁止上传第 3 张 |
| Provider 超时 | `ai_timeout` | 只重试目标候选 |
| Schema 校验失败 | `ai_schema_invalid` | 后端修复一次后失败；前端可重试 |
| 任一候选抽取失败 | `candidate_extraction_failed` | 不开始比较；可重试/替换/删除失败项 |
| 旧决策 | `decision_stale` | 返回候选页重新分析 |
| 重复请求 | 幂等返回原资源 | 不重复创建 UI 卡片 |
| 达到限额 | `rate_limit_exceeded` | 显示可恢复时间，不自动重试 |
| 会话过期 | `session_expired` | 保留本地买后数据，重新建选茶会话 |

错误响应建议统一：

```ts
type ApiError = {
  error: {
    code: string
    message: string
    retryable: boolean
    field?: string
    resourceId?: string
    requestId?: string
  }
}
```

## 6. 轮询和并发

前端 Poller 必须按 `job_id` 隔离：

1. 前 5 秒每 1 秒；
2. 5 秒后每 2 秒；
3. 页面进入后台每 5 秒；
4. completed/failed/stale 后停止；
5. 离开页面或删除候选时取消；
6. 同一资源只允许一个活跃 Poller；
7. 重试产生新 Job，旧 Job 结果不能覆盖新版本。

服务端候选最大并发为 3；前端不得自行并发调用 5 个 Provider 请求。

## 7. 数据所有权

| 数据 | P0 权威来源 | 前端可缓存 |
| --- | --- | --- |
| 匿名 client ID | 本地生成/服务端确认 | 是 |
| SelectionSession | 后端 | ID 与恢复摘要 |
| Candidate/Image | 后端 | ViewModel |
| Evidence/ExtractionVersion | 后端 | 当前只读版本 |
| Decision/Question/Delta | 后端 | 当前只读版本 |
| 原始用户图片 | 后端临时处理后删除 | 不放 localStorage |
| TeaStockItem | 本地 | 是，主数据 |
| BrewSession | 本地 | 是，主数据 |
| PreferenceEvidence (P0) | 本地 | 是，主数据 |
| AI/管理日志 | 后端 | 否 |

## 8. 旧 API 到新 API 的迁移判断

| 旧接口 | 新接口 | 迁移结论 |
| --- | --- | --- |
| `POST /compare-sessions` | `POST /api/v1/selection-sessions` | 重写合同 |
| `populate-manual/from-text/from-external` | candidate + image + extraction job | 不保留公开兼容层 |
| `populate-from-images` | 每候选独立图片资源 | 重写；旧整批图片语义不兼容 |
| `/compare` | `/analyze` + `/jobs` + DecisionVersion | 改异步资源模型 |
| `/follow-up-questions` POST | DecisionVersion questions GET | 问题是决策版本派生资源 |
| `/seller-replies` | `/merchant-replies` | 术语和证据模型重写 |
| `/rejudge` | 同名新版本接口 + Job/Delta | 保留概念，不保留 DTO |
| session detail | selection session + current decision | 拆分资源，避免巨型响应 |
| `/admin/*` | `/api/v1/admin/*` | 仅迁移必要能力 |

## 9. OpenAPI 冻结前待确认

1. `SelectionNeedInput` 的预算、用途和风险态度最终字段；
2. anonymous client ID 放 Header、Cookie 还是请求体；
3. 创建候选是否允许同时上传第一张图，还是严格两步；
4. 上传接口返回 Job，还是图片资源中包含 `current_job_id`；
5. `POST /analyze` 在候选抽取尚未完成时的错误码；
6. DecisionVersion 的候选排序、分档、证据摘要和 explanation DTO；
7. 问题为 0 条时的合法返回；
8. MerchantReply 覆盖多个问题时的字段结构；
9. `rejudge` 同步创建版本还是异步 Job；
10. `next_brew_adjustment` 的结构化 Schema；
11. 前端提交近期 PreferenceEvidence 的数量上限和最小字段；
12. 清除匿名云端会话的接口是否进入 P0。

这些问题确认并写入 OpenAPI 后，才适合开始阶段 1 接口代码。

