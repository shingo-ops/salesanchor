# フロントエンド13ボタン移管・再起動引き継ぎ

これは何か: 再起動後に、完了済みと未完を取り違えず作業を再開するための入口。
親: [recon](../recon.md) / [設計AH・AJ](../../../specs/design-system/design.md)

PO原文: 「再起動するからここまでを保存して記録してくれ」。新しい作業を停止して中断保存。**完成・設計の最終検収・本番反映の報告ではない。**

## 保存状態

- branch: release/frontend-shared-button-migration
- worktree: /Users/tanizawashingo/worktrees/salesanchor/release-frontend-shared-button-migration
- base: adc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b
- PR3435: MERGED、merge adc8bc4d、2026-09-11T09:07:09Z。CI38成功/8対象外、PO GO #3435を直接確認済み。
- 本便はPR未提出、番号付きGO未受領、マージ未実施。本店のAGENTS.mdと未追跡他者作業は触っていない。
- **現コードは6部品16利用の移管WIP。AJの5部品13利用へ絞る設計は保存済みだが、CommissionPanel.tsxの基準への復元は未実行。** 新CIは全画面統一の最後。

## 実施済みと未完

1. preflight成功。公式new-worktree.shで作成・台帳登録。npm ci成功（依存定義変更なし）。
2. 6TSXは退避基準から差分0を確認後、7原稿hash照合で復元。全体構文比較はButton70→86、旧先頭btn332→316、専用20/リンク8不変、6ファイルはimport/tag/class以外のAST差分0。保存原稿再実行exit0。
3. 退避テストのURL副作用をsubclass+終了後復元検査へ修正。売上/仕入/発送の新規POST追加。20操作単独試験は初回成功（67.53s）。root buildで配列at/APIError引数の型不適合4件を検出後、テストだけ実型へ修正し、厳格lintと20操作単独再試験成功（2.72s）。型修正後の全体buildは未実行。
4. root check:all成功。root buildは型修正前にexit2、Storybookは未実行。全体coverageはexit1（11failed files、21failed/188passed tests、worker未起動2files）。時間超過が多数。高負荷84.34等を観測したが原因を環境だけと断定しない。単独試験成功と全体合格を混同しない。
5. 初回browserはCommission390/enで輪郭欠けを検出。実表body幅390に対しscrollWidth528→537。旧から横overflow、今回約9px増加。実画像・全祖先rect/scrollLeft取得。初回原稿は左右のみ/ヘッダー混入という不足もあり、全体検収に採用しない。
6. 別inventory12条件のfailures0は強制スクロール後の個別ボタン収容だけ。初期欠けの解消や全条件合格を示さない。最長実Confirmラベル、全幅/明暗、実Tab等の最終検証は未完。Reviewerの最終APPROVEなし。

## 次に行うこと（順序）

1. このworktreeでpreflight、branch/status、origin/mainとPR状況を再確認。他者差分を戻さない。
2. 設計AJを読む。Commission3（BSA002/003/004）を表統一便へ保留し、残13を先行。**正式カードを作成・lintしてからGeneratorへ渡す。まだ分離カードは未発行。** Commissionの現在hash一致を確認し、基準adc8bc4dの当該1ファイル原文へ戻す。他5TSXと修正済みテストを保持。
3. 再監査目標: Button70→83、旧btn332→319、専用20・リンク8不変、Commission製品差分0。5TSXの全業務本文/残属性不変。現16利用の86/316をそのまま引用しない。
4. 対象13の初期横overflowと自然なキーボード到達後の輪郭を別測定。viewport/クリップ祖先の上下左右、対象数/IDを照合。明暗×日英×390/767/768/1279/1280と640px（200%相当、実zoomではない）、実Confirm長文・外部form・保存中を確認。強制スクロールで初期欠けを隠さない。
5. 最終製品でlint/unit/coverage/checkall/build/Storybook、限定第二レビュー。既存テストの失敗を単独再現で切り分け、設定・期待条件を緩和しない。
6. 証跡・移行台帳を更新しready PRを正式wrapperで提出。新PR番号付きGOを受領してから正式merge。PR3435のGOを流用しない。PO画面確認は完成後。

## 証跡の復元

同ディレクトリのah-restart-checkpoint.tar.gzに当該/tmp成果物、監査、限定レビュー、旧退避7案、再開カードと復元原稿を保存。ah-restart-archive-manifest.jsonは各保存ファイルのSHA256とarchive SHA256。既存/tmpを上書きせず別の一時ディレクトリへ展開し、原稿の絶対パスを対応させる。依存node_modulesは含めない。

既存担当: frontend_definition_audit=Generator、ci_preflight_readonly=限定Reviewer、overlay_contract_audit=読み取り構文監査。再起動後に同担当へ接続できるとは仮定しない。新担当を起動する場合はPOの既存委任範囲・カード運用を守る。
