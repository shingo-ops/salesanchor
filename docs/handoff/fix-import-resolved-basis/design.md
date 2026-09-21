# design: 解決/未解決カウントを created_count ベースに変更

recon: docs/handoff/fix-import-resolved-basis/recon.md
対象ADR: ADR-027, ADR-067, ADR-144

## KGI
取り込みテーブルの「解決」「未解決」列が、ファイル全体ではなく新規取り込みメッセージ（created_count）ベースで表示される。

| 基準 | 検証方法 |
|------|----------|
| 解決 = created_count - unresolved_count | ブラウザで取り込みテーブルを開き、解決列が created_count 以下の値になっている（従来は message_count 以下） |
| 未解決 = unresolved_count（変化なし） | unresolved_count カラムの値は変更なし |
| reused メッセージが解決数に含まれない | created_count < message_count のケースで解決数が適切に下がる |

## 変更ファイル一覧

### 変更
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:483` — 計算式変更（1行）

### 新規作成
- `docs/handoff/fix-import-resolved-basis/recon.md` — 本調査記録
- `docs/handoff/fix-import-resolved-basis/design.md` — 本設計書

### 削除するファイル
なし

## 設計方針
- フロントエンドの計算式のみ変更（バックエンドAPIレスポンス変更なし）
- `created_count` は `ImportRecord` interface で既に `number` 型として定義済み
- `?? 0` ガードを追加（API側で数値が保証されているが防御的に）

## 外部・過去事例の参照と我々への応用
- 取り込みパイプラインのベストプラクティス: 「新規vs再利用」を明示するのは ETL系ツール（Apache NiFi等）の標準パターン。今回は既存の `created_count` フィールドをそのまま活用することで最小変更で正確な集計を実現。

## 維持の仕組み

守り手: `ImportRecord` interface の `created_count: number` 定義（`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:125`）。バックエンドAPIレスポンス仕様変更時（`created_count` 廃止等）は TypeScript 型エラーで検出可能。
