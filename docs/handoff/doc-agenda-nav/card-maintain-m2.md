# 実装カード 便M2: 商品登録の見張りの試験を CI で動かす（design.md §32 D2・32-4 M2）

- 設計: docs/handoff/doc-agenda-nav/design.md §32（審査6回目 APPROVE on d2f244d70・PR #4797）。PO 実装承認 2026-10-26（PO 原文「1」）。
- 枝: release/doc-agenda-nav-maintain-m2（M1 #4799 マージ後の origin/main 起点）。1便＝1PR。push まで。PR は手元（Opus）が作る。
- 発行: Opus（設計担当）2026-10-26。

## 0. 先に確かめること（実物点検。合わなければ止めて報告）

| # | 確かめる事実 | 期待 |
|---|---|---|
| P1 | .github/workflows/agent-hooks-test.yml 全文 | job は `review-gate`（name「review-gate hook test」）の1つだけ。paths は `scripts/agent-hooks/**`・`.github/workflows/agent-hooks-test.yml`・`.claude/agents/reviewer.md` の3つ |
| P2 | `bash scripts/agent-hooks/test_master_register_rules_guard.sh; echo rc=$?`（クラウドの Linux で） | PASS 28件・FAIL 0・rc=0（PASS の行数は `grep -c ^PASS` で数える） |
| P3 | `grep -n "到達検査 CI\|設計持ち込みの検査" docs/adr/ADR-1040-doc-agenda-nav-entry-index.md` と「## 維持の仕組み」の最初の行 | 「強制の仕組み」表に3行（行数検査 CI・到達検査 CI・設計持ち込みの検査）。維持の仕組みの1行目が「守り手は上の表の3つ（…）」 |
| P4 | docs/specs/product-master/registration-rules.md が在るか | 在る |

P1〜P4 の生出力は §4 の証拠ファイルに貼る。
P2 で FAIL があれば: 原因を調べる。試験側の環境差（パス・python の版・GNU と BSD のコマンドの差）なら §1-1 と同じコミットで試験スクリプトを直してよい（直した行と理由を証拠に書く）。見張り本体 scripts/agent-hooks/master-register-rules-guard.py の判定が変わる直しが要るなら、作らずに止めて `NEEDS_DECISION:` で報告する。

## 1. 変更（この範囲だけ）

### 1-1 workflow に job を足す（.github/workflows/agent-hooks-test.yml）
- `on.pull_request.paths` の最後に `- 'docs/specs/product-master/registration-rules.md'` を1行足す（見張り本体は既存の `scripts/agent-hooks/**` に入っているので足さない）。
- 冒頭のコメントの1行目を「# scripts/agent-hooks/ の受入試験（review-gate: ADR-1029・商品登録の見張り: doc-agenda-nav design §32 D2）。」に直す。他のコメント行は変えない。
- `jobs:` の最後に次の job を足す（review-gate job と同じ形）:
```yaml
  master-register-guard:
    name: master-register guard test
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v5
      - name: Run master-register guard tests
        run: bash scripts/agent-hooks/test_master_register_rules_guard.sh
```
- 試験スクリプトが失敗のとき rc≠0 で終わるか確かめる（末尾の `exit` の行）。rc を返さない作りなら、作らずに止めて報告する。

### 1-2 ADR-1040（docs/adr/ADR-1040-doc-agenda-nav-entry-index.md）
- 「## 強制の仕組み」表の「到達検査 CI」の行の後に1行足す:
  `| 登録の見張りの試験 CI | .github/workflows/agent-hooks-test.yml（job「master-register guard test」）・scripts/agent-hooks/test_master_register_rules_guard.sh | 商品登録の見張り（K2）の試験を、見張り・試験・登録の決まり（docs/specs/product-master/registration-rules.md）が変わる PR で動かし、1件でも FAIL なら失敗。必須チェックではない |`
- 「## 維持の仕組み」の1行目の「守り手は上の表の3つ（行数検査 CI・到達検査 CI・設計持ち込みの検査）。」を「守り手は上の表の4つ（行数検査 CI・到達検査 CI・登録の見張りの試験 CI・設計持ち込みの検査）。」に直す。他の文は変えない。
- `node scripts/generate-adr-index.js` を実行し、docs/adr/README.md に差分が出たら同じコミットに入れる。

### 1-3 触らない範囲
- scripts/agent-hooks/master-register-rules-guard.py（見張り本体）・review-gate job・他の workflow・設計書 design.md・kgi.md。
- 必須チェック（Ruleset）への登録はしない。

## 2. 作る順
1. `./scripts/dev/executor-preflight.sh || exit 1`
2. §0 を実行して証拠に貼る。
3. §1-1・§1-2 を1コミット（`ci: run master-register guard test in agent-hooks-test (ADR-1040 M2)`）。
4. `python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?` が rc=0 であること（rc≠0 なら commit しない・止めて報告）。
5. 証拠ファイルを別コミットにして push。

## 3. CI 上の失敗→成功の確認（32-6「試験を1本わざと壊したコミットで失敗」）
- push の後、job「master-register guard test」が success になったのを確かめる（`gh run list --workflow agent-hooks-test.yml --branch release/doc-agenda-nav-maintain-m2`。結果が出るまで待つ。15分で出なければその時点の状態を書いて止める）。
  - ※ PR がまだ無いと pull_request で動かない。PR が無い間は Opus が PR を作るまで待つ必要があるので、この §3 は PR 作成後に Opus が別の依頼で頼む。最初の依頼では §2 の5まで。
- 壊すコミット V5: 試験スクリプトの `# T1` の2行下（`echo "$O" | grep -q '"permissionDecision": "deny"' && …; check "T1 deny+全文" $?` の行）の `"permissionDecision": "deny"` だけを `"permissionDecision": "denyX"` に変える（他の T の行は触らない）（試験の1件だけが FAIL になる変更。見張り本体は触らない）。commit・push し、job が failure になり、ログに `FAIL T1` があることを確かめる。
- 戻すコミット: `git revert --no-edit <V5>` で戻して push し、success を確かめる。最後に `git diff <§2-3 のコミット> HEAD -- . ':!docs/handoff'` が空であること。
- 各実行の URL と結論の行を証拠ファイルに足して push。

## 4. 証拠ファイル
- docs/handoff/doc-agenda-nav/evidence-maintain-m2.md（新規）。§0 の生出力・§2-4 の rc・§3 の実行 URL と結論の行。要約しない。

## 5. 報告
- 最後の行は `DONE <HEAD の sha40>`・`BLOCKED: <理由>`・`NEEDS_DECISION: <内容>` のどれか。
