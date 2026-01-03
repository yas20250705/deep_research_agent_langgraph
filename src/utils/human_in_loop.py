"""
Human-in-the-Loop機能

グラフ実行中に人間の承認や入力を受け付ける機能
"""

from typing import List, Optional, Dict, Any
from src.graph.state import ResearchState
import logging

logger = logging.getLogger(__name__)


def setup_human_intervention(
    graph: Any,  # CompiledGraph
    interrupt_nodes: List[str]
) -> Any:  # CompiledGraph
    """
    人間介入ポイントを設定
    
    注意: interrupt_beforeは既にgraph_builderで設定済み
    この関数は補助的な処理を行う
    
    Args:
        graph: コンパイル済みグラフ
        interrupt_nodes: 中断するノード名のリスト
    
    Returns:
        設定済みグラフ
    """
    
    logger.info(f"人間介入ポイントを設定: {interrupt_nodes}")
    # interrupt_beforeは既にgraph_builderで設定済み
    return graph


def wait_for_human_input(
    graph: Any,  # CompiledGraph
    config: Dict,
    timeout: Optional[float] = None
) -> Optional[str]:
    """
    人間入力を待つ
    
    実際の実装では、UIやAPI経由で入力を受け取る
    
    Args:
        graph: コンパイル済みグラフ
        config: 設定
        timeout: タイムアウト（秒）
    
    Returns:
        人間からの入力文字列、またはNone（タイムアウト）
    """
    
    state = graph.get_state(config)
    
    if state.next:
        # 中断されている
        logger.info("人間入力を待っています...")
        # 実際の実装では、UIやAPI経由で入力を受け取る
        # ここでは簡易的な実装
        try:
            human_input = input("入力してください: ")
            return human_input
        except (EOFError, KeyboardInterrupt):
            return None
    
    return None


def resume_with_input(
    graph: Any,  # CompiledGraph
    config: Dict,
    human_input: str
) -> ResearchState:
    """
    人間入力でグラフを再開
    
    Args:
        graph: コンパイル済みグラフ
        config: 設定
        human_input: 人間からの入力
    
    Returns:
        更新されたステート
    """
    
    # ステートを更新
    graph.update_state(config, {"human_input": human_input})
    
    logger.info(f"人間入力でグラフを再開: {human_input[:50]}...")
    
    # 再開
    result = graph.invoke(None, config)
    return result

