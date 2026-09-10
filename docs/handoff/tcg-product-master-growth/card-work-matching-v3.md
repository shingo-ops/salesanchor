本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

CARD-LINE-WORK-MATCHING-V3-01

この文書は、作品違いの商品判定と通常版への限定版の取り違えを防ぐ実装の指示書です。
親: [商品マスタ](../../specs/product-master/README.md)
設計: `docs/handoff/tcg-product-master-growth/design-keyword.md` §10
対象ADR: ADR-154追加決定案／ADR-113。mode: handoff。

状態: 文書レビュー用。設計とADR追加決定が正式承認されmainへ入った後に有効。本カードを保存したことは実装役の起動ではない。
POの実装依頼・GOは受領済み。本番操作・マージ・配信・既存解析の一括修復は許可に含まない。

読んだ節: `docs/handoff/design-partner-card-ops/guards/00-common.md`、`guards/11-lint.md`、`docs/ai-agents/design-partner.md` §5.5。
自己照合: 1○ 記号をコード表記、2○ PRはready、3○ 報告宛先指定、4○ 商品特定1目的、5○ origin/mainから新規、6○ PR記載例、7○ 対象と結果の基準を設計§10へ固定。
機械チェックは本カードに対する `scripts/card-lint.sh` の実行記録を設計側が添える。

受領確認
最初に「CARD-LINE-WORK-MATCHING-V3-01 受領」と返す。

許可
設計§10の製品・テスト・migration・runnerの列挙ファイルだけを実装する。必要な台帳の当該行と本カードの実行結果を更新してよい。
設計の文書承認を確認後、下記の専用ブランチで実装する。他者の変更は上書きせず、同じファイルに重複実装があれば既存の契約適合を確認する。
ローカルPostgreSQLのテスト、静的検査、文書検査、文書に定めた匿名化標本でのGemini確認、コミット・push・main向けready PR起票までを許可する。

禁止
本番・QAサーバーDBの更新、既存データの一括再解析、原文全文のGit登録、新商品の独断登録、CI・deploy.yml・secrets変更、承認の代筆、サブエージェント起動、マージ、ガード迂回は禁止。
同名migrationが既に存在し内容が異なる場合、改名して回避しない。

開始条件
設計§10とADR-154の追加決定が正式承認済みであることをPRの記録から確認し、そのURLを報告に残す。未承認の場合はここで停止する。

手順0
  cd /Users/tanizawashingo/salesanchor && ./scripts/dev/executor-preflight.sh

手順1
  cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/line-work-matching-v3

手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-work-matching-v3 && git status --short

手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-work-matching-v3 && git rev-list --left-right --count HEAD...origin/main

実装作業
手順3は `0 0`、手順2は変更なしを確認してから実装する。
設計§9のGO後契約を§10の差分で補完した最終契約に従い、9列抽出・作品根拠2列保存・作品候補制限・同一明細の除外語確認・訂正保護を実装する。
PM0200の「コロ」追加は冪等なdata migrationとし、PM0285や新規商品は変更しない。
スキーマ変更は追加専用。型番のみ判定、見出しの帰属、不明と矛盾の扱い、旧7列とv3エラーの扱いを設計から変更しない。

検証作業
設計§10.3の表をすべて検証し、ケース名・期待・実測・合否を対応させる。29は過去保存行相当の入力数であり、Gemini正答数として流用しない。
PostgreSQL統合試験はローカルのテストDBで実行する。既存のTCG抽出・解析・配信テストも実行する。Dockerが使えなければ統合試験をPASSとせず、未実施を報告して停止する。
Gemini実験は匿名化した標本だけを用い、形式失敗・正答・不明・誤分類を別計測する。失敗や正例の取りこぼしを隠して受入済みとしない。

手順4
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-work-matching-v3/backend && make lint-ci

手順5
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-work-matching-v3 && bash scripts/check-task-state.sh

手順6
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-work-matching-v3 && git diff --check

PR作業
検証完了後に実際に変更したファイルだけをコミットする。コミットの実在は `git log -1 --format=%H` で確認してからpushする。
公式 `scripts/gh-pr-create-safe.sh` の手順でmain向けready PRを作る。PR本文は実在する本文ファイルを作り `--body-file` で渡す。文書承認・実装GOと本番GOを混同しない。
良い記載例: `### 標準ワークフロー確認` の中に `設計: docs/handoff/tcg-product-master-growth/design-keyword.md` を置く。
禁止形: 対象ADR・recon・設計を別セクションへ平打ちする。触るファイルには実際の変更パスを全件宣言する。
追加決定が未承認のまま本文に承認済みと書かない。

完了報告と停止
報告冒頭は「本報告はカード CARD-LINE-WORK-MATCHING-V3-01 の実行結果である」。完了報告の本文に実行した検証の生出力を全文含め、PR URL・HEAD・差分ファイル・検証ケースの結果・未実施項目を設計パートナーへ返す。
停止時は停止した手順番号／最後のコマンド／停止理由とエラー生出力を返す。契約矛盾や必要ファイルの追加は設計側へ戻し、実装役で設計を変えない。

END OF CARD
