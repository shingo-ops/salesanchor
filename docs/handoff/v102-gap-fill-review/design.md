# design: v102 取りこぼし疑いを要確認の理由にし、間の行番号を画面に出す（段2a）

- 状態: 設計案（Opus 作成・自己審査済み。独立した第二者レビューではない）
- PO の決定（原文）:
  - 「D2を採用、追加で商品がマスタから特定できなかった場合は要確認に回し、理由としてはgeminiの取りこぼしの疑いがあるとして間の行番号を見える状態で提出できる？」
  - 「抽出されなかったブロック感の行番号を全て対象にする」
  - 「要確認に回す条件は価格と数量の記載がある場合、商品名だけ記載ある場合でも価格と数量がなければトラない」
  - 2026-10-12「離席するので、このセッションだけで最後まで完結させる」「PRマージ、デプロイまで完走させてくれ」
- 現在地: [recon.md](recon.md)（docs/handoff/v102-gap-fill-review/recon.md）
- 前の段: docs/handoff/v102-gap-detect-record/design.md（段1。記録の形と規則 H2）
- 対象ADR: ADR-154（:70 配信は needs_review=false のみ）、ADR-1007（値は1回だけのデータ変更）、ADR-027（UI 文字列は t()）、ADR-144（UI は金型）、ADR-135・ADR-136（この段は migration を含まない）

## 1. 目的（利用者に見える変化）
1. Gemini が件と件の間の行を使わず、商品が決まらなかった件（価格と数量はある）に、要確認の理由「Gemini取りこぼし疑い」が付く。
2. 要確認の件を開くと、その件に効く間の行番号（例: L14）と、間の行から見つかった商品の候補（あれば）が見える。
3. 理由の出どころは「書き写し（extraction）」なので、その投稿は書き写しを直す投稿の一覧（v102 投稿の画面）にも出る。

配信・集計リストは変えない（§3 で証明）。

## 2. 設計の選択（Fable 案からの変更）
- Fable 案の段2a は「候補が1つなら商品を当てて matched にする（要確認のまま）」だった。
- recon.md §4 の本番の読み取りで、matched（pid_resolved=TRUE）にすると、最新の行の順位付け（`backend/app/services/tcg_analyzer_svc.py:1744-1879`）に入る。そのため、同じ仕入れ先の今配信中の行が要確認の行に置き換わり、集計リストから消える恐れがある、と分かった。投稿 6e135e76 では、候補1つの 9件すべてに該当した。
- よって段2a では商品を当てない。候補は段1の記録（`extraction_jobs.system_review_detail`）にだけあり、画面で人に見せる。人は既存の商品の訂正（`item_corrections.py:127-169`）で決める。
- 商品を自動で当てるのは段2b（配信に影響するので、基準と GO は PO が決める）。
- 案の比較:

| 案 | 配信への影響 | データの置き場 | 採否 |
|---|---|---|---|
| A. 候補1つを matched にする（Fable 案） | あり（今の配信の行が消える恐れ。recon §4） | analysis_results | 不採用（段2b で PO 判断） |
| B. product_id だけ書き pid_resolved=FALSE | 無し。ただし「product_id あり・未解決」という今は無い組み合わせを作る | analysis_results | 不採用（新しい状態の影響を調べ切れていない） |
| C. 理由の種類だけ足し、候補は段1の記録から画面に出す | 無し（§3） | 理由＝analysis_results.review_reasons（既存）・行と候補＝system_review_detail（段1、唯一の置き場） | **採用** |

## 3. 配信が変わらないことの根拠
- 理由を足すのは、段1の対象の件だけ（`backend/app/services/v102_gap_lines.py:146-151`：`match_status == "unmatched"`、価格と数量の写しあり）。
- unmatched の件は `line_analysis_v102_svc.py:592` で matched=False → :607 で `product_id=None`・`pid_resolved=False`。
- 配信は `ar.pid_resolved = TRUE` が条件（`tcg_distribution_svc.py:290`・:361）。最新の行の順位付けも `pid_resolved = TRUE` の行だけ（`tcg_analyzer_svc.py:1744-1879`）。
- よって、この理由が付く件は、今も変更後も配信にも順位付けにも入らない。product_id・pid_resolved・is_current は変えない。

## 4. 変更（PR を2つに分ける。データ変更は PR-A のマージ前）

### PR-A（解析：理由の種類を足す。コードのみ）
1. `backend/app/services/line_analysis_v102_svc.py`
   - 定数 `REASON_GEMINI_GAP_SUSPECT = "gemini_gap_suspect"` を、既存の `REASON_VALUE_OUT_OF_RANGE` 等の定数の隣に置く。
   - 新しい関数 `_with_gap_reasons(items: list[dict], detail: dict | None) -> list[dict]`（純粋。元の件は変えない）
     - detail が None なら items をそのまま返す。
     - `detail["gap_name"]` の各要素を gemini_index で引く（gemini_index が None の要素は使わない）。
     - rejected でない件のうち、gemini_index が引ける件の review の最後に、次の1要素を足す。
       `{"kind": REASON_GEMINI_GAP_SUSPECT, "line": 件の price_line, "lines": 要素の gap_lines, "candidates": 要素の candidates, "source": SOURCE_SYSTEM}`
     - 例外が出たら logger.exception に記録し、items をそのまま返す（`_gap_detail` :263-272 と同じ扱い。解析を止めない）。
   - `run_v102_pipeline` :305 を次のように変える。
     - 変更前: `return {**fields, "v102_gap_detail": _gap_detail(fields, ctx, masters)}`
     - 変更後: `detail = _gap_detail(fields, ctx, masters)` の後、`return {**fields, "v102_items": _with_gap_reasons(fields["v102_items"], detail), "v102_gap_detail": detail}`
   - 段1の記録（`v102_gap_detail`）は、理由を足す前の件から作る。そのため中身は今と同じ。
2. 理由コードの3点セット（`backend/tests/test_review_reason_codes_consistency.py` :60・:66・:71 がそろいを検査）
   - 新規 `docs/handoff/v102-prod-switch/data/review_reason_codes/seed_20261012_gemini_gap_suspect.sql`：`('gemini_gap_suspect', 'system', 'extraction')`
     - fix_stage を extraction にする理由：原因は書き写しの抜け。`v102_transcription_svc.py:47` により、書き写しを直す投稿の一覧に出る。
   - `frontend/src/locales/ja.json`・`en.json` の `reviewReason.gemini_gap_suspect`
     - ja: 「Gemini取りこぼし疑い（間の行に商品名がある可能性）」
     - en: 「Possible Gemini omission (gap lines may hold the product name)」
   - `test_review_reason_codes_consistency.py` の `_code_side_constants()` に `REASON_GEMINI_GAP_SUSPECT` を足す。
3. 1回だけのデータ変更 SQL（同じディレクトリ。前例 up_*.sql の型を写す）
   - `gs_precheck.sql`（ROWS|36・HAS_NEW|0）
   - `gs_dryrun.sql`（INSERTED|1・CHECK_OK 1・ROWS_OK 37・ROLLBACK）
   - `gs_commit.sql`
   - `gs_verify.sql`（gemini_gap_suspect|system|extraction・ROWS|37）
   - `gs_rollback.sql`
   - README に記録欄
4. 試験（`backend/tests/test_line_analysis_v102_svc.py`）
   - 対象の件に要素が1つ足され、lines と candidates が段1の記録と同じ。
   - 対象でない件・rejected の件・detail が None のときは変わらない。
   - `_analysis_values` で `needs_review=True`・`pid_resolved=False`・`product_id=None`、`review_reasons` に gemini_gap_suspect が入る。
   - `_with_gap_reasons` が例外のとき items が変わらない。
5. `docs/specs/line-analysis-tuning/README.md` に1行。

### データ変更（PR-A の CI 合格後・マージ前に1回）
- gs_precheck → gs_dryrun → gs_commit → gs_verify を本番で実行し、README に記録する（ADR-1007。前例：便G の gt_* を本 PR マージ前に Opus が実行）。
- 先に入れる理由：コードが先に出ると、表に無いコードで「このままで良い」が拒否される（`item_corrections.py:177-206` の検査）。行が先にあっても、使われないだけで害は無い。

### PR-B（画面：間の行番号と候補を見せる。コードのみ。PR-A の本番反映を確かめてから）
1. backend
   - `backend/app/services/v102_gap_lines.py` に純粋関数 `gap_suspects_by_item(stored: Mapping | None) -> dict[str, dict]` を追加する。
     - 段1の記録（v1）から `{extraction_item_id: {"gap_lines": [...], "candidates": [...]}}` を作る。
     - 版が 1 でない、または形が違うときは空の辞書を返す。
     - 記録の形の持ち主はこのファイルだけにする（SSOT）。
   - `backend/app/services/tcg_analysis_review_svc.py` の一覧 SQL（:147-327）に `ej.system_review_detail` を足す。
     - 件ごとに `gap_suspect = {"gap_lines": [...], "candidates": [{"product_id", "name"}]}` を作る。該当なしは None。
     - 候補の商品名は、同じ SQL が今 system の商品名に使っている列を、`public.products` から id でまとめて1回引く（新しい名前の置き場を作らない）。
   - `backend/app/routers/tcg_analysis_review.py` `AnalysisResultItem`（:85-96）に `gap_suspect: GapSuspect | None = None`。
   - `backend/app/services/v102_transcription_svc.py`（:32 の SELECT と :233）と `backend/app/routers/tcg_v102_posts.py` の PostItem に、同じ `gap_suspect`。
   - API の型の生成（CI「API contract is up to date」）を更新する。
2. frontend
   - 新規 `frontend/src/features/tcg-analysis-review/GapSuspectNote.tsx`（props: gapLines・candidates）。
     - 表示は `t("reviewItem.gapLines", { lines })` と `t("reviewItem.gapCandidates", { names })`。
     - lines は `t("reviewItem.gapLineNumber", { n })` を `t("reviewReason.separator")` でつなぐ。
     - 部品は既存の金型（Stack 等）と既存のトークンだけを使う。色の直値・生の要素の新しいスタイルは使わない。
   - `ReviewItemDrawer.tsx` の理由の表示（:71-95）と `V102PostEditModal.tsx` の件の理由（:204-205 付近）で、code が gemini_gap_suspect で gap_suspect があるときに GapSuspectNote を出す。
   - i18n：`reviewItem.gapLines`「間の行: {{lines}}」、`reviewItem.gapLineNumber`「L{{n}}」、`reviewItem.gapCandidates`「候補: {{names}}」（en も同じ鍵）。
     - `reviewReason.*` に置かない理由：整合テスト :60 が `reviewReason` の鍵を seed のコードと一致させるため。
   - 試験：GapSuspectNote と Drawer の表示（vitest）。
3. 戻し方：PR-B の revert（PR-A とデータは残っても、理由の名前が出るだけ）。

## 5. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| 1. 保存済み応答 1,021 回で、変更前後の違いが「対象の件の review に gemini_gap_suspect の要素が1つ増える」ことだけ（他の項目・他の件・post_review・段1の記録の違いは 0） | stage1-parity の不変の道具で前後を比べる（Sonnet が実行、Opus が結果を確認） |
| 2. 1,021 回で、足された要素の数＝段1の記録の gap_name の要素の数 | 同上 |
| 3. 1,021 回で、needs_review が false→true に変わる件の数を数えて記録する。pid_resolved・product_id の違いは 0 | 同上（`_analysis_values` を前後で計算） |
| 4. CI 全緑（整合テスト・PG 試験を含む） | gh pr checks |
| 5. 本番の表に gemini_gap_suspect が1行（ROWS 37） | gs_verify.sql |
| 6. 反映後の新しい v102 投稿で、gemini_gap_suspect の件の数＝その投稿の system_review_detail の gap_name の要素の数。その件はすべて needs_review の理由に含み、pid_resolved=FALSE | 本番の読み取り SQL |
| 7. 反映の前後で、配信の対象の件数の計算（`fetch_preview_data` と同じ条件）に、この理由による違いが無い | 本番の読み取り：gemini_gap_suspect を持つ件のうち pid_resolved=TRUE の件が 0 |
| 8. PR-B：要確認の件を開くと「間の行: L14」と候補の商品名が出る | vitest（表示）＋本番の API の値の元（system_review_detail）の読み取り。画面の実機確認は PO の作業として記録 |

## 6. 危険と対処
- 対象の件で、人が前に「このままで良い」で product_not_in_master を外していた件は、再解析で gemini_gap_suspect が新しく付き、要確認に戻る。配信は変わらない（§3）。数は受入3で数える。
- 書き写しを直す投稿の一覧（`v102_transcription_svc.py:47`）に出る投稿が増える。これは目的（§1-3）。
- `_with_gap_reasons` の失敗で解析が止まる → 例外を握って件を変えずに返す（試験あり）。
- 画面の候補の商品名の取得が重い → 一覧の1回の要求につき、候補の id をまとめて1回だけ引く。

## 7. 維持の仕組み
- 守り手:
  - `backend/tests/test_review_reason_codes_consistency.py`（コード・seed・ja/en のそろい）
  - `backend/tests/test_line_analysis_v102_svc.py`（理由の付き方と配信に入らないこと）
  - `backend/tests/test_v102_gap_lines.py`（記録の形の読み取り）
- 記録の形の持ち主は `v102_gap_lines.py` だけ。画面の行番号の唯一の読み元は `extraction_jobs.system_review_detail`。

## 8. 外部・過去事例の参照と我々への応用
- 過去事例（社内）：便G（PR #4127）で理由コード4つを、同じ「seed＋i18n＋定数＋本番1回の SQL（マージ前に実行）」の型で入れ、本番で問題なし（README の gt_* の記録：INSERTED 4・ROWS_OK 35・VERIFY_DONE）。今回も同じ型を使う。
- 外部事例：該当なし。理由は、社内の既存の型をそのまま使う変更で、新しい技術の選択を含まないため。

## 9. 審査（Architect・Opus 自己審査）
- 判定: APPROVE（PR-A・データ変更・PR-B）
- 根拠：
  - 配信不変を、コードの条件（§3）で示した。
  - 置き場は既存の2か所（理由＝analysis_results、行と候補＝system_review_detail）で、新しい置き場を作らない。
  - 理由コードの追加は既存の型と整合テストで守られる。
- 未解決：画面の実機での見え方は PO の確認が要る（受入8）。段2b（商品を自動で当てる・配信）は PO の判断。
