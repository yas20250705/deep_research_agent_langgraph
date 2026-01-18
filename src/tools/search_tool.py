"""
Tavily検索ツール

Web検索を実行するツール
"""

try:
    # 新しいlangchain-tavilyパッケージを優先的に使用
    from langchain_tavily import TavilySearch
    TAVILY_NEW_API = True
except ImportError:
    # フォールバック: 古いAPIを使用
    from langchain_community.tools.tavily_search import TavilySearchResults
    TAVILY_NEW_API = False
    import warnings
    # 非推奨警告を抑制
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain_community.tools.tavily_search")

from langchain_core.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type
from typing import List, Dict, Any
import os
import logging
from src.utils.cache import cache_search_result

logger = logging.getLogger(__name__)


@tool
@cache_search_result
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_not_exception_type(ValueError),
    reraise=True
)
def tavily_search_tool(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Tavily Search APIを使用してWeb検索を実行
    
    Args:
        query: 検索クエリ
        max_results: 最大結果数（1-20推奨）
    
    Returns:
        検索結果のリスト
    
    Raises:
        ValueError: クエリが空の場合、またはmax_resultsが範囲外の場合、またはAPIキーが設定されていない場合
        Exception: Tavily API呼び出しエラー
    """
    
    if not query or not query.strip():
        raise ValueError("検索クエリが空です")
    
    if max_results < 1 or max_results > 20:
        raise ValueError("max_resultsは1-20の範囲で指定してください")
    
    # APIキーの確認
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        error_msg = (
            "TAVILY_API_KEY環境変数が設定されていません。"
            "検索機能を使用するには、環境変数にTAVILY_API_KEYを設定してください。"
            "例: export TAVILY_API_KEY='your-api-key'"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Tavilyツール初期化
    try:
        if TAVILY_NEW_API:
            # 新しいAPIを使用
            tavily = TavilySearch(
                max_results=max_results,
                api_key=api_key
            )
            # 新しいAPIは辞書形式で結果を返す: {"query": ..., "results": [...]}
            search_response = tavily.invoke({"query": query})
            
            # 結果形式を変換（古いAPI形式に合わせる）
            if isinstance(search_response, dict) and "results" in search_response:
                # 新しいAPIの結果形式: {"results": [{"url": ..., "title": ..., "content": ..., "score": ...}, ...]}
                raw_results = search_response.get("results", [])
                results = []
                for item in raw_results:
                    # 古いAPI形式に変換: {"url": ..., "title": ..., "content": ..., "score": ...}
                    result = {
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score", 0.0)
                    }
                    # published_dateがあれば追加
                    if "published_date" in item:
                        result["published_date"] = item["published_date"]
                    results.append(result)
            elif isinstance(search_response, list):
                # 既にリスト形式の場合
                results = search_response
            else:
                # 予期しない形式の場合
                logger.warning(f"予期しないTavily結果形式: {type(search_response)}")
                results = []
        else:
            # 古いAPIを使用（フォールバック）
            tavily = TavilySearchResults(
                max_results=max_results,
                api_key=api_key
            )
            # 検索実行
            results = tavily.invoke({"query": query})
        
        logger.info(f"Tavily検索完了: クエリ='{query}', 結果数={len(results)}")
        
        return results
        
    except ValueError as e:
        # ValueErrorは再スロー（リトライしない）
        logger.error(f"Tavily検索エラー（設定エラー）: クエリ='{query}', エラー={str(e)}")
        raise
    except Exception as e:
        logger.error(f"Tavily検索エラー: クエリ='{query}', エラー={str(e)}")
        raise

