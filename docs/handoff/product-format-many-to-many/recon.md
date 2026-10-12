# 細分類→中分類 多対多化 — Recon

## 目的

product_formats（細分類）と type_master（中分類）の関係を1対1から多対多に変更し、重複データを解消する。

## 現状（2026-09-22 実測）

- product_formats: 38件（「ブースターパック」が10ゲーム分で10行重複）
- products.product_format_id: 参照0件（安全に統合可能）
- product_formats.type_master_id: 1対1のFK（重複の原因）

## 関連ADR

- ADR-155, ADR-156
