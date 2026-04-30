# 架构图 v0.2 待办

v0.1(upload-flow-v0.1.png)是局部流程图,v0.2 升级为系统架构图,必须包含:

## 必须有
- [ ] 两个接口都画(POST /api/upload + POST /api/search)
- [ ] Milvus 作为独立组件(画成数据库符号,标 collection 名)
- [ ] dashscope API 作为独立外部服务(标"外部依赖")
- [ ] 数据形态在每条箭头上标注(PDF / str / List[str] / List[List[float]])
- [ ] 模块/文件分组(用虚线框圈出 routes/ services/ db/)

## 加分项
- [ ] 错误路径(Milvus 挂 / dashscope 超时 / PDF 加密)
- [ ] chunk metadata 结构(doc_id / chunk_index / source_filename + v0.1.1 要加的 4 个字段)
- [ ] 用 Mermaid 重画一遍,塞进 README