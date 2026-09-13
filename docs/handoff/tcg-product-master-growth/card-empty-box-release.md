本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
CARD-LINE-EMPTY-BOX-RELEASE-01

読んだ節: docs/ai-agents/design-partner.md §5.5、docs/handoff/design-partner-card-ops/guards/00-common.md、06-merge.md、09-gh.md、11-lint.md。
自己照合: 公式wrapper・番号を引数に渡さない・マージ後は本店から読取・生出力保存・PO原文逐語・本番前確認と本番後確認を区別。
受領確認: 「CARD-LINE-EMPTY-BOX-RELEASE-01受領。GO #3470の範囲で安全確認・マージ・配備確認を行います。」
目的: 空箱状態と人の確認前配信停止を、既存PR3470から本番へ反映する。
担当: 既存empty_box_implementation 1名。親は設計担当のまま証拠と文書を保存する。追加エージェントは禁止。

承認
PO原文は「GO #3470」。発行者shingo-ops。記録時刻2026-09-13 13:45 JST（実時計04:45:25 UTCからの記録時刻）。
直前に本番安全確認後のマージと自動本番反映を実装担当へ委任する旨を説明済み。代理GOではない。
承認対象の実装HEAD8684707cdf7fe347cd14ec48b4d94c978dcc111f、設計PR3464 §19、22所有ファイル、全pytest2813成功/95skip/失敗0、UI6成功。
PR3464自体のマージ・25th商品辞書登録・再解析・3シート配信は本カード対象外。

許可と停止条件
PR3470のGO原文転記、最新main読取/通常追従、CI読取/必要な再検証、push、公式merge commit、自動配備の監視、公開HTTP読取を許可する。
このリリース作業に限りprod1への通常SSHを使い、本番の稼働・実行中ジョブ・条件辞書・必要な件数を読取確認できる。
本番DB読取はdefault_transaction_read_only=onとstatement_timeoutを明示。接続前に列/コンテナ名を既存仕様と実物で照合し、秘密値の表示は禁止。
バックアップはconditions/analysis_results/item_correctionsの3表をpg_dumpで読取退避し、非公開ローカルへ保存する。DB内に退避表を作らない。
ローカル保存先は/private/tmp/empty-box-release-3470、ディレクトリ700/ファイル600。時刻・bytes・SHA256・pg_restoreの一覧可読性を記録する。
SQLの直接書込み、製品コード追加変更、CI/運用スクリプト/secrets/保護設定変更、管理者強制、ガード解除、GO自己発行は禁止。
本番の変更はPR3470マージに伴う既存deployの自動migration/配備だけ。条件1行を手動で先行投入しない。
実行中の抽出/解析や別deployがあればマージを止め、読取監視で終了を確認する。ジョブを停止/再試行/再解析しない。
検査失敗、既存条件の想定外差分、読取不能、製品の想定外差分、権限/保護拒否は該当操作を停止し親へ報告する。許可を拡大しない。

手順0
  cd /Users/tanizawashingo/salesanchor && ./scripts/dev/executor-preflight.sh

手順1 現在地
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-empty-box-condition-review && git status --short
PR3470のOPEN/HEAD/22ファイル/mergeableをGitHubで照合。最新mainとの差分が判明するまでマージしない。

手順2 最新mainと検証
公式手順でorigin/mainを取得して関係を確認。通常追従が必要なら双方を保持し、所有22ファイルの意味変更が無いことを照合して親へ報告。
競合や想定外の意味変更は親へ戻す。HEADが変わった場合はそのHEADでCI再確認する。別PRやmainへ直接pushしない。

手順3 本番安全確認とバックアップ
既存deploy/runbookから実配備HEAD・コンテナ名を確認。進行中deploy、抽出/解析ジョブ、CN0011の有無と既存状態定義を読取記録。
上記3表の読取バックアップを取得し、生成時刻/サイズ/SHA/可読性を確認。空や読取不能ならマージ不可。
HTTPの事前状態、稼働中処理への影響を記録する。データ内容・バックアップ本体・認証情報はGit/公開PRへ載せない。

手順4 GO転記とCI
PR本文に「### GO記録」とGO発行者/日時/GO原文/バックアップ確認の4欄を正式書式で追記。バックアップは手順3の実測のみ記す。
本文を一時ファイルへ実改行で保存してbody-fileで更新。一般の進めるを番号付きGOに変更しない。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-empty-box-condition-review && gh pr checks
全検査の実行完了・失敗0・GOゲート成功を確認する。skipを成功に数えず、必須試験が実行されたHEADを確認。

手順5 マージ直前
最新HEAD/最新main/GO本文/バックアップ/実行中処理なし/CI成功/所有範囲を再確認して親へ報告。
以下のwrapper出力は/private/tmp/empty-box-release-3470/merge.logへ全文保存する。マージ後に作業台が消えることを前提にする。

手順6 正式マージ
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-empty-box-condition-review && bash scripts/gh-pr-merge-safe.sh --merge --match-head-commit "$(git rev-parse HEAD)" >> /private/tmp/empty-box-release-3470/merge.log 2>&1
squash/管理者強制/長命ブランチ削除は禁止。未知の再試行や拒否は停止し親へ返す。

手順7 マージ・配備確認
  cd /Users/tanizawashingo/salesanchor && gh pr view 3470 --json state,mergedAt,mergeCommit,url
MERGEDとmerge SHAを記録。以後の読取は本店から行い、mainへの直接編集/commitはしない。
  cd /Users/tanizawashingo/salesanchor && gh run list --workflow deploy.yml --branch main --limit 5 --json databaseId,headSha,status,conclusion,url
該当merge SHAのdeployを特定し監視。ログを取得しmigration/配備HEAD/healthを確認。監視の長いtool待ちは60秒以下で区切る。

手順8 本番後の読取
API https://api.salesanchor.jp/api/health と https://app.salesanchor.jp/ のHTTP結果を記録。
読取SQLでCN0011が設計どおり有効1件、既存条件定義を保持、実配備版一致を確認する。
人の確認操作・配信操作・再解析を実機確認のために実行しない。API/DB読取だけで確認できないUI挙動は未確認と明記。
配備失敗なら追加の本番変更/独断rollbackをせず、該当ログと状態を親へ返す。

手順9 完了報告
冒頭「本報告はカード CARD-LINE-EMPTY-BOX-RELEASE-01 の実行結果である」。
PR/最終HEAD/merge SHA/deploy run/バックアップ時刻サイズSHA/HTTP/条件辞書照合/未実施を親へ報告。
生出力は全文を非公開ファイルへ保存してパスを返す。停止時は手順番号・最後のコマンド・理由・エラー全文を返す。
親が設計文書・台帳を更新する。再解析・シート配信は未実施として停止する。
END OF CARD
