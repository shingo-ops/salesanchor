# Runbook: ファネルダッシュボード PR1 デプロイ手順

**対象**: migrations 101〜105（deals.closed_at / close_reasons / leads initiative+channel / goals kpi拡張 / purchase_cost nullable）  
**前提**: PO の明示 GO を確認済みであること  
**作成日**: 2026-06-12  
**関連**: `docs/adr/ADR-138-funnel-dashboard-stage1.md`

---

## 0. 実施前チェックリスト

- [ ] PO から「PR1 GO」の明示確認（チャット or GitHub コメント）
- [ ] CI（GitHub Actions）が緑であること
- [ ] `gh pr view` でPR が open 状態であること

---

## 1. 直前バックアップ取得（必須）

```bash
# VPS に SSH
ssh -i ~/.ssh/id_ed25519 ubuntu@49.212.137.46

# バックアップ実行（pg_dump, custom 形式）
source ~/.claude-access.env 2>/dev/null || true
cd /home/ubuntu/salesanchor

BACKUP_FILE="/home/ubuntu/backups/postgres/pre_pr1_funnel_$(date +%Y%m%d_%H%M%S).dump"
docker compose exec -T postgres \
  pg_dump -U jarvis -d jarvis_db --format=custom \
  > "${BACKUP_FILE}"

ls -lh "${BACKUP_FILE}"
# → ファイルサイズが 0 でないことを確認
echo "Backup: ${BACKUP_FILE}"
```

バックアップが取得できたことを確認してから次のステップへ。

---

## 2. デプロイ実行

GitHub Actions の通常 deploy フローに従う。migrations は `backend/startup.py` の自動適用で実行される。

```bash
# PR をマージ（develop へ）後、deploy.yml が自動トリガー
# または手動デプロイ:
gh workflow run deploy.yml --ref develop
```

---

## 3. デプロイ後確認

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@49.212.137.46

# migration ログ確認（backend コンテナ起動ログ）
docker compose logs backend --tail=100 | grep -E 'Migration 10[1-5]|ERROR|FATAL'
# 期待: "Migration 101: complete" 〜 "Migration 105: complete"

# deals.closed_at が追加されていること
docker compose exec -T postgres psql -U jarvis -d jarvis_db -c \
  "SELECT column_name, data_type, is_nullable
   FROM information_schema.columns
   WHERE table_schema='tenant_004' AND table_name='deals' AND column_name='closed_at';"
# 期待: closed_at | timestamp with time zone | YES

# close_reasons テーブルが存在し、デフォルト値が入っていること
docker compose exec -T postgres psql -U jarvis -d jarvis_db -c \
  "SELECT type, COUNT(*) FROM tenant_004.close_reasons GROUP BY type ORDER BY type;"
# 期待: lost | 8, won | 7

# leads.source が削除され initiative/channel_type が追加されていること
docker compose exec -T postgres psql -U jarvis -d jarvis_db -c \
  "SELECT column_name FROM information_schema.columns
   WHERE table_schema='tenant_004' AND table_name='leads'
   AND column_name IN ('source','initiative','channel_type') ORDER BY column_name;"
# 期待: channel_type, initiative（source は表示されない）

# purchase_cost が NULL 許容になっていること
docker compose exec -T postgres psql -U jarvis -d jarvis_db -c \
  "SELECT column_name, is_nullable, column_default
   FROM information_schema.columns
   WHERE table_schema='tenant_006' AND table_name='order_financials'
   AND column_name='purchase_cost';"
# 期待: is_nullable=YES, column_default=NULL

# goals kpi_type CHECK 制約が更新されていること
docker compose exec -T postgres psql -U jarvis -d jarvis_db -c \
  "SELECT pg_get_constraintdef(c.oid)
   FROM pg_constraint c
   JOIN pg_class t ON t.oid=c.conrelid
   JOIN pg_namespace n ON n.oid=t.relnamespace
   WHERE n.nspname='tenant_004' AND t.relname='goals' AND c.contype='c'
   AND pg_get_constraintdef(c.oid) LIKE '%kpi_type%'
   AND pg_get_constraintdef(c.oid) NOT LIKE '%owner_check%';"
# 期待: won_count と gross_profit が含まれること
```

---

## 4. 異常時ロールバック

```bash
# バックアップからリストア（全データ上書き）
BACKUP_FILE="<ステップ1で記録したパス>"

docker compose exec -T postgres \
  pg_restore -U jarvis -d jarvis_db --clean --if-exists \
  < "${BACKUP_FILE}"

# コンテナ再起動
docker compose restart backend celery-worker celery-beat
```

**注意**: リストアは全テナントデータを上書きする。実施前に PO 確認必須。
