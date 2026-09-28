# CARD-LINE-GUIDE-02 — 原稿レビュー反映と検証

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: 冒頭でカード名を示す。担当Sol、設計・レビューAstra。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、01-read.md、03-file.md、11-lint.md。
§5.5照合: 記号○、ready指定○（PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業台と許可ファイルはCARD-LINE-GUIDE-01と同じ。起動cwdも正式worktreeであること。
本便の追加目的は原稿の意味を明確にし、既存設計とのずれを修正して試験すること。
前便の変更を保持し、他者変更を巻き戻さない。commit/push/PR/merge/deployは禁止。

## Astraレビュー（REVISEからの具体的修正）

1. ja/en原稿に設計者への禁止事項が混入している。利用者が取る行動の説明へ直す。
2. 段階5は照合自体が自動解析であり「照合後に自動解析」という別処理に読める文を直す。
3. 目次のidは設計どおり各h3へ付け、tabIndex=-1で移動先見出しにフォーカスできるようにする。liからidは除く。
4. E2Eの仕入元ボタンは手順2のCardへ限定して選択する。同名ボタンが2個あるので全画面の単数locatorは不適合。
5. 遷移E2EはURLだけでなく遷移先内容/見出しもassertする。ガイド見出しが消えることと対象画面の実在表示を確認する。

## 原稿の確定修正（ja。enは同義に忠実翻訳）

readOnlyNotice: 手順を確認するページです。各操作は、ボタンで開く画面で行います。
prerequisites.item3: 商品・単位・状態の登録情報と、読み取り方を決めるルール・指示文を確認できる権限
step1.trouble: 取り込めない場合は、書き出したファイルが.txt形式か、指定した期間に投稿があるかを確認します。
step3.trouble: 使いたい投稿が見当たらない場合は、原文の投稿日時と指定した期間を確認します。
step4.reference: 仕入元別ルールで書き方の特徴、抽出フィルタ / ルールで読み飛ばす条件、抽出プロンプト設定でAIへの読み取り指示を確認します。
step4.trouble: 読み取りに失敗した場合は、エラーログを開いて原因を確認します。
step5.input: 自動解析が有効な場合、システムが登録情報を使って、どの商品・単位・状態に当たるかを照合します。
step5.result: 商品や単位などの照合結果と、確認が必要な項目が記録されます。
step5.next: 解析が終わったら、取込画面で結果を確認します。
step5.trouble: 抽出が終わっても解析が始まらない場合は、管理担当者に自動解析の設定を確認してもらいます。
step6.trouble: 判断できない項目は、元の投稿と登録情報を確認します。処理の失敗が表示されている場合は、エラーログで原因を確認します。
step7.trouble: 配信が止まる場合は、抽出・解析が終わっているか、配信先が登録されているかを確認します。
exceptions.item4（追加）: 設定済みの端末からの自動取込も、この流れにつながります。自動解析・自動配信は、それぞれの設定が有効な場合に動きます。

exceptionsは4項目表示へ変更。未実装機能の案内を作らないという設計制約は文書に残し、画面には利用者の行動だけを載せる。
DB/配線SSOT/金型/文言t参照は継続。新しい業務動作は追加しない。

手順1 正式カードチェック
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && bash scripts/card-lint.sh docs/handoff/pipeline-procedure-map/CARD-LINE-GUIDE-02.md

手順2 前述の確定修正をSolが実装する

許可対象は前便のlocale2件、GuidePanel、unit/E2E、台帳/tasks/evidence。CSSは既存設計範囲のみ。
編集は正式起動cwdのapply_patchを使用。ガード拒否は原因とともに停止報告し、別手段に切り替えない。

手順3 依存準備と試験
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide/frontend && npm ci
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide/frontend && npm run check:all
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide/frontend && npm run build
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide/frontend && npm run test:unit -- src/pages/super-admin/components/LineWorkflowGuidePanel.test.tsx src/features/tcg-import-workflow/ImportWorkflowPanel.test.tsx
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide/frontend && npm run test:e2e -- tests-e2e/analysis-rules-line-guide.spec.ts --project=chromium

依存が既に準備済みならnpm ciは繰り返さない。lockfile変更は禁止。
通信/依存取得/localhost bindにsandbox権限が必要なら、その同一コマンドをrequire_escalatedの個別審査へ出すことを許可する。
設定・guard・trustは変更しない。審査拒否なら停止して理由を返す。ブラウザ実行体不足は既存test:e2e:installを許可する。
テスト失敗は期待値を弱めず原因を報告。前便concurrently不在は依存未導入として分類済みであり、本便npm ciで解消する。

手順4 検算・報告
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && git diff --check
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide && git status --short --untracked-files=all

期待値: 設計契約逸脱0、各試験exit0、7段階表示、ja/en、画面遷移実体、表示中書込0、狭幅横はみ出し0。
達成/未達を分けて本カード名付きでAstraへ報告し待機。停止時は手順番号・最後のコマンド・理由を添える。
生出力の秘密は除く。teeは使用しない。本番確認・CI・マージ未実施を明記する。

END OF CARD
