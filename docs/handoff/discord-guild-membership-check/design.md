# design: 前から登録されている会社のサーバーに、ボットが本当に入っているかを読むだけで確かめる（U2）

- 調査の根拠: `docs/handoff/discord-guild-membership-check/recon.md`（以下 recon §n）
- 関係する設計: `docs/handoff/discord-oauth-ownership-proof/design.md`（G3。U2 はその残り）
- 状態: U2 本体は実装・本番実行済み（2026-11-07・全行 o）。§14 の追補は設計審査済み（2回目 APPROVE・14-11）。実装は未着手

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
  0. 出力を絞る（審査1回目 Q1・Q2、2回目 Q4）: app を import する**前**に `logging.disable(logging.CRITICAL)` と `warnings.simplefilter("ignore")` を実行する。app の import は一番外側の `try` の**中**で行う（import の失敗も `error=unexpected` にする）（`backend/app/services/discord_rest.py:77-80・:106-109・:121-124・:136-139` の警告・エラー記録は path に `after=<番号>` を含み、4xx では応答の本文も含むため。設定が無くても WARNING 以上は標準エラーに出る）。`from app.database import AsyncSessionLocal, engine` の直後に `engine.sync_engine.echo = False` を実行する（`backend/app/database.py:20` は `ENVIRONMENT` が production 以外だと SQL 文を出す設定で、`docker-compose.yml:69` の既定は development。本番の値は未確認なので、値によらず止める）
  1. `os.environ.get("DISCORD_BOT_TOKEN")` が空なら `error=missing_env` を出して終了コード 1
  2. DB: `from app.database import AsyncSessionLocal`（recon §5・SSOT）。セッション内で最初に `SET TRANSACTION READ ONLY` を実行し、続けて `SELECT tenant_id, purpose, guild_id FROM public.tenant_discord_config ORDER BY tenant_id, purpose` だけを流す。失敗時は `error=db_error` で終了コード 1（例外の本文は出さない）
  3. Discord: `from app.services.discord_rest import discord_api_request, DiscordAPIError`（recon §5・送り直しの SSOT）。`method="GET"`、`path="/users/@me/guilds?limit=200"`（2回目からは `&after=<前回の最後の id>`）、`expected_statuses=(200,)`。返りが 200 件未満になったら止める。上限 50 回（1万サーバー）で止まらなければ `error=too_many_pages` で終了コード 1。`DiscordAPIError` は `error=discord_error status=<status_code>` で終了コード 1。`status_code` が `None`（ネットワークの失敗・`backend/app/services/discord_rest.py:82-84`）のときは `status=000` と出す
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
- 守り手: Opus（設計担当）。再び使うときは本書 §10 の受入条件と §12 の手順を読み直してから流す

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
| A6 | 実行の前後で登録の行が消えも増えもせず、作成・更新の時刻が同じ（K3 の補助・§14-10 で前提を訂正） | reader で実行の前と後に `SELECT tenant_id, purpose, guild_id, created_at, updated_at FROM ai_ro.public__tenant_discord_config ORDER BY tenant_id, purpose` を流し、2つの出力を `diff` → 差分 0 行・行数 4。~~reader では番号が `masked:len=N:digits` に置き換わる…このため同じ長さの番号への書き換えは A6 では判定できない~~（誤り。§14-10 で訂正: reader の ai_ro は伏せないので番号そのものも比べている）。また updated_at を自動で直す仕掛けは無い（`migrations/099_add_discord_guild_config.sql:6-11`）。番号を書き換えないことは、A6 ではなく READ ONLY（§4-1 手順2）・GET だけ（手順3）・A4 で保証する |
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
- 社内の前例: `scripts/ops/place-secretary-token.sh`（PO の `!`・manual-only 鍵・値を出さない）、`.github/workflows/line-import-device.yml:69`（入れ物の中で一回だけ動かす）
- 数値の外部事例は不要: 一回きりの読み取りで、成否は本番の出力で直接判定できるため

## 12. 実装の進め方（1つの作業）

1. クラウドの Sonnet が §4 の2ファイルを書き、A4・A5 をクラウドで流して生出力を残す
2. 審査役 reviewer（opus）→ CI 緑 → 委任 GO（scripts/ は危ない場所・recon §7）→ main へ取り込み（デプロイの対象外のファイルだけ）
3. 実行前の reader（A6 の前）→ PO に、取り込み後の main と同じ中身の作業場所（~/worktrees 配下）にあるスクリプトを `!` で流してもらう（本店の写しは古いので使わない） → 実行後の reader → A1〜A7 を判定
4. 結果を PO へ。× があれば K4 のとおり扱いを PO に聞く

## 13. 審査（Architect）

### 1回目（2026-11-07 05:13Z・クラウドの Opus・HEAD 145ebf451）: REVISE

- (1) 引用の行: 合う（`backend/app/database.py` の sessionmaker の終わりは :40）。(2) 書き込みの道: 無い。(4) `python -` と `-w /app`: 合う（`Dockerfile:4`・:24）
- Q1（必須）`backend/app/services/discord_rest.py` の警告記録が path の `after=<番号>` を出す → §4-1 の手順0 `logging.disable(logging.CRITICAL)`（import の前）
- Q2（必須）`backend/app/database.py:20` の echo の既定（ENVIRONMENT が production 以外で SQL 文を出す） → §4-1 の手順0 `engine.sync_engine.echo = False`。`backend/app/database.py` と `docker-compose.yml:69` を Opus が手元で照合済み
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

- (a) 2回目の4点は解けている。(b) 審査役が見本ファイルで「A3・A4 の命令」を流した: (1)(2) は 0、(3) は正しい行だけで 0・1行足すと 1、(4) は 0、(5) は 1。(c) `missing_env` の改名は合う。(d) A6 の範囲は合う（時刻の列は reader でそのまま見える `migrations/20261024_100000_create_ai_cloud_meta.sql:122-127`、行数4は recon §1 と一致）
- Q1（推奨）`2>&1` は ssh 全体にかかるので、ssh・docker の警告で (3) が 1 になりうる → (3) が 0 でないときの扱いを「A3・A4 の命令」の下に1行足した
- 未解決の事項: なし。Discord 公式の決まりは審査の環境から読めないため、Opus が recon §4 で公式ページを直接読んだ結果に依る。本番で全サーバーが返るかは A1（対照）で判定する

## 14. 追補: 登録に無い2つのサーバーの名前を PO の画面にだけ出す（2026-11-07）

- 状態: 設計審査済み（2回目 APPROVE・推奨3件を反映・14-11）。実装は未着手
- ブランチ: release/discord-unregistered-guild-names

### 14-0. PO の言葉（原文）と、K2 の例外の範囲

- 2026-11-07「2と3は何？不透明さをなくして進める」（本番の実行結果 `unregistered_bot_guilds=2` を受けて）
- 2026-11-07「1」（Opus の選択肢「1. 登録に無い2つの名前を画面に出して確かめる【おすすめ】 2つとも何のサーバーか分かります。名前はしんごさんの画面と手元の記録にだけ残ります」への回答）
- K2 の例外は**登録に無いボットのサーバーの名前だけ**。番号・鍵・登録済みのサーバーの名前は今までどおり出さない
- 名前は PO の端末と Mac の `/tmp/CC報告ファイル/u2/names.txt` にだけ残す。リポジトリ・PR・Issue・メモリ・作戦ボードには書かない

### 14-1. 成功条件（KGI）

| # | 基準 | 判定 |
|---|---|---|
| N1 | 登録に無いボットのサーバーについて、名前が1行ずつ出る。行の数が `unregistered_bot_guilds` と同じ | ○× |
| N2 | 各行に「閲覧ページの申し込み用サーバーか（`o`/`x`）」が付く | ○× |
| N3 | 出力にサーバーの番号・ボットの鍵が1つも出ない。登録済みのサーバーの名前も出ない | ○× |
| N4 | 何も書き換えない（DB にも Discord にも書かない）。旗なしの動き（§4-1-1 の出力）は1文字も変わらない | ○× |

### 14-2. 調べた事実（Opus・worktree 170ff9612 で照合）

- 名前は既に取っている応答に入っている: `fetch_all` が返す各要素は Discord の `GET /users/@me/guilds` の要素で、`name` を含む（recon §4 の公式ページ）。追加の API 呼び出しは要らない
- 閲覧ページの申し込み用サーバーの登録: `public.viewer_discord_config`（1行だけ・`guild_id VARCHAR(32)`）`migrations/20261017_100000_add_viewer_discord_config.sql:2-12`
- 現在の判定関数と出力: `scripts/ops/discord_guild_membership_check.py:25-39`（`judge`）、旗の読み取り `:172-177`

### 14-3. 変更前と変更後

変更前: 登録に無いサーバーは数（`unregistered_bot_guilds=2`）しか分からない。

変更後（既存ファイル1本の追記・新規ファイル1本）:

#### 14-3-1. `scripts/ops/discord_guild_membership_check.py`（追記）

- 旗 `--show-unregistered-names` を足す。旗が無いときの動き・出力は今と同じ（N4）
- 旗があるときだけ、同じ `SET TRANSACTION READ ONLY` の取引の中で2本目の読み取り `SELECT guild_id FROM public.viewer_discord_config` を流す（`tenant_discord_config` の SELECT の後）。失敗は `error=db_error`
- 新しい純粋関数:

```python
def clean_name(name) -> str:
    """名前を1行に収める。"""

def unregistered_lines(rows, guilds, viewer_ids) -> list[str]:
    """rows = (tenant_id, purpose, guild_id)。rows 側の guild_id も judge と同じく str(guild_id).strip() で比べる。guilds 側の id は str(g["id"])。guilds = 応答の要素（id と name）。
    viewer_ids = viewer_discord_config の guild_id を str(...).strip() した集合。
    登録に無いボットのサーバーだけを `unregistered name=<clean_name> is_viewer_guild=<o|x>` の形で返す。
    同じ id が2回あっても1行にする（id で重複を除き、先に出たほうの名前を残す。judge の数は集合で数えるため）。並びは clean_name の文字の順（同じ名前なら出る順）。"""
```

- `clean_name` の決まり（この順に行う）: (1) `None` や文字列でない値は `(no_name)`。(2) `unicodedata.category(ch)` が `C` で始まる文字（制御文字・改行・ゼロ幅などの書式文字）と、`Zl`・`Zp`（行の区切り U+2028・段落の区切り U+2029）を消す。(3) その後で 17 桁以上の数字の並び（`\d{17,}`）を `#` 1文字に置き換える（消した後に並べるので、ゼロ幅文字で区切った数字もつながってから置き換わる。名前に番号が書かれていても K2 の検査 (1) に当たらないように）。(4) 前後の空白を除き、100 文字を超えたら 100 文字で切って末尾に `~` を足す。(5) 空になったら `(no_name)`
- 出力の形（旗ありのとき・標準出力）: §4-1-1 の行のすぐ後に、`unregistered_lines` の行を続ける

```
bot_guild_count=...
config_rows=...
tenant=... purpose=... bot_in_guild=...
unregistered_bot_guilds=<N>
unregistered name=<名前> is_viewer_guild=<o|x>
...（N 行）
```

- 旗の読み取り: `sys.argv[1:]` に `--self-test` があれば今と同じ。それ以外で `--show-unregistered-names` があれば旗あり。どちらでも無い引数は無視しない: `error=unexpected` で終了コード 1（打ち間違いで名前が出ないまま「合格」に見えるのを防ぐ）。この判定は app を import する前（`run()` を呼ぶ前）に行う（app の無いクラウドでも試せるように）
- 書き込みに当たる語（§4-1 の一覧）は今までどおり 0 回（A4）

#### 14-3-2. 自己試験（`--self-test`・今の4つに2つ足して `self-test ok 6`）

- T5: 登録2行・ボット側4件（うち2件は登録済み、1件は viewer の番号）→ 2行だけ返る。viewer の行が `o`、他方が `x`。登録済みの名前が出ない。名前の文字の順に並ぶ
- T6: `clean_name` に「改行・タブ・ゼロ幅の書式文字・U+2028・18 桁の数字・「9桁＋ゼロ幅の文字＋9桁」・150 文字」を混ぜた名前と `None` を渡す → 制御文字が残らない、`\d{17,20}` に当たらない、100 文字＋`~`、`None` は `(no_name)`

#### 14-3-3. `scripts/ops/discord-unregistered-guild-names.sh`（新規・PO が `!` で流す）

既存の `scripts/ops/discord-guild-membership-check.sh` は変えない（旗なしの手順を残すため）。中身は同じ形で、違いは次の3点だけ:

- 遠くで流す命令: `'docker exec -i -w /app astro-webapp-backend-1 python - --show-unregistered-names'`（`python -` の後ろの引数は `sys.argv[1:]` に入る）
- 書き出し先: `/tmp/CC報告ファイル/u2/names.txt`
- 冒頭の注釈: 「登録に無いボットのサーバーの名前を PO の画面と Mac の /tmp にだけ出す。番号・鍵は出ない。書き込みなし。」

### 14-4. 影響範囲（呼び出し元の全走査）

- `discord_guild_membership_check.py` を呼ぶのは `scripts/ops/discord-guild-membership-check.sh` と新しい .sh だけ（どちらも PO の `!`）。CI・定期処理・backend からは呼ばれない（Opus が 2026-11-07 に worktree 170ff9612 で `.sh`・`.py`・`.yml`・`.yaml`・`.json`・`.toml` を grep した結果、呼び出しは `scripts/ops/discord-guild-membership-check.sh:11` の1か所だけ）
- 既存の部品（`AsyncSessionLocal`・`discord_api_request`）は中身を変えない

### 14-5. リスクと対処

| リスク | 対処 |
|---|---|
| 名前が公開の場所に残る | 実行は PO の `!` だけ。names.txt は Mac の /tmp。Opus は PO への返事で名前を伝えるが、リポジトリ・PR・メモリ・ボードには書かない |
| 名前に番号や改行が入っていて検査が崩れる | `clean_name`（14-3-1）と T6。B2 の (1)・(3) で確かめる |
| 登録済みのサーバーの名前が出る | `unregistered_lines` は登録済みを除く。T5 で確かめる |
| 旗の打ち間違いで名前が出ず、気づかない | 知らない引数は `error=unexpected`。B1 で行の数を `unregistered_bot_guilds` と照合 |
| 2本目の SELECT が書き込みになる | 同じ READ ONLY の取引。A4 の語の検査を新しいファイルにもかける |

### 14-6. 代替案

| 案 | 採否 | 理由 |
|---|---|---|
| A. 旗で名前を出す（本案） | 採用 | 1回の GET の応答をそのまま使う。旗なしの動きは変わらない |
| B. 名前を出さず、viewer かどうかだけ出す | 不採用 | 2つ目のサーバーが viewer でないとき、何のサーバーか分からないまま残る（PO「不透明さをなくして」） |
| C. PO が Discord の画面でボットの入っているサーバーを数える | 不採用 | ボットが入っているサーバーは PO の画面から一覧できない（PO が入っていないサーバーもありうる） |

### 14-7. 受入条件と検証方法

| # | 基準 | 検証方法 |
|---|---|---|
| B1 | names.txt の `unregistered name=` の行の数が `unregistered_bot_guilds=` の値と同じ（N1） | 下の (6) と (7) の数が同じ |
| B2 | names.txt に 17〜20 桁の数字 0 件・`token` 0 件・形以外の行 0 件（N3） | 下の (1)(2)(8) がすべて 0 |
| B3 | 書き込みの語が単語として 0 件（N4） | §10 の A4 (4)(5) を新しい py に流す（(4)=0・(5)=1）。新しい .sh にも (4) を流して 0 |
| B4 | 自己試験が通る | クラウドで `python3 -I scripts/ops/discord_guild_membership_check.py --self-test` → `self-test ok 6`。あわせて `python3 -I scripts/ops/discord_guild_membership_check.py --bogus; echo "exit=$?"` → 標準エラーに `error=unexpected`・`exit=1`（知らない引数） |
| B5 | 旗なしの出力が変わらない（N4） | 流す前に Opus が前回の run.txt（7行・`bot_guild_count=6`〜`unregistered_bot_guilds=2`）を `/tmp/CC報告ファイル/u2/run-prev.txt` に写す（既存の .sh は run.txt を上書きするため・2026-11-07 写し済み・7行）。実行の後に PO が既存の `scripts/ops/discord-guild-membership-check.sh` も流し、`diff /tmp/CC報告ファイル/u2/run-prev.txt /tmp/CC報告ファイル/u2/run.txt` → 差分 0 行（サーバーの出入りが無い限り） |
| B6 | 登録の行が消えも増えもしない（K3・K4 の補助） | §10 の A6 と同じ前後比較（reader・diff 0 行・行数 4） |

```bash
# B1・B2（names.txt は 14-3-3 が書く）
grep -c -E '[0-9]{17,20}' /tmp/CC報告ファイル/u2/names.txt     # (1) → 0
grep -c -i 'token' /tmp/CC報告ファイル/u2/names.txt             # (2) → 0
grep -c '^unregistered name=' /tmp/CC報告ファイル/u2/names.txt  # (6)
sed -n 's/^unregistered_bot_guilds=//p' /tmp/CC報告ファイル/u2/names.txt   # (7) → (6) と同じ数
grep -c -v -E '^(bot_guild_count=[0-9]+|config_rows=[0-9]+|tenant=[0-9]+ purpose=(customer|own) bot_in_guild=[ox]|unregistered_bot_guilds=[0-9]+|unregistered name=.+ is_viewer_guild=[ox]|error=(missing_env|db_error|discord_error status=[0-9]{3}|too_many_pages|unexpected))$' /tmp/CC報告ファイル/u2/names.txt   # (8) → 0
```

- (2) は名前に `token` の文字が入っていると当たる。そのときは不合格として止まり、Opus がその行だけを読んで鍵の値でないこと（短い名前であること）を確かめてから PO に見せる
- (8) が 0 でないときの扱いは §10 の注意と同じ

### 14-8. 実装の進め方

1. クラウドの Sonnet が 14-3 の2ファイルを書き、B3・B4 をクラウドで流して生出力を残す
2. 審査役 reviewer（opus）→ CI 緑 → 委任 GO（`scripts/` は危ない場所）→ main へ取り込み
3. 取り込み後の main からスクリプト2本を `/tmp/CC報告ファイル/u2/bin2/` へ写し、Git の blob の番号が main と同じことを確かめる（worktree はマージで消えるため・前回の教訓）
4. run-prev.txt があることを確かめる（B5）→ 実行前の reader → PO が `! bash /tmp/CC報告ファイル/u2/bin2/discord-unregistered-guild-names.sh` → PO が `! bash /tmp/CC報告ファイル/u2/bin2/discord-guild-membership-check.sh`（B5）→ 実行後の reader → B1〜B6 を判定
5. 名前と viewer かどうかを PO へ。扱い（そのまま・ボットを抜く・会社に登録する）は PO に聞く。抜く・登録するは別の作業

### 14-9. 維持の仕組み

- 一回きりの確認。定期化しない
- 守り手: Opus（設計担当）。再び使うときは 14-7 と 14-8 を読み直してから流す

### 14-10. §10 A6 の前提の訂正（2026-11-07 Opus）

- §10 A6 の「reader では番号が `masked:len=N:digits` に置き換わる」は誤り。Mac の reader が読む `ai_ro` は伏せない。伏せるのはクラウドの相談係 AI が読む `ai_cloud` だけ（`docs/adr/ADR-1024-ai-readonly-db-path.md:131`「PO 決定: 「1」…Mac の AI は今の ai_ro のまま。2026-10-30」）。`migrations/20261024_100300_create_ai_cloud_views.sql:274` は `ai_cloud` の決まり
- このため A6 の前後比較では番号そのものも比べており、同じ長さの番号への書き換えも diff に出る。A6 の判定（差分 0 行・行数 4）と前回の結果（2026-11-07・差分 0 行）は変わらない
- reader の出力には番号がそのまま入るので、before.txt・after.txt は Mac の /tmp だけに置き、中身をチャット・PR に出さない（差分の行数だけを報告する）

### 14-11. 審査（Architect）

#### 1回目（2026-11-07 08:29Z・クラウドの Opus・HEAD bc882f55d）: REVISE

- (a)(b)(d)(e)(f) 合う。(d) は審査役が見本ファイルで (1)(2)=0・(6)=(7)=2・(8)=0、1行足して (8)=1 を確かめた。(a) のうち「応答に name が入る」はクラウドから未確認（recon §4 で Opus が公式ページを直接読んだ結果に依る）
- Q1（必須）既存の .sh は run.txt を上書きするので、B5 の比べる相手が残らない → B5 と 14-8 手順4 に `run-prev.txt` への写しを足した。Opus が 2026-11-07 に写し済み（7行）
- Q2（推奨）消す順で、ゼロ幅文字で区切った数字が18桁残る。U+2028/2029 は種類 Zl/Zp で C に入らない → clean_name の順番 (1)〜(5) を明記し、Zl・Zp も消す。T6 に U+2028 と「9桁＋ゼロ幅＋9桁」を足した
- Q3（推奨）§10 A6 の表に誤った文が残る → 打ち消し線にして §14-10 を指した
- Q4（推奨）重複した id で B1 が合わなくなる → unregistered_lines は id で重複を除くと明記した

#### 2回目（2026-11-07 08:37Z・クラウドの Opus・HEAD c2f27d2b4）: APPROVE

- (a) 1回目の Q1〜Q4 は解けている（run-prev.txt が Mac にあることはクラウドから未確認。Opus が 2026-11-07 に `wc -l` で7行を確かめた）。(b) 審査役が clean_name の見本を10通り（U+2028・U+2029・9桁＋U+200B＋9桁・改行とタブ・18桁・150文字・None ほか）で流し、`\d{17,20}` 0件・C/Zl/Zp 0件・長さ101以下・空と None は `(no_name)`
- Q1（推奨）rows 側の strip → unregistered_lines の説明に `str(guild_id).strip()` を足した
- Q2（推奨）重複したときに残す名前 → 先に出たほうを残すと足した
- Q3（推奨）状態の行が古い・知らない引数の試験が無い → 状態を直し、旗の判定を app の import の前に行うと決め、B4 に `--bogus` で `error=unexpected`・`exit=1` を手で流す手順を足した
- 未解決の事項: なし
