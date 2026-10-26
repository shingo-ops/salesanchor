# 引き継ぎ: WhatsApp 連携（HIGH LIFE JPN / tenant_004）

状態（2026-10-26 時点）: 調査済み／設計案は作成前／PO 承認待ち（方式の選択）／実装未着手

この文書はセッション間の引き継ぎ用です。PO の決定として書いた行には PO の言葉を添えています。それ以外の行は Claude Opus の調査結果と提案で、まだ決定ではありません。

## 1. PO の願い（原文）
- 「メッセージの送受信がしたい」
- 「待っている間に審査無しでメッセージを取得するロジックを作成してほしい」
- 「そうじゅしんどちらも複数顧客で実現できるか？」
- 前回の審査について：「審査が取るまで2週間かかってその結果理由も公開されずに却下になった」

## 2. 決まったこと
- LP（salesanchor.jp）を申請専用にし、検索に出さない：PR #4738、本番反映済み（2026-10-25）、ADR-1044
- アプリ（app.salesanchor.jp）も検索に出さない：PR #4755、本番反映済み（2026-10-25 23:55 JST に `/` と `/login` が 200、noindex が1件）、ADR-1044 の追記
- 非公式の方法（WhatsApp Web の自動操作、whatsapp-web.js、Baileys）は採用しない（Opus の判断。根拠は §4-3）

## 3. 未決（PO に聞いている1件）
Opus が出した選択肢：
1. 書き出し（Export chat）の取り込みを作る。まず PO のスマホで書き出したお客さん1人分のファイルを受け取る【おすすめ】
2. 書き出しの取り込みと、別番号での Cloud API 直接接続の試験を並行する
3. 書き出しはやめ、別番号での直接接続の試験だけ行う

あわせて確認中：WhatsApp の相手は「お客さん」か「仕入元」か。仕入元なら入れ先が系統B（§5）に変わる。

## 4. 確かめた事実（出典は evidence/ 配下）
### 4-1 審査なしで使える公式の道（evidence/wa-noreview-paths.md）
- 自社用（Direct Developer）なら App Review は不要。原文："if you are using the API for yourself as a Direct Developer, you do not need Advanced access or app review"
- ビジネス認証は、アプリに役割を持つ自社ユーザーだけが使う場合は不要（一般の規則）。WhatsApp 専用ページには明記なし
- 前回却下された Tech Provider の Access verification は「他社が使うアプリ」の場合だけに必要
- 未確認：Development モードのアプリに webhook が実際に届くか。表示名が未承認でも送受信できるか。未認証で定型文（テンプレート）を登録できるか
- 制約："Numbers already in use with WhatsApp cannot be registered unless they are deleted first."（いまの番号を API に移すと、スマホアプリで使えなくなる）。Coexistence は Solution Partner または Tech Provider が条件
- 上限：新規ポートフォリオは番号2つ、窓外の送信相手は250人/日。受信には上限なし
- 書き出し：1回につき1会話。iPhone/Web は ZIP、Android は共有シート経由。件数上限は現行の公式ページに記載なし（未確認）
### 4-2 料金・他社（evidence/wa-verify-meta.md、wa-verify-vendors.md）
- 受信は無料。24時間窓内のサービス返信は番号ごとに月1,000通まで無料
- 宣伝メッセージは Rest of Asia Pacific（日本・台湾）宛てが 0.0842 USD/通
- 為替 156.51 円/USD（三菱UFJ 2026-10-23 TTS/TTB の中値）
- Business Suite の受信箱は日本が対象外。Coexistence は 2025-10-23 から日本が対象
### 4-3 外部事例（evidence/wa-case-studies.md）
- 数値ありの成功例は提供会社の発表のみ（利害関係あり）
  - Breakthrough Maths：応答時間 54分→26分、売上 +35%
  - Contalink：初回応答 1時間→15分、成約 +50%
- 非公式ライブラリ：GitHub issue で "banned" が whatsapp-web.js に58件、Baileys に35件（Baileys は2024年1件→2025年14件）
- 審査の長期化：却下4回・約6週間・理由なし、「審査中」のまま約3か月の例がある
- 未達：B（Coexistence）と D（書き出し）は、数値つきの事例が目標件数に届いていない
### 4-4 コードの現状（evidence/wa-recon-codebase.md、wa-recon-send.md、基準 origin/main d18f6ce9f）
- お客さんとの会話は系統A：tenant スキーマの conversation_logs（channel_type VARCHAR(30)）、書き込みは backend/app/services/conv_log_writer.py（lead_id 必須）
- LINE の書き出し取り込みは系統B：public.source_messages。仕入元の投稿専用で、1ファイル＝1トーク、送り手の名前を suppliers.line_name と完全一致させる。お客さんとの会話には流用できない
- WhatsApp の受け皿は一部ある：channel_masters の whatsapp（manual）、連絡先・leads の WhatsApp 列、ADR-098 の電話番号の正規化
- 送信は Messenger/Instagram の1人ずつ返信だけ（backend/app/routers/leads.py:1766、backend/app/services/meta_graph.py:775）。一斉送信、WhatsApp 送信、LINE 送信のコードはない
- ADR-095:101 で「多チャネル取り込みは未設計」

## 5. 次の一手（PO の回答を受けてから）
1. STANDARD-WORKFLOW の①：KGI を PO と合意する（例：書き出し1ファイルを取り込むと、該当のお客さんの会話画面に全メッセージが重複なく並ぶ）
2. ②：この文書と evidence を recon.md に正式化する
3. ③：design.md と ADR 案（会話履歴に WhatsApp の書き出しを取り込む）を作る。架空のファイルを作らないため、実物のファイル形式を確認してから作る
4. 承認・実装カードがそろったら Sonnet に実装を任せる

## 6. 次のセッションの始め方
`docs/handoff/whatsapp-intake/README.md` を読み、§3 の PO の回答から再開する。

## 外部・過去事例の参照と我々への応用
他社事例の調査は `evidence/wa-case-studies.md` にある。応用の判断はまだしていない（PO の回答待ち。上の §5 の③で design.md に進む）。

## 維持の仕組み
この文書は引き継ぎ用で、設計ではない。守り手: PO の回答後に設計を起こす担当（§5 の③で決める）。
