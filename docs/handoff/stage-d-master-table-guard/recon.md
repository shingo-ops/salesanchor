# recon — Stage D: 共用マスタテーブルCI保護拡張

**仕事名**: stage-d-master-table-guard  
**日付**: 2026-09-18  
**対象ADR**: ADR-155  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/migration-guard.yml:416` | check 7 PROTECTED_TABLES 定義（変更対象） |
| `.github/workflows/migration-guard.yml:499` | check 8 PROTECTED_TABLES 定義（変更対象） |
| `.github/workflows/migration-guard.yml:394` | check 7 コメントブロック（変更対象） |
| `.github/workflows/migration-guard.yml:490` | check 8 コメントブロック（変更対象） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 保護追加対象テーブルの選定 | migration内のINSERT文をgrepで全数調査 | ✅ 解消済み |
| 2 | 既存migrationへの影響 | check 7/8は新規SQLファイルのみチェック（diff基準） | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
