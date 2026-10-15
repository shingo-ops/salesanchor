# Phase 3 設計 — remaining-n-price-inherit（価格なし・数ありの行に前の価格を引き継ぐ）

**状態**: 設計 PO 承認済み（目標の直しと48時間）／**実装未承認**。この承認は実装・マージ・本番反映の承認を兼ねない。
**対象ADR**: ADR-158（部分更新の趣旨。Proposed）・ADR-1014・ADR-113・ADR-1015
**recon**: docs/handoff/remaining-n-price-inherit/recon.md
**日付**: 2026-10-15
**担当**: 設計 Opus／文書化 文書担当
**PO の決定（原文）**: 2026-10-15 PO「y」＋「引き継ぐのは…48h以内の商品」。目標を「前の価格があるのに消えている組を 0（今は 1）」とし、引き継ぐ価格は48時間以内とする。

---

## 1. 目的と KGI

目的: 仕入元が価格を書かず数だけ投稿（例「残りN個」）しても、その商品×状態が在庫表・GAS・配信から消えず、「前の価格・新しい数」で出続ける。

**KGI（PO が画面・出力で○×を判定できる形）**: 本番で「前の価格（48時間以内）があるのに、数だけ行が現在値で在庫表に出ていない組」= 0（現在 1）。判定は、実装の反映と再解析の後に、読み取りで件数を数える。

対象外: 価格が原文にあるのに読めていない 3 組（別テーマ）、前の価格が無い組（引き継ぎでは直らない）。

## 2. 現状（事実。根拠は recon.md）

- 解析の保存後、`backend/app/services/tcg_analyzer_svc.py:1955` の merge が価格を見ずに最新 job を is_current=TRUE にする。
- 配信は `backend/app/services/tcg_distribution_svc.py:338` で価格 NULL を落とし、`backend/app/services/tcg_distribution_svc.py:335` で needs_review も落とす（二重に落ちる）。
- 30日・v102 7,208 行のうち、商品特定済み・価格なし・数ありは 13 行（0.18%）。いま消えている組は 5。内訳は 引き継ぎで直る 1／価格の読み取り不具合 3（別テーマ）／前の価格なし 1。前の価格ありの 10 行の経過時間は 0.4〜101.5 時間（48時間以内 8、超過 2）。完売扱いは 0。

## 3. 変更（案A。勝手に変えない）

差し込み位置: `backend/app/services/line_analysis_v102_svc.py:947` と `backend/app/services/line_analysis_v102_svc.py:948` の間。ループ `for index, (item, row) in enumerate(pairs):`（:942）の中で、`values = _apply_soldout_targets(...)` の直後、`session.execute(text(_UPSERT_SQL...` の直前。`values` の `price_normalized` と `price_basis` の2つだけを差し替える。相場検査（:941 `_unit_price_mismatches`）の対象には入れない。後から来る別投稿の相場の母数からも外す（3-11）。

### 3-1. 対象行（全部満たすとき）

1. `values["price_normalized"] is None`
2. `values["quantity_normalized"] is not None`
3. `values["product_id"] is not None` かつ `values["pid_resolved"]`
4. `values["status"] != STATUS_SOLD_OUT`（完売行は引き継がない）
5. 人が価格を消していない（3-3）
6. 仕入元が価格を書いていない: `row.raw_price` が None、または前後の空白を除いて小文字にした値が `''` か `'none'`（`row` は extraction_items の行で、SELECT に raw_price を含む `backend/app/services/line_analysis_v102_svc.py:1187-1193`）。価格が書いてあるのに読めなかった行（本番 30日で「37万」「38万」「＠65,000円（4,400円/BOX可）」の3行。recon5）に古い価格を写して、書かれた新しい価格を隠さないため

### 3-2. 引き継ぎ元の探し方（新規の読み取り SQL 1本）

- 今の job の supplier_channel_id と line_posted_at は `_FOLLOWUP_CURRENT_SQL`（:1004-1008）で job id から引く。
- 元の行の条件: 同じ supplier_channel_id（source_messages 経由。analysis_results には無い）・同じ product_id・同じ condition_id・`price_normalized IS NOT NULL`・`status IS DISTINCT FROM 'Sold out'`。
- **price_basis が `INHERIT:%` の行は元にしない**（連鎖で古い価格が延命するのを防ぐ）。
- 元の line_posted_at が今の投稿より前、かつ差が 172800 秒（48時間）以内。`SOLDOUT_REF_MAX_GAP_SECONDS`（:1041）を流用し、`load_soldout_ref_posts`（:1052-1069）と同じ測り方にする（`now-48h` ではない）。
- 各投稿は最新 job の行だけを見る（`_STOCK_ITEMS_SQL`（:1072-1084）と同じ `ej.id = (SELECT j2.id … ORDER BY j2.created_at DESC, j2.id DESC LIMIT 1)` の型）。is_current と is_active は条件にしない。
- 並びは元の line_posted_at の新しい順で 1 件。
- 結合: analysis_results → extraction_items → extraction_jobs → source_messages。
- **未指定の補足案（実装裁量。設計に明記が無い。実装時にレビューで確認する）**: 同時刻・同投稿内で複数候補があるときの決定性のため `ORDER BY sm.line_posted_at DESC, ei.line_start DESC NULLS LAST, ar.id DESC`。LIKE のパターンは bind パラメータ（`:inherit_like` = `INHERIT:%`）で渡す。

### 3-3. 人が価格を消した行

`item_corrections` の `extraction_item_id = row.id AND field_name = 'v102_price'`（定数 `FIELD_V102_PRICE`、`backend/app/services/v102_human_decisions_svc.py:35`）の最新行（`ORDER BY corrected_at DESC, id DESC`。`backend/app/services/v102_human_decisions_svc.py:49` の `_CORRECTIONS_SQL` と同じ読み方）の `human_value` が空文字なら引き継がない。人が足した件（`v102_item_added`）で価格が無いものは v102_price の行が無いので引き継ぐ。`load_v102_decisions` は価格の判断を返さない（`backend/app/services/v102_human_decisions_svc.py:75`）ので、新規の読み取りが要る。

### 3-4. 失敗時

読み取りは `session.begin_nested()`（SAVEPOINT）で包み、例外なら引き継がず今のまま保存する。型は `_buyback_units`（:882-890）と `_unit_price_mismatches`（:893-910）の try/except と `logger.warning`。解析全体は止めない。

### 3-5. 読み取りの回数

対象行が 1 つ以上あるときだけ読む（月 13 行程度）。既存の `_FakeSession`（`backend/tests/test_line_analysis_v102_svc.py:475`）の単体試験には影響させない（begin_nested が try の内側なので、FakeSession でも例外は握りつぶされ値は変わらない）。

### 3-6. 保存する値

見つかったら `price_normalized` を元の値、`price_basis` を `INHERIT:<元の analysis_results.id>`（`_PRICE_BASIS_MAX` で切る。44 字なので収まる）にして返す。DB の列追加なし。COMMENT は変えない（migration 不要）。

### 3-7. 時刻列

「前の投稿」と48時間は `line_posted_at`（配信の窓 `backend/app/services/tcg_distribution_svc.py:224` と同じ）。merge は received_at 基準（`backend/app/services/tcg_analyzer_svc.py:1927`）のまま変えない。本番の直近30日で、同じチャンネル内の received_at 順と line_posted_at 順の逆転は 0 組（比較 2,170 組）、line_posted_at の NULL は 0 件（recon5）。

### 3-8. 文書

`docs/specs/line-analysis-tuning/README.md:41` の price_basis の表に `INHERIT:<id>` を足す。**実装 PR で行う**（この文書 PR では触らない）。

### 3-9. 触らない範囲

配信 SQL、要確認 SQL、`_merge_supplier_products`、GAS 本体、Gemini の抽出、migrations、deploy.yml、scripts/。危険パスなし。変更は `backend/app/services/line_analysis_v102_svc.py`（定数・読み取り関数・ヘルパ・ループ内の代入1行・import 1つ）、`backend/app/services/v102_unit_price_check_svc.py` の `_MARKET_SQL` の条件1行（3-11）、試験（単体・PG）、README の1行に限る。

### 3-10. 選ばなかった案

- 案B（配信 SQL と要確認 SQL で前の価格を補う）: SQL が重くなり、3か所で補い方を揃える必要があり、出どころが DB に残らない。
- 案C（merge で価格なし行を現在値にしない）: 数が更新されない。

### 3-11. 相場の母数から外す（SSOT の整理）

- 価格の置き場は `analysis_results.price_normalized` の1か所だけ。出どころは同じ行の `price_basis` に書く（`INHERIT:<元id>`）。別の表・別の列・読み手ごとの補完は作らない。
- 読み手は全員この列をそのまま読む（配信・在庫表・GAS・要確認・ダッシュボード。recon4 の R1〜R7・R10〜R13）。
- 例外は相場だけ。相場は「仕入元が書いた価格」の中央値と投稿数で、写した価格を入れると同じ価格を2回数える（`backend/app/services/v102_unit_price_check_svc.py:54-67` の `_MARKET_SQL` は is_current の価格行を全部数え、今は price_basis の条件が無い。recon6）。そこで `_MARKET_SQL` の WHERE に `AND (ar.price_basis IS NULL OR ar.price_basis NOT LIKE 'INHERIT:%')` を1行足す。出どころの判定は price_basis の1か所で行い、データは分けない。
- 買取の中央値は analysis_results を読まない（`backend/app/services/v102_buyback_unit_svc.py:54-65`。recon4）ので変えない。

## 4. 外部・過去事例の参照と我々への応用

- 該当なし：社内の LINE 投稿の書き方に固有の問題で、判断は本番の実測（13 行／消えている 5 組／経過時間の分布）に基づく。過去の関連設計として、〆の件が過去投稿を48時間以内で参照する仕組み（`backend/app/services/line_analysis_v102_svc.py:1041`）の測り方と読み取りの型を流用する。

## 5. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 前の価格（48時間以内）がある数だけ行は、価格と `INHERIT:<id>` を引き継ぐ | CI の pytest（PG）。実装 PR で新設する引き継ぎの試験 |
| 48時間より古い・前の価格が無い・別の状態・別チャンネルの元は引き継がない | CI の pytest（PG）。同じ試験ファイルの否定ケース |
| 完売行は引き継がない | CI の pytest（PG） |
| 人が価格を消した行は引き継がず、人が足した価格なし行は引き継ぐ | CI の pytest（PG）。item_corrections を使うケース |
| 配信 SQL で「新しい数・前の価格」の1行が出る | CI の pytest（PG）。`backend/tests/test_inventory_distribution_rows_pg.py` の `_add_job`・`_add_row`・`_rows` の型 |
| 連鎖しない: A 価格あり→B 数だけ（A を引き継ぐ）→C 数だけ は C が A の価格と `INHERIT:<A_id>`。A が48時間超なら C は価格なし | CI の pytest（PG） |
| 価格あり行・完売行の price_basis は今と同じ（V102:yen_free か NULL） | CI の pytest（PG） |
| 仕入元が価格を書いているのに読めなかった行（raw_price が「37万」のような値）は引き継がない | CI の pytest（PG） |
| condition_id が NULL の行は引き継がない | CI の pytest（PG） |
| 相場（`_MARKET_SQL`）の中央値と投稿数に `INHERIT:` の行が入らない | CI の pytest（PG） |
| 読み取りで例外が出ても price_normalized は None のまま保存され、例外が外に出ない | CI の pytest（単体）。`backend/tests/test_line_analysis_v102_svc.py` の `_FakeSession` の型 |
| 既存の試験が全部通る | CI の backend テスト全件 |
| 本番で「前の価格（48時間以内）があるのに数だけ行で在庫表に出ていない組」= 0（現在 1） | 実装 PR のマージ・反映・再解析の後に、読み取りの件数 SQL で確認（今回は実施しない） |
| 引き継いだ行を特定できる | `price_basis LIKE 'INHERIT:%'` の件数を読み取りで数える |

## 6. 技術 How・KPI

- KPI: KGI の組数 1 → 0。引き継ぎ件数（`INHERIT:%`）は月 13 行以下の見込み（前の価格ありは 10 行、うち48時間以内 8 行）。
- 技術選択: 保存時に価格を引き継ぎ、出どころを `price_basis` に残す（配信・要確認・GAS を無改修で直せる。戻し方が明確）。

## 7. 弊害・トレードオフ（リスクと対処）

| リスク | 対処 |
|---|---|
| 古い価格が新しく見える | 上限を48時間にする。出どころを `INHERIT:<id>` で残す |
| 相場検査に二重に入る | 書き込み時の検査（:941）は差し込み位置より前なので入らない。後から来る別投稿の相場は `_MARKET_SQL` で `INHERIT:` の行を外す（3-11） |
| 人が価格を消した行に価格が付く | item_corrections の最新行が空なら引き継がない |
| ダッシュボードの price_ok が増える | 期待どおり（受け入れ基準に入れる） |
| 既に消えている組 | 再解析で直る。再解析は別途 PO の y が要る |
| max_age_hours=48 のとき、引き継いだ価格の元投稿は最大96時間前になりうる | PO が許容（2026-10-15 22時台、PO 原文「y」）。根拠: 本番30日の実測で前の価格の古さは 0.38〜6.38 時間、7件中6件は 5.58〜20.15 時間後に新しい価格の投稿で置き換わり、表示される価格の古さの最大は約49時間。表示される行は received_at の最新投稿で価格の有無を見ない（`backend/app/services/tcg_analyzer_svc.py:1932-1972`）ので、新しい価格の投稿が来れば置き換わる |

確定（recon4〜6）: 本番の max_age_hours は 48（tcg_distribution_settings、2026-09-27 更新）。配信はこれを新しい行の line_posted_at から NOW() までで測る（`backend/app/services/tcg_distribution_svc.py:224`）。投稿時刻の逆転 0 件。supplier_channels の NOT NULL 列は channel・is_active・supplier_id（`migrations/20260921_110000_pipeline_tables_public.sql:11-17`）。frontend は price_basis を使っていない（0件）。

【未確認】（合格を妨げない）: GAS 本体（リポジトリ外）が価格空行をどう扱うか（今回は価格が入るので影響なし）。

## 8. 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | この文書 PR（recon・design・実装カード・台帳）を Draft で起票し、PO が確認 | 文書担当 |
| 2 | 実装 PR の GO（PO。番号つき）を受ける | PO |
| 3 | 実装カードに沿って実装と試験（`backend/app/services/line_analysis_v102_svc.py`、試験、README の1行） | Sonnet |
| 4 | コード審査・CI 緑・マージ | Opus |
| 5 | 反映後、再解析の可否を PO に確認 → 再解析 → KGI の件数を読み取りで確認 | Opus |

戻し方: 実装 PR を revert する。引き継いだ行は `price_basis LIKE 'INHERIT:%'` で特定でき、再解析で元に戻る。DB の列追加なし。

## 9. 維持の仕組み

- 実装 PR で、引き継ぎの条件（48時間・連鎖しない・完売と人の削除は除く）を PG 試験と単体試験にし、CI の backend テストで毎回走らせる。ただしその試験はこの PR には無く、実装 PR で新設される（この PR の時点では守り手のファイルが存在しない）。
- 守り手: 人手で守る（試験ファイルが実装 PR で初めてできるため。実装 PR の設計欄で守り手を試験ファイルに更新する）

## 10. 継続

- 完了後の監視: 反映後に `price_basis LIKE 'INHERIT:%'` の件数と、KGI の組数（目標 0）を読み取りで確認する。
- 次フェーズへの引き継ぎ: 価格の読み取り不具合 3 組（「万」・「＠…円」の書き方）は別テーマとして別の設計にする。

## 11. 審査記録

同一 AI による自己審査で APPROVE（独立した第二者のレビューとは称さない）。設計の合格は、PO の実装承認・マージ・本番反映の承認を兼ねない。
