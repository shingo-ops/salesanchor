# AK 次便の登録・更新・取消ボタン調査

親: [recon](../recon.md) / [設計AK](../../../specs/design-system/design.md)。2026-09-13、固定main 739f772d4cf55c1b3972c02c086a7c77b807d293。設計担当rootの直接調査。新サブエージェント0、製品編集0。

## 観測事実

- 前便PR3442はmerge d66923e2、本番deploy34717188762成功。最新mainにはPR3438のTcgProductImportPanelのButton1個が追加され、共通数は83ではなく84。git diff d66923e2..739f772d -- frontend で確認。
- 同じTypeScript構文監査・除外規則で旧prefix319/専用20/リンク8。広い正規表現339を旧btn件数と呼ばない。3ページのform-actions直属buttonは12、うち旧btn10・クラスなし2。
- CompaniesPage.tsx:550/551、ContactsPage.tsx:350/351は新規作成のsubmittingに連動。CompaniesPage.tsx:298、ContactsPage.tsx:164に連投防止。仕入先作成と全編集には同じsubmitting指定がない。これを勝手に追加しない。
- POST/PATCH実物: CompaniesPage.tsx:219/301/315/320、ContactsPage.tsx:160/181/193/198、SuppliersPage.tsx:70/75/81/87。ID、空値→null、会社IDの数値化、会社電話検証、失敗表示と成功後close/reloadを変更しない。
- 配置owner: components.css:46のform-actions、company-forms.css:78/129/194のform-grid・全列span・768px以下の1列。Modal.tsx:142のbody、Drawer.css:83/104のbody padding・mobile全幅。今回はcomp-modal-footerではない。前便のfooter wrap成功を流用しない。
- Button.tsx:39/56/83はnative残余属性とdisabledを転送。既定typeを追加せず12件の既存typeを逐語保持。loadingを付けると状態と文言が変わるため追加禁止。Button.css:2/95/134の36px・mobile44px・輪郭width/offsetを継承。
- 既存tests-e2e/ui-companies-edit-modal-i18n.spec.tsは編集Modal・タブ前提の過去試験で、現Drawerの6フォームを網羅しない。既存試験があることを操作保証にしない。Button.test.tsxとSharedButtonMigration.test.tsxは共通部品と前便の確認で、今回のページ検収とは別。

| ID | 既存ID | 実物 | 変更後 | 保持する無効化 |
|---|---|---|---|---|
| AK-01 | 旧btn集合外の取消 | frontend/src/pages/companies/CompaniesPage.tsx:550 | secondary/md、type="button" | {submitting} |
| AK-02 | BSA-114 | frontend/src/pages/companies/CompaniesPage.tsx:551 | primary/md、type="submit" | {submitting} |
| AK-03 | BSA-115 | frontend/src/pages/companies/CompaniesPage.tsx:572 | secondary/md、type="button" | 指定なしを保持 |
| AK-04 | BSA-116 | frontend/src/pages/companies/CompaniesPage.tsx:573 | primary/md、type="submit" | 指定なしを保持 |
| AK-05 | 旧btn集合外の取消 | frontend/src/pages/contacts/ContactsPage.tsx:350 | secondary/md、type="button" | {submitting} |
| AK-06 | BSA-132 | frontend/src/pages/contacts/ContactsPage.tsx:351 | primary/md、type="submit" | {submitting} |
| AK-07 | BSA-133 | frontend/src/pages/contacts/ContactsPage.tsx:373 | secondary/md、type="button" | 指定なしを保持 |
| AK-08 | BSA-134 | frontend/src/pages/contacts/ContactsPage.tsx:374 | primary/md、type="submit" | 指定なしを保持 |
| AK-09 | BSA-393 | frontend/src/pages/suppliers/SuppliersPage.tsx:124 | secondary/md、type="button" | 指定なしを保持 |
| AK-10 | BSA-394 | frontend/src/pages/suppliers/SuppliersPage.tsx:125 | primary/md、type="submit" | 指定なしを保持 |
| AK-11 | BSA-395 | frontend/src/pages/suppliers/SuppliersPage.tsx:143 | secondary/md、type="button" | 指定なしを保持 |
| AK-12 | BSA-396 | frontend/src/pages/suppliers/SuppliersPage.tsx:144 | primary/md、type="submit" | 指定なしを保持 |


## 実行した確認と限界

構文監査は固定SHAの追跡原文のみ。ak-form-button-audit.jsonへ12要素の原文・全属性・祖先・3ファイルSHA256を保存。再現原稿のTypeScript解決先は本環境のmain/node_modulesであり製品依存を変更しない。

配置予備試験: 実CSS9ファイルと実ja/en翻訳を使用し、フォーム下部とModal/Drawer祖先を再構成。6フォーム＋会社/連絡先saving2状態 × 6幅(390/640/767/768/1279/1280) × ja/en × light/dark =192組、前後384表示。afterの文字欠け/本体欠け/有効ボタン周囲4px余白不足0。高さ36/44px確認。640pxは狭幅による200%相当で実zoomではない。

初回144条件の失敗は原稿の非行頭@import除去がtokens.css:3のコメントから宣言を削除していたことによる。行頭importだけの除去へ訂正。初回・訂正版の原稿と結果をarchiveへ保持。初回sandboxのChromium起動はmacOS MachPort権限で失敗し、通常の承認付き実行で起動した。ガード変更なし。

これは配置の実現性調査であり、実Reactページ・長い入力欄・ページCSS全体・API・Tab移動の検収ではない。ringFitsは現Button輪郭の4px空間の幾何検算で、実focus-visible検証ではない。実画面検収は設計AKの受入に残す。

再現: archiveを/tmpの専用ディレクトリへ展開し、node ak-raw-audit.cjs 固定SHA raw.json、node ak-form-audit.cjs リポジトリパス 固定SHA form.json raw.json、node ak-layout-probe.cjs 作業台パス probe.json。各引数は当該実在値へ設定する。archiveの8filehashはmanifest参照。

## 調査手段・未確認

新ライブラリ/新API仕様を採用しないため追加の外部事例・Context7仕様調査は不要。既存ButtonとローカルPlaywrightの実物で調査した。企業事例を成功証拠としない。実ページの保存/取消/フォーカスと最終ビルドは実装後に実行する項目であり本設計段階の成功とは数えない。


審査記録: design.md§AK末尾で同一AI Architect自己審査APPROVE。今回の実装承認・実ページ検収は未完。カード草案はak-page-form-card.txt、正式card-lint exit0（長行警告2件）。
