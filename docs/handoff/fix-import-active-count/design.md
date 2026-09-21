# Design: fix-import-active-count

参照 recon: docs/handoff/fix-import-active-count/recon.md
関連 ADR: ADR-027, ADR-067, ADR-144

## 変更内容
インポートタブのKPIカード「メッセージ総数」を「有効メッセージ」に変更。

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| ラベルキー | `importMessages` | `importActiveMessages` |
| 値 | `data.total_messages` | `data.active_message_count` |
| 表示ラベル(ja) | メッセージ総数 | 有効メッセージ |

## 設計根拠
- `source_messages` テーブルはインポートのたびに旧レコードを `is_active=FALSE` に更新して履歴を保持する
- `total_messages` は全履歴を含む集計値（supersede済みを含む）
- ダッシュボードには「現在有効なメッセージ数」のみを表示するのが正確なSSOT表示

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| インポートタブに「有効メッセージ」ラベルが表示される | ブラウザで目視確認 |
| 表示値が `active_message_count` の値と一致する | APIレスポンスと突合 |
| TypeScript型エラーなし | `tsc --noEmit` PASS |
| ESLintエラーなし | `eslint` PASS |

## 影響範囲
- 変更ファイル: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` のみ
- バックエンド変更なし（`active_message_count` は既にAPIレスポンスに含まれる）
- データ変更なし

## 外部・過去事例の参照と我々への応用
該当なし（既存フィールドの表示切り替えのみ・新規設計要素なし）

## 維持の仕組み
守り手: frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx（`ImportSummary` インターフェースが `active_message_count` を持つことをTypeScript型チェックで保証）
