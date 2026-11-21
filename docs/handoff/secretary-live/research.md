# 秘書チャット 音声機能（A: マイク入力 / B: LIVE）調べ結果

- 調べた日: 2026-11-21
- 調べた人: クラウドの Sonnet（調べ役）
- 検索の数: WebSearch 22 回（standard）。WebFetch は公式サイト（developers.openai.com / ai.google.dev）が許可ドメイン外で名前解決できず**全て失敗**。cloud.google.com は取得できたが中身が空だった。
- **重要な制約**: 公式ページを直接読めていない。下の数値は「検索結果が要約した公式ページの文言」か第三者の記事。公式 URL は検索結果に出たものを書くが、**本文を自分で読んで確認した行は無い**。確認度を各行に付けた（検索要約 / 第三者 / 未確認）。数値は必ず公式ページで再確認してから設計に使うこと。
- 為替: 1 USD ≒ 159.3 円（2026-11-18、XE の表示を検索結果が引用。同月は 158〜160 円の幅。第三者の見積り）。円換算は 1 USD = 159 円で丸めた概算。

## 0. 先に結論（要約）

- 費用の目安（検索要約ベースの概算）: OpenAI gpt-realtime は音声トークン入力 $32/100万・出力 $64/100万。音声は入力 1 トークン=100ms、出力 1 トークン=50ms と読めるので、入力 約 $0.019/分、出力 約 $0.077/分（計算は調べ役の算術）。会話履歴が毎ターン再課金されるため実費はこれより上がる（要確認）。
- Gemini Live は音声 25 トークン/秒、料金表の版が複数あり食い違う。第三者の下限見積りは入力 $0.005/分・出力 $0.018/分だが、毎ターン履歴を再課金するので下限扱い。
- 聞き取り→AI→読み上げの組合せは部品ごとに安いが、割り込み・ターン検出・つなぎ込みを自前で作る量が最大。
- (A) 話している間から文字が出る機能は、LIVE（声の会話）とは別物。文字起こし専用の接続（OpenAI の realtime transcription 系、Google の streaming STT）で足りる可能性が高い。ただし公式での確認は未了。
- iPhone のホーム画面アプリでのマイクは**歴史的に不具合報告が多い**（下記）。最新 iOS での現状は未確認。実機検証が必須。
- 外部事例は、数値付きで裏が取れたものが少ない。成功は全てベンダー自己申告、失敗は規制当局（SEC）資料や報道で数値あり。件数の達成状況は第 3 節に正直に書いた。

## 1. 作り方の候補の比較表

確認日は全行 2026-11-21（検索要約を読んだ日）。「公式を直接読んだ」行は 0。

| 項目 | OpenAI Realtime API | Google Gemini Live API | 聞き取り→AI→読み上げ（Google Cloud STT + 任意の LLM + TTS） |
|---|---|---|---|
| 1分あたりの費用 | gpt-realtime: 音声 入力 $32 / 出力 $64（各 100万トークン）、キャッシュ入力 $0.40/100万、テキスト 入力 $4 / 出力 $16。音声は入力 100ms=1トークン、出力 50ms=1トークン → 入力 約$0.019/分（約3円）、出力 約$0.077/分（約12円）（算術は調べ役）。会話が長いと履歴が毎ターン入力に積み上がる可能性。公式の分あたり表は見つからず。確認度: 検索要約。 | 音声 25 トークン/秒（Google 料金ページの文言と検索要約）。料金表の版が複数: ある版は音声入力 $2.10・音声出力 $8.50（100万トークン）、別の Vertex 版は音声入力 $3.00。第三者は 入力 約$0.005/分・出力 約$0.018/分（下限）と見積り。毎ターン履歴を再課金（フォーラムの返信）。無料枠あり（開発者 API）。確認度: 検索要約・第三者。**版の食い違いが解消できていない**。 | STT: 標準 $0.016/分（500,000分まで。ただし Gemini Enterprise 節の下に出ていて定価かは不明）、ストリーミング専用の値は未確認。TTS: Chirp 3 HD $30/100万文字（第二次の写し）、Neural2 $16、Standard/WaveNet $4。LLM は別途。確認度: 検索要約（一部第二次）。 |
| 返事までの待ち時間 | 第三者実測: gpt-realtime 2.1 の初音までの p50 = 1,022ms（Speko）。Artificial Analysis の Big Bench Audio 平均初音 1.21 秒（gpt-realtime-2.1 High）。OpenAI の公表値は未確認。確認度: 第三者。 | 第三者実測: Gemini 3.8 Live 1,242ms（p50）、拡張思考設定は 863ms（Speko）。条件で逆転する。Google 公表値は未確認。確認度: 第三者。 | 公表値・実測とも未確認（構成次第。3 つを直列にするので足し算になる）。 |
| 日本語 | Realtime 公式ガイドに日本語版の URL あり（ja-JP）。モデルの日本語品質は未確認。 | 日本語のドキュメントはある（エフェメラルトークンの日本語ページ）。モデルの日本語品質は未確認。 | Google STT/TTS は多言語対応だが、日本語の対応モデル一覧は未確認。 |
| 割り込み | ガイドが「割り込み（barge-in）・ターン交代・ツール呼び出し」を想定用途に挙げると要約（中国語版ガイド）。詳細な設定は未確認。 | Live API に VAD 割り込みがある旨は一般に知られるが、今回の検索では未確認。 | 自前実装（再生を止める・STT を止めない等）。標準機能なし（未確認だが構成上そうなる）。 |
| 双方の文字起こし | 入力音声の文字起こし設定がある（細部は未確認）。 | 入力・出力の文字起こし設定名は知られるが、今回の検索では未確認。 | STT の結果と LLM の文字が自然に手元にある（最も扱いやすい）。 |
| 関数呼び出し | リアルタイムのツール呼び出しに対応と要約。 | Live API で対応（Full-Duplex-Bench-v3 論文が Gemini Live の tool use を評価）。詳細は未確認。 | LLM 側の関数呼び出しをそのまま使える（既存の秘書の仕組みを流用しやすい）。 |
| ブラウザとのつなぎ方と鍵 | WebRTC（ブラウザが SDP を送る）または WebSocket。サーバーで短命の client secret を発行し、ブラウザはそれだけ使う。トークンは 1 分で失効と要約。サーバー側作成時に OpenAI-Safety-Identifier ヘッダを付けるよう公式が助言。確認度: 検索要約。 | WebSocket。バックエンドでエフェメラルトークンを発行してブラウザに渡す。既定は「新規セッション開始まで 1 分・メッセージ送信まで 30 分」、`uses` で 1 回に限定可、再接続はセッション再開が必要、トークンは Live API のみ。API の版（v1alpha/v1beta）の記述が食い違う。確認度: 検索要約。 | 鍵は FastAPI 側に置き、ブラウザは自社 WebSocket/HTTP だけに接続する（鍵は画面に出ない）。 |
| iPhone Safari・ホーム画面アプリ | 下の第 2 節を参照（方式共通の問題が大半）。WebRTC は iOS の音声まわりの既知問題に当たる。 | 下の第 2 節。WebSocket + Web Audio で自前再生するので、無音スイッチと AudioContext の問題に直接当たる。 | 同上。 |
| 音声の保存と学習利用 | API の業務データは既定で学習に使わない（2023-03-01 以降）。不正検知ログは最大 30 日（realtime / speech 生成は 30 日保持の表）。ZDR は条件付き申請。確認度: 検索要約（公式ページの要約）。 | 有料枠は学習に使わないと第三者が要約。無料枠は製品改善に使い人が見る場合あり。Google の ZDR ページは「不正使用検知のためだけに一定期間ログを保持」と記載。検索接地を使うと 30 日保存。確認度: 第三者中心。**公式規約は未確認**。 | Google Cloud のデータロギング設定次第（未確認）。 |

### 公式資料 URL（検索結果に出たもの。本文は直接読んでいない）

- OpenAI モデル: https://developers.openai.com/api/docs/models/gpt-realtime
- OpenAI 費用ガイド: https://developers.openai.com/api/docs/guides/realtime-costs
- OpenAI WebRTC: https://developers.openai.com/api/docs/guides/realtime-webrtc
- OpenAI client secret: https://developers.openai.com/api/reference/resources/realtime/subresources/client_secrets/methods/create
- OpenAI データ: https://developers.openai.com/api/docs/guides/your-data
- Gemini 料金: https://ai.google.dev/gemini-api/docs/pricing
- Gemini エフェメラルトークン: https://ai.google.dev/gemini-api/docs/ephemeral-tokens
- Gemini ZDR: https://ai.google.dev/gemini-api/docs/zdr
- Google STT 料金: https://cloud.google.com/speech-to-text/pricing
- Google TTS 料金: https://cloud.google.com/text-to-speech/pricing
- 第三者の待ち時間比較（Speko 数値の引用元）: https://www.gradually.ai/en/ai-audio-model-comparison/gpt-realtime-2.1-vs-gemini-3.8-live/
- Artificial Analysis: https://artificialanalysis.ai/speech-to-speech
- Gemini 料金の第三者解説: https://www.cekura.ai/blogs/gemini-live-api-pricing

## 2. iPhone（Safari・ホーム画面アプリ）の既知の問題

出典は WebKit のバグ票と Apple 開発者フォーラム。**どれも「報告」であり、最新 iOS で今も起きるかは未確認**。確認日 2026-11-21。

- ホーム画面アプリでの getUserMedia: 過去に「ホーム画面モードで動かない」報告（WebKit 185448、https://bugs.webkit.org/show_bug.cgi?id=185448）。許可が保持されない・URL パスが変わると再度許可を求められる、との報告。
- pushState の画面遷移でストリームがミュートされる報告。
- iOS 17.4.1 / 17.5.1 でホーム画面アプリのカメラストリーム不具合（WebKit 273938 ほか。マイクではなくカメラ）。
- ホーム画面アプリでは webkitSpeechRecognition が動かない報告（Apple フォーラム 748048）。**マイク印(A)を Web Speech API で作る案は、ホーム画面アプリでは使えない恐れ**。
- 音声の再生: AudioContext・音声要素はユーザーの操作の中で開始・再開が必要（WebKit 177292）。画面ロック/バックグラウンドで WebRTC 音声が止まる（Apple フォーラム 774239）。
- 無音スイッチ（消音）: Web Audio 出力が消音スイッチで止まる報告（WebKit 237878）。LIVE の読み上げが無音になる原因候補。
- iOS 26.5 で setSinkId が成功と返すのに出力先が変わらない報告（WebKit 320087、2026-07 提出）。
- WebRTC の事前参加で「user gesture is required」の報告（WebKit 319706）。
- 既知の対処: AudioContext をタップの中で作る/再開、visibilitychange で再開、ボタンを押してから接続。ただし公式の確定した修正は確認できず。

## 3. 外部の導入事例

### 3.1 件数の正直な報告

- 成功（数値あり・件数に数える）: **4 件**（ただし全てベンダー自己申告で、日付・費用は多くが未確認）
- 失敗（数値あり・件数に数える）: **2 件確定**（McDonald's、Presto）。**依頼の「3 件以上」に 1 件足りない**。Taco Bell は規模の数値のみで成果数値が無いため「参考（件数に数えない）」。Kinney Drugs は数値なしで件数に数えない。
- 日本の導入事例: 検索では完了率・削減件数を載せた公開事例が確認できなかった（JCB「アイブリー」、NTT COTOHA など。数値なし）。

### 3.2 成功（数値あり）

共通の注意: 4 件とも PolyAI 社または報道が出した**ベンダー自己申告**。定義（封じ込め=人に回さず終えた割合）と、問い合わせの種類の違いが大きい。確認日 2026-11-21。公開日は検索結果に出ず**未確認**。

**S1. Landry's / Golden Nugget（PolyAI）— 封じ込め 87%（初日）**
- いつ: 未確認（初日の数値）。どこが: Landry's の Golden Nugget ホテル・カジノ。誰に: 予約などの電話の客（「収益に関わらない通話」の 87% と G2 レビューは言う）。何を: 電話の音声アシスタント。なぜ: 電話対応の負荷。どうやって: PolyAI の音声アシスタント。いくらで: 未確認。
- 数値: 封じ込め 87%（初日）。
- 出典: https://www.casestudies.com/company/polyai/case-study/how-landrys-golden-nugget-hotels-casinos-deployed-a-voice-assistant-with-87-containment-on-day-1 （ベンダー自己申告）

**S2. Hello Sugar（PolyAI）— 全通話に応答 100%、封じ込め 56%**
- いつ: 未確認。どこが: 脱毛サロンチェーン（アリゾナ）。誰に: 来店予約などの客。何を: 電話の AI エージェント。なぜ: 電話に出られない取りこぼし。どうやって: 複雑な通話は人へ引き継ぐ構成。いくらで: 未確認。
- 数値: 応答 100%（アリゾナ）、封じ込め 56%。
- 出典: https://www.destinationcrm.com/Articles/CRM-Insights/CRM-Case-Studies/PolyAI-Agents-Sweeten-Interactions-for-Hello-Sugar-171673.aspx

**S3. 米国の小売銀行（PolyAI の匿名事例）— 通話の 30% を解決、CSAT 96% を維持**
- いつ: 未確認。どこが: 小売銀行（社名不明）。誰に: 銀行の顧客。何を: 電話の音声アシスタント。なぜ/どうやって/いくらで: 未確認。
- 数値: 解決 30%、CSAT 96% 維持。社名不明のため追跡不能。
- 出典: PolyAI 事例の検索要約（個別 URL 未確認。一覧は https://www.casestudies.com/company/polyai ）

**S4. Wendy's FreshAI（Google 生成 AI）— 提供時間 22 秒短縮、正確さ 99%（店員が補助した場合）**
- いつ: 2023-12 の Columbus テスト開始、2024-10 に拡大報道。どこが: Wendy's。誰に: ドライブスルーの客。何を: 音声注文。なぜ: 速度と人手。どうやって: Google の生成 AI。いくらで: 未確認。
- 数値: 平均より 22 秒速い（初回テスト）。正確さ 99% は「店員が最後に補助した場合」で AI 単独ではない。160 店超に展開（Restaurant Dive）、2025 年末に 500〜600 店の目標。
- 出典: https://fortune.com/2024/10/15/wendy-google-ai-drive-thru-expansion ほか https://www.wendys.com/blog/wendysr-square-deal-blog/transforming-ordering-experience-wendys-freshai-update

**成功の要因を数値に結びつけた読み方（推測を含む）**
- 高い封じ込め（87%・56%）は、通話の種類が限られた予約・案内系で、複雑な通話を人に渡す設計の案件。封じ込め 87% は「収益に関わらない通話」の割合で、全通話ではない。
- 同じ PolyAI でも Carnival UK は最大 14%、PG&E は開始時 5% → 1 年後 21%。**同じ製品でも業務の種類で 5%〜87% と開く**。
- Wendy's の 99% は店員の補助込み。AI 単独の精度ではない。Intouch Insight の独立調査では AI 注文の正確さは 2025 年に 83%（全体 87%）、店員が助けると 90%。

### 3.3 失敗（数値あり）

**F1. McDonald's × IBM（AI ドライブスルー）— 正確さ 80% 台前半、必要水準 95%**
- いつ: 2021 年から試験、2024-06 に終了を通知、2024-07-26 までに停止。どこが: 米国 100 店超。誰に: ドライブスルーの客。何を: 自動注文受付。なぜ: 速度・人手。どうやって: IBM の音声技術。いくらで: 未確認。
- 数値: 加盟店の話として正確さは 80% 台前半（2022-06 の BTIG アナリスト調査）。拡大に必要な水準は 95%。100 店超・約 3 年。McDonald's は正確さについてコメントしていない（公式値なし）。
- 要因: 数値の差（80 台前半 vs 95）が拡大の見送りに直結。
- 出典: https://www.nbcnews.com/business/business-news/mcdonalds-end-ai-drive-test-ibm-rcna157603 / https://fortune.com/2024/06/17/mcdonalds-ai-order-taking-drive-thru-ends/ （公開 2024-06、確認 2026-11-21）

**F2. Presto Automation（Presto Voice）— 注文の 70% 超で人の介入が必要**
- いつ: 2023-11 の SEC 提出書類で公表。SEC の命令は 2025（33-11352）。どこが: 米国ドライブスルーの導入先（Carl's Jr. 等の報道。詳細未確認）。誰に: 客。何を: 音声注文。なぜ: 人手削減。どうやって: AI と、フィリピン・インド等の海外の人手の併用。いくらで: 未確認。
- 数値: 「人の介入なしで完了」は 30% 以下（書類の文言）。以前の宣伝は「最大 95% が店員の介入なし」。SEC は、海外の人手が大半の注文を処理していた点と、その開示が誤解を招くと認定。
- 要因: 自動完了率の定義（店員の介入なし ≠ 人の介入なし）が成果の見え方を左右した。
- 出典: https://www.sec.gov/enforcement-litigation/administrative-proceedings/33-11352-s / https://www.bloomberg.com/news/articles/2023-12-07/ai-fast-food-drive-thrus-need-human-workers-70-of-time （確認 2026-11-21）

### 3.4 参考（件数に数えない）

- **Taco Bell（Yum Brands）**: 2025-08 に 500 店超で運用、200 万件超の注文後に「展開を見直す」と報道（WSJ 経由の二次報道）。注文 1 件で水 18,000 杯のいたずらが話題。のち 2026-07 時点で 890 店超・38 州（Omilia）と再拡大の報道。**成果数値（正確さ・完了率）は未確認**。数値なしのため件数に数えない。https://www.pymnts.com/artificial-intelligence-2/2025/taco-bell-reconsiders-voice-ai-after-seeing-mixed-results/
- **Kinney Drugs（米国の薬局チェーン）**: 2026-08 に AI 電話アシスタントを縮小（誤った用量・処方通知の欠落の苦情）。**数値なし**。https://www.ky3.com/2026/08/08/drugstore-chain-pulls-back-ai-assistant-after-receiving-hundreds-customer-complaints/
- **業界調査**: Sinch の調査で、企業の 74% が顧客向け AI エージェントを導入後に巻き戻した（全チャネル、ベンダー依頼の調査）。https://www.theregister.com/ai-ml/2026/05/13/ai-customer-service-bots-get-rolled-back-at-74-of-firms/5239800
- **待ち時間の目安**: Haptik（ベンダー）は 1,200ms 超で封じ込めが大きく下がると主張。根拠データは未確認。
- 失敗の追加候補（要調査）: 社名・数値の取れる別の失敗事例を、次回調べる必要がある。

## 4. 我々の秘書に当てはめる注意

1. **規模の違い**: 事例は電話・ドライブスルーを数百〜数百万件処理する用途。我々の秘書は PO 数人の社内ツールで、聞くのは日本語の指示（予定、請求書の下書き）。数値（封じ込め 87% 等）は直接の目標にならない。
2. **成果の定義**: 失敗 2 件とも「完了率の定義」と「人の介入」の扱いが問題だった。我々は「秘書が関数呼び出しを最後まで正しく実行できた割合」を最初に定義し、AI 単独と人の補助を分けて測るべき。
3. **日本語**: 事例の数値は英語の環境。日本語の認識・読み上げの品質と待ち時間は**未確認**。実機で測る。
4. **実機の壁**: PC の Chrome よりも、iPhone のホーム画面アプリでマイク・音声再生が止まるリスクが大きい。LIVE（B）を先に作るより、(A) 文字起こし（ブラウザ標準の音声認識はホーム画面アプリで不可の恐れ。サーバー側の STT を検討）の方が実機リスクは小さい、というのは推測。
5. **操作を伴う関数呼び出し**: LIVE 中に請求書の下書きを作る操作は、聞き間違いが直接の事故になる。McDonald's の差（80 台前半 vs 95）が示すとおり、確認の一言（「この内容で下書きしますか」）を挟む設計が前提。下書き止まりで送信しない現在の方針が活きる。
6. **費用**: 1 分あたり数円〜十数円の概算（第 1 節）。ただし履歴の再課金で伸びる。LIVE の 1 回の最大時間・無通話の自動終了を決める。
7. **学習利用・保存**: OpenAI は業務データを既定で学習に使わない・30 日ログ。Gemini は有料枠かどうかで変わる。顧客データ（請求書）が声に混ざるため、Gemini なら有料枠限定。いずれも公式規約を PO が確認すること。
8. **この調べの限界**: 公式ページを直接読めていない。待ち時間は第三者実測のみ。成功事例は全て自己申告。**設計前に公式ページを許可ドメインに入れて再確認する**（developers.openai.com・ai.google.dev・cloud.google.com の取得を許可する必要がある）。
