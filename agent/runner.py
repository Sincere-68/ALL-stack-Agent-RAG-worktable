import os

from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.messages import AIMessage

from agent.exceptions.custom_exception import CustomException
from agent.graph.builder import build_graph
from agent.knowledge.vectorstore import search_with_sources as kb_search_with_sources
from agent.logger.logger import get_logger
from agent.prompts.system import SYSTEM_PROMPT

logger = get_logger(__name__)
graph = build_graph()

load_dotenv()


def _is_llm_connection_error(error: Exception) -> bool:
    current = error
    while current:
        name = current.__class__.__name__
        text = str(current).lower()
        if name in {"APIConnectionError", "APITimeoutError", "RemoteProtocolError", "ConnectError", "ReadTimeout"}:
            return True
        if "connection error" in text or "server disconnected" in text or "request timed out" in text:
            return True
        current = current.__cause__ or current.__context__
    return False


def run_agent(prompt: str, history: list[dict] = None, tool_hint: str = None) -> str:
    return run_agent_detailed(prompt, history=history, tool_hint=tool_hint)["response"]


def run_agent_detailed(prompt: str, history: list[dict] = None, tool_hint: str = None) -> dict:
    try:
        logger.info("Agent invoked with prompt: %s", prompt)

        if tool_hint == "web_search" and (
            not os.getenv("TAVILY_API_KEY")
            or os.getenv("ENABLE_ONLINE_TOOLS", "").strip().lower() not in {"1", "true", "yes", "on"}
        ):
            return {
                "response": (
                    "联网搜索工具未配置：请在后端 .env 文件中添加 TAVILY_API_KEY，"
                    "并设置 ENABLE_ONLINE_TOOLS=1，然后重启后端服务。"
                    "默认可直接使用知识库检索、文档列表、计算器和当前时间等本地工具。"
                ),
                "sources": [],
            }

        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        try:
            kb_payload = kb_search_with_sources(prompt, k=3)
        except Exception:
            logger.warning("Knowledge base search failed; continuing without KB context", exc_info=True)
            kb_payload = {"contexts": [], "sources": []}

        kb_results = kb_payload["contexts"]
        kb_sources = kb_payload["sources"]
        if kb_results:
            context = "\n\n".join(kb_results)
            messages.append(
                SystemMessage(
                    content=(
                        "以下是与用户问题相关的知识库内容。回答时优先依据这些内容，"
                        "如果内容不足，请明确说明不确定。\n\n"
                        f"{context}"
                    )
                )
            )

        if tool_hint:
            messages.append(SystemMessage(content=f"用户希望你使用 {tool_hint} 工具来回答这个问题。"))

        if history:
            for msg in history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=prompt))

        system_contents = [
            msg.content for msg in messages if isinstance(msg, SystemMessage)
        ]
        non_system_messages = [
            msg for msg in messages if not isinstance(msg, SystemMessage)
        ]
        messages = [
            SystemMessage(content="\n\n".join(system_contents)),
            *non_system_messages,
        ]

        result = graph.invoke({
            "messages": messages,
            "tool_hint": tool_hint,
        })

        return {
            "response": result["messages"][-1].content,
            "sources": kb_sources,
        }

    except Exception as e:
        logger.error("Agent execution failed", exc_info=True)
        if _is_llm_connection_error(e):
            return {
                "response": (
                    "LLM 服务连接失败。请检查 LLM_BASE_URL、API key、代理或网络连接，"
                    "稍后再试。"
                ),
                "sources": [],
            }
        raise CustomException(e)
