"""
APIミドルウェア

セキュリティ、認証、レート制限などのミドルウェア
"""

from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Dict
import time
import logging
from collections import defaultdict
from src.utils.security import sanitize_input, validate_theme
from src.config.settings import Settings

logger = logging.getLogger(__name__)

# API Key認証
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

# レート制限用のストレージ（簡易実装、本番環境ではRedis推奨）
_rate_limit_storage: Dict[str, list] = defaultdict(list)


class SecurityMiddleware(BaseHTTPMiddleware):
    """セキュリティミドルウェア"""
    
    async def dispatch(self, request: Request, call_next):
        # リクエストパスのログ
        logger.debug(f"リクエスト: {request.method} {request.url.path}")
        
        # ヘルスチェックエンドポイントはスキップ
        if request.url.path == "/health":
            return await call_next(request)
        
        # リクエストボディの検証（POST/PUT/PATCHのみ）
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # リクエストボディを再度読み込めるようにする
                    async def receive():
                        return {"type": "http.request", "body": body}
                    request._receive = receive
            except Exception as e:
                logger.warning(f"リクエストボディの読み込みエラー: {e}")
        
        response = await call_next(request)
        
        # セキュリティヘッダーを追加
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """レート制限ミドルウェア"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
    
    async def dispatch(self, request: Request, call_next):
        # ヘルスチェックエンドポイントはスキップ
        if request.url.path == "/health":
            return await call_next(request)
        
        # クライアント識別子を取得（IPアドレスまたはAPIキー）
        client_id = self._get_client_id(request)
        
        # レート制限チェック
        if not self._check_rate_limit(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="レート制限を超過しました。しばらく待ってから再試行してください。"
            )
        
        response = await call_next(request)
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """クライアント識別子を取得"""
        # APIキーがある場合はそれを使用
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"
        
        # なければIPアドレスを使用
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """レート制限をチェック"""
        current_time = time.time()
        minute_ago = current_time - 60
        
        # 1分以内のリクエストをフィルタ
        requests = _rate_limit_storage[client_id]
        requests[:] = [req_time for req_time in requests if req_time > minute_ago]
        
        # レート制限チェック
        if len(requests) >= self.requests_per_minute:
            logger.warning(f"レート制限超過: {client_id}")
            return False
        
        # リクエストを記録
        requests.append(current_time)
        return True


def setup_cors(app):
    """CORS設定"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 本番環境では特定のオリジンを指定
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def verify_api_key(api_key: Optional[str] = None) -> bool:
    """
    APIキーを検証
    
    Args:
        api_key: APIキー
    
    Returns:
        有効かどうか
    """
    if not api_key:
        return False
    
    # 簡易実装: 環境変数から許可されたAPIキーを取得
    # 本番環境ではデータベースや専用サービスを使用
    settings = Settings()
    allowed_keys = getattr(settings, "ALLOWED_API_KEYS", "").split(",")
    allowed_keys = [k.strip() for k in allowed_keys if k.strip()]
    
    if not allowed_keys:
        # APIキーが設定されていない場合は認証をスキップ（開発環境用）
        logger.warning("ALLOWED_API_KEYSが設定されていません。認証をスキップします。")
        return True
    
    return api_key in allowed_keys


def get_api_key_from_request(request: Request) -> Optional[str]:
    """リクエストからAPIキーを取得"""
    # X-API-Keyヘッダーから取得
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    
    # Authorizationヘッダーから取得（Bearerトークン）
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    
    return None

