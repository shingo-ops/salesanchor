# Design: public.products 列 churn 再発防止（tcg_uuid）— 第2便

**対象**: デプロイ失敗 2026-10-04（run 37133284790、`migrations/20260909_000000_public_products_phase2b_columns.sql` ステップ223/317）
**recon**: docs/handoff/products-column-churn-2/recon.md
**日付**: 2026-10-04
**担当**: Opus(設計) / Sonnet(実装)

---

## 外部・過去事例の参照と我々への応用

第1便（docs/handoff/products-column-churn/design.md）で fetch 済みの PostgreSQL 16 公式ドキュメントを再掲・再利用する（同じ仕様がそのまま今回の再発にも当てはまるため、再 fetch はしない）。

- `ALTER TABLE` の Notes（https://www.postgresql.org/docs/16/sql-altertable.html）:
  > The `DROP COLUMN` form does not physically remove the column, but simply makes it invisible to SQL operations... the space occupied by the dropped column is not reclaimed.
- `limits.html`（https://www.postgresql.org/docs/16/limits.html）:
  > columns per table | 1,600 ... Columns that have been dropped from the table also contribute to the maximum column limit.

**我々への応用（再発の教訓）**: 第1便は `condition`/`unit`/`category_classification` の3列を直したが、
`tcg_uuid` という同種の「移行用一時列→後で永久 DROP」パターンを見落とした。原因は、第1便のレビュー手法が
「designer が気づいた列だけ」を対象にした一点集中チェックで、`scripts/run_all_migrations.sh` 全体を
機械的に横断する「ADD している列名」×「DROP している列名」の総当たり照合をしていなかったこと。
本書では recon.md §2 でその総当たりウォークを行い、1600列上限が「他のどの列が原因でも再発しうる」
構造的リスクであることを踏まえ、両方のタイミング的な抜け（628 行目の ADD だけでなく、同一内容を
再掲する 661 行目の ADD も）を洗い出して修正する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `scripts/run_all_migrations.sh` の構文が壊れていない | `bash -n scripts/run_all_migrations.sh` → exit 0 |
| tcg_uuid の無条件再 ADD が無い（2ファイルとも） | `migrations/20260909_000000_public_products_phase2b_columns.sql` と `migrations/20260914_140000_unify_tcg_products_to_public.sql` の diff を目視（本書「変更内容」） |
| 次回デプロイで「Run database migrations」が成功する | 本番デプロイ後の GitHub Actions run 結果を確認（本PRのスコープ外・次回デプロイで確認） |
| フレッシュDB 1周目: 移行データが正しく入る（既存挙動を壊さない） | CI `migration-test-run` ジョブの「変更 SQL 1回目実行」（本PRの2ファイルが対象、§CIカバレッジ参照） |
| フレッシュDB 2周目: 再実行してもエラーなし・新規列が増えない | 同ジョブの「変更 SQL 2回目実行（冪等性テスト）」 |
| 本番 `public.products` の dropped attribute 数が今後増え続けない | 次回デプロイ後に 1543（現状）で固定、以降のデプロイで変化しない（要・次回以降デプロイ後の実測確認、本PRのスコープ外） |
| CI: 全件ドライラン（`migration-full-dryrun`）は本PRの対象ファイルを検証しない（既知のギャップ、第1便と同様） | 下記「CIカバレッジ」セクションで対象ファイルの正規表現マッチを実測確認済み |

---

## 設計方針

recon.md §2 のウォークで判明した唯一の churn 原因は `tcg_uuid` で、2つのファイル
（`migrations/20260909_000000_public_products_phase2b_columns.sql:11` と
`migrations/20260914_140000_unify_tcg_products_to_public.sql:35`）が同一の無条件
`ADD COLUMN IF NOT EXISTS tcg_uuid UUID;` を持つ。片方だけ直すと、直した方がスキップしても
もう片方が無条件に実行されてしまい、同じ attnum 消費が再発する。したがって **両方に同一のガード**
を入れる。

### 選んだパターン: 「後の DROP を過ぎたかどうか」を判定する DO ブロックガード

第1便（PR #3958）は「ADD を削除し、依存箇所を個別にガード／除去」する方式を採った。しかし
`tcg_uuid` は condition/unit/category_classification と異なり、**フレッシュDBの1周目では
本物のデータ移行（tcg_products → public.products のコピー、Phase 2a/2b）に実際に使われる**
列であり、ADD 文を単純に削除すると「フレッシュDB CI の1周目」で移行ロジックそのものが
動かなくなってしまう（コメントアウトされた本体データコピー処理が tcg_uuid を列リストに
含んでいるため）。よって condition/unit 方式（ADD 自体を削除）ではなく、
**「まだ必要なら ADD する／もう不要になったら ADD しない」を判定するガード**を選んだ。

#### マーカー訂正の経緯（2026-10-04、設計担当 Opus の指摘）

初版では「`tenant_*.tcg_products` がどこにも残っていない」をマーカーにしていたが、これは
**本番で実際には成立していない誤った前提**だった。実装担当（Sonnet）はこれを本番未確認のまま
「確認済み」として報告していたが、設計担当 Opus が本番を read-only で確認したところ、
`tenant_004.tcg_products` は**現在も存在する**（`pg_class` 照会で1行確認）。原因は recon.md §3
の通り、Phase 2c の DROP（`migrations/20260915_010000_drop_tcg_products_phase2c.sql`、
`scripts/run_all_migrations.sh:668`）がそれより手前のステップ（第1便の churn・今回の tcg_uuid
churn）で毎回デプロイが失敗していたため、一度も実行完了に到達していないこと。この状態で初版の
マーカーを使うと、本番では「`tcg_uuid` が無い」かつ「`tcg_products` がまだ残っている」という
組み合わせになり、ガードが TRUE（ADD実行）と誤判定し、1600列上限エラーが再発する。

#### 正しいマーカー: `public.products.work_id` が INTEGER かどうか

```sql
IF EXISTS (tcg_uuid 列が既に存在する)
   OR NOT EXISTS (work_id 列が存在し、かつ型が INTEGER)
THEN
    ADD COLUMN IF NOT EXISTS tcg_uuid UUID;
    -- 索引・制約もこのブロック内でのみ作成
ELSE
    -- work_id が INTEGER に再キャスト済み（Phase 3 完了）→ tcg_uuid はもう要らない → 何もしない
END IF;
```

この判定が恒久的に正しい理由を、`migrations/20260919_010000_master_ssot_work_id_recast.sql`
を読んで確認した:
- `migrations/20260919_010000_master_ssot_work_id_recast.sql:38-81`（Step1）: `work_id_old_uuid`
  列が既に存在する場合は RENAME をスキップ（冪等）。存在しなければ `work_id`（UUID）を
  `work_id_old_uuid` にリネームし、NOT NULL を解除する。
- 同ファイル:86-110（Step2）: `work_id` が INTEGER 型で既に存在する場合は ADD をスキップ
  （冪等）。存在しなければ `work_id INTEGER` を新規 ADD する。
- このファイル自身も含め、全 migrations を `grep` した結果（本書「tcg_uuid 以外の churn
  確認」参照の手法を再利用）、`public.products.work_id` を再び UUID 型に戻す／UUID 型で
  再作成する migration は**一件も無い**（`work_id` という名前で UUID 型の ADD が出てくるのは
  `migrations/20260909_000000` と `migrations/20260914_140000` の既存の
  `ADD COLUMN IF NOT EXISTS work_id UUID` のみだが、これは名前が既に INTEGER で存在するため
  `IF NOT EXISTS` が名前一致でスキップし、型には影響しない）。したがって一度 `work_id` が
  INTEGER になれば、**それ以降のどの migration が何回再実行されても INTEGER のまま変わらない**
  ── 恒久的なマーカーとして使える。
- 本番は `work_id` が既に INTEGER（attnum 826、設計担当 Opus が本番 read-only で確認済み）
  のため、本番の次回デプロイではこのマーカーで正しく「もう要らない」と判定され、`tcg_uuid` が
  二度と ADD されない（`tenant_004.tcg_products` がまだ残っていることとは独立に安全）。
- フレッシュDB の1周目では `work_id` 列自体がまだ存在しない（`20260909_000000` 到達時点では
  `20260919_010000` はまだ実行されていない）ため `NOT EXISTS (... data_type='integer')` が
  TRUE になり、ガードは「まだ必要」と判定して元のロジック通り ADD する（regression なし）。

tcg_uuid 列自体の存在チェックを OR で加えているのは、たとえ将来何らかの理由で tcg_uuid が
まだ生きている状態で work_id が先に INTEGER になるような順序になっても、既存列を壊さない
ための安全弁。

このガードを **両方のファイル**（20260909, 20260914）の Step1 に適用し、索引
（`idx_products_tcg_uuid`）と UNIQUE 制約（`uq_products_tcg_uuid`、20260914 のみ）も
同じガードの中に移動した（tcg_uuid 列が存在しない状態でこれらを実行すると
「column tcg_uuid does not exist」で即座に失敗するため）。

Step2/Step3/Step4（データコピー・FK張替え・件数照合）は元から型チェックで自己ガード済み
（`tcg_uuid` が UUID 型で存在しない場合は `RETURN`）であり、変更不要。本番では `tcg_uuid` が
存在しないため、これらは本 PR の変更とは無関係に常に `RETURN` して安全（本書「628〜674の
ウォーク」参照）。

### なぜ他の列は無修正か

recon.md §2 のウォーク表の通り、`tcg_uuid` 以外で ADD→DROP が繰り返される列は無い。
`work_id`・`product_category_id` は「UUID→INTEGER の型スワップ」だが、いずれも
`pg_attribute`/`information_schema` を使った型チェックで二重実行を防いでおり、新しい
列名で ADD されるのではなく **既存の列を RENAME してから別名で再利用する** ため、
一度変換が終われば同じ列名での ADD が `IF NOT EXISTS` の名前一致により永久にスキップされる
（新しい attnum を消費しない）。これは既に第1便の範囲外で正しく設計されている部分であり、
本 PR では触らない。

---

## 変更内容

1. `migrations/20260909_000000_public_products_phase2b_columns.sql` — `tcg_uuid` の ADD と
   その部分ユニーク索引を `DO $guard_tcg_uuid$` ブロックでガード。他6列（division_id,
   work_id, manufacturer_id, product_category_id, category_class, is_active）は無変更
   （いずれも非churning、recon.md §2 参照）。
2. `migrations/20260914_140000_unify_tcg_products_to_public.sql` — Step1 の `tcg_uuid` ADD・
   部分ユニーク索引・UNIQUE 制約を同じ `DO $guard_tcg_uuid$` ブロックでガード。Step2/3/4 は
   既存の自己ガードのみで対応済みのため無変更。

**触らない**: `migrations/20260916_120000_phase_c_drop_tcg_uuid.sql`（DROP側、既存ガード済み）、
`migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`（tcg_uuid を読むが各テーブルの
型チェックで自己ガード済み）、`migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql`
（制約のみ、既存ガード済み）。

---

## 修正後の再ウォーク — attnum 消費 = 0 を示す

### (a) 本番・次回デプロイ

recon.md §2 の表の「tcg_uuid」行のみ変化する:
- line628（20260909）: ガード判定 = `tcg_uuid` 列は現在無い（本番で確認済み、設計担当 Opus）
  AND `public.products.work_id` は INTEGER で存在する（attnum 826、設計担当 Opus が本番
  read-only で確認済み）→ `NOT EXISTS(work_id が INTEGER)` は **FALSE** → 全体の条件
  `FALSE OR FALSE` = **FALSE** → ELSE 分岐（RAISE NOTICE のみ）→ **新規 attnum 消費 0**。
  `tenant_004.tcg_products` が本番にまだ存在するかどうかは、このマーカーの判定には**影響しない**
  （recon.md §3 参照）。
- line661（20260914）: 同じ判定 → 同じ理由で ELSE 分岐 → **新規 attnum 消費 0**。
- line674（20260916）: `DROP COLUMN IF EXISTS tcg_uuid` → 存在しないので no-op。

他の全ステートメント（recon.md §2 の表の残り全行）はいずれも元から「NO」（非allocating）なので
変化なし。**本番・次回デプロイの新規 attnum 消費合計 = 0**。

### (b) フレッシュDB・CI 1周目

- line628: ガード判定 = `tcg_uuid` 列は無い（まだ）AND `work_id` 列自体がまだ存在しない
  （`20260919_010000` はまだ実行されていない）→ `NOT EXISTS(work_id が INTEGER)` は
  **TRUE**（存在しないので「INTEGERで存在する」の否定は真）→ 全体の条件 TRUE → ADD 実行
  → 元の挙動と同一（tcg_uuid が本物のデータ移行用に使われる、regression なし）。
- line661: 同上、`work_id` はまだ INTEGER になっていないので TRUE → 実質 no-op（628 が既に
  ADD済みのため IF NOT EXISTS でスキップ）だが、ガード自体は通る → 既存挙動と同一。
- Phase 2c（`migrations/20260915_010000_drop_tcg_products_phase2c.sql`）が `tcg_products` を全廃
  （tcg_uuid 側のガードとは無関係に、この migration 自身は無変更で実行される）。
- line674: `tcg_uuid` を DROP（1周目の最後、既存挙動と同一）。
- line692（`20260919_010000`）: `work_id` を INTEGER に再キャスト（既存挙動と同一）。
- **1周目終了時点のスキーマ**: `tcg_uuid` 列は存在しない・`work_id` は INTEGER
  （修正前と同じ最終状態）。

### (c) フレッシュDB・CI 2周目（冪等性チェック、1周目適用済みDBへの再実行）

- line628: ガード判定 = `tcg_uuid` 列は無い（1周目で DROP 済み）AND `work_id` は INTEGER
  で存在する（1周目で recast 済み）→ `NOT EXISTS(work_id が INTEGER)` は **FALSE** →
  全体の条件 FALSE → ELSE 分岐 → **新規 attnum 消費 0**。
- line661: 同上 → **新規 attnum 消費 0**。
- line674: `DROP COLUMN IF EXISTS tcg_uuid` → no-op。
- **2周目の新規 attnum 消費合計 = 0**。2周目終了時点のスキーマは1周目と同一
  （`tcg_uuid` 列は存在しない）→ **冪等**。

### 628〜674 の間で `tcg_uuid` を読む全ステップ（本番で `tcg_uuid` が無い場合の挙動）

本番（`tcg_uuid` 列が無い）を前提に、`scripts/run_all_migrations.sh` の line628〜674 の
範囲で `tcg_uuid` を参照する全ステートメントを再確認した。

| line | file:line | tcg_uuid への参照 | 本番（tcg_uuid無し）での挙動 | ガード済みか |
|---|---|---|---|---|
| 628 | `migrations/20260909_000000_public_products_phase2b_columns.sql:18-37`（Step1） | ADD + 索引 | 本PRの新ガードで ELSE 分岐 → 何もしない | ✅（本PRで修正） |
| 628 | 同ファイル:65-144（Step2 bootstrap、`CONTINUE` は:100） | INSERT列リストに tcg_uuid を含む | ループ内で `work_id already INTEGER` を検出した時点で `CONTINUE`（スキップ）。tcg_uuid の有無を見る前にスキップするため無関係 | ✅（既存の自己ガード） |
| 661 | `migrations/20260914_140000_unify_tcg_products_to_public.sql:42-70`（Step1） | ADD + 索引 + 制約 | 本PRの新ガードで ELSE 分岐 → 何もしない | ✅（本PRで修正） |
| 661 | 同ファイル:94-122（Step2 冒頭） | `tcg_uuid` が UUID 型で存在するか確認 | 存在しない → `_tcg_uuid_is_uuid = false` → `RETURN`（Step2全体スキップ） | ✅（既存の自己ガード） |
| 661 | 同ファイル:301-321（Step3 冒頭） | 同上の型チェック | 同様に `RETURN`（Step3全体スキップ） | ✅（既存の自己ガード） |
| 661 | 同ファイル:579-610（Step4 冒頭） | `tcg_products` 全不在チェック→`tcg_uuid`型チェック | `tenant_004.tcg_products` がまだ存在するため1つ目のチェック（:584-591）は通らないが、続く `tcg_uuid` 型チェック（:606-611）で `_tcg_uuid_is_uuid = false` となり `RETURN`（Step4全体スキップ） | ✅（既存の自己ガード・二段目で安全） |
| 671 | `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`（4テーブル分） | `p.tcg_uuid` を JOIN キーに使う行は各テーブルの `ELSE` 分岐内のみ | 各テーブルの `product_id` は本番で既に INTEGER（`work_id` が INTEGER である＝このファイルの後続 migration まで到達済みという事実と整合）→ `IF _atttypid = _int_oid THEN skip` で該当ブロックに入らない | ✅（既存の自己ガード） |
| 674 | `migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:5-7` | `DROP CONSTRAINT/INDEX/COLUMN IF EXISTS` | 全て `IF EXISTS` 済みのため no-op | ✅（既存のガード） |

**結論**: 628〜674 のどのステップも、`tcg_uuid` が本番に存在しない状態で安全に動作する
（エラーなし・新規 attnum 消費なし）。

---

## CI カバレッジ（第1便と同じ既知のギャップ、今回の対象ファイルで再確認）

`.github/workflows/migration-test.yml` の2つの関連ジョブで、本PRが変更する2ファイル
（いずれも `20260909_*`・`20260914_*`、日付は Sept）がどちらに乗るかを実際のファイル名で確認した。

1. **`migration-test-run`**（既存データ付きスキーマ + Sprint1 python script → PR で変更された
   SQL を検出して1回目・2回目実行、`:937` の正規表現 `^migrations/[0-9][0-9][0-9].*\.sql$`）:
   両ファイルとも数字始まりのファイル名のため **マッチする（対象）**。このジョブで本PRの
   両ファイルが「変更SQL」として検出・2回実行される。
2. **`migration-full-dryrun`**（`scripts/run_all_migrations.sh` の全 `run_sql` を記載順に1周目・2周目
   実行、対象ファイル正規表現は `^migrations/0|^migrations/2026060[4-9]|^migrations/2026061|
   ^migrations/2026062`、`.github/workflows/migration-test.yml:1660,1665,1695,1699`）:
   実際にマッチを確認した。
   ```
   migrations/20260909_000000_public_products_phase2b_columns.sql -> EXCLUDED
   migrations/20260914_140000_unify_tcg_products_to_public.sql -> EXCLUDED
   ```
   この正規表現は 2026年6月4日〜6月29日のタイムスタンプ付きファイルのみを対象にしており、
   9月（Sept）日付のファイルはそもそも範囲外。**本PRの2ファイルは全件ドライランの対象外**。

**リスク**: 第1便と同じギャップ。`migration-full-dryrun` は本PRの変更と後続の実在 migration
（`20260915_010000` Phase2c drop・`20260916_120000` tcg_uuid drop）との組み合わせを機械的には
再検証しない。本書 recon.md §2 の手動ウォークがこのギャップを補っている唯一の根拠。
（第1便のギャップ提案と合わせて、`migration-full-dryrun` の対象範囲を拡張する守り手案を
下記「維持の仕組み」に記載）

---

## 変更範囲

| 層 | 変更 |
|---|---|
| migrations（ガード追加） | `20260909_000000` と `20260914_140000` の tcg_uuid ADD/索引/制約を `DO` ブロックでガード |
| migrations（無変更） | `20260915_120000`・`20260916_120000`・`20260916_130000`・`20260919_010000`・`20260920_010000`・`20260922_070000` — いずれも既存の自己ガードで対応済み、触らない |
| docs | `docs/handoff/products-column-churn-2/recon.md`（新規）・`docs/handoff/products-column-churn-2/design.md`（新規） |
| 台帳 | .claude-pipeline/active-work.d/release-stop-products-column-churn-2.md（main checkout に新規作成、このブランチには含めない） |

## 触るファイル

1. `migrations/20260909_000000_public_products_phase2b_columns.sql`
2. `migrations/20260914_140000_unify_tcg_products_to_public.sql`
3. `docs/handoff/products-column-churn-2/recon.md`（新規）
4. `docs/handoff/products-column-churn-2/design.md`（新規・本ファイル）

削除するファイル: 無し（行削除も無し。既存行を `DO` ブロックで包んだのみで、元のステートメントは
そのまま残っている）。

---

## 維持の仕組み

守り手: 以下はアイデア提案のみで未実装（本PRのスコープ外）
- CI に新規ジョブを追加する案:「`scripts/run_all_migrations.sh` に登録されている全 migration を
  静的解析し、ある migration が `ALTER TABLE public.<table> ADD COLUMN <col>` を含み、かつ
  **別の登録済み migration**（登録順が後）が同じ `<table>`.`<col>` に対して無条件の
  `DROP COLUMN` を含む場合、CI を失敗させる」チェック。今回・前回とも「ADD が後の DROP に
  気づかずガード無しで残っていた」ことが根本原因なので、この組み合わせを機械的に検知できれば
  再発を防げる。実装には `ADD COLUMN` と `DROP COLUMN` の対象列名をファイル横断で突き合わせる
  簡易パーサが必要（今回の recon.md §2 の手作業ウォークと同じロジックをスクリプト化するイメージ）。
  静的解析だけでは「ガードされているか」まで判定できないため、まず「組み合わせの存在」を
  検知して人間に警告する形（fail ではなく warning からの段階導入）が安全。
- 第1便から引き続き: `migration-full-dryrun` の対象ファイル正規表現を全日付範囲に拡張する案
  （Python依存の除外ロジックとどう共存させるかは別途検証が必要、提案のみ）。
