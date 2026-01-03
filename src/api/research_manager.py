"""
リサーチ管理機能

リサーチの実行と状態管理を行う
"""

import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from langchain_core.messages import HumanMessage
from src.graph.graph_builder import build_graph
from src.graph.state import ResearchState
from src.utils.checkpointer import create_checkpointer
from src.utils.logger import setup_logger
import logging

logger = setup_logger()


class ResearchManager:
    """リサーチ管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.researches: Dict[str, Dict] = {}
        self.graphs: Dict[str, any] = {}
    
    def create_research(
        self,
        theme: str,
        max_iterations: int = 5,
        enable_human_intervention: bool = False,
        checkpointer_type: str = "memory"
    ) -> str:
        """
        リサーチを作成して開始
        
        Args:
            theme: 調査テーマ
            max_iterations: 最大イテレーション数
            enable_human_intervention: 人間介入を有効化するか
            checkpointer_type: チェックポイントタイプ
        
        Returns:
            リサーチID
        """
        
        research_id = str(uuid.uuid4())
        
        # チェックポイント作成
        checkpointer = create_checkpointer(checkpointer_type)
        
        # グラフ構築
        interrupt_before = ["supervisor", "writer"] if enable_human_intervention else None
        graph = build_graph(
            checkpointer=checkpointer,
            interrupt_before=interrupt_before
        )
        
        # 初期ステート作成
        initial_state: ResearchState = {
            "messages": [HumanMessage(content=theme)],
            "task_plan": None,
            "research_data": [],
            "current_draft": None,
            "feedback": None,
            "iteration_count": 0,
            "next_action": "research",
            "human_input_required": False,
            "human_input": None
        }
        
        # 設定
        config = {
            "configurable": {
                "thread_id": research_id
            }
        }
        
        # リサーチ情報を保存
        self.researches[research_id] = {
            "research_id": research_id,
            "status": "started",
            "theme": theme,
            "max_iterations": max_iterations,
            "created_at": datetime.now(),
            "config": config,
            "enable_human_intervention": enable_human_intervention
        }
        
        self.graphs[research_id] = graph
        
        # 非同期で実行開始
        asyncio.create_task(self._run_research(research_id, initial_state, config))
        
        logger.info(f"リサーチを作成: research_id={research_id}, theme={theme}")
        
        return research_id
    
    async def _run_research(
        self,
        research_id: str,
        initial_state: ResearchState,
        config: Dict
    ):
        """
        リサーチを実行（非同期）
        
        Args:
            research_id: リサーチID
            initial_state: 初期ステート
            config: 設定
        """
        
        try:
            self.researches[research_id]["status"] = "processing"
            
            graph = self.graphs[research_id]
            
            # 実行
            result = graph.invoke(initial_state, config)
            
            # 結果を保存
            self.researches[research_id].update({
                "status": "completed",
                "result": result,
                "completed_at": datetime.now()
            })
            
            logger.info(f"リサーチ完了: research_id={research_id}")
            
        except Exception as e:
            logger.error(f"リサーチエラー: research_id={research_id}, error={e}", exc_info=True)
            self.researches[research_id].update({
                "status": "failed",
                "error": str(e)
            })
    
    def get_research(self, research_id: str) -> Optional[Dict]:
        """
        リサーチ情報を取得
        
        Args:
            research_id: リサーチID
        
        Returns:
            リサーチ情報、またはNone
        """
        
        return self.researches.get(research_id)
    
    def get_status(self, research_id: str) -> Optional[Dict]:
        """
        リサーチの状態を取得
        
        Args:
            research_id: リサーチID
        
        Returns:
            ステータス情報、またはNone
        """
        
        research = self.researches.get(research_id)
        if research is None:
            return None
        
        graph = self.graphs.get(research_id)
        if graph is None:
            return None
        
        # グラフの状態を取得
        state = graph.get_state(research["config"])
        
        return {
            "research_id": research_id,
            "status": research["status"],
            "state": state.values if state.values else None,
            "next": state.next if hasattr(state, 'next') else None
        }
    
    def resume_research(self, research_id: str, human_input: str) -> bool:
        """
        中断されたリサーチを再開
        
        Args:
            research_id: リサーチID
            human_input: 人間からの入力
        
        Returns:
            成功したかどうか
        """
        
        research = self.researches.get(research_id)
        if research is None:
            return False
        
        if not research.get("enable_human_intervention"):
            return False
        
        graph = self.graphs.get(research_id)
        if graph is None:
            return False
        
        try:
            # ステートを更新
            graph.update_state(research["config"], {"human_input": human_input})
            
            # 再開
            result = graph.invoke(None, research["config"])
            
            # 結果を保存
            research.update({
                "status": "processing",
                "result": result
            })
            
            logger.info(f"リサーチを再開: research_id={research_id}")
            return True
            
        except Exception as e:
            logger.error(f"リサーチ再開エラー: research_id={research_id}, error={e}")
            return False
    
    def delete_research(self, research_id: str) -> bool:
        """
        リサーチを削除
        
        Args:
            research_id: リサーチID
        
        Returns:
            成功したかどうか
        """
        
        if research_id in self.researches:
            del self.researches[research_id]
            if research_id in self.graphs:
                del self.graphs[research_id]
            logger.info(f"リサーチを削除: research_id={research_id}")
            return True
        return False


# グローバルインスタンス
research_manager = ResearchManager()









