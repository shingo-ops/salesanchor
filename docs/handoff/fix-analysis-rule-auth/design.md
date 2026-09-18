# design: 完売ルール・日付ルール管理画面 認証不具合修正

## 目的
管理画面の API 呼び出しを正規の認証付きクライアント（api.get/api.post）に統一し、「権限がありません」エラーを解消する。

## 対象ADR
- ADR-027: i18n強制（変更なし・準拠維持）
- ADR-144: UI金型ガバナンス（変更なし・準拠維持）

## 変更前後

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| API呼び出し | 生 fetch() + credentials: "include" | api.get() / api.post() |
| 認証トークン | 送信されない | Firebase IDトークン自動付与 |
| エラー判定 | 文字列比較 e.message === "401" | 数値比較 e.status === 401 |

## 影響範囲
- frontend/src/pages/super-admin/components/SoldOutRulesPanel.tsx（7関数）
- frontend/src/pages/super-admin/components/DateRulesPanel.tsx（7関数）

## 対象外
- バックエンド変更なし
- DB変更なし
- 他ページへの影響なし

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| 管理画面で「権限がありません」が消える | ブラウザで /super-admin/analysis-rules を開く |
| 完売ルールの4タブが表示される | 指示文/検索・除外ワード/テスト/変更履歴 |
| 日付ルールの4タブが表示される | 指示文/フォーマット/テスト/変更履歴 |
| ESLint PASS | cd frontend && npm run lint |
| TypeScript型チェック PASS | cd frontend && npx tsc --noEmit |

## リスクと対処
- リスク: なし（認証方式の統一のみ、ロジック変更なし）
- ロールバック: git revert で即時可能
