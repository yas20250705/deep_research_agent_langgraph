"""
ステートスキーマ定義（TypedDict）

LangGraphの共有ステートを定義
"""

from typing import TypedDict, List, Optional, Literal, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from src.schemas.data_models import ResearchPlan, SearchResult


class ResearchState(TypedDict):
    """
    リサーチエージェントの共有ステート
    
    全ノードが共有・参照・更新するデータ構造
    
    フィールド説明:
    - messages: LangGraph標準のメッセージ履歴（自動マージ）
    - task_plan: 調査計画（初回Supervisor実行時に生成）
    - research_data: 収集された検索結果のリスト
    - current_draft: Writerが生成したレポートドラフト
    - feedback: Reviewerからの改善フィードバック
    - iteration_count: ループ回数（無限ループ防止）
    - next_action: 次のアクション（ルーティング用）
    - human_input_required: 人間介入が必要かどうか
    - human_input: 人間からの入力内容
    """
    
    # メッセージ履歴（LangGraph標準、自動マージ）
    messages: Annotated[
        List[BaseMessage], 
        add_messages
    ]
    
    # 調査計画（初回はNone、Supervisorで生成）
    task_plan: Optional[ResearchPlan]
    
    # 収集された研究データ（Researcherが追加）
    research_data: List[SearchResult]
    
    # 現在のドラフト（Writerが生成）
    current_draft: Optional[str]
    
    # Reviewerからのフィードバック
    feedback: Optional[str]
    
    # ループ回数（各ノード実行時にインクリメント）
    iteration_count: int
    
    # 次のアクション（ルーティング決定用）
    next_action: Literal["research", "write", "review", "end"]
    
    # 人間介入フラグ
    human_input_required: bool
    
    # 人間からの入力
    human_input: Optional[str]




