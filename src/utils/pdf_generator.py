"""
PDF生成ユーティリティ

URLからPDFを生成する機能
"""

from typing import Optional, Dict
from io import BytesIO
from urllib.parse import urlparse
import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# デバッグログ: 環境変数 PDF_DEBUG=1 または true で有効
_PDF_DEBUG = os.environ.get("PDF_DEBUG", "").strip().lower() in ("1", "true", "yes")


def _debug_log(msg: str, **kwargs) -> None:
    """デバッグ用ログ（PDF_DEBUG が有効なときのみ出力）"""
    if _PDF_DEBUG:
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.debug(f"[PDF] {msg}" + (f" {extra}" if extra else ""))


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
    """日本語フォントを登録（CID → TTF/TTC の順で試行）"""
    # 1. Adobe CID フォント（Acrobat Reader 等がある環境）
    try:
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        return 'HeiseiKakuGo-W5'
    except Exception:
        pass
    try:
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
        return 'HeiseiMin-W3'
    except Exception:
        pass
    # 2. Windows 等の TTF/TTC 日本語フォント（Helvetica は日本語非対応のため必須）
    try:
        from reportlab.pdfbase.ttfonts import TTFont
        font_name = "JapanesePDFFont"
        windir = os.environ.get("WINDIR", "C:\\Windows")
        fonts_dir = os.path.join(windir, "Fonts")
        candidates = [
            ("msgothic.ttc", 0),
            ("msgothic.ttf", None),
            ("yugothm.ttc", 0),
            ("meiryo.ttc", 0),
            ("YuGothM.ttc", 0),
        ]
        for fname, subfont in candidates:
            path = os.path.join(fonts_dir, fname)
            if os.path.isfile(path):
                try:
                    if subfont is not None:
                        pdfmetrics.registerFont(TTFont(font_name, path, subfontIndex=subfont))
                    else:
                        pdfmetrics.registerFont(TTFont(font_name, path))
                    return font_name
                except Exception as e:
                    logger.debug(f"TTF登録失敗: {path}, {e}")
                    continue
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"TTFフォント検索失敗: {e}")
    logger.warning(
        "日本語フォントが見つかりません。Heisei/CID または Windows Fonts の msgothic/yugothm/meiryo を利用可能にしてください。"
    )
    return "Helvetica"


def _safe_text_for_paragraph(text: str, font_name: str) -> str:
    """Helvetica のときは非ASCIIを置換して reportlab の描画エラーを防ぐ"""
    if not text or font_name != "Helvetica":
        return text or ""
    return "".join(c if ord(c) < 128 else "?" for c in text)


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


# 日本語ページでよく使われるエンコーディング（試行順）
_JAPANESE_ENCODINGS = ("utf-8", "cp932", "euc-jp", "iso-2022-jp", "shift_jis")

# サーバーが返す charset 名を Python のエンコーディング名に正規化（大文字・ハイフン等の違いを吸収）
_ENCODING_ALIASES = {
    "shift_jis": "cp932",
    "shift-jis": "cp932",
    "windows-31j": "cp932",
    "ms932": "cp932",
    "x-sjis": "cp932",
    "csshiftjis": "cp932",
}


def _normalize_encoding(enc: Optional[str]) -> Optional[str]:
    """Content-Type の charset を Python で使えるエンコーディング名に正規化"""
    if not enc or not enc.strip():
        return None
    key = enc.strip().lower().replace("-", "_").replace(" ", "")
    return _ENCODING_ALIASES.get(key, key)


def _decode_html_content(raw: bytes, preferred_encoding: Optional[str] = None) -> Optional[str]:
    """
    バイト列を日本語対応のエンコーディングでデコードする。
    response.encoding が誤っている日本語ページ（Shift_JIS 等）でも正しく読めるようにする。
    """
    if not raw or not raw.strip():
        return None
    encodings_to_try = []
    if preferred_encoding:
        normalized = _normalize_encoding(preferred_encoding)
        if normalized and normalized not in encodings_to_try:
            encodings_to_try.append(normalized)
    for enc in _JAPANESE_ENCODINGS:
        if enc not in encodings_to_try:
            encodings_to_try.append(enc)
    for enc in encodings_to_try:
        try:
            text = raw.decode(enc, errors="strict")
            # 置換文字が多すぎる場合は別のエンコーディングを試す
            if "\ufffd" in text and text.count("\ufffd") > min(50, len(text) // 20):
                continue
            if text.strip():
                _debug_log("HTMLデコード成功", encoding=enc, length=len(text))
                return text
        except (LookupError, UnicodeDecodeError):
            continue
    # 厳密に失敗した場合は replace で utf-8 のみ
    try:
        text = raw.decode("utf-8", errors="replace")
        _debug_log("HTMLデコード fallback utf-8 replace", length=len(text))
        return text
    except Exception:
        return None


def _get_html_content(url: str) -> Optional[str]:
    """
    取得方法の多段階化: requests.get を優先（ブロックされにくい）、失敗時は trafilatura.fetch_url
    日本語ページは Shift_JIS / EUC-JP 等に対応するため複数エンコーディングでデコードを試行する。
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
        # 日本語ページ対応: 複数エンコーディングでデコードを試行（charset 未指定時は apparent_encoding を利用）
        enc = response.encoding
        if not enc or (enc and enc.lower() in ("iso-8859-1", "latin-1")):
            enc = getattr(response, "apparent_encoding", None)
        enc = _normalize_encoding(enc) if enc else None
        html = _decode_html_content(response.content, enc)
        if html and html.strip():
            _debug_log("HTML取得成功 requests", url=url, html_len=len(html))
            return html
        logger.info(f"日本語ページのHTML取得: レスポンスは成功したがデコード後が空: url={url}")
    except Exception as e:
        logger.info(f"requests.get 失敗: {url}, エラー: {e}")
    # 2. フォールバック: trafilatura.fetch_url
    if TRAFILATURA_AVAILABLE:
        try:
            html = trafilatura.fetch_url(url)
            if html and html.strip():
                _debug_log("HTML取得成功 trafilatura.fetch_url", url=url, html_len=len(html))
                return html
        except Exception as e:
            logger.info(f"trafilatura.fetch_url 失敗: {url}, エラー: {e}")
    logger.warning(f"日本語ウェブページ等のHTML取得に失敗: url={url}")
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
                _debug_log("本文抽出成功 trafilatura", url=url, text_len=len(content))
                return content
        except Exception as e:
            _debug_log("trafilatura.extract 失敗", url=url, error=str(e))
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
                    _debug_log("本文抽出成功 BeautifulSoup", url=url, text_len=len(text))
                    return text
        # いずれも空または短い場合は全文を使用
        text = soup.get_text(separator="\n", strip=True)
        if text and text.strip():
            _debug_log("本文抽出成功 BeautifulSoup 全文", url=url, text_len=len(text))
            return text
    except Exception as e:
        logger.info(f"BeautifulSoup 抽出失敗: {url}, エラー: {e}")
    logger.info(f"日本語ページの本文抽出に失敗: url={url}（HTMLは取得済み）")
    return None


def _fetch_url_content(url: str) -> Optional[str]:
    """URL先のページコンテンツを取得（取得・抽出の多段階化）"""
    if not SCRAPING_AVAILABLE:
        _debug_log("ページコンテンツ取得 スキップ SCRAPING_AVAILABLE=False", url=url)
        return None
    try:
        html_content = _get_html_content(url)
        if not html_content:
            _debug_log("ページコンテンツ取得 失敗 HTMLなし", url=url)
            return None
        text = _extract_text_from_html(html_content, url)
        if text:
            _debug_log("ページコンテンツ取得 成功", url=url, content_len=len(text))
        else:
            _debug_log("ページコンテンツ取得 失敗 抽出テキストなし", url=url)
        return text
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
    
    _debug_log("generate_source_pdf 開始", url=url, title=title[:50] if title else "")
    
    # PDFファイルのURLかどうかをチェック
    is_pdf_url = url != 'N/A' and (url.lower().endswith('.pdf') or '.pdf' in url.lower())
    
    # PDFファイルの場合は、そのままダウンロードして返す（PyPDF2 は不要）
    if is_pdf_url:
        pdf_content = _download_pdf_file(url)
        if pdf_content:
            _debug_log("PDFファイル ダウンロード成功", url=url, size=len(pdf_content))
            return BytesIO(pdf_content)
        logger.warning(f"PDFファイルのダウンロードに失敗（バイナリ取得できず）: url={url}, title={title}")
    
    # HTMLページまたはPDFファイルの取得に失敗した場合、テキスト形式でPDFを生成
    japanese_font = _register_japanese_font()
    _debug_log("日本語フォント", font=japanese_font)
    
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
    
    def _p(s: str, style):
        """Paragraph に渡す文字列をフォントに応じてサニタイズ"""
        story.append(Paragraph(_safe_text_for_paragraph(s, japanese_font), style))

    # タイトル
    _p(f"<b>{theme} - 参照ソースページ内容</b>", title_style)
    story.append(Spacer(1, 12))
    _p(f"作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}", normal_style)
    story.append(Spacer(1, 20))
    
    # ソース情報
    _p(f"<b>{title}</b>", heading_style)
    
    # URL
    if url != 'N/A':
        _p(f"<b>URL:</b> {url}", url_style)
        
        # PDFファイルの場合は情報のみ表示
        if is_pdf_url:
            pdf_content = _download_pdf_file(url)
            if pdf_content and PDF_TEXT_EXTRACTION_AVAILABLE:
                try:
                    pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
                    _p(f"<b>PDFファイル:</b> {len(pdf_reader.pages)}ページ", normal_style)
                except Exception:
                    _p("<b>PDFファイル:</b> 取得済み", normal_style)
                _p("（このPDFファイルはそのまま含まれています）", normal_style)
    
    # 要約
    if summary:
        story.append(Spacer(1, 6))
        summary_escaped = summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        _p(f"<b>要約:</b> {summary_escaped}", normal_style)
    
    # ページ内容
    if url != 'N/A' and not is_pdf_url:
        story.append(Spacer(1, 6))
        _p("<b>ページ内容:</b>", normal_style)
        
        page_content = _fetch_url_content(url)
        if page_content:
            _debug_log("ページ内容 取得成功（HTML→PDF）", url=url, content_len=len(page_content))
            # HTMLエスケープ処理
            page_content_escaped = page_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # 長すぎる場合は切り詰め（10000文字程度）
            if len(page_content_escaped) > 10000:
                page_content_escaped = page_content_escaped[:10000] + "\n\n... (内容が長いため一部を省略しています)"
            # 段落ごとに分割して追加
            paragraphs = page_content_escaped.split('\n\n')
            for para in paragraphs[:50]:  # 最大50段落まで
                if para.strip():
                    _p(para.strip(), content_style)
                    story.append(Spacer(1, 3))
        else:
            logger.warning(
                f"日本語ウェブページのページ内容取得に失敗（PDFは要約のみで生成）: url={url}, title={title}"
            )
            _p("ページ内容の取得に失敗しました。", content_style)
            if summary:
                _p("以下はレポート生成時の要約です。", content_style)
                story.append(Spacer(1, 3))
                summary_escaped_fallback = summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                if len(summary_escaped_fallback) > 5000:
                    summary_escaped_fallback = summary_escaped_fallback[:5000] + "..."
                for para in summary_escaped_fallback.split('\n\n'):
                    if para.strip():
                        _p(para.strip(), content_style)
                        story.append(Spacer(1, 3))
    
    # 関連性スコア
    if relevance_score is not None:
        _p(f"<b>関連性スコア:</b> {relevance_score:.2f}", normal_style)
    
    # ソースタイプ
    if source_type:
        _p(f"<b>ソース:</b> {source_type}", normal_style)
    
    # PDFを生成（日本語ウェブページのPDF作成失敗をログに記録）
    try:
        doc.build(story)
        buffer.seek(0)
        _debug_log("generate_source_pdf 成功（HTML→テキストPDF）", url=url, size=len(buffer.getvalue()))
        return buffer
    except Exception as e:
        logger.error(
            f"日本語ウェブページのPDF作成に失敗: url={url}, title={title}, error={type(e).__name__}: {e}",
            exc_info=True,
        )
        raise
