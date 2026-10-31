# 要件定義 草案 v1：受信箱の「会話の画面」を本物の WhatsApp に揃える

状態: 草案（Opus 作成）。§11 の成功の条件は PO 承認済み（2026-11-01「1」）。PO 承認済みの項目は「決定」欄に PO の言葉を添える。それ以外は決定ではない。
作成: 2026-10-31 JST

## 0. 出発点（決定済み）
- 2026-10-29 PO: 会話の中の画面（吹き出し・入力欄）は Android 実機で測った本物の WhatsApp の値に揃える。手本はクローンではない。取りかかるのはリード統合の後。足りない値は着手時に測り足す。
  出典: docs/handoff/inbox-brushup/README.md:34-36（origin/main）
- 2026-10-31 PO: 見本の4部分のうち「会話の画面」から始める（回答「1」）。要件定義から整理して壁打ちしてから着手する。
- 前提の達成: リード統合は #4840・#4843 で main へマージ済み（git log origin/main）。

## 1. 目的（案）
営業担当がスマホで相手とやり取りするとき、WhatsApp と同じ見た目・同じ押し心地で読み書きできるようにする。
- 誰が: アプリで受信箱を使う営業担当（PO・社員）
- いつ: スマホで受信箱の会話を開いたとき（PC の扱いは未決 Q2）

## 2. いまの食い違い（事実・origin/main）
出典: docs/handoff/inbox-brushup/evidence/size-compare.md:51-66、docs/specs/design-system/visual-language/benchmark/whatsapp-reproduction-spec.md

| 部位 | WhatsApp 実測 | 今の SA（スマホ） | 判定 |
|---|---|---|---|
| 吹き出しの角 | 角丸 10dp＋受信側だけ左上に 7dp の尾 | PC と同じ値（角 20.8px・尾 4.8px） | 不一致 |
| 吹き出しの内側の余白 | 2dp | 上下8px・左右12px | 不一致 |
| 吹き出しの置き場 | 行の左から17dp・上下5dp | 未確認 | 比べられない |
| 吹き出しの中の時刻 | 本文と同じ行の右下（本文の右に37dp 先取り） | 吹き出しの下 | 不一致 |
| 吹き出しの幅 | 中身に合わせて縮む | 最大85%（縮むかは未確認） | 未確認 |
| 入力欄の帯 | 高さ 55.7dp | スマホ用の指定なし | 不一致 |
| 入力欄の枠 | 286.7×48.3dp・角丸 約3〜4dp・中に絵文字/添付/カメラ 各48dp | 約56px（計算値）・中の並びは未確認 | 不一致 |
| 送信ボタン | 48dp の緑の完全な円・枠の外に別の丸 | 44px | 不一致（44px の基準を選んだ経緯あり） |
| 文字の大きさ | 吹き出し本文16・行の間隔19・時刻12・入力欄18（2026-10-31 見本照合で確定、measure1-summary.md） | 吹き出し16px・入力14.4px | 本文は一致・入力欄は不一致（14.4→18）・時刻は SA 側未確認 |

## 3. 範囲（案）
- 対象: スマホの会話の画面の「吹き出し」と「入力欄」
- 対象外: 一覧・上の帯・戻るボタン（一致済み）、商談の帯・商談の窓・列の画面・「＋」の送付物メニュー（見本の別部分）

## 4. 成功の条件（案。○×で判定）
| 基準 | 測り方 |
|---|---|
| 上表の各部位が WhatsApp 実測と ±1px で一致 | 幅360の本物の画面の写真と、画面の中の大きさを機械で読み取った値 |
| 新しい値はすべてデザイントークン経由・直書き0件 | 既存のトークン点検（CI）と grep |
| PC の会話画面が変わらない（Q2 で PC 対象外になった場合） | PC 幅1280の前後の写真比較 |
| PO が写真を見て合格 | 本番に出す前に写真を PO に見せる（10/28 の決定と同じ） |

## 5. 未決（PO に聞く順）
- Q1 今回の範囲 → **決定 2026-10-31 PO 回答「2」**: 見た目に加えて、入力欄の「＋」から定型文や見積などを送れるようにする。段階の帯は対象外。
- Q1-2 「＋」に入れる物（下の事実を見て PO に聞く）
  - 事実（origin/main）:
    - 画像の添付と送信は入力欄に既にある（frontend/src/pages/inbox/InboxMessageThread.tsx:806-817、useInboxState.ts:773-781 sendImageMessage）。画像以外のファイルを送る道は検索で見つからない（frontend/src/pages/inbox/ 内）。
    - 定型文は別の画面 /templates へ移動するメニューだけ（InboxPage.tsx:87-91、InboxThreadHeaderMobile.tsx:88-91）。会話の入力欄へ差し込めるかは未確認。
    - 登録リンクはカルテの中で作れる（InboxKartePanel.tsx:362 register/add_address/change_billing、:405）。
    - 請求書はカルテのボタンから作成画面 /invoices/new へ移動するだけ（useInboxState.ts:956-957）。会話に送る道は無い。
    - 見積は frontend/src/pages/inbox/ 内に無い。ただしアプリには見積の作成・一覧・詳細の画面がある（frontend/src/pages/quote-create/QuoteCreatePage.tsx、quotes/QuotesPage.tsx、quote-detail/QuoteDetailPage.tsx）。PO への説明で「作る所が見つからない」と誤って伝えた（受信箱の中だけを探していたため）。2026-10-31 に訂正した。
    - 請求書の PDF を作る道がある（backend/app/routers/invoices.py:809-861 /invoices/{id}/pdf）。見積の PDF もある（同 :969-1033 /quotes/{id}/pdf）。
    - PayPal の請求書を送ると、お客さまの支払いページの URL を保存している（backend/app/routers/invoices.py:681-690 recipient_view_url を paypal_approval_url に保存）。
- Q1-2 → **決定 2026-10-31 PO 回答「2」**: 「＋」に 画像・定型文・登録リンク を集め、請求書を会話にそのまま送れるようにする。見積と画像以外のファイルは今回は対象外。
- Q1-3 請求書を会話に送る形 → **決定 2026-10-31 PO**: 「PayPalはリンク、Wiseの場合はPDFを送る」
  - 事実: 請求書の出し方は会社ごとの設定で4種類（backend/app/schemas/tenant_policy.py:21 issue_mode = paypal_auto / paypal_manual / pdf / wise_pdf、既定 pdf。画面は frontend/src/pages/admin/TenantPolicyPage.tsx:33,303）。wise_pdf の PDF の中身（振込先が載るか）は未確認。検索の生出力: /tmp/CC報告ファイル/inbox-deal-ui/wise-grep.txt
  - 帰結: Wise の場合は PDF を会話に送る仕組みが新しく要る（今は画像だけ送れる）。
- Q1-4 PayPal か Wise かの決め方 → **決定 2026-10-31 PO 回答「1,3」**: お客さまごとに決めておき、請求書ごとにその場で選び直せる。
  - 事実: 請求書1枚ごとの払い方の欄は既にある（invoices.payment_method VARCHAR(50)、backend/app/services/tenant.py:877、migrations/005_add_phase2_tenant_tables.sql:125。更新可 backend/app/routers/invoices.py:144）。値の決まりは無く自由に入る（migrations/20261024_100300_create_ai_cloud_views.sql:407 の注記）。PayPal の送信時は 'paypal' を入れる（invoices.py:686,780）。
  - 事実: お客さま側に払い方の欄は検索で見つからない（payment_method / preferred_payment 等で backend/app と migrations を検索。生出力 /tmp/CC報告ファイル/inbox-deal-ui/payment-method-grep.txt）。支払い名義の欄はある（migrations/015_replace_customers_schema.sql:101）。
- Q1-5 お客さまの払い方の持ち方 → **決定 2026-10-31 PO**: 「3で固定設定しておくが作成時に選択できる余地は残しておく」。カルテ（お客さま）に払い方の欄を足して固定で持ち、請求書を作るときは選び直せる。請求書に残る払い方は既存の invoices.payment_method 1か所（二重に持たない）。
  - 設計担当の既定（PO に聞かずに置く・変えるなら PO が言う）: お客さまの払い方が空のときは、会社の設定（tenant_policy の issue_mode）を最初に選んでおく。
- Q1-6 お客さまの払い方で選べる種類 → PO 回答「1」の直後に、選択肢3の説明を求められた。決定は保留（説明後に聞き直す）。
  - 事実: 会社の設定の4種類の画面の名前は「PayPal 自動」「PayPal 手動」「PDF」「Wise PDF」（frontend/src/locales/ja.json:1996-1999 origin/main）。それぞれ実際に何をするかはまだ確かめていない。
  - 事実: 請求書1枚ごとにも issue_mode が保存されている（backend/app/routers/invoices.py:138 _INVOICE_COLUMNS）。payment_method と issue_mode の2つが請求書にある。どう使い分けているかは未確認 → 設計前に調べる（同じことを2か所に持たないため）。
  - 訂正: Opus は選択肢3を「お客さまにとって違いのない選び方が残る」と説明した。自動と手動の違いを確かめずに書いた説明だった。
  - 調査 2026-10-31（Opus・origin/main を読むだけ。生出力 issue-mode-research.txt / issue-mode-research2.txt）:
    - ADR-101 §6（docs/adr/ADR-101-sa-quotation-invoice-generation.md:136-147）: 払い方ごとの出し方。PayPal は (1) API自動（リンク自動発行＋入金自動確認）(2) 手動発行＋リンク貼付 (3) 自社PDF。Wise は 自社PDF＋メール送金（入金確認は手動）。「テナント×決済方法で選択」。
    - 実装: 会社の設定 issue_mode を読むのは設定画面と設定の保存だけ（TenantPolicyPage.tsx・routers/tenant_policy.py:41・services/tenant.py:1767）。請求書の作成・PayPal 送付はこの設定を読まない（invoices.py・integrations.py に issue_mode の読み取り無し）。→ 今は4つのどれを選んでも動きは変わらない。
    - 請求書の issue_mode 列は「会社の設定から継承」と注記（migrations/20260604_160000_add_invoice_snapshot_columns.sql:51-52）だが、請求書の作成（invoices.py:277-287 INSERT）は書き込まない。
    - 請求書の payment_method は作成時 NULL（invoices.py:285）。PayPal 送付時に 'paypal'（invoices.py:686,780、integrations.py:800,949）。作成画面で払い方を選ぶ欄は無い（詳細画面で表示のみ InvoiceDetailPage.tsx:304）。
    - 実装の4種類と ADR の表の対応: 「pdf」は払い方の指定が無い。ADR の PayPal(3) 自社PDF に当たるかは記述が無く未確認。
  - 整理（Opus）: 払い方（PayPal／Wise）と出し方（自動・手動・PDF）は別のもの。ADR-101 は「出し方は会社が払い方ごとに選ぶ」形。カルテに持つのは払い方だけで ADR と合う。
  - 未決（設計で扱う・あとで PO に聞く）: 会社の設定が「pdf」（Wise でない PDF）のとき、カルテが空のお客さまに最初に何を選ぶか。
- Q2 → PO に質問中
- （Q1-2 の定型文・入力欄の検索の生出力: /tmp/CC報告ファイル/inbox-deal-ui/inbox-composer-grep.txt）
- Q2 PC の会話画面も揃えるか、スマホだけか
- Q3 文字の大きさを測り足すか（Android 実機での撮影が要る。手順書 docs/handoff/app-visual-language/phone-capture-runbook.md）
- Q4 送信ボタンは 48px（WhatsApp）か 44px（今の基準）か → 閉じる（Opus判断・2026-10-31）: 10/11 PO決定「スマホは実測値」（benchmark/README.md:36）に含まれるため 48。44px は「タップ領域の最小」（whatsapp-reproduction-spec.md:220）で、48 はこれを満たす。実測 x909–1050=142画素（色の許容内のみ数えたため縁の1画素ずつを除く）
- Q5 SA にしかない吹き出しの中身の置き場所 — 現状は §6-2。まず訳文の置き場所を PO に質問中（2026-11-01）。
- Q5 への PO 回答 2026-11-01（原文）: 「１，whatsappにはない機能だけど言語切替機能って付けられる？通常/日本語　モードで切り替えが出来るようにして、通常では原文を表示するwhatsappと同じ仕様、日本語モードにすると裏でgeminiが和訳した文章に表示が切り替わって日本語で全て表示される仕様」
  - Opus の読み取り（PO が違えば直す）: 吹き出しの1件ごとの訳ボタンの代わりに、画面全体を「通常（原文）／日本語（和訳）」で切り替える。通常は WhatsApp と同じ見た目。
  - 事実（生出力 translate-mode-research.txt / -2.txt、origin/main 55e3baed1）:
    - Gemini の和訳は既にある。受信の和訳は gemini-3.5-flash-lite（backend/app/services/message_translator.py:49）。入口 backend/app/routers/leads.py:1374。
    - 和訳は会社ごとの表 message_translations に保存し、同じ投稿×同じ言語は2回目から保存分を返す（migrations/094_create_message_translations.sql:9-14,33-41）。
    - 会社ごとの月の予算を超えると和訳は止まる（message_translator.py:486-489、画面の文言 InboxMessageThread.tsx:359-361）。
    - 今の訳先は画面の言語（InboxMessageThread.tsx:341-342、ADR-088 と注記）。
  - 未確認: 1件あたりの費用（円）、自社の送った投稿の日本語の元の文が残っているか（outbound_translation_drafts）、切り替えを人ごとに覚えておく置き場所。
  - 次の質問: 和訳をいつ作るか（開いたときに画面の分だけ／届いた時点で全部）。
  - **決定 2026-11-01 PO**: 「基本的に届いた文章は翻訳されていてほしい」→ 届いた時点で全部を和訳しておく。
  - PO の追加依頼: Gemini 以外の方法と外部事例の調査 → /tmp/CC報告ファイル/inbox-deal-ui/translation-evidence.md（2026-11-01）。
  - 次の質問: 訳す AI の選び方（自社のメッセージで比べるか、比べる相手にどこまで含めるか）。
  - Luna と Gemini の比較の調査 → translation-evidence.md §1-4（2026-11-01）。直接比べた外の試験は無し。
  - **決定 2026-11-01 PO 回答「3」**: 今は比べる試験をしない。訳す AI は今のまま（gemini-3.5-flash-lite、message_translator.py:49）で、画面の要件の話に戻る。
  - 次の質問: 会話を開いたとき最初にどちらの表示にするか（人ごとに前回を覚える／いつも通常／いつも日本語）。
  - **決定 2026-11-01 PO 回答「1」**: 人ごとに前回の選び方を覚えておく。置き場所は設計で SSOT 点検（端末ではなく人に紐づける＝PC とスマホで同じになる、が Opus の読み取り。違えば PO が直す）。
  - 設計担当の既定（PO が変えるなら言う）: 日本語の表示で、訳がまだ無い・訳せなかった投稿は原文を出し「訳せませんでした」の印を付ける。
  - 次の質問: 吹き出しごとの今の訳ボタンをどうするか。
  - **決定 2026-11-01 PO 回答「1」**: 吹き出しごとの訳ボタン（TSX:638-649）はなくす。訳せなかった投稿にだけ「もう一度訳す」を出す。
  - 事実（生出力 outbound-source-research.txt / -2.txt、origin/main 1896879cb）: 英訳の下書きを通して送った投稿は、担当者の日本語の元の文が残る（outbound_translation_drafts.original_text、migrations/20260604_220000_create_translation_glossary.sql:110）。送った投稿との紐付けもある（meta_message_id、leads.py:2146-2156、migrations/20260626_100000_add_outbound_draft_message_link.sql:37）。担当者が英文を直したかの印もある（is_edited、同 :50）。下書きを通さず送った投稿には日本語の元の文は無い。
  - 次の質問: 日本語の表示で、自社が送った投稿をどう見せるか。
  - **決定 2026-11-01 PO 回答「1」**: 日本語の表示では、送った英文をいつも日本語に訳して見せる（お客さまに届いた中身を確かめるため）。日本語の元の文（original_text）は表示に使わない。訳は届いた投稿と同じ置き場所 message_translations 1か所（二重に持たない・設計で SSOT 点検）。送った時点で訳しておくかは届いた投稿の決定（届いた時点で全部）に揃える（Opus の読み取り）。
  - 事実（生出力 msgtype-row.txt、origin/main 1896879cb）: 吹き出しの上の種類の行は、Meta の決まりの印 message_tag を出す（TSX:567-570）。HUMAN_AGENT は「ヒューマンエージェント」と表示（ja.json:1242）。お客さまの最後の投稿から24時間〜7日の間に送った返信に付く（backend/app/services/messaging_window.py:31-32,43,54,88-89）。文字の大きさなどは style の直書き（TSX:568）。
  - 次の質問: この種類の行を残すか。
  - **決定 2026-11-01 PO 回答「1」**: 種類の行（「ヒューマンエージェント」）は吹き出しに出さない。送るときの Meta の決まりの扱い（messaging_window.py）は変えない。
  - 設計担当の既定（PO が変えるなら言う）: 送信失敗の印は残す（送れていないことが分かる必要があるため）。ハート・絵文字（Discord だけ）は今のまま残す（WhatsApp の画面の対象外）。
  - 事実（生出力 read-receipt-research.txt、origin/main 1896879cb）: seen_at は「担当者が届いた投稿を読んだ」印で、届いた投稿だけに使う（migrations/041_extend_meta_messages.sql:14,25,46、leads.py:1182-1219）。お客さまが読んだ・届いたの知らせ（read / delivery）は Meta から来ても捨てている（backend/app/routers/webhook.py:350-364）。お客さまの既読を持つ欄は無い。
  - 次の質問: 送った投稿に WhatsApp のような「届いた・読まれた」の印を付けるか。
  - **決定 2026-11-01 PO 回答「2」**: 今回いっしょに作る（お客さまの「届いた・読まれた」の知らせを残し、送った吹き出しに印を付ける）。
  - Context7 は月の上限で使えなかった（2026-11-01「Monthly quota exceeded」）。起動指示の代替として公式資料を直接確かめた。
  - 事実（公式 2026-11-01 取得）: Messenger の既読の知らせ message_reads は read.watermark「この時刻以前に送った投稿は全部読まれた」（developers.facebook.com/docs/messenger-platform/reference/webhook-events/message-reads。表は「以前または同時」、本文は「以前」で境目の書き方が食い違う）。届いた知らせ message_deliveries は mids（投稿の番号の並び・無いこともある）と watermark（同 message-deliveries）。WhatsApp は送った投稿ごとに sent / delivered / read の知らせが来る（同 whatsapp/cloud-api/webhooks/payload-examples）。Instagram の既読の知らせ：公式の該当ページで記述を見つけられず → まだ確かめていない。
  - 事実（生出力 receipt-subscribe.txt、origin/main 1896879cb）: Facebook ページの受信登録に message_deliveries・message_reads が既に入っている（backend/app/services/meta_graph.py:48-49）。→ 知らせは今も届いていて、webhook.py:350-364 で捨てている。WhatsApp の受け口の router は見つからない（routers の検索で whatsapp を含むのは contact_channel_links.py・conv_logs.py・leads.py のみ）。
  - 設計担当の既定（PO が変えるなら言う）: 印は WhatsApp と同じ3段階（送った・届いた・読まれた）。知らせが来ない連絡手段（Discord 等・確かめるのは設計で）では印を出さない。
  - 設計で扱う: Messenger の知らせは「時刻まで全部」の形なので、投稿1件ごとの印に直す決まりが要る。置き場所は meta_messages 1か所に寄せるかを SSOT 点検。

## 6. 今の画面の事実（2026-11-01 クラウド調査・読むだけ・origin/main 7e9155163）
生データ: /tmp/CC報告ファイル/inbox-deal-ui/thread-recon-raw.md（枝 release/inbox-thread-recon-raw 456476bd3・main との差はこの1ファイルだけ）。調査は Bash と Read だけ。メール等の道具の呼び出しは0件（実行記録で確認）。
略号: TSX=frontend/src/pages/inbox/InboxMessageThread.tsx、CSS=frontend/src/pages/inbox/InboxPage.css、tok=frontend/src/tokens.css、idx=frontend/src/index.css
### 6-1 吹き出しの置き方
- 吹き出しは別の部品ではなく TSX:534-664 に直書き。金型（components/）は使っていない（raw F 節）。
- 幅の上限は .msg-stack の 70%（CSS:502）、スマホ 85%（CSS:1173）。吹き出しに width の指定は無い＝中身の幅に縮む（CSS:504-511、:1937）。→ §2「縮むかは未確認」は解消: 縮む。
- 送信は右寄せ・受信は左寄せ（CSS:499-500、:1935-1936）。行どうしの間 8px（CSS:496）、画面の端との余白 16px（CSS:488-497）。
- 余白 8px/12px・文字 16px・行の高さ 1.45 直書き（CSS:504-511）。
- 時刻は吹き出しの中、本文と訳文の下の別の行、右寄せ（受信は左寄せ）（TSX:635-650、CSS:530-536）。文字 11.2px・薄さ0.7。
- スマホの色: 送信 var(--accent)（ライト #1e3a8a）・受信 var(--neutral-bg)（ライト #e2e8f0）（CSS:1312-1313）。角はスマホでも PC と同じ 20.8px/尾4.8px（tok:103-104、767px以下の上書き無し CSS:1112-1686 検索）。
- 1000〜1279px と 560px 以下に吹き出しの上書きは無い（raw E-2・E-3）。InboxPage.css 以外のファイルの上書きは未確認（raw G）。
### 6-2 吹き出しの中身（SA にしか無い物を含む）
- 本文（TSX:614）／画像 4分岐（TSX:577-613、最大 240×200 tok:179-180）／時刻（TSX:636）
- SA だけの物: 訳文と「翻訳した」の印（TSX:618-633、本文の下に線で区切る CSS:564-570）／訳ボタン（時刻の行の中 TSX:638-649）／メッセージの種類の行（HUMAN_AGENT など TSX:567-571、直書き style）／送信失敗の帯（TSX:572-576）／ハートと絵文字（Discord だけ、吹き出しの外の下 TSX:654-660）
- 無い物: 既読・送信済みの印（seen_at は型にあるが未使用 frontend/src/lib/messages.ts:74）、送った人の名前、返信の引用、画像以外の添付の表示（動画・音声は本文として出る。backend/app/discord_gateway/ticket_channel_writer.py:108 は video/audio を入れうる）
### 6-3 入力欄と「＋」
- 定型文を入力欄へ入れる道は無い。setDraft は入力・空にするの4か所だけ（TSX:785、frontend/src/pages/inbox/useInboxState.ts:593,776,785）。
- /templates は「準備中」の画面（frontend/src/App.tsx:288-293）。/super-admin/viewer-templates は Discord 自動通知の文面で別物（App.tsx:349）。
- WhatsApp の承認済みテンプレート送信の道は見つからない（raw C 節の語句検索）。
- 入力欄の並び: 添付 28px（CSS:630-）・英訳ボタン（CSS:1692-1704）・送信 36px／スマホ 44px（CSS:709-730、:1190-1193）。入力の文字 14.4px（frontend/src/components/FormField.css:55,292、10/31 の調査）。
- 送信の確認窓（TSX:683-721）・画像の拡大（TSX:865-884）は素の div で Modal 金型を使っていない（金型の決まりから外れている箇所として設計で扱う）。
### 6-4 未確認（raw G 節）
- Textarea・Button 金型の中身、--size-icon-btn-lg 等の値、InboxPage.css 以外の上書き、ja.json の inbox.* の実際の文言、送信 API の受け取り項目、Messenger/Instagram の取り込み範囲、ダークの見え方。

## 7. 出し方の整理（2026-10-31 PO の問いへの Opus 案・未決）
- PO の問い（原文）: 「API設定をしていればPayPalは自動化出来るからリンクで良い、WiseはAPIが取得できないので自社のPDFを発行する、PDF→Wiseパターンと同義なので同じでいい、発行方法を裏でAPIorPDFで選択できるようにしておくといいの？」
- Opus 案: カルテは PayPal／Wise の2つ。出し方は払い方から自動で決める（PayPal＝リンク、Wise＝自社 PDF）。PayPal の API がつながっているときはリンクを自動で作る。つながっていないときは担当者が PayPal で作ったリンクを貼る（ADR-101 §6 の PayPal(2)）。会社の4択の設定は使われていないので外す方向（ADR-101 §6 の改訂が要る・設計で扱う）。
- 理由: 設定と実際の動きがずれる場所を無くす（今は設定が何も動かしていない）。同じことを決める場所を1つにする。
- 未確認: PayPal の API がつながっているかをシステムがどこで判定しているか（PayPal の登録画面 paypalIntegration はある。ja.json:617-641）。

## 8. 確かめた事実（2026-10-31 Opus・origin/main を読むだけ・公式資料）
生出力: paypal-connect-research.txt / paypal-connect-research2.txt / invoice-pdf-research.txt / invoice-pdf-research2.txt
- PayPal の「つながっている」の判定 = 会社の PayPal の鍵が保存されているか（tenant_paypal_config の行の有無。backend/app/services/paypal_payments.py:51-60、/integrations/paypal/status は integrations.py:521-532）。鍵が本当に使えるかは別の「接続テスト」（integrations.py:585-）で、自動の判定には入っていない。
- PayPal リンクの発行（invoices.py:622-）: 鍵が無いと「PayPal が未接続です」で止まる（invoices.py:612-619）。お客さまの担当者のメールが無いと止まる（:650-661）。PayPal がお客さまへメールで請求書を送る（:24 ADR 文・ja.json linkHint）。リンクは paypal_approval_url に保存（:681-690）。
- 担当者が PayPal で作ったリンクを貼り付ける道は無い（paypal_approval_url を書くのは API の2か所だけ: invoices.py:685、integrations.py:724。_UPDATABLE_COLUMNS invoices.py:144 にも無い）。→ §7 の「つながっていないときは貼る」案は今は無い道。訂正。
- 請求書の PDF に振込先は載らない: PDF に渡す中身（invoices.py:830-852）に払い方・振込先が無い。会社の情報は 名前・住所・電話・メール・サイトだけ（invoices.py:109-127）。PDF を作る部品 backend/app/services/invoice_renderer.py に bank/wise/payment/account/terms/口座 の語は0件。ADR-101 の必須項目「Payment Terms（方法・通貨・期限・手数料・Wise口座名義の注記）」（ADR-101:133）は未実装。→ Wise の PDF を送っても、どこに振り込むかがお客さまに伝わらない。
- 会話で PDF を送れるか（公式資料 2026-10-31 取得）:
  - WhatsApp Cloud API: 「PDF | .pdf | application/pdf | 100 MB」 https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media
  - Instagram: File 型 pdf・最大25MB https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api
  - Messenger: 「Files」を送れる。PDF の明記と大きさの上限はこのページに無い（未確認） https://developers.facebook.com/docs/messenger-platform/send-messages
- 未決（PO に聞く順）: ①PayPal が未接続のときの扱い ②Wise の振込先をどこに1か所で持つか

## 9. 決定と事実（2026-10-31 続き）
- ①PayPal が未接続のとき → **決定 2026-10-31 PO 回答「1,2」**。Opus の読み取り: 「PayPal がつながっていません」と出す。そのうえで、担当者が PayPal で作ったリンクを貼り付けて送れる道を新しく作る（入金は担当者が確かめる）。読み取りが違えば PO が直す。
  - 設計で扱う: 貼り付けたリンクの置き場所は既存の paypal_approval_url 1か所に入れる（二重に持たない）。貼り付けか API かを区別する印が要るかは設計で決める。
- ②Wise の振込先の置き場所 → PO に質問中
  - 事実（生出力 bank-field-research.txt / bank-field-research2.txt）: 振込先（銀行・口座・SWIFT 等）を持つ欄は migrations に0件。お客さま側の支払い名義だけある（015_replace_customers_schema.sql:101）。
  - 会社の情報の表 tenant_profile の列: 会社名・英名・住所・電話・メール・サイト・印影・既定の言葉（migrations/069_create_tenant_profile.sql:71-85）。請求書の PDF はここから会社の情報を取る（invoices.py:109-127）。
  - 支払い手数料の表 payment_fee_settings は手数料の率と期間の履歴（migrations/20261002_160000_create_payment_fee_settings.sql:7-25）。振込先を置く表ではない（Opus の判断）。
- ②Wise の振込先の置き場所 → **決定 2026-10-31 PO 回答「1」**: 会社の情報（tenant_profile が候補・置き場所の最終は設計で SSOT 点検）に Wise の振込先を足し、請求書の PDF に毎回自動で載せる。
- ③Wise の振込先は通貨ごとに違う（公式 https://wise.com/help/articles/2897238/what-are-account-details 2026-10-31 取得: 「Select the account details of the currency you want to receive」「Up to 10 sets of account details per currency」「USD local account details are not available everywhere」）。→ どの通貨で受け取るかで、持つ振込先の数と項目が変わる。PO に質問中。
  - 事実: 本番の請求書の記録は全社合わせて2行（2026-10-28 読み取り・inbox-brushup-README §4-4）。記録から受け取り通貨は数えられない。
- ③ → **決定 2026-10-31 PO 回答「2」**: 米ドル以外の通貨でも受け取る。通貨ごとに Wise の振込先を書いておき、請求書の通貨に合う振込先を PDF に自動で載せる。
  - 帰結（設計で扱う）: 会社の情報の表 tenant_profile は会社に1行（069:71-85）なので、通貨ごとに複数持つには別の表が要る。置き場所は設計で SSOT 点検。
  - 設計担当の既定（PO が変えるなら言う）: 請求書の通貨の振込先が登録されていないときは、PDF を送らず「この通貨の振込先が登録されていません」と出して止める（振込先の無い請求書を送らないため）。
- Q2 PC → **既に決定済み（再承認しない）**: PO 決定 2026-10-11「吹き出しは PC と スマホ で分ける」。PC は今の値（20.8px）を維持し、スマホだけ実測に揃える（docs/specs/design-system/visual-language/benchmark/README.md:36 origin/main）。PC の手本は ADR-064（Meta Business Suite の PC 版）（同 :46）。入力欄の PC 側もこの分け方に従う（Opus の読み取り。PO が違えば直す）。「＋」の中身は PC とスマホの両方に出す（機能のため。Opus の既定）。
- Q3 文字の大きさ → PO に質問中
  - 事実: 測り方は「部品の構造データの文字の枠の高さ」と「写真の画素」（phone-runbook §5・benchmark/README 測り方1-2）。文字の大きさそのものを読む方法は手順に無い。文字の枠の高さは行の間隔を含むため、文字の大きさは逆算になる（benchmark/README:51「フォントサイズ自体は測れていないため『一致』とは言えない」）。
- Q3 → **決定 2026-10-31 PO 回答「2」**: スマホの画面写真から文字の高さを測り、近い大きさを選ぶ（値は逆算であることを記録に明記する）。
  - PO の問い: 「PCからスマホ操作してデータ取得したり連携したり出来る？」「アンドロイドは今はtermuxのubuntuでclaude codeが開発している」
  - 事実: Mac に adb は入っていない（which adb → not found、2026-10-31）。公式（developer.android.com/tools/adb 2026-10-31 取得）: USB デバッグ、または Android 11 以上のワイヤレスデバッグ（adb pair）でパソコンからつなげる。画面写真は `adb exec-out screencap -p > screen.png`。
  - 事実: スマホの中の Claude Code が撮る手順書は PO 合意済み（docs/handoff/app-visual-language/phone-capture-runbook.md・2026-10-05）。adb は Termux 本体で入れ、Ubuntu の中では入れない（同 §2）。この道で WhatsApp の観察メモが既に作られている（benchmark/whatsapp-*.md）。
  - 道の選び方 → PO に質問中
- 道の選び方 → **決定 2026-10-31 PO 回答「2」**: Mac に道具を入れて Mac から撮る。PO「wifiは同じwifiが繋がっている」。
  - 実施 2026-10-31 18:43 JST: `brew install --cask android-platform-tools` → 成功（37.0.1、/opt/homebrew/bin/adb。生出力 adb-install.txt）。署名 Developer ID Application: Google LLC (EQHXZ8M8AV)（codesign -dv）。
  - `adb version` が5分応答せず止めた。ファイルに macOS の「インターネットから取ってきた印」（com.apple.quarantine）が付いている。初回起動時の macOS の確認が画面に出て待っている可能性 → 未確認。印を外す操作は macOS の安全確認を飛ばすことになるので、Opus は行わず PO に聞く。

## 10. 払い方の決定（2026-11-01）
- Q1-6／§7 → **決定 2026-11-01 PO 回答「1」**: お客さまの払い方は「PayPal」「Wise」の2つだけ。出し方は払い方から自動で決める（PayPal＝リンク、Wise＝通貨に合う振込先付きの自社 PDF）。会社の設定の4択（tenant_policy の issue_mode）はなくす。
  - 帰結（設計で扱う）: ADR-101 §6（docs/adr/ADR-101-sa-quotation-invoice-generation.md:136-147）の改訂が要る。請求書の issue_mode 列（書き込みなし）の扱いも設計で決める。§5 Q1-6 の未決「会社の設定が pdf のとき」は解消。
  - 設計担当の既定（§5 Q1-5 の既定を置き換え。PO が変えるなら言う）: お客さまの払い方が空のときは、請求書を作るときに必ず選ぶ（選ぶまで送れない）。

## 11. 成功の条件 第2版（**PO 承認 2026-11-01 回答「1」**: この順番と確かめ方で進める）
§1・§3・§4 は 10/31 時点の古い案。決定を反映したのが本節。§2 の文字の大きさは measure1-summary.md で確定済みのため Q3 は解消。
出す順（案）: A 見た目 → B 表示の切り替え → C 届いた・読まれた印 → D 「＋」と請求書。1つずつ本番に出して確かめてから次へ。

| 番号 | 基準（○×） | 測り方 |
|---|---|---|
| A1 | スマホの吹き出しの角・余白・時刻の位置・幅、入力欄、送信ボタン、文字の大きさが WhatsApp 実測と ±1px | 幅360の本物の画面の写真と、画面の部品の大きさの読み取り値 |
| A2 | 新しい値はすべてデザイントークン経由・直書き0件。吹き出しの種類の行の直書き（TSX:568）も0件 | トークン点検（CI）と grep |
| A3 | PC の会話画面が前後で変わらない | PC 幅1280の前後の写真比較 |
| A4 | PO が写真を見て合格 | 本番に出す前に写真を PO に見せる |
| B1 | 「通常」で原文だけ、「日本語」で全部の吹き出しが和訳になる | 試験用の会話10件を両方の表示で写真に撮り、全件を確かめる |
| B2 | 届いた投稿・送った投稿は1分以内に和訳が保存される（予算の上限で止まった分を除く） | 届いた・送った時刻と和訳の保存時刻の差を100件で数え、100件中100件 |
| B3 | 片方の機械で切り替えると、もう片方の機械で開いたときも同じ表示 | PC で切り替え→スマホで開く を3回、3回中3回 |
| B4 | 訳せなかった投稿は原文＋「訳せませんでした」＋「もう一度訳す」。押すと訳が出る | 予算の上限を試験環境で再現して1件確かめる |
| B5 | 吹き出しごとの訳ボタンと「ヒューマンエージェント」の文字が出ない | 画面の写真と grep |
| C1 | メッセンジャーで送った投稿が、相手が読むと1分以内に「読まれた」の印になる | 試験用の相手に3回送り、3回中3回 |
| C2 | 知らせが来ない連絡手段では印が出ない | 対象の連絡手段ごとに写真1枚 |
| D1 | 「＋」から画像・定型文・登録リンクを送れる | 試験用の相手に各1回 |
| D2 | PayPal のお客さまにはリンク、Wise のお客さまには請求書の通貨の振込先が載った PDF が送られる | 試験用の相手に各1回、届いた中身を写真で確かめる |
| D3 | 振込先の無い通貨では送らず「この通貨の振込先が登録されていません」と出る | 1回 |
| D4 | PayPal がつながっていないと「PayPal がつながっていません」と出て、貼り付けたリンクで送れる | 1回 |
| D5 | お客さまの払い方（PayPal／Wise）を持ち、請求書を作るときに選び直せる。会社の4択の設定が画面から消える | 画面の写真と、請求書に残る払い方の値 |
| 全体 | 画面の文字は全部 t() 経由・ja/en 同じキー。新しい部品は金型（components/）を使う | i18n 点検と UI の決まりの点検（CI） |

## 2026-10-31 スマホ接続の記録（事実）
- adb pair 成功: 証拠 /tmp/CC報告ファイル/inbox-deal-ui/adb-pair.txt
- adb connect 成功・端末 SC-51G・Android 16・Physical size 1080x2340・density 480（=3.0倍、1dp=3px）: 証拠 /tmp/CC報告ファイル/inbox-deal-ui/adb-connect.txt
- 接続時点の前面は設定アプリ。WhatsAppの会話画面はPOに開いてもらう（どの会話を写すかはPOの判断）
