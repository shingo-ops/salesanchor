# ルールテストシステム — design

recon: [docs/handoff/rule-test-system/recon.md](./recon.md)

## 概要
tcg_status_master のルール検証テストシステム。テストケース管理・一括実行・結果比較・ルール有効化ゲート。

## 対象ADR: ADR-027, ADR-067, ADR-144

## 変更前後

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| テスト機能 | なし（PR #3623で削除済み） | テストケースCRUD + Celery実行 + 結果表示 |
| ルール有効化 | 無条件で有効/無効切替可 | テスト合格がfalse→true切替の前提条件 |
| DB | 変更なし | rule_test_cases/runs/run_results 3テーブル追加 |
| マッチングロジック | resolve_status_v2（変更なし） | テストでも同一ロジックを使用（SSOT） |

## 新規ファイル
- `migrations/20260922_020000_create_rule_test_tables.sql` — 3テーブル
- `backend/app/routers/rule_test.py` — 6エンドポイント
- `backend/app/tasks/rule_test.py` — Celeryタスク
- `frontend/src/pages/super-admin/components/RuleTestPanel.tsx` — テストUI

## 変更ファイル
- `backend/app/main.py` — ルーター登録
- `backend/app/celery_app.py` — タスク登録
- `backend/app/routers/super_admin_status_master.py` — PATCHゲート追加
- `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx` — テストタブ追加
- `frontend/src/locales/ja.json` / `en.json` — i18nキー追加
- `scripts/run_all_migrations.sh` — migration登録

## テスト実行フロー
1. ユーザーがテストケースを登録（入力テキスト + 期待結果）
2. 「テスト一括実行」クリック → Celeryタスクにエンキュー
3. タスクが tcg_status_master から enabled ルールをロード
4. 各テストケースに対し resolve_status_v2 を実行（本番同一ロジック）
5. 期待値と実際の結果を比較し、結果を保存
6. 全件合格 → state=passed / 1件でも不合格 → state=failed

## ゲート機構
- PATCH /super-admin/status-master/:id で enabled: false→true の場合
- 最新テストランの state が 'passed' でなければ 409 エラー
- true→false（無効化）は常に許可

## 受入条件

| 基準 | 検証方法 |
|------|----------|
| テストケースの追加・削除ができる | 画面操作確認 |
| テスト一括実行で結果が表示される | 画面操作確認 |
| 合格/不合格がBadgeで色分け | 画面確認 |
| テスト合格後にルール有効化が可能 | 画面操作確認 |
| テスト未合格時にルール有効化が409で拒否 | API確認 |
| 本番マッチングと同一ロジック | resolve_status_v2 直接インポート確認 |

## 外部・過去事例の参照と我々への応用
旧テストシステム（PR #3623で削除）の設計を踏襲し、tcg_status_master SSOTに適合するよう簡素化。
旧システムのポリシー/リビジョン制度（8テーブル）は不要のため3テーブルに削減。

## 維持の仕組み
- `backend/app/tasks/rule_test.py:16` — resolve_status_v2 直接インポート（SSOT・変更時は tasks/rule_test.py も連動更新）
- `backend/app/routers/super_admin_status_master.py:200-214` — enabled ゲートロジック（本ファイル変更時はゲートテストも更新）
- CI の backend テストが `rule_test.*` エンドポイントをカバー（追加必要）

## 守り手
- `backend/app/tasks/rule_test.py:16` — resolve_status_v2を直接インポート（本番同一ロジック・SSOT）
- `backend/app/routers/rule_test.py:17` — require_super_admin 認証（全エンドポイント）
- `backend/app/routers/super_admin_status_master.py:200-214` — enabled false→true ゲート（テスト合格必須）
- `frontend/src/pages/super-admin/components/RuleTestPanel.tsx:12` — 全UI文字列 t() 経由（ADR-027）
