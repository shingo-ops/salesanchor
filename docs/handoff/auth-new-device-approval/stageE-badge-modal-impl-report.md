# 段E 実装報告: 鈴のバッジ（数の丸）と依頼の小窓（ADR-1055）

## HEAD の確認
- 作業開始時の HEAD: 247fcd510b1f26cfb3f72212f0f89d57fdfcf0df（247fcd510 で始まる＝指示どおり）
- 実装 commit: 9601382e70ba6a912484d874a758a70f6165f891

## 変えたファイル
- M	frontend/src/App.tsx
- M	frontend/src/components/Badge.css
- M	frontend/src/components/Badge.stories.tsx
- M	frontend/src/components/Badge.tsx
- M	frontend/src/components/NoticeBell.css
- M	frontend/src/components/NoticeBell.test.tsx
- M	frontend/src/components/NoticeBell.tsx
- R090	frontend/src/features/auth/LoginRequestDetailPage.test.tsx	frontend/src/features/auth/LoginRequestDecision.test.tsx
- R089	frontend/src/features/auth/LoginRequestDetailPage.tsx	frontend/src/features/auth/LoginRequestDecision.tsx
- M	frontend/src/index.css
- M	frontend/src/tokens.css
- M	tests/prod-check/device-accept.spec.ts

## §6 の分岐に当たったか
- 当たっていない。Badge の試験ファイルは無く、NoticeBell.test.tsx 側の 1 件で確かめた。Modal は Popover の外の同じ階層に置いた。消した経路を指す箇所は App.tsx の 2 か所のみ。CSS 検査・題名検査は通った。
- 作業中、最初の試験ファイルの書き出しで自分の置換ミスがあり（import 行を誤って切った）、作り直した。内容への影響なし。

## 確かめ (1 npx tsc --noEmit)
```
exit 0
```
## 確かめ (2 npm run lint)
```

/root/worktrees/salesanchor/release-notice-badge-modal/frontend/src/pages/oauth-callback/OAuthCallbackPage.tsx
  130:6  warning  React Hook useEffect has a missing dependency: 't'. Either include it or remove the dependency array  react-hooks/exhaustive-deps

✖ 59 problems (0 errors, 59 warnings)
  0 errors and 1 warning potentially fixable with the `--fix` option.

exit 0
```
## 確かめ (3 vitest NoticeBell.test + LoginRequestDecision.test（Badge の試験ファイルは無い）)
```
|
!  No story files found for the specified pattern: src/**/*.mdx

 RUN  v4.1.7 /root/worktrees/salesanchor/release-notice-badge-modal/frontend


 Test Files  2 passed (2)
      Tests  10 passed (10)
   Start at  02:47:42
   Duration  2.16s (transform 865ms, setup 120ms, import 1.43s, tests 627ms, environment 1.55s)

exit 0
```
## 確かめ (4) npx vitest run（全部）
storybook プロジェクト（ブラウザ試験）は作業場所に Chromium が無く起動できないため飛ばした（CI を正とする）。全部を流したときの要約:
```
 Test Files  197 passed (272)
      Tests  2216 passed (2216)
     Errors  1 error
```
unit プロジェクトだけ（npx vitest run --project unit）の結果、落ちた数 0:
```

 Test Files  197 passed (197)
      Tests  2216 passed (2216)
   Start at  02:50:15
   Duration  132.40s (transform 9.81s, setup 4.81s, import 66.78s, tests 125.50s, environment 160.11s)

exit 0
```
## 確かめ (5) bash scripts/dev/check-before-submit.sh（commit 後・末尾）
```
  - run_rule_fixtures（全件）                    流していない: CI で確かめる（約 375 秒。--full で流せます）

== 版の違い（手元と CI）==
  手元: Python 3.11.18 / node v22.23.4
  CI  : Python 3.12 / node 22（guard-authoring だけ 24）
  版が違うので、最後の判定は CI です（この入口は提出前の補助）

合計 10.8 秒 / 必須 16 件を表示 / 流した検査 18 件 / 落ちた検査 0 件 / ログ /tmp/check-before-submit.STtdKT（消さずに残します）
注意: この枝は main より遅れている。main を取り込んでから流すと CI と同じ結果になる
結果: ○ 流した検査は全部通りました（終了コード 0）
流した印を書きました: /home/user/salesanchor/.git/worktrees/release-notice-badge-modal/check-before-submit.ok
exit 0
```
## 確かめ (6) git grep（0 件＝出力なし・終了コード 1）
```
exit 1
```
## 確かめ (7) ja.json / en.json のキー数（葉の数）
```
ja 5272
en 5272
```
## 確かめ (8) check-dark-parity.js
```
✅ ダークモード変数パリティチェック PASSED (131 変数すべて対応済み)
exit 0
```
## 【4/5】generate:icon-sizes
実行後の git status は空（差分なし）。
```
> node scripts/generate-icon-sizes.js

exit 0
```
## 【4/5】git diff origin/main -- frontend/src | grep -n px（生出力）
px を含む行は、tokens.css の定義行（+ の行）と、既存の行・Badge.stories の既存の行のみ。stories の新しい行は var(--space-2)。
```
65:     <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
591:   --notice-panel-width:       360px;                     /* 知らせ一覧の幅 */
593:   --notice-unread-dot-size:   8px;                       /* 未読の丸 */
594:+  --notice-bell-icon-size:        var(--icon-lg);   /* 24px — 鈴の絵（Instagram 実測 24） */
595:+  --notice-bell-badge-offset-x:   11px;             /* 鈴の絵の左から数の丸の左まで（Instagram 実測） */
596:+  --notice-bell-badge-offset-y:   9px;              /* 鈴の絵の上から数の丸の上まで（Instagram 実測） */
599:      .page-subtitle は margin-bottom: var(--space-3) = 12px（pages-layout.css）。
602:   --comp-badge-height-sm:  20px;                       /* small */
603:   --comp-badge-height-md:  24px;                       /* medium */
604:+  --comp-badge-count-size:  18px;                 /* 数の丸の中身の高さ・最小幅（Instagram 実測 2026-11-05） */
605:+  --comp-badge-count-ring:  var(--space-2px);     /* 2px — 数の丸の外枠の太さ（Instagram 実測） */
606:+  --comp-badge-count-font:  var(--font-2xs);      /* 11.2px — Instagram 実測 11px に一番近い既存の段 */
609:   --comp-badge-dot-size:   var(--space-6px);           /* 6px */
```
注: この枝は origin/main より遅れているため、下の diff には main の側の新しい変更が逆向きに含まれる。
## git diff --stat origin/main
```
 .../release-discord-own-server-bin2.md             |   5 -
 .../active-work.d/release-notice-badge-modal.md    |   5 +
 .github/workflows/migration-guard.yml              |   2 +-
 backend/app/main.py                                |   6 -
 backend/app/realtime/topics.py                     |   1 -
 backend/app/routers/discord_own_server.py          | 173 -------
 backend/tests/conftest.py                          |  14 -
 backend/tests/test_discord_own_server_snapshot.py  | 277 -----------
 .../stageE-badge-modal-card.md                     | 228 +++++++++
 .../card-bin2-own-server-snapshot.md               | 552 ---------------------
 docs/handoff/discord-server-management/design.md   |  18 -
 .../discord-server-management/impl-report-bin2.md  |  57 ---
 frontend/api-contract/openapi.json                 |  50 --
 frontend/src/App.tsx                               |   2 -
 frontend/src/components/Badge.css                  |  13 +
 frontend/src/components/Badge.stories.tsx          |  10 +
 frontend/src/components/Badge.tsx                  |   4 +-
 frontend/src/components/NoticeBell.css             |   4 +-
 frontend/src/components/NoticeBell.test.tsx        |  21 +-
 frontend/src/components/NoticeBell.tsx             |  37 +-
 ...Page.test.tsx => LoginRequestDecision.test.tsx} |  14 +-
 ...uestDetailPage.tsx => LoginRequestDecision.tsx} |  24 +-
 frontend/src/index.css                             |   2 +
 frontend/src/locales/en.json                       |   5 +-
 frontend/src/locales/ja.json                       |   5 +-
 .../src/pages/admin/DiscordOwnServerPanel.test.tsx |  67 ---
 frontend/src/pages/admin/DiscordOwnServerPanel.tsx |  29 --
 frontend/src/tokens.css                            |   6 +
 ...20000_create_discord_server_snapshot_tables.sql |  69 ---
 scripts/run_all_migrations.sh                      |   2 -
 tests/prod-check/device-accept.spec.ts             |  16 +-
 31 files changed, 348 insertions(+), 1370 deletions(-)
```
