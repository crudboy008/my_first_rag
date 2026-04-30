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