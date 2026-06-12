"""FedEx Label Validation 申請支援サービス（ADR-129）。

テナントが FedEx 国際配送（IP / IE / IPE / FICP）の Label Validation を
申請するためのカバーシート PDF 自動生成とメール文面生成を提供する。

カバーシート:
  - reportlab（po_renderer.py と同じパターン）で A4 PDF を生成
  - テナントプロフィール（tenant_profile）から会社名・住所・連絡先を取得
  - FedEx アカウント番号（Sandbox）を記載

メール文面:
  - 構造化テキスト（件名・本文）を返す
  - FedEx Label Validation チーム宛の英文メール

変更履歴:
  2026-06-12: 初版（ADR-129）
"""
from __future__ import annotations

import io
import logging
from datetime import date
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import tenant_table_ref
from app.services.po_renderer import register_japanese_font

logger = logging.getLogger(__name__)

# ADR-129: 申請対象サービス
_SERVICES = [
    ("IP",   "INTERNATIONAL_PRIORITY",              "FedEx International Priority"),
    ("IE",   "INTERNATIONAL_ECONOMY",               "FedEx International Economy"),
    ("IPE",  "FEDEX_INTERNATIONAL_PRIORITY_EXPRESS","FedEx International Priority Express"),
    ("FICP", "FEDEX_INTERNATIONAL_CONNECT_PLUS",    "FedEx International Connect Plus"),
]


# ---------------------------------------------------------------------------
# テナントプロフィール取得
# ---------------------------------------------------------------------------


async def get_tenant_profile(db: AsyncSession, tenant_id: int) -> dict:
    """テナントプロフィールを取得する。"""
    # M2: tenant_table_ref を使用して SQLite(pytest) / PostgreSQL の差異を吸収する
    tp = tenant_table_ref(db, tenant_id, "tenant_profile")
    row = (await db.execute(
        text(f"""
            SELECT company_name, company_name_en, address, phone, email
            FROM {tp}
            ORDER BY id LIMIT 1
        """),
    )).mappings().first()
    if row is None:
        return {"company_name": None, "company_name_en": None, "address": None, "phone": None, "email": None}
    return dict(row)


# ---------------------------------------------------------------------------
# カバーシート PDF 生成
# ---------------------------------------------------------------------------


def generate_cover_sheet_pdf(
    company_name: Optional[str],
    company_name_en: Optional[str],
    address: Optional[str],
    phone: Optional[str],
    email: Optional[str],
    account_number: Optional[str],
) -> bytes:
    """FedEx Label Validation 申請用カバーシート PDF（A4）を生成する。

    Returns:
        PDF バイト列（Content-Disposition: attachment でブラウザ直接ダウンロード用）
    """
    buf = io.BytesIO()
    font = register_japanese_font()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    margin_l = 20 * mm
    margin_r = w - 20 * mm
    y = h - 20 * mm

    def text_line(text_str: str, x: float, y_pos: float, size: int = 11) -> None:
        c.setFont(font, size)
        c.drawString(x, y_pos, text_str)

    def section_title(text_str: str, y_pos: float) -> float:
        c.setFont(font, 13)
        c.setFillColorRGB(0.1, 0.3, 0.7)
        c.drawString(margin_l, y_pos, text_str)
        c.setFillColorRGB(0, 0, 0)
        c.setStrokeColorRGB(0.1, 0.3, 0.7)
        c.line(margin_l, y_pos - 2 * mm, margin_r, y_pos - 2 * mm)
        c.setStrokeColorRGB(0, 0, 0)
        return y_pos - 8 * mm

    def labeled_field(label: str, value: Optional[str], y_pos: float) -> float:
        c.setFont(font, 9)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(margin_l, y_pos, label)
        c.setFillColorRGB(0, 0, 0)
        c.setFont(font, 11)
        c.drawString(margin_l + 50 * mm, y_pos, value or "—")
        return y_pos - 7 * mm

    # ── タイトル ────────────────────────────────────────────────────
    c.setFont(font, 18)
    c.setFillColorRGB(0.1, 0.3, 0.7)
    c.drawCentredString(w / 2, y, "FedEx Label Validation Application")
    y -= 7 * mm
    c.setFont(font, 12)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawCentredString(w / 2, y, "FedExラベル バリデーション申請書")
    c.setFillColorRGB(0, 0, 0)
    y -= 12 * mm

    # ── 申請日 ───────────────────────────────────────────────────────
    today_str = date.today().strftime("%Y-%m-%d")
    c.setFont(font, 10)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawRightString(margin_r, y, f"Application Date: {today_str}")
    c.setFillColorRGB(0, 0, 0)
    y -= 10 * mm

    # ── 申請者情報 ───────────────────────────────────────────────────
    y = section_title("Applicant Information（申請者情報）", y)
    y = labeled_field("Company (JA):", company_name, y)
    y = labeled_field("Company (EN):", company_name_en, y)
    y = labeled_field("Address:", address, y)
    y = labeled_field("Phone:", phone, y)
    y = labeled_field("Email:", email, y)
    y -= 5 * mm

    # ── FedEx アカウント ─────────────────────────────────────────────
    y = section_title("FedEx Account Information（FedExアカウント情報）", y)
    y = labeled_field("Account Number:", account_number, y)
    c.setFont(font, 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(margin_l, y, "（Note: Account number registered in Sandbox environment for Label Validation）")
    c.setFillColorRGB(0, 0, 0)
    y -= 12 * mm

    # ── 申請サービス一覧 ────────────────────────────────────────────
    y = section_title("Services for Validation（申請サービス一覧）", y)
    for abbr, code, name in _SERVICES:
        c.setFont(font, 11)
        c.drawString(margin_l + 5 * mm, y, f"• {name}")
        c.setFont(font, 9)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(margin_l + 5 * mm + 80 * mm, y, f"[{abbr}]  serviceType: {code}")
        c.setFillColorRGB(0, 0, 0)
        y -= 7 * mm
    y -= 5 * mm

    # ── 添付物 ──────────────────────────────────────────────────────
    y = section_title("Attachments（添付物）", y)
    for item in [
        "Test shipping labels — 4 services (PDF, printed & scanned)",
        "This cover sheet",
    ]:
        c.setFont(font, 11)
        c.drawString(margin_l + 5 * mm, y, f"• {item}")
        y -= 7 * mm
    y -= 5 * mm

    # ── 備考 ────────────────────────────────────────────────────────
    y = section_title("Notes（備考）", y)
    notes = [
        "Test labels were generated using the FedEx Sandbox environment.",
        "All labels include AWB (Air Waybill) copies (3 pages each).",
        "Please validate each service type and provide feedback.",
    ]
    for note in notes:
        c.setFont(font, 10)
        c.drawString(margin_l + 5 * mm, y, f"• {note}")
        y -= 6 * mm

    c.save()
    return buf.getvalue()


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
