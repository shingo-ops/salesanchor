# 設計 — fix-tcg-api-path

**対象ADR**: ADR-152
**recon**: docs/handoff/fix-tcg-api-path/recon.md
**日付**: 2026-09-01
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 事例1: `api` クライアントのベース URL 設計（プロジェクト内慣例）— 他の全 super-admin 画面（`TcgSeriesTab.tsx` 等）は `/super-admin/tcg/types` 形式でプレフィックスなし。→ 本修正も同一慣例に揃える。
- 事例2: FastAPI `include_router(prefix="/api/v1")` — ルーター側は `/tcg/parallel-report` のみ定義し、prefix でバージョンを付与する標準パターン。フロント側が `/api/v1` を重複して指定すると `/api/v1/api/v1/...` になる（本バグの根本原因）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 本番 `/api/v1/tcg/parallel-report` に認証済みリクエストを送ると 200 が返る | ブラウザで `https://app.salesanchor.jp/super-admin/tcg-parallel-report` を開きレポートが表示される |
| バックエンドログに `/api/v1/api/v1/tcg/parallel-report 404` が記録されない | デプロイ後 `docker logs astro-webapp-backend-1 | grep tcg` で確認 |

---

## 技術 How・KPI

- KPI: `https://app.salesanchor.jp/super-admin/tcg-parallel-report` でレポートが正常表示（現在: 「レポート取得失敗: Not Found」）
- 技術選択: `api.get("/api/v1/tcg/parallel-report")` → `api.get("/tcg/parallel-report")` の1行修正。他 super-admin API 呼び出しと同一の慣例に統一。

---

## 弊害・トレードオフ

- なし。1行の誤ったプレフィックス除去であり、副作用ゼロ。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `TcgParallelReportPage.tsx:70` の `/api/v1/tcg/parallel-report` → `/tcg/parallel-report` | Generator |
| 2 | CI green 確認・PR #3185 マージ | PO |

---

## 継続

- 完了後の監視: デプロイ後にブラウザで画面を開き、レポートが表示されることを確認
- 次フェーズへの引き継ぎ: ADR-152 を参照し、frontend の `api.get/post/...` 呼び出しには常に `/api/v1` プレフィックスなしの相対パスを使用すること
