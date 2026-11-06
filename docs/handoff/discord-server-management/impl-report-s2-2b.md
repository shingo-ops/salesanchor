# 実装報告: 第2段 2b（スタッフのロールの付け外し／消したスタッフを自社サーバーから外す）

- 受領確認: card-s2-2b-staff-role-sync.md を読んだ
- origin/release/discord-own-server-s2-2b の先頭 sha（`git rev-parse origin/release/discord-own-server-s2-2b` の生出力）: `f51269985e3478abaa571861b367a61e5f3ea1ff`
- 触るファイルは 14 個と報告書だけ、と理解した

## §0 準備

### executor-preflight（生出力。クラウドのため [1/3][2/3] の FAIL はカードの想定どおり。[3/3][4/4] は OK）

```
== executor preflight (identity=shingo-cc, mode=fix) ==
[1/3] network -> api.github.com
  [FAIL] GitHub API に到達不可。Mac回線ではなく実行役サンドボックスの通信OFFが濃厚。
       => Codexをネット有効で起動 (信頼repo内: codex --sandbox danger-full-access / または config の network_access=true)
[2/3] gh auth = shingo-cc
  [warn] gh の active account が shingo-cc でない。gh auth switch で切り替え試行...
  [FAIL] gh auth switch --hostname github.com --user shingo-cc に失敗。gh auth status --active で現状を確認。
[3/3] git config user.name = shingo-cc
  [OK]   git user.name を shingo-cc に設定
[4/4] long-lived branch -> origin/main
  [OK]   origin/main は存在
==============================================
PREFLIGHT FAIL — 上の対策を実施し再実行(深追いしない)
```

### 作業場所

- `git log -1 --oneline` の生出力: `f51269985 docs(discord): 第2段 2b の細かい決め D2-8 と実装カード・台帳`
- `bash scripts/ledger-lookup.sh release/discord-own-server-s2-2b` の生出力（rc=0）:
  `| release/discord-own-server-s2-2b | Discord: 第2段 2b 自社サーバーのスタッフのロールを5分ごとと書いたあとに付け外し／消したスタッフを自社サーバーから外す | 2026-11-06 | IN_PROGRESS | | | docs/handoff/discord-server-management/card-s2-2b-staff-role-sync.md |`

### 変更前の行（実物。すべてカードと同じ行番号・同じ文）

```
staff.py:42: from app.services.audit import record_audit_log
staff.py:141: _UPDATABLE = {
staff.py:643:         await invalidate_user_permissions(tenant_id, user_id)
staff.py:718:     if ui_prefs is not None:
staff.py:735:         await invalidate_user_permissions(tenant_id, old_row["user_id"])
staff.py:757:         # 副テーブルは ON DELETE CASCADE で消える
roles.py:42: from app.services.audit import record_audit_log
roles.py:377:     await invalidate_tenant_permissions(tenant_id)
roles.py:606:     await invalidate_user_permissions(tenant_id, user_id)
celery_app.py:49:         "app.tasks.google_calendar_sync",  # ADR-1059 便2: Google の予定の取り込み
celery_app.py:251:     "notify-viewer-share-flags-hourly": {
compose:225:   celery-worker:
compose:235:       - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-redis://redis:6379/2}
        message={<><strong>{deleteTarget?.surname_jp} {deleteTarget?.given_name_jp}</strong>{t("common.deleteConfirmSuffix")}<br />{t("common.irreversible")}</>}   (StaffPage.tsx:380)
    "deleteStaff": "スタッフを削除",   (ja.json:2110)
    "deleteStaff": "Delete Staff",   (en.json:2110)
@pytest.fixture(autouse=True)   (conftest.py:1921)
        await db.execute(text("DELETE FROM staff WHERE id = :id"), {"id": staff_id})   (staff.py:758。`sed -n '758p'` の生出力）
```

- 注: staff.py:758 は staff の行を消す文で、カードの想定どおり。§4（６）はその文の直後に足した。
- 行の守り（RLS）の確かめ: `grep -rln tenant_discord_config migrations | xargs grep -n "ROW LEVEL"` → 出力なし（rc=123＝xargs の grep が 1 件も当たらなかった。守りは無い）

## 実装

- §1・§2 はカードのコードを 1 文字も変えずに写した（ruff が並びの直しを求めなかったので、並びの直しもなし）
- §3〜§9・§11・§12 はカードどおり。staff.py・roles.py の行番号は §4（２）で 10 行増えるため、（３）以降は文を頼りに一意の場所へ足した
- §10 の試験は 26 件（カードの 25 項目＋ 9 を「一時的な失敗」と「恒久的な失敗」の 2 件に分けた）
- §10-22 の `PUT /users/{id}/roles` は、スキーマ（`UserRoleAssign.role_ids` が 1 件以上必須）のため `{"role_ids": [1]}` を送る形にした（カードの準備の写しのまま、本文のみ）

## §13 確かめ（生出力）

### 1. pytest（python3.12 の venv に backend/requirements.txt ＋ pytest・pytest-asyncio・aiosqlite・pytest-xdist・pytest-cov・ruff）

```
215 passed, 1 skipped, 65 warnings in 21.68s
rc=0
```

- 1 skipped は既存の試験側の skip（私が足したものではない）。新規ファイル単体: `26 passed, 13 warnings in 16.35s`

### 2. ruff

```
All checks passed!
ruff rc=0
```

### 3. check_test_schema_dup（commit 前の最初の実行は「変更なし」で素通りしたため、commit 後にもう一度流した結果を下の「§14」に貼る）

最初の実行（commit 前・参考）:
```
対象テストファイルの変更なし - スキップ(pass)
rc=0
```

### 4. tenant_1.json

```
rc=0
```

### 5. docker compose config -q

```
rc=0
```
（警告は環境変数が未設定の旨と `version` が古い旨のみ。docker はクラウドにあった）

### 6. eslint（StaffPage.tsx）

```
eslint rc=0
```

### 7. tsc

- 最初の実行（`src/api/generated/schema` が無い環境のため）: 私が触っていないファイルの 4 件で `tsc rc=2`
  - `soldOutApi.ts`・`OwnInventoryPage.tsx`: Cannot find module '../../api/generated/schema'
  - `SoldOutResultsPanel.tsx`: TS7006（上記の型が無いための連鎖）
- `frontend/package.json` の標準の手順 `npm run generate:api-types`（出力先 `src/api/generated/` は .gitignore。tracked な差は出ない＝`git status` で確認）を流したあと:
```
tsc rc=0
```

### 8. i18n の点検

- `frontend/CLAUDE.md` に grep のセルフチェックの記述は無かった（`@AGENTS.md` の取り込みのみ）。`frontend/AGENTS.md`「i18n 強制」は ESLint の `local/no-japanese-literal` が自動検出するとあり、上の eslint が rc=0。加えて StaffPage.tsx の追加行の日本語直書きを grep:
```
grep rc=1 (1=該当なし)
```
- ja と en の `staff` の下のキー:
```
ja 29 en 29 same true
only_ja [] only_en []
Discord の自社サーバーからも外れます。 | They will also be removed from your company's Discord server.
```

### 9. grep の確かめ

```
## grep -n 'List Guild\|/members"' backend/app/services/discord_own_staff_sync.py
5:全員の一覧（List Guild Members）は読まない。Bot が管理するロール（アプリの役割につないだ番号・
## grep -rn '"staff"' backend/app/services/discord_own_staff_sync.py
25:STAFF_ROLE_KEY = "staff"
```

## §14 保存

### check_test_schema_dup（commit 後の生出力）

```
[INFO] backend/tests/test_discord_own_server_apply.py: BASE=0 HEAD=0
[INFO] backend/tests/test_discord_own_server_plan.py: BASE=0 HEAD=0
[INFO] backend/tests/test_discord_own_staff_sync.py: BASE=0 HEAD=0
テストへの新規スキーマ複製なし(pass)
rc=0
```

### git diff --name-only origin/main...HEAD（生出力）

```
.claude-pipeline/active-work.d/release-discord-own-server-s2-2b.md
backend/app/celery_app.py
backend/app/discord_blueprints/tenant_1.json
backend/app/routers/roles.py
backend/app/routers/staff.py
backend/app/services/discord_own_staff_sync.py
backend/app/tasks/discord_own_staff_sync.py
backend/tests/conftest.py
backend/tests/test_discord_own_server_apply.py
backend/tests/test_discord_own_server_plan.py
backend/tests/test_discord_own_staff_sync.py
docker-compose.yml
docs/handoff/discord-server-management/card-s2-2b-staff-role-sync.md
docs/handoff/discord-server-management/design.md
docs/handoff/discord-server-management/impl-report-s2-2b.md
frontend/src/locales/en.json
frontend/src/locales/ja.json
frontend/src/pages/staff/StaffPage.tsx
```

- Opus の文書 3 つ（`.claude-pipeline/active-work.d/…`＝台帳・カード・design.md）＋触ってよい 14 個＋報告書。それ以外は無い。

### commit（生出力。amend 前の commit 時点の `git log --oneline -3`）

```
3b3a61cc7 feat(discord): 自社サーバーのスタッフのロールをアプリの登録どおりに付け外し・消したスタッフを自社サーバーから外す（discord-server-management 第2段 2b）
f51269985 docs(discord): 第2段 2b の細かい決め D2-8 と実装カード・台帳
b437f27d1 Merge pull request #5193 from shingo-ops/release/ledger-done-5188
```

- この節を足すために、push 前の自分の commit を amend した（push 済みの履歴は触っていない）。そのため最終の sha は上と違う。push 後の `git rev-parse HEAD` と push の出力は、報告書に書くと sha が変わり続けるため、最後の返事に貼る。
