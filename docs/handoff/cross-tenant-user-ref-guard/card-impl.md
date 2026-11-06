---
mode: handoff
---
# 実装カード: 他社の人の番号を保存させない6入口と、Discord の手で打つ登録口を閉じる

親: [design.md](./design.md) 1〜5 節・10 節・12 節（Architect r5 APPROVE・13 節）／根拠: [recon.md](./recon.md)

- 状態: カード作成済み（2026-11-06 Opus）。実装は未着手。
- PO の言葉（原文。design.md 0 節）: 「1、推測は禁止して事実確認を怠らずに確実性を重視して最も効果があり、現状把握の粒度が細く、精度が高いエビデンスを確立して安全に進めてくれ。」「確立したなら進める。」「fableが最終評価、DBのSSOTとセキュリティリスクで問題がなければGO」。設計の審査合格（r5 APPROVE）をもって実装に進む。マージと本番への反映は Fable の最終評価の後（Opus が行う）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・GO 記録・マージ判断。
- 本カードの許可・禁止は、過去のカードの禁止条項をすべて上書きする。
- 区分: A（`frontend/api-contract/` を触るため。ADR-1015）。`migrations/`・`deploy.yml`・本番 `scripts/` は触らない。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§6。PR は Opus が作る） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1つの作業に1つの目的（6入口の照合と Discord の手で打つ口を閉じる。連携の戻り口の証明 G3 は別の作業） | ○ |
| 5 | 起点の明示（origin/main から new-worktree.sh で作業場所を作り、設計の枝を取り込む） | ○（§5 手順1） |
| 6 | PR 欄の書式を良い例と禁止形で示す | ○（§6） |
| 7 | 合格基準を出力まで縛る（想定外の削除が無いこと） | ○（§5 手順10） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順10） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の作業名） | ○（§7） |
| 11 | 行番号を停止条件にしない（行番号は目印。前後の文で探す） | ○ |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・validate-pr-body.sh・フックに止められたら言い換えない） | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・03-file.md・04-worktree.md・05-pr.md・11-lint.md。

基準: 設計の基準 origin/main 133808dce。r5 審査で origin/main 5a8b0dd91 と比べ、対象ファイルの差分は無い。行番号は目印で、ずれていたら前後の文で探す。

## 1. 目的（利用者に見える変化）

- 自社の人を選んで保存する普段の操作は今までと同じ。
- 別の会社の人の番号を送ると、保存されずに 422「指定された担当者が見つかりません」が返る（6入口）。
- Discord の設定画面から、サーバー番号を手で打つ欄が無くなる。代わりにチャネル画面（`/channels`）へ案内するボタンが出る。連携済みの会社の設定はそのまま。
- `PUT /api/v1/admin/discord-config` は 405 を返し、表を変えない。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `backend/app/services/tenant_users.py`（新規） | design 4-1 の関数をそのまま置く |
| `backend/app/routers/leads.py` | create_lead・update_lead に1行ずつ（design 4-2） |
| `backend/app/routers/shifts.py` | create_shift に1行（design 4-2） |
| `backend/app/routers/goals.py` | create_goal に1行（design 4-2） |
| `backend/app/routers/teams.py` | create_team・update_team に1行ずつ（design 4-2） |
| `backend/app/routers/discord_guild_config.py` | PUT の口と、ほかで使わなければ `DiscordConfigUpdate`、冒頭の説明の PUT の行を消す（design 4-3） |
| `frontend/api-contract/openapi.json` と生成される型 | §5 手順7 の命令で作り直す（手で書かない） |
| `frontend/src/pages/admin/DiscordConfigPage.tsx` | 「① サーバー接続」カードを design 4-3 のとおりに直す |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | 新しいキー2つを足し、使わなくなるキーを消す（design 4-3） |
| `frontend/src/pages/admin/DiscordConfigPage.test.tsx` | design 5 節のとおりに直す |
| `backend/tests/test_discord_d2.py` | PUT の試験4本を消し、405 の試験1本に置き換える |
| `backend/tests/conftest.py` | `INBOX_BADGE_SQLITE_DDL` に users の表を足す |
| `backend/tests/test_inbox_new_assignment_badge.py` | design 5 節の手順(2)(3) |
| `backend/tests/test_analytics.py` | assigned_to 321 の人を会社 999 の users 行として足す |
| `backend/tests/test_notification_event_routing.py` | assigned_to 7・9 の人を会社 999 の users 行として足す |
| `backend/tests/test_shifts_pg.py` | (id=2, tenant_id=901) の users 行を入れてから呼ぶ。他社の人なら 422 の試験を足す |
| `backend/tests/test_tenant_user_ref_guard_pg.py`（新規） | §3-4 の試験 |

触らないもの: 照合済みの6入口（companies・teams のメンバー追加・roles・notice_fallback・bots・order_commissions）／`backend/app/routers/discord_oauth.py`（連携の戻り口。G3 で別の作業）／`backend/tests/test_discord_own_server.py`／badges.py・buddy.py／`migrations/`・`deploy.yml`・`scripts/`／各入口の権限・SQL・監査記録・commit と `reset_tenant_context` の位置／design.md・recon.md・本カード（Opus が直す）。

## 3. 作るものの決まり（design.md が正。食い違えば design.md に従い、報告する）

### 3-1. backend

- `tenant_users.py` は design 4-1 のコードのとおり。is_active は見ない。SQL の `tenant_id = :tid` を外さない。
- 6入口に足す行と置く場所は design 4-2 の表のとおり。DB に書く前に呼ぶ。
- 照合の SQL を routers に直書きしない。`git grep -n "FROM public.users WHERE id = :uid AND tenant_id" backend/app/routers` が5件のままであること（K3）。
- Discord: `DiscordConfigUpdate` を消す前に `git grep -n DiscordConfigUpdate` で使う所を確かめ、結果を報告に書く。

### 3-2. 画面（DiscordConfigPage.tsx）

- design 4-3 の「変更後」「消すもの」のとおり。`ButtonLink`（:20 で読み込み済み）に `to="/channels"` を渡す。2つの `ButtonLink` は `canEdit` のときだけ出す。
- `:374` の `!guildReady` は `!configQ.data` に置き換える。`fetchAll` の CONFIG_PATH の取り直し（:186）と `useSeededForm` の読み込み（:16）と `SNOWFLAKE_RE` は残す。
- 金型だけを使う（ADR-144）。色・余白の直書きをしない（ADR-067）。文字はすべて `t()`（ADR-027）。新しい部品・新しい class を作らない。金型にない部品が要ると分かったら停止して報告する。
- 新しいキー: `discordConfig.connectViaChannels`（ja「チャネル画面で連携する」・en「Connect on Channels page」）と `discordConfig.connectViaChannelsHint`（ja「Discord サーバーとの連携は、チャネル画面の連携ボタンから行います。」・en「Connect your Discord server with the connect button on the Channels page.」）。
- 使わなくなるキー（serverIdLabel・serverIdPlaceholder・serverIdHint・invalidGuildId・connect など）は、`git grep -n "discordConfig.キー名" frontend/src` でほかに使う所が無いものだけ ja・en の両方から消す。消したキーと確かめた結果を報告に書く。

### 3-3. 既存の試験の直し方（design 5 節）

- 照合を偽物に差し替えない（monkeypatch・mock 禁止）。本物の users 行を足す。
- `test_inbox_new_assignment_badge.py`: (1) users の表の DDL は `conftest.py` の `INBOX_BADGE_SQLITE_DDL` に足す (2) この engine の `sync_engine` に `before_cursor_execute`（`retval=True`）の仕掛けを足し、`public.users` を `users` に置き換える（`conftest.py:296-302` と同じ形。connect の手当て :75-81 は使わない）(3) assigned_to 10・20 の人を会社 999 で入れる。
- `DiscordConfigPage.test.tsx`: :47-74 を新しい画面に合わせて書き直す。:138-152・:154-162 のチケット設定の試験は残す。:164-173 は `queryByRole("link", { name: "Change" })` が null になる形に直す。権限ありの試験で `getByRole("link", { name: "Change" })` の `href` が `/channels` であることを確かめる。
- users 行を足す INSERT は、すべて末尾に `ON CONFLICT (id) DO NOTHING` を付ける（SQLite の DB は試験をまたいで共有されるため、付けないと同じ番号の2回目で落ちる。3回目の実行で `test_analytics.py`・`test_notification_event_routing.py` が落ちた）。
- `leads.py` の `from app.services.tenant_users import ensure_user_in_tenant` は、`from app.services.meta_graph import (...)` の塊の後に置く（ruff の I001 の並び順）。
- `test_discord_d2.py`: :307-340 の4本を消し、「PUT は 405・`public.tenant_discord_config` が変わらない」の試験1本に置き換える。

### 3-4. 新しい試験（design 10 節）

- `backend/tests/test_tenant_user_ref_guard_pg.py`: `test_shifts_pg.py` と同じ形（CI の使い捨て PostgreSQL 専用。`GITHUB_ACTIONS` でないときは skip）。2社と各社の人を作り、6入口それぞれで:
  - 他社の人の番号 → 422、行が増えない／変わらない
  - 自社の人の番号 → 今までどおり成功
  - 担当なし（None）→ 成功（leads・goals の team 目標・teams）
- 試験の値に実在の人の名前を使わない。

## 4. 守ること

- 担当は sleep しない（待ちは設計者が期限付きで行う）。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントで書かない。python などのスクリプトでファイルを書き換えない（1回目の実行で起きたため明記。2026-11-06 Opus）。
- PostgreSQL を自分で立てない（initdb・pg_ctl・作業用の場所の作り直しをしない）。`_pg` の試験は CI の使い捨て PostgreSQL で確かめる。手元では skip になってよい。
- `rm` を使わない（見張りが止める。1回目の実行はこれで止まった）。
- PR を作る前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（PR は Opus が作る）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 停止するのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除が要るとき／金型にない部品が要るとき／design.md と食い違うのに design.md どおりに作れないとき／§2 の表に無いファイルを直さないと試験が通らないとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く（判定は設計者がする）。
- 本番 DB・本番サーバーに接続しない。GO 記録・evidence-registry に書かない。マージしない。

## 5. 手順

クラウドで行う。取り出したリポジトリの最上位を「本店」と呼ぶ。本店では編集も commit もしない（見張りが commit を止める。3回目の実行はこれで手順9で止まり、作業がすべて消えた。2026-11-06 Opus）。手順1で作る `~/worktrees/salesanchor/release-cross-tenant-user-ref-guard` を「作業場所」と呼び、手順1の後の命令は毎回その場所へ cd してから流す。編集も作業場所の中のファイルに行う。1手順1命令。

手順1 作業場所を作り、設計の枝を取り込む（起点は origin/main）
    cd 本店 && git fetch origin
    cd 本店 && bash scripts/new-worktree.sh release/cross-tenant-user-ref-guard
    cd 作業場所 && git merge --no-ff --no-edit origin/release/cross-tenant-user-ref-guard-design
    cd 作業場所 && git log -1 --format=%H && git rev-parse origin/main
    期待する出力: new-worktree.sh が作業場所の場所を出すこと。取り込みがぶつからないこと（設計の枝は文書だけ）。2つの番号を報告に書く。ぶつかったら BLOCKED: で終える。

手順2 main との関係を確かめる
    cd 作業場所 && git merge-base --is-ancestor origin/main HEAD && echo up-to-date
    期待する出力: up-to-date。出なければ BLOCKED: で終える。

手順3 対象ファイルが設計の基準から変わっていないか確かめる
    cd 作業場所 && git diff --stat 133808dce origin/main -- backend/app/routers/leads.py backend/app/routers/shifts.py backend/app/routers/goals.py backend/app/routers/teams.py backend/app/routers/discord_guild_config.py frontend/src/pages/admin/DiscordConfigPage.tsx frontend/src/pages/admin/DiscordConfigPage.test.tsx backend/tests/conftest.py backend/tests/test_inbox_new_assignment_badge.py backend/tests/test_analytics.py backend/tests/test_notification_event_routing.py backend/tests/test_shifts_pg.py backend/tests/test_discord_d2.py
    期待する出力: 空。差分があれば記録して続行し、報告に書く。

手順3b Python 3.12 の作業用の環境を作り、backend の依存を入れる（py312-guard の決まり。2回目の実行は手順7でこれに止められ、作業がすべて消えた。編集より前に行う）
    cd 作業場所/backend && python3.12 -m venv /tmp/xtu-venv
    cd 作業場所/backend && /tmp/xtu-venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt > /tmp/xtu-pip.txt 2>&1
    cd 作業場所 && tail -3 /tmp/xtu-pip.txt
    期待する出力: エラーの行が無いこと。python3.12 が無い・入れられないときは、ここで BLOCKED: で終える（まだ何も直していないので失うものは無い）。以後の backend の命令はすべて /tmp/xtu-venv/bin/python で流す。

手順4 §3-1 の backend と §3-2 の画面を直し、§3-3・§3-4 の試験を書く。

手順5 照合の直書きの数を確かめる（K3）
    cd 作業場所 && git grep -n "FROM public.users WHERE id = :uid AND tenant_id" backend/app/routers
    期待する出力: 5行（bots.py・companies.py・roles.py 2行・teams.py）。

手順6 照合の差し替えが無いことを確かめる
    cd 作業場所 && git diff origin/main -- backend/tests | grep -n "ensure_user_in_tenant" | head -20
    期待する出力: monkeypatch・mock で差し替える行が無いこと。出た行をすべて報告に書く。

手順7 API の形を作り直す（手で書かない）
    cd 作業場所/backend && ENVIRONMENT=test /tmp/xtu-venv/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json
    cd 作業場所/frontend && npm ci
    cd 作業場所/frontend && npm run generate:api-types

手順8 試験とビルドを流す
    cd 作業場所/backend && timeout 300 /tmp/xtu-venv/bin/python -m pytest tests/test_inbox_new_assignment_badge.py tests/test_analytics.py tests/test_notification_event_routing.py tests/test_shifts.py tests/test_audit_goals_carrier.py tests/test_discord_d2.py tests/test_discord_own_server.py tests/test_shifts_pg.py tests/test_tenant_user_ref_guard_pg.py -q --no-cov -p no:cacheprovider
    （3回目の実行では、coverage を付けると全体が10分を超えた。`--no-cov` と `timeout 300` を必ず付ける。時間切れなら、同じ形で1ファイルずつ `timeout 150` で流し、止まったファイル名を報告に書く。背景に回さない）
    期待する出力: 全部 passed。`_pg` の試験が skipped になるのは想定どおり。その数と理由を報告に書いて続行する（CI で確かめる）。
    cd 作業場所/frontend && npx vitest run src/pages/admin/DiscordConfigPage.test.tsx
    期待する出力: 全部 passed。
    cd 作業場所/frontend && npx tsc --noEmit
    期待する出力: exit 0。
    cd 作業場所/frontend && npx eslint src/pages/admin/DiscordConfigPage.tsx src/pages/admin/DiscordConfigPage.test.tsx
    期待する出力: exit 0。

手順9 commit
    cd 作業場所 && git add backend frontend
    commit 文は Write でファイルに書き（1行目 `feat: reject other-tenant user ids on 6 write paths and close manual Discord guild PUT`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d と `frontend/dist` は commit しない。
    cd 作業場所 && git log -1 --stat
    期待する出力: commit の番号と、§2 の表のファイルだけ。

手順10 差分の点検（手順1の取り込みの commit と、手順9の commit の差だけを見る）
    cd 作業場所 && git diff --numstat HEAD^1 HEAD
    期待する出力: §2 の表のファイルだけ。削除の数（2列目）が 0 でないファイルは、名前と消えた行の要旨を報告に書く。表に無いファイルがあれば、その名前を報告に書いて停止する。

手順11 push（PR は作らない。PR は Opus が手元で作る）
    cd 作業場所 && git push -u origin release/cross-tenant-user-ref-guard
    cd 作業場所 && git ls-remote origin release/cross-tenant-user-ref-guard
    期待する出力: 手順9 の commit と同じ番号。

## 6. 受入条件（design.md 10 節）

| 基準 | 検証方法 |
|---|---|
| 6入口それぞれで、他社の人の番号を送ると 422、行が増えない／変わらない | `test_tenant_user_ref_guard_pg.py`（CI の PostgreSQL） |
| 6入口それぞれで、自社の人の番号なら今までどおり成功 | 同じ試験 |
| 担当なし（None）は今までどおり成功（leads・goals の team 目標・teams） | 同じ試験 |
| `PUT /admin/discord-config` が 405、`public.tenant_discord_config` が変わらない | `test_discord_d2.py` |
| GET・DELETE /own・連携の戻り口の既存試験が緑 | `test_discord_d2.py`・`test_discord_own_server.py` ほか既存の CI |
| Discord の設定画面に番号を打つ欄が無く、チャネル画面へのボタンがある。権限の無い人には出ない | `DiscordConfigPage.test.tsx`＋反映後に PO の画面で目視 |
| 画面の文字が `t()` 経由、ja/en が同じキー | 既存の CI（i18n の確かめ） |
| openapi.json が API の形と一致 | 既存の CI（api-contract-check） |
| routers 内の照合の直書きが 5 のまま | 手順5 |
| 照合の試験は本物の users 行で通す（mock なし） | 手順6＋審査 |
| 本番の4欄で自社の人でない番号が 0 | 反映後に Opus が読み取りの道で recon.md 6-4 の SQL を流す（担当はしない） |

PR について（Opus が作る。実装役は作らない）:

- Opus が手元で `scripts/gh-pr-create-safe.sh` を使い、ready（Draft にしない）で作る。本文は `.github/PULL_REQUEST_TEMPLATE.md` を起点にし、`scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめてから出す。
- 欄の良い例: `触るファイル: backend/app/routers/leads.py, backend/app/services/tenant_users.py`（1行・カンマ区切り・実際のファイル名）。禁止形: 箇条書き／ファイル名の後ろの注記／テンプレの仮の値を残す。
- `区分: A`、`PO承認:` に design.md 0 節の PO の言葉、`対象ADR: ADR-1008`。
- マージは Fable の最終評価（DB の正本とセキュリティ）とマージ前の審査の後。

## 7. 報告

- 報告の冒頭に「本報告は実装カード（他社の人の番号を保存させない）の実行結果である」と書く。
- 受領確認: 受け取ったら最初に「実装カードを受領」と1行書く。
- 完了報告の本文に、手順1・2・3・5・6・8・9・10・11 の生出力を全文含める。枝の名前と push した commit の番号を書く。§6 の各行をどの試験で確かめたかの表を書く。
- 停止したときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容` と書く。

END OF CARD
