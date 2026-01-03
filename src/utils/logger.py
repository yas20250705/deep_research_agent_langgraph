"""
ロギング・可観測性機能

ロガーの設定とLangSmith連携
"""

import logging
import os
from typing import Optional


def setup_logger(name: str = "research_agent", level: int = logging.INFO) -> logging.Logger:
    """
    ロガーを設定
    
    Args:
        name: ロガー名
        level: ログレベル
    
    Returns:
        設定済みロガー
    """
    logger = logging.getLogger(name)
    
    # 既にハンドラーが設定されている場合はスキップ
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # コンソールハンドラー
    handler = logging.StreamHandler()
    handler.setLevel(level)
    
    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


def setup_langsmith() -> None:
    """
    LangSmithのトレーシングを設定
    
    環境変数から設定を読み込む
    """
    settings = None
    try:
        from src.config.settings import Settings
        settings = Settings()
    except Exception:
        # 設定が読み込めない場合は環境変数から直接読み込む
        pass
    
    if settings and settings.LANGCHAIN_TRACING_V2:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
        if settings.LANGCHAIN_API_KEY:
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    elif os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
        # 環境変数から直接設定
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        if not os.getenv("LANGCHAIN_ENDPOINT"):
            os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        if not os.getenv("LANGCHAIN_PROJECT"):
            os.environ["LANGCHAIN_PROJECT"] = "research-agent"




