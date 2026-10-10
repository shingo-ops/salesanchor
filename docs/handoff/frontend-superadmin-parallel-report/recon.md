# AY-2h recon: 比較レポート画面（tcg-parallel-report）の削除

実測時の origin/main: 58dd91233（#4101 AY-2g の merge）。
既存 ADR の検索: `git grep -il "parallel-report\|TcgParallelReport" docs/adr/` で該当する設計判断を確認する。画面の存続を定める ADR は、設計の調査では見つかっていない。関連は ADR-027（i18n）と ADR-144（UI 金型）。

## 1. ページの事実（file:line）
- frontend/src/pages/super-admin/TcgParallelReportPage.tsx（本便で削除。2行目）冒頭コメント「/super-admin/tcg-parallel-report — 並行運用比較レポート」、MIG-04 Phase 4。
- frontend/src/pages/super-admin/TcgParallelReportPage.tsx（本便で削除。71-72行目）が `api.get<ParallelReportResponse>("/tcg/parallel-report")` を呼ぶ。読み取り専用。
- frontend/src/App.tsx:91 import、:306-310 Route（`/super-admin/tcg-parallel-report`）。

## 2. このページだけが使うもの
- import は icons（TABLE_ICONS）・useSuperAdmin・PageLayout・api の4つ。どれも共用部品。ページ専用の子部品・CSS・api 関数・試験は0件。型5つはページ内定義。
- nav キー: frontend/src/locales/ja.json:260・en.json:260（nav.superAdminTcgParallelReport）。参照元はページ自身（:116・:119・:126）のみ。
- i18n ブロック: frontend/src/locales/ja.json:5033・en.json:5033（tcgParallelReport、各20行）。参照元はページ自身のみ。テンプレート接頭辞での参照も無い（`git grep -n "tcgParallelReport"` はページと両 locale のみ）。

## 3. 参照元の全走査（`git grep -n -i -E "tcg-parallel-report|TcgParallelReport|parallel-report|parallel_report"`）
- frontend/src: App.tsx、ja.json、en.json、ページ自身。
- tests-e2e・単体試験・docs/ai-agents・.github・scripts: 0件。
- backend: backend/app/main.py:122・:724、backend/app/routers/tcg_parallel_report.py（:66 が GET /tcg/parallel-report）、backend/app/services/tcg_parallel_report_svc.py。変更しない。
- 生成物 frontend/api-contract/openapi.json と frontend/src/api/generated は backend の定義から作られる。変更しない。
- docs 配下の過去文書（design.md:706 ほか、migration.md:136-137）は書き換えない。

## 4. 転送の既存の型
- frontend/src/pages/super-admin/legacyPageRedirects.ts（AY-2g）の配列を、App.tsx と legacyPageRedirects.test.tsx が共有する。1件追加するだけで Route が増える。
- 転送先 `/super-admin/analysis-rules`（section なし）はダッシュボードが初期表示（AnalysisRulesPage.tsx の `|| "dashboard"`）。

## 5. 本番の利用状況（直近30日。設計の調査結果）
ページを直接開いた回数0、API の呼び出し0。画面の中にこのページへのリンクは無い。
