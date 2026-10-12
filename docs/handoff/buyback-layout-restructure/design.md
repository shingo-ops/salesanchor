# Design: 買取相場レイアウト再構成

## recon参照
docs/handoff/buyback-layout-restructure/recon.md

## ADR参照
ADR-144

## 変更内容
- アラート設定・今すぐ取得ボタンを PageLayout headerAction に移動
- ContentToolbar を2行に分割（行1: ビュー切替、行2: 検索＋フィルタ群）
- 買取店 SelectControl に size="sm" を追加（高さ統一）
- BuybackByProductPage のフィルタ行も ContentToolbar に統一

## 対象外
- バックエンド変更（なし）
- i18n キー追加（なし）
- カテゴリタブのテーブル連結（PR #3741 で完了済み）

## 受入条件
| 基準 | 検証方法 |
|------|---------|
| ヘッダーにアラート設定・今すぐ取得ボタン | 目視確認 |
| ビュー切替が独立行 | 目視確認 |
| 検索＋フィルタが水平配置の独立行 | 目視確認 |
| 全プルダウンの高さが統一 | 目視確認 |

## 維持の仕組み
- 守り手: ADR-144 CI ゲート

## 外部・過去事例
該当なし（レイアウト変更のみ）
