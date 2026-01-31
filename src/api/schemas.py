"""
APIスキーマ定義

FastAPI用のリクエスト・レスポンスモデル
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict
from src.schemas.data_models import ResearchPlan, SearchResult, ResearchReport


class ResearchRequest(BaseModel):
    """リサーチ開始リクエスト"""
    
    theme: str = Field(..., description="調査テーマ", min_length=1, max_length=500)
    max_iterations: int = Field(
        default=5,
        description="最大イテレーション数",
        ge=1,
        le=10
    )
    enable_human_intervention: bool = Field(
        default=False,
        description="人間介入を有効化するか"
    )
    checkpointer_type: str = Field(
        default="memory",
        description="チェックポイントタイプ",
        pattern="^(memory|redis)$"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "theme": "LangGraphについて調査してください",
                "max_iterations": 5,
                "enable_human_intervention": False,
                "checkpointer_type": "memory"
            }
        }
    }


class ResearchResponse(BaseModel):
    """リサーチ開始レスポンス"""
    
    research_id: str = Field(..., description="リサーチID（UUID）")
    status: str = Field(
        ...,
        description="ステータス",
        pattern="^(started|processing|completed|failed|interrupted)$"
    )
    message: str = Field(..., description="メッセージ")
    created_at: datetime = Field(..., description="作成日時")
    estimated_completion_time: Optional[datetime] = Field(
        None,
        description="推定完了時刻"
    )


class ProgressInfo(BaseModel):
    """進捗情報"""
    
    current_iteration: int = Field(..., description="現在のイテレーション", ge=0)
    max_iterations: int = Field(..., description="最大イテレーション数", ge=1)
    current_node: str = Field(
        ...,
        description="現在実行中のノード",
        pattern="^(supervisor|researcher|writer|reviewer|unknown|end)$"
    )
    nodes_completed: List[str] = Field(
        default_factory=list,
        description="完了したノードのリスト"
    )
    nodes_remaining: List[str] = Field(
        default_factory=list,
        description="残りのノードのリスト"
    )


class ResearchStatistics(BaseModel):
    """統計情報"""
    
    iterations: int = Field(..., description="イテレーション回数", ge=0)
    sources_collected: int = Field(..., description="収集されたソース数", ge=0)
    processing_time_seconds: int = Field(..., description="処理時間（秒）", ge=0)


class ResearchResultResponse(BaseModel):
    """リサーチ結果レスポンス"""
    
    research_id: str = Field(..., description="リサーチID")
    status: str = Field(..., description="ステータス")
    theme: str = Field(..., description="調査テーマ")
    plan: Optional[ResearchPlan] = Field(None, description="調査計画")
    report: Optional[Dict] = Field(None, description="レポート（statusがcompletedの場合のみ）")
    statistics: ResearchStatistics = Field(..., description="統計情報")
    created_at: datetime = Field(..., description="作成日時")
    completed_at: Optional[datetime] = Field(None, description="完了日時（完了時のみ）")


class StatusResponse(BaseModel):
    """ステータスレスポンス"""
    
    research_id: str = Field(..., description="リサーチID")
    status: str = Field(..., description="ステータス")
    progress: Optional[ProgressInfo] = Field(None, description="進捗情報")
    statistics: Optional[ResearchStatistics] = Field(None, description="統計情報")
    last_updated: datetime = Field(..., description="最終更新日時")


class ResumeRequest(BaseModel):
    """再開リクエスト"""
    
    human_input: str = Field(..., description="人間からの入力", min_length=1)


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    
    error: str = Field(..., description="エラーコード")
    message: str = Field(..., description="エラーメッセージ")
    details: Optional[Dict] = Field(None, description="詳細情報")


class ResearchHistoryItem(BaseModel):
    """履歴一覧の1件"""
    research_id: str = Field(..., description="リサーチID")
    theme: str = Field(..., description="調査テーマ")
    status: str = Field(..., description="ステータス")
    created_at: Optional[datetime] = Field(None, description="作成日時")
    completed_at: Optional[datetime] = Field(None, description="完了日時")


class ResearchHistoryResponse(BaseModel):
    """履歴一覧レスポンス（サーバー再起動後の復元用）"""
    items: List[ResearchHistoryItem] = Field(default_factory=list, description="履歴一覧")


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    
    status: str = Field(..., description="ステータス（healthy or unhealthy）")
    version: str = Field(..., description="APIバージョン")
    timestamp: datetime = Field(..., description="チェック時刻")
    services: Dict[str, str] = Field(..., description="各サービスの状態")

