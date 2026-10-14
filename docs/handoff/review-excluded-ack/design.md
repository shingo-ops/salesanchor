<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — review-excluded-ack

**対象ADR**: `docs/adr/ADR-144-ui-component-governance.md` / `docs/adr/ADR-067-design-token-enforcement.md` / `docs/adr/ADR-027-ui-internationalization.md`  
**recon**: `docs/handoff/review-excluded-ack/recon.md`  
**前提の設計**: `docs/handoff/review-fix-column/design.md`（#4269、修正列）  
**日付**: 2026-10-14  
**担当**: Planner（Opus）。設計審査は Fable（architect）、実装は Sonnet

---

## 0. PO の依頼と決定（原文）

- 依頼（2026-10-14、#4269 反映後の本番スクショ付き）:「テーブルの行をクリックしても開かない、除外の対象だと意味が不明、何を確認してほしいのかが非エンジニアにも理解できるように出来る？」
- 依頼（同日）:「直す　直したい行を表から押してください→この表記も不要」
- 決定（同日 PO「y」、案 /tmp/CC報告ファイル/review-excluded-proposal.md）: 除外の件で「このままで良い」を押したら一覧から消えるようにする。在庫に出さない判断（除外）はそのまま。

## 1. 目的（KGI）

- K1: スライドで、行を選ぶ前は「直す」見出しも「直したい行を表から押してください」も出ない。行を押すか「このままで良い」を押したときだけ、表の下に直す欄が出る。
- K2: 理由「除外の対象」の件では、赤字の理由のすぐ下に「『<販売状況>』と読んだため、在庫の対象から外しています。合っていれば『このままで良い』、違えば表の行を押して直してください。」が出る（<販売状況> は比較表「販売状況」行と同じ値。例 Sold out）。
- K3: 除外の件で「このままで良い」を押して保存すると、一覧を読み直したときその件は「要確認」タブから消える。「すべて」タブには残る。
- K4: K3 のあとも、その件は在庫（配信）に出ない。
- K5: 理由が2つある件で、1つずつ「このままで良い」を押しても、先に押した方が解析のやり直しで戻ってこない（不具合修正）。

## 2. 変更前 → 変更後

### 変更前（recon §1〜§4）
- 行を選ぶ前も「直す」見出しとヒントが常に出る（`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx` 116-120 行）。
- 「除外の対象」はラベル1語だけ。何を見て除外したのか書いていない。
- 除外の件の「このままで良い」は保存・再解析まで通るが、一覧は除外の印（analysis_results.exclusion）から毎回「除外の対象」を作り直すので、件は要確認に残り続ける（`backend/app/services/tcg_condition_review_svc.py` 204 行、`backend/app/services/tcg_analysis_review_svc.py` 83-85 行・99-102 行）。
- 確認済みは「最新の1行」だけが有効（`backend/app/services/v102_human_decisions_svc.py` 125-132 行）。画面は1理由ずつ送る（`frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx` 95-116 行）。そのため2つ目を押すと1つ目が無効になる。

### 変更後
- 直す欄は、scope が決まったときだけ出す（見出しなし）。
- 除外の件だけ、平易な説明1行を理由の下に出す。
- 一覧は「有効な確認済みの記録に excluded が入っている件」では「除外の対象」を作らない。除外の印そのもの（analysis_results.exclusion）は変えないので、在庫に出さない判断は変わらない。
- 確認済みを保存するとき、その時点で有効な確認済みの理由と合わせて1行に保存する（和集合）。

## 3. backend の変更（DB の列・migrations は変えない）

### 3-1. 一覧の「除外の対象」を確認済みで止める
ファイル: `backend/app/services/tcg_condition_review_svc.py`（review_joins）

- 既存の `cr_event` LATERAL の近くに、次の LATERAL を1つ足す（別名 `cr_review_ack`。`cr_ack_condition` と紛れない名前で、fence の正規表現 `backend/app/services/tcg_condition_review_svc.py` 117 行に当たらない形 `) cr_review_ack ON TRUE` にする。**OFFSET 0 は書かない**＝`backend/tests/test_tcg_condition_review_fenced.py` 50 行の個数 9 を変えない）。中身は「この件の field_name='review_ack' の行のうち、corrected_at・id の降順で最新1行。ただし corrected_at が同じか後の書き写し直し（TRANSCRIPTION_FIELDS の4種）が無いこと」。その行の human_value が JSON オブジェクトで、`v` が 1、`codes` が配列で、**全要素が空でない文字列**で、`'excluded'` を含むときだけ `excluded_acked = TRUE`、それ以外は FALSE。
  - 規則の正本は Python の `load_v102_decisions`（`backend/app/services/v102_human_decisions_svc.py` 106-115 行・125-185 行。最新1行のみ、古い行へ戻らない、cutoff は「書き写し直しの最大 corrected_at 以下は無効」）。SQL はこれと同じ意味にする。
  - FIELD_REVIEW_ACK・REVIEW_ACK_VERSION・TRANSCRIPTION_FIELDS は Python の定数から literal で埋め込み、手書きしない。`backend/app/services/v102_human_decisions_svc.py` 22 行が既に本ファイルを import しているため、review_joins 関数の中で遅延 import する（モジュール先頭で import すると循環する）。
  - human_value の JSON 判定は既存 cr_event と同じ書き方（`IS JSON OBJECT AND pg_input_is_valid(..., 'jsonb')`）。
- 導出の行（204 行）を `CASE WHEN cr_data.ar->>'exclusion' IS NOT NULL AND NOT cr_review_ack.excluded_acked THEN 'excluded' END` に変える。
- 211 行の除外条件にも同じく `OR cr_review_ack.excluded_acked` を足す（ar.review_reasons 側に excluded が入っていた場合も消すため）。
- cr の出力に `cr_review_ack.excluded_acked AS excluded_acked` を足す（試験と将来の参照用。version の digest には入れない＝latest_correction_id で変化は既に拾える）。

### 3-2. 要確認タブの条件
ファイル: `backend/app/services/tcg_analysis_review_svc.py`

- 84 行と 101 行の `ar.exclusion IS NOT NULL` を削る（`(NOT ar.pid_resolved OR NOT ar.unit_resolved OR cr.needs_review)`）。理由: 未確認の除外は 3-1 で cr.needs_review が真になるので同じ件が出る。確認済みの除外だけが外れる。
- NORMAL_COMPLETED（94 行）は変えない（除外の件は確認済みでも「正常完了」ではない。「すべて」タブには出る）。

### 3-3. 確認済みの和集合保存（K5）
ファイル: `backend/app/services/v102_human_decisions_svc.py` の `save_review_ack`

- 手順: (1) `_CURRENT_REASONS_SQL` に `FOR UPDATE` を付けて analysis_results の行をロックして読む（並行保存で前の codes を取りこぼさないため。`backend/app/services/tcg_condition_review_svc.py` 302-303 行の save_condition_review と同じ考え方）。(2) `await db.run_sync(lambda s: load_v102_decisions(s, [extraction_item_id]))` で前の有効な ack_codes を読む（同じ接続・同じトランザクション。前例 `backend/app/services/v102_transcription_svc.py` 386 行）。新しい判定は書かない。(3) `normalize_ack_codes([*sorted(前の ack_codes), *今回の codes])` を1行に保存。
- 書き写し直しの後なら前の codes は無効なので合わせない（load_v102_decisions の規則どおり）。
- 呼び出し元は2つ: `backend/app/routers/item_corrections.py`（画面）と `backend/app/services/tcg_review_csv_svc.py` 257 行（CSV）。どちらにも効く。

### 3-4. 影響する呼び出し元（全走査済み、recon §3）
- `backend/app/services/tcg_distribution_svc.py` 322・432 行: `cr.needs_review IS FALSE AND ar.exclusion IS DISTINCT FROM 'excluded'`。本番の exclusion の値は 'excluded' と NULL だけ（recon §5 実測）なので、確認済みの除外も配信に出ない（K4）。
- `backend/app/services/tcg_import_progress.py` 129 行: review_joins は並び順にだけ使う。要確認の数は ar.needs_review 列（同 32-33・66-67・97 行）なので変わらない。
- `backend/app/services/tcg_analysis_dashboard_svc.py` 470・477 行: ar.exclusion を直接数えるので変わらない。

## 4. frontend の変更

ファイル: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx`

- 116-130 行: `scope === null` のときは `<section className="review-item-fix">` ごと出さない。scope があるときは見出し `<h3>` を出さずに ReviewFixWizard だけを出す。
- 理由の `<li>` で、`detail.code === "excluded"` のとき、ラベルの下に説明1行 `t("reviewItem.excludedHelp", { status })` を出す。`status` は `item.system.status`。空なら `t("reviewItem.excludedHelpNoStatus")` を出す。
  - 部品は既存の `<p>` とトークンだけ（GapSuspectNote と同じ並べ方）。新しい色・余白の直値なし。新しい金型なし。
- 使わなくなる i18n キー `reviewItem.fixHeading`・`reviewItem.pickRowHint` は ja/en から消す（他で使っていないことを grep で確認してから）。
- 既存試験 `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx` 106・159・185 行の「Select the row you want to fix in the table」の断言は、「直す欄が無い」断言に書き換える。

## 5. 文言（i18n。ja/en 同一キー、ADR-027）

| キー | ja | en |
|---|---|---|
| reviewItem.excludedHelp | 「{{status}}」と読んだため、在庫の対象から外しています。合っていれば「このままで良い」、違えば表の行を押して直してください。 | Read as "{{status}}", so this item is kept out of stock. If that is right, choose "Keep as is"; if not, select a row in the table to fix it. |
| reviewItem.excludedHelpNoStatus | 販売状況から、在庫の対象から外しています。合っていれば「このままで良い」、違えば表の行を押して直してください。 | Kept out of stock because of its sale status. If that is right, choose "Keep as is"; if not, select a row in the table to fix it. |

- en の「Keep as is」は既存 `reviewItem.wizard.choice.keep` の en 原文に合わせる（実装時に原文を確認して同じ語にする）。
- reviewReason ブロックは変えない（backend の写し `backend/app/data/review_reason_labels_ja.json` の再生成は不要）。

## 6. 対象と対象外
- 対象: 上の 3・4・5 のファイルと、その試験。
- 対象外: migrations/、DB の列、除外の判定そのもの（状態マスタ）、他の理由コードの説明文（今回は除外のみ。PO の例が除外のため）、数量・価格の行の修正。
- 行を押しても開かない件: origin/main 758d84e8d で、本番と同じデータ・1280/390 幅の実ブラウザでは再現しなかった（recon §1）。今回はコードを変えず、PO の目視で再確認する。

## 7. 代替案と選択理由
- 案A（analysis_results に確認済みの列を足す）: migrations/ が要る＝PO 本人の GO 待ち、再解析での保持の設計も要る。不採用。
- 案A'（解析で excluded を review_reasons に書く）: 既存 1,413 行（本番、recon §5）は再解析するまで一覧から消えてしまう。不採用。
- 案B（採用）: 一覧が確認済みの記録を読む。列追加なし、既存の記録の形のまま。規則の二重実装は 3-1 の試験（Python の読み手と SQL が同じ件で同じ答えを出す）で守る。

## 8. 外部・過去事例の参照と我々への応用
- 該当事例なし。理由: 社内の一覧の条件と記録の読み方の修正で、外部の数値事例が判断を変えない。過去の自社事例として、一覧の速度設計（docs/handoff/review-speed/design.md）の「行ごとの LATERAL は重い」を参照し、速度を 10 で測る。

## 9. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K1 行選択前に直す欄が無い | vitest: ReviewItemDrawer を描画し「直す」「直したい行を表から押してください」が無いこと。行を押すと ReviewFixWizard が出ること |
| K2 除外の説明 | vitest: excluded の件で「『Sold out』と読んだため」が出る。status 空で NoStatus 文言 |
| K3 確認済みの除外が要確認から消える | pytest（PG）: exclusion='excluded' の件 → NEEDS_REVIEW に出る → review_ack(excluded) 保存 → NEEDS_REVIEW に出ない・ALL に出る |
| K3 書き写し直し後は戻る | pytest（PG）: ack の後に v102_lines の訂正 → 再び NEEDS_REVIEW に出る |
| K4 配信に出ない | pytest（PG）: 確認済みの除外の件が配信行 SQL に出ない |
| K5 和集合 | pytest（PG）: excluded を ack → note_unmatched を ack → 最新行の codes が両方 / load_v102_decisions の ack_codes が両方 |
| K5 CSV 経路 | pytest: CSV の確認済み保存でも和集合になる |
| SQL と Python の規則一致 | pytest（PG）: 有効・書き写し後・同時刻の書き写し・v≠1・壊れた JSON・codes に空文字・codes に数値 の7件で、SQL の excluded_acked と Python の ack_codes に excluded が入るかが一致 |
| 既存試験 | backend: test_v102_human_decisions*.py, test_tcg_condition_review*.py, test_tcg_analysis_review.py, test_tcg_distribution* が緑。frontend: tcg-analysis-review 配下の試験が緑 |
| i18n | ja/en 同一キー（CI） |
| 速度 | 11 の方法で、変更前後の要確認一覧1回分（count・providers・items の3クエリ）の実行時間が 1.2 倍以内 |

## 10. リスクと対処
- 一覧が重くなる: LATERAL が1つ増える。item_corrections の extraction_item_id 索引で引く（既存 cr_event と同じ）。デプロイ後に 11 で測り、1.2 倍を超えたら戻す。
- 規則のずれ（SQL と Python）: 9 の一致試験で守る。
- 並行保存: 3-3 の行ロックで守る。
- 和集合で、既に解消した理由まで記録に残る: 害は無い（理由が無ければ外すものが無いだけ）。

## 11. 戻し方・測り方
- 戻し方: この PR を revert（DB・データの変更なし）。確認済みの記録は従来から item_corrections に書く形のまま。
- 測り方: デプロイ後、本番で読み取り専用に (1) 要確認の件数（タブ NEEDS_REVIEW の total）、(2) exclusion='excluded' かつ is_current の件数を取り、(1) が変わっていない（まだ誰も確認済みにしていないため）ことを確認。速度は、マージ前に Sonnet が変更前後の3クエリの SQL 文字列を Python から出力し、Opus が本番で読み取り専用に EXPLAIN ANALYZE を取って比べる（要確認タブ・1ページ目・既定の並び）。1.2 倍を超えたらマージしない。

## 12. 計画票
1. Sonnet: 3-1〜3-3 backend と試験（PG 試験含む）。
2. Sonnet: 4・5 frontend と試験。
3. Fable: コード審査。
4. PR → CI → 委譲 GO（例外パスなし）→ マージ → デプロイ確認 → 本番で 11 の測定。

## 維持の仕組み
- 規則一致: 9 の PG 試験（`backend/tests/test_v102_human_decisions_pg.py` に追加）。守り手: `backend/tests/test_v102_human_decisions_pg.py`
- i18n: CI の ja/en 同一キー検査。守り手: 人手で守る（既存 CI）

## 13. 設計審査（Fable）REVISE への対応
- 1回目 REVISE（2026-10-14）の6点を反映: codes 全要素の検査と一致試験7件（3-1・9）／定数の遅延 import（3-1）／別名 cr_review_ack と OFFSET 0 を書かない（3-1）／和集合の手順・行ロック・順序・CSV 経路（3-3・9）／進捗の記述訂正（3-4）／既存 vitest の書き換え（4）。任意の速度基準も3クエリ・マージ前測定に変更（9・11）。
- 2回目 APPROVE（2026-10-14）。書き損じ cr_ack → cr_review_ack を統一。analysis_results に行が無い件の保存挙動は変えない（404 にしない）。
