# 观茶 Current System SSOT 最终事实核验

核验日期：2026-08-13  
核验方式：独立只读反向检查；核验者未修改代码或文档。  
最终结果：`PASS`

## 核验目标

逐项检查 SSOT 中所有“Current / Implemented / Verified”表述，避免出现：

- PRD 愿景冒充当前实现；
- 自动测试冒充真实世界准确率；
- fixture 冒充 live Provider 质量；
- 买后设计冒充完整上线；
- analytics 基础设施冒充真实用户使用；
- 0 位参与者冒充用户验证；
- HTTP 200 冒充 Browser E2E；
- Docker/Procfile 冒充已确认托管平台。

## 第一轮结果与修订

第一轮未发现 P0，但要求修正结构与事实分级。主文档随后完成：

- Future Codex header 与 Document Authority；
- 四类 Current Product Scope；
- 完整 Non-goals、逐步 Flow 状态和 Architecture Layers；
- AI/Rule Boundary、Replay/Idempotency；
- Need 前端 transition 与 PostgreSQL 未验证边界拆分；
- 正式 Release Gate blockers 收束为数据库和浏览器；
- 平台/Provider/deployed commit 移至未决运行事实；
- 历史 UI 观察移出当前 P2；
- 未决问题补齐未知原因与关闭证据；
- Git 分支/commit 角色和 Claims to Avoid；
- Contradiction Audit 的旧说法状态与当前事实状态拆分；
- 买后“已设计/未来”分类去重。

## 第二轮结论

### P0

0。

### P1

0。

### 已反向核实的关键事实

- 产品代码边界 `cabc959`，Phase 15 报告/Phase 16 起点 `84f1435`。
- 当前发布判断 `CODE_GATES_CLOSED_DB_BROWSER_VALIDATION_REQUIRED`。
- 1–5 candidates，每候选 1–2 images；JPEG/PNG，HEIC/HEIF 条件转换；5 MB。
- Home-first；首次开始后 O1/O2；skip 清伪偏好；Need 位于候选页。
- 五个 Action Bucket 与同档排序顺序。
- Evidence 三维枚举、来源边界和 strength。
- Question 最多 3 条、threshold 3、无副作用 counterfactual。
- MerchantReply 主状态与确定性默认 parser。
- Aggregate Rejudge、V1→V2→Delta。
- Decision 内容快照与可变生命周期字段的边界。
- Selection bridge v3 和 12 条/90 天 preference evidence 边界。
- Analytics 13 client + 13 server，fail-open，不参与 Decision。
- AI Eval 30 total / 26 PASS / 0 FAIL / 4 BLOCKED。
- Frontend 61/61；Backend 228 PASS / 76 SKIP；Privacy 26/26，P0/P1=0。
- 当前 live Provider calls=0；真实 Provider 质量未确认。
- Participants=0。
- 买后代码存在，但完整浏览器体验只部分验证。
- Platform、deployed commit、provider/model、database host 均 `UNCONFIRMED`。

## 代码变更核验

- Phase 16 相对 `84f1435` 无产品代码、测试、migration、Docker 或 deployment 文件改动。
- 本轮新产物只允许位于 `docs/GUANCHA_CURRENT_SYSTEM_SPEC.md` 与 `artifacts/system-spec/*`。
- 用户原有运行说明删除/替换和未跟踪 `__pycache__` 必须继续排除。

## 剩余未决口径

主 SSOT 保留 10 个未决领域；其中 7 个是跨文档/部署层直接矛盾或未知。它们不阻止建立 SSOT，但阻止把系统写成已经完整发布验证。

## 最终裁决

- Product Truth：PASS
- Engineering Truth：PASS WITH EXPLICIT DB/BROWSER BOUNDARIES
- Implemented / Planned Separation：PASS
- Historical Contradictions：15 项已裁决
- Resume-safe Facts：PASS
- Fact Check：PASS

推荐最终 Verdict：

`CURRENT_SYSTEM_SSOT_READY_WITH_UNRESOLVED_FACTS`
