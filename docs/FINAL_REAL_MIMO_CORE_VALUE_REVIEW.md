# Final Real MiMo Core Value Review

审查类型：独立只读审查（Phase 11C）。

审查材料：真实 A/B 的非敏感运行记录、浏览器结果与复判观察，以及当前
`answer_contract.py`、`frontend/adapters.js`、`app.js`。本审查未读取密钥、数据库密码或图片内容，未改动生产代码。

## 受审事实

- A：`mimo` / `mimo-v2.5` / `live-ai`，一张真实商品截图；关键显式页面线索为
  `tea_category=乌龙茶`、`tea_subtype=铁观音`、`roast_or_style=清香型`、
  `sample_available=true`、价格 `55.3`。
- B：`mimo` / `mimo-v2.5` / `live-ai`，一张真实商品截图；关键显式页面线索为
  `tea_category=乌龙茶`、`tea_subtype=铁观音`、`roast_or_style=浓香型`，并有
  “花果熟香”商品页声明。
- 两者均仍因关键购买信息不完整而在 `DecisionVersion` 中为
  `action_bucket=insufficient-information`；其服务端顺序为 A=1、B=2。
  这不是展示层自行决定的排序。
- 商家回复为 A“轻火”、B“中足火”。统一复判展示“焙火程度”，说明首选未变、
  但对与本次需求的关系更明确；未展示工程枚举。

## 九项审查

### 1. 这仍然像 OCR 吗？

**否，核心结果链不再像 OCR。** 商品页信息只是受限的输入证据；结果首层先展示
“为什么它更像 / 不像你会喜欢”，以本次 Need 和受控风格线索解释 A/B 的意义，
商品字段后置。截图上传仍是事实入口，但不是最终价值表述。

### 2. A/B 是否真的基于 Evidence 形成不同体验解释？

**是。** A 的显式“清香型”被映射为“通常更偏清鲜、轻扬”，并与“清爽花香、火味不要太明显”对应；B 的显式“浓香型”被映射为“通常更偏熟香、醇厚方向”，因而提示其更偏另一种风格。两种说法由相异的 `roast_or_style` Evidence 触发，不依赖候选字母或硬编码排序。

### 3. Sensory Translation 有没有把推断冒充实喝？

**没有。** mapper 仅消费 `information_status=explicit` 的 Evidence，且用“如果商品页……描述准确”“通常”“不代表已验证实际浓度/某种花香”等边界语。它没有断言用户已经喝到花香、没有火味，或 B 的品质高低。

### 4. Personal Fit 是否真的与 Current Need 相关？

**是。** 前端的第一条解释固定为本次明确的 Need；随后才基于 Sensory Interpretation 给出“更接近清爽花香”或“更偏另一种风格”。A/B 的差异由 Need 与真实 Evidence 的关系形成，而非由既往偏好覆盖 Need。

### 5. O1/O2 是否获得合理回报？

**是，且位置正确。** O1/O2 在结果中作为有限、低置信的口味参考出现，并明确“不覆盖你这次的需求”。本轮的兰花、水蜜桃、柑橘等偏好没有被重复堆砌，也没有被送入后端排序。

### 6. 后端 ranking 是否仍权威？

**是。** `applySessionDecision()` 按服务端 `overall_order` 排序；结果优先标签读取
`DecisionVersion` 的 `overall_order` / `action_bucket`。Personal Fit 仅解释“接近/偏离”，不写回、也不重排 A/B。当前 A=1、B=2 与服务端 Decision 一致。需要强调：Decision 仍是 `insufficient-information`，展示层没有把它包装为已可直接购买的确定推荐。

### 7. Question 是否具有 Decision Value？

**是。** 真实后端问题聚焦具体焙火程度；页面同时说明“为什么值得问”以及该回答可能改变风险、行动建议或当前选择。它不是为了补全所有商品字段而问的泛问题。

### 8. Rejudge 是否体现新证据改变理解？

**是。** A 的“轻火”和 B 的“中足火”被保存后统一复判，Delta 以用户语言展示“焙火程度”。本轮排名未变，但页面明确说明未变的原因：补充信息让“为什么接近/偏离本次需求”更明确；没有虚构排名变化。

### 9. 如果去掉图片输入，观茶价值是否仍成立？

**是，作为核心价值合同成立。** 若用户以其他可信入口提供同样的显式香型、焙火、价格等 Evidence，当前 mapper、Personal Fit、Question 和统一 Rejudge 仍可输出同一类受边界约束的解释。这里的判断不等于声称当前比赛版另有完整的手动录入页面；它说明价值不依赖“识别几个字段”本身，而依赖 Evidence 到选择解释的链路。

## 风险分级

- **P0：0。** 未发现真实 Evidence 已存在而被感官 mapper、DTO 或结果页丢失的断点；展示顺序与服务端 Decision 顺序一致。
- **P1：0。** `insufficient-information` 是当前缺少关键购买信息时的服务端保守结论，不是前端问题；本轮没有以 Personal Fit 绕过该边界。
- **P2：1。** `roast_or_style` 是历史兼容字段，承载“清香型/浓香型”时语义混合。当前最小 alias 映射对本轮两个明确值有效且有回归测试；赛后宜将抽取字段语义统一，但不应在截止前扩展 Schema 或重写 Decision。

## 最终判定

**READY_FOR_DEADLINE_DEMO**

条件均满足：真实 A/B 为 `live-ai` 且 Evidence 明显不同；感官翻译具有边界；Need 优先、O1/O2 仅作参考；服务端排序仍权威；Question、统一复判和 Delta 均已体现决策价值。当前“信息不足”的购买边界应保留在演示话术中，不应被表述成确定购买推荐。
