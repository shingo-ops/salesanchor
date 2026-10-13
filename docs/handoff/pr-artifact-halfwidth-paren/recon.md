# recon: PR本文の半角かっこ注記をファイル名から外す

## 事実

- scripts/check-process-artifacts.js:266 は「触るファイル:」欄の各行を整形する処理で、注記の除去が全角かっこのみ（正規表現 /（[^）]*）/g）。
- scripts/check-process-artifacts.js:274 は「削除するファイル:」欄の各行を整形する処理で、同じく全角かっこのみ。
- そのため「- migrations/x.sql (22行削除)」のように半角かっこの注記を付けると、注記が残ってパスとして読めず、検査が失敗する。
- 同ファイル内で全角かっこだけを除去する処理は上記2か所のみ（grep -n で他に該当なし）。
- parseSOPDeclaration は scripts/check-process-artifacts.js:248 にあり、module.exports（:975 以降）で公開済み。

## 既存テスト

- scripts/tests/test-process-artifacts.js が parseSOPDeclaration を直接呼ぶ単体テストを持つ（実行: node scripts/tests/test-process-artifacts.js）。変更前 121 PASS。
- 呼び出し元: scripts/dev/validate-pr-body.sh, scripts/dev/check-pr-merge-ready.py, scripts/sop-health-collector.js, .github/workflows/process-artifacts-gate.yml ほか（git grep -l check-process-artifacts で確認）。

## 旧 PR #3557 との関係

- #3557 は古い main の1か所だけを同じ正規表現に直していた（docs/handoff/pr-parser-parenthesis-fix/ に recon・design があるが main には未収載）。
- 現在の main は2か所とも未修正のため、今の main を元に2か所とも直す本PRで置き換える。本PRが通ったあと #3557 を閉じる（PO 承認済み 2026-10-13）。

## 既存 ADR の検索

git grep -il process-artifacts docs/adr/ の結果:

docs/adr/ADR-1003-go-delegation-to-opus.md
docs/adr/ADR-121-sop-process-artifacts-gate.md
docs/adr/ADR-124-sop-health-reporter.md
docs/adr/ADR-129-audit-log-coverage-medium.md
docs/adr/ADR-129-github-actions-node-version-tracking.md
docs/adr/ADR-134-design-site-delivery.md
docs/adr/ADR-135-release-stowaway-prevention.md
docs/adr/ADR-136-cc-bot-github-identity.md
docs/adr/FEATURE-INDEX.md
docs/adr/README.md

本件は ADR-121 のゲートの解析の不具合修正であり、方針の変更を伴わない。
