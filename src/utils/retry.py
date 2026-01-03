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
from typing import Callable, Any
import openai
import requests
import logging

logger = logging.getLogger(__name__)


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
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError, openai.RateLimitError))
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



