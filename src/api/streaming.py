"""
ストリーミング出力機能

Server-Sent Events (SSE)を使用したストリーミング出力
"""

from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Dict, Any
import json
import asyncio
import logging
from src.api.research_manager import research_manager

logger = logging.getLogger(__name__)


async def stream_research_progress(research_id: str) -> AsyncGenerator[str, None]:
    """
    リサーチの進捗をストリーミング
    
    Args:
        research_id: リサーチID
    
    Yields:
        SSE形式のデータ
    """
    try:
        # 初期状態を送信
        research = research_manager.get_research(research_id)
        if research:
            yield f"data: {json.dumps({'type': 'status', 'status': research['status']})}\n\n"
        
        # 進捗を監視
        last_iteration = -1
        max_wait_time = 600  # 最大10分
        check_interval = 2  # 2秒ごとにチェック
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            status_info = research_manager.get_status(research_id)
            
            if status_info is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'リサーチが見つかりません'})}\n\n"
                break
            
            status = status_info.get("status")
            state = status_info.get("state")
            
            # ステータスが完了または失敗した場合
            if status in ["completed", "failed"]:
                yield f"data: {json.dumps({'type': 'status', 'status': status})}\n\n"
                
                if status == "completed":
                    # 結果を取得
                    research = research_manager.get_research(research_id)
                    if research and research.get("result"):
                        result = research["result"]
                        yield f"data: {json.dumps({'type': 'result', 'data': {'iteration_count': result.get('iteration_count', 0), 'sources_count': len(result.get('research_data', []))}})}\n\n"
                
                break
            
            # イテレーションが進んだ場合
            if state:
                current_iteration = state.get("iteration_count", 0)
                if current_iteration > last_iteration:
                    progress_data = {
                        "type": "progress",
                        "iteration": current_iteration,
                        "sources_collected": len(state.get("research_data", [])),
                        "current_node": state.get("next_action", "unknown")
                    }
                    yield f"data: {json.dumps(progress_data)}\n\n"
                    last_iteration = current_iteration
            
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
        
        # タイムアウト
        if elapsed_time >= max_wait_time:
            yield f"data: {json.dumps({'type': 'timeout', 'message': 'タイムアウトしました'})}\n\n"
    
    except Exception as e:
        logger.error(f"ストリーミングエラー: {e}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


async def stream_llm_response(prompt: str) -> AsyncGenerator[str, None]:
    """
    LLM応答をストリーミング（将来の拡張用）
    
    Args:
        prompt: プロンプト
    
    Yields:
        SSE形式のデータ
    """
    # 将来の実装: OpenAI Streaming APIを使用
    # 現在はプレースホルダー
    yield f"data: {json.dumps({'type': 'info', 'message': 'ストリーミング機能は開発中です'})}\n\n"


def create_streaming_response(generator: AsyncGenerator[str, None]) -> StreamingResponse:
    """
    ストリーミングレスポンスを作成
    
    Args:
        generator: データジェネレータ
    
    Returns:
        StreamingResponse
    """
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginx用
        }
    )

