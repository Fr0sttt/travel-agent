"""
长期记忆管理模块

基于ChromaDB向量数据库实现三层记忆结构：
1. Episodic Memory（情节记忆）: 存储历史旅行交互事件
2. Semantic Memory（语义记忆）: 存储旅行知识和目的地信息
3. User Preference Memory（用户偏好记忆）: 存储用户画像和历史偏好

支持RAG检索，通过向量相似度搜索获取相关记忆。
"""

from typing import Any, Optional
import time
import json
import os
import hashlib
import httpx

# ChromaDB向量数据库
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class _InMemoryCollection:
    """内存集合 - ChromaDB不可用时降级使用

    提供与ChromaDB Collection类似的接口，数据存储在内存中。
    适合测试和开发环境。
    """

    def __init__(self, name: str, metadata: dict = None):
        self.name = name
        self.metadata = metadata or {}
        self._documents: dict[str, str] = {}  # id -> document
        self._metadatas: dict[str, dict] = {}  # id -> metadata
        self._embeddings: dict[str, list[float]] = {}  # id -> embedding

    def add(self, ids: list[str], documents: list[str],
            embeddings: list[list[float]] = None,
            metadatas: list[dict] = None) -> None:
        """添加文档到内存集合"""
        for i, doc_id in enumerate(ids):
            self._documents[doc_id] = documents[i]
            if metadatas and i < len(metadatas):
                self._metadatas[doc_id] = metadatas[i]
            if embeddings and i < len(embeddings):
                self._embeddings[doc_id] = embeddings[i]

    def query(self, query_texts: list[str] = None,
              query_embeddings: list[list[float]] = None,
              n_results: int = 5,
              where: dict = None,
              include: list[str] = None) -> dict:
        """查询内存集合（简单线性搜索）"""
        if not self._documents:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        # 过滤符合条件的文档
        filtered_ids = list(self._documents.keys())
        if where:
            filtered_ids = [
                doc_id for doc_id in filtered_ids
                if self._match_where(self._metadatas.get(doc_id, {}), where)
            ]

        if not filtered_ids:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        # 计算相似度（如果提供了embedding）
        if query_embeddings and query_embeddings[0]:
            query_vec = query_embeddings[0]
            scored = []
            for doc_id in filtered_ids:
                doc_vec = self._embeddings.get(doc_id)
                if doc_vec:
                    sim = self._cosine_similarity(query_vec, doc_vec)
                else:
                    # 无embedding时，用文本匹配度
                    sim = self._text_similarity(query_texts[0] if query_texts else "",
                                                 self._documents.get(doc_id, ""))
                scored.append((doc_id, sim))
            scored.sort(key=lambda x: x[1], reverse=True)
            top_ids = [doc_id for doc_id, _ in scored[:n_results]]
        elif query_texts and query_texts[0]:
            # 文本匹配
            scored = []
            query = query_texts[0]
            for doc_id in filtered_ids:
                sim = self._text_similarity(query, self._documents.get(doc_id, ""))
                scored.append((doc_id, sim))
            scored.sort(key=lambda x: x[1], reverse=True)
            top_ids = [doc_id for doc_id, _ in scored[:n_results]]
        else:
            top_ids = filtered_ids[:n_results]

        docs = [self._documents.get(doc_id, "") for doc_id in top_ids]
        metas = [self._metadatas.get(doc_id, {}) for doc_id in top_ids]
        dists = [1.0 - self._text_similarity(query_texts[0] if query_texts else "",
                                              self._documents.get(doc_id, ""))
                 for doc_id in top_ids]

        return {
            "documents": [docs],
            "metadatas": [metas],
            "distances": [dists]
        }

    def count(self) -> int:
        """返回文档数量"""
        return len(self._documents)

    def _match_where(self, metadata: dict, where: dict) -> bool:
        """匹配where条件"""
        for key, value in where.items():
            if key == "$and":
                if not all(self._match_where(metadata, cond) for cond in value):
                    return False
            elif key == "$or":
                if not any(self._match_where(metadata, cond) for cond in value):
                    return False
            elif metadata.get(key) != value:
                return False
        return True

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """简单文本相似度（Jaccard）"""
        if not a or not b:
            return 0.0
        set_a = set(a.lower())
        set_b = set(b.lower())
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0


class _InMemoryClient:
    """内存客户端 - ChromaDB不可用时降级使用"""

    def __init__(self, persist_dir: str = None, settings=None):
        self._collections: dict[str, _InMemoryCollection] = {}

    def get_or_create_collection(self, name: str, metadata: dict = None):
        """获取或创建集合"""
        if name not in self._collections:
            self._collections[name] = _InMemoryCollection(name, metadata)
        return self._collections[name]

    def delete_collection(self, name: str) -> None:
        """删除集合"""
        if name in self._collections:
            del self._collections[name]


class _ElasticsearchCollection:
    """Elasticsearch 索引包装器。

    以索引前缀模拟 ChromaDB Collection 接口，便于长期记忆模块无感切换。
    """

    def __init__(
        self,
        index_name: str,
        base_url: str,
        vector_dims: int = 384,
        username: str = "",
        password: str = "",
        metadata: dict | None = None,
    ):
        self.name = index_name
        self.metadata = metadata or {}
        self.base_url = base_url.rstrip("/")
        self.vector_dims = vector_dims
        self._auth = (username, password) if username and password else None
        self._client = httpx.Client(
            timeout=30.0,
            auth=self._auth,
            headers={"Content-Type": "application/json"},
        )
        self._ensure_index()

    def _index_url(self, suffix: str = "") -> str:
        return f"{self.base_url}/{self.name}{suffix}"

    def _ensure_index(self) -> None:
        """创建索引和向量映射。"""
        last_error: Exception | None = None
        for attempt in range(1, 31):
            try:
                resp = self._client.head(self._index_url())
                if resp.status_code == 200:
                    return
                if resp.status_code != 404:
                    resp.raise_for_status()

                mapping = {
                    "settings": {
                        "index": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0,
                        }
                    },
                    "mappings": {
                        "properties": {
                            "content": {"type": "text"},
                            "metadata": {"type": "object", "dynamic": True},
                            "embedding": {
                                "type": "dense_vector",
                                "dims": self.vector_dims,
                                "index": True,
                                "similarity": "cosine",
                            },
                            "session_id": {"type": "keyword"},
                            "type": {"type": "keyword"},
                            "topic": {"type": "keyword"},
                            "preference_type": {"type": "keyword"},
                            "timestamp": {"type": "date"},
                            "destination": {"type": "keyword"},
                        }
                    },
                }
                create_resp = self._client.put(self._index_url(), json=mapping)
                create_resp.raise_for_status()
                return
            except Exception as exc:
                last_error = exc
                if attempt >= 30:
                    raise
                time.sleep(2.0)

        if last_error is not None:
            raise last_error

    def add(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]] | None = None,
        metadatas: list[dict] | None = None,
    ) -> None:
        """批量写入文档。"""
        if not ids or not documents:
            return

        bulk_lines: list[str] = []
        for i, doc_id in enumerate(ids):
            document = documents[i]
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            embedding = embeddings[i] if embeddings and i < len(embeddings) else [0.0] * self.vector_dims

            payload = {
                "content": document,
                "metadata": metadata,
                "embedding": embedding,
            }
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        payload[key] = value

            bulk_lines.append(json.dumps({"index": {"_index": self.name, "_id": doc_id}}, ensure_ascii=False))
            bulk_lines.append(json.dumps(payload, ensure_ascii=False))

        body = "\n".join(bulk_lines) + "\n"
        resp = self._client.post(
            f"{self.base_url}/_bulk",
            content=body.encode("utf-8"),
            params={"refresh": "wait_for"},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errors"):
            raise RuntimeError(f"Elasticsearch bulk write failed: {data}")

    def query(
        self,
        query_texts: list[str] | None = None,
        query_embeddings: list[list[float]] | None = None,
        n_results: int = 5,
        where: dict | None = None,
        include: list[str] | None = None,
    ) -> dict:
        """检索相关文档。"""
        query_vector = query_embeddings[0] if query_embeddings and query_embeddings[0] else None
        filter_query = self._build_filter(where)

        if query_vector:
            inner_query: dict[str, Any] = {"match_all": {}}
            if filter_query:
                inner_query = {"bool": {"filter": filter_query}}
            body = {
                "size": n_results,
                "query": {
                    "script_score": {
                        "query": inner_query,
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {"query_vector": query_vector},
                        },
                    }
                },
                "_source": ["content", "metadata", "embedding", "session_id", "type", "topic", "preference_type", "timestamp", "destination"],
            }
        else:
            must_clause = []
            if query_texts and query_texts[0]:
                must_clause.append({"match": {"content": query_texts[0]}})
            body = {
                "size": n_results,
                "query": {
                    "bool": {
                        "must": must_clause or [{"match_all": {}}],
                        "filter": filter_query or [],
                    }
                },
                "_source": ["content", "metadata", "embedding", "session_id", "type", "topic", "preference_type", "timestamp", "destination"],
            }

        resp = self._client.post(f"{self._index_url()}/_search", json=body)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])

        documents: list[str] = []
        metadatas: list[dict] = []
        distances: list[float] = []
        for hit in hits:
            source = hit.get("_source", {})
            documents.append(source.get("content", ""))
            metadatas.append(source.get("metadata", {}) or {})
            score = float(hit.get("_score") or 0.0)
            if query_vector:
                distances.append(max(0.0, 2.0 - score))
            else:
                distances.append(1.0 / (score + 1.0))

        return {"documents": [documents], "metadatas": [metadatas], "distances": [distances]}

    def count(self) -> int:
        """返回索引文档数。"""
        resp = self._client.get(f"{self._index_url()}/_count")
        resp.raise_for_status()
        return int(resp.json().get("count", 0))

    def delete(self) -> None:
        """删除索引。"""
        resp = self._client.delete(self._index_url())
        if resp.status_code not in (200, 404):
            resp.raise_for_status()

    def _build_filter(self, where: dict | None) -> list[dict]:
        """把简单 where 条件翻译成 Elasticsearch filter。"""
        if not where:
            return []

        filters: list[dict] = []
        for key, value in where.items():
            if key == "$and" and isinstance(value, list):
                nested = [self._build_filter(item) for item in value]
                filters.append({"bool": {"must": [f for group in nested for f in group]}})
                continue
            if key == "$or" and isinstance(value, list):
                nested = [self._build_filter(item) for item in value]
                should_filters = [{"bool": {"filter": group}} for group in nested if group]
                if should_filters:
                    filters.append({"bool": {"should": should_filters, "minimum_should_match": 1}})
                continue

            if isinstance(value, (list, tuple, set)):
                filters.append({"terms": {key: list(value)}})
            else:
                filters.append({"term": {key: value}})
        return filters


class _ElasticsearchClient:
    """Elasticsearch 客户端包装器。"""

    def __init__(
        self,
        base_url: str,
        vector_dims: int = 384,
        username: str = "",
        password: str = "",
        index_prefix: str = "travel_memory",
    ):
        self.base_url = base_url.rstrip("/")
        self.vector_dims = vector_dims
        self.username = username
        self.password = password
        self.index_prefix = index_prefix
        self._collections: dict[str, _ElasticsearchCollection] = {}

    def get_or_create_collection(self, name: str, metadata: dict | None = None):
        if name not in self._collections:
            self._collections[name] = _ElasticsearchCollection(
                index_name=name,
                base_url=self.base_url,
                vector_dims=self.vector_dims,
                username=self.username,
                password=self.password,
                metadata=metadata,
            )
        return self._collections[name]

    def delete_collection(self, name: str) -> None:
        if name in self._collections:
            self._collections[name].delete()
            del self._collections[name]


class EmbeddingProvider:
    """Embedding提供者接口

    支持OpenAI Embedding或开源替代方案。
    当OpenAI不可用时，自动降级为简单的哈希模拟。
    """

    def __init__(self, provider: str = "openai", model: str = None):
        """初始化Embedding提供者

        Args:
            provider: embedding提供者类型 (openai/sentence-transformers/hash)
            model: 模型名称
        """
        self.provider = provider
        self.model = model
        self._client = None
        self._embedding_func = None

        if provider == "openai":
            self._init_openai()
        elif provider == "sentence-transformers":
            self._init_sentence_transformers()
        else:
            # 默认使用hash模拟（无需外部依赖）
            self.provider = "hash"

    def _init_openai(self) -> None:
        """初始化OpenAI Embedding"""
        try:
            import openai
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._client = openai.OpenAI(api_key=api_key)
                self.model = self.model or "text-embedding-3-small"
            else:
                self.provider = "hash"
        except ImportError:
            self.provider = "hash"

    def _init_sentence_transformers(self) -> None:
        """初始化Sentence Transformers（开源方案）"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = self.model or "all-MiniLM-L6-v2"
            self._client = SentenceTransformer(self.model)
        except ImportError:
            self.provider = "hash"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转换为embedding向量

        Args:
            texts: 要编码的文本列表

        Returns:
            embedding向量列表
        """
        if not texts:
            return []

        if self.provider == "openai" and self._client:
            try:
                response = self._client.embeddings.create(
                    model=self.model,
                    input=texts
                )
                return [item.embedding for item in response.data]
            except Exception:
                # 降级到hash方案
                return self._hash_embed(texts)

        elif self.provider == "sentence-transformers" and self._client:
            try:
                embeddings = self._client.encode(texts)
                return embeddings.tolist()
            except Exception:
                return self._hash_embed(texts)

        return self._hash_embed(texts)

    def _hash_embed(self, texts: list[str], dim: int = 384) -> list[list[float]]:
        """使用哈希函数生成确定性embedding（降级方案）

        无需外部依赖，生成确定性的伪随机向量。
        适合测试和开发环境。

        Args:
            texts: 文本列表
            dim: 向量维度

        Returns:
            embedding向量列表
        """
        import random
        results = []
        for text in texts:
            # 使用文本哈希作为随机种子，确保相同文本产生相同向量
            seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % (2**32)
            rng = random.Random(seed)
            vec = [rng.uniform(-1, 1) for _ in range(dim)]
            # L2归一化
            norm = sum(x**2 for x in vec) ** 0.5
            vec = [x / norm if norm > 0 else 0 for x in vec]
            results.append(vec)
        return results

    def embed_sync(self, texts: list[str]) -> list[list[float]]:
        """同步版本embedding（用于ChromaDB回调）"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在已运行的事件循环中，创建新循环
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result = new_loop.run_until_complete(self.embed(texts))
                asyncio.set_event_loop(loop)
                return result
            return loop.run_until_complete(self.embed(texts))
        except RuntimeError:
            # 没有事件循环，使用hash方案
            return self._hash_embed(texts)


class LongTermMemory:
    """长期记忆管理 - 向量数据库 + RAG

    三层记忆结构：
    1. Episodic Memory: 历史交互事件（对话、行程、反馈）
    2. Semantic Memory: 旅行知识和目的地信息
    3. User Preference Memory: 用户画像和历史偏好

    Attributes:
        client: ChromaDB客户端
        embedder: Embedding提供者
        episodic_collection: 情节记忆集合
        semantic_collection: 语义记忆集合
        preference_collection: 用户偏好集合
    """

    def __init__(
        self,
        collection_name: str = "travel_memory",
        persist_dir: str = "./data/chroma_db",
        embedding_provider: str = "hash",
        backend: str = "chromadb",
        elasticsearch_url: str = "http://127.0.0.1:9200",
        elasticsearch_username: str = "",
        elasticsearch_password: str = "",
        elasticsearch_index_prefix: str = "travel_memory",
        elasticsearch_vector_dims: int = 384,
    ):
        """????????"""
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self.backend = backend if backend in {"chromadb", "elasticsearch"} else "chromadb"
        self.elasticsearch_index_prefix = elasticsearch_index_prefix
        self.elasticsearch_vector_dims = elasticsearch_vector_dims
        self._use_chromadb = CHROMADB_AVAILABLE and self.backend == "chromadb"

        # ??? Embedding ???
        self.embedder = EmbeddingProvider(provider=embedding_provider)

        # ????????????????
        if self.backend == "elasticsearch":
            self.client = _ElasticsearchClient(
                base_url=elasticsearch_url,
                vector_dims=elasticsearch_vector_dims,
                username=elasticsearch_username,
                password=elasticsearch_password,
                index_prefix=elasticsearch_index_prefix,
            )
        elif self._use_chromadb:
            self.client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        else:
            # ????????
            self.client = _InMemoryClient(persist_dir=persist_dir)

        # ??????
        self.episodic_collection = self.client.get_or_create_collection(
            name=f"{collection_name}_episodic",
            metadata={"description": "????????"},
        )
        self.semantic_collection = self.client.get_or_create_collection(
            name=f"{collection_name}_semantic",
            metadata={"description": "??????????"},
        )
        self.preference_collection = self.client.get_or_create_collection(
            name=f"{collection_name}_preferences",
            metadata={"description": "??????"},
        )

    # ========== Episodic Memory（情节记忆） ==========

    async def add_interaction(self, session_id: str, query: str, response: str,
                              feedback: str = None, metadata: dict = None) -> str:
        """存储交互记录（Episodic Memory）

        记录一次完整的用户-Agent交互，包括查询、回复和反馈。

        Args:
            session_id: 会话ID
            query: 用户查询
            response: Agent回复
            feedback: 用户反馈（可选）
            metadata: 附加元数据（可选）

        Returns:
            记忆ID
        """
        memory_id = f"ep_{session_id}_{int(time.time() * 1000)}"

        document = f"""
        用户查询: {query}
        Agent回复: {response}
        {f"用户反馈: {feedback}" if feedback else ""}
        """.strip()

        meta = {
            "session_id": session_id,
            "type": "interaction",
            "timestamp": time.time(),
            "has_feedback": feedback is not None,
            "query_preview": query[:100],
        }
        if metadata:
            # ChromaDB元数据必须是简单类型
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    meta[key] = value
                elif isinstance(value, (list, dict)):
                    meta[key] = json.dumps(value, ensure_ascii=False)

        # 生成embedding
        embeddings = await self.embedder.embed([document])

        self.episodic_collection.add(
            ids=[memory_id],
            documents=[document],
            embeddings=embeddings if embeddings else None,
            metadatas=[meta]
        )

        return memory_id

    async def add_episode(self, session_id: str, episode: dict) -> str:
        """添加情节记忆

        Args:
            session_id: 会话ID
            episode: 情节字典，包含：
                - event: 事件描述
                - outcome: 结果
                - satisfaction: 满意度 (0-1)
                - destination: 目的地
                - tags: 标签列表

        Returns:
            记忆ID
        """
        memory_id = f"ep_{session_id}_{episode.get('event', '')[:20]}_{int(time.time())}"

        document = f"""
        事件: {episode.get('event', '')}
        结果: {episode.get('outcome', '')}
        满意度: {episode.get('satisfaction', 'unknown')}
        目的地: {episode.get('destination', 'unknown')}
        """.strip()

        embeddings = await self.embedder.embed([document])

        self.episodic_collection.add(
            ids=[memory_id],
            documents=[document],
            embeddings=embeddings if embeddings else None,
            metadatas=[{
                "session_id": session_id,
                "destination": episode.get("destination", ""),
                "satisfaction": episode.get("satisfaction", 0),
                "tags": ",".join(episode.get("tags", [])),
                "type": "episode",
                "timestamp": time.time()
            }]
        )

        return memory_id

    # ========== Semantic Memory（语义记忆） ==========

    async def add_travel_knowledge(self, topic: str, content: str,
                                    source: str = None, metadata: dict = None) -> str:
        """存储旅行知识（Semantic Memory）

        Args:
            topic: 知识主题
            content: 知识内容
            source: 来源（可选）
            metadata: 附加元数据（可选）

        Returns:
            知识ID
        """
        knowledge_id = f"km_{topic.replace(' ', '_')}_{int(time.time())}"

        meta = {
            "topic": topic,
            "source": source or "manual",
            "type": "knowledge",
            "timestamp": time.time()
        }
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    meta[key] = value
                elif isinstance(value, (list, dict)):
                    meta[key] = json.dumps(value, ensure_ascii=False)

        embeddings = await self.embedder.embed([content])

        self.semantic_collection.add(
            ids=[knowledge_id],
            documents=[content],
            embeddings=embeddings if embeddings else None,
            metadatas=[meta]
        )

        return knowledge_id

    # ========== 检索方法 ==========

    async def retrieve_relevant(self, query: str, k: int = 5,
                                 memory_type: str = None) -> list[dict]:
        """检索相关记忆

        根据查询文本检索最相关的记忆，支持按类型过滤。

        Args:
            query: 查询文本
            k: 返回的最大结果数
            memory_type: 记忆类型过滤 (episodic/semantic/preference)

        Returns:
            相关记忆列表，每项包含content、metadata、distance
        """
        # 生成查询embedding
        query_embeddings = await self.embedder.embed([query])
        query_embedding = query_embeddings[0] if query_embeddings else None

        results = []

        # 从指定集合检索
        collections_to_search = []
        if memory_type == "episodic":
            collections_to_search = [("episodic", self.episodic_collection)]
        elif memory_type == "semantic":
            collections_to_search = [("semantic", self.semantic_collection)]
        elif memory_type == "preference":
            collections_to_search = [("preference", self.preference_collection)]
        else:
            # 混合检索：搜索所有集合
            collections_to_search = [
                ("episodic", self.episodic_collection),
                ("semantic", self.semantic_collection),
                ("preference", self.preference_collection)
            ]

        for coll_type, collection in collections_to_search:
            try:
                if query_embedding:
                    raw_results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=min(k, 10),
                        include=["documents", "metadatas", "distances"]
                    )
                else:
                    raw_results = collection.query(
                        query_texts=[query],
                        n_results=min(k, 10),
                        include=["documents", "metadatas", "distances"]
                    )

                if raw_results["documents"] and raw_results["documents"][0]:
                    for doc, meta, dist in zip(
                        raw_results["documents"][0],
                        raw_results["metadatas"][0],
                        raw_results["distances"][0]
                    ):
                        results.append({
                            "content": doc,
                            "metadata": meta,
                            "distance": dist,
                            "memory_type": coll_type
                        })
            except Exception as e:
                # 集合可能为空或查询失败，跳过
                print(f"[LongTermMemory] 检索{coll_type}集合时出错: {e}")
                continue

        # 按距离排序（升序，距离越小越相关）
        results.sort(key=lambda x: x["distance"])

        return results[:k]

    async def get_user_preferences(self, user_id: str) -> dict:
        """获取用户历史偏好

        从用户偏好集合中检索指定用户的所有偏好信息。

        Args:
            user_id: 用户ID

        Returns:
            用户偏好字典
        """
        try:
            results = self.preference_collection.query(
                query_texts=[f"用户 {user_id} 偏好"],
                where={"session_id": user_id},
                n_results=20,
                include=["documents", "metadatas"]
            )

            prefs = {}
            if results["documents"] and results["documents"][0]:
                for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                    pref_type = meta.get("preference_type", "general")
                    prefs[pref_type] = {
                        "content": doc,
                        "metadata": meta
                    }

            # 同时从episodic集合中搜索偏好相关信息
            episodic_results = self.episodic_collection.query(
                query_texts=[f"用户偏好 预算 目的地 兴趣 {user_id}"],
                n_results=5,
                include=["documents", "metadatas"]
            )

            if episodic_results["documents"] and episodic_results["documents"][0]:
                prefs["_from_episodes"] = [
                    {"content": doc, "metadata": meta}
                    for doc, meta in zip(
                        episodic_results["documents"][0],
                        episodic_results["metadatas"][0]
                    )
                ]

            return prefs

        except Exception as e:
            print(f"[LongTermMemory] 获取用户偏好时出错: {e}")
            return {}

    async def update_user_profile(self, user_id: str, new_info: dict) -> str:
        """更新用户画像

        将新的用户偏好信息存储到偏好集合中。

        Args:
            user_id: 用户ID
            new_info: 新的偏好信息字典

        Returns:
            偏好记录ID
        """
        pref_id = f"pref_{user_id}_{int(time.time() * 1000)}"

        # 构建偏好文档
        info_parts = []
        for key, value in new_info.items():
            if isinstance(value, (list, dict)):
                info_parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
            else:
                info_parts.append(f"{key}: {value}")

        document = f"用户 {user_id} 偏好信息: " + "; ".join(info_parts)

        meta = {
            "session_id": user_id,
            "preference_type": new_info.get("type", "general"),
            "type": "preference",
            "timestamp": time.time()
        }
        # 添加其他简单类型元数据
        for key, value in new_info.items():
            if isinstance(value, (str, int, float, bool)):
                meta[f"pref_{key}"] = value

        embeddings = await self.embedder.embed([document])

        self.preference_collection.add(
            ids=[pref_id],
            documents=[document],
            embeddings=embeddings if embeddings else None,
            metadatas=[meta]
        )

        return pref_id

    async def get_similar_itineraries(self, destination: str, style: str) -> list[dict]:
        """获取相似行程作为参考

        检索指定目的地和风格的历史行程。

        Args:
            destination: 目的地
            style: 旅行风格（如family/romantic/adventure/cultural）

        Returns:
            相似行程列表
        """
        query = f"{destination} {style} 旅行行程  itinerary"

        results = self.episodic_collection.query(
            query_texts=[query],
            where={"type": "episode"},
            n_results=5,
            include=["documents", "metadatas", "distances"]
        )

        itineraries = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            ):
                itineraries.append({
                    "content": doc,
                    "metadata": meta,
                    "distance": dist,
                    "destination": meta.get("destination", ""),
                    "tags": meta.get("tags", "").split(",")
                })

        return itineraries

    async def store_preference(self, session_id: str, preference_type: str,
                                preference_value: Any) -> str:
        """存储用户偏好（快捷方法）

        Args:
            session_id: 会话ID
            preference_type: 偏好类型
            preference_value: 偏好值

        Returns:
            偏好ID
        """
        pref_id = f"pref_{session_id}_{preference_type}_{int(time.time())}"

        document = f"用户偏好: {preference_type} = {preference_value}"

        self.preference_collection.add(
            ids=[pref_id],
            documents=[document],
            metadatas=[{
                "session_id": session_id,
                "preference_type": preference_type,
                "type": "preference",
                "timestamp": time.time()
            }]
        )

        return pref_id

    # ========== 工具方法 ==========

    def get_collection_stats(self) -> dict:
        """获取集合统计信息

        Returns:
            各集合的文档数量统计
        """
        try:
            return {
                "episodic": self.episodic_collection.count(),
                "semantic": self.semantic_collection.count(),
                "preferences": self.preference_collection.count()
            }
        except Exception as e:
            return {"error": str(e)}

    def clear_collection(self, collection_type: str = None) -> None:
        """清空指定集合

        Args:
            collection_type: 集合类型 (episodic/semantic/preference/all)
        """
        try:
            if collection_type in ("episodic", "all"):
                self.client.delete_collection(f"{self.collection_name}_episodic")
                self.episodic_collection = self.client.get_or_create_collection(
                    name=f"{self.collection_name}_episodic"
                )
            if collection_type in ("semantic", "all"):
                self.client.delete_collection(f"{self.collection_name}_semantic")
                self.semantic_collection = self.client.get_or_create_collection(
                    name=f"{self.collection_name}_semantic"
                )
            if collection_type in ("preference", "all"):
                self.client.delete_collection(f"{self.collection_name}_preferences")
                self.preference_collection = self.client.get_or_create_collection(
                    name=f"{self.collection_name}_preferences"
                )
        except Exception as e:
            print(f"[LongTermMemory] 清空集合时出错: {e}")

    def __repr__(self) -> str:
        stats = self.get_collection_stats()
        return (
            f"LongTermMemory("
            f"episodic={stats.get('episodic', 0)}, "
            f"semantic={stats.get('semantic', 0)}, "
            f"preferences={stats.get('preferences', 0)}, "
            f"embedder={self.embedder.provider}"
            f")"
        )
