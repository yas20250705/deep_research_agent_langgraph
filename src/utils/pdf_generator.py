"""
PDF生成ユーティリティ

URLからPDFを生成する機能
"""

from typing import Optional, Dict, List, Tuple, Any
from io import BytesIO
from urllib.parse import urlparse, urljoin
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
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Image as PlatypusImage,
        Table,
        TableStyle,
    )
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


def _download_image(url: str) -> Optional[bytes]:
    """画像URLからバイナリを取得（PDF用）"""
    if not url or url.startswith("data:"):
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }
        response = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
        response.raise_for_status()
        ct = response.headers.get("Content-Type", "").lower()
        if "image/" not in ct and "octet-stream" not in ct:
            return None
        return response.content
    except Exception as e:
        _debug_log("画像ダウンロード失敗", url=url, error=str(e))
        return None


def _extract_flowables_from_html(
    html_content: str, base_url: str
) -> List[Dict[str, Any]]:
    """
    HTMLからPDF用のフロー要素を document 順で抽出する。
    見出し(h1-h6)・段落(p)・リスト(li)・画像・表をタグ名付きで返し、
    PDFで元ページに近い文字サイズ・レイアウトを再現するために使う。
    返却: [{'type': 'paragraph'|'image'|'table', 'text': '...', 'tag': 'h1'|'p'|'li'|...}, ...]
    """
    if not html_content or not BS4_AVAILABLE:
        return []
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        container = soup.find("main") or soup.find("article") or soup.find("body")
        if not container:
            return []
        block_tags = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "img", "table"]
        elements = container.find_all(block_tags)
        result: List[Dict[str, Any]] = []
        for el in elements:
            if el.name == "img":
                src = el.get("src")
                if src:
                    abs_url = urljoin(base_url, src)
                    result.append({"type": "image", "url": abs_url})
            elif el.name == "table":
                result.append({"type": "table", "soup": el})
            else:
                text = el.get_text(separator="\n", strip=True)
                if text and not el.find_parent("table"):
                    list_parent = el.find_parent("ol") or el.find_parent("ul")
                    list_kind = "ol" if el.find_parent("ol") else ("ul" if el.find_parent("ul") else None)
                    result.append({
                        "type": "paragraph",
                        "text": text,
                        "tag": el.name,
                        "list_kind": list_kind,
                    })
        return result
    except Exception as e:
        logger.debug(f"HTML flowables 抽出失敗: {base_url}, エラー: {e}")
        return []


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
    # 余白を広めにして読みやすく（約2cm = 約56pt）
    margin_pt = 56
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin_pt,
        rightMargin=margin_pt,
        topMargin=margin_pt,
        bottomMargin=margin_pt,
    )
    story = []
    styles = getSampleStyleSheet()
    
    # メタ情報用スタイル
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=japanese_font,
        fontSize=18,
        textColor=(0, 0, 0),
        spaceAfter=24,
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
    # 本文用：元ページに近い可読性（11pt・行間1.4程度）
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=11,
        textColor=(0.15, 0.15, 0.15),
        spaceAfter=8,
        spaceBefore=0,
        alignment=TA_JUSTIFY,
        leading=15,
    )
    # 見出しスタイル（Webのh1〜h6に近いサイズ・間隔）
    h1_style = ParagraphStyle(
        'H1', parent=styles['Normal'], fontName=japanese_font,
        fontSize=22, textColor=(0, 0, 0), spaceBefore=18, spaceAfter=12,
        alignment=TA_LEFT, leading=26,
    )
    h2_style = ParagraphStyle(
        'H2', parent=styles['Normal'], fontName=japanese_font,
        fontSize=18, textColor=(0, 0, 0), spaceBefore=14, spaceAfter=10,
        alignment=TA_LEFT, leading=22,
    )
    h3_style = ParagraphStyle(
        'H3', parent=styles['Normal'], fontName=japanese_font,
        fontSize=16, textColor=(0.05, 0.05, 0.05), spaceBefore=12, spaceAfter=8,
        alignment=TA_LEFT, leading=20,
    )
    h4_style = ParagraphStyle(
        'H4', parent=styles['Normal'], fontName=japanese_font,
        fontSize=14, textColor=(0.1, 0.1, 0.1), spaceBefore=10, spaceAfter=6,
        alignment=TA_LEFT, leading=18,
    )
    h5_style = ParagraphStyle(
        'H5', parent=styles['Normal'], fontName=japanese_font,
        fontSize=12, textColor=(0.1, 0.1, 0.1), spaceBefore=8, spaceAfter=6,
        alignment=TA_LEFT, leading=16,
    )
    h6_style = ParagraphStyle(
        'H6', parent=styles['Normal'], fontName=japanese_font,
        fontSize=11, textColor=(0.15, 0.15, 0.15), spaceBefore=6, spaceAfter=4,
        alignment=TA_LEFT, leading=14,
    )
    list_style = ParagraphStyle(
        'List',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=11,
        textColor=(0.15, 0.15, 0.15),
        leftIndent=22,
        spaceAfter=4,
        spaceBefore=2,
        alignment=TA_LEFT,
        leading=14,
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=9,
        textColor=(0.15, 0.15, 0.15),
        spaceAfter=2,
        alignment=TA_LEFT,
        leading=11,
    )
    tag_to_style = {
        "h1": h1_style, "h2": h2_style, "h3": h3_style,
        "h4": h4_style, "h5": h5_style, "h6": h6_style,
        "p": body_style, "li": list_style,
    }
    content_style = body_style
    
    def _p(s: str, style):
        """Paragraph に渡す文字列をフォントに応じてサニタイズ"""
        story.append(Paragraph(_safe_text_for_paragraph(s, japanese_font), style))

    # 冒頭タイトル: query（テーマ）
    _p(f"<b>{theme}</b>", title_style)
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
    
    # 関連性スコア・ソース（要約の後に表示）
    if relevance_score is not None:
        _p(f"<b>関連性スコア:</b> {relevance_score:.2f}", normal_style)
    if source_type:
        _p(f"<b>ソース:</b> {source_type}", normal_style)
    
    # ページ内容（テキスト・図・表を含む）：2行空行のあと、見出しは大きくボールド
    page_content_heading_style = ParagraphStyle(
        'PageContentHeading',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=14,
        textColor=(0, 0, 0),
        spaceAfter=8,
        spaceBefore=0,
        alignment=TA_LEFT,
        leading=18,
    )
    if url != 'N/A' and not is_pdf_url:
        story.append(Spacer(1, 12))
        story.append(Spacer(1, 12))
        _p("<b>ページ内容:</b>", page_content_heading_style)

        html_content = _get_html_content(url) if SCRAPING_AVAILABLE else None
        flowables = _extract_flowables_from_html(html_content, url) if html_content else []

        if flowables:
            _debug_log("ページ内容 取得成功（図・表含む）", url=url, flowables_count=len(flowables))
            max_image_width = 500  # ポイント（A4余白を考慮）
            flowable_count = 0
            max_flowables = 80  # 段落・画像・表の合計上限

            for item in flowables:
                if flowable_count >= max_flowables:
                    break
                kind = item.get("type")
                if kind == "paragraph":
                    text = item.get("text", "").strip()
                    if not text:
                        continue
                    tag = item.get("tag", "p")
                    style = tag_to_style.get(tag, body_style)
                    if tag == "li":
                        list_kind = item.get("list_kind")
                        bullet = "• " if list_kind == "ul" or not list_kind else "・ "
                        text = bullet + text
                    text_escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    if len(text_escaped) > 2000:
                        text_escaped = text_escaped[:2000] + " ..."
                    story.append(Paragraph(_safe_text_for_paragraph(text_escaped, japanese_font), style))
                    flowable_count += 1
                elif kind == "image":
                    img_url = item.get("url", "")
                    img_data = _download_image(img_url) if img_url else None
                    if not img_data:
                        continue
                    try:
                        buf = BytesIO(img_data)
                        buf.seek(0)
                        reader = ImageReader(buf)
                        iw, ih = reader.getSize()
                        if iw <= 0:
                            continue
                        scale = min(1.0, max_image_width / iw)
                        w = max_image_width if scale < 1 else iw
                        h = ih * scale
                        buf.seek(0)
                        img_flowable = PlatypusImage(buf, width=w, height=h)
                        story.append(img_flowable)
                        story.append(Spacer(1, 6))
                        flowable_count += 1
                    except Exception as e:
                        _debug_log("画像PDF追加スキップ", url=img_url, error=str(e))
                elif kind == "table":
                    soup_table = item.get("soup")
                    if not soup_table:
                        continue
                    rows_data = []
                    for tr in soup_table.find_all("tr"):
                        row = []
                        for cell in tr.find_all(["td", "th"]):
                            cell_text = cell.get_text(separator=" ", strip=True)
                            cell_escaped = cell_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            if len(cell_escaped) > 500:
                                cell_escaped = cell_escaped[:500] + "..."
                            row.append(
                                Paragraph(
                                    _safe_text_for_paragraph(cell_escaped, japanese_font),
                                    table_cell_style,
                                )
                            )
                        if row:
                            rows_data.append(row)
                    if rows_data:
                        try:
                            tbl = Table(rows_data)
                            tbl.setStyle(
                                TableStyle(
                                    [
                                        ("GRID", (0, 0), (-1, -1), 0.5, (0.4, 0.4, 0.4)),
                                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                    ]
                                )
                            )
                            story.append(tbl)
                            story.append(Spacer(1, 8))
                            flowable_count += 1
                        except Exception as e:
                            _debug_log("表PDF追加スキップ", error=str(e))

        if not flowables:
            page_content = _fetch_url_content(url)
            if page_content:
                _debug_log("ページ内容 取得成功（テキストのみ）", url=url, content_len=len(page_content))
                page_content_escaped = page_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                if len(page_content_escaped) > 10000:
                    page_content_escaped = page_content_escaped[:10000] + "\n\n... (内容が長いため一部を省略しています)"
                for para in page_content_escaped.split("\n\n")[:50]:
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
                    summary_escaped_fallback = summary.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    if len(summary_escaped_fallback) > 5000:
                        summary_escaped_fallback = summary_escaped_fallback[:5000] + "..."
                    for para in summary_escaped_fallback.split("\n\n"):
                        if para.strip():
                            _p(para.strip(), content_style)
                            story.append(Spacer(1, 3))
        # ページ内容の後に区切り線
        sep = Table([['']], colWidths=[doc.width], rowHeights=[8])
        sep.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 0.8, (0.3, 0.3, 0.3))]))
        story.append(sep)
    
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
