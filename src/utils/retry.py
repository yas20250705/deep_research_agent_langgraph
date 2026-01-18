"""
リトライロジック

LLM呼び出しと検索API用のリトライデコレータ
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from typing import Callable, Any, Tuple
import openai
import requests
import logging

logger = logging.getLogger(__name__)

# Geminiエラーのインポート（オプション）
try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    GEMINI_ERRORS_AVAILABLE = True
except ImportError:
    GEMINI_ERRORS_AVAILABLE = False
    # フォールバック: 一般的な例外クラスを使用
    class google_exceptions:
        class GoogleAPIError(Exception):
            pass


def call_llm_with_retry(llm_func: Callable, *args, **kwargs) -> Any:
    """
    LLM呼び出し（リトライ付き）
    
    Args:
        llm_func: LLM呼び出し関数
        *args: 位置引数
        **kwargs: キーワード引数
    
    Returns:
        LLMの応答
    """
    
    # リトライ対象のエラーを定義
    retry_exceptions: Tuple = (openai.APIError, openai.APIConnectionError, openai.RateLimitError)
    
    # Geminiエラーも追加（利用可能な場合）
    if GEMINI_ERRORS_AVAILABLE:
        try:
            # Google APIのエラーを追加（一般的なエラーは含めない）
            retry_exceptions = retry_exceptions + (
                google_exceptions.GoogleAPIError,
            )
        except AttributeError:
            pass
    
    @retry(
        stop=stop_after_attempt(5),  # リトライ回数を3→5に増加
        wait=wait_exponential(multiplier=2, min=8, max=60),  # 待機時間を延長（最小8秒、最大60秒）
        retry=retry_if_exception_type(retry_exceptions)
    )
    def _retry_wrapper():
        return llm_func(*args, **kwargs)
    
    return _retry_wrapper()


def search_with_retry(search_func: Callable, *args, **kwargs) -> Any:
    """
    検索実行（リトライ付き）
    
    Args:
        search_func: 検索関数
        *args: 位置引数
        **kwargs: キーワード引数
    
    Returns:
        検索結果
    """
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def _retry_wrapper():
        return search_func(*args, **kwargs)
    
    return _retry_wrapper()



