"""
PDF生成ユーティリティ

URLからPDFを生成する機能
"""

from typing import Optional, Dict
from io import BytesIO
from urllib.parse import urlparse
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# PDF生成用のインポート
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# PDFテキスト抽出用のインポート
try:
    import PyPDF2
    PDF_TEXT_EXTRACTION_AVAILABLE = True
except ImportError:
    PDF_TEXT_EXTRACTION_AVAILABLE = False

# Webスクレイピング用のインポート（BeautifulSoup があれば取得・抽出可能）
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
SCRAPING_AVAILABLE = BS4_AVAILABLE  # BeautifulSoup のみでもHTML取得・抽出は可能


def _register_japanese_font():
    """日本語フォントを登録"""
    try:
        # 日本語フォントを登録（MS Gothic等）
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        return 'HeiseiKakuGo-W5'
    except:
        try:
            # フォールバック
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
            return 'HeiseiMin-W3'
        except:
            # デフォルトフォント
            return 'Helvetica'


def _download_pdf_file(url: str) -> Optional[bytes]:
    """PDFファイルをダウンロード"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,application/octet-stream,*/*",
        }
        response = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
            return response.content
        return None
    except Exception as e:
        logger.warning(f"PDFファイルのダウンロードに失敗: {url}, エラー: {e}")
        return None


def _get_html_content(url: str) -> Optional[str]:
    """
    取得方法の多段階化: requests.get を優先（ブロックされにくい）、失敗時は trafilatura.fetch_url
    """
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en;q=0.9",
    }
    if origin:
        headers["Referer"] = origin + "/"
    # 1. requests.get を優先（ブラウザ風ヘッダーでブロックされにくい）
    try:
        response = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
        response.raise_for_status()
        html = response.content.decode(response.encoding or "utf-8", errors="replace")
        if html and html.strip():
            return html
    except Exception as e:
        logger.info(f"requests.get 失敗: {url}, エラー: {e}")
    # 2. フォールバック: trafilatura.fetch_url
    if TRAFILATURA_AVAILABLE:
        try:
            html = trafilatura.fetch_url(url)
            if html and html.strip():
                return html
        except Exception as e:
            logger.info(f"trafilatura.fetch_url 失敗: {url}, エラー: {e}")
    return None


def _extract_text_from_html(html_content: str, url: str) -> Optional[str]:
    """
    抽出の多段フォールバック: trafilatura.extract → BeautifulSoup（script/style のみ除去）→ 全文
    """
    if not html_content or not html_content.strip():
        return None
    # 1. trafilatura.extract(html, url=url, favor_recall=True)
    if TRAFILATURA_AVAILABLE:
        try:
            content = trafilatura.extract(html_content, url=url, favor_recall=True)
            if content and content.strip():
                return content
        except Exception:
            pass
    # 2. BeautifulSoup: script/style のみ除去して本文を取得（nav/header/footer は残して取りこぼしを防ぐ）
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        # main / article / body の順で取得
        for node in (soup.find("main"), soup.find("article"), soup.find("body")):
            if node:
                text = node.get_text(separator="\n", strip=True)
                if text and len(text.strip()) > 50:
                    return text
        # いずれも空または短い場合は全文を使用
        text = soup.get_text(separator="\n", strip=True)
        if text and text.strip():
            return text
    except Exception as e:
        logger.info(f"BeautifulSoup 抽出失敗: {url}, エラー: {e}")
    return None


def _fetch_url_content(url: str) -> Optional[str]:
    """URL先のページコンテンツを取得（取得・抽出の多段階化）"""
    if not SCRAPING_AVAILABLE:
        return None
    try:
        html_content = _get_html_content(url)
        if not html_content:
            return None
        return _extract_text_from_html(html_content, url)
    except Exception as e:
        logger.warning(f"URLコンテンツの取得に失敗: {url}, エラー: {e}")
        return None


def generate_source_pdf(source: Dict, theme: str = "参照ソース") -> BytesIO:
    """
    参照ソースのURLからPDFを生成
    
    Args:
        source: ソース情報（title, url, summary等）
        theme: テーマ（デフォルト: "参照ソース"）
    
    Returns:
        PDFのBytesIOオブジェクト
    """
    if not PDF_AVAILABLE:
        raise ImportError("reportlabがインストールされていません")
    
    title = source.get('title', 'N/A')
    url = source.get('url', 'N/A')
    summary = source.get('summary', '')
    relevance_score = source.get('relevance_score')
    source_type = source.get('source', '')
    
    # PDFファイルのURLかどうかをチェック
    is_pdf_url = url != 'N/A' and (url.lower().endswith('.pdf') or '.pdf' in url.lower())
    
    # PDFファイルの場合は、そのままダウンロードして返す
    if is_pdf_url and PDF_TEXT_EXTRACTION_AVAILABLE:
        pdf_content = _download_pdf_file(url)
        if pdf_content:
            return BytesIO(pdf_content)
    
    # HTMLページまたはPDFファイルの取得に失敗した場合、テキスト形式でPDFを生成
    japanese_font = _register_japanese_font()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # カスタムスタイル（日本語フォントを使用）
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=japanese_font,
        fontSize=18,
        textColor=(0, 0, 0),
        spaceAfter=30,
        alignment=TA_LEFT
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=japanese_font,
        fontSize=14,
        textColor=(0, 0, 0),
        spaceAfter=12,
        spaceBefore=12,
        alignment=TA_LEFT
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=10,
        textColor=(0, 0, 0),
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=14
    )
    
    url_style = ParagraphStyle(
        'CustomURL',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=9,
        textColor=(0, 0, 0.8),
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    content_style = ParagraphStyle(
        'CustomContent',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=9,
        textColor=(0, 0, 0),
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=12
    )
    
    # タイトル
    story.append(Paragraph(f"<b>{theme} - 参照ソースページ内容</b>", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 20))
    
    # ソース情報
    story.append(Paragraph(f"<b>{title}</b>", heading_style))
    
    # URL
    if url != 'N/A':
        story.append(Paragraph(f"<b>URL:</b> {url}", url_style))
        
        # PDFファイルの場合は情報のみ表示
        if is_pdf_url:
            pdf_content = _download_pdf_file(url)
            if pdf_content and PDF_TEXT_EXTRACTION_AVAILABLE:
                try:
                    pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
                    story.append(Paragraph(f"<b>PDFファイル:</b> {len(pdf_reader.pages)}ページ", normal_style))
                except:
                    story.append(Paragraph("<b>PDFファイル:</b> 取得済み", normal_style))
                story.append(Paragraph("（このPDFファイルはそのまま含まれています）", normal_style))
    
    # 要約
    if summary:
        story.append(Spacer(1, 6))
        summary_escaped = summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        story.append(Paragraph(f"<b>要約:</b> {summary_escaped}", normal_style))
    
    # ページ内容
    if url != 'N/A' and not is_pdf_url:
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>ページ内容:</b>", normal_style))
        
        page_content = _fetch_url_content(url)
        if page_content:
            # HTMLエスケープ処理
            page_content_escaped = page_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # 長すぎる場合は切り詰め（10000文字程度）
            if len(page_content_escaped) > 10000:
                page_content_escaped = page_content_escaped[:10000] + "\n\n... (内容が長いため一部を省略しています)"
            # 段落ごとに分割して追加
            paragraphs = page_content_escaped.split('\n\n')
            for para in paragraphs[:50]:  # 最大50段落まで
                if para.strip():
                    story.append(Paragraph(para.strip(), content_style))
                    story.append(Spacer(1, 3))
        else:
            story.append(Paragraph("ページ内容の取得に失敗しました。", content_style))
            if summary:
                story.append(Paragraph("以下はレポート生成時の要約です。", content_style))
                story.append(Spacer(1, 3))
                summary_escaped_fallback = summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                if len(summary_escaped_fallback) > 5000:
                    summary_escaped_fallback = summary_escaped_fallback[:5000] + "..."
                for para in summary_escaped_fallback.split('\n\n'):
                    if para.strip():
                        story.append(Paragraph(para.strip(), content_style))
                        story.append(Spacer(1, 3))
            else:
                pass  # 要約も無い場合は「ページ内容の取得に失敗しました。」のみ（上で既に追加済み）
    
    # 関連性スコア
    if relevance_score is not None:
        story.append(Paragraph(f"<b>関連性スコア:</b> {relevance_score:.2f}", normal_style))
    
    # ソースタイプ
    if source_type:
        story.append(Paragraph(f"<b>ソース:</b> {source_type}", normal_style))
    
    # PDFを生成
    doc.build(story)
    buffer.seek(0)
    return buffer
