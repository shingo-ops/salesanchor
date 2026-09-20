# Design: テナント管理センター状態マスタページ

## 概要
管理センターにテナント固有の状態マスタCRUDページを追加する。バックエンドAPIはPR #3590で実装済み。

## 変更内容

### フロントエンド
- ConditionsPage: テナント固有状態のCRUD + 共有カタログ表示
- ManagementCenterPage: サイドナビに状態マスタ項目追加
- App.tsx: /management-center/conditions ルート追加
- i18n: ja/en翻訳キー追加
- routeTitles: ページタイトル追加

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| 管理センターのサイドナビに「状態マスタ」が表示される | /management-center/conditions にアクセス |
| テナント固有状態の一覧が表示される | GET /conditions API応答確認 |
| 共有カタログが表示される | GET /conditions/catalog API応答確認 |
| CRUD操作が機能する | 新規追加・編集・削除の操作確認 |

## 外部・過去事例の参照と我々への応用

StatusMasterPage（PR #3595で実装済み）の横展開。同一構造・同一コンポーネント・同一パターンを適用。

## 維持の仕組み

- i18n CIチェック（ADR-027、ハードコード文字列検出）
- ADR-144 UIガバナンス（金型コンポーネント強制）
- conditions.view 権限による表示制御
