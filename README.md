# my_first_rag

今晚版最小 RAG 检索服务：上传 PDF，提取文本，切块，调用通义 `text-embedding-v2` 生成 1536 维 dense 向量，写入本地 Milvus collection `rag_demo_v1`，再通过关键词/query 做 COSINE 召回。

## 环境准备

要求本地 Milvus 已在 `localhost:19530` 运行。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DASHSCOPE_API_KEY="你的通义 DashScope API Key"
```

可选配置见 `.env.example`。如果使用 `.env`，需要自行加载环境变量后再启动服务。

## 启动服务

```powershell
.\scripts\run-dev.ps1
```

健康检查：

```powershell
curl.exe http://127.0.0.1:18088/health
```

## 上传 PDF

```powershell
curl.exe -X POST "http://127.0.0.1:18088/api/upload" `
  -F "file=@E:\path\to\sample.pdf;type=application/pdf"
```

期望返回：

```json
{
  "doc_id": "uuid",
  "chunk_count": 3,
  "filename": "sample.pdf"
}
```

## 检索 chunks

```powershell
curl.exe -X POST "http://127.0.0.1:18088/api/search" `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"你的关键词\",\"top_k\":3}"
```

期望返回：

```json
{
  "chunks": [
    {
      "id": "chunk-id",
      "text": "chunk text",
      "score": 0.8,
      "metadata": {
        "doc_id": "uuid",
        "chunk_index": 0,
        "source_filename": "sample.pdf"
      }
    }
  ]
}
```

## 验收清单

1. `curl.exe` 上传 PDF，返回 `{doc_id, chunk_count, filename}`，且 `chunk_count > 0`。
2. `curl.exe` 查询关键词，返回 top 3 相关 chunks。
3. 停止并重启 `uvicorn` 后，再次调用 `/api/search`，Milvus 中数据仍可召回。
4. 确认无敏感信息后再提交并 push：

```powershell
git status
git add .
git commit -m "Add minimal PDF RAG search service"
git push
```
