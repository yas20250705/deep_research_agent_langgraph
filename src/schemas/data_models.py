"""
データモデル定義（Pydantic）

ResearchPlan, SearchResult, ResearchReportの定義
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Literal


class ResearchPlan(BaseModel):
    """調査計画モデル"""
    
    theme: str = Field(..., description="調査テーマ", min_length=1, max_length=500)
    investigation_points: List[str] = Field(
        default_factory=list,
        description="調査観点のリスト",
        min_length=1,
        max_length=10
    )
    search_queries: List[str] = Field(
        default_factory=list,
        description="検索クエリのリスト",
        min_length=1,
        max_length=20
    )
    source_priority: Dict[str, int] = Field(
        default_factory=lambda: {"tavily": 1, "arxiv": 2},
        description="情報源の優先度（数値が小さいほど優先度が高い）"
    )
    plan_text: str = Field(..., description="人間可読な計画テキスト", min_length=10)
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "theme": "LangGraphについて調査してください",
                "investigation_points": [
                    "LangGraphの基本概念と特徴",
                    "LangGraphの用途とユースケース"
                ],
                "search_queries": [
                    "LangGraph framework",
                    "LangGraph use cases"
                ],
                "plan_text": "LangGraphについて包括的に調査します...",
                "created_at": "2024-12-27T10:00:00Z"
            }
        }
    }


class SearchResult(BaseModel):
    """検索結果モデル（共通スキーマ）"""
    
    title: str = Field(..., description="タイトル", min_length=1, max_length=500)
    summary: str = Field(..., description="要約", min_length=1, max_length=2000)
    source: Literal["tavily", "arxiv"] = Field(..., description="情報源")
    url: str = Field(..., description="URL", pattern=r"^https?://")
    published_date: Optional[str] = Field(
        None,
        description="公開日",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    authors: Optional[List[str]] = Field(
        None,
        description="著者リスト（arXiv用）",
        max_length=50
    )
    categories: Optional[List[str]] = Field(
        None,
        description="カテゴリリスト（arXiv用）",
        max_length=20
    )
    relevance_score: Optional[float] = Field(
        None,
        description="関連性スコア",
        ge=0.0,
        le=1.0
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "LangGraph Documentation",
                "summary": "LangGraphの公式ドキュメント...",
                "source": "tavily",
                "url": "https://langchain-ai.github.io/langgraph/",
                "published_date": "2024-01-01",
                "relevance_score": 0.95
            }
        }
    }


class ResearchReport(BaseModel):
    """リサーチレポートモデル"""
    
    theme: str = Field(..., description="調査テーマ", min_length=1, max_length=500)
    executive_summary: str = Field(
        ...,
        description="エグゼクティブサマリー",
        min_length=50,
        max_length=1000
    )
    key_findings: List[str] = Field(
        default_factory=list,
        description="主要発見のリスト",
        min_length=1,
        max_length=20
    )
    detailed_analysis: str = Field(
        ...,
        description="詳細解説",
        min_length=100
    )
    constraints_and_challenges: str = Field(
        default="",
        description="制約・課題",
        max_length=2000
    )
    sources: List[SearchResult] = Field(
        default_factory=list,
        description="参考ソース一覧"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="生成日時"
    )
    
    def to_markdown(self) -> str:
        """Markdown形式に変換"""
        md_lines = [
            f"# {self.theme}",
            "",
            "## Executive Summary",
            "",
            self.executive_summary,
            "",
            "## Key Findings",
            ""
        ]
        
        for i, finding in enumerate(self.key_findings, 1):
            md_lines.append(f"{i}. {finding}")
        
        md_lines.extend([
            "",
            "## Detailed Analysis",
            "",
            self.detailed_analysis,
            ""
        ])
        
        if self.constraints_and_challenges:
            md_lines.extend([
                "## Constraints and Challenges",
                "",
                self.constraints_and_challenges,
                ""
            ])
        
        md_lines.extend([
            "## References",
            ""
        ])
        
        for i, source in enumerate(self.sources, 1):
            md_lines.append(f"{i}. **{source.title}**")
            md_lines.append(f"   - Source: {source.source}")
            md_lines.append(f"   - URL: {source.url}")
            if source.published_date:
                md_lines.append(f"   - Published: {source.published_date}")
            if source.authors:
                md_lines.append(f"   - Authors: {', '.join(source.authors)}")
            md_lines.append("")
        
        md_lines.append(
            f"\n*Generated at: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}*"
        )
        
        return "\n".join(md_lines)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "theme": "LangGraphについて調査してください",
                "executive_summary": "LangGraphは...",
                "key_findings": [
                    "発見1",
                    "発見2"
                ],
                "detailed_analysis": "詳細な分析...",
                "constraints_and_challenges": "制約と課題...",
                "sources": [],
                "generated_at": "2024-12-27T10:02:00Z"
            }
        }
    }

