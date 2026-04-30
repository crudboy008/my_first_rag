# devlog

## 2026-04-30 — 项目初始化，upload 和 search 功能跑通

- 实现 `POST /api/upload`：PDF 上传 → pdfplumber 提取文本 → RecursiveCharacterTextSplitter 分块 → DashScope text-embedding-v2 向量化 → 写入 Milvus
- 实现 `POST /api/search`：query 向量化 → Milvus COSINE 相似度检索 → 返回 top_k 分块
- 配置通过 `.env` + pydantic Settings 统一管理
- 添加 CLAUDE.md 项目说明文档，写入 devlog 自动追加规则
