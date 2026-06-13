# design.md — tenant_001 スキーマ・データ調査（読み取り専用）

- 対応 recon: docs/handoff/tenant001-investigation/recon.md
- 対象 ADR: ADR-036

## ゴール

本番 DB の tenant_001 スキーマ・データ状態を読み取り専用で確認し、
「削除推奨 / 補修推奨 / 要追加調査」の判断材料を得る。

## 設計

| 基準 | 検証方法 |
|------|---------|
| DB への書き込みゼロ | `SET TRANSACTION READ ONLY` + `ROLLBACK` — PostgreSQL が物理ブロック |
| 個人データ非取得 | COUNT/MAX のみ（SELECT \* なし） |
| 誤トリガーなし | `workflow_dispatch` + `confirm == 'yes'` ガード |
| 使い捨て保証 | 調査完了後に本ファイル + workflow ファイルを削除する別 PR |

## 外部・過去事例の参照と我々への応用

本番 DB への読み取り専用調査に `workflow_dispatch` を使うパターンは、
GitHub 公式ドキュメント（`on.workflow_dispatch.inputs`）で推奨される手動起動手段。
`SET TRANSACTION READ ONLY` は PostgreSQL 公式 (§13.2.3) の DML 物理ブロック手法であり、
アプリ層の制御に依存しない多重防護として業界標準。
本プロジェクトでは CC の本番経路を制限付き鍵のみに絞った（PR #2078 / design-b）実績があり、
今回は更に GitHub Secrets 経由の SSH + READ ONLY TP で二段構えを取る。
