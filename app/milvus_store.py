from pymilvus import DataType, MilvusClient


class MilvusChunkStore:
    def __init__(
        self,
        host: str,
        port: str,
        collection_name: str,
        #向量维度  就是一个向量里有多少个数字
        embedding_dim: int,
    ) -> None:
        self.collection_name = collection_name
        self.client = MilvusClient(uri=f"http://{host}:{port}")
        #检查 Milvus 里是否已经有这个 collection，有就直接加载;没有就按 schema 定义创建它
        self._ensure_collection(embedding_dim)

    def insert_chunks(
        self,
        doc_id: str,
        source_filename: str,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> int:
        rows = [
            {
                "id": f"{doc_id}_{chunk_index}",
                "text": chunk,
                "dense_vec": vector,
                "doc_id": doc_id,
                "chunk_index": chunk_index,
                "source_filename": source_filename,
            }
            #enumerate在每对前面加序号
            for chunk_index, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]

        if rows:
            self.client.insert(collection_name=self.collection_name, data=rows)
            self.client.flush(collection_name=self.collection_name)

        return len(rows)

    def search(self, query_vector: list[float], top_k: int) -> list[dict]:
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            #指定要在哪个向量字段上做近似最近邻检索,dense_vec 是稠密字段
            anns_field="dense_vec",
            #返回最相近的k个
            limit=top_k,
            #向量检索默认只返回向量主键 + 距离分数。如果想顺带把标量字段（原文、文档 ID、chunk 序号、源文件名）也一起拉回来，
            # 必须在这里显式列出。否则后续要再发一次 query 请求按主键回查，多一次 RTT（Round-Trip Time，往返时延）
            output_fields=["text", "doc_id", "chunk_index", "source_filename"],
            search_params={"metric_type": "COSINE", "params": {"nprobe": 10}},
        )
        chunks: list[dict] = []
        """
        data=[query_vector]   # 传入的是 list[list[float]]，只有 1 条
        results              # 返回的是 list[list[Hit]]，外层对应每条查询
        results[0]           # 第 0 条查询的结果 → list[Hit]
        """
        for hit in results[0]:

            #TODO: ⚠️ 这里有个不彻底的防御：下面 entity["text"]、entity["doc_id"] 都是用 [] 直接取的，
            # 如果 entity 真的是 {}，照样会抛 KeyError。所以 .get("entity", {}) 这个兜底其实是形式上的安全，实质上没生效。
            # 生产代码要么彻底用 .get(..., default)，要么干脆让它 fail-fast。这是一处面试时可以拿来讨论的代码味道（code smell）
            entity = hit.get("entity", {})
            # TODO:为什么chunks模板要这么设计?
            #DDD防腐层
            chunks.append(
                {
                    "id": hit["id"],
                    "text": entity["text"],
                    "score": float(hit["distance"]),
                    "metadata": {
                        "doc_id": entity["doc_id"],
                        "chunk_index": entity["chunk_index"],
                        "source_filename": entity["source_filename"],
                    },
                }
            )

        return chunks

    def _ensure_collection(self, embedding_dim: int) -> None:
        if self.client.has_collection(self.collection_name):
            #TODO:milvus的内存加载机制是什么？一次性会加载多少数据进来？怎么保证在数据量很大的情况下不会内存溢出？
            self.client.load_collection(collection_name=self.collection_name)
            return
        ##enable_dynamic_field=False 表示禁止动态字段。
        #TODO:什么是动态字段？
        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
        #"id"：字段名DataType.VARCHAR：字符串类型
        # is_primary=True：主键，每条数据唯一标识，不能重复
        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=128)
        schema.add_field("text", DataType.VARCHAR, max_length=65535)
        #向量维度 DataType.FLOAT_VECTOR：浮点向量类型，专门用于存 embedding
        schema.add_field("dense_vec", DataType.FLOAT_VECTOR, dim=embedding_dim)
        schema.add_field("doc_id", DataType.VARCHAR, max_length=64)
        schema.add_field("chunk_index", DataType.INT64)
        #文件名
        schema.add_field("source_filename", DataType.VARCHAR, max_length=512)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            #给哪个字段建索引
            field_name="dense_vec",
            index_type="IVF_FLAT",
            #相似度计算方式
            metric_type="COSINE",
            #把所有向量分成 128 个簇
            params={"nlist": 128},
        )
        #创建集合
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        self.client.load_collection(collection_name=self.collection_name)
