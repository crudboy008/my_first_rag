from pymilvus import DataType, MilvusClient


class MilvusChunkStore:
    def __init__(
        self,
        host: str,
        port: str,
        collection_name: str,
        embedding_dim: int,
    ) -> None:
        self.collection_name = collection_name
        self.client = MilvusClient(uri=f"http://{host}:{port}")
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
            anns_field="dense_vec",
            limit=top_k,
            output_fields=["text", "doc_id", "chunk_index", "source_filename"],
            search_params={"metric_type": "COSINE", "params": {"nprobe": 10}},
        )

        chunks: list[dict] = []
        for hit in results[0]:
            entity = hit.get("entity", {})
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
            self.client.load_collection(collection_name=self.collection_name)
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=128)
        schema.add_field("text", DataType.VARCHAR, max_length=65535)
        schema.add_field("dense_vec", DataType.FLOAT_VECTOR, dim=embedding_dim)
        schema.add_field("doc_id", DataType.VARCHAR, max_length=64)
        schema.add_field("chunk_index", DataType.INT64)
        schema.add_field("source_filename", DataType.VARCHAR, max_length=512)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="dense_vec",
            index_type="IVF_FLAT",
            metric_type="COSINE",
            params={"nlist": 128},
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        self.client.load_collection(collection_name=self.collection_name)
