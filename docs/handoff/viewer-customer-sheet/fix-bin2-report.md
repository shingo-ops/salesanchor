# 便2 直し1 報告（fix-bin2-report.md）

カード 便2 直し1 を受領。対象: release/viewer-billing-form-bin2（PR #5137）。

## 変えたもの（カード §2 の3ファイルのみ）
- 新規 frontend/src/pages/super-admin/components/ViewerBillingSection.tsx（請求先の区切りを移した部品。中身は移しただけ）
- frontend/src/pages/super-admin/ViewerAccountsPage.tsx（1042行 → 922行。部品の呼び出しに置き換え。key={detail.id}。useEffect 内の2行の初期化を削除。ApiError などの import は他で使うため残した）
- backend/tests/test_viewer_billing_form_pg.py（test_billing_fields_live_in_one_table_only のみ design §3-2 の数え方に書き直し。先に両表の存在を to_regclass で確認）

check-page-size.js・ベースライン json・ViewerAccountsPage.test.tsx・locales は変更なし。

## 手順2 preflight
./scripts/dev/executor-preflight.sh は exit=1。原因は [1/3] api.github.com に到達不可（クラウドの通信制限）と [2/3] gh auth switch shingo-cc の失敗。いずれも gh/GitHub API 側の確かめで、git fetch/push は通る環境。カード §4-2 に従い、出力をここに書いて続けた。

## 手順4 確かめ（終了コードと最後の20行）
### node scripts/check-page-size.js — exit 0
```
✅ ページサイズチェック PASSED
```
wc -l ViewerAccountsPage.tsx = 922（上限1000以下）

### npm run check:all — exit 0（lint は warning 59・error 0。main にもある既存の warning）
```
[1]   150:13  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1]   158:14  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1]   159:14  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1]   160:14  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1]   165:22  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1]   166:13  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1]   183:25  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1]   223:18  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1]   241:25  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1]   281:18  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1]   299:25  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1]   339:18  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
[1] 
[1] /root/worktrees/salesanchor/release-viewer-billing-form-bin2/frontend/src/pages/oauth-callback/OAuthCallbackPage.tsx
[1]   130:6  warning  React Hook useEffect has a missing dependency: 't'. Either include it or remove the dependency array  react-hooks/exhaustive-deps
[1] 
[1] ✖ 59 problems (0 errors, 59 warnings)
[1]   0 errors and 1 warning potentially fixable with the `--fix` option.
[1] 
[1] npm run lint exited with code 0
```
（generate:api-types は exit 0 で流したが、差分は出ていない）

### npx tsc --noEmit -p . — exit 0
```
(出力なし)
```

### npx vitest run（ViewerAccountsPage.test.tsx・BillingForm.test.tsx・ViewerTemplatesPage.test.tsx）— exit 0
```
|
!  No story files found for the specified pattern: src/**/*.mdx

 RUN  v4.1.7 /root/worktrees/salesanchor/release-viewer-billing-form-bin2/frontend

|
•  Storybook collects completely anonymous usage telemetry. We use it to
|  shape Storybook's roadmap and prioritize features. You can learn more,
|  including how to opt out, at ]8;;https://storybook.js.org/telemetryhttps://storybook.js.org/telemetry]8;;

 Test Files  3 passed (3)
      Tests  73 passed (73)
   Start at  18:46:23
   Duration  4.49s (transform 2.06s, setup 249ms, import 3.20s, tests 4.11s, environment 2.32s)
```

### pytest tests/test_viewer_billing_form_pg.py -q — exit 1（流せなかった）
この環境には PostgreSQL が無く、27件すべて skip。終了コード1は skip のみで総合カバレッジ 60% の下限（6.39%）に届かなかったため。試験の中身は通っていない＝「流せなかった」。PG のある CI（#5137）で確かめる必要がある。
```
app/tasks/tcg_extraction_recovery.py                   189    189     0%   23-587
app/tasks/tcg_import_discard.py                         22     22     0%   10-64
app/tasks/tcg_mirror.py                                114    114     0%   17-338
app/tasks/translation.py                                62     62     0%   1-177
app/tasks/verify_meta_subscriptions.py                 126    126     0%   41-360
app/tasks/viewer_inventory_cache.py                     81     57    30%   40-45, 50-69, 74-99, 104-134, 139-142
app/tasks/viewer_share_flag_monitor.py                  63     63     0%   7-96
app/tcg_config.py                                        8      8     0%   15-29
app/tools/__init__.py                                    0      0   100%
app/tools/prompt_ab.py                                 438    438     0%   20-727
app/tools/prompt_ab_recompute.py                        97     97     0%   11-147
app/tools/reextract_v6_with_v102.py                    562    562     0%   27-852
app/tools/sync_review_reason_labels.py                  15     15     0%   8-31
app/viewer_admin_cli.py                                 30     30     0%   6-53
app/viewer_discord_cli.py                               85     85     0%   6-141
app/viewer_register_cli.py                              19     19     0%   6-30
----------------------------------------------------------------------------------
TOTAL                                                46216  43262     6%
FAIL Required test coverage of 60% not reached. Total coverage: 6.39%
27 skipped in 8.51s
```

### git diff --stat
§2 の3ファイルと本報告ファイルだけ（commit 前に確認）。
