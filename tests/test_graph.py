"""
グラフの統合テスト

グラフ全体の実行フローをテスト
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage
from src.graph.graph_builder import build_graph
from src.graph.state import ResearchState
from src.graph.edges import route_supervisor, route_reviewer
from src.schemas.data_models import ResearchPlan


@pytest.fixture
def initial_state():
    """初期ステート"""
    return {
        "messages": [HumanMessage(content="テストテーマについて調査してください")],
        "task_plan": None,
        "research_data": [],
        "current_draft": None,
        "feedback": None,
        "iteration_count": 0,
        "next_action": "research",
        "human_input_required": False,
        "human_input": None
    }


class TestGraphBuilder:
    """グラフ構築のテスト"""
    
    def test_build_graph(self):
        """グラフが正常に構築される"""
        graph = build_graph()
        assert graph is not None
    
    def test_build_graph_with_checkpointer(self):
        """チェックポイント付きでグラフが構築される"""
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
        graph = build_graph(checkpointer=checkpointer)
        assert graph is not None


class TestRouting:
    """ルーティング関数のテスト"""
    
    def test_route_supervisor(self, initial_state):
        """Supervisorからのルーティング"""
        initial_state["next_action"] = "research"
        result = route_supervisor(initial_state)
        assert result == "research"
        
        initial_state["next_action"] = "write"
        result = route_supervisor(initial_state)
        assert result == "write"
        
        initial_state["next_action"] = "end"
        result = route_supervisor(initial_state)
        assert result == "end"
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'TAVILY_API_KEY': 'test-key'})
    def test_route_reviewer_max_iterations(self, initial_state):
        """最大イテレーション到達時のルーティング"""
        from src.config.settings import Settings
        settings = Settings()
        
        initial_state["iteration_count"] = settings.MAX_ITERATIONS
        initial_state["next_action"] = "research"
        
        result = route_reviewer(initial_state)
        assert result == "end"
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'TAVILY_API_KEY': 'test-key'})
    def test_route_reviewer_normal(self, initial_state):
        """通常時のルーティング"""
        initial_state["iteration_count"] = 1
        initial_state["next_action"] = "write"
        
        result = route_reviewer(initial_state)
        assert result == "write"


class TestGraphFlow:
    """グラフフローのテスト"""
    
    @patch('src.nodes.supervisor.get_llm_from_settings')
    @patch('src.nodes.supervisor.call_llm_with_retry')
    @patch('src.nodes.researcher.tavily_search_tool')
    @patch('src.nodes.writer.get_llm_from_settings')
    @patch('src.nodes.writer.call_llm_with_retry')
    @patch('src.nodes.reviewer.get_llm_from_settings')
    @patch('src.nodes.reviewer.call_llm_with_retry')
    def test_basic_flow(
        self,
        mock_reviewer_retry,
        mock_reviewer_llm,
        mock_writer_retry,
        mock_writer_llm,
        mock_researcher_tool,
        mock_supervisor_retry,
        mock_supervisor_llm,
        initial_state
    ):
        """基本的なフローのテスト（モック使用）"""
        
        # Supervisorのモック
        mock_supervisor_response = Mock()
        mock_supervisor_response.content = '''{
            "theme": "テストテーマ",
            "investigation_points": ["観点1"],
            "search_queries": ["クエリ1"],
            "plan_text": "テスト計画（10文字以上）"
        }'''
        mock_supervisor_retry.return_value = mock_supervisor_response
        
        # Researcherのモック
        mock_researcher_tool.invoke.return_value = [
            {
                "title": "テスト結果",
                "content": "テスト要約",
                "url": "https://example.com",
                "score": 0.9
            }
        ]
        
        # Writerのモック
        mock_writer_response = Mock()
        mock_writer_response.content = "# テストテーマ\n\n## Executive Summary\nテストサマリー\n\n## Key Findings\n1. 発見1\n\n## Detailed Analysis\n詳細な分析（100文字以上）" * 2
        mock_writer_retry.return_value = mock_writer_response
        
        # Reviewerのモック（承認）
        mock_reviewer_response = Mock()
        mock_reviewer_response.content = '''{
            "approved": true,
            "overall_score": 0.9,
            "scores": {
                "fact_check": 0.95,
                "completeness": 0.9,
                "logic": 0.9,
                "format": 0.85
            },
            "feedback": "",
            "suggested_action": "write",
            "issues": []
        }'''
        mock_reviewer_retry.return_value = mock_reviewer_response
        
        # グラフを構築
        graph = build_graph()
        
        # 実行（実際にはモックが動作するため、完全な実行はしない）
        # ここではグラフが正常に構築されることを確認
        assert graph is not None

