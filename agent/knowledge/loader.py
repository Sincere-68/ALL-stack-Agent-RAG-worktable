"""
文件加载器
支持 PDF / DOCX / TXT / MD / CSV / XLSX 格式
"""
from pathlib import Path
from agent.logger.logger import get_logger

logger = get_logger(__name__)


def load_file(file_path: str) -> str:
    """根据文件扩展名加载文本内容"""
    path = Path(file_path)
    suffix = path.suffix.lower()

    loaders = {
        ".pdf": _load_pdf,
        ".docx": _load_docx,
        ".txt": _load_text,
        ".md": _load_text,
        ".csv": _load_csv,
        ".xlsx": _load_xlsx,
    }

    loader = loaders.get(suffix)
    if not loader:
        raise ValueError(f"Unsupported file format: {suffix}")

    logger.info("Loading file: %s (type: %s)", path.name, suffix)
    return loader(path)


def _load_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return text


def _load_docx(path: Path) -> str:
    import docx2txt
    return docx2txt.process(str(path))


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _load_csv(path: Path) -> str:
    import pandas as pd
    df = pd.read_csv(str(path))
    return df.to_string(index=False)


def _load_xlsx(path: Path) -> str:
    import pandas as pd
    df = pd.read_excel(str(path))
    return df.to_string(index=False)
