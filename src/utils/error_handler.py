"""
エラーハンドリングデコレータ

ノード実行時のエラーをハンドルする
"""

from functools import wraps
import logging
from src.graph.state import ResearchState
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)


def handle_node_errors(node_func):
    """
    ノード実行時のエラーをハンドルするデコレータ
    
    エラーが発生した場合:
    1. エラーログを記録
    2. エラーメッセージをステートに追加
    3. next_actionを"end"に設定
    
    Args:
        node_func: ノード関数
    
    Returns:
        デコレータ関数
    """
    
    @wraps(node_func)
    def wrapper(state: ResearchState) -> ResearchState:
        try:
            return node_func(state)
        except Exception as e:
            logger.error(
                f"Error in {node_func.__name__}: {e}",
                exc_info=True
            )
            
            # エラーをステートに記録
            error_message = f"エラーが発生しました: {str(e)}"
            state["messages"].append(
                AIMessage(content=error_message)
            )
            
            # 次のアクションを終了に設定
            state["next_action"] = "end"
            
            return state
    
    return wrapper










