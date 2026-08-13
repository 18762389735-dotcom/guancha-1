# Phase 16 Current System SSOT Consolidation Report

## Executive Summary

Phase 16 仅整合当前事实，没有修改产品代码。新的主事实源为 `docs/GUANCHA_CURRENT_SYSTEM_SPEC.md`。它把当前实现、部分验证、设计、未来、历史和未知拆开，并保留 Phase 15 的数据库/浏览器发布边界。

最终事实核验 P0=0、P1=0。由于部署运行事实、PostgreSQL 全链、浏览器 E2E、live Provider 和真实用户价值仍未确认，本轮 verdict 为：

`CURRENT_SYSTEM_SSOT_READY_WITH_UNRESOLVED_FACTS`

## Baseline

- Phase：Current System SSOT Consolidation
- Competition baseline/freeze：`05b0292`
- Observable Beta boundary：`1d9d606`
- Phase 15 product code：`cabc959`
- Phase 15 report / Phase 16 starting head：`84f1435`
- Phase 16 branch：`codex/system-spec-consolidation`
- Historical origin main：`f1cc4e8`
- Deployed commit：`UNCONFIRMED`

## Sources Read

本轮按任务优先级定向读取，而非全量历史扫描：

- 当前前端、FastAPI application、domain decision/question、repository、provider、analytics、persistence 与 tests。
- `artifacts/release-gate/RELEASE_GATE_REPORT.md`
- `artifacts/release-gate/PRIVACY_RED_TEAM.md`
- `artifacts/observable-beta/MORNING_REPORT_2.md`
- `artifacts/overnight/MORNING_REPORT.md`
- `docs/CURRENT_STATE.md`
- 当前用户替换但未提交的 `docs/观茶_项目运行说明_.md`（只读，不纳入本次提交）
- `docs/CLIENT_PERSISTENCE_CONTRACT.md`
- `docs/PRODUCT_ANALYTICS_SPEC.md`
- `docs/AI_EVAL_MATRIX.md`
- `docs/AI_FAILURE_TAXONOMY.md`
- `docs/BACKEND_GAP_ANALYSIS.md`
- `docs/PHASE_2_SINGLE_IMAGE_PLAN.md`
- `docs/MVP_RUNBOOK.md`
- `docs/REAL_PROVIDER_SMOKE.md`
- 完整机制、比赛汇总、买后与早期黑客松 PRD。

任务指定的 `GUANCHA_CORE_EXPERIENCE_V3.md` 在定向查找中未找到，标记为 `UNCONFIRMED`，未凭历史记忆补写。

## Current Facts Confirmed

- 产品北极星是专业茶语 → 感官含义 → 可解释、可追问、可修正的候选选择。
- 当前主要范围为铁观音比赛版，1–5 候选、每候选 1–2 图。
- Selection Need 优先；Evidence 来源/验证边界强制保留。
- Decision 为五档规则行动建议，同档排序不等于 AI 总分。
- Question 使用 bounded counterfactual，MerchantReply 逐题绑定，Aggregate Rejudge 生成 V2/Delta。
- Client persistence schema v3 不保存 Need、商家原文、图片或完整证据/Answer/Delta 树。
- Analytics 共 26 个闭集事件，fail-open，不影响 Decision。
- AI Eval 30=26 PASS/0 FAIL/4 BLOCKED；participants=0。

## Historical Claims Superseded

共裁决 15 个主题，包括：OpenAI 唯一 Provider、Vercel/Render 当前平台、固定临时端口、Supabase 当前数据库、单候选/单图或四图、逐回复即时复判、直接入仓、OCR 定位、自动 O1、长期偏好优先、旧 Answer 顺序、茶仓不存在/完整上线、推荐与用户选择混同、Phase 14 telemetry 缺陷仍开放、READY_FOR_DEADLINE_DEMO 等于当前可发布。

旧 PRD 和审计没有被批量改写；它们保留为项目演进档案。对于 current-state 问题，本 SSOT 覆盖它们。

## Implementation / Verification Boundary

| Area | Current evidence | Boundary |
|---|---|---|
| Frontend | 61/61 PASS | Browser E2E 未完成 |
| Backend | 228 PASS | 76 DB tests skipped |
| AI Eval | 26 PASS / 0 FAIL | 4 DB cases BLOCKED；非真实准确率 |
| Privacy | 26/26，P0/P1=0 | IndexedDB TTL 为 P2 |
| PostgreSQL chain | 代码/Stub/部分合同 | 隔离 DB 全链 BLOCKED |
| Browser | 宿主服务曾可返回 HTTP 200 | 不等于 Browser E2E |
| Provider | adapter/fixture 存在 | 当前 commit live calls=0 |
| Analytics | 事件合同/脚本测试通过 | 不代表真实用户数据 |
| User validation | 计划与工具存在 | participants=0 |

## Major Contradictions Resolved

15 个历史主题已按“旧说法状态 / 当前事实状态”分栏裁决。最重要的收束是：

- 当前架构不是线性“大模型推荐”，而是证据与决策两条相交管线。
- 当前系统支持多个 Provider adapter，但实际运行 Provider 未确认。
- 当前持久化是 PostgreSQL 合同，不等同于 Supabase 托管事实。
- 当前买后能力存在基础本地实现，但不是完整云端长期学习。
- Phase 15 关闭代码门，不代表数据库和浏览器发布门已通过。

## Unresolved Questions

主 SSOT 保留 10 个未决领域：部署身份、PostgreSQL 全链、浏览器主链、live extraction、买后浏览器行为、IndexedDB TTL、analytics retention、缺失核心体验 V3、历史 UI P2、用户/商业假设。

其中 7 个属于直接跨文档/部署未知：当前平台、deployed commit、provider/model、数据库托管商、runtime port、买后浏览器 E2E、PostgreSQL exactly-once/full chain。

## SSOT File

`docs/GUANCHA_CURRENT_SYSTEM_SPEC.md`

后续 Codex 任务应先读取该文件；若历史文档冲突，不得静默选用历史版本。

## Files Changed

只包含：

- `docs/GUANCHA_CURRENT_SYSTEM_SPEC.md`
- `artifacts/system-spec/PRODUCT_TRUTH_AUDIT.md`
- `artifacts/system-spec/ENGINEERING_TRUTH_AUDIT.md`
- `artifacts/system-spec/DOCUMENT_CONTRADICTIONS.md`
- `artifacts/system-spec/FINAL_FACT_CHECK.md`
- `artifacts/system-spec/CONSOLIDATION_REPORT.md`

产品代码、测试、Docker、Provider、Prompt、Decision、Question、Rejudge、analytics implementation、migration、database 和 deployment 均未修改。

## Git Commit

- Branch：`codex/system-spec-consolidation`
- Commit message：`docs: establish current guancha system source of truth`
- Commit hash：见包含本报告的 Git commit；为避免自引用，不在提交前写入猜测值。
- Push 不等于 merge 或 deploy。

## Final Verdict

- Product Truth：PASS
- Engineering Truth：PASS
- Implemented / Planned Separation：PASS
- Historical Contradictions：15 resolved topics
- Unresolved Current Questions：10 SSOT domains（其中 7 cross-document/deployment）
- Resume-safe Facts：PASS
- Fact Check：PASS
- Code Changed：NO
- Tests Modified：NO
- Deployment Modified：NO
- Database Modified：NO
- Provider Called：NO

`CURRENT_SYSTEM_SSOT_READY_WITH_UNRESOLVED_FACTS`
