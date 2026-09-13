CARD-PRODUCT-NAME-SPACE-IMPL-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、01-read.md、03-file.md、04-worktree.md、10-executor.md、11-lint.md。
照合: 実在する専用worktree、基点、6製品ファイル、設計の完全一致契約、Docker接続失敗を直接確認。L32は自己照合。

状態
POのA便正式設計承認済み。実装開始・担当への委任は承認待ち。本カードを保存しただけでは実行しない。
担当は承認後にPOが委任する既存実装役1名。新規エージェントや別セッションを起動しない。
目的はdesign §17-2/17-3・§18のA便のみ忠実実装し、6ファイルの差分と検証報告を設計担当へ返すこと。

許可と禁止
手順の範囲で製品6ファイルの実装・テスト追加・同範囲の修正と、そのための既存ソース/試験の読取を許可する。
他者の編集を戻さない。設計の再解釈、依存追加/lock変更、DB/本番接続、商品値変更、CSV改稿/登録、再解析/配信は禁止。
CI/運用スクリプト/secrets/ガード/認証設定の変更、GO記録作成、commit/push/PR作成/マージは禁止。
文書・台帳・根拠登録は設計担当が行う。製品差分は下記6ファイル以外へ広げない。
試験用一時ファイルと既存依存用backend/.venvは許可する。環境変数一覧・秘密の値を報告しない。

出力先
/tmp/reports/CARD-PRODUCT-NAME-SPACE-IMPL-01.txt
一字一句そのまま使い、既存なら上書きせず停止。全コマンドの標準出力/標準エラー・終了コード・開始/終了を直接追記する。
10MBを超えたら停止。秘密は[REDACTED]。空ファイルや以前の報告を成果として再送しない。

停止条件
実装承認未受領、作業場所/基点/設計SHA不一致、既存未保存変更、他者の先約、範囲外修正の必要、権限拒否で該当操作を停止する。
実装に由来する検査失敗は6ファイル内で修正できる。既存問題や仕様の矛盾は推測で解消せず設計担当へ返す。
ローカルDockerはCLIがあるがdaemonに接続できないことを確認済み。pytest/実DB検査は既存CIへ引き継ぎ、本カードで実行しない。
GITHUB_ACTIONS偽装、fixtureの安全条件緩和、外部DB代用、skip追加で検査を通さない。
停止時は手順・最後のコマンド・秘密を伏せた生出力・終了コードを返す。

受領確認
「CARD-PRODUCT-NAME-SPACE-IMPL-01を受領。承認されたA便6ファイルを実装し、公開・商品データ変更は行いません。」

手順1 新規報告を作成
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && python3 -c 'from pathlib import Path; p=Path("/tmp/reports/CARD-PRODUCT-NAME-SPACE-IMPL-01.txt"); p.parent.mkdir(parents=True,exist_ok=True); p.open("x").close()'
手順2 ブランチ
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git branch --show-current
期待値: release/product-name-space-match-impl。以後の全出力も上記報告へ保存する。
手順3 未保存変更
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git status --short --untracked-files=all
期待値: 空。初期状態だけでなく終了時も差分を確認する。
手順4 基点
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git rev-parse HEAD origin/main
期待値: HEADはaf269ae20ed2f52e6cd49ba0403ad7799e3a3870。origin/mainが進んでいれば対象6ファイルへの差分を設計担当へ返す。
手順5 preflight
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && ./scripts/dev/executor-preflight.sh
期待値: PREFLIGHT OK、終了0。
手順6 規則と設計
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && cat AGENTS.md backend/AGENTS.md
読取入力: /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-registration-preflight/docs/handoff/tcg-product-import/design.md
SHA256: a7fadf29dc43719514791a022938bf71f220e396091dd5cea5e134648b09f4db
このファイルのSHA256を照合して§17-2/17-3、§18-1〜18-3、18-6/18-7を読む。
同じ文書作業場所のrecon、keyword-*-experiment.json、keyword-reducer-equivalence.json、再現コード資料とlive-snapshot.jsonを読取可。
実験は設計参考であり製品実装/pytest結果ではない。検算資料を恒久的な第二の判定実装にしない。
手順7 既存依存の準備
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl/backend && /usr/local/bin/python3.12 -m venv .venv
手順8 依存導入
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl/backend && .venv/bin/python -m pip install -r requirements-dev.txt
手順9 忠実実装
許可ファイル:
- backend/app/services/tcg_analyzer_svc.py
- backend/app/services/tcg_keyword_lint.py
- backend/tests/test_tcg_keyword_matching.py
- backend/tests/test_tcg_keyword_lint.py
- backend/tests/test_tcg_product_guards.py
- backend/tests/test_tcg_work_matching_integration.py
各商品で通常一致優先、通常成立語0のときだけ日本語を含む空白なし検索語と商品名全体を追加照合する。
既存normalize_en後、商品名のU+0020/U+3000だけを除く。改行/復帰/タブ/余分な数量/フィールド跨ぎを追加一致させない。
候補選択をanalyzer内の純関数へ共有化し、v3で元文字列の再照合をしない。旧関数の引数/tuple/順序/basisを維持する。
R5検索側も同じ追加一致関数を使う。除外側・作品制約・単品マーカー・数字境界・状態/注記の照合意味を変えない。
AST試験の抽出名へ新関数を追加する。A1〜A8の正否例/同値性/既存293名称/隔離PG試験を対象テストへ組み込む。
最新mainのWORK_ID_PROMPT_VERSIONSとp1/p2統合試験を維持する。設計実験の古いファイルで上書きしない。
実装上の関数名/局所変数は契約を変えない範囲で選べる。追加サービス・データ・依存・CI変更をしない。
手順10 静的検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl/backend && PATH="/Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl/backend/.venv/bin:$PATH" make lint-ci
期待値: 終了0。pytest/PG未実施を区別し、CI成功を宣言しない。
手順11 差分検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git diff --check
手順12 範囲検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git status --short --untracked-files=all
手順13 差分の報告
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git diff --stat
手順14 引き継ぎ
6ファイルの差分、実施した検証と未実施のpytest/PG、A1〜A8対応箇所、停止/未決、報告ファイルを設計担当へ返す。
設計担当が読取レビュー後にPR公開と通常CIへ引き継ぐ。正式試験未実施の状態で実装完了/公開可能としない。
END OF CARD
