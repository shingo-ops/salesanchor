<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — AI アシスタント（秘書を まとめ役＋係 へ）第2.10版・草案

この文書は、今の秘書を「まとめ役 1 人と、係ごとの専属 AI」に作り替える作りの案です。§10 の審査を受けて直した版です。

親（仕様書）: [../../specs/secretary-chat/README.md](../../specs/secretary-chat/README.md)
要件のすり合わせ: [requirements.md](requirements.md)
recon: [recon.md](recon.md)
外部事例（5W2H）: [research.md](research.md)

**対象ADR**: ADR-1056（今の秘書・改めが要る）・ADR-1058（AI の担当表・正本のまま使い、選択肢を migration で足す）・ADR-1077（決まり帳・正本のまま使う）・ADR-1078（カルテ・そのまま）・ADR-1004（使用の台帳）・ADR-1080/1082/1087（声・影響を受ける）・ADR-009/091/159（Discord・ADR-091 は改めが要る）・ADR-135/136（危険 PR の GO）・ADR-1003（secrets）  
**日付**: 2026-11-25  
**担当**: Planner（Claude Opus。審査は Fable〈クラウド〉と審査役〈Opus〉。同じ会社の AI どうしの審査で、独立した第三者の審査ではない）  
**状態**: 設計案第2.10版作成済み（便0-B 8回目が対照①で止まった件の直し・K9 の検証方法・第2.9版の審査 REVISE の直し）／K1〜K9 と便0 の試し方は PO 承認済み（Q8・基準の文は変えていない）／第2.4版は審査役 APPROVE・第2.6版・第2.7版は REVISE・第2.8版は審査役 APPROVE・第2.9版は REVISE・第2.10版は審査待ち（§10）／アプリの実装未着手

---

## 0. PO 決定の前提（原文は requirements.md §3）

- Q1「1」: しんごさんだけで始め、あとで社員へ。
- Q2「1」: アプリの窓と、SA がつないだ Discord の非公開の部屋。Hermes 自身の Discord 接続は使わない。
- Q3「1」: 最初は全部承認。実績が基準を超えた仕事だけ PO が任せる。
- Q4c「1」: 基準の一覧。数字と止める/動かすは画面で PO、新しい種類は開発が足す。
- Q5-pre「1で検討」: 部署は名札。まとめ役と係の 2 段。
- Q6「実装した後に効果確認を実施する」: 速さと正しさは作った後に今の秘書と並べて測る。
- Q7「1」: Hermes の自動の振り返りは止め、決まり帳で育てる。
- Q8「1」: 便0 の試し方。場所はクラウドの作業場所（動くかを最初に確かめ、動かなければ止めて相談）。ログインは今の秘書と同じ ChatGPT 月額契約で、試し用に別に 1 回。合格の線は K1〜K9。同じ日に本番を 1 回読んで今の秘書も測る。会話は毎回消して「全文を残さない」を満たしたとする。形がくずれたらアプリで 1 回だけやり直す。

## 1. 第1版からの変更（審査の指摘と直し方）

| 指摘 | 第1版 | 第2版 |
|---|---|---|
| 振り分けを Hermes の中の「仕事を振る道具」で行う（M3〜M5・3-1） | まとめ役が `profile_routes` で係へ振る | **アプリが振る**。①アプリがまとめ役の部屋に「どの係か」だけを聞く（答えは JSON 1 行）②アプリが係の部屋を名指しで呼ぶ（Hermes の `/p/<部屋名>/v1/chat/completions`）。Hermes の中の振り分けの道具は使わない |
| 道具を切ると振り分けが動かない（M3） | 「全部切る」と「振る」が両立しない | 振り分けが道具でなくなったので、全部屋で道具を全部切れる（部屋の設定 `platform_toolsets.api_server` を空） |
| 頭の正本が DB と Hermes の 2 か所（M1・3-1） | 部屋の設定で頭を替える | 頭の正本は DB の担当表（ADR-1058）のまま。係ごとに仕事名を足し、アプリが呼ぶたびに頭を渡す（渡し方は §5「頭の渡し方」の 1 つだけ）。どの部屋・どの頭で動いたかはアプリが台帳に書く（AI の申告に頼らない） |
| 覚え書きが決まり帳と二重（M2・M4・3-7） | Hermes の覚え書きを許可制で使う | Hermes の覚え書きは切る（`memory_enabled: false`・`user_profile_enabled: false`）。覚えることは今の決まり帳（`public.secretary_rules`）だけ。毎回アプリが渡す |
| 「1 行足す形」は不正確（R3） | `agent_url()` に 1 行 | migration（provider と sdk の値・仕事名の追加）＋口の形の変換部品が要る。migration は危険 PR で GO まで main に入れない |
| 置き場の変更を書いていない（M6・3-4） | 本番 prod1 に置かない | 本番の置き場は **PO が決める**（PO の言葉は「サーバーの中に置くが安全面も考慮する」）。便0 は本番と別の試しの場所で、本番の判断の材料（メモリの実測）を取るだけ |
| 会社のデータを外の AI に渡す（M7・U8） | 渡す前提 | 便0 は作り物のデータだけ。本物を渡すかは便1 の前に PO が決める |
| 会社ごとの分け隔てが無い（R4） | 記載なし | 覚え書きと会話を Hermes に残さないので、分け隔ては今の秘書と同じくアプリの側（会社の文脈）で保つ。便0 で「残らない」ことを実測 |
| 受け入れ基準が緩い・○× にならない（M8・§4） | 95/100・30 秒 | 今の秘書の実測（69/69・中央値 5.12 秒）を線にする（§4） |

## 2. 作りの全体（頭と手を分ける）

```
しんごさん ──(アプリの窓 / Discord の非公開の部屋)──▶ SA アプリ（手）
   ① アプリ → まとめ役の部屋「この頼みはどの係？」 → 答え {"role":"calendar"} だけ
   ② アプリ → 係の部屋（名指し）に、文＋今の日時＋決まり帳＋カルテを渡す
   ③ 係 → 下書き（今の秘書と同じ形の JSON）
   ④ アプリが形を確かめて見せる → しんごさんの「はい」→ アプリが作る・送る
   ⑤ アプリが台帳に「どの部屋・どの頭・何秒・使った量」を書く。1 行＝AI の応答 1 回（ADR-1004 の単位のまま）なので、頼み 1 回で 2 行（まとめ役・係）。2 行は同じ頼みの番号で結ぶ
```

- 手（DB への書き込み・お客様への送信）は SA アプリだけが持つ。Hermes の全部屋で道具は 0 個・覚え書きは切る。今の ADR-1056「AI は下書きだけ」を保つ。
- 部署は名札: 係の部屋の名前の頭に付ける（例 `keiri-invoice`）。画面の並べ方と成績の集計にだけ使う。部署の長の AI は置かない（research.md の事例 1〜3）。
- 共通の決まり（話し方・しんごさんとの接し方）の文書と、係ごとの決まりの文書（人格の文書）は、リポジトリの中に置いて PR で変える。Hermes の部屋へはそこから写す。写した版の番号を台帳に書く。
- 頭の付け替え（A/B）: 担当表の係の仕事の行を替える。比べるときは同じ試しの頼み（下の §4）を両方に流して数字で比べる。
- 戻し方: 担当表の `secretary_intent` を今の秘書（codex）に戻すだけで、Hermes は呼ばれなくなる。

## 3. 外部・過去事例の参照と我々への応用

出典・取得日・引いた数字の場所は [research.md](research.md)。既存の外部事例: [../secretary-chat/external-cases.md](../secretary-chat/external-cases.md)。

- 事例 1（Google Research ほか・2025-12）: まとめ役なしは間違いが 17.2 倍、ありは 4.4 倍 → まとめ役は置く。ただし「どの係か」を答えるだけにし、形の確かめはアプリが行う。
- 事例 2（LangChain・2025-06）: まとめ役が係の答えを言い直すと誤り。そのまま渡す改善で約 50% 向上 → 第2版では係の答えをまとめ役が通らない（アプリが係を直接呼ぶ）。
- 事例 3（UC Berkeley MAST・2025）: 複数 AI の失敗率 41〜86.7% → 段は 2 段。最後に決めるのはしんごさんの「はい」だけ。
- 事例 4（Klarna）: 品質を測らず失敗 → 係ごとに「直さずに はい」の割合を数える。
- 事例 5（Anthropic・2025-06）: 使用量は約 15 倍 → 1 回ごとの使用量を台帳に書き、上限で止める。
- 事例 6（Cognition・2025-06）: 書き込みは 1 本の流れ → 書き込みはアプリの 1 か所。
- 適用の限界: どの事例も Hermes そのものの実測ではない。本件の成功の証明には使わず、作りの選び方の根拠にだけ使う。証明は便0 の実測で行う。

## 4. 受け入れ基準（KGI・PO 承認済み 2026-11-25「1」＝requirements.md Q8）

試しの頼みは今の秘書の束 `backend/app/assistant_regression/cases.json`（23 件。今の秘書の 69 件はこれを 3 回流したもの）を 3 回流す。比べる元は、決まり帳を付けた今の秘書の実測（`docs/handoff/secretary-rulebook/baseline.md` 中央値 7.88 秒・最長 12.42 秒）。日によって値が変わるので、便0 と同じ日に今の秘書も流して並べる（今の秘書は本番にしか無いので、その回だけ本番を読む。Q8 で PO 承認済み。読む日にその日の同意票を 1 回取る）。束の正解「わからない」7 件（unknown 4・rule 3）は、まとめ役の答え「none」を正解とする。

| 基準 | 合格の線 | 検証方法 |
|------|---------|---------|
| K1 正しい係に振られる | 69 件のうち 69 件（今と同じ） | 便0: 束を流し、まとめ役の答えの係と、束の正解の種類（予定→予定係、請求書→請求書係）を突き合わせて数える |
| K2 下書きが今の形で返る | 69 件のうち 69 件が `secretary-agent/schema.json` の検査を通る（Q8 のやり直し 1 回の後で数える。やり直した件数も別に記録する） | 便0: 係の部屋への頼みに、`secretary-agent/schema.json` から送るたびに作る形の指示（role system・§5「形の渡し方」）を付ける。係の返事を同じ形の検査に通して数える。落ちたら 1 回だけやり直し（新しい会話番号で）、その結果で数える |
| K3 中身の当たり | 束の頼みに書いた日時・会社名・金額が下書きの欄に入った割合が、同じ日の今の秘書以上 | 便0: 束には正解の欄が無い（項目は expected・group・id・text だけ）。便0 の担当が 23 件分の正解表を作り、PR で Opus が 1 件ずつ確かめてから測る |
| K4 道具が無い | 3 部屋それぞれに道具を使わせる頼み 5 件（ファイルを読む・コマンドを動かす・ネットを見る・覚える・別の部屋へ振る）＝15 件がどれも実行されない 15/15 | 便0: 会話を消す前に、その会話の記録に道具の実行が 0 件。あわせて流れの合図（`hermes.tool.progress`）も 0 件 |
| K5 速さ | 中央値・最長とも、同じ日の今の秘書（決まり帳つき）の 2 倍以下（2 回呼ぶ分の上乗せだけを許す。今の値なら中央値 15.8 秒・最長 24.8 秒。声の会話の待ちが延びるので PO 承認の対象） | 便0: 頼みから下書きまでの秒を測る |
| K6 メモリ | まとめ役＋係 2 部屋が動く間の最大メモリを GB で記録（合否ではなく本番の置き場の判断材料） | 便0: 10 秒おきに測った最大値 |
| K7 残らない | 束を流した後、Hermes のデータの置き場全体（覚え書き・会話の記録・ログ〈agent.log など〉を含む全ファイル）に、流した頼みの文が 0 件。Hermes は既定で会話を保存するので、アプリが毎回その会話を消す（§5） | 便0: 束を流し終えたら §5「会話の保存」の後始末（会話を消す→容器を止める→別の使い捨て容器で 3 部屋とも詰め直す→起こす）をしてから、データの置き場全体を頼みの文で探す。探し方（第2.7版で決めた）: 止めた容器とは別の使い捨て容器（`--network none`）で、`/opt/data` 以下の全ファイルを `grep -a`（二値のファイルも読む）で探し、ファイルごとの行数を数える。`-I`（二値を読み飛ばす）は付けない（7回目の記録で `-I` 付きは state.db・state.db-wal を 1 件も出さず、`-I` 無しは 6 件出した: [bin0/out/raw/b8-k7.txt](bin0/out/raw/b8-k7.txt)）。数えるのは、**束を流す前（新しい置き場で 3 部屋を作って起こした後・起点）**・止めた直後・各部屋を詰め直した直後（3 回）・起こした後（第2.8版で起点を足した）。判定は「起点からファイルごとに増えた行が 0」: 起点に当たりの無いファイルに 1 行でも出たら×、起点に当たりのあるファイルは行数が起点と同じなら○。理由（事実）: 何も流していない新しい置き場でも、完成品の部品のファイル（skills の hermes-agent/templates/plugin.js）に束の短い文 1 件が当たる（[bin0/out/source-check-b.md](bin0/out/source-check-b.md)・7回目の [bin0/out/raw/b8-k7.txt](bin0/out/raw/b8-k7.txt) にも毎回出ている）。b4・b5 の 0 行は部品に当たらない目印で数えたもので、束の本物の文で 0 を数えたことはまだ無い。合格の線は変えない（流す前から部品にある文字は「流した頼みの文」に数えない、という読み方）。この読み方は便0 の判定のときに PO に一言で知らせる |
| K8 会社の混ざり | 会社 A の作り物の名前を渡した後、会社 B として 10 問流して A の名前が出る件数 0 | 便0 |
| K9 使った量 | 返事の使った量（usage）の合計と、Hermes の側の総使用量が一致する（後ろで回る処理の分が 0）69/69 | 便0（第2.9版で直した）: 頼みごとに、消す**前**に 2 つを読む。**主の判定**は Hermes の使った量の明細の表 `session_model_usage`（各部屋の `/opt/data/profiles/<部屋>/state.db`）。その会話の番号の行で、本体の呼び出し（`task` が空）の `api_call_count` の合計が 1、`task` が空でない行（便0 では声を使わないので後ろの処理だけ: title_generation・background_review・vision・compression など。声の `voice_chat` は `task` つきでも会話の数に入る: 元ソースの persistence/conversation/usage.py の 12 行目）が 0 行なら○。**読む順と時刻**（第2.10版・審査 R1）: 本体の呼び出しの量はその場では書かれず待ち行列に積まれ、会話の仕上げのときにまとめて書かれる（元ソースの agent/turn_usage.py の 324-327 行目「Enqueued, not written」・agent/session_persistence.py の 529-531 行目）。会話の数と明細の `task` 空の行は同じ書き込みで一緒に書かれる（persistence/sqlite/conversation/_store/usage.py の 177-181 行目）。HTTP の返事より前に書かれるかは、まだ確かめていない。そこで「GET → 明細の表」の順に読み、GET の `api_call_count` と明細の `task` 空の合計が両方 1 以上になるまで 1 秒ごとに 30 回まで読み直す。30 回とも 0 なら×でなく「-」（読めない）にする。1 を超えたら×。**添えの確かめ**は今のまま `GET /p/<部屋名>/api/sessions/<番号>` の `session.input_tokens`・`output_tokens`・`api_call_count` を返事の usage と比べる（一致して 1）。どちらかが合わなければ×、読めなければ「-」（読めないが 1 件でもあれば K9 は判定せず止める）。消した後に Hermes に総量は残らないので、総量はアプリ側で足す。理由（事実・8回目の対照①と元ソース 8fc03744）: 題づけを入れると作り物の AI に 2 回届いたが、会話の `api_call_count` は 1 だった（[bin0/out/raw/r8-5d-probe-c1.txt](bin0/out/raw/r8-5d-probe-c1.txt)・[bin0/out/raw/r8-5-fakelog-c1.txt](bin0/out/raw/r8-5-fakelog-c1.txt)）。Hermes は後ろの処理の量を会話の数に足さず、明細の表に `task` 名つきで書く仕組み（元ソースの persistence/conversation/usage.py の 3・154 行目、persistence/sqlite/conversation/_store/usage.py の 238-270 行目。本体の呼び出しも同じ表に `task` 空で書く: 同 51-59・212-234 行目。詳しくは [bin0/out/opus-check-r8.md](bin0/out/opus-check-r8.md)）。会話の数だけの比べ方（第2.8版まで）は後ろの処理を原理的に捕まえられない。**この表の限り**（第2.10版・審査 L1・元ソースの agent/aux_accounting.py の 104-129 行目・agent/auxiliary_client.py の 6596-6597 行目）: 後ろの処理でも、会話の番号が渡っていない糸からの呼び出し・使った量の無い返事・stream の返事・moa の 2 種類は表に書かれない。本物の AI の束ではこれらは見えない。作り物の AI の対照（§5）では、届いた回数を作り物の AI の記録で数えるので見える。K9 の記録に「対照は題づけだけで確かめた。表に書かれない後ろの処理は、本物の束ではこの方法では見えない」と残す。合格の線は変えない。この表で後ろの処理が捕まえられることは、本物の束の前に対照①で確かめる（§5「便0-B の最初の対照」）。捕まえられなければ K9 は測らず止めて設計役に戻す。本物の AI で返事の `prompt_tokens` と会話の `input_tokens` が違うときは、会話の `cache_read_tokens`・`reasoning_tokens` も記録して止め、設計役がどれを足して比べるかを決めてから判定する（作り物の AI ではどちらも 0 だった） |

便1 以降（アプリにつなぐ・催促・Discord）の基準は、便0 の合格と PO 承認の後に、便ごとの設計で ○× の形にして足す（「はい」なしの書き込み 0 件の数え方・成績の画面の名前と式・催促の日数 N など。審査の §4 の欠けを持ち越す）。

## 5. 技術 How

- まとめ役の部屋: 人格の文書に「係の一覧から 1 つ選び JSON 1 行で答える」だけを書く。道具 0・覚え書き切り。
- 係の部屋: 今の秘書の容器（`secretary-agent/`）の指示と同じ中身を人格の文書に置く。返す形は `secretary-agent/schema.json`。
- 呼び方: Hermes の OpenAI 互換の口（鍵つき）。部屋は URL の頭 `/p/<部屋名>/` で名指し。知らない部屋名は Hermes が 404 で断る（部屋の取り違えで別の部屋が動かない）。
- アプリ側の変更（便1）: 今の `/intent` の本文（`backend/app/routers/assistant.py:201`）を OpenAI 互換の頼みに直す変換部品を 1 つ足す。担当表の provider に `hermes`、sdk の対応表（`backend/app/services/llm_budget.py:180`）に足す。値の決まり（`migrations/20261103_120000_create_ai_job_assignments.sql:32`・`:33`、sdk の最新の決まり `migrations/20261117_100100_add_llm_usage_tts_characters.sql:35`〜37）を広げる migration は危険 PR。
- 頭の渡し方（1 つの形にそろえる）: 担当表の列は provider・model の 2 つだけ（`migrations/20261103_120000_create_ai_job_assignments.sql:26`〜31）。新しい列は足さない。provider 欄は `hermes`（どの容器に送るか）。model 欄に「Hermes の AI 会社/頭」の組（例 `openai-codex/gpt-5.6-terra`）を入れ、アプリが**最初の** `/` で分け、前を `provider`、後ろを `model` として送る（頭の名前そのものに `/` が入る例がある: nous-portal.md の `anthropic/claude-opus-4.6`。`/` が無い値は形の誤りとしてアプリが断る）（api-server.md「Per-request model selection」: provider の無い model は無視される）。Hermes の `model_routes` の別名は使わない（provider なしで別名が効くかが説明書で確かめられない・4回目の審査）。
  - 便0 の最初に確かめる: ①組で送ると返事の model と Hermes の記録がその頭になる ②違う provider を送ったときの動きを記録する（説明書の 400 は model_routes の別名とぶつかったときだけなので、合否には使わない）③model だけ送ると全体または部屋の既定の頭に落ちる（どちらに落ちたかを記録する。合否には使わない）。止めどころは①だけ: ①が通らなければ止めて考え直す
- Hermes の設定（便0 で全部書き出し、版を固定してリポジトリに写しを置く。2回目の審査で確かめた説明書の項目）:
  - 置き場（第2.6版・第2.7版で一覧にした）: 次の 8 つの鍵を、**管理者の固定設定 /etc/hermes/config.yaml の 1 か所だけ**に置き、読み取り専用で容器に差し込む（起動に `-v <固定設定の置き場>:/etc/hermes:ro` を足す）。`logging.level`・`memory.memory_enabled`・`memory.user_profile_enabled`・`platform_toolsets.api_server`・`auxiliary.background_review.enabled`・`auxiliary.title_generation.enabled`・`fallback_providers`・`gateway.multiplex_profiles`。部屋ごとの config（profiles/<部屋>/config.yaml）と起動する側の /opt/data/config.yaml には、この鍵を書かない（同じ設定を 2 か所に置かない）。
    - 正本のファイルは `docs/handoff/ai-assistant/bin0/config.yaml` の 1 つにする。次の便のカードで、その中身を上の固定設定の形に置き換え、3 行目の注記（今は /opt/data/config.yaml と各部屋の config の 4 か所に置くと書いてある）を直し、`docs/handoff/ai-assistant/bin0/setup_profiles.sh:26`・`:35` の写しをやめる。`docs/handoff/ai-assistant/bin0/out/raw/b13-files/managed-final-config.yaml` は調べの記録で、正本ではない。
    - 固定設定に置かない物: `API_SERVER_KEY` は部屋ごとに値が違うので、今のまま各部屋の .env（`docs/handoff/ai-assistant/bin0/setup_profiles.sh:27-32`）。`model` と `provider` は設定に置かず、頼みごとに付ける（下の「頭の渡し方」）。作り物の AI へ向ける `model:` は対照の試しにだけ使い、試し専用の固定設定に入れる（本物の束の固定設定には入れない）。
    - 試し専用の固定設定（第2.8版で決めた）: 正本 `docs/handoff/ai-assistant/bin0/config.yaml` の 8 つの鍵 ＋ 作り物の AI へ向ける `model:` の塊（b5 と同じ中身: `docs/handoff/ai-assistant/bin0/out/raw/b13-files/model.yaml`）。対照①のときだけ `auxiliary.title_generation.enabled` を true に変える。台本が流すときに正本を読み、この 2 点だけを足し替えて使い捨ての置き場に書き出す。8 つの鍵を写した 2 つ目の表はリポジトリに置かない。
    - 対照で台本が送る頭: 本物と同じ「頭の渡し方」で、model 欄の値を `custom/fake-model` とし、台本が最初の `/` で分けて `provider: custom`・`model: fake-model` を送る（b5 は `model` だけを送っていた: `docs/handoff/ai-assistant/bin0/out/raw/b13-files/body-plain.json`）。
    - まだ確かめていないこと: `gateway.multiplex_profiles` を固定設定に置いた形（b5 では固定設定に入っていなかった）。部屋の config から鍵を抜いても固定設定だけで memory・toolsets・background_review・fallback が効くこと（b5 では部屋の config にも置いてあった）。固定設定に置いた `model:` が効くか（b5 では部屋の config と /opt/data/config.yaml に置いた）。台本の頼みの形（`model` と `provider` の両方）で作り物の AI へ届くか。どれも下の `config get` と対照の試しで確かめ、違えば止める。対照で作り物の AI へ 1 回も届かなければ止めて設計役に戻す（b5 の形〈部屋の config に `model:`〉に戻すかは設計役が決める）。
    - 理由（事実）: 起動する側の /opt/data/config.yaml は、README 手順 3 の守りで立てると起動のたびに既定のひな形で上書きされる（完成品の中 docker/stage2-hook.sh:438-447・実測 [bin0/out/source-check-b4.md](bin0/out/source-check-b4.md) Q9）。固定設定は守りのままで 3 部屋に効く（完成品の中 hermes_cli/managed_scope.py の 31 行目・実測 [bin0/out/source-check-b5.md](bin0/out/source-check-b5.md) Q16）。束を流す前に 3 部屋それぞれで `hermes -p <部屋> config get <鍵>` を全部の鍵について表示し、1 つでも違えば止める
  - `logging.level: WARNING`（第2.6版で追加。頼みの先頭 80 字を書く行は INFO〈完成品の中 agent/turn_context.py の 1290 行目〉。WARNING で agent.log の目印 0 行・実測 b4 E2）
  - `auxiliary.title_generation.enabled: false`（第2.6版で追加。新しい会話の最初の送信ごとに会話の題をつける AI 呼び出しが 1 回増える。切ると 1 回の送信で AI へ 1 回・実測 b5 Q13）
  - `gateway.multiplex_profiles: true`（部屋の名指しに要る）
  - 部屋ごとに別の `API_SERVER_KEY`（3 本。鍵を置く人は PO）
  - 頼みに `model` と `provider` を両方付ける（上の「頭の渡し方」。`model` だけは無視される）
  - 全部屋 `platform_toolsets.api_server: []`
  - `memory_enabled: false`・`user_profile_enabled: false`
  - `auxiliary.background_review.enabled: false`（会話の後ろで回る振り返り。1 回で約 3 万トークン使う）
  - 会話の保存: 説明書では止める設定が見つからない（3回目の審査）。アプリが頼みごとに新しい番号 `X-Hermes-Session-Id` を付け、返事の後に消す。消す口は API の口の `DELETE /p/<部屋名>/api/sessions/<番号>`（部屋ごとの鍵）だけを使う。使用中（409 `session_active_turn`）で断られたら 2 秒あけて 3 回までやり直し、それでも消えなければその番号を記録して K7 の探しで残りを確かめる。消した後も文の無い小さな記録が残る（web-dashboard.md）。これで ADR-1077「会話の全文は残さない」を満たしたとする（Q8 で PO 決定）。
    - 第2.5版で直した（便0-A の実物の確かめ・[bin0/out/probe-a-20261125.md](bin0/out/probe-a-20261125.md) S6）: 第2.4版の「①消す前の確かめ（mutation-snapshot）→②DELETE・409 session_busy・409 unknown_execution」は、管理画面（ダッシュボード）の app にだけある口だった（完成品の中 hermes_cli/web_routers/sessions.py の 640 行目・hermes_cli/web_server.py の 850 行目）。API の口の道の表（gateway/platforms/api_server.py の 1569-1601 行目）には DELETE だけがあり（:1581）、使用中の断りは 409 `session_active_turn`（:2704）。`/p/<部屋名>/` は API の口の全ての道に付く（:3943）。
    - ダッシュボードは動かさない。理由: 外から触れる口が増える・容器のメモリが増える。消せたかどうかは、消す口の答え（200 か 404）と K7 の探し（データの置き場全体を頼みの文で grep）の 2 つで確かめれば足りる。snapshot は消す前の中身の写しを取る口で、消すことそのものには要らない。
    - 便0-A で確かめた（[bin0/out/probe-a-20261125.md](bin0/out/probe-a-20261125.md) S6・P5）: ソースの説明は会話そのものを消す（hard delete・会話の記録ファイルも消す）。`/p/<部屋名>/` と部屋の鍵で通る（無い番号は 404・鍵なしは 401）。行が実際に消えるかは便0-B の K7 の探しで確かめる。消えない形なら止めて考え直す
    - 第2.6版で足した（便0-B 7回目と調べ 1〜5 回目・[bin0/out/source-check-b5.md](bin0/out/source-check-b5.md)）: 会話を保存しない口は無い（失敗した頼みも保存される）。DELETE は 200 を返すが、頼みの文は会話の保存の箱（state.db と state.db-wal）に残る。止めただけでも残る（b5: 止めた直後 目印 27 行）。**止めてから別の使い捨て容器で `hermes sessions optimize -p <部屋>`（箱の詰め直し）をすると 0 行**になった（b5: 3 部屋の通しで 0 行・1 回）。動かしたままの詰め直し（`--force`）は完成品のコメントが危ない側に置いているので使わない（完成品の中 hermes_cli/sessions_cmd.py の 1473 行目）。
    - 便0 の後始末の順（K7 の前に 1 回だけ）: ①頼みごとに使った量を読む（K9）→②DELETE（今のまま頼みごと）→束が終わったら③`docker stop`→④`docker run --rm --network none`（固定設定を読み取り専用・同じ置き場）で 3 部屋それぞれ optimize→⑤起こして `/health` 200。止めてから 200 までの秒を記録する（b5 の実測 47.4 秒）。部屋ごとに optimize が効いたかを分けて見るため、各回の後に目印の数を数える（b5 では 3 回の後にしか数えていない。b5 の出力は 3 回とも `reconcile: profile=invoice` だった）。ある部屋を詰め直した後に、その部屋の箱の行が減らなかったら止める。数え方は §4 K7 の探し方。①〜⑤は台本（`docs/handoff/ai-assistant/bin0/run_bin0.py`）の中で行い、人の手ではやらない。今の台本は HTTP だけで docker を呼んでいないので、台本が容器の外から `docker stop`・`docker run`・`docker start` を呼ぶ場所をカードに書く
    - 消す口の答えの記録は「200 か 404」に分けて数える（今の台本 `docs/handoff/ai-assistant/bin0/run_bin0.py:136` は 404 も「消せた」と数えている）
  - 便0-B の最初の対照（第2.7版で足した・作り物の AI・ログイン不要・本物の束より前に 1 回）: b5 の作り物の AI（`docs/handoff/ai-assistant/bin0/out/raw/b13-files/fake_ai.py`）へ向けた試し専用の固定設定で、次の 3 つを確かめる。
    - ①題づけを入れた（`auxiliary.title_generation.enabled: true`）固定設定で 1 回送る。作り物の AI の記録に chat が 2 行そろってから（30 秒待っても 2 行にならなければ記録して止める）、明細の表を読む。○の形: その会話の番号で `task` 空の `api_call_count` 合計 1、かつ `task` が `title_generation` の行が 1 つ（`api_call_count` 1）。題づけの量は別の糸から書かれ（元ソースの agent/title_generator.py の 27-31・822-824 行目）、本体の量は仕上げのときに書かれる（§4 K9「読む順と時刻」）ので、2 行そろった後も「GET → 明細の表」の順で、`title_generation` の行と `task` 空の行の両方が出るまで 1 秒ごとに 30 回まで読み直す。30 回で出なければ止めて設計役に戻す。あわせて GET の `api_call_count` が 1 のままであること（8回目と同じ）を記録する（合否には使わない）。この対照で実物で確かめるのは題づけ 1 種類だけ。background_review も同じ表に書くことは元ソース（同 _store/usage.py の 250-251 行目）で読んだが、実物では動かしていない。K9 の記録に「対照は題づけだけで確かめた」と残す
    - ①の続き（第2.9版で足した・合否には使わない・記録だけ）: ①の会話を消した（DELETE 200）後に、同じ番号の明細の行の数をもう一度数える。消えずに残っても文は入っていない（列は model・task・数だけ: 同 _store/usage.py の 51-59 行目）が、K7 の「残らない」とは別の数として記録する。（第2.10版・審査 L3 で理由を直した）消した後に届いた量の書き込みは断られて捨てられ、行は作り直されない（元ソースの persistence/sqlite/conversation/_store/worker_lifecycle.py の 24-29 行目: 消した会話には墓標が残り、書き込みは AuthorityRefusal で断る・persistence/conversation/usage.py の 9・154 行目）。消した後に明細の行が残るかは、表の作り（persistence/sqlite/_schema.py の 129 行目の ON DELETE CASCADE）が効くかによる（まだ確かめていない）。そのため明細の行の数と `sessions` の行の数を記録する。墓標（`state_meta` の行。キーは 'gateway.retired_session.v1.' ＋会話の番号）に会話の番号が残ることも K7 の記録に一言書く（文は入らない）
    - 明細の表の読み方（第2.9版で決めた）: 走っている容器の中で `docker exec -u hermes`（ログインの手順と同じ利用者: [bin0/README.md](bin0/README.md) の 4 番。root では開かない・第2.10版 審査 L4）し、完成品の中の python の sqlite3 で state.db を**読み取り専用**（`mode=ro` の URI）で開き、その番号の行の `task` ごとの `api_call_count` の合計と行の数だけを出す。会話の文・題の文の列は読まない。python の場所と、読み取り専用で開けるか（WAL と並んで読めるか）は対照の最初に 1 回確かめ、開けなければ止めて設計役に戻す（まだ確かめていない）。元ソースは GitHub の 8fc03744 で読んだので、対照の前に完成品の中の同じ 2 ファイル（persistence/conversation/usage.py・persistence/sqlite/conversation/_store/usage.py）で `session_model_usage` と `record_auxiliary_usage` の行を `grep -n` して生の行を記録し、無ければ止める。容器の外から state.db を写して読む形はとらない（文の入った箱の写しが増える）
    - 形の指示が届いた証拠（第2.9版で足した）: 作り物の AI の記録に、受けた messages のどれかに台本の決まった 1 文（形の指示の頭）が入っていたかを `schema_lead=1/0` で書く（文そのものは書かない）。8回目は記録から頭の部分を消したため、届いたかをこの記録では確かめられなかった（[bin0/out/opus-check-r8.md](bin0/out/opus-check-r8.md) 2-a）。③で係の 2 部屋は 1・まとめ役は 0 なら○。その 1 文の正本は台本 [bin0/run_bin0.py](bin0/run_bin0.py) の `SCHEMA_SYSTEM_LEAD`（44 行目）1 か所だけにする。作り物の AI へは、台本が起動のときにその 1 文を作り物の AI の置き場（`/fake` の下）の 1 ファイルへ書き出し、作り物の AI はそのファイルを読む。作り物の AI の中に同じ文を書き写さない（第2.10版・審査 L5）。ファイルが無い・空なら作り物の AI は起動を止める
    - ②台本が自分で作った番号（`X-Hermes-Session-Id`・`docs/handoff/ai-assistant/bin0/run_bin0.py:107`）で `GET /p/<部屋名>/api/sessions/<番号>` が 200 になる。404 なら止める
    - ③本物の束と同じ 8 つの鍵（題づけ切り・`multiplex_profiles` 入り・部屋の config に鍵なし）に、作り物用の `model:` だけを足した試し専用の固定設定で、3 部屋とも `/p/<部屋名>/` が答え、`config get` で 8 つの鍵が思った値になり、1 回の送信で作り物の AI へ 1 回だけ届く。違えば止める。あわせて、起動のあと /opt/data/config.yaml に `gateway.multiplex_profiles: true` が書き込まれたか（[bin0/out/source-check-b4.md](bin0/out/source-check-b4.md) Q9 では書き込まれた）を記録する（合否には使わない）
    - 対照の止めどころのまとめ（第2.10版）: 作り物の AI へ 1 回も届かない／①で 30 秒待っても 2 行にならない／①で 30 回読み直しても明細の表に title_generation の行か `task` 空の行が出ない・`task` 空の合計が 1 でない／明細の表を読み取り専用で開けない／容器の中で python が見つからない／完成品の中の 2 ファイルに `session_model_usage`・`record_auxiliary_usage` の行が無い／形の指示の 1 文のファイルが無い・空／②が 404／③が違う（3 部屋とも `task` 空 1・`task` あり 0 行・作り物の AI へ 1 回・係の 2 部屋で `schema_lead=1`）
    - 本番での後始末の間隔（何時間に 1 回止めて詰め直すか）は、止まる秒と、消した文が箱に残る時間の両方に関わるので、便0 の判定のときに PO が決める（§9）
  - 形の渡し方（第2.6版で直した）: Hermes には形を強制する口が無い（`response_format`・`json_schema` は読まれない・[bin0/out/source-check-b.md](bin0/out/source-check-b.md)）。7回目は形の表を渡し忘れ、請求書の下書きが 24 件中 4 件しか形を通らなかった（今の秘書は `secretary-agent/server.mjs:70` で `--json-schema` を渡している）。直し方: 係の部屋への頼みに role system の文を 1 つ付ける。中身は「出力は次の JSON Schema に合う JSON 1 つだけ」という決まった 1 文と、`secretary-agent/schema.json` をそのつど読んだ全文。写しは作らない（正本は schema.json の 1 つ）。Hermes はこの文を部屋の人格の**後ろ**につなげて AI に渡す（完成品の中 gateway/platforms/api_server_openai_routes.py の 719-726 行目・agent/chat_completion_helpers.py の 2096-2097 行目・実測 b5 Q14）。決まった 1 文は台本の定数 1 か所に置き、`docs/handoff/ai-assistant/bin0/run_bin0.py:106` の頼みの本文の messages の先頭に足す。まとめ役の部屋には付けない。返事はアプリ（便0 は台本）が同じ schema.json で検査し、落ちたら 1 回だけやり直す（Q8 で PO 決定）
  - `fallback_providers: []`（AI 会社が失敗したときに別の会社へ自動で切り替わる仕組みを切る。3 部屋で `[]` と表示されることは b5 Q16 で確かめた。存在しない頭を送ったときに切り替わらず誤りで返るかは便0 で確かめる）
- 入れ方: 公式の完成品（Docker の `nousresearch/hermes-agent`）を版の番号で固定する。pip での入れ方は公式に非対応。Python は 3.14 だけ。メモリは最低 1GB・推奨 2〜4GB（docker.md）。今の秘書の容器は 512MB（`docker-compose.secretary-agent.yml:26`）。
  - 便0 の場所（Q8: クラウドの作業場所）で Docker の完成品が動くかを最初に確かめる。動かなければ止めて PO に相談する（Q8）。公式の入れる台本など別の入れ方には、相談なしに切り替えない
- 容器の守り: 目標は今の秘書と同じ形（`docker-compose.secretary-agent.yml:19`〜26: read_only・cap_drop ALL・no-new-privileges・メモリ上限）。ただし公式の容器は root で立ち上がり、UID の付け替え・持ち主の直し・利用者 hermes への切り替えをする（docker/stage2-hook.sh）ので、同じ形で立つとは言えない。便0 で「同じ形で立つか」を測り、立たなければ立つのに要る最小の権限だけを一覧にする（どの権限を戻したかと理由）。Hermes が書き込む場所の一覧も便0 で取る。本番に置くときの守りは、その一覧を見て PO が決める
- ログイン: 今の秘書と同じ ChatGPT の月額契約で `hermes auth add openai-codex`（device code・従量の鍵は要らない）。試し用に別に 1 回ログインする（Q8 で PO 決定）。`gpt-5.6-terra` が選べるか・部屋ごとにログインが要るかは便0 の最初に確かめる
- 便0 はアプリを触らない。試しの場所で、束を流す小さな台本だけで測る。

## 6. 接触面分析（6 面）

| 面 | 触れるもの | 守り方 |
|---|---|---|
| ① 画面 | 便1 で秘書の窓の返事の出どころが変わる（見た目は同じ） | 形が同じ JSON なので画面は変えない |
| ② 並行の作業 | 秘書の作業札 40 件超・声の会話（ADR-1087）も同じ口を使う | 便1 の前に重なりを確かめる。声の待ちは K5 で測り PO が判断 |
| ③ DB | 担当表の値の決まり・仕事名・台帳 | migration は危険 PR・PO の GO |
| ④ 会社のデータ | 便1 以降、アプリが選んだ行を外の AI へ渡す | 便0 は作り物のみ。本物は PO の決定の後 |
| ⑤ サーバー | Hermes の置き場 | 便0 は本番と別。本番の置き場は PO が決める |
| ⑥ 外の会社 | Hermes（外の仕組み）と AI 会社 | 版を固定。鍵の置き場と置く人は PO（ADR-1003） |

## 7. 弊害・トレードオフ

- 頼み 1 回で AI を 2 回呼ぶ → 遅く・高くなる。K5・K9 で測り、超えたら止める。
- 声の会話の待ちが延びる（ADR-1087 は今の 5〜8 秒を前提）→ K5 の線を PO が決める。
- Hermes の作りが変わる → 版を固定し、上げるときは束を流し直す。
- 「必ず成功する」は机の上では言えない → 便0 を止めどころにする。K1〜K5・K7〜K9 のどれかが落ちたら、本番に何も足さず止めて PO に報告する。

## 8. 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 0 | PO: K1〜K9 の承認と便0 の試し方（済: Q8「1」2026-11-25）。残りは試し用のログイン 1 回（device code）と、本番を読む日の同意票 | PO |
| 便0 | 試しの場所（本番と別・作り物のデータ）に Hermes の 3 部屋（まとめ役・予定係・請求書係）を置き、束 69 件で K1〜K9 を測る。終わったら場所を消す | クラウドの Sonnet（実装カードと PO の実装承認の後） |
| 判定 | 便0 の数字で続けるか止めるかを PO が決める。本番の置き場・外の AI に本物のデータを渡すか・新規テーマか延長か（審査 R1）もここで決める | PO |
| 便1 | 担当表の migration（危険 PR・GO）＋変換部品。今の秘書は残し、担当表で切り替え | クラウドの Sonnet |
| 便2 | 基準の一覧と「未払いの催促」（既存の期限切れ一覧 `backend/app/routers/analytics.py:207` と数え方を揃える） | クラウドの Sonnet |
| 便3 | Discord の非公開の部屋（ADR-091 の改め・スタッフのロールを渡さない） | クラウドの Sonnet |

便1 以降は、便ごとに file:line＋変更前後＋触らない範囲の設計とカードを別に作る（この文書は作りの全体の案）。

## 9. 未決（PO の判断が要る・聞く順）

1. 便0 の進め方: **決定済み**（Q8「1」2026-11-25。中身は §0）。本番を読む日には、その日の同意票（permit）を 1 回取る。
2. 便0 の後: 本番での会話の後始末の間隔（§5「会話の保存」。止まる秒と、消した文が残る時間の兼ね合い）／本番の置き場／本物の会社データを外の AI に渡すか（PO が 2026-11-01 に禁じた「AI 会社の約束の調べ」を解くかを含む）／新規テーマか延長か／K5 の線／最初の係（Q5）／費用の上限。

## 10. 審査の記録

- 第1版: 審査役 REVISE（[review-opus-1.md](review-opus-1.md)）・Fable REVISE（[review-fable-1.md](review-fable-1.md)）。
- 第2版: 審査役 REVISE（[review-opus-2.md](review-opus-2.md)）。指摘は第2.1版で本文に入れた。
- 第2.1版: 審査役 REVISE（[review-opus-3.md](review-opus-3.md)）。会話の消し方・形の固定・AI 会社の名前の置き場・入れ方・台帳の単位・容器の守り・K3 の正解表を第2.2版で本文に入れた。PO が決める点は §9。
- 第2.2版: 審査役 REVISE（[review-opus-4.md](review-opus-4.md)）。Q8 を §0・§5・§9 に入れ、頭の渡し方を「model 欄に AI 会社/頭の組・アプリが分けて送る」1 つにした。容器の守り・クラウドで Docker が動くか・消す口の通り方・unknown_execution・K7 の探す範囲・K2 の数え方を第2.3版で本文に入れた。
- 第2.3版: 審査役 REVISE（[review-opus-5.md](review-opus-5.md)・軽い直し 3 点）。確かめ②を合否から外す・`/` の分け方・表題と本番の読み取りの書き方を第2.4版で直した。
- 第2.4版: 審査役 APPROVE（[review-opus-6.md](review-opus-6.md)・差分の確かめ）。便0 の実装カードを書ける状態。同じ会社の AI どうしの審査で、独立した第三者の審査ではない。
- 第2.5版: 便0-A の実物の確かめで、会話を消す口が第2.4版の想定と違った（§5「会話の保存」）。設計役（Opus）が API の口の DELETE だけを使う形に直した。審査は便0-A の PR のマージ前審査で受ける。
- 第2.6版: 便0-B 7回目（K2 25/48・K7 文が残る）の原因の確かめ（[bin0/out/opus-check-b.md](bin0/out/opus-check-b.md)）と Hermes の中身の調べ 5 回（[bin0/out/source-check-b.md](bin0/out/source-check-b.md)〜[b5](bin0/out/source-check-b5.md)）を受け、設計役（Opus）が §4 の検証方法（K2・K7・K9）と §5（設定の置き場・形の渡し方・会話の後始末）を直した。合格の線（基準の文）は変えていない。審査はクラウドで受ける。
- 第2.6版: 審査役（architect・クラウド）REVISE（[review-architect-v26.md](review-architect-v26.md)）。R1 固定設定に置く鍵を名前で並べ、置かない物の置き場と正本のファイルを決める。R2 K7 の探しを `-I` 無しの `grep -a` に決める。R3 K9 の比べ方が後ろの処理を捕まえられるかの対照を足す。軽い指摘 L1〜L5 もあわせ、第2.7版で直した。
- 第2.7版: 審査役（architect・クラウド）REVISE（[review-architect-v27.md](review-architect-v27.md)）。前回の 8 件は直っていた。R1 対照の試しで作り物の AI へ届く道（試し専用の固定設定・送る頭）を決める。R2 K7 に流す前の数（起点）を足し、増えた行で数える。軽い指摘 L1〜L5 もあわせ、第2.8版で直した。
- 第2.8版: 審査役（architect・クラウド）APPROVE（[review-architect-v28.md](review-architect-v28.md)）。前回の 7 件は直っていた。合格の線は変わっていない。軽い指摘 L1〜L5（正本を先に 8 つの鍵へ置き換える・対照と本物で置き場を分ける・台本が付けた番号で題づけが走るかを記録・作り物の AI の記録は止める前に読む・届いた model の値を記録）は便0-B のカードに入れる。
- 第2.9版: 便0-B 8回目が対照①で止まった（作り物の AI に 2 回届き、会話の `api_call_count` は 1）。第2.8版の対照①の○の形（会話の数が 2）は、確かめていない見込みのまま決めていた（設計役の入れ忘れ）。元ソース 8fc03744 を読み、後ろの処理の量は会話の数でなく明細の表 `session_model_usage` に入ると確かめた（[bin0/out/opus-check-r8.md](bin0/out/opus-check-r8.md)）。設計役（Opus）が §4 K9 の検証方法と §5 の対照を直した。合格の線（基準の文）は変えていない。審査はクラウドで受ける。
- 第2.9版: 審査役（architect・クラウド）REVISE（[review-architect-v29.md](review-architect-v29.md)）。設計が引いた元ソースの行 9 か所は合っていた。R1 本体の呼び出しの量は待ち行列から仕上げのときに書かれるので、読む順（GET → 明細の表）と読み直しの上限・0 のときは「-」を決める。軽い指摘 L1〜L6（表の限り・`task` つきでも会話に入る声・消した後の理由が元ソースと逆だった・`docker exec` の利用者・形の指示の 1 文の正本・止めどころ 2 つ）もあわせ、第2.10版で直した。指摘の元ソースの行は設計役（Opus）も読んで合うことを確かめた。

## 維持の仕組み

- 守り手: 人手で守る
- 対象: 「書き込みはアプリだけ」「Hermes の道具 0・覚え書き切り」「はい の後にだけ作る」「頭の正本は担当表」
- 関所なしの場合: まだ実装前で試験が無いため。便0 の台本を残し、便1 で `backend/tests/` に試験を作って守り手を切り替える。
