# Provider / 双图 / Evidence 只读审查

审查日期：2026-08-08  
审查范围：`FakeProvider`、`MiMoVisionProvider`、Provider factory、图片 Job、同 Candidate 双图、Evidence 溯源、Extraction / Decision stale。  
审查方式：只读代码与既有自动化测试；**未调用真实 MiMo、未修改 Prompt、未修改业务代码**。

## 结论

当前代码已经具备「Candidate 内最多两张图、第二张 Job 携带同 Candidate 当前图片集合、Provider 接口可一次接收多个 object key、完成时写入一个新的 ExtractionVersion」的骨架，并且 PostgreSQL 层会将不同 Candidate 的图片集合隔离。

但它尚不满足本轮集中收口的关键验收：比赛正常运行时会默认启用 FakeProvider；双图的单条 Evidence 无法可靠归属到第二张图片；第二张图上传后旧 Extraction 在新联合提取完成前仍可作为 current；并且当前是“上传第一张立即做一次调用、上传第二张再做一次联合调用”，不是一次 A1+A2 联合理解。这些问题会让真实比赛链路产生 fixture、错误溯源或旧结果展示，必须先修复再做最终 E2E。

## P0：阻止比赛真实链路验收

### P0-1 比赛默认 runtime 会进入 FakeProvider

- **证据**：`backend/src/guancha_api/main.py:45-64` 的 `_provider_from_environment()` 使用 `os.getenv("GUANCHA_PROVIDER", "fake")`；缺少环境变量时直接构建内置 `FakeProvider`。`create_app()` 在 `main.py:96-99` 默认调用该 factory。
- **结果**：正常启动而未显式设置环境变量时，用户上传真实截图会生成固定的 `安溪铁观音` / `fixture` Evidence，而不是失败并要求配置真实 MiMo。
- **为什么是 P0**：本轮产品冻结要求比赛正常用户流程必须使用真实 MiMo；Fake 只能用于自动测试或明确内部环境。这里没有内部环境开关、启动阻断或 UI 可见的运行模式区分。
- **建议方向**：将运行模式显式化；比赛/production 启动时缺少 `GUANCHA_PROVIDER=mimo`、模型或 Key 应启动失败或仅暴露不可分析状态。Fake 必须要求显式测试开关/测试注入，绝不能成为默认。

### P0-2 双图 Evidence 不能可靠标注真实来源图

- **证据 1**：`backend/src/guancha_api/providers/openai.py:43-65` 的共享 `_EXTRACTION_SCHEMA` 没有 `source_image_index` 字段，且 `additionalProperties: false`。MiMo 在 `backend/src/guancha_api/providers/mimo.py:135-156` 把同一 Candidate 的多张图一起发送，但要求模型遵循该 schema。
- **证据 2**：`backend/src/guancha_api/application/job_runner.py:33-44` 的内部 `FakeEvidencePayload` 虽有 `source_image_index`，却默认 `1`；`job_runner.py:167-185` 据此把 `source_image_id` 写为 `input_image_ids[item.source_image_index - 1]`。
- **证据 3**：`job_runner.py:187-202` 对模型没有给出独立 Evidence 的结构化字段，又为展示字段补造 Evidence，并且在 `job_runner.py:199,202,301-311` 无条件使用第一张图片 ID。
- **结果**：真实 MiMo 无法在严格 schema 中返回图序号，因此其所有原始 Evidence 都会落到 A1；若价格、规格或详情只出现在 A2，`source_image_id` 仍错误地指向 A1。补造的 `price`、`origin`、`risk_flag` 等展示 Evidence 也一律指向 A1。
- **为什么是 P0**：本轮明确要求每项 Evidence 可追溯且 `source_image_id` 正确；错误归属会污染后续 Decision、追问和商家回复的依据，不能用 `source_image_ids` 的集合存在来替代逐条来源。
- **建议方向**：在共享 Provider 输出合同中加入受约束的 `source_image_index: 1|2`（或等价且可验证的 image reference）；把 Prompt、Pydantic 和 JSON Schema 同步。对于无法归属的结构化摘要，不要伪造 A1 来源，应以 `unknown` / candidate-level 明确语义持久化或要求模型给出依据。

### P0-3 补第二张图后旧 Extraction 仍可被当作 current

- **证据**：上传新图后 `backend/src/guancha_api/application/phase2_service.py:117-154` 会创建新 Job，并在 `:140` 仅调用 `stale_current_decision_for_candidate()`；没有使当前 Extraction stale。`backend/src/guancha_api/repositories/postgres.py:582-587` 的 `get_current_extraction_for_candidate()` 只查询 `is_current and status='completed'`，不校验 `candidates.image_set_version`。
- **对照**：删除图片时 `postgres.py:1136-1147` 会显式把当前 extraction 设为 `stale`，说明所需语义已在另一条路径中存在。
- **结果**：A1 已完成后上传 A2，在 A1+A2 联合 Job 完成前（甚至联合 Job 失败后）页面仍能读取只基于 A1 的旧 Extraction，尽管 Candidate 的图片集合已变化。
- **为什么是 P0**：这会使一个已经改变输入集的 Evidence / Decision 被显示为当前结论，违反“补图后旧 extraction / decision stale”的集中验收要求。
- **建议方向**：新图片成功持久化且产生新 image set 后，在同一明确状态转换中使该 Candidate 的 current Extraction 与所在 session 的 current Decision stale；仅联合 Job 成功时再创建新的 current Extraction。需要回归“新 Job 失败时 current-extraction 不得回退为旧输入集结论”。

## P1：当前阶段必须修复

### P1-1 A1+A2 不是一次联合提取，而是先单图、后双图两次调用

- **证据**：每次上传都会在 `phase2_service.py:117-126` 调用 `create_image_and_initial_job()`，并在 `:142-145` 立即入队。Repository 在 `postgres.py:336-348` 将“目前所有未删除图片”作为该新 Job 的 `input_image_ids`。
- **既有测试反证**：`backend/tests/test_phase3_multi_candidate_multi_image.py:130-159` 明确断言首图 provider input 是 `(A1,)`，第二次才是 `(A1, A2)`（`:153-154`），并且产生 `v1 != v2`（`:141,149,152`）。
- **结果**：用户依次上传 A1、A2 时，会发生一次单图提取和一次双图提取。后者确实是单次联合调用并得到一个新 Version，但前者仍消耗一次真实调用、产生历史 Version，并可能短暂对外可见。
- **建议方向**：把“上传图”与“提交当前图片集进行提取”分开，或为双图场景设置明确的集合完成/防抖边界；最终 A1+A2 只允许一个联合 Job / 一个当前 ExtractionVersion。不能用前端拼字段或两个独立 Version 伪装联合理解。

### P1-2 MiMo 双图请求缺少专门的离线回归测试

- **证据**：MiMo adapter 确实循环 `keys`，见 `backend/src/guancha_api/providers/mimo.py:120-157`；但 `backend/tests/test_mimo_provider.py:85-107` 只断言一张图。多图契约测试在 `test_phase3_multi_candidate_multi_image.py` 中使用的是 `RecordingFakeProvider`（`:28-36,130-159`），不是 MiMo adapter。
- **风险**：当前真实 MiMo 请求格式为 OpenAI-compatible `chat.completions` 的 `image_url` 数组，且已经过几次网络/超时调试；没有一个 test double 断言两张图都进入同一 `messages[1].content`，容易被以后改动破坏。
- **建议方向**：增加纯离线 client fake 测试：传入两个 private object keys，断言只发一条 request、两个 `image_url` 均存在且顺序对应 A1/A2；不触发真实网络。

### P1-3 “FakeExtractionJobRunner” 命名掩盖真实 Provider runtime

- **证据**：`backend/src/guancha_api/application/phase2_service.py:47` 无论传入的是 Fake、MiMo 还是 OpenAI 都实例化 `FakeExtractionJobRunner`。`job_runner.py:231-235` 再依 provider name 写 `live-ai`。
- **影响**：功能本身可工作，但名称和测试夹杂会促进“Fake fixture / live AI”概念混淆，也使排查实际运行模式更困难。
- **建议方向**：后续 WP1/WP2 将其重命名为 provider-neutral `ExtractionJobRunner`（保持兼容别名可选）；同时记录并在 API/UI 显式隔离 internal/test mode。该重命名不得与 UI 重做绑定。

## P2：可在集中收口后处理

### P2-1 `cache-fallback` 合同描述与实际 runtime 不一致

- **证据**：`backend/src/guancha_api/schemas/contracts.py:78-80` 描述一个“真实 Provider 失败后”的 exact demo fallback。但在 `backend/src/guancha_api` 的运行代码检索中没有对应 fallback 执行路径；只有 tests support 中有 catalog (`backend/tests/support/demo_fallback.py`)。
- **判断**：这不会造成“真实失败自动变 fixture”；实际执行链 `backend/src/guancha_api/providers/execution.py:45-84` 在失败时抛 typed error，`job_runner.py:147-160` 将 Job 失败。因此真实失败**当前不会自动回退到 fixture**，这是通过项。
- **建议方向**：在 WP1 统一删除未实现的对外语义，或实现一个仅内部显式启用、可审计且不会伪装为 live-ai 的策略；比赛真实流程不应依赖它。

### P2-2 已完成双图的私有对象会保留到图片删除

- **证据**：`job_runner.py:113-123` 注释说明为支持后续 A1+A2 联合调用而保留；`complete_extraction_job()` 在 `postgres.py:1271-1274` 明确忽略 `temporary_image_deleted`。
- **判断**：这是目前支持补第二张图的有意设计，不是本次 P0。不过对象生命周期、重启后的 InMemory storage 与真实持久化 storage 的差异需作为部署前风险单列。

## 已确认通过的边界

| 审查项 | 代码 / 测试证据 | 结论 |
|---|---|---|
| 真实 MiMo 出错不会自动调用 Fake | `providers/execution.py:45-84` 只重试同一 provider；`job_runner.py:147-160` 写 failed；未找到 runtime fallback 调用 | 通过 |
| MiMo 可接收多图 object key | `providers/mimo.py:120-157` 循环所有 `image_object_keys` 并组合进一条 chat completion request | 实现存在，需补专测 |
| 同 Candidate 的第二个 Job 取得该 Candidate 全部图 | `repositories/postgres.py:283-348` 先锁 Candidate，再查询 `candidate_images where candidate_id=%s` | 通过 |
| 跨 Candidate 图像集合隔离 | Job 查询条件固定 `candidate_id`；`test_phase3_multi_candidate_multi_image.py:215-240` 验证 3 个 Candidate / 6 图的 current version 与 Evidence 不串线 | 通过（Fake 集成层） |
| 当前 Extraction 的 Version / Evidence / Job 完成原子写入 | `repositories/postgres.py:1275-1349` 单 transaction；会校验每项 `source_image_id in input_image_ids` | 通过，前提是输入来源本身正确 |
| 截图 Evidence 强制 product-claim / unverified | `job_runner.py:175-180` 覆盖 Provider 输出；`test_mimo_provider.py:242-265` 覆盖 MiMo test double | 通过 |
| 删除图片会 stale Extraction 与 Decision | `repositories/postgres.py:1136-1147` | 通过 |

## 建议的最小修复顺序

1. **WP1**：取消比赛 runtime 默认 Fake；将 real provider 未配置 / 失败显式化为不可分析或 failed，不制造 fixture success。
2. **WP2**：定义单次“当前图片集合”提交语义，修复 A1+A2 的单次联合 Job；新图入库时立即 stale 旧 extraction / decision。
3. **WP2**：把 `source_image_index` 加入同一个 Provider / Pydantic / Evidence 合同，拒绝越界和不明来源的双图 Evidence；补 MiMo 双图离线测试。
4. 回归：A/B/C，A 两图、B 两图、C 一图；断言每个 current extraction 的 `source_image_ids`、每项 Evidence 的 `source_image_id`、旧 Version 的 stale、不同 Candidate 无 Evidence 串线；真实 MiMo 只做一次已批准的固定人工 smoke。

## 审查限制

- 本报告没有调用真实 MiMo，也没有读取或输出任何 Key。
- 既有多图全链路测试使用 `FakeProvider`；因此它证明数据库/Job 组合，但不证明实际 MiMo 服务响应能够正确返回双图 Evidence 来源。
- 本文件是当前集中只读审查的一部分；修复方案应由 orchestrator 与其余 audit 统一裁决后实施。
