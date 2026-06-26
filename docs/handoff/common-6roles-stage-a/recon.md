# Recon — 共通6ロール標準化 段階A

## 現状把握

### DEFAULT_ROLES 定義場所
- `backend/app/services/tenant.py:37` — `DEFAULT_ROLES` リスト定義開始
- `backend/app/services/tenant.py:67` — マネージャー（旧リーダー）エントリ
- `backend/app/services/tenant.py:141` — 仕入れエントリ（新規追加）
- `backend/app/services/tenant.py:159` — 発送エントリ（新規追加）

### seed 関数
- `backend/app/services/tenant.py:1516` — `seed_system_roles()` 定義
- 冪等性: `ON CONFLICT (tenant_id, name) DO UPDATE` による重複防止

### ロール紐付けの安全性
- `tenant_NNN.user_roles`: `role_id` FK（name でなく id 参照）→ 改名後も紐付け維持
- `tenant_NNN.roles`: `UNIQUE(tenant_id, name)` 制約

### 適用スクリプト
- `scripts/migrate_6roles_stage_a.py:79` — `_RENAME_MAP` 定義（旧名→新名マッピング）
- `scripts/migrate_6roles_stage_a.py:86` — `_count_roles()` ヘルパー（before/after ログ用）
- `scripts/migrate_6roles_stage_a.py:98` — `_migrate_tenant()` コアロジック
- `scripts/migrate_6roles_stage_a.py:173` — `main()` 本番ガード（`_PRODUCTION_TENANT_IDS`）
- `scripts/migrate_6roles_stage_a.py:231` — argparse `--tenant-id` 必須化

### 権限キー確認
- `backend/app/services/tenant.py:146` — 仕入れ permissions（`reports.view` 含む）
- `backend/app/services/tenant.py:163` — 発送 permissions（`reports.view` 含む）
