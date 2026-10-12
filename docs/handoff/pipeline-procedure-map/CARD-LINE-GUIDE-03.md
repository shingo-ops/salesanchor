# CARD-LINE-GUIDE-03 — スマートフォンの可視範囲確認

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を冒頭に示す。担当Sol、レビューAstra。
読んだ節: guards/00-common.md、01-read.md、03-file.md、11-lint.md（docs/handoff/design-partner-card-ops配下）。
§5.5照合: 記号○、ready指定○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
目的: fullPage画像で下部メニューが本文に重なって見える点を、実際の390x900可視範囲で確定する。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide
ブランチ: release/line-workflow-guide。設計は同ディレクトリdesign.mdの2026-09-28追補。
他者と共用中。既存変更を保持する。製品コード修正・共通MobileShell変更・commit/push/PR/merge/deployは禁止。

手順1 カード検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && bash scripts/card-lint.sh docs/handoff/pipeline-procedure-map/CARD-LINE-GUIDE-03.md

手順2 証跡取得

編集許可: frontend/tests-e2e/analysis-rules-line-guide.spec.ts のみ。
既存モック・2つの390px設定を再利用し、fullPage:falseで冒頭・手順1・手順7のviewport画像を追加取得する。
手順見出し/操作ボタンが実際のviewportで見え、メニューに覆われず操作可能なことを確認する。
ボタンのclick trial等で遮蔽を確かめる。書込操作は実行せず、画面遷移ボタンのactionability確認に限る。
証跡は既存 /tmp/reports/card-line-guide-01 内に保存する。
共通Shell由来の不具合が実在した場合は修正せず、再現条件と画像をAstraへ報告する。
E2Eは変更した390pxの2ケースのみ再実行。他のcheck/build/unitの繰返しは不要。
5173番に他worktreeのサーバーがないことを確認する。無関係プロセスは停止しない。
同一試験のlocalhost bind等に必要なrequire_escalatedの正規審査は許可。guard/trust/configは変更禁止。

手順3 報告
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && git diff --check

期待値: ja/enの390x900画面で冒頭・手順1・手順7の画像各1、操作ボタン遮蔽なし、横はみ出し0。
Astra宛に画像パス・試験結果・観測事実を報告し停止。報告だけで本番確認済みとしない。
新たな不明点・失敗・ガード拒否は停止して根拠を返し、迂回しない。

END OF CARD
