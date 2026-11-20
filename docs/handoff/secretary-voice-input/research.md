# 秘書に声で話しかける — 調べたこと（research）

調べた日: 2026-11-19。仕様は Context7（MDN・Google Cloud の公式文書）と公式ページで確かめた。

## 1. 聞き取りのやり方 2 つ

### A. ブラウザが元から持つ聞き取り（Web Speech API の SpeechRecognition）

- 出典: MDN `SpeechRecognition`（Context7 `/mdn/content`。https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition）
- 「一部のブラウザでは、音声はウェブのサービスに送られて聞き取られる」（MDN の注記の要約）。Chrome では Google の一般向けの聞き取りに送られる。会社の契約（Google Cloud の約束）の外になる
- `continuous=false` なら 1 回の発話で自動で止まる（黙ると区切る処理をブラウザがやる）
- `processLocally=true` で端末の中だけで聞き取れるが、言語の部品の取り込みが要る（同ページ）
- 費用 0 円。使用量はアプリから数えられない
- **まだ確かめていない**: iPhone でホーム画面に置いたアプリ（standalone）の中で動くか。実機でしか確かめられない

### B. Google Cloud Speech-to-Text v2（読み上げと同じ Google Cloud の契約・同じ鍵の会社）

- 出典: REST `projects.locations.recognizers.recognize`（Context7 `/websites/cloud_google_speech-to-text_reference_rest_v2`。https://docs.cloud.google.com/speech-to-text/docs/reference/rest/v2/projects.locations.recognizers/recognize）
  - 認識器の名前を `_` にすると、事前の作成なしで使える
  - 権限 `speech.recognizers.recognize` が要る
  - `autoDecodingConfig` で自動で読める形式に `WEBM_OPUS`（Chrome の録音の形）と `MP4_AAC`（Safari の録音の形）が入っている
- 上限: 同期の 1 回は 10 MB または 1 分まで（https://docs.cloud.google.com/speech-to-text/v2/docs/quotas）
- 値段: v2 の標準の聞き取りは 1 分 0.016 ドル（月 50 万分まで）（https://cloud.google.com/speech-to-text/pricing）
  - 円: 1 分 約 2.6 円（1 ドル 159.5 円・日本銀行 2026-11-16 17 時の値 https://www.boj.or.jp/en/statistics/market/forex/fxdaily/fxlist/fx261116.pdf ）
  - 見込み: 1 日 50 回 × 5 秒 = 約 4 分 → 月 約 125 分 → 約 2 ドル（約 320 円）。回数は見込みで、まだ測っていない
- **まだ確かめていない**: 今の鍵でこの機能が使えるか（API の有効化と権限）・日本語のモデルとその場所・本番からの速さ

## 2. 黙ったら区切る（B を選ぶときに要る）

- 出典: MDN `AnalyserNode.getByteTimeDomainData`・`MediaRecorder`（Context7 `/mdn/content`）
- 録音は `MediaRecorder`、音の大きさは `AnalyserNode` で 50 ミリ秒ごとに見る。話し始めを見つけたあと 1.2 秒静かなら区切る（数値は設計の初期値。本番で K3 を測って直す）

## 3. 外部の事例

- ChatGPT の音声モード（OpenAI・2023-09-25 公開・https://openai.com/index/chatgpt-can-now-see-hear-and-speak/ ）: 入力欄の横のアイコンで画面いっぱいの音声モードに入り、黙ると区切って声で返す。PO が「chatgptみたいに」と名指しした形で、画面の形の見本として使う。数値の根拠（成功率など）には使わない
- 前の段の調べ（`docs/handoff/secretary-voice/research.md` F3）: 業務の声の秘書は「聞き違いがあった」65%（Forrester）。→ 聞き取った文は必ず画面に出し、PC では自分で送る・音声モードでも予定は「入れますか？」で確かめる（K2・K6）設計の理由

## 4. ChatGPT・Claude のアプリとつなぐ案（PO の質問 2026-11-19）

- ChatGPT: 外のサービスをつなぐ仕組み（開発者モード・MCP）あり。書き込みまでは会社向けの契約という案内 https://help.openai.com/ro-ro/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta
- ChatGPT の声: 古い公式 FAQ は「声では使えない」 https://help.openai.com/en/articles/8400625-voice-mode-faq ／ 外部記事は 2026-09-23 から声でも使えると報じる（声での許可は不可） https://windowsforum.com/news/chatgpt-voice-adds-connected-apps-under-existing-plugin-permissions.445694/ 。新しい公式ページは手元から読めず **未確認**
- Claude: つなぐ仕組みあり https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp 。声のときだけ使えない不具合の報告（Anthropic 未確認） https://claudeissues.com/issue/77312-bug-claude-ai-voice-mode-custom-mcp-connector-tools-fail-with-tool-is-not-regist
- ChatGPT は自社の聞き取り（Whisper）を自社サーバーで動かす https://openai.com/index/chatgpt-can-now-see-hear-and-speak 。Claude は聞き取り後に録音を消すと公式に記載 https://support.claude.com/en/articles/11101966-use-voice-mode
- 無料の別案: スマホ・Mac のキーボードの音声入力（今のままで使える。続けて話す音声モードにはならない）

### 4-1 公式で確かめた（Context7 `/websites/help_openai_en`・2026-11-19）

- 声でつないだサービスを使える: 2026-09-23 から web・iOS・Android の Live で使える。許可が要る操作は画面で押して許可（声での許可は不可）。https://help.openai.com/en/articles/20001274-chatgpt-voice ・ https://help.openai.com/en/articles/6825453-chatgpt-release-notes → 上の「未確認」は解消
- 自社のサービスへの書き込み: 「Full MCP（書き込みを含む）は Business と Enterprise/Edu だけ」。Pro は読み取りだけ。Plus の記載なし（**未確認**）。https://help.openai.com/en/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta
- 入口の守り: OAuth 2.1（保護資源の情報を /.well-known/oauth-protected-resource で返す）。https://developers.openai.com/plugins/build/auth
- Business の値段: 標準の席 1 人 月 25 ドル（年払いなら 20 ドル）。最低 2 席。https://help.openai.com/en/articles/12111915
  - 円: 最低 月 50 ドル ≈ 7,976 円（年払い 40 ドル ≈ 6,381 円）。1 ドル 159.52 円（日本銀行 2026-11-16）

### 4-2 個人の Plus で書き込めるか（PO の質問・2026-11-19）

- 公式の記載: 「Full MCP（書き込み）は今は Business と Enterprise/Edu だけ」「Pro は開発者モードで読み取りだけ」 https://help.openai.com/en/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta 。Plus についての記載は見つからない → **未確認**（Pro より下の契約なので、書き込みは載っていない）
- 別の道: ChatGPT Sites に置いた MCP をプラグインにする形は「どの契約でも作れる」 https://help.openai.com/en/articles/20001256-plugins-in-chatgpt ・ https://help.openai.com/en/articles/20001547-hosting-a-plugin-with-chatgpt-sites 。ただし入口が OpenAI 側のサイトに置かれ、そこからセールスアンカーに書き込めるか・鍵をどこに置くかは **未確認**
- 確かめ方: PO の Plus の画面で chatgpt.com/plugins に「Add custom MCP server」が出るか（開発者向け案内の手順 https://developers.openai.com/plugins/build/plugins ）

## 5. Grok と ChatGPT の比べ（PO の質問 2026-11-19）

- Grok の自社サービスつなぎ: grok.com/connectors で自分の MCP を足せる（公式 https://docs.x.ai/grok/connectors ）。有料の契約が要るという記事あり（二次情報）。書き込みまでできるかは **未確認**
- Grok の声でつないだサービスを使う: ブログ記事のみ（2026-08-10 https://www.basenor.com/blogs/news/grok-voice-connector-5-details-that-matter ）。xAI 公式では **未確認**
- Grok の学習: 一般向けは既定で利用者のデータを学習に使う（止める設定あり）。Business は「学習に使わない」と xAI が表明（https://x.ai/news/grok-business ）。アイルランドのデータ保護当局の調査中という記事あり（https://www.waimakers.com/en/resources/ai-data-security/grok-xai ）。値段は 1 人 月 30 ドルという報道（二次情報）
- ChatGPT: 声でつないだサービスを使えることは公式で確認済み（§4-1）。書き込みは Business で確認済み（§4-1）。セールスアンカーの秘書の担当表に ChatGPT（codex）の選択肢が既にある（`backend/app/routers/assistant.py:104-112`）。Grok の選択肢は無い
- 日本語の会話のうまさ・営業の相談のうまさの比べ: 測った数字は見つからない → **未確認**

## 6. iPhone のホーム画面のアプリで聞き取りが動くか（2026-11-19）

- 動かないという報告: WebKit の不具合票（2021〜）「ホーム画面に置いたアプリでは使えない」 https://bugs.webkit.org/show_bug.cgi?id=225298 ／ firt.dev の iOS 14.5 の記事 https://firt.dev/ios-14.5/ ／ Apple の開発者の場（PWA にすると動かない） https://developer.apple.com/forums/thread/748048
- 動くという記載: https://whatpwacando.today/speech-recognition （Apple の文書では確かめられない）
- 上の多くは 2021〜2023 年。今の iOS でどうかは **未確認** → 試しの便（design §14）で実機で確かめる
- 失敗の種類の一覧: MDN `SpeechRecognitionErrorEvent.error`（Context7 `/mdn/content`）: aborted・audio-capture・language-not-supported・network・no-speech・not-allowed・phrases-not-supported・service-not-allowed
