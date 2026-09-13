分類: 6-2
出所: （2026-07-24 PR #3068/#3070）

- カードの停止条件に「コマンドが非0終了したら停止」を一律で書かない。`gh pr checks` は exit 8 を「Checks pending」として返す（`gh pr checks --help` の Additional exit codes に明記）。停止条件は返り値でなく「判定に必要な値が揃ったか」で書く（2026-07-24 訓練Fで誤停止を実測）。
- カードの照合値に、時間で動く数字を固定で書かない。origin/main のSHAは実測出典であって将来の期待値ではない。訓練G発行時の 08750fe2 は実行前に PR #3069 のマージで 6459e9bb へ前進し、固定SHA照合が誤停止を招いた。位置の検証は `git merge-base --is-ancestor HEAD origin/main` 等の相対条件で書く（2026-07-24 実測）。

分類: 6-3
出所: （2026-07-24 PR #3068/#3070）

- ガードの効果は単独の結果では言えない。対照を取る。範囲内（§6-5）に1行=SEC6_ADDED=1・FAILURE・BLOCKED、範囲外（§7）に1行=SEC6_ADDED=0・SUCCESS・UNSTABLE。process-artifacts gate が赤という条件まで揃えたうえで結果が割れて初めて「そのガードが単独で止めた」と言える（2026-07-24 訓練F/Gで実測）。
- 合否条件は「緑になったか」でなく「どの経路で緑になったか」で書く。ラベル例外の実証は SEC6_ADDED=1 を保ったまま conclusion=success を条件にすることで、検知消滅による偽合格を排除できる（2026-07-24 訓練H・run 30042870942 で実測）。
- 実装役の報告が途中で切れても、成果物の実在（PR番号・コミットSHA・pending=0）で停止か完了かを判定する。訓練Gは報告が step6 途中で切れたが成果物は揃っており、作業のやり直しは不要だった（2026-07-24 実測）。

分類: 6-1
出所: （2026-07-24 PR #3068/#3070）

- マージ状態の語彙を混ぜない。BLOCKED=方針が禁止、UNSTABLE=必須外のチェックが赤、BEHIND=mainに遅れ、は別物。チェック未完了の段階でも BLOCKED は返るため、全チェック完了前の BLOCKED は阻止の証拠にならない（2026-07-24 訓練F初回採取・全QUEUEDで BLOCKED を実測）。
- 訓練用ダミーPRは必須チェックが全緑になり得るため、証拠採取の直後にクローズする。訓練G #3070 は必須チェック全緑・赤は必須外の process-artifacts gate のみで、mergeStateStatus=UNSTABLE＝マージ可能な状態だった（2026-07-24 実測）。
- 本店（worktree外）からの `git push origin --delete` は手元検問が拒否する。閉じたPRの残ブランチ削除は `gh api -X DELETE repos/<owner>/<repo>/git/refs/heads/<branch>` を使う（--no-verify による素通しは行わない。2026-07-24 PO許可のうえ実施・実測）。
