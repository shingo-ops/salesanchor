# design: 前から登録されている会社のサーバーに、ボットが本当に入っているかを読むだけで確かめる（U2）

- 調査の根拠: `docs/handoff/discord-guild-membership-check/recon.md`（以下 recon §n）
- 関係する設計: `docs/handoff/discord-oauth-ownership-proof/design.md`（G3。U2 はその残り）
- 状態: 設計案（審査3回目 APPROVE・推奨1件を反映済み。2026-11-07 PO「1」で実装の承認あり。実装カード card-impl.md）

## 0. PO の言葉（原文）

- 2026-11-07「1,2両方とも順番に」（1 = 前からの2社の確認を進める）
- 2026-11-07「1」（成功の基準の案をそのまま承認。原文の後半は PO の常設条件「推測は禁止して事実確認を怠らずに…確立したなら進める。」）

## 1. 目的と、利用者に見える変化

- 目的: G3 の前の戻り口（URL の番号をそのまま保存）で登録された会社4・6 のサーバー番号が、Sales Anchor のボットが本当に入っているサーバーかを確かめる（recon §2）
- 利用者に見える変化: なし（読むだけ）。PO は2社それぞれの ○× を受け取る

## 2. 成功条件（KGI・PO 承認 2026-11-07「1」）

| # | 基準 | 判定 |
|---|---|---|
| K1 | 会社4・会社6 それぞれについて「ボットが入っている ○／いない ×」が1行ずつ出る | ○× |
| K2 | 出力にサーバーの番号・サーバー名・ボットの鍵が1つも出ない | ○× |
| K3 | 何も書き換えない（DB にも Discord にも書かない） | ○× |
| K4 | × が出ても消さずに PO へ報告し、その会社の扱いは別に決める | ○× |

## 3. 対象と対象外

- 対象: 読み取りの確認スクリプト2本（§4）と、その一回の本番実行
- 対象外: つながりを外す・登録を直す（K4）／ボットの招待のやり直し／画面の変更／定期実行化／backend の入れ物の作り直し（デプロイしない）

## 4. 変更前と変更後

変更前: 確かめる道が無い（reader に鍵が無い・制限付き鍵は監視だけ・recon §3）。

変更後: 新しいファイル2本（どちらも `scripts/ops/`）。

### 4-1. `scripts/ops/discord_guild_membership_check.py`（新規）

backend の入れ物の中で `python -` として標準入力から流す。入れ物には置かない（デプロイ不要）。

- 先頭で `--self-test` を受けたら §4-1-4 の自己試験だけを行い、app を import せずに終わる（外のつなぎなしで試せるように）
- それ以外は次の順:
  0. 出力を絞る（審査1回目 Q1・Q2、2回目 Q4）: app を import する**前**に `logging.disable(logging.CRITICAL)` と `warnings.simplefilter("ignore")` を実行する。app の import は一番外側の `try` の**中**で行う（import の失敗も `error=unexpected` にする）（`discord_rest.py:77-80・:106-109・:121-124・:136-139` の警告・エラー記録は path に `after=<番号>` を含み、4xx では応答の本文も含むため。設定が無くても WARNING 以上は標準エラーに出る）。`from app.database import AsyncSessionLocal, engine` の直後に `engine.sync_engine.echo = False` を実行する（`database.py:20` は `ENVIRONMENT` が production 以外だと SQL 文を出す設定で、`docker-compose.yml:69` の既定は development。本番の値は未確認なので、値によらず止める）
  1. `os.environ.get("DISCORD_BOT_TOKEN")` が空なら `error=missing_env` を出して終了コード 1
  2. DB: `from app.database import AsyncSessionLocal`（recon §5・SSOT）。セッション内で最初に `SET TRANSACTION READ ONLY` を実行し、続けて `SELECT tenant_id, purpose, guild_id FROM public.tenant_discord_config ORDER BY tenant_id, purpose` だけを流す。失敗時は `error=db_error` で終了コード 1（例外の本文は出さない）
  3. Discord: `from app.services.discord_rest import discord_api_request, DiscordAPIError`（recon §5・送り直しの SSOT）。`method="GET"`、`path="/users/@me/guilds?limit=200"`（2回目からは `&after=<前回の最後の id>`）、`expected_statuses=(200,)`。返りが 200 件未満になったら止める。上限 50 回（1万サーバー）で止まらなければ `error=too_many_pages` で終了コード 1。`DiscordAPIError` は `error=discord_error status=<status_code>` で終了コード 1。`status_code` が `None`（ネットワークの失敗・`discord_rest.py:82-84`）のときは `status=000` と出す
  4. 判定: §4-1-3 の純粋関数 `judge(rows, bot_ids)` に渡して出力する
  5. 終わりに必ず `await engine.dispose()`（`try/finally`）
- 一番外側（app の import と `asyncio.run(main())` の両方を包む所）で `Exception` を捕まえ、`error=unexpected` だけを標準エラーに出して終了コード 1。traceback・例外の本文は出さない（審査 Q3）
- 書き込みに当たる語を持たない: `POST`・`PUT`・`PATCH`・`DELETE`・`INSERT`・`UPDATE`・`commit` が単語としてファイルに 0 回（受入 A4 で `grep -w` で数える。`DELETE` は HTTP と SQL の両方の意味で 0）。注釈・文字列にもこれらの語を書かない

#### 4-1-1. 出力の形（標準出力・これ以外は出さない）

```
bot_guild_count=<ボットが入っているサーバーの数>
config_rows=<登録の行数>
tenant=<会社番号> purpose=<customer|own> bot_in_guild=<o|x>
...（登録の行の数だけ。会社番号・用途の順）
unregistered_bot_guilds=<ボットは入っているが登録に無いサーバーの数>
```

- 記号は ASCII の `o` / `x`（端末の文字化けを避ける）
- サーバーの番号・名前・ボットの鍵・例外の本文は出さない（K2）

#### 4-1-2. 失敗の形（標準エラー・1行）

`error=<missing_env|db_error|discord_error status=NNN|too_many_pages|unexpected>` だけ（NNN は3桁。status が無いときは `000`）。§4-2 で標準出力とまとめて run.txt に残し、A3 の検査に含める。

#### 4-1-3. 純粋関数

```python
def judge(rows: list[tuple[int, str, str]], bot_ids: set[str]) -> list[str]:
    """rows = (tenant_id, purpose, guild_id)。§4-1-1 の行（先頭2行と末尾1行を含む）を返す。"""
```

- `bot_ids` は Discord の応答の各要素の `id` を `str` にしたもの
- `guild_id` は `str(guild_id).strip()` で比べる

#### 4-1-4. 自己試験（`--self-test`）

次の4つを assert し、通れば `self-test ok 4` を出す:
- T1: 登録2行・ボット側に1行だけ一致 → 一致した行が `o`、もう1行が `x`、`unregistered_bot_guilds` が正しい
- T2: 出力のどの行にも 17〜20 桁の数字が無い（`re.search(r"\d{17,20}", line)` が None）
- T3: ページ分け: 200件・200件・3件を返す偽の取得関数で、取得が3回で止まり、2回目・3回目の path に前回最後の id が `after=` で入る（取得部分は `fetch_all(request)` として偽物を差し込める形にする）
- T4: 登録0行 → `bot_guild_count=<ボット数>`・`config_rows=0`・`unregistered_bot_guilds=<ボット数>` の3行だけ

### 4-2. `scripts/ops/discord-guild-membership-check.sh`（新規・PO が `!` で流す）

`scripts/ops/place-secretary-token.sh:8-9`（recon §5）と同じ接続先・鍵の書き方。

```bash
#!/usr/bin/env bash
# U2: 登録されたサーバーにボットが入っているかを読むだけで確かめる（docs/handoff/discord-guild-membership-check/design.md）。
# PO が手元で `!` で流す。書き込みなし。出力にサーバーの番号・名前・鍵は出ない。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SSH_OPTS=(-F /dev/null -i "$HOME/.ssh/manual-only/id_ed25519" -o IdentitiesOnly=yes)
HOST="ubuntu@49.212.137.46"
OUT_DIR="/tmp/CC報告ファイル/u2"
mkdir -p "$OUT_DIR"
ssh "${SSH_OPTS[@]}" "$HOST" 'docker exec -i -w /app astro-webapp-backend-1 python -' \
  < "$HERE/discord_guild_membership_check.py" 2>&1 | tee "$OUT_DIR/run.txt"
```

- 入れ物名・作業場所は `.github/workflows/line-import-device.yml:69` と `backend/Dockerfile:4` に合わせる（recon §5）
- `python -` は作業場所 `/app` を読み込み先に入れるので `import app...` が通る（前例 `python -m app.line_device_admin` と同じ作業場所）

## 5. 影響範囲（呼び出し元の全走査）

- 新規2ファイルだけ。既存のコード・表・画面・CI は変えない
- 新しいファイルを呼ぶのは PO の `!` だけ。CI からも本番の定期処理からも呼ばれない
- 使う既存の部品（読むだけ）: `AsyncSessionLocal`・`discord_api_request`。どちらも中身は変えない

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| 番号が画面・記録に出る | 出力は §4-1-1 の形だけ。自己試験 T2 と受入 A3 で 17〜20 桁の数字が 0 件を確かめる |
| 書き込みが起きる | `SET TRANSACTION READ ONLY`。HTTP は GET だけ。受入 A4 で書き込みの語を数える |
| ボットの一覧が全部返らない（ページ分け・シャーディング） | `after` で続きを取る。gateway はシャーディング無し（recon §4）。受入 A1（会社1 の2行が両方 o）を対照にする。A1 が × なら確かめ方自体を疑い、会社4・6 の結果を使わず止める |
| 公開の記録に出る | GitHub Actions を使わない（リポジトリは公開・recon §6）。結果は PO の端末と Mac の /tmp だけ |
| Discord の回数制限 | 1〜数回の GET だけ。429 は既存の送り直しに任せる |

## 7. 代替案と選んだ理由

| 案 | 採否 | 理由 |
|---|---|---|
| A. 本番の入れ物の中で一覧を読む（本案） | 採用 | 鍵と登録の正本が両方そこにある（SSOT）。書き込み・デプロイ・公開の記録が無い |
| B. GitHub の手動ワークフロー | 不採用 | リポジトリが公開で、記録を誰でも読める（recon §6）。ワークフローの新設も要る |
| C. 読み取りの道（reader） | 不可 | ボットの鍵が無い（recon §3） |
| D. 登録ごとに `GET /guilds/{id}` | 不採用 | 403/404 の理由が「入っていない」以外（権限・番号違い）とも重なる。一覧1回の方が判定が一義 |
| E. 2社に聞く | 不採用 | 機械で確かめられず、時間がかかる |

## 8. 維持の仕組み

- 一回きりの確認。定期化しない（対象外）
- G3 以後の登録は Discord が持ち主を確かめた番号だけになった（G3 design）ので、同じ確認が要るのは G3 前の行だけ
- スクリプトは残す。また前からの行を疑う場面で同じ手順を使える

## 9. 戻し方

- 書き込みが無いので、本番の戻しは不要
- ファイルを消す PR を出せば元に戻る

## 10. 受入条件と検証方法

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | 会社1 の customer・own が両方 `o`（2026-11-07 に PO がボットを入れてつないだ行・対照） | 本番実行の出力 run.txt |
| A2 | 会社4・会社6 の行がそれぞれ1行、`o` か `x` で出る（K1） | run.txt |
| A3 | run.txt（標準出力と標準エラーの両方）に 17〜20 桁の数字が 0 件、`token` の語が 0 件、§4-1-1・§4-1-2 の形以外の行が 0 件（K2） | 下の「A3・A4 の命令」の (1)〜(3) がすべて 0 |
| A4 | スクリプトに書き込みの語が単語として 0 件（K3） | 下の「A3・A4 の命令」の (4) が 0。あわせて (5) の対照（わざと語を入れた写し）が 1 以上になり、命令が効いていることを示す |
| A5 | 自己試験が通る | クラウドで `python3 -I scripts/ops/discord_guild_membership_check.py --self-test` → `self-test ok 4` |
| A6 | 実行の前後で登録の行が消えも増えもせず、作成・更新の時刻が同じ（K3 の補助） | reader で実行の前と後に `SELECT tenant_id, purpose, guild_id, created_at, updated_at FROM ai_ro.public__tenant_discord_config ORDER BY tenant_id, purpose` を流し、2つの出力を `diff` → 差分 0 行・行数 4。reader では番号が `masked:len=N:digits` に置き換わる（`migrations/20261024_100000_create_ai_cloud_meta.sql:138`・`migrations/20261024_100300_create_ai_cloud_views.sql:274`）。このため**同じ長さの番号への書き換えは A6 では判定できない**。また updated_at を自動で直す仕掛けは無い（`migrations/099_add_discord_guild_config.sql:6-11`）。番号を書き換えないことは、A6 ではなく READ ONLY（§4-1 手順2）・GET だけ（手順3）・A4 で保証する |
| A7 | `x` が出た会社の行を消していない（K4） | A6 の後の出力に、`x` が出た会社の行が残っている（行数 4 のまま） |

### A3・A4 の命令（表の外に書く。`|` をそのまま書くため）

```bash
# A3（run.txt は §4-2 が書く /tmp/CC報告ファイル/u2/run.txt）
grep -c -E '[0-9]{17,20}' /tmp/CC報告ファイル/u2/run.txt                         # (1) → 0
grep -c -i 'token' /tmp/CC報告ファイル/u2/run.txt                                 # (2) → 0
grep -c -v -E '^(bot_guild_count=[0-9]+|config_rows=[0-9]+|tenant=[0-9]+ purpose=(customer|own) bot_in_guild=[ox]|unregistered_bot_guilds=[0-9]+|error=(missing_env|db_error|discord_error status=[0-9]{3}|too_many_pages|unexpected))$' /tmp/CC報告ファイル/u2/run.txt   # (3) → 0
# A4
grep -c -w -E 'POST|PUT|PATCH|DELETE|INSERT|UPDATE|commit' scripts/ops/discord_guild_membership_check.py   # (4) → 0
# A4 の対照: 写しの末尾に1語足して、(4) と同じ命令が当たることを示す
{ cat scripts/ops/discord_guild_membership_check.py; echo '# DELETE'; } | grep -c -w -E 'POST|PUT|PATCH|DELETE|INSERT|UPDATE|commit'   # (5) → 1
```

- (3) の対照として、実装役はクラウドで正しい形の行だけの見本ファイル（0 件になる）と、`foo` を1行足した見本ファイル（1 件になる）の両方で (3) を流し、生出力を残す
- `grep -c` は 0 件のとき終了コード 1 を返す。判定は終了コードではなく出力された数で行う
- (3) が 0 でないときは不合格として止まり、会社4・6 の結果を使わない。ssh や docker 自身の警告が混ざっただけの場合もあるため、(1) と (2) が両方 0 のときに限って、余計な行を Opus が読んで PO に見せる（(1) か (2) が 0 でなければ run.txt を誰にも見せず、PO に止まったことだけを伝える）

## 11. 外部・過去事例の参照と我々への応用

- discord.py の `get_guilds`（recon §4）: ボットの鍵で `/users/@me/guilds` を `after` 付きで読む。同じ読み方をそのまま使う
- 社内の前例: `scripts/ops/place-secretary-token.sh`（PO の `!`・manual-only 鍵・値を出さない）、`line-import-device.yml:69`（入れ物の中で一回だけ動かす）
- 数値の外部事例は不要: 一回きりの読み取りで、成否は本番の出力で直接判定できるため

## 12. 実装の進め方（1つの作業）

1. クラウドの Sonnet が §4 の2ファイルを書き、A4・A5 をクラウドで流して生出力を残す
2. 審査役 reviewer（opus）→ CI 緑 → 委任 GO（scripts/ は危ない場所・recon §7）→ main へ取り込み（デプロイの対象外のファイルだけ）
3. 実行前の reader（A6 の前）→ PO に、取り込み後の main と同じ中身の作業場所（~/worktrees 配下）にあるスクリプトを `!` で流してもらう（本店の写しは古いので使わない） → 実行後の reader → A1〜A7 を判定
4. 結果を PO へ。× があれば K4 のとおり扱いを PO に聞く

## 13. 審査（Architect）

### 1回目（2026-11-07 05:13Z・クラウドの Opus・HEAD 145ebf451）: REVISE

- (1) 引用の行: 合う（`database.py` の sessionmaker の終わりは :40）。(2) 書き込みの道: 無い。(4) `python -` と `-w /app`: 合う（`Dockerfile:4`・:24）
- Q1（必須）`discord_rest.py` の警告記録が path の `after=<番号>` を出す → §4-1 の手順0 `logging.disable(logging.CRITICAL)`（import の前）
- Q2（必須）`database.py:20` の echo の既定（ENVIRONMENT が production 以外で SQL 文を出す） → §4-1 の手順0 `engine.sync_engine.echo = False`。`database.py` と `docker-compose.yml:69` を Opus が手元で照合済み
- Q3（必須）想定外の例外の traceback・標準エラーが検査から漏れる → 一番外側の `error=unexpected`、`engine.dispose()`、§4-2 を `2>&1 | tee`、A3 に「形以外の行 0 件」を追加
- Q4（推奨）T4 に `bot_guild_count` の行を追加
- Q5（推奨）A4 を `grep -w` にし、注釈・文字列にも書き込みの語を書かないと明記
- Q6（推奨）design.md:151（A6）への指摘。実行記録の表示が途中で切れていて本文を読めなかった。A6 は「行数・作成日時・更新日時・番号の長さと要約値（md5）を前後で diff して差分0行」に強めた。2回目の審査で、Q6 の指摘が解けたかの確認を頼む

### 2回目（2026-11-07 05:22Z・クラウドの Opus・HEAD 47da25613）: REVISE

- (a) 1回目の Q1〜Q5: 解けている。(b) logging を通る記録は止まる。warnings と import の失敗は logging を通らない
- Q1（必須）表の中の `\|` を grep に渡すと `|` の文字そのものを探す（審査役がクラウドで試して確認）→ A3・A4 の命令を表の外のコードの塊へ移し、A4 に効いていることを示す対照 (5) を足した
- Q2（必須・1回目 Q6 の全文）reader では guild_id が `masked:len=N:digits` に置き換わり、md5 では書き換えを判定できない → A6 を「行の削除・追加と時刻の比較」に絞り、番号を書き換えないことは READ ONLY・GET だけ・A4 で保証すると明記した
- Q3（推奨）ネットワークの失敗で status が None → `status=000` と決め、§4-1-2 に書いた
- Q4（推奨）app の import を一番外側の try の中へ入れ、`warnings.simplefilter("ignore")` を足した
- Opus が自分で見つけた点: 失敗の印 `error=no_token` は A3 (2) の `token` 検査に当たってしまう → `error=missing_env` に改名した。A3 (3) の型を手元の見本2つで流し、正しい行だけなら 0 件・`foo` を足すと 1 件、(2) は両方 0 件を確認（生出力は Opus の手元の作業場所）

### 3回目（2026-11-07 05:30Z・クラウドの Opus・HEAD b408a5133）: APPROVE

- (a) 2回目の4点は解けている。(b) 審査役が見本ファイルで「A3・A4 の命令」を流した: (1)(2) は 0、(3) は正しい行だけで 0・1行足すと 1、(4) は 0、(5) は 1。(c) `missing_env` の改名は合う。(d) A6 の範囲は合う（時刻の列は reader でそのまま見える `meta.sql:122-127`、行数4は recon §1 と一致）
- Q1（推奨）`2>&1` は ssh 全体にかかるので、ssh・docker の警告で (3) が 1 になりうる → (3) が 0 でないときの扱いを「A3・A4 の命令」の下に1行足した
- 未解決の事項: なし。Discord 公式の決まりは審査の環境から読めないため、Opus が recon §4 で公式ページを直接読んだ結果に依る。本番で全サーバーが返るかは A1（対照）で判定する
