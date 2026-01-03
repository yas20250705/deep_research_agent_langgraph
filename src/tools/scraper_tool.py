"""
Webスクレイピングツール

指定URLのコンテンツを取得するツール
"""

from langchain_core.tools import tool
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import logging

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    """
    URL検証
    
    Args:
        url: 検証対象URL
    
    Returns:
        有効なURLかどうか
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ["http", "https"]
    except Exception:
        return False


def extract_main_content(soup: BeautifulSoup) -> str:
    """
    メインコンテンツを抽出
    
    優先順位:
    1. <main>タグ
    2. <article>タグ
    3. <div class="content">等
    4. <body>タグ（フォールバック）
    
    Args:
        soup: BeautifulSoupオブジェクト
    
    Returns:
        抽出されたテキスト
    """
    # mainタグ
    main = soup.find("main")
    if main:
        return main.get_text(separator=" ", strip=True)
    
    # articleタグ
    article = soup.find("article")
    if article:
        return article.get_text(separator=" ", strip=True)
    
    # コンテンツクラス
    content_div = soup.find("div", class_=re.compile("content|main|article", re.I))
    if content_div:
        return content_div.get_text(separator=" ", strip=True)
    
    # フォールバック: body
    body = soup.find("body")
    if body:
        # スクリプトとスタイルを除去
        for script in body(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        return body.get_text(separator=" ", strip=True)
    
    return ""


def clean_text(text: str) -> str:
    """
    テキストをクリーンアップ
    
    - 余分な空白を除去
    - 改行を正規化
    
    Args:
        text: クリーンアップ対象テキスト
    
    Returns:
        クリーンアップされたテキスト
    """
    # 複数の空白を1つに
    text = re.sub(r'\s+', ' ', text)
    # 改行を正規化
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()


@tool
def web_scraper_tool(url: str) -> str:
    """
    指定URLのコンテンツをスクレイピング
    
    Args:
        url: スクレイピング対象URL
    
    Returns:
        ページのテキストコンテンツ
    
    Raises:
        ValueError: URLが無効な場合
        requests.RequestException: HTTPリクエストエラー
    """
    
    # URL検証
    if not is_valid_url(url):
        raise ValueError(f"無効なURL: {url}")
    
    # リクエスト実行
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (Research Agent Bot)"
        }
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        
        # HTMLパース
        soup = BeautifulSoup(response.content, "html.parser")
        
        # メインコンテンツ抽出
        content = extract_main_content(soup)
        
        # テキストクリーンアップ
        cleaned = clean_text(content)
        
        logger.info(f"スクレイピング完了: URL={url}, 文字数={len(cleaned)}")
        
        return cleaned
        
    except requests.RequestException as e:
        logger.error(f"リクエストエラー: URL={url}, エラー={str(e)}")
        raise
    except Exception as e:
        logger.error(f"スクレイピングエラー: URL={url}, エラー={str(e)}")
        raise




