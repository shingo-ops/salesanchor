# CI Guard Recon — supplier_channels.supplier_id 保護

## 調査日
2026-09-18

## 対象ファイル
`.github/workflows/migration-guard.yml`

## 既存チェック一覧
| チェック番号 | 名称 | 行範囲 |
|---|---|---|
| チェック1 | models.py に新 Column → deploy.yml に migrate_ 追記 | 19-74行 |
| チェック2 | migration ファイル命名規則 | 75-120行付近 |
| チェック3 | migration タイムスタンプ重複 | 以降 |
| チェック4 | cross-schema 参照禁止 | 以降 |
| チェック5 | SSOT 違反検出 | 以降 |
| チェック6 | DROP COLUMN / DROP TABLE — ADR 承認必須 | 343-391行 |
| チェック7 | 共用マスタテーブルへのデータ操作禁止（ADR-155） | 393行以降 |
| チェック8 | マスタテーブル参照禁止 | 以降 |

- ファイル総行数（追加前）: 584行

## 既存のADR / 関連PR
- PR #3539: supplier SSOT migration（supplier_channels.supplier_id を INTEGER 統一）
- ADR-155: product-master-ssot-csv-app（マスタSSoT方針、チェック7-8の根拠）

## チェック6 との関係
チェック6 (`.github/workflows/migration-guard.yml:343-391`) が最も近いパターン。
- git diff → 追加行抽出 → grep で危険パターン検出 → PR本文 ADR 参照確認
- チェック9 も同じ構造を採用する

## ギャップ
- 既存チェックは `supplier_channels.supplier_id` の列削除・型変更を個別には検出しない
- チェック6 は `DROP COLUMN/TABLE` 全般を検出するが、テーブル名の絞り込みをしない
- 今回 supplier_channels.supplier_id に特化したガードが必要

## フルパス参照
- `.github/workflows/migration-guard.yml:343` — チェック6 開始
- `.github/workflows/migration-guard.yml:391` — チェック6 終了
- `docs/handoff/supplier-ssot/recon.md` — supplier SSOT 移行 recon
- `docs/handoff/supplier-ssot/design.md` — supplier SSOT 移行 design
