---
mode: handoff
---

# 設計審査（Architect・同一 AI による自己審査）

- 対象: [design.md](./design.md)（2026-11-06 版）
- 審査者: Claude Opus（設計を書いた同じ AI。独立した第二者の審査ではない）
- 判定: **APPROVE（条件つき）**

## 確かめたこと

| 観点 | 結果 | 根拠 |
|---|---|---|
| 既存 ADR との整合 | ○ 新 ADR で 14列の記述を改める手当てがある | recon §0、design §8 |
| 並びの正本が1か所か | ○ `_SHEET_LAYOUT` で見出しと列名を組で持つ | design §4-2 の1 |
| 閲覧ページへの影響 | ○ `viewer_inventory_cache.py:78` は引数なしで呼ぶので14列のまま | recon §3、design §4-2 の5 |
| 既存の試験を壊さないか | ○ `fetch_output_rows` の既定は14列のまま。`fetch_output_rows` を mock する試験（`test_tcg_review_sheet_svc.py:183`・`test_distribution_rows_builder.py:134-140`）は引数を見ないので通る | 実物を読んだ |
| 配信の経路の漏れ | ○ 自動配信（`backend/app/tasks/tcg_extraction.py:802`）・全件（`backend/app/routers/tcg_distribution.py:188`）・1件（同 `:195`）はすべて `run_distribution` を通る | 実物を読んだ |
| 商品IDの取り出し | ○ SELECT は既に `product_id` を出す（`tcg_distribution_svc.py:295,343`）。SQL は触らない | recon §2 |
| 受入条件が判定できるか | ○ K1〜K7 は○×か件数で判定できる | design §7 |
| 戻し方 | ○ PR を戻せば次の配信で14列に戻る。DB の変更なし | design §5 |

## 条件（実装カードの前に片づける）

1. design §9 確認1（お客さんのブックが位置で読んでいないか）の PO の回答。山崎涼太郎さんの「価格表」は在庫集計タブ以外を読めていない（recon §6）。
2. 在庫一覧の GAS の本番の版は手元の写しで確かめただけ（recon §5【未確認】）。実装後の K4 で画面を確かめる。

## 未解決

- なし（上の条件2つは PO の確認と反映後の確認で片づく）。
