"""
セキュリティユーティリティ

セキュリティ関連の機能を提供
"""

import re
import html
from typing import Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def sanitize_input(text: str, max_length: Optional[int] = None) -> str:
    """
    ユーザー入力をサニタイズ
    
    Args:
        text: 入力テキスト
        max_length: 最大長（Noneの場合は制限なし）
    
    Returns:
        サニタイズされたテキスト
    """
    if not isinstance(text, str):
        raise ValueError("入力は文字列である必要があります")
    
    # HTMLエスケープ
    sanitized = html.escape(text)
    
    # 制御文字を除去
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    
    # 最大長チェック
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        logger.warning(f"入力が最大長を超えました。切り詰めました: {max_length}文字")
    
    return sanitized


def validate_url(url: str) -> bool:
    """
    URLの妥当性を検証
    
    Args:
        url: 検証するURL
    
    Returns:
        有効なURLかどうか
    """
    try:
        result = urlparse(url)
        # スキームとネットロックの両方が必要
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_uuid(uuid_string: str) -> bool:
    """
    UUIDの妥当性を検証
    
    Args:
        uuid_string: 検証するUUID文字列
    
    Returns:
        有効なUUIDかどうか
    """
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_string))


def sanitize_error_message(error: Exception, include_details: bool = False) -> str:
    """
    エラーメッセージをサニタイズ（情報漏洩を防ぐ）
    
    Args:
        error: エラーオブジェクト
        include_details: 詳細情報を含めるか（本番環境ではFalse推奨）
    
    Returns:
        サニタイズされたエラーメッセージ
    """
    if include_details:
        return str(error)
    else:
        # 一般的なエラーメッセージのみ返す
        error_type = type(error).__name__
        return f"エラーが発生しました: {error_type}"


def check_sql_injection(text: str) -> bool:
    """
    SQLインジェクションの可能性をチェック
    
    Args:
        text: チェックするテキスト
    
    Returns:
        SQLインジェクションの可能性があるかどうか
    """
    sql_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"('|(\\')|(;)|(\|)|(\*)|(%)|(\+))",
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"SQLインジェクションの可能性を検出: {text[:50]}...")
            return True
    
    return False


def check_xss(text: str) -> bool:
    """
    XSS（クロスサイトスクリプティング）の可能性をチェック
    
    Args:
        text: チェックするテキスト
    
    Returns:
        XSSの可能性があるかどうか
    """
    xss_patterns = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    
    for pattern in xss_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"XSSの可能性を検出: {text[:50]}...")
            return True
    
    return False


def validate_theme(theme: str) -> tuple[bool, Optional[str]]:
    """
    調査テーマの妥当性を検証
    
    Args:
        theme: 調査テーマ
    
    Returns:
        (有効かどうか, エラーメッセージ)
    """
    if not theme or not theme.strip():
        return False, "テーマが空です"
    
    if len(theme) > 500:
        return False, "テーマが長すぎます（最大500文字）"
    
    if check_sql_injection(theme):
        return False, "無効な文字が含まれています"
    
    if check_xss(theme):
        return False, "無効な文字が含まれています"
    
    return True, None

