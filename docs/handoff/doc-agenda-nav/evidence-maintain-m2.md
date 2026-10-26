# 便M2 証拠（§3 は PR 作成後に別依頼）

- 実装コミット: aae1cddd31ff79041ad80be6e10640e36dca96c2
- 実行環境: クラウド Linux（preflight 不使用）

## P1 agent-hooks-test.yml（変更前の全文）
```
name: Agent Hooks Test

# scripts/agent-hooks/review-gate/ (ADR-1029) の受入試験。docs/handoff/review-gate-hook/design.md §5-1・§8。
# 偽の gh・一時ディレクトリだけを使う。本物の ~/.claude には触れない。
# ※ 必須チェック（Branch Protection）には登録しない。

on:
  pull_request:
    paths:
      - 'scripts/agent-hooks/**'
      - '.github/workflows/agent-hooks-test.yml'
      - '.claude/agents/reviewer.md'

jobs:
  review-gate:
    name: review-gate hook test
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v5
      - name: Run review-gate tests
        run: bash scripts/agent-hooks/review-gate/test_review_gate.sh
```

## P2 `bash scripts/agent-hooks/test_master_register_rules_guard.sh; echo rc=$?`
```
PASS T1 deny+全文
PASS T2 正しい印はallow(出力なし)
PASS T3 /backend/ は素通り
PASS T4 additionalContextに全文
PASS T5 古い印はdeny
PASS T6 grepは素通り
PASS T7 cat heredoc書き込みはdeny
PASS T8 grep+リダイレクトもdeny(許容する副作用)
PASS T9-15 出ない: 在庫表の商品名の列幅を直して。あとログイン登録画面のバグも見て
PASS T9-15 出ない: ユーザー登録フォームで商品一覧が出ない
PASS T9-15 出ない: マスタ画面の表示が遅い。GitHub に登録してあるワークフローも確認
PASS T9-15 出ない: Discord の webhook を登録して商品の通知を流す
PASS T9-15 出ない: マスタを整備して正答率を上げたい。登録はまだしない
PASS T9-15 出ない: 商品を登録して
PASS T9-15 出ない: PR を作って
PASS T16-18 出る: 商品マスタに新しいカードを登録して
PASS T16-18 出る: 共用マスタへ登録する候補一覧を出して
PASS T16-18 出る: 販売先を顧客マスタに登録して
PASS T19 記録置き場(keep)への Write は素通り
PASS T20 記録置き場(tmp)への Write は素通り
PASS T21 Bash の登録コマンドは止まる
PASS T22 リポジトリの外の docs は止まる
PASS T23 記録置き場の .py は止まる
PASS T24 作業場所の docs は素通り
PASS T25 .. で外へ出るパスは止まる
PASS T26 記録置き場(/private/tmp)への .md は素通り
PASS T27 絶対パスでないものは止まる
PASS T28 段の名前そのもの(下に何も無い)は止まる
rc=0
grep -c ^PASS = 28 / grep -c ^FAIL = 0
```
試験スクリプト末尾 `exit $FAIL`（FAIL 時は 1）。試験・見張り本体は未変更。

## P3 ADR-1040（変更前）
```
56:| 到達検査 CI | .github/workflows/doc-index-reachability.yml（job「doc index reachability」）・scripts/ci/check_doc_index.py | 目次から届かない文書・深さ・「いつ読むか」空欄・壊れたリンク・入口の安全の決まりの欠け（K7）・同じ決まりの重複（K3）を数え、1件でもあれば失敗（`--strict`）。必須チェックではない（登録は PO の操作。design §32 M4） |
57:| 設計持ち込みの検査 | .github/workflows/process-artifacts-gate.yml | PR に recon・design・対象 ADR の記載を求める |
61:- 守り手は上の表の3つ（行数検査 CI・到達検査 CI・設計持ち込みの検査）。到達検査は pull_request・main への push・毎週月曜に動く。
59:## 維持の仕組み
60-
61-- 守り手は上の表の3つ（行数検査 CI・到達検査 CI・設計持ち込みの検査）。到達検査は pull_request・main への push・毎週月曜に動く。
```

## P4
```
-rw-r--r-- 1 root root 11423 Oct 24 00:11 docs/specs/product-master/registration-rules.md
```

## §2-4 `python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?`
```
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=0 safety_missing=0 agents_import_missing=0 warnings=0
MAX_DEPTH_TERMINAL 3
rc=0
```

## generate-adr-index.js: README.md に差分なし

## §3 CI 上の失敗→成功（32-6）

- 壊したコミット V5: fe8a18143054ddd19dcf5e5b27a2b3268e9ea11c（試験 T1 の行の deny を denyX に。1行だけ）
- V5 の CI: https://github.com/shingo-ops/salesanchor/actions/runs/40346263580
  - job「master-register guard test」が failure（https://github.com/shingo-ops/salesanchor/actions/runs/40346263580/job/121653873698）。ログの FAIL 行は `FAIL T1 deny+全文` の1行だけ
  - job「review-gate hook test」は success
- 戻すコミット: 250d76f9130648b7dc9eb833b575905f4308fbe2
  - 手元試験 `bash scripts/agent-hooks/test_master_register_rules_guard.sh`: FAIL 行 0 件・rc=0（出力に集計行は無く、PASS T1〜T28 が並ぶ）
  - `git diff aae1cddd31ff79041ad80be6e10640e36dca96c2 HEAD -- . ':!docs/handoff'` は空だった
- 戻した後の CI の結果は Opus が PR コメントに記録する
