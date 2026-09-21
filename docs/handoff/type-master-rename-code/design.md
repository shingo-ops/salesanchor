# design: ADR-156 Phase 2 — tcg_type_master → type_master コード統一

## 概要

recon: docs/handoff/type-master-rename-code/recon.md

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

## 外部・過去事例の参照と我々への応用

該当なし（純粋な内部リファクタリング。DB リネーム後のコード統一は標準的なパターン）。

## 維持の仕組み

守り手: migration-guard.yml の PROTECTED_TABLES（type_master を保護対象として含む）

- migration-guard.yml の `PROTECTED_TABLES` が `type_master` を保護対象として含む → 新規 migration で誤った INSERT/UPDATE/DELETE をブロック
- migration-guard.yml の `PUBLIC_TABLES` から `tcg_type_master` が削除済み → 旧名 FK 参照を新規 migration で使うと CI エラーになる
- 互換ビュー `public.tcg_type_master` が3か月間フォールバックとして残存 → 見落とした参照があっても本番障害に直結しない

## 影響範囲

- Python: SQL 文字列・コメント・dict キー の置換のみ。実行時セマンティクスの変更なし
- フロントエンド: JSDoc・コメントのみ。ロジック変更なし
- CI: PROTECTED_TABLES の正規表現パターン更新。`type_master` は Phase 1 で既に PUBLIC_TABLES に追加済み

## 戻し方

`git revert <commit_hash>` で即時戻し可能。DB は Phase 1 の互換ビューが残存するため戻し後も動作継続。

## ADR 参照

- ADR-083: TCG 種別マスタ設計
- ADR-156: type_master リネーム計画（Phase 1-2）
