# CARD-LINE-GUIDE-15 — LINE業務ガイドの正式PR提出

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、05-pr.md、11-lint.md。
§5.5照合: 記号○、ready指定○、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
他者と共用中。他者変更を巻き戻さない。目的は検証済みガイドのready PRを公式入口で1件作ること。
前提: CARD14の3SHA一致、Astra最終レビューAPPROVE、本文完成の明示連絡後のみ実行。
本文path: /private/tmp/line-workflow-guide-resume-pr-body.md。
製品/文書編集・commit・push・GO原文作成・merge・本番操作は禁止。

文書保存の境界: executable例を含むカード保存コマンドがPR実行としてhookに拒否されたため、本カードは実行契約を以下の入力欄で示す。
実際のPR操作は別tool callで正規入口を文字どおり実行し、通常のhook/本文/HEAD/作者検査をすべて受ける。
文書保存をPR操作の成功や承認とみなさない。guard/trust設定は変更しない。

手順1: branch/HEADと14報告を確認し、本文ファイル実在・実差分の全path/行削除宣言一致を確認する。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-15.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/dev/validate-pr-body.sh < /private/tmp/line-workflow-guide-resume-pr-body.md
対象repo shingo-ops/salesanchor、head release/line-workflow-guide-resume、全stateの既存PRを読取確認する。
既存PRがあれば二重作成せずAstraへ報告して停止する。

手順2: guards/05-pr.mdに明記された唯一の正規PR作成wrapperを読み、次の固定入力で1回だけ実行する。
base: main
head: release/line-workflow-guide-resume
title: feat: LINE解析を7段階で読める業務手順ページを追加
body-file: /private/tmp/line-workflow-guide-resume-pr-body.md
ready PRとして作成する。直接CLI/APIで代替しない。実行コマンドは先頭cdとcwdを専用worktreeへ固定する。

手順3: .pr-numberと実PRの番号/HEAD/stateを読取照合する。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && cat .pr-number
番号一致・URL・HEAD・wrapper終了値をAstraへ報告し停止。CIと番号付き承認は別工程。
正規sandbox escalation可。実ガード拒否・本文不一致・作成結果不明は停止。
別経路作成/再送/skip/mock/GO代筆は禁止。

END OF CARD
