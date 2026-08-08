# ANSWER_CONTRACT_V2：后端事实合同与用户答案合同分层

> 状态：**待实施设计**。本文件不变更现有 OpenAPI、Evidence 枚举、Prompt、Provider 或数据库迁移。
>
> 适用范围：铁观音比赛版，单个 Selection Session 内 1–5 个 Candidate，每个 Candidate 1–2 张商品截图；候选间独立提取、统一比较。

## 1. 目标与边界

用户需要的不是 Evidence dump，而是一份可行动的选茶答案：

```
当前结论 → 为什么和你有关 → 已知事实 → 关键不确定项 / 风险 → 一个下一步
```

Answer Contract V2 **不是**新的事实来源：

- 不取代 `ExtractionVersion`、`EvidenceItem`、`DecisionVersion`、`FollowupQuestion`、`MerchantReply` 或 `DecisionDelta`。
- 不创建第二次模型调用，不改 Vision Prompt，不推测缺失字段。
- 不将 `merchant-claim/unverified` 升级为“已验证事实”。
- 不把 `internal_score`、枚举或 Provider 细节给普通用户。

## 2. 两层合同

### 2.1 Backend Data Contract（系统事实合同，保留现有）

| 领域对象 | 现有权威字段 | 角色 |
|---|---|---|
| `ExtractionVersionResponse` | `candidate_id`, `source_image_ids`, `status`, `evidence_items` | 某一候选、1–2 张截图的不可变抽取快照 |
| `EvidenceItem` | `field_name`, `raw_text`, `normalized_value`, `information_status`, `source_type`, `verification_status`, `source_image_id`, `source_location`, `evidence_strength` | 可追溯事实；不是页面文案 |
| `CandidateDecision` | `action_bucket`, `overall_order`, `reasons`, `risk_flags`, `missing_critical_fields`, `score_components` | 后端确定性比较输出 |
| `FollowupQuestion` | `field_key`, `question_text`, `reason`, `affected_decision`, `answer_branches`, `priority` | 只挑能改变判断的问题 |
| `MerchantReply / MerchantClaim` | 原文、解析状态、`merchant-claim/unverified` | 商家声明，追加而非覆盖商品页声明 |
| `DecisionDelta` | 新旧版本、补全字段、未解决字段、风险变化、排序/行动变化、解释 | 重判前后可追溯变化 |

这些字段的当前代码依据见：`backend/src/guancha_api/schemas/contracts.py:340-467`。

### 2.2 User-facing Answer Contract（用户答案合同，新增 presentation 层）

建议内部命名 `SelectionAnswerV2`；可先作为后端 mapper 返回给页面，或作为 `api/services` 中唯一允许替换 mock 的 adapter 输出。其稳定性优先于当前数据库字段。

```json
{
  "answer_version": "v2",
  "selection_session_id": "uuid",
  "decision_version_id": "uuid",
  "status": "ready | needs_follow_up | failed",
  "headline": {
    "kind": "relative_recommendation | ask_before_buying | sample_first | insufficient_information | not_recommended_now",
    "text": "当前相对更适合候选茶 A",
    "candidate_id": "uuid-or-null",
    "qualification": "价格仍未明确，结论以当前商品页信息为准。"
  },
  "candidates": [
    {
      "candidate_id": "uuid",
      "position": 1,
      "display_name": "候选茶 A",
      "product_title": "安溪铁观音…",
      "image_preview": { "image_id": "uuid", "alt": "商品截图" },
      "verdict": "当前更值得继续考虑",
      "why_it_fits": ["最多三条、只说与本次需求直接有关的理由"],
      "known_facts": [
        {"label": "茶类", "value": "铁观音", "basis": "商品页明确标注"}
      ],
      "decision_uncertainties": [
        {"label": "价格", "why_it_matters": "会影响是否符合你的预算", "change_if": "若超出预算，当前结论可能下调"}
      ],
      "risks": ["最多三条、自然语言且与购买决定有关"],
      "next_step": {
        "kind": "ask_merchant | sample | consider | avoid",
        "text": "先向商家确认到手价是否为…",
        "question_id": "uuid-or-null"
      }
    }
  ],
  "rejudgement": {
    "available": true,
    "summary": "商家补充的价格信息没有改变候选茶 A 当前相对更适合的结论。",
    "changed": false,
    "resolved": ["价格已明确"],
    "still_matters": ["焙火程度仍未明确"]
  }
}
```

### 2.3 禁止出现在普通用户结果页的内容

| 禁止直接显示 | 改为 |
|---|---|
| `product-claim`, `merchant-claim`, `unverified`, `explicit` | “商品页明确标注”“商家后续说明”“尚待进一步确认” |
| `fixture`、Provider 名称、模型名 | 不显示；出现即视为 runtime / presentation P0 |
| `tea_subtype`、`risk_penalty`、`internal_score`、`source_image_id`、`source_location` | 中文标签或完全不显示 |
| 缺失字段的全量列表 | 最多 1–3 条真正可能改变本轮决定的不确定项 |
| 原始商家回复解析状态 | “已补充 / 未回答 / 信息互相矛盾”的自然语言摘要 |

## 3. 映射规则

### 3.1 Headline（全局结论）

| 后端条件 | 用户文案原则 |
|---|---|
| 存在 `top_candidate_id` 且至少一个 Candidate 有可区分的决策依据 | “当前相对更适合候选茶 X”；附一句关键保留条件 |
| 顶部候选为 `currently-selectable` | “当前可优先考虑候选茶 X” |
| 顶部候选为 `sample-first` | “风格方向可继续考虑，建议先试饮候选茶 X” |
| 顶部候选为 `ask-before-buying` | “候选茶 X 暂时更接近你的需求，但先问清 X 再买” |
| 没有可区分依据，或所有候选的关键差异仍未知 | “目前还不能可靠地区分这几款茶”；只在此时用 `insufficient_information` |
| 顶部候选为 `not-recommended-now` | “当前不建议直接购买”；说明关键冲突或风险 |

**关键规则**：有 unknown 字段不等于 `insufficient_information`。只有 unknown 会消除候选间的区分性、或命中高影响反事实时，才阻断结论。

### 3.2 Why it fits（最多三条）

输入：当前 Candidate 的 `Decision.reasons`、用户 `SelectionNeed`、强度足够且相关的 Evidence。

输出规则：

1. 优先“需求 → 已知事实 → 为什么有关”的完整句。
2. 不把品牌营销词变成事实；`product-claim/unverified` 只能说“商品页标注”，不能说“已经证实”。
3. 不够三条时留空，不用默认话术凑满。

示例：

> 你这次想找清香、日常喝的方向；商品页明确标注为铁观音并写有清香型描述，因此与本次偏好存在直接匹配。

### 3.3 Known facts（3–5 条）

- 展示 `information_status in {explicit, inferred}` 的 Evidence，但 `inferred` 必须带“页面内容推测”。
- 优先：产品名、茶类/具体茶类、香型/焙火、净含量、价格、产地、试饮/退换；按本次 Need 的相关度排序。
- 每项只用 `{label, value, basis}`，不泄漏 `source_type` / `verification_status`。
- 多图同候选只汇总同一个 ExtractionVersion 的 Evidence；不得从其他 Candidate 拼字段。

### 3.4 Uncertainties and risks（各最多三条）

`decision_uncertainties` 只来自 `missing_critical_fields` 中经 Question Value 判断仍会影响决策的字段；每项必须有：

- 缺什么；
- 为什么与本次 Need 有关；
- 什么答案可能改变结论。

`risks` 来自 `risk_flags` 或 `information_status=conflict`；必须说后果，不显示内部 flag 名。

### 3.5 Next step（至多一个关键动作）

| 条件 | 动作 |
|---|---|
| 有高价值 `FollowupQuestion` | `ask_merchant`，显示该问题与“为什么问” |
| 有试饮证据且风险集中在体验不确定 | `sample` |
| 当前可选择且无高价值追问 | `consider`（“可考虑加入茶仓 / 继续查看”） |
| 高风险或冲突 | `avoid` |

问题必须来自现有 `FollowupQuestion`，不得由页面临时杜撰。

## 4. 商家回复与统一复判的展示合同

本合同依赖后续“分别保存 → 汇总一次复判”的流程；它不改变已冻结的 Evidence 枚举。

1. 每个 Candidate 的回复先显示“已保存，等待本轮统一更新判断”。
2. 仅有问题的 Candidate 需要回复；没有问题的不强制填写。
3. 用户点击“更新判断”后，服务端汇总有效 Merchant Evidence，创建新的不可变 `DecisionVersion` 与一个 `DecisionDelta`。
4. 结果只能二选一地清楚表达：
   - **判断改变**：什么新事实使哪一项排序/行动变化；
   - **判断未变**：补充了什么、为何仍不足以改变“当前相对更适合”的结论。
5. 不能用硬编码“推荐/变化”示例替代 Delta。

## 5. 实施边界与验收

### 最小文件责任

| 层 | 建议位置 | 不应承担 |
|---|---|---|
| Mapper | `backend/src/guancha_api/application/answer_contract.py`（或同级） | Provider 调用、数据库查询、UI HTML |
| API DTO | `backend/src/guancha_api/schemas/contracts.py` 的新增只读 DTO；或单独 presentation schema | 覆盖 Evidence/Decision 权威 DTO |
| 路由 | 现有 `api/v1/routes.py` 加只读 answer 端点，或由既有读接口服务层内部使用 | 拼 UI 文案或访问本地存储 |
| 前端 adapter | `frontend/adapters.js` / `api-client.js` | 修改 CSS、SVG、页面结构 |
| 页面 | `app.js` 只渲染 V2 已组织字段 | 读取 raw Evidence 枚举 |

### 验收用例

1. 真实/假 Provider 的提取结果都经过同一 mapper；Fake 标记绝不出现在正常答案。
2. 有价格 unknown 但 A/B/C 仍可区分时，headline 仍给“当前相对更适合 X”，并把价格列为关键待确认项。
3. 没有可区分证据时才输出“目前还不能可靠地区分”。
4. 每条 `known_fact` 可追溯到本 Candidate 的 Evidence；跨候选污染测试必须失败。
5. 用户页文本不得出现 `fixture`、snake_case、raw enum、`internal_score`、Provider/模型名。
6. 商家回复只追加 Merchant Evidence；商品页声明仍保留；统一复判后 V1/V2/Delta 均可追溯。
7. 高保真 UI 的结构与样式不变，只替换 `api/services` 与结果字段来源。

## 6. 当前代码到 V2 的差距分级

### P0

- `app.js:740` 直接渲染工程 Evidence 细节，违反本合同“普通用户不看 raw enum”。
- `app.js:673-687` 的复判文案硬编码，不能用真实 `DecisionDelta` 证明答案变化。

### P1

- `app.js:258-264` 没有 Answer mapper，仅截断后端 reasons。
- `app.js:743-745` 将 `insufficient-information` 当作普通结果动作，未表达“相对推荐 + 条件”的中间态。
- 商家回复当前按单 reply 立即复判；这与“保存后统一复判”的 V2 约束不符（相关 API 当前见 `api/v1/routes.py:246-260`）。

### P2

- Answer 文案可在未来支持更细的可访问性、国际化与管理员证据视图；这些不阻塞比赛版。
