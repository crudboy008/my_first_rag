# devlog

## 2026-04-30 — 项目初始化，upload 和 search 功能跑通

- 实现 `POST /api/upload`：PDF 上传 → pdfplumber 提取文本 → RecursiveCharacterTextSplitter 分块 → DashScope text-embedding-v2 向量化 → 写入 Milvus
- 实现 `POST /api/search`：query 向量化 → Milvus COSINE 相似度检索 → 返回 top_k 分块
- 配置通过 `.env` + pydantic Settings 统一管理
- 添加 CLAUDE.md 项目说明文档，写入 devlog 自动追加规则

### [15:45] 完成上传接口流程图 v0.1
- 上下文:上午消化代码后的可视化输出
- 动作:用 Excalidraw 画了 upload 接口的执行流程
- 结果:9 步流程清晰,但**只是流程图,不是架构图**
- 不足:缺数据形态标注、缺外部系统抽象、缺检索接口、缺模块边界
- 下一步:本周末画 v0.2 架构图(参考 docs/architecture-todo.md 的检查清单)
### [20:30] 环境异常导致下午进度延误
- 上下文:朋友找事打断一次 + 教室断电锁门被赶
- 动作:迁移到朋友宿舍继续工作
- 结果:有效学习时间损失约 2 小时,
       原计划手搓上传接口需要压缩
- 下一步:21:00 起按精简版执行,目标降到"今晚有一个 commit"

## 2026-05-01 — 修复磁盘文件名与 doc_id 不一致问题

- `save_upload_file` 增加 `doc_id` 参数，文件保存路径改为 `{doc_id}_{filename}`
- `main.py` 调用处把已生成的 `doc_id` 传入，不再各自 `uuid4()`
- 为什么:之前磁盘 PDF 文件名用的是新 UUID,跟 Milvus 里 doc_id 完全无关,导致检索结果反查不到原始文件、孤儿 PDF 也对不上账。业务实体 ID 必须贯穿 HTTP 请求 → 文件系统 → 数据库全程
- 顺手清理 `pdf_loader.py` 里 4.30 已答的 TODO 注释

## 2026-05-03 — 测试集补 5 条到 25 + 接 BGE-Reranker 跑 Eval 对比

### [16:44] 下载BGE模型失败，reranker流程无法执行
- 问claude desktop拿了LLM兜底策略，走LLM不走BGE了，cursor生成代码我去review

## 2026-05-07 — V0.3 Phase 1 APIRouter 模块化重构

### 重构内容
- 拆分 `app/main.py` (148 行 → 12 行)：原文件承担 FastAPI 实例 + 全局单例 + 3 个路由 + 4 个工厂函数，全部混在一起
- 新建 `app/dependencies.py`：迁移 `get_embedder` / `get_store` / `get_reranker` + 全局单例占位 + `validate_vectors`
- 新建 `app/routers/{health,upload,search}.py`：每个路由独立成模块
- `app/main.py` 重写为 FastAPI 实例 + `app.include_router` 装配（约 12 行）

### 顺手做的事
- **修复 `search.py` line 89 typo**：`get_store().sea1.rch(...)` → `.search(...)`。修前 `use_reranker=True` 路径会直接 `AttributeError`，永远不可达——意味着 5/3 BGE 实测的 use_reranker=True 路径其实跑不到此 bug 行（5/3 的 eval_with_bge.py 走的是另一条路径）；但 V0.3 #1 LLM 答案生成会调 search 接口，触发到这条路径
- 重命名 `_validate_vectors` → `validate_vectors`：从下划线私有改为公开导出（PEP 8），方便跨模块 import
- TODO 注释原样保留（line 59 / line 87 各一处用户标记的"为什么"问题）

### 行为验证（Gate 2 通过）
- 静态 import：通过，三业务端点全注册（`/health` / `/api/upload` / `/api/search`）
- GET /health：200，4ms
- eval baseline（25 条 testset，use_reranker=False）：**Hit@5=0.720 / MRR=0.461，与 5/3 实测完全一致**——证明重构未破坏行为
- 报告：`eval/reports/eval_20260507_163732.md`

### 环境踩坑（与代码无关，但耗时）
- toolref-milvus 启动时 19530 不对外暴露的真因：**Windows excluded port range 包含 9000/9091/9001**，导致 docker port publish 原子性失败（19530 不在排除内但被连带）
- 修复路径：管理员 PowerShell 跑 `net stop winnat && net start winnat` 重置区间 → `docker start toolref-{etcd,minio,milvus}`
- 另一个坑：uvicorn worker 第一次 POST 触发 pymilvus 卡死后不会自愈，需要重启 uvicorn 才能恢复
- 第三个坑：当时 reload 模式下 worker 行为不稳，重启时改用非 reload 单进程更稳

### 下一步（Phase 2）
- 启动 V0.3 Agent Team（A: LLM 答案生成 / B: 文档删除 / C: 上传增强 #4 #5）
- V0.3 #3 SHA256 去重已砍（Milvus collection `enable_dynamic_field=False` 不允许加字段）

