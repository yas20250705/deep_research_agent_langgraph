"""
ロギング・可観測性機能

ロガーの設定とLangSmith連携
コンソールとファイルの両方にログを出力する。
"""

import logging
import os
from pathlib import Path
from typing import Optional

# プロジェクトルート（src/utils の2階層上）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_LOG_DIR = _PROJECT_ROOT / "logs"
_DEFAULT_LOG_FILE = _DEFAULT_LOG_DIR / "research_agent.log"


def setup_logger(name: str = "research_agent", level: int = logging.INFO) -> logging.Logger:
    """
    ロガーを設定（コンソール＋ファイル）。
    ルートロガーにファイルハンドラを追加するため、全モジュールのログがファイルに残る。
    
    Args:
        name: ロガー名
        level: ログレベル
    
    Returns:
        設定済みロガー
    """
    root = logging.getLogger()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # ルートロガーにファイルハンドラが既にあるか（同じパス）を判定
    log_path = os.environ.get("LOG_FILE")
    log_file = Path(log_path) if log_path else _DEFAULT_LOG_FILE
    _file_handler_key = getattr(setup_logger, "_file_handler_log_path", None)
    
    if _file_handler_key != str(log_file):
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
            root.setLevel(min(root.level, level))
            setup_logger._file_handler_log_path = str(log_file)
        except OSError as e:
            import warnings
            warnings.warn(f"ログファイルを開けません: {log_file}, {e}", UserWarning)
    
    # 名前付きロガーはルートに伝播するので、コンソールはルートに1本だけ追加
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root.handlers):
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(formatter)
        root.addHandler(console)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
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




