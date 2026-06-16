# Phase 3 設計 — paypal-invoicer-view-url

**対象ADR**: ADR-101  
**recon**: docs/handoff/paypal-invoicer-view-url/recon.md  
**日付**: 2026-06-16  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：`create_and_send_invoice` がすでに `invoicer_view_url` を返却しており、UPDATE 文に 1 カラム追加するだけで対応可能なため外部事例の参照は不要と判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| テスト請求書発行後、DB の `paypal_invoicer_view_url` カラムに値が保存される | 手動: テスト発行→詳細画面で「原本を開く」ボタンが表示されることを確認 |
| `paypal_approval_url`（支払いページ）は従来通り保存される | 回帰確認: 「支払いページを開く」が引き続き動作すること |

---

## 技術 How・KPI

- KPI: テスト請求書の詳細画面で「原本を開く」ボタンが表示されること（ADR-101 Inc1 ワンクリック導線）
- 技術選択: `paypal_test_invoice` の UPDATE 文に `paypal_invoicer_view_url = :ivu` を追加（migration 不要、カラム既存）

---

## 弊害・トレードオフ

- `invoicer_view_url` が sandbox から返らない場合は NULL 保存（`result.get("invoicer_view_url")` で安全に処理）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `integrations.py:730` の UPDATE 文に `paypal_invoicer_view_url` を追加 | Generator |

---

## 継続

- 完了後の監視: テスト請求書発行後に invoice 詳細画面で「原本を開く」が表示されることを確認
- 次フェーズへの引き継ぎ: 本番請求書（`issue_paypal_link`）も同様の保存済みであることを別途確認
