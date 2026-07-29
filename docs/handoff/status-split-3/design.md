# status 2分割 便3 設計

**対象ADR**: docs/adr/ADR-109-leads-status-ssot-immutable-codes.md
**recon**: docs/handoff/status-split-2/recon.md（便2 recon を親参照）
**日付**: 2026-07-29
**担当**: Generator

---

## 外部・過去事例の参照と我々への応用

- docs/adr/ADR-109-leads-status-ssot-immutable-codes.md の status SSOT 化パターン → status 追加時の KPI 側対応は NOT IN リスト更新が定跡。同じパターンで out_of_scope → 2値に置換。
- 過去事例: 便1（enum 追加・サーバールーティング）・便2（フロント表示）が先にマージ済み → 便3は KPI 計算層のみ対象。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| analytics.py の NOT IN に `lead_out_of_scope`, `negotiating_out_of_scope` が含まれる（全9箇所） | grep 確認 |
| analytics.py の excluded カウントが 2値合算 | analytics.py:505 の `IN ('lead_out_of_scope', 'negotiating_out_of_scope')` 確認 |
| dashboard.py:104 の converted に `negotiating_out_of_scope` が含まれる | grep 確認 |
| dashboard.py:105 の conversion_denominator の NOT IN が 2値＋disqualified | grep 確認 |
| tasks/dashboard.py:61 の open_count NOT IN が 2値 | grep 確認 |
| close_rate は触らない（analytics.py:1199-1203 は `IN ('existing_customer', 'lost')` のまま） | grep で out_of_scope 参照ゼロを確認 |
| pytest 全緑 | CI pass |

---

## 技術 How・KPI

- 変更量: 3ファイル・合計16行変更
  - backend/app/routers/analytics.py: 11箇所（定数1+SQL10）
  - backend/app/routers/dashboard.py: 3箇所（L101, L104, L105）
  - backend/app/tasks/dashboard.py: 1箇所（L61）
- テスト変更: 不要（実データ 0件で期待値変化なし）
- close_rate: `AND status IN ('existing_customer', 'lost')` のまま → negotiating_out_of_scope を分母に含めない

---

## 弊害・トレードオフ

- 便1未マージの状態でこの便3がマージされても: DB に `lead_out_of_scope` / `negotiating_out_of_scope` が存在しないため KPI 数値変化なし（安全）。
- `disqualified` は NOT IN に残置: 移行済みで DB に存在しないが、参照が残っていても無害。2値整理と合わせて残置扱い。

---

## 計画票

| ステップ | 内容 |
|---------|------|
| 1 | analytics.py 11箇所置換（定数・SQL） |
| 2 | dashboard.py 3箇所置換 |
| 3 | tasks/dashboard.py 1箇所置換 |
| 4 | pytest 実行 |
| 5 | push → PR 作成 |

---

## 維持の仕組み

- 守り手: .github/workflows/backend-ci.yml（pytest SQLite + PostgreSQL RLS 実行）
- 守り手: .github/workflows/ui-governance-gate.yml（PR 本文の宣言と実変更ファイルの一致を強制）
- 対象: 新ステータス追加時に analytics.py / dashboard.py の NOT IN リストも更新し忘れると、対象外ステータスのリードがオープン件数に混入する。

---

## 継続

- 便1マージ後: DB に 2値が書き込まれるようになり、本変更が実際に動作する
- 本番 DB 移行: `scripts/migrate_status_split_lead_out_of_scope.py` で `disqualified` → `lead_out_of_scope`（別カード）
