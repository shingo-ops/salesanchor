<!-- rules-ack: 607cd6e7 -->
# 実装カード 便2c — 商品マスタの CSV（新規取り込み・往復の更新）に細分類と「調べたが存在しない」の印を足す（ADR-1020）

> この文書は何か：共用商品マスタの9項目必須化（ADR-1020）の便2cの作業指示書です。CSV で商品を新しく取り込む口と、書き出した CSV を直して戻す口（往復）の2つに、列 `product_format_code`（細分類のコード）と `blank_confirmed`（調べたが存在しなかった列の名前をカンマで区切る）を足します。新規の取り込みは今までの10列の CSV も受け付けたままにします。保存はまだ止めません（止めるのは便3）。

- 設計: docs/handoff/master-register-required-fields/design.md:67（CSV の列）・:73（便2c。旧10列も受け付け、新列の必須化は便3。往復・説明・テンプレートも直す）。KGI と3便は PO 承認 2026-10-16「y」
- 前提の便: 便2a（#4412）・便2b-1（#4414）・便2b-2（#4415）・便2b-3（#4416）が main にマージ済み。§10 手順1 で確かめる
- 対象ADR: ADR-1020（本テーマ）、ADR-027（i18n。文言は `t()` だけ・ja/en 同じキー）、ADR-155（共用商品の正規の更新は CSV と画面）
- 状態: 設計は Opus 自己審査 APPROVE。§2-2 の細部は Opus の技術判断（設計の目的・範囲は変えない）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。担当はマージしない
- 担当: 実装 Sonnet／コード審査・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（下書きにしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（CSV の2つの口だけ） |
| 5 | 起点と作業場所を明示 | ○（§10 手順1） |
| 6 | 書式は実例で示した | ○（§4 に完成形のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（origin/main 7eeae7b4f の実物。b9980e8f1 で CSV の2ファイルは変わっていない） |
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

作業を始める前に、報告の冒頭へ「本報告はカード ADR-1020 便2c の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `backend/app/services/tcg_product_import_svc.py`: 12列（旧10列も可）・細分類コードの引き当て・印の読み取り・作品との照合（§4-1）
2. `backend/app/services/tcg_product_roundtrip_svc.py`: 書き出しと更新に2列を足す（§4-2）
3. 試験: `backend/tests/test_tcg_product_import.py`・`backend/tests/test_tcg_product_roundtrip.py`・`backend/tests/test_tcg_product_import_atomicity_pg.py`（必要なら `backend/tests/test_tcg_product_roundtrip_pg.py`）（§4-4）
4. `frontend/public/templates/tcg-product-import-template.csv`: 見出しを12列に（§4-3）
5. `frontend/src/features/tcg-product-import/importMessages.ts`: 新しい3つの止める理由の文言（§4-3）
6. `frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx`: 列数 10→12（§4-4）
7. `frontend/src/locales/ja.json`・`en.json`: 文言（§4-3）
8. このカードを `docs/handoff/master-register-required-fields/card-bin2c.md` に置く

入れない:
- 保存を止めること（便3）。足りない項目があっても取り込み・更新は今までどおり通す
- `backend/app/services/tcg_product_master_svc.py`（`create_product`・`save_blank_confirmations`・`format_matches_game` は呼ぶだけ。変えない）
- `backend/app/routers/tcg_product_import.py`、`TcgProductImportPanel.tsx`・`TcgProductImportPreview.tsx`（文言は i18n のキーの中身だけ変える）
- 商品詳細・解析レビューの画面、DB の表、migration

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 7eeae7b4f。/tmp/CC報告ファイル/master-required-fields/bin2c/recon/ に写し）

- 新規取り込み `backend/app/services/tcg_product_import_svc.py`
  - `CSV_COLUMNS` :43-54 は10列。`parse_rows` :134-165 は見出しの完全一致だけ（:150 `CSV_HEADER_MISMATCH`）、行の列数も `len(CSV_COLUMNS)` と比べる（:159）
  - `load_lookup_maps` :173-217 は作品・大分類・メーカー・商品区分のコード→id を返す。細分類は無い
  - `check_codes` :225-240 は `for column in lookups` で回し、空なら `MISSING_`、無ければ `UNKNOWN_` ＋列名＋`_`＋コードで止める
  - `validate_row_static` :243-288、`build_payload` :291-307（`create_product` に渡す引数。細分類と印が無い）
  - `preview` :358-405、`commit_import` :479-557 は `create_product(db, force=True, commit=False, actor=executed_by, **payload)`（:528）
- `backend/app/services/tcg_product_master_svc.py`（変えない）
  - `BLANK_CONFIRMABLE_FIELDS` :38 = `("name_en", "mark", "release_date", "exclude_keywords")`
  - `format_matches_game(db, product_format_id, work_id)` :76-83、`_validate_product_format` :86-99（`PRODUCT_FORMAT_INVALID`・`PRODUCT_FORMAT_GAME_MISMATCH` の `ValueError`）
  - `save_blank_confirmations(db, *, product_id, values, confirmations, actor)` :120-155。`confirmations=None` なら値の入った項目の印だけ消す。集合なら「空の項目 ∩ 集合」に置き換える
  - `create_product` :454 は `product_format_id`・`blank_confirmations` を受け、細分類を照合し（:487）、印を保存する（:559-570）
- 往復 `backend/app/services/tcg_product_roundtrip_svc.py`
  - `COLUMNS = ["product_id", "revision", *CSV_COLUMNS]`（:21）。新規の列を足すと往復の見出しも自動で変わる
  - `revision` :101-108（`"v1:"`＋商品行と語の JSON の指紋）、`snapshots` :111-140、`values` :154-166、`export_csv` :169-179
  - `inspect_update` :182-310。見出しの完全一致（:196）、差分のループ :245-284（`WORDS`・参照コード・それ以外を products の列として扱う）
  - `commit_update` :318-408。`LOCK TABLE` :327-337、`UPDATE public.products` の型変換 :365-373、`SET LOCAL app.is_operator` :375
- 本番（読み取り 2026-10-17 03:06 JST・/tmp/CC報告ファイル/master-required-fields/bin2c/prod/grants.txt）
  - `public.product_formats` は 25 行・`code` は 25 種類で重複なし・25 行とも有効。例 `BOOSTER`・`EXTRA_BOOSTER`・`STARTER_DECK`
  - アプリのロール `salesanchor_app` は `product_blank_confirmations`・`product_formats`・`product_format_game_links`・`products` に SELECT・UPDATE・DELETE の権限を持つ（`LOCK TABLE` に要る権限がある）
- 画面
  - `frontend/src/features/tcg-product-import/importMessages.ts` が止める理由のコードを文言に変える（完全一致の表・前置きの表・参照コード4つのループ）
  - `TcgProductImportPanel.test.tsx` の `blank CSV template` は、サービスの `CSV_COLUMNS` を正規表現で読み、テンプレートの見出しと一致すること・`toHaveLength(10)` を確かめる
  - テンプレート `frontend/public/templates/tcg-product-import-template.csv` は BOM＋見出し1行＋CRLF

### 2-2. 設計の細部（Opus の技術判断）

- D1 列の名前: `product_format_code`（細分類の `code`）と `blank_confirmed`。`blank_confirmed` に書くのは **CSV の列名** の `english_title`・`mark`・`release_date`・`exclude_keywords`（使う人が見ている名前）。保存のときに `english_title` → `name_en` に置き換える。順序と重複は問わず、書き出しは常にこの4つの順で出す
- D2 新規取り込みは12列の見出しと旧10列の見出しの両方を受ける。旧10列のときは2列を空として扱う（設計 :73）
- D3 細分類コードが空なら細分類なし（便2では止めない）。入っていて有効な細分類に無ければ `UNKNOWN_PRODUCT_FORMAT_CODE_` ＋コードで止める。作品に紐づかない細分類は `PRODUCT_FORMAT_GAME_MISMATCH` で止める（便2a で詳細保存と登録の口が同じ理由で 422 にしているのに揃える）
- D4 `blank_confirmed` に4つ以外の名前があれば `BLANK_CONFIRMED_INVALID_` ＋名前で止める。値の入った列の印は保存しない（`save_blank_confirmations` が外す）
- D5 往復: 書き出しに2列を足す。印は `revision` に入れ、前置きを `"v2:"` にする（印だけを他の人が変えたときも「古いファイル」で止めるため）。このため便2c より前に書き出したファイルは見出しも指紋も合わず戻せない。書き出し直してもらう（文言で案内する）
- D6 往復の更新では、行に変化があれば `save_blank_confirmations` を必ず呼ぶ（印の列が変わったときは集合、変わっていないときは `None`。値を入れた列の印が残らないようにする）。細分類か作品が変わったら、最後の組み合わせを `format_matches_game` で照合する
- D7 往復の確定では `public.product_blank_confirmations` を商品・語と同じ `SHARE ROW EXCLUSIVE` でロックし、`public.product_formats`・`public.product_format_game_links` を `SHARE` でロックする
- D8 `check_codes` は細分類を「空なら止める」対象にしない（便2では任意のため）。`load_lookup_maps` の返り値に `product_format_code` を足すので、`check_codes` で読み飛ばす

## 3. 触るファイル

1. `backend/app/services/tcg_product_import_svc.py`
2. `backend/app/services/tcg_product_roundtrip_svc.py`
3. `backend/tests/test_tcg_product_import.py`
4. `backend/tests/test_tcg_product_roundtrip.py`
5. `backend/tests/test_tcg_product_import_atomicity_pg.py`
6. `frontend/public/templates/tcg-product-import-template.csv`
7. `frontend/src/features/tcg-product-import/importMessages.ts`
8. `frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx`
9. `frontend/src/locales/ja.json`
10. `frontend/src/locales/en.json`
11. `docs/handoff/master-register-required-fields/card-bin2c.md`（新規）
12. （§6 の分岐のときだけ）`backend/tests/test_tcg_product_roundtrip_pg.py`

## 4. 実装

### 4-1. `tcg_product_import_svc.py`

(a) 先頭の説明文の「CSV の列（10列・見出し行あり）」の段を次に置き換える。

```
CSV の列（12列・見出し行あり。旧10列の見出しも受け付け、無い2列は空として扱う）:
  mark / japanese_title / english_title / release_date /
  search_keywords / exclude_keywords /
  division_code / work_code / manufacturer_code / product_category_code /
  product_format_code / blank_confirmed

product_format_code は細分類のコード（空なら細分類なし）。blank_confirmed は
「調べたが存在しない」列の名前（english_title / mark / release_date /
exclude_keywords）をカンマで区切る（ADR-1020）。
```

(b) `CSV_COLUMNS` の末尾（`"product_category_code",` の次）に `"product_format_code",` と `"blank_confirmed",` を足す。宣言は `CSV_COLUMNS: list[str] = [` の形と、閉じ `]` を行頭に置く形を変えない（画面の試験が正規表現で読む）。直後に次を足す。

```python
# ADR-1020 便2c: 便2の間は旧10列の見出しも受け付ける（無い2列は空として扱う）
LEGACY_CSV_COLUMNS: list[str] = CSV_COLUMNS[:10]

# ADR-1020: blank_confirmed に書く CSV の列名 → 印の項目名（tcg_product_master_svc.BLANK_CONFIRMABLE_FIELDS）
BLANK_CONFIRMED_COLUMNS: dict[str, str] = {
    "english_title": "name_en",
    "mark": "mark",
    "release_date": "release_date",
    "exclude_keywords": "exclude_keywords",
}

# 空でも止めないコード列（便2では任意。check_codes が読み飛ばす）
OPTIONAL_CODE_COLUMNS: frozenset[str] = frozenset({"product_format_code"})
```

(c) `split_keywords` の次に、印の読み書きを足す。

```python
def parse_blank_confirmed(value: str) -> tuple[list[str], list[str]]:
    """blank_confirmed のセルを読む。(印の項目名の一覧, 知らない名前の一覧) を返す。

    項目名は BLANK_CONFIRMED_COLUMNS の順にそろえ、重複は1つにする。
    """
    names = split_keywords(value)
    invalid = [n for n in names if n not in BLANK_CONFIRMED_COLUMNS]
    fields = [BLANK_CONFIRMED_COLUMNS[c] for c in BLANK_CONFIRMED_COLUMNS if c in names]
    return fields, invalid


def format_blank_confirmed(fields: list[str] | set[str]) -> str:
    """印の項目名を blank_confirmed のセルの形（CSV の列名をカンマで区切る）にする。"""
    return ",".join(c for c, f in BLANK_CONFIRMED_COLUMNS.items() if f in fields)
```

(d) `parse_rows` の見出しの判定と行の組み立てを次に置き換える（:149-163）。

```python
    header = [h.strip() for h in records[0]]
    if header == CSV_COLUMNS:
        columns = CSV_COLUMNS
    elif header == LEGACY_CSV_COLUMNS:
        columns = LEGACY_CSV_COLUMNS
    else:
        file_errors.append("CSV_HEADER_MISMATCH")
        return [], file_errors

    rows: list[dict[str, str]] = []
    for i, rec in enumerate(records[1:], start=1):
        if not any((c or "").strip() for c in rec):
            continue
        if len(rec) != len(columns):
            file_errors.append("CSV_COLUMN_COUNT_MISMATCH_ROW_" + str(i))
            continue
        row = {column: "" for column in CSV_COLUMNS}
        row.update({columns[j]: (rec[j] or "").strip() for j in range(len(columns))})
        row["row_no"] = str(i)
        rows.append(row)
```

(e) `load_lookup_maps` の `maps["division_code"] = pk_map` の次（`return maps` の前）に足す。docstring の Returns の例に `"product_format_code": {"BOOSTER": 1, ...}` を足す。

```python
    # ADR-1020 便2c: 細分類のコード → id（有効なものだけ。空のセルは細分類なし）
    pf_result = await db.execute(
        text("SELECT code, id FROM public.product_formats WHERE is_active = TRUE")
    )
    maps["product_format_code"] = {str(r[0]): int(r[1]) for r in pf_result.fetchall()}  # type: ignore[assignment]
```

(f) `check_codes` のループの先頭に、任意の列を読み飛ばす2行を足す。

```python
    for column in lookups:
        if column in OPTIONAL_CODE_COLUMNS:
            continue
```

(g) `validate_row_static` の `blocking.extend(check_codes(row, lookups))` の次に足す。

```python
    format_code = row.get("product_format_code", "")
    if format_code and format_code not in lookups.get("product_format_code", {}):
        blocking.append("UNKNOWN_PRODUCT_FORMAT_CODE_" + format_code)

    _, invalid_marks = parse_blank_confirmed(row.get("blank_confirmed", ""))
    blocking.extend("BLANK_CONFIRMED_INVALID_" + name for name in invalid_marks)
```

docstring の「design 5-4 の 1 2 3 5 8 9 11 を見る。」の次の行に「ADR-1020 便2c: 細分類コードと blank_confirmed も見る。」を足す。

(h) `build_payload` の `for column, arg in LOOKUP_ARGS.items():` のループの次（`return payload` の前）に足す。docstring は「create_product に渡す引数を組み立てる。使われない2つには空文字を渡す。細分類と印は ADR-1020 便2c。」にする。

```python
    format_code = row.get("product_format_code", "")
    payload["product_format_id"] = (
        lookups.get("product_format_code", {}).get(format_code) if format_code else None
    )
    payload["blank_confirmations"], _ = parse_blank_confirmed(row.get("blank_confirmed", ""))
```

(i) `preview` のループの `if not checked["blocking"]:` の塊を次に置き換える（細分類と作品の照合を、既存の動的検査の前に足す）。

```python
        if not checked["blocking"]:
            payload = build_payload(row, lookups)
            format_id = payload.get("product_format_id")
            work_id = payload.get("work_id")
            if format_id is not None and work_id:
                from app.services.tcg_product_master_svc import format_matches_game

                if not await format_matches_game(db, int(format_id), int(work_id)):
                    checked["blocking"].append("PRODUCT_FORMAT_GAME_MISMATCH")
        if not checked["blocking"]:
            checked["warnings"].extend(
                await validate_row_dynamic(db, row, payload, keyword_owners)
            )
```

`commit_import` は変えない（`build_payload` の返り値に2つの引数が増えるので、そのまま `create_product` に渡る。`create_product` 側でも細分類を照合する）。

### 4-2. `tcg_product_roundtrip_svc.py`

(a) import を次にする。

```python
from app.services.tcg_product_import_svc import (
    CSV_COLUMNS,
    LOOKUP_ARGS,
    LOOKUP_TABLES,
    format_blank_confirmed,
    parse_blank_confirmed,
)
```

`from app.services.tcg_product_code_collision_svc import find_code_collisions` の次に
`from app.services.tcg_product_master_svc import format_matches_game, save_blank_confirmations` を足す（import の循環で落ちたら §6）。

(b) `revision` を次に置き換える。

```python
def revision(snapshot: dict) -> str:
    # ADR-1020 便2c: 印も指紋に入れる（v2）。v1 で書き出したファイルは見出しも合わないため戻せない
    canonical = json.dumps(
        {
            "schema": TCG_SCHEMA,
            "product": snapshot["product"],
            **{key: snapshot[key] for key in WORDS},
            "blank_confirmed": sorted(snapshot.get("blank_confirmed") or []),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "v2:" + hashlib.sha256(canonical.encode()).hexdigest()
```

(c) `snapshots` の SQL に細分類のコードと印を足す。`references.append("'work_code', work.code")` の次に

```python
    # ADR-1020 便2c: 細分類のコード
    joins.append("LEFT JOIN public.product_formats fmt ON fmt.id=p.product_format_id")
    references.append("'product_format_code', fmt.code")
```

を足し、`keyword_sql` のループの次に

```python
    # ADR-1020 便2c: 「調べたが存在しない」の印
    keyword_sql.append(
        "COALESCE((SELECT jsonb_agg(c.field_code ORDER BY c.field_code) "
        "FROM public.product_blank_confirmations c WHERE c.product_id=p.id),'[]'::jsonb) AS blank_confirmed"
    )
```

を足す。

(d) `_ALL_REF_COLUMNS = {"work_code", *LOOKUP_TABLES}` を `_ALL_REF_COLUMNS = {"work_code", "product_format_code", *LOOKUP_TABLES}` にする。`values` のループの `if field in WORDS or field in _ALL_REF_COLUMNS:` を `if field in WORDS or field in _ALL_REF_COLUMNS or field == "blank_confirmed":` にし、`result.update({key: encode_words(...) ...})` の次に

```python
    result["blank_confirmed"] = format_blank_confirmed(snapshot.get("blank_confirmed") or [])
```

を足す。

(e) `inspect_update`
- `references` を組み立てるループの次に、細分類のコード→行を足す。

```python
    # ADR-1020 便2c: 細分類のコード → 行（有効なものだけ）
    format_result = await db.execute(text("SELECT to_jsonb(r) FROM public.product_formats r WHERE r.is_active=TRUE"))
    formats = {row[0]["code"]: row[0] for row in format_result.fetchall()}
```

- `plan: dict[str, Any] = {"row": item, "sets": {}, "words": {}}` を `{"row": item, "sets": {}, "words": {}, "marks": None}` にする。
- 差分のループの `if field in WORDS:` の **前** に、2つの分岐を足す（`if field in WORDS:` は `elif field in WORDS:` にする）。

```python
                if field == "blank_confirmed":
                    marks, invalid = parse_blank_confirmed(row[field])
                    if invalid:
                        errors.extend("BLANK_CONFIRMED_INVALID_" + name for name in invalid)
                        continue
                    if format_blank_confirmed(marks) == old[field]:
                        continue
                    plan["marks"] = set(marks)
                elif field == "product_format_code":
                    if not row[field]:
                        plan["sets"]["product_format_id"] = None
                    elif row[field] not in formats:
                        errors.append(f"UNKNOWN_PRODUCT_FORMAT_CODE_{row[field]}")
                    else:
                        plan["sets"]["product_format_id"] = formats[row[field]]["id"]
                elif field in WORDS:
```

- ループの後、`if item["changes"]:` の前に、細分類と作品の照合を足す。

```python
            if not errors and ("product_format_id" in plan["sets"] or "work_id" in plan["sets"]):
                final_format = plan["sets"].get("product_format_id", snapshot["product"].get("product_format_id"))
                final_work = plan["sets"].get("work_id", snapshot["product"].get("work_id"))
                if final_format is not None and final_work is not None and not await format_matches_game(
                    db, int(final_format), int(final_work)
                ):
                    errors.append("PRODUCT_FORMAT_GAME_MISMATCH")
            # ADR-1020 便2c: 確定のとき印を直すための、更新後の4項目
            plan["blank_values"] = {
                "name_en": row["english_title"],
                "mark": row["mark"],
                "release_date": row["release_date"],
                "exclude_keywords": plan["words"].get(
                    "exclude_keywords", [w["keyword"] for w in snapshot["exclude_keywords"]]
                ),
            }
```

(f) `commit_update`
- 1つ目の `LOCK TABLE` の表に `public.product_blank_confirmations` を足す（`"public.product_search_keywords, public.product_exclude_keywords, public.product_blank_confirmations "`）。
- 2つ目の `LOCK TABLE` の次に足す。

```python
        # ADR-1020 便2c: 細分類と作品の照合に使う表
        await db.execute(text("LOCK TABLE public.product_formats, public.product_format_game_links IN SHARE MODE"))
```

- 型変換の `if field in ("work_id", "product_category_id", "product_kind_id")` に `"product_format_id"` を足す。
- `for field, words in plan["words"].items(): ... replace_words(...)` の次に足す。

```python
            if plan["row"]["changes"]:
                await db.execute(text("SET LOCAL app.is_operator = 'true'"))
                await save_blank_confirmations(
                    db,
                    product_id=plan["id"],
                    values=plan["blank_values"],
                    confirmations=plan["marks"],
                    actor=executed_by,
                )
```

### 4-3. 画面・テンプレート・文言

(a) テンプレート: Write ツールで中身を BOM（EF BB BF）＋ `mark,japanese_title,english_title,release_date,search_keywords,exclude_keywords,division_code,work_code,manufacturer_code,product_category_code,product_format_code,blank_confirmed` ＋ CRLF にする（BOM と CRLF が Write で付かないときは `printf` を使ってよい。`od -c` で先頭3バイトと末尾 `\r\n` を確かめる）。

(b) `importMessages.ts`
- `exact` に `PRODUCT_FORMAT_GAME_MISMATCH: "formatGameMismatch",` を足す
- `prefixes` に `["BLANK_CONFIRMED_INVALID_", "blankConfirmedInvalid"],` を足す
- 参照コードのループの配列の末尾に `"PRODUCT_FORMAT_CODE"` を足す

(c) 文言（ja と en で同じキー。既存のキーは中身だけ変える）

| キー | ja | en |
|---|---|---|
| `productCsv.format`（変更） | `UTF-8形式・12列のCSV（従来の10列も可）、2MBまで。` | `UTF-8 CSV with 12 columns (the former 10 columns are also accepted), up to 2 MB.` |
| `productCsv.templateOptional`（変更） | `発売日はYYYY-MM-DD形式で入力し、不明なら空欄にします。検索・除外キーワードを複数指定する場合は、1つのセル内でカンマで区切ってください。細分類は product_format_code に細分類のコードを入れます。英語名・型番・発売日・除外キーワードを調べて存在しなかった場合は、blank_confirmed にその列名（english_title、mark、release_date、exclude_keywords）をカンマで区切って入れます。` | 既存の en の文に、`For the format, enter its code in product_format_code. If you checked and the English name, model number, release date or exclusion keywords do not exist, list those column names (english_title, mark, release_date, exclude_keywords) in blank_confirmed, separated by commas.` を足す |
| `productCsv.fields.PRODUCT_FORMAT_CODE`（追加） | `細分類` | `Format` |
| `productCsv.messages.headerError`（変更） | `CSVの見出しが指定の列と一致しません。サンプルCSVか、いま書き出したCSVの見出しを使ってください。` | `The CSV headers do not match. Use the sample CSV or the headers of a freshly exported CSV.` |
| `productCsv.messages.formatGameMismatch`（追加） | `細分類が作品に紐づいていません。細分類マスタで使えるゲームを確認してください。` | `The format is not linked to this work. Check the games allowed for the format in the format master.` |
| `productCsv.messages.blankConfirmedInvalid`（追加） | `blank_confirmed に使えない列名があります：{{value}}` | `blank_confirmed has a column name that cannot be used: {{value}}` |

en の既存の文は、実物を読んで同じ位置のキーを変える（en に `format`・`headerError` の英文が既にある）。

### 4-4. 試験

`backend/tests/test_tcg_product_import.py` に足す（名前はこのとおり）:
1. `test_parse_rows_accepts_new_and_legacy_headers` — 12列の見出しの行は2列が読まれる。旧10列の見出しの行は `product_format_code`・`blank_confirmed` が `""`。どちらでもない見出しは `CSV_HEADER_MISMATCH`
2. `test_static_check_blocks_unknown_format_and_bad_mark_names` — `lookups={"product_format_code": {"BOOSTER": 1}}` で `"BAD"` は `UNKNOWN_PRODUCT_FORMAT_CODE_BAD`、`blank_confirmed="name_en,mark"` は `BLANK_CONFIRMED_INVALID_name_en` だけ（`mark` は正しい）、空の細分類は止めない（`MISSING_PRODUCT_FORMAT_CODE` が出ない）
3. `test_build_payload_maps_format_and_marks` — `product_format_code="BOOSTER"` → `product_format_id == 1`、`blank_confirmed=" mark , english_title,mark"` → `blank_confirmations == ["name_en", "mark"]`、空なら `None` と `[]`
4. `test_preview_blocks_format_not_linked_to_work` — `format_matches_game` を `AsyncMock(return_value=False)` に差し替え（`app.services.tcg_product_master_svc` の属性）、`blocking` に `PRODUCT_FORMAT_GAME_MISMATCH`、`validate_row_dynamic` が呼ばれない

`backend/tests/test_tcg_product_roundtrip.py` に足す:
5. `test_export_writes_format_code_and_marks` — `snap["refs"]["product_format_code"]="BOOSTER"`・`snap["blank_confirmed"]=["mark","name_en"]` で `values(snap)` が `"BOOSTER"` と `"english_title,mark"`
6. `test_revision_changes_when_marks_change` — 印を足すと `revision` が変わり、前置きが `v2:`
7. `test_update_plans_format_and_marks` — `formats` の問い合わせの戻りを差し替え、細分類コードの変更が `plan["sets"]["product_format_id"]`、知らないコードが `UNKNOWN_PRODUCT_FORMAT_CODE_x`、`blank_confirmed` の変更が `plan["marks"]`、知らない名前が `BLANK_CONFIRMED_INVALID_x`

既存の試験の直し:
- `test_tcg_product_import_atomicity_pg.py` の `csv_input` の各行の末尾に `"", ""` を足す（見出しは `importer.CSV_COLUMNS` のまま）
- `TcgProductImportPanel.test.tsx` の `toHaveLength(10)` を `toHaveLength(12)` にする
- 既存の往復の試験で `revision` の前置きや `values` の列が合わなくなったものは、意味を変えずに新しい形に合わせる。直した試験の名前と理由を報告に書く

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. バックエンドの試験: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c/backend && /private/tmp/claude-501/py312-openapi/bin/python -m pytest tests/test_tcg_product_import.py tests/test_tcg_product_roundtrip.py tests/test_tcg_product_code_collision_wiring.py -q -p no:cacheprovider 2>&1 | tail -20` が全部合格（pytest が venv に無ければ §6）。

5-2. 試験の名前: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c && git diff origin/main -- backend/tests | grep -nE "^\+\s*(async def test_|def test_)" | head -10` の出力（7 行、名前が §4-4 のとおり）。

5-3. 画面の試験: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/tcg-product-import/ 2>&1 | tail -30` が全部合格。

5-4. 型と lint: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | tail -20` と `npx eslint src/features/tcg-product-import/importMessages.ts src/features/tcg-product-import/TcgProductImportPanel.test.tsx 2>&1 | tail -20` がどちらもエラー 0（`src/api/generated/schema.d.ts` が無くて落ちるときは、先に `npm run generate:api-types 2>&1 | tail -3`。生成物はコミットしない）。

5-5. i18n: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c/frontend && npm run check:i18n-missing-keys 2>&1 | tail -10` が合格。

5-6. テンプレート: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c && od -c frontend/public/templates/tcg-product-import-template.csv | head -2 && tail -c 4 frontend/public/templates/tcg-product-import-template.csv | od -c | head -1` で先頭が `357 273 277 m a r k`、末尾が `\r \n`。

5-7. 差分: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c && git diff origin/main --stat | tail -15` が §3 のファイルだけ。

5-8. PR の CI は担当が待たない。PR を作ったら URL を報告して終える。

## 6. 分岐ごとの対処

- §10 手順1 で origin/main の `frontend/src/features/tcg-analysis-review/reviewActions.ts` に `blank_confirmations` の文字が無い → BLOCKED:（便2b-3 が入っていない。作業を始めない）
- §4 の目印が実物と違う → 実物の該当行を貼り、同じ意味・同じ位置に合わせて書く。見つからなければ NEEDS_DECISION:
- 往復のサービスから `tcg_product_master_svc` を先頭で import すると循環で落ちる → `format_matches_game`・`save_blank_confirmations` を使う関数の中で import する形に変え、落ちた原文を報告に書く
- `test_tcg_product_roundtrip_pg.py`（実 DB の試験）の DB に `public.product_formats` か `public.product_blank_confirmations` が作られない → その試験の作り方（どの migration を流すか）を貼り、その migration を足す最小の直しを `test_tcg_product_roundtrip_pg.py` か共通の土台にする。共通の土台を変える必要があれば NEEDS_DECISION:
- `/private/tmp/claude-501/py312-openapi/bin/python -m pytest --version` が失敗 → 出力を貼り「手元では未実行・CI で実行」と書いて続ける（3.12 以外の Python で作らない）
- husky や CI の自動検査が落ちる → 検査名と原文を貼る。迂回（`--no-verify` など）しない

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 新規取り込みが12列と旧10列の両方を受け、それ以外を止める | 試験 1 |
| 細分類コードが id になって登録に渡り、知らないコード・作品に紐づかない細分類は止まる | 試験 2・3・4 |
| `blank_confirmed` が印の項目名になって登録に渡り、知らない名前は止まる | 試験 2・3 |
| 往復の書き出しに細分類コードと印が出て、印の変化で指紋が変わる | 試験 5・6 |
| 往復の更新で細分類と印が直せ、知らない値は止まる | 試験 7 |
| 足りない項目があっても止めない（便2） | 既存の試験が合格（旧10列の `_HEADER` の試験がそのまま通る） |
| 文言は ja/en 同じキー | §5-5 |

## 8. 反映の前後（Opus が行う。担当はしない）

- CI の緑を確かめ、差分を審査し、「確認済み」のコメントを残してマージ → deploy の成功を Actions の記録で確かめる
- 反映後、本番の HEAD がマージ commit と一致すること、本番のテンプレート `https://app.salesanchor.jp/templates/tcg-product-import-template.csv` の見出しが12列であること、本番の画面 JS に `blank_confirmed has a column name` が入っていること、紐づけ表が 69 行のままであることを読み取りで確かめる
- 生出力は /tmp/CC報告ファイル/master-required-fields/bin2c/ に置く

## 9. 戻し方

- この PR の revert を main にマージ（CSV の形が元に戻る。DB の表は変えていない）

## 10. PR

手順1 前提が main にあることを確かめ、新しい作業場所を作る
    cd /Users/tanizawashingo/salesanchor && git fetch -q origin && git grep -c "blank_confirmations" origin/main -- frontend/src/features/tcg-analysis-review/reviewActions.ts
期待する出力 1 以上（0 なら §6 の1つ目）
    cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/master-register-required-fields-bin2c --claude 2>&1 | tail -5
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c && git status -sb | head -3 && git log -1 --oneline
期待する出力 作業場所が origin/main の先頭から作られている。以下のコマンドの作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c
    このカードを /tmp/CC報告ファイル/master-required-fields/bin2c/card-bin2c.md から Read し、Write ツールで `/Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c/docs/handoff/master-register-required-fields/card-bin2c.md` に同じ内容で置く。`cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c/frontend && ls node_modules | head -1` で依存が無ければ `npm ci 2>&1 | tail -5`

手順2 §4 を Write/Edit ツールで実装し、§5-1〜5-7 を実行する

手順3 commit と push
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c && git add backend/app/services/tcg_product_import_svc.py backend/app/services/tcg_product_roundtrip_svc.py backend/tests/test_tcg_product_import.py backend/tests/test_tcg_product_roundtrip.py backend/tests/test_tcg_product_import_atomicity_pg.py frontend/public/templates/tcg-product-import-template.csv frontend/src/features/tcg-product-import/importMessages.ts frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx frontend/src/locales/ja.json frontend/src/locales/en.json docs/handoff/master-register-required-fields/card-bin2c.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c && git commit -m "feat: ADR-1020便2c 商品CSVに細分類コードと調べたが存在しないの印を追加"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c && git push -q -u origin release/master-register-required-fields-bin2c && git log -1 --oneline && git log origin/release/master-register-required-fields-bin2c -1 --oneline
期待する出力 2 つの git log が同じハッシュ。§6 で `test_tcg_product_roundtrip_pg.py` を直したときは、最初の git add にそれも足す

手順4 PR を作る
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2c && gh auth status 2>&1 | grep -c "Active account: true"

- 名義が `shingo-cc` であることを確かめる
- 本文は Write ツールで英字だけのパスのファイル（/private/tmp/claude-501/bin2c-pr-body.md）に作り、作業場所に cd してから `scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめる（2 分以上かかるので timeout を長めにする）
- PR は `scripts/gh-pr-create-safe.sh` に本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。base は main。ready で作る（下書きにしない）。担当はマージしない
- 作成後に `.pr-number` と `gh pr list --head release/master-register-required-fields-bin2c --json number` の一致を確かめる
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/master-register-required-fields/recon.md）・設計（docs/handoff/master-register-required-fields/design.md）・このカード・ADR-1020・ADR-027 を書く。区分は M（危険パスなし）。PO承認: に「PO 2026-10-16『y』（KGI G1〜G4・3便）、PO 2026-10-17 チャット『PRマージ、デプロイまで完走させてくれ』（本セッション＝ADR-1020 便2〜便3）」と書く。validate-pr-body.sh が「設計docに参照がない」と ADR を指摘したら、その ADR だけを `対象ADR` から外し、外したことを報告に書く
- `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし。触るファイル: は §3 で実際に変えたファイル。削除するファイル: は既存行を変えたファイル（§3 の 1〜10。便2b-3 #4416 と同じ書き方）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-7 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/master-required-fields/bin2c/impl/）／判断を要した点（事実のみ）
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
