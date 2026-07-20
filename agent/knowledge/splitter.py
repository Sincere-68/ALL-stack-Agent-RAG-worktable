"""
文本切分模块
使用 LangChain RecursiveCharacterTextSplitter
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from agent.logger.logger import get_logger

logger = get_logger(__name__)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", "。", ".", " ", ""],
)


def split_text(text: str) -> list[str]:
    """将文本切分为 chunks"""
    chunks = splitter.split_text(text)
    logger.info("Split text into %d chunks", len(chunks))
    return chunks
