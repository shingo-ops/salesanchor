# design: ADR-156 Phase 2 — tcg_type_master → type_master コード統一

## 概要

DB Phase 1（PR #3620）で `public.tcg_type_master` → `public.type_master` リネーム完了。
本 Phase 2 はコード・コメント・CI設定の全参照を統一するリファクタリング。
DB 変更なし・migration なし。

## 受入基準

| 基準 | 検証方法 |
|------|---------|
| backend/app/ に tcg_type_master SQL参照が0件 | `grep -rn "tcg_type_master" backend/app/ --include="*.py"` で結果0件（コメント含む） |
| テスト内の tcg_type_master テーブル参照が0件（migration ファイル名除く） | `grep -rn "tcg_type_master" backend/tests/ --include="*.py" \| grep -v "085_create_tcg_type_master.sql"` で結果0件 |
| 既存テスト全件 PASS | CI pytest 緑 |
| migration-guard.yml が type_master を保護対象にしている | `grep type_master .github/workflows/migration-guard.yml` で `PROTECTED_TABLES` 内に確認 |
| migration-guard.yml PUBLIC_TABLES に tcg_type_master が残っていない | `grep "PUBLIC_TABLES=" .github/workflows/migration-guard.yml \| grep -v tcg_type_master` |

## 外部事例

該当なし（内部リファクタリング）。

## 守り手

互換ビュー `public.tcg_type_master`（旧名 → 新テーブルへのビュー）が3か月間フォールバックとして存在。
万一見落とした参照があっても本番障害には直結しない。

## 影響範囲

- Python: SQL 文字列・コメント・dict キー の置換のみ。実行時セマンティクスの変更なし
- フロントエンド: JSDoc・コメントのみ。ロジック変更なし
- CI: PROTECTED_TABLES の正規表現パターン更新。`type_master` は Phase 1 で既に PUBLIC_TABLES に追加済み

## 戻し方

git revert このコミット。DB は Phase 1 の互換ビューが残存するため即時戻し可能。

## ADR 参照

- ADR-083: TCG 種別マスタ設計
- ADR-156: type_master リネーム計画（Phase 1-2）
