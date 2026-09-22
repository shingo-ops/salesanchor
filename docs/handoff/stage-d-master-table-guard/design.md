# Phase 3 設計 — Stage D: 共用マスタテーブルCI保護拡張

**対象ADR**: ADR-155  
**recon**: docs/handoff/stage-d-master-table-guard/recon.md  
**日付**: 2026-09-18  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

該当なし：CIガード変数の拡張のみであり、check 7/8のロジック自体は#3543で実装・検証済み。新たな外部事例参照は不要と判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| PROTECTED_TABLES が14テーブルを含む | `.github/workflows/migration-guard.yml:416` と `:499` を目視確認 |
| YAML構文が正しい | `python3 -c "import yaml; yaml.safe_load(open(...))"` で検証済み |
| 既存migrationがcheck 7/8に引っかからない | check 7/8は新規SQLファイルのdiffのみチェック（既存ファイルは対象外） |
| CI green | process-artifacts gate + 全CIチェック通過 |

---

## 技術 How・KPI

- KPI: 保護対象テーブル数 4 → 14（全共用マスタをカバー）
- 技術選択: 既存のPROTECTED_TABLES変数にテーブル名を追加するのみ（ロジック変更なし）

---

## 弊害・トレードオフ

- 新たに保護されたテーブルへのseed INSERTを含む既存migrationは引き続き実行される（check 7/8は新規ファイルのみ対象）。既存seed migrationの中和は別タスクで対応。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | check 7/8 PROTECTED_TABLES拡張 | Sonnet |
| 2 | コメント・エラーメッセージ更新 | Sonnet |
| 3 | YAML検証 | Sonnet |

---

## 継続

- 守り手: `.github/workflows/migration-guard.yml` check 7 + check 8
- 残件: 追加10テーブルの既存seed migrationの中和（Stage Cと同様の手法で別PRにて実施）
