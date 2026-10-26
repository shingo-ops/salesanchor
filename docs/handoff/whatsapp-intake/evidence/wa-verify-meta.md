# WhatsApp 一次資料の原文確認（取得日時 2026-10-25 23:04〜23:20 JST）
生データ: /private/tmp/claude-501/-Users-tanizawashingo-salesanchor/6188646d-799b-417a-9c66-665f20bd0080/scratchpad/wa-raw/
注: developers.facebook.com は ?locale=en_US 付き curl で英語原文のHTMLが取れた（日本語版は地域で自動切替）。faq.whatsapp.com と facebook.com/business/help は curl ではタイトルのみ→Playwright で表示して本文を読んだ。

## A. WhatsApp Business アプリ
- 料金【確認済（公式、ただしアプリ本体のダウンロード料金）】
  出典 https://business.whatsapp.com/whatsapp-vs-whatsapp-business （curl生HTML: wa-raw/https___business_whatsapp_com_whatsapp-vs-whatsapp-business.html.txt）
  原文: "Is the WhatsApp Business app free? Yes. The WhatsApp Business app is free-to-download." / "The WhatsApp Business app is free to download and uses a cellular connection or Wi-Fi exactly like the WhatsApp personal app."
  faq.whatsapp.com/641572844337957 の本文はPlaywrightが落ちて自分では読めず。WebSearch抜粋（二次）は "WhatsApp Business is a free-to-download app"。【FAQ原文は未確認】
  注意: 原文は "free-to-download"。Meta Verified/Meta One は有料サブスク（下記）。
- Metaビジネス認証の要否【記載なし】
  business.whatsapp.com/products/business-app, /business-app-features, 上記 vs ページを grep（verif）: 認証が必要とも不要とも書かれていない。認証に触れるのは有料の "Meta Verified"（チェックマーク・"linking up to 10 devices"）のみ。
- 端末数【確認済】
  出典 https://faq.whatsapp.com/395911122612120/?locale=en_US "About multi-agent"（Playwrightで表示、wa-raw/faq_395911122612120.yml）
  原文: 表 "Without multi-agent: Connect up to four devices to your account / With multi-agent: Connect up to 10 devices to your account"
  原文: "The maximum number of devices you can assign to your business account is determined by the benefits included in your Meta Verified or Meta One subscription." 
  原文: "Note: The premium version of this feature may not be available to you yet." / "If you cancel your subscription ... only your four most recently active devices will remain linked."
  → 標準4台、10台は Meta Verified か Meta One 加入時。
  参考 https://faq.whatsapp.com/1317564962315842 (How to link a device, 個人版): "using your primary phone to link up to four devices. You'll need to log in to WhatsApp on your primary phone every 14 days"

## B. Meta Business Suite 受信箱で WhatsApp【確認済：日本は対象外】
出典 https://www.facebook.com/business/help/353293243562513?locale=en_US （Playwright、wa-raw/fb_help_353293243562513.yml）
原文: "Syncing your WhatsApp Business account with Inbox in Meta Business Suite is only available in certain regions or countries."
原文: "You won't be able to access this feature if you are located in one of the following countries or regions: Australia; Japan; Nigeria; Philippines; Russia; South Africa; South Korea; Turkey; European Economic Area; European Union; United Kingdom."
他: "WhatsApp group chats will not be transferred. ... up to the last 6 months of individual chat history." / "You'll need to open your WhatsApp Business app at least once every 20 days"

## C. Coexistence
- 国【確認済：現在は日本も対応】
  出典 https://developers.facebook.com/documentation/business-messaging/whatsapp/changelog?locale=en_US （curl、wa-raw/dev_changelog.html.txt）
  原文 (Oct 23, 2025, Embedded Signup): "The following countries/regions are now supported for Coexistence in Embedded Signup: Australia, Japan, Philippines, Russia, South Korea, Turkey, European Economic Area (EEA), European Union (EU), United Kingdom (UK)"
  追加 (Apr 15, 2026): "WhatsApp Business app phone numbers from Nigeria and South Africa are now supported when onboarding WhatsApp Business app users via Embedded Signup."
  出典 .../embedded-signup/onboarding-business-app-users?locale=en_US （更新 Jun 26, 2026）に「対象外の国の一覧」は無し（grepでJapan/countries記載なし）。→ 日本は対象外一覧に入っていない。
  ※ 上のBの受信箱機能の対象外一覧（日本を含む）は別機能。混同注意。
- 制限される機能【確認済】同ページ "Feature comparison" 表（3列目 "Is the WhatsApp Business app feature supported on Cloud API?"）:
  1:1チャット Supported（直近6か月 "All chat messages in the most recent 6 months can be synchronized."）／連絡先 Supported／
  Not supported: グループ（"Group chats will not be synchronized."）、消えるメッセージ（1:1で無効化）、1回表示（無効化）、ライブ位置（無効化）、ブロードキャストリスト（"will be disabled... Existing Broadcast lists will become read-only."）、音声/ビデオ通話、ビジネスツール（catalog, orders, status）、メッセージツール（marketing messages, greeting message, away message, quick replies, labels）、ビジネスプロフィール、チャンネル。
  リンク端末: "All companion clients are supported, except for WhatsApp for Windows and WhatsApp for WearOS." / "all companion apps will be unlinked from the account, and the business can then re-link"
  その他: "fixed throughput of 20 mps"、"The 24-hour customer service window restriction applies to messages sent via Cloud API. Messages sent from the WhatsApp Business app are not subject to the customer service window"。
  料金: "messages sent by the business via the WhatsApp Business app will continue to be free, but messages sent via Cloud API will be subject to Cloud API pricing."
- 必要条件【一部確認済】
  原文 Requirements: "The business customer must use WhatsApp Business app version 2.24.17 or higher." / "You must already be a Solution Partner or Tech Provider." / "You must know how to use Cloud API." / "You must use Embedded Signup with session logging."
  → 導入する提供会社（自社システム側）が Tech Provider か Solution Partner であること。利用企業自身のビジネス認証の要否はこのページに記載なし【記載なし】。
  messaging-limits ページ: 認証は上限を2,000へ上げる経路の1つ（下記E）。Coexistence導入の必須条件としては書かれていない。

## D. 会話の料金
出典 https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing?locale=en_US （"Updated: Sep 30, 2026"、wa-raw/dev_pricing.en.html.txt）
- 課金方式【確認済】"Effective July 1, 2025 – Meta charges on a per-message basis ... by category–market, and only for messages from businesses to users. Meta does not charge for messages from users to businesses." "Businesses are only charged when a message is delivered."
- 無料になる条件【確認済・重要】"There are two instances where Meta does not charge for a message a business delivers to a WhatsApp user: (1) In the free entry point window ... (2) For the first 1,000 service messages each month – For each business phone number, Meta provides 1,000 free service messages per month, which do not roll over ... Meta only charges as of the 1,001st service message".
  → 「24時間以内の返信は常に無料」は成り立たない。24時間窓内の非テンプレ返信は "Service" カテゴリで、事業者の電話番号ごと月1,000通まで無料、1,001通目から課金。ユーザー→事業者の受信は無料。
  サービスメッセージ定義: "Any non-template message not powered by the Meta Business Agent Platform" / 非テンプレは "can only be sent in an open 24-hour customer service window, which opens and resets with each user message".
  FEP: 広告(CTWA)経由で最大7日 "The FEP window may remain open for up to 7 days." 窓内は marketing/utility/authentication/service とも無料。
- 2026-10-01 の変更【確認済】"This page reflects pricing updates that became effective as of October 1, 2026". "This only applies to service messages, as of 12am by Messaging account timezone on October 1, 2026. As Meta resumes charging for service messages, Meta provides every business phone number with a free tier of 1,000 service messages per month." Webhookのpricing type: 10/1以降、無料枠を超えた分は free_customer_service → regular。無料枠を超える運用で支払方法がないと配信されない旨の記載あり。
- 窓内のutilityの扱い: ページ本文に「窓内utilityが無料」という記載は見つからず（grep）。前回メモの「2025-07-01から窓内utilityが無料」は今回の原文では確認できず【未確認】。
- 国区分【確認済】同ページ: 47市場（名前付き39＋地域8）。"Rest of Asia Pacific – 16 markets: Afghanistan, Australia, Cambodia, China, Japan (JP) - 81, Laos, Mongolia, New Zealand, Papua New Guinea, Philippines, Taiwan (TW) - 886, Tajikistan, Thailand, Turkmenistan, Uzbekistan, Vietnam"。North America = Canada, United States。Hong Kong・Singapore・United Kingdom は名前付き市場。
- 料金表（List rates、USD、2026-10-01有効）【確認済】
  出典: 同ページの "List rates (CSV)" USDリンク（実体は xlsx。wa-raw/rate_1.csv、抜粋 wa-raw/usd_rates.txt）。表題 "Cost per message in USD on the WhatsApp Business Platform, effective October 1, 2026"。
  | 市場(受信者) | Marketing | Utility | Authentication | Service |
  | Rest of Asia Pacific（日本・台湾を含む） | 0.0842 | 0.0113 | 0.0113 | 0.0113 |
  | North America（米国） | 0.0250 | 0.0034 | 0.0034 | 0.0034 |
  | Hong Kong | 0.0732 | 0.0260 | 0.0260 | 0.0260 |
  | Singapore | 0.0732 | 0.0160 | 0.0160 | 0.0160 |
  | United Kingdom | 0.0635 | 0.0220 | 0.0220 | 0.0220 |
  Taiwan は単独行なし＝Rest of Asia Pacific の料金（0.0842/0.0113）。日本は Japan単独でなく Rest of Asia Pacific。単位は USD/通。utility・authentication は別CSVに月間量による段階単価あり（上は定価。段階表は未解読）。Meta Business Agent は別建て（"$2.00 USD / 1 M tokens"）。
  PDF版も同ページにあり未読（CSV=xlsxで足りた）。

## E. 送れる相手の上限【確認済】
出典 https://developers.facebook.com/documentation/business-messaging/whatsapp/messaging-limits?locale=en_US （wa-raw/dev_messaging-limits.en.html.txt）
原文: "Messaging limits are the maximum number of unique WhatsApp user phone numbers your business can deliver messages to, outside of a customer service window, within a moving 24-hour period."
原文: "Newly created business portfolios have a messaging limit of 250, but this messaging limit can be increased to: 2,000 (by completing a scaling path), 10,000 (via automatic scaling), 100,000 (via automatic scaling), Unlimited (via automatic scaling)"
Scaling paths（2,000へ）: "Verify your business" / "Have your partner verify your business (if you were onboarded by one)" / "Send 2,000 delivered messages outside of customer service windows to unique WhatsApp user phone numbers within a 30-day moving period, using templates with a high quality rating."
自動拡大: "sending high-quality messages across all ... In the last 7 days, your business has utilized at least half of your current messaging limit" → "increases by one level within 6 hours."
注: 上限は「窓外（テンプレ起点）」の相手数。ページに "未認証" という語での記載はなく、新規ポートフォリオ=250、認証等で2,000。顧客から先に来た会話への返信（窓内）は対象外。

## 未確認として残る点
- faq.whatsapp.com/641572844337957 の本文（Playwrightが接続切断で読めず）。無料の根拠は business.whatsapp.com の生HTMLで代替。
- Businessアプリ利用にビジネス認証が必要か: 公式ページに記載なし（「不要」の明記もなし）。
- Coexistence で利用企業自身の認証が必要か: 記載なし。
- 窓内utilityの無料扱い（前回メモ）: 今回の原文に記載なし。
- utility/authentication の月間量による段階単価（別シート）。
