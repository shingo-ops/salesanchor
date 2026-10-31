7e91551634a8a6e06a11b5387b6d0a70a0e29f5b
# 受信箱スレッド 調査生データ（読み取りのみ・推測なし）
前提: パスは repo 直下からのフルパス。CSS=frontend/src/pages/inbox/InboxPage.css、TSX=frontend/src/pages/inbox/InboxMessageThread.tsx、tok=frontend/src/tokens.css、idx=frontend/src/index.css。値は origin/main 7e9155163 時点。
吹き出しの描画: 別ファイルなし。TSX の map の中で直書き（TSX:534-664）。リアクション表示だけ frontend/src/pages/inbox/MessageReactionBadges.tsx。
色の値の実体: ライト/ダーク2組ある（idx:102-103 ライト・idx:291-292 ダーク の --bubble-*）。

## C. 定型文を入力欄に入れる道
draft の state: useState("") / frontend/src/pages/inbox/useInboxState.ts:268 / 変数 draft, setDraft
setDraft を外へ渡す: frontend/src/pages/inbox/useInboxState.ts:1143-1144 / 変数
InboxPage から子へ渡す: frontend/src/pages/inbox/InboxPage.tsx:212-213 / draft={state.draft} setDraft={state.setDraft}
TSX の props 型: frontend/src/pages/inbox/InboxMessageThread.tsx:45-46 / draft, setDraft
setDraft 呼び出し（変える）1: setDraft(e.target.value)（入力欄 onChange） / frontend/src/pages/inbox/InboxMessageThread.tsx:785
setDraft 呼び出し（変える）2: setDraft("")（会話を選び直したとき） / frontend/src/pages/inbox/useInboxState.ts:593 / 直書き ""
setDraft 呼び出し（変える）3: setDraft("")（画像送信成功後） / frontend/src/pages/inbox/useInboxState.ts:776 / 直書き ""
setDraft 呼び出し（変える）4: setDraft("")（テキスト送信成功後） / frontend/src/pages/inbox/useInboxState.ts:785 / 直書き ""
他ファイルで setDraft を呼ぶ所: frontend/src 内の inbox 配下では上の4つ以外に未発見（語句検索 setDraft|draft、対象 useInboxState.ts InboxPage.tsx OutboundTranslationPreview.tsx InboxKartePanel.tsx ManualRecordSection.tsx）
定型文を入力欄へ入れる呼び出し: 無い（上記4件はすべて「入力」か「空にする」）
draft を読む（入れるのではない）: trimmedDraft = draft.trim() / frontend/src/pages/inbox/useInboxState.ts:756
draft を英訳プレビューへ渡す: draftText={draft} / frontend/src/pages/inbox/InboxMessageThread.tsx:671
英訳プレビュー後の確定: onConfirmedSend(finalText, draftId) で submitSend({ draftId }) / frontend/src/pages/inbox/InboxMessageThread.tsx:675-678（finalText は入力欄に入れず捨てている。draft_id だけ送る）
英訳プレビュー側の draft_id（サーバー側の下書き行）: requestOutboundPreview / confirmOutboundDraft / frontend/src/pages/inbox/OutboundTranslationPreview.tsx:51,74
/templates ページ: ルート直書き path="/templates" / frontend/src/App.tsx:288
/templates の中身: <ComingSoonPage title={t("templates.title")} description={t("templates.description")} /> / frontend/src/App.tsx:290-293（準備中ページ）
ComingSoonPage の実体: frontend/src/pages/coming-soon/ComingSoonPage.tsx（62行・title と description を出すだけ）
templates の文言: ja.json "templates": {"title":"テンプレート管理","description":"メール・メッセージテンプレート管理"} / frontend/src/locales/ja.json:2232-2235
別物の「テンプレート」画面: ViewerTemplatesPage（Viewer の Discord 自動通知文を編集する super-admin 画面） / frontend/src/pages/super-admin/ViewerTemplatesPage.tsx / ルート frontend/src/App.tsx:349 path="/super-admin/viewer-templates"。受信箱の入力欄とは繋がっていない（受信箱配下に参照なし）
別物の backend: backend/app/services/viewer_message_templates.py（DB表 public.viewer_message_templates から Viewer ボット文面を読む。台帳 :4, SELECT :120, INSERT :188, UPDATE :198）。受信箱の送信APIとは別。
WhatsApp 承認済みテンプレート送信の画面・部品・API: 見つからない
 使った語（frontend/src と backend/app と migrations、*.py *.ts *.tsx *.sql）: whatsapp / message_template / messageTemplate / approved_template / template_name / hsm / 定型文 / quick_reply / quickReply / canned / saved_repl / snippet
 whatsapp の該当は channel の名前だけ: backend/app/services/channel_masters.py:16,22-23 / backend/app/schemas/contact.py:81 / backend/app/schemas/lead.py:193,263 / backend/app/routers/conv_logs.py:68 / backend/app/routers/contact_channel_links.py:10。送信の道ではない（ここでは名前の一覧・リンク欄）
 frontend 側 whatsapp_link: frontend/src/pages/inbox/inbox.types.ts:105 / frontend/src/components/MergeLeadModal.tsx:90（欄の名前のみ）
 注: 上の語句検索は -l（ファイル名一覧）で head -40 に切って見た。backend/tests と frontend の stories も該当に出るが読んでいない
Meta の messaging_type / message_tag（送信種別の印）: メッセージ型に項目あり frontend/src/lib/messages.ts:69-70。画面の入力欄に選ぶ部品は無い。表示だけ frontend/src/pages/inbox/InboxMessageThread.tsx:567-571
AI の下書き（入力欄に入る）: 無い。近いもの = 英訳プレビュー（frontend/src/pages/inbox/OutboundTranslationPreview.tsx）。backend/app/routers/translation.py が draft_id を持つ（中身は未読）

## D. 吹き出しの中に出る中身（出す行 と 出る条件）
本文: <div>{msg.message_text || t("inbox.noBody")}</div> / frontend/src/pages/inbox/InboxMessageThread.tsx:614 / 条件 = 画像分岐（:577-613）に入らないとき。本文が空なら t("inbox.noBody")
訳文（ボタンで開いた訳）: <div className="msg-translation"> の <span className="msg-translation-text"> / frontend/src/pages/inbox/InboxMessageThread.tsx:628-633 / 条件 = translations[message_id].text がある。翻訳先は UI 言語（:342）
訳文の読み込み中: "msg-translation msg-translation--loading" / frontend/src/pages/inbox/InboxMessageThread.tsx:618-622 / 条件 = translationState.loading
訳文のエラー: "msg-translation msg-translation--error" / frontend/src/pages/inbox/InboxMessageThread.tsx:623-627 / 条件 = translationState.error（429 は予算超過文言 :359-361）
訳文の出所バッジ: <span className="msg-translation-badge">{t("inbox.translatedBy")}</span> / frontend/src/pages/inbox/InboxMessageThread.tsx:631 / 条件 = 訳文あり
訳ボタン（吹き出し内・時刻の行の中）: <button className="msg-translate-btn"> / frontend/src/pages/inbox/InboxMessageThread.tsx:638-649 / 条件 = msg.message_id && msg.message_text && !failed
送信状態の印（「送信失敗」帯）: t("inbox.sendError.generic") + t("inbox.sendError.codeSuffix") / frontend/src/pages/inbox/InboxMessageThread.tsx:572-576 / 条件 = failed = !!msg.error_code（:536）
送信状態の印（「送信中」「送信済み」「既読」）: 無い（Message 型に seen_at があるが吹き出しでは使っていない。frontend/src/lib/messages.ts:74）
時刻: relativeTime(msg.created_at, t, i18n.language) / frontend/src/pages/inbox/InboxMessageThread.tsx:636 / 条件 = 常に出す。7日未満は経過ラベル、7日以上は月/日（frontend/src/pages/inbox/inbox.types.ts:148-154）
時刻の絶対値: title={formatAbsolute(...)} / frontend/src/pages/inbox/InboxMessageThread.tsx:564 / 条件 = 失敗でないとき吹き出しの hover のタイトル（失敗時は失敗文言 :563）
送った人の名前: 吹き出しに出さない（msg.sender_name を TSX で参照しない。Message 型には sender_name あり frontend/src/lib/messages.ts:64）
メッセージタグ行: msg.message_tag === "HUMAN_AGENT" ? t("inbox.humanAgentLabel") : msg.message_tag / frontend/src/pages/inbox/InboxMessageThread.tsx:567-571 / 条件 = msg.message_tag あり && !failed / 直書きの style（font-size var(--font-2xs)・opacity var(--opacity-secondary)・margin-bottom var(--space-1)・font-weight var(--font-weight-semi)）
画像（自社配信API・/leads/ で始まる URL）: Blob を取得してから <img className="msg-attachment-img"> / frontend/src/pages/inbox/InboxMessageThread.tsx:578-586 / 条件 = attachment_type==="image" && attachment_url が "/leads/" 始まり && blobUrl[msg.id] あり。取得前は placeholder（:588-591）
画像（外部 CDN の URL）: <img className="msg-attachment-img" onClick=ライトボックス onError=URL 再取得> / frontend/src/pages/inbox/InboxMessageThread.tsx:599-606 / 条件 = attachment_type==="image" && URL あり && 再取得で失敗済みでない
画像の期限切れ: t("inbox.imageExpired") / frontend/src/pages/inbox/InboxMessageThread.tsx:593-597 / 条件 = retriedRef に入っていて resolvedUrl が無い
画像の URL なし: t("inbox.imageSent") の placeholder / frontend/src/pages/inbox/InboxMessageThread.tsx:608-612 / 条件 = attachment_type==="image" && !attachment_url
画像の原寸表示: ライトボックス（style 直書き） / frontend/src/pages/inbox/InboxMessageThread.tsx:865-884 / 条件 = lightboxUrl あり
リアクション（ハート含む）: <MessageReactionBadges /> / frontend/src/pages/inbox/InboxMessageThread.tsx:654-660 / 条件 = canReact = msg.platform==="discord" && !!msg.message_id && !failed（:539）。吹き出しの外（msg-stack の中・吹き出し行の下）
ハートボタン（ホバー/長押しで出る）: heartButton / frontend/src/pages/inbox/InboxMessageThread.tsx:541-551,556,652 / 条件 = heartHover = canReact && 自分のハートが付いていない（:540）。送信側は吹き出しの左・受信側は右に置く
ハート以外の絵文字バッジ: frontend/src/pages/inbox/MessageReactionBadges.tsx:56-69 / 条件 = others.length>0（表示専用）
Discord 絵文字画像: https://cdn.discordapp.com/emojis/<id>.(gif|png)?size=32 / frontend/src/pages/inbox/MessageReactionBadges.tsx:57-58 / 直書きの URL
送信失敗の吹き出し: msg-bubble failed + role="alert" / frontend/src/pages/inbox/InboxMessageThread.tsx:558-559
送信失敗の再送ボタン: 吹き出しの中には無い。入力欄の上の帯に出る <Button>（discordGuide.cta.kind==="retry" で retrySend()） / frontend/src/pages/inbox/InboxMessageThread.tsx:741-756 / 条件 = discordGuide?.cta あり
テンプレート: 無い
AI の下書き: 無い
返信の引用: 無い（reply/quote の項目が Message 型にも画面にも無い）
Message 型の全項目（frontend/src/lib/messages.ts:60-81）:
 id: number / frontend/src/lib/messages.ts:61
 platform: string / :62
 sender_id: string | null / :63
 sender_name: string | null / :64
 message_text: string | null / :65
 direction: "inbound" | "outbound" | string / :66
 message_id: string | null / :67
 recipient_id: string | null / :68
 messaging_type: string | null / :69
 message_tag: string | null / :70
 sent_by_staff_id: number | null / :71
 error_code: string | null / :72
 error_message: string | null / :73
 seen_at: string | null / :74
 seen_by_staff_id: number | null / :75
 created_at: string | null / :76
 attachment_url: string | null / :77
 attachment_type: string | null / :78
 reactions?: MessageReaction[] / :80（Discord のみ）
MessageReaction の項目: emoji_name / emoji_id / emoji_animated / count / is_mine / reactors（frontend/src/lib/messages.ts:51-58）
吹き出しで使っている項目: direction, error_code, error_message(title のみ), message_tag, message_id, message_text, attachment_type, attachment_url, created_at, platform, reactions, id
吹き出しで使っていない項目: sender_id, sender_name, recipient_id, messaging_type, sent_by_staff_id, seen_at, seen_by_staff_id
無い: 画像以外の添付の描画（attachment_type が "image" 以外は画像分岐に入らず本文表示。バックエンドは video / audio を attachment_type に入れうる backend/app/discord_gateway/ticket_channel_writer.py:108）／ファイル／スタンプ／音声／動画／位置／返信の引用／既読の印／送った人の名前／送信中の印／テンプレート／AI の下書き／再送ボタン（吹き出し内）

## E. 吹き出しの置き方（全幅の既定。値の元は tok / idx）
.inbox-center: display:flex; flex-direction:column; flex:1; overflow:hidden; background:var(--bg-surface); min-width:0; position:relative / CSS:392-401 / 直書きなしでトークン
.inbox-messages: display:flex; flex-direction:column; flex:1; min-height:0; overflow-y:auto; padding:var(--space-4)(=16px, tok:77); gap:var(--space-2)(=8px, tok:75) ← 吹き出し行どうしの縦の間隔 / CSS:488-497
.inbox-msg-row: display:flex / CSS:498。.outbound は justify-content:flex-end(:499)、.inbound は justify-content:flex-start(:500)
.msg-stack: display:flex; flex-direction:column; min-width:0; max-width:70% / CSS:502 / 直書き 70%
.msg-stack（後ろの定義）: .inbox-msg-row.inbound .msg-stack{align-items:flex-start}（CSS:1935）／ .inbox-msg-row.outbound .msg-stack{align-items:flex-end}（CSS:1936）
.msg-stack .msg-bubble: max-width:100%; min-width:0 / CSS:1937（:505 の max-width:70% を上書き。幅の上限は msg-stack 側の 70% が実効）
.msg-bubble-line: display:flex; align-items:center; gap:var(--space-1)(=4px); max-width:100%; min-width:0 / CSS:1940-1946
.msg-bubble: max-width:70%（CSS:505。実効は :1937 で 100%）; padding:var(--space-2) var(--space-3)(=8px 12px, tok:75,76); font-size:var(--font-md)(=1rem=16px, tok:17); line-height:1.45(直書き); word-break:break-word; white-space:pre-wrap / CSS:504-511。width は指定なし（中身の幅）。display は指定なし（div の既定=block、ただし .msg-bubble-line の flex の子）。align-self は指定なし
.msg-bubble.outbound: background:var(--bubble-outbound-bg)(ライト #8B2EF5 idx:103／ダーク #6d28d9 idx:292); color:var(--on-accent)(#ffffff idx:135); border-radius:var(--radius-bubble-out)(=20.8px, tok:103) / CSS:513-517
.msg-bubble.inbound: background:var(--bubble-inbound-bg)(ライト #EFEFEF idx:102／ダーク #334155 idx:291); color:var(--text-primary)(ライト #1a202c idx:24／ダーク #f1f5f9 idx:230); border-radius:var(--radius-bubble-in)(=20.8px 20.8px 20.8px 4.8px, tok:104) / CSS:519-523
.msg-bubble.failed: background:var(--danger-bg)(ライト #fed7d7 idx:53); color:var(--danger-text)(#9b2c2c idx:54); border:2px solid var(--danger)(#e53e3e idx:52); border-radius:var(--radius-xl)(=12px, tok:99) / CSS:524-529
.msg-time: font-size:var(--font-2xs)(=0.7rem=11.2px, tok:13); opacity:var(--opacity-muted)(=0.7, tok:269); margin-top:var(--space-1)(=4px); text-align:right / CSS:530-535。display は指定なし（div=block）。line-height は指定なし（親の .msg-bubble の 1.45 を引き継ぐ）。.msg-time.inbound は text-align:left（CSS:536）
時刻の位置: 吹き出しの中（.msg-bubble の子。出す行 TSX:635-650）。本文・訳文の下、右寄せ（受信は左寄せ）。訳ボタン .msg-translate-btn は時刻の行の中（inline-flex; padding:var(--space-2px); margin-left:var(--space-1); CSS:539-553）
.msg-translation: margin-top:var(--space-2); padding-top:var(--space-2); border-top:1px solid var(--border-light)(ライト #eeeeee idx:153); font-size:var(--font-sm)(=0.85rem, tok:15); line-height:1.4 / CSS:564-570
.msg-translation-badge: display:inline-block; margin-top:var(--space-1); font-size:var(--font-2xs); opacity:var(--opacity-muted); font-style:italic / CSS:584-590
.msg-attachment-img: max-width:var(--size-msg-attach-w)(=240px, tok:179); max-height:var(--size-msg-attach-h)(=200px, tok:180); border-radius:var(--radius-sm)(=4px, tok:96); display:block; object-fit:cover / CSS:693-699
.msg-attachment-placeholder: display:inline-flex; align-items:center; gap:var(--space-1); color:var(--text-secondary); font-size:var(--font-sm) / CSS:700-706
.msg-heart-hover: display:inline-flex; flex-shrink:0; opacity:0; pointer-events:none / CSS:1949-1955（hover/focus-within/長押しで opacity:1 CSS:1956-1966）
.msg-reactions: display:flex; flex-wrap:wrap; align-items:center; gap:var(--space-1); margin-top:var(--space-1) / CSS:1969-1975。送信側は justify-content:flex-end(CSS:1976)
.msg-reaction-badge: display:inline-flex; gap:var(--space-1); padding:var(--space-1) var(--space-2); border:1px solid var(--border); border-radius:var(--radius-pill)(=20px, tok:101); background:var(--bg-subtle); color:var(--text-secondary); font-size:var(--font-xs)(=12px); line-height:1 / CSS:1979-1990
行の縦の間隔: 行どうし = .inbox-messages の gap 8px（CSS:496）／ 吹き出しとリアクションの間 = .msg-reactions の margin-top 4px（CSS:1974）／ 本文と時刻 = .msg-time の margin-top 4px（CSS:533）
吹き出しのインライン style（直書き）: メッセージタグ行 TSX:568、失敗の見出し TSX:573（font-size var(--font-2xs); font-weight var(--font-weight-semi); margin-bottom var(--space-1)）、画像 TSX:584,603（cursor:zoom-in）
空メッセージ表示: textAlign:center; color:var(--text-secondary); padding:var(--space-8) の直書き / TSX:530

### E-1. スマホ幅 767px 以下（@media (max-width: 767px) CSS:1112-）
.msg-stack: max-width:85% / CSS:1173
.msg-bubble.outbound: background:var(--accent)(ライト #1e3a8a idx:34／ダーク #5b8dd9 idx:238) / CSS:1312（--bubble-outbound-bg の紫を使わない。コメント CSS:1304-1311）
.msg-bubble.inbound: background:var(--neutral-bg)(ライト #e2e8f0 idx:114／ダーク #334155 idx:303) / CSS:1313
.inbox-send-btn: width/height:var(--size-icon-btn-lg) / CSS:1190-1193（値は tok の --size-icon-btn-lg: 未読）
.inbox-center: 既定 display:none（CSS:1148）、.inbox-wrapper.thread-open .inbox-center で display:flex; width:100%; flex:1; min-height:var(--inbox-center-min-h)(=300px, tok:314); overflow:hidden（CSS:1151-1157）
.inbox-messages / .inbox-msg-row / .msg-bubble 本体 / .msg-time / .send-card / .send-top-row / .send-input-wrap / .inbox-textarea の 767 以下の上書き: CSS:1112-1686 の範囲を msg|send-|inbox-messages|inbox-center|textarea|bubble|inbox-send で検索して該当なし（上記以外）
### E-2. 560px 以下（@media (max-width: 560px) CSS:1687-1689）
.inbox-profile-modal { min-width: unset } のみ。吹き出し・入力欄の上書きなし
### E-3. 1000〜1279px
@media (max-width: 1279px) は CSS:1000-。吹き出し関連（msg|send|inbox-messages|inbox-center|textarea|bubble）の行を CSS:1000-1111 で検索して該当なし。1000〜1279 専用（min-width:1000 を使う範囲指定）の @media は InboxPage.css に無い（@media の行は :1000 :1112 :1687 :1961 のみ）
@media (hover: hover) CSS:1961-1966: ハート表示の hover のみ

### 送信エリア（参考・同じ画面の入力欄）
.inbox-send-area: padding:var(--space-1) var(--space-3) var(--space-3) / CSS:594-596（+ .sticky-bottom-bar frontend/src/pages-layout.css:140-146 position:sticky; bottom:0; flex-shrink:0; background:var(--bg-surface); z-index:var(--z-base)）
.send-card: background:var(--bg-surface); border:1px solid var(--border); border-radius:var(--radius-xl); display:flex; flex-direction:column; overflow:hidden / CSS:598-605
.send-top-row: display:flex; align-items:flex-end; gap:var(--space-2); padding:var(--send-top-row-padding)(=10px 10px 6px相当, tok:290) / CSS:607-612
.send-input-wrap: flex:1; min-width:0; background:var(--bg-subtle); border-radius:var(--radius-pill); padding:var(--space-2) var(--space-14px); display:flex; align-items:center; gap:var(--space-1) / CSS:614-624
入力欄: <TextareaControl variant="embedded" className="inbox-textarea" rows={2}> / TSX:780-796。入力欄の見た目の実体（Textarea の embedded）は未読
添付ボタン: .send-attach-btn（28px, tok:167 --size-icon-btn-sm）/ CSS:630- / TSX:809-818
英訳ボタン: .inbox-translate-outbound-btn / CSS:1692-1704 / TSX:821-833 / 条件 = canSend && trimmedDraft.length>0 && !attachedFile
送信ボタン: .inbox-send-btn / CSS:709- / TSX:834-851

## F. 金型（frontend/src/components）
C〜E で使っている金型:
 Button: frontend/src/components/Button.tsx / 使う所 TSX:17,742（送信失敗帯の CTA・variant="secondary" size="sm"）
 IconToggleButton: frontend/src/components/IconToggleButton.tsx / TSX:18,543（ハート）／ frontend/src/pages/inbox/MessageReactionBadges.tsx:9,43（variant="badge"）
 Select（SelectControl）: frontend/src/components/Select.tsx / TSX:19,454（ヘッダの言語プルダウン。吹き出しではない）
 Textarea（TextareaControl）: frontend/src/components/Textarea.tsx / TSX:20,780（入力欄 variant="embedded"）
 Tooltip: frontend/src/components/Tooltip.tsx（MessageReactionBadges.tsx:8,41 でリアクションした人を出す）
 loading（LoadingBlock）: frontend/src/components/loading / TSX:26,524
 Toast（toast）: frontend/src/components/loading/Toast / TSX:24,229（ハート送信失敗）
 ComingSoonPage（金型ではなくページ部品）: frontend/src/pages/coming-soon/ComingSoonPage.tsx（/templates）
金型を使わずこの画面だけで作っている所:
 吹き出し本体 .msg-bubble（outbound / inbound / failed）: TSX:557-566 の div と CSS:504-529
 吹き出し行 .inbox-msg-row / .msg-stack / .msg-bubble-line: TSX:553-555 と CSS:498-502,1934-1946
 時刻 .msg-time: TSX:635 の div と CSS:530-536
 訳ボタン .msg-translate-btn（素の <button>）: TSX:639-648 と CSS:539-561
 訳文 .msg-translation*: TSX:618-633 と CSS:564-590
 画像 .msg-attachment-img と placeholder: TSX:577-613 と CSS:693-706
 画像ライトボックス: TSX:865-884（style 直書きの div。Modal 金型を使っていない）
 送信失敗の帯 .inbox-send-error: TSX:725-758
 送信ガード確認ダイアログ .send-guard-*: TSX:683-721（素の <div role="dialog">。Modal 金型を使っていない）
 英訳プレビューモーダル .outbound-translation-*: frontend/src/pages/inbox/OutboundTranslationPreview.tsx と CSS:1707-
 送信エリア .inbox-send-area / .send-card / .send-top-row / .send-input-wrap: TSX:724-853 と CSS:594-624
 添付ボタン .send-attach-btn / 英訳ボタン .inbox-translate-outbound-btn / 送信ボタン .inbox-send-btn（素の <button>）: TSX:809,822,834
 ドロップのオーバーレイ .inbox-drop-overlay: TSX:391-398 と CSS:405-428
 ヘッダ（PC・タブレット）: TSX:418-518（素の header・button。スマホは別ファイル frontend/src/pages/inbox/InboxThreadHeaderMobile.tsx）
 リアクションの絵文字バッジ .msg-reaction-badge（素の span）: frontend/src/pages/inbox/MessageReactionBadges.tsx:60 と CSS:1979-

## G. 未確認
Textarea（embedded）の見た目の実体（frontend/src/components/Textarea.tsx の中身と対応する CSS）
Button / IconToggleButton / Tooltip / Select の各ファイルの中身
--size-icon-btn-lg の値、--z-base の値、--font-weight-medium 等 C〜E で触れたが読んでいないトークン
.inbox-send-btn / .send-attach-btn / .send-preview-* / .inbox-send-error の CSS の全体（CSS:630-720 の途中以降と該当行）
@media (max-width: 1279px) ブロックの終わりの行（CSS:1000 から :1111 の範囲を吹き出し語句で検索しただけ。ブロックの閉じ位置は未確認）
CSS:1256-1311 以外の 767 以下ブロックの本文全部（検索語に当たった行のみ確認）
InboxPage.css 以外（frontend/src/index.css, pages-layout.css, components.css, 他の *.css）に .msg-* / .inbox-msg-row / .inbox-messages の上書きがあるか（idx では bubble の語のみ確認。他は未検索）
useLongPressReveal.ts / reactionHeart.ts / reactionEmojiPresets.ts の中身
backend の送信 API（メッセージ送信・画像送信）の受け取り項目と、WhatsApp 向けのテンプレート送信の有無（語句検索のファイル名一覧のみ。backend/app/routers 内の個別ファイルの本文は未読）
backend/app/routers/translation.py の draft_id 周りの中身
ja.json の inbox.* 文言（noBody, imageSent, imageExpired, sendError.*, humanAgentLabel）の実際の文字列
messaging_type / message_tag の取りうる値（バックエンド側）
Discord 以外（Messenger / Instagram）でのリアクション表示・受信の画像以外（video / audio / sticker）のバックエンド取り込みの範囲（webhook.py の _extract_first_image_type は名前から画像のみと推測できるが本文は未読）
ダーク時の各トークンの実際の見え方（実測していない）
