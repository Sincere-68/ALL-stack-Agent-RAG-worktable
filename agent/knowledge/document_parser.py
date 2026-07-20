from pathlib import Path

from agent.knowledge.loader import load_file
from agent.knowledge.pdf_parser import parse_pdf
from agent.knowledge.schema import KnowledgeElement
from agent.logger.logger import get_logger

logger = get_logger(__name__)


def parse_document(file_path: str) -> list[KnowledgeElement]:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(path)

    text = load_file(str(path))
    logger.info("Using text fallback parser for %s", path.name)
    return [
        KnowledgeElement(
            text=text,
            source=path.name,
            page=None,
            section_path="",
            content_type=_content_type_for_suffix(suffix),
        )
    ]


def _content_type_for_suffix(suffix: str) -> str:
    if suffix in {".csv", ".xlsx"}:
        return "table"
    return "text"

