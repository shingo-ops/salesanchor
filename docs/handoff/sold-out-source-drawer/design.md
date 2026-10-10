# AY-2j design: 完売の結果の原文を Drawer で開く・列の整理

正本は docs/specs/design-system/design.md の「#### AY-2j 完売の結果：原文を Drawer で開く・列の整理（2026-10-10）」節と「#### AY-2j 実装結果」節。本ファイルは PR 用の写し。recon は docs/handoff/sold-out-source-drawer/recon.md。対象 ADR は ADR-027（docs/adr/ADR-027-ui-internationalization.md）と ADR-144。
PO 決定（2026-10-10）: 2件とも「y」（recon.md の第2節）。

## 変更契約
1. 列を8本から6本にする（判定と原文表示を削除）。product_title 列に width "250px"。
2. Drawer を置き、DataTable に onRowClick を付ける。一覧を再取得するとき選択を null に戻す。
3. SourceDetail から details と summary を外す（中身は変えない）。
4. 試験を列の削除と Drawer に合わせて直し、it を1本追加する。
5. 変更しない: Drawer・DataTable の金型、CSS、トークン、i18n、soldOutApi.ts、backend、ほかの画面、CI、依存。

## 受入
|基準|検証方法|
|---|---|
|1行判定|開発モード build と preview、偽ログイン、API モックのダミー5行。幅1280と1440で、仕入元・数量・価格・投稿日・原文の状態のセルの行数が1（ay2j-oneline.json）|
|Drawer|行を押すと dialog に原文が出て mark で強調され、Esc で閉じる（ay2j-drawer.json、ay2j-drawer-1440.png、ay2j-list-1440.png、ay2j-list-1280.png）|
|試験|変えた expect と理由の一覧（design.md 末尾の AY-2j 実装結果、ay2j-test-diff.txt）|
|品質|generate 後の tsc、lint、check:all、test:coverage（maxWorkers=1）、build、build-storybook がすべて成功（ay2j-chk-*）|
|本番|Deploy 成功。app と /api/health が 200（merge 後）|

## 維持の仕組み
守り手: SoldOutResultsPanel.test.tsx、Drawer と DataTable の既存の試験、frontend-check。切戻しは本PRの merge commit を revert する（DB 影響なし）。

## 外部・過去事例の参照と我々への応用
外部事例: 不要（社内の金型 Drawer と onRowClick の前例をそのまま使う）。過去事例: AY-2i（PR #4112）。
