CARD-PRODUCT-CSV-RELEASE-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、05-pr.md、09-gh.md、11-lint.md。
受領確認: 「CARD-PRODUCT-CSV-RELEASE-01を受領。GO #3438の範囲で反映と完了確認を行います。」
目的: POが明示した「GO #3438」に基づき既存PR3438をマージし、自動本番配備の完了を確認する。
担当: 既存csv_card_executor。親は製品実装へ切り替わらず、証拠と台帳を保存する。

許可
既存PR3438のGO転記・main追従・検査・push・確認コメント・正式wrapperによるmerge commit・自動配備監視・本番HTTP読取。
GO発行者はしんごさん(shingo-ops)、GO原文は「GO #3438」。AI代理GOではない。
記録日時は実時刻取得による転記日時とする。以前の別番号3458をこの承認の根拠にしない。
バックアップ確認は前回配備2026-09-12 19:39 JST/6.7Mの生成ログ確認、今回の配備直前取得は既存workflowで新規取得し失敗停止、今回分未取得と正確に記す。

禁止
製品8ファイルの変更、CI/運用スクリプト/secrets/保護設定変更、admin/bypass、データ登録/再解析/配信、新規エージェント、別PRマージ。
本番への手動変更は禁止。自動配備が失敗したら読取診断を親へ報告し、独断修復しない。
他者の変更を戻さない。main/developを削除しない。親の文書PR3436はマージ対象外。

停止条件
PR番号不一致、対象8製品SHA不一致、未知のmain変更、競合、未保存/独自の未追跡ファイル、CI失敗、権限拒否、配備失敗で該当操作を停止する。
通常のrequire_escalated権限審査は使用可。拒否を設定解除で解決しない。

手順1 状態確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && ./scripts/dev/executor-preflight.sh
status、.pr-number、gh pr list --head release/product-import-template-implの一致を確認する。PR3438/開始HEAD2184092cが期待値。
報告 /tmp/reports/SA-CSV-RELEASE-20260913.txt を排他作成し、以後全出力を直接追記する。
全shell要求は実在するworktreeへのcdを先頭に置き、ログの前処理と本体要求は分ける。

手順2 GO転記
PR本文を取得しtmpのbodyファイルに保存、### GO記録に正規欄名「GO発行者:」「日時:」「GO原文:」「バックアップ確認:」を用いる。日時は実記録日時であると注記する。
現在地をPO承認済み・マージ前へ訂正し、gh pr edit --body-fileで反映する。未取得のバックアップや配備成功は記さない。

手順3 最新main統合
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git fetch origin
親確認済みのmain 4d30c0ba6e2138ac923c091099e262ad8d8a2e86に限りgit merge --no-edit origin/mainを許可。
追加は別画面のButton統一6ファイルと設計文書、配信サービスの日付列1行修正とその試験/文書。配信サービスへの商品CSVの参照0を親が確認。今回の8製品/共通Button自体の変更0、商品CSV機能は変更された画面部品を参照しないことを親が確認。
他のmain SHAなら差分を親へ戻す。git競合は解消せず停止。

手順4 一致検査と公開
8製品SHAを /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02-parent-review.json と照合し、mainとの差が8製品＋4文書だけか確認。
状態がcleanならpush。新HEADをPR本文の検証対象へ追記、過去試験の実行HEADと新HEADの不変確認を区別する。

手順5 CI
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && gh pr checks
新HEADの全検査完了を待ち、process-artifactsも成功を確認。未完了・fail・対象外を成功へ混ぜない。
必要なCIログは当該PR/配備の正常読取経路で取得する。通常権限審査を使用可。

手順6 マージ直前確認
PR本文GO、最新HEAD、最新main、8製品SHA、12ファイル境界、全実行CI成功、status空を確認して親へ報告。
「確認済み：」から始まるコメントをbody-fileでPRに残す。本カードのGO/検査に基づく確認であり独立レビューを名乗らない。
wrapperは成功後に実装worktreeを削除するため、報告はtmpへ保存。独自の未保存ファイルがないことを確認し、生成依存以外の未保管ファイルがあれば停止。

手順7 正式マージ
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && bash scripts/gh-pr-merge-safe.sh --merge --match-head-commit "$(git rev-parse HEAD)" >> /tmp/reports/SA-CSV-RELEASE-20260913.txt 2>&1
squash/admin/delete-branchオプションを付けない。自動再試行で未知のmain更新が見つかれば親へ報告。
成功後は実装worktreeの存在に依存しない。以後の読取先は /Users/tanizawashingo/salesanchor とする。

手順8 マージ事実
  cd /Users/tanizawashingo/salesanchor && gh pr view 3438 --json state,mergedAt,mergeCommit,url
MERGEDとmerge SHAを取得。wrapperのcleanupの失敗だけをマージ失敗と混同しない。

手順9 自動配備
  cd /Users/tanizawashingo/salesanchor && gh run list --workflow deploy.yml --branch main --limit 5 --json databaseId,headSha,status,conclusion,url
マージSHAに一致する配備runを特定し、終了まで監視。ログはtmpへ保存。新しいbackupの生成日時/サイズ、実配備HEAD、health成功を照合。
主張は該当ログで得た内容だけに限定。長い監視中も親へ進捗を送る。

手順10 本番読取確認
API https://api.salesanchor.jp/api/health と https://app.salesanchor.jp/ のHTTP200を確認。
https://app.salesanchor.jp/templates/tcg-product-import-template.csv をtmpへ取得し、コミット資産148バイトとSHA一致、BOM/CRLF/10列/商品0行を検査。
製品worktreeは消える可能性があるため期待バイト/SHAはマージ前にtmpへ保存する。
ブラウザー保存ボタンの本番認証操作や商品登録を成功確認に含めない。

手順11 終了報告
PR/merge SHA/配備run/backup日時サイズ/配備HEAD/HTTP/CSV一致/失敗と未確認を親へ返す。
生報告パスを示す。親が設計文書・台帳・必要な索引を更新する。追加実装・新たなGO・別テーマ作業をしない。
END OF CARD
