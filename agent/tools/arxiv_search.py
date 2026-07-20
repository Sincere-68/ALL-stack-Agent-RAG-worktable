"""
ArXiv 论文搜索工具
"""
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from langchain_community.utilities import ArxivAPIWrapper
from agent.logger.logger import get_logger

logger = get_logger(__name__)


def get_arxiv_tool():
    """获取 ArXiv 搜索工具"""
    try:
        api_wrapper = ArxivAPIWrapper(top_k_results=3, load_max_docs=3)
        tool = ArxivQueryRun(api_wrapper=api_wrapper)
        logger.info("ArXiv tool initialized")
        return tool
    except Exception as e:
        logger.warning("ArXiv tool unavailable: %s", e)
        return None
