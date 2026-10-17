# 実装カード 便2a — 細分類の選択肢・ゲームとの照合・印の返却（ADR-1020）

> この文書は何か：共用商品マスタの9項目必須化（ADR-1020）の便2a（バックエンドだけ）の作業指示書です。画面（便2b）が細分類と「調べたが無い」の印を扱えるように、API が細分類の選択肢（紐づくゲーム付き）と印を返し、細分類とゲームの組み合わせを照合し、細分類マスタで「使えるゲーム」を置き換えられるようにします。**新規登録で足りない項目を止めるのは便3**（この便では止めない）。

- 設計: docs/handoff/master-register-required-fields/design.md §4「便2 の分け方」・§7（KGI と3便は PO 承認 2026-10-16「y」）
- 現在地: docs/handoff/master-register-required-fields/recon.md、便2の調査 /tmp/CC報告ファイル/master-required-fields/bin2/recon/facts.md、本番の読み取り /tmp/CC報告ファイル/master-required-fields/bin2a/
- 登録ルール: docs/specs/product-master/registration-rules.md
- 対象ADR: ADR-1020（本テーマ）、ADR-156（分類の3層）、ADR-155・ADR-1007（migration で値を入れない。この便は migration なし）、ADR-027（この便では画面を触らない）
- 状態: 設計は Opus 自己審査 APPROVE。§2-2 の細部は Opus の技術判断（設計の目的・範囲は変えない）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。担当はマージしない
- 担当: 実装 Sonnet／コード審査・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（下書きにしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（API の返却と照合だけ。画面は便2b、CSV は便2c、止めるのは便3） |
| 5 | 既存ブランチへの追記。起点と作業場所を明示 | ○（§10 手順1。作業場所は作成済み・origin/main 449a77166 に追いつき済み） |
| 6 | 書式は実例で示した | ○（§4 に SQL・関数の完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2・§5-4） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行の目印は origin/main 449a77166 で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | 既存の作業場所の実在を `ls -1d` と `git worktree list` で確かめる | ○（§10 手順1） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh`。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | 本番には触らない | ○（§8） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード ADR-1020 便2a の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `backend/app/services/tcg_product_master_svc.py`: 細分類とゲームの照合、細分類の選択肢を返す関数、登録フォームの選択肢に細分類を足す（§4-1）
2. `backend/app/routers/tcg_product_import.py`: `GET /tcg/products/lookups` に細分類を足す（§4-2）
3. `backend/app/services/tcg_product_detail_svc.py`: 詳細の取得に印と細分類の選択肢を足す。詳細保存で細分類とゲームを照合する（§4-3）
4. `backend/app/schemas/product_format.py` と `backend/app/routers/super_admin_product_formats.py`: 細分類マスタの応答に `game_ids`、使えるゲームの置き換え口（§4-4）
5. 試験（§4-5）と `frontend/api-contract/openapi.json` の再生成（§4-6）

入れない:
- 足りない項目で保存を止める（422 にする）こと（便3）
- 画面・`ja.json`・`en.json`（便2b）
- CSV の列の追加、往復 CSV（便2c）
- migration・本番データの書き換え・紐づけの値の追加
- `.github/workflows/` の変更

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 449a77166）

| # | 事実 | 出典 |
|---|---|---|
| F1 | `_validate_product_format(db, product_format_id)` は None を素通りし、有効な細分類が無ければ `ValueError("PRODUCT_FORMAT_INVALID")` | `backend/app/services/tcg_product_master_svc.py` の `async def _validate_product_format` |
| F2 | 新規登録の関数は先頭で `await _validate_product_format(db, product_format_id)` を呼ぶ。`work_id: str | int` は必須の引数 | 同ファイル `async def create_product` の直後 |
| F3 | 登録フォームの選択肢は `lookups[...] = [{"id": r.id, "name": r.name} ...]` の形で4種（work_id・product_kind_id・manufacturer_id・product_category_id）。最後は `return {"item": item, "lookups": lookups}` | 同ファイル `async def fetch_registration_form` |
| F4 | `GET /tcg/products/lookups` も同じ形の4種で、最後は `return {"lookups": lookups}` | `backend/app/routers/tcg_product_import.py` の `async def get_product_lookups` |
| F5 | 詳細の `_snapshot` は `row_to_json(p) AS product` と検索・除外の語の2つ。`_revision` はこの辞書全体の sha256。`_response` の選択肢は `{"id","name","is_active"}` の形で、最後は `return {"product": product, "revision": _revision(snapshot), "lookups": lookups}` | `backend/app/services/tcg_product_detail_svc.py` の `_snapshot`・`_revision`・`_response` |
| F6 | 詳細保存は products の UPDATE の後に「`if "product_format_id" in values:` → `_validate_product_format` → `UPDATE public.products SET product_format_id`」。作品は `params["work_id"]`（変わらなければ元の値）。元の行は `product = before["product"]` | 同ファイル `async def update_product_detail` |
| F7 | 保存の応答の型 `ProductDetailSaveResult` は `product: dict[str, Any]`・`extra="allow"`（product に項目が増えても落ちない） | `backend/app/schemas/tcg_product_code_collision.py` |
| F8 | 画面の下書き（`draftFrom`）は決まった項目だけを拾う。応答に `blank_confirmations` や選択肢が増えても、保存の body には入らない | `frontend/src/features/tcg-product-import/productDetailModel.ts` の `draftFrom`・`buildUpdateBody` |
| F9 | 細分類マスタ API の列 `_COLS`、応答 `ProductFormatResponse`。紐づけ表 `product_format_game_links`（`format_id`・`type_master_id`・`alias`、PK は2つの組、どちらも CASCADE）を読み書きするコードは 0 件 | `backend/app/routers/super_admin_product_formats.py`・`backend/app/schemas/product_format.py`・facts.md §C |
| F10 | 本番: 細分類と作品が両方入った共用商品 1247 件のうち、紐づけに無い組み合わせは 0 件 | /tmp/CC報告ファイル/master-required-fields/bin2a/prod-pairs.txt |
| F11 | 本番: 紐づけ表は RLS 無し。アプリのロール `salesanchor_app` に INSERT・SELECT・UPDATE・DELETE がある | /tmp/CC報告ファイル/master-required-fields/bin2a/prod-links-rls.txt |

### 2-2. 設計の細部（Opus の技術判断）

- D1 照合の規則: 細分類と作品の両方があるとき、`product_format_game_links` にその組が無ければ拒む。どちらかが無ければ照合しない（足りないことを止めるのは便3）
- D2 詳細保存の照合は「細分類が変わった」か「作品が変わった」ときだけ。変えていない古い組み合わせは止めない（ADR-1020 What 3「古い空欄は止めない」と同じ考え）。今は F10 のとおり古い不一致は 0 件
- D3 詳細保存の不一致のコードは `PRODUCT_DETAIL_FORMAT_GAME_MISMATCH`（422）。新規登録は `ValueError("PRODUCT_FORMAT_GAME_MISMATCH")`（入口が既に 422 にする）
- D4 細分類の選択肢の形は、ほかの選択肢と同じ `id`（文字列）・`name`・`is_active` に `game_ids`（文字列の配列。作品の選択肢の `id` と同じ表し方）を足す。並びは `display_order, id`
- D5 印は詳細の `_snapshot` に入れる（`blank_confirmations`、項目名の配列・名前順）。revision と監査の記録にも入る。反映の直後だけ、開きっぱなしの画面の保存が 1 回 409 になりうる（開き直せば直る）
- D6 使えるゲームの置き換えは丸ごと（送った一覧にする）。残す組の `alias` は消さない。外す組を使っている共用商品・テナント商品が1件でもあれば 409 `PRODUCT_FORMAT_GAME_IN_USE` で何も変えない。存在しないか無効なゲームが入っていれば 422

## 3. 触るファイル

1. `backend/app/services/tcg_product_master_svc.py`
2. `backend/app/services/tcg_product_detail_svc.py`
3. `backend/app/routers/tcg_product_import.py`
4. `backend/app/routers/super_admin_product_formats.py`
5. `backend/app/schemas/product_format.py`
6. `backend/tests/test_product_format_game_links_pg.py`（新規）
7. `backend/tests/test_product_format_game_links.py`（新規）
8. `frontend/api-contract/openapi.json`
9. `docs/handoff/master-register-required-fields/card-bin2a.md`（このカード。§13 に追記）
10. `docs/handoff/master-register-required-fields/design.md`（Opus が編集済み。担当は内容を変えず add するだけ）

## 4. 実装

### 4-1. `tcg_product_master_svc.py`

`_validate_product_format` を次の形に置き換える（呼び出しの互換のため `work_id` は省略可）:

```python
async def format_matches_game(db: AsyncSession, product_format_id: int, work_id: int) -> bool:
    """ADR-1020 便2a: 細分類がそのゲーム（作品）に紐づいているか。"""
    row = (await db.execute(
        text("SELECT 1 FROM public.product_format_game_links "
             "WHERE format_id = :fid AND type_master_id = :wid"),
        {"fid": int(product_format_id), "wid": int(work_id)},
    )).first()
    return row is not None


async def _validate_product_format(
    db: AsyncSession, product_format_id: int | None, work_id: int | None = None,
) -> None:
    if product_format_id is None:
        return
    row = (await db.execute(
        text("SELECT 1 FROM public.product_formats WHERE id = :id AND is_active = TRUE"),
        {"id": int(product_format_id)},
    )).first()
    if row is None:
        raise ValueError("PRODUCT_FORMAT_INVALID")
    if work_id is not None and not await format_matches_game(db, product_format_id, work_id):
        raise ValueError("PRODUCT_FORMAT_GAME_MISMATCH")
```

その直後に選択肢の関数を足す:

```python
async def fetch_product_format_options(db: AsyncSession, selected: int | None = None) -> list[dict[str, Any]]:
    """ADR-1020 便2a: 細分類の選択肢。各細分類に紐づくゲーム（作品）の id を付ける。"""
    rows = await db.execute(text(
        "SELECT f.id::text AS id, f.name AS name, f.is_active AS is_active, "
        "COALESCE(array_agg(l.type_master_id::text ORDER BY l.type_master_id) "
        "FILTER (WHERE l.type_master_id IS NOT NULL), ARRAY[]::text[]) AS game_ids "
        "FROM public.product_formats f "
        "LEFT JOIN public.product_format_game_links l ON l.format_id = f.id "
        "WHERE f.is_active = TRUE OR f.id = :selected "
        "GROUP BY f.id, f.name, f.is_active, f.display_order "
        "ORDER BY f.display_order, f.id"
    ), {"selected": selected})
    return [
        {"id": r["id"], "name": r["name"], "is_active": r["is_active"], "game_ids": list(r["game_ids"])}
        for r in rows.mappings()
    ]
```

`create_product` の先頭の `await _validate_product_format(db, product_format_id)` を次に置き換える:

```python
    try:
        _work_id_int: int | None = int(work_id) if str(work_id).strip() else None
    except (TypeError, ValueError):
        _work_id_int = None
    await _validate_product_format(db, product_format_id, work_id=_work_id_int)
```

`fetch_registration_form` の `return {"item": item, "lookups": lookups}` の直前に足す:

```python
    # ADR-1020 便2a: 細分類（紐づくゲーム付き）
    lookups["product_format_id"] = await fetch_product_format_options(db)
```

### 4-2. `tcg_product_import.py`

`get_product_lookups` の `return {"lookups": lookups}` の直前に、§4-1 と同じ 2 行（コメントと `lookups["product_format_id"] = await fetch_product_format_options(db)`）を足す。import に `fetch_product_format_options` を足す（このファイルが `tcg_product_master_svc` から何も import していなければ、`from app.services.tcg_product_master_svc import fetch_product_format_options` を新しく書く）。

### 4-3. `tcg_product_detail_svc.py`

`_snapshot` の SELECT の、除外ワードの行（`... AS exclude_keywords "`）の後ろに 1 行足す（最初の行末の `AS exclude_keywords "` を `AS exclude_keywords, "` にする）:

```python
        "COALESCE((SELECT json_agg(c.field_code ORDER BY c.field_code) "
        "FROM public.product_blank_confirmations c WHERE c.product_id=p.id), '[]'::json) AS blank_confirmations "
```

`_response` の `for field in WORD_TABLES:` のループの直後に足す:

```python
    # ADR-1020 便2a: 「調べたが無い」の印（項目名の配列）
    product["blank_confirmations"] = list(snapshot.get("blank_confirmations") or [])
```

`_response` の `return` の直前に足す:

```python
    # ADR-1020 便2a: 細分類（紐づくゲーム付き）
    lookups["product_format_id"] = await fetch_product_format_options(db, selected=product.get("product_format_id"))
```

import の行（`_validate_product_format, save_blank_confirmations` を import している行）に `fetch_product_format_options` と `format_matches_game` を足す。

`update_product_detail` の `if "product_format_id" in values:` のブロック（`UPDATE public.products SET product_format_id` まで）の直後、`await save_blank_confirmations(` の前に足す:

```python
        # ADR-1020 便2a: 細分類とゲームの照合（細分類か作品が変わったときだけ・D2）
        final_format_id = values["product_format_id"] if "product_format_id" in values else product.get("product_format_id")
        format_changed = "product_format_id" in values and values["product_format_id"] != product.get("product_format_id")
        work_changed = params["work_id"] != product.get("work_id")
        if (final_format_id is not None and params["work_id"] is not None
                and (format_changed or work_changed)
                and not await format_matches_game(db, final_format_id, params["work_id"])):
            raise ProductDetailError(422, "PRODUCT_DETAIL_FORMAT_GAME_MISMATCH")
```

（既存の `except BaseException: await db.rollback(); raise` により、それまでの UPDATE は戻る）

### 4-4. 細分類マスタ API

`backend/app/schemas/product_format.py`:
- `ProductFormatResponse` に `game_ids: list[int] = Field(default_factory=list)` を足す
- 末尾に足す:

```python
class ProductFormatGamesUpdate(BaseModel):
    """ADR-1020 便2a: 使えるゲーム（type_master.id）を丸ごと置き換える。"""

    model_config = ConfigDict(extra="forbid")

    game_ids: list[int] = Field(max_length=200)
```

`backend/app/routers/super_admin_product_formats.py`:
- 先頭の説明の API 一覧に `PUT    /api/v1/super-admin/product-formats/{format_id}/games — 使えるゲームの置き換え` を足す
- import に `ProductFormatGamesUpdate` を足す
- `_UPDATABLE` の下に足す:

```python
async def _game_ids_for(db: AsyncSession, format_ids: list[int]) -> dict[int, list[int]]:
    """ADR-1020 便2a: 細分類ごとの使えるゲーム（product_format_game_links）。"""
    if not format_ids:
        return {}
    result = await db.execute(
        text(
            "SELECT format_id, array_agg(type_master_id ORDER BY type_master_id) AS game_ids "
            "FROM public.product_format_game_links WHERE format_id = ANY(:ids) GROUP BY format_id"
        ),
        {"ids": format_ids},
    )
    return {row["format_id"]: list(row["game_ids"]) for row in result.mappings().all()}
```

- 一覧（`list_product_formats`）の最後を次にする:

```python
    rows = [dict(row) for row in result.mappings().all()]
    games = await _game_ids_for(db, [row["id"] for row in rows])
    return [ProductFormatResponse(**row, game_ids=games.get(row["id"], [])) for row in rows]
```

- 更新（`update_product_format`）の `return ProductFormatResponse(**dict(row))` を次にする（作成はゲームが無いので今のまま）:

```python
    games = await _game_ids_for(db, [row["id"]])
    return ProductFormatResponse(**dict(row), game_ids=games.get(row["id"], []))
```

- 更新の関数と削除の関数の間に足す:

```python
@router.put(
    "/super-admin/product-formats/{format_id}/games",
    response_model=ProductFormatResponse,
    dependencies=[Depends(require_super_admin)],
)
async def replace_product_format_games(
    format_id: int,
    data: ProductFormatGamesUpdate,
    db: AsyncSession = Depends(get_db),
):
    """ADR-1020 便2a: 使えるゲームを送った一覧に置き換える。外す組を商品が使っていれば 409。"""
    wanted = sorted(set(data.game_ids))
    fmt = (await db.execute(
        text(f"SELECT {_COLS} FROM public.product_formats WHERE id = :id FOR UPDATE"),
        {"id": format_id},
    )).mappings().first()
    if not fmt:
        raise HTTPException(status_code=404, detail="フォーマットが見つかりません")
    if wanted:
        found = (await db.execute(
            text("SELECT count(*) FROM public.type_master WHERE id = ANY(:ids) AND is_active = TRUE"),
            {"ids": wanted},
        )).scalar_one()
        if found != len(wanted):
            raise HTTPException(status_code=422, detail="PRODUCT_FORMAT_GAME_UNKNOWN")
    in_use = (await db.execute(
        text(
            "SELECT 1 FROM public.products WHERE product_format_id = :id "
            "AND work_id IS NOT NULL AND NOT (work_id = ANY(:ids)) LIMIT 1"
        ),
        {"id": format_id, "ids": wanted},
    )).first()
    if in_use:
        raise HTTPException(status_code=409, detail="PRODUCT_FORMAT_GAME_IN_USE")
    try:
        await db.execute(
            text(
                "DELETE FROM public.product_format_game_links "
                "WHERE format_id = :id AND NOT (type_master_id = ANY(:ids))"
            ),
            {"id": format_id, "ids": wanted},
        )
        for game_id in wanted:
            await db.execute(
                text(
                    "INSERT INTO public.product_format_game_links (format_id, type_master_id) "
                    "VALUES (:id, :gid) ON CONFLICT (format_id, type_master_id) DO NOTHING"
                ),
                {"id": format_id, "gid": game_id},
            )
    except IntegrityError as exc:
        await db.rollback()
        log_hidden_error("super_admin_product_formats.replace_product_format_games", exc)
        raise HTTPException(status_code=409, detail="制約違反")
    await db.commit()
    games = await _game_ids_for(db, [format_id])
    return ProductFormatResponse(**dict(fmt), game_ids=games.get(format_id, []))
```

（products の SELECT はテナント商品も含めて数える。RLS で見えない行がある場合の扱いは §6）

### 4-5. 試験

`backend/tests/test_product_format_game_links.py`（新規・DB なし）。次の 3 本（名前もこのとおり）:

| # | 試験の名前 | 確かめること |
|---|---|---|
| 1 | `test_games_body_rejects_unknown_field` | `ProductFormatGamesUpdate(game_ids=[1], alias="x")` が `ValidationError` |
| 2 | `test_games_body_limits_length` | `game_ids` が 201 個で `ValidationError` |
| 3 | `test_response_defaults_game_ids_empty` | `ProductFormatResponse` を `game_ids` なしで作ると `[]` |

`backend/tests/test_product_format_game_links_pg.py`（新規・実 PostgreSQL）。環境の扱い・skip の条件・接続は `backend/tests/test_tcg_product_detail_pg.py` の `edit_pg` と同じにする（作品・細分類・紐づけの行の作り方も、その試験の `test_classification_change_derives_work_name_and_rejects_unknown` に倣う。紐づけ表と細分類の表が準備に無ければ §6）。作った行は後片付けで消す。次の 8 本:

| # | 試験の名前 | 確かめること |
|---|---|---|
| 1 | `test_validate_accepts_linked_and_rejects_unlinked` | 紐づけありの組は通る／無い組は `ValueError("PRODUCT_FORMAT_GAME_MISMATCH")`／`work_id=None` は通る |
| 2 | `test_format_options_include_game_ids_and_selected_inactive` | 選択肢の試験用細分類に `game_ids == [str(作品の id)]`。無効にした細分類は出ず、`selected` に渡すと出る |
| 3 | `test_detail_get_returns_confirmations_and_format_lookup` | 印を 1 行入れた商品の詳細に `product["blank_confirmations"] == ["mark"]`、`lookups` に `"product_format_id"` がある |
| 4 | `test_revision_changes_when_confirmation_changes` | 印を足す前と後で `revision` が違う |
| 5 | `test_detail_update_rejects_unlinked_format_change` | 紐づけの無い細分類に変えると 422 `PRODUCT_DETAIL_FORMAT_GAME_MISMATCH`、商品の細分類と名前は元のまま |
| 6 | `test_detail_update_keeps_unchanged_old_pair` | 紐づけの無い組を直接入れた商品で、細分類を送らずに名前だけ変える保存が通る |
| 7 | `test_replace_games_adds_and_removes_links` | `replace_product_format_games` で 2 ゲームにし、次に 1 ゲームにする → 紐づけ表がそのとおり。残した組の `alias` は消えない |
| 8 | `test_replace_games_blocks_removal_in_use` | その細分類と作品の商品がある状態で、その作品を外すと 409 `PRODUCT_FORMAT_GAME_IN_USE`、紐づけは変わらない |

### 4-6. API の形

`cd backend && ENVIRONMENT=test /private/tmp/claude-501/py312-openapi/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json` を実行し、差分をコミットする（venv が無ければ §6）。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 静的検査: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2/backend && ruff check app/services/tcg_product_master_svc.py app/services/tcg_product_detail_svc.py app/routers/tcg_product_import.py app/routers/super_admin_product_formats.py app/schemas/product_format.py tests/test_product_format_game_links.py tests/test_product_format_game_links_pg.py` が 0 件。

5-2. 試験の名前: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2 && grep -nE "^(async )?def test_" backend/tests/test_product_format_game_links.py backend/tests/test_product_format_game_links_pg.py` が 11 行で、名前が §4-5 の表のとおり。

5-3. 試験: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2/backend && python3 -m pytest tests/test_product_format_game_links.py tests/test_product_format_game_links_pg.py tests/test_product_required_fields.py tests/test_tcg_product_master.py tests/test_tcg_product_import.py tests/test_tcg_product_detail_pg.py tests/test_product_blank_confirmations_pg.py -q -p no:cacheprovider 2>&1 | tail -30` の出力。加えて `git grep -l "product-formats\|product_format" -- backend/tests` で出た既存の試験ファイルも同じ形で実行し、最後の 30 行を貼る。PG の試験は手元では skip になる。そのときは「手元では skip・CI で実行」と書く。

5-4. 差分: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2 && git diff origin/main --stat -- backend frontend migrations scripts docs | tail -15` の出力。§3 の 1〜8 と 10（とこのカード）以外のファイルが無いこと。`migrations/`・`scripts/` が 0 行であること。

5-5. SQL に利用者の文字列が入らないこと: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2 && grep -n "product_format_game_links" backend/app/services/tcg_product_master_svc.py backend/app/routers/super_admin_product_formats.py` の出力（すべてバインド変数）。

5-6. PR の CI は担当が待たない。PR を作ったら URL を報告して終える。

## 6. 分岐ごとの対処

- 作業ブランチに origin/main を取り込んで衝突した → 解消せずに BLOCKED:（衝突したファイル名を貼る）
- §2-1 の目印（関数名・`return` の行・import の行）が実物と違う → 実物の該当行を貼り、同じ意味・同じ位置に合わせて書く。同じ箇所が見つからなければ NEEDS_DECISION:
- 既存の試験が偽の DB の呼び出し回数・SQL の文字列・応答の辞書の完全一致で落ちる → 落ちた試験の名前と原文を貼る。期待値を変えてよいのは「選択肢に `product_format_id` が増えた」「詳細に `blank_confirmations` が増えた」「応答に `game_ids` が増えた」「照合の SELECT が 1 回増えた」による差だけ。ほかは BLOCKED:
- PG の試験の準備に `product_formats`・`product_format_game_links`・`product_blank_confirmations` の表が無い → `tests.rls_bootstrap` の `_apply_migration` で `migrations/20260922_030000_product_format_game_links.sql` など作成の migration を当てる（`test_product_blank_confirmations_pg.py` の `_setup` と同じ形）。それでも作れなければ BLOCKED:
- §4-4 の products の SELECT が RLS でテナント商品を見られず、試験 pg-8 がテナント商品の作り方でしか確かめられない → 共用商品（`tenant_id` が NULL）で試験を書き、その旨を報告に書く（コードは変えない）
- `/private/tmp/claude-501/py312-openapi/bin/python` が無い → `ls -1d /private/tmp/claude-501/py312-openapi` の出力を貼って BLOCKED:（3.12 以外の Python で作らない）
- 循環 import で起動できない → `tcg_product_detail_svc.py` の import を関数の中に移す。それでも直らなければ BLOCKED:

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 細分類は、紐づけに無いゲームとの組み合わせでは新規登録も詳細保存も通らない | CI の pytest（pg-1・pg-5） |
| 変えていない古い組み合わせは、ほかの項目の保存を止めない | CI の pytest（pg-6） |
| 3つの選択肢の口が細分類と紐づくゲームの id を返す | CI の pytest（pg-2・pg-3）と §8 の本番確認 |
| 詳細が印を返し、印が変わると revision が変わる | CI の pytest（pg-3・pg-4） |
| 細分類マスタで使えるゲームを置き換えられ、使用中の組み合わせは外せない | CI の pytest（pg-7・pg-8） |
| 入力の形が違う置き換えは拒む | CI の pytest（1・2） |
| migration・本番データの変更が無い | §5-4 |

## 8. 反映の前後（Opus が行う。担当はしない）

- CI の緑を確かめ、差分を審査し、「確認済み」のコメントを残してマージ → deploy の成功を Actions の記録で確かめる
- 本番を読むだけで確かめる: 紐づけ表の行数が 69 のまま（この便は値を入れない）
- 生出力は /tmp/CC報告ファイル/master-required-fields/bin2a/ に置く

## 9. 戻し方

- この PR の revert を main にマージ（API は元の形に戻る。表もデータも変えていない）

## 10. PR

手順1 作業場所を確かめ、origin/main を取り込む（既存ブランチ。new-worktree.sh は使わない）
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2 && ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2 && git worktree list | grep -c release-master-register-required-fields-bin2
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2 && git fetch -q origin && git status -sb | head -5 && git merge --no-edit origin/main 2>&1 | tail -5
期待する出力 merge が成功（または Already up to date）。`git status` に design.md の変更とこのカードの未追跡が出る（Opus が書いたもの。消さない）

手順2 §4 を Write/Edit ツールで実装し、§5-1〜5-5 を実行する

手順3 commit と push（ブランチはまだ origin に無いので最初の push で上流を付ける）
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2 && git add backend/app/services/tcg_product_master_svc.py backend/app/services/tcg_product_detail_svc.py backend/app/routers/tcg_product_import.py backend/app/routers/super_admin_product_formats.py backend/app/schemas/product_format.py backend/tests/test_product_format_game_links.py backend/tests/test_product_format_game_links_pg.py frontend/api-contract/openapi.json docs/handoff/master-register-required-fields/card-bin2a.md docs/handoff/master-register-required-fields/design.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2 && PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH" git commit -m "feat: ADR-1020便2a 細分類の選択肢・ゲームとの照合・印の返却"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2 && git push -q -u origin release/master-register-required-fields-bin2 && git log -1 --oneline && git log origin/release/master-register-required-fields-bin2 -1 --oneline
期待する出力 2 つの git log が同じハッシュ

手順4 PR を作る
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2 && gh auth status 2>&1 | grep -c "Active account: true"

- 名義が `shingo-cc` であることを確かめる
- 本文は Write ツールで英字だけのパスのファイル（/private/tmp/claude-501/bin2a-pr-body.md）に作り、`scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめる（2 分以上かかるので timeout を長めにする）
- PR は `scripts/gh-pr-create-safe.sh` に本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。base は main。ready で作る（下書きにしない）。担当はマージしない
- 作成後に `.pr-number` と `gh pr list --head release/master-register-required-fields-bin2 --json number` の一致を確かめる
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/master-register-required-fields/recon.md）・設計（docs/handoff/master-register-required-fields/design.md）・このカード・ADR-1020 を書く。区分は M（危険パスなし）。PO承認: に「PO 2026-10-16『y』（KGI G1〜G4・3便）」と書く
- `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし。良い例: 触るファイル: backend/app/services/tcg_product_master_svc.py, backend/app/services/tcg_product_detail_svc.py, backend/app/routers/tcg_product_import.py, backend/app/routers/super_admin_product_formats.py, backend/app/schemas/product_format.py, backend/tests/test_product_format_game_links.py, backend/tests/test_product_format_game_links_pg.py, frontend/api-contract/openapi.json, docs/handoff/master-register-required-fields/card-bin2a.md, docs/handoff/master-register-required-fields/design.md ／ 削除するファイル: には差分に削除の行があるファイルだけを書く（無ければ「なし」）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-5 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/master-required-fields/bin2a/impl/）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える
- 登録ルールのフック（master-register-rules-guard）は、Bash のコマンドに新規登録の関数名と丸かっこの組み合わせなどがあると止める。この便は商品の登録ではないので、Bash のコマンドにはその文字列を書かない（grep は関数名だけで検索する）。ack の行は書かない
- Bash のコマンドに削除の SQL の語（大文字の削除文）を書かない（危険操作のフックが止める）。ファイルの中に書くのは Write/Edit ツールで行う

## 13. 報告欄（担当が追記）

- 実装済み（§4-1〜4-6）。生出力: /tmp/CC報告ファイル/master-required-fields/bin2a/impl/
- 手元: ruff 0 件・新規試験 3 passed／PG 8 本は skip（CI で実行）・既存関連試験は通過
- 判断した点（カード §3 の外）: `backend/tests/test_tcg_product_detail_pg.py` の選択肢の集合の期待値に `product_format_id` を追加（§6 の許容差分）。`backend/tests/test_tcg_product_list_pg.py` の `create_product_schema` に紐づけ表と印の表の migration（IF NOT EXISTS）を追加（詳細の取得が両表を読むため）

END OF CARD
