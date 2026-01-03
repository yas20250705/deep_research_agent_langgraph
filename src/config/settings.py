"""
設定管理（Pydantic Settings）

環境変数から設定を読み込む
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import os

# プロジェクトルートを取得（このファイルから3階層上）
_project_root = Path(__file__).parent.parent.parent
_env_file = _project_root / ".env"


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # OpenAI設定
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    
    # Tavily設定
    TAVILY_API_KEY: str = ""
    
    # Redis設定（オプション）
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # PostgreSQL設定（オプション）
    DATABASE_URL: Optional[str] = None  # postgresql://user:password@localhost/dbname
    ENABLE_DB_PERSISTENCE: bool = False  # データベース永続化を有効化するか
    
    # 制限設定
    MAX_ITERATIONS: int = 5
    MAX_SEARCH_RESULTS: int = 10
    MAX_RESULTS_PER_QUERY: int = 5
    
    # LangSmith設定（オプション）
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "research-agent"
    
    # API認証設定（オプション）
    ALLOWED_API_KEYS: str = ""  # カンマ区切りで複数のAPIキーを指定
    ENABLE_API_AUTH: bool = False  # API認証を有効化するか
    
    # レート制限設定
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60  # 1分あたりのリクエスト数
    
    # セキュリティ設定
    ENABLE_RATE_LIMIT: bool = True  # レート制限を有効化するか
    
    model_config = {
        "env_file": str(_env_file) if _env_file.exists() else None,
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"  # 追加のフィールドを無視
    }
    
    def __init__(self, **kwargs):
        # .envファイルを明示的に読み込む（python-dotenvを使用）
        try:
            from dotenv import load_dotenv
            if _env_file.exists():
                load_dotenv(_env_file, override=False)
            else:
                # 親ディレクトリの.envファイルも確認
                parent_env = _project_root.parent / ".env"
                if parent_env.exists():
                    load_dotenv(parent_env, override=False)
        except ImportError:
            pass  # python-dotenvがインストールされていない場合はスキップ
        
        super().__init__(**kwargs)

