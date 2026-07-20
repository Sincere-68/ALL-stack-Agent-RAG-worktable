"""
ChromaDB vector store for the knowledge base.

Embeddings use the configured OpenAI-compatible API endpoint.
"""
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from agent.logger.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

# 使用 HuggingFace 国内镜像加速下载，离线模式避免重复检查
CHROMA_DIR = Path(__file__).resolve().parents[2] / "chroma_db"

# 全局单例
CHROMA_DIR = Path(__file__).resolve().parents[2] / "chroma_db"

_vectorstore = None
_embedding = None

EMBEDDING_COLLECTION_NAME = os.getenv("EMBEDDING_COLLECTION_NAME", "knowledge_base_bge_m3")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
RETRIEVAL_CANDIDATE_MULTIPLIER = int(os.getenv("RETRIEVAL_CANDIDATE_MULTIPLIER", "8"))
MAX_RERANK_BONUS = float(os.getenv("RETRIEVAL_MAX_RERANK_BONUS", "0.6"))

_TABLE_INTENT_TERMS = {
    "table",
    "tables",
    "tab",
    "表",
    "表格",
    "数据",
    "结果",
    "指标",
    "准确率",
    "召回率",
    "精确率",
    "precision",
    "recall",
    "accuracy",
    "f1",
    "iou",
}
_CHINESE_NUMERAL_MAP = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _build_embedding():
    from langchain_openai import OpenAIEmbeddings
    import httpx

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    trust_env = _env_enabled("LLM_TRUST_ENV_PROXY")
    timeout = float(os.getenv("EMBEDDING_TIMEOUT", os.getenv("LLM_TIMEOUT", "30")))

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for embeddings.")

    kwargs = {
        "model": EMBEDDING_MODEL,
        "api_key": api_key,
        "http_client": httpx.Client(trust_env=trust_env, timeout=timeout),
        "max_retries": int(os.getenv("EMBEDDING_MAX_RETRIES", os.getenv("LLM_MAX_RETRIES", "1"))),
        "timeout": timeout,
    }
    if base_url:
        kwargs["base_url"] = base_url

    logger.info(
        "OpenAI-compatible embedding model initialized: model=%s, base_url=%s",
        EMBEDDING_MODEL,
        base_url or "default",
    )
    return OpenAIEmbeddings(**kwargs)


def _get_embedding():
    global _embedding
    if _embedding is None:
        _embedding = _build_embedding()
    return _embedding


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        import chromadb
        from langchain_chroma import Chroma
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _vectorstore = Chroma(
            client=client,
            collection_name=EMBEDDING_COLLECTION_NAME,
            embedding_function=_get_embedding(),
        )
        logger.info(
            "ChromaDB vectorstore initialized at %s, collection=%s, embedding_model=%s",
            CHROMA_DIR,
            EMBEDDING_COLLECTION_NAME,
            EMBEDDING_MODEL,
        )
    return _vectorstore


def add_documents(chunks: list[str], metadata: dict = None, metadatas: list[dict] | None = None):
    """将文本 chunks 存入向量库"""
    vs = _get_vectorstore()
    if metadatas is None:
        metadatas = [metadata or {} for _ in chunks]
    try:
        vs.add_texts(texts=chunks, metadatas=metadatas)
    except Exception as error:
        if "expecting embedding with dimension" in str(error).lower():
            raise RuntimeError(
                "Embedding dimension mismatch. The current Chroma collection was created with a "
                "different embedding model. Restart the backend and use "
                f"EMBEDDING_COLLECTION_NAME={EMBEDDING_COLLECTION_NAME}, or rebuild chroma_db. "
                f"Current EMBEDDING_MODEL={EMBEDDING_MODEL}."
            ) from error
        raise
    logger.info("Added %d chunks to vectorstore", len(chunks))


def search(query: str, k: int = 4) -> list[str]:
    docs = _search_documents(query, k)
    return [_format_result(doc, vs) for doc, vs in docs]


def search_with_sources(query: str, k: int = 4) -> dict:
    docs = _search_documents(query, k)
    contexts = []
    sources = []
    for index, (doc, vs) in enumerate(docs, start=1):
        contexts.append(_format_result(doc, vs))
        sources.append(_source_payload(doc, rank=index))
    return {"contexts": contexts, "sources": sources}


def _search_documents(query: str, k: int = 4) -> list[tuple]:
    vs = _get_vectorstore()
    candidate_k = max(k, k * RETRIEVAL_CANDIDATE_MULTIPLIER)
    try:
        scored_results = vs.similarity_search_with_score(query, k=candidate_k)
    except Exception:
        logger.warning(
            "similarity_search_with_score failed; falling back to similarity_search",
            exc_info=True,
        )
        return [(doc, vs) for doc in vs.similarity_search(query, k=k)]

    reranked = _rerank_results(query, scored_results)
    deduped = _dedupe_results(reranked)
    return [(doc, vs) for doc, _score, _bonus in deduped[:k]]

def _rerank_results(query: str, scored_results: list[tuple]) -> list[tuple]:
    terms = _extract_query_terms(query)
    query_tables = _extract_table_numbers(query)
    table_intent = _has_table_intent(query, terms, query_tables)

    reranked = []
    for doc, distance in scored_results:
        bonus = _lexical_bonus(doc, terms, query_tables, table_intent)
        final_score = -float(distance) + bonus
        reranked.append((doc, final_score, bonus))

    reranked.sort(key=lambda item: item[1], reverse=True)
    return reranked


def _lexical_bonus(doc, terms: list[str], query_tables: set[int], table_intent: bool) -> float:
    meta = doc.metadata or {}
    content = (doc.page_content or "").lower()
    section = str(meta.get("section_path") or "").lower()
    content_type = str(meta.get("content_type") or "").lower()
    chunk_type = str(meta.get("chunk_type") or "").lower()
    doc_tables = _doc_table_numbers(doc)

    bonus = 0.0
    for term in terms:
        normalized = term.lower()
        if normalized and normalized in content:
            bonus += 0.08
        if normalized and normalized in section:
            bonus += 0.12

    if chunk_type == "small":
        bonus += 0.03

    is_table = content_type == "table" or chunk_type == "table" or bool(doc_tables)
    if is_table:
        bonus += 0.05
        if table_intent:
            bonus += 0.08

    if query_tables and doc_tables:
        if query_tables & doc_tables:
            bonus += 0.5
        else:
            bonus -= 0.05

    return min(bonus, MAX_RERANK_BONUS)


def _dedupe_results(results: list[tuple]) -> list[tuple]:
    merged = []
    seen = set()
    for doc, score, bonus in results:
        meta = doc.metadata or {}
        table_numbers = _doc_table_numbers(doc)
        if table_numbers:
            key = ("table", meta.get("source"), tuple(sorted(table_numbers)))
        else:
            key = (
                meta.get("source"),
                meta.get("page"),
                meta.get("section_path"),
                meta.get("content_type"),
                (doc.page_content or "")[:160],
            )
        if key in seen:
            continue
        seen.add(key)
        merged.append((doc, score, bonus))
    return merged


def _extract_query_terms(query: str) -> list[str]:
    normalized = query.strip().lower()
    terms = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{1,}|[\u4e00-\u9fff]{2,}|\d+(?:\.\d+)?%?", normalized)
    stop_terms = {"什么", "如何", "这个", "那个", "请问", "一下", "请", "the", "and", "for", "with"}
    return [term for term in dict.fromkeys(terms) if term not in stop_terms]


def _has_table_intent(query: str, terms: list[str], query_tables: set[int]) -> bool:
    if query_tables:
        return True
    normalized = query.lower()
    return any(term in normalized for term in _TABLE_INTENT_TERMS) or any(
        term in _TABLE_INTENT_TERMS for term in terms
    )


def _doc_table_numbers(doc) -> set[int]:
    meta = doc.metadata or {}
    numbers = set()
    for key in ("table_number", "table_index"):
        value = meta.get(key)
        if value is not None:
            try:
                numbers.add(int(value))
            except (TypeError, ValueError):
                pass
    numbers.update(_extract_table_numbers(doc.page_content or ""))
    return numbers


def _extract_table_numbers(text: str) -> set[int]:
    numbers = set()
    pattern = (
        r"表\s*(\d{1,3})"
        r"|第\s*(\d{1,3})\s*(?:张表|个表|表)"
        r"|table\s*(\d{1,3})"
        r"|tab\.\s*(\d{1,3})"
    )
    for match in re.finditer(pattern, text, re.I):
        for group in match.groups():
            if group:
                numbers.add(int(group))
    for match in re.finditer(r"表\s*([一二三四五六七八九十])|第\s*([一二三四五六七八九十])\s*(?:张表|个表|表)", text):
        value = _CHINESE_NUMERAL_MAP.get(match.group(1))
        if value is None and match.lastindex and match.group(2):
            value = _CHINESE_NUMERAL_MAP.get(match.group(2))
        if value is not None:
            numbers.add(value)
    return numbers


def _format_result(doc, vectorstore=None) -> str:
    meta = doc.metadata or {}
    source = meta.get("source", "unknown")
    page = meta.get("page") or "unknown"
    section = meta.get("section_path") or "unknown"
    content_type = meta.get("content_type") or "text"
    chunk_type = meta.get("chunk_type") or "unknown"
    table_number = meta.get("table_number")
    caption = meta.get("caption")
    table_context = ""
    if table_number:
        table_context += f"; Table: {table_number}"
    if caption:
        table_context += f"; Caption: {caption}"
    header = (
        f"[Source: {source}; Page: {page}; Section: {section}; Type: {content_type}; "
        f"Chunk: {chunk_type}{table_context}]"
    )
    parent_context = _get_parent_context(doc, vectorstore)
    if parent_context:
        return f"{header}\n{doc.page_content}\n\n[Parent context]\n{parent_context}"
    return f"{header}\n{doc.page_content}"


def _source_payload(doc, rank: int) -> dict:
    meta = doc.metadata or {}
    table_number = meta.get("table_number")
    try:
        table_number = int(table_number) if table_number not in {None, ""} else None
    except (TypeError, ValueError):
        table_number = None

    return {
        "rank": rank,
        "source": meta.get("source") or "unknown",
        "page": meta.get("page") or None,
        "section_path": meta.get("section_path") or "",
        "content_type": meta.get("content_type") or "text",
        "chunk_type": meta.get("chunk_type") or "unknown",
        "table_number": table_number,
        "caption": meta.get("caption") or "",
        "preview": _preview_text(doc.page_content or ""),
    }


def _preview_text(text: str, limit: int = 180) -> str:
    if text.startswith("Source:") and "\n\n" in text:
        text = text.split("\n\n", 1)[1]
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:limit] + ("..." if len(cleaned) > limit else "")


def _get_parent_context(doc, vectorstore=None) -> str:
    meta = doc.metadata or {}
    if str(meta.get("chunk_type") or "").lower() != "small":
        return ""
    parent_id = meta.get("parent_id")
    if not parent_id or vectorstore is None:
        return ""

    try:
        result = vectorstore._collection.get(
            where={"parent_id": parent_id},
            include=["documents", "metadatas"],
            limit=3,
        )
    except Exception:
        logger.debug("Failed to fetch parent context for %s", parent_id, exc_info=True)
        return ""

    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []
    for parent_doc, parent_meta in zip(documents, metadatas):
        if str((parent_meta or {}).get("chunk_type") or "").lower() == "large":
            return parent_doc
    return ""


def get_stats() -> dict:
    vs = _get_vectorstore()
    collection = vs._collection
    return {
        "total_chunks": collection.count(),
        "embedding_model": EMBEDDING_MODEL,
        "embedding_collection": EMBEDDING_COLLECTION_NAME,
    }


def delete_by_source(source: str):
    """按来源删除文档"""
    vs = _get_vectorstore()
    vs._collection.delete(where={"source": source})
    logger.info("Deleted documents with source: %s", source)


def list_documents() -> list[dict]:
    """列出所有文档及其 chunk 内容"""
    vs = _get_vectorstore()
    collection = vs._collection
    all_data = collection.get(include=["documents", "metadatas"])

    docs = {}
    for doc_id, doc, meta in zip(all_data["ids"], all_data["documents"], all_data["metadatas"]):
        source = meta.get("source", "unknown")
        if source not in docs:
            docs[source] = {"filename": source, "chunks": []}
        docs[source]["chunks"].append({
            "id": doc_id,
            "content": doc[:500],  # 截断显示
        })

    return list(docs.values())
