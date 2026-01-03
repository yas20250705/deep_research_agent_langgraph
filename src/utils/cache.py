"""
キャッシュ機能

検索結果やLLM応答をキャッシュしてパフォーマンスを向上
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any, TypeVar
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SimpleCache:
    """シンプルなインメモリキャッシュ"""
    
    def __init__(self, ttl: int = 3600):
        """
        初期化
        
        Args:
            ttl: Time To Live（秒）、デフォルトは1時間
        """
        self._cache: Dict[str, tuple[Any, float]] = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        キャッシュから値を取得
        
        Args:
            key: キャッシュキー
        
        Returns:
            キャッシュされた値、またはNone
        """
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        
        # TTLチェック
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            logger.debug(f"キャッシュが期限切れ: {key}")
            return None
        
        logger.debug(f"キャッシュヒット: {key}")
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        キャッシュに値を設定
        
        Args:
            key: キャッシュキー
            value: キャッシュする値
        """
        self._cache[key] = (value, time.time())
        logger.debug(f"キャッシュに保存: {key}")
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        self._cache.clear()
        logger.info("キャッシュをクリアしました")
    
    def size(self) -> int:
        """キャッシュサイズを取得"""
        return len(self._cache)


# グローバルキャッシュインスタンス
_search_cache = SimpleCache(ttl=3600)  # 1時間
_llm_cache = SimpleCache(ttl=1800)  # 30分


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    キャッシュキーを生成
    
    Args:
        prefix: プレフィックス
        *args: 位置引数
        **kwargs: キーワード引数
    
    Returns:
        キャッシュキー（ハッシュ）
    """
    # 引数をシリアライズ
    key_data = {
        "prefix": prefix,
        "args": args,
        "kwargs": kwargs
    }
    key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    
    # ハッシュ化
    return hashlib.sha256(key_string.encode()).hexdigest()


def cache_search_result(func):
    """
    検索結果をキャッシュするデコレータ
    
    Usage:
        @cache_search_result
        def search(query: str):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # キャッシュキーを生成
        cache_key = generate_cache_key("search", *args, **kwargs)
        
        # キャッシュから取得を試みる
        cached_result = _search_cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # キャッシュにない場合は実行
        result = func(*args, **kwargs)
        
        # キャッシュに保存
        _search_cache.set(cache_key, result)
        
        return result
    
    return wrapper


def cache_llm_response(func):
    """
    LLM応答をキャッシュするデコレータ
    
    Usage:
        @cache_llm_response
        def call_llm(prompt: str):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # キャッシュキーを生成
        cache_key = generate_cache_key("llm", *args, **kwargs)
        
        # キャッシュから取得を試みる
        cached_result = _llm_cache.get(cache_key)
        if cached_result is not None:
            logger.info("LLM応答をキャッシュから取得")
            return cached_result
        
        # キャッシュにない場合は実行
        result = func(*args, **kwargs)
        
        # キャッシュに保存
        _llm_cache.set(cache_key, result)
        
        return result
    
    return wrapper


def clear_all_caches():
    """すべてのキャッシュをクリア"""
    _search_cache.clear()
    _llm_cache.clear()
    logger.info("すべてのキャッシュをクリアしました")


def get_cache_stats() -> Dict[str, Any]:
    """キャッシュ統計情報を取得"""
    return {
        "search_cache_size": _search_cache.size(),
        "llm_cache_size": _llm_cache.size(),
        "search_cache_ttl": _search_cache.ttl,
        "llm_cache_ttl": _llm_cache.ttl
    }

