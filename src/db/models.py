"""
データベースモデル定義

SQLAlchemyモデル
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Conversation(Base):
    """会話履歴テーブル"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # リレーション
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, conversation_id={self.conversation_id}, title={self.title})>"


class Message(Base):
    """メッセージテーブル"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(255), ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # リレーション
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, content_length={len(self.content)})>"


class ResearchHistory(Base):
    """リサーチ履歴テーブル"""
    __tablename__ = "research_history"
    
    id = Column(Integer, primary_key=True, index=True)
    research_id = Column(String(255), unique=True, index=True, nullable=False)
    theme = Column(Text, nullable=False)
    title = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)  # "started", "processing", "completed", "failed", "interrupted"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # メタデータ（JSON形式で保存）
    metadata_json = Column(JSON, nullable=True)  # statistics, plan等
    
    def __repr__(self):
        return f"<ResearchHistory(id={self.id}, research_id={self.research_id}, theme={self.theme[:50]})>"

