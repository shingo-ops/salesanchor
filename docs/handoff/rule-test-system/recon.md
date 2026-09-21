# ルールテストシステム — recon

## 目的
tcg_status_master (SSOT) のルールが正しく動作するか検証するテスト機能を再構築する。
PR #3623 で削除された旧テストシステムの機能を、tcg_status_master ベースで再実装。

## 既存資産

### 本番マッチングロジック（変更なし・再利用）
- `backend/app/services/tcg_analyzer_svc.py:1092-1130` — resolve_status_v2（3段階判定: EXCLUDE → OUTPUT → DEFAULT）
- `backend/app/services/tcg_analyzer_svc.py:1077-1089` — _match_status_pattern（LITERAL/REGEX/DEFAULT）
- `backend/app/services/tcg_analyzer_svc.py:1048-1072` — load_status_master（enabled=TRUE のみロード）

### Celeryインフラ（稼働中・変更なし）
- `docker-compose.yml:191` — celery-worker コンテナ
- `docker-compose.yml:251` — celery-beat コンテナ
- `backend/app/celery_app.py:38` — タスク登録リスト（rule_test 追加）

### PATCH ゲート対象
- `backend/app/routers/super_admin_status_master.py:200-214` — update_status_master（enabled変更のゲート追加先）

### DB SSOT
- `public.tcg_status_master` — 9件シードデータ（完売5件、日付3件、デフォルト1件）

### ADR
- ADR-027: i18n 強制
- ADR-067: デザイントークン強制
- ADR-144: UI金型
