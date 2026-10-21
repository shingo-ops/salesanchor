# 実装カード 便1: 要確認一覧の取得を1本にまとめる＋見え方（2026-10-21 Opus 作成）

- 設計: docs/handoff/review-speed/design.md §10-5〜10-8（main 674fe62ce 以降）、ADR-1023 改訂 2026-10-21（コミット済み）
- PO 実装承認: 2026-10-21「1」（品質指示つき: 推測禁止・配線とDBのSSOT厳守・データ分散禁止・金型とデザイントークン厳守・金型外のハードコード禁止・不明点は止まって聞く）
- 調査の材料（repo 外）: /tmp/CC報告ファイル/review-bin1-recon/SUMMARY.md と同ディレクトリの写し
- 行番号は origin/main（2026-10-21 時点）。着手時に `git show origin/main:<path>` で再確認し、ずれていたら新しい行番号で読み替える（中身が違えば NEEDS_DECISION）。

## 0. 守ること（違反したら止まって BLOCKED / NEEDS_DECISION で報告）
1. 作業場所: `bash scripts/new-worktree.sh release/review-speed-bin1 --claude`。その worktree の中だけで作業。`./scripts/dev/executor-preflight.sh || exit 1` を最初に実行。
2. 触ってよいファイルは §8 の一覧だけ。DB・migrations・deploy.yml・本番 scripts・nginx は触らない。
3. 新しい表・列・置き場所を作らない。投稿日は既存の `sm.line_posted_at` を読むだけ。
4. UI は金型だけ（Button / SelectControl / ContentToolbar / Stack）。生 select・生 input・色や寸法の直値・インライン style の新規追加は禁止。文字はすべて `t("…")`、ja.json / en.json は同じキー。
5. 今の道（§3）の SQL 文字列は1文字も変えない。§5-1 のスナップショット試験で証明する。
6. マージしない。PR を出したら DONE で報告して止まる。生出力はファイルに保存してパスを書く。推測で埋めない。

## 1. やること（要約）
- API に引数を2つ足す（既定は従来）。`status_tab="NEEDS_REVIEW"` かつ `order="posted_desc"` かつ `extraction_item_ids is None` のときだけ、新しい1本の SQL（S1）＋ JIT をその1本だけ切る（S2）＋ 24時間の絞り F3 形（S3）で取る。
- 要確認タブ（production）だけ: 24時間ボタン（既定 ON）・件数 25/50/100（既定 25）・常に新しい順・日付欄を投稿日時に。
- 確認済みタブ（acked）は何も変えない（20件・引数なし・日付欄も今のまま）。

## 2. バックエンド

### 2-1. ルーター backend/app/routers/tcg_analysis_review.py
- GET /tcg/analysis-results の handler（:128-177、limit 引数 :133）に引数を2つ足す。書き方は同じ関数の既存の引数（Query の使い方）に合わせる。
  - `order: Literal["default", "posted_desc"] = "default"`（範囲外は 422）
  - `posted_within_hours: int | None`（ge=1, le=720、既定 None）
- :155-168 の fetch_analysis_results 呼び出しに `order=order, posted_within_hours=posted_within_hours` を足す。:146-153（不正 status_tab→ALL、extraction_item_ids 時の ALL 強制）は変えない。
- 応答型（:103-110）は変えない（posted_at は既に :91 にある）。
- openapi.json（frontend/api-contract/openapi.json）は便0 と同じく CI と同じ Python 3.12・requirements.txt で再生成する（追加だけになることを diff で確認）。

### 2-2. サービス backend/app/services/tcg_analysis_review_svc.py
- fetch_analysis_results（:193-207）の署名の末尾に `order: str = "default", posted_within_hours: int | None = None` を足す。docstring に「order / posted_within_hours は新しい道でだけ効く。他の道では無視する（要確認画面の要確認タブだけが送る）」と書く。
- :225-227 の直後で分岐:
  ```python
  if status_tab == "NEEDS_REVIEW" and order == "posted_desc" and extraction_item_ids is None:
      rows, total, providers = await _fetch_needs_review_posted_desc(db, src=src, base_from=base_from, where=where, params=params, offset=offset, limit=limit, posted_within_hours=posted_within_hours)
  else:
      （今の :229-311 をそのまま。文字列は変えない）
  ```
  その後の :313-405（reason_table・suspects・decisions・items 組み立て・strip_raw_text・works・戻り値）は両方の道で共有する。コードの重複を作らないこと（同じ items 組み立てを2つ書かない）。
- 列リストの共有（SSOT）: 今の items_sql の SELECT 列（:253-297）と eat LATERAL（:300-306）を、文字列として**一字一句同じ**になる形でモジュール内の1か所（関数か定数）へ切り出し、今の道と新しい道の両方がそれを使う。今の道の最終 SQL 文字列が変わらないことは §5-1 で証明する。W25（下記）の列リストを手で写さない。
- 新しい関数 `_fetch_needs_review_posted_desc`（W 形。原型は /tmp/CC報告ファイル/review-bin1-recon/W25_sql.sql、本番実測 1.12〜1.14秒）:
  ```sql
  {src}
  , base AS MATERIALIZED (
      SELECT
          row_number() OVER (ORDER BY sm.line_posted_at DESC NULLS LAST, sm.id ASC, {result_order_sql()}) AS rn,
          {共有の列リスト}
      {base_from}
      {共有の eat LATERAL}
      {where}{窓の条件}
  )
  , meta AS (
      SELECT count(*) AS total,
             COALESCE(json_agg(DISTINCT provider ORDER BY provider) FILTER (WHERE provider IS NOT NULL), '[]'::json) AS providers
      FROM base
  )
  SELECT meta.total AS meta_total, meta.providers AS meta_providers, base.*
  FROM meta LEFT JOIN base ON base.rn > :offset AND base.rn <= :offset + :limit
  ORDER BY base.rn
  ```
  - 窓の条件（S3、posted_within_hours が None でないときだけ）: `" AND (sm.line_posted_at + interval '0 second') >= now() - make_interval(hours => :posted_within_hours)"`。where は NEEDS_REVIEW なので必ず "WHERE …" で始まる（`assert where.startswith("WHERE ")` を置く）。
  - コメントに理由を残す（設計 §10-4・§10-6 S3）: 「+0秒を足すのは、素直な比較だと索引の見積りが1行になり本番で55秒かかったため（2026-10-20 実測）。消さないこと」。
  - 結果: 1行目の meta_total / meta_providers から total と providers（list[str]）を取る。json の列はドライバによって文字列で返る（asyncpg は既定で json を復元しない）ので、str なら `json.loads` する。どちらで返るかは 5-2 の PG 試験で確かめる。ページが空のときは base 側が NULL の1行だけ返るので、`extraction_item_id is None` の行は rows から除く。
  - params は `dict(params, limit=limit, offset=offset, v102_prefix=V102_PROMPT_VERSION_PREFIX)` に、窓があるときだけ `posted_within_hours` を足す。
  - 仕入元の名前: 今の道は `COALESCE(ps.name, '不明')` の DISTINCT を `ORDER BY name`。新しい道は列リストの `provider`（同じ COALESCE）を使うので同じ値・同じ照合順になる。
- S2（JIT をその1本だけ切る）: PostgreSQL のときだけ（`backend/app/auth/dependencies.py:451-459` の公開関数 `is_postgresql(db)` を使う。:317-327 の私的関数は呼ばない）、1本の前後で:
  ```python
  prev_jit = (await db.execute(text("SELECT current_setting('jit')"))).scalar_one()
  await db.execute(text("SELECT set_config('jit', 'off', true)"))
  rows = (await db.execute(text(sql), p)).fetchall()
  await db.execute(text("SELECT set_config('jit', :v, true)"), {"v": prev_jit})
  ```
  例外時は戻さない（is_local=true なのでトランザクション終了で元に戻る）。コメントに理由（本番 EXPLAIN で JIT の準備に時間を取られた、設計 §10-4）を書く。
- W25 との突き合わせ（必須・最初の生出力）: 新しい関数が作る SQL を、W25 と同じ値（v102_prefix='v102:'、24、offset 0、limit 25）で文字列化し、W25_sql.sql と diff を取ってファイルに保存。許される差は「空白・改行」「パラメータの書き方（:name とリテラル）」「`meta_total`/`meta_providers` の別名」だけ。それ以外（列・JOIN・WHERE・ORDER の違い）が1つでもあれば NEEDS_DECISION で止まる。

## 3. 変えない（今の道のまま）
- CSV tcg_review_csv_svc.py:75、シート tcg_review_sheet_svc.py:108（collect_review_rows）、配信 tcg_distribution_svc.py:858-863（collect_review_rows 経由）、SupplierDetailView、InventoryRowDrawer、他タブ、確認済みタブ。これらは新しい引数を渡さない。
- `_base_from()`（:66-77）・`_BASE_FROM`（:80）・`_NEEDS_REVIEW_COND`（:88-91）・`_build_where`（:94-156）・`result_order_sql`（tcg_result_order.py:18-42）・tcg_condition_review_svc.py は変えない。

## 4. フロントエンド frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx（:1-257）
- 定数（:26 の PAGE_SIZE の近く）: `PAGE_SIZE = 20` は確認済みタブ用にそのまま残す。要確認タブ用に `PRODUCTION_PAGE_SIZES = [25, 50, 100] as const`（既定は先頭）と `FRESH_WINDOW_HOURS = 24` を足す（この2つは画面の中でこの1か所だけ）。
- 型 NeedsReviewItem（:36-54）に `posted_at: string | null` を足す。
- state: `freshOnly`（既定 true）、`productionPageSize`（既定 25）。どちらかを変えたら offset を 0 に戻し、ドロワーは閉じない（changeTab :200-207 と違い、タブは同じため）。
- 取得 useEffect（:96-134）: production のときだけ URLSearchParams に `order=posted_desc` を足し、`freshOnly` なら `posted_within_hours=String(FRESH_WINDOW_HOURS)` を足す。limit は production なら productionPageSize、acked なら PAGE_SIZE。依存配列に freshOnly・productionPageSize を足す。acked の params は今と1文字も変えない。
- DataTable（:230-239）の page / onPageChange の計算は、今のタブの件数（production なら productionPageSize、acked なら PAGE_SIZE）を使う。
- 計時（:90-94）: pageSize に production の件数を渡す（便0 の受け口は 20/25/50/100 を受ける、router :246）。
- 操作台（production タブのときだけ、CSV の Card :221-226 の後・表示中の文字 :227 の前）:
  ```tsx
  <ContentToolbar left={
    <Stack direction="row" gap="2">
      <Button variant={freshOnly ? "primary" : "secondary"} size="sm" layoutClassName="field-h-md" type="button"
        data-testid="needs-review-fresh-toggle" aria-pressed={freshOnly} onClick={…}>
        {t("needsReview.freshOnly", { hours: FRESH_WINDOW_HOURS })}
      </Button>
      <SelectControl size="sm" className="field-h-md" data-testid="needs-review-page-size"
        aria-label={t("needsReview.pageSize")} value={String(productionPageSize)} onChange={…}
        options={PRODUCTION_PAGE_SIZES.map((n) => ({ value: String(n), label: t("needsReview.pageSizeOption", { n }) }))} />
    </Stack>
  } />
  ```
  props の名前・型は frontend/src/components/ContentToolbar.tsx・Stack.tsx・Button.tsx・Select.tsx の実物に合わせる（上の書き方は InventoryToolbar の前例 :68-97 の写し）。実物の props と合わず金型の変更が要るなら、金型を変えずに NEEDS_DECISION。
- 日付欄（:177-190）: production タブのときだけ `item.posted_at` を `formatDate(item.posted_at, i18n.language)` で出す（null は "—"、例外時は今と同じく元の値）。acked タブは今の中身（gemini.span）のまま。見出しキー needsReview.createdAt（「日時」/「Date」）は変えない。
- i18n（ja.json / en.json の needsReview、:5471-5495。両方同じキー）:
  - `freshOnly`: 「{{hours}}時間以内」/「Last {{hours}} h」（inventory.view.freshOnly ja/en :1475 と同じ言い方）
  - `pageSize`: 「表示件数」/「Rows per page」
  - `pageSizeOption`: 「{{n}}件」/「{{n}} rows」（変数名は n。count にすると i18next の複数形の決まりが働くため）

## 5. テスト

### 5-1. 今の道が変わらない証明（新規 backend/tests/test_tcg_analysis_review_sql_snapshot.py）
- 実 DB を使わず、`db.execute` に渡された SQL 文字列を記録するだけの偽セッションで fetch_analysis_results を呼ぶ（既存の mock の作り方 test_tcg_analysis_review.py に合わせる）。
- 組み合わせ: (status_tab=ALL, limit 5000) / (NEEDS_REVIEW, limit 5000) / (NEEDS_REVIEW, limit 20, offset 20) / (ACKED, 20) / (ALL, extraction_item_ids=[1件]) / (NEEDS_REVIEW, order="posted_desc", extraction_item_ids=[1件]) / (ACKED, order="posted_desc", posted_within_hours=24)。
- 期待値: **変更を入れる前の origin/main で**記録した各 SQL 文字列の sha256 を試験に直書きする（記録した生出力をファイルに保存し、PR 本文にパスと値を書く）。変更後も同じ値で通ること。最後の2つは「新しい引数を渡しても今の道のまま」の証明。
- 新しい道の SQL 文字列の固定: `+ interval '0 second'`、`make_interval(hours => :posted_within_hours)`、`ORDER BY sm.line_posted_at DESC NULLS LAST, sm.id ASC,`、`meta LEFT JOIN base` を含むこと。窓なしのときは `make_interval` を含まないこと。SQLite（偽セッションの方言）では `set_config` を流さないこと。

### 5-2. 新しい道と今の道の中身が同じ（PG・CI のみ。既存 `pg` fixture、test_tcg_condition_review.py:46-60 と :329-345 の作り方に合わせる）
- 用意: 要確認になる行を、24時間以内の投稿に2件以上・24時間より古い投稿に1件以上・仕入元2つ以上・同じ投稿に2行以上。
- ③ 窓なし: 新しい道（limit 25/50/100 で全ページ）と今の道（NEEDS_REVIEW、limit 大）で total・providers・items の集合（extraction_item_id ごとの中身全体）が一致。順番は「今の道の結果を (posted_at の新しい順・NULL は最後, source_message_id 昇順) で安定ソートしたもの」と一致（result_order_sql は ei.id で終わるので全順序）。
- ② 窓あり（24）: 同じ比較を、今の道の結果を Python で posted_at ≥ now−24h に絞ったものと行う。
- ⑥ JIT: 新しい道を呼ぶ前と後で `SELECT current_setting('jit')` が同じ値。
- 空ページ: offset が total 以上のとき items=[] で total・providers は入っている。

### 5-3. ルーター
- order の範囲外・posted_within_hours=0 / 721 は 422。指定した値が fetch_analysis_results に渡る（:256-283 の型に合わせて kwargs を見る）。

### 5-4. フロント（新規 NeedsReviewTabsPanel.view.test.tsx。api mock は timing.test.tsx の作り方）
- 既定の GET に `status_tab=NEEDS_REVIEW`・`order=posted_desc`・`posted_within_hours=24`・`limit=25`・`offset=0`。
- ボタンを押すと aria-pressed=false、次の GET に posted_within_hours が無く offset=0。
- 件数を 50 にすると limit=50・offset=0。
- 確認済みタブの GET は `status_tab=ACKED&offset=0&limit=20` だけ（order・posted_within_hours なし）。操作台が出ない。
- 日付欄: production は posted_at を日本時間で表示、null は "—"。
- 既存の修正は timing.test.tsx:108 の `page_size` 20 → 25 だけ。他の既存試験（drawer.test.tsx:118 の回数 2、timing.test.tsx:126-137・:202-220 の GET 回数、acked.test.tsx、panel.test.tsx:45）は変えずに通すこと。通らなければ NEEDS_DECISION。

### 5-5. 通り続けること（触らない）
test_tcg_analysis_review.py:223-253、test_tcg_condition_review.py:681-692・:944-976、test_tcg_condition_review_fenced.py:26-44、test_tcg_result_order.py:366-374、test_v102_human_decisions_pg.py:278-305・:436-447。

## 6. 設計 doc の更新（同じ PR、docs/handoff/review-speed/design.md）
- §10-7 便1 の受入条件①の「1.5秒以下（…仮置き…本節に追記する）」を次に置き換える:
  「1.94秒以下（PO が開いた3回の中央値）。根拠: 便0 の計時 2026-10-21 02:39:42Z / 02:39:48Z / 02:39:54Z の3行（panel_ms 4313 / 4299 / 4200、list_ms 4243 / 4239 / 4145、行ごとの差 70 / 60 / 55 ms）。差の中央値 60ms → 2.0 − 0.06 = 1.94秒」
- §10-10 の後に「### 10-11. 便1 実装カード」を足し、本カードのパス（docs/handoff/review-speed/card-bin1.md）と、設計の行番号と実物の食い違い13件の表（SUMMARY.md 末尾の表をそのまま）を載せる。
- 本カードを docs/handoff/review-speed/card-bin1.md として同じ PR に入れる。

## 7. PR
- `gh auth status` で shingo-cc を確認。`gh pr create --base main`（Draft でない。migrations 等の危険パスなし）。本文は Write でファイルにしてから `--body-file`。テンプレの `### 標準ワークフロー確認` を埋める: recon docs/handoff/review-speed/recon.md、設計 docs/handoff/review-speed/design.md、対象ADR: ADR-1023, ADR-1014, ADR-027, ADR-144, ADR-067、触るファイル/削除するファイル（§8 を全列挙）、PO承認 2026-10-21「1」。
- worktree に `.pr-number` を書く。CI の結果は待たずに PR URL・HEAD sha を報告する。

## 8. 触るファイル（これ以外は触らない）
- backend/app/routers/tcg_analysis_review.py
- backend/app/services/tcg_analysis_review_svc.py
- backend/tests/test_tcg_analysis_review.py（5-3 を足すとき）
- backend/tests/test_tcg_analysis_review_sql_snapshot.py（新規）
- 5-2 の PG 試験を置くファイル（既存の pg fixture があるファイルに足すか新規。どちらにしたか報告）
- frontend/api-contract/openapi.json
- frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx
- frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.view.test.tsx（新規）
- frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.timing.test.tsx（:108 の1か所だけ）
- frontend/src/locales/ja.json・en.json（パスは実物に合わせる。needsReview に3キー）
- docs/handoff/review-speed/design.md、docs/handoff/review-speed/card-bin1.md（新規）
- .claude-pipeline/active-work.d/ の自分の台帳1枚（公式手順どおり）

## 9. 報告（DONE / BLOCKED: / NEEDS_DECISION:）
- 生出力を /tmp/CC報告ファイル/review-bin1-impl/ に保存: preflight、W25 突き合わせ diff、5-1 の変更前 sha256、pytest（変更ファイル分）、vitest、tsc、eslint、UI ガバナンス・i18n 検査、openapi 再生成の diff。
- 報告にはパスと結果（通った数・落ちた数）だけ書く。PG 試験が手元で走らないことは「CI のみ」と書く。
