"""
Researcherノード実装

Web検索と情報収集を行うノード
"""

import logging
from typing import List, Optional
from functools import partial
from langchain_core.messages import AIMessage
from src.graph.state import ResearchState
from src.schemas.data_models import SearchResult, ensure_research_plan
from src.tools.search_tool import tavily_search_tool
from src.config.settings import Settings
from src.utils.error_handler import handle_node_errors
from src.utils.parallel import run_parallel_sync
from src.utils.summarizer import summarize_url_content

logger = logging.getLogger(__name__)

def get_settings() -> Settings:
    """Settingsインスタンスを取得（遅延初期化）"""
    return Settings()


def _execute_search(query: str = None, max_results: int = 5) -> List[dict]:
    """
    単一の検索クエリを実行（並列実行用）
    
    Args:
        query: 検索クエリ
        max_results: 最大結果数
    
    Returns:
        検索結果のリスト
    """
    if query is None:
        return []
    
    try:
        search_results = tavily_search_tool.invoke({
            "query": query,
            "max_results": max_results
        })
        return search_results if search_results else []
    except ValueError as e:
        # APIキーが設定されていない場合など、設定エラーは一度だけログに記録
        error_msg = str(e)
        if "TAVILY_API_KEY" in error_msg:
            logger.warning(f"検索スキップ（APIキー未設定）: クエリ={query}")
        else:
            logger.error(f"検索エラー（設定エラー）: クエリ={query}, エラー={e}")
        return []
    except Exception as e:
        # その他のエラー（ネットワークエラーなど）はリトライ後にログに記録
        logger.error(f"検索エラー（クエリ: {query}）: {e}")
        return []


def _create_search_result_with_summary(
    result: dict,
    settings: Settings,
    existing_urls: set
) -> Optional[SearchResult]:
    """
    検索結果からSearchResultを作成（要約を含む、並列実行用）
    
    Args:
        result: 検索結果の辞書
        settings: Settingsインスタンス
        existing_urls: 既存URLのセット（重複チェック用）
    
    Returns:
        SearchResult、またはNone（重複またはエラーの場合）
    """
    try:
        # URLのコンテンツを取得
        content = result.get("content", "")
        url = result.get("url", "")
        
        # 重複チェック（早期リターン）
        if url in existing_urls:
            return None
        
        # LLMで要約を生成
        try:
            summary = summarize_url_content(
                content=content,
                url=url,
                settings=settings,
                max_length=settings.SUMMARY_MAX_LENGTH
            )
        except Exception as e:
            # 要約が失敗した場合は元のコンテンツの先頭部分を使用
            logger.warning(f"要約失敗、フォールバック使用: URL={url}, エラー={e}")
            summary = content[:settings.SUMMARY_MAX_LENGTH] if len(content) > settings.SUMMARY_MAX_LENGTH else content
        
        search_result = SearchResult(
            title=result.get("title", ""),
            summary=summary,
            url=url,
            source="tavily",
            published_date=result.get("published_date"),
            relevance_score=result.get("score", 0.0)
        )
        
        return search_result
        
    except Exception as e:
        logger.warning(f"SearchResult作成エラー: {e}, 結果={result}")
        return None


@handle_node_errors
def researcher_node(state: ResearchState) -> ResearchState:
    """
    Researcherノード: Web検索と情報収集
    
    処理ステップ:
    1. task_planから検索クエリを取得
    2. 各クエリに対してTavily検索を実行
    3. 検索結果をSearchResultモデルに変換
    4. 重複除去（URLベース）
    5. research_dataに追加
    6. メッセージに結果を記録
    
    Args:
        state: 現在のステート
    
    Returns:
        更新されたステート
    """
    
    plan = ensure_research_plan(state.get("task_plan"))
    if plan is None:
        logger.error("task_planが設定されていません")
        state["messages"].append(
            AIMessage(content="エラー: 調査計画が設定されていません")
        )
        state["next_action"] = "end"
        return state
    
    # 既存URLのセット（重複除去用）
    existing_urls = {r.url for r in state.get("research_data", [])}
    
    new_results = []
    
    # 設定を取得
    settings = get_settings()
    
    # 並列検索を実行
    search_tasks = [
        partial(_execute_search, query=query, max_results=settings.MAX_RESULTS_PER_QUERY)
        for query in plan.search_queries
    ]
    
    logger.info(f"並列検索を開始: {len(search_tasks)}件のクエリ")
    search_results_list = run_parallel_sync(search_tasks, max_workers=min(len(search_tasks), 5))
    
    # すべての検索結果を収集
    all_search_results = []
    for query, search_results in zip(plan.search_queries, search_results_list):
        if not search_results:
            logger.warning(f"検索結果が空: クエリ={query}")
            continue
        all_search_results.extend(search_results)
    
    # 重複を事前に除去（URLベース）
    unique_results = []
    seen_urls = set()
    for result in all_search_results:
        url = result.get("url", "")
        if url and url not in seen_urls and url not in existing_urls:
            unique_results.append(result)
            seen_urls.add(url)
    
    logger.info(f"要約処理を開始: {len(unique_results)}件のURL")
    
    # 要約処理を並列実行
    if unique_results:
        summary_tasks = [
            partial(_create_search_result_with_summary, result=result, settings=settings, existing_urls=existing_urls)
            for result in unique_results
        ]
        # 要約処理はLLM API呼び出しが多いため、並列数を制限（API制限を考慮）
        max_summary_workers = min(len(summary_tasks), 5)  # 最大5並列
        summary_results = run_parallel_sync(summary_tasks, max_workers=max_summary_workers)
        
        # 結果をフィルタリング（Noneを除外）
        for search_result in summary_results:
            if search_result is not None:
                new_results.append(search_result)
                existing_urls.add(search_result.url)
    
    # 結果を追加
    current_research_data = state.get("research_data", [])
    state["research_data"] = current_research_data + new_results
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    
    # サマリーメッセージ
    total_count = len(state["research_data"])
    summary = f"検索完了: {len(new_results)}件の新しい結果を追加しました（合計: {total_count}件）"
    state["messages"].append(AIMessage(content=summary))
    
    logger.info(f"Researcher実行完了: 新規結果={len(new_results)}件, 合計={total_count}件")
    
    return state

