from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from agent.state.agent_state import AgentState
from agent.nodes.llm_node import llm_node, _tools
from agent.logger.logger import get_logger
from agent.exceptions.custom_exception import CustomException

logger = get_logger(__name__)


def _should_continue(state):
    """判断 LLM 是否请求调用工具"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


def build_graph():
    try:
        logger.info("Graph builder invoked")

        graph = StateGraph(AgentState)

        # 添加节点
        graph.add_node("llm", llm_node)
        graph.add_node("tools", ToolNode(_tools))

        # 设置入口
        graph.set_entry_point("llm")

        # 条件边：LLM 返回 tool_calls → 走 tools 节点，否则结束
        graph.add_conditional_edges("llm", _should_continue, {
            "tools": "tools",
            END: END,
        })

        # tools 节点执行完后回到 LLM（可能还需要继续调用工具）
        graph.add_edge("tools", "llm")

        return graph.compile()

    except Exception as e:
        logger.error("Graph builder failed", exc_info=True)
        raise CustomException(e)
