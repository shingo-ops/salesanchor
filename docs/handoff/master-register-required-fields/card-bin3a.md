<!-- rules-ack: 607cd6e7 -->
# 実装カード 便3a — 共用商品の9項目が足りないとき、新規登録と「空に戻す」更新をバックエンドで止める（ADR-1020）

> この文書は何か：共用商品マスタの9項目必須化（ADR-1020）の便3aの作業指示書です。新規登録の全入口（`create_product` を通る3つの口と CSV 取り込み）で足りない項目があれば 422 で止め、足りない項目名を全部返します。既存商品の更新（詳細保存・往復 CSV）は「値か印のあった項目を、印なしの空にする」ときだけ止めます。古い空欄は止めません。画面のドロワー側の表示は便3b で行います（この便では CSV 取り込み画面の文言だけ足します）。

- 設計: docs/handoff/master-register-required-fields/design.md:76-78（便3 止める）・:88（足りない項目名を全部出す）・:96-98（V1〜V3）。ADR-1020:29-38（既存商品は「値または記録がある項目を記録なしの空に戻す」ときだけ止める・5つの入口）。KGI と3便は PO 承認 2026-10-16「y」
- 前提の便: 便2c（#4417）が main にマージ済み。§10 手順1 で確かめる
- 対象ADR: ADR-1020（本テーマ）、ADR-027（i18n。文言は `t()` だけ・ja/en 同じキー）
- 状態: 設計は Opus 自己審査 APPROVE。§2-2 の細部は Opus の技術判断（設計の目的・範囲は変えない）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。担当はマージしない
- 担当: 実装 Sonnet／コード審査・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（下書きにしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（バックエンドで止める＋CSV 画面の文言だけ） |
| 5 | 起点と作業場所を明示 | ○（§10 手順1） |
| 6 | 書式は実例で示した | ○（§4 に完成形のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（origin/main b9980e8f1 の実物と便2c #4417 の差分。/tmp/CC報告ファイル/master-required-fields/bin3/recon/） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない | ○ |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | 新しい作業場所は `scripts/new-worktree.sh` で作る | ○（§10 手順1） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh`。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | 本番には触らない | ○（§8） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード ADR-1020 便3a の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `backend/app/services/tcg_product_master_svc.py`: 共通の関数2つ（`missing_for_create`・`find_cleared_fields`）を足し、`create_product` の最初で止める（§4-1）
2. `backend/app/services/tcg_product_detail_svc.py`: 詳細保存で「空に戻す」を止める（§4-2）
3. `backend/app/services/tcg_product_import_svc.py`: 取り込みの検査で足りない項目を止める理由に出す。旧10列の見出しの受け付けをやめる（§4-3）
4. `backend/app/services/tcg_product_roundtrip_svc.py`: 往復の更新で「空に戻す」を止める（§4-4）
5. `frontend/src/features/tcg-product-import/importMessages.ts`・`frontend/src/locales/ja.json`・`en.json`: CSV 取り込み画面の止める理由の文言（§4-5）
6. 既存の試験の直しと新しい試験（§4-6）
7. このカードを `docs/handoff/master-register-required-fields/card-bin3a.md` に置く

入れない:
- 商品詳細ドロワー・解析レビューの登録ドロワーの表示（便3b）
- ルーター（`backend/app/routers/`）。どの口も `ValueError`／`ProductDetailError` を 422 にする既存の変換をそのまま使う（recon: routers/tcg_product_master.py:264-265、routers/tcg_product_import.py:321-322・:424-425）
- DB の表、migration、本番のデータ

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main b9980e8f1＋便2c #4417。/tmp/CC報告ファイル/master-required-fields/bin3/recon/ に写し）
- products を INSERT するアプリのコードは `create_product`（tcg_product_master_svc.py:453、INSERT は :528）の1か所だけ。呼ぶのは POST /tcg/products（routers/tcg_product_master.py:245）、POST /tcg/products/create（routers/tcg_product_import.py:405）、CSV 取り込みの `commit_import`（tcg_product_import_svc.py の `create_product(db, force=True, commit=False, ...)`）
- `create_product` は今、足りない項目をログに出すだけ（:570-572 `logger.info("[ADR-1020] ...")`）。止めていない
- 本番の products は 1411 行すべて tenant_id が NULL（共用）。tenant_id 列は NULL 可・既定値なし（/tmp/CC報告ファイル/master-required-fields/bin3/prod/tenant-col.txt）
- 詳細保存 `update_product_detail`（tcg_product_detail_svc.py:125）は、UPDATE（:188）の前に分類の検査、後に印の保存（:214-221）。失敗は全部 rollback（:255-257）。`before["product"]` は `row_to_json(p)`（:55）なので列名（name・name_en・mark・release_date・work_id・product_format_id・product_category_id・tenant_id）で値が取れる。`before["search_keywords"]`・`before["exclude_keywords"]` は行の一覧（`keyword` キー）、`before["blank_confirmations"]` は項目名の一覧
- 往復の更新 `inspect_update`（tcg_product_roundtrip_svc.py）は行ごとに `errors`（=`item["blocking"]`）へ止める理由を足す。便2c で `plan["marks"]`（印を変えるときの集合、変えないなら None）と `plan["blank_values"]` が入った
- 検査関数 `check_required_fields(values, blank_confirmations)`（tcg_product_master_svc.py:58）は REQUIRED_FIELDS の順で足りない項目名を返す。検索ワード・除外ワードは文字列（カンマ区切り）でも一覧でもよい

### 2-2. 設計の細部（Opus の技術判断）
- D1 新規登録は `create_product` の最初（DB を読む前）で止める。こうすると3つの口・CSV・登録台本が全部同じ1か所で止まる（ADR-1020 What 4）。例外は `ValueError("REQUIRED_FIELDS_MISSING:" + ",".join(missing))`。ルーターの既存変換で 422・`detail` はこの文字列になる
- D2 既存商品の更新は「前は足りていた（値か印があった）項目が、後で足りない」ものだけを止める。前も後も足りない項目（古い空欄）は止めない（ADR-1020:29-31）。判定は `find_cleared_fields` の1か所で行い、詳細保存と往復が同じ関数を使う
- D3 判定は共用商品（`tenant_id` が None）だけ。tenant の商品は今0行だが、ADR-1020 の対象外なので止めない
- D4 詳細保存の例外は `ProductDetailError(422, "REQUIRED_FIELDS_CLEARED:" + ",".join(cleared))`。UPDATE の前に判定する
- D5 CSV 取り込みは、検査（preview）の段で行ごとに `REQUIRED_FIELD_MISSING_` ＋ CSV の列名 を止める理由に足す。列名で返すのは、CSV を直す人が見るのは列名だから（`blank_confirmed` にも同じ列名を書く・便2c）。確定（commit）は preview をやり直すので同じく止まり、万一すり抜けても `create_product` が止める
- D6 往復の更新は行ごとに `REQUIRED_FIELD_CLEARED_` ＋ CSV の列名 を止める理由に足す
- D7 旧10列の見出しの受け付けをやめる（design.md:73「新列を必須にするのは便3」）。旧10列には細分類の列が無く、全行が止まるだけなので、見出しで分かりやすく止める
- D8 項目名 → CSV の列名の対応は1か所（`tcg_product_import_svc.py` の `REQUIRED_FIELD_CSV_COLUMNS`）に置き、往復はそれを import する

## 3. 触るファイル

| # | ファイル | 何をするか |
|---|---|---|
| 1 | backend/app/services/tcg_product_master_svc.py | §4-1 |
| 2 | backend/app/services/tcg_product_detail_svc.py | §4-2 |
| 3 | backend/app/services/tcg_product_import_svc.py | §4-3 |
| 4 | backend/app/services/tcg_product_roundtrip_svc.py | §4-4 |
| 5 | frontend/src/features/tcg-product-import/importMessages.ts | §4-5 |
| 6 | frontend/src/locales/ja.json | §4-5 |
| 7 | frontend/src/locales/en.json | §4-5 |
| 8 | backend/tests/test_product_required_fields.py | §4-6 新しい試験 |
| 9 | §4-6 の表にある既存の試験ファイル | §4-6 直し |
| 10 | docs/handoff/master-register-required-fields/card-bin3a.md | このカード |

## 4. 実装

### 4-1. `tcg_product_master_svc.py`

`check_required_fields` の直後に足す:

```python
def missing_for_create(args: dict[str, Any]) -> list[str]:
    """ADR-1020 便3: create_product の引数（名前は create_product と同じ）から、足りない項目名を返す。"""
    values = {
        "name": args.get("japanese_title"),
        "name_en": args.get("english_title"),
        "mark": args.get("mark"),
        "release_date": args.get("release_date"),
        "search_keywords": args.get("search_keywords"),
        "exclude_keywords": args.get("exclude_keywords"),
        "work_id": args.get("work_id"),
        "product_format_id": args.get("product_format_id"),
        "product_category_id": args.get("product_category_id"),
    }
    return check_required_fields(values, set(args.get("blank_confirmations") or []))


def find_cleared_fields(
    before: dict[str, Any], before_marks: Any, after: dict[str, Any], after_marks: Any,
) -> list[str]:
    """ADR-1020 便3: 前は足りていた（値か印があった）のに、後で足りなくなった項目名を返す。

    前も後も足りない項目（古い空欄）は返さない。before / after のキーは REQUIRED_FIELDS の名前。
    """
    was_missing = set(check_required_fields(before, set(before_marks or [])))
    return [f for f in check_required_fields(after, set(after_marks or [])) if f not in was_missing]
```

`create_product` の docstring の直後、`try: _work_id_int ...` の前に足す:

```python
    # ADR-1020 便3: 足りない項目があれば DB を読む前に止める（全入口がここを通る）
    missing = missing_for_create({
        "japanese_title": japanese_title, "english_title": english_title, "mark": mark,
        "release_date": release_date, "search_keywords": search_keywords,
        "exclude_keywords": exclude_keywords, "work_id": work_id,
        "product_format_id": product_format_id, "product_category_id": product_category_id,
        "blank_confirmations": blank_confirmations,
    })
    if missing:
        raise ValueError("REQUIRED_FIELDS_MISSING:" + ",".join(missing))
```

`create_product` の後ろの、足りない項目をログに出す3行（`missing = check_required_fields(filled_values, confirmed)` と `if missing:` と `logger.info("[ADR-1020] product %s registered without required fields: %s", ...)`）は消す（止めるようになったので到達しない）。`confirmed`・`filled_values`・印の保存（`if confirmed: await save_blank_confirmations(...)`）は残す。

### 4-2. `tcg_product_detail_svc.py`

import に `find_cleared_fields` を足す（`from app.services.tcg_product_master_svc import (...)` の中）。

`update_product_detail` の、分類の検査ループ（`for field, table in PUBLIC_INTEGER_LOOKUPS.items():`）の後、`await db.execute(text("SET LOCAL app.is_operator = 'true'"))` の前に足す:

```python
        # ADR-1020 便3: 値か印のあった項目を、印なしの空にする保存だけ止める（古い空欄は止めない）
        if product.get("tenant_id") is None:
            before_marks = list(before.get("blank_confirmations") or [])
            after_marks = (
                values["blank_confirmations"] if values.get("blank_confirmations") is not None else before_marks
            )
            cleared = find_cleared_fields(
                {
                    "name": product.get("name"), "name_en": product.get("name_en"),
                    "mark": product.get("mark"), "release_date": product.get("release_date"),
                    "search_keywords": [row["keyword"] for row in before["search_keywords"]],
                    "exclude_keywords": [row["keyword"] for row in before["exclude_keywords"]],
                    "work_id": product.get("work_id"),
                    "product_format_id": product.get("product_format_id"),
                    "product_category_id": product.get("product_category_id"),
                },
                before_marks,
                {
                    "name": values.get("japanese_title"), "name_en": params["english_title"],
                    "mark": params["mark"], "release_date": params["release_date"],
                    "search_keywords": values["search_keywords"],
                    "exclude_keywords": values["exclude_keywords"],
                    "work_id": params["work_id"],
                    "product_format_id": (
                        values["product_format_id"] if "product_format_id" in values
                        else product.get("product_format_id")
                    ),
                    "product_category_id": values.get("product_category_id"),
                },
                after_marks,
            )
            if cleared:
                raise ProductDetailError(422, "REQUIRED_FIELDS_CLEARED:" + ",".join(cleared))
```

（`values` のキー名 `japanese_title`・`product_category_id`・`search_keywords`・`exclude_keywords` は実物の `ProductDetailUpdate`（routers/tcg_product_import.py:276-291）と UPDATE 文の束縛名で確かめる。違えば §6）

### 4-3. `tcg_product_import_svc.py`

1. 旧10列の受け付けをやめる（D7）: `LEGACY_CSV_COLUMNS` の定義と、`parse_rows` の `elif header == LEGACY_CSV_COLUMNS:` の分岐を消し、見出しは `CSV_COLUMNS` と一致したときだけ通す。`columns` 変数は `CSV_COLUMNS` だけになるので、便2c の前の形（`header != CSV_COLUMNS` なら `CSV_HEADER_MISMATCH`、行は `CSV_COLUMNS` で読む）に戻してよい。モジュール先頭の docstring の「旧10列の見出しも受け付け、無い2列は空として扱う」を消す。
2. 項目名 → CSV の列名（D8）。`BLANK_CONFIRMED_COLUMNS` の直後に足す:

```python
# ADR-1020 便3: 必須9項目の名前 → CSV の列名（止める理由に列名で出す。往復も使う）
REQUIRED_FIELD_CSV_COLUMNS: dict[str, str] = {
    "name": "japanese_title",
    "name_en": "english_title",
    "mark": "mark",
    "release_date": "release_date",
    "search_keywords": "search_keywords",
    "exclude_keywords": "exclude_keywords",
    "work_id": "work_code",
    "product_format_id": "product_format_code",
    "product_category_id": "product_category_code",
}
```

3. `preview` の、`payload = build_payload(row, lookups)` の直後（便2c の細分類と作品の照合の前）に足す:

```python
            # ADR-1020 便3: 足りない項目を列名で止める（create_product と同じ判定）
            from app.services.tcg_product_master_svc import missing_for_create

            checked["blocking"].extend(
                "REQUIRED_FIELD_MISSING_" + REQUIRED_FIELD_CSV_COLUMNS[f] for f in missing_for_create(payload)
            )
```

（`build_payload` が返すキーが `missing_for_create` の読む名前（`japanese_title`・`english_title`・`mark`・`release_date`・`search_keywords`・`exclude_keywords`・`work_id`・`product_format_id`・`product_category_id`・`blank_confirmations`）と同じであることを実物で確かめる。違えば §6）

4. `japanese_title` が空の行はすでに `JAPANESE_TITLE_REQUIRED` で止まり `build_payload` まで来ない。重ねて出さなくてよい。

### 4-4. `tcg_product_roundtrip_svc.py`

1. import に `REQUIRED_FIELD_CSV_COLUMNS` を足す（`from app.services.tcg_product_import_svc import (...)`）。`find_cleared_fields` は `from app.services.tcg_product_master_svc import ...` の行に足す。
2. `inspect_update` の、便2c の細分類と作品の照合（`if not errors and ("product_format_id" in plan["sets"] or "work_id" in plan["sets"]):` のかたまり）の後、`plan["blank_values"] = {...}` の前に足す:

```python
            # ADR-1020 便3: 値か印のあった項目を、印なしの空にする更新だけ止める
            product = snapshot["product"]
            if product.get("tenant_id") is None:
                before_marks = list(snapshot.get("blank_confirmed") or [])
                cleared = find_cleared_fields(
                    {
                        "name": product.get("name"), "name_en": product.get("name_en"),
                        "mark": product.get("mark"), "release_date": product.get("release_date"),
                        "search_keywords": [w["keyword"] for w in snapshot["search_keywords"]],
                        "exclude_keywords": [w["keyword"] for w in snapshot["exclude_keywords"]],
                        "work_id": product.get("work_id"),
                        "product_format_id": product.get("product_format_id"),
                        "product_category_id": product.get("product_category_id"),
                    },
                    before_marks,
                    {
                        "name": row["japanese_title"], "name_en": row["english_title"],
                        "mark": row["mark"], "release_date": row["release_date"],
                        "search_keywords": plan["words"].get(
                            "search_keywords", [w["keyword"] for w in snapshot["search_keywords"]]
                        ),
                        "exclude_keywords": plan["words"].get(
                            "exclude_keywords", [w["keyword"] for w in snapshot["exclude_keywords"]]
                        ),
                        "work_id": plan["sets"].get("work_id", product.get("work_id")),
                        "product_format_id": plan["sets"].get("product_format_id", product.get("product_format_id")),
                        "product_category_id": plan["sets"].get(
                            "product_category_id", product.get("product_category_id")
                        ),
                    },
                    plan["marks"] if plan["marks"] is not None else before_marks,
                )
                errors.extend("REQUIRED_FIELD_CLEARED_" + REQUIRED_FIELD_CSV_COLUMNS[f] for f in cleared)
```

（`snapshot["product"]` に `tenant_id`・`name`・`name_en`・`product_format_id`・`product_category_id` が入っていること、`plan["sets"]` で作品と商品区分のキーが `work_id`・`product_category_id` であること（`LOOKUP_ARGS` の値）を実物で確かめる。違えば同じ意味の名前に合わせ、§6 のとおり報告に書く）

### 4-5. 画面の文言（CSV 取り込み画面）

`importMessages.ts` の `prefixes` に2つ足す（`BLANK_CONFIRMED_INVALID_` の次）:

```ts
    ["REQUIRED_FIELD_MISSING_", "requiredFieldMissing"],
    ["REQUIRED_FIELD_CLEARED_", "requiredFieldCleared"],
```

`ja.json` の `productCsv.messages` に（`blankConfirmedInvalid` の次）:

```json
      "requiredFieldMissing": "{{value}} が未入力です。値を入れるか、調べて存在しなかった場合は blank_confirmed にこの列名を入れてください（english_title・mark・release_date・exclude_keywords だけ）。",
      "requiredFieldCleared": "{{value}} を空にはできません。値を入れるか、調べて存在しなかった場合は blank_confirmed にこの列名を入れてください（english_title・mark・release_date・exclude_keywords だけ）。",
```

`en.json` の同じ場所に:

```json
      "requiredFieldMissing": "{{value}} is empty. Enter a value, or if you checked and it does not exist, put this column name in blank_confirmed (english_title, mark, release_date or exclude_keywords only).",
      "requiredFieldCleared": "{{value}} cannot be emptied. Enter a value, or if you checked and it does not exist, put this column name in blank_confirmed (english_title, mark, release_date or exclude_keywords only).",
```

`productCsv.format` を旧10列なしの文に戻す。ja: `"UTF-8形式・12列のCSV、2MBまで。"`、en: `"UTF-8 CSV with 12 columns, up to 2 MB."`。
`productCsv.templateRequired` を9項目の必須に合わせる。ja: `"日本語名・英語名・型番・発売日・検索キーワード・除外キーワード・作品・細分類・商品区分は必須です（英語名・型番・発売日・除外キーワードは、調べて存在しなければ blank_confirmed に列名を入れて空にできます）。大分類とメーカーのコードも必要です。分類コードには登録済みのコードを使用してください。"`、en: `"Japanese title, English title, model number, release date, search keywords, exclusion keywords, series, format and product category are required (English title, model number, release date and exclusion keywords may be left empty if you checked and they do not exist and you list the column name in blank_confirmed). Division and manufacturer codes are also needed. Use existing classification codes."`

### 4-6. 試験

新しい試験 `backend/tests/test_product_required_fields.py` に足す（既存ファイル。便1 の試験の後ろ）:
1. `test_missing_for_create_lists_all_missing_in_order`: 全部空の引数 → 9項目の名前が REQUIRED_FIELDS の順
2. `test_missing_for_create_accepts_blank_confirmations`: 英語名・型番・発売日・除外ワードが空で4つとも印あり、他は値あり → 空の一覧
3. `test_find_cleared_fields_only_newly_missing`: 前は mark に値・name_en は空で印なし → 後は mark 空・印なし、name_en 空 → `["mark"]` だけ（name_en は古い空欄なので返さない）
4. `test_find_cleared_fields_mark_keeps_blank`: 前は exclude_keywords に値 → 後は空で印 exclude_keywords あり → 空の一覧
5. `test_create_product_rejects_missing_before_db`: 偽の db（`AsyncMock`）で `create_product` を、細分類なし・英語名なしで呼ぶ → `ValueError` の文が `REQUIRED_FIELDS_MISSING:name_en,` で始まり `product_format_id` を含む。偽 db の `execute` が一度も呼ばれていない

既存の試験に足す:
6. `backend/tests/test_tcg_product_import.py` に `test_preview_blocks_missing_required_with_column_names`: 細分類コードが空・英語名が空で印なしの行 → `blocking` に `REQUIRED_FIELD_MISSING_english_title` と `REQUIRED_FIELD_MISSING_product_format_code`。同じ行に `blank_confirmed=english_title` と細分類コードを入れると、その2つが消える（既存の preview 試験の偽 db の作り方に合わせる）
7. `backend/tests/test_tcg_product_import.py`: 旧10列の見出しを受け付けていた便2c の試験は、`CSV_HEADER_MISMATCH` になることを確かめる形に直す
8. `backend/tests/test_tcg_product_detail_pg.py` に `test_clearing_value_without_mark_is_rejected`: 型番の入った共用商品の型番を、印なしで空にする保存 → `ProductDetailError` 422・文が `REQUIRED_FIELDS_CLEARED:mark`、DB の型番は変わらない。同じ保存に `blank_confirmations=["mark"]` を付けると保存でき、印の表に `mark` が1行
9. `backend/tests/test_tcg_product_roundtrip.py` に `test_update_blocks_clearing_required_field`: 除外ワードのある商品の往復で除外ワードを空にし、`blank_confirmed` は空 → `blocking` に `REQUIRED_FIELD_CLEARED_exclude_keywords`。`blank_confirmed=exclude_keywords` を入れると止まらない（既存の inspect_update 試験の偽 db の作り方に合わせる）

便3で壊れうる既存の試験（recon §7。直すときは試験の意図を変えず、足りない項目を埋めるか印を付ける。止める判定が正しく働いた結果の失敗だけを直す）:

| ファイル:行 | 何が足りないか | 直し方 |
|---|---|---|
| backend/tests/test_tcg_completion_safety.py:163-165 | name_en・mark・release_date・exclude_keywords・product_format_id | 実在する細分類（作品に紐づくもの）を渡す。英語名・型番・発売日・除外ワードは値か印。土台の DB に細分類と紐づけが無ければ §6 |
| backend/tests/test_tcg_product_code_collision_wiring.py:54-58 | name_en・release_date・product_format_id | 値を足す（偽 db） |
| backend/tests/test_tcg_product_import.py:361-372 | name_en・mark・release_date・product_format_id | 値を足す（偽 db） |
| backend/tests/test_tcg_product_import_atomicity_pg.py（csv_input :25-33・:265） | 44商品すべて english_title・release_date・product_format_code | 値を入れるか `blank_confirmed` に列名。細分類コードは土台の DB にある作品に紐づくもの。無ければ §6 |
| backend/tests/test_tcg_product_detail_pg.py:178・:278 | 除外ワードを印なしで空にする | `blank_confirmations=["exclude_keywords"]` を付ける（試験の意図が「空にできること」でないなら別の語に変える） |
| backend/tests/test_tcg_product_detail_pg.py:408 | 検索ワードを空にする | 検索ワードは印で空にできない。試験が見たいもの（語の差し替えなど）を読み、空でない別の語に変える。意図が「空にできること」なら §6 |
| backend/tests/test_tcg_product_roundtrip_pg.py:109-131 | 往復で除外ワードを空にする | changes に `blank_confirmed` の `exclude_keywords` を足す |

上の表以外で落ちた試験は、落ちた原文と「止める判定が正しく働いた結果か」を報告に書き、正しく働いた結果なら同じ方針で直す。そうでなければ直さずに NEEDS_DECISION:。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. バックエンドの試験: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a/backend && /private/tmp/claude-501/py312-bin2c/bin/python -m pytest tests/test_product_required_fields.py tests/test_tcg_product_import.py tests/test_tcg_product_roundtrip.py tests/test_tcg_product_code_collision_wiring.py tests/test_tcg_schema_qualification.py tests/test_tcg_product_master.py -q -p no:cacheprovider --no-cov 2>&1 | tail -20` が全部合格（`_pg` の試験は手元に PostgreSQL が無ければ skip でよい。CI で確かめる）。

5-2. 試験の名前: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a && git diff origin/main -- backend/tests | grep -nE "^\+\s*(async def test_|def test_)" | head -20` の出力（新しい試験 9 個の名前が §4-6 のとおり。直した試験は名前が変わらないので出ない）。

5-3. 止める箇所の数: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a && git grep -n "REQUIRED_FIELDS_MISSING\|REQUIRED_FIELDS_CLEARED\|REQUIRED_FIELD_MISSING_\|REQUIRED_FIELD_CLEARED_" -- backend/app frontend/src | head -20`（backend/app に4か所: create_product・詳細保存・取り込みの preview・往復。frontend/src に importMessages.ts の2か所）。

5-4. 画面の試験・型・lint: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/tcg-product-import/ 2>&1 | tail -15` が合格、`npx tsc --noEmit -p tsconfig.json 2>&1 | tail -10` と `npx eslint src/features/tcg-product-import/importMessages.ts 2>&1 | tail -10` がエラー 0（`src/api/generated/schema.d.ts` が無くて落ちるときは、先に `npm run generate:api-types 2>&1 | tail -3`。生成物はコミットしない）。

5-5. i18n: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a/frontend && npm run check:i18n-missing-keys 2>&1 | tail -10` が合格。

5-6. 差分: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a && git diff origin/main --stat | tail -20` が §3 のファイルだけ。

5-7. PR の CI は担当が待たない。PR を作ったら URL を報告して終える。

## 6. 分岐ごとの対処

- §10 手順1 で origin/main の `backend/app/services/tcg_product_import_svc.py` に `blank_confirmed` の文字が無い → BLOCKED:（便2c が入っていない。作業を始めない）
- §4 の目印や引数・キーの名前が実物と違う → 実物の該当行を貼り、同じ意味・同じ位置に合わせて書く。見つからなければ NEEDS_DECISION:
- 実 DB の試験（`_pg`）の土台に、試験で使う作品に紐づく細分類が無い → 試験の中で `public.product_formats` と `public.product_format_game_links` に試験用の行を作る（その試験ファイルの既存の作り方に合わせる）。共通の土台（conftest 等）を変える必要があれば NEEDS_DECISION:
- `/private/tmp/claude-501/py312-bin2c/bin/python -m pytest --version` が失敗 → 出力を貼り「手元では未実行・CI で実行」と書いて続ける（3.12 以外の Python で作らない）
- husky や CI の自動検査が落ちる → 検査名と原文を貼る。迂回（`--no-verify` など）しない

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| V2 新規登録の全入口で、足りない項目があると 422 と項目名が全部返る | 試験 1・5（create_product＝3つの口と CSV の確定が通る1か所）・6（CSV の検査） |
| 印のある4項目は空でも登録できる | 試験 2・6 |
| V3 詳細保存で、値のあった項目を印なしで空にすると 422、印ありなら保存できる | 試験 3・8 |
| 古い空欄は止めない | 試験 3 |
| 往復の更新でも同じ | 試験 4・9 |
| 旧10列の CSV は見出しで止まる | 試験 7 |
| 文言は ja/en 同じキー | §5-5 |

## 8. 反映の前後（Opus が行う。担当はしない）

- CI の緑を確かめ、差分を審査し、「確認済み」のコメントを残してマージ → deploy の成功を Actions の記録で確かめる
- 反映の前に、紐づけの無いゲーム（8981・8982）の扱いを PO に確かめる（design.md:74・:88）
- 反映後、本番の HEAD がマージ commit と一致すること、本番の画面 JS に `cannot be emptied` が入っていること、未ログインの POST /api/v1/tcg/products が 401 のままであることを読み取りで確かめる。V1（新規共用商品で空かつ印なしが0件）は反映時刻以降の新規行を本番 SELECT で数える
- 生出力は /tmp/CC報告ファイル/master-required-fields/bin3/ に置く

## 9. 戻し方

- この PR の revert を main にマージ（止める判定がログだけに戻る。DB の表は変えていない）

## 10. PR

手順1 前提が main にあることを確かめ、新しい作業場所を作る
    cd /Users/tanizawashingo/salesanchor && git fetch -q origin && git grep -c "blank_confirmed" origin/main -- backend/app/services/tcg_product_import_svc.py
期待する出力 1 以上（0 なら §6 の1つ目）
    cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/master-register-required-fields-bin3a --claude 2>&1 | tail -5
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a && git status -sb | head -3 && git log -1 --oneline
期待する出力 作業場所が origin/main の先頭から作られている。以下のコマンドの作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a
    このカードを /tmp/CC報告ファイル/master-required-fields/bin3/card-bin3a.md から Read し、Write ツールで `/Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a/docs/handoff/master-register-required-fields/card-bin3a.md` に同じ内容で置く。`cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a/frontend && ls node_modules | head -1` で依存が無ければ `npm ci 2>&1 | tail -5`

手順2 §4 を Write/Edit ツールで実装し、§5-1〜5-6 を実行する

手順3 commit と push
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a && git add backend/app/services backend/tests frontend/src/features/tcg-product-import/importMessages.ts frontend/src/locales/ja.json frontend/src/locales/en.json docs/handoff/master-register-required-fields/card-bin3a.md && git status -s | head -30
期待する出力 §3 のファイルだけが追加されている（それ以外が出たら git restore --staged で外す）
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a && git commit -m "feat: ADR-1020便3a 共用商品の必須9項目が足りない登録と空に戻す更新を止める"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a && git push -q -u origin release/master-register-required-fields-bin3a && git log -1 --oneline && git log origin/release/master-register-required-fields-bin3a -1 --oneline
期待する出力 2 つの git log が同じハッシュ

手順4 PR を作る
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3a && gh auth status 2>&1 | grep -c "Active account: true"

- 名義が `shingo-cc` であることを確かめる
- 本文は Write ツールで英字だけのパスのファイル（/private/tmp/claude-501/bin3a-pr-body.md）に作り、作業場所に cd してから `scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめる（2 分以上かかるので timeout を長めにする）
- PR は `scripts/gh-pr-create-safe.sh` に本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。base は main。ready で作る（下書きにしない）。担当はマージしない
- 作成後に `.pr-number` と `gh pr list --head release/master-register-required-fields-bin3a --json number` の一致を確かめる
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/master-register-required-fields/recon.md）・設計（docs/handoff/master-register-required-fields/design.md）・このカード・ADR-1020・ADR-027 を書く。区分は M（危険パスなし）。PO承認: に「PO 2026-10-16『y』（KGI G1〜G4・3便）、PO 2026-10-17 チャット『PRマージ、デプロイまで完走させてくれ』（本セッション＝ADR-1020 便2〜便3）」と書く。validate-pr-body.sh が「設計docに参照がない」と ADR を指摘したら、その ADR だけを `対象ADR` から外し、外したことを報告に書く
- `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし。触るファイル: は実際に変えた全ファイル（`git diff origin/main --name-only` と一致させる）。削除するファイル: は既存行を変えた全ファイル（新しく作ったカードの md を除く）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-6 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/master-required-fields/bin3/impl/）／§4-6 の表の各試験をどう直したか（ファイル:行と直した内容）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える
- 登録ルールのフック（master-register-rules-guard）に止められたら、言い換えずに報告して終える。ack の行は書かない
- Bash のコマンドに削除の SQL の語（大文字の削除文）を書かない

## 13. 報告欄（担当が追記）

（未記入）

END OF CARD
