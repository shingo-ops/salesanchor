# Phase 2 下調べ: 必須でない確かめが赤いままの合流を機械で止める

- 根拠の写し: S=origin/main fbee46fce811822e20265566a2de51307f189190（Merge #4980）。行番号はすべてこの sha。
- 調べた日時: 2026-11-01 17:30〜18:20 JST。生の出力は /tmp/CC報告ファイル/dup-guard/ に置いた（下の各行にファイル名）。
- 既存 ADR の検索: `git grep -i -E "review-gate|mergeStateStatus|merge-ready" docs/adr/` と docs/adr/FEATURE-INDEX.md。該当は ADR-1029（AI のマージをフックで止める）・ADR-121（試験の表の写し・test-schema-dup gate）・ADR-1011（hooks は AI がパッチ、PO が反映）。新しい ADR は作らず ADR-1029 に追補する。

## 1. 何が起きたか（事実）

- 2026-10-31 07:53 UTC の #4942 から 23:33 UTC の #4968 までに、`test-schema-dup gate` が赤のまま本線に入った PR が 22 件ある（merged-gate-status.txt）。うち shingo-cc 名義が 18 件、shingo-ops 名義（台帳の自動合流）が 4 件。
- 最初の 1 件 #4942（release/auth-audit-tenant-fix）が test_rls_auth_audit.py の写しを増やした。その後の 21 件は、本線が赤いので巻き込まれて赤になった。
- shingo-cc 名義の 18 件に自動合流の予約（auto_merge_enabled）は無い（merge-events.txt）。台帳の 4 件のうち確かめた 2 件（#4953・#4957）には予約がある。
- 正規の合流の道 scripts/gh-pr-merge-safe.sh は、赤のある PR を止める。実例: #4961 で `STOP: mergeStateStatus is not CLEAN: 'UNSTABLE'`（/tmp/CC報告ファイル/schema-dup/merge-out.txt）。止める行は scripts/dev/check-pr-merge-ready.py:100-101。
- 【推測（根拠つき）】18 件は gh-pr-merge-safe.sh を通らず、直接の合流の命令（`gh pr merge <番号> --merge` 等）で入った。根拠: 正規の道は UNSTABLE を止める（上の実例）・予約も無い・GitHub は必須でない赤では合流を断らない（§2）。【未確認】どの会話のどの命令だったか（会話の記録を Bash で読むことは見張りが止める）。設計はどの直接の命令でも止まる形にするので、この未確認は設計の結論を変えない。

## 2. 直接の合流が通る理由

- 見張り scripts/agent-hooks/review-gate/gate.py は、`gh pr merge` を含むすべての合流の命令を見つける（:310-328）。
- しかし通すかどうかは「今の HEAD に Opus 審査役の APPROVE 記録があるか」と「--auto なら --match-head-commit が同じか」だけで決める（resolve :458-491）。確かめ（CI）の色は見ない。
- 必須の確かめは GitHub 側（Ruleset）で止まるが、test-schema-dup gate は必須に入っていない（docs/specs/rule-enforcement/required-checks.txt の 16 件に無い・.github/workflows/test-schema-dup-gate.yml の説明にも「必須でない・Ruleset への追加は後で GO」とある）。

## 3. 確かめの信頼性（止めたとき誤りで止まらないか）

- test-schema-dup gate の最近 200 回: 成功 141・失敗 59（gate-runs-summary.txt）。
- 失敗 59 回はすべて 10/31 07:32〜11/1 01:37 UTC。直し #4967（10/31 23:52 UTC）の後の失敗は 4 回で、全部本物だった（after-fix-fail-logs.txt）: 2 回は直しより前の先頭で走ったもの、2 回は release/lead-regression-backend が本当に写しを 21 件増やしたもの（その枝は後で直して緑になった）。
- 直しの後、01:37 UTC 以降の 33 回は全部成功（after-fix-runs.txt）。誤って赤を出した回は 0 回。
- process-artifacts gate は、合流の後（PR を閉じたとき）にもう一度走って赤になることがある（#4932・#4939・#4942 は合流より後の時刻の失敗。stability.txt）。合流の時点の色ではない。

## 4. 確かめの色を読む方法

- `gh pr checks <番号> --repo <owner/repo> --json name,bucket`（gh 2.85.0）。同じ名前は最新の 1 件にまとめて返す（pr-checks-dedup.txt: #4962 の process-artifacts gate は fail と pass の 2 回あるが一覧は pass の 1 件）。
- bucket は pass・fail・pending・skipping・cancel の 5 つ（`gh pr checks --help` の 6-7 行目・ghchecks-help.txt）。
- `--json` 付きでは、走り中が残っていても終了コードは 0 だった（#4984: pending 3 件で rc=0・ghchecks-4984.json）。終了コードに頼らず中身で判定する。
- 全部緑の #4967 は 55 件（pass 44・skipping 11）（ghchecks-4967.json）。

## 5. ほかのリポジトリ

- 見張りはユーザー設定なので全リポジトリにかかる（ADR-1029 What 5）。
- 作業画面アプリ（GEN-RYU-System/agent-console）では、最近 25 件の合流のうち 8 件が `check (macos-latest)` 赤のまま入っている（ac-merged-red.txt）。全リポジトリにかけると、今の運用のあちらの合流が止まる。
- 今回の対象は salesanchor だけにする。あちらの赤の扱いは別の件として PO へ上げる（この件の範囲外）。

## 6. 見張りの入れ方と試験

- 入れ方: scripts/agent-hooks/review-gate/install.sh を PO が `!` で実行する（ADR-1029 の状態欄・ADR-1011:39）。gate.py を ~/.claude/scripts/review-gate/ に読み取り専用で写す（install.sh:15-21）。
- 試験: scripts/agent-hooks/review-gate/test_review_gate.sh（324 行・偽の gh は :36-49 で pr view だけ答える）。CI は .github/workflows/agent-hooks-test.yml:25 が流す。
- 既存の試験はリポジトリ名を o/r で走る（:42）。salesanchor だけにかける決まりなら、既存の試験は結果が変わらない。
