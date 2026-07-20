import threading

from fastapi import APIRouter

from agent.memory.database import add_message, create_conversation, get_messages
from agent.runner import run_agent_detailed
from backend.schemas import ChatRequest, ChatResponse

router = APIRouter()

_conversation_locks: dict[int, threading.Lock] = {}
_conversation_locks_guard = threading.Lock()


def _get_conversation_lock(conv_id: int) -> threading.Lock:
    with _conversation_locks_guard:
        if conv_id not in _conversation_locks:
            _conversation_locks[conv_id] = threading.Lock()
        return _conversation_locks[conv_id]


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    conv_id = req.conversation_id
    if not conv_id:
        title = req.prompt[:30] + ("..." if len(req.prompt) > 30 else "")
        conv = create_conversation(title)
        conv_id = conv["id"]

    with _get_conversation_lock(conv_id):
        history = get_messages(conv_id)
        add_message(conv_id, "user", req.prompt)

        result = run_agent_detailed(req.prompt, history=history, tool_hint=req.tool_hint)
        response = result["response"]
        add_message(conv_id, "assistant", response)

    return {
        "response": response,
        "conversation_id": conv_id,
        "sources": result.get("sources", []),
    }
