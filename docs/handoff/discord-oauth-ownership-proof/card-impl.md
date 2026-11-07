---
mode: handoff
---
# 実装カード: Discord 連携の戻り口で、サーバーの持ち主を Discord に確かめてから保存する（G3）

親: [design.md](./design.md) 1〜4 節・10 節・12 節（Architect 2回目 APPROVE・13 節）／根拠: [recon.md](./recon.md)

- 状態: カード作成済み（2026-11-07 Opus）。実装は未着手。
- PO の言葉（原文）: 2026-11-07 Opus の選択肢「1. 作り始める【おすすめ】」への回答「1」。KGI（K1〜K4）は 2026-11-07「1」で承認（design.md 0 節）。常設の条件「推測は禁止して事実確認を怠らずに確実性を重視して…分からないことは聞いてくれ。確立したなら進める。」
- 担当: クラウドの Sonnet（実装）。Opus は審査・GO 記録・マージ判断。
- 本カードの許可・禁止は、過去のカードの禁止条項をすべて上書きする。
- 区分: A（`.github/workflows/deploy.yml` と `frontend/api-contract/` を触るため。ADR-1015）。deploy.yml は ADR-135/136 の危険パス。マージは GO 記録の後で Opus が行う。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§6。PR は Opus が作る） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1つの作業に1つの目的（戻り口で code を交換して持ち主を確かめる。画面の文言・既存4行の点検は別の作業） | ○ |
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

基準: 設計の基準 origin/main 5574bf327。2026-11-07 に origin/main 75c84e176 と比べ、対象ファイル（discord_oauth.py・main.py・docker-compose.yml・deploy.yml・test_discord_oauth.py・test_discord_oauth_rls.py・ADR-091）の差分は無い。行番号は目印で、ずれていたら前後の文で探す。

## 1. 目的（利用者に見える変化）

- Discord の画面でサーバーを選んでボットを入れれば、今までどおり「接続済み」になる（顧客用・自社用とも）。
- Discord を通らずに戻り口を開いた場合・Discord の答えと URL の番号が違う場合は、保存されず、戻り先に失敗の理由が付く。
- 秘密の鍵が無い間は、連携の開始口が 503 を返す（Discord へは進まない）。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `backend/app/routers/discord_oauth.py` | design 4-1〜4-4 のとおり（鍵の読み方・開始口の 503・code の交換の関数・戻り口の順番） |
| `backend/app/main.py` | design 4-5（起動時の警告に DISCORD_CLIENT_SECRET を足す。起動は止めない） |
| `docker-compose.yml` | design 4-5（backend の環境変数に1行。backend の塊だけ。celery-worker・discord-gateway には足さない） |
| `.github/workflows/deploy.yml` | design 4-5（消す sed に1行・heredoc に1行） |
| `backend/tests/test_discord_oauth.py` | §3-3・§3-4 |
| `backend/tests/test_discord_own_server.py` | §3-3 |
| `frontend/api-contract/openapi.json` | §5 手順7 の命令で作り直す（手で書かない） |
| `docs/adr/ADR-091-discord-bot-scope-definition.md` | §3-5 の追記 |
| `docs/adr/README.md` | `node scripts/generate-adr-index.js` で作り直す（手で書かない） |

触らないもの: 招待の URL（`_build_invite_url` の scope・response_type・redirect_uri）／`backend/app/services/oauth_state.py`／他の Discord の router／`backend/tests/test_discord_oauth_rls.py`／frontend の画面と ja.json・en.json／`migrations/`・`scripts/`／design.md・recon.md・本カード（Opus が直す）。

## 3. 作るものの決まり（design.md が正。食い違えば design.md に従い、報告する）

### 3-1. discord_oauth.py

- `import httpx` を import の塊に足す（ruff の並び順に従う）。
- `_DISCORD_TOKEN_URL`・`_client_secret()`・`_ExchangeError`・`_exchange_code_for_guild_id` は design 4-1・4-3 のコードのとおり。`_client_secret()` はモジュール読み込み時に固定せず、呼ぶたびに `os.getenv` で読む。
- 開始口の 503 は design 4-2 のとおり。置く場所は、権限の確かめ（own の `tenant.profile.edit`）の後、`oauth_state.issue_state` の `try` の前。
- 戻り口は design 4-4 の 1〜10 の順。引数に `code: str | None = Query(None)` を足す。6〜8 は `base` へ戻す。交換は state を使った後・`set_tenant_context` の前。
- INSERT・監査の `new_data`・IntegrityError の warning・最後の info ログに使う番号は、すべて `verified`。監査の `new_data` に `"verified_by": "token_exchange"` を足す。
- ログに出してよいのは status・Discord の `error` の語・tenant・purpose・番号だけ。鍵・code・access_token・refresh_token・応答の本文はログにも転送先 URL にも出さない（K4）。

### 3-2. 配線（main.py・docker-compose.yml・deploy.yml）

- design 4-5 の3か所だけ。deploy.yml の他の行は変えない。heredoc の行の字下げは、すぐ上の `DISCORD_BOT_TOKEN=` の行と同じにする。
- 鍵の値をどこにも書かない。試験でも実在しそうな値を使わず、`test-secret-not-real` のような値にする。

### 3-3. 既存の試験の直し方

- `test_discord_oauth.py`:
  - 開始口の試験 `test_start_returns_invite_url_and_state`・`test_invite_url_contains_required_permissions`・`test_invite_url_contains_required_oauth_params` は、`monkeypatch.setenv("DISCORD_CLIENT_SECRET", "test-secret-not-real")` を入れてから呼ぶ。
  - 戻り口で保存まで進む試験（`test_callback_valid_state_and_guild_id_redirects_connected`・`test_callback_calls_set_tenant_context_before_db_writes`）は、鍵の環境変数と `code` を足し、Discord の応答を §3-4 の偽の通信で返す（応答の guild.id は URL と同じ番号）。
  - state なし・state 無効・guild_id なしの試験は、交換より前で止まるので中身を変えない。
- `test_discord_own_server.py`:
  - `test_01`・`test_02` は鍵の環境変数を入れる。`test_03`・`test_04`・`test_07` は変えない。
  - `_callback` に `code` を足す（例 `"code": "c"`）。`test_05`・`test_06`・`test_08`・`test_11` は、`patch("app.routers.discord_oauth._exchange_code_for_guild_id", AsyncMock(return_value=GUILD)（GUILD はその試験で URL に渡す番号）)` で交換を差し替える（この試験は用途ごとの行と戻り先を見るもの。交換そのものは §3-4 で確かめる）。

### 3-4. 新しい試験（test_discord_oauth.py・design 10 節）

- 偽の通信は `backend/tests/test_meta_oauth_endpoints.py` の `_patch_graph` と同じ形にする: 先に `real_async_client = httpx.AsyncClient` を取っておき、`patch("app.routers.discord_oauth.httpx.AsyncClient", side_effect=...)` で `httpx.MockTransport` を使う本物の AsyncClient を返す（取っておかないと自分を呼び続ける）。respx は使わない。
- 1つの試験に1つの確かめ。どの試験も、戻り口の前後で `tenant_discord_config` の行を読み、増えた／変わったかを確かめる:
  1. code なし → `reason=missing_code`、行が増えない
  2. Discord が 400 `{"error":"invalid_grant"}` → `reason=code_exchange_failed`、行が増えない
  3. 応答の guild.id が URL の番号と違う → `reason=guild_mismatch`、行が増えない。既に行がある会社でも、その行が変わらない
  4. 応答に guild が無い → `reason=missing_guild_in_token`
  5. 応答の本文が辞書でない JSON（例 `[]`）で 400 → `reason=code_exchange_failed`（500 にならない）
  6. 通信の失敗（`httpx.ConnectError` を投げる handler）→ `reason=code_exchange_failed`
  7. 正しい code → connected、保存された guild_id が応答の guild.id
  8. 交換の送り方: handler が受けた要求の method が POST、URL が `https://discord.com/api/oauth2/token`、Content-Type が `application/x-www-form-urlencoded`、本文の `grant_type=authorization_code`・`code`・`redirect_uri`（`_DISCORD_CALLBACK_URL` と同じ）、`Authorization` が `Basic` で始まる
  9. 鍵が無い（`monkeypatch.delenv("DISCORD_CLIENT_SECRET", raising=False)`）→ 開始口が 503、戻り口が `reason=discord_not_configured`（行が増えない）
  10. caplog（全レベル）と転送先 URL に、試験用の鍵・code・偽の access_token の文字が含まれない（2・3・7 の流れで確かめる）
  11. 自社用（purpose=own）の失敗は `/admin/discord-config?tab=own&discord_status=error&reason=...` に戻る（mismatch で1本）
- 試験の値に実在の人の名前・実在のサーバー番号を使わない。

### 3-5. ADR-091 の追記

- `## Scope（対象外）` の前に `### 戻り口でのサーバーの持ち主の確かめ（2026-11-07 追記・G3）` を足し、次の4点を書く: 戻り口は Discord から受けた `code` を `https://discord.com/api/oauth2/token` で交換し、応答の `guild.id` だけを保存する／URL の `guild_id` は公式のとおり目安としてだけ使い、応答と違えば保存しない（`guild_mismatch`）／秘密の鍵 `DISCORD_CLIENT_SECRET` は GitHub Secrets → deploy.yml → .env → docker-compose の backend → `os.getenv` の1本道（ADR-075）／設計: `docs/handoff/discord-oauth-ownership-proof/design.md`。
- その後 `node scripts/generate-adr-index.js` を流す。

## 4. 守ること

- 担当は sleep しない（待ちは設計者が期限付きで行う）。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントで書かない。python などのスクリプトでファイルを書き換えない。
- `rm` を使わない（見張りが止める）。
- PostgreSQL を自分で立てない。
- PR を作る前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（PR は Opus が作る）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 停止するのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除・GitHub Secrets の操作が要るとき／design.md と食い違うのに design.md どおりに作れないとき／§2 の表に無いファイルを直さないと試験が通らないとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く（判定は設計者がする）。
- 本番 DB・本番サーバー・Discord に接続しない。GO 記録・evidence-registry に書かない。マージしない。

## 5. 手順

クラウドで行う。取り出したリポジトリの最上位を「本店」と呼ぶ。本店では編集も commit もしない。手順1で作る `~/worktrees/salesanchor/release-discord-oauth-ownership-proof` を「作業場所」と呼び、手順1の後の命令は毎回その場所へ cd してから流す。編集も作業場所の中のファイルに行う。1手順1命令。

手順1 作業場所を作り、設計の枝を取り込む（起点は origin/main）
    cd 本店 && git fetch origin
    cd 本店 && bash scripts/new-worktree.sh release/discord-oauth-ownership-proof
    cd 作業場所 && git merge --no-ff --no-edit origin/release/discord-oauth-ownership-proof-design
    cd 作業場所 && git log -1 --format=%H && git rev-parse origin/main
    期待する出力: new-worktree.sh が作業場所の場所を出すこと。取り込みがぶつからないこと（設計の枝は文書だけ）。2つの番号を報告に書く。ぶつかったら BLOCKED: で終える。

手順2 main との関係を確かめる
    cd 作業場所 && git merge-base --is-ancestor origin/main HEAD && echo up-to-date
    期待する出力: up-to-date。出なければ BLOCKED: で終える。

手順3 対象ファイルが設計の基準から変わっていないか確かめる
    cd 作業場所 && git diff --stat 5574bf327 origin/main -- backend/app/routers/discord_oauth.py backend/app/main.py docker-compose.yml .github/workflows/deploy.yml backend/tests/test_discord_oauth.py backend/tests/test_discord_own_server.py docs/adr/ADR-091-discord-bot-scope-definition.md
    期待する出力: 空。差分があれば記録して続行し、報告に書く。

手順3b Python 3.12 の作業用の環境を作り、backend の依存を入れる（編集より前に行う）
    cd 作業場所/backend && python3.12 -m venv /tmp/g3-venv
    cd 作業場所/backend && /tmp/g3-venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt > /tmp/g3-pip.txt 2>&1
    cd 作業場所 && tail -3 /tmp/g3-pip.txt
    期待する出力: エラーの行が無いこと。python3.12 が無い・入れられないときは、ここで BLOCKED: で終える。以後の backend の命令はすべて /tmp/g3-venv/bin/python で流す。

手順4 §3-1〜§3-5 のとおりに直し、試験を書く。

手順5 鍵の値の形の文字列が無いことを確かめる（K4）
    cd 作業場所 && git grep -n -iE "DISCORD_CLIENT_SECRET\s*[=:]\s*['\"]?[A-Za-z0-9_-]{20,}" ; echo "exit=$?"
    期待する出力: 0件（exit=1）。出たら、その行を報告に書いて停止する。

手順6 鍵を読む所が1か所だけであることを確かめる
    cd 作業場所 && git grep -n "DISCORD_CLIENT_SECRET" -- backend/app docker-compose.yml .github/workflows
    期待する出力: discord_oauth.py の `_client_secret` の1行・main.py の警告・docker-compose.yml の backend の1行・deploy.yml の2行。出た行をすべて報告に書く。

手順7 API の形を作り直す（手で書かない）
    cd 作業場所/backend && ENVIRONMENT=test /tmp/g3-venv/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json
    cd 作業場所/frontend && npm ci
    cd 作業場所/frontend && npm run generate:api-types
    cd 作業場所 && git diff --stat -- frontend/api-contract/openapi.json
    期待する出力: openapi.json だけが変わり、変わった所は戻り口の `code` の引数の追加だけ（`git diff -- frontend/api-contract/openapi.json` を報告に全文書く）。

手順8 試験と点検を流す
    cd 作業場所/backend && /tmp/g3-venv/bin/python -m pytest tests/test_discord_oauth.py tests/test_discord_own_server.py tests/test_discord_oauth_rls.py tests/test_discord_d2.py -q --no-cov -p no:cacheprovider
    （coverage を付けない。10分を超えたら止めて、同じ形で1ファイルずつ流し、止まったファイル名を報告に書く。背景に回さない）
    期待する出力: 全部 passed。`test_discord_oauth_rls.py` が PostgreSQL の無い所で skipped になるのは想定どおり。その数と理由を報告に書いて続行する。
    cd 作業場所/backend && /tmp/g3-venv/bin/python -m ruff check app/routers/discord_oauth.py app/main.py tests/test_discord_oauth.py tests/test_discord_own_server.py
    期待する出力: exit 0。
    cd 作業場所/frontend && npx tsc --noEmit
    期待する出力: exit 0。

手順9 commit
    cd 作業場所 && git add backend frontend/api-contract docker-compose.yml .github/workflows/deploy.yml docs/adr
    commit 文は Write でファイルに書き（1行目 `feat: verify Discord guild ownership by exchanging the OAuth code at the callback`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d と `frontend/dist` は commit しない。
    cd 作業場所 && git log -1 --stat
    期待する出力: commit の番号と、§2 の表のファイルだけ。

手順10 差分の点検（手順1の取り込みの commit と、手順9の commit の差だけを見る）
    cd 作業場所 && git diff --numstat HEAD^1 HEAD
    期待する出力: §2 の表のファイルだけ。削除の数（2列目）が 0 でないファイルは、名前と消えた行の要旨を報告に書く。表に無いファイルがあれば、その名前を報告に書いて停止する。
    cd 作業場所 && git diff HEAD^1 HEAD -- .github/workflows/deploy.yml docker-compose.yml backend/app/main.py
    期待する出力: 足した行だけ（deploy.yml 2行・compose 1行・main.py の警告）。全文を報告に書く。

手順11 push（PR は作らない。PR は Opus が手元で作る）
    cd 作業場所 && git push -u origin release/discord-oauth-ownership-proof
    cd 作業場所 && git ls-remote origin release/discord-oauth-ownership-proof
    期待する出力: 手順9 の commit と同じ番号。

## 6. 受入条件（design.md 10 節）

| 基準 | 検証方法 |
|---|---|
| code なしで `missing_code`、行が増えない（K1） | §3-4 の1 |
| Discord が拒否する code で `code_exchange_failed`、行が増えない（K1） | §3-4 の2・5・6 |
| 応答の番号と URL の番号が違うと `guild_mismatch`、行が増えない／変わらない（K1） | §3-4 の3 |
| 応答に guild が無いと `missing_guild_in_token` | §3-4 の4 |
| 正しい code で、応答の guild.id が保存され connected（K3） | §3-4 の7 |
| 交換の送り方が公式どおり（form・Basic・grant_type・code・redirect_uri） | §3-4 の8 |
| 鍵が無いと開始口が 503、戻り口は `discord_not_configured` | §3-4 の9 |
| アプリのログと転送先 URL に鍵・code・access_token が出ない（K4） | §3-4 の10 |
| 鍵の値の形の文字列がコードと文書に無い（K4） | 手順5 |
| 既存の試験（開始口・戻り口・自社用）が緑 | 手順8＋CI |
| 自社用の失敗の戻り先が `/admin/discord-config?tab=own&…` | §3-4 の11 |
| openapi.json が API の形と一致 | 手順7＋既存の CI（api-contract-check） |
| deploy.yml と compose に DISCORD_CLIENT_SECRET が入る | 手順10＋審査 |
| K2: 本番で顧客用・自社用がつながる | 反映後、PO がテナント001で解除→再接続（担当はしない） |
| K3: 本番の新しい行の guild_id が PO の選んだサーバー | 反映後、Opus が読み取りの道で確かめる（担当はしない） |

PR について（Opus が作る。実装役は作らない）:

- Opus が手元で `scripts/gh-pr-create-safe.sh` を使い、ready（Draft にしない）で作る。本文は `.github/pull_request_template.md` を起点にし、`scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめてから出す。
- 欄の良い例: `触るファイル: backend/app/routers/discord_oauth.py, backend/app/main.py`（1行・カンマ区切り・実際のファイル名）。禁止形: 箇条書き／ファイル名の後ろの注記／テンプレの仮の値を残す。
- `区分: A`、`PO承認:` に本カード冒頭の PO の言葉、`対象ADR: ADR-091`。
- マージは、CI 緑・マージ前の審査・GO 記録（ADR-136 の3行まとめを PO へ）・PO が GitHub Secrets に鍵を入れた後（design 12 節）。

## 7. 報告

- 報告の冒頭に「本報告は実装カード（Discord 連携の戻り口で持ち主を確かめる）の実行結果である」と書く。
- 受領確認: 受け取ったら最初に「実装カードを受領」と1行書く。
- 完了報告の本文に、手順1・2・3・5・6・7・8・9・10・11 の生出力を全文含める。枝の名前と push した commit の番号を書く。§6 の各行をどの試験で確かめたかの表を書く。
- 停止したときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容` と書く。

END OF CARD
