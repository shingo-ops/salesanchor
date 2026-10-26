# 実装カード 便M1: 目次の検査を「落とす」検査にする（design.md §32 D1・32-4 M1）

- 設計: docs/handoff/doc-agenda-nav/design.md §32（審査6回目 APPROVE on d2f244d70・PR #4797）。PO 実装承認 2026-10-26（PO 原文「1」）。
- 枝: release/doc-agenda-nav-maintain-m1（origin/main ee7204104 起点）。1便＝1PR。push まで。PR は手元（Opus）が作る。
- 発行: Opus（設計担当）2026-10-26。

## 0. 先に確かめること（実物点検。合わなければ止めて報告）

| # | 確かめる事実 | 期待 |
|---|---|---|
| P1 | `grep -rn check_doc_index .github scripts frontend/scripts` | 呼び出し元は .github/workflows/doc-index-reachability.yml:26 の1か所だけ |
| P2 | docs/handoff/doc-agenda-nav/check_doc_index.py の行数・:4・:206-210 | 215行。:4 が使い方の行。:206 が SUMMARY、:209 が `if a.strict and warnings >= 1:` |
| P3 | AGENTS.md:15・:23・:32 | 「## 不可逆操作は必ず PO 確認」「## VPS 直作業禁止（…）」「…への直接コミット禁止…」 |
| P4 | CLAUDE.md:3・frontend/CLAUDE.md:3・backend/CLAUDE.md:3 | 3つとも 「@AGENTS.md」 の1行 |
| P5 | 9語（下の §1-2）を6ファイルで `grep -nF` | 2ファイル以上に出るのは「日本語」だけ。出現は frontend/AGENTS.md:23・:24・:31 と backend/AGENTS.md:66 の4行だけ |
| P6 | `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root . --strict; echo rc=$?` | rc=0（今の main は合格） |

P1〜P6 の生出力は §5 の証拠ファイルに貼る。P5 で「日本語」以外の語が2ファイル以上に出たら、作らずに止めて報告する（`NEEDS_DECISION:`）。

## 1. 変更（この範囲だけ）

### 1-1 スクリプトを移す
- `git mv docs/handoff/doc-agenda-nav/check_doc_index.py scripts/ci/check_doc_index.py`。元の場所には何も残さない。
- 冒頭の説明 :2 を「目次 docs/INDEX.md から手順書が届くか、入口の安全の決まりと重複を数える検査（--strict で 1件でもあれば失敗。CI は --strict で動かす）。」に、:4 を `使い方: python3 -I scripts/ci/check_doc_index.py --root . [--strict]` に直す。
- 過去のカード・設計書の中の旧パスは記録なので直さない。

### 1-2 K3（同じ決まりの重複）の検査を足す
- スクリプトの先頭（定数の並び。:15-26 の近く）に次の2つを置く（正本はここ1か所）。
  - `DUP_FILES = ["CLAUDE.md", "AGENTS.md", "frontend/AGENTS.md", "backend/AGENTS.md", "frontend/CLAUDE.md", "backend/CLAUDE.md"]`
  - `DUP_WORDS = ["i18n", "ハードコード", "不可逆", "推測", "executor-preflight", "squash", "worktree", "日本語", "file:line"]`（design.md:444 の K3 の9語）
  - `DUP_EXCLUDE = [(ファイル, その行にある決まった文言, 理由), ...]`。理由は「design §25: 別の決まり（画面の文字の決まり）」「design §25: 別の決まり（説明を日本語で書く決まり）」のように書く。組は P5 で確かめた4行それぞれに1つ。文言は実物の行から写す（例: frontend/AGENTS.md「ハードコード日本語は絶対禁止」・「日本語ハードコード」・「コメント内の日本語は OK」、backend/AGENTS.md「日本語説明を書く」。実物と1字でも違えば実物に合わせる）。
- 数え方: 各ファイルを行ごとに見て、語が部分一致（大文字小文字を区別。grep -F 相当）する行を「出現」とする。出現が除外の組（同じファイル・その行に決まった文言を含む）に当たるかを記録する。
- 落とす決まり: ある語が2ファイル以上に出て、かつその出現のうち除外に当たらないものが1つでもあれば、その語を重複として数える。除外した行を先に取り除いてから数えるのではない。
- 出す行: 重複の語ごとに `DUP_WORD <語> <ファイル:行>,<ファイル:行>...`（除外に当たらない出現だけを並べる）。数を `dup_words`。

### 1-3 K7（入口の安全の決まり）の検査を足す
- 先頭に `SAFETY_PHRASES = ["不可逆操作は必ず PO 確認", "VPS 直作業禁止", "直接コミット禁止"]` と `IMPORT_FILES = ["CLAUDE.md", "frontend/CLAUDE.md", "backend/CLAUDE.md"]` を置く。
- AGENTS.md（ルート）に各文言が部分一致で1件以上あるか。無い文言ごとに `SAFETY_MISSING <文言>`。数を `safety_missing`。
- IMPORT_FILES の各ファイルに、前後の空白を除いて 「@AGENTS.md」 と一致する行が1件以上あるか。無いファイルごとに `AGENTS_IMPORT_MISSING <ファイル>`。数を `agents_import_missing`。

### 1-4 まとめの行と終わり方
- :206 の SUMMARY を `SUMMARY unreached=%d deep=%d blank_when=%d no_when_column=%d broken_link=%d dup_words=%d safety_missing=%d agents_import_missing=%d warnings=%d` にする。`warnings` は今の5つに新しい3つを足した合計。
- `--strict` で warnings が1以上なら exit 1（:209 の形のまま）。ファイルが読めないときの扱いは今の `read()` に合わせる（新しい例外の道を作らない）。

### 1-5 workflow（.github/workflows/doc-index-reachability.yml）
- `name: Doc Index Reachability`。冒頭コメントの「警告だけで失敗にはしない。失敗への昇格は段5…」を「--strict で動かし、1件でもあれば失敗する（design §32 D1）。必須チェックへの登録は PO の操作（design §32 M4）。」に直す。「paths を使わず常時実行する」の行は残す。
- `on:` に `push: branches: [main]` と `schedule: - cron: '0 0 * * 1'`（毎週月曜 09:00 日本時間）を足す。pull_request はそのまま。
- job 名を `doc index reachability` にする（「(warning only)」を外す）。
- 実行の行を次にする（失敗してもまとめの1行を残すため）:
  ```
  set +e
  python3 -I scripts/ci/check_doc_index.py --root . --strict | tee /tmp/doc-index.txt
  rc=${PIPESTATUS[0]}
  set -e
  echo "doc-index: $(grep '^SUMMARY' /tmp/doc-index.txt)" >> "$GITHUB_STEP_SUMMARY"
  exit "$rc"
  ```
  `set -o pipefail` の行は外してよい（rc を PIPESTATUS で取るため）。
- `workflow-lint.yml` には触らない。

### 1-6 文書（design.md §32-4 M1）
- docs/adr/ADR-1040-doc-agenda-nav-entry-index.md
  - :56「| 到達検査 CI | 段2で新設 | 目次から届かない文書を数える |」を「| 到達検査 CI | .github/workflows/doc-index-reachability.yml（job「doc index reachability」）・scripts/ci/check_doc_index.py | 目次から届かない文書・深さ・「いつ読むか」空欄・壊れたリンク・入口の安全の決まりの欠け（K7）・同じ決まりの重複（K3）を数え、1件でもあれば失敗（`--strict`）。必須チェックではない（登録は PO の操作。design §32 M4） |」にする。
  - 「## 強制の仕組み」の表の後に「## 維持の仕組み」の節を足す。中身（その時点の実物だけ）: 守り手は上の表の3つ（行数検査 CI・到達検査 CI・設計持ち込みの検査）。到達検査は pull_request・main への push・毎週月曜に動く。K11 は続けて測らない（design §32 D5 の理由を1行）。今後また入口から決まりを移すときは、その段の設計に K11 の照合を書く。リポジトリ外の点検と K12 の時期は design §32 D3・D4 で作る予定（M3。まだ無い）と書く。
- docs/handoff/doc-agenda-nav/design.md:326「- 追加予定の守り手（段2で新設、まだ存在しない）: …」の1行を「- 到達検査の守り手: .github/workflows/doc-index-reachability.yml（job「doc index reachability」）・scripts/ci/check_doc_index.py。`--strict` で失敗する。CLAUDE.md↔AGENTS.md の見出し重複は K3 の語の重複検査と行数検査で代えた。詳細と続きは §32」にする。:327（担当と数え方）・:328（リポジトリ外）は触らない（M3 で直す）。§32 本文は触らない。
- docs/STANDARD-WORKFLOW.md:75 の段落の次に空行を挟んで1行: 「新しい手順書・仕様書は docs/INDEX.md か docs/specs/README.md に『いつ読むか』付きで1行足す（CI『doc index reachability』で止まる）。」
- docs/specs/doc-agenda-nav/kgi.md の「## 運用方針」の最後の箇条の次に「- 合格後の点検: design.md §32。」を1行。
- `node scripts/generate-adr-index.js` を回し、差が出たら同じコミットに入れる。

### 触らない範囲
- 上の6ファイル（スクリプト・workflow・ADR-1040・design.md:326・STANDARD-WORKFLOW.md・kgi.md）と ADR の索引以外。特に AGENTS.md・CLAUDE.md 類・frontend/scripts/check-claude-size.js・workflow-lint.yml・Ruleset。
- 旧パス・「warning only」を含む過去の記録（card-*.md・design.md の §32 以外の経緯）。`grep -rn "warning only\|doc-agenda-nav/check_doc_index" docs .github` の結果は証拠ファイルに貼るだけで直さない。

## 2. 想定される分岐

| 起きたこと | どうする |
|---|---|
| P5 で「日本語」以外も2ファイル以上に出る | 作らずに止めて `NEEDS_DECISION:` |
| 実装後に今の main 相当で `--strict` が rc=1 | 出た行を証拠に貼り、除外の文言の写し違いなら直す。それ以外（新しい重複・壊れたリンク）は止めて `NEEDS_DECISION:` |
| 文書の直しで broken_link や unreached が増える | 自分の直しの書き方が原因なら直す。それ以外は止める |
| generate-adr-index.js が無関係な差を出す | 差をそのまま入れずに止めて報告 |
| 見張り（フック）に止められた | 言い換えて再試行しない。止められた操作と文面を報告して止める |

## 3. 手元での確かめ（クラウドの作業場所で。commit しない一時の変更）

実装を commit した後、次の4つを1つずつ「変える→`python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?`→`git checkout -- <ファイル>` で戻す→もう一度回す」で確かめ、生出力（SUMMARY 行と rc、出た DUP_WORD などの行）を証拠ファイルに貼る。

| # | 変えること | 期待（変えた後 → 戻した後） |
|---|---|---|
| V1 | docs/INDEX.md から手順書への1行を消す | unreached か broken_link が1以上・rc=1 → 全項目0・rc=0 |
| V2 | AGENTS.md:23 の見出しから「VPS 直作業禁止」の文字を消す | safety_missing=1・rc=1 → 0・rc=0 |
| V3 | AGENTS.md（ルート）の最後に「- i18n の決まりは frontend/AGENTS.md」を1行足す | dup_words=1（DUP_WORD i18n）・rc=1 → 0・rc=0 |
| V4 | AGENTS.md（ルート）の最後に「- 返事は日本語で書く」を1行足す | dup_words=1（DUP_WORD 日本語・AGENTS.md の行だけが並ぶ）・rc=1 → 0・rc=0 |

CI での同じ確かめ（PR 上で失敗→成功の実行を記録）は、PR ができた後に別の依頼で行う。今回はしない。

## 4. 受け入れ基準（今回の依頼の分）

| 基準 | 検証方法 |
|---|---|
| P1〜P6 が期待どおり | 証拠ファイルの生出力 |
| 実装後の最終 HEAD で全項目0 | `python3 -I scripts/ci/check_doc_index.py --root . --strict` の SUMMARY が全項目0・rc=0 |
| V1〜V4 が失敗→成功 | 証拠ファイルの生出力 |
| 旧パスが残っていない | `test ! -e docs/handoff/doc-agenda-nav/check_doc_index.py` と P1 の grep を実装後にもう一度（workflow は新パスだけ） |
| 触ったファイルが範囲どおり | `git diff --stat origin/main...HEAD` を証拠に貼る |

## 5. 証拠ファイルと報告

- 証拠は docs/handoff/doc-agenda-nav/evidence-maintain-m1.md に、コマンドと生出力をそのまま書いて同じ枝に commit する（要約で作らない）。
- commit は2つまで（実装と証拠）。メッセージの末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- push まで。PR は作らない。`.claude-pipeline/active-work.d/` は commit しない。
- 最後の返答の最終行は `DONE <HEAD の sha40>`、止めたなら `BLOCKED: <理由>` か `NEEDS_DECISION: <内容>`。
