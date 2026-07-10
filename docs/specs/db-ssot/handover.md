# 引き継ぎメモ（DB設計のSSOT化）2026-07-10時点

> この文書は何か（専門用語なしの1行）:
> 次回セッションがすぐ続きから動けるよう、済んだこと・残りの宿題・全体の前提を1枚にまとめたメモ。

親: ./README.md

## 済（紙になっている）
- あるべき姿・KGI（K1〜K5）: ./ideal-state.md, ./kgi.md
- 会話データ一元化の設計図: ./conversation-unification/design.md

## 次にやる宿題（優先順）
1. 予測値の設計: 2種類ある。手入力=営業優先度づけの材料 / 自動計算=CRM本命の正確値。別の場所に分離する。
   稼働前なので現状のデータ分布（leads側は空 0/56・companies側は使用 9/51）に引きずられず理想で設計する。
   assigned_to（担当者）は予測値と別物・後で個別に扱う。
2. 金額の重複: total_amount / shipping_fee / subtotal / paid_at が orders / invoices / quotes / purchase_orders に分散。
   未調査のため、まず recon（実DB・読み取り専用）から。
3. 分類値の台帳化（K4関連・表記ゆれ防止）: 未着手。

## 全体の前提（重要）
- 本番未稼働。既存データは捨てて理想形で新規構築してよい（引っ越し不要）。現状のデータ分布に設計を引きずらない。
- 各設計は db-ssot の子として <テーマ名>/design.md を追加し、親README §子欄を「design済＋リンク」に更新する（会話便と同じ型）。
- 実DB確認は本番tenant_004・読み取り専用（default_transaction_read_only=on）で行う。SQLはファイル転送してpsql -fで流す（クォート崩れ回避）。
