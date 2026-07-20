"""
Tavily 网络搜索工具
"""
from agent.logger.logger import get_logger

logger = get_logger(__name__)


def get_web_search_tool():
    """获取 Tavily 搜索工具"""
    try:
        from langchain_tavily import TavilySearch
        tool = TavilySearch(max_results=5)
        tool.name = "web_search"
        tool.description = "Search the internet for current information."
        logger.info("Tavily search tool initialized")
        return tool
    except Exception as e:
        logger.warning("Tavily search unavailable: %s", e)
        from langchain_core.tools import tool

        @tool("web_search")
        def unavailable_web_search(query: str) -> str:
            """Search the internet for current information."""
            return (
                "Web search is unavailable because TAVILY_API_KEY is not configured. "
                "Add TAVILY_API_KEY to the backend .env file and restart the server."
            )

        return unavailable_web_search
