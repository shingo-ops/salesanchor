# 実装カード: 名簿から「電話」「対面」を外す手順一式

- 設計: docs/handoff/conversation-unification/phone-off/design.md（同じ枝）
- 前例（形をそろえる）: docs/handoff/conversation-unification/data-store/ の run.sh と SQL 5 本
- 枝: release/channel-phone-in-person-off
- 実装役: クラウドの Sonnet。この手順一式は「書くだけ」。本番に流すのは Opus（PO の委任・manual-only 鍵）

## 1. 作るファイル（この 6 つだけ。ほかは触らない）

置き場所はすべて docs/handoff/conversation-unification/phone-off/。SQL は .gitignore の `*.sql` に当たるので `git add -f` で入れる。

### 1-1. run.sh

data-store/run.sh を写し、次の 3 か所だけ変える。
- 2 行目のコメント: `# 名簿の共通行 id 10・11（phone・in_person）を全社で外す（is_active=false）。`
- 3 行目のコメント: `# 設計 docs/handoff/conversation-unification/phone-off/design.md・card.md。`
- 4 行目のコメント: `# PO の委任を受けた Opus が manual-only 鍵で流す。`
- 5 行目のコメント: `# 順番: precheck → dryrun → commit → verify（戻すとき: rollback）`
- 6 行目以降（`set -euo pipefail` から最後まで）は一字も変えない。ファイルは全部で data-store/run.sh と同じ行数。

### 1-2. 各 SQL の 1 行目（共通の見出し）

`-- 名簿から電話・対面を外す（PO 2026-11-08「3」全社の名簿から外す）。設計 docs/handoff/conversation-unification/phone-off/design.md。`

### 1-3. precheck.sql（読み取りだけ）

1 行目の見出しの後に、この順で書く。
```
-- precheck（読み取りだけ）。名簿が設計の形と違えばゼロ除算で止まる。
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL)=6 THEN 1 ELSE 0 END) AS shared_must_be_6;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=true AND id IN (10,11) AND platform IN ('phone','in_person'))=2 THEN 1 ELSE 0 END) AS ids_10_11_must_be_active;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=true AND id IN (7,8,9,12))=4 THEN 1 ELSE 0 END) AS ids_7_8_9_12_must_be_active;
SELECT id, tenant_id, platform, display_name, is_active, updated_at FROM public.channel_masters ORDER BY id;
```

### 1-4. dryrun.sql（試して必ず ROLLBACK）

```
-- dryrun（試して必ず ROLLBACK する）。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL app.is_operator = 'true';
UPDATE public.channel_masters SET is_active=false, updated_at=now() WHERE id IN (10,11) AND tenant_id IS NULL AND platform IN ('phone','in_person') AND is_active=true;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL)=6 AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=true)=4 AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=false AND id IN (10,11))=2 THEN 1 ELSE 0 END) AS phone_in_person_off;
ROLLBACK;
```

### 1-5. commit.sql

dryrun.sql と同じ中身で、2 行目のコメントを `-- commit（PO の委任を受けた Opus が流す）。数が違えばゼロ除算で失敗し、COMMIT に届かない。`、最後の `ROLLBACK;` を `COMMIT;` にする。

### 1-6. verify.sql（読み取りだけ）

```
-- verify（読み取りだけ）。
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL)=6 AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=true)=4 AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=false AND id IN (10,11))=2 THEN 1 ELSE 0 END) AS phone_in_person_off;
SELECT id, tenant_id, platform, display_name, is_active, updated_at FROM public.channel_masters ORDER BY id;
```

### 1-7. rollback.sql（id 10・11 を戻す）

```
-- rollback（id 10・11 を is_active=true に戻す）。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL app.is_operator = 'true';
UPDATE public.channel_masters SET is_active=true, updated_at=now() WHERE id IN (10,11) AND tenant_id IS NULL AND platform IN ('phone','in_person') AND is_active=false;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=true)=6 THEN 1 ELSE 0 END) AS restored;
COMMIT;
```

## 2. 触らない範囲

- backend/・frontend/・migrations/・scripts/・.github/ は一切触らない
- data-store/ の既存ファイルは触らない
- design.md・card.md は触らない

## 3. 確かめ（クラウドで）

- `bash -n docs/handoff/conversation-unification/phone-off/run.sh` が rc=0
- `diff <(sed -n '6,$p' data-store/run.sh) <(sed -n '6,$p' phone-off/run.sh)` が空（実行の部分が同じ）
- `git diff --name-only origin/main...HEAD` が phone-off/ の 8 ファイル（design.md・card.md・run.sh・SQL 5 本）だけ
- 本番・DB には接続しない

## 4. 返事

1 行目は DONE / BLOCKED: / NEEDS_DECISION: のどれか。続けて、確かめのコマンドの生の出力と `git log --oneline -3` と `git ls-remote origin refs/heads/release/channel-phone-in-person-off`。
