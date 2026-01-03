"""
データベースモジュール

PostgreSQLを使用した会話履歴の永続化
"""

from .database import get_db_session, init_db
from .models import Conversation, Message, ResearchHistory
from .crud import (
    create_conversation,
    get_conversation,
    get_all_conversations,
    update_conversation,
    delete_conversation,
    add_message,
    get_messages,
    save_research_history,
    get_research_history,
    get_all_research_history
)

__all__ = [
    "get_db_session",
    "init_db",
    "Conversation",
    "Message",
    "ResearchHistory",
    "create_conversation",
    "get_conversation",
    "get_all_conversations",
    "update_conversation",
    "delete_conversation",
    "add_message",
    "get_messages",
    "save_research_history",
    "get_research_history",
    "get_all_research_history",
]

