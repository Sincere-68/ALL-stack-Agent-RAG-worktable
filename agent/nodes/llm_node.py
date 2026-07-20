import os

from agent.llm.llm_factory import get_llm
from agent.tools.local_tools import LOCAL_TOOLS
from agent.logger.logger import get_logger
from agent.exceptions.custom_exception import CustomException

logger = get_logger(__name__)

llm = get_llm()

_tools = list(LOCAL_TOOLS)


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _load_optional_online_tools():
    if not _env_enabled("ENABLE_ONLINE_TOOLS"):
        logger.info("Online tools disabled. Set ENABLE_ONLINE_TOOLS=1 to enable web/wiki/arxiv tools.")
        return

    if os.getenv("TAVILY_API_KEY"):
        from agent.tools.web_search import get_web_search_tool

        web_tool = get_web_search_tool()
        if web_tool:
            _tools.append(web_tool)

    if _env_enabled("ENABLE_WIKIPEDIA_TOOL"):
        from agent.tools.wiki import get_wiki_tool

        wiki_tool = get_wiki_tool()
        if wiki_tool:
            _tools.append(wiki_tool)

    if _env_enabled("ENABLE_ARXIV_TOOL"):
        from agent.tools.arxiv_search import get_arxiv_tool

        arxiv_tool = get_arxiv_tool()
        if arxiv_tool:
            _tools.append(arxiv_tool)


_load_optional_online_tools()

logger.info("Loaded %d tools: %s", len(_tools), [tool.name for tool in _tools])


def _is_tool_calling_unsupported(error: Exception) -> bool:
    current = error
    while current:
        text = str(current).lower()
        if "function call is not supported" in text:
            return True
        if "tool" in text and "not supported" in text:
            return True
        current = current.__cause__ or current.__context__
    return False


def llm_node(state):
    try:
        logger.info("LLM node invoked")

        llm_with_tools = llm.bind_tools(_tools)
        try:
            response = llm_with_tools.invoke(state["messages"])
        except Exception as tool_error:
            if not _is_tool_calling_unsupported(tool_error):
                raise
            logger.warning(
                "Current model does not support tool/function calling; retrying without tools"
            )
            response = llm.invoke(state["messages"])

        return {
            "messages": [response],
        }

    except Exception as error:
        logger.error("LLM node failed", exc_info=True)
        raise CustomException(error)
