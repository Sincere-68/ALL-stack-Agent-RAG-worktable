from fastapi import APIRouter, HTTPException
from backend.schemas import ConversationCreate, ConversationOut, MessageOut
from agent.memory.database import (
    create_conversation, list_conversations, delete_conversation, get_messages,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def get_conversations():
    return list_conversations()


@router.post("", response_model=ConversationOut)
def new_conversation(req: ConversationCreate):
    return create_conversation(req.title)


@router.delete("/{conv_id}")
def remove_conversation(conv_id: int):
    delete_conversation(conv_id)
    return {"message": "deleted"}


@router.get("/{conv_id}/messages", response_model=list[MessageOut])
def get_conversation_messages(conv_id: int):
    return get_messages(conv_id)
