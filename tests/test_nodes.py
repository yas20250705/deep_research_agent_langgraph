"""
ノードのユニットテスト

各ノードの動作を確認するテスト（モック使用）
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from src.graph.state import ResearchState
from src.schemas.data_models import ResearchPlan, SearchResult
from src.nodes.supervisor import supervisor_node, extract_user_message, evaluate_progress
from src.nodes.researcher import researcher_node
from src.nodes.writer import writer_node
from src.nodes.reviewer import reviewer_node


# テスト用の環境変数を設定
@pytest.fixture(autouse=True)
def setup_env():
    """すべてのテストで環境変数を設定"""
    os.environ['OPENAI_API_KEY'] = 'test-openai-key'
    os.environ['TAVILY_API_KEY'] = 'test-tavily-key'
    yield
    # クリーンアップ（必要に応じて）


@pytest.fixture
def mock_state():
    """テスト用のモックステート"""
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


@pytest.fixture
def mock_plan():
    """テスト用のモック計画"""
    return ResearchPlan(
        theme="テストテーマ",
        investigation_points=["観点1", "観点2"],
        search_queries=["クエリ1", "クエリ2"],
        plan_text="テスト計画（10文字以上）"
    )


class TestSupervisorNode:
    """Supervisorノードのテスト"""
    
    def test_extract_user_message(self):
        """ユーザーメッセージの抽出"""
        messages = [
            HumanMessage(content="最初のメッセージ"),
            AIMessage(content="AIの応答"),
            HumanMessage(content="最新のメッセージ")
        ]
        result = extract_user_message(messages)
        assert result == "最新のメッセージ"
    
    def test_evaluate_progress(self, mock_state, mock_plan):
        """進捗評価のテスト"""
        mock_state["task_plan"] = mock_plan
        mock_state["research_data"] = [
            SearchResult(
                title="テスト1",
                summary="要約1",
                source="tavily",
                url="https://example.com/1",
                relevance_score=0.9
            ),
            SearchResult(
                title="テスト2",
                summary="要約2",
                source="tavily",
                url="https://example.com/2",
                relevance_score=0.8
            )
        ]
        
        progress = evaluate_progress(mock_state)
        assert progress["data_count"] == 2
        assert 0.0 <= progress["data_quality"] <= 1.0
        assert 0.0 <= progress["coverage"] <= 1.0
    
    @patch('src.nodes.supervisor.ChatOpenAI')
    @patch('src.nodes.supervisor.call_llm_with_retry')
    def test_supervisor_generates_plan(self, mock_retry, mock_llm_class, mock_state):
        """Supervisorが計画を生成"""
        # LLMのモック
        mock_response = Mock()
        mock_response.content = '''{
            "theme": "テストテーマ",
            "investigation_points": ["観点1", "観点2"],
            "search_queries": ["クエリ1", "クエリ2"],
            "plan_text": "テスト計画（10文字以上）"
        }'''
        
        mock_chain = Mock()
        mock_chain.invoke.return_value = mock_response
        mock_retry.return_value = mock_response
        
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        result = supervisor_node(mock_state)
        
        assert result["task_plan"] is not None
        assert result["next_action"] in ["research", "write", "end"]


class TestResearcherNode:
    """Researcherノードのテスト"""
    
    @patch('src.nodes.researcher.tavily_search_tool')
    def test_researcher_executes_search(self, mock_search_tool, mock_state, mock_plan):
        """Researcherが検索を実行"""
        mock_state["task_plan"] = mock_plan
        
        # モック検索結果
        mock_search_tool.invoke.return_value = [
            {
                "title": "テスト結果",
                "content": "テスト要約",
                "url": "https://example.com",
                "score": 0.9
            }
        ]
        
        result = researcher_node(mock_state)
        
        assert len(result["research_data"]) > 0
        assert result["iteration_count"] == 1
    
    @patch('src.nodes.researcher.tavily_search_tool')
    def test_researcher_removes_duplicates(self, mock_search_tool, mock_state, mock_plan):
        """重複URLを除去"""
        existing_result = SearchResult(
            title="既存",
            summary="既存の要約",
            source="tavily",
            url="https://example.com/existing"
        )
        
        mock_state["task_plan"] = mock_plan
        mock_state["research_data"] = [existing_result]
        
        # 同じURLを含む検索結果を返すモック
        mock_search_tool.invoke.return_value = [
            {
                "title": "新しい結果",
                "content": "新しい要約",
                "url": "https://example.com/existing",  # 既存と同じURL
                "score": 0.8
            },
            {
                "title": "別の結果",
                "content": "別の要約",
                "url": "https://example.com/new",  # 新しいURL
                "score": 0.7
            }
        ]
        
        result = researcher_node(mock_state)
        
        # 重複は追加されず、新しいURLのみ追加される
        urls = [r.url for r in result["research_data"]]
        assert urls.count("https://example.com/existing") == 1
        assert "https://example.com/new" in urls


class TestWriterNode:
    """Writerノードのテスト"""
    
    @patch('src.nodes.writer.ChatOpenAI')
    @patch('src.nodes.writer.call_llm_with_retry')
    def test_writer_generates_draft(self, mock_retry, mock_llm_class, mock_state, mock_plan):
        """Writerがドラフトを生成"""
        mock_state["task_plan"] = mock_plan
        mock_state["research_data"] = [
            SearchResult(
                title="テストソース",
                summary="テスト要約",
                source="tavily",
                url="https://example.com"
            )
        ]
        
        # LLMのモック
        mock_response = Mock()
        mock_response.content = "# テストテーマ\n\n## Executive Summary\nテストサマリー\n\n## Key Findings\n1. 発見1\n\n## Detailed Analysis\n詳細な分析（100文字以上）" * 2
        
        mock_retry.return_value = mock_response
        
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        result = writer_node(mock_state)
        
        assert result["current_draft"] is not None
        assert len(result["current_draft"]) > 0


class TestReviewerNode:
    """Reviewerノードのテスト"""
    
    @patch('src.nodes.reviewer.ChatOpenAI')
    @patch('src.nodes.reviewer.call_llm_with_retry')
    def test_reviewer_evaluates_draft(self, mock_retry, mock_llm_class, mock_state, mock_plan):
        """Reviewerがドラフトを評価"""
        mock_state["task_plan"] = mock_plan
        mock_state["current_draft"] = "# テストテーマ\n\n## Executive Summary\nテストサマリー\n\n## Key Findings\n1. 発見1\n\n## Detailed Analysis\n詳細な分析（100文字以上）" * 2
        mock_state["research_data"] = [
            SearchResult(
                title="テストソース",
                summary="テスト要約",
                source="tavily",
                url="https://example.com"
            )
        ]
        
        # LLMのモック
        mock_response = Mock()
        mock_response.content = '''{
            "approved": false,
            "overall_score": 0.75,
            "scores": {
                "fact_check": 0.9,
                "completeness": 0.7,
                "logic": 0.8,
                "format": 0.6
            },
            "feedback": "改善が必要",
            "suggested_action": "write",
            "issues": []
        }'''
        
        mock_retry.return_value = mock_response
        
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        result = reviewer_node(mock_state)
        
        assert result["feedback"] is not None
        assert result["next_action"] in ["research", "write", "end"]
    
    @patch('src.nodes.reviewer.ChatOpenAI')
    @patch('src.nodes.reviewer.call_llm_with_retry')
    def test_reviewer_approves_draft(self, mock_retry, mock_llm_class, mock_state, mock_plan):
        """ドラフトが承認された場合、終了"""
        mock_state["task_plan"] = mock_plan
        mock_state["current_draft"] = "# テストテーマ\n\n## Executive Summary\nテストサマリー\n\n## Key Findings\n1. 発見1\n\n## Detailed Analysis\n詳細な分析（100文字以上）" * 2
        mock_state["research_data"] = []
        
        # LLMのモック（承認）
        mock_response = Mock()
        mock_response.content = '''{
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
        
        mock_retry.return_value = mock_response
        
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        result = reviewer_node(mock_state)
        
        assert result["next_action"] == "end"
        assert result["feedback"] is None

