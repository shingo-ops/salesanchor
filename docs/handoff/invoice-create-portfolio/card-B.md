# card: 便B 関税の額の画面と API を作る（invoice-create-portfolio）

状態: カード発行（Opus、2026-11-15）。PO の設計承認と実装承認は 2026-11-13「1,（２）決済手数料を合計に足す仕組みは、今回は作りません。別の作業に回します。→次便で」と、同じ日の常設の指示「…確立したなら進める。…PRマージ、デプロイまで完走させてくれ。」（design.md 第9版・審査 APPROVE）。2026-11-15 に PO が「1」で「振込先の画面と、請求書の画面の作業に進む」を選んだ。
設計: docs/handoff/invoice-create-portfolio/design.md §3-2（通貨の選択肢）・§3-3（関税の決まり・重なりの 409・送料の会社の形）・§3-6（関税の額の画面）・§5 の便 B・§8 の K18・K20。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret・DB には触らない。PR は作らない（Opus が作る）。
基準: origin/main `46b57dfef` で行番号と数を測った。行番号がずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で停止）。
危険便か: いいえ（`migrations/`・`.github/workflows/`・本番の `scripts/` を触らない。表は便A で作り済み）。マージ前に Opus の審査役の APPROVE と CI 全通過を必須にする（担当の作業ではない）。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと（このカードで固めたこと。根拠つき）

- D1 この便は「関税の額の決まりを見る・足す・直す・消す」API と画面だけ。請求書の計算（便C）・請求書の画面（便D）・PDF はしない。表は便A（PR #5507）で各テナントに作り済み（tenant_duty_rules・tenant_duty_rule_components。backend/app/services/tenant.py の `CREATE TABLE IF NOT EXISTS {schema}.tenant_duty_rules (`）。移行は足さない。
- D2 API は 5 本。`GET /api/v1/admin/duty-rules`（一覧）・`GET /api/v1/admin/duty-rules/options`（今の関税の条件・通貨・基準の選択肢）は tenant.profile.view か tenant.profile.edit。`POST /api/v1/admin/duty-rules`（201）・`PUT /api/v1/admin/duty-rules/{rule_id}`・`DELETE /api/v1/admin/duty-rules/{rule_id}`（204）は tenant.profile.edit（design.md §3-6）。
- D3 関税の条件（DAP・DDU・DDP）の正本は tenant_settings.duty_incoterms だけ（design.md §3-3）。options はそこを読むだけで、この画面から変えない。画面は条件を読むだけで出し、変えるのは会社の決まりのページ（/management-center/tenant-policy）への文字のリンク。DAP・DDU のときは「今は関税を請求しません」を出す（design.md §3-6）。
- D4 通貨の選択肢は `JPY` と public.app_fx_rate_history にある通貨（JPY 以外・重なりなし・並べ替え）。画面に通貨を書かない（design.md §3-2・PO 2026-11-13「ハードコードはなくしてDBから該当する部分を取得するSSOTを採用」）。app_fx_rate_history の読みの決まりは全ロール許可（migrations/20261003_100000_create_app_fx_rate_history.sql「全ロール許可（為替は公開情報・テナント分離不要）」）。
- D5 同じ国・同じ送料の会社で有効期間が重なると 409 `duty_rule_overlap`（重なった相手の id を `rule_ids` に入れる）。送料の会社は小文字・前後の空白なしで保存し、空は NULL（「どの送料の会社でも」）。NULL どうしも重なりとして数える（IS NOT DISTINCT FROM）。PUT は自分の行を除いて比べる。同時に足された2件を両方通さないよう、会社と国の組で pg_advisory_xact_lock を取る（design.md §3-3・K18）。
- D6 止めてある決まり（is_active が偽）は重なりの比べに入れない。止めた古い決まりを残したまま、同じ期間に新しい決まりを足せるようにするため（請求書の計算でも止めた決まりは使わない。design.md §3-3 の is_active）。
- D7 足す・直す・消すのたびに、その会社の audit_logs に1行を足す（record_audit_log、table "tenant_duty_rules"、action は create・update・delete、直す前後の値つき。K20）。commit の直後に reset_tenant_context() を呼ぶ（ADR-072）。
- D8 書き込みの3本は backend/app/realtime/topics.py の NO_SIGNAL_ROUTES に、ほかの管理の口と同じ `_PENDING` で載せる（合図は出さない。test_realtime_topics.py が新しい書き込みルートの載せ忘れを赤にする）。
- D9 画面は 管理センター の「ビジネス設定」の並びに「関税の額」として足す（/management-center/duty-rules。ManagementCenterPage の business の並び・App.tsx の management-center の下）。/admin の入口には足さない。メニューの権限は menuPermissions.ts に `dutyRules`（tenant.profile.edit か tenant.profile.view）を足し、テナント管理の行に載せる。
- D10 部品は金型だけを使う（ADR-144）: PageLayout・DataTable・Button・Badge・Callout・Stack・TextLink・ConfirmModal・Modal・TextField・Textarea・Select・Toggle・CountryCombobox・LoadingBlock・Spinner。色・大きさの直書きと新しい CSS は無い。文字はすべて t()（ADR-027）で、ja.json と en.json に同じ鍵（dutyRules の 51 鍵と nav.dutyRules）。失敗の文は「起きたこと＋次にすること」（ADR-1071。check-error-text-next-action.js で確かめた）。
- D11 数（率・下限・上限）は画面で丸めず、文字のまま送り、文字のまま受け取る（サーバーの Decimal が正本）。
- D12 PG の試験のテナント番号は 964（2026-11-15 に 46b57dfef で backend・migrations・scripts を `git grep -w 964` して 0 件。962 は便A、963 は発行元の表の試験が使う）。
- D13 API の形が変わるので frontend/api-contract/openapi.json を作り直して入れる（.github/workflows/api-contract-check.yml が照合する）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らない（Opus が作る） | ○（冒頭・§5） |
| 3 | 報告の宛先と生出力の扱い | ○（§5。完了報告の本文に各手順の出力を tail の範囲でそのまま貼る） |
| 4 | 1便1目的 | ○（関税の額の決まりの API と画面。D1） |
| 5 | 既存ブランチへの追記ではない | ○（このカードが main に入った後、Opus が origin/main から新しい実装の枝 `release/invoice-create-portfolio-bin-b` を作る） |
| 6 | 書式は実例で示した | ○（§2 に新規の全文と、既存の変更前・変更後） |
| 7 | 合格基準を出力まで縛った | ○（§3 の各手順の期待） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（手順9 の `git status --short` と `git diff --stat`） |
| 9 | 出力量に上限のないコマンドを使わない | ○（すべて tail か wc） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§4・§5・末尾） |
| 11 | 期待値は実測から | ○（P の数は 46b57dfef で実測。画面の差し込みは 46b57dfef の写しに §2 を当て、check-page-layout・check-i18n-missing-keys・check-error-text-next-action・check-loading-clear・check-page-size・check-nav-title-sync など 12 本が通ることを確かめた。ruff と py_compile も通った） |
| 12 | 停止は本番影響のあるものに限る | ○（§4） |
| 13 | 委任文の定型4点 | ○（§6） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない（commit は git log で確かめる） | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2 は全文） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-create-portfolio-B HEAD=`（続けて `git rev-parse HEAD` の 40 桁）。2 行目に「本報告はカード 便B 関税の額の画面と API を作る の実行結果である」と書く。

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

- P1 `docs/handoff/invoice-create-portfolio/card-B.md`（このカード）が枝に在る。
- P2 §1 の新規 10 ファイルがどれも無い（`ls` が 10 行とも「No such file or directory」）。
- P3 表は便A で作り済み: `grep -c "CREATE TABLE IF NOT EXISTS {schema}.tenant_duty_rules (" backend/app/services/tenant.py` が 1、`grep -c "CREATE TABLE IF NOT EXISTS {schema}.tenant_duty_rule_components ("` が 1。
- P4 まだ API も画面も無い: `grep -rc "duty-rules\|duty_rules" backend/app/main.py backend/app/realtime/topics.py frontend/src/App.tsx frontend/src/constants/menuPermissions.ts` がどれも 0。`grep -c '"dutyRules"' frontend/src/locales/ja.json frontend/src/locales/en.json` がどちらも 0。
- P5 §2 の「変更前」の目印の行が、それぞれのファイルに 1 回ずつある（手順2 の `grep -c -x -F` がどれも 1）。
- P6 `git grep -c -w 964 -- backend migrations scripts` が何も出さない（試験のテナント番号 964 は未使用。D12）。

## 1. 触るファイル

1. backend/app/schemas/duty_rules.py（新規）
2. backend/app/services/duty_rules.py（新規）
3. backend/app/services/fx_currencies.py（新規）
4. backend/app/routers/duty_rules.py（新規）
5. backend/tests/test_duty_rules_router.py（新規）
6. backend/tests/test_duty_rules_pg.py（新規）
7. frontend/src/pages/admin/dutyRuleTypes.ts（新規）
8. frontend/src/pages/admin/DutyRuleFormModal.tsx（新規）
9. frontend/src/pages/admin/DutyRulesPage.tsx（新規）
10. frontend/src/pages/admin/DutyRulesPage.test.tsx（新規）
11. backend/app/main.py
12. backend/app/realtime/topics.py
13. frontend/src/App.tsx
14. frontend/src/pages/management-center/ManagementCenterPage.tsx
15. frontend/src/pages/management-center/ManagementCenterPage.test.tsx
16. frontend/src/constants/menuPermissions.ts
17. frontend/src/constants/menuPermissions.test.ts
18. frontend/src/locales/ja.json
19. frontend/src/locales/en.json
20. frontend/api-contract/openapi.json（手順7 の書き出しで作り直す。手で書かない）

触らない: 上に無いファイル全部。特に migrations/・backend/app/services/tenant.py・.github/workflows/ の全部・frontend/src/components/・CSS ファイル・frontend/src/pages/admin/AdminHubPage.tsx。

## 2. 変更

### 2-1. backend/app/schemas/duty_rules.py（新規。全文）

```python
"""関税の額の決まりの入出力の形（invoice-create-portfolio 便B・design.md §3-3・§3-6）。

表は migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql（会社ごとのスキーマ）。
- 送料の会社（carrier）は前後の空白を除き小文字にして持つ。空の文字は「どの会社でも」（NULL）。
- 根拠の URL は必須（ADR-095 付録1-4）。
- 基準（base）の3つは表の CHECK と同じ。並びの正本はこの DutyBase だけ（画面は /admin/duty-rules/options で受け取る）。
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DutyBase = Literal["subtotal", "subtotal_shipping", "subtotal_shipping_prior"]
DUTY_BASES: tuple[str, ...] = get_args(DutyBase)


def _strip(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class DutyComponentIn(BaseModel):
    """関税の中身の1行（例: 関税・DDP 手数料・MPF）。"""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., min_length=1)
    base: DutyBase
    rate_pct: Decimal = Field(..., ge=0, max_digits=8, decimal_places=4)
    min_amount: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    max_amount: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    amount_currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")

    @field_validator("label", mode="before")
    @classmethod
    def _strip_label(cls, value: Any) -> Any:
        return _strip(value)

    @field_validator("min_amount", "max_amount", "amount_currency", mode="before")
    @classmethod
    def _blank_amounts(cls, value: Any) -> Any:
        return _blank_to_none(value)

    @model_validator(mode="after")
    def _check_amounts(self) -> "DutyComponentIn":
        if self.min_amount is not None and self.max_amount is not None and self.min_amount > self.max_amount:
            raise ValueError("min_amount must be <= max_amount")
        if (self.min_amount is not None or self.max_amount is not None) and self.amount_currency is None:
            raise ValueError("amount_currency is required with min_amount or max_amount")
        return self


class DutyRuleIn(BaseModel):
    """関税の額の決まり1件（足す・直すで同じ形。中身の行は丸ごと置き換える）。"""

    model_config = ConfigDict(extra="forbid")

    destination_country_code: str = Field(..., pattern=r"^[A-Z]{2}$")
    carrier: str | None = Field(None, max_length=50)
    label: str = Field(..., min_length=1)
    effective_from: datetime.date
    effective_to: datetime.date | None = None
    source_url: str = Field(..., pattern=r"^https?://\S+$")
    note: str | None = None
    is_active: bool = True
    components: list[DutyComponentIn] = Field(..., min_length=1, max_length=20)

    @field_validator("destination_country_code", mode="before")
    @classmethod
    def _upper_country(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("carrier", mode="before")
    @classmethod
    def _normalize_carrier(cls, value: Any) -> Any:
        # 表の CHECK（carrier = lower(btrim(carrier)) AND carrier <> ''）と同じ形にそろえる（design.md §3-3 第7版）
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value

    @field_validator("label", "source_url", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> Any:
        return _strip(value)

    @field_validator("note", "effective_to", mode="before")
    @classmethod
    def _blank(cls, value: Any) -> Any:
        return _blank_to_none(value)

    @model_validator(mode="after")
    def _check_period(self) -> "DutyRuleIn":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be >= effective_from")
        return self


class DutyComponentRead(BaseModel):
    id: int
    sort_order: int
    label: str
    base: str
    rate_pct: str
    min_amount: str | None = None
    max_amount: str | None = None
    amount_currency: str | None = None


class DutyRuleRead(BaseModel):
    id: int
    destination_country_code: str
    carrier: str | None = None
    label: str
    effective_from: datetime.date
    effective_to: datetime.date | None = None
    source_url: str
    note: str | None = None
    is_active: bool
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None
    components: list[DutyComponentRead]


class DutyRuleOptions(BaseModel):
    """画面の選択肢（正本はそれぞれ tenant_settings・為替の表・DutyBase）。"""

    duty_incoterms: str
    currencies: list[str]
    bases: list[str]
```

### 2-2. backend/app/services/duty_rules.py（新規。全文）

```python
"""関税の額の決まりを読む・足す・直す・消す（invoice-create-portfolio 便B・design.md §3-3）。

- 表は会社ごとのスキーマの tenant_duty_rules と tenant_duty_rule_components（便Aで作成済み）。
- ここでは commit しない。commit と取引の後始末は呼ぶ側（routers/duty_rules.py）が行う。
- 同じ国・同じ送料の会社で、有効な決まりの期間が重なるときは DutyRuleOverlap を上げる（K18）。
  - 送料の会社は schemas/duty_rules.py で小文字・空白なしにそろえてから来る。空は NULL（どの会社でも）。
  - NULL どうしも同じとみなす（IS NOT DISTINCT FROM）。
  - 直すときは自分の行を比べる相手から外す。
  - 同時に足したときの取りこぼしを防ぐため、会社と国ごとの取引ロックを取ってから調べる（PostgreSQL のみ）。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import is_postgresql, tenant_table_ref
from app.schemas.duty_rules import DutyRuleIn

_RULE_COLS = (
    "id, destination_country_code, carrier, label, effective_from, effective_to, "
    "source_url, note, is_active, created_at, updated_at"
)
_COMPONENT_COLS = "id, rule_id, sort_order, label, base, rate_pct, min_amount, max_amount, amount_currency"


class DutyRuleNotFound(Exception):
    """指定の決まりがこの会社に無い。"""


class DutyCountryInvalid(Exception):
    """国の表（public.countries）に有効な国として無い。"""


class DutyRuleOverlap(Exception):
    """同じ国・同じ送料の会社で、有効な決まりの期間が重なる。"""

    def __init__(self, rule_ids: list[int]) -> None:
        super().__init__("duty_rule_overlap")
        self.rule_ids = rule_ids


def _dec(value: Any) -> str | None:
    return None if value is None else str(value)


def _component_out(row: Any) -> dict:
    return {
        "id": row["id"],
        "sort_order": row["sort_order"],
        "label": row["label"],
        "base": row["base"],
        "rate_pct": _dec(row["rate_pct"]),
        "min_amount": _dec(row["min_amount"]),
        "max_amount": _dec(row["max_amount"]),
        "amount_currency": row["amount_currency"],
    }


def _rule_out(row: Any, components: list[dict]) -> dict:
    return {
        "id": row["id"],
        "destination_country_code": (row["destination_country_code"] or "").strip(),
        "carrier": row["carrier"],
        "label": row["label"],
        "effective_from": row["effective_from"],
        "effective_to": row["effective_to"],
        "source_url": row["source_url"],
        "note": row["note"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "components": components,
    }


async def _components_by_rule(db: AsyncSession, tenant_id: int, rule_ids: list[int]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {rid: [] for rid in rule_ids}
    if not rule_ids:
        return out
    comps = tenant_table_ref(db, tenant_id, "tenant_duty_rule_components")
    if is_postgresql(db):
        result = await db.execute(
            text(f"SELECT {_COMPONENT_COLS} FROM {comps} "
                 "WHERE rule_id = ANY(CAST(:ids AS INTEGER[])) ORDER BY rule_id, sort_order, id"),
            {"ids": rule_ids},
        )
    else:
        placeholders = ", ".join(f":id{i}" for i in range(len(rule_ids)))
        result = await db.execute(
            text(f"SELECT {_COMPONENT_COLS} FROM {comps} "
                 f"WHERE rule_id IN ({placeholders}) ORDER BY rule_id, sort_order, id"),
            {f"id{i}": rid for i, rid in enumerate(rule_ids)},
        )
    for row in result.mappings().all():
        out.setdefault(row["rule_id"], []).append(_component_out(row))
    return out


async def list_duty_rules(db: AsyncSession, tenant_id: int) -> list[dict]:
    """この会社の決まりを国・送料の会社・始まりの日の順で返す（中身の行つき）。"""
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    result = await db.execute(
        text(f"SELECT {_RULE_COLS} FROM {rules} "
             "ORDER BY destination_country_code, carrier NULLS FIRST, effective_from, id"),
    )
    rows = result.mappings().all()
    comps = await _components_by_rule(db, tenant_id, [r["id"] for r in rows])
    return [_rule_out(r, comps.get(r["id"], [])) for r in rows]


async def get_duty_rule(db: AsyncSession, tenant_id: int, rule_id: int) -> dict:
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    result = await db.execute(
        text(f"SELECT {_RULE_COLS} FROM {rules} WHERE id = :id"),
        {"id": rule_id},
    )
    row = result.mappings().first()
    if row is None:
        raise DutyRuleNotFound()
    comps = await _components_by_rule(db, tenant_id, [rule_id])
    return _rule_out(row, comps.get(rule_id, []))


async def _check_country(db: AsyncSession, country_code: str) -> None:
    result = await db.execute(
        text("SELECT 1 FROM public.countries WHERE code = :code AND is_active = TRUE"),
        {"code": country_code},
    )
    if result.first() is None:
        raise DutyCountryInvalid()


async def _lock_and_check_overlap(db: AsyncSession, tenant_id: int, body: DutyRuleIn, exclude_id: int) -> None:
    """期間の重なりを調べる。重なる相手の id を DutyRuleOverlap で返す。"""
    if is_postgresql(db):
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
            {"k": f"duty_rules:{int(tenant_id)}:{body.destination_country_code}"},
        )
    if not body.is_active:
        # 使わない決まりは請求書の計算に出ないので、重なりを調べない（D6）
        return
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    result = await db.execute(
        text(f"""
            SELECT id FROM {rules}
            WHERE destination_country_code = :country
              AND carrier IS NOT DISTINCT FROM CAST(:carrier AS VARCHAR)
              AND is_active = TRUE
              AND id <> :exclude_id
              AND effective_from <= COALESCE(CAST(:to_date AS DATE), DATE '9999-12-31')
              AND COALESCE(effective_to, DATE '9999-12-31') >= CAST(:from_date AS DATE)
            ORDER BY id
        """),
        {
            "country": body.destination_country_code,
            "carrier": body.carrier,
            "exclude_id": exclude_id,
            "from_date": body.effective_from,
            "to_date": body.effective_to,
        },
    )
    ids = [r[0] for r in result.all()]
    if ids:
        raise DutyRuleOverlap(ids)


async def _insert_components(db: AsyncSession, tenant_id: int, rule_id: int, body: DutyRuleIn) -> None:
    comps = tenant_table_ref(db, tenant_id, "tenant_duty_rule_components")
    for index, comp in enumerate(body.components):
        await db.execute(
            text(f"""
                INSERT INTO {comps}
                    (rule_id, tenant_id, sort_order, label, base, rate_pct, min_amount, max_amount, amount_currency)
                VALUES (:rule_id, :tenant_id, :sort_order, :label, :base, :rate_pct, :min_amount, :max_amount,
                        :amount_currency)
            """),
            {
                "rule_id": rule_id,
                "tenant_id": int(tenant_id),
                "sort_order": index,
                "label": comp.label,
                "base": comp.base,
                "rate_pct": comp.rate_pct,
                "min_amount": comp.min_amount,
                "max_amount": comp.max_amount,
                "amount_currency": comp.amount_currency,
            },
        )


async def create_duty_rule(db: AsyncSession, tenant_id: int, body: DutyRuleIn) -> dict:
    await _check_country(db, body.destination_country_code)
    await _lock_and_check_overlap(db, tenant_id, body, exclude_id=0)
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    result = await db.execute(
        text(f"""
            INSERT INTO {rules}
                (tenant_id, destination_country_code, carrier, label, effective_from, effective_to,
                 source_url, note, is_active)
            VALUES (:tenant_id, :country, :carrier, :label, :from_date, :to_date, :source_url, :note, :is_active)
            RETURNING id
        """),
        {
            "tenant_id": int(tenant_id),
            "country": body.destination_country_code,
            "carrier": body.carrier,
            "label": body.label,
            "from_date": body.effective_from,
            "to_date": body.effective_to,
            "source_url": body.source_url,
            "note": body.note,
            "is_active": body.is_active,
        },
    )
    rule_id = int(result.scalar_one())
    await _insert_components(db, tenant_id, rule_id, body)
    return await get_duty_rule(db, tenant_id, rule_id)


async def update_duty_rule(db: AsyncSession, tenant_id: int, rule_id: int, body: DutyRuleIn) -> tuple[dict, dict]:
    """直す。戻り値は（直す前, 直した後）。中身の行は丸ごと置き換える。"""
    before = await get_duty_rule(db, tenant_id, rule_id)
    await _check_country(db, body.destination_country_code)
    await _lock_and_check_overlap(db, tenant_id, body, exclude_id=rule_id)
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    comps = tenant_table_ref(db, tenant_id, "tenant_duty_rule_components")
    await db.execute(
        text(f"""
            UPDATE {rules}
            SET destination_country_code = :country, carrier = :carrier, label = :label,
                effective_from = :from_date, effective_to = :to_date, source_url = :source_url,
                note = :note, is_active = :is_active, updated_at = now()
            WHERE id = :id
        """),
        {
            "id": rule_id,
            "country": body.destination_country_code,
            "carrier": body.carrier,
            "label": body.label,
            "from_date": body.effective_from,
            "to_date": body.effective_to,
            "source_url": body.source_url,
            "note": body.note,
            "is_active": body.is_active,
        },
    )
    await db.execute(text(f"DELETE FROM {comps} WHERE rule_id = :id"), {"id": rule_id})
    await _insert_components(db, tenant_id, rule_id, body)
    after = await get_duty_rule(db, tenant_id, rule_id)
    return before, after


async def delete_duty_rule(db: AsyncSession, tenant_id: int, rule_id: int) -> dict:
    """消す。戻り値は消す前の中身（監査の記録に使う）。中身の行は表の ON DELETE CASCADE で消える。"""
    before = await get_duty_rule(db, tenant_id, rule_id)
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    await db.execute(text(f"DELETE FROM {rules} WHERE id = :id"), {"id": rule_id})
    return before


async def get_duty_incoterms(db: AsyncSession, tenant_id: int) -> str | None:
    """関税の条件の正本 tenant_settings.duty_incoterms を読む（design.md §3-6）。行が無いときは None。"""
    result = await db.execute(
        text("SELECT duty_incoterms FROM public.tenant_settings WHERE tenant_id = :tenant_id"),
        {"tenant_id": int(tenant_id)},
    )
    row = result.first()
    return None if row is None else row[0]
```

### 2-3. backend/app/services/fx_currencies.py（新規。全文）

```python
"""請求に使える通貨の一覧（invoice-create-portfolio 便B・design.md §3-2）。

正本は為替の履歴の表 public.app_fx_rate_history（ハードコードしない。PO 2026-11-13）。
円（JPY）は為替の表に行が無くても常に使えるので先頭に置く。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_invoice_currencies(db: AsyncSession) -> list[str]:
    result = await db.execute(
        text(
            "SELECT DISTINCT currency FROM public.app_fx_rate_history "
            "WHERE currency <> 'JPY' ORDER BY currency"
        ),
    )
    return ["JPY", *[str(r[0]) for r in result.all()]]
```

### 2-4. backend/app/routers/duty_rules.py（新規。全文）

```python
"""関税の額の決まりの入口（invoice-create-portfolio 便B・design.md §3-3・§3-6・K18・K20）。

- 見る: tenant.profile.view か tenant.profile.edit。足す・直す・消す: tenant.profile.edit。
- 書いたら同じ取引で、その会社の audit_logs に1行ずつ残す（K20）。
- 失敗の detail は識別子だけの dict にする（test_error_detail_guard.py）。画面が辞書の文に置き換える。
"""
from __future__ import annotations

import json
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    set_tenant_context,
)
from app.database import get_db
from app.models import User
from app.schemas.duty_rules import DUTY_BASES, DutyRuleIn, DutyRuleOptions, DutyRuleRead
from app.services import duty_rules as svc
from app.services.audit import record_audit_log
from app.services.fx_currencies import list_invoice_currencies

router = APIRouter()

_TABLE = "tenant_duty_rules"


def _audit_dict(rule: dict) -> dict:
    return json.loads(DutyRuleRead.model_validate(rule).model_dump_json())


def _raise_for(exc: Exception) -> NoReturn:
    if isinstance(exc, svc.DutyRuleNotFound):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "duty_rule_not_found"})
    if isinstance(exc, svc.DutyCountryInvalid):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "duty_country"})
    if isinstance(exc, svc.DutyRuleOverlap):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "duty_rule_overlap", "rule_ids": exc.rule_ids},
        )
    raise exc


@router.get(
    "/admin/duty-rules",
    response_model=list[DutyRuleRead],
    summary="関税の額の決まりの一覧",
    dependencies=[Depends(require_permission("tenant.profile.view", "tenant.profile.edit"))],
)
async def list_rules(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    await set_tenant_context(db, tenant_id)
    return await svc.list_duty_rules(db, tenant_id)


@router.get(
    "/admin/duty-rules/options",
    response_model=DutyRuleOptions,
    summary="関税の額の画面の選択肢（関税の条件・通貨・基準）",
    dependencies=[Depends(require_permission("tenant.profile.view", "tenant.profile.edit"))],
)
async def get_options(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> DutyRuleOptions:
    await set_tenant_context(db, tenant_id)
    incoterms = await svc.get_duty_incoterms(db, tenant_id)
    if incoterms is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "tenant_settings_missing"})
    currencies = await list_invoice_currencies(db)
    return DutyRuleOptions(duty_incoterms=incoterms, currencies=currencies, bases=list(DUTY_BASES))


@router.post(
    "/admin/duty-rules",
    response_model=DutyRuleRead,
    status_code=status.HTTP_201_CREATED,
    summary="関税の額の決まりを足す",
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def create_rule(
    body: DutyRuleIn,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, tenant_id)
    try:
        created = await svc.create_duty_rule(db, tenant_id, body)
    except (svc.DutyCountryInvalid, svc.DutyRuleOverlap) as exc:
        await db.rollback()
        _raise_for(exc)
    await record_audit_log(
        db, tenant_id, current_user.id, "create", _TABLE,
        record_id=created["id"], new_data=_audit_dict(created),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return created


@router.put(
    "/admin/duty-rules/{rule_id}",
    response_model=DutyRuleRead,
    summary="関税の額の決まりを直す",
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def update_rule(
    rule_id: int,
    body: DutyRuleIn,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await set_tenant_context(db, tenant_id)
    try:
        before, after = await svc.update_duty_rule(db, tenant_id, rule_id, body)
    except (svc.DutyRuleNotFound, svc.DutyCountryInvalid, svc.DutyRuleOverlap) as exc:
        await db.rollback()
        _raise_for(exc)
    await record_audit_log(
        db, tenant_id, current_user.id, "update", _TABLE,
        record_id=rule_id, old_data=_audit_dict(before), new_data=_audit_dict(after),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return after


@router.delete(
    "/admin/duty-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="関税の額の決まりを消す",
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> None:
    await set_tenant_context(db, tenant_id)
    try:
        before = await svc.delete_duty_rule(db, tenant_id, rule_id)
    except svc.DutyRuleNotFound as exc:
        await db.rollback()
        _raise_for(exc)
    await record_audit_log(
        db, tenant_id, current_user.id, "delete", _TABLE,
        record_id=rule_id, old_data=_audit_dict(before),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
```

### 2-5. backend/tests/test_duty_rules_router.py（新規。全文）

```python
"""関税の額の決まりの入口の試験（invoice-create-portfolio 便B・K18・K20）。

中身の SQL は test_duty_rules_pg.py で本物の PostgreSQL に当てる。ここでは入口の形・権限・監査の記録・失敗の形を見る。
"""
from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.services import duty_rules as svc

BASE = "/api/v1/admin/duty-rules"

_RULE = {
    "id": 7,
    "destination_country_code": "US",
    "carrier": "fedex",
    "label": "US DDP FedEx",
    "effective_from": datetime.date(2026, 1, 1),
    "effective_to": None,
    "source_url": "https://www.fedex.com/en-us/billing/duty-tax.html",
    "note": None,
    "is_active": True,
    "created_at": None,
    "updated_at": None,
    "components": [
        {"id": 1, "sort_order": 0, "label": "Duty", "base": "subtotal", "rate_pct": "15.0000",
         "min_amount": None, "max_amount": None, "amount_currency": None},
    ],
}

_BODY = {
    "destination_country_code": " us ",
    "carrier": " FedEx ",
    "label": "US DDP FedEx",
    "effective_from": "2026-01-01",
    "effective_to": "",
    "source_url": "https://www.fedex.com/en-us/billing/duty-tax.html",
    "components": [{"label": "Duty", "base": "subtotal", "rate_pct": "15"}],
}


@pytest.fixture
def audit():
    mock = AsyncMock()
    with patch("app.routers.duty_rules.record_audit_log", mock):
        yield mock


@pytest.mark.asyncio
async def test_list_returns_rules(client, audit):
    with patch.object(svc, "list_duty_rules", AsyncMock(return_value=[_RULE])):
        res = await client.get(BASE)
    assert res.status_code == 200
    assert res.json()[0]["carrier"] == "fedex"
    assert res.json()[0]["components"][0]["rate_pct"] == "15.0000"
    audit.assert_not_called()


@pytest.mark.asyncio
async def test_options_returns_incoterms_currencies_and_bases(client, audit):
    with patch.object(svc, "get_duty_incoterms", AsyncMock(return_value="DDP")), \
            patch("app.routers.duty_rules.list_invoice_currencies", AsyncMock(return_value=["JPY", "USD"])):
        res = await client.get(f"{BASE}/options")
    assert res.status_code == 200
    assert res.json() == {
        "duty_incoterms": "DDP",
        "currencies": ["JPY", "USD"],
        "bases": ["subtotal", "subtotal_shipping", "subtotal_shipping_prior"],
    }


@pytest.mark.asyncio
async def test_options_404_when_tenant_settings_missing(client, audit):
    with patch.object(svc, "get_duty_incoterms", AsyncMock(return_value=None)):
        res = await client.get(f"{BASE}/options")
    assert res.status_code == 404
    assert res.json()["detail"] == {"code": "tenant_settings_missing"}


@pytest.mark.asyncio
async def test_create_normalizes_and_records_audit(client, audit):
    create = AsyncMock(return_value=_RULE)
    with patch.object(svc, "create_duty_rule", create):
        res = await client.post(BASE, json=_BODY)
    assert res.status_code == 201
    body = create.await_args.args[2]
    assert body.destination_country_code == "US"
    assert body.carrier == "fedex"
    assert body.effective_to is None
    assert audit.await_count == 1
    assert audit.await_args.args[3] == "create"
    assert audit.await_args.args[4] == "tenant_duty_rules"


@pytest.mark.asyncio
async def test_create_blank_carrier_becomes_null(client, audit):
    create = AsyncMock(return_value={**_RULE, "carrier": None})
    with patch.object(svc, "create_duty_rule", create):
        res = await client.post(BASE, json={**_BODY, "carrier": "   "})
    assert res.status_code == 201
    assert create.await_args.args[2].carrier is None


@pytest.mark.asyncio
async def test_create_overlap_returns_409_with_ids(client, audit):
    with patch.object(svc, "create_duty_rule", AsyncMock(side_effect=svc.DutyRuleOverlap([3, 5]))):
        res = await client.post(BASE, json=_BODY)
    assert res.status_code == 409
    assert res.json()["detail"] == {"code": "duty_rule_overlap", "rule_ids": [3, 5]}
    audit.assert_not_called()


@pytest.mark.asyncio
async def test_create_unknown_country_returns_422(client, audit):
    with patch.object(svc, "create_duty_rule", AsyncMock(side_effect=svc.DutyCountryInvalid())):
        res = await client.post(BASE, json=_BODY)
    assert res.status_code == 422
    assert res.json()["detail"] == {"code": "duty_country"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "patch_body",
    [
        {"source_url": "fedex.com/duty"},
        {"source_url": ""},
        {"components": []},
        {"effective_from": "2026-02-01", "effective_to": "2026-01-01"},
        {"components": [{"label": "Duty", "base": "total", "rate_pct": "1"}]},
        {"components": [{"label": "Fee", "base": "subtotal", "rate_pct": "0", "min_amount": "10"}]},
        {"components": [{"label": "Fee", "base": "subtotal", "rate_pct": "0", "min_amount": "10",
                         "max_amount": "5", "amount_currency": "USD"}]},
    ],
)
async def test_create_rejects_bad_input(client, audit, patch_body):
    create = AsyncMock(return_value=_RULE)
    with patch.object(svc, "create_duty_rule", create):
        res = await client.post(BASE, json={**_BODY, **patch_body})
    assert res.status_code == 422
    create.assert_not_called()
    audit.assert_not_called()


@pytest.mark.asyncio
async def test_update_records_before_and_after(client, audit):
    after = {**_RULE, "label": "US DDP FedEx 2026"}
    with patch.object(svc, "update_duty_rule", AsyncMock(return_value=(_RULE, after))):
        res = await client.put(f"{BASE}/7", json=_BODY)
    assert res.status_code == 200
    assert res.json()["label"] == "US DDP FedEx 2026"
    assert audit.await_count == 1
    kwargs = audit.await_args.kwargs
    assert audit.await_args.args[3] == "update"
    assert kwargs["old_data"]["label"] == "US DDP FedEx"
    assert kwargs["new_data"]["label"] == "US DDP FedEx 2026"


@pytest.mark.asyncio
async def test_update_not_found_returns_404(client, audit):
    with patch.object(svc, "update_duty_rule", AsyncMock(side_effect=svc.DutyRuleNotFound())):
        res = await client.put(f"{BASE}/99", json=_BODY)
    assert res.status_code == 404
    assert res.json()["detail"] == {"code": "duty_rule_not_found"}
    audit.assert_not_called()


@pytest.mark.asyncio
async def test_update_overlap_returns_409(client, audit):
    with patch.object(svc, "update_duty_rule", AsyncMock(side_effect=svc.DutyRuleOverlap([8]))):
        res = await client.put(f"{BASE}/7", json=_BODY)
    assert res.status_code == 409
    assert res.json()["detail"]["rule_ids"] == [8]


@pytest.mark.asyncio
async def test_delete_returns_204_and_records_audit(client, audit):
    with patch.object(svc, "delete_duty_rule", AsyncMock(return_value=_RULE)):
        res = await client.delete(f"{BASE}/7")
    assert res.status_code == 204
    assert audit.await_count == 1
    assert audit.await_args.args[3] == "delete"
    assert audit.await_args.kwargs["old_data"]["id"] == 7


@pytest.mark.asyncio
async def test_delete_not_found_returns_404(client, audit):
    with patch.object(svc, "delete_duty_rule", AsyncMock(side_effect=svc.DutyRuleNotFound())):
        res = await client.delete(f"{BASE}/99")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_view_only_can_read_but_not_write(client, audit):
    view_only = AsyncMock(return_value={"tenant.profile.view"})
    create = AsyncMock(return_value=_RULE)
    with patch("app.auth.dependencies.load_user_permissions", new=view_only), \
            patch.object(svc, "list_duty_rules", AsyncMock(return_value=[])), \
            patch.object(svc, "create_duty_rule", create), \
            patch.object(svc, "delete_duty_rule", AsyncMock(return_value=_RULE)):
        assert (await client.get(BASE)).status_code == 200
        assert (await client.post(BASE, json=_BODY)).status_code == 403
        assert (await client.put(f"{BASE}/7", json=_BODY)).status_code == 403
        assert (await client.delete(f"{BASE}/7")).status_code == 403
    create.assert_not_called()
    audit.assert_not_called()


def test_duty_bases_match_migration_check():
    """基準の並びの正本（DutyBase）が表の CHECK と同じ3つであること。"""
    from pathlib import Path

    from app.schemas.duty_rules import DUTY_BASES

    root = Path(__file__).resolve().parents[2]
    sql = (root / "migrations" / "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql").read_text(
        encoding="utf-8"
    )
    for base in DUTY_BASES:
        assert f"'{base}'" in sql
    assert DUTY_BASES == ("subtotal", "subtotal_shipping", "subtotal_shipping_prior")
```

### 2-6. backend/tests/test_duty_rules_pg.py（新規。全文）

```python
"""関税の額の決まりの読み書きを本物の PostgreSQL で確かめる（invoice-create-portfolio 便B・K18）。

- 送料の会社の大文字・空白の違いは同じ会社として重なりになる。空は NULL で、NULL どうしも重なりになる。
- 直すときに自分の行とは重ならない。ほかの行と重なれば重なりになる。使わない決まりは重なりを調べない。
- 国の表に無い国は断る。無い決まりは見つからない。消すと中身の行も消える。
- 試験の中で入れた行は最後に戻す。ゲートは CI が設定する RLS_ADMIN_DATABASE_URL（前例 test_tenant_duty_rules_pg.py）。
"""
from __future__ import annotations

import datetime
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.schemas.duty_rules import DutyRuleIn
from app.services import duty_rules as svc
from tests.rls_bootstrap import (
    bootstrap_public_countries,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

# 試験・移行のどこにも無い 964 を使う（962 は便Aの関税の表、963 は発行元の表の試験が使用）
_TENANT_ID = 964
_SCHEMA = f"tenant_{_TENANT_ID:03d}"


def _body(**overrides) -> DutyRuleIn:
    data = {
        "destination_country_code": "US",
        "carrier": "fedex",
        "label": "US DDP FedEx",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "source_url": "https://www.fedex.com/en-us/billing/duty-tax.html",
        "components": [
            {"label": "Duty", "base": "subtotal", "rate_pct": "15"},
            {"label": "DDP fee", "base": "subtotal_shipping", "rate_pct": "2.5",
             "min_amount": "10", "max_amount": "100", "amount_currency": "USD"},
        ],
    }
    data.update(overrides)
    return DutyRuleIn.model_validate(data)


async def _expect_overlap(db: AsyncSession, coro) -> list[int]:
    sp = await db.begin_nested()
    with pytest.raises(svc.DutyRuleOverlap) as exc_info:
        await coro
    await sp.rollback()
    return exc_info.value.rule_ids


async def _check_service(db: AsyncSession) -> None:
    tid = _TENANT_ID
    first = await svc.create_duty_rule(db, tid, _body(carrier=" FedEx "))
    assert first["carrier"] == "fedex"
    assert first["destination_country_code"] == "US"
    assert [c["sort_order"] for c in first["components"]] == [0, 1]
    assert first["components"][1]["min_amount"] == "10.00"
    assert first["components"][1]["amount_currency"] == "USD"

    # 大文字・空白の違いは同じ会社（K18）
    assert await _expect_overlap(db, svc.create_duty_rule(db, tid, _body(carrier="FEDEX "))) == [first["id"]]

    # 直す: 自分の行とは重ならない（200 相当）。中身の行は置き換わる
    before, after = await svc.update_duty_rule(
        db, tid, first["id"],
        _body(effective_to="2026-12-31", components=[{"label": "Duty", "base": "subtotal", "rate_pct": "12"}]),
    )
    assert before["effective_to"] is None
    assert after["effective_to"] == datetime.date(2026, 12, 31)
    assert [c["rate_pct"] for c in after["components"]] == ["12.0000"]

    # 期間が重ならなければ足せる
    later = await svc.create_duty_rule(
        db, tid, _body(effective_from="2027-01-01", effective_to="2027-12-31", label="US DDP FedEx 2027"),
    )
    # 2026-06-01 から終わりの無い決まりは first とも later とも重なる
    assert await _expect_overlap(db, svc.create_duty_rule(db, tid, _body(effective_from="2026-06-01"))) == [
        first["id"], later["id"],
    ]
    # 直す: ほかの行と重なれば重なり（409 相当）
    assert await _expect_overlap(
        db, svc.update_duty_rule(db, tid, later["id"], _body(effective_from="2026-06-01", effective_to="2027-12-31")),
    ) == [first["id"]]

    # 空の送料の会社は NULL。NULL どうしも重なり（K18）。fedex の行とは別
    any_carrier = await svc.create_duty_rule(db, tid, _body(carrier="   ", label="US DDP any"))
    assert any_carrier["carrier"] is None
    assert await _expect_overlap(db, svc.create_duty_rule(db, tid, _body(carrier=None))) == [any_carrier["id"]]

    # 使わない決まりは重なりを調べない
    inactive = await svc.create_duty_rule(db, tid, _body(is_active=False, label="draft"))
    assert inactive["is_active"] is False

    # 国の表に無い国は断る
    sp = await db.begin_nested()
    with pytest.raises(svc.DutyCountryInvalid):
        await svc.create_duty_rule(db, tid, _body(destination_country_code="ZZ"))
    await sp.rollback()

    # 一覧は国・送料の会社（NULL が先）・始まりの日の順
    rows = await svc.list_duty_rules(db, tid)
    # fedex の 2026-01-01 始まりは first と inactive の2件で、id の小さい first が先
    assert [r["id"] for r in rows] == [any_carrier["id"], first["id"], inactive["id"], later["id"]]

    # 消す: 中身の行も消える。無い決まりは見つからない
    removed = await svc.delete_duty_rule(db, tid, later["id"])
    assert removed["id"] == later["id"]
    left = (
        await db.execute(
            text(f"SELECT count(*) FROM {_SCHEMA}.tenant_duty_rule_components WHERE rule_id = :id"),
            {"id": later["id"]},
        )
    ).scalar_one()
    assert left == 0
    with pytest.raises(svc.DutyRuleNotFound):
        await svc.get_duty_rule(db, tid, later["id"])
    with pytest.raises(svc.DutyRuleNotFound):
        await svc.delete_duty_rule(db, tid, later["id"])


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_duty_rule_service_on_postgres():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        await bootstrap_public_countries(admin_engine)
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            try:
                assert await bootstrap_tenant_schema(admin_engine, _TENANT_ID) == _SCHEMA
                async with AsyncSession(admin_engine, expire_on_commit=False) as db:
                    try:
                        await _check_service(db)
                    finally:
                        await db.rollback()
            finally:
                async with public_bootstrap_lock(admin_engine):
                    async with admin_engine.begin() as conn:
                        await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
    finally:
        await admin_engine.dispose()
```

### 2-7. frontend/src/pages/admin/dutyRuleTypes.ts（新規。全文）

```ts
/**
 * 関税の額の決まりの形（invoice-create-portfolio 便B・design.md §3-3・§3-6）。
 * 正本はサーバーの schemas/duty_rules.py。数は文字のまま受け取り、文字のまま送る（小数の丸めを画面でしない）。
 */
export interface DutyComponent {
  id: number;
  sort_order: number;
  label: string;
  base: string;
  rate_pct: string;
  min_amount: string | null;
  max_amount: string | null;
  amount_currency: string | null;
}

export interface DutyRule {
  id: number;
  destination_country_code: string;
  carrier: string | null;
  label: string;
  effective_from: string;
  effective_to: string | null;
  source_url: string;
  note: string | null;
  is_active: boolean;
  components: DutyComponent[];
}

export interface DutyRuleOptions {
  duty_incoterms: string;
  currencies: string[];
  bases: string[];
}

/** 書いた後に取り直す写しの頭（ADR-1054）。一覧と選択肢の両方を含む */
export const DUTY_RULES_HEAD = ["admin", "duty-rules"] as const;
```

### 2-8. frontend/src/pages/admin/DutyRuleFormModal.tsx（新規。全文）

```tsx
/**
 * 関税の額の決まりを足す・直す窓（invoice-create-portfolio 便B・design.md §3-6）。
 * - 根拠の URL は必須。中身の行は 1〜20 行。
 * - 送料の会社は空なら「どの送料の会社でも」。保存の形（小文字・空白なし）はサーバーが決める。
 * - 重なり（409）・入力の誤り（422）はそれぞれの文で知らせ、窓は閉じない。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import { Modal } from "../../components/Modal";
import { Button } from "../../components/Button";
import { Stack } from "../../components/Stack";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import { Select } from "../../components/Select";
import { Toggle } from "../../components/Toggle";
import { CountryCombobox } from "../../components/CountryCombobox";
import type { DutyRule, DutyRuleOptions } from "./dutyRuleTypes";

interface ComponentDraft {
  label: string;
  base: string;
  rate_pct: string;
  min_amount: string;
  max_amount: string;
  amount_currency: string;
}

interface RuleDraft {
  destination_country_code: string;
  carrier: string;
  label: string;
  effective_from: string;
  effective_to: string;
  source_url: string;
  note: string;
  is_active: boolean;
  components: ComponentDraft[];
}

/** 基準の名前（値の正本はサーバーの選択肢。ここは見せる文の対応だけ） */
export const BASE_LABEL_KEYS: Record<string, string> = {
  subtotal: "dutyRules.baseSubtotal",
  subtotal_shipping: "dutyRules.baseSubtotalShipping",
  subtotal_shipping_prior: "dutyRules.baseSubtotalShippingPrior",
};

const MAX_COMPONENTS = 20;

function emptyComponent(options: DutyRuleOptions): ComponentDraft {
  return { label: "", base: options.bases[0] ?? "", rate_pct: "", min_amount: "", max_amount: "", amount_currency: "" };
}

function toDraft(rule: DutyRule | null, options: DutyRuleOptions): RuleDraft {
  if (rule === null) {
    return {
      destination_country_code: "", carrier: "", label: "", effective_from: "", effective_to: "",
      source_url: "", note: "", is_active: true, components: [emptyComponent(options)],
    };
  }
  return {
    destination_country_code: rule.destination_country_code,
    carrier: rule.carrier ?? "",
    label: rule.label,
    effective_from: rule.effective_from,
    effective_to: rule.effective_to ?? "",
    source_url: rule.source_url,
    note: rule.note ?? "",
    is_active: rule.is_active,
    components: rule.components.map((c) => ({
      label: c.label,
      base: c.base,
      rate_pct: c.rate_pct,
      min_amount: c.min_amount ?? "",
      max_amount: c.max_amount ?? "",
      amount_currency: c.amount_currency ?? "",
    })),
  };
}

/** 空の欄は null で送る（サーバーも空を null にするが、送る形をはっきりさせる） */
function toBody(draft: RuleDraft) {
  const blank = (v: string) => (v.trim() === "" ? null : v.trim());
  return {
    destination_country_code: draft.destination_country_code,
    carrier: blank(draft.carrier),
    label: draft.label.trim(),
    effective_from: draft.effective_from,
    effective_to: blank(draft.effective_to),
    source_url: draft.source_url.trim(),
    note: blank(draft.note),
    is_active: draft.is_active,
    components: draft.components.map((c) => ({
      label: c.label.trim(),
      base: c.base,
      rate_pct: c.rate_pct.trim(),
      min_amount: blank(c.min_amount),
      max_amount: blank(c.max_amount),
      amount_currency: blank(c.amount_currency),
    })),
  };
}

interface Props {
  open: boolean;
  rule: DutyRule | null;
  options: DutyRuleOptions;
  onClose: () => void;
  onSaved: () => void;
}

export function DutyRuleFormModal({ open, rule, options, onClose, onSaved }: Props) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<RuleDraft>(() => toDraft(rule, options));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof RuleDraft>(key: K, value: RuleDraft[K]) =>
    setDraft((d) => ({ ...d, [key]: value }));
  const setComponent = (index: number, key: keyof ComponentDraft, value: string) =>
    setDraft((d) => ({
      ...d,
      components: d.components.map((c, i) => (i === index ? { ...c, [key]: value } : c)),
    }));

  const canSave =
    draft.destination_country_code !== "" &&
    draft.label.trim() !== "" &&
    draft.effective_from !== "" &&
    draft.source_url.trim() !== "" &&
    draft.components.length > 0 &&
    draft.components.every((c) => c.label.trim() !== "" && c.base !== "" && c.rate_pct.trim() !== "");

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      if (rule === null) {
        await api.post("/admin/duty-rules", toBody(draft));
      } else {
        await api.put(`/admin/duty-rules/${rule.id}`, toBody(draft));
      }
      onSaved();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setError(t("dutyRules.overlapError"));
      else if (e instanceof ApiError && e.status === 422) setError(t("dutyRules.inputError"));
      else setError(t("dutyRules.saveError"));
    } finally {
      setSaving(false);
    }
  };

  const baseOptions = options.bases.map((b) => ({ value: b, label: BASE_LABEL_KEYS[b] ? t(BASE_LABEL_KEYS[b]) : b }));
  const currencyOptions = [
    { value: "", label: t("dutyRules.currencyNone") },
    ...options.currencies.map((c) => ({ value: c, label: c })),
  ];

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={rule === null ? t("dutyRules.addTitle") : t("dutyRules.editTitle")}
      size="lg"
      dismissOnOverlay={false}
      footer={
        <>
          <Button type="button" variant="secondary" size="md" onClick={onClose} disabled={saving}>
            {t("common.cancel")}
          </Button>
          <Button
            type="button"
            variant="primary"
            size="md"
            loading={saving}
            disabled={saving || !canSave}
            onClick={() => void handleSave()}
          >
            {t("dutyRules.save")}
          </Button>
        </>
      }
    >
      <Stack gap="4">
        <div className="comp-field">
          <label htmlFor="duty-rule-country" className="comp-field__label">{t("dutyRules.country")}</label>
          <CountryCombobox
            id="duty-rule-country"
            value={draft.destination_country_code}
            onChange={(v) => set("destination_country_code", v)}
            placeholder={t("common.search")}
            required
          />
        </div>
        <TextField
          label={t("dutyRules.carrier")}
          helperText={t("dutyRules.carrierHelp")}
          value={draft.carrier}
          onChange={(e) => set("carrier", e.target.value)}
          fullWidth
        />
        <TextField
          label={t("dutyRules.label")}
          helperText={t("dutyRules.labelHelp")}
          value={draft.label}
          onChange={(e) => set("label", e.target.value)}
          required
          fullWidth
        />
        <Stack direction="row" gap="3">
          <TextField
            type="date"
            label={t("dutyRules.effectiveFrom")}
            value={draft.effective_from}
            onChange={(e) => set("effective_from", e.target.value)}
            required
          />
          <TextField
            type="date"
            label={t("dutyRules.effectiveTo")}
            helperText={t("dutyRules.effectiveToHelp")}
            value={draft.effective_to}
            onChange={(e) => set("effective_to", e.target.value)}
          />
        </Stack>
        <TextField
          type="url"
          label={t("dutyRules.sourceUrl")}
          helperText={t("dutyRules.sourceUrlHelp")}
          value={draft.source_url}
          onChange={(e) => set("source_url", e.target.value)}
          required
          fullWidth
        />
        <Textarea
          label={t("dutyRules.note")}
          value={draft.note}
          onChange={(e) => set("note", e.target.value)}
          fullWidth
        />
        <Stack direction="row" gap="2">
          <Toggle
            id="duty-rule-active"
            checked={draft.is_active}
            onCheckedChange={(v) => set("is_active", v)}
            aria-label={t("dutyRules.active")}
          />
          <label htmlFor="duty-rule-active" className="comp-field__label">{t("dutyRules.active")}</label>
        </Stack>

        <h3>{t("dutyRules.componentsTitle")}</h3>
        {draft.components.map((c, i) => (
          <Stack key={i} gap="2">
            <Stack direction="row" gap="3">
              <TextField
                label={t("dutyRules.componentLabel", { n: i + 1 })}
                value={c.label}
                onChange={(e) => setComponent(i, "label", e.target.value)}
                required
              />
              <Select
                label={t("dutyRules.base")}
                options={baseOptions}
                value={c.base}
                onChange={(e) => setComponent(i, "base", e.target.value)}
              />
              <TextField
                type="number"
                inputMode="decimal"
                min="0"
                step="0.0001"
                label={t("dutyRules.ratePct")}
                value={c.rate_pct}
                onChange={(e) => setComponent(i, "rate_pct", e.target.value)}
                required
              />
            </Stack>
            <Stack direction="row" gap="3">
              <TextField
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                label={t("dutyRules.minAmount")}
                value={c.min_amount}
                onChange={(e) => setComponent(i, "min_amount", e.target.value)}
              />
              <TextField
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                label={t("dutyRules.maxAmount")}
                value={c.max_amount}
                onChange={(e) => setComponent(i, "max_amount", e.target.value)}
              />
              <Select
                label={t("dutyRules.amountCurrency")}
                helperText={t("dutyRules.amountCurrencyHelp")}
                options={currencyOptions}
                value={c.amount_currency}
                onChange={(e) => setComponent(i, "amount_currency", e.target.value)}
              />
            </Stack>
            {draft.components.length > 1 && (
              <Stack direction="row" gap="2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => set("components", draft.components.filter((_, j) => j !== i))}
                >
                  {t("dutyRules.removeComponent", { n: i + 1 })}
                </Button>
              </Stack>
            )}
          </Stack>
        ))}
        {draft.components.length < MAX_COMPONENTS && (
          <Stack direction="row" gap="2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => set("components", [...draft.components, emptyComponent(options)])}
            >
              {t("dutyRules.addComponent")}
            </Button>
          </Stack>
        )}
        {error && <p role="alert">{error}</p>}
      </Stack>
    </Modal>
  );
}
```

### 2-9. frontend/src/pages/admin/DutyRulesPage.tsx（新規。全文）

```tsx
/**
 * DutyRulesPage — 関税の額の決まり（invoice-create-portfolio 便B・design.md §3-6）
 *
 * - 上に今の会社の関税の条件（DAP・DDU・DDP）を読むだけで出す。変えるのは会社の決まりのページ。
 * - DDP のときだけ、ここの額が請求書に効く。DAP・DDU のときは「今は関税を請求しません」と出す。
 * - 一覧（国・送料の会社・有効期間・根拠）と、足す・直す・消す。
 * - 見る: tenant.profile.view／edit。足す・直す・消す: tenant.profile.edit。
 *
 * ルート: /management-center/duty-rules
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { Badge } from "../../components/Badge";
import { Callout } from "../../components/Callout";
import { Stack } from "../../components/Stack";
import { TextLink } from "../../components/TextLink";
import ConfirmModal from "../../components/ConfirmModal";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { LoadingBlock, Spinner } from "../../components/loading";
import { BASE_LABEL_KEYS, DutyRuleFormModal } from "./DutyRuleFormModal";
import { DUTY_RULES_HEAD } from "./dutyRuleTypes";
import type { DutyRule, DutyRuleOptions } from "./dutyRuleTypes";

/** 窓の状態。null は閉じている。rule が null なら足す、あれば直す */
type FormState = { rule: DutyRule | null } | null;

export default function DutyRulesPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const canEdit = hasPermission("tenant.profile.edit");
  const rulesQuery = useApiQuery<DutyRule[]>("/admin/duty-rules");
  const optionsQuery = useApiQuery<DutyRuleOptions>("/admin/duty-rules/options");
  const invalidate = useInvalidateApi();
  const [form, setForm] = useState<FormState>(null);
  const [deleting, setDeleting] = useState<DutyRule | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const rules = rulesQuery.data ?? [];
  const options = optionsQuery.data;
  const loadFailed = rulesQuery.isError || optionsQuery.isError;
  const shownError = error ?? (loadFailed ? t("dutyRules.loadError") : null);

  const handleSaved = () => {
    setForm(null);
    void invalidate(DUTY_RULES_HEAD);
  };

  const handleDelete = async () => {
    if (deleting === null) return;
    setSaving(true);
    setError(null);
    try {
      await api.delete(`/admin/duty-rules/${deleting.id}`);
      setDeleting(null);
      void invalidate(DUTY_RULES_HEAD);
    } catch {
      setError(t("dutyRules.deleteError"));
    } finally {
      setSaving(false);
    }
  };

  const baseLabel = (base: string) => (BASE_LABEL_KEYS[base] ? t(BASE_LABEL_KEYS[base]) : base);

  const columns: DataTableColumn<DutyRule>[] = [
    { key: "country", header: t("dutyRules.country"), renderCell: (r) => r.destination_country_code },
    { key: "carrier", header: t("dutyRules.carrier"), renderCell: (r) => r.carrier ?? t("dutyRules.anyCarrier") },
    {
      key: "label",
      header: t("dutyRules.label"),
      renderCell: (r) => (
        <>
          {r.label}
          {!r.is_active && (
            <>
              {" "}
              <Badge variant="neutral" size="sm">{t("dutyRules.inactive")}</Badge>
            </>
          )}
        </>
      ),
    },
    {
      key: "period",
      header: t("dutyRules.period"),
      renderCell: (r) =>
        t("dutyRules.periodValue", { from: r.effective_from, to: r.effective_to ?? t("dutyRules.noEnd") }),
    },
    {
      key: "components",
      header: t("dutyRules.componentsTitle"),
      renderCell: (r) => (
        <Stack gap="1">
          {r.components.map((c) => (
            <span key={c.id}>
              {t("dutyRules.componentSummary", { label: c.label, rate: c.rate_pct, base: baseLabel(c.base) })}
            </span>
          ))}
        </Stack>
      ),
    },
    { key: "source", header: t("dutyRules.sourceUrl"), renderCell: (r) => r.source_url },
  ];
  if (canEdit) {
    columns.push({
      key: "actions",
      header: t("dutyRules.actions"),
      renderCell: (r) => (
        <Stack direction="row" gap="2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setForm({ rule: r })}
            aria-label={t("dutyRules.editAriaLabel", { name: r.label })}
          >
            {t("common.edit")}
          </Button>
          <Button
            type="button"
            variant="danger"
            size="sm"
            onClick={() => setDeleting(r)}
            aria-label={t("dutyRules.deleteAriaLabel", { name: r.label })}
          >
            {t("common.delete")}
          </Button>
        </Stack>
      ),
    });
  }

  const pending = rulesQuery.isPending || optionsQuery.isPending;
  const fetching = (rulesQuery.isFetching || optionsQuery.isFetching) && !pending;

  return (
    <PageLayout navKey="nav.dutyRules" headerLeft={fetching ? <Spinner size="sm" /> : undefined}>
      {pending && !loadFailed ? (
        <LoadingBlock />
      ) : (
        <Stack gap="4">
          {options && (
            <Callout
              variant="info"
              title={t("dutyRules.incotermsTitle", { value: options.duty_incoterms })}
            >
              <Stack gap="1">
                <span>
                  {options.duty_incoterms === "DDP" ? t("dutyRules.incotermsDdp") : t("dutyRules.incotermsNotDdp")}
                </span>
                <TextLink to="/management-center/tenant-policy">{t("dutyRules.changeTerms")}</TextLink>
              </Stack>
            </Callout>
          )}
          {shownError && <p role="alert">{shownError}</p>}
          {canEdit && options && (
            <Stack direction="row" gap="2">
              <Button type="button" variant="primary" size="md" onClick={() => setForm({ rule: null })}>
                {t("dutyRules.add")}
              </Button>
            </Stack>
          )}
          <DataTable
            columns={columns}
            data={rules}
            rowKey={(r) => String(r.id)}
            emptyState={loadFailed ? undefined : t("dutyRules.empty")}
          />
        </Stack>
      )}

      {form !== null && options && (
        <DutyRuleFormModal
          key={form.rule?.id ?? "new"}
          open
          rule={form.rule}
          options={options}
          onClose={() => setForm(null)}
          onSaved={handleSaved}
        />
      )}
      <ConfirmModal
        open={deleting !== null}
        title={t("dutyRules.deleteTitle")}
        message={t("dutyRules.deleteMessage", { name: deleting?.label ?? "" })}
        confirmLabel={t("common.delete")}
        danger
        confirmLoading={saving}
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleting(null)}
      />
    </PageLayout>
  );
}
```

### 2-10. frontend/src/pages/admin/DutyRulesPage.test.tsx（新規。全文）

```tsx
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import i18n from "../../i18n";
import { queryClient } from "../../lib/query/apiQuery";
import DutyRulesPage from "./DutyRulesPage";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), put: vi.fn(), post: vi.fn(), delete: vi.fn() },
  ApiError: class extends Error {
    status: number;
    responseDetail: unknown;
    constructor(message: string, status: number, responseDetail: unknown) {
      super(message);
      this.status = status;
      this.responseDetail = responseDetail;
    }
  },
}));
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: vi.fn() }));
// 国の選択は自分で /countries を取りに行く部品なので、ここでは文字の欄に差し替える
vi.mock("../../components/CountryCombobox", () => ({
  CountryCombobox: ({ id, value, onChange }: { id: string; value: string; onChange: (v: string) => void }) => (
    <input id={id} value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}));

const RULE = {
  id: 7,
  destination_country_code: "US",
  carrier: "fedex",
  label: "US DDP FedEx",
  effective_from: "2026-01-01",
  effective_to: null,
  source_url: "https://www.fedex.com/en-us/billing/duty-tax.html",
  note: null,
  is_active: true,
  components: [
    { id: 1, sort_order: 0, label: "Duty", base: "subtotal", rate_pct: "15.0000",
      min_amount: null, max_amount: null, amount_currency: null },
  ],
};
const OPTIONS = {
  duty_incoterms: "DDP",
  currencies: ["JPY", "USD"],
  bases: ["subtotal", "subtotal_shipping", "subtotal_shipping_prior"],
};

const mockGets = (options: object, rules: object[]) => {
  vi.mocked(api.get).mockImplementation(async (path: string) =>
    path === "/admin/duty-rules/options" ? options : rules,
  );
};
const mockCanEdit = (canEdit: boolean) =>
  vi.mocked(usePermissions).mockReturnValue({
    loading: false,
    hasPermission: (p: string) => (p === "tenant.profile.edit" ? canEdit : true),
    hasAny: () => true,
  } as unknown as ReturnType<typeof usePermissions>);
const view = () => render(<MemoryRouter><DutyRulesPage /></MemoryRouter>);
const callsTo = (path: string) => vi.mocked(api.get).mock.calls.filter((c) => c[0] === path).length;

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  mockCanEdit(true);
  mockGets(OPTIONS, [RULE]);
});
afterEach(() => { cleanup(); queryClient.clear(); });

it("shows the current terms read-only with a link to the tenant policy page and lists the rules", async () => {
  view();
  await screen.findByText("US DDP FedEx");
  expect(screen.getByText("Current duty terms: DDP")).toBeTruthy();
  expect(screen.getByText("The terms are DDP, so these amounts are added to invoices.")).toBeTruthy();
  expect(
    screen.getByRole("link", { name: "Change the terms on the Tenant Policy page" }).getAttribute("href"),
  ).toBe("/management-center/tenant-policy");
  expect(screen.getByText("fedex")).toBeTruthy();
  expect(screen.getByText("2026-01-01 - No end")).toBeTruthy();
  expect(screen.getByText("Duty: 15.0000% of Subtotal")).toBeTruthy();
  expect(screen.getByText(RULE.source_url)).toBeTruthy();
});

it("says duty is not billed now when the terms are not DDP", async () => {
  mockGets({ ...OPTIONS, duty_incoterms: "DAP" }, [{ ...RULE, carrier: null }]);
  view();
  await screen.findByText("Current duty terms: DAP");
  expect(
    screen.getByText("Duty is not billed now. These amounts are added to invoices only when the terms are DDP."),
  ).toBeTruthy();
  expect(screen.getByText("Any carrier")).toBeTruthy();
});

it("hides add, edit and delete for a view-only user", async () => {
  mockCanEdit(false);
  view();
  await screen.findByText("US DDP FedEx");
  expect(screen.queryByRole("button", { name: "Add rule" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Edit US DDP FedEx" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Delete US DDP FedEx" })).toBeNull();
});

it("adds a rule with an empty carrier sent as null and reloads the list", async () => {
  mockGets(OPTIONS, []);
  vi.mocked(api.post).mockResolvedValue(RULE);
  view();
  fireEvent.click(await screen.findByRole("button", { name: "Add rule" }));
  const dialog = await screen.findByRole("dialog");
  const save = within(dialog).getByRole("button", { name: "Save" }) as HTMLButtonElement;
  expect(save.disabled).toBe(true);
  fireEvent.change(within(dialog).getByLabelText(/^Destination country/), { target: { value: "US" } });
  fireEvent.change(within(dialog).getByLabelText(/^Name on invoice/), { target: { value: "US DDP" } });
  fireEvent.change(within(dialog).getByLabelText(/^Start date/), { target: { value: "2026-01-01" } });
  fireEvent.change(within(dialog).getByLabelText(/^Source URL/), { target: { value: RULE.source_url } });
  fireEvent.change(within(dialog).getByLabelText(/^Component 1 name/), { target: { value: "Duty" } });
  fireEvent.change(within(dialog).getByLabelText(/^Rate \(%\)/), { target: { value: "15" } });
  expect(save.disabled).toBe(false);
  const listCalls = callsTo("/admin/duty-rules");
  fireEvent.click(save);
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  expect(vi.mocked(api.post).mock.calls[0][0]).toBe("/admin/duty-rules");
  expect(vi.mocked(api.post).mock.calls[0][1]).toEqual({
    destination_country_code: "US",
    carrier: null,
    label: "US DDP",
    effective_from: "2026-01-01",
    effective_to: null,
    source_url: RULE.source_url,
    note: null,
    is_active: true,
    components: [
      { label: "Duty", base: "subtotal", rate_pct: "15", min_amount: null, max_amount: null, amount_currency: null },
    ],
  });
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(callsTo("/admin/duty-rules")).toBeGreaterThan(listCalls));
});

it("keeps the form open and explains an overlap when the server answers 409", async () => {
  vi.mocked(api.put).mockRejectedValue(new ApiError("conflict", 409, { code: "duty_rule_overlap", rule_ids: [8] }));
  view();
  fireEvent.click(await screen.findByRole("button", { name: "Edit US DDP FedEx" }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
  await within(dialog).findByText(
    "Another rule for the same country and carrier overlaps this period. Check the period or the carrier.",
  );
  expect(vi.mocked(api.put).mock.calls[0][0]).toBe("/admin/duty-rules/7");
  expect(screen.getByRole("dialog")).toBeTruthy();
});

it("deletes a rule after confirmation", async () => {
  vi.mocked(api.delete).mockResolvedValue(undefined);
  view();
  fireEvent.click(await screen.findByRole("button", { name: "Delete US DDP FedEx" }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: "Delete" }));
  await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/admin/duty-rules/7"));
});
```

### 2-11. backend/app/main.py（2か所。どれも足すか置き換えるだけ）

(1) 変更前:

```text
    duplicates,
```

(1) 変更後:

```text
    duplicates,
    duty_rules,  # invoice-create-portfolio 便B: 関税の額の決まり
```

(2) 変更前:

```text
app.include_router(
    duplicates.router, prefix="/api/v1", tags=["duplicates"],
    dependencies=[Depends(get_current_tenant)],
)
```

(2) 変更後:

```text
app.include_router(
    duplicates.router, prefix="/api/v1", tags=["duplicates"],
    dependencies=[Depends(get_current_tenant)],
)
app.include_router(
    duty_rules.router, prefix="/api/v1", tags=["duty-rules"],
    dependencies=[Depends(get_current_tenant)],
)
```

### 2-12. backend/app/realtime/topics.py（1か所。どれも足すか置き換えるだけ）

(1) 変更前:

```text
    ("POST", "/api/v1/admin/discord/own-server/apply"): _PENDING,
```

(1) 変更後:

```text
    ("POST", "/api/v1/admin/discord/own-server/apply"): _PENDING,
    ("POST", "/api/v1/admin/duty-rules"): _PENDING,
    ("PUT", "/api/v1/admin/duty-rules/{rule_id}"): _PENDING,
    ("DELETE", "/api/v1/admin/duty-rules/{rule_id}"): _PENDING,
```

### 2-13. frontend/src/App.tsx（2か所。どれも足すか置き換えるだけ）

(1) 変更前:

```text
import ChannelMastersPage from "./pages/admin/ChannelMastersPage";
```

(1) 変更後:

```text
import ChannelMastersPage from "./pages/admin/ChannelMastersPage";
// invoice-create-portfolio 便B: 関税の額の決まり
import DutyRulesPage from "./pages/admin/DutyRulesPage";
```

(2) 変更前:

```text
                      <Route path="channel-masters"     element={<ChannelMastersPage />} />
```

(2) 変更後:

```text
                      <Route path="channel-masters"     element={<ChannelMastersPage />} />
                      <Route path="duty-rules"          element={<DutyRulesPage />} />
```

### 2-14. frontend/src/pages/management-center/ManagementCenterPage.tsx（1か所。どれも足すか置き換えるだけ）

(1) 変更前:

```text
        { to: "channel-masters", labelKey: "nav.channelMasters", visible: can("channelMasters") },
```

(1) 変更後:

```text
        { to: "channel-masters", labelKey: "nav.channelMasters", visible: can("channelMasters") },
        { to: "duty-rules",      labelKey: "nav.dutyRules",      visible: can("dutyRules") },
```

### 2-15. frontend/src/pages/management-center/ManagementCenterPage.test.tsx（3か所。どれも足すか置き換えるだけ）

(1) 変更前:

```text
  "channel-masters": "Channel Management",
```

(1) 変更後:

```text
  "channel-masters": "Channel Management",
  "duty-rules": "Duty Amounts",
```

(2) 変更前:

```text
it("links the 4 admin pages under the management-center layout", () => {
```

(2) 変更後:

```text
it("links the 5 admin pages under the management-center layout", () => {
```

(3) 変更前:

```text
  expect(screen.getAllByRole("link").length).toBeGreaterThan(4);
```

(3) 変更後:

```text
  expect(screen.getAllByRole("link").length).toBeGreaterThan(5);
```

### 2-16. frontend/src/constants/menuPermissions.ts（3か所。どれも足すか置き換えるだけ）

(1) 変更前:

```text
  | "channelMasters"
```

(1) 変更後:

```text
  | "channelMasters"
  | "dutyRules"
```

(2) 変更前:

```text
  channelMasters: { labelKey: "nav.channelMasters", anyOf: ["tenant.profile.edit"] },
```

(2) 変更後:

```text
  channelMasters: { labelKey: "nav.channelMasters", anyOf: ["tenant.profile.edit"] },
  dutyRules: { labelKey: "nav.dutyRules", anyOf: ["tenant.profile.edit", "tenant.profile.view"] },
```

(3) 変更前:

```text
    menus: ["tenantProfile", "tenantPolicy", "discordConfig", "discordAnnounce", "channelMasters"],
```

(3) 変更後:

```text
    menus: ["tenantProfile", "tenantPolicy", "discordConfig", "discordAnnounce", "channelMasters", "dutyRules"],
```

### 2-17. frontend/src/constants/menuPermissions.test.ts（1か所。どれも足すか置き換えるだけ）

(1) 変更前:

```text
  channelMasters: (h) => h("tenant.profile.edit"),
```

(1) 変更後:

```text
  channelMasters: (h) => h("tenant.profile.edit"),
  dutyRules: (h) => h("tenant.profile.edit") || h("tenant.profile.view"),
```

### 2-18. frontend/src/locales/ja.json（2か所に足す。消す行は無い）

(1) 変更前:

```text
    "channelMasters": "チャネル管理",
```

(1) 変更後:

```text
    "channelMasters": "チャネル管理",
    "dutyRules": "関税の額",
```

(2) `  "funnel": {` の行（字下げ 2 つ。ファイルに 1 回だけ）の直前に、次の行をそのまま足す:

```text
  "dutyRules": {
    "add": "決まりを足す",
    "addTitle": "関税の額の決まりを足す",
    "editTitle": "関税の額の決まりを直す",
    "save": "保存",
    "country": "届け先の国",
    "carrier": "送料の会社",
    "carrierHelp": "空のままなら、どの送料の会社でも使います（例: fedex）",
    "anyCarrier": "どの会社でも",
    "label": "請求書に出す名前",
    "labelHelp": "請求書の関税の行に出ます",
    "effectiveFrom": "使い始める日",
    "effectiveTo": "使い終わる日",
    "effectiveToHelp": "空のままなら終わりなし",
    "period": "有効期間",
    "periodValue": "{{from}} 〜 {{to}}",
    "noEnd": "終わりなし",
    "sourceUrl": "根拠の URL",
    "sourceUrlHelp": "額の根拠になるページの URL（必須）",
    "note": "メモ",
    "active": "この決まりを使う",
    "inactive": "使っていない",
    "componentsTitle": "中身",
    "componentLabel": "中身 {{n}} の名前",
    "componentSummary": "{{label}}: {{base}}の {{rate}}%",
    "base": "計算の元",
    "baseSubtotal": "小計",
    "baseSubtotalShipping": "小計＋送料",
    "baseSubtotalShippingPrior": "小計＋送料＋前の中身",
    "ratePct": "率（%）",
    "minAmount": "下限の額",
    "maxAmount": "上限の額",
    "amountCurrency": "下限・上限の通貨",
    "amountCurrencyHelp": "下限か上限を入れたときは選んでください",
    "currencyNone": "選ばない",
    "addComponent": "中身を足す",
    "removeComponent": "中身 {{n}} を外す",
    "actions": "操作",
    "editAriaLabel": "{{name}} を直す",
    "deleteAriaLabel": "{{name}} を消す",
    "deleteTitle": "関税の額の決まりを消す",
    "deleteMessage": "「{{name}}」を消します。発行済みの請求書の額は変わりません。",
    "incotermsTitle": "今の関税の条件: {{value}}",
    "incotermsDdp": "条件が DDP なので、ここの額が請求書に入ります。",
    "incotermsNotDdp": "今は関税を請求しません。条件が DDP のときだけ、ここの額が請求書に入ります。",
    "changeTerms": "条件を変えるのは会社の決まりのページです",
    "empty": "まだ決まりがありません。",
    "loadError": "読み込めませんでした。ページを開き直してください。",
    "saveError": "保存に失敗しました。もう一度お試しください。",
    "deleteError": "消せませんでした。もう一度お試しください。",
    "overlapError": "同じ国・同じ送料の会社で期間が重なる決まりがあります。期間か送料の会社を確かめてください。",
    "inputError": "入力に誤りがあります。国・根拠の URL・期間・中身の下限と上限と通貨を確かめてください。"
  },
```

### 2-19. frontend/src/locales/en.json（2か所に足す。消す行は無い）

(1) 変更前:

```text
    "channelMasters": "Channel Management",
```

(1) 変更後:

```text
    "channelMasters": "Channel Management",
    "dutyRules": "Duty Amounts",
```

(2) `  "funnel": {` の行（字下げ 2 つ。ファイルに 1 回だけ）の直前に、次の行をそのまま足す:

```text
  "dutyRules": {
    "add": "Add rule",
    "addTitle": "Add duty amount rule",
    "editTitle": "Edit duty amount rule",
    "save": "Save",
    "country": "Destination country",
    "carrier": "Carrier",
    "carrierHelp": "Leave empty to use it for any carrier (e.g. fedex)",
    "anyCarrier": "Any carrier",
    "label": "Name on invoice",
    "labelHelp": "Shown on the duty line of the invoice",
    "effectiveFrom": "Start date",
    "effectiveTo": "End date",
    "effectiveToHelp": "Leave empty for no end",
    "period": "Valid period",
    "periodValue": "{{from}} - {{to}}",
    "noEnd": "No end",
    "sourceUrl": "Source URL",
    "sourceUrlHelp": "URL of the page that supports the amount (required)",
    "note": "Note",
    "active": "Use this rule",
    "inactive": "Not in use",
    "componentsTitle": "Components",
    "componentLabel": "Component {{n}} name",
    "componentSummary": "{{label}}: {{rate}}% of {{base}}",
    "base": "Based on",
    "baseSubtotal": "Subtotal",
    "baseSubtotalShipping": "Subtotal + shipping",
    "baseSubtotalShippingPrior": "Subtotal + shipping + earlier components",
    "ratePct": "Rate (%)",
    "minAmount": "Minimum amount",
    "maxAmount": "Maximum amount",
    "amountCurrency": "Currency of min / max",
    "amountCurrencyHelp": "Choose one when you enter a minimum or maximum",
    "currencyNone": "None",
    "addComponent": "Add component",
    "removeComponent": "Remove component {{n}}",
    "actions": "Actions",
    "editAriaLabel": "Edit {{name}}",
    "deleteAriaLabel": "Delete {{name}}",
    "deleteTitle": "Delete duty amount rule",
    "deleteMessage": "Delete \"{{name}}\". Amounts on issued invoices do not change.",
    "incotermsTitle": "Current duty terms: {{value}}",
    "incotermsDdp": "The terms are DDP, so these amounts are added to invoices.",
    "incotermsNotDdp": "Duty is not billed now. These amounts are added to invoices only when the terms are DDP.",
    "changeTerms": "Change the terms on the Tenant Policy page",
    "empty": "No rules yet.",
    "loadError": "Could not load. Please reopen the page.",
    "saveError": "Could not save. Please try again.",
    "deleteError": "Could not delete. Please try again.",
    "overlapError": "Another rule for the same country and carrier overlaps this period. Check the period or the carrier.",
    "inputError": "Some input is invalid. Check the country, source URL, period, and the min / max and currency of each component."
  },
```

### 2-20. frontend/api-contract/openapi.json

手で書かない。手順7 の `python -m tools.export_openapi` が書き出したものをそのまま入れる。

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa 2>&1 | tail -1
    cd ~/sa && git checkout release/invoice-create-portfolio-bin-b
    cd ~/sa && git log --oneline -1 | tail -1
    cd ~/sa && git merge-base --is-ancestor origin/main HEAD; echo "is-ancestor exit=$?"
  期待: 4行目 `is-ancestor exit=0`。1 なら `BLOCKED: 手順1 is-ancestor`（取り込みは Opus が行う）。

手順2 実装前点検 P1〜P6 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/invoice-create-portfolio/card-B.md | tail -1
    cd ~/sa && ls backend/app/schemas/duty_rules.py backend/app/services/duty_rules.py backend/app/services/fx_currencies.py backend/app/routers/duty_rules.py backend/tests/test_duty_rules_router.py backend/tests/test_duty_rules_pg.py frontend/src/pages/admin/dutyRuleTypes.ts frontend/src/pages/admin/DutyRuleFormModal.tsx frontend/src/pages/admin/DutyRulesPage.tsx frontend/src/pages/admin/DutyRulesPage.test.tsx 2>&1 | grep -c "No such file or directory"
    cd ~/sa && grep -c "CREATE TABLE IF NOT EXISTS {schema}.tenant_duty_rules (" backend/app/services/tenant.py
    cd ~/sa && grep -c "CREATE TABLE IF NOT EXISTS {schema}.tenant_duty_rule_components (" backend/app/services/tenant.py
    cd ~/sa && grep -c "duty-rules\|duty_rules" backend/app/main.py backend/app/realtime/topics.py frontend/src/App.tsx frontend/src/constants/menuPermissions.ts | tail -4
    cd ~/sa && grep -c '"dutyRules"' frontend/src/locales/ja.json frontend/src/locales/en.json | tail -2
    cd ~/sa && grep -c -x -F '    duplicates,' backend/app/main.py
    cd ~/sa && grep -c -x -F '    duplicates.router, prefix="/api/v1", tags=["duplicates"],' backend/app/main.py
    cd ~/sa && grep -c -x -F '    ("POST", "/api/v1/admin/discord/own-server/apply"): _PENDING,' backend/app/realtime/topics.py
    cd ~/sa && grep -c -x -F 'import ChannelMastersPage from "./pages/admin/ChannelMastersPage";' frontend/src/App.tsx
    cd ~/sa && grep -c -x -F '                      <Route path="channel-masters"     element={<ChannelMastersPage />} />' frontend/src/App.tsx
    cd ~/sa && grep -c -x -F '        { to: "channel-masters", labelKey: "nav.channelMasters", visible: can("channelMasters") },' frontend/src/pages/management-center/ManagementCenterPage.tsx
    cd ~/sa && grep -c -x -F '  "channel-masters": "Channel Management",' frontend/src/pages/management-center/ManagementCenterPage.test.tsx
    cd ~/sa && grep -c -x -F 'it("links the 4 admin pages under the management-center layout", () => {' frontend/src/pages/management-center/ManagementCenterPage.test.tsx
    cd ~/sa && grep -c -x -F '  expect(screen.getAllByRole("link").length).toBeGreaterThan(4);' frontend/src/pages/management-center/ManagementCenterPage.test.tsx
    cd ~/sa && grep -c -x -F '  | "channelMasters"' frontend/src/constants/menuPermissions.ts
    cd ~/sa && grep -c -x -F '  channelMasters: { labelKey: "nav.channelMasters", anyOf: ["tenant.profile.edit"] },' frontend/src/constants/menuPermissions.ts
    cd ~/sa && grep -c -x -F '    menus: ["tenantProfile", "tenantPolicy", "discordConfig", "discordAnnounce", "channelMasters"],' frontend/src/constants/menuPermissions.ts
    cd ~/sa && grep -c -x -F '  channelMasters: (h) => h("tenant.profile.edit"),' frontend/src/constants/menuPermissions.test.ts
    cd ~/sa && git grep -c -w 964 -- backend migrations scripts | wc -l
  期待: 3行目 10。4行目 1。5行目 1。6行目は4ファイルとも `:0`。7行目は2ファイルとも `:0`。8行目から20行目はどれも 1。21行目 0。

手順3 §2 の変更をする（2-1 から順に。新規の 10 ファイルは Write ツール、それ以外は Edit ツールで行う。2-20 の openapi.json は手順7 で作る）

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

手順5 backend の形
    cd ~/sa && ~/venv312/bin/ruff check backend/app/schemas/duty_rules.py backend/app/services/duty_rules.py backend/app/services/fx_currencies.py backend/app/routers/duty_rules.py backend/app/main.py backend/app/realtime/topics.py 2>&1 | tail -10
    cd ~/sa && ~/venv312/bin/ruff check backend/tests/test_duty_rules_router.py backend/tests/test_duty_rules_pg.py 2>&1 | tail -10
    cd ~/sa && grep -c "duty_rules" backend/app/main.py
    cd ~/sa && grep -c "/api/v1/admin/duty-rules" backend/app/realtime/topics.py
  期待: ruff は2本とも `All checks passed!`／3行目 2（import の1行と include の1行）／4行目 3。

手順6 backend の試験（実 PostgreSQL の試験は CI だけで動く。ここでは skip と出てよい。failed と error は 0 であること）
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_duty_rules_router.py tests/test_duty_rules_pg.py 2>&1 | tail -15
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_realtime_topics.py 2>&1 | tail -15
  期待: 1本目は `21 passed`（router の試験 15 本、うち1本は入力の誤り 7 通り）と `1 skipped`（PG の1本）で failed 0・error 0。2本目は failed 0・error 0。

手順7 API の形を書き出す
    cd ~/sa/backend && ENVIRONMENT=test ~/venv312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -5
    cd ~/sa && grep -c "\"/api/v1/admin/duty-rules" frontend/api-contract/openapi.json
    cd ~/sa && git diff --numstat frontend/api-contract/openapi.json | tail -1
  期待: 1行目は何も出ない（exit 0）。2行目 3（一覧・選択肢・1件の3つの道）。3行目は足した行が 0 より大きい（数は Opus が見る）。

手順8 画面の点検と試験
    cd ~/sa/frontend && npm ci 2>&1 | tail -3
    cd ~/sa/frontend && npm run generate:api-types 2>&1 | tail -3
    cd ~/sa/frontend && npm run check:all 2>&1 | tail -30
    cd ~/sa/frontend && npx tsc --noEmit 2>&1 | tail -20
    cd ~/sa/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/admin/DutyRulesPage.test.tsx src/pages/management-center/ManagementCenterPage.test.tsx src/constants/menuPermissions.test.ts 2>&1 | tail -20
  期待: check:all は最後まで通り、失敗の行が無い（`npm run check:all` の終了が 0）。tsc は何も出さない。vitest は 3 ファイルとも passed で failed 0（DutyRulesPage.test.tsx は 6 本）。

手順9 変えたファイルの名前と数
    cd ~/sa && git status --short | tail -30
    cd ~/sa && git diff --stat | tail -20
  期待: §1 のファイルだけ（新規の 10 ファイルは `??` で各1行。既存は 10 ファイル）。`frontend/src/api/generated/` は git の外なので出ない。

手順10 記録と送り出し
    cd ~/sa && git add backend/app/schemas/duty_rules.py backend/app/services/duty_rules.py backend/app/services/fx_currencies.py backend/app/routers/duty_rules.py backend/tests/test_duty_rules_router.py backend/tests/test_duty_rules_pg.py backend/app/main.py backend/app/realtime/topics.py && git status --short | tail -30
    cd ~/sa && git add frontend/src/pages/admin/dutyRuleTypes.ts frontend/src/pages/admin/DutyRuleFormModal.tsx frontend/src/pages/admin/DutyRulesPage.tsx frontend/src/pages/admin/DutyRulesPage.test.tsx frontend/src/App.tsx && git status --short | tail -30
    cd ~/sa && git add frontend/src/pages/management-center/ManagementCenterPage.tsx frontend/src/pages/management-center/ManagementCenterPage.test.tsx frontend/src/constants/menuPermissions.ts frontend/src/constants/menuPermissions.test.ts && git status --short | tail -30
    cd ~/sa && git add frontend/src/locales/ja.json frontend/src/locales/en.json frontend/api-contract/openapi.json && git status --short | tail -30
    cd ~/sa && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(duty-rules): add duty amount rules API and management-center screen (invoice-create-portfolio bin B)" && git log --oneline -1 | tail -1
    cd ~/sa && git branch --show-current | tail -1
    cd ~/sa && git push -u origin HEAD 2>&1 | tail -3
    cd ~/sa && git log --oneline -2 @{u} | tail -2
  最後の `git add` の後の status に §1 に無いファイルが出たら、commit せずに `BLOCKED: 範囲外のファイル` で停止する。`git branch --show-current` が `release/invoice-create-portfolio-bin-b` でなければ push せずに `BLOCKED: 枝の名前` で停止する。最後の `git log` の1行目は commit の行と同じであること。

## 4. 想定される分かれ道

- 停止する（その場で作業を停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - 手順1 の is-ancestor が 0 でない・P1〜P6 のどれかが外れた → `BLOCKED: 手順1` か `BLOCKED: P番号`。
  - §2 の変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名 変更前の文`。
  - 手順5 の数・手順7 の数の期待が外れた → 出力を貼って `BLOCKED: 手順5` か `BLOCKED: 手順7`。
  - 手順6 で failed か error が 1 件でも出た → 試験を直さず最後の 15 行を貼って `BLOCKED: pytest`。ただしカードからの書き写し間違い（字・字下げ）が出力から分かるときだけ、カードの文に合わせて直してよい。直したら何をどう直したかを書く。
  - 手順8 の check:all・tsc・vitest のどれかが失敗した → 直さず最後の行を貼って `BLOCKED: 手順8 check:all`・`BLOCKED: 手順8 tsc`・`BLOCKED: 手順8 vitest` のどれか。書き写し間違いの扱いは手順6 と同じ。
  - push が拒まれた → 最後の 3 行を貼って `BLOCKED: push`（force はしない）。
- 記録して続ける（値を報告に書き、判定は Opus がする）:
  - ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I` を同じファイルに流して、その結果を書く。I 以外を出したら `BLOCKED: ruff`。
  - ruff が E501（行が長い）だけを出した → 直さずにそのまま書く（判定は Opus がする）。
  - 手順6 で skipped が出る → そのまま書く（実 PostgreSQL の試験は CI で動く）。
  - npm ci や vitest が警告（warn）を出す → そのまま書く。

## 5. 報告の形

- 宛先: 完了報告の本文（クラウドの実行の最後の返事）。ファイルに書かない。
- 1 行目: `RECEIVED invoice-create-portfolio-B HEAD=…`。2 行目: 「本報告はカード 便B 関税の額の画面と API を作る の実行結果である」。
- 手順1・2・4・5・6・7・8・9・10 の出力（tail の範囲）をそのまま貼る。要約しない。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。待ちが要るものは Opus が見る（CI の結果など）。
- ファイルの編集は Edit ツールで行う（新規の 10 ファイルだけ Write ツール）。ヒアドキュメントで書かない。
- PR は作らない（Opus が作り、`scripts/dev/validate-pr-body.sh` で確かめる）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

END OF CARD

