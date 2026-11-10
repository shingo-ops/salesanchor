# recon — 必須チェックの「まとめ役」が、変更の判定に失敗しても緑を出す件

- 調べた日: 2026-11-10（JST）。行番号は origin/main ae8def4d3。
- 調べた人: Claude Opus（設計担当）。読むだけ（ファイルを読む・GitHub の実行記録を読む）。CI の設定は変えていない。
- きっかけ: docs/handoff/soldout-ref-read-speed/design.md §11 の事後の点検で、「pytest のまとめ役は、変更の判定の結果を見ていない」と気づいた。PO が 2026-11-10 に「1」（この穴を塞ぐ設計を作る）を選んだ。
- 生出力（手元の写し）: /tmp/CC報告ファイル/ci-gate-hole/（各 yml の写し・scan_runs.jsonl・scan_runs.err）。

## 0. 既存 ADR・設計の検索

- `git grep -n "aggregator\|集約" origin/main -- docs/adr` は、この型を決めた ADR に当たらなかった（当たった 2 件は別の話）。
- この型の由来は Issue #523 / PR #534（paths の絞り込みがあると、必須チェックが「報告なし」のまま待ち続け、PR を合流できなくなった）。`.github/workflows/e2e.yml:30` と `.github/workflows/schema-check.yml:20-23` の説明に書いてある。
- この型を守る既存の検査: `.github/workflows/workflow-lint.yml:86-95`（migration-test.yml と e2e.yml に `has_aggregator_pattern`）と `:147-172`（`job.get("if") == "always()"` で needs を持つジョブがあるか、dorny/paths-filter を使うジョブがあるか）。この検査は「まとめ役が変更の判定の結果を見ているか」は見ない。この検査のファイルは PO だけが変えられる（CLAUDE.md「不可逆操作」、`.github/workflows/workflow-lint.yml:28-41` が自分の変更を止める）。
- 関係する決まり: ADR-135・ADR-136（必須チェックと危険なパス）・ADR-1047（決まり台帳）・docs/specs/rule-enforcement/README.md（決まりを機械の検査に変える取り組み）。

## 1. まとめ役の今の形（事実）

「まとめ役」= 名前が必須チェックと同じで、`if: always()` で必ず動き、実行役のジョブの結果を見て 0 か 1 で終わるジョブ。

| ワークフロー | まとめ役（必須チェック名） | 場所 | needs | 判定に使う結果 | 必須か |
|---|---|---|---|---|---|
| test.yml | pytest (SQLite + PostgreSQL RLS) | `.github/workflows/test.yml:263-280` | detect-changes, pytest-run, lint-backend | pytest-run, lint-backend | はい |
| e2e.yml | Lint & Dark Mode Check (ADR-067) | `.github/workflows/e2e.yml:126-145` | detect-changes, lint-run, unit-run | lint-run, unit-run | はい |
| migration-test.yml | マイグレーションSQL 実行テスト（実DB） | `.github/workflows/migration-test.yml:2130-2152` | detect-changes, registration-exists, registration-exists-regression, test-run, full-dryrun | 4 つの実行役 | はい |
| schema-check.yml | テナントスキーマ整合性チェック | `.github/workflows/schema-check.yml:222-238` | detect-changes, schema-check-run | schema-check-run | はい |
| e2e.yml | 画面検査（受信箱 3幅 Playwright） | `.github/workflows/e2e.yml:230-245` | detect-changes, visual-language-run | visual-language-run | いいえ |
| karte-gate.yml | Karte Visual Gate (chromium) | `.github/workflows/karte-gate.yml:121-137` | detect-changes, karte-gate-run | karte-gate-run | いいえ |

- 必須かどうかは `docs/specs/rule-enforcement/required-checks.txt:1-16` で確かめた（上の 4 つが入っている。下の 2 つは入っていない）。
- 6 つとも、判定の式は「実行役が success か skipped なら 0」。`needs.detect-changes.result`（変更の判定ジョブ自体の結果）と、その出力（true/false）は、どれも見ていない（各場所の run の中身を全部読んだ）。
- 実行役の動く条件は、どれも `needs.detect-changes.outputs.<名前> == 'true'`（`.github/workflows/test.yml:63`・`:118`、`.github/workflows/e2e.yml:64`・`:90`・`:156`、`.github/workflows/migration-test.yml:59`・`:94`・`:1388`、`.github/workflows/schema-check.yml:50`、`.github/workflows/karte-gate.yml:36`）。例外は migration-test.yml の registration-exists-regression で、条件も needs も無く毎回動く。
- 変更の判定のやり方: test.yml・e2e.yml・migration-test.yml・karte-gate.yml は dorny/paths-filter@v4。schema-check.yml は `git diff`（`.github/workflows/schema-check.yml:38-45`）。

## 2. 穴の仕組み（事実＝GitHub の公式文書とファイルの中身から）

- GitHub の公式文書（Context7 `/websites/github_en_actions`）: needs の result は success・failure・cancelled・skipped の 4 つ。「ジョブが失敗するか飛ばされると、それを needs に持つジョブは、条件の式が無い限り全部飛ばされる」。`always()` は依存の結果にかかわらず動き、取り消されたときも true を返す。
- だから、変更の判定ジョブが失敗する（checkout の失敗・paths-filter の失敗・git diff の失敗など）と、次のように進む:
  （１）実行役は needs の判定ジョブが失敗したので skipped になる。
  （２）まとめ役は `if: always()` なので動く。
  （３）まとめ役は「実行役が skipped なら 0」で終わる。必須チェックは緑になる。
  （４）その PR は、試験を 1 本も流していないのに、合流できる。
- 判定ジョブが成功しても、出力が 'true' でも 'false' でもない値（空など）なら、実行役の条件は偽になり、同じく skipped → 緑になる。

## 3. この穴に今まで当たったか（事実＝実行記録の数え上げ）

- 道具: scratchpad の scan_runs.py（読むだけ。各必須ワークフローの pull_request の直近 300 回の実行について、変更の判定ジョブの結論と、まとめ役の結論を数える）。
- 結果（scan_runs.jsonl）:
  - test.yml: 300 回（いちばん古いもの 2026-11-07T12:37:40Z）。判定ジョブが success でなかった回 0、そのときまとめ役が success だった回 0。
  - e2e.yml: 300 回（いちばん古いもの 2026-11-07T12:53:00Z）。判定ジョブが success でなかった回 1（run 42440529069・2026-11-08T02:55:18Z・判定ジョブ cancelled・まとめ役 failure・回全体 cancelled）、そのときまとめ役が success だった回 0。
  - migration-test.yml・schema-check.yml: 下の §3-1。
- 意味: 少なくとも直近の範囲では、この穴を通って緑になった PR は 0 件。穴は「起きたら気づけない」形で、まだ起きていない。

### 3-1. 残り 2 つの必須ワークフローの数え上げ

- migration-test.yml: 300 回（いちばん古いもの 2026-11-07T12:56:06Z）。判定ジョブが success でなかった回 0、そのときまとめ役が success だった回 0。
- schema-check.yml: 300 回（いちばん古いもの 2026-11-07T12:56:06Z）。判定ジョブが success でなかった回 0、そのときまとめ役が success だった回 0。
- 数え上げのエラー出力（scan_runs.err）は空だった。
- 必須でない 2 つ（e2e.yml の画面検査・karte-gate.yml）は数えていない。

## 4. 守る場所の候補（事実）

- workflow-lint.yml の has_aggregator_pattern は `job.get("if") == "always()"` を文字の一致で確かめる（`.github/workflows/workflow-lint.yml:150-156`）。まとめ役の `if:` を `!cancelled()` などに変えると、この検査が落ちる。この検査のファイルは PO だけが変えられる。だから、まとめ役の `if: always()` は変えず、run の中の判定の式を変える。
- 必須チェックの一覧を変える（Ruleset）のは PO だけ（CLAUDE.md「不可逆操作」）。だから、新しい検査は、すでに必須で毎回動くジョブの中の 1 つの段として足す。
- test.yml のまとめ役 `pytest` は毎回動き、必須チェック。今は checkout をしていない（`.github/workflows/test.yml:268-280` は run 1 つだけ）。
- test.yml の判定ジョブの対象（`.github/workflows/test.yml:39-51`）は backend/・migrations/・scripts/・test.yml・deploy.yml など。e2e.yml・schema-check.yml などワークフローの変更だけの PR では、pytest-run は動かない。だから、検査を pytest の試験として足すだけだと、ワークフローだけを変える PR で検査が走らない。
- 既存の scripts/ci の検査と試験の置き場: `scripts/ci/check_rule_registry.py` とその試験 `scripts/tests/test_check_rule_registry.py`（`.github/workflows/rule-registry.yml:32-33` で `python3 -I` で流す）。この型にそろえる。
- workflow-lint.yml は、GitHub の実行機に入っている python3 で `import yaml` を使っている（`.github/workflows/workflow-lint.yml:46-47`）。同じ実行機（ubuntu-latest）で PyYAML が使える実例。

## 5. まだ確かめていないこと

- 変更の判定ジョブが、実際にどのくらいの頻度で失敗するか（§3 の範囲外の期間）。
- 取り消された回（e2e.yml は `concurrency: cancel-in-progress: true`、`.github/workflows/e2e.yml:34-36`）で、まとめ役が何を出したか。設計では、取り消しで判定ジョブが success でない回は赤にする（設計 §3）。
