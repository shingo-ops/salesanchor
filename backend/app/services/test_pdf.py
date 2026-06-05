"""簡易テスト PDF 生成（API連携 Googleドライブ 動作確認用）。

po_renderer と同じ日本語フォント登録を流用し、中央に1行の文字列（既定
"テスト"）を描いた A4 1ページの PDF を bytes で返す。フォントは Docker に
導入済みの IPA ゴシック（fonts-ipafont-gothic）を使用する。

変更履歴:
  2026-06-06: 初版
"""

from __future__ import annotations

import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.services.po_renderer import _register_japanese_font


def render_test_pdf(text: str = "テスト") -> bytes:
    """中央に text を描いたテスト用 PDF を bytes で返す。"""
    font = _register_japanese_font()
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    pdf.setFont(font, 48)
    pdf.drawCentredString(width / 2, height / 2, text)
    pdf.setFont(font, 12)
    pdf.drawCentredString(width / 2, height / 2 - 40, "salesanchor Google ドライブ 連携テスト")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
