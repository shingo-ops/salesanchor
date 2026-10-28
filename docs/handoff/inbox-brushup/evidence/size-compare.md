# 受信箱 サイズ比較（読み取りのみ・px換算 1単位=4px）

注記: chatwoot/zernio には「スマホ専用レイアウト」が無く、幅の切替点で値が変わる。SA は ≤767px をスマホ、それ以外を PC とした。
計算値＝コードのクラスから私が足し算した値（実測ではない）。SA の行は origin/main の frontend/src 配下（InboxPage.css 等）。
パス略記: cw=chatwoot app/javascript/dashboard、zu=zernio src、fd=WhatsAppClone src

| 部位 | chatwoot | zernio | WhatsAppClone | SA スマホ | SA PC |
|---|---|---|---|---|---|
| 1 ヘッダー帯の高さ | 96px（xl未満）/48px（xl=1280以上） cw/components/widgets/conversation/ConversationHeader.vue:118 | 56px zu/components/thread/thread-header.tsx:46 | 64px fd/components/Chat/ChatHeader.tsx:80 | 56px InboxPage.css:2133-2143, tokens.css:177 | 最小81px、padding12/16 InboxPage.css:430-439 |
| 2 ボタン タップ寸法/アイコン | ⋯ 32px（ButtonV4 sm）/アイコン約14px（text-smの1em。アイコン既定サイズは未確認） MoreActions.vue:103-111, components-next/button/Button.vue:166 | 戻る 36px/16px thread-header.tsx:49-54 | アイコン20px。ボタン枠なし（アイコン自体がクリック対象＝20px） ChatHeader.tsx:136,144,154 | 戻る48px/16px、カルテと⋯は44px/20px InboxPage.css:1161-1172, InboxThreadHeaderMobile.tsx:131,167,179, tokens.css:163,467 | 36px/20px InboxPage.css:465-473 |
| 3 ヘッダー アバター/名前 | 32px、名前14px・medium ConversationHeader.vue:131,138 | 36px、名前14px・medium（補助12px） thread-header.tsx:56,63,70 | 40px、名前14px・semibold（補助12px） ChatHeader.tsx:102,112,115 | 48px、名前16px・700 InboxPage.css:288-289, 2163-2165 | 名前16px・700 InboxPage.css:440-443（アバターは未確認） |
| 4 一覧の行 | 高さ約70px（計算値）、アバター32px、名前14px(unread semibold/他medium)、本文14px、時刻10px cw/components/widgets/conversation/ConversationCard.vue:132,149,182,198,220; tailwind.config.js xxs | 最小68px、アバター44px、名前14px・semibold、本文12px、時刻11px zu/components/conversation-list/row.tsx:56,64,80,84,90 | 高さ70px、アバター クラス h-15 w-15 は Tailwind 既定に無く寸法は未確認（画像指定は40）、名前 text-md は既定に無く未確認、本文12px、時刻12px fd/components/Chat/ChatListItem.tsx:80,92,103,106,118 | 最小76px、アバター48px、名前16px・600、本文12px、時刻12px InboxPage.css:1241-1243,288,1299-1302,364-366,352-353 | 最小92px、padding12、アバター48px、名前14.4px、本文12px、時刻12px InboxPage.css:253-259,330-340,364,352 |
| 5 吹き出し | 14px/行高22.4px、padding 16x12、角12px（尾2px）、最大512px components-next/message/bubbles/Text/Index.vue:91, Base.vue:57-59, Message.vue:117,121, tailwind.config.js | 14px、padding 12x8、角16px、最大70% zu/components/thread/message-bubble.tsx:216,256 | 14px、padding 横8・上4、角6px(rounded-md)、最大90%（sm以上70%、md以上50%） fd/components/Chat/MessageContainer.tsx:128 | 16px/行高1.45、padding 12x8、角20.8px（尾4.8px）、最大85% InboxPage.css:504-511,1173, tokens.css:98-99 | 同左だが最大70% InboxPage.css:502 |
| 6 入力欄 | 編集欄の最小80/既定120px、本文14px/行高1.65 ResizableEditorWrapper.vue:20-21, _base.scss:12-13 | 帯約75px（スマホ）/71px（PC）計算値、入力16px（sm=640以上は14px） zu/components/composer/composer.tsx:538,558,575 | 帯 py-2＋入力欄高さ40px→約56px計算値、入力14px fd/components/Chat/MessageBar.tsx:78,106,113 | 入力欄約56px計算値（14.4px×1.4×2行+16）、入力14.4px、送信44px InboxPage.css:594-624,1190-1193, FormField.css:50-61,285-293（スマホ個別の文字サイズ上書きは見つからず） | 同左、送信36px InboxPage.css:709-711 |
| 7 ⋯メニュー | 項目高32px、文字14px、左右8px、最小幅136px components-next/dropdown-menu/DropdownMenu.vue:140,186,206,220 | 項目32px計算値、14px、左右8px、最小幅128px zu/components/ui/dropdown-menu.tsx:45,77 | 項目 py6+行高20=32px計算値、14px、左右8px、最小幅128px（ChatHeaderは w-56=224px指定） fd/components/ui/dropdown-menu.tsx:48,83; ChatHeader.tsx:158 | 項目最小44px、文字13.6px、左右14px、最小幅180px ContextMenu.css:7-42, tokens.css:163 | 同左（PCだけの別指定は未確認） |
| 8 モーダル | 幅最大448px、padding24、タイトル16px・medium、ボタン高40px components-next/dialog/Dialog.vue:84,135,140,156-173 | 幅最大512px（thread-pane.tsx:383は448px）、padding24、タイトル18px・semibold、ボタン高36px zu/components/ui/dialog.tsx:63,113; button.tsx:25-28 | 幅最大512px、padding24、タイトル18px・semibold、ボタン高40px（Cancel/Deleteは py-1 等の個別指定あり、実高は未確認） fd/components/ui/alert-dialog.tsx:46,69; button.tsx:20; ChatHeader.tsx:214 | 幅最大420px(sm)/既定600px(md)、padding 24、タイトル17.6px・600、ボタン44px。余白: 見出し20/24/16 本文20/24 フッタ16/24/20 Modal.css:21,42-45,56,61-67,76,89, Button.css:12,168-170, ConfirmModal.tsx:37 | 同左、ボタン36px |
| 9 連絡先パネル | 余白16、名前16px、情報行高20px/14px、項目 見出し14px・medium、値は指定なし(本文継承16px)、見出し下6px ContactInfo.vue:207,235; ContactInfoRow.vue:81,114; ContactDetailsItem.vue:12-14 | 無し | 無し | ラベル12px(大文字)、値13.6px・500、行padding 10px、行間2px、パネル幅396px、アバター40px InboxPage.css:797-822,1362-1379; tokens.css | 同左 |
| 10 本文の基準 | html/body指定なし→16px継承。pは14px/行高1.65 _woot.scss:21-39, _base.scss:12-13 | body文字サイズ指定なし→16px継承 globals.css:106-115。行高1.5は未確認 | body文字サイズ指定なし→16px継承 fd/styles/globals.css:75-77 | 本文14.4px基準、行高1.6 tokens.css:11-37, index.css | 同左 |

## 未確認一覧
1. chatwoot ⋯ボタンのアイコン既定サイズ（node_modules無し）
2. chatwoot 連絡先の値の文字サイズ（クラス指定なし、継承と読めるのみ）
3. zernio body 行高（Tailwind4 preflight）
4. WhatsAppClone 一覧のアバター h-15 w-15 の寸法
5. WhatsAppClone 一覧の名前 text-md の寸法
6. WhatsAppClone モーダルのボタン実高
7. SA PC ヘッダーのアバター寸法
8. SA PC のメニュー専用指定
9. SA スマホ入力欄の文字サイズ上書き有無（見つからず＝上書き無しとは断定せず）

## SA と参照3つの比較（事実のみ）
1 ヘッダー帯: スマホ56pxは zernio と同じ、chatwoot(96px)・WhatsApp(64px)より小さい。PCは81pxで全参照より大きい
2 ボタン: SAスマホ44-48pxは参照(32-36px)より大きい。SA PC 36pxは zernio戻る36pxと同じ
3 ヘッダー名前: SA 16px は参照の14pxより大きい。アバター48pxは参照(32-40px)より大きい
4 一覧行: SA高さ76/92pxは参照(68-70px)より大きい。アバター48pxは参照(32-44px)より大きい。本文12pxは zernio・WhatsApp と同じ、chatwoot(14px)より小さい。時刻12pxは参照(10-11px)より大きい
5 吹き出し: SA 16px は参照(14px)より大きい。角20.8pxは参照(6-16px)より大きい。最大幅はPC 70%が zernioと同じ
6 入力欄: SA入力14.4pxは chatwoot・WhatsApp(14px)より大きい。zernioスマホ16pxより小さい
7 ⋯メニュー: SA項目44pxは参照(32px)より大きい。文字13.6pxは参照(14px)より小さい。左右14pxは参照(8px)より大きい。最小幅180pxは参照(128-136px)より大きい
8 モーダル: SA幅 sm=420pxは参照(448-512px)より小さい。タイトル17.6pxは zernio・WhatsApp(18px)より小さく chatwoot(16px)より大きい。SAスマホのボタン44pxは参照(36-40px)より大きい
9 連絡先パネル: SAラベル12px・値13.6pxは chatwoot(14px)より小さい。zernio・WhatsAppは無し
10 本文基準: SA 14.4pxは参照(16px継承。pは14px)の間

## 追記（2026-10-29）: WhatsApp 本体の実測との照合

調べた人: 担当（Sonnet）が origin/main を読んだ。設計担当は `frontend/src/tokens.css:177,238,279` の3つを自分で確かめた。

- 記録の正本: `docs/specs/design-system/visual-language/benchmark/README.md`（Android 実機で WhatsApp を測った。PO 決定 2026-10-11: dp の値をそのまま px に使う）、寸法は同じ場所の `whatsapp-reproduction-spec.md`。
- 「Android 側で大きさを調整させた」という文言は記録に無い。記録にあるのは「Android で WhatsApp を測り、SA の画面の値をその数に合わせた」こと。

| 部位 | WhatsApp 実測 | 今の SA（スマホ） | 判定 |
|---|---|---|---|
| 一覧の行の高さ | 76dp | 76px（`--min-height-conv-item-mobile`） | 一致 |
| 一覧のアバター | 48dp | 48px | 一致 |
| 一覧の右余白 | 16dp | 16px | 一致 |
| 上の帯の高さ | 56dp | 56px | 一致 |
| 戻るボタン | 48dp | 48px | 一致 |
| 一覧の名前・時刻・本文 | 文字の大きさは測れていない | 16px・12px・12px | 比べられない |
| 吹き出しの角 | 約10dp＋尾 | PC と同じ値のまま | 不一致 |
| 吹き出しの余白 | 上下5・左17dp | 8px 12px | 不一致 |
| 吹き出しの中の時刻 | 本文と同じ行 | 吹き出しの下 | 不一致 |
| 入力欄の帯・枠の高さ | 55.7dp・48.3dp | スマホ用の指定なし | 不一致 |
| 送信ボタン | 48dp | 44px | 不一致（44px の基準を選んだ） |

- 【未確認】吹き出しと入力欄の指定が `frontend/src/pages/inbox/InboxPage.css` の外（会話の部品の別の CSS）にあるか。
- 今回の「⋯」メニューと統合の窓は、上の不一致の部位に触らない。
