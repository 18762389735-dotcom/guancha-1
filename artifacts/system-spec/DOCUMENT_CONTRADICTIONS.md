# 观茶文档矛盾审计

审计日期：2026-08-13

## 裁决规则

冲突按以下优先级裁决：当前代码 → Phase 15 报告 → Phase 14 → Phase 13 → 最新运行说明 → 核心经验证体验文档 → 较晚 PRD → 完整机制 PRD → 后端 PRD → 买后 PRD → 更早历史文档。旧文档仍可说明演进，但不再拥有当前事实权。

## 已裁决的主要矛盾

| # | 主题 | 历史说法 | 当前裁决 | 旧说法状态 | 当前事实状态 |
|---:|---|---|---|---|---|
| 1 | Provider | OpenAI 是唯一/当前 Provider | 代码支持 fake、OpenAI、MiMo 等；实际 runtime 未确认 | `SUPERSEDED` | `UNCONFIRMED` |
| 2 | 部署平台 | Vercel、Render 等不同平台说法 | 只能确认 Dockerfile/Procfile 兼容形态，当前平台未知 | `HISTORICAL_ONLY` | `UNCONFIRMED` |
| 3 | 端口 | 8011 等是固定当前端口 | 本地默认 8000；容器读取 PORT、缺省 8080；线上未知 | `HISTORICAL_ONLY` | 本地/容器 `IMPLEMENTED_VERIFIED`，线上 `UNCONFIRMED` |
| 4 | 数据库 | Supabase 就是当前部署数据库 | 只能确认 PostgreSQL repository；托管商未知 | `SUPERSEDED` | repository `IMPLEMENTED_PARTIALLY_VERIFIED` |
| 5 | 候选/图片数量 | 单候选、单图片或最多 4 图 | 当前为 1–5 个候选、每个 1–2 图 | `SUPERSEDED` | `IMPLEMENTED_VERIFIED` |
| 6 | 复判方式 | 每条回复立即独立复判 | 当前是会话范围聚合回复后统一复判 | `SUPERSEDED` | `IMPLEMENTED_PARTIALLY_VERIFIED` |
| 7 | 结果后动作 | 直接选茶/直接入仓 | 有问题先追问复判；无可行动问题可选择；入仓另确认 | `SUPERSEDED` | `IMPLEMENTED_PARTIALLY_VERIFIED` |
| 8 | 核心能力 | OCR/识别茶款 | 当前核心是证据、感官翻译、候选比较和可修正判断 | `SUPERSEDED` | `IMPLEMENTED_PARTIALLY_VERIFIED` |
| 9 | Onboarding | 打开即自动进入 O1 | 当前 Home-first；首次开始后才进入 O1/O2 | `SUPERSEDED` | `IMPLEMENTED_VERIFIED`（路由测试） |
| 10 | 偏好优先级 | 长期偏好主导推荐 | Selection Need 优先，偏好仅有边界参照 | `SUPERSEDED` | `IMPLEMENTED_VERIFIED` |
| 11 | Answer 信息顺序 | 旧九段顺序 | 当前以 Need/Personal Fit/Sensory 为先，证据边界贯穿 | `SUPERSEDED` | `IMPLEMENTED_VERIFIED`（代码结构） |
| 12 | 茶仓/日记 | 完全不存在；或已经完整在线 | 基础本地功能存在但仅部分验证；云端完整能力未实现 | 两种说法均 `SUPERSEDED` | `IMPLEMENTED_PARTIALLY_VERIFIED` |
| 13 | 推荐与选择 | 用户选择被写成系统推荐 | 当前分别保存系统首选与用户选择 | `SUPERSEDED` | `IMPLEMENTED_VERIFIED` |
| 14 | Analytics 隐私/重放 | Phase 14 的 P0/P1 仍是当前缺陷 | Phase 15 已关代码级 P0/P1；DB exactly-once 仍 BLOCKED | `SUPERSEDED` | `IMPLEMENTED_PARTIALLY_VERIFIED` |
| 15 | 发布结论 | READY_FOR_DEADLINE_DEMO / 可部署 | 当前仅 `CODE_GATES_CLOSED_DB_BROWSER_VALIDATION_REQUIRED` | `HISTORICAL_ONLY` | `IMPLEMENTED_VERIFIED`（报告事实） |

## 仍未解决、不得自动推断的事实

1. 当前实际托管平台。
2. 当前已部署 commit。
3. 当前线上 extraction provider/model。
4. 当前数据库托管商。
5. 当前线上 runtime port。
6. 茶仓/泡茶日记在真实浏览器中的完整状态。
7. PostgreSQL same-key exactly-once 与 Decision→Question→Reply→Rejudge→Delta 全链。

## 文档使用建议

- `docs/GUANCHA_CURRENT_SYSTEM_SPEC.md`：Phase 16 之后的当前事实入口。
- `artifacts/release-gate/RELEASE_GATE_REPORT.md`：Phase 15 验证边界。
- Phase 13–15 的审计工件：只解释当时发现、修复与证据，不作为当前产品总览。
- 最新运行说明：用于操作入口，但其未提交替换文件属于用户工作区内容，本轮不修改、不纳入提交。
- 旧 PRD：继续作为设计意图和演进档案，不能单独证明当前实现。

## 特别缺失

任务引用的 `GUANCHA_CORE_EXPERIENCE_V3.md` 在本次定向查找范围内未找到。其内容状态为 `UNCONFIRMED`；若未来找到，必须与当前代码逐项对照，不能自动提升为当前事实。
