dc99a062e2c409aeb1a851a01b8bd0fa09ac3b64
# inbox thread part A recon raw (read-only research)
略記: CSS=frontend/src/pages/inbox/InboxPage.css TSX=frontend/src/pages/inbox/InboxMessageThread.tsx tok=frontend/src/tokens.css idx=frontend/src/index.css
注意: 行番号は origin/main dc99a062 時点。「直書き」「変数」は値の書き方。

## H. デザイントークン
--bubble-inbound-bg: #EFEFEF（ライト） / frontend/src/index.css:102 / 直書き（トークン定義）
--bubble-outbound-bg: #8B2EF5（ライト） / frontend/src/index.css:103 / 直書き（トークン定義）
--bubble-inbound-bg: #334155（ダーク :root.force-dark） / frontend/src/index.css:291 / 直書き
--bubble-outbound-bg: #6d28d9（ダーク） / frontend/src/index.css:292 / 直書き
--radius-bubble-out: 20.8px（Messenger outbound・Meta実測） / frontend/src/tokens.css:103 / 直書き
--radius-bubble-in: 20.8px 20.8px 20.8px 4.8px（テール付き） / frontend/src/tokens.css:104 / 直書き
--radius-2xs: 3px / frontend/src/tokens.css:94
--radius-xs: 2px / frontend/src/tokens.css:95
--radius-sm: 4px / frontend/src/tokens.css:96
--radius-md: 6px / frontend/src/tokens.css:97
--radius-lg: 8px / frontend/src/tokens.css:98
--radius-xl: 12px / frontend/src/tokens.css:99
--radius-badge: 10px / frontend/src/tokens.css:100
--radius-pill: 20px（入力欄の角丸・意味的例外） / frontend/src/tokens.css:101
--radius-full: 9999px / frontend/src/tokens.css:102
--space-1: 4px / frontend/src/tokens.css:74
--space-2: 8px / frontend/src/tokens.css:75
--space-3: 12px / frontend/src/tokens.css:76
--space-4: 16px / frontend/src/tokens.css:77
--space-5: 20px / frontend/src/tokens.css:78
--space-6: 24px / frontend/src/tokens.css:79
--space-8: 32px / frontend/src/tokens.css:80
--space-9: 36px / frontend/src/tokens.css:81
--space-10: 40px / frontend/src/tokens.css:82
--space-12: 48px / frontend/src/tokens.css:83
--space-1px: 1px / frontend/src/tokens.css:86
--space-2px: 2px / frontend/src/tokens.css:87
--space-3px: 3px / frontend/src/tokens.css:88
--space-6px: 6px / frontend/src/tokens.css:89
--space-10px: 10px / frontend/src/tokens.css:90
--space-14px: 14px / frontend/src/tokens.css:91
--font-2xs: 0.7rem(11.2px) / frontend/src/tokens.css:13
--font-xs: 0.75rem(12px) / frontend/src/tokens.css:14
--font-sm: 0.85rem(13.6px) / frontend/src/tokens.css:15
--font-base: 0.9rem(14.4px) / frontend/src/tokens.css:16
--font-md: 1rem(16px) / frontend/src/tokens.css:17
--font-lg: 1.1rem(17.6px) / frontend/src/tokens.css:18
--font-xl: 1.25rem(20px) / frontend/src/tokens.css:19
--font-title-mobile: 1.3125rem(21px) / frontend/src/tokens.css:20
--font-2xl: 1.5rem(24px) / frontend/src/tokens.css:21
--font-3xl: 2rem(32px) / frontend/src/tokens.css:22
--font-sidebar-brand: 1.6rem / frontend/src/tokens.css:25
--font-display: 1.6rem / frontend/src/tokens.css:26
--font-weight-normal: 400 / frontend/src/tokens.css:29
--font-weight-medium: 500 / frontend/src/tokens.css:30
--font-weight-semi: 600 / frontend/src/tokens.css:31
--font-weight-bold: 700 / frontend/src/tokens.css:32
--line-height-tight: 1.25 / frontend/src/tokens.css:35
--line-height-base: 1.5 / frontend/src/tokens.css:36
--size-icon-btn: 36px（SSoT: ADR-067） / frontend/src/tokens.css:166
--size-icon-btn-sm: 28px（ピル内インライン） / frontend/src/tokens.css:167
--size-icon-btn-lg: 44px（モバイルタッチ WCAG 2.5.5） / frontend/src/tokens.css:168
(関連) --field-h-sm 28px / frontend/src/tokens.css:169 ; --field-h-md 36px :170 ; --field-h-lg 44px :171 ; --field-h-tap 48px :172
(関連) --textarea-min-h: 80px / frontend/src/tokens.css:181
(関連) --size-thread-avatar: 36px / frontend/src/tokens.css:421
(関連) --size-avatar-sm: 32px / frontend/src/tokens.css:241
(関連) --send-top-row-padding: var(--space-10px) var(--space-10px) var(--space-6px) / frontend/src/tokens.css:290
(関連) --opacity-muted: 0.7 / frontend/src/tokens.css:269 ; --opacity-disabled: 0.6 :274
(関連) --comp-btn-height-lg 48px :472 ; --comp-btn-height-auth 52px :473 ; --comp-btn-radius var(--radius-md) :476 ; --comp-btn-radius-pill var(--radius-full) :477（すべて frontend/src/tokens.css）
(関連) --comp-input-radius: var(--radius-full) / frontend/src/tokens.css:495 ; --comp-textarea-radius: var(--radius-xl) / frontend/src/tokens.css:496
(関連) --neutral-bg: #e2e8f0 / frontend/src/index.css:114 ; ダーク #334155 / frontend/src/index.css:303
--line-height-* のうち吹き出しは使わず直書き 1.45（CSS:508）。--bubble-* に padding/font/line-height 系トークンは無い
スマホ(<=767px)でトークンを上書きする仕組み: 未発見。tokens.css の @media は 595 行 (max-width: 1279px) の :root 内 --schedule-allday-row-h のみ / frontend/src/tokens.css:595-599。index.css に @media なし。--bubble-* --radius-* --space-* --font-* --size-icon-btn* を @media 内 :root で上書きする箇所は未発見
スマホの上書きの実際のやり方: クラスごとに @media (max-width: 767px) 内で個別に値や var を差し替える / frontend/src/pages/inbox/InboxPage.css:1112 以降
ブレークポイント定義（参照専用）: --breakpoint-mobile-max 767px 他 / frontend/src/tokens.css:117-121 ; JS は constants/breakpoints.ts（中身は未読）

## I. 金型
Textarea 金型: TextareaControl（forwardRef 裸 textarea） / frontend/src/components/Textarea.tsx:45 / variant: standard|karte|embedded|composer|schedule|product-edit（:32）, size: sm|md|lg（standard のみ・:18）, textStyle: normal|code（:35）
Textarea 基本 CSS: .comp-field__textarea 幅100% padding var(--space-2) var(--space-3) border 1px border-radius var(--comp-textarea-radius) font-size var(--font-base) line-height var(--line-height-base) min-height var(--textarea-min-h) resize vertical / frontend/src/components/FormField.css:48-69 / 変数
Textarea embedded variant CSS: min-height auto padding 0 border none border-radius 0 background transparent line-height 1.4 resize none outline none / frontend/src/components/FormField.css:286-296 / line-height 1.4 は直書き、他は値直書き(0/none)
Textarea embedded disabled: opacity var(--opacity-disabled) / frontend/src/components/FormField.css:303-307
Textarea スマホの @media: frontend/src/components/FormField.css:535-541 は .comp-field__input/.select/.comp-select__control の min-height のみ。textarea には効かない
Button 金型: Button / frontend/src/components/Button.tsx:43 / props: variant primary|secondary|ghost|danger|outline|tab (:7), size sm|md|lg|tap|auth (:8), shape default|pill (:9), fullWidth, loading, active, iconOnly(aria-label必須), layoutClassName（:25-39）。className と style は受けない（:41 Omit）
Button 基本 CSS: .comp-btn min-height var(--field-h-md) padding var(--space-2) var(--space-5) border-radius var(--comp-btn-radius) font-size var(--font-base) line-height var(--line-height-tight) / frontend/src/components/Button.css:2-18 / 変数
Button sm: min-height var(--field-h-sm) padding var(--space-1) var(--space-3) font-size var(--font-xs) / frontend/src/components/Button.css:40-44
Button icon-only: width/height/min-height var(--size-icon-btn) padding 0 / frontend/src/components/Button.css:149-155 ; sm は --size-icon-btn-sm :157-161 ; lg と tap は --size-icon-btn-lg :163-173
Button スマホ @media(<=767px): .comp-btn min-height var(--size-icon-btn-lg), icon-only は 44px / frontend/src/components/Button.css:175-193
Button pill: border-radius var(--comp-btn-radius-pill) / frontend/src/components/Button.css:196-198。ログイン画面だけ（Button.tsx:28、buttonShapeUsage.test.ts が強制）
IconButton という名前の金型: 未発見（components 直下に IconButton.tsx なし）。近いもの = IconToggleButton / frontend/src/components/IconToggleButton.tsx:44 / props: pressed, onClick, iconOff, iconOn, aria-label, size sm|md, variant default|badge, disabled, count（:21-37）
IconToggleButton CSS: sm = min-width/height var(--size-icon-btn-sm) border-radius var(--radius-full) ; md = var(--size-icon-btn) / frontend/src/components/IconToggleButton.css:12-30
入力欄の金型使用: TextareaControl variant="embedded" className="inbox-textarea" rows={2} / frontend/src/pages/inbox/InboxMessageThread.tsx:782-796（import :20）
送信ボタンの金型使用: 金型を使わない生 <button className="inbox-send-btn"> / frontend/src/pages/inbox/InboxMessageThread.tsx:835-852
添付ボタンの金型使用: 金型を使わない生 <button className="send-attach-btn"> / frontend/src/pages/inbox/InboxMessageThread.tsx:810-820
英訳ボタン: 生 <button className="inbox-translate-outbound-btn"> / frontend/src/pages/inbox/InboxMessageThread.tsx:822-833
Button 金型の使用箇所（送信エリア内）: エラー行の CTA だけ <Button variant="secondary" size="sm"> / frontend/src/pages/inbox/InboxMessageThread.tsx:737-751
IconToggleButton の使用: import のみ確認 / frontend/src/pages/inbox/InboxMessageThread.tsx:18 ; 使用行は未確認
アイコン: INBOX_ACTION_ICONS.attach size={ICON.md} :820 ; .send size={ICON.base} :850 ; ICON は constants/iconSizes（値は未読）

## J. 上書き（frontend/src 全体 grep。InboxPage.css 以外は FormField.css の 1 行コメントのみ）
.inbox-messages: padding var(--space-4) gap var(--space-2) flex column overflow-y auto / frontend/src/pages/inbox/InboxPage.css:488-497 / 変数
.inbox-msg-row: display flex ; .outbound は flex-end ; .inbound は flex-start / frontend/src/pages/inbox/InboxPage.css:498-500
.msg-stack: max-width 70% / frontend/src/pages/inbox/InboxPage.css:502 / 直書き
.msg-stack スマホ: max-width 85% / frontend/src/pages/inbox/InboxPage.css:1173 / @media (max-width: 767px)（開始 :1112）/ 直書き
.msg-bubble: max-width 70% padding var(--space-2) var(--space-3) font-size var(--font-md) line-height 1.45 word-break/white-space pre-wrap / frontend/src/pages/inbox/InboxPage.css:504-511 / 70% と 1.45 は直書き
.msg-bubble.outbound: background var(--bubble-outbound-bg) color var(--on-accent) border-radius var(--radius-bubble-out) / frontend/src/pages/inbox/InboxPage.css:513-517
.msg-bubble.inbound: background var(--bubble-inbound-bg) color var(--text-primary) border-radius var(--radius-bubble-in) / frontend/src/pages/inbox/InboxPage.css:519-523
.msg-bubble.failed: danger 系 2px border radius var(--radius-xl) / frontend/src/pages/inbox/InboxPage.css:524-529 / 2px 直書き
.msg-bubble.outbound スマホ: background var(--accent) / frontend/src/pages/inbox/InboxPage.css:1312 / @media (max-width: 767px)（コメント 1304-1311「紫はスマホでは使わない。PC は ADR-064 の範囲なので触らない」）
.msg-bubble.inbound スマホ: background var(--neutral-bg) / frontend/src/pages/inbox/InboxPage.css:1313 / 同上。border-radius はスマホでも --radius-bubble-* のまま
.msg-time: font-size var(--font-2xs) opacity var(--opacity-muted) margin-top var(--space-1) text-align right ; .inbound は left / frontend/src/pages/inbox/InboxPage.css:530-536
.inbox-msg-row.inbound .msg-stack: align-items flex-start ; .outbound は flex-end / frontend/src/pages/inbox/InboxPage.css:1935-1936
.msg-stack .msg-bubble: max-width 100% min-width 0 / frontend/src/pages/inbox/InboxPage.css:1937 / 直書き
.msg-bubble-line: flex gap var(--space-1) / frontend/src/pages/inbox/InboxPage.css:1940-1946 ; ハート表示 :1949-1966（@media (hover: hover) :1961）
.inbox-msg-row.outbound .msg-reactions: justify-content flex-end / frontend/src/pages/inbox/InboxPage.css:1976
入力欄の帯の class 名（TSX 確認）: 外側 "inbox-send-area sticky-bottom-bar" / frontend/src/pages/inbox/InboxMessageThread.tsx:724 ; 内側 "send-card" :759 ; 行 "send-top-row" :775 ; 入力ラップ "send-input-wrap" :779
.inbox-composer: 該当 class は未発見（TSX・CSS とも 0 件）。入力欄の帯は .inbox-send-area
.inbox-send-area: padding var(--space-1) var(--space-3) var(--space-3) / frontend/src/pages/inbox/InboxPage.css:594-596 ; position sticky 等は .sticky-bottom-bar（frontend/src/pages-layout.css:140-146: sticky bottom 0 background var(--bg-surface) z-index var(--z-base)）
.send-card: background var(--bg-surface) border 1px var(--border) border-radius var(--radius-xl) overflow hidden / frontend/src/pages/inbox/InboxPage.css:598-605
.send-top-row: flex align-items flex-end gap var(--space-2) padding var(--send-top-row-padding) / frontend/src/pages/inbox/InboxPage.css:607-612
.send-input-wrap: background var(--bg-subtle) border-radius var(--radius-pill) padding var(--space-2) var(--space-14px) flex align-items center gap var(--space-1) / frontend/src/pages/inbox/InboxPage.css:614-624
.inbox-textarea: flex 1 min-width 0 / frontend/src/pages/inbox/InboxPage.css:625-628
.send-attach-btn: width/height var(--size-icon-btn-sm) radius var(--radius-full) transparent / frontend/src/pages/inbox/InboxPage.css:630-644 ; hover :645 ; disabled :650。スマホの上書きは無い（1176-1186 のコメントで「ピル内の28pxは触らない」と明記）
.inbox-send-btn: width/height var(--size-icon-btn) border-radius 50% background var(--accent) color var(--on-accent) / frontend/src/pages/inbox/InboxPage.css:709-723 / 50% 直書き
.inbox-send-btn スマホ: width/height var(--size-icon-btn-lg)(44px) / frontend/src/pages/inbox/InboxPage.css:1190-1193 / @media (max-width: 767px)
.inbox-send-btn disabled: background var(--bg-active) color var(--text-secondary) / frontend/src/pages/inbox/InboxPage.css:726-730
InboxPage.css の @media 一覧: (max-width: 1279px) :1000 ; (max-width: 767px) :1112 ; (max-width: 560px) :1687 ; (hover: hover) :1961
.inbox-send-area .send-card 等へのタブレット(1279px)ブロック内の規則: 未確認（1000-1111 は未読）
CSS Modules・styled・インライン style で上記 class を指す箇所: grep では InboxPage.css 以外 0 件。TSX のインライン style は conv-avatar だけ（TSX:776）

## K. スマホと PC の出し分け
アプリ全体の Shell 切替: ShellSwitch が useIsMobile() で MobileShell / DesktopShell を返す / frontend/src/App.tsx:132-142（import :8-9）
useIsMobile: matchMedia (max-width: BREAKPOINTS.MOBILE_MAX px) / frontend/src/hooks/useIsMobile.ts（ADR-137 参照のコメントあり）
Shell 部品: frontend/src/components/MobileShell.tsx（冒頭コメント :4 「ADR-137: MobileShell は DesktopShell（Layout.tsx）とは独立した DOM」）; frontend/src/components/DesktopShell.tsx
受信箱ページ内: isMobile なら InboxConversationListMobile、それ以外は InboxConversationList / frontend/src/pages/inbox/InboxPage.tsx:188-192
会話の画面（本体）: スマホと PC で同じ InboxMessageThread を使う / frontend/src/pages/inbox/InboxPage.tsx:194（1 箇所のみ）
会話ヘッダだけ出し分け: isMobile ? InboxThreadHeaderMobile : 従来 <header className="inbox-center-header"> / frontend/src/pages/inbox/InboxMessageThread.tsx:400-418（useIsMobile は :106）
メッセージ一覧・吹き出し・送信エリアの TSX（:522 以降）: isMobile 分岐なし。同一 TSX で CSS の @media だけで差が出る（isMobile の参照は TSX:106 と :400 の 2 件のみ）
スマホ専用部品: frontend/src/pages/inbox/InboxThreadHeaderMobile.tsx ; InboxConversationListMobile.tsx
吹き出し部分の TSX 行: .inbox-messages :522 ; .inbox-msg-row :553 ; .msg-stack :554 ; .msg-bubble-line :555 ; .msg-bubble :559 ; .msg-time :635

## L. 決まりと点検
ADR-137 の取り違え注意: docs/adr に ADR-137 は 3 本あるが題は FedEx ETD / nginx 反映 / v_company_stats で、Shell 分離の本文ではない（docs/adr/README.md:154-156）。コードと ADR-140 が「ADR-137（Adaptive Shell Architecture: DesktopShell/MobileShell 分離）」と呼ぶ本文は docs/adr 配下に未発見 → 未確認
ADR-140: DesktopShell/MobileShell 分離で PC 側影響なし / docs/adr/ADR-140-mobile-nav-bottom-tabs.md:9,19,46
ADR-064: 吹き出し・入力欄・金型の条文なし。トークン条は --inbox-separator と --inbox-hover の 2 つだけ / docs/adr/ADR-064-inbox-meta-exact-replica.md:34-45。追記で「区切り線・hover・パネル幅・padding の記述は現実装と異なり根拠にしてはならない。アバター48pxのみ有効」/ :96,:117。実装の正は現コードと design.md §10 / :117
ADR-064 の本文: Meta 実測のカラートークン化（方向）。Status Accepted のまま / :6-8, :122
ADR-067: トークンを唯一の真実とし逸脱を CI と ESLint で止める / docs/adr/ADR-067-design-token-enforcement.md:21
ADR-067: 2層（tokens.css=色以外 / index.css=色） / :38-42
ADR-067: 新規トークンは手順どおり。色は :root と :root.force-dark の両方 / :128-133
ADR-067: コンポーネントトークン表に --size-thread-avatar 36px / :62
ADR-067: Inbox 専用カラートークン表に --inbox-separator 等。--bubble-* は表に無い / :137-144
ADR-067: npm scripts check:css-colors, check:css-var-fallbacks, check:css-values, check:dark-parity, check:stylelint, check:all / :103-112
ADR-067: 許可される例外（% 文字列、@media の値、calc、opacity 0/1、min-width 0、gap の数値は対象外） / :116-124
ADR-067 の @media 条文: 「CSS 変数は @media 条件式で使用不可。constants/breakpoints.ts と tokens.css で値を同期管理」/ :119
ADR-144: pages/ は原則 components/ の金型を使う / docs/adr/ADR-144-ui-component-governance.md:31
ADR-144: 禁止対象は生 select・生 input(text/search/省略)・自作タブ・色直値/生px インライン。生 textarea・生 button は禁止表に無い / :34-39
ADR-144: ゲートは scripts/check-ui-governance.js（pages/**/*.tsx の BASE/HEAD 件数比較・増えたら赤） / :41-48
ADR-144: 例外口 {/* ui-allow: <理由> (#<課題番号>) */}（理由と番号が必須） / :47-48
ADR-144: 色ゲートは ADR-067 の ESLint（eslint.config.js:40-115）に統合 / :50-54
ADR-144: className/.css 内の直値は check:css-colors / check:css-values が担当 / :56-57
ADR-144: 金型が無いときは実装を止め PO に報告、許可後に Xxx.tsx+Xxx.css(var()のみ)+Xxx.stories.tsx で新設 / :59-64
ADR-144 改訂案（Proposed・2026-09-10）: ui-allow 廃止・全件検査へ置換・共通UIへの自由な style/className と利用先CSSからの所有外観上書きを検出 / :108-128
ADR-144 追記: checkbox（:130-140）と radio（:142-148）を種別に追加。種別は 5 つ
WhatsApp 実測 帯（画面1080x2340px・480dpi・px÷3=dp） / docs/specs/design-system/visual-language/benchmark/whatsapp-conversation.md:8
whatsapp-conversation.md:121-125: 吹き出しの行 1080x128px = 360x42dp ; 全幅 ; 長押し可
whatsapp-conversation.md:131-139: 入力欄の帯 360x56dp ; 入力枠 286x48dp ; 絵文字 48x48 ; 添付 48x48 ; カメラ 48x48 ; 送信/音声 48x48 ; 文字欄 142x32dp
whatsapp-conversation.md:141: 入力欄の操作ボタンはすべて 48x48dp
whatsapp-conversation.md:95-103: input_layout_content 287x48 ; emoji 144px=48dp ; entry 428x97px=143x32dp ; attach 48dp ; camera 48dp ; send_container 48dp
whatsapp-conversation.md:111-115: 色（最頻色）上部バー #0a1014 / #f7f8fa ; 本文 #0a1014 / #20272b ; 入力帯 #0a1014 / #20272b ; 最下部 #000000 / #20272b（吹き出し専用の色の行は無い）
whatsapp-reproduction-spec.md:99: 入力欄の帯 高さ 55.7dp
whatsapp-reproduction-spec.md:100: 丸い入力枠 286.7x48.3dp ; 余白 左8 右4 上3.3 下4 dp
whatsapp-reproduction-spec.md:101: 絵文字48（左端）→ 文字欄 142.7x32.3dp（左48・上7.7）→ 添付48 → カメラ48（右端）
whatsapp-reproduction-spec.md:102: 送信ボタンは枠の外。buttons 51.3dp の中に 48dp のボタン。右6dp 上2.3dp
whatsapp-reproduction-spec.md:103: 文字欄の高さ 32.3dp（上下に約8dp）
whatsapp-reproduction-spec.md:108-114: 吹き出しの構造（conversation_row_text 360x42.7dp ; main_layout 101x32.7dp 左17 上5 右242 下5 ; message_text 62x28.7dp 余白2 ; date_wrapper 35x16.3dp 左64 上14.3 ; date 23x16.3dp 左右6）
whatsapp-reproduction-spec.md:120-125: 行は全幅360x42.7dp ; 吹き出しは中身に合わせて縮む（例101dp幅・行の左から17dp）; 上下余白5dp ; 本文の内側余白2dp ; 時刻は吹き出しの中の右下に同じ行（左64 上14.3 高16.3dp 左右6dp）; 本文の右に37dp空けて時刻
whatsapp-reproduction-spec.md:49-61: 上部バー 56dp ; 戻る 48 ; 顔写真 48
whatsapp-color-structure.md:31: 強調色は画面の 1.5〜1.7%。送信ボタン・未読バッジ・選択中の印だけ。面として広く塗らない
whatsapp-longpress-menu.md:124: 選択中の吹き出し y=1720〜1848 の色 #11442c / #20272b
whatsapp-ux-behavior.md:118-119: キーボードで入力枠・各ボタンは同量移動・大きさ不変 ; 吹き出しは 155dp 上へ移動
whatsapp-ux-behavior.md:141,160,168: 吹き出し長押し→選択モード（上部バーだけ置換）; 0件の会話は吹き出し0個
文字サイズ（sp）・時刻の文字サイズ・吹き出しの角丸・吹き出しの色コード・送信ボタンの色: WhatsApp 実測に見つからず → 未確認（全 whatsapp-*.md を吹き出し/バブル/角丸/送信/時刻で grep。whatsapp-reproduction-spec.md の 3 章以外の本文は全文読んでいない）
スマホ版 reproduction-spec の言及: CSS コメント CSS:1159-1160 が whatsapp-reproduction-spec.md §2 を参照
点検 script と workflow:
  frontend/package.json:17 check:css-colors → frontend/scripts/check-css-hardcoded-colors.js（hex 直書き検出・変数定義ファイルは除外 :19）
  frontend/package.json:18 check:dark-parity → frontend/scripts/check-dark-parity.js
  frontend/package.json:20 check:css-var-fallbacks → frontend/scripts/check-css-var-fallbacks.js
  frontend/package.json:21 check:css-values → frontend/scripts/check-css-hardcoded-values.js（opacity/border-radius/z-index の数値）
  frontend/package.json:40 check:new-tokens → frontend/scripts/check-new-tokens.js
  frontend/package.json:41 check:stylelint → stylelint "src/**/*.css"
  frontend/package.json:42 check:css-class-naming → frontend/scripts/check-css-class-naming.js
  frontend/package.json:30 check:breakpoint-sync / :31 check:mobile-responsive-structure2 / :36 check:color-token-sync
  frontend/package.json:46 check:all（上記の連結）
  scripts/check-design-token-ratchet.sh（ページ側 hex ベタ書きの新規増加を止める・BASE_SHA/HEAD_SHA 必須）← .github/workflows/design-token-guard.yml:20
  .github/workflows/frontend-check.yml:53 check:new-tokens ; :60 audit:unused-tokens（非ブロック）
  .github/workflows/design-token-audit.yml（週次・未使用トークン監査 scripts/check-unused-tokens.js）
  scripts/check-ui-governance.js ← .github/workflows/ui-governance-gate.yml（ジョブ名 UI governance gate・main の ruleset 15777895 の必須チェックと ADR-144:139 に記載）
  ui-allow: 上記 ui-governance-gate が対象。生 button・生 textarea は検出種別外（ADR-144:34-39）
  ESLint のインライン style 数値禁止: eslint.config.js:40-115（ADR-144:53 記載。ファイルの中身は未読）
  CI 上で .css の --bubble-* や .msg-bubble の直書きを個別に禁じる規則: 未発見
  workflow-lint.yml 他の workflow 全一覧は先頭 60 件のみ確認 → 残りは未確認

## M. 試験（InboxMessageThread を参照するもの）
frontend/src/pages/inbox/InboxMessageThread.discordSendError.test.tsx
frontend/src/pages/inbox/useInboxState.autoSelectBadge.test.tsx
frontend/tests-e2e/inbox-header-menu.spec.ts
frontend/tests-e2e/visual-language/inbox-baseline.spec.ts
frontend/tests-e2e/visual-language/inbox-single-column.spec.ts
frontend/tests-e2e/visual-language/inbox-helpers.ts
(名前に InboxMessageThread を含むが inbox 外) frontend/src/components/DataTable.test.tsx ; frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx ; frontend/src/features/tcg-analysis-review/SourceRawPane.test.tsx ; frontend/src/constants/icons.tsx（文字列一致のみ。中身は未確認）
stories: InboxMessageThread を直接使う stories は未発見。frontend/src/pages/inbox/InboxPage.stories.tsx（InboxPage.css を import :10）と InboxHeaderMenu.stories.tsx は InboxMessageThread の名前を含まない（中身は未読）
MessageReactionBadges.test.tsx / useInboxState の別 test は吹き出し周辺（未読）
msg-bubble 等の class を見る試験: frontend/tests-e2e/visual-language/ 配下を class 名で grep していない → 未確認

## N. 未確認の一覧
1. ADR-137「Adaptive Shell Architecture」本文の場所（docs/adr の ADR-137 は 3 本とも別題）
2. スマホで --bubble-* 等のトークンを @media 内 :root で上書きする仕組み（見つからず。クラス単位の上書きのみ確認）
3. InboxPage.css:1000-1111（1279px ブロック）内の送信エリア・吹き出し関連規則
4. IconToggleButton の TSX 使用行、ICON の数値、constants/breakpoints.ts の中身
5. WhatsApp 実測の文字サイズ・時刻の文字サイズ・吹き出しの角丸と色コード・送信ボタン色
6. tests-e2e の吹き出し/入力欄の class を検査する行
7. .inbox-composer は存在しない（0 件）
8. eslint.config.js の中身、workflow 全件
9. 本ファイルはコードの読み取りのみで、実画面・実機の寸法は未測定
