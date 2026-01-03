"""
CRUD操作

データベースの基本的な操作
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
from .models import Conversation, Message, ResearchHistory
from src.utils.logger import setup_logger

logger = setup_logger()


# ==================== Conversation CRUD ====================

def create_conversation(db: Session, conversation_id: str, title: Optional[str] = None) -> Conversation:
    """会話を作成"""
    conversation = Conversation(
        conversation_id=conversation_id,
        title=title,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    logger.info(f"会話を作成しました: {conversation_id}")
    return conversation


def get_conversation(db: Session, conversation_id: str) -> Optional[Conversation]:
    """会話を取得"""
    return db.query(Conversation).filter(Conversation.conversation_id == conversation_id).first()


def get_all_conversations(db: Session, limit: int = 50, offset: int = 0) -> List[Conversation]:
    """すべての会話を取得（新しい順）"""
    return db.query(Conversation).order_by(Conversation.updated_at.desc()).offset(offset).limit(limit).all()


def update_conversation(db: Session, conversation_id: str, title: Optional[str] = None) -> Optional[Conversation]:
    """会話を更新"""
    conversation = get_conversation(db, conversation_id)
    if conversation:
        if title is not None:
            conversation.title = title
        conversation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(conversation)
        logger.info(f"会話を更新しました: {conversation_id}")
    return conversation


def delete_conversation(db: Session, conversation_id: str) -> bool:
    """会話を削除"""
    conversation = get_conversation(db, conversation_id)
    if conversation:
        db.delete(conversation)
        db.commit()
        logger.info(f"会話を削除しました: {conversation_id}")
        return True
    return False


# ==================== Message CRUD ====================

def add_message(db: Session, conversation_id: str, role: str, content: str) -> Message:
    """メッセージを追加"""
    # 会話が存在しない場合は作成
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        conversation = create_conversation(db, conversation_id)
    
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        created_at=datetime.utcnow()
    )
    db.add(message)
    
    # 会話の更新時刻を更新
    conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    return message


def get_messages(db: Session, conversation_id: str, limit: int = 100) -> List[Message]:
    """会話のメッセージを取得（時系列順）"""
    return db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).limit(limit).all()


# ==================== ResearchHistory CRUD ====================

def save_research_history(
    db: Session,
    research_id: str,
    theme: str,
    status: str,
    title: Optional[str] = None,
    metadata_json: Optional[Dict] = None
) -> ResearchHistory:
    """リサーチ履歴を保存または更新"""
    research = db.query(ResearchHistory).filter(ResearchHistory.research_id == research_id).first()
    
    if research:
        # 更新
        research.theme = theme
        research.status = status
        research.updated_at = datetime.utcnow()
        if title is not None:
            research.title = title
        if metadata_json is not None:
            research.metadata_json = metadata_json
        if status == "completed":
            research.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(research)
        logger.info(f"リサーチ履歴を更新しました: {research_id}")
    else:
        # 新規作成
        research = ResearchHistory(
            research_id=research_id,
            theme=theme,
            title=title,
            status=status,
            metadata_json=metadata_json,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        if status == "completed":
            research.completed_at = datetime.utcnow()
        db.add(research)
        db.commit()
        db.refresh(research)
        logger.info(f"リサーチ履歴を作成しました: {research_id}")
    
    return research


def get_research_history(db: Session, research_id: str) -> Optional[ResearchHistory]:
    """リサーチ履歴を取得"""
    return db.query(ResearchHistory).filter(ResearchHistory.research_id == research_id).first()


def get_all_research_history(db: Session, limit: int = 50, offset: int = 0) -> List[ResearchHistory]:
    """すべてのリサーチ履歴を取得（新しい順）"""
    return db.query(ResearchHistory).order_by(ResearchHistory.updated_at.desc()).offset(offset).limit(limit).all()

