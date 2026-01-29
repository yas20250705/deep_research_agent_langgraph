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
    
    # LLMプロバイダー設定
    LLM_PROVIDER: str = "openai"  # "openai" / "gemini" / "mock"（開発・テスト用）
    
    # モックLLM設定（LLM_PROVIDER=mock のときのみ使用）
    MOCK_RESPONSE_DELAY: float = 0.1  # レスポンス遅延（秒）
    MOCK_LOG_PROMPTS: bool = False  # プロンプトをログ出力するか
    
    # OpenAI設定
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    
    # Gemini設定
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3-flash"  # 利用可能なモデル: gemini-pro, gemini-1.5-pro-latest, gemini-1.5-flash-latest, gemini-3-flash
    
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
    SUMMARY_MAX_LENGTH: int = 300  # URL要約の最大文字数（デフォルト300文字）
    
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

