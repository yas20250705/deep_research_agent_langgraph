"""
Researcherノード実装

Web検索と情報収集を行うノード
"""

import logging
from typing import List
from functools import partial
from langchain_core.messages import AIMessage
from src.graph.state import ResearchState
from src.schemas.data_models import SearchResult
from src.tools.search_tool import tavily_search_tool
from src.config.settings import Settings
from src.utils.error_handler import handle_node_errors
from src.utils.parallel import run_parallel_sync

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
    
    plan = state.get("task_plan")
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
    
    # 検索結果を処理
    for query, search_results in zip(plan.search_queries, search_results_list):
        if not search_results:
            logger.warning(f"検索結果が空: クエリ={query}")
            continue
        
        # SearchResultに変換
        for result in search_results:
            try:
                search_result = SearchResult(
                    title=result.get("title", ""),
                    summary=result.get("content", "")[:2000],  # 要約を2000文字に制限
                    url=result.get("url", ""),
                    source="tavily",
                    published_date=result.get("published_date"),
                    relevance_score=result.get("score", 0.0)
                )
                
                # 重複チェック
                if search_result.url not in existing_urls:
                    new_results.append(search_result)
                    existing_urls.add(search_result.url)
                    
            except Exception as e:
                logger.warning(f"SearchResult変換エラー: {e}, 結果={result}")
                continue
    
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

