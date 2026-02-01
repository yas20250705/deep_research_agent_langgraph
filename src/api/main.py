"""
FastAPIメインアプリケーション

REST APIエンドポイントを実装
"""

from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse, Response
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import quote
from src.api.schemas import (
    ResearchRequest,
    ResearchResponse,
    ResearchResultResponse,
    StatusResponse,
    InterruptedStateResponse,
    ResumeRequest,
    ErrorResponse,
    HealthResponse,
    ProgressInfo,
    ResearchStatistics,
    ResearchHistoryResponse,
    ResearchHistoryItem,
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
import os

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
            checkpointer_type=request.checkpointer_type,
            previous_reports_context=request.previous_reports_context
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


@app.get("/research/history", response_model=ResearchHistoryResponse)
async def get_research_history():
    """
    永続化済みリサーチの一覧を返す（サーバー再起動後もGUIで履歴を復元するために使用）
    """
    items = research_manager.list_persisted_researches()
    return ResearchHistoryResponse(
        items=[ResearchHistoryItem(
            research_id=x["research_id"],
            theme=x["theme"],
            status=x["status"],
            created_at=x.get("created_at"),
            completed_at=x.get("completed_at"),
        ) for x in items]
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
            detail={
                "error": "not_found",
                "message": "指定されたリサーチIDが見つかりません。サーバー再起動後は、完了したリサーチのみ参照できます。",
            }
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
            detail={
                "error": "result_not_found",
                "message": "リサーチ結果が見つかりません。",
            }
        )
    
    # レポート情報を構築（result はメモリ上のオブジェクトまたは永続化ファイル由来の辞書）
    report = None
    if result.get("current_draft"):
        sources = []
        for r in result.get("research_data", []) or []:
            if isinstance(r, dict):
                sources.append({
                    "title": r.get("title", ""),
                    "summary": r.get("summary", ""),
                    "url": r.get("url", ""),
                    "source": r.get("source", "tavily"),
                    "relevance_score": r.get("relevance_score"),
                })
            else:
                sources.append({
                    "title": r.title,
                    "summary": r.summary,
                    "url": r.url,
                    "source": r.source,
                    "relevance_score": r.relevance_score,
                })
        report = {
            "draft": result["current_draft"],
            "sources": sources,
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
    raw_state = status_info.get("state") or {}
    state = raw_state if isinstance(raw_state, dict) else {}
    
    # 進捗情報
    progress = None
    if state:
        # 次のノードを取得（list/tuple の場合は先頭要素、デフォルトは"supervisor"）
        next_nodes = status_info.get("next")
        if next_nodes and len(next_nodes) > 0:
            first = next_nodes[0] if isinstance(next_nodes, (list, tuple)) else next_nodes
            current_node = first if isinstance(first, str) else str(first)
        else:
            current_node = "supervisor"  # デフォルト値
        if current_node not in ("supervisor", "planning_gate", "revise_plan", "researcher", "writer", "reviewer", "unknown", "end"):
            current_node = "unknown"
        
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
    
    # 中断時のみ: 次に実行されるノードと state の一部を返す（state が空でも next_node は返す）
    interrupted_state = None
    if status_info["status"] == "interrupted":
        next_nodes = status_info.get("next")
        if next_nodes and len(next_nodes) > 0:
            first = next_nodes[0] if isinstance(next_nodes, (list, tuple)) else next_nodes
            next_node = first if isinstance(first, str) else str(first)
        else:
            next_node = "supervisor"
        task_plan_raw = state.get("task_plan")
        task_plan_dict = None
        if task_plan_raw is not None:
            task_plan_dict = task_plan_raw.model_dump() if hasattr(task_plan_raw, "model_dump") else task_plan_raw
        research_data_raw = state.get("research_data") or []
        research_data_summary = []
        for r in research_data_raw[:20]:
            if isinstance(r, dict):
                research_data_summary.append({"title": r.get("title", ""), "url": r.get("url", "")})
            else:
                research_data_summary.append({"title": getattr(r, "title", ""), "url": getattr(r, "url", "")})
        draft = state.get("current_draft") or ""
        current_draft_preview = draft[:500] + "..." if len(draft) > 500 else (draft if draft else None)
        feedback_val = state.get("feedback")
        interrupted_state = InterruptedStateResponse(
            next_node=next_node,
            task_plan=task_plan_dict,
            research_data_summary=research_data_summary,
            current_draft_preview=current_draft_preview,
            feedback=feedback_val,
        )
    
    return StatusResponse(
        research_id=research_id,
        status=status_info["status"],
        progress=progress,
        statistics=statistics,
        last_updated=datetime.now(),
        interrupted_state=interrupted_state,
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
    
    success = research_manager.resume_research(
        research_id,
        request.human_input or "",
        request.action
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="リサーチの再開に失敗しました"
        )
    
    message = "計画を再作成しました" if request.action == "replan" else "リサーチを再開しました"
    return ResearchResponse(
        research_id=research_id,
        status="processing",
        message=message,
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


@app.post("/research/export-report")
async def export_report(body: Dict):
    """
    レポートMarkdownをサーバー側のダウンロード保存先に保存する。
    DOWNLOAD_SAVE_DIR が設定されている場合のみ保存する（永続化データとは別の保存先）。
    """
    research_id = body.get("research_id") or ""
    content = body.get("content") or ""
    filename = body.get("filename") or ""
    if not research_id or not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="research_id と content は必須です"
        )
    if not getattr(settings, "DOWNLOAD_SAVE_DIR", None) or not str(settings.DOWNLOAD_SAVE_DIR).strip():
        return JSONResponse(content={"saved": False, "reason": "DOWNLOAD_SAVE_DIR が未設定です"})
    if not filename.strip():
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in research_id[:50])
        filename = f"report_{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    if not filename.endswith(".md"):
        filename = filename + ".md"
    # ファイル名の禁止文字のみ除去（日本語などは残す）
    _unsafe = set('\\/:*?"<>|\n\r')
    filename = "".join("_" if c in _unsafe else c for c in filename)
    save_dir = os.path.abspath(os.path.normpath(str(settings.DOWNLOAD_SAVE_DIR).strip()))
    try:
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("レポートMDを保存しました: %s", save_path)
        return JSONResponse(content={"saved": True, "path": save_path})
    except Exception as e:
        logger.warning("DOWNLOAD_SAVE_DIR へのレポート保存をスキップ: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"レポートの保存に失敗しました: {str(e)}"
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
        
        # ファイル名を生成
        title = source.get('title', 'source')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # ASCII フォールバック（古いクライアント用）
        safe_title_ascii = "".join(
            c if ord(c) < 128 and (c.isalnum() or c in (' ', '-', '_')) else '_'
            for c in title[:50]
        ).strip() or "source"
        filename_ascii = f"{safe_title_ascii}_{timestamp}.pdf"
        # 日本語対応: RFC 5987 filename*=UTF-8'' で UTF-8 ファイル名を送る
        unsafe_chars = {'\\', '/', ':', '*', '?', '"', '<', '>', '|', '\n', '\r'}
        safe_title_utf8 = "".join(
            c if c not in unsafe_chars else '_' for c in title[:80]
        ).strip() or "source"
        filename_utf8 = f"{safe_title_utf8}_{timestamp}.pdf"
        # DOWNLOAD_SAVE_DIR が設定されている場合はサーバー側にのみ保存し、PDFバイナリは返さない（ブラウザのダウンロードフォルダには保存しない）
        if getattr(settings, "DOWNLOAD_SAVE_DIR", None) and str(settings.DOWNLOAD_SAVE_DIR).strip():
            save_dir = os.path.abspath(os.path.normpath(str(settings.DOWNLOAD_SAVE_DIR).strip()))
            try:
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, filename_utf8)
                with open(save_path, "wb") as f:
                    f.write(pdf_buffer.getvalue())
                logger.info("参照ソースPDFを保存しました: %s", save_path)
                return JSONResponse(content={"saved": True, "path": save_path})
            except Exception as e:
                logger.warning("DOWNLOAD_SAVE_DIR へのPDF保存をスキップ: %s", e)
        filename_utf8_encoded = quote(filename_utf8, safe="._-()")
        content_disp = (
            f'attachment; filename="{filename_ascii}"; '
            f"filename*=UTF-8''{filename_utf8_encoded}"
        )
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": content_disp
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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTPException は正しいステータスコードで返す（429 等が 500 にならないように）"""
    content = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=content)


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

