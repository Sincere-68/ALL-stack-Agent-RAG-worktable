import re
from pathlib import Path

from agent.knowledge.ocr_vlm import describe_image
from agent.knowledge.schema import KnowledgeElement
from agent.logger.logger import get_logger

logger = get_logger(__name__)

TITLE_PATTERNS = [
    (1, re.compile(r"^(\u6458\u8981|abstract|\u5173\u952e\u8bcd|key words?|\u53c2\u8003\u6587\u732e|references)$", re.I)),
    (1, re.compile(r"^\u7b2c[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\d]+[\u7ae0\u8282\u7bc7]\s*.?")),
    (1, re.compile(r"^\d{1,2}\s+(?!.*\d)[\u4e00-\u9fffA-Za-z].{0,60}$")),
    (2, re.compile(r"^\d+\.\d+\s*.+")),
    (3, re.compile(r"^\d+\.\d+\.\d+\s*.+")),
    (2, re.compile(r"^[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]+[\u3001\uff0e]\s*.+")),
    (3, re.compile(r"^[\(\uff08][\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\d]+[\)\uff09]\s*.+")),
]

def parse_pdf(path: Path) -> list[KnowledgeElement]:
    import fitz

    doc = fitz.open(str(path))
    elements: list[KnowledgeElement] = []
    section_stack: list[str] = []
    table_counter = 0

    for page_index, page in enumerate(doc, start=1):
        page_text = page.get_text("text").strip()

        if len(page_text) < int(_get_env("OCR_MIN_TEXT_LENGTH", "80")):
            ocr_text = _ocr_page(page)
            if ocr_text:
                elements.append(
                    KnowledgeElement(
                        text=_format_text(ocr_text),
                        source=path.name,
                        page=page_index,
                        section_path=" > ".join(section_stack),
                        content_type="ocr",
                    )
                )
            continue

        table_entries = _extract_tables(page, page_text, table_counter + 1)
        if table_entries:
            table_counter += len(table_entries)
        else:
            table_entries = _extract_text_tables(page_text, table_counter + 1)
            table_counter += len(table_entries)

        for table_entry in table_entries:
            elements.append(
                KnowledgeElement(
                    text=table_entry["text"],
                    source=path.name,
                    page=page_index,
                    section_path=" > ".join(section_stack),
                    content_type="table",
                    extra_metadata={
                        "chunk_type": "table",
                        "table_number": table_entry["table_number"],
                        "caption": table_entry.get("caption", ""),
                    },
                )
            )

        for paragraph in _page_paragraphs(page, page_text):
            title_level = paragraph.get("title_level") or _title_level(paragraph["text"])
            if title_level:
                section_stack = section_stack[: title_level - 1]
                section_stack.append(_clean_title(paragraph["text"]))
                continue

            elements.append(
                KnowledgeElement(
                    text=_format_text(paragraph["text"]),
                    source=path.name,
                    page=page_index,
                    section_path=" > ".join(section_stack),
                    content_type="text",
                )
            )

    logger.info("Parsed %d knowledge elements from PDF %s", len(elements), path.name)
    return [element for element in elements if element.text.strip()]


def _get_env(name: str, default: str) -> str:
    import os

    return os.getenv(name, default)


def _paragraphs(text: str) -> list[str]:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = re.split(r"\n{2,}", cleaned)
    paragraphs: list[str] = []
    for part in parts:
        lines = [line.strip() for line in part.splitlines() if line.strip()]
        if not lines:
            continue
        if all(len(line) < 80 for line in lines):
            paragraphs.extend(lines)
        else:
            paragraphs.append(" ".join(lines))
    return [_format_text(paragraph) for paragraph in paragraphs if paragraph.strip()]


def _page_paragraphs(page, page_text: str) -> list[dict]:
    styled_lines = _styled_lines(page)
    if not styled_lines:
        return [{"text": paragraph, "title_level": _title_level(paragraph)} for paragraph in _paragraphs(page_text)]

    body_size = _median([line["size"] for line in styled_lines if line["size"] > 0]) or 10.5
    paragraphs: list[dict] = []
    for line in styled_lines:
        text = _format_text(line["text"])
        if not text:
            continue
        title_level = _title_level(text)
        if title_level is None:
            title_level = _style_title_level(text, line, body_size)
        paragraphs.append({"text": text, "title_level": title_level})

    return paragraphs or [{"text": paragraph, "title_level": _title_level(paragraph)} for paragraph in _paragraphs(page_text)]


def _styled_lines(page) -> list[dict]:
    try:
        data = page.get_text("dict")
    except Exception:
        return []

    lines: list[dict] = []
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = [span for span in line.get("spans", []) if span.get("text", "").strip()]
            if not spans:
                continue
            text = "".join(span.get("text", "") for span in spans).strip()
            if not text:
                continue
            max_size = max(float(span.get("size") or 0) for span in spans)
            bold = any(_is_bold_span(span) for span in spans)
            lines.append({"text": text, "size": max_size, "bold": bold})
    return lines


def _is_bold_span(span: dict) -> bool:
    font = str(span.get("font") or "").lower()
    flags = int(span.get("flags") or 0)
    return bool(flags & 16) or any(token in font for token in ("bold", "black", "heavy", "hei", "heiti"))


def _style_title_level(text: str, line: dict, body_size: float) -> int | None:
    candidate = _clean_title(text)
    if len(candidate) > 90 or _is_table_caption(candidate):
        return None
    if re.search(r"[\u3002\uff01\uff1f\uff0c,!?;；]$", candidate):
        return None

    size = float(line.get("size") or 0)
    bold = bool(line.get("bold"))
    has_heading_marker = bool(
        re.match(r"^(\d+\.\d+(\.\d+)*|\d{1,2}\s+(?!.*\d)|[一二三四五六七八九十]+[、.．]|第[一二三四五六七八九十百\d]+[章节篇])\s*.+", candidate)
    )
    looks_sentence_like = bool(re.search(r"[\u3002\uff01\uff1f\uff0c,;；]", candidate))

    if size >= body_size + 3 and len(candidate) <= 50 and not looks_sentence_like:
        return 1
    if bold and size >= body_size + 1.2 and has_heading_marker:
        return 2
    if bold and has_heading_marker:
        return 2
    return None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _title_level(text: str) -> int | None:
    candidate = _clean_title(text)
    if len(candidate) > 80:
        return None
    for level, pattern in TITLE_PATTERNS:
        if pattern.match(candidate):
            return level
    return None


def _clean_title(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" \t\r\n:：")


def _format_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_tables(page, page_text: str, start_number: int) -> list[dict]:
    if not hasattr(page, "find_tables"):
        return []
    try:
        tables = page.find_tables()
    except Exception as exc:
        logger.debug("PDF table extraction failed: %s", exc)
        return []

    captions = _find_table_captions(page_text)
    results: list[dict] = []
    for index, table in enumerate(getattr(tables, "tables", []), start=1):
        try:
            rows = table.extract()
        except Exception:
            continue
        rows = [[str(cell or "").strip() for cell in row] for row in rows if row]
        if not rows:
            continue
        table_number = _caption_number(captions[index - 1]) if index - 1 < len(captions) else None
        if table_number is None:
            table_number = start_number + index - 1
        caption = captions[index - 1] if index - 1 < len(captions) else f"Table {table_number}"
        results.append(
            {
                "table_number": table_number,
                "caption": caption,
                "text": _format_table_context(table_number, caption, rows),
            }
        )
    return results


def _extract_text_tables(page_text: str, start_number: int) -> list[dict]:
    lines = [line.strip() for line in page_text.replace("\r", "\n").splitlines()]
    lines = [line for line in lines if line]
    results: list[dict] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not _is_table_caption(line):
            index += 1
            continue

        caption = line
        table_number = _caption_number(caption) or (start_number + len(results))
        collected = []
        cursor = index + 1
        while cursor < len(lines) and len(collected) < 24:
            candidate = lines[cursor]
            if _is_table_caption(candidate):
                break
            if _looks_like_heading(candidate) and collected:
                break
            if _looks_like_table_line(candidate):
                collected.append(candidate)
            elif collected:
                break
            cursor += 1

        if collected:
            rows = [_split_table_line(row) for row in collected]
            results.append(
                {
                    "table_number": table_number,
                    "caption": caption,
                    "text": _format_table_context(table_number, caption, rows),
                }
            )
            index = cursor
            continue

        index += 1
    return results


def _find_table_captions(text: str) -> list[str]:
    captions = []
    for line in text.replace("\r", "\n").splitlines():
        candidate = _format_text(line)
        if _is_table_caption(candidate):
            captions.append(candidate)
    return captions


def _is_table_caption(text: str) -> bool:
    return bool(re.match(
        r"^(表\s*[一二三四五六七八九十百\d]+|第\s*[一二三四五六七八九十百\d]+\s*(张表|个表|表)|table\s*\d+|tab\.\s*\d+)",
        text,
        re.I,
    ))


def _caption_number(text: str) -> int | None:
    digit = re.search(r"(?:表|第|table|tab\.)\s*(\d{1,3})", text, re.I)
    if digit:
        return int(digit.group(1))
    chinese = re.search(r"(?:表|第)\s*([一二三四五六七八九十])", text)
    if chinese:
        return _CHINESE_NUMBER_MAP.get(chinese.group(1))
    return None


def _looks_like_table_line(text: str) -> bool:
    if re.search(r"\s{2,}|\t|,|，|\|", text):
        return True
    tokens = text.split()
    has_number = bool(re.search(r"\d", text))
    return has_number and len(tokens) >= 2


def _looks_like_heading(text: str) -> bool:
    return len(text) < 80 and bool(re.match(r"^(\d+(\.\d+)*|[一二三四五六七八九十]+[、.．])\s*[\u4e00-\u9fffA-Za-z]", text))


def _split_table_line(text: str) -> list[str]:
    cells = re.split(r"\s{2,}|\t|\||,|，", text)
    return [cell.strip() for cell in cells if cell.strip()]


def _format_table_context(table_number: int, caption: str, rows: list[list[str]]) -> str:
    markdown = _rows_to_markdown(rows)
    compact_rows = []
    for row in rows[:30]:
        if row:
            compact_rows.append(" | ".join(row))
    compact = "\n".join(compact_rows)
    return (
        f"Table {table_number}\n"
        f"Caption: {caption}\n"
        f"Markdown:\n{markdown}\n\n"
        f"QA context: This is table {table_number}. Caption: {caption}. "
        f"Table content:\n{compact}"
    )


def _rows_to_markdown(rows: list[list[str]]) -> str:
    clean_rows = [[cell.strip() for cell in row] for row in rows if any(cell.strip() for cell in row)]
    if not clean_rows:
        return ""
    width = max(len(row) for row in clean_rows)
    normalized = [row + [""] * (width - len(row)) for row in clean_rows]
    header = normalized[0]
    body = normalized[1:] or [[""] * width]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def _ocr_page(page) -> str:
    try:
        pixmap = page.get_pixmap(matrix=__import__("fitz").Matrix(2, 2), alpha=False)
        return describe_image(pixmap.tobytes("png"), mime_type="image/png")
    except Exception as exc:
        logger.warning("Failed to OCR PDF page: %s", exc, exc_info=True)
        return ""
