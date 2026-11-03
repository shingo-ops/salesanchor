# ADR-1058: アプリの中で働く AI の担当（AI とモデル）は DB の1か所で決め、スーパー管理の画面で見て切り替える・成功も失敗も使用の記録に1行ずつ残す・秘書は ChatGPT（Codex CLI・月額契約）も選べる

| 項目 | 内容 |
|---|---|
| ステータス | Accepted（2026-11-03 PO が「この設計で決める」の選択肢に「1」と答えた。設計審査 9回目 合格〔同じ種類の AI による審査〕。方針の芯は PO の言葉: 「chatbotはchatgptに任せたい」・「画面でそれぞれのログイン情報や担当業務が見える化出来ていて管理できるようにしておいてほしい」・範囲はアプリの中の AI（選択「1」）・画面から AI とモデルを切り替えられるところまで（選択「2」）・最初の選択肢の一覧（選択「1」）、いずれも 2026-11-02） |
| 起案日 | 2026-11-03 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1056（チャット秘書。本 ADR が一部を置き換える）、ADR-1004（LLM 使用量台帳）、ADR-1016（即時反映の表）、ADR-027（i18n）、ADR-067・ADR-144（金型とデザイントークン）、ADR-135・ADR-136（危険 PR の GO） |
| 設計 | docs/handoff/secretary-chatgpt/design.md（現在地: docs/handoff/secretary-chatgpt/recon.md、KGI: docs/handoff/secretary-chatgpt/kgi.md、審査の記録: design.md §14） |

---

## What（何を決めたか）

- アプリの中で AI が働く仕事は5つとし、名前を使用の記録の purpose と同じにする: `line_extraction`（解析）・`translation_inbound`・`translation_inbound_escalation`・`translation_outbound`（翻訳）・`secretary_intent`（秘書）。
- 仕事ごとの担当（provider と model）の正本は DB の public の表 `ai_job_assignments` の1か所。選べる組み合わせは `ai_job_choices`、変えた記録は `ai_job_assignment_history`。3表とも tenant_id を持たない。
- コードの固定値と環境変数のモデル名（`_GEMINI_MODEL`・`MODEL_RECEIVE`・`MODEL_SEND`・`DEFAULT_MODEL`・`TRANSLATION_MODEL_*`・秘書の容器の `"sonnet"`）は消す。読むのは関数 `get_ai_assignment(job_key)` だけで、1回の仕事の初めに1回読み、下へ引数で渡す。行が無ければ止まる（既定値に逃げない）。
- 選択肢は migration でだけ足す。画面と API に選択肢を足す道は作らない。最初の一覧（PO 2026-11-02「1」）:
  - 解析: gemini / gemini-3.1-flash-lite の1つだけ（固定）。
  - 翻訳3つ: gemini / 料金表 `LLM_PRICING` にある5モデル。
  - 秘書: claude / sonnet。codex / gpt-6-luna・gpt-5.6-terra・gpt-5.6-luna は ChatGPT の容器を入れる段で足す。
- 解析の選択肢を増やす時は、先に正答率の測り方で測ってから migration で足す。料金表に無い Gemini モデルは選択肢に入れない（CI で確かめる）。
- 値の一覧の正本は DB の CHECK。Python・画面・i18n の一覧は写しで、CI で CHECK と同じ集合であることを確かめる。
- 使用の記録 `llm_usage_events` に `outcome`（ok・failed）と `error_code` を足す。error_code は9つに閉じる: `auth_failed`・`timeout`・`rate_limited`・`http_error`・`unreadable`・`tool_used`・`not_ready`・`busy`・`other`。API を呼んだ1回ごとに1行（その場の送り直しも1回ずつ）。API を呼んでいない失敗と打ち切りは書かない（これは Gemini の経路の決まり）。秘書は backend から容器への1回の頼みを1回と数え、その頼みの失敗は `not_ready`・`busy` も含めて書く。担当表を読む前の失敗は、AI とモデルが分からないので書かない（design §4-2-3・§5-3）。今の集計は `outcome = 'ok'` だけを数え、数字を変えない。
- スーパー管理の解析ダッシュボードに「AI の担当」タブを置き、5つの仕事の AI・モデル・ログインの○×・最後に動いた日時・直近24時間の回数・最後の失敗の理由・変えた記録を見せ、切り替えられるようにする。API はスーパー管理者だけ。鍵の値・メールは返さない。
- 秘書は ChatGPT（Codex CLI・`@openai/codex@0.162.1` 固定・月額契約のログイン）を担当に選べる。専用の容器 `secretary-codex` を Claude の容器と並べて置き、道具・ウェブ検索・書き込みを止めた設定で、頼みの文は標準入力で渡す。許す一覧の外の合図が1つでもあれば答えを捨てる。
- ADR-1056 のうち次の2点を置き換える: 「秘書の AI は Claude Code に固定」→担当表で選ぶ。「秘書は `llm_usage_events` に書かない」→成功も失敗も1行ずつ書く（cost_usd は月額のため NULL）。ADR-1056 のほかの決まり（AI に会社のデータも道具も渡さない・作成は利用者が「作る」を押した時に今の口で行う・使える人の条件）はそのまま。

## Why（なぜ）

- PO の求めは「画面で担当とログインが見え、管理できる」こと。今はモデルがコード・環境変数・容器の3か所に散っていて（recon §1）、どこを変えれば何が変わるかが画面から分からない。正本を DB の1か所にすれば、画面・記録・実際の呼び出しが同じ値を見る。
- 選択肢を migration に限るのは、解析の正答率や料金表に無いモデルの費用を、画面の操作1つで崩さないため。
- 失敗を記録しないと、ログインが切れても画面に×を出せない（今の記録は成功した Gemini の呼び出しだけ。recon §2）。
- 秘書を ChatGPT にするのは PO の決定。容器を分けて並べるのは、合格するまで Claude を戻し先に残すため。

## リスク（記録）

- 月額契約（ChatGPT の個人の契約）を会社のサーバーで使ってよいかは使い方の約束の判断で、PO が決める。決まるまで ChatGPT の容器は本番に出さない。答えが「不可」なら秘書は Claude のまま。
- ログインの鍵（auth.json）は容器専用の書けるボリュームに残る。この容器だけに付け、中身は誰も表示しない。
- 失敗の行を書く別の取引が失敗しても元の処理は止めない（種類だけログに出す）。
- 解析・翻訳の担当を画面で変えるとお客さんの解析・翻訳に効く。試験のために本番の解析・翻訳の担当は切り替えない。

## Scope

- Included: 担当の3表・使用の記録の列と CHECK・読む関数と読み手の直し・失敗の記録・画面「AI の担当」タブと API・容器 `secretary-codex`・deploy.yml の段・i18n・試験
- Excluded: 解析を ChatGPT や月額契約に変えること、開発で働く AI の表示、指示文の中身、料金表の値、予算の数え方

## 戻し方

- 秘書: 画面で担当を claude に戻す（次の呼び出しから効く）。容器は `docker stop secretary-codex`。
- コード: 前の版に戻せば元どおり（担当表は今の本番と同じ値で始める）。足した表と列は残しても害は無い。failed の行は残るが集計には入らない。
- 段ごとの細かい戻し方は design.md §10。
