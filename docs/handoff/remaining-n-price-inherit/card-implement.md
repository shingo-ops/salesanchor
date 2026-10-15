# 実装カード — 価格なし・数ありの行に前の価格を引き継ぐ

> この文書は何か：解析の保存時に、商品が決まっていて数だけ書かれた（価格なし）行へ、同じ仕入元・同じ商品×状態の「前の価格（48時間以内）」を引き継ぐ実装の作業指示書です。直すのは `backend/app/services/line_analysis_v102_svc.py` と、相場の SQL（`backend/app/services/v102_unit_price_check_svc.py` の `_MARKET_SQL`）の条件1行で、試験と README の1行を足します。

- 設計: docs/handoff/remaining-n-price-inherit/design.md（3章が変更の正本。変えてはいけない）
- 事実確認: docs/handoff/remaining-n-price-inherit/recon.md（file:line は実測 HEAD 803d7c58a で確認済み）
- 対象ADR: ADR-158（部分更新の趣旨。Proposed）・ADR-1014・ADR-1015
- 状態: **このカードは実行しない。** PO が承認したのは設計だけで、実装は未承認。PO の「GO #実装PR番号」（番号必須）を Opus が受け取り、このカードの §0 の「GO の記録」欄に原文が書かれてから始める
- 危険便: いいえ（`migrations/`・`deploy.yml`・`scripts/` を触らない）
- 担当: 実装 Sonnet／コード審査・GO 記録・マージ・反映確認 Opus

## 0. カード発行前チェック

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | 報告の宛先・生出力の扱いを明記 | ○（§10） |
| 3 | 1便1目的 | ○（価格の引き継ぎだけ） |
| 4 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 5 | 変更前後のコードを実物どおりに書いた | ○（§4） |
| 6 | 触らない範囲を明記 | ○（§1・§3） |
| 7 | 停止条件・報告3点・受領確認・終端合図 | ○（§7・§10） |
| 8 | 社外秘（仕入元の ID・名前・投稿原文）を試験にも本文にも入れない | ○（§8） |

GO の記録（Opus が記入）: 未記入（PO の GO がまだ無い）

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 |
|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない |
| guards/04-worktree.md | worktree は `scripts/new-worktree.sh` で作る |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 価格の引き継ぎ（remaining-n-price-inherit）の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `backend/app/services/line_analysis_v102_svc.py` に、定数・読み取り SQL・ヘルパ関数を足し、保存ループの中で1行呼ぶ。import に `FIELD_V102_PRICE` を足す
2. 単体試験（読み取りで例外が出ても価格なしのまま保存され、例外が外に出ない）
3. PG 試験（引き継ぎの条件・連鎖しない・配信 SQL に出る）
4. `docs/specs/line-analysis-tuning/README.md:41` の price_basis の表に `INHERIT:<id>` の説明を1行足す
5. `backend/app/services/v102_unit_price_check_svc.py:54-67` の `_MARKET_SQL` の WHERE に `AND (ar.price_basis IS NULL OR ar.price_basis NOT LIKE 'INHERIT:%')` を1行足す（設計 3-11）。それ以外の行は変えない

入れない（触らない）:
- 配信 SQL（`backend/app/services/tcg_distribution_svc.py`）、要確認 SQL（`backend/app/services/tcg_condition_review_svc.py`）、`_merge_supplier_products`（`backend/app/services/tcg_analyzer_svc.py`）
- GAS 本体、Gemini の抽出、`backend/app/services/v102_unit_price_check_svc.py` の `_MARKET_SQL` の1行以外
- `migrations/`・`.github/workflows/`・`scripts/`
- 価格が原文にあるのに読めていない件（別テーマ）。再解析（別途 PO の y が要る）

## 2. 前提の事実（recon.md の引用）

| # | 事実 | 根拠 |
|---|---|---|
| 1 | 保存ループは `line_analysis_v102_svc.py` の942行目から。`values` の組み立てが943〜947行、UPSERT が948行から | `backend/app/services/line_analysis_v102_svc.py:942` |
| 2 | 今の job の仕入元と投稿時刻は `_FOLLOWUP_CURRENT_SQL` で引ける | `backend/app/services/line_analysis_v102_svc.py:1004` |
| 3 | 48時間の定数は既存 | `backend/app/services/line_analysis_v102_svc.py:1041` |
| 4 | SAVEPOINT＋try/except の型は既存 | `backend/app/services/line_analysis_v102_svc.py:882` |
| 5 | 人が価格を直すと `v102_price` の行ができる。消すと空文字 | `backend/app/services/v102_transcription_svc.py:302` |
| 6 | price_basis は VARCHAR(100)。`INHERIT:<uuid>` は44字 | `migrations/20261011_150000_add_analysis_results_price_basis.sql:2` |

## 3. 触るファイル（これ以外は触らない）

| ファイル | 内容 |
|---|---|
| `backend/app/services/line_analysis_v102_svc.py` | 定数2つ・SQL2本・ヘルパ関数・ループ内の代入1行・import 1つ |
| `backend/app/services/v102_unit_price_check_svc.py` | `_MARKET_SQL` の WHERE に条件1行 |
| 単体試験（既存の `backend/tests/test_line_analysis_v102_svc.py` に足す） | 例外時の試験・raw_price が書かれている行の試験 |
| PG 試験（新規ファイル。名前は backend/tests/test_v102_price_inherit_pg.py） | 引き継ぎの条件・連鎖・配信 |
| `docs/specs/line-analysis-tuning/README.md` | 41行目の表に1行 |

## 4. 作り方

### 4-1. 変更前（実物どおり。`backend/app/services/line_analysis_v102_svc.py` の942〜952行）

```python
    for index, (item, row) in enumerate(pairs):
        decision = decisions.get(str(row.id))
        values = _apply_soldout_targets(
            _apply_decisions(_with_unit_price_reason(base_values[index], index in mismatches), item, decision, canonicals),
            item, decision, canonicals, excluded_ids,
        )
        result_id = session.execute(
            text(_UPSERT_SQL.format(schema=analyzer.TCG_SCHEMA)),
            {**values, "id": str(uuid.uuid4()), "extraction_item_id": str(row.id), "engine_version": V102_ENGINE_VERSION,
             "computed_at": now, "updated_at": now},
        ).scalar_one()
```

### 4-2. 変更後

947行目の閉じ括弧の直後に1行足す（これだけ）:

```python
        values = _inherit_price(session, extraction_job_id, row, values)
```

import（62行目）は次にする:

```python
from app.services.v102_human_decisions_svc import FIELD_V102_PRICE, Decisions, load_v102_decisions
```

### 4-3. 足す定数・SQL・ヘルパ（`load_soldout_ref_posts` の後ろ。`SOLDOUT_REF_MAX_GAP_SECONDS` の定義より後ろに置く）

以下は設計 3章を形にした案。名前や細部は直してよいが、3章の条件は変えない。

```python
PRICE_BASIS_INHERIT_PREFIX = "INHERIT:"
INHERIT_PRICE_MAX_GAP_SECONDS = SOLDOUT_REF_MAX_GAP_SECONDS  # 48時間。〆の参照と同じ測り方

_INHERIT_PRICE_SQL = """
    SELECT ar.id, ar.price_normalized
    FROM {schema}.analysis_results ar
    JOIN {schema}.extraction_items ei ON ei.id = ar.extraction_item_id
    JOIN {schema}.extraction_jobs ej ON ej.id = ei.extraction_job_id
    JOIN {schema}.source_messages sm ON sm.id = ej.source_message_id
    WHERE sm.supplier_channel_id = :channel
      AND ar.product_id = :product_id AND ar.condition_id = :condition_id
      AND ar.price_normalized IS NOT NULL
      AND ar.status IS DISTINCT FROM :sold_out
      AND (ar.price_basis IS NULL OR ar.price_basis NOT LIKE :inherit_like)
      AND sm.line_posted_at < :posted_at
      AND sm.line_posted_at >= :posted_at - make_interval(secs => :gap)
      AND ej.id = (SELECT j2.id FROM {schema}.extraction_jobs j2 WHERE j2.source_message_id = ej.source_message_id
                   ORDER BY j2.created_at DESC, j2.id DESC LIMIT 1)
    ORDER BY sm.line_posted_at DESC, ei.line_start DESC NULLS LAST, ar.id DESC
    LIMIT 1
"""
_PRICE_CORRECTION_SQL = """
    SELECT human_value FROM {schema}.item_corrections
    WHERE extraction_item_id::text = :item_id AND field_name = :field
    ORDER BY corrected_at DESC, id DESC LIMIT 1
"""
```

ヘルパ `_inherit_price(session, extraction_job_id, row, values)` の流れ:
1. 純 Python の条件（設計 3-1 の 1〜4 と 6）を満たさなければ、DB を使わず `values` をそのまま返す。6 は `row.raw_price` が None か、`str(row.raw_price).strip().lower()` が `''` か `'none'` のときだけ対象（`row` は SELECT に raw_price を含む。`backend/app/services/line_analysis_v102_svc.py:1187-1193`）。`values["condition_id"]` が None なら対象外
2. `try: with session.begin_nested():` の中で、`_PRICE_CORRECTION_SQL` の最新行の `human_value` が空文字なら `values` を返す
3. 同じ中で `_FOLLOWUP_CURRENT_SQL` から仕入元と時刻を引く（無ければ `values` を返す）
4. 同じ中で `_INHERIT_PRICE_SQL` を、`channel`・`product_id`・`condition_id`・`sold_out=STATUS_SOLD_OUT`・`inherit_like=PRICE_BASIS_INHERIT_PREFIX + "%"`・`posted_at`・`gap=INHERIT_PRICE_MAX_GAP_SECONDS` で実行する
5. 見つかれば `{**values, "price_normalized": src.price_normalized, "price_basis": f"{PRICE_BASIS_INHERIT_PREFIX}{src.id}"[:_PRICE_BASIS_MAX]}` を返す。見つからなければ `values`
6. `except Exception as exc:  # noqa: BLE001` で `logger.warning` を出し `values` を返す（`_unit_price_mismatches` と同じ形）

注意: `ar.price_basis NOT LIKE` は NULL を除外してしまうので、上の SQL のように `IS NULL OR` を付ける。SQL 内の `price_basis` 列が `analyzer.TCG_SCHEMA` の `analysis_results` にあることを、PG 試験の実行で確かめる。

### 4-4. 試験

PG 試験（型は `backend/tests/test_inventory_distribution_rows_pg.py` の `_add_job`・`_add_row`・`_rows`、`backend/tests/test_line_analysis_v102_pg.py:198` 付近の差し替えの型）。次を1つずつ別の試験にする:
1. 前の価格行（48時間以内）あり → 価格と `INHERIT:<id>` を引き継ぐ
2. 元が48時間より古い／元が無い／別の状態／別チャンネル → 引き継がない
3. 完売行は引き継がない
4. 人が価格を消した行（item_corrections の最新が空文字）は引き継がず、人が足した価格なし行（v102_price の行なし）は引き継ぐ
5. 配信 SQL で「新しい数・前の価格」の1行が出る
6. 連鎖: A 価格あり → B 数だけ（A を引き継ぐ）→ C 数だけ。C は A の価格と `INHERIT:<A_id>`。A が48時間を超えると C は価格なし
7. 価格あり行・完売行の price_basis は今と同じ（V102:yen_free か NULL）
8. raw_price が「37万」のように書かれていて price_normalized が空の行は引き継がない（値は架空でよい）
9. condition_id が NULL の行は引き継がない
10. 相場: `INHERIT:` の行は `_MARKET_SQL` の中央値と投稿数に入らない（同じ商品×単位に、仕入元が書いた価格の行と `INHERIT:` の行を置いて、posts と median_price が `INHERIT:` を足す前と同じ）

単体試験: 読み取りで例外 → price_normalized は None のまま保存され、例外が外に出ない（`backend/tests/test_line_analysis_v102_svc.py` の `_FakeSession` の型）。

注意:
- 別チャンネルの fixture は既存に無い（`_add_job` はいつも supplier_channels の先頭1件）。supplier_channels を直接 INSERT する。public.supplier_channels の列は `id`・`channel`（NOT NULL）・`external_id`・`is_active`（NOT NULL）・`supplier_id`（NOT NULL・suppliers 参照）。NOT NULL は channel・is_active・supplier_id（`migrations/20260921_110000_pipeline_tables_public.sql:11-17`）。INSERT の型は `backend/tests/test_inventory_distribution_rows_pg.py:388-404` の `_set_supplier`
- `_add_row` は price_basis と is_current を INSERT しない（is_current は既定 TRUE）。INHERIT 行や非 current 行は UPDATE で作る
- `pg` fixture は GITHUB_ACTIONS が true のときだけ動く。ローカルでは skip されるので、PG 試験は CI でのみ実行される。ローカルで未実行と報告に書く

### 4-5. README

`docs/specs/line-analysis-tuning/README.md` の41行目の表（price_basis の値）に `INHERIT:<id>` の行を足す。意味は「価格が書かれていない数だけの行に、同じ仕入元・同じ商品×状態の前の価格（48時間以内）を引き継いだ。id は元の analysis_results.id」。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

1. 単体試験: `cd` で worktree に入り、`backend/tests/test_line_analysis_v102_svc.py` と `backend/tests/test_v102_buyback_unit.py` を pytest で通す（出力は末尾30行まで）
2. `git diff --stat` に、§3 の表にないファイルが無い
3. 触らない範囲（§1）のファイルが差分に無い（`git diff --name-only` で確認）
4. 日本語のハードコード UI 文字列を足していない（バックエンドのログ文のみ）
5. PG 試験は PR の CI で結果を見る（待たずに PR の URL を報告する）

## 6. 分岐ごとの対処

| 分岐 | 対処 |
|---|---|
| 既存の単体試験が壊れた | 読み取りを begin_nested の外に出していないか確認。直せなければ停止 |
| 引き継ぎで相場検査の対象行が増えた | 設計は「相場検査に入れない」（書き込み時の検査は差し込み位置より前、後から来る投稿の相場は `_MARKET_SQL` で外す）。試験 10 が通らなければ停止して Opus に報告 |
| 同時刻・同投稿内で候補が複数 | ORDER BY の補足案（line_start・id）で決める。補足案は設計に明記が無いので、PR 本文に「未指定の補足」と書く |
| price_basis の列が見つからない | 停止して報告（migration は触らない） |

## 7. 停止条件

次のいずれかになったら、作業を止めて Opus に報告する（言い換えて再試行しない）:
- 設計 3章と食い違う実装が必要になった
- §1 の「入れない」に触る必要が出た
- フック・分類器・CI に止められた
- 試験の結果が想定と合わない（数字が合わない・説明できない差分）

## 8. 社外秘

試験データ・PR 本文・コミットメッセージに、実在の仕入元の ID・名前・投稿原文・仕入元別の件数を入れない。試験の値は架空のもの（例: product_id・価格はダミー）にする。

## 9. 戻し方

この実装 PR を revert する。引き継いだ行は `price_basis LIKE 'INHERIT:%'` で特定でき、再解析で元に戻る。DB の列追加はない。

## 10. PR と報告

- 作業場所は `scripts/new-worktree.sh release/remaining-n-price-inherit-impl` で作る（実在は `git worktree list` で確かめる）
- 作成前に `gh auth status` で `shingo-cc` 名義を確かめる
- PR は `scripts/gh-pr-create-safe.sh` で作る。本文は `.github/pull_request_template.md` 起点。`### 標準ワークフロー確認` に recon・design・このカード・ADR を書き、「触るファイル:」を同一行・カンマ区切りで全列挙する
- commit の後に `git log -1 --oneline`、push の後に `git log origin/release/remaining-n-price-inherit-impl -1 --oneline` で実在を確かめる
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる
- マージは Opus が GO 記録の後に行う。担当はマージしない。sleep しない。CI の完了を待たず PR の URL を報告する
- 報告の1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか。完了報告に、冒頭の受領文・§5 の出力・PR の URL・生出力のパス・判断を要した点（事実のみ）を書く。停止したときは、停止した箇所・最後に実行したコマンド・停止した理由の原文を書く
- 本番の確認（KGI の組数 = 0）は、反映と再解析（PO の y が別途要る）の後に Opus が読み取りで行う。担当は実施しない

## 11. 報告欄（担当が追記）

（未記入）

END OF CARD
