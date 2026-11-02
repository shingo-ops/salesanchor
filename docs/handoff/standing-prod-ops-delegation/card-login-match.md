---
mode: handoff
---
# 実装カード: 無制限鍵の入室を会話の記録で照らす入口 `--prod-logins`

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

親: [design.md](./design.md)「追補（2026-11-03）: 照合2の道具」／[recon.md](./recon.md)「追補（2026-11-03）」

この文書は何か: 本番2台への無制限鍵の入室1回ずつを、手元の会話の記録で説明できるかを分ける道具を、今の点検の道具 `scripts/dev/consent-audit.py` に足すための作業指示です。

- 状態: カード作成済み・カード自己審査済み（§9）・PO 実装承認 済（2026-11-03 チャットで「1」＝「この設計で作る」）・クラウドの Sonnet へ実装依頼
- 担当: Sonnet（クラウドで実装〜試験〜push）。PR は Opus が手元で shingo-cc 名義・ready（`--draft` を付けない）で作る。Opus は審査・実データでの受入・マージ判断。
- 基準: origin/main `6d532b2a2`（`scripts/dev/consent-audit.py` は 1161 行）。
- ブランチ: `release/prod-login-match`（新しいブランチ。origin/main から作る）。
- 秘密: 試験は作り物のデータだけを使う。本物の会話の記録・auth.log・`~/.ssh` は読まない（クラウドには無い）。

## 0. カード発行前チェック（design-partner.md §5.5・Opus 2026-11-03）

| # | 照合 | 結果 |
|---|---|---|
| 1 | 記号を含む文字列（パス・glob・正規表現・`--` 付きの引数）をバッククォートで囲んだ | ○ |
| 2 | PR は Opus が ready で作ると書いた（実装役は push まで。`--draft` を使わない） | ○ |
| 3 | 報告の宛先: 完了報告の本文に §7 の生出力を全文含めると書いた | ○ |
| 4 | 1便1目的: 入口 `--prod-logins` の追加と、その試験だけ | ○ |
| 5 | 既存ブランチへの追記ではない（新しいブランチ `release/prod-login-match` を origin/main から） | ○ |
| 6 | 書式は実例で示した（§3 の出力の各行に良い例、§3-6 に禁止形） | ○ |
| 7 | 合格基準を出力まで縛った（§6 で終わりの番号・`PASS=`/`FAIL=` の行・差分のファイル数・削除行0） | ○ |
| 8 | 件数の停止条件に名前を出す手順を対で置いた（試験の FAIL は試験名を出す） | ○ |
| 9 | 出力量に上限: 試験の出力は1試験1行。`git diff` は `--stat` と `--name-only` だけ | ○ |
| 10 | 報告様式に 停止した手順番号／最後に実行したコマンド／停止した理由、受領確認、「本報告はカード card-login-match の実行結果である」を置いた（§7） | ○ |
| 11 | 期待値は実測から（既存の行数 1161・既存の試験の最後の行の形 `PASS=n FAIL=m TOTAL=k`）。置き場所は行番号でなく前後の文字で指定した | ○ |

## 1. 作るもの・触らないもの

- `scripts/dev/consent-audit.py`（変更。関数と入口 `--prod-logins` を足す。今ある関数・入口の動きは1行も変えない）
- `scripts/dev/prod-login-match-tests.py`（新規。§4 の試験）

触らないもの: 上の2つ以外の全部（`scripts/dev/consent-unit-tests.py`・`scripts/dev/permission-delegation-tests.py` を含む）。`.claude/`・`.github/`・`backend/`・`frontend/`・`migrations/`・`docs/` は変えない。

## 2. 足す場所

- 新しい関数はすべて、今の `def run_audit(home, now, with_permissions, out, commit=False, gh_view=None, git_run=None):` の行の直前に、見出しのコメント `# ── --prod-logins ─────` を置いて、その下にまとめて書く。
- 会話の記録の場所は、今の `paths(home)["projects"]` を使う。時刻は今の `parse_ts` を使う（文字列 → UTC の datetime）。JSON の1行は `json.loads` で読む。新しい場所の組み立て・時刻の読み方を別に作らない。
- `main()` の引数に次を足す（今の `--probe` `--audit` `--permissions` `--commit-snapshot` の動きは変えない）。`args.prod_logins` が真のときは、今の `if args.probe:` より前で `return run_prod_logins_cli(args, home, now)` とする。

```
--prod-logins                 （store_true）この照合をする
--auth LABEL=PATH             （append。何回でも）入室の記録のファイル。例: --auth prod1=/x/a.txt --auth prod2=/x/b.txt
--since ISO8601               期間の始まり。時差の付いた形だけ受ける（例 2026-10-26T14:00+09:00）
--until ISO8601               期間の終わり。同上
--delegation-start ISO8601    既定 2026-11-02T18:06+09:00
--mac-ip IP                   既定 49.128.148.145
```

## 3. 関数と決まり

### 3-1. `pl_parse_auth(path, label)` → list
- ファイルを1行ずつ読む。`Accepted publickey` を含む行だけ使う。行の最初の空白までが時刻（例 `2026-11-02T23:45:10.398968+09:00`）、` from ` の次の語が接続元の IP。
- 返す要素は `{"t": UTC の datetime, "host": label, "src": IP}`。時刻が読めない行は数えずに飛ばす（試験 T1 で件数を確かめる）。
- ファイルが無い・読めないときは `OSError` をそのまま上げる（入口で終わりの番号 2 にする）。

### 3-2. `pl_uses_key(cmd, resolve, read_file)` → `"yes"` / `"no"` / `"unreadable"`
文面1つ（Bash の `command`、または `!` の `<bash-input>` の中身）が無制限鍵を使うかを決める。`resolve(host)` は identityfile の文字列のリストを返す関数、`read_file(path)` は中身の文字列か None を返す関数（どちらも試験で差し替える）。

1. 書くだけの heredoc を消す: 行の中に `<<` があり、その行の `<<` より前に `cat >`・`cat >>`・`tee ` のどれかがあるとき、その次の行から、終わりの印（`<<` の次の語。`'EOF'`・`"EOF"`・`-EOF` の飾りを外した `EOF`）だけの行までを消す。それ以外の heredoc（`bash <<'EOF'`・`sh <<EOF`・`ssh prod1 <<'EOF'` など）は消さない。
2. 残った文面から、語 `ssh`・`scp`・`rsync`・`sftp` で始まる呼び出しを取り出す（行頭・空白・`;`・`|`・`&`・`(`・`"`・`'`・`$(` の直後に現れるもの）。呼び出しの範囲は次の `;`・`&&`・`||`・`|`・改行まで。
3. 呼び出しの中に `-i` の次の語、または `-o IdentityFile=…`・`-oIdentityFile=…` があり、そこに `manual-only` を含めば `yes`。
4. 3 で決まらず、呼び出しが `ssh`・`sftp` のとき: 引数を左から見て、値を取る選択肢（`-b -c -D -E -e -F -I -i -J -L -l -m -O -o -p -Q -R -S -W -w`）はその次の語ごと飛ばし、最初の残りの語を行き先とする。`scp`・`rsync` のとき: `:` を含む最初の語の `:` より前を行き先とする。行き先の `user@` は外す。行き先が `$` を含む・空なら決めない（`no` 扱い）。
5. 行き先を `resolve(行き先)` で解き、返ったどれかに `manual-only` を含めば `yes`。
6. どの呼び出しも `yes` でなければ、文面の中の台本のパスを探す: 正規表現 `(?:^|[\s;|&("'])((?:~|/)[^\s;|&)"'<>]+\.(?:sh|py))`（試作4と同じ。`~` か `/` で始まる絶対パスだけ。相対パスは見ない）。見つかった各パスを `os.path.expanduser` して `read_file` に渡す。
   - 中身が返ったら、その中身に `manual-only` の文字があれば `yes`。無ければ中身に 1〜5 を当てる（台本の中の台本はたどらない＝深さ1）。
   - None が返ったパスが1つでもあり、ほかに `yes` が無ければ `unreadable`。
7. それ以外は `no`。

既定の `resolve`: `subprocess.run(["ssh", "-G", host], capture_output=True, timeout=10)` の出力の `identityfile ` で始まる行の値のリスト。終わりの番号が 0 以外・タイムアウトなら空のリスト。同じ行き先は1回だけ解く（辞書で覚える）。既定の `read_file`: 2,000,000 バイトまで読んで文字列、`OSError` なら None。同じパスは1回だけ読む。

### 3-3. `pl_load_windows(projects_dir, since, until, resolve, read_file)` → (windows, stats)
- 読むファイル: `projects_dir/*/*.jsonl`（メイン）と `projects_dir/*/*/subagents/*.jsonl`（担当）。更新時刻が `since` より前のファイルは読まない。
- 1行ずつバイトのまま読み、`toolu_`・`<bash-input>`・`<bash-stdout>` のどれも含まない行は `json.loads` しない（速さのため。試作4で1週 154 秒）。
- 会話の印 `sid8`: `projects_dir` から見た相対パスの2つ目の要素の先頭8文字（メインは `<会話>.jsonl`、担当は `<会話>` のフォルダ名）。
- 担当かどうか: 担当のファイル、またはメインのファイルでも記録に `"isSidechain": true` があるもの。
- 呼び出しの窓（記録の `timestamp` を `parse_ts` で読む）:

| 呼び出し | 始まり | 終わり |
|---|---|---|
| assistant の `tool_use` で name が `Bash`、`input.run_in_background` が真でなく、同じ id の `tool_result` の中身に `moved to the background`・`running in background` のどちらも無い | `tool_use` の記録の時刻 | 同じ id（`tool_use_id`）の `tool_result` の記録の時刻 |
| name が `Monitor`、または `run_in_background` が真、または上の文字がある | `tool_use` の記録の時刻 | 同じファイルの後の記録で、行の生の文字に `<task-notification>` と `<tool-use-id>その id</tool-use-id>` の両方があるもののうち最初の時刻。無ければそのファイルで最後に読めた時刻とし、`noend` に数える |
| user の記録で `message.content` が文字列で `<bash-input>` で始まる（メインのファイルだけ） | その記録の時刻 | その後の最初の、`message.content` が `<bash-stdout>` で始まる user の記録の時刻 |

- 窓の要素: `{"start", "end", "sid8", "who": "main"|"sub"|"bang", "key": pl_uses_key(...) の値, "noend": 真偽}`。`!` の窓の `key` は `pl_uses_key` を当てずに `"bang"` とする。
- `until` より後に始まる窓と、`since` より 1 日以上前に終わる窓は捨てる。
- stats: `{"files": 読んだファイル数, "calls": 窓の数, "noend": 終わり不明の数, "long": 長さが1時間を超える窓の数}`。

### 3-4. `pl_classify(logins, windows, mac_ip, slack_s=3)` → list
入室1回ずつ、`窓の始まり - 3秒 <= 入室の時刻 <= 窓の終わり + 3秒` の窓を重なりとし、次の順で最初に当たった分類を付ける。分類名の文字はこのとおり（出力にそのまま出す）。

| 順 | 分類名 | 条件 | 説明できる |
|---|---|---|---|
| 1 | `異常: 接続元が違う` | `src` が `mac_ip` ではない | いいえ |
| 2 | `異常: 担当が使った` | 重なる窓に who=sub・key=yes がある | いいえ |
| 3 | `説明済み: メインの会話` | 重なる窓に who=main・key=yes がある | はい |
| 4 | `説明済み: PO の !` | 重なる窓に who=bang がある | はい |
| 5 | `要確認: 台本が読めない` | 重なる窓に key=unreadable がある | いいえ |
| 6 | `要確認: 関係の無い実行だけ` | 重なる窓がある | いいえ |
| 7 | `要確認: 記録なし` | 重なる窓が無い | いいえ |

- 返す要素: `{"t", "host", "class", "explained": 真偽, "win": その分類を決めた窓（7 と 1 は None。1 で重なる窓があればその最初）}`。
- 窓は始まりの順に並べ、`bisect` で候補を絞る（全部の組を比べない）。

### 3-5. `run_prod_logins(home, auth_specs, since, until, delegation_start, mac_ip, out, resolve=None, read_file=None)` → 終わりの番号
- `auth_specs` は `[(label, path), …]`。`out` は1行ずつ受け取る関数（今の `run_audit` と同じく `print` を渡す）。
- 入室は `since <= t <= until` のものだけ。
- 出力（この順。日本時間は `%Y-%m-%d %H:%M:%S`、窓の時刻は `%H:%M:%S`）:

```
== 無制限鍵の入室と会話の記録の照合 ==
期間: 2026-10-26 14:00:00 〜 2026-11-02 18:06:00（委任の開始 2026-11-02 18:06:00）
入室: prod1=1226 prod2=31
会話の記録: ファイル=812 呼び出し=51626 終わり不明=279 1時間を超える窓=3
分類: 異常: 接続元が違う 全体 prod1=0 prod2=0 委任の後 prod1=0 prod2=0
分類: 異常: 担当が使った 全体 prod1=2 prod2=0 委任の後 prod1=0 prod2=0
（7分類すべてを §3-4 の順で1行ずつ。0件の分類も出す）
UNEXPLAINED=2026-10-30 12:19:41 prod1 7149cc23 異常: 担当が使った 委任の前 窓=12:19:40-12:19:45
（説明できない入室を1行ずつ時刻の順に。窓が無いときは 窓=なし）
AFTER_MAIN=2026-11-02 22:30:05 prod1 7149cc23 窓=22:30:04-22:30:06 prod-ops=3行
（委任の後の「説明済み: メインの会話」を1行ずつ。prod-ops= は §3-5 の下の決まり）
秒=154
UNEXPLAINED_AFTER_DELEGATION=0
```

  上の数字は形を示す例で、期待値ではない。
- `prod-ops=`: `home/CC報告ファイル-keep/prod-ops/<入室の日本時間の YYYYMMDD>.md` があればその行数を `N行`、無ければ `なし`。
- 終わりの番号: 委任の開始以後（`t >= delegation_start`）に説明できない入室が1件でもあれば 1、無ければ 0。
- 呼び出しの文面（`command`・`<bash-input>` の中身）と台本のパスは1文字も出力しない。

### 3-6. `run_prod_logins_cli(args, home, now)` → 終わりの番号
- `--auth` が1つも無い・`LABEL=PATH` の形でない・`--since`/`--until` が無い・時差が無い（`parse_ts` は時差が無いと UTC とみなすので、文字列に `+`・`-`（日付の中の `-` を除く時刻の後ろ）・`Z` が無いことを先に確かめる）・入室のファイルが読めない → `STOP: <理由>` を1行出して 2。
- それ以外は `run_prod_logins(home, …, out=print)` の戻り値。

禁止形（出力の例）: `UNEXPLAINED=2026-10-30 12:19:41 prod1 ssh -o BatchMode=yes prod1 …`（文面を出している）、`分類: 異常: 担当が使った: 2`（サーバーごと・委任の前後に分けていない）。

## 4. 試験 `scripts/dev/prod-login-match-tests.py`（新規）

- `importlib.util.spec_from_file_location` で `scripts/dev/consent-audit.py` を読み込む（`permission-delegation-tests.py` の `load` と同じやり方）。
- すべて `tempfile.mkdtemp` の一時の場所に作り物の記録と入室のファイルを作る。`resolve` と `read_file` は試験の中の辞書で差し替える（例 `{"prod1": ["~/.ssh/manual-only/id_ed25519"], "49.212.137.46": ["~/.ssh/salesanchor-claude"]}`）。
- 1試験1行で `PASS <名前> <説明>` か `FAIL <名前> <説明>` を出し、最後の行は `PASS=<n> FAIL=<m> TOTAL=<k>`。FAIL が1つでもあれば終わりの番号 1、無ければ 0。
- 試験（名前はこのとおり。1つの名前に複数の確かめがあってよい）:

| 名前 | 確かめること |
|---|---|
| T1 | `2026-11-02T23:45:10.398968+09:00 h sshd[1]: Accepted publickey for ubuntu from 49.128.148.145 port 5 ssh2: ED25519 SHA256:x` が UTC 14:45:10.398968・src 49.128.148.145 になる。`Failed password` の行と時刻の壊れた行は数えない |
| T2 | 手前の Bash（始まり 00:00:00・終わり 00:00:10・`ssh -i ~/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46 uptime`）に対し、入室 00:00:13.0 は `説明済み: メインの会話`、00:00:13.5 は `要確認: 記録なし`。始まりの側も 23:59:57.0 は入り 23:59:56.5 は入らない |
| T3 | 別名: `ssh prod1 "df -h"` は yes。`ssh 49.212.137.46 x` は no で、重なる入室は `要確認: 関係の無い実行だけ`。`ssh -o BatchMode=yes prod1 'x'`・`ssh -p 22 prod1 x`・`ssh ubuntu@prod1 x`・`scp a prod1:/tmp/`・`rsync -e "ssh -i ~/.ssh/manual-only/k" a b:/c` は yes。`ssh -o IdentityFile=~/.ssh/manual-only/k 1.2.3.4 x` は yes |
| T4 | `run_in_background` が真の Bash（`tool_result` は +1秒、`<task-notification>` と `<tool-use-id>その id</tool-use-id>` の行が +600秒）に +300秒の入室が `説明済み: メインの会話`。知らせが無いときはファイルの最後の時刻が終わりで、stats の noend が 1 |
| T5 | 手前の Bash の `tool_result` に `moved to the background` がある場合も T4 と同じ扱い。`Monitor` も同じ |
| T6 | `!`: `<bash-input>ssh prod1 ls</bash-input>` の user 記録（t）と `<bash-stdout>…` の user 記録（t+5秒）に t+3秒の入室が `説明済み: PO の !` |
| T7 | 担当: `<会話>/subagents/agent-a.jsonl` の `ssh prod1 x` に重なる入室が `異常: 担当が使った`。メインのファイルの `"isSidechain": true` の記録でも同じ。担当とメインの両方の鍵ありが重なるときも `異常: 担当が使った` |
| T8 | heredoc: `cat > /tmp/README.md <<'EOF'` の中の `ssh -i ~/.ssh/manual-only/k prod1` は no。`tee /tmp/a <<EOF` の中も no。`bash <<'EOF'` の中の `ssh prod1 ls` は yes。`bash -c "ssh prod1 ls"` は yes。`ssh prod1 <<'EOF'` は yes |
| T9 | 台本: `bash /abs/run.sh` で read_file が `ssh -i ~/.ssh/manual-only/k 1.2.3.4 x` を返すと yes。`ssh prod1 x` を返すと yes。`echo hi` を返すと no。None を返すと unreadable で、重なる入室は `要確認: 台本が読めない`。`bash scripts/x.sh`（相対）は read_file を呼ばない |
| T10 | 接続元が `1.2.3.4` の入室は、メインの鍵ありが重なっても `異常: 接続元が違う` |
| T11 | `run_prod_logins` の全体: 委任の前だけに説明できない入室があると終わりの番号 0、委任の後に1件あると 1。最後の行が `UNEXPLAINED_AFTER_DELEGATION=` で始まる。分類の行が7行。出力の全行に、試験で使った文面の文字（`ssh `・`df -h`・`/abs/run.sh`）が1つも無い |
| T12 | `run_prod_logins_cli`: `--since 2026-11-02T18:06`（時差なし）・`--auth prod1`（`=` なし）・無いファイル の各場合に `STOP:` の行と終わりの番号 2 |
| T13 | `prod-ops=`: 一時の home の `CC報告ファイル-keep/prod-ops/20261102.md`（3行）があると `prod-ops=3行`、無い日は `prod-ops=なし` |
| T14 | 今の入口が変わらない: `main(["--audit"])` を一時の home で（`real_home` を差し替えて）流しても例外にならず、`ABNORMAL=` の行が出る |

## 5. 手順（クラウドの作業場所で）

1. `git fetch origin && git checkout -b release/prod-login-match origin/main`
2. `git log -1 --format=%H origin/main` と `wc -l scripts/dev/consent-audit.py` を報告に貼る。
3. §2・§3 のとおり `scripts/dev/consent-audit.py` を直す。§4 の `scripts/dev/prod-login-match-tests.py` を作る。
4. `python3 -I -B scripts/dev/prod-login-match-tests.py`
5. `python3 -I -B scripts/dev/permission-delegation-tests.py`
6. `python3 -I -B scripts/dev/consent-audit.py --help`（新しい引数が出ること）
7. `git diff --stat origin/main...HEAD` と `git diff --name-only origin/main...HEAD`（コミットの後）
8. `git add scripts/dev/consent-audit.py scripts/dev/prod-login-match-tests.py && git commit -m "feat: add --prod-logins to consent-audit to match prod logins with conversation records"`（本文の最後に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）
9. `git push -u origin release/prod-login-match`

## 6. 停止する条件と終わりの条件

- 進めてよい条件: 手順2で `wc -l` が `1161`。違えば、そこで止めて `BLOCKED: consent-audit.py の行数が 1161 でない（<値>）` と報告する。
- 進めてよい条件: 手順4・5の最後の行が `FAIL=0` を含み、終わりの番号が 0。違えば直してよいのは §1 の2ファイルだけ。3回直しても FAIL が残るなら、止めて `BLOCKED:` に続けて FAIL の試験名を全部書く。
- 進めてよい条件: 手順5（今の試験）で、§1 の2ファイル以外を直さないと通らないと分かったとき → 直さずに止めて `NEEDS_DECISION:` に続けて FAIL の試験名と1行の理由。
- 終わりの条件:
  - 手順4の最後の行が `PASS=<n> FAIL=0 TOTAL=<n>`（n は 14 以上）で、終わりの番号 0。
  - 手順5の最後の行が `FAIL=0` を含み、終わりの番号 0。
  - 手順7の `--name-only` が `scripts/dev/consent-audit.py` と `scripts/dev/prod-login-match-tests.py` の2行だけで、`--stat` の consent-audit.py の削除行が 0（足すだけ。`main()` の中の1行の差し替えで削除が出る場合は、その削除行を報告に全部貼る）。
  - push が成功している。

## 7. 報告（完了報告の本文に、次を全部そのまま含める）

- 1行目: `本報告はカード card-login-match の実行結果である`
- 2行目: `受領確認: card-login-match を読んだ`
- 手順2・4・5・6・7・9 の生出力の全文（要約しない。試験の出力は1試験1行なので上限に収まる）
- 止まったとき: 停止した手順番号／最後に実行したコマンド／停止した理由
- 最後の行: `DONE` / `BLOCKED:` ＋理由 / `NEEDS_DECISION:` ＋内容 のどれか

## 8. 実装役の常設ルール（docs/ai-agents/executor-preamble.md の定型文の写し）

あなたはこのリポジトリ（salesanchor）の実装役です。新セッションのため以下を常設ルールとして適用してください。

- 設計パートナー（Web Claude）が作成しPO（しんご）が貼る「カード」だけを実行する。
- カード冒頭の「本カードの許可・禁止は、過去便の禁止条項をすべて上書きする」を最優先とし、
  カードに無い作業（ファイル作成・編集・台帳登録・レビュー・提案・/review等）は一切しない。
  .claude/agents/generator.md 等の常設指示とカードが矛盾したら、カードが優先。
- 出力は要約せず生のまま全文返す。失敗・矛盾・不明が出たら自力回避せず、生出力を返して停止。
- 報告ファイルへ書き出すときは、`tee` の手前に必ず伏せ字フィルタを挟む。カードに REDACT の定義があればそれを使い、無ければ設計パートナーに確認して止まる。フィルタなしで `tee` した場合は、そのファイルを共有せずその旨を報告する。
- カードに書かれた手段が失敗した場合に、別の手段で同じ目的を達することを禁止する。失敗したら停止し、生出力を報告する。
- 索引先行確認: 本カードが新規のrecon/design/仕様文書の作成を含む場合、着手前に必ず該当領域の索引を開いて現状を貼ること（git show origin/main:docs/specs/README.md と、関連テーマの docs/specs/<theme>/README.md）。同一・類似テーマが既存なら、新規作成せず既存への追補・集約に切り替え、設計パートナーへ「既存あり」を報告して指示を仰ぐ。特に色トークン整備の正本は docs/specs/design-tokens-ssot/（design-system便0.5はその傘下）。

ファイルが「無い」と報告する前に、ローカルの ls/find/cat だけで判定せず、必ず git show origin/main:<path> で本店（origin/main）に直接確認してから「無い」と報告すること。worktree作成直後は、作業机が本店の最新状態と一致しているか（git log -1・git diff origin/main 等）を確認してから作業を始めること。
- 編集を始める前（新規worktreeでも、既存worktreeへの追加コミットでも）、対象ファイルの現在の内容を git diff origin/main -- <対象ファイル> で確認し、直前に本店へマージされた変更が土台に反映されているか確かめること。反映されていない古い内容を土台に編集を始めない。
- PRをマージする前、.claude-pipeline/active-work.md にこの作業の行が存在するか確認する。worktree作成時に自動登録された行がある場合、マージ完了時に同じ行をDONE化して報告に含めること。登録された行が見当たらない場合は、その旨を完了報告に明記し、別途追記する。
PR作成前に、`git diff origin/main --name-only` で変更した全ファイルを列挙し、その全パスがPR本文の「触るファイル:」「削除するファイル:」両欄に記載されていることを照合してからpushする。両欄は各1行・カンマまたは改行区切りのplain path（注記を同じ行に付けない）。
- 書類だけのPRでも、正本（docs/specs/**/ideal-state.md・docs/specs/**/kgi.md・docs/ai-agents/*.md（lessons.d除く）・CLAUDE.md・AGENTS.md）を1件でも含む場合、関所は自動スキップせず宣言照合を行う（「書類だけだから宣言不要」は不可）。関所は該当時に「書類のみだが正本を含む — 宣言照合へ進む（柱2）」と出力する。根拠: docs/specs/process-hardening/design-pillar2.md

### PR作成の手順（例外なし）

PR本文は .github/PULL_REQUEST_TEMPLATE.md を起点にする。
gh pr create --body-file <テンプレートを埋めたファイル> で作成し、
本文を自前で組み立てない。

「### 標準ワークフロー確認」の記入規則（すべて実測で確認済み）:

- 触るファイル: は半角コロンと同じ行にカンマ区切りで書く。
  箇条書き（行頭 -）は検査に通らない。削除するファイル: も同様。
- 削除するファイル: には、diff に deletions がある実ファイルを列挙する。
  「なし」と書いても、実際に削除行があれば検査に落ちる。
- 対象ADR: / recon: / 設計: は平打ち形式で書く。テーブル記法は検査に通らない。
- recon / design は実ファイルが必要。本文にパスを書くだけでは通らない。
- recon / design に書くパスは、書く前に ls で実在を確認する。
  ADR のファイル名は「ADR-番号-説明」の形で、説明部分を推測すると必ず外れる。
- recon / design 内のバッククォート付きパスは実在確認される。
  そのPRで削除するファイルは、バッククォートを付けずプレーンテキストで書く。

frontend/src、backend/app/routers、backend/app/services 等の変更は
GO（PO、または ADR-1003 に基づく Opus の委任 GO）を受領し「### GO記録」に転記してからマージする。

PR作成後、マージ前に gh pr checks で赤を確認する。
赤が出たら自力で直さず、失敗ログ全文を報告して停止する。

## 9. カードの自己審査（2026-11-03 Opus。同じ AI による自己審査で、独立した第二者の審査ではない）

- 判定: APPROVE
- 設計との整合: design.md 追補の「入力」「呼び出しの窓」「判定」「分類」「出力」を §3-1〜§3-5 に写した。設計からの変更は2点で、design.md 追補に同じ日に書き足した: ①入室のファイルにサーバーの名前を付けるため `--auth LABEL=PATH` とした（auth.log の行の機体名は `os3-322-50792` の形で prod1/prod2 が分からない・recon の実測）②出力はファイルに書かず画面に出し、手順の行でファイルに残す（今の手作業の記録 `20261102-prod-login-check.md` を上書きしないため。名前は `-prod-login-match.md`）。
- 実物との照合: origin/main `6d532b2a2` で `scripts/dev/consent-audit.py` 1161 行、`paths`・`parse_ts`・`read_jsonl`・`run_audit`・`main` の形を読んだ。`scripts/dev/permission-delegation-tests.py` の最後の行の形 `PASS=%d FAIL=%d TOTAL=%d` と `load` のやり方を読んだ。
- 試作との照合: 窓の決め方・文字での先絞り・台本のパスの正規表現・知らせの行の条件は、試作4（1週 154 秒・重なり無し 0 件）と同じにした。
- 残る確かめ（Opus がマージ前に手元の実データで）: design.md 追補の受入条件の表の1〜6行目。クラウドには会話の記録と auth.log が無いので、カードには入れていない。
- 受け入れた弱さ: 相対パスの台本と、Python の台本の中の `["ssh", "prod1"]` の形は見ない（試作4と同じ）。見落とすと「要確認: 関係の無い実行だけ」に出るので、説明できるものを説明できないと出す側に倒れる（見逃しにはならない）。

END OF CARD
