# 阶段 2：单图证据抽取实施计划

## 目标与边界

阶段 2 只完成一个匿名客户端在一次选茶会话中，为一个候选茶上传一张真实 JPEG/PNG 商品截图，并获得可追溯的结构化证据摘要。

本阶段不实现：第二张图联合分析、第二候选、多候选并行、候选排名、行动分档、下一最佳问题、商家回复复判、买后 AI 分析。

前端保留未来双图入口的视觉位置，但阶段 2 将第二候选和第二图片入口置为不可用状态；不得删除该入口，也不得把它接到后端。

## 实施顺序与提交纪律

1. 包结构迁移：将后端迁移到 `backend/src/guancha_api/`，只保留一个可启动 FastAPI 入口；先让既有阶段 1 测试与 CI 通过。
2. 数据库与 Repository：新增最小迁移、Repository 合同与 GitHub Actions PostgreSQL 服务测试。
3. 图片管线：验证、解码、去 EXIF、尺寸限制、重新编码、临时私有存储和 finally 删除。
4. Job 与 FakeProvider：持久化 Job、重试、结构修复、不可变抽取版本和证据写入。
5. 前端联调：单图上传、轮询、刷新恢复和真实证据摘要展示。
6. 真实 Supabase 人工集成烟测：不在 CI 运行。
7. 经本人明确授权后的 OpenAI 单次人工烟测：不在 CI 运行。

每个子阶段必须先运行对应测试、提交并推送到 `codex/phase-2-single-image-extraction`。不得直接修改 `main`。公共 OpenAPI、Pydantic Schema、枚举和迁移编号仅由主 Agent 修改。

## 后端包布局

```text
backend/
  src/guancha_api/
    main.py                    # 唯一 ASGI 入口
    api/                       # 路由、请求/响应与 HTTP 错误适配
    application/               # 上传、任务创建、轮询恢复用例
    domain/                    # Schema、枚举、状态机、Ports
    infrastructure/
      repositories/            # PostgreSQL/Supabase 实现
      storage/                 # 临时私有对象存储
      providers/               # FakeProvider 与 OpenAI Vision Provider
      image_pipeline.py
  tests/
    fixtures/
    contract/
    integration/
```

项目安装使用 `backend/pyproject.toml` 的 `src` 包布局。迁移期间删除旧 `backend.app` 可启动入口，而不是同时维护两套入口；所有旧测试、CI 和 README 引用同步改为 `guancha_api`。

## 数据模型与迁移

迁移编号由主 Agent 分配。表名固定如下：

| 表 | 最小职责 |
| --- | --- |
| `anonymous_clients` | `X-Client-Id` 对应的匿名客户端与创建时间 |
| `selection_sessions` | 属于匿名客户端的单次选茶会话 |
| `candidates` | 会话内的候选；阶段 2 强制每会话仅一条 |
| `candidate_images` | 图片哈希、MIME、像素尺寸、处理状态；不长期保存可访问对象路径 |
| `analysis_jobs` | 持久化的抽取任务、幂等键、状态、尝试次数和错误码 |
| `extraction_versions` | 成功抽取的不可变版本与 Schema 版本 |
| `evidence_items` | 结构化证据、来源、状态和版本归属 |
| `ai_call_logs` | Provider、模型标识、关联 ID、时长、token/错误元数据；不保存 API Key 或原始图片 |

`analysis_jobs.status` 的公开枚举固定为 `queued`、`processing`、`completed`、`failed`、`stale`。不得使用 `succeeded`。

每个 `evidence_items` 至少包含：`information_status`、`source_type`、`verification_status`、`source_image_id`、`source_location`。商品页可直接读到的描述统一作为 `source_type=product-claim` 且 `verification_status=unverified`，不得因模型抽取而变成已核验事实。

## 安全图片管线

1. 仅接受单张 JPEG/PNG，并同时验证声明 MIME、文件签名、可解码性、文件大小、像素数和最长边。
2. 服务端解码后移除 EXIF，限制尺寸并重新编码，计算 SHA-256。
3. 预处理后的文件只写入临时私有存储，绝不使用公开 URL。
4. 无论任务完成、失败或超时，均在 `finally` 删除对象；数据库长期只保存哈希、格式、尺寸、状态和证据。
5. 同一候选的第二图片请求以及同一会话的第二候选请求均返回明确的合同错误。

## API 合同

所有匿名请求必须携带 `X-Client-Id`；所有创建型请求必须携带 `Idempotency-Key`。服务端按客户端、会话、候选、图片和 Job 逐层校验资源归属，不允许跨客户端读取或重试。

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| `POST` | `/api/v1/selection-sessions` | 创建会话 |
| `POST` | `/api/v1/selection-sessions/{id}/candidates` | 创建唯一候选 |
| `POST` | `/api/v1/candidates/{id}/images` | 上传唯一图片；原子地创建 `candidate_image` 与 `analysis_job`，同时返回二者 |
| `GET` | `/api/v1/candidate-images/{id}` | 获取图片处理元数据，不返回长期可访问对象路径 |
| `POST` | `/api/v1/candidates/{id}/extraction-jobs` | 仅当最新 Job 为失败状态时创建重试 Job |
| `GET` | `/api/v1/jobs/{id}` | 获取 Job 公开状态与失败码 |
| `GET` | `/api/v1/extraction-versions/{id}` | 获取不可变版本和证据摘要 |

上传接口不再要求前端额外调用创建 Job。`POST /extraction-jobs` 不是普通重新分析入口，只用于失败重试。

## Provider 与失败策略

`VisionProvider` 通过 Port 注入。测试与 CI 默认使用带固定 fixture 的 `FakeProvider`，禁止访问付费 API。

- Provider 网络失败自动重试一次；仍失败则 Job 为 `failed`。
- 初次结构化输出未通过 Pydantic Schema 时，执行一次结构修复调用；仍不合格则 Job 为 `failed`。
- 不得静默补全字段、不得返回部分伪结果、不得把失败伪装成完成。
- 真实 OpenAI Provider 只通过未提交环境变量配置；仅在本人明确授权的本地人工烟测中调用一次。

## 前端范围

前端只允许一个候选和一张图片。上传后保存会话、候选、图片与 Job 标识；刷新后恢复并继续轮询。界面仅展示：图片处理状态、Job 状态、失败原因、ExtractionVersion 的 EvidenceItem 摘要。

不得展示推荐、排名、行动分档、追问、商家回复复判或买后分析。第二图片和第二候选入口仅显示禁用状态与范围提示。

## 测试矩阵

| 层级 | 最低覆盖 |
| --- | --- |
| 包迁移 | 唯一入口导入、既有阶段 1 `/health` 与 OpenAPI 合同、CI 路径 |
| 图片管线 | MIME/签名、大小、像素、EXIF 清理、重新编码、finally 删除 |
| Repository | PostgreSQL 真实服务下的客户端归属、单候选/单图限制、幂等、Job 状态和版本不可变性 |
| API 合同 | 必填头、资源归属、上传自动建 Job、失败重试限制、公开状态枚举 |
| Provider | FakeProvider 成功、网络重试一次、Schema 修复一次、最终失败不返回部分结果 |
| 前端 | 单图上传、轮询、刷新恢复、状态/证据渲染、禁用第二候选与第二图片 |
| CI | GitHub Actions PostgreSQL service + FakeProvider；不调用真实 Supabase/OpenAI |
| 人工烟测 | 真实 Supabase，再经本人授权调用一次真实 OpenAI；均不写入 CI |

## 验收标准

一次匿名单图流程能够在刷新后恢复，最终仅生成可追溯的 `ExtractionVersion` 与 `EvidenceItem`；临时图片对象已删除；失败可观察、可重试且不产生伪摘要；CI 在不使用真实收费 API 的情况下通过。
