# card: 便2-2c2a 請求書・見積書の発行元を新しい表から読み、請求先の国で地域を決める（ADR-1061）

状態: カード発行（Opus、2026-11-12）。PO の設計承認と実装承認は 2026-11-12「1、推測は禁止して…確立したなら進める。」（ideal-state 54。review.md「2026-11-12 PO の設計承認」）。
設計: docs/handoff/viewer-contract-stage/design.md §3-4（発行元の会社情報・請求書の発行元区分）・§8・A40。ADR-1061。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret・DB には触らない。PR は作らない（Opus が作る）。
基準: origin/main `b6b444eff`（便2-2c1 #5460 合流後）で行番号を測った。カード起票時の origin/main `e7bc71f71` との差は §1 の外のファイルだけ（`git diff --stat b6b444eff e7bc71f71 -- 触るファイル` で 0）。行番号がずれていたら「変更前」の文で場所を探す（同じ文が決めた数と違えば BLOCKED: で停止）。
危険便か: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を変えない。表と列は便2-2c1 で本番に在る）。マージ前に Opus の審査役の APPROVE と CI 全通過を必須にする（担当の作業ではない）。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと（このカードで固めたこと。根拠つき）

- D1 発行元の読み方を新しい1か所 `backend/app/services/issuer.py` の `get_issuer(db, tenant_id, region)` にまとめる。発行元の表（便2-2c1 の `tenant_issuer_profiles`）にその地域の行があればそれだけを読む。行が無いときだけ旧来の会社情報の表 `tenant_profile` を読む（移行の間の予備）。行がある地域では空の欄を旧来の表で埋めない（混ぜると正本が2か所になる）。表の名前は `tenant_table_ref`（backend/app/auth/dependencies.py:434）で作る。
- D2 請求書の発行元区分 `issuer_region` は、請求書を作るとき（直接作成と見積からの作成の2経路）に、請求先の住所の写し `bill_to_snapshot` の国で決めて保存する。JP（大文字小文字・前後の空白を問わない）なら domestic、それ以外の国なら overseas。あとから会社の住所を変えても請求書の値は変わらない。
- D3 請求先の国が無い（既定の請求先の住所が無い・国が空）ときは、請求書を作らずに 422 `detail="bill_to_country"` を返す。理由コードを画面の理由コードの表（frontend/src/lib/apiErrorReason.ts）に足し、ja・en の文を足す（ADR-1071 の決まり: 起きたこと＋次にすること）。
- D4 PDF の3つの入口が `get_issuer` を使う: 請求書 PDF と PayPal の写し PDF は `row["issuer_region"] or "overseas"`（今ある請求書は NULL なので海外用。海外用の行が無いので旧来の表を読み、本番の PDF は今と同じ）。見積書 PDF は常に `"overseas"`（見積は地域を持たない。地域の表示と見積の扱いは便2-2c2b 以降）。
- D5 登録番号（`is_invoice_registered` が真のときだけ `registration_number`）は請求書 PDF にだけ `Registration No.: …` の1行で載せる。見積書 PDF には載せない（見積の描画は `tenant_registration_number` を渡さない）。
- D6 発注書（po_renderer）・FedEx の送り状（label_validation）・会社情報の画面（routers/tenant_profile.py）・テナント作成（services/tenant.py）は今回触らない。A40 の検査で「旧来の表を読む場所」をこの4ファイル＋issuer.py に固定する（issuer.py は1か所だけ）。
- D7 PayPal の試験用請求書（backend/app/routers/integrations.py:684）は `issuer_region` を入れないまま（NULL＝海外用の扱い）。今回は触らない。
- D8 請求書の詳細画面での地域の表示・A29 の入れられない欄・発行元の写しの保存（issuer_snapshot）は便2-2c2b 以降。今回は API の応答に `issuer_region` を足すだけ（InvoiceResponse。InvoiceDetailResponse は継承で付く）。frontend/api-contract/openapi.json を作り直してコミットする（CI「API の形」の検査が見る）。
- D9 画面: 422 `bill_to_country` を受けたら、請求書作成画面と見積詳細画面で、今のエラー表示（文は理由コードの表から出る）の下に「取引先の画面を開く」ボタン（金型 `components/Button`・secondary・sm）を出し、`/crm/companies/<会社の番号>` へ移る。会社の番号は作成画面では選んでいる会社、見積詳細では見積の会社。ほかのエラー・やり直し・モード切替で消す。
- D10 既存の試験で請求書を作る会社に、既定の請求先の住所（国 US）を持たせる（test_invoices・test_company_stats・test_products・test_paypal_invoicing の4ファイル）。持たせないと D3 の 422 で今の試験が落ちる。
- D11 試験の SQLite（backend/tests/conftest.py）に都道府県の表 `prefectures`・発行元の表 `tenant_issuer_profiles`・請求書の列 `issuer_region` を足し、`public.prefectures` を読み替える。試験の後片付けに発行元の表を足す。都道府県の値は試験に書かず、正本の seed ファイル（docs/handoff/viewer-contract-stage/data/prefectures.sql）から読む。国名も試験に書かず国の表から読む。
- D12 PDF の中身の試験は、`get_issuer` と描画の関数を直接呼んで pdfminer で文字を取り出して確かめる（先例 backend/tests/test_po_renderer.py:80-89。PDF の入口を通す試験は前例が無く、SQLite では日時が文字で返るため作らない）。3つの入口が正しい地域で `get_issuer` を呼ぶことはソースの検査で確かめる。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らない（Opus が作る） | ○（冒頭・§5） |
| 3 | 報告の宛先と生出力の扱い | ○（§5。完了報告の本文に各手順の出力を tail の範囲でそのまま貼る） |
| 4 | 1便1目的 | ○（発行元を新しい表から読み、請求先の国で地域を決める。D1〜D3） |
| 5 | 既存ブランチへの追記ではない | ○（このカードが main に入った後、Opus が origin/main から新しい実装の枝 `release/viewer-contract-bin2-2c2a` を作る） |
| 6 | 書式は実例で示した | ○（§2 に変更前・変更後の全文） |
| 7 | 合格基準を出力まで縛った | ○（§3 の各手順の期待） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（手順9 の `git status --short` と `git diff --stat`） |
| 9 | 出力量に上限のないコマンドを使わない | ○（すべて tail か wc） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§4・§5・末尾） |
| 11 | 期待値は実測から | ○（P2〜P14 は b6b444eff で実測） |
| 12 | 停止は本番影響のあるものに限る | ○（§4） |
| 13 | 委任文の定型4点 | ○（§6） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない（commit は git log で確かめる） | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2 は全文。openapi.json だけは手順7 の道具で作り直す） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED viewer-contract-bin2-2c2a HEAD=`（続けて `git rev-parse HEAD` の 40 桁）。2 行目に「本報告はカード 便2-2c2a 請求書・見積書の発行元を新しい表から読み、請求先の国で地域を決める の実行結果である」と書く。

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

- P1 `docs/handoff/viewer-contract-stage/card-2-2c2a.md`（このカード）が枝に在る。
- P2 `ls backend/app/services/issuer.py backend/tests/test_issuer.py frontend/src/components/BillToCountryGuidance.test.tsx` が3つとも「無い」。
- P3 backend/app/routers/invoices.py で次の数: `ship_to_snapshot, bill_to_snapshot, fx_rate_snapshot$` 2・`:ship_to, :bill_to, :fx_rate$` 2・`"fx_rate": json.dumps(fx_snap) if fx_snap else None,$` 2・`    paypal_invoicer_view_url, paypal_copy_pdf_at$` 1・`    tenant_schema = await _get_tenant_schema(tenant_id)` 3・`from app.services.payment_dates import PAID_AT_SQL, paid_at_from_date, paypal_paid_at` 1・`issuer_region` 0。
- P4 backend/app/services/invoice_renderer.py で `    tenant_website: Optional\[str\] = None` 1・`        tenant_website=tenant_profile.get("website"),` 2・`registration_number` 0。
- P5 backend/app/schemas/invoice.py で `    paypal_copy_pdf_at: datetime | None = None` 1・`issuer_region` 0。
- P6 backend/tests/conftest.py で `if "public.countries" in statement:` 1・`                paypal_copy_pdf_at TIMESTAMP$` 1・`        # === Phase 4 テーブル ===` 1・`DELETE FROM tenant_profile` 1・`prefectures` 0・`tenant_issuer_profiles` 0・`issuer_region` 0。
- P7 `grep -c 'json={"name": company_name, "lead_id": lead_id})'` が backend/tests/test_invoices.py で 1。
- P8 `grep -c '"merge_target_archived",'` が backend/tests/test_api_error_reason_sync.py で 1。`grep -c "toBe(9)"` が frontend/src/lib/apiErrorReason.test.ts で 1。
- P9 `grep -c '"openCompanyForBillTo"\|"billToCountry"\|bill_to_country'` が frontend/src/locales/ja.json・frontend/src/locales/en.json・frontend/src/lib/apiErrorReason.ts でそれぞれ 0。
- P10 `wc -l` が frontend/src/pages/invoice-create/InvoiceCreatePage.tsx で 437、frontend/src/pages/quote-detail/QuoteDetailPage.tsx で 216。
- P11 A40 の検査（手順2 の python）が次の10行を出す: `routers/invoices.py 114`・`routers/tenant_profile.py 50`・`routers/tenant_profile.py 67`・`routers/tenant_profile.py 98`・`services/label_validation.py 85`・`services/po_renderer.py 9`・`services/po_renderer.py 258`・`services/tenant.py 1143`・`services/tenant.py 1159`・`services/tenant.py 1160`。
- P12 `grep -c "issuer_region" frontend/api-contract/openapi.json` が 0。`grep -c '"paypal_copy_pdf_at": {' frontend/api-contract/openapi.json` が 2。
- P13 `grep -c 'json={"name": "統計テスト会社", "lead_id": lead_id})'` と `grep -c 'json={"name": "他社", "lead_id": other_lead_id})'` が backend/tests/test_company_stats.py でそれぞれ 1。`grep -c 'json={"name": "請求FK会社", "lead_id": lead_id})'` が backend/tests/test_products.py で 1。`grep -c 'json={"name": "Invoicingテスト会社", "lead_id": lead_id})'` が backend/tests/test_paypal_invoicing.py で 1。
- P14 `grep -c "ON CONFLICT (code) DO NOTHING;" docs/handoff/viewer-contract-stage/data/prefectures.sql` が 1。

## 1. 触るファイル

1. backend/app/services/issuer.py（新規）
2. backend/app/routers/invoices.py
3. backend/app/services/invoice_renderer.py
4. backend/app/schemas/invoice.py
5. backend/tests/conftest.py
6. backend/tests/test_invoices.py
7. backend/tests/test_company_stats.py
8. backend/tests/test_products.py
9. backend/tests/test_paypal_invoicing.py
10. backend/tests/test_api_error_reason_sync.py
11. backend/tests/test_issuer.py（新規）
12. frontend/src/lib/apiErrorReason.ts
13. frontend/src/lib/apiErrorReason.test.ts
14. frontend/src/locales/ja.json
15. frontend/src/locales/en.json
16. frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
17. frontend/src/pages/quote-detail/QuoteDetailPage.tsx
18. frontend/src/components/BillToCountryGuidance.test.tsx（新規）
19. frontend/api-contract/openapi.json（手順7 の道具で作り直す。手で書かない）

## 2. 変更

### 2-1 backend/app/services/issuer.py（新規。Write ツールでこの全文）

```python
"""請求書・見積書の PDF に載せる発行元（自社）の情報を読む（ADR-1061 便2-2c2a）。

- 正本は会社ごとの発行元の表（国内向け・海外向けの 2 行まで）。
- その地域の行が無いときだけ、旧来の会社情報の表（1 行）から読む（移行の間の予備）。
- 行がある地域では、空の欄を旧来の表で埋めない（混ぜると正本が 2 か所になるため）。
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import tenant_table_ref

ISSUER_REGIONS = ("domestic", "overseas")


def decide_issuer_region(bill_to_snapshot: Mapping[str, Any] | None) -> str | None:
    """請求先の写しの国から発行元の地域を決める。国が無いときは None。"""
    if not bill_to_snapshot:
        return None
    country = bill_to_snapshot.get("country")
    if not isinstance(country, str) or not country.strip():
        return None
    return "domestic" if country.strip().upper() == "JP" else "overseas"


def format_issuer_address(row: Mapping[str, Any], prefecture_name: str | None, country_name: str | None) -> str:
    """発行元の住所を 1 行にする。日本は〒・都道府県から、海外は通りから国へ。"""
    city = row.get("city") or ""
    address1 = row.get("address1") or ""
    address2 = row.get("address2") or ""
    if row.get("country_code") == "JP":
        postal = row.get("postal_code") or ""
        head = f"〒{postal[:3]}-{postal[3:]} " if postal else ""
        line = f"{head}{prefecture_name or ''}{city}{address1}"
        return f"{line} {address2}" if address2 else line
    tail = f"{row.get('state_region') or ''} {row.get('postal_code') or ''}".strip()
    return ", ".join(p for p in [address1, address2, city, tail, country_name or ""] if p)


async def get_issuer(db: AsyncSession, tenant_id: int, region: str) -> dict:
    """発行元の情報を返す。キー: name, address, phone, email, website, registration_number, legacy。"""
    if region not in ISSUER_REGIONS:
        raise ValueError(f"unknown issuer region: {region}")
    profiles = tenant_table_ref(db, tenant_id, "tenant_issuer_profiles")
    result = await db.execute(
        text(f"""
            SELECT p.company_name, p.email, p.website, p.country_code, p.postal_code,
                   p.state_region, p.city, p.address1, p.address2, p.phone,
                   p.is_invoice_registered, p.registration_number,
                   pr.name_ja AS prefecture_name, co.name AS country_name
            FROM {profiles} p
            LEFT JOIN public.prefectures pr ON pr.code = p.prefecture_code
            LEFT JOIN public.countries co ON co.code = p.country_code
            WHERE p.region = :region
            ORDER BY p.id
            LIMIT 1
        """),
        {"region": region},
    )
    row = result.mappings().first()
    if row:
        return {
            "name": row["company_name"],
            "address": format_issuer_address(row, row["prefecture_name"], row["country_name"]),
            "phone": row["phone"] or "",
            "email": row["email"] or "",
            "website": row["website"] or "",
            "registration_number": row["registration_number"] if row["is_invoice_registered"] else None,
            "legacy": False,
        }
    legacy = tenant_table_ref(db, tenant_id, "tenant_profile")
    result = await db.execute(
        text(f"""
            SELECT company_name, company_name_en, address, phone, email, website
            FROM {legacy}
            ORDER BY id LIMIT 1
        """),
    )
    old = result.mappings().first()
    if not old:
        return {"name": "", "address": "", "phone": "", "email": "", "website": "",
                "registration_number": None, "legacy": True}
    return {
        "name": old["company_name"] or old["company_name_en"] or "",
        "address": old["address"] or "",
        "phone": old["phone"] or "",
        "email": old["email"] or "",
        "website": old["website"] or "",
        "registration_number": None,
        "legacy": True,
    }
```

### 2-2 backend/app/routers/invoices.py（9か所）

(1) 取り込み。変更前:
```
from app.services.payment_dates import PAID_AT_SQL, paid_at_from_date, paypal_paid_at
```
変更後:
```
from app.services.issuer import decide_issuer_region, get_issuer
from app.services.payment_dates import PAID_AT_SQL, paid_at_from_date, paypal_paid_at
```
（並び順は invoice_renderer → issuer → payment_dates の字の順。ruff の I001 が出ない位置）

(2) `_get_tenant_schema` を消す。変更前:
```
async def _get_tenant_schema(tenant_id: int) -> str:
    """tenant_id からスキーマ名 (tenant_NNN) を生成する。"""
    return f"tenant_{tenant_id:03d}"


```
変更後: （何も無い。直後の `async def _fetch_address_snapshot(` が前の行の2行の空行の後に来る）

(3) `_fetch_tenant_profile` を消す。変更前:
```
async def _fetch_tenant_profile(db: AsyncSession, tenant_schema: str) -> dict:
    """tenant_profile からテナント情報を取得する。"""
    result = await db.execute(
        text(f"""
            SELECT company_name, company_name_en, address, phone, email, website
            FROM {tenant_schema}.tenant_profile
            ORDER BY id LIMIT 1
        """),
    )
    row = result.mappings().first()
    if not row:
        return {}
    return {
        "name": row["company_name"] or row["company_name_en"] or "",
        "address": row["address"] or "",
        "phone": row["phone"] or "",
        "email": row["email"] or "",
        "website": row["website"] or "",
    }


```
変更後: （何も無い。直後の `_INVOICE_COLUMNS = """` が前の関数の後の2行の空行の後に来る）

(4) 列の一覧。変更前:
```
    paypal_invoicer_view_url, paypal_copy_pdf_at
"""
```
変更後:
```
    paypal_invoicer_view_url, paypal_copy_pdf_at,
    issuer_region
"""
```

(5) 見積からの作成で地域を決める。変更前（1か所だけ）:
```
    company_id = q.get("company_id")
    ship_to_snap = await _fetch_address_snapshot(db, company_id, "delivery")
    bill_to_snap = await _fetch_address_snapshot(db, company_id, "billing")

    # 為替レート取得（JPY 以外の場合）
    currency = q["currency"]
```
変更後:
```
    company_id = q.get("company_id")
    ship_to_snap = await _fetch_address_snapshot(db, company_id, "delivery")
    bill_to_snap = await _fetch_address_snapshot(db, company_id, "billing")
    # ADR-1061 便2-2c2a: 発行元の地域は請求先の国で決めて保存する（国が無いと作らない）
    issuer_region = decide_issuer_region(bill_to_snap)
    if issuer_region is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="bill_to_country")

    # 為替レート取得（JPY 以外の場合）
    currency = q["currency"]
```

(6) 直接作成で地域を決める。変更前（1か所だけ）:
```
    ship_to_snap = await _fetch_address_snapshot(db, data.company_id, "delivery")
    bill_to_snap = await _fetch_address_snapshot(db, data.company_id, "billing")
```
変更後:
```
    ship_to_snap = await _fetch_address_snapshot(db, data.company_id, "delivery")
    bill_to_snap = await _fetch_address_snapshot(db, data.company_id, "billing")
    # ADR-1061 便2-2c2a: 発行元の地域は請求先の国で決めて保存する（国が無いと作らない）
    issuer_region = decide_issuer_region(bill_to_snap)
    if issuer_region is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="bill_to_country")
```

(7) 2つの INSERT に列を足す（Edit ツールの replace_all で、それぞれちょうど2か所）。
- 変更前 `                ship_to_snapshot, bill_to_snapshot, fx_rate_snapshot` → 変更後 `                ship_to_snapshot, bill_to_snapshot, fx_rate_snapshot, issuer_region`
- 変更前 `                :ship_to, :bill_to, :fx_rate` → 変更後 `                :ship_to, :bill_to, :fx_rate, :issuer_region`
- 変更前 `            "fx_rate": json.dumps(fx_snap) if fx_snap else None,` → 変更後（2行）:
```
            "fx_rate": json.dumps(fx_snap) if fx_snap else None,
            "issuer_region": issuer_region,
```

(8) 見積書 PDF（先にこれをする。1か所だけ）。変更前:
```
    bill_to_snap = await _fetch_address_snapshot(db, company_id, "billing")

    tenant_schema = await _get_tenant_schema(tenant_id)
    tenant_profile = await _fetch_tenant_profile(db, tenant_schema)
```
変更後:
```
    bill_to_snap = await _fetch_address_snapshot(db, company_id, "billing")

    # ADR-1061 便2-2c2a: 見積は地域を持たないので海外用の発行元を使う
    tenant_profile = await get_issuer(db, tenant_id, "overseas")
```

(9) 請求書 PDF と PayPal の写し PDF（(8) の後に replace_all で、ちょうど2か所）。変更前:
```
    tenant_schema = await _get_tenant_schema(tenant_id)
    tenant_profile = await _fetch_tenant_profile(db, tenant_schema)
```
変更後:
```
    tenant_profile = await get_issuer(db, tenant_id, row["issuer_region"] or "overseas")
```
（どちらの入口も `row` は `_INVOICE_COLUMNS` を読んだ行。請求書 PDF は `SELECT {_INVOICE_COLUMNS}`、写しは呼び出し元の `UPDATE … RETURNING {_INVOICE_COLUMNS}`）

### 2-3 backend/app/services/invoice_renderer.py（3か所）

(1) 変更前:
```
    tenant_website: Optional[str] = None
```
変更後:
```
    tenant_website: Optional[str] = None
    # ADR-1061 便2-2c2a: 適格請求書の登録番号（請求書だけに載せる。見積書では渡さない）
    tenant_registration_number: Optional[str] = None
```

(2) 変更前:
```
    if data.tenant_website:
        c.setFont(font, 8)
        c.drawString(20 * mm, y, f"Web: {data.tenant_website}")
        y -= 4 * mm
```
変更後:
```
    if data.tenant_website:
        c.setFont(font, 8)
        c.drawString(20 * mm, y, f"Web: {data.tenant_website}")
        y -= 4 * mm
    if data.tenant_registration_number:
        c.setFont(font, 8)
        c.drawString(20 * mm, y, f"Registration No.: {data.tenant_registration_number}")
        y -= 4 * mm
```

(3) render_invoice_pdf の中だけ。変更前（1か所だけ）:
```
        tenant_website=tenant_profile.get("website"),
        paypal_copy=paypal_copy,
```
変更後:
```
        tenant_website=tenant_profile.get("website"),
        tenant_registration_number=tenant_profile.get("registration_number"),
        paypal_copy=paypal_copy,
```

### 2-4 backend/app/schemas/invoice.py（1か所）

変更前:
```
    paypal_copy_pdf_at: datetime | None = None
```
変更後:
```
    paypal_copy_pdf_at: datetime | None = None
    # ADR-1061 便2-2c2a: 発行元の地域（domestic / overseas。作成時に請求先の国で決める。古い請求書は NULL）
    issuer_region: str | None = None
```

### 2-5 backend/tests/conftest.py（5か所）

(1) 変更前:
```
        if "public.countries" in statement:
            statement = statement.replace("public.countries", "countries")
```
変更後:
```
        if "public.countries" in statement:
            statement = statement.replace("public.countries", "countries")
        if "public.prefectures" in statement:
            statement = statement.replace("public.prefectures", "prefectures")
```

(2) 変更前:
```
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS countries (
                code CHAR(2) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                dial_code VARCHAR(10) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
```
変更後:
```
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS countries (
                code CHAR(2) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                dial_code VARCHAR(10) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # ADR-1061 便2-2c2a: 都道府県の表（値は試験が正本の seed ファイルから入れる）
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prefectures (
                code CHAR(2) PRIMARY KEY,
                name_ja TEXT NOT NULL,
                name_en TEXT NOT NULL,
                sort_order INTEGER NOT NULL
            )
        """))
```

(3) 変更前（1か所だけ）:
```
                paypal_copy_pdf_at TIMESTAMP
            )
```
変更後:
```
                paypal_copy_pdf_at TIMESTAMP,
                issuer_region VARCHAR(20)
            )
```

(4) 変更前（1か所だけ）:
```
        # === Phase 4 テーブル ===
```
変更後:
```
        # ADR-1061 便2-2c2a: 発行元の会社情報（本番は会社ごとのスキーマ。試験では CHECK・外部キーを省く）
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tenant_issuer_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL DEFAULT 999,
                region VARCHAR(20) NOT NULL,
                company_name VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                website VARCHAR(255),
                country_code CHAR(2) NOT NULL,
                postal_code VARCHAR(10),
                prefecture_code CHAR(2),
                state_region VARCHAR(100),
                city VARCHAR(100) NOT NULL,
                address1 VARCHAR(255) NOT NULL,
                address2 TEXT,
                phone VARCHAR(16),
                is_invoice_registered BOOLEAN NOT NULL DEFAULT 0,
                registration_number VARCHAR(14),
                updated_by_user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (tenant_id, region)
            )
        """))
        # === Phase 4 テーブル ===
```

(5) 後片付け。変更前:
```
        # Sprint 8: tenant_profile
        await conn.execute(text("DELETE FROM tenant_profile"))
```
変更後:
```
        # Sprint 8: tenant_profile
        await conn.execute(text("DELETE FROM tenant_profile"))
        # ADR-1061 便2-2c2a: 発行元の会社情報
        await conn.execute(text("DELETE FROM tenant_issuer_profiles"))
```

### 2-6 backend/tests/test_invoices.py（1か所。D10）

変更前:
```
async def _create_company_contact(client, company_name="請求テスト会社"):
    from tests.helpers_txn import create_lead
    lead_id = await create_lead(client, company_name)
    co = await client.post("/api/v1/companies", json={"name": company_name, "lead_id": lead_id})
```
変更後:
```
async def _create_company_contact(client, company_name="請求テスト会社", country="US"):
    """会社と担当を作る。country を渡すと既定の請求先の住所を付ける（ADR-1061 便2-2c2a: 請求書は請求先の国が要る）"""
    from tests.helpers_txn import create_lead
    lead_id = await create_lead(client, company_name)
    body = {"name": company_name, "lead_id": lead_id}
    if country is not None:
        body["addresses"] = [{"address_type": "billing", "country_code": country, "is_default": True}]
    co = await client.post("/api/v1/companies", json=body)
```

### 2-7 backend/tests/test_company_stats.py（2か所）

(1) 変更前:
```
    co_res = await client.post("/api/v1/companies", json={"name": "統計テスト会社", "lead_id": lead_id})
```
変更後:
```
    co_res = await client.post("/api/v1/companies", json={
        "name": "統計テスト会社", "lead_id": lead_id,
        "addresses": [{"address_type": "billing", "country_code": "US", "is_default": True}],
    })
```

(2) 変更前:
```
        other_co = await client.post("/api/v1/companies", json={"name": "他社", "lead_id": other_lead_id})
```
変更後:
```
        other_co = await client.post("/api/v1/companies", json={
            "name": "他社", "lead_id": other_lead_id,
            "addresses": [{"address_type": "billing", "country_code": "US", "is_default": True}],
        })
```

### 2-8 backend/tests/test_products.py（1か所）

変更前:
```
        co = await client.post("/api/v1/companies", json={"name": "請求FK会社", "lead_id": lead_id})
```
変更後:
```
        co = await client.post("/api/v1/companies", json={
            "name": "請求FK会社", "lead_id": lead_id,
            "addresses": [{"address_type": "billing", "country_code": "US", "is_default": True}],
        })
```

### 2-9 backend/tests/test_paypal_invoicing.py（1か所）

変更前:
```
    co = await client.post("/api/v1/companies", json={"name": "Invoicingテスト会社", "lead_id": lead_id})
```
変更後:
```
    co = await client.post("/api/v1/companies", json={
        "name": "Invoicingテスト会社", "lead_id": lead_id,
        "addresses": [{"address_type": "billing", "country_code": "US", "is_default": True}],
    })
```

### 2-10 backend/tests/test_api_error_reason_sync.py（1か所）

変更前:
```
        "merge_target_archived",
    ]
```
変更後:
```
        "merge_target_archived",
        "bill_to_country",
    ]
```

### 2-11 backend/tests/test_issuer.py（新規。Write ツールでこの全文）

```python
"""請求書・見積書の発行元の読み方の試験（ADR-1061 便2-2c2a。design.md §3-4・A40 の一部）。

- 発行元の地域は、請求書を作るときの請求先の国で決まり、あとから会社の住所を変えても変わらない。
- 請求先の国が無いときは作らずに 422 "bill_to_country" を返す。
- 発行元の表にその地域の行があればそれだけを読み、無いときだけ旧来の会社情報の表を読む。
- 登録番号は請求書だけに載り、見積書には載らない。
- 都道府県名・国名は試験に書かず、正本（都道府県の seed ファイル・国の表）から読む。
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
from sqlalchemy import text

from app.services.invoice_renderer import render_invoice_pdf, render_quote_pdf
from app.services.issuer import decide_issuer_region, format_issuer_address, get_issuer
from tests.test_invoices import _create_approved_quote, _create_company_contact

_ROOT = Path(__file__).resolve().parents[2]
_APP = _ROOT / "backend" / "app"
_PREF_SEED = _ROOT / "docs" / "handoff" / "viewer-contract-stage" / "data" / "prefectures.sql"
_PREF_ROW_RE = re.compile(r"^\s*\('(\d{2})',\s*'([^']+)',\s*'([^']+)',\s*(\d+)\),?$", re.M)
_A40_RE = re.compile(
    r'\{[A-Za-z_]+\}\.tenant_profile\b|"tenant_profile"\s*\)|\bFROM\s+tenant_profile\b'
    r"|\bINTO\s+tenant_profile\b|\bUPDATE\s+tenant_profile\b",
    re.I,
)
_REG_NO = "T1234567890123"


def _extract_text(pdf_bytes: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text
    except ImportError:
        pytest.skip("pdfminer.six 未インストール (requirements.txt 適用要)")
    return extract_text(io.BytesIO(pdf_bytes))


def _invoice_data() -> dict:
    return {
        "invoice_code": "IN-0001-01",
        "issued_at": "2026-11-12T00:00:00",
        "ship_to_snapshot": None,
        "bill_to_snapshot": None,
        "items": [{"name_en": "Item", "quantity": 1, "unit_price": 10.0, "subtotal": 10.0, "hs_code": None}],
        "subtotal": 10.0,
        "shipping_fee": 0.0,
        "tax_amount": 0.0,
        "total_amount": 10.0,
        "currency": "USD",
        "duty_amount": None,
        "fx_rate_snapshot": None,
        "notes": None,
    }


def _quote_data() -> dict:
    return {
        "quote_code": "QT-0001",
        "created_at": "2026-11-12T00:00:00",
        "ship_to_snapshot": None,
        "bill_to_snapshot": None,
        "items": [{"name_en": "Item", "quantity": 1, "unit_price": 10.0, "subtotal": 10.0, "hs_code": None}],
        "subtotal": 10.0,
        "shipping_fee": 0.0,
        "tax_amount": 0.0,
        "total_amount": 10.0,
        "currency": "USD",
        "notes": None,
    }


async def _insert_issuer(db, region: str, *, company_name: str, email, country_code: str,
                         prefecture_code=None, postal_code=None, registered: bool = False,
                         registration_number=None):
    await db.execute(
        text(
            "INSERT INTO tenant_issuer_profiles (tenant_id, region, company_name, email, website,"
            " country_code, postal_code, prefecture_code, state_region, city, address1, address2,"
            " phone, is_invoice_registered, registration_number)"
            " VALUES (999, :region, :company_name, :email, NULL, :country_code, :postal_code,"
            " :prefecture_code, NULL, :city, :address1, NULL, :phone, :registered, :registration_number)"
        ),
        {
            "region": region,
            "company_name": company_name,
            "email": email,
            "country_code": country_code,
            "postal_code": postal_code,
            "prefecture_code": prefecture_code,
            "city": "CityA",
            "address1": "Street1",
            "phone": "0312345678",
            "registered": registered,
            "registration_number": registration_number,
        },
    )


async def _insert_legacy(db):
    await db.execute(
        text(
            "INSERT INTO tenant_profile (company_name, company_name_en, address, phone, email, website)"
            " VALUES (:n, :ne, :a, :p, :e, :w)"
        ),
        {"n": "Legacy Co", "ne": "Legacy Co EN", "a": "Legacy Address", "p": "0000",
         "e": "legacy@example.com", "w": "legacy.example.com"},
    )


async def _company_with_billing(client, name: str, country):
    """既定の請求先の住所を持つ会社（country=None なら国の無い請求先・"none" なら請求先なし）"""
    company_id, contact_id = await _create_company_contact(client, name, country=None)
    if country != "none":
        address = {"address_type": "billing", "is_default": True}
        if country is not None:
            address["country_code"] = country
        res = await client.patch(f"/api/v1/companies/{company_id}", json={"addresses": [address]})
        assert res.status_code == 200, res.text
    return company_id, contact_id


async def _invoice_count(db) -> int:
    return (await db.execute(text("SELECT COUNT(*) FROM invoices"))).scalar_one()


# ---------------------------------------------------------------------------
# 単体: 地域の決め方・住所の書き方
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("snapshot", "expected"),
    [
        ({"country": "JP"}, "domestic"),
        ({"country": "jp"}, "domestic"),
        ({"country": " jp "}, "domestic"),
        ({"country": "US"}, "overseas"),
        (None, None),
        ({}, None),
        ({"country": None}, None),
        ({"country": ""}, None),
    ],
)
def test_decide_issuer_region(snapshot, expected):
    assert decide_issuer_region(snapshot) == expected


def test_format_issuer_address_jp():
    row = {"country_code": "JP", "postal_code": "1000001", "city": "C", "address1": "A1", "address2": None}
    assert format_issuer_address(row, "P", None) == "〒100-0001 PCA1"
    row["address2"] = "B2"
    assert format_issuer_address(row, "P", None) == "〒100-0001 PCA1 B2"


def test_format_issuer_address_overseas():
    row = {"country_code": "US", "postal_code": "94105", "state_region": "CA", "city": "SF",
           "address1": "1 Main St", "address2": None}
    assert format_issuer_address(row, None, "Countryname") == "1 Main St, SF, CA 94105, Countryname"


async def test_get_issuer_rejects_unknown_region(db_session):
    with pytest.raises(ValueError):
        await get_issuer(db_session, 999, "x")


# ---------------------------------------------------------------------------
# 単体: 印刷（登録番号は請求書だけ）
# ---------------------------------------------------------------------------

def test_invoice_pdf_prints_registration_number_only_when_set():
    with_no = _extract_text(render_invoice_pdf(_invoice_data(), {"name": "Issuer A", "registration_number": _REG_NO}))
    assert "Registration No.: " + _REG_NO in with_no
    without = _extract_text(render_invoice_pdf(_invoice_data(), {"name": "Issuer A", "registration_number": None}))
    assert "Registration No." not in without


def test_quote_pdf_never_prints_registration_number():
    out = _extract_text(render_quote_pdf(_quote_data(), {"name": "Issuer A", "registration_number": _REG_NO}))
    assert "Issuer A" in out
    assert _REG_NO not in out


# ---------------------------------------------------------------------------
# 発行元の読み方（DB）
# ---------------------------------------------------------------------------

async def test_get_issuer_reads_region_row_with_prefecture_and_registration(db_session):
    code, name_ja, name_en, sort_order = _PREF_ROW_RE.findall(_PREF_SEED.read_text("utf-8"))[12]
    assert code == "13"
    await db_session.execute(
        text("INSERT OR IGNORE INTO prefectures (code, name_ja, name_en, sort_order) VALUES (:c, :j, :e, :s)"),
        {"c": code, "j": name_ja, "e": name_en, "s": int(sort_order)},
    )
    await _insert_legacy(db_session)
    await _insert_issuer(db_session, "domestic", company_name="Domestic Issuer", email=None,
                         country_code="JP", prefecture_code="13", postal_code="1000001",
                         registered=True, registration_number=_REG_NO)
    issuer = await get_issuer(db_session, 999, "domestic")
    assert issuer["name"] == "Domestic Issuer"
    assert issuer["address"] == f"〒100-0001 {name_ja}CityAStreet1"
    assert issuer["registration_number"] == _REG_NO
    assert issuer["legacy"] is False
    # 行がある地域では空の欄を旧来の表で埋めない
    assert issuer["email"] == ""
    pdf = _extract_text(render_invoice_pdf(_invoice_data(), issuer))
    assert "Domestic Issuer" in pdf
    assert _REG_NO in pdf
    assert "legacy@example.com" not in pdf


async def test_get_issuer_registration_hidden_when_not_registered(db_session):
    await _insert_issuer(db_session, "domestic", company_name="Domestic Issuer", email="d@example.com",
                         country_code="JP", postal_code="1000001",
                         registered=False, registration_number=_REG_NO)
    issuer = await get_issuer(db_session, 999, "domestic")
    assert issuer["registration_number"] is None


async def test_get_issuer_overseas_uses_country_table_name(db_session):
    country_name = (await db_session.execute(
        text("SELECT name FROM countries WHERE code = 'US'")
    )).scalar_one()
    await _insert_issuer(db_session, "overseas", company_name="Overseas Issuer", email="o@example.com",
                         country_code="US", postal_code="94105")
    issuer = await get_issuer(db_session, 999, "overseas")
    assert issuer["name"] == "Overseas Issuer"
    assert issuer["address"].endswith(country_name)
    assert issuer["registration_number"] is None
    # 見積書は海外用の行を使う（invoices.py の呼び出しは下のソース検査で確かめる）
    out = _extract_text(render_quote_pdf(_quote_data(), issuer))
    assert "Overseas Issuer" in out


async def test_get_issuer_falls_back_to_legacy_only_without_row(db_session):
    await _insert_legacy(db_session)
    await _insert_issuer(db_session, "domestic", company_name="Domestic Issuer", email=None,
                         country_code="JP", postal_code="1000001",
                         registered=True, registration_number=_REG_NO)
    overseas = await get_issuer(db_session, 999, "overseas")
    assert overseas["name"] == "Legacy Co"
    assert overseas["email"] == "legacy@example.com"
    assert overseas["registration_number"] is None
    assert overseas["legacy"] is True
    pdf = _extract_text(render_invoice_pdf(_invoice_data(), overseas))
    assert "Legacy Co" in pdf
    assert _REG_NO not in pdf


async def test_get_issuer_without_any_row_returns_blank(db_session):
    issuer = await get_issuer(db_session, 999, "domestic")
    assert issuer == {"name": "", "address": "", "phone": "", "email": "", "website": "",
                      "registration_number": None, "legacy": True}


# ---------------------------------------------------------------------------
# 請求書を作るときの地域の決定（2つの作り方）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(("country", "expected"), [("JP", "domestic"), ("jp", "domestic"), ("US", "overseas")])
async def test_direct_create_stores_region(client, country, expected):
    company_id, contact_id = await _company_with_billing(client, f"地域{country}", country)
    res = await client.post("/api/v1/invoices", json={
        "company_id": company_id, "contact_id": contact_id,
        "items": [{"product_name": "P", "quantity": 1, "unit_price": "10.00"}],
    })
    assert res.status_code == 201, res.text
    assert res.json()["issuer_region"] == expected


@pytest.mark.parametrize(("country", "expected"), [("JP", "domestic"), ("US", "overseas")])
async def test_from_quote_stores_region(client, country, expected):
    company_id, contact_id = await _company_with_billing(client, f"見積地域{country}", country)
    quote_id = await _create_approved_quote(client, company_id, contact_id)
    res = await client.post(f"/api/v1/invoices/from-quote/{quote_id}")
    assert res.status_code == 201, res.text
    assert res.json()["issuer_region"] == expected


@pytest.mark.parametrize("country", ["none", None])
async def test_direct_create_without_bill_to_country_is_422(client, db_session, country):
    company_id, contact_id = await _company_with_billing(client, "国なし直接", country)
    before = await _invoice_count(db_session)
    res = await client.post("/api/v1/invoices", json={
        "company_id": company_id, "contact_id": contact_id,
        "items": [{"product_name": "P", "quantity": 1, "unit_price": "10.00"}],
    })
    assert res.status_code == 422, res.text
    assert res.json()["detail"] == "bill_to_country"
    assert await _invoice_count(db_session) == before


@pytest.mark.parametrize("country", ["none", None])
async def test_from_quote_without_bill_to_country_is_422(client, db_session, country):
    company_id, contact_id = await _company_with_billing(client, "国なし見積", country)
    quote_id = await _create_approved_quote(client, company_id, contact_id)
    before = await _invoice_count(db_session)
    res = await client.post(f"/api/v1/invoices/from-quote/{quote_id}")
    assert res.status_code == 422, res.text
    assert res.json()["detail"] == "bill_to_country"
    assert await _invoice_count(db_session) == before


async def test_region_does_not_follow_later_address_change(client):
    company_id, contact_id = await _company_with_billing(client, "あとで変える会社", "JP")
    res = await client.post("/api/v1/invoices", json={
        "company_id": company_id, "contact_id": contact_id,
        "items": [{"product_name": "P", "quantity": 1, "unit_price": "10.00"}],
    })
    assert res.status_code == 201, res.text
    invoice_id = res.json()["id"]
    upd = await client.patch(f"/api/v1/companies/{company_id}", json={
        "addresses": [{"address_type": "billing", "country_code": "US", "is_default": True}],
    })
    assert upd.status_code == 200, upd.text
    got = await client.get(f"/api/v1/invoices/{invoice_id}")
    assert got.status_code == 200
    assert got.json()["issuer_region"] == "domestic"


# ---------------------------------------------------------------------------
# ソース検査（A40: 旧来の会社情報の表を読むのは決まった場所だけ）
# ---------------------------------------------------------------------------

def test_a40_tenant_profile_readers_are_limited():
    hits: dict[str, int] = {}
    for p in sorted(_APP.rglob("*.py")):
        n = sum(1 for line in p.read_text("utf-8").splitlines() if _A40_RE.search(line))
        if n:
            hits[str(p.relative_to(_APP))] = n
    assert set(hits) == {
        "routers/tenant_profile.py",
        "services/tenant.py",
        "services/po_renderer.py",
        "services/label_validation.py",
        "services/issuer.py",
    }
    assert hits["services/issuer.py"] == 1


def test_invoice_router_reads_issuer_through_get_issuer():
    src = (_APP / "routers" / "invoices.py").read_text("utf-8")
    assert src.count('get_issuer(db, tenant_id, row["issuer_region"] or "overseas")') == 2
    assert src.count('get_issuer(db, tenant_id, "overseas")') == 1
    assert "_fetch_tenant_profile" not in src
    assert "_get_tenant_schema" not in src
    assert src.count('detail="bill_to_country"') == 2
```

### 2-12 frontend/src/lib/apiErrorReason.ts（1か所）

変更前:
```
  merge_target_archived: "apiError.mergeTargetArchived",
};
```
変更後:
```
  merge_target_archived: "apiError.mergeTargetArchived",
  bill_to_country: "apiError.billToCountry",
};
```

### 2-13 frontend/src/lib/apiErrorReason.test.ts（1か所）

変更前:
```
    expect(Object.keys(API_ERROR_REASON_KEYS).length).toBe(9);
```
変更後:
```
    expect(Object.keys(API_ERROR_REASON_KEYS).length).toBe(10);
```

### 2-14 frontend/src/locales/ja.json（2か所）

(1) 変更前:
```
    "createBtn": "請求書を作成",
```
変更後:
```
    "createBtn": "請求書を作成",
    "openCompanyForBillTo": "取引先の画面を開く",
```

(2) 変更前:
```
    "mergeTargetArchived": "残す方の顧客は今の状態ではまとめられません。先に残す方の状態を変えてから、やり直してください。",
```
変更後:
```
    "mergeTargetArchived": "残す方の顧客は今の状態ではまとめられません。先に残す方の状態を変えてから、やり直してください。",
    "billToCountry": "請求先の国が入っていないため、請求書を作れません。取引先の画面で、既定の請求先の住所と国を入れてください。",
```

### 2-15 frontend/src/locales/en.json（2か所）

(1) 変更前:
```
    "createBtn": "Create invoice",
```
変更後:
```
    "createBtn": "Create invoice",
    "openCompanyForBillTo": "Open customer page",
```

(2) 変更前:
```
    "mergeTargetArchived": "The customer you chose to keep cannot be merged in its current status. Change its status first, then try again.",
```
変更後:
```
    "mergeTargetArchived": "The customer you chose to keep cannot be merged in its current status. Change its status first, then try again.",
    "billToCountry": "The invoice can't be created because the customer's billing country is missing. Add a default billing address with a country on the customer page.",
```

### 2-16 frontend/src/pages/invoice-create/InvoiceCreatePage.tsx（5か所）

(1) 変更前:
```
import { api } from "../../lib/api";
```
変更後:
```
import { api, ApiError } from "../../lib/api";
```

(2) 変更前:
```
  const [error, setError] = useState("");
```
変更後:
```
  const [error, setError] = useState("");
  // ADR-1061 便2-2c2a: 請求先の国が無くて作れなかったとき、取引先の画面へ移るボタンを出す会社の番号
  const [billToCompanyId, setBillToCompanyId] = useState<number | null>(null);
```

(3) 見積の読み込み。変更前:
```
  const loadQuoteForEdit = async (quoteId: number) => {
    setError("");
```
変更後:
```
  const loadQuoteForEdit = async (quoteId: number) => {
    setError("");
    setBillToCompanyId(null);
```

(4) 作成。変更前:
```
    e.preventDefault();
    setError("");
    setSelectorError("");
```
変更後:
```
    e.preventDefault();
    setError("");
    setBillToCompanyId(null);
    setSelectorError("");
```
そして、変更前:
```
      setError(e instanceof Error ? e.message : t("common.saveError"));
```
変更後:
```
      setError(e instanceof Error ? e.message : t("common.saveError"));
      if (e instanceof ApiError && e.responseDetail === "bill_to_country") setBillToCompanyId(companyId);
```

(5) 表示。変更前:
```
      {shownError && <div className="error-message">{shownError}</div>}
```
変更後:
```
      {shownError && <div className="error-message">{shownError}</div>}
      {billToCompanyId !== null && error !== "" && (
        <div style={{ marginBottom: "var(--space-3)" }}>
          <Button type="button" variant="secondary" size="sm" onClick={() => navigate(`/crm/companies/${billToCompanyId}`)}>
            {t("invoices.openCompanyForBillTo")}
          </Button>
        </div>
      )}
```

### 2-17 frontend/src/pages/quote-detail/QuoteDetailPage.tsx（4か所）

(1) 変更前:
```
import { api } from "../../lib/api";
```
変更後:
```
import { api, ApiError } from "../../lib/api";
```

(2) 変更前:
```
  const [error, setError] = useState("");
```
変更後:
```
  const [error, setError] = useState("");
  // ADR-1061 便2-2c2a: 請求先の国が無くて請求書を作れなかったとき、取引先の画面へ移るボタンを出す会社の番号
  const [billToCompanyId, setBillToCompanyId] = useState<number | null>(null);
```

(3) 変更前:
```
  const doAction = async (action: string) => {
    try {
      await api.post(`/quotes/${id}/${action}`, {});
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    }
  };

  const convertToInvoice = async () => {
    try {
      const result = await api.post<{ id: number }>(`/invoices/from-quote/${id}`, {});
      navigate(`/invoices/${result.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    }
  };
```
変更後:
```
  const doAction = async (action: string) => {
    setBillToCompanyId(null);
    try {
      await api.post(`/quotes/${id}/${action}`, {});
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    }
  };

  const convertToInvoice = async () => {
    setBillToCompanyId(null);
    try {
      const result = await api.post<{ id: number }>(`/invoices/from-quote/${id}`, {});
      navigate(`/invoices/${result.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
      if (e instanceof ApiError && e.responseDetail === "bill_to_country" && quote) setBillToCompanyId(quote.company_id);
    }
  };
```
そして、変更前:
```
      setError(e instanceof Error ? e.message : t("common.fetchError"));
```
変更後:
```
      setError(e instanceof Error ? e.message : t("common.fetchError"));
      setBillToCompanyId(null);
```

(4) 変更前:
```
      {shownError && <div className="error-message">{shownError}</div>}
```
変更後:
```
      {shownError && <div className="error-message">{shownError}</div>}
      {billToCompanyId !== null && (
        <div style={{ marginBottom: "var(--space-4)" }}>
          <Button type="button" variant="secondary" size="sm" onClick={() => navigate(`/crm/companies/${billToCompanyId}`)}>
            {t("invoices.openCompanyForBillTo")}
          </Button>
        </div>
      )}
```

### 2-18 frontend/src/components/BillToCountryGuidance.test.tsx（新規。Write ツールでこの全文）

```tsx
// ADR-1061 便2-2c2a: 請求先の国が無くて請求書を作れなかったとき、取引先の画面へ移るボタンを出す
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceCreatePage from '../pages/invoice-create/InvoiceCreatePage';
import QuoteDetailPage from '../pages/quote-detail/QuoteDetailPage';
import en from '../locales/en.json';
import { ApiError } from '../lib/api';
import { queryClient } from '../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../lib/api')>()), api: mock }));
let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
function Location() { const value = useLocation(); return <output data-testid="location">{value.pathname}</output>; }
function wrap(node: React.ReactNode, entries = ['/start']) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}>{node}<Location /></MemoryRouter></I18nextProvider>; }
function routed(node: React.ReactNode, path: string, entries: string[]) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}><Routes><Route path={path} element={node} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>; }

const summary = { id: 7, quote_code: 'Q-7', company_id: 4, currency: 'USD', total_amount: 10, status: 'approved', created_at: '' };
const detail = { id: 7, quote_code: 'Q-7', company_id: 4, contact_id: 5, currency: 'USD', items: [{ product_id: 2, product_name: 'Card', quantity: 1, unit_price: 10, weight: null }] };
const approvedQuote = { id: 7, quote_code: 'Q-7', company_id: 4, currency: 'USD', subtotal: 10, shipping_fee: null, tax_amount: null, total_amount: 10, status: 'approved', validity_date: null, notes: null, created_at: '', items: [] };

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['invoices.create'] };
    if (url === '/quotes?status=approved') return [summary];
    if (url === '/quotes/7') return detail;
    if (url === '/companies?per_page=100') return [];
    if (url.startsWith('/contacts')) return [];
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected post'); });
  mock.patch.mockResolvedValue({});
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function loadQuoteIntoCreatePage() {
  render(wrap(<InvoiceCreatePage />));
  fireEvent.click(await screen.findByTestId('invoice-edit-from-quote-7'));
  expect(await screen.findByDisplayValue('Card')).toBeTruthy();
}

describe('bill-to country guidance (ADR-1061 bin2-2c2a)', () => {
  it('create page: shows the reason and a button that opens the customer page', async () => {
    await loadQuoteIntoCreatePage();
    mock.post.mockRejectedValue(new ApiError(tr('apiError.billToCountry'), 422, 'bill_to_country'));
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.createBtn') }));
    expect(await screen.findByText(tr('apiError.billToCountry'))).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.openCompanyForBillTo') }));
    expect(screen.getByTestId('location').textContent).toBe('/crm/companies/4');
  });

  it('create page: another error does not show the button', async () => {
    await loadQuoteIntoCreatePage();
    mock.post.mockRejectedValue(new ApiError('Other failure', 400, 'something_else'));
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.createBtn') }));
    expect(await screen.findByText('Other failure')).toBeTruthy();
    expect(screen.queryByRole('button', { name: tr('invoices.openCompanyForBillTo') })).toBeNull();
  });

  it('quote detail: converting shows the reason and a button that opens the customer page', async () => {
    mock.get.mockImplementation(async (url: string) => {
      if (url === '/me/permissions') return { permissions: ['invoices.create'] };
      if (url === '/quotes/7') return approvedQuote;
      throw new Error(`Unexpected GET ${url}`);
    });
    mock.post.mockRejectedValue(new ApiError(tr('apiError.billToCountry'), 422, 'bill_to_country'));
    render(routed(<QuoteDetailPage />, '/quotes/:id', ['/quotes/7']));
    fireEvent.click(await screen.findByRole('button', { name: tr('quotes.convertToInvoice') }));
    expect(await screen.findByText(tr('apiError.billToCountry'))).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.openCompanyForBillTo') }));
    expect((await screen.findByTestId('location')).textContent).toBe('/crm/companies/4');
  });
});
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/viewer-contract-bin2-2c2a && git log --oneline -1 | tail -1
    cd ~/sa && git merge-base --is-ancestor origin/main HEAD; echo "is-ancestor exit=$?"
  期待: 2行目 `is-ancestor exit=0`。1 なら `BLOCKED: 手順1 is-ancestor`（取り込みは Opus が行う）。

手順2 実装前点検 P1〜P14 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/viewer-contract-stage/card-2-2c2a.md | tail -1
    cd ~/sa && ls backend/app/services/issuer.py backend/tests/test_issuer.py frontend/src/components/BillToCountryGuidance.test.tsx 2>&1 | tail -3
    cd ~/sa && F=backend/app/routers/invoices.py && grep -c "ship_to_snapshot, bill_to_snapshot, fx_rate_snapshot$" $F; grep -c ":ship_to, :bill_to, :fx_rate$" $F; grep -c '"fx_rate": json.dumps(fx_snap) if fx_snap else None,$' $F; grep -c "    paypal_invoicer_view_url, paypal_copy_pdf_at$" $F; grep -c "    tenant_schema = await _get_tenant_schema(tenant_id)" $F; grep -c "from app.services.payment_dates import PAID_AT_SQL, paid_at_from_date, paypal_paid_at" $F; grep -c "issuer_region" $F
    cd ~/sa && F=backend/app/services/invoice_renderer.py && grep -c "    tenant_website: Optional\[str\] = None" $F; grep -c '        tenant_website=tenant_profile.get("website"),' $F; grep -c "registration_number" $F
    cd ~/sa && F=backend/app/schemas/invoice.py && grep -c "    paypal_copy_pdf_at: datetime | None = None" $F; grep -c "issuer_region" $F
    cd ~/sa && F=backend/tests/conftest.py && grep -c 'if "public.countries" in statement:' $F; grep -c "                paypal_copy_pdf_at TIMESTAMP$" $F; grep -c "        # === Phase 4 テーブル ===" $F; grep -c "DELETE FROM tenant_profile" $F; grep -c "prefectures" $F; grep -c "tenant_issuer_profiles" $F; grep -c "issuer_region" $F
    cd ~/sa && grep -c 'json={"name": company_name, "lead_id": lead_id})' backend/tests/test_invoices.py
    cd ~/sa && grep -c '"merge_target_archived",' backend/tests/test_api_error_reason_sync.py; grep -c "toBe(9)" frontend/src/lib/apiErrorReason.test.ts
    cd ~/sa && grep -c '"openCompanyForBillTo"\|"billToCountry"\|bill_to_country' frontend/src/locales/ja.json frontend/src/locales/en.json frontend/src/lib/apiErrorReason.ts | tail -3
    cd ~/sa && wc -l frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/quote-detail/QuoteDetailPage.tsx | tail -3
    cd ~/sa && python3 -c "import re,pathlib;r=pathlib.Path('backend/app');p=re.compile(r'\{[A-Za-z_]+\}\.tenant_profile\b|\"tenant_profile\"\s*\)|\bFROM\s+tenant_profile\b|\bINTO\s+tenant_profile\b|\bUPDATE\s+tenant_profile\b',re.I);[print(f.relative_to(r),i) for f in sorted(r.rglob('*.py')) for i,l in enumerate(f.read_text('utf-8').splitlines(),1) if p.search(l)]" | tail -15
    cd ~/sa && grep -c "issuer_region" frontend/api-contract/openapi.json; grep -c '"paypal_copy_pdf_at": {' frontend/api-contract/openapi.json
    cd ~/sa && grep -c 'json={"name": "統計テスト会社", "lead_id": lead_id})' backend/tests/test_company_stats.py; grep -c 'json={"name": "他社", "lead_id": other_lead_id})' backend/tests/test_company_stats.py; grep -c 'json={"name": "請求FK会社", "lead_id": lead_id})' backend/tests/test_products.py; grep -c 'json={"name": "Invoicingテスト会社", "lead_id": lead_id})' backend/tests/test_paypal_invoicing.py
    cd ~/sa && grep -c "ON CONFLICT (code) DO NOTHING;" docs/handoff/viewer-contract-stage/data/prefectures.sql
  期待（行の順に）: P1 ファイル名1行／P2 3つとも「No such file or directory」／P3 `2 2 2 1 3 1 0`（1行に1つずつ）／P4 `1 2 0`／P5 `1 0`／P6 `1 1 1 1 0 0 0`／P7 1／P8 `1 1`／P9 3ファイルとも `:0`／P10 437 と 216／P11 §0-3 の10行と同じ／P12 `0 2`／P13 `1 1 1 1`／P14 1。

手順3 §2 の変更をする（2-1 から 2-18 の順。2-2 は (1)〜(7)、(8)、(9) の順。新規の3ファイルは Write ツール、それ以外は Edit ツールで行う）

手順4 道具を入れる（本番と同じ Python 3.12 の venv を作業場所の外 ~/venv312 に作る。素の pip は見張り py312-guard が止めるので使わない）
    cd ~ && python3.12 --version 2>&1 | tail -1
    cd ~ && python3.12 -m venv ~/venv312 2>&1 | tail -3
    cd ~ && ~/venv312/bin/python --version 2>&1 | tail -1
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements-dev.txt 2>&1 | tail -3
    cd ~ && ~/venv312/bin/ruff --version | tail -1
  手順4 の python3.12 が無いときだけ、1行目と2行目の代わりに次を流す（それも失敗したら `BLOCKED: python3.12 なし`）。
    cd ~ && uv venv --python 3.12 ~/venv312 2>&1 | tail -3
    cd ~ && ~/venv312/bin/python -m ensurepip 2>&1 | tail -1

手順5 形と数（backend）
    cd ~/sa/backend && ~/venv312/bin/ruff check app/ 2>&1 | tail -10
    cd ~/sa && python3 scripts/lint_tenant_schema.py --mode strict backend/app/ 2>&1 | tail -5; echo "lint exit=$?"
    cd ~/sa && python3 -c "import re,pathlib;r=pathlib.Path('backend/app');p=re.compile(r'\{[A-Za-z_]+\}\.tenant_profile\b|\"tenant_profile\"\s*\)|\bFROM\s+tenant_profile\b|\bINTO\s+tenant_profile\b|\bUPDATE\s+tenant_profile\b',re.I);[print(f.relative_to(r),i) for f in sorted(r.rglob('*.py')) for i,l in enumerate(f.read_text('utf-8').splitlines(),1) if p.search(l)]" | tail -15
    cd ~/sa && F=backend/app/routers/invoices.py && grep -c "tenant_schema" $F; grep -c "_fetch_tenant_profile\|_get_tenant_schema" $F; grep -c 'get_issuer(db, tenant_id, row\["issuer_region"\] or "overseas")' $F; grep -c 'get_issuer(db, tenant_id, "overseas")' $F; grep -c 'detail="bill_to_country"' $F; grep -c "issuer_region" $F
  期待（上から順に）: ruff は `All checks passed!`（CI と同じく backend で `app/` だけを見る。tests は設定で対象外）／lint は失敗の行が無く `lint exit=0`／A40 は10行で、`routers/invoices.py` の行が無く `services/issuer.py` の行がちょうど1つ（残り9行は P11 の tenant_profile.py・label_validation.py・po_renderer.py・tenant.py の行と同じ）／`0 0 2 1 2` ・`14`（取り込み1・列の一覧1・2経路で決める行と if の行が計4・INSERT の列名2・値2・パラメータ2・PDF の入口2。違えば出力を貼って `BLOCKED: 手順5 数`）。
  ※ lint の `echo "lint exit=$?"` は tail の終了コードを示すので、判定は lint の出力の中身（`violation`・`error` の行が無いこと）で行う。

手順6 backend の試験（failed と error は 0 であること）
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_issuer.py tests/test_api_error_reason_sync.py tests/test_prefectures_seed.py 2>&1 | tail -15
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_invoices.py tests/test_company_stats.py tests/test_products.py tests/test_paypal_invoicing.py 2>&1 | tail -15
  期待: どちらも failed 0・error 0。1本目の passed に test_issuer.py の試験を含む（pdfminer が無くて skipped が出たら §4 のとおり記録）。

手順7 API の形を作り直す（CI「API の形」の検査と同じ道具）
    cd ~/sa/backend && ENVIRONMENT=test ~/venv312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -3
    cd ~/sa && git diff --stat frontend/api-contract/openapi.json | tail -2
    cd ~/sa && grep -c '"issuer_region": {' frontend/api-contract/openapi.json
    cd ~/sa && git diff -U0 frontend/api-contract/openapi.json | grep -c "^-[^-]"
  期待: 3行目 2（InvoiceResponse と InvoiceDetailResponse）。4行目 0（消えた行が無い。足しただけ）。0 でなければ差分の最初の 40 行を `git diff -U0 frontend/api-contract/openapi.json | head -40` で貼って `BLOCKED: openapi`。

手順8 frontend（node が無いときは §4 のとおり）
    cd ~/sa/frontend && node --version | tail -1 && npm --version | tail -1
    cd ~/sa/frontend && npm ci 2>&1 | tail -3
    cd ~/sa/frontend && npm run generate:api-types 2>&1 | tail -3
    cd ~/sa/frontend && npx tsc --noEmit -p . 2>&1 | tail -15; echo "tsc done"
    cd ~/sa/frontend && npm run test:unit -- src/components/BillToCountryGuidance.test.tsx src/lib/apiErrorReason.test.ts src/components/CommerceNavigationButtonMigration.test.tsx 2>&1 | tail -20
    cd ~/sa/frontend && npm run check:all 2>&1 | tail -30
    cd ~/sa/frontend && wc -l src/pages/invoice-create/InvoiceCreatePage.tsx src/pages/quote-detail/QuoteDetailPage.tsx | tail -3
  期待: tsc はエラーの行が無く `tsc done`。試験は failed 0（3ファイルとも passed）。check:all はどの検査も失敗しない（最後に失敗の行が無い）。行数はどちらも 800 未満。

手順9 変えたファイルの名前と数
    cd ~/sa && git status --short | tail -25
    cd ~/sa && git diff --stat | tail -25
  期待: §1 の 19 ファイルだけ（新規の3ファイルは `??` で各1行）。`frontend/src/api/generated/schema.d.ts` が出たら、それは追跡しないファイルなので add しない（`git status` に出ても §1 の外として数えない）。ほかのファイルが出たら `BLOCKED: 範囲外のファイル`。

手順10 記録と送り出し
    cd ~/sa && git add backend/app/services/issuer.py backend/app/routers/invoices.py backend/app/services/invoice_renderer.py backend/app/schemas/invoice.py backend/tests/conftest.py backend/tests/test_invoices.py backend/tests/test_company_stats.py backend/tests/test_products.py backend/tests/test_paypal_invoicing.py backend/tests/test_api_error_reason_sync.py backend/tests/test_issuer.py frontend/src/lib/apiErrorReason.ts frontend/src/lib/apiErrorReason.test.ts frontend/src/locales/ja.json frontend/src/locales/en.json frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/quote-detail/QuoteDetailPage.tsx frontend/src/components/BillToCountryGuidance.test.tsx frontend/api-contract/openapi.json && git status --short | tail -25
    cd ~/sa && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(invoices): read issuer from issuer profiles and decide issuer region from bill-to country (ADR-1061 bin2-2c2a)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/viewer-contract-bin2-2c2a 2>&1 | tail -3
    cd ~/sa && git log --oneline origin/release/viewer-contract-bin2-2c2a -2 | tail -2
  `git add` の後の status で、ステージした行（1文字目が空白でない行）に §1 に無いファイルがあれば、commit せずに `BLOCKED: 範囲外のファイル` で停止する。

## 4. 想定される分かれ道

- 停止する（その場で作業を停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - 手順1 の is-ancestor が 0 でない・P1〜P14 のどれかが外れた → `BLOCKED: 手順1` か `BLOCKED: P番号`。
  - §2 の変更前の文が見つからない・決めた数と違う → `BLOCKED: ファイル名 変更前の文`。
  - 手順5 の数・A40 の期待が外れた → 出力を貼って `BLOCKED: 手順5`。
  - 手順6 か手順8 で failed か error が 1 件でも出た → 試験も本体も直さず最後の行を貼って `BLOCKED: pytest` か `BLOCKED: vitest`。ただしカードからの書き写し間違い（字・字下げ）が出力から分かるときだけ、カードの文に合わせて直してよい。直したら何をどう直したかを書く。
  - tsc・check:all が失敗した → 最後の行を貼って `BLOCKED: tsc` か `BLOCKED: check:all`。
  - 手順7 の期待が外れた → `BLOCKED: openapi`。
  - push が拒まれた → 最後の 3 行を貼って `BLOCKED: push`（force はしない）。
- 記録して続ける（値を報告に書き、判定は Opus がする）:
  - ruff が何か出した → `--fix` は流さず、出力を貼って `BLOCKED: ruff`。
  - 手順6 で skipped が出る（pdfminer が無い・実 PostgreSQL の試験）→ そのまま件数を書く。
  - 手順8 で node か npm が無い → `frontend 未実行（node なし）` と書いて手順9 へ進む（CI の frontend の検査で Opus が確かめる）。

## 5. 報告の形

- 宛先: 完了報告の本文（クラウドの実行の最後の返事）。ファイルに書かない。
- 1 行目: `RECEIVED viewer-contract-bin2-2c2a HEAD=…`。2 行目: 「本報告はカード 便2-2c2a 請求書・見積書の発行元を新しい表から読み、請求先の国で地域を決める の実行結果である」。
- 手順1・2・4・5・6・7・8・9・10 の出力（tail の範囲）をそのまま貼る。要約しない。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。待ちが要るものは Opus が見る（CI の結果など）。
- ファイルの編集は Edit ツールで行う（新規の3ファイルだけ Write ツール）。ヒアドキュメントで書かない。
- PR は作らない（Opus が作り、`scripts/dev/validate-pr-body.sh` で確かめる）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

END OF CARD
