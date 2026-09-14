# CARD-PRODUCT-ALL-TERMS-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: CARD-PRODUCT-ALL-TERMS-01。設計・実装後審査は同一AI自己審査。
読んだ節: guards/00-common.md、guards/03-file.md、guards/05-pr.md。
カード照合1〜7: ○記号保持 ○ready PR ○報告宛先 ○全語一致の1目的 ○origin/main起点 ○PR書式 ○対象/期待出力。
根拠: design.md §23/24、partial-match-evidence-20260914.json。設計自己審査APPROVE。
POの最新依頼を実装と条件付き公開の承認根拠とする。未整備のGO委任は自己有効化しない。
責任: 本セッションが設計契約の実装と検証を行う。新たなagentは起動しない。他者の変更を戻さない。
対象製品6ファイルと正確な処理・受入条件はdesign§24に列挙済み。それ以外の製品変更禁止。
設計差分/検証結果は既存design/recon/ADR154/品質設計と台帳/根拠登録に保存可。
本番DB書込、旧参照書替え、モデル呼出し、配信、migration/CI/運用script変更は禁止。
手順1 設計契約の実装前確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-keyword-all-terms && git status --short
期待する出力: 自分の設計文書以外の変更なし。矛盾があれば対象名を報告して該当編集停止。
手順2 実装
設計§24/24-5の6ファイルに限定し、肯定検索関数/版更新/R5接続と既存テスト更新・追加を行う。
手順3 検証
境界16例と追加unit、固定正解4明細、全1504明細対照、品質規則の全差分を確認する。
Dockerなしの場合はDB pytestを実行せず、正式CIのPostgreSQLで既存+追加テストを実行する。
期待する出力: 固定正解4/4、既存一意特定喪失0、別商品変更0、新規STOP0。失敗対象を全列挙する。
手順4 保存と公開準備
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-keyword-all-terms && git diff --check
commit後git logで実在確認し、正規gh-pr-create-safe.sh経由でready PRを作成する。
番号/HEADの一致、CIとレビュー、配備障害解消を確認。正規GO検査未充足の場合は本番反映を停止する。
完了報告はPO向け本文に結果と未完了条件、実行ログ保存先を含める。実装担当用生出力は証跡に保存する。
停止時は手順番号/最後のコマンド/理由/対象を報告。精度が悪化又は根拠未確認なら公開しない。
END OF CARD
