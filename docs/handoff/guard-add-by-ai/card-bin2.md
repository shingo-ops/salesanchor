# 実装カード 便2: AI が見張りを入れる共通の台本 install-guard.sh と、最初の札（mac-test-guard）

> What this document is, in one line:
> Build one shared installer script that copies a reviewed guard from the synced main checkout into ~/.claude, registers its hooks without ever removing or loosening anything, and writes ledger rows that the weekly audit (bin 1) can match; add the first guard manifest and run the guard tests in CI.

- 親: design.md（同じフォルダ）§5-0・§5-5・§6・§10・§13（特に §13-1 の便2 と、この便で足した §13-8）。ADR-1072 は PO 承認済み（2026-11-09「1」。承認と実装の開始を選んだ返事）。便1 は PR #5329 でマージ済み（30f297528）
- 基準: origin/main 30f297528。行番号はすべて、この版で Opus が読んで確かめた
- ブランチ: `release/guard-add-by-ai-bin2`（作業場所は Opus が `bash scripts/new-worktree.sh release/guard-add-by-ai-bin2 --claude` で作り済み。カードの commit がこの枝の先頭にある）
- 読んだ決まり: docs/handoff/design-partner-card-ops/guards/00-common.md・04-worktree.md・05-pr.md・10-executor.md
- 受領確認: 着手の前に、§0 を満たしたかを1行で返してから始める
- 起票: Opus が手元で行う。担当は push までとする
  - `--base main`、`shingo-cc` 名義で起票する
  - `scripts/` を含むので GO 記録が要る（ADR-136。Opus が委任 GO で行う）
  - マージ、HKI-1 の追加、install-guard.sh の初回の実行は、担当が行わない（PO の `!` と Opus）

## 0. 着手条件（満たさなければ止まって BLOCKED: で返す）

- origin/main の次の行が、下の表の「基準の中身」と同じであること
  - 確かめ方の例: `git show origin/main:scripts/dev/consent-audit.py | sed -n '938p'`
  - 1つでも違えば、BLOCKED: で差を返す

| 場所 | 基準の中身（先頭の語） |
|---|---|
| `scripts/dev/consent-audit.py:404` | `TOOLS_DIRNAME = ".salesanchor-tools"` |
| `scripts/dev/consent-audit.py:459` | `def item_sha8(item):` |
| `scripts/dev/consent-audit.py:585` | `def _hook_items(hooks):` |
| `scripts/dev/consent-audit.py:641` | `with open(os.path.join(tools, "scripts", "agent-hooks", "install-guard.sh"), "rb") as f:` |
| `scripts/dev/consent-audit.py:697` | `files.append("%s|%s" % (sha8(os.path.relpath(fp, p["hook_dir"])), digest))` |
| `scripts/dev/consent-audit.py:938` | `def _ga_manifest(text, name):` |
| `scripts/dev/consent-audit.py:970` | `def _ga_words_ok(text):` |
| `scripts/dev/consent-audit.py:980` | `def _ga_hook_form(home, name, hk):` |
| `scripts/dev/consent-audit.py:1058` | `live = [ln.lstrip() for ln in run.split("\n") if not ln.lstrip().startswith("#")]` |
| `scripts/dev/consent-audit.py:1957` | `if __name__ == "__main__":` |
| `scripts/dev/perm-change.py:286` | `raise Exit(EXIT_FAIL, "python3 -I -B で起動してください（isolated と dont_write_bytecode が必要）")` |
| `scripts/dev/perm-change.py:290` | `raise Exit(EXIT_FAIL, "~/%s/%s から起動してください" % (TOOLS_DIRNAME, SELF_REL))` |
| `scripts/dev/perm-change.py:774` | `r = sub.add_parser("record")` |
| `scripts/dev/perm-change.py:784` | `r.add_argument("--old-json", default="")` |
| `scripts/agent-hooks/mac-test-guard/install.sh:34` | `cmd = "python3 %s/guard.py" % os.environ["DEST"]` |
| `scripts/agent-hooks/mac-test-guard/test_guard.py:6` | `GUARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'guard.py')` |
| `.github/workflows/agent-hooks-test.yml:23` | `- uses: actions/checkout@v5` |
| `.github/workflows/agent-hooks-test.yml:25` | `run: bash scripts/agent-hooks/review-gate/test_review_gate.sh` |
| `.github/workflows/agent-hooks-test.yml:34` | `- uses: actions/checkout@v5` |
| `.github/workflows/agent-hooks-test.yml:36` | `run: bash scripts/agent-hooks/test_master_register_rules_guard.sh` |

- `scripts/agent-hooks/install-guard.sh` と `scripts/agent-hooks/mac-test-guard/guard-manifest.json` が origin/main に無いこと（`git show origin/main:<path>` が失敗する）

## 1. 事実（Opus が確かめたこと。担当は確かめ直さなくてよい）

- 週次点検の写しで、見張りの本体は `sha8(~/.claude/scripts から見た相対パス)|中身の sha256 先頭8桁`（consent-audit.py:697）。登録の組は `event|matcher|組の JSON の item_sha8`（:585 からの `_hook_items`）。台帳の item_hash は、どちらも末尾の8桁
- 札の検査は consent-audit.py の `_ga_manifest`（:938）、確認を飛ばす語の検査は `_ga_words_ok`（:970）、足す命令の形は `_ga_hook_form`（:980）にある。台本はこの3つを**読み込んで使う**（同じ規則を2か所に書かない。SSOT）。consent-audit.py は `if __name__ == "__main__":`（:1957）で守られていて、読み込むだけでは点検は走らない
- perm-change.py は `python3 -I -B ~/.salesanchor-tools/scripts/dev/perm-change.py` で起動しないと止まる（:286・:290）。record の引数は :774-784（`--target`・`--op`・`--item-hash`・`--po-ref`・`--intent`・`--reason`・`--actor`・`--replaced-by`・`--batch`・`--old-json`）。`--old-json` の命令に `=` を含む語か32字以上の英数字の語があると拒む（:687-692）
- 点検の CI の検査（:1058 の前後）は、`run:` の行に `scripts/agent-hooks/<name>/<試験>` の文字列があるかを見る。今の CI は review-gate と master-register の2つだけを流す（agent-hooks-test.yml:25・:36）
- mac-test-guard の試験は、引数1つで本体のパスを受ける（test_guard.py:6）。本体は subprocess で流すので、`__pycache__` は作らない（:46）
- 手元の Mac には mac-test-guard が既に入っている（~/.claude/settings.json の PreToolUse・Bash の組で `mac-vm-guard.py` の直後に `python3 /Users/<名前>/.claude/scripts/mac-test-guard/guard.py`。写しの中身は正本と sha256 が同じ。Opus が 2026-11-09 に確かめた）。このため初回の実行は「差が無い」で終わり、台帳の行は書かれない（設計 §6）

## 2. この便で作る範囲（設計 §13-1 の便2）

1. `scripts/agent-hooks/install-guard.sh`（新規）
2. `scripts/agent-hooks/mac-test-guard/guard-manifest.json`（新規。本体の guard.py・test_guard.py・install.sh・rollback.sh は**変えない**）
3. `scripts/agent-hooks/test_install_guard.py`（新規。台本の試験）
4. `.github/workflows/agent-hooks-test.yml`（job を2つ足し、全 job の checkout を `fetch-depth: 0` にする）

## 3. やること（この順）

1. §0 を確かめ、受領確認を1行で返す
2. 変える前の main で、`python3 scripts/agent-hooks/mac-test-guard/test_guard.py` をクラウドで流し、生の出力の最後の5行を取っておく（Linux で通るかの確かめ）
3. §4 の札を足す
4. §5 の台本を書く
5. §6 の試験を書き、クラウドで流す
6. §7 の CI を変える
7. §8 の検索を流す
8. commit して push する（`git add` は §2 の4ファイルと、台帳の自分の枝のファイルだけ）

## 4. 札（`scripts/agent-hooks/mac-test-guard/guard-manifest.json`）

中身はこのとおり（設計 §5-0 の例と同じ）。最後に改行1つ。

```json
{"name": "mac-test-guard",
 "files": ["guard.py"],
 "hooks": [{"event": "PreToolUse", "matcher": "Bash", "interpreter": "python3", "file": "guard.py", "after": "mac-vm-guard.py"}],
 "tests": ["test_guard.py"]}
```

## 5. 台本（`scripts/agent-hooks/install-guard.sh`）

形: 先頭は `#!/bin/bash` と `set -eu`。本体の処理は `python3 -I -B - "$@" <<'PY'` の中に書く（今の mac-test-guard/install.sh:31 と同じ書き方）。出力の最後の1行は、次の3つのどれか。

| 最後の行 | 終了コード | 意味 |
|---|---|---|
| `INSTALL_OK` | 0 | 入れた、または差が無かった。記録も全部書けた |
| `INSTALL_OK_RECORD_INCOMPLETE` | 3 | 入れたが、記録の行の一部を書けなかった（週次点検で B に出る。Opus が PO に報告する） |
| `INSTALL_FAILED: <理由>` | 1 | 止まった。settings.json に触っていない。手順9より前で止まったときは `~/.claude/scripts/` にも触っていない（手順10の後で止まったときの扱いは手順10） |

手順（設計 §6 の 1〜10。どこか1つでも失敗したら `INSTALL_FAILED:` で止まる）:

1. 引数: ちょうど1つ。`^[a-z0-9-]+$` に合わなければ止まる。
2. 場所は固定: `H = os.environ["HOME"]`、入れ先 `H/.claude`、正本の写し `T = H/.salesanchor-tools`。環境変数 `CLAUDE_DIR` は読まない（文字列としても書かない）。
3. 正本の写しの確かめ（`git -C T` で）:
   - `status --porcelain --untracked-files=all` が空
   - `rev-parse --is-shallow-repository` が `false`
   - `rev-parse HEAD` が `ls-remote origin refs/heads/main` の1つ目の語と同じ
   - `T/scripts/agent-hooks/<name>/` がフォルダで、シンボリックリンクでない
4. 版と PR 番号（設計 §6 の 9 を前に出す。札を版から読むため）:
   - `mc = git log --first-parent HEAD -1 --format=%H -- scripts/agent-hooks/<name>/`
   - `subj = git log -1 --format=%s <mc>` が `^Merge pull request #([0-9]+) from ` に合うこと。合わなければ止まる（記録できないため）
   - HEAD を使うのは、3. で HEAD が GitHub の main と同じと確かめたから（写しの `origin/main` の参照は古いことがある）
5. 札: `git show <mc>:scripts/agent-hooks/<name>/guard-manifest.json` を読み、consent-audit.py の `_ga_manifest(text, name)` に通す。None なら止まる。`hooks` が空なら止まる。
   - consent-audit.py は `importlib.util.spec_from_file_location("consent_audit_for_install", T + "/scripts/dev/consent-audit.py")` で読み込む。
6. 語の検査（設計 §5-5）: 札の `files` と `hooks[].file` の各ファイルについて、`git show <mc>:scripts/agent-hooks/<name>/<file>` の中身を `_ga_words_ok` に通す。False なら止まる（`tests` のファイルは当てない）。
7. 置き場で試す（入れ先に触る前）:
   - `tempfile.mkdtemp()` の中に、札の `files` を正本の写し（`T/scripts/agent-hooks/<name>/<file>`）から写す。正本がシンボリックリンクなら止まる。正本が普通のファイルでなければ止まる（`os.path.islink` を先に見て、次に `os.path.isfile`）。
   - 札の `tests` を順に流す。拡張子が `.py` なら `python3 -I -B <T の試験> <置き場の hooks[0].file>`、`.sh` なら `bash <T の試験> <置き場の hooks[0].file>`、ほかは止まる。cwd は `T`。1本 300 秒で打ち切る。1本でも 0 以外なら止まる。
   - 試験の引数の決まり（本体のパスを1つ受ける）は、今の test_guard.py:6 と同じ。新しい見張りもこの形で書く（設計 §13-8）。
8. settings.json の新しい形を組み立てる（まだ書かない。入れ先に触る前に、読めないときに止まるため）:
   - `H/.claude/settings.json` が無い・JSON として読めない・object でないなら止まる。読んだ中身を `old` として、深い写し `d` を作る。
   - 札の `hooks` の各要素について、`new = _ga_hook_form(H, name, hk)`。`d["hooks"][event]` の組のうち `g.get("matcher", "") == hk.get("matcher", "")` のものに、`command` が `new["command"]` と同じフックが既にあれば何もしない。
   - 無ければ、同じ event と matcher の組を前から順に見て、`command` の最後の空白で区切った語が `after` と同じか `/` + `after` で終わるフックを探し、その直後に `new` を入れる。見つからなければ、同じ event と matcher の最初の組の最後に足す。そういう組が無ければ、`{"matcher": <matcher>, "hooks": [new]}` の組を `d["hooks"][event]` の最後に足す（札に matcher が無ければ `"matcher"` の欄を付けない）。
   - 既にあるフックを消す・並べ替える・欄を変えることはしない。
   - 変わった組ごとに、前の組（`old` の中の同じ位置の組。新しい組なら無し）と後の組（全部の要素を入れ終えた `d` の中の組）を覚える。1回の実行で同じ組に2件以上入れても、記録は「実行の前の組」と「全部入れた後の組」の1組だけにする（途中の形を記録すると、週次点検の `_ga_group` が組を見つけられず B に出る）。
9. 入れ先へ本体を写す（ここから先は ~/.claude に書く）:
   - 排他: `os.mkdir(H/.claude/.install-guard.lock)`。既にあれば止まる（自分で作っていない lock は消さない）。作った後は、終わりと失敗のどちらでも消す（try/finally）。
   - 札の `files` の各ファイルについて、前の中身8桁（入れ先に無ければ `-`）を覚える。
   - 中身が同じなら写さない。違えば、入れ先のファイルを書けるようにしてから写し、`chmod 0o555`（中のフォルダは `os.makedirs`）。写した後の sha256 が正本と同じでなければ止まる。
10. settings.json を書く:
   - `d == old` なら書き直さない（sha256 が前と同じまま）。
   - 違えば、`settings.json.bak-install-guard-<name>-<UTC の時刻>` に控えを取り、同じフォルダに一時ファイルを書き、読み直して JSON の object であることを確かめてから `os.replace`。書き方は `json.dump(d, f, ensure_ascii=False, indent=2)` と改行1つ（今の install.sh:56-57 と同じ）。
   - 手順9で本体を1つでも写した後に、手順9の残りか手順10で止まったとき: settings.json は変えないまま（`os.replace` の前なら元のまま）、写した本体の分の hook-files の記録（手順11の「本体」の行）だけを書いてから、`INSTALL_FAILED: <理由>` で止まる。こうすると、~/.claude/scripts の差は記録で説明でき、週次点検で B に出ない。
11. 記録（設計 §6 の 10・§5-3）。変わったものだけ書く。2回目の実行で差が無ければ1行も書かない。
    - batch: `"batch:" + secrets.token_hex(8)`（1回の実行で1つ）
    - 本体: 中身が変わったファイルごとに、前が `-` でなければ `--target hook-files --op remove --item-hash <前8桁>`、続けて `--target hook-files --op add --item-hash <後8桁>`
    - 登録: 手順8で覚えた変わった組ごとに（1組につき1回）、前の組が無い（新しい組）なら `--target user-hooks --op add --item-hash <item_sha8(後の組)> --batch <batch>`。前の組があれば、その add に加えて `--target user-hooks --op remove --item-hash <item_sha8(前の組)> --replaced-by <item_sha8(後の組)> --batch <batch> --old-json <前の組の JSON>`
    - どの行も `--po-ref PR#<n> --intent "install-guard <name>" --reason "ADR-1072 install-guard"`。`--actor` は付けない（既定の opus）
    - 呼び方: `subprocess.run(["python3", "-I", "-B", T + "/scripts/dev/perm-change.py", "record", ...])`。0 以外で返った行は `RECORD_FAILED: <target> <op> <item_hash>` と perm-change の標準エラーを出して次の行へ進み、最後を `INSTALL_OK_RECORD_INCOMPLETE`（終了コード 3）にする
    - item_sha8 は consent-audit.py の `item_sha8` を使う
12. 出力（値を出さない。8桁のハッシュだけ）: `PR=#<n>`、`FILE <name>/<file> <前8桁か-> <後8桁>`（変わったものだけ）、`GROUP <event>|<matcher> <前8桁か-> <後8桁>`（変わったものだけ）、差が無ければ `NO_CHANGE`、記録した行の数 `RECORDED=<数>`、最後の行（上の表）。

書かないこと: ほかの見張りの install.sh・rollback.sh を呼ばない。`~/.claude` の settings.json と `scripts/<name>/` と `.install-guard.lock` と控えのほかには書かない。外す処理を持たない。

## 6. 試験（`scripts/agent-hooks/test_install_guard.py`）

- 標準ライブラリだけ。`python3 scripts/agent-hooks/test_install_guard.py` で流れ、全部通れば終了コード 0、最後に `PASS=<数> FAIL=<数>` を出す（`FAIL` が1以上なら終了コード 1）。
- 本物の `~/.claude`・`~/.salesanchor-tools`・GitHub には触らない。試験ごとに一時の HOME を作り、台本を `env={"HOME": <一時の HOME>, "PATH": os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1"}` で `bash <一時の写しの install-guard.sh> <name>` として流す。
- 一時の HOME の作り方（試験ごと）:
  - `<HOME>/origin.git`（`git init --bare -b main` で作る）と、それを origin にした `<HOME>/.salesanchor-tools`（普通の clone。枝は main）。
  - git の名前とメールは env で渡す: `GIT_AUTHOR_NAME`・`GIT_AUTHOR_EMAIL`・`GIT_COMMITTER_NAME`・`GIT_COMMITTER_EMAIL`（値は `test`・`test@example.invalid`）。一時の HOME には git の設定が無いため、無いと commit が失敗する。
  - 写しの中身: このリポジトリの `scripts/agent-hooks/install-guard.sh`・`scripts/dev/consent-audit.py`（本物を写す）、`scripts/dev/perm-change.py` は**偽物**（受けた引数を `<HOME>/record-calls.jsonl` に1行の JSON で足して 0 で終わるだけ。本物の perm-change.py は origin の URL を GitHub と決めているので、試験では使えない。本物の record の行は便1 の G14 で確かめ済み）、見張りのフォルダ（下の各試験で作る）。
  - 見張りのフォルダは「PR のマージ」の形で入れる: 枝で commit し、`git merge --no-ff -m "Merge pull request #<n> from x/y"` で main に入れ、origin へ push する。commit の日時は固定する（GIT_AUTHOR_DATE・GIT_COMMITTER_DATE）。
  - `<HOME>/.claude/settings.json` に、PreToolUse・Bash の組 `{"matcher": "Bash", "hooks": [{"type": "command", "command": "/usr/bin/python3 <HOME>/.claude/scripts/mac-vm-guard.py", "timeout": 5}]}` を置く。
  - 試しの見張り `demo-guard` の本体は、標準入力を読んで終了コード 0 で終わるだけの python。試験は、引数のパスがあることを確かめて 0 で終わる python。
- 試験の一覧（名前は `test_g7_*`・`test_g9_*` などにする。G は設計 §13-6 の番号）:

| 名前 | 何を確かめるか | 期待 |
|---|---|---|
| G7-a | demo-guard（after: mac-vm-guard.py）を入れる | `INSTALL_OK`。命令が mac-vm-guard.py の直後に1件。`timeout: 5` が残る。本体が 0o555。記録の呼び出しは3回（hook-files add 1・user-hooks add 1・user-hooks remove 1（`--replaced-by`・`--batch`・`--old-json` あり、batch は add と同じ）。前の本体が無いので hook-files remove は無い）。`--po-ref` は `PR#<n>` |
| G7-b | G7-a の後にもう一度流す | `NO_CHANGE` と `INSTALL_OK`。命令は1件のまま。settings.json の sha256 が1回目の後と同じ。記録の呼び出しは増えない |
| G7-c | after の名前の組が無い札（matcher: Write） | 新しい組が最後に足され、記録は hook-files add と user-hooks add の2回（remove は無い） |
| G7-d | 本体だけを変えた2つ目のマージ（PR#<n+1>）の後で流す | `FILE` の行が出て、記録は hook-files remove（前の8桁）と add（後の8桁）。登録の組は変わらない |
| G9-a | 写しに追跡外のファイルがある | `INSTALL_FAILED:`。settings.json の sha256 と `~/.claude/scripts` の中身が前と同じ。記録0回 |
| G9-b | 写しの HEAD が origin の main と違う（origin に1つ commit を足す） | 同上 |
| G9-c | 名前の形が違う（`Demo`・`../x`・引数2つ・引数なし） | 4件とも同上 |
| A4-s | 札の無いフォルダ・札の `files` に `../x.py`・`/x.py`・event が `Notification` の札・`scripts/agent-hooks/` の直下のファイルの名前を渡す | 5件とも同上 |
| A8-s | 本体に7つの語（`permissionDecision` と `allow` を同じ行・`approve`・`updatedInput`・`updatedPermissions`・`updatedToolOutput`・`behavior`・`additionalContext`）のどれかがある | 7件とも同上 |
| A8-n | 試験のファイルだけに `--approve`・本体に大文字の `APPROVE` だけ | 2件とも `INSTALL_OK` |
| A11-s | 写しが浅い取得（`git clone --depth 1 file://...` で作る） | `INSTALL_FAILED:` と同上 |
| S-bad | `<HOME>/.claude/settings.json` を JSON でない中身にしておく | `INSTALL_FAILED:` と同上（`~/.claude/scripts/demo-guard/` が作られていない） |
| T-fail | 試験が 1 で終わる | `INSTALL_FAILED:`。`~/.claude/scripts/demo-guard/` が作られていない |
| T-sub | マージでない commit が最後に変えたフォルダ（`Merge pull request` の形でない） | `INSTALL_FAILED:` と同上 |
| R-fail | 偽の perm-change.py が remove の行だけ 1 で返す | 最後の行が `INSTALL_OK_RECORD_INCOMPLETE`、終了コード 3。`RECORD_FAILED:` の行が1つ |
| L-lock | `<HOME>/.claude/.install-guard.lock` を先に作っておく | `INSTALL_FAILED:`。終わった後も lock は試験が作ったまま（台本が消さない） |
| E-env | `CLAUDE_DIR=<別のフォルダ>` を env に足して流す | 入れ先は `<HOME>/.claude`。別のフォルダには何も作られない |
| M-real | このリポジトリの mac-test-guard の札と本体と試験を一時の写しに入れて流す | `INSTALL_OK`。命令は `python3 <HOME>/.claude/scripts/mac-test-guard/guard.py` で、mac-vm-guard.py の直後 |

- 「同上」の止まり方の確かめは、どれも ①最後の行が `INSTALL_FAILED:` で始まる ②終了コード 1 ③settings.json の sha256 が流す前と同じ ④`<HOME>/.claude/scripts` の下のファイル一覧と中身が流す前と同じ ⑤`record-calls.jsonl` が無いか空、の5つ。
- L-lock では lock を台本が消さないこと（自分で作っていない lock は消さない）。lock を作った後の失敗では消すこと（T-fail の後に lock が無いことを確かめる）。

## 7. CI（`.github/workflows/agent-hooks-test.yml`）

- 今の2つの job の `- uses: actions/checkout@v5` を、次の形にする（ほかの行は変えない）。

```yaml
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
```

- 最後に2つの job を足す（先頭の説明の注釈に「mac-test-guard・install-guard: ADR-1072」を足してよい）。`if:`・`continue-on-error`・`|| true` などは書かない（点検の CI の検査が B にするため。consent-audit.py の `_GA_CI_BAD`）。

```yaml
  mac-test-guard:
    name: mac-test-guard test
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - name: Run mac-test-guard tests
        run: python3 scripts/agent-hooks/mac-test-guard/test_guard.py

  install-guard:
    name: install-guard test
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - name: Run install-guard tests
        run: python3 scripts/agent-hooks/test_install_guard.py
```

## 8. 終わったときの検索（PR の枝で流し、結果を報告に入れる）

1. `git diff --name-only origin/main...HEAD` → §2 の4ファイルと、カード・設計書（Opus の commit）と台帳のファイルだけ
2. `git diff origin/main...HEAD -- scripts/agent-hooks/mac-test-guard/` → 札の追加だけ（ほかのファイルの差が0行）
3. `grep -n "CLAUDE_DIR" scripts/agent-hooks/install-guard.sh` → 0件
4. `grep -n "_ga_manifest\|_ga_words_ok\|_ga_hook_form\|item_sha8" scripts/agent-hooks/install-guard.sh` → 4つとも1件以上（規則を写さず読み込んで使っている）
5. `grep -n "rollback\|install.sh\|remove(" scripts/agent-hooks/install-guard.sh` → 外す処理と、ほかの台本の呼び出しが無い（`.install-guard.lock` を消す1か所と、一時の置き場を消す1か所だけは出てよい。出た行を全部報告に入れる）
6. `python3 -c "import yaml,sys; d=yaml.safe_load(open('.github/workflows/agent-hooks-test.yml')); print(sorted(d['jobs']))"` → 4つの job（PyYAML が無ければ入れてから流す）
7. `python3 scripts/agent-hooks/test_install_guard.py` の最後の5行と、`FAIL` を含む行の全部
8. `python3 scripts/agent-hooks/mac-test-guard/test_guard.py` の最後の5行（変える前と後）

## 9. 想定される分かれ道（こうなったらこうする）

| 起きたこと | どうする |
|---|---|
| §0 の行が基準と違う | 停止し、BLOCKED: で差を返す |
| mac-test-guard の test_guard.py が Linux で落ちる | 本体も試験も直さない（札を足す PR では本体を変えない。設計 §5-0）。停止し、BLOCKED: で生の出力を返す |
| `_ga_manifest`・`_ga_words_ok`・`_ga_hook_form` の動きを変えたくなる | consent-audit.py は変えない（印の中を変えると guard_judge が変わり、PO の「1」が要る）。NEEDS_DECISION: で返す |
| 設計書 §6・§13-8 と、このカードの §5 が食い違う | 書き手の判断で決めない。NEEDS_DECISION: で両方の文を返す |
| 試験の中で本物の GitHub・`~/.claude`・`~/.salesanchor-tools` に触れたくなる | 触らない。一時の HOME と bare のリポジトリで作る |
| 台本に、外す・並べ替える・欄を変える処理が要りそうになる | 足さない。NEEDS_DECISION: で返す |
| Mac で試験を回したくなる | 回さない。クラウドで流す |
| 手順の番号（§5 の 1〜12）と設計 §6 の番号がずれる | ずれは §13-8 と §13-9 で決めた並べ替え。カードの §5 の順に作る |
| 本物の組の命令に `=` が入っていて `--old-json` が perm-change に拒まれる | 試験では起きない。本物で起きたら `INSTALL_OK_RECORD_INCOMPLETE` になり、Opus が PO に報告する（この便では直さない） |

## 10. 触らない

- `~/.claude` の全部と `~/.salesanchor-tools`、agent-console
- `scripts/dev/` の全部（consent-audit.py・perm-change.py・permission-delegation-tests.py）
- `scripts/agent-hooks/` の、§2 の3ファイルのほかの全部（mac-test-guard の guard.py・test_guard.py・install.sh・rollback.sh、review-gate、confidential-quote-guard、cloud、master-register-rules-guard.py、test_master_register_rules_guard.sh）
- `.github/workflows/` の agent-hooks-test.yml のほかの全部
- `.claude/agents/`・`.claude/settings*.json`

## 11. 終わりの報告

- `DONE`／`BLOCKED: 理由`／`NEEDS_DECISION: 問い` のどれかで始める
- 停止したときは、その場で手を止める。止まった手順・命令・生の出力を返す。自分で回り道を作らない
- 報告に入れるもの:
  - push した HEAD（40桁）と `git log --oneline -3` の生の出力
  - §8 の8つの検索の生の出力
- 推測で埋めない。読めなかった出力は「読めなかった」と書く

## 12. 反映の後（Opus と PO が行う。担当はしない）

- マージ前: 新しく起動した opus の審査役の APPROVE（ADR-1029）。GO 記録（ADR-136・委任 GO）。
- マージの後、Opus が PO に知らせてから、PO が `!` で次の2つを行う:
  1. 自動判定の例外 HKI-1 の追加（文は設計 §6 のとおり）
  2. `~/.salesanchor-tools` を main に揃えた後、`bash ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh mac-test-guard` の初回の実行（`NO_CHANGE`・`RECORDED=0`・`INSTALL_OK` を期待。設計 §6）
- その後、受入条件 A6（AI が見張りごとの install.sh・rollback.sh・`CLAUDE_DIR=` 付き・引数2つの台本を流すと止まる）を Opus が1回ずつ試し、keep に残す。
- マージの後の最初の週次点検では、`guard_installer` が空から1件に増えて出る。これは PO の「1」（`consent:` の記録）で説明する（設計 §13-3）。Opus が点検の結果と一緒に PO に聞く。

END OF CARD
