"""
URL要約ユーティリティ

LLMを使用してURLのコンテンツを日本語で要約する機能
"""

from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
import logging
from src.config.settings import Settings
from src.utils.llm_factory import get_llm_from_settings

logger = logging.getLogger(__name__)

# LLMのトークン制限を考慮したコンテンツの最大長（概算）
# 1文字 ≈ 0.25トークン（日本語の場合）、安全のため余裕を持たせる
MAX_CONTENT_LENGTH_FOR_LLM = 8000  # 約2000トークン分


def truncate_content(content: str, max_length: int = MAX_CONTENT_LENGTH_FOR_LLM) -> str:
    """
    コンテンツを指定された長さに切り詰める
    
    Args:
        content: 切り詰めるコンテンツ
        max_length: 最大長
    
    Returns:
        切り詰められたコンテンツ
    """
    if len(content) <= max_length:
        return content
    
    # 文の途中で切らないように、最後の句点まで戻る
    truncated = content[:max_length]
    last_period = truncated.rfind('。')
    last_newline = truncated.rfind('\n')
    
    # 句点または改行の位置で切る
    cut_position = max(last_period, last_newline)
    if cut_position > max_length * 0.8:  # 80%以上残っている場合のみ
        return truncated[:cut_position + 1]
    
    return truncated


def summarize_url_content(
    content: str,
    url: str,
    settings: Settings,
    max_length: Optional[int] = None
) -> str:
    """
    URLのコンテンツをLLMで要約
    
    Args:
        content: URLのコンテンツ（テキスト）
        url: URL（ログ用）
        settings: Settingsインスタンス
        max_length: 最大文字数（Noneの場合はsettings.SUMMARY_MAX_LENGTHを使用）
    
    Returns:
        要約されたテキスト（日本語）
    """
    # max_lengthの決定
    if max_length is None:
        max_length = settings.SUMMARY_MAX_LENGTH
    
    # コンテンツが空の場合は空文字を返す
    if not content or not content.strip():
        logger.warning(f"要約スキップ（コンテンツが空）: URL={url}")
        return ""
    
    # LLMインスタンスの取得
    try:
        llm = get_llm_from_settings(settings, temperature=0.3)
    except Exception as e:
        logger.error(f"LLMインスタンス取得エラー: URL={url}, エラー={e}")
        # フォールバック: 元のコンテンツの先頭部分を返す
        return content[:max_length] if len(content) > max_length else content
    
    # コンテンツが長すぎる場合は切り詰める
    content_to_summarize = truncate_content(content, MAX_CONTENT_LENGTH_FOR_LLM)
    
    # プロンプトの作成
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "あなたは情報を要約する専門家です。与えられたコンテンツの要点を日本語で簡潔にまとめてください。"),
        ("human", """以下のURLのコンテンツの要点を日本語で{max_length}文字以内でまとめてください。

URL: {url}

コンテンツ:
{content}

要点を{max_length}文字以内でまとめてください。""")
    ])
    
    # LLM呼び出し
    try:
        chain = prompt_template | llm
        response = chain.invoke({
            "max_length": max_length,
            "url": url,
            "content": content_to_summarize
        })
        
        # レスポンスからテキストを抽出
        summary = response.content if hasattr(response, 'content') else str(response)
        
        # 文字数制限を適用（念のため）
        if len(summary) > max_length:
            summary = summary[:max_length]
            # 最後の句点まで戻る
            last_period = summary.rfind('。')
            if last_period > max_length * 0.8:
                summary = summary[:last_period + 1]
        
        logger.info(f"要約完了: URL={url}, 文字数={len(summary)}/{max_length}")
        return summary.strip()
        
    except Exception as e:
        logger.error(f"LLM要約エラー: URL={url}, エラー={e}")
        # フォールバック: 元のコンテンツの先頭部分を返す
        fallback = content[:max_length] if len(content) > max_length else content
        logger.warning(f"要約失敗、フォールバック使用: URL={url}, フォールバック文字数={len(fallback)}")
        return fallback
