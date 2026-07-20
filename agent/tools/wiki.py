"""
Wikipedia 查询工具
"""
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from agent.logger.logger import get_logger

logger = get_logger(__name__)


def get_wiki_tool():
    """获取 Wikipedia 查询工具"""
    try:
        api_wrapper = WikipediaAPIWrapper(top_k_results=3, load_all_available_meta=False)
        tool = WikipediaQueryRun(api_wrapper=api_wrapper)
        logger.info("Wikipedia tool initialized")
        return tool
    except Exception as e:
        logger.warning("Wikipedia tool unavailable: %s", e)
        return None
