"""
FastAPIメインアプリケーション

REST APIエンドポイントを実装
"""

from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse, Response
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.api.schemas import (
    ResearchRequest,
    ResearchResponse,
    ResearchResultResponse,
    StatusResponse,
    ResumeRequest,
    ErrorResponse,
    HealthResponse,
    ProgressInfo,
    ResearchStatistics
)
from src.api.research_manager import research_manager
from src.api.middleware import (
    SecurityMiddleware,
    RateLimitMiddleware,
    setup_cors,
    verify_api_key,
    get_api_key_from_request
)
from src.api.streaming import stream_research_progress, create_streaming_response
from src.utils.logger import setup_logger
from src.utils.security import validate_theme, sanitize_error_message
from src.utils.pdf_generator import generate_source_pdf, PDF_AVAILABLE
from src.config.settings import Settings
import logging

logger = setup_logger()

app = FastAPI(
    title="LangGraph搭載 自律型リサーチエージェント API",
    description="LangGraphを活用した自律型リサーチエージェントのREST API",
    version="1.0.0"
)

# ミドルウェアの設定
settings = Settings()

# CORS設定
setup_cors(app)

# セキュリティミドルウェア
app.add_middleware(SecurityMiddleware)

# レート制限ミドルウェア
if settings.ENABLE_RATE_LIMIT:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE
    )


def require_auth(request: Request) -> bool:
    """認証が必要なエンドポイント用の依存関数"""
    if not settings.ENABLE_API_AUTH:
        return True
    
    api_key = get_api_key_from_request(request)
    if not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です。X-API-KeyヘッダーまたはAuthorizationヘッダーにAPIキーを指定してください。"
        )
    return True


@app.post("/research", response_model=ResearchResponse, status_code=status.HTTP_201_CREATED)
async def create_research(
    request: ResearchRequest,
    authenticated: bool = Depends(require_auth)
):
    """
    リサーチを開始
    
    Args:
        request: リサーチリクエスト
        authenticated: 認証状態
    
    Returns:
        リサーチレスポンス
    """
    
    # テーマの検証
    is_valid, error_message = validate_theme(request.theme)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    try:
        research_id = research_manager.create_research(
            theme=request.theme,
            max_iterations=request.max_iterations,
            enable_human_intervention=request.enable_human_intervention,
            checkpointer_type=request.checkpointer_type
        )
        
        # 推定完了時刻（簡易計算: 1イテレーションあたり30秒）
        estimated_time = datetime.now() + timedelta(seconds=request.max_iterations * 30)
        
        return ResearchResponse(
            research_id=research_id,
            status="started",
            message="リサーチを開始しました",
            created_at=datetime.now(),
            estimated_completion_time=estimated_time
        )
        
    except Exception as e:
        logger.error(f"リサーチ作成エラー: {e}", exc_info=True)
        error_detail = sanitize_error_message(e, include_details=False)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@app.get("/research/{research_id}", response_model=ResearchResultResponse)
async def get_research(research_id: str):
    """
    リサーチ結果を取得
    
    Args:
        research_id: リサーチID
    
    Returns:
        リサーチ結果レスポンス
    """
    
    research = research_manager.get_research(research_id)
    if research is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたリサーチIDが見つかりません"
        )
    
    # 処理中の場合は422を返す
    if research["status"] == "processing":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "processing",
                "message": "リサーチはまだ処理中です",
                "status": "processing"
            }
        )
    
    result = research.get("result")
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="リサーチ結果が見つかりません"
        )
    
    # レポート情報を構築
    report = None
    if result.get("current_draft"):
        report = {
            "draft": result["current_draft"],
            "sources": [
                {
                    "title": r.title,
                    "summary": r.summary,
                    "url": r.url,
                    "source": r.source,
                    "relevance_score": r.relevance_score
                }
                for r in result.get("research_data", [])
            ]
        }
    
    # 統計情報
    statistics = ResearchStatistics(
        iterations=result.get("iteration_count", 0),
        sources_collected=len(result.get("research_data", [])),
        processing_time_seconds=int(
            (research.get("completed_at", datetime.now()) - research["created_at"]).total_seconds()
        )
    )
    
    return ResearchResultResponse(
        research_id=research_id,
        status=research["status"],
        theme=research["theme"],
        plan=result.get("task_plan"),
        report=report,
        statistics=statistics,
        created_at=research["created_at"],
        completed_at=research.get("completed_at")
    )


@app.get("/research/{research_id}/status", response_model=StatusResponse)
async def get_research_status(research_id: str):
    """
    リサーチの状態を取得
    
    Args:
        research_id: リサーチID
    
    Returns:
        ステータスレスポンス
    """
    
    status_info = research_manager.get_status(research_id)
    if status_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたリサーチIDが見つかりません"
        )
    
    research = research_manager.get_research(research_id)
    state = status_info.get("state")
    
    # 進捗情報
    progress = None
    if state:
        # 次のノードを取得（デフォルトは"supervisor"）
        next_nodes = status_info.get("next")
        if next_nodes and len(next_nodes) > 0:
            current_node = next_nodes[0] if isinstance(next_nodes, list) else str(next_nodes)
        else:
            current_node = "supervisor"  # デフォルト値
        
        progress = ProgressInfo(
            current_iteration=state.get("iteration_count", 0),
            max_iterations=research.get("max_iterations", 5),
            current_node=current_node,
            nodes_completed=[],
            nodes_remaining=[]
        )
    
    # 統計情報
    statistics = None
    if state:
        statistics = ResearchStatistics(
            iterations=state.get("iteration_count", 0),
            sources_collected=len(state.get("research_data", [])),
            processing_time_seconds=int(
                (datetime.now() - research["created_at"]).total_seconds()
            )
        )
    
    return StatusResponse(
        research_id=research_id,
        status=status_info["status"],
        progress=progress,
        statistics=statistics,
        last_updated=datetime.now()
    )


@app.post("/research/{research_id}/resume", response_model=ResearchResponse)
async def resume_research(research_id: str, request: ResumeRequest):
    """
    中断されたリサーチを再開
    
    Args:
        research_id: リサーチID
        request: 再開リクエスト
    
    Returns:
        リサーチレスポンス
    """
    
    research = research_manager.get_research(research_id)
    if research is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたリサーチIDが見つかりません"
        )
    
    if research["status"] != "interrupted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "not_interrupted",
                "message": "リサーチは中断されていません"
            }
        )
    
    success = research_manager.resume_research(research_id, request.human_input)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="リサーチの再開に失敗しました"
        )
    
    return ResearchResponse(
        research_id=research_id,
        status="processing",
        message="リサーチを再開しました",
        created_at=research["created_at"]
    )


@app.delete("/research/{research_id}")
async def delete_research(research_id: str):
    """
    リサーチを削除
    
    Args:
        research_id: リサーチID
    
    Returns:
        削除結果
    """
    
    success = research_manager.delete_research(research_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたリサーチIDが見つかりません"
        )
    
    return {
        "message": "リサーチが削除されました",
        "research_id": research_id
    }


@app.get("/research/{research_id}/stream")
async def stream_research(research_id: str):
    """
    リサーチの進捗をストリーミング（SSE）
    
    Args:
        research_id: リサーチID
    
    Returns:
        ストリーミングレスポンス
    """
    research = research_manager.get_research(research_id)
    if research is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたリサーチIDが見つかりません"
        )
    
    return create_streaming_response(stream_research_progress(research_id))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    ヘルスチェックエンドポイント
    
    Returns:
        ヘルスチェックレスポンス
    """
    
    # サービス状態の確認（簡易実装）
    services = {
        "openai": "healthy",  # 実際には接続確認が必要
        "tavily": "healthy",  # 実際には接続確認が必要
        "redis": "healthy"  # 実際には接続確認が必要
    }
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(),
        services=services
    )


@app.post("/source/pdf")
async def generate_source_pdf_endpoint(source: Dict):
    """
    参照ソースのURLからPDFを生成
    
    Args:
        source: ソース情報（title, url, summary等）
    
    Returns:
        PDFファイル（application/pdf）
    """
    if not PDF_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF生成機能を使用するにはreportlabをインストールしてください"
        )
    
    try:
        url = source.get('url', '')
        if not url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URLが指定されていません"
            )
        
        theme = source.get('theme', '参照ソース')
        pdf_buffer = generate_source_pdf(source, theme)
        
        # ファイル名を生成（HTTPヘッダーは latin-1 のため ASCII のみ使用）
        title = source.get('title', 'source')
        safe_title_ascii = "".join(
            c if ord(c) < 128 and (c.isalnum() or c in (' ', '-', '_')) else '_'
            for c in title[:50]
        ).strip() or "source"
        filename_ascii = f"{safe_title_ascii}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_ascii}"'
            }
        )
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"PDF生成ライブラリが利用できません: {str(e)}"
        )
    except Exception as e:
        logger.error(f"PDF生成エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF生成に失敗しました: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """グローバル例外ハンドラー"""
    
    logger.error(f"予期しないエラー: {exc}", exc_info=True)
    error_detail = sanitize_error_message(exc, include_details=False)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": error_detail
        }
    )

