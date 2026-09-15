CARD-PRODUCT-NAME-SPACE-RELEASE-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、05-pr.md、06-merge.md、09-gh.md、11-lint.md。
受領確認: 「CARD-PRODUCT-NAME-SPACE-RELEASE-01を受領。POのGO #3473に基づき通常マージと配備結果確認を行います。」
担当: 既存/root/csv_card_executor。親は設計・証拠保存・読取検証を担当する。

承認
PO原文「GO #3473」を受領。対象PR3473、承認時HEADe484f168c757d9b46869895d1d70d96451f22ae0。
GO発行者はPOしんごさん(shingo-ops)。AI代理GOではない。原文は上記のまま記録し、日時は実時計による転記日時と注記する。
通常マージと自動本番配備、今回のバックアップ/HEAD/健康確認まで許可。文書PR3466のマージは対象外。

許可と禁止
PR3473のGO転記、下記確認済みmainへの追従、チェック、push、必要な確認コメント、正式wrapperのmerge commitと自動配備読取監視を許可。
製品6ファイルの編集、CI/運用スクリプト/保護設定/secrets変更、本番手動変更、データ登録/再解析/配信、新規エージェント/別PRマージは禁止。
本番へ手動接続して操作を加えない。配備失敗時は読取診断で停止し親へ報告する。
旧worktree/他者変更を上書き・清掃しない。main/developを削除しない。文書の新規加筆は親が担当。

停止条件
PR/初期HEAD/6製品SHA不一致、未知main、製品競合、未保存変更、CI技術失敗、権限拒否、配備失敗で該当操作を停止。
最新main統合の台帳末尾競合だけは双方の追記を全文保持して解消・commit可。それ以外の競合は親へ戻す。
通常の権限審査は使えるが、拒否を設定解除・迂回で解決しない。失敗と未確認を明示する。

報告
/tmp/reports/CARD-PRODUCT-NAME-SPACE-RELEASE-01.txt を排他的新規作成し、全出力/終了コード/開始終了を直接保存。
秘密は[REDACTED]。旧報告を上書きしない。マージ後worktreeが削除されるため必要な版/期待SHAをtmpへ先に保存する。

手順1 状態と事前検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && ./scripts/dev/executor-preflight.sh
status空、.pr-number3473、PRのbranchと承認時HEAD一致を照合。6製品SHAは /tmp/reports/CARD-PRODUCT-NAME-SPACE-RELEASE-01-sha.json と一致必須。
手順2 GO転記
PR本文を通常のgh pr viewで取得し、tmp本文を編集後gh pr edit --body-fileで反映する。既存検証・設計記録は保持。
### GO記録 の正規欄 GO発行者: shingo-ops / 日時: 実転記日時 / GO原文: GO #3473 / バックアップ確認: を使う。
直近配備34740608928の14:34:49 JSTバックアップ7.6M生成は親が実ログ確認済み。今回配備分はまだ未取得と記録する。
既存deploy.ymlの配備前新規バックアップ生成・存在確認と失敗停止を維持する。過去バックアップを今回取得済みとしない。
手順3 最新取得
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git fetch origin
確認済みmainはc50d719b2505c3e1d1977c4f36bdae39f14dae22に更新。別SHAなら親へ差分を戻す。
c22ad508からの追加はPR3468のスタッフ画面6ボタン共通化・試験・文書14ファイル。親が実diffで6製品への変更0を確認済み。
再開時の製品HEADはa618c147bac99296c46cd4647d7cec0e0ff456a6、初期6SHAは不変。手順3から通常取込・push・新HEADのCIを行う。
今回6製品ファイルにmain側変更0。追加は抽出タスクの120/100秒→330/300秒、public.productsの既承認seed55件と登録、所有権/フックの補助、文書。
親が現物照合済み。seedはpublic.productsで本便が照合するtenant側tcg_productsとは別。既存main内容を保持する。
手順4 確認済みmain取込
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git merge --no-edit origin/main
台帳末尾の単純追記競合だけは上記範囲で解消。製品差分の独断修正は禁止。
手順5 一致・公開
最終差分6製品+固定版17文書、6製品SHA不変、status空を確認。git logでcommit実在を確かめてpushする。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git push -u origin HEAD
新HEADをPR本文へ記録し、旧HEADの3260成功と新HEADで実行したCIを区別する。
手順6 CI
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && gh pr checks
全実行チェック成功を待ち、GO記録gateも成功を直接確認。pytest/PG内部ジョブが実際に走ったかを確認。
必要な当該PR/配備のCIログは通常読取経路で取得可。未知の技術失敗は親へ報告して停止する。
本文更新で取消された旧GO gateだけがrollupに残る場合、同一HEADの当該旧runを通常のgh run rerunで再実行可。
同一HEAD・GO本文不変を照合し、再実行の成功を待つ。取消を成功扱いせず、失敗・拒否なら停止する。
手順7 マージ直前
GO本文、最新HEAD、最新main、23ファイル境界、6製品SHA、全実行CI成功/対象外、status空を同じ時点で確認。
必要な「確認済み：」コメントはbody-fileで記録可。独立レビューを名乗らない。確認済み版から変化していれば停止。
手順8 正式マージ
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && bash scripts/gh-pr-merge-safe.sh --merge --match-head-commit "$(git rev-parse HEAD)" >> /tmp/reports/CARD-PRODUCT-NAME-SPACE-RELEASE-01.txt 2>&1
squash/admin/自動承認オプションを付けない。未知mainによる再試行・競合は親へ戻す。
成功後の読取はworktree消失に備え本店で行う。cleanup失敗とGitHubマージ失敗を混同しない。
手順9 マージ事実
  cd /Users/tanizawashingo/salesanchor && gh pr view 3473 --json state,mergedAt,mergeCommit,url
MERGEDとmerge SHAを直接確認。
手順10 自動配備
  cd /Users/tanizawashingo/salesanchor && gh run list --workflow deploy.yml --branch main --limit 5 --json databaseId,headSha,status,conclusion,url
merge SHA一致のrunを特定し終了まで監視。実ログの今回バックアップ日時/サイズ、実配備HEAD、healthを照合。
新規バックアップ生成失敗・配備失敗なら手動修復せず報告。ログ未取得を成功としない。
手順11 公開HTTP
https://api.salesanchor.jp/api/health と https://app.salesanchor.jp/ のHTTP200をcurl等の読取で直接確認し保存。
新しい解析や商品登録を起動しない。既存過去結果や本番での実投稿精度が変わったとは主張しない。
手順12 結果
merge SHA/配備run/今回バックアップ/実配備HEAD/HTTP/CI根拠/未確認/生報告を親へ返す。
PR本文の最終状態も通常編集で実績に合わせ、GO原文と検証履歴を保持する。親が正式台帳と文書を保存する。
公開PRへの内部詳細追記が審査拒否された場合、公開済みPR/merge/run成功と公開HTTP成功だけの結果追記へ縮小可。GO原文/履歴を保持し、再拒否なら停止。
END OF CARD
