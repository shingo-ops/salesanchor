# 審査なしで自社WhatsApp番号の会話を取り込む方法：一次資料の確認
取得日時: 2026-10-26 09:26〜09:50 JST。生データ: wa-raw3/（同フォルダ）。
取得法: developers.facebook.com は curl（?locale=en_US、または .md 付きURLで原文Markdown）。faq.whatsapp.com は Playwright。whatsapp.com/legal は curl。WebFetch は不使用。WebSearch は「ページを探す」用途のみで、判定の根拠にしていない（二次情報は別記）。
注意: /docs/development/release/access-verification 等は ?locale=en_US だけだと日本語が返る。Accept-Language: en-US を足すと英語。

## 項目1 自社番号を Cloud API で直接利用（Tech Provider でない）
### 1-a App Review 不要【確認済】
出典 https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/app-review/ （wa-raw3/solution-providers_app-review.txt）
原文: "Business apps are automatically approved for Standard Access for all Permissions and Features available to the Business app type, so you can test your app while you are in this access level. Make sure your test users have a developer or admin role in the Meta app being used to implement Embedded Signup. This means that if you are using the API for yourself as a Direct Developer, you do not need Advanced access or app review."
原文: "If you are building an app that other businesses will be using, you must request Advanced access for any permissions your app needs."
→ 自社利用（Direct Developer）は Advanced access も App Review も不要、と明記。

### 1-b 受信 webhook に必要な権限【確認済】
出典 https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview.md （wa-raw3/md_webhooks_overview.md）
原文: "You need the following permissions to receive webhooks: whatsapp_business_messaging — for messages and calls webhooks / whatsapp_business_management — for all other webhooks"
原文: "If you are a direct developer, use your system user to grant your app these permissions when generating your system token."
原文: "If you are a partner ... you must be approved for advanced access for the permissions via App Review before your business customers will be able to grant your app these permissions during onboarding."
→ 直接利用者はシステムユーザーのトークンで権限を付与するだけ。審査の言及は partner 側のみ。

### 1-c ビジネス認証 不要（アプリが自社ユーザーだけの場合）【確認済】／WhatsApp固有ページでの「不要」明記は【未確認】
出典 https://developers.facebook.com/docs/development/release/business-verification/ （Accept-Language: en-US。wa-raw3/en_business-verification.txt）
原文: "Apps that request advanced access for permissions and apps that allow other Businesses to access their own data must be connected to a Business that has completed Business Verification."
原文: "If your app will only be used by app users who have a role on the app itself you do not need to complete verification; these users can grant your app any permissions at any time and all features are always active."
→ 一般規則としては、役割(role)を持つ自社ユーザーだけが使うアプリは認証不要。ただし WhatsApp の get-started ページ自体（wa-raw3/get-started.txt, m2_get-started.md）には「認証不要」の文言なし。
get-started の流れ（原文）: "Open the Meta App Dashboard to create a new Meta app with the WhatsApp use case." / "Click Generate access token to generate a temporary access token" / "You will need to set up a webhook endpoint in order to receive notifications" / システムユーザー作成→ "Select your app and toggle Manage app under Full control. Select your WhatsApp account and toggle Manage WhatsApp Business accounts under Full control." 手順のどこにも認証・審査の手順は出ない。

### 1-d Live モード【未確認（明文なし）】
出典 https://developers.facebook.com/docs/development/build-and-test/app-modes/ （wa-raw3/en_appmodes.txt）
原文: "Apps in Development mode can only request permissions from role users, and only permissions with standard or advanced access levels. Similarly, features will only be active for role users"
原文: "Apps in Live mode can request permissions from anyone, but only permissions approved through App Review."
→ 自社のロール保持者だけで使う限り Development のままで足りる、と読めるが、「WhatsApp webhook が Development モードのアプリに実際に届く」と書いた原文は見つからず【未確認】。試したこと: webhooks/overview.md、create-webhook-endpoint、get-started、app-modes を grep（"development mode"/"live mode"）。webhooks/overview.md には "Before you can use your app in a production capacity, you must create and configure your own webhook endpoint on a public server"（create-webhook-endpoint）とあるのみ。実機で確かめるのが確実。

### 1-e 未認証での上限【確認済】
- 番号数 出典 https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/phone-numbers.md （m2_business-phone-numbers_phone-numbers.md）
  原文: "New business portfolios are initially capped at two registered business phone numbers. If your business becomes verified, or if you have reached a messaging limit of 2,000, Meta will automatically increase your cap to 20."
- 相手の数 出典 .../messaging-limits （前回 wa-raw/ で確認済）
  原文: "Newly created business portfolios have a messaging limit of 250 ..." ただしこれは「顧客サービス窓の外で」届けられる相手数の上限（原文 "outside of a customer service window"）。受信は対象外。
- 表示名 出典 https://developers.facebook.com/documentation/business-messaging/whatsapp/display-names.md
  原文: "When you reach a higher messaging limit, your business phone number's display name automatically undergoes verification based on the display name guidelines."
  原文: "It can also appear at the top of individual chat threads and the chat list if your business phone number is approved via display name verification."
  → 表示名の審査は上限が上がった時点で自動。未承認でも番号登録・送受信が可能かは明記なし【未確認】。
- 受信 webhook の可否: 受信メッセージの課金 "Meta does not charge for messages from users to businesses"（前回確認）。未認証だと受信できない、という文言は見つからず【未確認（反証もなし）】。
- 既存番号の注意【確認済】 同 phone-numbers.md 原文: "Numbers already in use with WhatsApp cannot be registered unless they are deleted first." → 今スマホの WhatsApp / Business アプリで使っている番号は、そのままでは Cloud API に登録できない。併用(Coexistence)は次項。
- Coexistence 条件 出典 .../embedded-signup/onboarding-business-app-users 原文: "You must already be a Solution Partner or Tech Provider." / "You must use Embedded Signup with session logging." → 直接利用者が Coexistence を自力で使えるとは書かれていない【自社での利用可否は未確認】。

## 項目2 Tech Provider の Access verification【確認済】
出典 https://developers.facebook.com/docs/development/release/access-verification/ （wa-raw3/en_access-verification.txt）
原文: "Any business that has created or claimed an app that will be used by other businesses and requires any of the permissions listed below must be verified as a Tech Provider before other businesses can use the app." （対象権限の一覧に whatsapp_business_management が含まれる。whatsapp_business_messaging は一覧に無し）
原文: "Note that access verification is independent of App Review and permission access levels."
原文: "the endpoint first checks if the person who granted the permission has a role on the app itself. If the person does have a role on the app, the endpoint accepts the call and continues processing the request."
原文: "Before a business admin can begin the access verification process: a business admin must complete Business Verification"
→ 他社が使うアプリの場合に必要。アプリに役割を持つ本人が付与した権限なら検査を通る。自社だけで使う場合は対象外と読める（一覧と上記規則による）。
Tech Provider 公式手順 https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/get-started-for-tech-providers/ 原文: "To become a tech provider you need to verify your business with Meta." / "Your business must be verified before you can start the app review process."

## 項目3 受信 webhook（messages）【確認済】
出典 https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages/text.md ほか（wa-raw3/md_webhooks_reference_messages_text.md, ..._image.md）
- 権限: 上記1-b（messages は whatsapp_business_messaging）。
- テキスト: "from"(送信者番号 <WHATSAPP_USER_PHONE_NUMBER>)、"id"、"timestamp"("Unix timestamp indicating when the webhook was triggered.")、"type":"text"、"text":{"body"}。contacts[].profile.name と wa_id も付く。
- 画像: "type":"image"、image:{caption, mime_type, sha256, id, url}。原文: "You can perform a GET on this ID to get the asset URL, then perform a GET on the returned URL (using your access token) to get the underlying asset."（"url" は "being released to developers gradually ... starting November 12, 2025"）
- 注意: timestamp は webhook 発火時刻の表記（メッセージ作成時刻ではない書き方）。
- 履歴は取れない: 原文 "There are no APIs for fetching historical webhook data, so capture and store webhook payloads accordingly."（create-webhook-endpoint）。再送は最大7日（"for up to 7 days"）。
- 自分がスマホから送った分: smb_message_echoes / history webhook は Coexistence 用（onboarding-business-app-users にリンク）。直接利用で出るかは【未確認】。

## 項目4 チャット書き出し（Export chat）
出典 https://faq.whatsapp.com/1180414079177245/ （Playwright、?cms_platform=android / iphone / web、en_US、2026-10-26 取得。wa-raw3/faq_1180414079177245.txt に Web 版のみ保存。Android/iPhone は Playwright の戻り値から転記）
- Android【確認済】原文: "Tap > More > Export chat. Tap Without media or Include media. Choose your desired method (ex. Quick Share, Gmail, or Chat) to export chat history." / "If you choose Include media, the most recent media sent will be added as attachments to be sent from your sharesheet." / "Your chat history can't be re-imported because it's a text file and not a backup file."
- iPhone【確認済】原文: "Tap your contact's name or group name > Export chat. If the chat contains media, choose With all media, With selected media…, or Without media." / "Your chat history will be exported as a ZIP file." / "View once messages will not be exported."
- Web【確認済】原文: "Select All messages or Custom date range." "Your chat history will be exported as a ZIP file. Media isn't included, unlike exporting chats on your mobile device."
- 形式: iPhone/Web は ZIP、Android は共有先へ渡す形で形式の明記なし（"a text file"）。
- 件数上限【未確認】: 現在の公式ページ（en_US と kk_KZ の両方を取得）に件数の数字は無い。WebSearch の抜粋（二次情報）に「添付あり1万件・なし4万件、メールのサイズ制限のため」とあったが、現行ページ原文では確認できず。旧版FAQの文言の可能性があり、採用不可。
- 会話ごと手動。Business アプリ固有のページは見つけられず【未確認】。

## 項目5 非公式の方法
### 5-a 個人版 利用規約 https://www.whatsapp.com/legal/terms-of-service （curl。ページ表示の Effective Date: January 4, 2021。wa-raw3/legal_terms-of-service.txt）【確認済】
原文: "You will not use (or assist others in using) our Services in ways that: ... (e) involve sending illegal or impermissible communications such as bulk messaging, auto-messaging, auto-dialing, and the like; or (f) involve any non-personal use of our Services unless otherwise authorized by us."
原文: "You must not (or assist others to) directly, indirectly, through automated or other means, access, use, copy, adapt, modify ... or otherwise exploit our Services in impermissible or unauthorized manners ... including that you must not directly or through automated means: (a) reverse engineer, alter, modify, create derivative works from, decompile, or extract code from our Services; ... (e) create accounts for our Services through unauthorized or automated means; (f) collect information of or about our users in any impermissible or unauthorized manner; ... (h) distribute or make our Services available over a network where they could be used by multiple devices at the same time, except as authorized through tools we have expressly provided via our Services; (i) create software or APIs that function substantially the same as our Services and offer them for use by third parties in an unauthorized manner"
原文: "We may modify, suspend, or terminate your access to or use of our Services anytime for any reason, such as if you violate the letter or spirit of our Terms"
### 5-b Business アプリ利用規約 https://www.whatsapp.com/legal/WhatsApp-Terms-for-WhatsApp-Business-App （Effective September 23, 2026。wa-raw3/l3_WhatsApp-Terms-for-WhatsApp-Business-App.txt）【確認済】
原文 Restrictions: "Company must not directly, indirectly, or through automated or other means: ... (e) reverse engineer any aspect of our Business App Services ...; (f) scrape or extract data from our Business App Services; (g) develop or use any applications that interact with our Business App Services without our prior written consent; and (h) create software or APIs that function substantially the same as our Business App Services and offer them for use by third parties in an unauthorized manner"
原文: "(b) distribute or make our Business App Services available over a network to be used by multiple devices at the same time, except as authorized through tools and configurations that we have expressly provided for your use"
原文 Terminating: "We may modify, suspend, or terminate Company's access to or use of our Business App Services ... including if we determine, in our sole discretion, that Company violates these Business App Terms"
→ 非公式ライブラリ(whatsapp-web.js、Baileys 等)や WhatsApp Web の自動操作は、(g)「事前の書面同意なしにアプリと連携するアプリの開発・使用」にあたると読める。ただしライブラリ名を挙げた条文は見つからず、当てはめは解釈【名指しは未確認】。
### 5-c 公式FAQ【確認済】
- https://faq.whatsapp.com/520312452657376/ "About unofficial apps": "Unofficial apps or websites are fake WhatsApp apps, developed by third-parties. Using these apps or linking your WhatsApp account to unofficial versions of WhatsApp violates our Terms of Service." / "Your WhatsApp account might also be temporarily or permanently banned, or it could lead to restrictions on your account, including the ability to link devices." 例示: "GB WhatsApp, FM WhatsApp, TeleMessage, TM WhatsApp, and others."
- https://faq.whatsapp.com/general/temporarily-banned/about-temporarily-banned-accounts/ : "Switch to the official app or stop engaging in scraping after being temporarily banned. If you don't, your account might be permanently banned" / "Scraping is the automated extraction of information, both targeted and at scale, for any unpermitted purposes."
- https://faq.whatsapp.com/465883178708358/ "About account bans": "We ban accounts if we believe the account activity violates our Terms of Service" / "You can't access your chat history or backups while your account is banned." / "If you don't see an option to request a review, it means the ban is final and can't be appealed."
- https://faq.whatsapp.com/434518851968943/ : "Accounts could be temporarily or permanently banned if suspected of scraping personal information from WhatsApp."
- Business 用 "About account bans on the WhatsApp Business App" は存在がリンクで確認できたのみ、本文は未取得【未確認】。
