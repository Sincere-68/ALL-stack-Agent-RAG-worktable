import hashlib
import os
import re

from agent.knowledge.schema import KnowledgeElement
from agent.logger.logger import get_logger

logger = get_logger(__name__)

PARENT_CHARS = int(os.getenv("RAG_PARENT_CHARS", "1200"))
PARENT_OVERLAP_CHARS = int(os.getenv("RAG_PARENT_OVERLAP_CHARS", "200"))
CHILD_CHARS = int(os.getenv("RAG_CHILD_CHARS", "400"))
CHILD_OVERLAP_CHARS = int(os.getenv("RAG_CHILD_OVERLAP_CHARS", "100"))
TABLE_CHARS = int(os.getenv("RAG_TABLE_CHARS", "8000"))
ATOMIC_CHARS = int(os.getenv("RAG_ATOMIC_CHARS", "3000"))

ATOMIC_CONTENT_TYPES = {"table", "ocr", "image"}
SENTENCE_END_RE = re.compile(r"[\u3002\uff01\uff1f!?\.\uff1b;]\s*|[\r\n]+")


def semantic_split(elements: list[KnowledgeElement]) -> tuple[list[str], list[dict]]:
    chunks: list[str] = []
    metadatas: list[dict] = []

    buffer: list[str] = []
    buffer_meta: dict | None = None
    parent_counters: dict[str, int] = {}

    def flush_text_buffer() -> None:
        nonlocal buffer, buffer_meta
        if not buffer or not buffer_meta:
            buffer = []
            buffer_meta = None
            return

        text = "\n\n".join(part for part in buffer if part.strip()).strip()
        if text:
            _append_parent_child_chunks(text, buffer_meta, parent_counters, chunks, metadatas)

        buffer = []
        buffer_meta = None

    for element in elements:
        text = element.text.strip()
        if not text:
            continue

        meta = element.metadata()
        content_type = str(meta.get("content_type") or element.content_type or "text")

        if content_type in ATOMIC_CONTENT_TYPES:
            flush_text_buffer()
            max_chars = TABLE_CHARS if content_type == "table" else ATOMIC_CHARS
            for index, piece in enumerate(_split_atomic_text(text, max_chars)):
                atomic_meta = {
                    **meta,
                    "chunk_type": meta.get("chunk_type") or content_type,
                    "chunk_index": index,
                }
                chunks.append(_prefix_context(piece, atomic_meta))
                metadatas.append(atomic_meta)
            continue

        if buffer_meta and not _compatible(buffer_meta, meta):
            flush_text_buffer()

        if buffer_meta is None:
            buffer_meta = meta

        buffer.append(text)

    flush_text_buffer()
    logger.info("Semantic split produced %d chunks from %d elements", len(chunks), len(elements))
    return chunks, metadatas


def _append_parent_child_chunks(
    text: str,
    base_meta: dict,
    parent_counters: dict[str, int],
    chunks: list[str],
    metadatas: list[dict],
) -> None:
    parent_pieces = _split_with_sentence_boundaries(text, PARENT_CHARS, PARENT_OVERLAP_CHARS)
    source_key = _source_key(base_meta)

    for parent_text in parent_pieces:
        parent_index = parent_counters.get(source_key, 0)
        parent_counters[source_key] = parent_index + 1
        parent_id = _parent_id(base_meta, parent_index, parent_text)

        parent_meta = {
            **base_meta,
            "chunk_type": "large",
            "parent_id": parent_id,
            "parent_index": parent_index,
            "chunk_index": parent_index,
        }
        chunks.append(_prefix_context(parent_text, parent_meta))
        metadatas.append(parent_meta)

        child_pieces = _split_with_sentence_boundaries(parent_text, CHILD_CHARS, CHILD_OVERLAP_CHARS)
        for child_index, child_text in enumerate(child_pieces):
            child_meta = {
                **base_meta,
                "chunk_type": "small",
                "parent_id": parent_id,
                "parent_index": parent_index,
                "child_index": child_index,
                "chunk_index": child_index,
            }
            chunks.append(_prefix_context(child_text, child_meta))
            metadatas.append(child_meta)


def _compatible(left: dict, right: dict) -> bool:
    return (
        left.get("source") == right.get("source")
        and left.get("section_path") == right.get("section_path")
        and left.get("content_type") == right.get("content_type")
    )


def _split_with_sentence_boundaries(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    normalized = re.sub(r"[ \t]+", " ", text).strip()
    if len(normalized) <= max_chars:
        return [normalized] if normalized else []

    pieces: list[str] = []
    start = 0
    length = len(normalized)

    while start < length:
        hard_end = min(start + max_chars, length)
        end = _nearest_sentence_end(normalized, start, hard_end)
        piece = normalized[start:end].strip()
        if piece:
            pieces.append(piece)

        if end >= length:
            break

        next_start = max(end - overlap_chars, start + 1)
        next_start = _advance_to_sentence_start(normalized, next_start, end)
        start = next_start

    return pieces


def _split_atomic_text(text: str, max_chars: int) -> list[str]:
    normalized = re.sub(r"[ \t]+", " ", text).strip()
    if len(normalized) <= max_chars:
        return [normalized] if normalized else []

    pieces: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        line_break = normalized.rfind("\n", start, end)
        if line_break > start + int(max_chars * 0.6):
            end = line_break
        piece = normalized[start:end].strip()
        if piece:
            pieces.append(piece)
        start = end
    return pieces


def _nearest_sentence_end(text: str, start: int, hard_end: int) -> int:
    window = text[start:hard_end]
    matches = list(SENTENCE_END_RE.finditer(window))
    if not matches:
        return hard_end

    min_reasonable = int(len(window) * 0.55)
    for match in reversed(matches):
        if match.end() >= min_reasonable:
            return start + match.end()
    return hard_end


def _advance_to_sentence_start(text: str, candidate: int, previous_end: int) -> int:
    if candidate <= 0:
        return 0
    search_end = min(previous_end + 1, len(text))
    window = text[candidate:search_end]
    match = SENTENCE_END_RE.search(window)
    if match and match.end() < len(window):
        return candidate + match.end()
    return candidate


def _source_key(metadata: dict) -> str:
    return "|".join(
        str(metadata.get(key) or "")
        for key in ("source", "section_path", "content_type")
    )


def _parent_id(metadata: dict, parent_index: int, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    source = str(metadata.get("source") or "unknown")
    section = str(metadata.get("section_path") or "")
    section_digest = hashlib.sha1(section.encode("utf-8")).hexdigest()[:8]
    return f"{source}:{section_digest}:{parent_index}:{digest}"


def _prefix_context(text: str, metadata: dict) -> str:
    context = [
        f"Source: {metadata.get('source')}",
        f"Page: {metadata.get('page') or 'unknown'}",
        f"Section: {metadata.get('section_path') or 'unknown'}",
        f"Content type: {metadata.get('content_type') or 'text'}",
        f"Chunk type: {metadata.get('chunk_type') or 'unknown'}",
    ]
    if metadata.get("parent_index") is not None:
        context.append(f"Parent index: {metadata.get('parent_index')}")
    if metadata.get("table_number"):
        context.append(f"Table number: {metadata.get('table_number')}")
    if metadata.get("caption"):
        context.append(f"Caption: {metadata.get('caption')}")
    return "\n".join(context) + "\n\n" + text
