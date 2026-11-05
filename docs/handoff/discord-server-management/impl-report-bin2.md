# 実装報告 便2（自社用サーバーの今の姿を読み取る）

- 受領確認: card-bin2-own-server-snapshot.md を読んだ
- origin/release/discord-own-server-bin2 の先頭 sha（git rev-parse の生出力）: 81ab7b299d7d237abf7153e07d3d1b6d7b0d4fd6
- 触るファイルは上の一覧と報告書だけ、と理解した

## §0 preflight 生出力

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

クラウドの [1/3][2/3] の FAIL はカードの想定どおり。[3/3][4/4] は OK のため先へ進む。

## §8 確かめ（生出力）

- `bash -n scripts/run_all_migrations.sh`: 出力なし（rc=0）
- `grep -n "20261106_120000_create_discord_server_snapshot_tables" scripts/run_all_migrations.sh`: `1229:run_sql migrations/20261106_120000_create_discord_server_snapshot_tables.sql`（1 行）。最後の run_sql は想定どおり `20261104_161223_add_calendar_events_meet_url.sql` だった
- `grep -c "discord_server_snapshots discord_server_apply_runs" .github/workflows/migration-guard.yml`: `1`
- `git diff origin/main --stat -- .github/workflows/migration-guard.yml`: `1 file changed, 1 insertion(+), 1 deletion(-)`（末尾 `…ai_job_assignment_history discord_server_snapshots discord_server_apply_runs"` の 1 行入れ替えのみ）
- 移行ファイルとカード §1 の SQL（カード 64-132 行）の diff: 差分なし（rc=0）
- pytest（カード指定の 7 ファイル、`/tmp/v312/bin/python`）: `87 passed, 5 warnings in 9.92s`（失敗 0）
- openapi 生成: `ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` rc=0、`frontend/api-contract/openapi.json | 50 +++`
- `scripts/check_test_schema_dup.py`: 試験ファイルが未 commit の時点では「対象テストファイルの変更なし - スキップ(pass)」rc=0。commit 後の再実行結果は下に追記
- 全体の pytest: 流していない（CI に任せる）
- vitest（DiscordOwnServerPanel.test.tsx・DiscordConfigPage.test.tsx）: `Test Files 2 passed (2) / Tests 13 passed (13)`
- `npm run check:i18n-missing-keys`: `✅ i18n key check PASSED (all prefixes)`
- `npm run lint -- <2 ファイル>`: `✖ 59 problems (0 errors, 59 warnings)`（警告は既存のファイル分。DiscordOwnServerPanel の 2 ファイルに警告なし）
- `npx tsc --noEmit -p .`: 最初は生成型 `src/api/generated/schema` が無く 4 件エラー（既存ファイル・未生成が原因）。`npm run generate:api-types` で生成後 rc=0
- `git grep -nE "style=|#[0-9a-fA-F]{3,6}\b|rgb\(" -- frontend/src/pages/admin/DiscordOwnServerPanel.tsx`: 0 行
- commit 後の `check_test_schema_dup.py`: `[INFO] backend/tests/test_discord_own_server_snapshot.py: BASE=0 HEAD=0` / `テストへの新規スキーマ複製なし(pass)` rc=0
- `git log --oneline -4`（commit 後）:
  ```
  4cbcb40be feat(discord): 自社用サーバーの今の姿を読み取る（discord-server-management 便2）
  e2f86facf feat(db): 自社用サーバーの今の姿と反映の記録の表を作る（discord-server-management 便2）
  81ab7b299 docs(discord): 便2 カードの目印を本線取り込み後の値に合わせる
  a89caa285 Merge remote-tracking branch 'origin/main' into release/discord-own-server-bin2
  ```
- push（pre-push の提出前の入口: 落ちた検査 0 件・rc=0）: `81ab7b299..4cbcb40be  HEAD -> release/discord-own-server-bin2`
- PostgreSQL なし・CI の migration-test に任せる
- `git diff --stat origin/main`: 15 files changed, 1205 insertions(+), 3 deletions(-)（`.claude-pipeline` の札・カード・design.md はこの枝の既存コミット由来。報告書を足す前の値）

---

`migrations/20261106_120000*` は既存なし（20261106_100000 のみ）。run_all_migrations.sh の最後の run_sql は `migrations/20261104_161223_add_calendar_events_meet_url.sql`（カードの記載どおり）。
