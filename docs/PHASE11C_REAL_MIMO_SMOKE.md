# Phase 11C｜Real MiMo A/B Core Value Smoke

最终状态：`READY_FOR_DEADLINE_DEMO`。

## 真实调用

| 候选 | 实际截图 | job | extraction | provider / model / mode | 图片数 |
|---|---|---|---|---|---|
| A | `screenshot_20260531_155443.png`（标题明确“清香型兰花香”） | `b617f07d-ce22-5116-b530-5cbc75134006` | `79af8112-7ce9-490a-9436-fc6f5d336c0c` | `mimo` / `mimo-v2.5` / `live-ai` | 1 |
| B | `screenshot_20260531_195725.png`（标题明确“浓香铁观音”） | `eee39528-924f-58dc-bc6c-235e4cd72686` | `6325aa67-6d4b-4815-9821-25fff164faf1` | `mimo` / `mimo-v2.5` / `live-ai` | 1 |

真实调用数为 2；技术重试为 0。未记录 API Key、图片 base64 或数据库密码。

## Fake 诊断

详见 `FINAL_FAKE_SENSORY_DIAGNOSIS.md`：A/B Fake payload 完全相同，缺少 mapper 所需的受控字段，分类为 `FIXTURE_INSUFFICIENT`。

## 真实 Evidence 与展示结果

| 候选 | 非敏感真实 Evidence | Sensory Interpretation | Personal Fit |
|---|---|---|---|
| A | `tea_category=乌龙茶`、`tea_subtype=铁观音`、`roast_or_style=清香型`、`sample_available=true` | “如果商品页的清香型描述准确，整体风格通常更偏清鲜、轻扬。”并明确不代表已验证实际花香 | “清香或低火味线索，更接近…清爽花香方向。” |
| B | `tea_category=乌龙茶`、`tea_subtype=铁观音`、`roast_or_style=浓香型`、花果熟香声明 | “如果商品页的浓香型描述准确，风格通常更偏熟香、醇厚方向。”并明确不代表实际浓度已验证 | “更偏熟香或焙火方向…可能更偏另一种风格。” |

首次真实结果存在 P1 展示断点：live provider 的香型写入兼容字段 `roast_or_style`，mapper 仅将它视为焙火词，故 Sensory section 为空。已作最小修复：将该字段中的清香型/浓香型按受控香型解释处理；未改 Prompt、MiMo、Evidence、Decision 或数据库。浏览器复验通过，A/B感官解释和 Personal Fit 均不同且保持条件/边界语言。

## Need、偏好、排序

- Current Need 位于 Personal Fit 第一行；O1/O2 只在最后作为“低置信口味参考”，明确不覆盖 Need。
- Presentation 没有重排：DecisionVersion 仍为 A `overall_order=1`、B `overall_order=2`，两者都是 `insufficient-information`。
- `tea_category` / `roast_or_style` 与规范字段的历史语义混合仍应赛后治理；本轮没有让展示层替代或篡改 Decision 排序，后端的 A1/B2 及 `insufficient-information` 状态保持权威。

## Question 与 Rejudge

- 两款均产生“具体焙火程度”这一高价值问题，UI 明示它可能改变高风险提示或补足判断说明。
- 测试回复：A“轻火焙制，火味不明显”；B“中足火焙制，焙火感会比较明显”。
- 保存全部回复后已执行一次 aggregate rejudge。Delta 以“这次补充对你意味着什么”展示“焙火程度”，无英文/raw enum，并说明新信息未改变当前首选、但使偏离本次需求的原因更明确。

## Gate 判定

| Gate | 结果 |
|---|---|
| Real Evidence Difference | PASS |
| Sensory Interpretation / Safety | PASS（修复后） |
| Personal Fit / O1-O2 Return | PASS（修复后） |
| Question / Aggregate Rejudge / Delta Meaning | PASS |
| Backend ranking authority | PASS（未被展示层覆盖） |
| NOT JUST OCR | PASS：同样的香型、焙火、价格、规格 Evidence 进入现有账本时，解释、个人适配、追问、复判仍成立；图片仅是该 Evidence 的一个采集入口。 |

独立审查见 `FINAL_REAL_MIMO_CORE_VALUE_REVIEW.md`：P0=0、P1=0、P2=1（历史字段语义治理），可判为 `READY_FOR_DEADLINE_DEMO`。

## Git 保护

- `README.md`：`PRE_EXISTING_README_DIRTY = YES`，未触碰。
- 本阶段代码修复仅在 `answer_contract.py`、`adapters.js`、`index.html` 及对应测试中。
