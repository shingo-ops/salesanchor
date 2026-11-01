# 確かめが赤いままの合流を見張りで止める 実装カード（第2版）

> この文書は何か（専門用語なしの1行）:
> AI が PR を本線に入れる命令を出したとき、salesanchor の確かめが 1 つでも緑でなければ、見張りがその命令を止めるようにする作業の指示書。

- 根拠の写し: S=origin/main fbee46fce811822e20265566a2de51307f189190（Merge #4980）。行番号はすべてこの sha。実装の前に最新の origin/main で行を合わせ直す（§6 の分岐1）。
- 対象の決まり: ADR-1029（このカードの書類 PR で What 7 を追補）。
- 状態: 第2版（第1版の設計審査 REQUEST_CHANGES の指摘（１）試験の流し方・（３）件数の書き違いを直した）。設計審査は第2版でやり直す。
- 設計: docs/handoff/merge-red-check-guard/design.md。下調べ: docs/handoff/merge-red-check-guard/recon.md。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・sleep しない・報告に無い出力を成功と扱わない | ○（§7・§13） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4・§13） |
| guards/04-worktree.md | 作業場所は scripts/new-worktree.sh で作り、作った後に枝の名前と先頭を確かめる | ○（§7 手順1） |
| guards/05-pr.md | commit・push の各段で実在を確かめる。PR はクラウドでは作らない（コード変更を含む枝のため） | ○（§12） |
| scripts/agent-hooks/cloud/rules.md | クラウドは push まで・PR は手元で shingo-cc 名義・`.claude-pipeline/active-work.d/` は commit しない・reset/rebase/force/merge/pull を使わない | ○（§7・§12・§13） |

あなたは Sales Anchor の実装役（Sonnet）です。このカードだけを実行し、push までします。PR は作りません。最初に `scripts/agent-hooks/cloud/rules.md` を読み、従ってください。

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 確かめが赤いままの合流を見張りで止める（第2版）の実行結果である」と書くこと。
- 種類: AI の見張りの台本と、その試験だけ（scripts/agent-hooks/review-gate/ 配下の 2 ファイル）。本番のコード・migration・CI・deploy には触れない。

## 1. 目的と、PO から見える変化
- 今: 見張りは「Opus の審査の合格の記録があるか」だけを見る。確かめ（CI）が赤くても、直接の合流の命令なら本線に入る。10/31 に 22 件が赤のまま入った（recon §1）。
- 後: salesanchor の PR では、確かめが 1 つでも緑（pass・skipping）でなければ、見張りが合流の命令を止める。止める文に緑でない確かめの名前が出る。
- 別のリポジトリ（作業画面アプリ・kb）は今のまま。

## 2. 現在地（実測。S で測った）
- scripts/agent-hooks/review-gate/gate.py:47-50 に止める文 HEAD_MSG。:439-455 に gh_view。:458-491 に resolve。:487-490 が --auto の照合、:491 が allow の記録。
- scripts/agent-hooks/review-gate/test_review_gate.sh:36-48 が偽の gh（`pr view` だけ答え、ほかは exit 1）。:64-67 に mk_rec（o__r の記録だけ作る）。:70-76 に expect。:179 に `FAKE_URL_REPO=x/z expect_rec …` の書き方（関数の前の一時代入）。:297 の `# ---…--- install -> rollback で元に戻る` の行が往復の試験の始まり。
- `gh pr checks N --repo OWNER/REPO --json name,bucket` の返り: `[{"name":"…","bucket":"pass"},…]`。bucket は pass・fail・pending・skipping・cancel。走り中でも終了コード 0（recon §4）。

## 3. 直し方（選んだ案と理由）
- resolve で、APPROVE 記録と --auto の照合が通った後、allow の記録の前に、salesanchor の PR だけ確かめの一覧を読む。pass・skipping 以外が 1 つでもあれば止める。一覧が読めない・空・JSON でないときも止める。終了コードは見ない。
- 理由は design.md §1・§2。

## 4. 変更前後（実装の担当はこの形どおりに書く）

### 4-1. gate.py: 定数と止める文を足す（:47-50 の HEAD_MSG の直後、空行 2 つの前）

変更前: :47 から始まる `HEAD_MSG = (` の 4 行（:50 の `"別のリポジトリの PR なら、行の末尾に「 repo %s/%s」を足させてください。")` で終わる）。

変更後（その 4 行はそのまま。:50 の直後に次を足す）:
```python
# ADR-1029 What 7: このリポジトリの PR は、確かめ（CI）が全部緑でなければ合流を止める
STRICT_CHECK_REPOS = {"shingo-ops/salesanchor"}
CHECK_OK_BUCKETS = {"pass", "skipping"}
CHECKS_MSG = ("review-gate: PR #%s の確かめ（CI）に緑でないものがあります: %s。"
              "必須でない確かめも含め、全部が pass か skipping になるまで待つか直してから、"
              "もう一度合流してください。")
CHECKS_READ_MSG = ("review-gate: PR #%s の確かめ（CI）の一覧を gh で読めないため止めます"
                   "（一覧が空・gh の失敗・JSON でない。再実行してください）。")
```

### 4-2. gate.py: 関数 gh_checks を足す（:455 の gh_view の終わりと :458 の def resolve の間）

変更後（gh_view の `        return None` の後の空行 2 つの後に、次と空行 2 つを足す）:
```python
def gh_checks(n, owner, repo, wd):
    """[(name, bucket), ...] を返す。読めない・空・形が違うときは None。終了コードは見ない。"""
    if not os.path.isdir(wd):
        return None
    cmd = [gh_path(), "pr", "checks", str(n), "--json", "name,bucket",
           "--repo", "%s/%s" % (owner, repo)]
    try:
        r = subprocess.run(cmd, cwd=wd, capture_output=True, text=True, timeout=60)
        j = json.loads(r.stdout)
        if not isinstance(j, list) or not j:
            return None
        return [(str(x["name"]), str(x["bucket"])) for x in j]
    except Exception:
        return None
```

### 4-3. gate.py: resolve に判定を足す（:487-491）

変更前: :487 の `        if c["auto"] and c["match_head"] != head:` から始まる 4 行（--auto の照合。:490 の `% (c["n"], head[:9]), pr=c["n"], head=head, kind=c["kind"])` で終わる）。その次の :491 が次の行。
```python
        log({"decision": "allow", "pr": c["n"], "head": head, "kind": c["kind"]})
```

変更後: :487-490 の 4 行と :491 の log の行はそのまま。:490 と :491 の間に次の 7 行を足す。足した後の並びは「--auto の照合の 4 行 → 次の 7 行 → log の行」。
```python
        if ("%s/%s" % (owner, repo)).lower() in STRICT_CHECK_REPOS:
            ck = gh_checks(c["n"], owner, repo, c["wd"])
            if ck is None:
                deny(CHECKS_READ_MSG % c["n"], pr=c["n"], head=head, kind=c["kind"])
            bad = ["%s(%s)" % (name, bucket) for name, bucket in ck if bucket not in CHECK_OK_BUCKETS]
            if bad:
                deny(CHECKS_MSG % (c["n"], "、".join(bad)), pr=c["n"], head=head, kind=c["kind"])
```

### 4-4. gate.py: 先頭の説明（:5-7）に 1 行足す

変更前（:7）:
```python
 (c) PR のマージ操作は、今の HEAD に reviewer(opus) の APPROVE 記録が無ければ止める (R1-R3)
```
変更後（:7 はそのまま。直後に次の 1 行）:
```python
 (d) shingo-ops/salesanchor の PR は、確かめ（CI）が全部 pass/skipping でなければ止める (ADR-1029 What 7)
```

### 4-5. test_review_gate.sh: 偽の gh に `pr checks` を足す（:36-48）

変更前（:37-48 の一部）:
```bash
# 偽 gh: pr view だけ答える。head は $FAKE_HEAD_FILE。$FAKE_GH_FAIL があれば失敗する。
[ -n "${FAKE_GH_FAIL:-}" ] && exit 1
if [ "$1" = "pr" ] && [ "$2" = "view" ]; then
```
変更後:
```bash
# 偽 gh: pr view と pr checks だけ答える。head は $FAKE_HEAD_FILE。$FAKE_GH_FAIL があれば失敗する。
# pr checks は --repo が無ければ失敗し、あれば $FAKE_CHECKS_JSON（無ければ pass 1 件）を出して $FAKE_CHECKS_RC で終わる。
[ -n "${FAKE_GH_FAIL:-}" ] && exit 1
if [ "$1" = "pr" ] && [ "$2" = "checks" ]; then
  repo=""; prev=""
  for a in "$@"; do [ "$prev" = "--repo" ] && repo="$a"; prev="$a"; done
  [ -z "$repo" ] && exit 1
  if [ -n "${FAKE_CHECKS_JSON:-}" ]; then printf '%s\n' "$FAKE_CHECKS_JSON"; else echo '[{"name":"t","bucket":"pass"}]'; fi
  exit "${FAKE_CHECKS_RC:-0}"
fi
if [ "$1" = "pr" ] && [ "$2" = "view" ]; then
```
（`pr view` の分岐と、最後の `exit 1`・`EOF` はそのまま。）

### 4-6. test_review_gate.sh: 試験を足す（:297 の `# ---…--- install -> rollback で元に戻る` の行の直前に、次と空行 1 つ）

```bash
# ---------------------------------------------------------------- What 7: salesanchor は確かめが全部緑でなければ止める
mk_rec_sa() { # N SHA
  mkdir -p "$GD/records"
  printf '{"pr":%s,"repo":"shingo-ops/salesanchor","head":"%s","verdict":"APPROVE"}' "$1" "$2" > "$GD/records/shingo-ops__salesanchor-$1-$2.json"
}
clear_records; echo "$SHA1" > "$FAKE_HEAD_FILE"; mk_rec 1 "$SHA1"; mk_rec_sa 1 "$SHA1"
SA=shingo-ops/salesanchor
CK_OK='[{"name":"lint","bucket":"pass"},{"name":"e2e","bucket":"skipping"}]'
CK_FAIL='[{"name":"lint","bucket":"pass"},{"name":"test-schema-dup gate","bucket":"fail"}]'
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON=$CK_OK expect "C1 salesanchor 全部 pass/skipping なら通る" 0 'gh pr merge 1 --merge'
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON=$CK_FAIL expect "C2 salesanchor fail が 1 つで止める" 2 'gh pr merge 1 --merge' "$WORK" 'test-schema-dup gate(fail)'
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON=$CK_FAIL FAKE_CHECKS_RC=1 expect "C2b fail で gh が終了コード 1 でも止める" 2 'gh pr merge 1 --merge' "$WORK" 'test-schema-dup gate(fail)'
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON='[{"name":"build","bucket":"pending"}]' expect "C3 salesanchor pending で止める" 2 'gh pr merge 1 --merge' "$WORK" 'build(pending)'
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON='[{"name":"build","bucket":"cancel"}]' expect "C4 salesanchor cancel で止める" 2 'gh pr merge 1 --merge' "$WORK" 'build(cancel)'
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON='[]' expect "C5 salesanchor 一覧が空で止める" 2 'gh pr merge 1 --merge' "$WORK" '一覧を gh で読めない'
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON='no checks reported' FAKE_CHECKS_RC=1 expect "C6 salesanchor JSON でない出力で止める" 2 'gh pr merge 1 --merge' "$WORK" '一覧を gh で読めない'
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON='[{"name":"x","bucket":"weird"}]' expect "C6b salesanchor 知らない bucket で止める" 2 'gh pr merge 1 --merge' "$WORK" 'x(weird)'
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON=$CK_FAIL expect "C7 --auto --match-head-commit 一致でも fail なら止める" 2 "gh pr merge 1 --auto --merge --match-head-commit $SHA1" "$WORK" 'test-schema-dup gate(fail)'
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON=$CK_FAIL expect "C8 gh-pr-merge-safe.sh でも fail なら止める" 2 'bash scripts/gh-pr-merge-safe.sh --merge' "$GITWT" 'test-schema-dup gate(fail)'
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON=$CK_OK expect "C8b gh-pr-merge-safe.sh で全部緑なら通る" 0 'bash scripts/gh-pr-merge-safe.sh --merge' "$GITWT"
FAKE_CHECKS_JSON=$CK_FAIL expect "C9 別のリポジトリ o/r は fail でも今までどおり通る" 0 'gh pr merge 1 --merge'
clear_records
FAKE_URL_REPO=$SA FAKE_CHECKS_JSON=$CK_OK expect "C10 salesanchor 全部緑でも APPROVE が無ければ審査の文で止める" 2 'gh pr merge 1 --merge' "$WORK" 'APPROVE がありません'
```

## 5. 触らない範囲
- scripts/agent-hooks/review-gate/ の record.py・install.sh・rollback.sh。
- gate.py の §4-1〜§4-4 以外の行。test_review_gate.sh の §4-5・§4-6 以外の行（既存の試験は 1 行も変えない）。
- docs/adr/ 配下（ADR-1029 の追補は書類 PR で Opus が行う）。.github/ 配下。backend・frontend・migrations。
- ~/.claude/ 配下（本物の見張りへの反映は合流の後に PO が行う）。

## 6. 想定の分岐（実物を見て違えば止める）
- 分岐1: 最新の origin/main で §2 の行が動いていたら、文字列の一致で場所を合わせ直す。変更前の文字列そのものが無いときは止めて Opus へ。
- 分岐2: 既存の試験が 1 件でも FAIL になったら、直さず止めて Opus へ（既存の試験を書き換えて通さない）。
- 分岐3: 足した試験 C1〜C10 のどれかが FAIL のとき、gate.py が §4 と 1 文字ずつ同じかを確かめる。同じなのに FAIL なら、直さず止めて Opus へ。
- 分岐4: 試験の台本の実行で python3 が無い・git が無いなどで動かないときは、止めずに「未測定」と報告に書いて手順を続ける（確かめは CI の agent-hooks-test に任せる）。

## 7. 手順（実行役）
手順1 作業場所を new-worktree.sh で作る（new-worktree.sh の出力はパイプに通さない）
    cd "$(git rev-parse --show-toplevel)" && git fetch origin main
    cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/merge-red-check-guard-impl 2>&1
    cd "$(git rev-parse --show-toplevel)" && ls -1d "$HOME/worktrees/salesanchor/release-merge-red-check-guard-impl" && git worktree list
    cd "$HOME/worktrees/salesanchor/release-merge-red-check-guard-impl" && git branch --show-current && git log --oneline -1 && git rev-parse origin/main
    期待する出力: ls -1d と git worktree list の両方にその道が出る。道が salesanchor 以外のフォルダ名の下にできたら、以後の cd をその道に読み替えず BLOCKED: で止まる。枝は release/merge-red-check-guard-impl。先頭は origin/main と同じ sha。作業場所が作れなければ BLOCKED: で止まる
手順2 直す前の試験を流す（基準値）
    cd "$HOME/worktrees/salesanchor/release-merge-red-check-guard-impl" && bash scripts/agent-hooks/review-gate/test_review_gate.sh > /tmp/rg-base.out 2>&1; tail -n 5 /tmp/rg-base.out
    注意: 試験は 1 回に約 130 秒かかる。手順2・手順4 の試験の命令は、Bash の timeout を 300000 にして流す。試験は 1 回だけ流し、結果はファイルから読む。
    期待する出力: 最後の行が「PASS n / FAIL 0」。n を記録する。FAIL が 1 以上なら止めて Opus へ。動かなければ分岐4
手順3 §4 のとおりに 2 つのファイルを Edit ツールで直す（ほかのファイルは作らない・直さない）
手順4 直した後の試験を流し、commit する
    cd "$HOME/worktrees/salesanchor/release-merge-red-check-guard-impl" && python3 -m py_compile scripts/agent-hooks/review-gate/gate.py && echo COMPILE_OK
    cd "$HOME/worktrees/salesanchor/release-merge-red-check-guard-impl" && bash scripts/agent-hooks/review-gate/test_review_gate.sh > /tmp/rg-after.out 2>&1; grep -E "^(FAIL|PASS: C)" /tmp/rg-after.out; tail -n 1 /tmp/rg-after.out
    cd "$HOME/worktrees/salesanchor/release-merge-red-check-guard-impl" && git diff --name-only
    cd "$HOME/worktrees/salesanchor/release-merge-red-check-guard-impl" && git add scripts/agent-hooks/review-gate/gate.py scripts/agent-hooks/review-gate/test_review_gate.sh
    cd "$HOME/worktrees/salesanchor/release-merge-red-check-guard-impl" && git commit -m "feat: block merges in review-gate when salesanchor PR checks are not all green" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" 2>&1 | tail -n 20
    cd "$HOME/worktrees/salesanchor/release-merge-red-check-guard-impl" && git log -1 --oneline && git diff --name-only origin/main...HEAD
    期待する出力: COMPILE_OK。FAIL の行が無く、PASS: C1〜C10（C2b・C6b・C8b を含む 13 行）が出る。最後の行が「PASS m / FAIL 0」で m = n + 13。変わったファイルは gate.py と test_review_gate.sh の 2 つだけ。違えば分岐2・分岐3
手順5 push して、push した先頭を確かめる（PR は作らない）
    cd "$HOME/worktrees/salesanchor/release-merge-red-check-guard-impl" && git push -u origin release/merge-red-check-guard-impl 2>&1 | tail -n 30
    cd "$HOME/worktrees/salesanchor/release-merge-red-check-guard-impl" && git fetch origin release/merge-red-check-guard-impl && git rev-parse HEAD && git rev-parse origin/release/merge-red-check-guard-impl
    期待する出力: 2 つの sha が同じ。push が断られたら（提出前の入口の × を含む）、直さず BLOCKED: で止まり、出力を報告する

## 8. 受入基準

| 基準 | 検証方法 |
|---|---|
| salesanchor で緑でない確かめがあると止まる | 手順4 の試験 C2・C2b・C3・C4・C6b・C7・C8 が PASS |
| 一覧が読めないと止まる | 試験 C5・C6 が PASS |
| 全部緑なら通る | 試験 C1・C8b が PASS |
| 審査の記録が無いときは今までどおり審査の文で止まる | 試験 C10 が PASS |
| ほかのリポジトリは変わらない | 試験 C9 が PASS。既存の試験が全部 PASS（m = n + 13・FAIL 0） |
| CI の確かめが緑 | PR の agent-hooks-test（.github/workflows/agent-hooks-test.yml:25）が success（Opus が確かめる） |
| 触る範囲が守られる | `git diff --name-only origin/main...HEAD` が gate.py と test_review_gate.sh の 2 つだけ |
| 本物の見張りで効く | 合流の後、PO が `!` で install.sh を実行し、その出力の試験が FAIL 0（install.sh:77 が写した先で試験を流す。Opus が確かめる） |

## 9. 弊害・戻し方・維持
- 弊害: design.md §5 のとおり（本線が赤い間は関係のない PR も AI は合流できない・gh の呼び出しが 1 回増える）。
- 戻し方: この PR を revert し、PO が install.sh を `!` でもう一度流す。急ぐときは rollback.sh で見張りごと外す。本番には触れない。
- 測り方: §8 の表。導入後 30 日の KPI は design.md §4。
- 維持: test_review_gate.sh を CI（agent-hooks-test）が scripts/agent-hooks/** の変更のたびに流す。決まりの正本は ADR-1029 What 7。

## 10. 外部事例
- 不要。理由: 新しい技術の選択が無く、既存の見張りと正規の合流の道（check-pr-merge-ready.py:100-101）の基準をそろえるだけのため。

## 11. 接触面
- 人: 無し（PO の画面は変わらない。AI の合流の命令が止まることがあるだけ）。
- 機械: AI の見張り（合流の後、PO が反映してから効く）と CI の試験。
- データ・本番・外部: 非接触。

## 12. commit・push・PR
- commit は手順4、push は手順5 で行う。push の後に手順5 の 2 つの sha が同じことで実在を確かめる。
- 実行役は PR を作らない（コード変更を含む枝はクラウドでは push まで・scripts/agent-hooks/cloud/rules.md）。PR は Opus が手元で shingo-cc 名義・scripts/gh-pr-create-safe.sh で作る。
- `.claude-pipeline/active-work.d/` の登録ファイルは commit しない（new-worktree.sh が自分で登録する）。
- reset・rebase・force・merge・pull・`--no-verify` は使わない。

## 13. 報告と委任の定型
- 完了報告の本文に: 冒頭の受領文／手順1・2・4 の出力／§8 の各行の結果／push した枝の名前と、push 後に確かめた先頭の sha／判断を要した点（事実のみ）。
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文。
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか。
- sleep しない（CI の待ちは Opus が行う）。
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- このカードに書いていないファイル・行は触らない。

END OF CARD
