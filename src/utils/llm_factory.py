"""
LLMファクトリー

プロバイダーに応じて適切なLLMインスタンスを作成
"""

from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
import logging

logger = logging.getLogger(__name__)

# Geminiのインポート（オプション）
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("langchain-google-genaiがインストールされていません。Geminiは使用できません。")


def create_llm(
    provider: str,
    model: str,
    temperature: float = 0.3,
    api_key: Optional[str] = None
) -> BaseChatModel:
    """
    LLMインスタンスを作成
    
    Args:
        provider: プロバイダー名（"openai" または "gemini"）
        model: モデル名
        temperature: 温度パラメータ（0.0-1.0）
        api_key: APIキー
    
    Returns:
        BaseChatModel: LLMインスタンス
    
    Raises:
        ValueError: 不明なプロバイダーまたは必要なパッケージがインストールされていない場合
    """
    
    if provider == "openai":
        if not api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key
        )
    
    elif provider == "gemini":
        if not GEMINI_AVAILABLE:
            raise ValueError(
                "Geminiを使用するには langchain-google-genai パッケージが必要です。"
                "インストール: pip install langchain-google-genai"
            )
        if not api_key:
            raise ValueError("GEMINI_API_KEYが設定されていません")
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key
        )
    
    else:
        raise ValueError(f"不明なLLMプロバイダー: {provider}。'openai' または 'gemini' を指定してください。")


def get_llm_from_settings(settings, temperature: float = 0.3) -> BaseChatModel:
    """
    SettingsからLLMインスタンスを作成（便利関数）
    
    Args:
        settings: Settingsインスタンス
        temperature: 温度パラメータ
    
    Returns:
        BaseChatModel: LLMインスタンス
    """
    
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "openai":
        return create_llm(
            provider="openai",
            model=settings.OPENAI_MODEL,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY
        )
    
    elif provider == "gemini":
        return create_llm(
            provider="gemini",
            model=settings.GEMINI_MODEL,
            temperature=temperature,
            api_key=settings.GEMINI_API_KEY
        )
    
    else:
        raise ValueError(f"不明なLLMプロバイダー: {provider}")
