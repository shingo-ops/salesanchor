# 証拠 便M3（card-maintain-m3.md §5）

実装コミット: aca42d68f0d8906cac2f36fbcf02dd9a6462bc3b（枝の起点 e238cbfedba2fe18c39b049b8080df421d608737）

## §0 P1〜P6 の生出力
```
$ P1
ls: cannot access 'scripts/dev/doc-entry-weekly-check.sh': No such file or directory
ls: cannot access 'scripts/dev/test_doc_entry_weekly_check.sh': No such file or directory
$ P2
6:## 基準時点
16:## K8 守られた回数
73:## K9 会話の始まりに読む量
92:## K10 目次を開いた割合
98:## K12 必要な手順書まで開いた割合
135:## 手順（変更後に同じ条件で測る）
141:## 変更後（段3c マージ後、2026-10-24 測定）
179:## 原因調べ（目次を開かない理由を分ける、2026-10-25）
197:## 入口の案内を強めた後の測り直し（2026-10-25）
221:## 段7 の後の測り直し（2026-10-25）
233:## 段8 の後の測り直し（2026-10-26）
245:## 全条件の測り直し（2026-10-26）
$ P3
- check-claude-size.js のエラー文（「ファイル名は必ず CLAUDE.md」）と LIMITS は段3c で本 ADR に合わせて直す。
- 手順を読むのに1〜3回ファイルを開く手間が増える。開いた割合は design KGI-10 で記録する。
- 戻し方: 各段の PR を revert する（design §8 の戻し方の列）。

## 強制の仕組み

| 仕組み | 担当 | 効果 |
|---|---|---|
| 行数検査 CI | .github/workflows/check-claude-size.yml・frontend/scripts/check-claude-size.js | 入口が上限を超えたら失敗（段2a・段3c で対象と上限を直す） |
| 到達検査 CI | .github/workflows/doc-index-reachability.yml（job「doc index reachability」）・scripts/ci/check_doc_index.py | 目次から届かない文書・深さ・「いつ読むか」空欄・壊れたリンク・入口の安全の決まりの欠け（K7）・同じ決まりの重複（K3）を数え、1件でもあれば失敗（`--strict`）。必須チェックではない（登録は PO の操作。design §32 M4） |
| 登録の見張りの試験 CI | .github/workflows/agent-hooks-test.yml（job「master-register guard test」）・scripts/agent-hooks/test_master_register_rules_guard.sh | 商品登録の見張り（K2）の試験を、見張り・試験・登録の決まり（docs/specs/product-master/registration-rules.md）が変わる PR で動かし、1件でも FAIL なら失敗。必須チェックではない |
| 設計持ち込みの検査 | .github/workflows/process-artifacts-gate.yml | PR に recon・design・対象 ADR の記載を求める |

## 維持の仕組み

- 守り手は上の表の4つ（行数検査 CI・到達検査 CI・登録の見張りの試験 CI・設計持ち込みの検査）。到達検査は pull_request・main への push・毎週月曜に動く。
- K11 は続けて測らない（design §32 D5 の理由: 入口から決まりを移すたびの照合で足りるため）。今後また入口から決まりを移すときは、その段の設計に K11 の照合を書く。
- リポジトリ外の点検と K12 の時期は design §32 D3・D4 で作る予定（M3。まだ無い）。
$ P4

## 運用方針

- 1段＝1PR。変えたら測って、次の段へ進む（design §8）。
- 安全の決まりは目次の奥へ移さない（K7）。
- 合否は PO が上の表の「判定の見方」の出力で判断する。
- 合格後の点検: design.md §32。
$ P5
- リポジトリ外（CI が見えない）の守り手（段7で新設案・PO の実装承認待ち）: ~/kb/scripts/patrol.sh（毎週月曜 09:00 に Discord 通知。今の点検4項目は recon2 c11）に「会話開始時に自動で読まれるユーザー側ファイルの合計行数」を1項目足す
$ P6
scripts/agent-hooks/master-register-rules-guard.py
/usr/local/bin/python3
```

## §2-3 試験の全出力（bash scripts/dev/test_doc_entry_weekly_check.sh; echo rc=$?）
```
PASS T1 K1=24
PASS T1 b.md を数えない
PASS T1 K2_COPY=SAME
PASS T1 K9=skipped
PASS T1 DOC_INDEX_CI=success
PASS T1 K12_LAST
PASS T1 K12_DUE=no
PASS T1 K12_OPEN_PR=none
PASS T1 PEER_LAST
PASS T1 RESULT=OK
PASS T1 rc=0
PASS T2 K1=214
PASS T2 RESULT=NG K1>200
PASS T2 rc=1
PASS T3 K2_COPY=DIFF
PASS T3 RESULT=NG
PASS T4 K12_DUE=yes
PASS T4 RESULT=OK
PASS T5 K12_LAST=2026-11-01
PASS T5 K12_DUE=yes
PASS T6 K12_DUE=no
PASS T7 DOC_INDEX_CI=failure
PASS T7 RESULT=NG
PASS T8 DOC_INDEX_CI=pending
PASS T8 RESULT=OK
PASS T9 PEER_LAST=2027-01-24
PASS T9 RESULT=NG
PASS T10 RESULT=OK
PASS T11 PEER_LAST=2027-01-24
PASS T11 RESULT=NG
PASS T12 K12_OPEN_PR=URL
PASS T12 RESULT=OK
PASS T13 K12_OPEN_PR=none
PASS T14 K1_MISSING
PASS T14 RESULT=NG
PASS T15 DOC_INDEX_CI=unreadable
PASS T15 K12_OPEN_PR=unreadable
PASS T15 RESULT=NG
PASS 38 / FAIL 0
rc=0
```

## §2-4 構文検査と shellcheck
```
$ bash -n scripts/dev/doc-entry-weekly-check.sh scripts/dev/test_doc_entry_weekly_check.sh; echo rc=$?
rc=0
shellcheck なし（command -v shellcheck が空）
```

## §2-6 到達検査（python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?）
```
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=0 safety_missing=0 agents_import_missing=0 warnings=0
MAX_DEPTH_TERMINAL 3
rc=0
```

## §3 基本の形の偽の環境で1回だけ手で動かした出力（DOC_ENTRY_SKIP_K9=1・TODAY=2027-01-31）
偽の環境の置き場は作業用の一時ディレクトリ。K1_FILES の後ろ2本は偽の REPO の絶対パス。
```
K1=24
K1_FILES=~/.claude/CLAUDE.md,~/kb/AGENTS.md,~/.claude/rules/common/a.md,/tmp/claude-0/-home-user-salesanchor/b4b68e1d-561b-5923-9112-aa406cf18cf9/scratchpad/manual/repo/CLAUDE.md,/tmp/claude-0/-home-user-salesanchor/b4b68e1d-561b-5923-9112-aa406cf18cf9/scratchpad/manual/repo/AGENTS.md
K1_MISSING=none
K2_COPY=SAME
K9=skipped
DOC_INDEX_CI=success
K12_LAST=2027-01-01
K12_DUE=no
K12_OPEN_PR=none
PEER_LAST=2027-01-31
RESULT=OK
rc=0
```

## 補足
- 実装の途中で、`~` の置き換えがシェルに展開され K1_FILES が `/root/...` になる不具合を見つけ、1-1 の `disp` と 1-2 の T14 の期待（引用符付き）を直してから上の出力を取り直した。期待の値（カードの値）は変えていない。
- 本物の ~/.claude を使う実行（32-6 (b)）はクラウドでは行っていない（マージ後に Opus）。
