# Phase 11C｜Fake Sensory 诊断

结论：`FIXTURE_INSUFFICIENT`。

本诊断只读取当前 FakeProvider 配置和 Sensory mapper；未调用真实 MiMo。

## Phase 11B 实际 Fake Evidence

FakeProvider 对每个候选返回同一份固定 payload，与上传的图片内容无关：

| 字段 | Candidate A | Candidate B |
|---|---|---|
| `tea_type` | 未作为该字段输出（旧字段为 `tea_category=乌龙茶`） | 相同 |
| `tea_subtype` | 铁观音 | 相同 |
| `aroma_style` | 缺失 | 缺失 |
| `roast_level` | 缺失 | 缺失 |
| `roast_or_style` | 清香型 | 相同 |
| `season` | 缺失 | 相同 |
| `sample_available` | 缺失 | 相同 |
| `marketing_claims` | 缺失（虽有旧 `aroma_claims=兰花香`，但不生成对应 Evidence） | 相同 |

两者都只有相同的商品名、茶类、铁观音、安溪和 `roast_or_style=清香型` Evidence。

## Sensory mapper 的当前支持范围

- `aroma_style=清香型/浓香型`：生成对应的、带“如果商品页描述准确／通常／不代表”的风格说明。
- `roast_level` 或 `roast_or_style` 中的轻焙、轻火、足火、中焙、重焙等：生成受边界约束的焙火说明。
- `sample_available=true`：生成试饮行动说明。
- `marketing_claims` 中的“兰花香”：只生成页面声明边界，不当作实喝体验。

Fake 的 `roast_or_style=清香型` 不属于 mapper 的焙火词，也没有 `aroma_style` Evidence；因此不会生成 Sensory section。这是输入字段不足的预期结果，不是 mapper 把有效 `aroma_style` 或 `roast_level` 丢失。

## 对四个问题的回答

1. A/B Fake Evidence 是否相同或高度相似？**是，完全相同。**
2. Fake 是否缺少可触发感官翻译的字段？**是，缺少 `aroma_style`、`roast_level`、明确的焙火词和 `marketing_claims` Evidence。**
3. 若 Fake 存在有效 Sensory 输入，为何最终为空？**不适用。它没有 mapper 支持的有效输入；旧别名中的“清香型”不是焙火词。**
4. 分类：**`FIXTURE_INSUFFICIENT`**。

不修改生产 Sensory 逻辑；继续对两张已有真实商品截图执行一次受控的 live-ai 烟测。
