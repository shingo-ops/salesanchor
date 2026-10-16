# 実装カード 便1 — 「調べたが無い」の記録の受け皿（ADR-1020）

> この文書は何か：共用商品マスタの9項目必須化（ADR-1020）の便1の作業指示書です。「調べたが存在しない」と確かめた空欄を記録する表を作り、商品を登録・保存する入口が、細分類と「調べたが無い」の印を受け取って保存できるようにします。**この便では保存を止めません**（止めるのは便3）。

- 設計: docs/handoff/master-register-required-fields/design.md §4 便1・§7（PO 承認 2026-10-16「y」）
- 現在地: docs/handoff/master-register-required-fields/recon.md、追加調査 /tmp/CC報告ファイル/master-required-fields/add/
- 登録ルール: docs/specs/product-master/registration-rules.md
- 対象ADR: ADR-1020（本テーマ・Proposed）、ADR-155（共用マスタの値は migration で入れない）、ADR-145（products の RLS）、ADR-135・ADR-136（危険 PR の GO）、ADR-027（文言。この便では画面を触らない）
- 状態: 設計は Opus 自己審査 APPROVE（design.md §11）。§2-2 の細部は Opus の技術判断（設計の目的・範囲は変えない）
- 危険便: はい（`migrations/` を含む）。GO は PO の「GO #番号」。担当はマージしない
- 担当: 実装 Sonnet／コード審査・GO 記録・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（下書きにしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（受け皿と受け取りだけ。画面は便2、止めるのは便3） |
| 5 | 既存ブランチへの追記。起点と作業場所を明示 | ○（§10 手順1。作業場所は作成済み・登録済み） |
| 6 | 書式は実例で示した | ○（§4 に SQL・関数の完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2・§5-4） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行の目印は HEAD 943afe6e6（origin/main 74eb678cf を含む）で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | 既存の作業場所の実在を `ls -1d` と `git worktree list` で確かめる | ○（§10 手順1） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh`。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/07-migration.md | `run_all_migrations.sh` の末尾に登録・直近を実測して採番・値を入れない | ○（§4-1・§5-5） |
| guards/08-vps.md | 本番には触らない | ○（§8） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード ADR-1020 便1 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. migration 1本: 表 `public.product_blank_confirmations`（§4-1）と、その実行登録（`scripts/run_all_migrations.sh`）と保護一覧（`scripts/migration-guard/protected-tables.txt`）への追記
2. `backend/app/services/tcg_product_master_svc.py`: 定数・検査関数・印の保存関数と、新規登録の関数が細分類と印を受け取る変更（§4-2・§4-3）
3. 新規登録の入口2つ（`backend/app/routers/tcg_product_import.py` の `POST /tcg/products/create`、`backend/app/routers/tcg_product_master.py` の `POST /tcg/products`）が細分類と印を受け取る（§4-4）
4. 詳細保存（`PUT /tcg/products/detail/{product_id}`）が細分類と印を受け取る（§4-5）
5. CSV 取り込みが登録者の名前を渡す（§4-6。列は足さない）
6. 試験（§4-7）と `frontend/api-contract/openapi.json` の再生成（§4-8）

入れない:
- 保存を止める（422 にする）こと。足りない項目はログに残すだけ（便3）
- 画面・`ja.json`・`en.json`（便2）
- CSV の列の追加、往復 CSV（`backend/app/services/tcg_product_roundtrip_svc.py`）の変更（便2・便3）
- 細分類と作品（ゲーム）の紐づけの照合（便2）
- 詳細の取得（GET）の応答に細分類と印を足すこと（便2）
- `.github/workflows/` の変更
- 本番のデータの書き換え

## 2. 前提の事実と設計の細部

### 2-1. 事実（HEAD 943afe6e6）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 新規登録の関数は引数がすべてキーワード指定。`mark: str = ""`・`english_title: str = ""`・`force`・`commit` がある。細分類と登録者の引数は無い | `backend/app/services/tcg_product_master_svc.py:331-348` |
| F2 | products への INSERT は `SET LOCAL app.is_operator = 'true'` の後。列は `product_code, name, release_date, category_class, product_kind_id, work_id, manufacturer_id, product_category_id, mark, name_en, is_active`。`RETURNING id::text AS id, id AS int_id`。products の id は整数 | `tcg_product_master_svc.py:393-425` |
| F3 | このファイルには logger が無い（`import logging` も無い） | `grep -n "logger" tcg_product_master_svc.py` が 0 行 |
| F4 | `CreateProductBody` は :369-379。入口は :382-412 で `_user: User = Depends(require_super_admin)`。ValueError を捕まえていない | `backend/app/routers/tcg_product_import.py` |
| F5 | `CreateProductRequest` は :92-105。入口は :210-242 で `_user: dict = Depends(require_super_admin)`。ValueError は 422 にしている | `backend/app/routers/tcg_product_master.py` |
| F6 | `ProductDetailUpdate` は `extra="forbid"`（:275-295）。保存口は :298-316 で `values = payload.model_dump(mode="json", exclude={"revision"})` を渡し、登録者は `str(user.email or user.id or "")` | `tcg_product_import.py` |
| F7 | 詳細保存のサービスは `SELECT ... FOR UPDATE` → 版の照合 → `SET LOCAL app.is_operator = 'true'`（:175）→ products の UPDATE（:176-184）→ 語の表 → 監査 → `await db.commit()`（:216）。失敗は全部 rollback | `backend/app/services/tcg_product_detail_svc.py:113-220` |
| F8 | CSV 取り込みは 1 行ごとに `create_product(db, force=True, commit=False, **payload)`（:524）。`executed_by` は関数の引数で来る（router :253） | `backend/app/services/tcg_product_import_svc.py:500-543` |
| F9 | products.product_format_id は `INTEGER REFERENCES public.product_formats(id) ON DELETE SET NULL`。product_formats は `id SERIAL`・`is_active BOOLEAN` | `migrations/20260920_130000_create_product_classification.sql:97-99`・`migrations/20260922_030000_product_format_game_links.sql:10` |
| F10 | RLS の前例: ENABLE と FORCE、SELECT は `USING (true)`、書き込みは `FOR ALL USING (current_setting('app.is_operator', true) = 'true') WITH CHECK (同じ)` | `migrations/20260628_170000_add_app_fx_rates.sql:45-63` |
| F11 | 保護一覧の正本は `scripts/migration-guard/protected-tables.txt`（表名は :11-37、最後は `supplier_aliases`） | 同ファイル |
| F12 | migration の直近は `20261016_180000_add_users_write_rls.sql`（origin/main）。新しい migration は `run_all_migrations.sh` か deploy.yml に登録しないと CI が落ちる。刻印の重複も落ちる | `git ls-tree origin/main migrations/`・`.github/workflows/migration-guard.yml:131-132`・`:287-332` |
| F13 | 4 つの書き込み口は即時反映の表 `NO_SIGNAL_ROUTES` に載っている（新しい口は作らないので表は触らない） | `backend/app/realtime/topics.py:353-358` |
| F14 | API の形が変わったら `frontend/api-contract/openapi.json` の再生成が CI で必須 | `.github/workflows/api-contract-check.yml:31-53` |
| F15 | 既存の試験は新規登録の関数を `**args` で呼ぶ（`test_tcg_product_import.py:368-370`・`test_tcg_completion_safety.py:164-165`・`test_tcg_product_code_collision_wiring.py:54`）。新しい引数には既定値を付けるので変えなくてよい | grep 結果 |
| F16 | 実 PostgreSQL の RLS 試験の前例（2 本の接続・skip の条件） | `backend/tests/test_ops_incident_tables_rls.py:1-26` |

### 2-2. 設計の細部の決定（Opus）

| # | 決めたこと | 理由 |
|---|---|---|
| D1 | 印を付けられる項目は `name_en`・`mark`・`release_date`・`exclude_keywords` の4つだけ（表の CHECK と pydantic の Literal の二重） | 設計 §2・ADR-1020。ほかの5項目は空を認めない |
| D2 | 印は「その項目が本当に空のとき」だけ保存する。値の入った項目に印が来ても保存しない（捨てる） | 値と印が同時にあると、便3の判定と月次の数え上げが狂う |
| D3 | 新規登録で印が来なければ、印の表には何も書かない（DB への問い合わせも増やさない） | 既存の試験の偽 DB（呼び出し回数）を壊さない |
| D4 | 詳細保存で `blank_confirmations` が来たら「その商品の印の全体」として置き換える。来なければ、値が入った項目の印だけを消す | 画面（便2）は印の全体を送る。古い画面は送らないので、既存の印を勝手に消さない |
| D5 | 詳細保存で `product_format_id` が来なければ、今の値を変えない。来たら（null を含む）その値にする | 今の画面は細分類を送らない。既定値で null を書くと、本番の 1,247 件の細分類が消える |
| D6 | 細分類は、指定されたら `product_formats` に `is_active = TRUE` で在るかを確かめる。無ければ新規登録は ValueError `PRODUCT_FORMAT_INVALID`、詳細保存は 422 `PRODUCT_DETAIL_INVALID_CLASSIFICATION` | 外部キーの違反で 500 にしない。作品との紐づけの照合は便2 |
| D7 | 検査関数は DB を触らない純粋な関数にし、便1 では足りない項目を `logger.info` で残すだけ | 便3 で 422 に切り替えるとき、同じ関数をそのまま使う |
| D8 | 登録者は `confirmed_by` に `str(user.email or user.id or "")` の先頭 200 文字。空なら `"unknown"` | 既存の詳細保存・CSV 取り込みと同じ表し方（F6・F8） |

## 3. 触るファイル（これ以外は触らない）

- 新規: `migrations/20261016_190000_create_product_blank_confirmations.sql`（刻印は §6 の分岐で変わることがある）
- 変更: `scripts/run_all_migrations.sh`（末尾に 2 行の追記のみ）
- 変更: `scripts/migration-guard/protected-tables.txt`（末尾に 1 行の追記のみ）
- 変更: `backend/app/services/tcg_product_master_svc.py`
- 変更: `backend/app/routers/tcg_product_import.py`
- 変更: `backend/app/routers/tcg_product_master.py`
- 変更: `backend/app/services/tcg_product_detail_svc.py`
- 変更: `backend/app/services/tcg_product_import_svc.py`（1 行の変更のみ）
- 新規: `backend/tests/test_product_required_fields.py`
- 新規: `backend/tests/test_product_blank_confirmations_pg.py`
- 変更: `backend/tests/test_tcg_product_import.py`（呼び出しの期待値に `actor` を足すだけ。Opus 追記 10/16）
- 変更: `backend/tests/test_tcg_product_master.py`（差し替え関数 `_bypass` の戻り値を `email`・`id` を持つ形にするだけ。Opus 追記 10/16）
- 変更: `frontend/api-contract/openapi.json`（再生成のみ）
- 変更: `docs/handoff/master-register-required-fields/card-bin1.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

### 4-1. migration（`migrations/20261016_190000_create_product_blank_confirmations.sql`）

次の完成形をそのまま書く（値の INSERT は書かない）:

```sql
-- ADR-1020 便1: 共用商品の「調べたが存在しない」空欄の記録。値の書き込みはしない（ADR-155）。冪等。
-- ロールバック: DROP TABLE IF EXISTS public.product_blank_confirmations;

CREATE TABLE IF NOT EXISTS public.product_blank_confirmations (
    product_id   INTEGER     NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    field_code   TEXT        NOT NULL,
    confirmed_by TEXT        NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    note         TEXT,
    CONSTRAINT product_blank_confirmations_pkey PRIMARY KEY (product_id, field_code),
    CONSTRAINT product_blank_confirmations_field_code_check
        CHECK (field_code IN ('name_en', 'mark', 'release_date', 'exclude_keywords')),
    CONSTRAINT product_blank_confirmations_note_size_check
        CHECK (note IS NULL OR char_length(note) <= 1000)
);

COMMENT ON TABLE public.product_blank_confirmations IS
    'ADR-1020: 共用商品の空欄を「調べたが存在しない」と確かめた記録。値が入ると消す';

ALTER TABLE public.product_blank_confirmations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_blank_confirmations FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS product_blank_confirmations_read ON public.product_blank_confirmations;
CREATE POLICY product_blank_confirmations_read
    ON public.product_blank_confirmations
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS product_blank_confirmations_write ON public.product_blank_confirmations;
CREATE POLICY product_blank_confirmations_write
    ON public.product_blank_confirmations
    FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');
```

`scripts/run_all_migrations.sh` の末尾（最後の `run_sql` の行の後）に次の 2 行を足す:

```bash
# ADR-1020 便1: 共用商品の「調べたが無い」の記録の表（空・構造のみ・冪等）
run_sql migrations/20261016_190000_create_product_blank_confirmations.sql
```

`scripts/migration-guard/protected-tables.txt` の末尾（`supplier_aliases` の次）に `product_blank_confirmations` を 1 行足す。

### 4-2. 定数と検査関数（`tcg_product_master_svc.py`）

- import の段に `import logging` を足し、`TCG_SCHEMA = "public"` の行の後に `logger = logging.getLogger(__name__)` を置く
- 同じ場所に次を足す:

```python
# ADR-1020: 共用商品の登録で入れる9項目と、「調べたが無い」の印で空を認める4項目
REQUIRED_FIELDS: tuple[str, ...] = (
    "name", "name_en", "mark", "release_date", "search_keywords",
    "exclude_keywords", "work_id", "product_format_id", "product_category_id",
)
BLANK_CONFIRMABLE_FIELDS: tuple[str, ...] = ("name_en", "mark", "release_date", "exclude_keywords")


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple)):
        return not [v for v in value if str(v).strip()]
    return False


def check_required_fields(values: dict[str, Any], blank_confirmations: set[str] | frozenset[str]) -> list[str]:
    """足りない項目の名前を REQUIRED_FIELDS の順で返す（DB は触らない）。

    values のキーは REQUIRED_FIELDS の名前。検索ワード・除外ワードは文字列（カンマ区切り）か語の一覧。
    印は BLANK_CONFIRMABLE_FIELDS の項目にだけ効く。
    """
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        value = values.get(field)
        if isinstance(value, str) and field in ("search_keywords", "exclude_keywords"):
            value = _split_csv_words(value)
        if not _is_blank(value):
            continue
        if field in BLANK_CONFIRMABLE_FIELDS and field in blank_confirmations:
            continue
        missing.append(field)
    return missing
```

### 4-3. 印の保存と、新規登録の関数の変更（`tcg_product_master_svc.py`）

検査関数の後に、次の 2 つを足す:

```python
async def _validate_product_format(db: AsyncSession, product_format_id: int | None) -> None:
    if product_format_id is None:
        return
    row = (await db.execute(
        text("SELECT 1 FROM public.product_formats WHERE id = :id AND is_active = TRUE"),
        {"id": int(product_format_id)},
    )).first()
    if row is None:
        raise ValueError("PRODUCT_FORMAT_INVALID")


async def save_blank_confirmations(
    db: AsyncSession,
    *,
    product_id: int,
    values: dict[str, Any],
    confirmations: set[str] | None,
    actor: str,
) -> None:
    """ADR-1020: 印を保存する。呼ぶ側が app.is_operator を立てた同じトランザクションで呼ぶ。

    confirmations が None なら、値が入った項目の印だけを消す（D4）。
    集合なら、その商品の印を「空の項目 ∩ confirmations」に置き換える（D2・D4）。
    """
    filled = [f for f in BLANK_CONFIRMABLE_FIELDS if not _is_blank(
        _split_csv_words(values.get(f)) if f == "exclude_keywords" and isinstance(values.get(f), str) else values.get(f)
    )]
    if confirmations is None:
        if filled:
            await db.execute(
                text("DELETE FROM public.product_blank_confirmations "
                     "WHERE product_id = :pid AND field_code = ANY(:fields)"),
                {"pid": product_id, "fields": filled},
            )
        return
    keep = [f for f in BLANK_CONFIRMABLE_FIELDS if f in confirmations and f not in filled]
    await db.execute(
        text("DELETE FROM public.product_blank_confirmations "
             "WHERE product_id = :pid AND NOT (field_code = ANY(:keep))"),
        {"pid": product_id, "keep": keep},
    )
    for field in keep:
        await db.execute(
            text("INSERT INTO public.product_blank_confirmations (product_id, field_code, confirmed_by) "
                 "VALUES (:pid, :field, :actor) ON CONFLICT (product_id, field_code) DO NOTHING"),
            {"pid": product_id, "field": field, "actor": (actor or "unknown")[:200]},
        )
```

新規登録の関数（:331-）を次のとおり変える:
- 引数の `commit: bool = True,` の後に 3 つ足す: `product_format_id: int | None = None,`・`blank_confirmations: list[str] | None = None,`・`actor: str = "",`
- 重複チェック（`dup_result = await check_duplicates(`）の直前に `await _validate_product_format(db, product_format_id)` を置く
- INSERT の列の並びの `mark, name_en, is_active` を `mark, name_en, product_format_id, is_active` に、値の並びの `:mark, :english_title, TRUE` を `:mark, :english_title, :product_format_id, TRUE` に変え、バインドの辞書に `"product_format_id": int(product_format_id) if product_format_id is not None else None,` を足す
- `product_id_int = new_row.int_id` の行の直後に、次を足す:

```python
    # ADR-1020 便1: 印の保存（来たときだけ・D3）と、足りない項目のログ（止めない・D7）
    confirmed = set(blank_confirmations or [])
    filled_values = {
        "name": japanese_title, "name_en": english_title, "mark": mark,
        "release_date": release_date, "search_keywords": search_keywords,
        "exclude_keywords": exclude_keywords, "work_id": work_id,
        "product_format_id": product_format_id, "product_category_id": product_category_id,
    }
    if confirmed:
        await save_blank_confirmations(
            db, product_id=product_id_int, values=filled_values, confirmations=confirmed, actor=actor,
        )
    missing = check_required_fields(filled_values, confirmed)
    if missing:
        logger.info("[ADR-1020] product %s registered without required fields: %s", pm_code, ",".join(missing))
```

- 戻り値は変えない（F15 の試験が戻り値を比べている）

### 4-4. 新規登録の入口 2 つ

両方の型に次の 2 つを足す（`from typing import Literal` が無ければ足す）:

```python
    product_format_id: int | None = None
    blank_confirmations: list[Literal["name_en", "mark", "release_date", "exclude_keywords"]] = Field(default_factory=list)
```

- `tcg_product_import.py` の `CreateProductBody`（:369-379 の末尾）。入口（:388-）は `_user` を `user` に改名し、関数の呼び出しに `product_format_id=body.product_format_id,`・`blank_confirmations=body.blank_confirmations,`・`actor=str(user.email or user.id or ""),` を足す。呼び出しを `try:` で囲み、`except ValueError as e: raise HTTPException(status_code=422, detail=str(e)) from e` にする
- `tcg_product_master.py` の `CreateProductRequest`（:92-105 の末尾）。`from pydantic import BaseModel` に `Field` を足す。入口（:216-）は `_user: dict` を `user: User` に改名する（`from app.models import User` を足す）。呼び出しに同じ 3 つを足す（ValueError は既に 422）

### 4-5. 詳細保存

`tcg_product_import.py` の `ProductDetailUpdate`（:275-288 の語の行の後）に足す:

```python
    product_format_id: int | None = None
    blank_confirmations: list[Literal["name_en", "mark", "release_date", "exclude_keywords"]] | None = None
```

保存口（:310）の `values = ...` の直後に次を足す（来なかった項目を渡さない・D4・D5）:

```python
    for optional in ("product_format_id", "blank_confirmations"):
        if optional not in payload.model_fields_set:
            values.pop(optional, None)
```

`tcg_product_detail_svc.py` の `update_product_detail`:
- import に `from app.services.tcg_product_master_svc import _validate_product_format, save_blank_confirmations` を足す（循環 import になったら関数の中で import する）
- products の UPDATE（:176-184）の直後に次を足す:

```python
        # ADR-1020 便1: 細分類（来たときだけ・D5）と印（D4）
        if "product_format_id" in values:
            try:
                await _validate_product_format(db, values["product_format_id"])
            except ValueError:
                raise ProductDetailError(422, "PRODUCT_DETAIL_INVALID_CLASSIFICATION")
            await db.execute(text(
                "UPDATE public.products SET product_format_id=:fid WHERE id=:pid"
            ), {"fid": values["product_format_id"], "pid": product["id"]})
        await save_blank_confirmations(
            db,
            product_id=product["id"],
            values={"name_en": params["english_title"], "mark": params["mark"],
                    "release_date": params["release_date"], "exclude_keywords": values["exclude_keywords"]},
            confirmations=set(values["blank_confirmations"]) if values.get("blank_confirmations") is not None else None,
            actor=actor,
        )
```

### 4-6. CSV 取り込み（`tcg_product_import_svc.py:524`）

`outcome = await create_product(db, force=True, commit=False, **payload)` の行だけを、`outcome = await create_product(db, force=True, commit=False, actor=executed_by, **payload)` に変える（`executed_by` はその関数の引数。名前が違えば §6）。

### 4-7. 試験

`backend/tests/test_product_required_fields.py`（新規・DB なし）。次の 6 本（名前もこのとおり）:

| # | 試験の名前 | 確かめること |
|---|---|---|
| 1 | `test_all_filled_returns_empty` | 9 項目すべてに値（検索・除外は `"a,b"`）で `[]` |
| 2 | `test_all_blank_returns_nine_in_order` | 空の辞書で `list(REQUIRED_FIELDS)` と一致 |
| 3 | `test_confirmation_allows_only_four_fields` | 全部空・印に9項目全部の名前 → 戻りは `["name", "search_keywords", "work_id", "product_format_id", "product_category_id"]` |
| 4 | `test_comma_only_keywords_are_blank` | 検索ワード `" , "` は足りない扱い |
| 5 | `test_create_body_rejects_unknown_confirmation` | `CreateProductBody(**最小の値, blank_confirmations=["name"])` が `ValidationError` |
| 6 | `test_detail_update_omits_unsent_optional_fields` | `ProductDetailUpdate` を細分類・印なしで作ると `model_fields_set` に `product_format_id`・`blank_confirmations` が無い |

`backend/tests/test_product_blank_confirmations_pg.py`（新規・実 PostgreSQL。冒頭の環境の扱い・skip の条件・接続 2 本は F16 と同じ。準備で §4-1 の migration を当てる）。次の 5 本:

| # | 試験の名前 | 確かめること |
|---|---|---|
| 1 | `test_write_requires_operator_flag` | アプリのロールで旗なしの INSERT が拒まれ（`42501` か 0 行）、旗ありなら入る |
| 2 | `test_field_code_check_rejects_other_fields` | 旗ありで `field_code = 'name'` の INSERT が CHECK 違反 |
| 3 | `test_cascade_on_product_delete` | 管理の接続で products に 1 行（`product_code` は `"TEST-BLANK-" + uuid4().hex[:8]`・`name`・`category_class`・`is_active`。前例 `test_tcg_product_import_atomicity_pg.py:52`）、印 1 行 → products の行を消すと印も消える |
| 4 | `test_save_replaces_and_drops_filled_fields` | 印の保存関数に `{"name_en": "", "mark": "X1"}`・印 `{"name_en", "mark"}` → 残る印は `name_en` だけ |
| 5 | `test_save_without_set_clears_only_filled` | 印 `name_en`・`release_date` がある商品に、`confirmations=None`・`{"name_en": "Foo", "release_date": None}` → 残るのは `release_date` だけ |

後片付けは管理の接続で、作った products の行を消す（印は CASCADE で消える）。

### 4-8. API の形

`cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` を実行し、差分をコミットする。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 静的検査: 作業場所で `cd backend && ruff check app/services/tcg_product_master_svc.py app/services/tcg_product_detail_svc.py app/services/tcg_product_import_svc.py app/routers/tcg_product_import.py app/routers/tcg_product_master.py tests/test_product_required_fields.py tests/test_product_blank_confirmations_pg.py` が 0 件。

5-2. 試験の名前: `grep -nE "^(async )?def test_" backend/tests/test_product_required_fields.py backend/tests/test_product_blank_confirmations_pg.py` が 11 行で、名前が §4-7 の表のとおり。

5-3. 試験: `cd backend && python3 -m pytest tests/test_product_required_fields.py tests/test_tcg_product_master.py tests/test_tcg_product_import.py tests/test_tcg_product_detail_pg.py tests/test_product_blank_confirmations_pg.py tests/test_realtime_topics.py -q -p no:cacheprovider` の出力の最後の 30 行。PG の試験は手元では skip になる。そのときは「手元では skip・CI で実行」と書く。

5-4. 差分: `git diff origin/main --stat -- backend migrations scripts frontend` の出力。§3 の 11 ファイル（カードを除く）と一致すること。加えて `git diff origin/main -- scripts/run_all_migrations.sh scripts/migration-guard/protected-tables.txt | grep -c "^-[^-]"` が 0。

5-5. migration に値が無いこと: `grep -ciE "^[[:space:]]*(INSERT|UPDATE|DELETE)" migrations/20261016_190000_create_product_blank_confirmations.sql` が 0。

5-6. 印の SQL に利用者の文字列が入らないこと: `grep -n "product_blank_confirmations" backend/app/services/tcg_product_master_svc.py` の出力（すべてバインド変数で書いていること）。

5-7. PR の CI は担当が待たない。PR を作ったら URL を報告して終える。

## 6. 分岐ごとの対処

- origin/main に `20261016_190000` 以降の刻印の migration が既にある → `git ls-tree --name-only origin/main migrations/ | tail -3` の出力を貼り、最後の刻印より後の `20261016_HH0000` を使う（§3・§4-1・§5 の名前も同じに変える）
- 作業ブランチに origin/main を取り込んで衝突した → 解消せずに BLOCKED:（衝突したファイル名を貼る）
- `tcg_product_import_svc.py` の関数の引数名が `executed_by` でない → その関数の def の行を貼り、同じ値を表す引数を渡す。無ければ NEEDS_DECISION:
- §4-5 の `params` のキー名（`english_title`・`mark`・`release_date`）や `ProductDetailError` の引数の形が実物と違う → 実物の該当行を貼り、同じ値・同じ形に合わせて書く（意味を変えない）。同じ値が見つからなければ NEEDS_DECISION:
- 循環 import で起動できない → `tcg_product_detail_svc.py` の import を関数の中に移す。それでも直らなければ BLOCKED:
- 既存の試験が偽の DB の呼び出し回数や SQL の文字列で落ちる → 落ちた試験の名前と原文を貼る。試験の期待値を変えてよいのは「INSERT の列に product_format_id が増えた」ことによる差だけ。ほかは BLOCKED:
- 試験 pg-1 で旗なしの INSERT が通る → 推測で直さず BLOCKED:（RLS の穴なので Opus が見る）
- CI の migration-guard が落ちる → 失敗の原文を貼って BLOCKED:

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 表が作られ、旗なしでは書けず、4 項目以外の印は入らず、商品を消すと印も消える | CI の pytest（pg-1〜3） |
| 印は空の項目にだけ残り、値が入ると消える | CI の pytest（pg-4・pg-5） |
| 9 項目の検査関数が足りない項目を順に返し、印は 4 項目にだけ効く | CI の pytest（1〜4） |
| 入口が細分類と印を受け取り、知らない印は 422 | CI の pytest（5）・既存の試験が緑 |
| 詳細保存で細分類を送らない今の画面は、細分類を消さない | CI の pytest（6）と §4-5 の分岐 |
| migration に値の書き込みが無い | §5-5・CI の migration-guard |
| 反映後、本番に表があり 0 行・RLS が有効 | §8（Opus） |

## 8. 反映の前後（Opus が行う。担当はしない）

- マージの前に PO の「GO #番号」を受け取り、PR 本文の `### GO記録` に書き写す（ADR-136）
- マージ → deploy の成功を Actions の記録で確かめる
- 本番を読むだけで確かめる: `product_blank_confirmations` が在り 0 行、`relrowsecurity` と `relforcerowsecurity` が真、ポリシー 2 つ
- 生出力は /tmp/CC報告ファイル/master-required-fields/bin1-deploy/ に置く

## 9. 戻し方

- この PR の revert を main にマージ（API は元の形に戻る）。表は残っても使う口が無い。表を消すなら `DROP TABLE IF EXISTS public.product_blank_confirmations;` を PO 確認の上で別の migration にする

## 10. PR

手順1 作業場所を確かめ、origin/main を取り込む（既存ブランチ。new-worktree.sh は使わない）
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields && ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields && git worktree list | grep -c release-master-register-required-fields
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields && git fetch -q origin && git status -sb | head -3 && git merge --no-edit origin/main 2>&1 | tail -5
期待する出力 git status の 1 行目が `## release/master-register-required-fields...origin/release/master-register-required-fields`、merge が成功

手順2 §4 を Write/Edit ツールで実装し、§5-1〜5-6 を実行する

手順3 commit と push
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields && git add migrations/20261016_190000_create_product_blank_confirmations.sql scripts/run_all_migrations.sh scripts/migration-guard/protected-tables.txt backend/app/services/tcg_product_master_svc.py backend/app/services/tcg_product_detail_svc.py backend/app/services/tcg_product_import_svc.py backend/app/routers/tcg_product_import.py backend/app/routers/tcg_product_master.py backend/tests/test_product_required_fields.py backend/tests/test_product_blank_confirmations_pg.py frontend/api-contract/openapi.json docs/handoff/master-register-required-fields/card-bin1.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields && PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH" git commit -m "feat: ADR-1020便1 調べたが無いの記録表と細分類・印の受け取り"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields && git log -1 --oneline && git push -q && git log origin/release/master-register-required-fields -1 --oneline
期待する出力 2 つの git log が同じハッシュ

手順4 PR を作る
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields && gh auth status 2>&1 | grep -c "Active account: true"

- 名義が `shingo-cc` であることを確かめる
- 本文は Write ツールで英字だけのパスのファイル（例: /private/tmp/claude-501/bin1-pr-body.md）に作り、`scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめる（2 分以上かかるので timeout を長めにする）
- PR は `scripts/gh-pr-create-safe.sh` に本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。base は main。ready で作る（下書きにしない）。担当はマージしない
- 作成後に `.pr-number` と `gh pr list --head release/master-register-required-fields --json number` の一致を確かめる
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/master-register-required-fields/recon.md）・設計（docs/handoff/master-register-required-fields/design.md）・このカード・ADR-1020 を書く。区分は L（危険便）。PO承認: に「PO 2026-10-16『y』（KGI G1〜G4・3便）」と書く
- `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし。良い例: 触るファイル: migrations/20261016_190000_create_product_blank_confirmations.sql, scripts/run_all_migrations.sh, scripts/migration-guard/protected-tables.txt, backend/app/services/tcg_product_master_svc.py, backend/app/services/tcg_product_detail_svc.py, backend/app/services/tcg_product_import_svc.py, backend/app/routers/tcg_product_import.py, backend/app/routers/tcg_product_master.py, backend/tests/test_product_required_fields.py, backend/tests/test_product_blank_confirmations_pg.py, frontend/api-contract/openapi.json, docs/handoff/master-register-required-fields/card-bin1.md ／ 削除するファイル: には差分に削除の行があるファイルだけを書く
- `### GO記録` は担当が書かない。本文に「GO 待ち（危険便・ADR-136）」と 1 行書く

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-6 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/master-required-fields/bin1-impl/）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える
- 登録ルールのフック（master-register-rules-guard）は、Bash のコマンドに新規登録の関数名と丸かっこの組み合わせなどがあると止める。この便は商品の登録ではないので、Bash のコマンドにはその文字列を書かない（grep は関数名だけで検索する）。ack の行は書かない

## 13. 報告欄（担当が追記）

（未記入）

END OF CARD
