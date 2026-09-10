# 共通部品の追加照合（担当報告）

読み取り担当 frontend_definition_audit / overlay_contract_audit の報告を設計担当が要約転記。製品・文書編集なし、テスト未実行。独立した設計審査ではない。設計worktree基準。目視はPOが完成後に担当。

## 入力・操作

- Button.tsx:20,36,47: 6variant/3size/native属性、ref転送なし。components.css:54とButton.css:17以降の2か所が外観を所有。
- TextField.tsx:18,26,43,64 / Textarea.tsx:17,25,42,63: 外側div必須、classNameはdivへ、styleは入力本体。ref転送なし。FormField.css:47/65。
- Select.tsx:17,23,53,68,103: 平坦なoptions。SelectControlは直接select、Selectはlabel付きdiv。FormField.css:80の矢印SVGに固定色がある。
- Tabs.tsx:25,37: items/activeKey/onChange、native属性を受け取る入口なし。Card.tsx:16,25,42: interactiveでもdivのままでキーボード操作は自動付与しない。Badge.tsx:16,20,54: native span属性を転送しない。
- ASTのnative button517、テスト等除外476。排他的な一次分類: tab3/menuitem8/option2/aria-pressed11/カレンダー5/行選択4/明示ナビ25/展開6/その他静的btn-*311/意味照合必要100。文字列条件による一次分類であり、意味が確定した移行表ではない。

個別契約が必要:
1. DataList.tsx:8、RolesPage.tsx:353の行全体ボタンは通常Buttonとは別用途。
2. SchedulePageImpl.tsx:488,611,635,681,696,785は日付/イベント/座標計算を保持。
3. InboxMessageThread.tsx:408、CountryCombobox.tsx:172、ChannelTypeCombobox.tsx:173のmenu/optionとonMouseDown.preventDefaultを保持。
4. OrdersPage.tsx:66,76の再クリック解除フィルターはTabsへ変換しない。
5. FedexEtdSetupGuide.tsx:102,107はcurrentTargetを使い、Tabs.onChangeのkeyだけでは不足。
6. InboxMessageThread.tsx:649,653,666のref/keydown/file入力を保持。入力の裸の本体とlabel付きwrapperを設計する必要。
7. InvoiceDetailPage.tsx:221,231、PaypalIntegrationPage.tsx:231,234はaリンクのhref/target/relを保持する共通外観経路が必要。
8. DashboardPage.tsx:494,509,523、FunnelSection.tsx:102等のキー処理はCard.interactive指定だけで代替不可。

## Modal・Drawer・EmptyState

使用数はTSXの部品名検索、stories/tests/design-preview除外。動的利用のAST網羅証明ではない。
- 通常Modal36使用/31ファイル、Drawer9使用/9ファイル、通常EmptyState製品使用0。
- loadingの同名3部品の直接/バレル使用0、ただしloading/index.ts:20-27に公開exportあり。
- 通常Modal.tsx:24必須title/string等、:49/60/69/82はfocus保存/初期移動/Esc/Tab、:112閉時unmount、:114Portal。
- 通常Drawer.tsx:22はfooter/fullpage、:45Portal先、:49-110focus/Esc/Tab、:125閉状態DOM維持、:132/145/156既存testid。
- loading/Modal.tsx:4のtitle/childrenは任意ReactNode、:27閉状態DOM維持。loading/Drawer.tsx:5/26も任意ReactNode/閉状態維持。通常への単純再exportは互換変更。
- EmptyState.tsx:18にsize/className、:50 icon aria-hidden、:52見出しp。loading側はsize/classNameなし、aria-hiddenなし、見出しspan。
- 通常3CSSとloading-animations.css:339-494が別の外観所有元。旧.modal-overlay/.modalはcomponents.css:472/483。
- tokens.css:125-128のbackdrop298/drawer301/modal400。Drawerコメント299は実値不一致。
- Modal/Drawerのheader/body/footer外観は集約候補。モバイルModal下寄せ90vh、Drawer全幅は用途差として保持。

保持する処理: FedExRateModal.tsx:140の閉じる前リセット、ConfirmModal.tsx:30-40のキャンセル/確定分離とautoFocus、PurchaseDetailPanel.tsx:299等のxl/footer、Drawer9使用中8のonOpenFullPage。
別途契約: InboxProfileModal.tsx:63とuseInboxState.ts:702-710の外部ref/focus/Esc、OutboundTranslationPreview.tsx:67-82の送信前確認、ParseReviewPage.tsx:865の棄却dialog、DesktopShell.tsx:423/ProductMasterDrawer.tsx:526/DistributionTargetForm.tsx:131の独自パネル。
未検証: Modal/Drawer同時表示のstackingとEsc、Drawer閉状態DOMのinert/aria-hidden欠落による影響、初回open時focus。コード構造の指摘であり再現済み不具合とは呼ばない。

全体設計の残件は意味別所有元、refと入力wrapper互換、未使用公開APIの扱い、独自overlayの既存動作、旧PRの採用範囲。数だけで移行可能や全体APPROVEにしない。
