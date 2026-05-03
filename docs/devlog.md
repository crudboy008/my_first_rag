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

