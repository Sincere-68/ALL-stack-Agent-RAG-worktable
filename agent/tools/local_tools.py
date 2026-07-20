import ast
import operator
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Only numeric expressions are supported.")


@tool("calculator")
def calculator(expression: str) -> str:
    """Evaluate a basic numeric expression, such as '12 * (3 + 4)'."""
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_safe_eval(tree))
    except Exception as error:
        return f"Calculation failed: {error}"


@tool("knowledge_search")
def knowledge_search(query: str) -> str:
    """Search the local RAG knowledge base. This does not require internet access."""
    try:
        from agent.knowledge.vectorstore import search

        results = search(query, k=5)
    except Exception as error:
        return f"Knowledge search failed: {error}"

    if not results:
        return "No relevant knowledge base content was found."
    return "\n\n".join(results)


@tool("list_knowledge_documents")
def list_knowledge_documents() -> str:
    """List documents that have been indexed in the local knowledge base."""
    try:
        from agent.knowledge.vectorstore import list_documents

        docs = list_documents()
    except Exception as error:
        return f"Failed to list knowledge documents: {error}"

    if not docs:
        return "No documents are currently indexed."
    return "\n".join(
        f"- {doc.get('filename', 'unknown')} ({len(doc.get('chunks', []))} chunks)"
        for doc in docs
    )


@tool("current_time")
def current_time(timezone: str = "Asia/Shanghai") -> str:
    """Return the current time for a timezone. Default is Asia/Shanghai."""
    try:
        now = datetime.now(ZoneInfo(timezone))
    except Exception:
        timezone = "Asia/Shanghai"
        now = datetime.now(ZoneInfo(timezone))
    return now.strftime(f"%Y-%m-%d %H:%M:%S {timezone}")


LOCAL_TOOLS = [
    knowledge_search,
    list_knowledge_documents,
    calculator,
    current_time,
]
