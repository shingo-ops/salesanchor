# 幅375 検索欄 width 変化の原因調査（読み取り・計測のみ。commit なし）

計測: ay2p-measure の before（コミット HEAD のまま）と after（現変更）を別 outDir に開発モード build（dist-before・dist-after）、preview 4182/4183、w375-measure.cjs（CDP CSS.getMatchedStylesForNode＋getComputedStyle＋規則を外す実験）、w375-scroll.cjs。生データ: w375/w375-before.json、w375/w375-after.json、w375/scroll-*.txt。

## 1. 192 と 149 を決めているもの
【事実】computed（S2 contacts / S3 inventory）。どちらも min-width auto、flex-shrink 1、flex-grow 0、flex-basis auto、box-sizing border-box、max-width none。
| | before width | after width | specified width（CSS） |
|---|---|---|---|
| S2 | 149（computed width 149px） | 160 | 160 (field-w-sm) |
| S3 | 149 | 192 | 280 (field-w-md) |

- 規則: 幅は `.field-w-sm/md` の width（frontend/src/components/field-size.css:13-21。after は複合セレクタ :16/:19 が当たる）が指定値、そこから flex 縮小（flex-shrink:1）で縮み、床は min-width:auto（＝入力欄の内容ベースの最小幅）で決まる。明示的な min-width・flex-basis の CSS 規則は無い。
- 親: `.content-toolbar__left`（frontend/src/components/ContentToolbar.css:16-22）は display:flex、flex-wrap:nowrap、min-width:0、overflow は visible。`.content-toolbar`（:4-15）も nowrap、overflow visible。375 では .content-toolbar__left の中身が溢れる（S3: scrollWidth 396 → 439 / clientWidth 303、S2: 262 → 273 / 222）。
- 規則を外す実験（S3 after）: inline min-width:0 → 56.0（縮み切る）、flex-shrink:0 → 280（指定幅）、`field-w-md` クラスを外す → 56.0、`comp-field__input` クラスを外す → 149（before と同じ）。S3 before: inline min-width:0 → 56.0、flex-shrink:0 → 280、width:280px → 149（変わらない＝床で決まっている）。S2 after: inline width:280px → 192（S3 after と同じ値）、クラス `comp-field__input` を外す → 149。
- 【事実からの結論】192 と 149 は CSS の宣言値ではなく、フレックスの自動最小幅（min-width:auto＝入力欄の内容ベースの固有幅）。before は生 input の固有幅 149px（padding 0・枠2px・13.33px）、after は `.comp-field__input`（frontend/src/components/FormField.css:47-62 の padding space-2 space-3・枠1px・font-size font-base）が付くことで固有幅が 192px に増えた。S3 は指定 280 が床 192 より大きいので床の 192 まで縮む。S2 は指定 160 が床 192 より小さいので指定どおり 160（自動最小幅は min(内容幅, 指定幅) になるため）。S2 の 149→160 はこの結果で、S3 の 149→192 も同じ機構。
- 幅375 の min-height 44 は FormField.css:442-448（@media max-width 767px）。

## 2. 幅375 で inventory の「詳細フィルタ」・リセットは見えているか
| 要素 | before rect | after rect | before 可視 | after 可視 |
|---|---|---|---|---|
| 検索（inventory-search-btn） | left 185.0 right 233.2 | 228.0 / 276.2 | right≤375 かつ 幅 48.2 | 同 48.2 |
| リセット（inventory-reset-sort） | 245.2 / 315.5 | 288.2 / 358.5 | right≤375、可視幅 70.3（全部） | right≤375、可視幅 70.3（全部） |
| 詳細フィルタ（inventory-filter-toggle） | 327.5 / 420.0（right>375） | 370.5 / 463.0（right>375） | 可視幅 47.5（全幅 92.5 のうち約半分） | 可視幅 4.5（ほぼ画面外） |
- 【事実】詳細フィルタは before でも半分切れていた（47.5/92.5）。after は 4.5/92.5 で、ほぼ見えない。リセットは前後とも全部見える。
- 横スクロール: .content-toolbar と .content-toolbar__left は overflow visible でスクロールしない（scrollLeft を設定しても 0 のまま）。スクロールするのは祖先の `.page-layout-content`（frontend/src/pages-layout.css:90、overflow auto。scrollWidth before 420 / after 463、clientWidth 375）。scrollLeft を最大にすると before は 45、after は 88 動き、詳細フィルタは前後とも right=374.98 で全部見える（w375/scroll-*.txt）。document の scrollWidth は前後とも 375 で、ページ全体には横はみ出しなし（ページ内の領域がスクロールする）。
- スクリーンショット: w375/before-inventory-w375-full.png、w375/after-inventory-w375-full.png（contacts も同名規則）。

## 3. 幅375 の /inventory は別ページか
【事実】同じ InventoryPage。frontend/src/App.tsx:206 `<Route path="/inventory" element={<InventoryPage />} />` は ShellSwitch（App.tsx:136-139 の `isMobile ? <MobileShell /> : <DesktopShell />`、境界は useIsMobile＝frontend/src/hooks/useIsMobile.ts:15 の BREAKPOINTS.MOBILE_MAX＝767px）の子ルート。MobileShell は frontend/src/components/MobileShell.tsx:194 の `<Outlet />`、DesktopShell は frontend/src/components/DesktopShell.tsx:397 の `<Outlet />` で同じ要素を差し込むだけ。幅375 の計測でも祖先に main.mobile-content > div.mobile-shell があり、InventoryPage のツールバー（inventory-filter-toggle 等）が出ている。ページの置き換えはない。

## 4. after/inventory-w375-STOPPED.png
【事実】after/ にそのファイルは存在しない（find で確認）。STOPPED の png は before2/ にだけある: inventory-w1440-STOPPED.png（00:56:49）、inventory-w375-STOPPED.png（00:57:21）、companies-w1280/w1440-STOPPED.png（01:01:00/06）。作成元は ay2p-measure2.cjs:58（goto/waitForSelector が全リトライ失敗した時の保存）で、最初の before2 取得時に preview がまだ起動しておらず接続拒否だったときの残骸（古い run のファイル）。最終の before2 JSON には STOPPED は無く、15シナリオすべて計測済み。証跡コピーにも含めていない。
- 補足: before2/ 直下は同じ出力ディレクトリを上書きして再実行したため、上記4枚の古い STOPPED が残っている。

## 判断材料（結論は設計者）
- 原因は金型化による入力欄の固有幅増（149→192）で、ツールバーの nowrap・overflow visible の構造は前後同じ。toolbar を縮めない対処（例: 検索欄に min-width:0）は設計外の変更になるため行っていない。
