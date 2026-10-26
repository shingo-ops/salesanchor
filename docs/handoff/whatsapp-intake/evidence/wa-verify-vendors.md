# WhatsApp 既製品 3社 + 為替 原文確認（取得 2026-10-25 23:05〜23:25 JST）
生HTML・テキスト化: /private/tmp/claude-501/-Users-tanizawashingo-salesanchor/6188646d-799b-417a-9c66-665f20bd0080/scratchpad/wa-raw2/
方法: curl -sL -A "Mozilla/5.0" で生HTML取得。Playwright MCP は接続が閉じて使えず。WebSearch は URL 探しにのみ使い、判定は curl 原文のみ。

## G. 為替 【確認済】
出典: https://www.murc-kawasesouba.jp/fx/index.php （三菱UFJ銀行 対顧客為替相場。取得 2026-10-25 23:05 JST）
原文: 「2026年10月23日現在　As of October 23, 2026」「公表仲値（TTM）は、TTSとTTBの中間の相場であり、（TTS＋TTB）/2で算出されます。」
US Dollar USD: TTS 157.51 / TTB 155.51
- ページに TTM の数値は直接載らない。TTM = (157.51+155.51)/2 = 156.51（同ページの算出式による計算値）
- 最新掲載は 10/23(金)。10/24・25 は週末で、?id=261024 は同じ 10/23 ページを返した。2026-10-24 の値は存在しない。
- past_3month.php（日別一覧）の10月分リンクは 1,2,5〜9,13〜16,19〜22 日のみ（取得ファイル mufg.html）。

## F-1. respond.io
- 料金（https://respond.io/pricing 取得 23:05）【確認済】
  原文(meta/構造化データ): "Starter ($79/mo), Growth ($159/mo), Advanced ($279/mo) & Enterprise. Pay only for the contacts you talk to."
  構造化データ: Starter(Monthly) 99.00 / Growth(Monthly) 199.00 / Advanced(Monthly) 349.00 USD、Yearly は 79 / 159(年1908) / 279。トグル "Monthly" / "Yearly (Save up to 20%)"、既定は Yearly。→ $79等は年払い換算、月払いは $99/$199/$349。
  含まれる人数: 静的HTMLに記載なし【未確認】。分かるのは無料トライアル原文 "Growth plan for 5 users and 1,000 Monthly Active Contacts" のみ（プラン含有数ではない）。Growth 以上は Monthly Active Contacts で課金（原文 "Monthly Active Contacts relevant only for the Growth Plan and above"）。
  Meta料金: 【確認済】原文 "WhatsApp fees are not included in any respond.io subscription. Meta charges these fees based on your usage."
- 日本から申込可否: 【確認済(制限なし)】 https://respond.io/help/whatsapp/whatsapp-business-api-quick-start 原文 "The number must not be from any of these restricted countries: Crimea (+7978) Cuba (+53) Iran (+98) North Korea (+850) Syria (+963)"。日本なし。利用規約 https://respond.io/terms-of-service は "Users aren't located in a country that is subject to a U.S. Government embargo..."（国名列挙なし）。「日本拠点でも契約できる」と明記した文は無い。
- Meta ビジネス認証: 【確認済(必須とは書かれていない)】同 quick-start 原文 "A legitimate, publicly accessible business website is mandatory in your Business Info — without one, your WABA may be disabled. It's also required when applying for Meta Business Verification." 認証を必須とする文は見つからず。
- Coexistence: https://respond.io/help/whatsapp/whatsapp-coexistence（ページ表題 "WhatsApp Business App Quick Start (WhatsApp Coexistence)"、2026-10-21 付）。対応【確認済】。原文 "WhatsApp Coexistence is available only to businesses actively using the WhatsApp Business App, based on Meta's review of account age and messaging quality." / "WhatsApp Business App version 2.24.17 or later." / "Open the WhatsApp Business App at least once every 14 days" / "Contact and message history syncing is currently not supported."
  日本で可否: 公式ヘルプに国一覧なし【未確認】。ただし同社ブログ https://respond.io/blog/how-to-get-whatsapp-api 原文 "Coexistence is not allowed by Meta in the EU, European Economic Area, UK, South Africa, Russia, South Korea, Australia, Japan, Nigeria, Philippines or Turkey. Businesses in these areas will need to first delete their existing WhatsApp Business Account to use the same phone number."（ブログ＝日付不明、公式ヘルプではない）→ 日本は対象外と読めるが、最新性は未確認。

## F-2. WATI
- 料金（https://www.wati.io/pricing/ 取得 23:05）【確認済】
  原文: Growth "$39 month billed annually" "3 Users Included No additional users"／Pro "$79 month billed annually" "5 Users Included Additional Users @ $24/user/month"／Business 価格は Custom、"5 Users Included Additional Users @ $59/user/month"。ページに "Annual Monthly" トグルあり。月払いの金額は静的HTMLに出ず【未確認】。
  Meta料金: 【確認済】 "Additional charges apply for messages. Per message charges vary for marketing, utility & authentication." / "There is no setup fee associated with using the WhatsApp API."
- 日本から申込可否: 国の制限・禁止国一覧は料金ページ・ヘルプに見つからず【未確認】。利用規約(wati.io)は 403 で取得不可。
- Meta ビジネス認証: https://support.wati.io/en/articles/11462963 （2026-09-21付）【確認済(必須か任意かは明記なし)】原文 "what to expect during Meta's business verification process. It also explains the messaging limits for unverified businesses and how those limits are removed after verification." / "Meta requires a publicly accessible business website as part of the business verification process." / 前提に "Meta Business Manager ID"。→ 未認証でも始められ、上限が付くと読めるが、「任意」と明言する文はない。
- Coexistence: https://support.wati.io/en/articles/11822421-how-to-connect-your-whatsapp-number-to-wati-via-whatsapp-coexistence-coex 【確認済(対応)】原文 "WhatsApp Coexistence lets you connect your existing WhatsApp Business App number to Wati's Cloud API platform while continuing to use the WhatsApp Business App on your phone." "Available on: All plans - Growth, Pro and Business." "WhatsApp Business App version 2.24.17 or later" "You have a Facebook Business Page and administrator access to it." "Your country is supported for WhatsApp Coexistence onboarding. Meta restricts this feature in certain countries." "Personal WhatsApp numbers are not supported."
  日本で可否: 国名の記載なし【未確認】。
- 参考: 通常の Cloud API 接続は "Use a phone number that does not have an active WhatsApp account"（11462963）。既存番号は https://support.wati.io/en/articles/11463152 "you can connect the number to Wati through the WhatsApp Coexistence process and continue using the WhatsApp Business App."

## F-3. Twilio
- 料金（https://www.twilio.com/en-us/whatsapp/pricing 、"Pricing current as of September 2026"）【確認済】
  原文: "Twilio’s message handling fee: $0.005 per message" "Twilio’s per-message fee for WhatsApp is $0.005, inbound or outbound*" "Pay Meta’s template fees for Marketing, Utility, Authentication, Service messages"。月額プラン・含有人数の記載なし（従量のみ）。Meta料金は別（Twilio が立替で上乗せ請求）。
- 日本から申込可否: 国制限の記載は WhatsApp ドキュメントに見つからず【未確認】。利用規約 https://www.twilio.com/legal/tos は制裁対象者の禁止（"is not on any government sanctions or restricted party lists"）のみで国名列挙なし。料金ページの国別料金表に Japan が載る（送信先としての一覧であり申込可否の根拠ではない）。
- Meta ビジネス認証: https://www.twilio.com/docs/whatsapp/self-sign-up 【確認済】原文 "If you created a new Meta Business Portfolio during the Self Sign-up process or your existing Meta Business Portfolio hasn't completed business verification, you must complete business verification on Meta before you can move into production." / "When you complete business verification, you can: Increase your messaging limits. Add more than two WhatsApp senders." / "Meta's processing time for business verification varies by region and can take several weeks." → 本番移行には認証が必須。
- Coexistence: 取得した Twilio 公式ドキュメント（self-sign-up, best-practices-and-faqs, tech-provider integration-guide, api, tutorial/connect-number-business-profile）に "coexist" の語なし【未確認：記載なし】。逆に self-sign-up 原文 "If registered with WhatsApp or WhatsApp Business app: Delete the WhatsApp account" ＝ 既存アプリ番号は削除が前提。

## 判定サマリ
| 項目 | respond.io | WATI | Twilio |
|---|---|---|---|
| 月額原文 | 確認済 年$79/159/279・月$99/199/349（人数は未確認） | 確認済 年払い$39(3人)/$79(5人)/Custom(5人)・月払い額未確認 | 確認済 月額なし $0.005/通 |
| Meta料金別 | 確認済 別 | 確認済 別 | 確認済 別（立替上乗せ） |
| 日本から申込 | 禁止国に日本なし(確認済)・「日本可」の明記はなし | 未確認 | 未確認 |
| Meta認証 | 必須とは書かれず | 必須/任意の明記なし | 本番移行に必須(確認済) |
| Coexistence | 対応(確認済)・日本は公式未確認、同社ブログは日本不可 | 対応(確認済)・日本は未確認 | 記載なし(未確認) |
