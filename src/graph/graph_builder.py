"""
グラフ構築とルーティング機能

LangGraphのグラフを構築してコンパイル
"""

from typing import Optional, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from src.graph.state import ResearchState
from src.nodes.supervisor import supervisor_node, planning_gate_node
from src.nodes.researcher import researcher_node
from src.nodes.writer import writer_node
from src.nodes.reviewer import reviewer_node
from src.graph.edges import route_supervisor, route_reviewer
import logging

logger = logging.getLogger(__name__)


def build_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    interrupt_before: Optional[List[str]] = None
):
    """
    グラフを構築してコンパイル
    
    グラフ構造:
    START → supervisor → [conditional] → researcher/writer/end
                                        ↓
                                  researcher → supervisor
                                        ↓
                                  writer → reviewer
                                        ↓
                                  reviewer → [conditional] → researcher/writer/end
    
    Args:
        checkpointer: チェックポイント（オプション）
        interrupt_before: 中断するノード名のリスト（オプション）
    
    Returns:
        コンパイル済みグラフ
    """
    
    # グラフ作成
    graph = StateGraph(ResearchState)
    
    # ノード追加
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("planning_gate", planning_gate_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)
    graph.add_node("reviewer", reviewer_node)
    
    # エントリーポイント
    graph.set_entry_point("supervisor")
    
    # Supervisorからの条件分岐（research のときは planning_gate 経由で Human-in-loop の中断ポイントへ）
    graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "research": "planning_gate",
            "write": "writer",
            "end": END
        }
    )
    
    # planning_gate → researcher（計画段階の中断は planning_gate の前のみ。Reviewer→researcher はこの経路を通らない）
    graph.add_edge("planning_gate", "researcher")
    
    # Researcher → Supervisor（常に）
    graph.add_edge("researcher", "supervisor")
    
    # Writer → Reviewer（常に）
    graph.add_edge("writer", "reviewer")
    
    # Reviewerからの条件分岐
    graph.add_conditional_edges(
        "reviewer",
        route_reviewer,
        {
            "research": "researcher",
            "write": "writer",
            "end": END
        }
    )
    
    # コンパイル
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before or []
    )
    
    logger.info("グラフを構築しました")
    
    return compiled




