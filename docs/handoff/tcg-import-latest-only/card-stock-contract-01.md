本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-CONTRACT-01

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。
照合結果: 実在する専用作業台を指定。新しい作業台の作成・自動回収・PR操作は含めない。実装内容はdesign §15の第1便に固定。コマンドは各手順のcd接頭辞から実行する。

担当: POがこのカードを渡した実装役。設計担当自身は実行しない。受領確認としてカードID・作業台・4ファイルの範囲を最初に返す。
目的: 根拠のない抽出値を拒否し、「①」を1と保持し、「10→残3」を103へ変換しない部品を作る。
設計審査: 同一AIによる第1便限定APPROVE（design §11）。全体設計も自己審査APPROVEだが、本カードの実装許可は第1便だけ。実装移行のPO原文記録はdesign §15。マージ/本番GOではない。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design
ブランチ: release/line-stock-message-design
このカードを引き渡す時点で設計担当は編集を終了する。受領者が正規にこの作業台を利用できる場合だけ続行する。所有制御の拒否を解除しない。

許可: 以下4ファイルの新規実装、同ファイルの部品試験、読み取り調査。実装は手順4で指定する範囲に限り、実装方法の選択は設計契約内で行う。
変更ファイル: backend/app/services/tcg_stock_evidence.py、backend/app/services/tcg_stock_quantity.py、backend/tests/stock_contract/test_stock_evidence.py、backend/tests/stock_contract/test_stock_quantity.py。
禁止: 既存製品コード・設定・依存・DB・migration・CI・scripts・secretsの編集、既存呼出元への接続、外部AI/Sheets/本番アクセス、文書/台帳/GO記録の編集、コミット/push/PR/マージ、サブエージェント起動。他者の変更を戻さない。

手順1: 必須preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。成功した場合のみ次へ。

手順2: 作業ブランチと未保存変更を確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && git status --short --branch
    期待する出力: 上記ブランチで、未保存変更0件。別ブランチや未保存変更があれば編集を停止して全文報告する。

手順3: 正式設計の内容一致を確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && shasum -a 256 docs/handoff/tcg-import-latest-only/design.md
    期待する出力: 6f435e1a1ceda35498557c9f248d7a38ae7d6677efc7b04714e4874570aa8ee8。一致した場合のみ次へ。

手順4: 実装
    設計文書の§15「第1便の実装境界」全文と§22/25を読み、指定した4ファイルを新規作成する。
    新規ファイルが既に存在した場合は上書きせず停止する。
    validate_stock_evidence、StockEvidenceError、parse_stock_quantityを指定型/戻り値/例外で実装する。
    6試験群をunittest.TestCaseで実装し、入力/期待値は設計の表と一致させる。
    本カードの範囲を拡張せず、DB・既存worker・画面・配信への呼出接続を作らない。

手順5: 部品テスト
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design/backend && python3 -m unittest discover -s tests/stock_contract -p 'test_*.py' -v
    期待する出力: 0件収集でなく、両モジュールの6試験群が収集され全成功。全backend試験やAI精度の合格とは報告しない。

手順6: backend静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design/backend && make lint-ci
    期待する出力: 既存の必須検査成功。mypyは既存makeが警告扱いにするため、その出力も残す。

手順7: 差分形式
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && git diff --check
    期待する出力: 既存の追跡済みファイルの差分エラー0。本コマンドだけで新規4ファイルを検査済みとしない。

手順8: 範囲検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && git status --short --untracked-files=all
    期待する出力: 指定4ファイルだけが新規。その他の差分0。新規ファイル全文と試験出力を設計担当へ返して停止する。

失敗・不明・契約矛盾・権限拒否があれば該当操作で停止し、コマンドと生出力全文を返す。許可の自己発行やチェック変更で回避しない。
報告: CARD ID、実際のブランチとHEAD、変更4ファイル全文、各検証のコマンド/生出力、未実施の検証を区別する。商品A〆でB維持、日付表示、実PG、UI、3シート配信はこのカードでは未検証と明記する。
END OF CARD

## カードの査定記録（実装手順ではない）

機械: scripts/card-lint.shを実行しexit 0、違反0。L24（200字超）は6行の警告のみ。未実装の目視項目も下記で照合した。
同一AIの目視: 実在作業台、確定した設計hash、4ファイルだけの権限、停止/報告、既存処理未接続を照合済み。独立レビューではない。
本カードの成果物は未接続の部品と試験。実装カード作成済みと製品実装済みを区別する。
