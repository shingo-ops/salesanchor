CARD-PMG-STAGE-CTA-02
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、05-pr.md、06-merge.md、09-gh.md。
照合: 1○記号、2○PR3467、3○原ログ、4○3カードCTA、5○main起点、6○GO受領、7○実出力確認。
受領確認: 「CARD-PMG-STAGE-CTA-02を受領」と返す。
PO本人原文「GO #3467」を受領済み。対象PR3467の通常マージ・本番反映を許可。
担当は既存pmg_cta_completion。rootは設計/公開HTTP検収。新agent禁止。
他者も作業中。他者の差分を巻き戻さず、scope外の変更は止めてrootへ報告。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-pmg-stage-card-actions。
承認時HEAD11970e3e、CI41成功/6対象外/GO未記録1件。製品差分検収APPROVE。
許可: 同テーマdesign/recon/card-stage-merge.md、tasks/evidence今回行の承認記録commit/push。
許可: PR3467本文へGO本人原文・発行者・記録日時・バックアップ確認を転記。本文はファイル経由。
許可: 最新main照合/通常統合、必要回帰、PR CI確認、公式merge script --merge、通常自動deployの読取監視。
禁止: 製品追加変更、DB変更、再解析、配信、CI/運用scripts/secrets変更、他PR操作。
禁止: GO創作、force/admin/auto、保護解除や別経路による迂回、main/develop直接push・削除。
既存の公開push承認も有効。今回GOの転記は委任AI名義ではなくPO本人原文。
新規CI失敗/対象差分の不明点/範囲外変更があれば該当操作を停止しrootへ報告。
最新HEADの全チェック終了・失敗0とmergeStateStatus=CLEANを確認して直ちに通常マージ。
merge scriptはworktree自動cleanupを行うため、先にreports全文を下記外部ログ先へ退避する。
許可ログ先: /tmp/CC報告ファイル/pmg-stage-card-actions/、親作業台reports/pmg-stage-card-actions-pr3467/。
root文書5ファイル以外を一括stageしない。reports/旧unfinishedをGitへ混入しない。
マージ後は本店でGitHub状態/mergeCommit/対応deployを読み取り。本店未保存差分は変更しない。
自動deployのbackup成功・配備HEAD・health結果を確認し、失敗時は推測で手動修正しない。
報告はcommit/CI/merge/deployを分け、終了code・ログ・未確認を保存する。

手順0: preflight
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-stage-card-actions && ./scripts/dev/executor-preflight.sh

手順1: 正式カード検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-stage-card-actions && bash scripts/card-lint.sh docs/handoff/pmg-import-delivery-ssot/card-stage-merge.md

手順2: 上記範囲でGO保存・commit/push・CI全成功確認。マージ直前CLEANとHEAD一致を確認。

手順3: 外部ログ先を作成して資料退避後、公式マージ
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-stage-card-actions && bash scripts/gh-pr-merge-safe.sh --merge >> /tmp/CC報告ファイル/pmg-stage-card-actions/merge-3467.txt 2>&1

手順4: 削除された作業台を使わず、本店からGitHubのmerge/deploy結果を読み取り報告する。

END OF CARD
