# 実装カード 便A: 理由コード表・要確認 API の出どころ・本番タブの出どころ列と訳の集約

- 設計: [design.md](./design.md) §12（§4-2・§4-3・§4-6 も §12 に合わせて訂正済み）
- 発行: 2026-10-09 Claude Opus。PO の承認: 2026-10-09「y」（Q3＝初期行は1回だけのデータ変更）、同日「PRマージ、デプロイまで完走させてくれ」「必要な権限は全て…使用して良い」
- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-v102-prod-switch-a（ブランチ release/v102-prod-switch-a、起点 656817ddd）。Bash は毎回 `cd <worktree> && ...`

## 0. 着手前（読むだけ。生出力を /tmp/CC報告ファイル/v102-binA/ に保存）
1. `./scripts/dev/executor-preflight.sh || exit 1`
2. 本番の権限の事実（読み取りのみ・無制限鍵は PO 許可済み。接続の型は ~/CC報告ファイル-keep/prompts/write_fc/run_write.sh と同じ、`PGOPTIONS='-c default_transaction_read_only=on'` 必須）:
   - アプリが DB に入る利用者名（docker-compose.yml の backend の DATABASE_URL の**変数名と利用者名の部分だけ**。パスワードは出さない）
   - `SELECT current_user; SELECT has_table_privilege('<アプリの利用者>','public.line_unit_ignore_phrases','SELECT'); SELECT defaclrole::regrole, defaclnamespace::regnamespace, defaclobjtype, defaclacl FROM pg_default_acl;`
   - `SELECT to_regclass('public.review_reason_codes');`（NULL のはず）
   - アプリの利用者が新しい表を SELECT できない見込み（default ACL に無い、かつ line_unit_ignore_phrases も false）なら NEEDS_DECISION で止まる。
3. 次を実物で確かめて file:line を報告。カードの前提と違えば NEEDS_DECISION:
   - (a) GET /tcg/analysis-results の応答の組み立て（tcg_analysis_review.py:72-80 AnalysisResultItem、tcg_analysis_review_svc.py:240-290）と、`condition_review.review_reasons` が件ごとにどこで作られるか。
   - (b) 本番タブの列定義 NeedsReviewTabsPanel.tsx:326-367 と、理由の表示 :337-355。
   - (c) 訳の利用箇所の全一覧: `git grep -n "pmgWorkflow.reviewReason\|conditionReview.reasons\|conditionReview.otherReason" frontend/src`、AnalysisDashboardPanel.tsx の理由内訳の表示（:1631-1642）。各テスト（*.test.tsx）で旧い訳の文字列を検査している箇所。
   - (d) frontend/CLAUDE.md の i18n セルフチェック（テンプレート文字列の鍵 `t(\`a.${x}\`)` が許されるか。既存例 ConditionReviewPanel.tsx:75）。
   - (e) PG テストの書き方（tests/test_tcg_condition_review.py の pg フィクスチャ）と、CI の DB で新しい表を作る方法（conftest か migration 一括適用か）。

## 1. 変更内容（最終形）

### 1-1. migration（構造のみ・INSERT 等を書かない＝ADR-1007）
`migrations/20261009_200000_create_review_reason_codes.sql`（時刻が重なれば重ならない値に）:
```sql
-- 便A（docs/handoff/v102-prod-switch/design.md §12）。構造のみ。初期行は data/review_reason_codes/ の1回だけのデータ変更（ADR-1007）。
CREATE TABLE IF NOT EXISTS public.review_reason_codes (
    code       TEXT PRIMARY KEY CHECK (code ~ '^[a-z][a-z0-9_]*$'),
    source     TEXT NOT NULL CHECK (source IN ('gemini', 'system')),
    fix_stage  TEXT NOT NULL CHECK (fix_stage IN ('extraction', 'analysis')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.review_reason_codes IS '要確認の理由コードの正本。出どころ（gemini=Gemini が自分で申告／system=システムが見つけた）と直す工程。画面の言葉は ja/en.json の reviewReason.<code>';
COMMENT ON COLUMN public.review_reason_codes.source IS 'gemini / system';
COMMENT ON COLUMN public.review_reason_codes.fix_stage IS 'extraction=Gemini の書き写しを直す／analysis=マスタ・商品割当で直す';
```
0-2 で GRANT が要ると分かった場合だけ、既存の public 新表の GRANT の書き方（git grep で例を探す）に合わせて GRANT SELECT を1行足す（足したら報告）。scripts/run_all_migrations.sh 末尾に既存の形式で登録。

### 1-2. データ変更の SQL（リポジトリに記録・実行はデプロイ後）
`docs/handoff/v102-prod-switch/data/review_reason_codes/` に:
- `seed_20261009.sql`: design.md §12-2 の29行の `INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES (...);`（1文、29組、表の順）
- `precheck.sql`（読み取り）: `to_regclass` が NULL でない／行数 `ROWS|<n>`（0 必須）／`has_table_privilege(<アプリの利用者>,'public.review_reason_codes','SELECT')` が t／`PRECHECK_DONE`
- `dryrun.sql`: `\set ON_ERROR_STOP on` → `BEGIN;` → seed と同じ INSERT → 29行・source/fix_stage の件数（gemini 1・system 28、extraction 13・analysis 16）を `DO $$ ... RAISE EXCEPTION $$` で検査 → `ROLLBACK;` → `SELECT 'DRYRUN_OK';`
- `commit.sql`: 同じ INSERT と検査 → `COMMIT;` → `SELECT 'COMMIT_DONE';`
- `verify.sql`（読み取り）: `code|source|fix_stage` を code 順で全行出力 → `VERIFY_DONE`
- `rollback.sql`: `DELETE FROM public.review_reason_codes WHERE code IN (<29個>) RETURNING code;`（使うのは戻すときだけ）
- `README.md`: 手順（precheck→dryrun→commit→verify）、戻し方、記録欄（実施日時・結果を後で設計者が書く）
- 本番ホスト名・IP・鍵のパスはリポジトリに書かない。実行用の run_write.sh は ~/CC報告ファイル-keep/v102-binA-write/ に、prompts/write_fc/run_write.sh の型で作る（各段のログ保存、dryrun 成功の印が無いと commit しない）。

### 1-3. backend
- 新規 `backend/app/services/review_reason_codes_svc.py`: `load_review_reason_codes(session) -> dict[str, tuple[str, str]]`（code → (source, fix_stage)）と `split_reason_codes(text) -> list[str]`（「,」で分け、空白除去、空を捨て、順番を保って重複を除く）と `build_review_reason_details(text, table) -> list[dict]`（{code, source, fix_stage}、表に無ければ source/fix_stage は None）。区切りは line_analysis_v102_svc.REASON_SEPARATOR を import して使う（二重定義しない）。
- tcg_analysis_review.py の AnalysisResultItem に `review_reason_details: list[ReviewReasonDetail]`（code: str, source: Literal['gemini','system'] | None, fix_stage: Literal['extraction','analysis'] | None）。値は 0-3(a) の `condition_review.review_reasons` を元に作る。表の読み込みは1リクエスト1回。既存の項目は変えない。
- テスト（PG）: 表に行がある・無いコード・空の理由・重複のある理由で、配列が期待どおり。既存の test_tcg_analysis_review.py の形の検査に新項目を足す。

### 1-4. frontend（金型・デザイントークンのみ。新しい部品・色・生要素・ui-allow を作らない）
- ja.json / en.json に `reviewReason` 名前空間（design.md §12-2 の29コード＋ unknown・source.gemini・source.system・separator）と `needsReview.source` を追加。訳文は §12-2 のとおり（変えない）。
- `pmgWorkflow.reviewReason`・`conditionReview.reasons` の鍵の集合を削除し、使っていた画面（0-3(c)）を `reviewReason.<code>` に切り替える。ConditionReviewPanel の「他にも確認が必要」（otherReason）の挙動は、訳が無いときの代わりの文として残すか reviewReason.unknown にするかで2通りに分かれる → **reviewReason.unknown に統一**（コード併記）。otherReason の鍵が他で使われていなければ削除。
- 理由の訳は1つの関数にまとめる（例: `frontend/src/features/tcg-analysis-review/reviewReasonLabel.ts` に `reviewReasonLabel(t, code)` と `reviewSourceLabel(t, details)`）。4画面はこれを使う。
- NeedsReviewTabsPanel 本番タブ: 「出どころ」列（needsReview.source）を「確認理由」の直前に追加。値は reviewSourceLabel（重複なし・gemini→system の順・無ければ「—」）。確認理由は review_reason_details を reviewReasonLabel で訳して reviewReason.separator で結ぶ。review_reason_details が空のときだけ今の review_issues の表示を残す。
- API の型（frontend の api 型定義）に review_reason_details を追加。
- テスト（vitest）: 本番タブで出どころ（Gemini・システム・両方・「—」）と訳された理由・未登録コードの表示。旧い訳の文字列を検査していたテストは新しい文に直す。

### 1-5. 抜け漏れ防止テスト（backend、非PG）
design.md §12-5 の3つ:
- data/review_reason_codes/seed_*.sql の INSERT のコード集合 ＝ ja.json の reviewReason のコード鍵 ＝ en.json（unknown・source・separator を除く）。
- 0-3 で見つけたコード側の名前付き定数（design §12-5 の列挙。import して値を集める）⊆ seed のコード集合。
- seed の各コードの文字列が backend/app/ 配下のどこかに現れる。

## 2. 触らない
要確認の判定（何を要確認にするか）、配信、analyzer・v102 の判定ロジック、試作版ファイル、extraction_jobs.review_reasons の画面（便C）、deploy.yml、.github/workflows/、本番 DB への書き込み（設計者が別に行う）。

## 3. 完了条件
- worktree で backend の pytest（非PG、--no-cov）・ruff、frontend の `npm run lint`・`npm run build`・vitest（関係するテスト）・i18n の検査（frontend/CLAUDE.md の手順）。生出力の末尾を報告。
- commit（Co-Authored-By なし）→ push → `gh pr create --draft --base main`（テンプレート起点。標準ワークフロー確認：recon は docs/handoff/v102-prod-switch/recon.md、設計 design.md §12、対象ADR ADR-027, ADR-144, ADR-1007。触るファイル・削除するファイルは実測から平打ち、パスのみ）。push と PR 作成は別コマンド。`gh pr edit` は worktree 内で実行。PR 作成前に gh auth status が shingo-cc。
- GO記録は書かない。マージしない。CI を待たない。PR URL を報告。
- 最終行 DONE / BLOCKED: / NEEDS_DECISION:。

## 4. 止まる条件
フック・権限に止められた（言い換えず文面を貼る）／0 の前提が違う／カードに無いファイルを触る必要／選択肢が2つ以上で決まらない／既存テストが落ちて原因がカードの範囲外。
