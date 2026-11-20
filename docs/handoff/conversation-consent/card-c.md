# 実装カード 便C: 同意の見張りの試験を GitHub で走らせる

正本: docs/handoff/conversation-consent/design.md §16-3(c)・§16-8 便C・K80。PO 実装承認 2026-11-20（設計 PR #5618 の報告への返事「1」。便C → 便A → 便B の順）。
ブランチ: release/consent-k0-bin-c（origin/main から新しく作る）。行番号は origin/main d4bea69c1 の値。

## 作業場所の作り方（クラウド）

1. `git fetch origin`
2. `bash scripts/new-worktree.sh release/consent-k0-bin-c`
3. 以後の作業はすべてこの worktree の中。clone のまま commit しない。

## 触るファイル（これ以外は触らない）

1. .github/workflows/agent-hooks-test.yml

触らない: scripts/dev/consent-audit.py、scripts/dev/consent-unit-tests.py、docs/handoff/conversation-consent/hooks/ の中身、他のワークフロー、~/.claude 配下すべて、ADR、design.md。

## 手順

### 1. paths に3行足す

変更前（:9-13）:

```yaml
    paths:
      - 'scripts/agent-hooks/**'
      - '.github/workflows/agent-hooks-test.yml'
      - '.claude/agents/reviewer.md'
      - 'docs/specs/product-master/registration-rules.md'
```

変更後:

```yaml
    paths:
      - 'scripts/agent-hooks/**'
      - '.github/workflows/agent-hooks-test.yml'
      - '.claude/agents/reviewer.md'
      - 'docs/specs/product-master/registration-rules.md'
      - 'scripts/dev/consent-audit.py'
      - 'scripts/dev/consent-unit-tests.py'
      - 'docs/handoff/conversation-consent/hooks/**'
```

### 2. 2行目の注記に1語足す

変更前（:3）: `# scripts/agent-hooks/ の受入試験（review-gate: ADR-1029・商品登録の見張り: doc-agenda-nav design §32 D2・mac-test-guard・install-guard・install-form-guard: ADR-1072）。`

変更後: `# scripts/agent-hooks/ の受入試験（review-gate: ADR-1029・商品登録の見張り: doc-agenda-nav design §32 D2・mac-test-guard・install-guard・install-form-guard: ADR-1072・同意の見張り: ADR-1033 conversation-consent design §16-3(c)）。`

### 3. ファイルの最後（go-comment-guard ジョブの後、:105 の次）に空行1つとジョブを1つ足す

```yaml

  consent-unit-tests:
    name: consent hook unit tests
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - name: Run consent hook unit tests and judge by output lines
        run: |
          # 試験の台本は FAIL でも終了コード 0 を返す（design §16-2(h)）。出力の行で判定する。
          judge_consent_out() {
            if grep -q '^FAIL' "$1"; then return 1; fi
            if ! grep -q '^PASS' "$1"; then return 1; fi
            if ! grep -qx 'DONE' "$1"; then return 1; fi
            return 0
          }
          # 手順1: 判定の関数そのものを作り物の出力4通りで確かめる（条件を1つだけ破る形）
          judge_selftest() {
            exp="$1"; shift
            printf '%s\n' "$@" > "$RUNNER_TEMP/judge-selftest.txt"
            if judge_consent_out "$RUNNER_TEMP/judge-selftest.txt"; then rc=0; else rc=$?; fi
            echo "SELFTEST expect=$exp got=$rc input=[$*]"
            if [ "$rc" != "$exp" ]; then
              echo "judge_consent_out self-test failed"
              exit 1
            fi
          }
          judge_selftest 1 'PASS a' 'FAIL b' 'DONE'
          judge_selftest 1 'DONE'
          judge_selftest 1 'PASS a'
          judge_selftest 0 'PASS a' 'DONE'
          # 手順2: 本物の試験を流す
          if python3 -I -B scripts/dev/consent-unit-tests.py docs/handoff/conversation-consent/hooks "$RUNNER_TEMP/consent" "$GITHUB_WORKSPACE" > "$RUNNER_TEMP/consent.out"; then prc=0; else prc=$?; fi
          # 手順3: 出力をそのまま表示する
          cat "$RUNNER_TEMP/consent.out"
          if [ "$prc" != "0" ]; then
            echo "consent-unit-tests.py exited with $prc"
            exit 1
          fi
          # 手順4: 本物の出力を判定する
          if judge_consent_out "$RUNNER_TEMP/consent.out"; then
            echo "consent unit tests: all PASS"
          else
            echo "consent unit tests: FAIL line found, or PASS/DONE missing"
            exit 1
          fi
```

- インデントは他のジョブと同じ2つ（ジョブ名）・4つ・6つ。タブは使わない。
- `continue-on-error` と `|| true` は書かない。

## 確かめ（クラウドで行う）

1. `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/agent-hooks-test.yml'))"` が例外なく終わる（yaml が無ければその旨を報告し、手順2へ）。
2. `git diff origin/main --stat` が `.github/workflows/agent-hooks-test.yml` の1ファイルだけ。
3. 手順3の `run:` の中身を `bash -e` で手元に写して流し、SELFTEST の4行が expect と got で一致し、最後に `consent unit tests: all PASS` が出る（GitHub の `$RUNNER_TEMP`・`$GITHUB_WORKSPACE` は一時フォルダと worktree の根に置き換える）。出力全文をファイルに残し、PASS・FAIL の行数を報告する。

## commit と push

- commit の文は Write でファイルに書き、`git commit -F <file>` で記録する。1 行目: `ci(consent): run consent hook unit tests on GitHub and judge by output lines`。最後の行: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git push -u origin release/consent-k0-bin-c`。PR は作らない（Opus が作る）。
- git の命令は1回に1つ。

## 想定される分かれ道

- 確かめ3で FAIL の行が出た（Linux と Mac の違いなど）→ 直さずに止め、FAIL の行の全文を添えて `BLOCKED:` で報告する。試験の台本・見張りは触らない。
- new-worktree.sh が失敗した → `BLOCKED:` で報告する。
- 変更前の行が上と違う（main が進んだ）→ 止めて `NEEDS_DECISION:` で違いを報告する。

## 報告

最後の文は `DONE:` / `BLOCKED:` / `NEEDS_DECISION:` のどれかで始め、commit の SHA・push の結果・確かめ1〜3の結果（SELFTEST 4行、PASS 行数、FAIL 行数）を書く。
