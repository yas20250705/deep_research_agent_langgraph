"""
データモデルのユニットテスト

ResearchPlan, SearchResult, ResearchReportのテスト
"""

import pytest
from pydantic import ValidationError
from datetime import datetime
from src.schemas.data_models import ResearchPlan, SearchResult, ResearchReport


class TestResearchPlan:
    """ResearchPlanモデルのテスト"""
    
    def test_research_plan_creation(self):
        """有効なResearchPlanを作成"""
        plan = ResearchPlan(
            theme="テストテーマ",
            investigation_points=["観点1", "観点2"],
            search_queries=["クエリ1", "クエリ2"],
            plan_text="計画テキスト（10文字以上）"
        )
        assert plan.theme == "テストテーマ"
        assert len(plan.investigation_points) == 2
        assert len(plan.search_queries) == 2
        assert plan.created_at is not None
    
    def test_research_plan_validation_error_empty_theme(self):
        """空のテーマでバリデーションエラー"""
        with pytest.raises(ValidationError):
            ResearchPlan(
                theme="",  # 空文字列は無効
                investigation_points=["観点1"],
                search_queries=["クエリ1"],
                plan_text="計画テキスト"
            )
    
    def test_research_plan_validation_error_empty_investigation_points(self):
        """空の調査観点でバリデーションエラー"""
        with pytest.raises(ValidationError):
            ResearchPlan(
                theme="テストテーマ",
                investigation_points=[],  # 空リストは無効
                search_queries=["クエリ1"],
                plan_text="計画テキスト"
            )
    
    def test_research_plan_validation_error_short_plan_text(self):
        """短い計画テキストでバリデーションエラー"""
        with pytest.raises(ValidationError):
            ResearchPlan(
                theme="テストテーマ",
                investigation_points=["観点1"],
                search_queries=["クエリ1"],
                plan_text="短い"  # 10文字未満は無効
            )
    
    def test_research_plan_default_values(self):
        """デフォルト値の確認"""
        plan = ResearchPlan(
            theme="テストテーマ",
            investigation_points=["観点1"],
            search_queries=["クエリ1"],
            plan_text="計画テキスト（10文字以上）"
        )
        assert plan.source_priority == {"tavily": 1, "arxiv": 2}
        assert plan.created_at is not None


class TestSearchResult:
    """SearchResultモデルのテスト"""
    
    def test_search_result_creation(self):
        """有効なSearchResultを作成"""
        result = SearchResult(
            title="テストタイトル",
            summary="テスト要約",
            source="tavily",
            url="https://example.com"
        )
        assert result.title == "テストタイトル"
        assert result.source == "tavily"
        assert result.url == "https://example.com"
    
    def test_search_result_invalid_url(self):
        """無効なURLでバリデーションエラー"""
        with pytest.raises(ValidationError):
            SearchResult(
                title="テスト",
                summary="テスト",
                source="tavily",
                url="invalid-url"  # HTTP/HTTPS形式ではない
            )
    
    def test_search_result_relevance_score_range(self):
        """関連性スコアの範囲チェック"""
        # 有効な範囲内
        result = SearchResult(
            title="テスト",
            summary="テスト",
            source="tavily",
            url="https://example.com",
            relevance_score=0.5
        )
        assert result.relevance_score == 0.5
        
        # 範囲外（1.0より大きい）
        with pytest.raises(ValidationError):
            SearchResult(
                title="テスト",
                summary="テスト",
                source="tavily",
                url="https://example.com",
                relevance_score=1.5  # 1.0より大きい
            )
        
        # 範囲外（0.0より小さい）
        with pytest.raises(ValidationError):
            SearchResult(
                title="テスト",
                summary="テスト",
                source="tavily",
                url="https://example.com",
                relevance_score=-0.1  # 0.0より小さい
            )
    
    def test_search_result_published_date_format(self):
        """公開日の形式チェック"""
        # 有効な形式
        result = SearchResult(
            title="テスト",
            summary="テスト",
            source="tavily",
            url="https://example.com",
            published_date="2024-12-27"
        )
        assert result.published_date == "2024-12-27"
        
        # 無効な形式
        with pytest.raises(ValidationError):
            SearchResult(
                title="テスト",
                summary="テスト",
                source="tavily",
                url="https://example.com",
                published_date="2024/12/27"  # 形式が違う
            )


class TestResearchReport:
    """ResearchReportモデルのテスト"""
    
    def test_research_report_creation(self):
        """有効なResearchReportを作成"""
        report = ResearchReport(
            theme="テストテーマ",
            executive_summary="エグゼクティブサマリー（50文字以上）" * 3,  # より長い文字列
            key_findings=["発見1", "発見2"],
            detailed_analysis="詳細な分析（100文字以上）" * 10  # より長い文字列
        )
        assert report.theme == "テストテーマ"
        assert len(report.key_findings) == 2
        assert report.generated_at is not None
    
    def test_research_report_to_markdown(self):
        """Markdown形式への変換"""
        source = SearchResult(
            title="テストソース",
            summary="テスト要約",
            source="tavily",
            url="https://example.com"
        )
        
        report = ResearchReport(
            theme="テストテーマ",
            executive_summary="エグゼクティブサマリー（50文字以上）" * 3,  # より長い文字列
            key_findings=["発見1", "発見2"],
            detailed_analysis="詳細な分析（100文字以上）" * 10,  # より長い文字列
            sources=[source]
        )
        
        markdown = report.to_markdown()
        assert "# テストテーマ" in markdown
        assert "## Executive Summary" in markdown
        assert "## Key Findings" in markdown
        assert "## Detailed Analysis" in markdown
        assert "## References" in markdown
        assert "テストソース" in markdown
        assert "https://example.com" in markdown
    
    def test_research_report_validation_error_short_summary(self):
        """短いエグゼクティブサマリーでバリデーションエラー"""
        with pytest.raises(ValidationError):
            ResearchReport(
                theme="テストテーマ",
                executive_summary="短い",  # 50文字未満
                key_findings=["発見1"],
                detailed_analysis="詳細な分析（100文字以上）" * 5
            )
    
    def test_research_report_validation_error_empty_findings(self):
        """空の主要発見でバリデーションエラー"""
        with pytest.raises(ValidationError):
            ResearchReport(
                theme="テストテーマ",
                executive_summary="エグゼクティブサマリー（50文字以上）" * 2,
                key_findings=[],  # 空リストは無効
                detailed_analysis="詳細な分析（100文字以上）" * 5
            )

