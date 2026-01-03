"""
データベース接続管理

SQLAlchemyを使用したPostgreSQL接続
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator
from src.config.settings import Settings
from src.utils.logger import setup_logger

logger = setup_logger()

settings = Settings()
Base = declarative_base()

# データベースエンジン（遅延初期化）
_engine = None
_SessionLocal = None


def get_engine():
    """データベースエンジンを取得（シングルトン）"""
    global _engine
    
    if _engine is None:
        if not settings.DATABASE_URL:
            raise ValueError("DATABASE_URL環境変数が設定されていません")
        
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,  # 接続の有効性をチェック
            echo=False  # SQLログを出力するか（デバッグ時はTrue）
        )
        logger.info("データベースエンジンを作成しました")
    
    return _engine


def get_session_local():
    """セッションローカルを取得（シングルトン）"""
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("セッションローカルを作成しました")
    
    return _SessionLocal


def get_db_session() -> Generator[Session, None, None]:
    """
    データベースセッションを取得（依存性注入用）
    
    Yields:
        Session: SQLAlchemyセッション
    """
    if not settings.ENABLE_DB_PERSISTENCE:
        logger.warning("データベース永続化が無効です")
        return
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    データベースを初期化（テーブル作成）
    """
    if not settings.ENABLE_DB_PERSISTENCE:
        logger.warning("データベース永続化が無効です。スキップします。")
        return
    
    if not settings.DATABASE_URL:
        logger.warning("DATABASE_URLが設定されていません。スキップします。")
        return
    
    try:
        engine = get_engine()
        # すべてのテーブルを作成
        Base.metadata.create_all(bind=engine)
        logger.info("データベーステーブルを作成しました")
    except Exception as e:
        logger.error(f"データベース初期化エラー: {e}", exc_info=True)
        raise

