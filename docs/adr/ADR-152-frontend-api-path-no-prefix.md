# ADR-152: フロントエンド API 呼び出しパスに /api/v1 プレフィックスを含めない

- **Status**: Accepted
- **Date**: 2026-09-01
- **Deciders**: shingo-ops（PO）, Hikky-dev（Dev）

## Context

`api` クライアント（`frontend/src/lib/api.ts`）はベース URL に `/api/v1` を含んでいる。
フロントエンドから `api.get("/api/v1/...")` と呼ぶと、実際のリクエスト URL が
`/api/v1/api/v1/...` となり HTTP 404 になる。

PR #3181 で追加した `TcgParallelReportPage.tsx` が `/api/v1/tcg/parallel-report` を
呼んでいたため、本番で「レポート取得失敗: Not Found」が発生した。

既存の全 super-admin ページ（`TcgSeriesTab.tsx` 等）は `/super-admin/tcg/types` のように
プレフィックスなしで記述しており、このバグは慣例から外れた記述が原因であった。

## Decision

フロントエンドの `api.get/post/put/patch/delete` 呼び出しパスは、
常に `/api/v1` プレフィックスなしの相対パス（例: `/tcg/parallel-report`）で記述する。

## Consequences

- `TcgParallelReportPage.tsx:70` を `/tcg/parallel-report` に修正（PR #3185）
- 既存コードは全てプレフィックスなし形式であり追加変更不要
- 今後の開発: `api.get("/api/v1/...")` 形式は ESLint ルール等で検出することを推奨（ADR-027 の i18n チェックと同様の仕組み）
