#!/bin/bash
# DB 接続の application_name の正本（docs/handoff/deploy-db-stall/design.md §16-3）。
# source して使う。backup.sh・run_all_migrations.sh・deploy-db-orphan-cleanup.sh が読む。
# scripts/migration_py_entry.py の APP_NAME は Python なので source できない。
# 同じ文字列であることを CI の試験 C4（backup-script-test.yml）が確かめる。
SA_APPNAME_MIGRATION=salesanchor_migration
SA_APPNAME_BACKUP_DEPLOY=salesanchor_backup_deploy
SA_APPNAME_BACKUP_CRON=salesanchor_backup_cron
