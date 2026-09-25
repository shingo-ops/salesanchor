---
title: "LINE解析ダッシュボード タブ分離 設計"
recon: docs/handoff/dashboard-tab-separation/recon.md
---

## 設計

### 原則
各タブは自分の担当工程の問題だけを表示する。

### タブ別変更

| タブ | 変更内容 |
|------|---------|
| Import | 抽出関連の提供者テーブル削除、orphan_count警告追加 |
| Extraction | 提供者別抽出エラー内訳テーブル追加（新規SQL） |
| Analysis | 提供者別解析問題テーブル追加（既存API再利用） |
| Distribution | 配信失敗/停止警告バッジ追加、解析ドメインデータ削除 |

### SSOT遵守
- 解析タブ: 既存 /tcg/supplier-quality-summaries API を再利用（新規エンドポイント不要）
- 抽出タブ: 既存 pipeline-summary エンドポイントを拡張（extraction_by_supplier フィールド追加）

### 受入基準

| 基準 | 検証方法 |
|------|---------|
| インポートタブに抽出・解析データなし | コード確認: extraction/analysis フィールド参照なし |
| 抽出タブに提供者別エラー表示 | 画面確認: エラーありの提供者がテーブルに表示 |
| 解析タブに提供者別問題表示 | 画面確認: 問題ありの提供者がテーブルに表示 |
| 配信タブに解析データなし | コード確認: analysis フィールド参照なし |
| i18n完全 | check-i18n-missing-keys.js PASS |
| デザインシステム遵守 | Badge/Card/DataTable のみ使用 |

## 外部・過去事例の参照と我々への応用

該当なし（内部リファクタリング。タブ別責任分離は既存4タブ構成の中で完結し、外部ライブラリ・外部事例への参照は不要）

## 維持の仕組み

守り手: i18n check script（check-i18n-missing-keys.js）/ TypeScript型チェック（tsc）/ process-artifacts gate（check-process-artifacts.js）
