# WhatsApp 取り込み事例調査（A〜E）
取得日: 2026-10-26 / 調査者: researcher / 方針: 数値なしは採用欄に入れない。推測で数値を補わない。
区分ラベル: [提供会社発表(利害あり)] / [第三者・一次報告(GitHub issue・フォーラム)] / [公式文書(Meta)]

## 0. 先に結論（調査の限界を含む）
- 目標の「A〜D 各2件以上の数値つき事例」: A=達成(成功3+失敗1)。B=事例は未達(数値つき成功1件のみ・提供会社発表。失敗は「制約の数値」のみで事例ではない)。C=達成(一次報告多数・ただし「停止割合」「復旧率」は分母が無く算出不能)。D=未達(数値つき事例0件。取り込み上限などの仕様数値のみ)。E=達成(3件)。
- 「個人事業での成否」を示した事例は E でも見つからなかった（未確認）。
- 提供会社発表の効果は、広告など他要因と混ざっている(Kommo自身が「自己申告・再現性不明」と明記)。

---
## A. 公式 Cloud API 直接 / BSP 経由で CRM 連携

### A-1 成功: Breakthrough Maths（respond.io） [提供会社発表(利害あり)]
| 項目 | 内容 |
|---|---|
| Who | Breakthrough Maths。オンライン数学コーチング。従業員数は未確認（月間アクティブ連絡先 約3,000） |
| When | 実施時期は未確認。ページに公開日なし（取得日 2026-10-26） |
| Where | アイルランド（英国でも事業） |
| What | WhatsApp アプリから WhatsApp Business API へ移行。respond.io の共有受信箱に会話を集約。一斉配信を利用 |
| Why | 問い合わせ対応の遅れ（原文要旨: 平均応答54分） |
| How | respond.io Business プラン(BSP経由) |
| How much | 平均応答時間 54分→26分(-50%)。売上 +35%。リード成約率 +21%。月間 受信約2,360件・一斉配信約12,800件。費用は公開データなし |
- 原文: "slashing the average from 54 minutes to just 26 minutes" / "a substantial 35% increase in sales" / "a 21% rise in lead conversion rates"
- URL: https://respond.io/customers/breakthrough-maths-boosts-sales-by-35-percent-by-halving-their-lead-response-times

### A-2 成功: Contalink（ActiveCampaign） [提供会社発表(利害あり)]
| 項目 | 内容 |
|---|---|
| Who | Contalink。SaaS。従業員 1-100人 |
| When | 未確認（ページに日付なし） |
| Where | メキシコ |
| What | WhatsApp Business から ActiveCampaign の WhatsApp Messaging へ。複数担当の受信箱、自動振り分け |
| Why | 顧客獲得・オンボーディング・サポートの会話の引き継ぎ |
| How | ActiveCampaign (BSP相当)。ルールで担当割当、フロー自動化 |
| How much | 成約率 +50%(4か月)。応答時間 -75%(初回応答 1時間→15分)。費用は公開データなし |
- 原文: "50% Increase in Conversion Rate" / "75% Faster Response Times"
- URL: https://www.activecampaign.com/customers/contalink

### A-3 成功: Solid Finanças / Carefree Boat Club Panama（Kommo） [提供会社発表(利害あり)・Meta公式サイト掲載]
| 項目 | 内容 |
|---|---|
| Who | Solid Finanças(金融・ブラジル)、Carefree Boat Club Panama(パナマ)。規模は未確認 |
| When | 集計期間 2025-11-01〜2026-04-01（5か月） |
| Where | ブラジル、パナマ |
| What | 既存の WhatsApp Business 番号を保ったまま、API 連携の自動化を追加（Click-to-WhatsApp 広告も併用） |
| Why | 応答遅れの解消、リード増 |
| How | Kommo(Meta Business Messaging Partner)。同じ電話番号のまま連携 |
| How much | Solid: 初回応答 15分→60秒未満(-70%)、月間有望リード +40%。Carefree: 1日のリード 3倍、初回応答 30〜60分→1分未満、リード1件の作業時間 最大-75%。費用は公開データなし |
- 原文: "Results are self-reported and not identifiably repeatable." / "70% reduction in first-response time" / "3X increase in daily sales leads"
- 注意: 広告の効果と分離不能。
- URL: https://whatsappbusiness.com/resources/success-stories/kommo/

### A-4 失敗: Cloud API で WABA が即時無効化（Meta開発者フォーラム） [第三者・一次報告]
| 項目 | 内容 |
|---|---|
| Who | 投稿者Adrián(会社名・規模は未確認)ほか、BSP(Callbell)を含む多数 |
| When | スレッド日付は相対表示のみ(約3年前、6月〜12月に返信)。正確な年は未確認 |
| Where | 国は未確認 |
| What | 番号追加の直後に WABA が「Business Policy 不適合」で無効化（期間: Permanent 表示） |
| Why | 投稿者はボット開発中に QA チームへ6通送っただけ、と主張 |
| How | 事業認証済みでも審査請求が却下。復旧策: 事業認証・支払方法追加・2FA(番号と全ユーザー)・再審査請求・Meta社員への連絡(投稿者1名は復旧) |
| How much | 「10分未満、時に即時」でブロック(返信者)。返信 約14件が同症状(Satya「複数回の審査請求は効かなかった」、Ram「選択回答では直らない」)。復旧は投稿者1名のみ確認、他は未解決。損失額は公開データなし |
- 原文: "WABAs get blocked in less than 10 minutes, sometimes even instantly." / "Multiple review requests didn't help."
- URL: https://developers.facebook.com/community/threads/806211104245421/

---
## B. Coexistence（スマホ Business アプリと API で同じ番号を共用）

### B-1 成功(数値あり・A-3 と同一事例): Kommo の2社（上記 A-3）
- 「同じ電話番号のまま」「会話履歴を失わない」を前面に出した事例。coexistence という語をページ自体が使っているかは未確認。

### B-2 制約の数値（事例ではない。Meta公式文書。失敗要因として使う） [公式文書(Meta)]
- URL: https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users （日付表示なし。ページ内に Embedded Signup v2/v3 を 2026-10-15 に廃止との記載）
- 原文: "you have 24 hours to synchronize their messaging history, otherwise they must be offboarded" / "have a fixed throughput of 20 mps" / "All chat messages in the most recent 6 months can be synchronized." / "only for media messages sent within 14 days of onboarding" / "primary device inactive for approximately 14 days" / "The business customer must use WhatsApp Business app version 2.24.17 or higher."
- 注意: この方式は「Solution Partner または Tech Provider」経由の導入が前提（原文 "You must already be a Solution Partner or Tech Provider."）。自社単独で Meta アプリ審査を通す経路とは別。
- BSP(WATI)ヘルプ 2026-09-07: 実利用 "at least 7 days of real activity in the WhatsApp Business App"(推奨30〜60日)、API 利用歴のある番号は "Use it actively for 1-2 months to rebuild eligibility"、履歴同期 "up to 6 hours"。エラー例 3441042 "This feature isn't available for phone numbers from this region."。URL: https://support.wati.io/en/articles/11875544-troubleshooting-whatsapp-coexistence-signup-process-common-issues-and-how-to-resolve-them [提供会社発表(利害あり)]
- 360dialog(第三者ではなくBSP文書): Standard Business Verification は coexistence で使えず、Partner-Led 認証か Meta Verified が必要。出典: https://docs.360dialog.com/docs/hub/embedded-signup/whatsapp-coexistence（検索結果の抜粋のみ確認、本文は未精読 → 未確認扱い）
- 失敗事例(実在企業が失敗した記録): 見つからず → 未確認。

---
## C. 非公式（whatsapp-web.js / Baileys）— 一次報告(GitHub issue)

### 集計方法と限界
- 方法: GitHub 検索 API で repo ごとに「ban」「banned」を含む issue 数を取得（2026-10-26）。
- 限界: issue 件数＝報告された件数。使用者全体(分母)が不明なので「停止された番号の割合」は算出不能。復旧率も集計データなし。

### 件数（生データ: scratchpad/ban_counts.txt）
全期間・issue: wwebjs/whatsapp-web.js は "ban" 84件・"banned" 58件・"suspended" 7件。WhiskeySockets/Baileys は "ban" 56件・"banned" 35件・"account suspended" 3件。
年別 "banned" を含む issue 数(題・本文) / その年の全 issue 数:
| 年 | whatsapp-web.js | Baileys |
|---|---|---|
| 2021 | 5/421 | -（repo 未作成扱い 0/0） |
| 2022 | 7/571 | 0/0 |
| 2023 | 9/605 | 2/321 |
| 2024 | 2/545 | 1/419 |
| 2025 | 5/355 | 14/665 |
| 2026(10/26まで) | 2/211 | 9/254 |
- 読み取り: Baileys は 2025 年に 1→14 件へ増加(2024比)。issue #1869(2025-10-05)に報告が集中。whatsapp-web.js は 2021〜2023 に多く、2025 も #3894 で集団報告。

### C-1 失敗: Baileys #1869 "High number of bans on WhatsApp!" [第三者・一次報告]
| 項目 | 内容 |
|---|---|
| Who | Baileys 利用者の開発者・ボット運営者。多数(会社名なし) |
| When | 2025-10-05 起票、2025-12-24 クローズ。コメント 39件 |
| Where | 国は未確認(ポルトガル語・スペイン語・英語の投稿あり) |
| What | Baileys v7.0.0-rc.5 / v6.7.19 の番号が大量停止 |
| Why | 目的は主にボット・自動化。業務利用の詳細は未確認 |
| How | 起票者 "This week alone, I was banned from 5 bots" |
| How much | 起票者1人 1週間で5番号停止(うち2つは3年以上無停止)。別の報告者 "same here 5 numbers" / "Mine also got banned 3 times" / "ban happened within 2 mins"(再接続後2分) / 28 ボット同一サーバーで運用中の人も停止。ban された個人番号が「数時間後に復旧」の報告 2件(bot に接続していない口座)。復旧の全体率: 公開データなし |
- 原文: "I was banned from 5 bots, each with approximately 9 groups. The most impressive thing is that two bots had been using Baileys for over 3 years and had never been banned"
- 別コメント: "The problem is that we are getting multiple bans in a row and then a permanent ban due to the number of bans in a short period of time"
- URL: https://github.com/WhiskeySockets/Baileys/issues/1869

### C-2 失敗: Baileys #2309 — サーバー上でステータス投稿 [第三者・一次報告]
- Who: 個人開発者(連絡先 約2,000〜3,000)。When: 2026-01-30、未解決(open)。
- What/How: 100人ずつチャンクでステータス投稿。ローカルPCでは正常、本番サーバーでは一時停止2回→永久停止。
- How much: 一時停止 2回 → 永久停止 1件。復旧: 質問したが回答での復旧手順は未確認。
- URL: https://github.com/WhiskeySockets/Baileys/issues/2309

### C-3 失敗: Baileys #2441 / #2707 — エラー463（reach-out time-lock） [第三者・一次報告]
- When: #2441 2026-03-25(コメント28件)、#2707 2026-07-14(open)。
- 内容: 原文 "WhatsApp seems to be locking users on a time-based rate-limit from sending new messages or making outgoing calls to **unknown** people." 保守側の調査では、過去に停止→復活したアカウントで 463 が出やすい。
- How much: 件数としての停止数なし(未確認)。#2707 では「繰り返す 463 で一時停止・停止に至る」との申告のみ。
- URL: https://github.com/WhiskeySockets/Baileys/issues/2441 , https://github.com/WhiskeySockets/Baileys/issues/2707

### C-4 失敗: whatsapp-web.js #532 — 顧客1,500人へ週次販促 [第三者・一次報告]
- Who: 小規模事業者(顧客リスト約1,500)。When: 2021-02-01 起票、2021-02-09 クローズ。Where: 未確認。
- How: 新規番号を登録→ライブラリで送信。画像のみ、禁止語回避、送信間隔1分、連絡先登録でも改善せず。
- How much: "after sending about 200 messages through whatsapp-web.js the account is banned"（最悪10通で停止）。
- URL: https://github.com/wwebjs/whatsapp-web.js/issues/532

### C-5 失敗: whatsapp-web.js #2247 — 3万件送信 [第三者・一次報告]
- When: 2023-06-02(クローズ 2023-12-04)。選挙の販促用途、India と推測できる番号形式だが国は未確認。
- How much: 1,000通で停止、対象 30,000件。回答: 利用規約違反との指摘。
- URL: https://github.com/wwebjs/whatsapp-web.js/issues/2247

### C-6 失敗: whatsapp-web.js #1872 — 20通・30分で停止 [第三者・一次報告]
- When: 2022-12-15 起票、2024-03-07 クローズ。How much: 原文 "After 30 min account get blocked"(20通前後)。
- 復旧: 保守側メンバー "There is nothing we can do. Email WhatsApp Support to get your number unbanned."（復旧の成功数: 未確認）。他の利用者 "all attempts to reactivate a number using the same IP are automatically marked as spam and the new number is banned... after blocking more than 6 numbers."（本人の観察。裏付け未確認）
- URL: https://github.com/wwebjs/whatsapp-web.js/issues/1872

### C-7 失敗: whatsapp-web.js #3894 — 「多くの顧客番号」が24時間制限 [第三者・一次報告]
- When: 2025-10-12 起票、2026-01-30 クローズ。コメント30件。
- 内容: "Many WhatsApp numbers are being logged out automatically... the account is restricted for 24 hours." / "Some accounts have also been banned completely."
- How much: 具体的な番号数は未確認。
- URL: https://github.com/wwebjs/whatsapp-web.js/issues/3894

### C 補足
- 公式の免責: whatsapp-web.js README 原文 "WhatsApp does not allow bots or unofficial clients on their platform, so this shouldn't be considered totally safe." / "it is not guaranteed you will not be blocked by using this method."
- Baileys の悪意ある派生パッケージ(マルウェア)警告: osv.dev MAL-2026-4470 等（検索結果で確認、本文未精読）。
- 提供会社(bot.space)の「公式API vs 非公式」比較は宣伝色あり。採用せず。

### 成功事例（非公式で安定運用した数値つき事例）
- 見つからず。#1869 の「3年以上無停止」(2 bots)が唯一の言及だが、その後停止している。

---
## D. 手作業（会話の書き出し・転記）

- 数値つき事例: **0件**（未確認）。検索で得られたのは作り方のガイドのみ（DRAG 2025頃、folk、Zoho中国語記事）。
- 仕様の数値(事例ではない): 書き出しは、メディアなしで約40,000通、メディア付きで約10,000通が上限（二次情報。WhatsApp ヘルプ本文は取得できず公式未確認。https://www.pcwelt.de/ratgeber/Whatsapp-Chat-exportieren-und-teilen-so-geht-s-11015467.html 他）。モバイルアプリからのみ書き出し可、.txt、メディアは別ファイル(folk ガイド)。繰り返さないと最新にならない(DRAG)。
- 数値なしの欄に分類: 上記ガイド類（提供会社の宣伝を含む）。

---
## E. Meta ビジネス認証の却下・長期化

### E-1 却下4回・約6週間・理由なし（UK代理店） [第三者・一次報告]
| 項目 | 内容 |
|---|---|
| Who | 投稿者 Luke F.、クライアントは英国登録の高級ライフスタイル系代理店。個人事業ではない |
| When | 2026-09-17 投稿 |
| Where | 英国 |
| What | WhatsApp Business API 用の Meta ビジネス認証が連続却下 |
| Why | 理由は表示されず |
| How | 再申請を繰り返した。毎回テスト用 WhatsApp Business Account が重複して残る。同じ会社の別ブランドは認証に成功。返信: 新規テストアカウント作成を止め、BSP 経由で手動審査を押すと良い |
| How much | 却下 4回、約6週間。解決の報告はスレッド内に無し(再申請で通ったかは未確認) |
- 原文: "rejected four times over about six weeks, no reason given" / "Oddly, a second brand under the same business verified fine."
- URL: https://community.clay.com/x/general/msg_XIk2G2WfX1p8/tips-for-overcoming-meta-business-verification-iss

### E-2 「審査中」のまま約3〜3.5か月（Meta開発者コミュニティ） [第三者・一次報告]
- Who: 投稿者 sebodingdong、ErezFlows（個人か会社かは未確認、国も未確認）。
- When: 一覧の取得日 2026-10-26。2026年6月末から約3.5か月、もう1件は約3か月。
- 内容: Security Center 表示では目安約2営業日。"There has been no request for more information, no email, and nothing in my Support Inbox"。返信 2件・1件。解決の報告なし。ErezFlows の件は App Review が止まっている。
- 注意: 別の検索結果にある「エラー141010でWABAがブロック」スレッドは一覧のみで本文を読めず、日数は未確認。
- URL: https://communityforums.atmeta.com/discussions/Questions_Discussions/whatsapp-business-verification-stuck-in-review-past-sla-%E2%80%94-waba-blocked-141010/1377120

### E-3 BSP文書の数値（事例ではなく仕様） [提供会社発表(利害あり)]
- Brevo: 再申請は最大3回(原文要旨 "up to 3 chances")。※ページは HTTP 403 で本文を取得できず、検索結果の要約のみ（未確認扱い）。
- 360dialog: 審査は最大14営業日、30日放置された場合は Trust and Safety へエスカレーションする（検索結果の要約のみ、本文未精読 → 未確認扱い）。却下理由の確認: Business Manager > Security Center > Contact Facebook。
- 日本向け許可書類(360dialog/WATI 国別リスト経由、本文未精読): 個人事業の開業届、営業許可、銀行明細、公共料金など。→ 未確認。
- Tenreply 2026-10-17: "Meta does not publish a guaranteed time." / 個人事業主向け "alternative document list offered for your country" [提供会社発表(利害あり)]。

### E の欠落
- 「再申請で通った方法」と「個人事業での成否」を示す、日数つきの一次報告: 見つからず(未確認)。
- 日本の個人事業の日数・却下理由: 公開データなし。

---
## 成功要因（数値と結びつけ）
1. 受信箱を1か所に集約して担当を自動割当: 応答時間 54→26分(-50%)、1時間→15分(-75%)、15分→1分未満。事例 3/3（すべて提供会社発表）。
2. 電話番号と履歴を保つ(Kommo): 番号を変えずに導入。1日のリード3倍、月間有望リード+40%（広告併用で分離不能）。
3. 一斉配信を同意済み相手に限る: 数値での直接検証事例は未確認。

## 失敗要因（数値と結びつけ）
1. 新規番号で未登録の相手へ連続送信(非公式): 約200通(#532)、1,000通(#2247)、20通前後・30分(#1872)で停止。事例 3件。
2. サーバー(データセンター)から接続: #2309 一時停止2回→永久停止。#2805(Official Business Account の青バッジ番号は QR 読込直後に制限、2026-09-07、open、1件の申告)。
3. 一度停止した番号の再利用・同じIP: 6番号以上ブロックの本人観察(#1872)、保守側の調査で 463 と過去の停止歴の関係(#2441)。
4. 公式側の自動審査で理由なく却下・無効化: 4回/6週間(E-1)、3〜3.5か月(E-2)、WABA が10分未満で無効化(A-4)。
5. coexistence の入口条件: 実利用7日以上(推奨30〜60日)、同期24時間以内、スマホは約14日以上放置しない。

## 数値なしの欄（採用しない）
- ChatArchitect: 手作業負荷-40%、予約欠席-30%、成約+20%（出典不明）。
- Wassenger: 4時間→5分、成約15%→45%（例示で実在企業なし）。
- TimelinesAI: 応答時間-80%、-35%（出典なし）。
- Eazybe: 手入力-65%（出典なし）。
- Chattigo: 84%の回答者がリード増（調査方法未確認）。
- MyAlice(Metal Detectors SA): 初回応答 -33.03%、解決時間 -23.66%（本文未精読。WhatsApp 利用かも未確認）。
- Interakt(Taal Healthcare): 応答 -30%、反応 +50%（検索結果の抜粋のみ、本文未精読）。
- Mercedes-Benz Turkey 他 Meta 成功事例（大企業・本件と規模が違う）。
- LinkedIn の「中小企業 MSME が突然停止」投稿（単一の主張・数値なし）。
- DEV Community(darkterminal, 2025-02-24): "I've sacrificed a lot of phone numbers"（件数なし）。
- D の手作業の成功・失敗事例（数値つき事例なし）。

## 出典一覧（取得日 2026-10-26）
1. https://respond.io/customers/breakthrough-maths-boosts-sales-by-35-percent-by-halving-their-lead-response-times （日付なし）[提供会社]
2. https://www.activecampaign.com/customers/contalink （日付なし）[提供会社]
3. https://whatsappbusiness.com/resources/success-stories/kommo/ （期間 2025-11〜2026-04）[提供会社]
4. https://developers.facebook.com/community/threads/806211104245421/ （相対日付）[フォーラム]
5. https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users [Meta公式]
6. https://support.wati.io/en/articles/11875544-troubleshooting-whatsapp-coexistence-signup-process-common-issues-and-how-to-resolve-them （2026-09-07）[提供会社]
7. https://github.com/WhiskeySockets/Baileys/issues/1869 （2025-10-05）
8. https://github.com/WhiskeySockets/Baileys/issues/2309 （2026-01-30）
9. https://github.com/WhiskeySockets/Baileys/issues/2441 （2026-03-25）
10. https://github.com/WhiskeySockets/Baileys/issues/2707 （2026-07-14）
11. https://github.com/WhiskeySockets/Baileys/issues/2805 （2026-09-07）
12. https://github.com/wwebjs/whatsapp-web.js/issues/532 （2021-02-01）
13. https://github.com/wwebjs/whatsapp-web.js/issues/1872 （2022-12-15）
14. https://github.com/wwebjs/whatsapp-web.js/issues/2247 （2023-06-02）
15. https://github.com/wwebjs/whatsapp-web.js/issues/3894 （2025-10-12）
16. https://github.com/wwebjs/whatsapp-web.js （README 免責）
17. https://community.clay.com/x/general/msg_XIk2G2WfX1p8/tips-for-overcoming-meta-business-verification-iss （2026-09-17）
18. https://communityforums.atmeta.com/discussions/Questions_Discussions/whatsapp-business-verification-stuck-in-review-past-sla-%E2%80%94-waba-blocked-141010/1377120
19. https://www.tenreply.com/blog/meta-business-verification-failed-stuck-fix （2026-10-17）[提供会社]
20. https://dev.to/darkterminal/whatsback-web-automate-whatsapp-with-power-responsibility-ap6 （2025-02-24）
21. 検索結果のみ確認・本文未精読: help.brevo.com/hc/en-us/articles/7517984313362（403）、docs.360dialog.com（各ページ）、dragapp.com/blog/whatsapp-crm、folk.app 各ガイド、zoho.com.cn/crm/articles/whatsapp-export0929.html
