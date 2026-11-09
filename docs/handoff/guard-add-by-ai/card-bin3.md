# 実装カード 便3: 自動判定の例外 HKI-1 を PO の `!` で足す・外す台本（ADR-1072）

- 版: 第2版（2026-11-10。クラウド審査1回目 APPROVE の推奨1〜3を取り込み。design.md §13-13）
- 設計: docs/handoff/guard-add-by-ai/design.md §6・§6-1・§13-13
- PO の決定: 2026-11-10 の返事「1」（「前回と同じ形の専用の台本を作る」を選んだ）。ADR-1072 と実装開始は 2026-11-09 の「1」
- 基準: origin/main 96a63df05a23c0250e7a0550ca7399e1ddb4b01a
- 担当: クラウドの Sonnet（実装・試験）。Opus は審査・マージ・PO への案内
- 担当が行わないこと: マージ、~/.claude と ~/.salesanchor-tools に触ること、HKI-1 を本物の settings.json に足すこと、install-guard.sh を本物の HOME で流すこと

## 0. 実物の確かめ（基準の版で、担当は最初にこの表と同じことを確かめる。1行でも違えば NEEDS_DECISION: で止まる）

| 場所 | 中身（行頭） |
|---|---|
| `docs/handoff/permission-delegation/po_delegation_edit.py:15` | `HEADING = "### 4-6."` |
| `docs/handoff/permission-delegation/po_delegation_edit.py:16` | `QUOTE_START = "> PDL-1:"` |
| `docs/handoff/permission-delegation/po_delegation_edit.py:34` | `    if len(sys.argv) != 5 or sys.argv[1] not in ("register", "unregister"):` |
| `docs/handoff/permission-delegation/po-register-delegation.sh:51` | `if ! (cd ~/.salesanchor-tools && python3 -I -B scripts/dev/perm-change.py record --target user-automode-allow --op add --item-hash "${HASH}" --po-ref "${PO_REF}" --actor po-script); then` |
| `docs/handoff/permission-delegation/po-unregister-delegation.sh:51` | 上と同じで `--op remove` |
| `scripts/dev/consent-audit.py:753` | `PO_BANG_OP_PREFIXES = (` |
| `scripts/dev/consent-audit.py:754` | `    "bash ~/.salesanchor-tools/docs/handoff/permission-delegation/po-register-delegation.sh ",` |
| `scripts/dev/consent-audit.py:756` | `    "bash ~/CC報告ファイル-keep/permission-delegation/po-apply-",` |
| `scripts/dev/consent-audit.py:817` | `            if n == k3 and op.startswith(PO_BANG_OP_PREFIXES):` |
| `scripts/dev/permission-delegation-tests.py:790` | `A20_OP = "bash ~/.salesanchor-tools/docs/handoff/permission-delegation/po-register-delegation.sh consent:KEY"` |
| `scripts/dev/permission-delegation-tests.py:1738` | `        for fn in (test_a1, ...`（main の試験の並び。ここに test_g18 を足す） |

- この PR の design.md（Opus が先に commit 済み）で、`docs/handoff/guard-add-by-ai/design.md` の `### 6-1.` の節に `> HKI-1:` で始まる行が行頭に1つだけあり、その行の `> ` の後ろの文の `item_sha8` が `203789ba`（733字）であることを確かめる。違えば止まる。

## 1. 目的
- ADR-1072 の HKI-1 を、PO が `!` で1回だけ足す。足すときは PDL-1 と同じ形にする（控え→足す→読み直す→台帳に `record --po-ref consent:<鍵>`）。
- その記録が週次点検で B に出ないよう、点検が PO の `!` の台本として数える命令の頭に、新しい2本を足す。
- 外す台本も同時に用意する（design.md §8 の戻し方）。

## 2. 触るファイル（これ以外は触らない）
1. `docs/handoff/permission-delegation/po_delegation_edit.py`（変える）
2. `docs/handoff/guard-add-by-ai/po-register-hki.sh`（新規）
3. `docs/handoff/guard-add-by-ai/po-unregister-hki.sh`（新規）
4. `scripts/dev/consent-audit.py`（変える。753〜757 行の組に2行足すだけ）
5. `scripts/dev/permission-delegation-tests.py`（変える。試験を足す）
6. `.claude-pipeline/active-work.d/release-guard-add-by-ai-bin3.md`（台帳。Opus が作成済み）

触らないもの: `docs/handoff/permission-delegation/po-register-delegation.sh`・`po-unregister-delegation.sh`・`design.md`（どちらのフォルダの design.md も担当は触らない）、`scripts/dev/perm-change.py`、`scripts/agent-hooks/` の全部、`.github/`。

## 3. po_delegation_edit.py の変更（規則は1か所のまま。PDL-1 の動きは変えない）
- 引数を「4つ」または「6つ」にする。6つのときの5番目は見出しの頭（例 `### 6-1.`）、6番目はラベル（例 `HKI-1`）。
  - 4つのとき: 見出し `### 4-6.`、ラベル `PDL-1`（今と同じ）。
  - 5番目は `^### [0-9]+(-[0-9]+)*\.$` に完全一致（re.fullmatch）しなければ止まる（`### ` だけ・`### 6` のように、ほかの節まで対象になる値を通さない）。6番目は `^[A-Z]{2,5}-[0-9]{1,3}$` に合わなければ止まる。どちらも exit 2 で、settings.json を読む前に止まる。
  - それ以外の数の引数は今と同じ usage を出して exit 2。usage の文は `register|unregister <settings.json> <design.md> <consent-audit.py> [<見出し> <ラベル>]` にする。
- `read_statement` の探し方は今のまま（行頭が `### ` の行で節を切り替え、節の中で行頭が `> <ラベル>:` の行を集め、1件でなければ止まる）。見出しとラベルを引数で受けるだけにする。字下げした行は今と同じく数えない。
- 出力の文の `PDL-1` を、ラベルに置き換える（4つの引数のときの出力は、今と1文字も変わらない）。止まるときの文の `§4-6` は、見出しの文字から `### ` を除いた部分（例 `4-6.`・`6-1.`）に置き換え、`design.md <その部分> に <ラベル> の文が %d 件ある（1件のはず）。変更しない。` にする。【4つの引数のときこの1文だけは今の文 `design.md §4-6 に PDL-1 の文が…` と変わる。試験 G18-1 はこの文を見ない】
- そのほか（足す位置は末尾・同じ文があれば足さない・外すのはその文だけ・一時ファイルと os.replace・読み直し・`CHANGED=`・`HASH=`）は変えない。

## 4. 新しい台本 2本（docs/handoff/guard-add-by-ai/）
- `po-register-hki.sh` は `docs/handoff/permission-delegation/po-register-delegation.sh` を写し、次だけを変える。
  - 2行目の説明: `# PO 用: 見張りを足す共通の台本（install-guard.sh）を Opus が通せるようにする例外の文 HKI-1 を 足す（ADR-1072・design.md §6-1）。`
  - `DESIGN="${HERE}/design.md"` はそのまま（guard-add-by-ai の design.md を指す）。
  - `AUDIT="${HERE}/../../../scripts/dev/consent-audit.py"` はそのまま。
  - `EDIT="${HERE}/../permission-delegation/po_delegation_edit.py"` を足し、python の呼び出しを `python3 -I -B "${EDIT}" register "${SETTINGS}" "${DESIGN}" "${AUDIT}" "### 6-1." "HKI-1"` にする。
  - record の行（:51）は今と同じ（`--target user-automode-allow --op add ... --actor po-script`）。
- `po-unregister-hki.sh` は `po-unregister-delegation.sh` を写し、上と同じ変更をする（`unregister`・`--op remove`・説明の「外す」）。
- 2本とも実行権（0755）を付ける。`set -euo pipefail`・`GIT_NO_REPLACE_OBJECTS=1`・consent: の確かめ・控え・失敗のとき控えから戻す・SKIP_RECORD は、写し元と同じにする。

## 5. consent-audit.py の変更
`PO_BANG_OP_PREFIXES`（:753〜757）の組の末尾に次の2行を足す。ほかは触らない。
```
    "bash ~/.salesanchor-tools/docs/handoff/guard-add-by-ai/po-register-hki.sh ",
    "bash ~/.salesanchor-tools/docs/handoff/guard-add-by-ai/po-unregister-hki.sh ",
```

## 6. 試験（scripts/dev/permission-delegation-tests.py に足す。番号は G18 と A20-ok4〜5・A20-n21）
共通: 一時のフォルダに settings.json を作る（`{"autoMode": {"allow": ["Bash(echo x)"]}}`）。リポジトリの本物の `docs/handoff/permission-delegation/design.md` と `docs/handoff/guard-add-by-ai/design.md` を読む。台本の試験では、一時の HOME に `~/.salesanchor-tools/scripts/dev/perm-change.py` の偽物（受けた引数を `<HOME>/record-calls.jsonl` に1行の JSON で足し、環境変数 `FAKE_RC` の値（無ければ 0）で終わる）を置く。台本は `env={"HOME": <一時の HOME>, "PATH": os.environ["PATH"]}` で `bash <リポジトリの台本> <鍵> <一時の settings.json>` として流す。本物の ~/.claude と ~/.salesanchor-tools には触らない。
- G18-7〜G18-11 は、番号ごとに別の一時フォルダ（settings.json と HOME の両方）を使う（控えの名前は秒単位なので、同じフォルダだと同じ秒に上書きされ `.bak-` の数がずれる）。
- 各番号の chk は1回だけ呼ぶ（1つの番号で複数の条件を見るときも、全部満たせば PASS の1回）。

| 番号 | 準備 | 期待 |
|---|---|---|
| G18-1 | 引数4つで register | exit 0。出力に `added: PDL-1 を末尾に1件追加した`・`CHANGED=yes`。allow の最後が PDL-1 の文、最初の要素はそのまま。`HASH=` が その文の item_sha8 |
| G18-2 | 引数6つ（`### 6-1.` `HKI-1`・guard-add-by-ai の design.md）で register | exit 0。`added: HKI-1 を末尾に1件追加した`・`CHANGED=yes`。allow の最後の文の item_sha8 が `203789ba`。`HASH=203789ba` |
| G18-3 | G18-2 の後にもう一度 register | exit 0。`no change: 同じ文が既にある`・`CHANGED=no`。allow の件数が同じ |
| G18-4 | PDL-1 と HKI-1 の両方を足した後、HKI-1 を unregister | exit 0。`removed: HKI-1 だけを外した`。PDL-1 と `Bash(echo x)` は残り、順も同じ |
| G18-5 | `> HKI-1:` の行が §6-1 に2つある一時の design.md で register | 0 以外で終わる。settings.json のバイト列が前と同じ |
| G18-6 | 5番目が `## 6.`／5番目が `### `／5番目が `### 6`／6番目が `hki-1`／引数5つ、の5通り | どれも exit 2。settings.json のバイト列が前と同じ。chk は1回だけ呼ぶ（5通りすべて満たせば PASS） |
| G18-7 | po-register-hki.sh を鍵 `x` で流す | exit 1。settings.json のバイト列が前と同じ。`.bak-` のファイルが無い。record の呼び出し0回 |
| G18-8 | po-register-hki.sh を鍵 `consent:KEY` で流す | exit 0。`.bak-` のファイルが1つ。record の呼び出し1回で、引数が `record --target user-automode-allow --op add --item-hash 203789ba --po-ref consent:KEY --actor po-script` |
| G18-9 | G18-8 と同じで `FAKE_RC=1` | exit 1。settings.json のバイト列が流す前と同じ（控えから戻った） |
| G18-10 | HKI-1 を足した settings.json に po-unregister-hki.sh を鍵 `consent:KEY` で流す | exit 0。HKI-1 が無い。record の呼び出し1回で `--op remove --item-hash 203789ba` |
| G18-11 | もう一度 po-register-hki.sh（既に HKI-1 がある） | exit 0。`record: 変更が無かったので台帳には書きません`。record の呼び出し0回 |
| A20-ok4 | 既存の a20_case で、操作の行を `bash ~/.salesanchor-tools/docs/handoff/guard-add-by-ai/po-register-hki.sh consent:KEY` にする | B の理由が無い |
| A20-ok5 | 同じく `.../guard-add-by-ai/po-unregister-hki.sh consent:KEY` | B の理由が無い |
| A20-n21 | 同じく `bash ~/.salesanchor-tools/docs/handoff/guard-add-by-ai/other.sh consent:KEY` | B（`user:permissions.deny` と item_hash） |

- `main()` の並びの末尾に `test_g18` を足す。A20 の3件は `test_a20` の中に足す。
- 終わりに、試験の全体を `python3 -I -B scripts/dev/permission-delegation-tests.py` で流し、`PASS=<n> FAIL=0` を確かめる。変える前の数（基準の版で流した PASS の数）も記録する。差は G18 の11件と A20 の3件で、ちょうど 14 増えるはず。違えば止まる。

## 7. 止まる条件（NEEDS_DECISION: で止まり、Opus に返す）
- §0 の表と実物が1行でも違う。
- G18-1 で、4つの引数の出力が今の出力と違う（今の出力は基準の版で同じ準備で流して取る）。
- 試験の PASS の増え方が 14 でない。既存の試験が1つでも FAIL になる。
- §2 に無いファイルを触りたくなった。

## 8. 想定する分かれ道
| 起きること | どうするか |
|---|---|
| `bash` の台本の中の `cd ~/.salesanchor-tools` が一時の HOME で解けない | HOME を env で渡しているので解ける。解けないなら止まる（台本の形を変えない） |
| 試験で `python3 -I` が一時の偽物の perm-change.py を読めない | 偽物は `-I` でも動く単独のファイルにする（import は標準だけ） |
| design.md の §6-1 を担当が直したくなる | 触らない。止まる |

## 9. 提出
- commit は §2 のファイルだけ。commit の文は英語で、末尾に `Co-Authored-By: Claude Sonnet` の行を付ける。
- push は `release/guard-add-by-ai-bin3` に1回。PR は作らない（Opus が作る）。
- 返す報告: 最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` のどれか。変える前と後の PASS/FAIL の数、§0 の確かめの結果、push した HEAD を書く。生の出力はそのまま貼る。
