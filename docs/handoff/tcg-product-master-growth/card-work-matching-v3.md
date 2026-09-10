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
PostgreSQL統合試験はローカルDocker、または既存のGitHub CIの使い捨てPostgreSQL 16で実行する。既存のTCG抽出・解析・配信テストも実行する。ローカルDockerがない場合はローカルpytestを実行せず、静的検査後にready PRを作って既存CIへ進む。統合試験を省略・SQLite代用・skipのままPASS扱いにしない。CIでも実行できない場合は未実施と根拠を報告して停止する。
Gemini実験は匿名化した標本だけを用い、形式失敗・正答・不明・誤分類を別計測する。失敗や正例の取りこぼしを隠して受入済みとしない。

手順4
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-work-matching-v3/backend && make lint-ci

手順5
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-work-matching-v3 && bash scripts/check-task-state.sh

手順6
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-work-matching-v3 && git diff --check

PR作業
ローカルで実行可能な検査を完了後、実際に変更したファイルだけをコミットする。Dockerがない場合はCI実行に必要なready PR起票を先行してよい。CIで新規PostgreSQL統合試験が実行され成功したことを確認するまで、検証完了とはしない。コミットの実在は `git log -1 --format=%H` で確認してからpushする。
公式 `scripts/gh-pr-create-safe.sh` の手順でmain向けready PRを作る。PR本文は実在する本文ファイルを作り `--body-file` で渡す。文書承認・実装GOと本番GOを混同しない。
良い記載例: `### 標準ワークフロー確認` の中に `設計: docs/handoff/tcg-product-master-growth/design-keyword.md` を置く。
禁止形: 対象ADR・recon・設計を別セクションへ平打ちする。触るファイルには実際の変更パスを全件宣言する。
追加決定が未承認のまま本文に承認済みと書かない。

完了報告と停止
報告冒頭は「本報告はカード CARD-LINE-WORK-MATCHING-V3-01 の実行結果である」。完了報告の本文に実行した検証の生出力を全文含め、PR URL・HEAD・差分ファイル・検証ケースの結果・未実施項目を設計パートナーへ返す。
停止時は停止した手順番号／最後のコマンド／停止理由とエラー生出力を返す。契約矛盾や必要ファイルの追加は設計側へ戻し、実装役で設計を変えない。



補正記録（2026-09-10）
停止分類: カード不備。設計§10.3はCIでのPostgreSQL検証を許可していたが、本カードがローカルDocker不在で一律停止としていたため整合させた。
実測: Dockerコマンドなし（exit127）、標準配置3箇所にも実体なし。製品変更前に停止した。
CI根拠: `.github/workflows/test.yml` のpytest-runはPostgreSQL16/Redis7を起動し、`RLS_ADMIN_DATABASE_URL`を設定してbackendのpytest全件を実行する。`backend/pyproject.toml` のtestpathsはtests。CI変更は不要。
実装テストはCIのこの接続情報を使い、使い捨てテストDB／名前空間に限定する。同時に走る他の試験や本番へ影響しないことを検証する。
Gemini実測の認証が利用できない場合は認証情報を探索・開示せず、匿名化標本と期待値を準備し、実測未了をPRへ明記する。コード・DB統合検証は続行可能だが、本番反映可とはしない（設計§10.3の本番前実測条件を維持）。
本補正で製品の仕様・受入条件・CI設定・本番権限は変更しない。実装役1名の委任はPOから受領済み。

追加補正（設計側指示）: 未一致のpid_basisは厳密に `NONE` を維持する。既存 `backend/app/services/tcg_analysis_review_svc.py:77,94,118` の完全一致条件を壊さないため。作品制約の表示は成功・複数候補時に付け、未一致の履歴は作品原文2列とengine_versionで追跡する。UIファイルの追加変更はしない。

検証環境補足: 試験のDB削除命令を含むファイル作成が不可逆操作ガードに拒否されたため、削除処理を取り除いた。CIの使い捨てサービス内だけでランダムな試験DBを作り、サービス終了時の廃棄に委ねる。GITHUB_ACTIONS・接続host・試験用DB名を検証し、本番・QA・ローカルDBには実行しない。ガード解除なし。

追加所有（設計側指示）: `backend/tests/test_gemini_error_redact.py` の正常応答fixtureを9列へ更新する。既存test_success_has_no_error_messageは新規extract_messageに7列を渡しており、厳格v3契約と矛盾するため。秘密情報の秘匿検証は維持し、旧7列は旧パーサのテストで保持する。

実行結果（2026-09-10）: ready PR https://github.com/shingo-ops/salesanchor/pull/3393 を提出。Python3.12静的検査、task-state、card-lint、diff検査を完了。PostgreSQL統合と既存回帰はCI確認待ち。Gemini APIキー未設定のため匿名標本の実測は未了。製品マージ・本番DB変更・配信は未実施。

有限の追加実測（設計側指示）: 既存CIのGemini認証を利用できるか、一時計測テストを1コミットだけ追加して確認する。匿名6メッセージ・期待8明細を実行し、安全な集計だけをログへ出す。キー不在は未実施を明記。CI完了まで他pushをせず、結果取得後に一時計測テストを除去する。将来のCIに外部API呼び出しを常設しない。

一時計測の検証修正: ff8098eeのCIは2425 passedだが、xdistによりcapsys.disabledの集計stdoutが残らず、8件正解と未実施を区別できなかった。既存artifactは0件。設計側指示で安全な集計JSONをUserWarningへ変更し、最大6メッセージの再計測を1回だけ行う。初回集計は取得不能として保存し、2回呼び出した可能性を隠さない。

最終実測記録: EV-20260910-LINE-ACCURACY-08の追補を参照。既存CIのPostgreSQL統合6テストを含む2424 passedを確認。Gemini実測2（6b489af4 / run34426443315）は匿名8明細中、作品特定7＋不明保持1が期待どおり、誤分類・形式失敗・欠落・過剰・API失敗0。初回ff8098eeは集計取得不能で母数に含めない。一時計測除去SHA b2700dd0dd04f3ad0e5733d902f3d6980bc8e2ec。rootは指摘修正とGitHub生集計を読み取り確認済み。最終CIと新PR固有GOは別の状態として管理する。

END OF CARD
