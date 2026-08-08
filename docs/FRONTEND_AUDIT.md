# 观茶前端审计

> 审计日期：2026-08-04  
> 审计对象：`guancha-o1-o2-prototype`  
> 结论状态：阶段 0 审计完成，**暂不进入阶段 1**  
> 本轮改动：仅新增审计文档，未修改 UI、业务代码或样式

## 1. 结论

当前项目是一个可直接打开的移动端纯前端演示原型。买前主链路和买后茶仓/日记链路可以运行，但所有分析、复判、证据、商品识别和口味证据仍是前端 Mock 或展示文案。

前端不适合直接在现有点击事件里追加 `fetch()` 开始联调。当前 `app.js` 同时承担状态、Mock 数据、渲染、业务判断、持久化、计时和设备能力；如果直接接后端，最容易出现候选串数据、重复任务、旧判断继续展示、商家回复假复判和买后证据误写。

推荐结论：**保留现有 UI 和渲染函数，阶段 1 先建立 API Client、合同适配器、持久化边界和显式状态机，再逐步替换 Mock。**

## 2. 审计依据与优先级

当前执行优先级如下：

1. 《观茶｜黑客松 P0 后端研发 PRD v1.0》（2026-08-04）：本轮研发执行基线；
2. 《观茶｜茶仓库与泡茶日记 PRD v0.3（比赛版最终范围）》：买后本地数据与交互基线；
3. 《观茶产品 PRD｜完整机制版 v0.3》：完整产品机制与长期方向；
4. 当前前端代码：实现事实，不自动获得产品决策权；
5. 旧后端、Obsidian 导出和历史评测：候选资产，不自动视为当前有效。

完整机制版写有“已有后端可复用”，后端研发 PRD 又要求“本轮后端基本从零，旧代码只能先审计”。本审计以后者为准。

## 3. 技术栈与运行方式

| 项目 | 当前事实 | 影响 |
| --- | --- | --- |
| 页面 | 单一 `index.html` | 无 URL 路由、无浏览器历史恢复 |
| 逻辑 | 原生 JavaScript，单文件 `app.js`，607 行 | 无模块边界、无静态类型 |
| 样式 | 单文件 `styles.css` | UI 已冻结，本轮不修改 |
| 状态 | 全局可变对象 `state` | 视图、领域和持久化状态混合 |
| 持久化 | `localStorage['guancha-prototype-v2']` | 无 Schema 版本和可靠迁移 |
| API | 无 `fetch`、XHR 或 API Client | 当前完全未联调后端 |
| 构建 | 无项目内 `package.json`、无构建命令 | 当前只能静态打开或静态托管 |
| 测试 | 无项目内自动化测试 | 只能做语法检查和浏览器流程检查 |

当前 README 的运行方式是直接用 Chrome 打开 `index.html`。阶段 1 若加入环境变量或 ES Module，必须先定义新的启动方式，但不能借机重写 UI。

## 4. 页面与路由事实

项目没有 URL 路由。`state.screen` 决定渲染函数，`setScreen()` 直接替换 `#app.innerHTML`。

| screen | 页面/状态 | 上游 | 主要下游 |
| --- | --- | --- | --- |
| `home` | 选茶首页 | 启动、返回 | `candidates`、`o1` |
| `o1` / `o2` | 初始口味偏好 | 首页/设置 | 首页 |
| `candidates` | 本次需求与候选 | 首页 | `analysis` |
| `analysis` | 固定 2.2 秒等待 | 候选页 | `result` |
| `result` | Mock 初判 | 等待页 | 商家追问 |
| `rejudge` | Mock 复判 | 商家回复 | `ownership` |
| `ownership` | 已购/已有/只保存 | 复判 | 茶仓或首页 |
| `warehouse` | 茶仓列表 | 一级导航 | 详情、手动入库、准备泡茶 |
| `warehouse-detail` | 茶仓详情 | 茶仓 | 准备泡茶 |
| `warehouse-add` | 手动入库 | 茶仓 | 茶仓 |
| `journal` | 月历 | 一级导航 | `journal-day` |
| `journal-day` | 某日记录 | 月历 | 选茶、详情 |
| `choose-tea` | 从茶仓选茶 | 当天记录 | `prepare` |
| `prepare` | 冲泡准备 | 茶仓/选茶 | `timer` |
| `timer` | 第 N 泡计时 | 准备/继续下一泡 | `infusion-done` |
| `infusion-done` | 一泡完成 | 计时 | 下一泡或反馈 |
| `feedback` / `advanced` | 基础/进阶反馈 | 一泡完成 | 保存结果 |
| `brew-result` | 下次建议与影响 | 保存 | 当天记录/详情 |
| `record-detail` | 单次记录详情 | 当天记录 | 删除/返回 |
| `settings` | 偏好与本地数据入口 | 一级导航 | 偏好或清除数据 |

一级导航已符合补充 PRD：`选茶｜泡茶日记｜茶仓库｜设置`。

## 5. 当前状态与 Mock 数据

### 5.1 全局状态

`defaultState`（`app.js:24`）当前包含：

- 视图状态：`screen`、`overlay`；
- 初始偏好：`o1`、`o2`；
- 本次需求：`need`；
- 候选：`candidates`、`activeCandidate`；
- 商家回复：`reply`；
- 选茶记录：`history`；
- 拥有状态：`ownershipChoice`；
- 茶仓：`warehouse`、`selectedTeaId`；
- 泡茶草稿：`brew`；
- 日记：`journalRecords`、动态添加的 `journalDate`、`activeRecordId`。

这些字段没有独立 Schema，也没有把 UI 临时状态、服务端资源 ID、本地业务数据和演示数据分开。

### 5.2 Mock 位置

| Mock | 位置 | 当前行为 |
| --- | --- | --- |
| 初始茶仓和日记 | `app.js:24-45` | 启动即注入演示数据 |
| 商品识别结果 | `addCandidate()`，`app.js:413-426` | 根据加入顺序分配固定茶名与字段 |
| 初判 | `resultData()`，`app.js:237-258` | 只按候选字母切换固定文本 |
| 商家问题 | `merchantQuestions()`，`app.js:405-411` | 永远返回固定 3 问 |
| 复判 | `resultData(candidate, true)` | 不解析回复，始终补充固定 3 条事实 |
| 分析任务 | `app.js:505` | 固定等待 2200ms，无真实任务 |
| 下次冲泡建议 | `saveBrewRecord()`，`app.js:597-601` | 只根据浓淡做简单文本判断 |
| 近期饮用证据 | `app.js:553` | 仅 Toast 固定文案，无证据对象 |

## 6. localStorage 审计

当前键：`guancha-prototype-v2`（`app.js:7`）。除 `overlay`、`sourceFor` 外，几乎整个 `state` 都被序列化。

主要风险：

1. `loadState()` 只做顶层浅合并；嵌套字段缺失、类型变化或旧枚举不会被可靠迁移；
2. 没有 `schemaVersion`、迁移函数、写入失败处理或损坏数据诊断；
3. 服务端会话、任务和决策版本未来若直接塞入同一对象，会和本地茶仓/日记混在一起；
4. Mock 数据与用户真实数据没有来源标识，清除时也无法区分；
5. 删除日记目前没有真实 `PreferenceEvidence` 可同步删除。

阶段 1 建议至少拆成三个持久化域：

| 域 | 建议所有权 | 内容 |
| --- | --- | --- |
| `uiSession` | 内存为主 | 当前 screen、overlay、选中项、轮询控制器 |
| `selectionBridge` | localStorage + 服务端 ID | anonymousClientId、sessionId、candidateId、imageId、currentDecisionVersionId、jobId |
| `localPostPurchase` | localStorage | TeaStockItem、BrewSession、PreferenceEvidence |

每个域必须有独立 `schemaVersion` 和迁移入口。

## 7. P0 问题清单

### P0-FE-01：不存在真实 API 接入点

- 证据：`app.js` 无任何 `fetch()`；分析由 `setTimeout` 完成；
- 后果：当前所有“已读取、已分析、已复判、已形成证据”都是演示状态；
- 阶段 1 边界：先增加服务层和适配器，视图不得直接处理原始后端 JSON。

### P0-FE-02：图片数量和格式违反冻结合同

- `index.html:14-15` 使用 `accept="image/*"`，会允许后端 P0 不接受的格式；
- `addCandidate()` 在 `app.js:423` 使用 `Math.min(4, fileCount)`；
- 浏览器实测一次选 3 张图后显示“已读取 3 张商品页”；
- 当前没有候选卡补第 2 张图的独立入口，也没有图片 ID、删除单图、重试单图能力；
- 当前上传只保存数量，文件和相机拍摄的 Blob 随即丢弃。

### P0-FE-03：没有证据版本和 stale 状态

新增/删除候选或图片后，当前代码不会保存 `ExtractionVersion`、`DecisionVersion`，也不会使旧问题和复判失效。P0 要求证据变化后旧判断标记 `stale`，否则容易展示错误结论。

### P0-FE-04：商家回复不会影响复判计算

`submit-rejudge` 只检查回复非空并切换页面；`resultData(..., true)` 永远产生相同补充事实。答非所问、部分回答、冲突和不同回复目前都会得到同一结果。

### P0-FE-05：行动分档不完整且不是数据状态

当前只存在展示文案“本轮推荐”“可作为备选”“当前优先关注・先问再买”，没有五类后端行动状态。`insufficient-information`、`sample-first`、`not-recommended-now` 不能被可靠表达和恢复。

### P0-FE-06：买后数据不符合目标合同

- `TeaStockItem` 缺少稳定的 `sourceDecisionId`、来源候选 ID 和购买快照结构；
- 防重复只按茶名比较（`app.js:514-519`），会误合并同名不同批次，也会漏掉改名重复；
- `BrewSession` 没有 `suggestedPlan` 与 `actualPlan` 双快照，也没有完整状态枚举；
- 继续下一泡会直接修改 `brew.plan.seconds`（`app.js:537`），最终记录可能丢失首泡建议；
- 没有真实 `BrewImpact` 和 `PreferenceEvidence` 对象；
- `issueSource` 只存中文展示值，尚未映射后端枚举。

### P0-FE-07：缺少真实加载、错误、重试和恢复状态

候选抽取、比较、复判和反馈分析均没有 `queued/processing/completed/failed/stale`。页面也没有按候选隔离的失败状态，无法做到“保留成功候选，仅重试失败候选”。

### P0-FE-08：部署依赖本机绝对路径

`DESKTOP_WORDMARK_DIR`（`app.js:22`）指向 `file:///C:/Users/QQ/Desktop/...`。部署到 Vercel 或其他电脑后无法可靠加载，应改为项目内资产引用，但本轮不修改 UI。

### P0-FE-09：计时模型会漂移且恢复语义不清

计时只靠每秒递减，浏览器进入后台时会漂移；没有 `startedAt`/`pausedAt`；刷新后会从保存的剩余秒数继续，而不是按 PRD 明确放弃或可靠恢复。退出提示仅覆盖页面内返回，不覆盖刷新/关闭。

## 8. P1/P2 工程风险

| 等级 | 问题 | 证据/影响 |
| --- | --- | --- |
| P1 | 潜在存储型 XSS | `detailSection()` 接收拼接后的用户参数和印象并作为 HTML 注入（`app.js:387-390`）；未来后端商品名/回复也可能进入未转义模板 |
| P1 | 无效 ID 静默回退 | `getTea()` 找不到 ID 时返回茶仓第一项（`app.js:277`），可能把日记关联到错误茶叶 |
| P1 | 硬编码日期 | `TODAY = '2026-08-04'`（`app.js:333`），月份、天数和首日偏移也固定 |
| P1 | 状态变更不可审计 | 大量事件分支直接修改全局对象，无法生成可重复的状态迁移测试 |
| P1 | 无请求取消/防重复 | 快速重复点击未来可能创建多个分析或复判任务 |
| P2 | 无 URL 路由 | 刷新只能依赖 localStorage 的 `screen`，链接不可分享，浏览器返回键无流程语义 |
| P2 | 可访问性不完整 | 动态弹层没有统一焦点管理，部分模拟按钮依赖 `role=button` 但无键盘事件 |

## 9. 行动状态映射

前端不应继续使用展示文案作为业务枚举。建议建立唯一适配器：

| 后端行动状态 | 中文展示 | 当前可复用文案 | 审计结论 |
| --- | --- | --- | --- |
| `currently-selectable` | 当前可选 | “本轮推荐” | 可映射，但需统一文案 |
| `ask-before-buying` | 先问清再买 | “当前优先关注・先问再买” | 可映射 |
| `sample-first` | 建议先试小样 | 无稳定状态 | 必须补数据映射，不新增页面 |
| `not-recommended-now` | 暂不建议 | 仅出现装饰性按钮文案 | 必须补数据映射 |
| `insufficient-information` | 信息不足，无法判断 | 无 | 必须补数据映射与失败/缺证据区分 |

映射函数只能负责枚举到文案/样式，不得在前端计算分档。

## 10. 推荐的阶段 1 边界（不改 UI）

```text
现有 render* 与样式
        ↑ 只接收 ViewModel
view-model adapters
        ↑
selection store / local post-purchase store
        ↑
API client + generated contracts
        ↑
FastAPI OpenAPI
```

最小模块职责：

| 模块 | 只负责 | 不负责 |
| --- | --- | --- |
| API Client | HTTP、超时、错误归一化、幂等键 | 业务分档、UI 文案 |
| Contract | OpenAPI 生成类型和枚举 | 手写第二套类型 |
| Adapter | 后端 DTO → 当前页面 ViewModel | 修改后端事实 |
| Selection Store | 会话、候选、图片、任务、版本 | 茶仓与日记规则 |
| Local Post-purchase Store | 茶仓、日记、低置信度证据 | 云端跨设备同步 |
| Poller | 轮询、取消、退避、页面后台降频 | 直接渲染页面 |

## 11. 验证记录

已完成：

- `node --check app.js`：通过；
- 两个资产处理脚本语法检查：通过；
- 本机 Chrome、360×800 视口只读主链路：选茶首页 → 上传 → 分析 → 问商家 → 复判 → 加入茶仓 → 泡茶日记，可走通；
- 该链路无浏览器控制台错误；
- 实测复现每候选可显示 3 张图片的合同违规；
- 未安装任何依赖，未修改 UI。

未完成：

- 没有真实后端，因此未做 API、超时、并发、断网或服务端错误回归；
- 没有项目内测试框架，因此未形成可重复执行的前端自动化套件；
- 未检查部署环境中的实际 Vercel 构建，因为当前无构建配置。

## 12. 阶段 1 开始前的审查门槛

以下内容需审查确认后再开发：

1. 是否接受“保留 UI、先建立四层边界”的方案；
2. 是否以后端研发 PRD 的 `/api/v1` 为唯一目标合同，旧 `/compare-sessions` 只作迁移参考；
3. localStorage 是否按三个域拆分并引入 `schemaVersion`；
4. 五类行动状态的中文显示映射；
5. 候选与图片的 ID、版本和 stale 规则；
6. 买后数据继续本地保存，只向 `/brew-feedback/analyze` 提交最小必要结构；
7. 本机绝对资产路径在阶段 1 作为必要部署修复处理，但不改变视觉。

