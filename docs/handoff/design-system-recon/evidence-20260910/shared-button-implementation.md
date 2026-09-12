# 共通6部品16ボタンの移管検収

これは何か: ボタンの材料を共通部品へ移した範囲と、操作が変わらないことの確認記録。

親: [設計AH](../../../specs/design-system/design.md#ah-共通6部品の旧ボタン16利用を移管2026-09-11)

基準: adc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b（先行PR3435マージ済み）。製品は6TSXとSharedButtonMigration.test.tsxの7ファイルだけ。新CIは最後、backend/API/翻訳/共通CSSは変更しない。

## 静的照合

限定読み取り担当が保存原稿を再実行しexit0。Button70→86、先頭btn332→316、専用20→20、リンク8→8。6ファイル全体でimport/tag/class→variant/size以外のAST差分0、退避6製品hash全件一致。rootは6製品差分を直接読み、原稿と結果を確認した。操作試験の実行とは区別する。詳細: [構文と件数](ah-working-verification.json)、[再現原稿](ah-working-check.cjs)、[再実行確認](ah-working-check-reexecution-verification.json)。原稿内の絶対パスは実行環境の記録で、再現時は作業場所/依存/出力先を対応させる。

## 試験原稿の事前レビュー

CSV試験のObject.assign(URL,...)が元URL自体を書き換える不備1件を限定レビューで検出。Generatorへ元オブジェクトを変えない方式と復元確認を指示した。既存PATCHに加え、売上・仕入・発送の新規POST保存も検収対象とする。最終試験結果は未確認。

## 未完

操作unit、実6部品のブラウザー検証、品質検査、製品の最終限定レビュー、PR提出と番号付きGOは未完。PO目視・本番反映は未確認。設計自己審査と実装合格を混同しない。


## 2026-09-12 AJ 13利用の実装・ローカル検収

PO原文: 「承認する、離席するのでPR．マージ、本番反映までしてくれ」。実装担当1名への委任とPR/マージ/本番反映の依頼として受領。番号付きGO原文を創作しない。LINE委任を本テーマへ流用しない。

実装担当がCARD-RAW-SHARED-SPLIT-03を実行。CommissionPanel.tsxを固定base adc8bc4dへ復元、残5TSX/修正済みテストは全バイト保持。単独20操作は担当実測20/20成功。
設計担当は復元後のソースを直接構文再監査。Button70→83、旧btn332→319、専用20/リンク8不変、Commission差分0、残5TSXの許可import/tag/class以外の業務本文/全属性差分0。

直接実行した品質検証: 対象eslint成功、全体coverage 23files/220tests成功、check:all/build/Storybook成功。coverageはstatements9.28%、branches9%、functions6.72%、lines9.19%（既存閾値を変更していない）。過去失敗は今回成功で上書きせず旧記録に保持。
直接実行した表示検証: 実部品/実Modal/実CSSを一時fixtureで使用し、実APIをモック。明暗×日英×390/767/768/1279/1280/640pxの5部品=120組をbefore/after比較。640pxは200%相当幅であり実zoomではない。
対象ID13の初期横欠け、実Tab到達後の上下左右クリップ祖先とviewport、ラベル/フォーカス輪郭を測定。ShiftTab、初回focus、取消後focusの前後一致。120組成功。
Confirm実呼出し25か所を構文走査し、動的OwnInventory3分岐を照合。実訳文15組×明暗×日英=60条件（390px）成功。最長候補を含む全実ラベル組を検査した。Enter/Spaceは5部品×2=10条件成功、外部form参照と保存中の重複0を確認。

初回表示検証の50失敗はPriority起動ボタンを余白0のrootへ置いたfixtureに限った。実利用はstoryのみ（製品画面0）、PriorityScoreOverride.stories.tsx:17のlayout paddedとStorybook base-preview-head.html:51-55の1remを照合し、fixtureに同じ余白を与えて再検証。製品を直していない。初回失敗・修正後原稿/結果を両方保存。
限界: Priorityの起動ボタンは既存カタログ配置で確認。任意の将来親画面の配置を保証しない。初回/取消後focusは前後同一の観測であり、既存Modalのfocus復帰実装を新たに修正・保証する便ではない。PO画面確認/本番確認は未実施。

追加読取レビュー: 実装担当がCARD-AJ-READONLY-REVIEW-04で5TSX/Button公開契約/テストpayload/URL副作用を照合しAPPROVE（限定範囲）。同担当はCommission復元の実行者なので独立した最終Reviewer/Evaluatorとは称しない。rootが別途構文/品質/表示を直接検算。
設計担当の実装提出判定: **APPROVE（この13移管のローカル検収とPR提出まで）**。全画面統一・最終承認・PO目視・本番反映の合格ではない。報酬3は表統一便へ保留、新CI最後。

根拠: [検証manifest](aj-validation-manifest.json)、[原稿/ログ/画像/初回失敗を含む保存物](aj-validation-checkpoint.tar.gz)。manifestの製品7hashでPR最終製品と照合する。
ブラウザーskillを読んだがnode_repl js実行ツールは利用不可のため、選択済みブラウザーを操作せず独立したローカルChromium検証を実行。Context7も利用不可。許可済み代替でPlaywright公式の[Keyboard](https://playwright.dev/docs/api/class-keyboard)、[Page](https://playwright.dev/docs/api/class-page)、[Network](https://playwright.dev/docs/network)を直接確認。

マージの未充足条件: scripts/check-process-artifacts.js:317で番号付きGOの原文を必須としている。POの今回原文をそのままvalidateGORecordへ渡すと「GO原文の書式不正」となることを直接確認。承認意図は受領済みだが、現行経路では新PR番号のGO照合を満たしていない。ガード変更・承認偽装・代理GOはしない。PR提出/CI観測まで進め、正式GO照合までマージ/本番反映を保留する。


### PR #3442 提出・初回CIの正式GO不足

ready PR https://github.com/shingo-ops/salesanchor/pull/3442 。初回HEAD44320bd63a940420f3b9235d52b5291b8cf822e5、base main、isDraft false、.pr-number=3442を直接確認。
main66b41766を通常統合。evidence-registry末尾の両側追記を全文保持し、製品hash7/7不変、task-state成功。
初回process-artifacts gate job103471236394のAPIログを直接取得し、2026-09-12T01:04:40Zに「PR本文にGO記録セクションがありません」でexit1と確認。POからの依頼原文はPR本文の承認状況に保存し、GO原文欄へ番号を創作していない。
最新CIはPRの現在HEADを参照。番号付きGO照合までmerge/deployを保留。rootの文書保存コミットは製品検収hashを変更しない。
後続実行カード: aj-review-card.txt、aj-commit-card.txt、aj-publish-card.txt（すべて正式lint exit0、長行警告のみ）。


## 2026-09-13 PO GO受領・本番反映手続き

PO原文: 「GO #3442」。受領確認時刻05:20 JST。前日のPR・マージ・本番反映依頼に対応する。代理GOではない。
最新main 5b21b3b8を確認。main側の追加フロントエンド差分0、根拠台帳の末尾追記競合1件を双方原文保持で統合する。製品hash7件と最新HEADのCIを再確認する。
承認記録はPR #3442本文のGO記録4欄へ逐語転記済み。マージと本番完了はPRのmergedAt/mergeCommitおよび当該SHAのdeploy run成功・公開配布物の実測で個別に確定する。
更新前本番HTML sha256: a3a99356560878cd600c2809fa73ba5c3b46a52fd89ea90e0fb93051cd271553。JS /assets/index-G0AkBERe.js、CSS /assets/index-D-QCsmaw.css。
最終結果の一次情報: https://github.com/shingo-ops/salesanchor/pull/3442 （実測結果を本文に追記）。未完了状態を完了と読み替えない。
