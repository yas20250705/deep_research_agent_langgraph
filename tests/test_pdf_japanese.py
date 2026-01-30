# -*- coding: utf-8 -*-
"""日本語PDF生成の動作確認"""


def test_register_japanese_font():
    from src.utils.pdf_generator import _register_japanese_font
    font = _register_japanese_font()
    assert font in ("HeiseiKakuGo-W5", "HeiseiMin-W3", "JapanesePDFFont", "Helvetica")


def test_generate_source_pdf_japanese():
    from src.utils.pdf_generator import generate_source_pdf
    source = {
        "title": "日本語タイトル",
        "url": "https://example.com",
        "summary": "これは要約です。",
    }
    buf = generate_source_pdf(source, "テスト")
    assert buf is not None
    assert len(buf.getvalue()) > 100
