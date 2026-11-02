# 秘書チャットを ChatGPT に・アプリの AI を画面で管理 — 設計（草案 v1・審査前）

- 状態: 設計案作成済み／設計審査 未／PO 承認 未／実装 未着手
- 目標: `kgi.md`（K1〜K10）。現在地: `recon.md`（§番号で参照）。
- 関係 ADR: ADR-1056（秘書）・ADR-1004（使用量台帳）・ADR-027・ADR-067・ADR-144。新しい ADR（案: ADR-1057「アプリの AI の担当は DB の1か所で決め、画面で見て切り替える」）を起案し、ADR-1056 の「Claude Code に固定」「ledger に書かない」を置き換える。

## 1. 目的（PO の言葉）
- 「chatbotはchatgptに任せたい」。
- 「画面でそれぞれのログイン情報や担当業務が見える化出来ていて管理できるようにしておいてほしい」。画面から AI とモデルを切り替えられるところまで（「2」）。

## 2. 対象と対象外
- 対象: 秘書の答え役を ChatGPT（Codex CLI・月額契約のログイン）にする。アプリで AI が働く5つの仕事の担当を DB の1か所に移す。スーパー管理の画面で見る・切り替える。使用の記録に成否と秘書を足す。
- 対象外: 解析を ChatGPT や月額契約に変えること（PO 11/2 保留）。開発で働く AI の表示（PO「1」）。指示文の中身の変更。料金表の作り（`llm_budget.py:57-89`）の変更。

## 3. 変更の前と後
| 項目 | 今（recon） | 後 |
|---|---|---|
| 解析のモデル | コード固定（recon §1） | DB の担当表から毎回読む |
| 翻訳のモデル | 環境変数（recon §1） | DB の担当表から毎回読む。環境変数は読まない |
| 秘書の AI | Claude Code・sonnet 固定（recon §4） | DB の担当表の AI・モデル。ChatGPT 用の容器を足す。Claude の容器は ChatGPT が合格するまで残し、戻し先にする |
| 使用の記録 | 成功した Gemini の呼び出しだけ（recon §2） | 5つの仕事の成功と失敗を同じ表に1行ずつ |
| 画面 | 担当・ログインの画面は無い（recon §3） | 解析ダッシュボードに「AI の担当」タブ |

## 4. DB（正本は1か所）
### 4-1 新しい表（public・tenant_id なし・前例 extraction_prompt_config）
- `public.ai_job_choices`（選べる組み合わせ）: id・job_key・provider・model・created_at。UNIQUE(job_key, provider, model)。行は migration でだけ足す（PO が決めた選択肢だけ）。
- `public.ai_job_assignments`（今の担当）: job_key PRIMARY KEY・provider・model・updated_by・updated_at。外部キーで (job_key, provider, model) が ai_job_choices にあることを DB が強制する。
- `public.ai_job_assignment_history`（変えた記録）: id・job_key・old_provider・old_model・new_provider・new_model・changed_by・changed_at。書き換え・消しはしない。
- job_key は5つ: line_extraction・translation_inbound・translation_inbound_escalation・translation_outbound・secretary_intent（llm_usage_events の purpose と同じ名前にし、記録と担当を名前でつなぐ）。
- 初めの行は今と同じ値（解析 gemini-3.1-flash-lite・翻訳3つ gemini-3.5-flash-lite・秘書 claude/sonnet）。入れ替えた日から挙動は変わらない。
- 選択肢の最初の行（PO 決定 2026-11-02「1」）:
  - line_extraction: gemini / gemini-3.1-flash-lite の1行だけ（解析は固定。増やす時は先に正答率を測ってから migration で足す）。
  - translation_inbound・translation_inbound_escalation・translation_outbound: gemini / 料金表にある5モデル（gemini-2.5-flash・gemini-2.5-pro・gemini-2.5-flash-lite・gemini-3.1-flash-lite・gemini-3.5-flash-lite。`llm_budget.py:57-89`）。
  - secretary_intent: codex / gpt-6-luna・gpt-5.6-terra・gpt-5.6-luna、claude / sonnet。
  - 料金表に無い Gemini モデルは選択肢に入れない（費用が計算できなくなるため）。CI 試験で「gemini の選択肢はすべて料金表にある」を確かめる。
### 4-2 使用の記録（llm_usage_events）を広げる
- 列を足す: `outcome`（ok・failed、既定 ok）・`error_code`（決まった短い名前だけ。例 auth_failed・timeout・rate_limited・unreadable・tool_used・other。本文やメッセージは入れない）。
- CHECK を作り直す: purpose に secretary_intent、sdk に codex-cli・claude-code を足す。
- 今の集計（`LlmUsageSection`・予算）は outcome='ok' だけを数えるように直す。失敗の行は費用 null・使用量 null。
- 翻訳の口（`message_translator.py`）と解析の口（`gemini_extraction_svc.py` ほか recon §1 の5か所）で、失敗した時にも1行書く。
### 4-3 分散させないための決まり
- モデル名の固定値（`_GEMINI_MODEL`）と `TRANSLATION_MODEL_*` の読み取りを消す。読む所は1つの関数 `get_ai_assignment(job_key)`（sync・async の2版、同じ SQL）だけ。行が無ければ例外で止める（既定値に逃げない）。
- 試験の道具（`tools/prompt_ab.py` など）も同じ関数から読む。比べ試験で別のモデルを使う引数は今どおり道具の引数で渡す（担当表は変えない）。
- 機械の検査: CI に「services の中にモデル名の文字列・TRANSLATION_MODEL の読み取りが0件」の試験を足す（K5）。

## 5. 秘書を ChatGPT に
### 5-1 容器 secretary-codex（新規・別 compose・Claude の容器と並べる）
- 中身: node:22-bookworm-slim＋`@openai/codex@0.162.1` を固定。server.mjs は今の作りを写し、呼ぶ所だけ codex に変える。
- 呼び方（1回ごと）: 空の一時フォルダを cwd に、`codex exec --ephemeral --ignore-user-config --ignore-rules --skip-git-repo-check --sandbox read-only --json --output-schema <schema> -m <model>` ＋ recon §5-2 の止め設定（web_search disabled・features 17個 false）。指示文と答えの形のファイルは今の secretary-agent のものをそのまま使う（写しを作らず同じファイルを両方の容器に入れる）。
- 返事の点検（機械の見張り）: 出てきた合図を全部読み、`agent_message` と、内容が「Code mode will fail closed」の error 以外の種類（command_execution・web_search・file_change・mcp_tool_call 等）が1つでもあれば答えを捨て、502 `tool_used` を返して記録する（K2 の二重の守り）。
- ログイン: CODEX_HOME を専用の名前付きボリューム `secretary-codex-home`（書ける・この容器だけ）にする。容器のほかの場所は read_only のまま。auth.json の中身は読まない・出さない。読むのは `last_refresh` の日時と、ファイルがあるかどうかだけ。
- ログインのし方: PO が手元で台本 `scripts/ops/secretary-codex-login.sh` を流す（manual-only 鍵）。中で `docker exec -it secretary-codex codex login --device-auth` を動かし、出てきたアドレスとコードを PO が手元のブラウザで入れる。AI は流さない。手元の Mac のログインとは別に持つ。
- `/health` は {ready: auth.json がある, last_refresh: 日時} だけを返す。
- 失敗の読み替え: exit≠0 で標準エラーに refresh_token_invalidated・token_revoked・401 があれば auth_failed（標準エラーは記録しない。種類の名前だけ）。そのほかは今の作り（server.mjs:86-115）と同じ。
- 使用量: turn.completed の input_tokens・cached_input_tokens・output_tokens・reasoning_output_tokens を返し、backend が ledger に書く（費用は月額のため null）。
### 5-2 backend
- `assistant.py` は呼ぶ前に `get_ai_assignment("secretary_intent")` を読み、provider が codex なら secretary-codex、claude なら secretary-agent に送る。送る body に model を足す。容器は model を受け取って -m（claude は --model）に渡す。容器の側で選択肢の一覧は持たない（正本は ai_job_choices）。
- 宛先の対応（provider→容器の URL）は配線なので backend の1か所の対応表に置く。
- 呼ぶたびに ledger に1行（成功・失敗とも）。

## 6. 画面（スーパー管理・解析ダッシュボードに「AI の担当」タブ）
- 置き場: `AnalysisDashboardPanel.tsx:55` の DashboardTab に `ai` を足し、新しい部品 `AiJobsSection.tsx` を出す（前例 LlmUsageSection）。
- 表（DataTable）5行。列: 仕事の名前・AI・モデル・ログイン（Badge ○×）・最後にうまく動いた日時・直近24時間の回数・最後の失敗の理由（error_code を i18n で言葉に）・秘書の行だけ ChatGPT のログインが最後に更新された日。
- 切り替え: 行の「変える」（Button）→ Modal の中で Select（選択肢は ai_job_choices の行だけ）→ ConfirmModal →保存。
- 変えた記録: 表の下に DataTable（誰が・いつ・何から何へ）。
- ログイン ○× の決め方: 次のどれかで ×。①その AI の最後の呼び出しが auth_failed ②Gemini の鍵が環境に無い（あるかどうかだけ見る） ③秘書の容器の /health が ready=false。どれも無ければ ○。値・メールは返さない（K4）。
- 金型・トークン・i18n だけ（ADR-144・ADR-067・ADR-027）。新しい CSS は var(--…) だけ。
### 6-1 API（新規・スーパー管理だけ）
- `GET /api/v1/super-admin/ai-jobs`: 5行＋各行の選択肢＋ログイン○×＋最後の成功・失敗・24時間の回数。
- `PUT /api/v1/super-admin/ai-jobs/{job_key}` {provider, model}: `require_super_admin`。ai_job_choices にない組は 422。担当の更新と履歴の1行を同じ取引で書く（K9・K10）。
- `GET /api/v1/super-admin/ai-jobs/history?limit=50`。

## 7. 進め方（1便ずつ・変更→反映→測る）
| 便 | 中身 | 合格の見方 |
|---|---|---|
| 便1 | 担当表3つ・ledger の列と CHECK・読む関数・解析と翻訳を担当表から読む（値は今と同じ）・失敗も記録 | 本番で解析の記録の model が今と同じ。失敗行が出る。モデル名の固定値0件（K5） |
| 便2 | 画面「AI の担当」タブ＋API（表示と切り替え） | K3・K4・K7・K9・K10 |
| 便3 | secretary-codex 容器（並べて起動・担当は Claude のまま）→PO がログイン→ 試験の担当切替で K1・K2・K6・K8 を測る→合格なら担当を ChatGPT に | K1・K2・K6・K8 |
| 便4（合格後） | Claude の容器と専用ファイルを片付けるかを PO が決める | — |
- 便3の前に、Docker の中で Codex が動くか（recon §5-3）を GitHub の一時 VM（sandbox-test）で確かめる。ログインが要らない範囲（起動・止め設定で道具一覧が出ないこと・囲いの起動失敗の出方）。

## 8. 受け入れの基準と確かめ方
|基準|検証方法|
|---|---|
| K1 秘書の頼み10本が同じ形で返る・答えは ChatGPT | 決まった10本を本番の秘書に送る表。ledger の sdk=codex-cli が10行 |
| K2 読む・書く・命令・外への通信0回 | 攻めの文10本。容器の合図点検で tool_used 0件、ledger の error_code=tool_used 0件、容器の一時フォルダが空 |
| K3 画面に5行・各項目 | PO が画面で数える |
| K4 鍵・メールが出ない | API の返事と画面の文字を機械検査（鍵の形・@ を含む文字列0件） |
| K5 担当は DB の1か所 | CI の試験（固定値・環境変数の読み取り0件）。担当を変えると画面と次の記録が変わる |
| K6 ログインが切れたら × | 試験の担当で秘書を ChatGPT にし、ボリュームの auth.json を退けて1回呼ぶ→×。戻して→○ |
| K7 金型・トークン・i18n | 既存の lint・i18n 検査・金型検査で違反0 |
| K8 空きメモリ | 便3の前に prod1 の空きを測り基準値を決める。後で同じ測り方 |
| K9 切り替えが次の呼び出しから効く・履歴 | 切り替え→次の1回の ledger の model が新しい値・履歴が1行増える |
| K10 スーパー管理だけ | ほかの権限で PUT→403 |

## 9. リスクと対処
- 解析のモデルを画面で変えると正答率が落ちうる → 選択肢は migration で PO が決めたものだけ。解析の選択肢を増やす時は正答率の測り方（ADR 正答率の測定）で先に測る決まりを ADR に書く。
- ChatGPT の答えが揺れる（recon §5-2 期限の null）→ K1 の10本で測る。揺れが出たら指示文の調整は別の便。
- 月額契約の使い方の約束・回数の上限 → 止められても秘書が「準備ができていません」になるだけ（ADR-1056 と同じ）。担当を Claude に戻せる。
- Docker で Codex が動かない・囲いが動かない → 便3の前の一時 VM で確かめる。道具はすべて切ってあり、合図の点検でも止める。
- auth.json は書けるボリュームに残る（ログインの鍵）→ この容器だけに付け、chmod 600・バックアップ対象から外す。中身は誰も表示しない。
- 失敗も記録すると行が増える → 解析の失敗は1日数件の想定（未測定）。便1のあと1週間の行数を測る。

## 10. 戻し方
- 便1・2: 担当表は今と同じ値で始めるので、コードを前の版に戻せば元どおり。新しい表は残しても害なし。
- 便3: 画面で秘書の担当を Claude に戻す（次の呼び出しから戻る）。容器は `docker stop secretary-codex`。

## 11. 維持の仕組み
- 選択肢を増やすのは migration だけ（画面からは足せない）。
- CI の試験で固定値・環境変数の読み取りが戻らないようにする（K5）。
- ログインの更新が止まったら画面の秘書の行が×になる。毎朝の本番点検に「秘書の行が○」を足す案は便2のあと PO に聞く。

## 12. 外部事例
- 使っていない。理由: 今回の判断はこのアプリの中の配線と、Codex CLI の実際の動き（手元の試験 recon §5-2）で決まり、他社の数値で決める点が無いため。

## 13. PO に決めてもらうこと（1回に1件ずつ）
1. 仕事ごとに選べる AI とモデルの最初の一覧 → 決定済み（PO 2026-11-02「1」: 解析は固定・翻訳は Gemini 5つ・秘書は ChatGPT 3つと Claude。§4-1）。
2. 秘書を ChatGPT にした時の最初のモデル（試験では3つとも6〜8秒で正しい形）。
3. Claude の容器を片付ける時期（便4）。

## 14. 審査（Architect・同じ AI による自己審査）
- 未実施。クラウドの審査に回す予定。
