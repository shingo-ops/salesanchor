# design: 前から登録されている会社のサーバーに、ボットが本当に入っているかを読むだけで確かめる（U2）

- 調査の根拠: `docs/handoff/discord-guild-membership-check/recon.md`（以下 recon §n）
- 関係する設計: `docs/handoff/discord-oauth-ownership-proof/design.md`（G3。U2 はその残り）
- 状態: 設計案（審査前）

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
  1. `os.environ.get("DISCORD_BOT_TOKEN")` が空なら `error=no_token` を出して終了コード 1
  2. DB: `from app.database import AsyncSessionLocal`（recon §5・SSOT）。セッション内で最初に `SET TRANSACTION READ ONLY` を実行し、続けて `SELECT tenant_id, purpose, guild_id FROM public.tenant_discord_config ORDER BY tenant_id, purpose` だけを流す。失敗時は `error=db_error` で終了コード 1（例外の本文は出さない）
  3. Discord: `from app.services.discord_rest import discord_api_request, DiscordAPIError`（recon §5・送り直しの SSOT）。`method="GET"`、`path="/users/@me/guilds?limit=200"`（2回目からは `&after=<前回の最後の id>`）、`expected_statuses=(200,)`。返りが 200 件未満になったら止める。上限 50 回（1万サーバー）で止まらなければ `error=too_many_pages` で終了コード 1。`DiscordAPIError` は `error=discord_error status=<status_code>` で終了コード 1
  4. 判定: §4-1-3 の純粋関数 `judge(rows, bot_ids)` に渡して出力する
- 書き込みに当たる語を持たない: `POST`・`PUT`・`PATCH`・`DELETE`・`INSERT`・`UPDATE`・`commit` がファイルに 0 回（受入 A4 で機械で数える。`DELETE` は HTTP と SQL の両方の意味で 0）

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

`error=<no_token|db_error|discord_error status=NNN|too_many_pages>` だけ。

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
- T4: 登録0行 → `config_rows=0` と `unregistered_bot_guilds=<ボット数>` だけ

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
  < "$HERE/discord_guild_membership_check.py" | tee "$OUT_DIR/run.txt"
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
| A3 | run.txt に 17〜20 桁の数字が 0 件、`token` の語が 0 件（K2） | `grep -c -E '[0-9]{17,20}' run.txt` → 0、`grep -c -i token run.txt` → 0 |
| A4 | スクリプトに書き込みの語が 0 件（K3） | `grep -c -E 'POST\|PUT\|PATCH\|DELETE\|INSERT\|UPDATE\|commit' scripts/ops/discord_guild_membership_check.py` → 0 |
| A5 | 自己試験が通る | クラウドで `python3 -I scripts/ops/discord_guild_membership_check.py --self-test` → `self-test ok 4` |
| A6 | 実行の前後で登録の行が同じ（K3） | reader で実行前後に `config.txt` と同じ問い合わせを流し、4行の `updated_at` が同じ |
| A7 | `x` が出た会社の行を消していない（K4） | A6 と同じ |

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

（審査の後に記入）
