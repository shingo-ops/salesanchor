# 秘書の声 — 外部・過去事例（5W2H・数値つき）

親: [kgi.md](kgi.md)・設計: [design.md](design.md)・調べた日: 2026-11-17（Web 検索と公式ページの取得。実測ではない）

## 0. 読み方と限界

- 数値の多くは、読み上げの仕組みを売る会社自身の発表です。第三者の監査済みの数ではありません。
- 日本の会社が業務アプリの秘書に声を付けた事例で、数値つきのものは見つかりませんでした。
- 「この事例があるから必ず成功する」と言える直接の根拠はありません。事例から借りるのは「成功・失敗を分けた要因」です。成否の判定は kgi.md の K1〜K5 を本番で測って決めます。

## 1. 成功事例

| # | Who（誰が） | What（何を） | When | Where | Why（なぜ） | How（どうやって） | How much（数値の成果） | 出典 | 限界 |
|---|---|---|---|---|---|---|---|---|---|
| S1 | Penn Foster（米国の通信教育・年 15 万人の受講者） | 教材の文章に読み上げを付けた | 記事の時点（日付は記事に明記なし） | オンライン講座 | 読むのが苦手な受講者の脱落を減らす | ReadSpeaker の読み上げを講座画面に埋め込み | 30 日以内の講座修了が 54% 増。試験を終えるまでが 13 日 → 9 日 | https://www.readspeaker.com/blog/implementing-text-to-speech-in-corporate-learning/ | 売る側（ReadSpeaker）の発表 |
| S2 | Bloomberg（米国の報道） | 記事の音声版 | 約 5 年前 | ニュースサイト | 読む時間の無い人にも記事を届ける | Play.ht の読み上げ | 1 回の訪問で聞く記事が 2.5 本 → 6 本。5,000 記事で、再生を押した人は訪問者の 5%・そのうち最後まで聞いた人は 18% | https://medium.com/@HammadH4/increasing-user-engagement-with-text-to-speech-a-case-study-by-play-ht-771a0f10b0da | 売る側の発表・古い |
| S3 | The Washington Post（米国の報道） | 記事の音声版 | 記事の時点 | ニュースサイト | 滞在を延ばす | 自動の読み上げ | 音声で聞いた人は 3 倍長く留まった | https://niemanreports.org/audio-articles-are-helping-news-outlets-gain-loyal-audiences/ ・ https://beyondwords.io/blog/news-publishers-using-audio-articles/ | 比べた条件の詳細は記事に無い |
| S4 | Il Foglio（イタリアの新聞） | 記事の音声版 | 記事の時点 | 新聞のサイト | いちばん自然なイタリア語の声が欲しい | **Google Chirp 3: HD**（私たちと同じ声の仕組み）。日替わりで 4 つの声を使う | 担当が 1 日で使い方を覚えた | https://cloud.google.com/customers/il-foglio | Google 自身の事例紹介。効果の数値は無い |

## 2. 失敗事例

| # | Who | What | When | Where | Why（失敗の要因） | How | How much（数値の損失） | 出典 | 限界 |
|---|---|---|---|---|---|---|---|---|---|
| F1 | Amazon（Alexa の機器部門） | 声の秘書の機器 | 2017〜2021 年 | 家庭 | 機器を安売りし、収入の道が弱かった。使われ方が「タイマー代わり」にとどまった。技術より先に期限を切った | 声で話しかける秘書 | 機器部門の損失 250 億ドル超 | https://qz.com/amazon-lost-25-billion-alexa-devices-echo-kindle-jassy-1851602188 （Wall Street Journal 2024 年 7 月の報道を紹介） | 機器の事業全体の損失で、声だけの損失ではない |
| F2 | OpenAI（ChatGPT の声「Sky」） | 声の一つを取り下げ | 2024 年 5 月 | ChatGPT | 俳優スカーレット・ヨハンソンさんの声に似ていると批判された | 5 か月かけて選んだ声 | 公開した声を取り下げ・利用者は別の声（Juniper）へ移された | https://www.bloomberg.com/news/articles/2024-05-20/openai-to-pull-johansson-soundalike-sky-s-voice-from-chatgpt | 損失の金額は不明 |
| F3 | 企業の声の秘書全般（Forrester の調べ・2020 年ごろ） | 業務に声の秘書を入れる | 2020 年ごろ | 企業 | 使いみちが無い 39%・使われない 24%・効果が測れない | 調査 | 利用者の 65% が「聞き違いがあった」と答えた | https://www.destinationcrm.com/Articles/CRM-Insights/Insight/Voice-Assistants-Still-Underutilized-for-Business-153441.aspx ・ https://www.infoworld.com/article/4153289/building-enterprise-voice-ai-agents-a-ux-approach.html | 声で話しかける（聞き取り）を含む調べ。私たちは読み上げだけ |

## 3. 判断に使う技術の事実

| # | 事実 | 数値 | 出典 |
|---|---|---|---|
| T1 | Chrome は、人が押す前に音を鳴らそうとすると止める | `play()` が NotAllowedError で拒まれる | https://developer.chrome.com/blog/autoplay |
| T2 | 声の自然さの比べ（第三者の点数） | Chirp 3 HD 1,056 点・Azure HD 1,127 点・ElevenLabs v3 1,179 点 | https://opentranscription.io/blog/google-cloud-chirp-3-capabilities-architecture-costs-and-com.html |
| T3 | 会話で自然に感じる待ち時間 | 0.5〜0.8 秒が目安。医療の会話の論文では 1 秒未満が滑らか。人型ロボットの実測の平均は 1.35 秒 | https://telnyx.com/resources/low-latency-voice-ai ・ https://arxiv.org/pdf/2603.29893 ・ https://arxiv.org/pdf/2503.15496 |
| T4 | 料金 | Chirp 3: HD は毎月 100 万字まで無料。超えたら 100 万字 30 ドル（1 ドル 157 円で約 4,710 円。為替は 2026-09-30 の外為どっとコムの記事の値・当日の値は未確認） | https://cloud.google.com/text-to-speech/pricing ・ https://www.gaitame.com/media/entry/2026/09/30/071337 |
| T5 | Google は読み上げに送った文と音を記録しない | 公式の文 | https://docs.cloud.google.com/text-to-speech/docs/data-logging |
| T6 | 画面の安全設定の `media-src` が守るのは `<audio>` と `<video>` の読み込み | 公式の説明 | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/media-src |

## 4. 成功要因・失敗要因 → 私たちの設計での手当て

| 要因 | どこから | 設計での手当て（design.md の節） |
|---|---|---|
| 自然な声を選ぶ | S4 | PO が 30 の声から聞き比べて 4 つに絞った（§1） |
| 使う人が自分で選べる・押した人だけに鳴る | S2（再生は 5%） | 「声で返事」は最初は切れていて、押した人だけ（§4-4）。使われた回数は台帳で数える（§9） |
| 待たせない | T3 | 文の区切りごとに作り、最初の 1 文が出来たら鳴らす。K4 で本番を測る（§4-3・§8） |
| 費用が膨らまない | F1 | 月 90 万字で止める上限を backend に置く（§4-2） |
| 声の権利 | F2 | 有名人に似せた声や声の複製は使わない。Google が用意した既製の声だけ（§6） |
| 使いみちが無いまま入れない | F3 | 目的は PO の言葉（一人ひとりに合わせた秘書）。対象外に「声で話しかける」を置き、読み上げだけに絞る（kgi.md §3） |
| 押す前に鳴らすと止められる | T1 | 切り替えを押した瞬間に音の部品を起こす（§4-4） |
