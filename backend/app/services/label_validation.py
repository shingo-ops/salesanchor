"""FedEx Label Validation 申請支援サービス（ADR-129）。

テナントが FedEx 国際配送（IP / IE / IPE / FICP）の Label Validation を
申請するためのカバーシート PDF 自動生成とメール文面生成を提供する。

カバーシート:
  - FedEx 公式 Cover Sheet（Label-Cover-Sheet-form.pdf v7.0）を使用
  - pypdf + reportlab オーバーレイ方式でフォームフィールドを埋め込む
    (PDF に AcroForm なし → テキストをピクセル精度で正確な座標に描画)
  - テナントプロフィール（tenant_profile）から会社名・連絡先を取得
  - FedEx アカウント番号 / 本番 API Key を記載

メール文面:
  - 構造化テキスト（件名・本文）を返す
  - FedEx Label Validation チーム宛の英文メール

変更履歴:
  2026-06-12: 初版（ADR-129）— reportlab 自作
  2026-06-12: FedEx 公式フォームへ切り替え（pypdf overlay 方式）
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

from reportlab.pdfgen import canvas as rl_canvas
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import tenant_table_ref
from app.services.po_renderer import register_japanese_font

logger = logging.getLogger(__name__)

# 公式フォーム PDF のパス（backend/app/assets/ に同梱）
_ASSET_DIR = Path(__file__).parent.parent / "assets"
_COVER_SHEET_TEMPLATE = _ASSET_DIR / "Label-Cover-Sheet-form.pdf"

# ADR-129: 申請対象サービス（メール文面・サンプルラベル発行で参照）
_SERVICES = [
    ("IP",   "INTERNATIONAL_PRIORITY",              "FedEx International Priority"),
    ("IE",   "INTERNATIONAL_ECONOMY",               "FedEx International Economy"),
    ("IPE",  "FEDEX_INTERNATIONAL_PRIORITY_EXPRESS","FedEx International Priority Express"),
    ("FICP", "FEDEX_INTERNATIONAL_CONNECT_PLUS",    "FedEx International Connect Plus"),
]

# ---------------------------------------------------------------------------
# フォームフィールド座標（pdfminer で実測、PDF サイズ: 580.6 x 792.0 pt）
# 各フィールドの入力ボックス左上に近い位置にテキストを描画する。
# ---------------------------------------------------------------------------
# (x, y) はボックス中心 y から 2pt 下げた描画開始点（フォントサイズ 10pt 想定）
_FIELD_COORDS: dict[str, tuple[float, float]] = {
    # ボックス y0=439.2 ~ y1=466.4 → 描画 y ≈ 449
    "account_number":    (248.0, 449.0),
    # ボックス y0=420.5 ~ y1=439.2 → 描画 y ≈ 426
    "production_api_key": (248.0, 426.0),
    # ボックス y0=290.8 ~ y1=311.5 → 描画 y ≈ 297
    "company_name":      (248.0, 297.0),
    # ボックス y0=271.9 ~ y1=290.8 → 描画 y ≈ 278
    "contact_name":      (248.0, 278.0),
    # ボックス y0=253.2 ~ y1=271.9 → 描画 y ≈ 259
    "email":             (248.0, 259.0),
    # ボックス y0=234.5 ~ y1=253.2 → 描画 y ≈ 240
    "printer_model":     (248.0, 240.0),
    # ボックス y0=214.6 ~ y1=234.5 → 描画 y ≈ 221
    "printer_count":     (248.0, 221.0),
}

# チェックボックス「PDF」（Laser 行）と「Express」（Services 行）の座標
# ☐ 文字の x0 に合わせて X を描画
_CHECKBOX_PDF_XY     = (281.2, 184.3)
_CHECKBOX_EXPRESS_XY = (248.4, 161.4)


# ---------------------------------------------------------------------------
# テナントプロフィール取得
# ---------------------------------------------------------------------------


async def get_tenant_profile(db: AsyncSession, tenant_id: int) -> dict:
    """テナントプロフィールを取得する。"""
    # tenant_table_ref を使用して SQLite(pytest) / PostgreSQL の差異を吸収する
    tp = tenant_table_ref(db, tenant_id, "tenant_profile")
    row = (await db.execute(
        text(f"""
            SELECT company_name, company_name_en, address, phone, email
            FROM {tp}
            ORDER BY id LIMIT 1
        """),
    )).mappings().first()
    if row is None:
        return {
            "company_name": None,
            "company_name_en": None,
            "address": None,
            "phone": None,
            "email": None,
        }
    return dict(row)


# ---------------------------------------------------------------------------
# カバーシート PDF 生成（pypdf オーバーレイ方式）
# ---------------------------------------------------------------------------


def generate_cover_sheet_pdf(
    company_name: Optional[str],
    company_name_en: Optional[str],
    address: Optional[str],  # noqa: ARG001  (テンプレートに address 欄なし)
    phone: Optional[str],    # noqa: ARG001
    email: Optional[str],
    account_number: Optional[str],
    production_api_key: Optional[str],
    contact_name: Optional[str],
    printer_model: Optional[str],
    printer_count: Optional[str],
) -> bytes:
    """FedEx 公式 Label Validation カバーシートにフォームデータを埋め込む。

    FedEx 配布の Label-Cover-Sheet-form.pdf（AcroForm なし）を背景テンプレートとして
    読み込み、reportlab で生成したテキストオーバーレイと pypdf で合成して返す。

    Args:
        company_name_en: 英語会社名（FedEx への申請は英語が標準）
        company_name:    日本語会社名（英語名がない場合のフォールバック）
        email:           申請担当者メールアドレス（tenant_profile から取得）
        account_number:  Sandbox アカウント番号（本番 API Key と同じ番号を使用）
        production_api_key: 本番 API Key（FedEx Portal の Client ID）
        contact_name:    担当者名（フロントエンドフォーム入力）
        printer_model:   プリンターモデル名（フロントエンドフォーム入力）
        printer_count:   プリンター台数（フロントエンドフォーム入力）

    Returns:
        PDF バイト列（Content-Disposition: attachment）
    """
    from pypdf import PdfReader, PdfWriter

    # ── 1. テンプレート読み込み ─────────────────────────────────────────
    template_bytes = _COVER_SHEET_TEMPLATE.read_bytes()
    template_reader = PdfReader(io.BytesIO(template_bytes))
    template_page = template_reader.pages[0]
    page_width  = float(template_page.mediabox.width)   # 580.6 pt
    page_height = float(template_page.mediabox.height)  # 792.0 pt

    # ── 2. オーバーレイ PDF を reportlab で生成 ─────────────────────────
    # 日本語フォントを登録（担当者名等が日本語になる場合に備える）
    ja_font = register_japanese_font()

    overlay_buf = io.BytesIO()
    c = rl_canvas.Canvas(overlay_buf, pagesize=(page_width, page_height))
    c.setFont(ja_font, 10)
    c.setFillColorRGB(0, 0, 0)

    # フォームフィールド値
    # 会社名は英語名を優先（なければ日本語名）
    company_display = company_name_en or company_name or ""
    fields: dict[str, Optional[str]] = {
        "account_number":     account_number,
        "production_api_key": production_api_key,
        "company_name":       company_display,
        "contact_name":       contact_name,
        "email":              email,
        "printer_model":      printer_model,
        "printer_count":      printer_count,
    }

    for field_key, value in fields.items():
        if value:
            x, y = _FIELD_COORDS[field_key]
            # 長い文字列はボックス幅（531-248=283pt）に収まるよう切り詰める
            c.drawString(x, y, _clip_text(c, value, ja_font, max_width=280.0))

    # チェックボックス「PDF」（Laser 欄）
    _draw_checkmark(c, *_CHECKBOX_PDF_XY)
    # チェックボックス「Express」（Services Requested 欄）
    _draw_checkmark(c, *_CHECKBOX_EXPRESS_XY)

    c.save()
    overlay_buf.seek(0)

    # ── 3. テンプレート + オーバーレイ を合成 ──────────────────────────
    overlay_reader = PdfReader(overlay_buf)
    overlay_page   = overlay_reader.pages[0]

    template_page.merge_page(overlay_page)

    writer = PdfWriter()
    writer.add_page(template_page)

    out_buf = io.BytesIO()
    writer.write(out_buf)
    return out_buf.getvalue()


def _clip_text(c: rl_canvas.Canvas, text: str, font: str, max_width: float) -> str:
    """文字列がボックス幅を超える場合に末尾を切り詰めて '…' を付加する。"""
    if c.stringWidth(text, font, 10) <= max_width:
        return text
    while text and c.stringWidth(text + "…", font, 10) > max_width:
        text = text[:-1]
    return text + "…"


def _draw_checkmark(c: rl_canvas.Canvas, x: float, y: float) -> None:
    """チェックボックス（☐）の上に 'X' を描画する。

    ☐ の文字幅は約 11pt。X を中央寄せで描画する。
    """
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 2.0, y, "X")
    # フォントを元に戻す（ja_font は呼び出し元で管理）


# ---------------------------------------------------------------------------
# メール文面生成
# ---------------------------------------------------------------------------


def generate_email_template(
    company_name_en: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    account_number: Optional[str],
) -> dict:
    """FedEx Label Validation 申請用メール文面（英文）を返す。

    Returns:
        {"subject": str, "body": str}
    """
    company = company_name_en or "Our Company"
    acct = account_number or "(Account Number)"

    subject = f"FedEx International Shipping Label Validation Request – {company}"

    body = f"""\
Dear FedEx Label Validation Team,

I hope this message finds you well.

My name is [Your Name] from {company}, and I am writing to request Label Validation \
for international shipping services under our FedEx account.

FedEx Account Number: {acct}

We would like to validate the following service types:
  • FedEx International Priority (IP)
  • FedEx International Economy (IE)
  • FedEx International Priority Express (IPE)
  • FedEx International Connect Plus (FICP)

Please find attached the following documents:
  1. Test shipping labels for all four services (printed and scanned)
  2. Cover sheet with applicant information

We look forward to your validation and kindly request your guidance on any \
adjustments required.

Please feel free to contact us at the details below.

Best regards,
[Your Name]
{company}
Email: {email or "(your email)"}
Phone: {phone or "(your phone)"}
"""

    return {"subject": subject, "body": body}
