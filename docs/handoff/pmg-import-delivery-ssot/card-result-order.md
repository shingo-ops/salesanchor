# CARD-TCG-RESULT-ORDER-01
読んだ節: guards/04-worktree.md、guards/05-pr.md、guards/11-lint.md。L32も人手で照合。
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: 本カード名と対象を確認して開始する。
mode: handoff
対象は解析結果と配信の並び順の共通化1件。
現時点は性能補正の実装役への明示委任待ち。設計担当自身の製品編集は自動承認レビューで拒否済み。
根拠は docs/handoff/pmg-import-delivery-ssot/design.md のRESULT-ORDER節と自己審査補正。
事業条件はPO合意済み8状態。条件付き本番許可は原文記録どおりであり番号付きGOを創作しない。

許可する製品差分:
- backend/app/services/tcg_result_order.py 新規: 固定SQLエイリアス専用の共通ORDER BY。
- backend/app/services/tcg_analysis_review_svc.py: ORDER BY共通化とitems_sqlのページID先行MATERIALIZED化。表示列/WHERE/count/providersを保持。
- backend/app/services/tcg_distribution_svc.py: ORDER BYの共通化。
- backend/app/services/tcg_import_progress.py: read_items内のみ、取込限定source hash/順位を追加しページ/JSON両方を同順にする。
- backend/tests/test_tcg_result_order.py 新規: 実PostgreSQLで順序と集合/ページを検証する。
- backend/tests/test_tcg_import_progress_pg.py: 既存fixtureに修正履歴の正規migrationを追加する。
許可する文書は本テーマのdesign/recon/証跡/本カード/tasks/evidence/当該分割台帳のみ。
禁止: API型変更、原文/解析保存値変更、DB migration、状態マスタ優先順位変更、GAS編集、コンディション絞り込み変更、secrets/CI/本番scripts変更。
許可・禁止は本件だけに適用し、他者の作業台や未保存変更へ触れない。

カード発行照合:
1 ○ パスは明示済み。
2 ○ PRはready。公開前に検証結果と対象差分を確認する。
3 ○ 本報告はカードCARD-TCG-RESULT-ORDER-01の実行結果である、と明示して生出力を添付する。
4 ○ 1便1目的。
5 ○ origin/main起点の専用作業台release/tcg-result-order-designを継続使用する。
6 ○ PR宣言は行頭の「触るファイル:」「削除するファイル:」。箇条書き見出し化はしない。
7 ○ 実PGで並び/全列/件数/ページ/未解析/無効原文/確定状態/未知状態の全期待値をassertする。

手順1
設計補正を含めて読む。各変更先の現行ブロックを照合し、合意済みORDER BY以外の契約を保持する。
手順2
既存PR差分を保持し、design末尾のページID先行補正を実装。上記6製品/テストファイルが許可対象。価格は文字列でなくar.price_normalized。順位は8状態、その他は末尾、NULL末尾。
手順3
実PostgreSQLで3経路を同一fixtureへ通し、IDに対応する値と件数不変、並べ替えの前後で集合一致を検証する。
既存本番DBは試験に使わない。正式CIの独立試験DBを使いskipを成功としない。
追加負荷確認は同テストファイル内、4097原文/明細、READ ONLY、各SQL10秒上限。解析500/取込100で先頭/offset4000と配信全件を確認。review_beforeの新構造への誤流用は禁止。EXPLAIN ANALYZEの実測を記録し、本番速度の保証とはしない。
手順4
既存の正規PR手順でreadyのPRを作成し、必須CIの最新HEAD結果を記録する。
手順5
レビューとCIが揃った場合のみ、PO条件付き許可とマージ前検査を照合する。
ガードが追加の承認条件を要求したら停止して、その操作と理由を報告する。迂回しない。
本番後はコード配備と実配信を区別し、実データの順序/内容保持まで照合できた場合のみ完了とする。

停止した場合は手順番号、最後のコマンド、理由、確認できた事実を報告する。
END OF CARD
