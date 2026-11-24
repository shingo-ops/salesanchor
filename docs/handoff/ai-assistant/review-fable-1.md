# 設計審査 1 回目（Fable・開発ルールの確認）— AI アシスタント（秘書を まとめ役＋係 へ）

この文書は、AI アシスタントの要件・調べ・設計案の 3 つが、開発の決まりと今ある決定に合っているかを確かめた結果です。

親（仕様書）: [../../specs/secretary-chat/README.md](../../specs/secretary-chat/README.md)

## 判定: REVISE（直す必要）

理由 3 行:

1. 設計は「ADR-1058 はそのまま使う」と書きながら、頭（AI とモデル）を Hermes の部屋の設定で決める作りで、ADR-1058 の「担当の正本は DB の 1 か所」を黙って破っている。決まり帳（ADR-1077）・会社ごとの分け隔て・置き場（本番サーバーの中）にも、書かれていない食い違いがある。
2. 「呼び出しは 1 行足す形」は実物と合わない。DB の値の決まり 2 つ・sdk の対応表・容器の口の形（/intent）・頼みの本文の形が違い、移行（危険 PR）と変換の部品が要る。
3. 受け入れ基準 K1〜K8 のうち K2・K3・K6・K7・K8 は、分母・記録の名前・場所が決まっておらず ○× を一義に判定できない。標準フローの必要物（あるべき姿と KGI の PO 承認・親から子へのリンク・接触面分析・recon の 7 観点）も欠けている。

良い点（事実）: recon の file:line 13 行は全部 origin/main の実物と合った（下の §2）。「必ず成功するとは言えない」と自分で書き、便0 を止めどころにしている（docs/handoff/ai-assistant/design.md:88）。ADR-1056 の変更が要ることを隠していない（同 :83）。

## 0. 審査の対象と方法

- 審査した物: origin/release/ai-assistant-requirements（`d11438047`）の docs/handoff/ai-assistant/requirements.md（65 行）・recon.md（62 行）・design.md（118 行）。この枝の main との差はこの 3 ファイルだけ（`git diff --stat origin/main...origin/release/ai-assistant-requirements` の出力: 3 files changed, 245 insertions）。
- 照らした実物: origin/main `ed9a9f158`（2026-11-25T01:02:52+09:00）。
- 読んだ正本: AGENTS.md・CLAUDE.md・docs/STANDARD-WORKFLOW.md・docs/ai-agents/design-partner.md・docs/handoff/_templates/design.md・docs/handoff/_templates/recon.md・docs/specs/README.md・docs/specs/secretary-chat/README.md・ideal-state.md・kgi.md・docs/specs/recon-standard/kgi.md・ADR-1056・1058・1004・1077・1078・1080・1082・1087・009・091・159。
- していないこと: Hermes Agent の公式の説明書は読んでいない（外の道具を使わない指示のため）。recon.md:41-50 の Hermes の表は未確認（U1）。本番・DB には触れていない。

## 1. 開発ルール（見る点 1）

| # | 決まり | 結果 | 事実 |
|---|---|---|---|
| 1-1 | Phase 1: KGI は PO 承認が必須の関所（docs/STANDARD-WORKFLOW.md:23・:81） | × | KGI は「草案・PO 承認前」（docs/handoff/ai-assistant/design.md:60）。kgi.md が無い。計画票のステップ 0 で PO が決める形にはなっている（同 :94）ので、順番の前後として R1 で直せる |
| 1-2 | Phase 1.5: あるべき姿を先に読む・理想優先（docs/STANDARD-WORKFLOW.md:24・:35） | × | 親のあるべき姿の PO の言葉は「サーバーの中に置く」（docs/specs/secretary-chat/ideal-state.md:11）。設計は「本番 prod1 には置かない」「別サーバー」（docs/handoff/ai-assistant/design.md:33・:75）。理想と違う方へ設計しており、食い違いの記載が無い。新しい PO の言葉（docs/handoff/ai-assistant/requirements.md:7-10）はあるべき姿のファイルに写されていない |
| 1-3 | §1.8 3 段階の振り分け（docs/STANDARD-WORKFLOW.md:65-75） | △（PO 確認が要る） | recon は「既存テーマの延長」と判定（docs/handoff/ai-assistant/recon.md:21）。しかし親の境界は「AI の置き場（本番サーバー内の専用の容器）…下書きの形、『作る』で今の機能を呼ぶ流れ」（docs/specs/secretary-chat/README.md:15）。今回は係の部屋・基準の一覧の表（新しいデータ構造）・AI からの話しかけ・Discord・覚え書きを足す。「新しいデータ構造・新機能を作る開発」は仕様書が必須（docs/STANDARD-WORKFLOW.md:36）。迷う場合は PO に確認する決まり（同 :75） |
| 1-4 | §1.6 子→親のリンク・1 行説明（docs/STANDARD-WORKFLOW.md:47・:49） | ○ | docs/handoff/ai-assistant/recon.md:6・:8、design.md:6・:8 |
| 1-5 | §1.6 親→子のリンク（docs/STANDARD-WORKFLOW.md:48） | × | 親 docs/specs/secretary-chat/README.md:22-31 の子の一覧に ai-assistant が無い（枝の差分は 3 ファイルだけで親を触っていない） |
| 1-6 | §1.7 維持の仕組み欄（docs/STANDARD-WORKFLOW.md:55-63） | ○ | docs/handoff/ai-assistant/design.md:114-118。守り手「人手で守る」＋理由あり |
| 1-7 | §2 recon: file:line・既存 ADR 検索の結果（docs/STANDARD-WORKFLOW.md:82・:84） | ○（一部 L） | 引用は全部フルパス。ADR 検索の記録あり（docs/handoff/ai-assistant/recon.md:18-21）。docs/adr/FEATURE-INDEX.md を引いた記録は無い（docs/STANDARD-WORKFLOW.md:25。L1） |
| 1-8 | §2 設計: 各基準に検証方法・外部事例欄・相互参照（docs/STANDARD-WORKFLOW.md:83） | △ | 表の欄は埋まっている（docs/handoff/ai-assistant/design.md:62-71・:49-58）。ただし検証方法の中身が実行できない行がある（§4）。外部事例の出典がリポジトリの外（同 :51）で、URL も無く確かめられない（R9） |
| 1-9 | recon の 7 観点（docs/ai-agents/design-partner.md:104・docs/specs/recon-standard/kgi.md:21-33） | × | recon.md に 7 観点の見出しが無い。特に観点 6「あるべき姿との対照（一致／不足／余剰）」（docs/specs/recon-standard/kgi.md:31）と観点 5「維持の仕組み」が無い |
| 1-10 | 設計書の様式 10 点のうち「接触面分析（6 面）」（docs/ai-agents/design-partner.md:144） | × | design.md に該当の節が無い。今回は会社のデータ（④）・別サーバー（⑤）・AI 会社（⑥）・並行中の秘書の便（②）に触れるので省けない |
| 1-11 | 設計の粒度: file:line＋変更前後＋触らない範囲＋○× 基準、未決定の語を残さない（docs/STANDARD-WORKFLOW.md:115・docs/ai-agents/design-partner.md:124） | ×（草案として） | 未決 4 件（docs/handoff/ai-assistant/design.md:107-112）。便ごとの変更前後・触らない範囲が無い。作りの全体の案としては読めるが、このままでは実装カードにできない（R10） |
| 1-12 | 完了の定義・人の確かめはテナント 001（docs/STANDARD-WORKFLOW.md:98） | △ | K3・K8 の「本番の記録を数える」（docs/handoff/ai-assistant/design.md:66・:71）がどの会社の記録かの記載が無い |
| 1-13 | 様式（docs/handoff/_templates/design.md・recon.md） | ○ | 見出し（外部事例・受け入れ基準・技術 How・弊害・計画票・継続、引用表・不明点リスト・未解決ゼロ確認）は揃っている |

## 2. recon の file:line（見る点 2・全行）

origin/main `ed9a9f158` の実物と 1 行ずつ照らした。

| recon の行 | 引用 | 実物 | 結果 |
|---|---|---|---|
| :27 | backend/app/routers/assistant.py:85 | `SECRETARY_AGENT_URL = os.getenv(...)` | ○ |
| :28 | backend/app/routers/assistant.py:106 | `def agent_url(provider: str)` | ○（行は合う。「1 行足せば呼べる形」という説明は × → R3） |
| :29 | backend/app/routers/assistant.py:98 | `_SECRETARY_DEPENDENCIES = [`（4 つは :99-102） | ○ |
| :30 | backend/app/services/ai_assignment.py:33 | `async def get_ai_assignment(db, job_key)` | ○ |
| :31 | backend/app/services/ai_assignment.py:47 | `SWITCHABLE_JOB_KEYS = frozenset({"secretary_intent"})` | ○ |
| :32 | docker-compose.secretary-agent.yml:19 | `read_only: true` | ○ |
| :33 | docker-compose.secretary-agent.yml:26 | `mem_limit: 512m` | ○ |
| :34 | backend/app/discord_gateway/private_channel.py:51 | `async def create_private_text_channel(` | ○（ただし staff_role_id を渡すとスタッフのロールも見られる。同 :76-83。→ R8） |
| :35 | backend/app/routers/invoices.py:153 | `issued_at, due_date, paid_at, voided_at, void_reason,` | ○ |
| :36 | backend/app/routers/invoices.py:899 | `UPDATE invoices SET status = 'paid' ... status IN ('issued', 'overdue')` | ○ |
| :37 | backend/app/routers/invoices.py:592 | `"due_date": None` | ○ |
| :38 | backend/app/routers/dashboard.py:138 | `COUNT(*) FILTER (WHERE status IN ('issued', 'overdue')) AS unpaid_count` | ○ |
| :39 | backend/app/services/messaging_window.py:68 | `last_inbound_at: Optional[datetime],`（関数 compute_state の引数） | △ 行は実在。ただし「会話ごとに持つ」値ではなく引数。値を作っているのは backend/app/routers/meta_inbox.py:951-952（meta_messages の MAX。Meta の経路だけ）→ L2 |
| :56 | backend/app/routers/dashboard.py:138・backend/app/routers/invoices.py:1008 | 読むだけの箇所 | ○ 行は合う。「overdue に書き換える所は無い」も `status = 'overdue'` を書く行が backend・migrations・scripts の .py/.sql/.sh に 0 件で合う。ただし読む箇所は 2 つだけではない（L3） |

requirements.md の引用も確かめた: backend/app/routers/invoices.py:1106（PayPal の入金確認の説明文）○、backend/app/routers/meta_inbox.py:952（`AS last_inbound_at`）○、backend/app/routers/quotes.py 実在 ○。

recon に無い事実（今回の設計に効く）:

- 期限を過ぎた請求書の一覧の口が既にある: backend/app/routers/analytics.py:207（`/analytics/overdue-invoices`）・:219-221（`CURRENT_DATE - due_date::date` と `status IN ('issued', 'overdue')`）。「未払いの催促」の基準（recon.md:56「期日（空なら発行日）から N 日」）は、この既存の数え方と 1 か所に揃える必要がある。
- 容器の口は `/intent`（backend/app/routers/assistant.py:226）、本文は `{"text","now","model","rules"}`＋カルテ（同 :201-204）。
- provider の値の決まり: migrations/20261103_120000_create_ai_job_assignments.sql:33（`CHECK (provider IN ('gemini', 'codex', 'claude'))`）。
- sdk の値の決まり: migrations/20261117_100100_add_llm_usage_tts_characters.sql:38。provider と sdk の対応: backend/app/services/llm_budget.py:180-185。対応が無い provider は呼ばれず not_ready になる（backend/app/routers/assistant.py:288-291）。

## 3. 既存 ADR との食い違い（見る点 3）

| # | ADR の決定 | 設計の記述 | 黙って破っているか |
|---|---|---|---|
| 3-1 | ADR-1058: 担当（provider と model）の正本は DB の表 ai_job_assignments の 1 か所（docs/adr/ADR-1058-ai-job-assignments.md:16）。読むのは get_ai_assignment だけ（:17）。選択肢は migration でだけ足す（:18）。値の一覧の正本は DB の CHECK（:23） | 「係の部屋ごとに使う AI を設定で変える」（docs/handoff/ai-assistant/design.md:45）。対象 ADR 欄は「ADR-1058（AI の担当表・そのまま使う）」（同 :12） | **破っている（記載なし）**。頭の正本が DB と Hermes の設定の 2 か所になる。画面「AI の担当」（ADR-1058:25）に出るのは「hermes」だけで、実際に動いた頭と合わなくなる |
| 3-2 | ADR-1058: 仕事は 5 つ（:15）。秘書は 1 回の頼みを 1 行、provider・model つきで台帳に書く（:24） | 係ごとの費用の上限と使用の記録（docs/handoff/ai-assistant/design.md:57・:84） | 記載不足。係ごとに数えるには job_key／purpose を足す（CHECK の作り直し＝移行）か、別の列が要る。Hermes が 1 回の頼みで何回 AI を呼び、その数とトークンを返すかは未確認（U2） |
| 3-3 | ADR-1056: AI に渡すのは文と今の日時だけ・会社のデータは渡さない（docs/adr/ADR-1056-secretary-chat.md:16） | アプリが選んだ行を渡す・覚え書きを持つ（docs/handoff/ai-assistant/design.md:77・:83） | 破っていない（:83 で新しい ADR を起案すると明記） |
| 3-4 | ADR-1056: 本番サーバーに専用の容器を置く（:15）。backnet に入れない・read_only・cap_drop ALL・mem_limit 512m・同時 1 本・80 秒（:19） | 別サーバー（docs/handoff/ai-assistant/design.md:33・:75）。覚え書きを持つので書き込める置き場になる | **記載なし**。§5 の「ADR-1056 の変更」（同 :83）に置き場と容器の守りの変更が入っていない |
| 3-5 | ADR-1056: 作成は、画面が今の POST /invoices・POST /calendar/events を利用者本人のログインで呼ぶ。新しい書き込みの道を作らない（:18・:27） | Discord の部屋で「はい」→「アプリが作る・送る」（docs/handoff/ai-assistant/design.md:39・:99）。催促をお客様に送る（同 :71） | **記載なし**。Discord の「はい」は本人のログインの画面を通らない。backend が代わりに作る道・お客様へ送る道は新しい書き込みの道で、権限確認・監査ログの作成者・会社の文脈の扱いを決める必要がある |
| 3-6 | ADR-1056: 鍵は VPS の専用ファイルにだけ置き、置くのは PO 本人（:20）。月額契約のログインで動かす（:15） | Hermes の口の鍵・各 AI 会社の鍵の置き場・誰が置くか・月額か従量かの記載が無い | 記載なし（secrets は PO 本人の GO。AGENTS.md「不可逆操作は必ず PO 確認」） |
| 3-7 | ADR-1077（Proposed・表と口は main に実装済み: backend/app/routers/assistant.py:296・migrations/20261113_100000_create_secretary_rules.sql）: 決まりと候補は public.secretary_rules の 1 表・写しを作らない（docs/adr/ADR-1077-secretary-rulebook.md:17）。承認の判定は require_super_admin の 1 か所（:16）。会話の全文は残さない（:18）。外の置き場は「決まりの写しが外にでき、データを 1 か所に置く方針に反する」ので採らない（:36） | 共通の決まりの文書・係ごとの人格の文書と手順書・覚え書きを Hermes の側に置き、許可は write_approval（docs/handoff/ai-assistant/design.md:46-47） | **破っている（記載なし）**。「人が承認してから効かせる決まり」の置き場が DB の表と Hermes のファイルの 2 つになる。design.md の対象 ADR 欄に 1077 が無い（同 :12）。PO の言葉「配線とDBのSSOTは遵守してデータを分散させることは禁止」（docs/specs/secretary-chat/ideal-state.md:19）にも当たる |
| 3-8 | ADR-1078（Proposed・実装済み: backend/app/routers/assistant.py:58・:300-345）: 次に聞く欄は AI でなく backend の関数が決める（docs/adr/ADR-1078-secretary-event-karte.md:16）。カルテは保存しない（:19） | 予定係が下書きを返す（docs/handoff/ai-assistant/design.md:36-37）。カルテ・決まりを Hermes にどう渡すかの記載が無い | 記載なし。担当表で hermes に切り替えた時点で、今の口は決まり（rules）とカルテを本文に載せて送る（backend/app/routers/assistant.py:201-204）。Hermes がこれを受けて同じ形（secretary-agent/schema.json）で返すかが決まっていない |
| 3-9 | ADR-1080・1082・1087: 声の読み上げ・聞き取り・「声で会話」は今の POST /api/v1/assistant/messages の返事を使う（docs/adr/ADR-1082-secretary-voice-input.md:19・docs/adr/ADR-1087-secretary-live-voice.md:16）。今の秘書の返事は 5〜8 秒（ADR-1087:41） | K5 は 30 秒以内（docs/handoff/ai-assistant/design.md:68） | 破ってはいないが、切り替えると声の会話の待ち時間が 5〜8 秒から最大 30 秒に伸びる。弊害欄に無い |
| 3-10 | ADR-1004: 台帳は 1 行＝応答 1 回（docs/adr/ADR-1004-llm-usage-ledger.md:25）。費用の式は 1 か所（:27） | 「使用の記録（ADR-1004）に載せる」（docs/handoff/ai-assistant/design.md:57） | 記載不足。まとめ役＋係で応答が 2 回以上になる。1 行にまとめるか応答ごとに書くかが無い。design.md の対象 ADR 欄に 1004 が無い |
| 3-11 | ADR-091: Bot の担当業務は 9 項目（docs/adr/ADR-091-discord-bot-scope-definition.md:24-42）。方針「担当者は Sales Anchor アプリで完結」（:49） | Discord の非公開の部屋でアシスタントと話す（docs/handoff/ai-assistant/design.md:99） | 記載不足。9 項目に無い 10 個目の業務になる。PO の決定（Q2）が根拠なので、ADR-091 の範囲表を改める点として書く必要がある |
| 3-12 | ADR-159: お客様への Discord の返信は担当者の名前で送り、Bot 名義では一切送らない（docs/adr/ADR-159-staff-identity-on-discord.md:30） | 返信係は「以降」（docs/handoff/ai-assistant/design.md:100） | 今回の便の範囲外。返信係の設計のときに守る決まりとして持ち越しに書く（L4） |
| 3-13 | ADR-009: 受信は MESSAGE_CREATE → DB 書き込み（docs/adr/ADR-009-discord-gateway.md:28） | しんごさんの部屋の発言の扱いの記載が無い | 未確認（U5）。チケットの部屋では bot と webhook の投稿は飛ばす（backend/app/discord_gateway/ticket_channel_writer.py:200）が、しんごさんの発言がお客様の受信箱に入らない作りの確かめが無い |

会社ごとの分け隔て（ADR-1056 の芯）: PO の言葉は「004のAIは他のテナントに干渉できない、001も001以外のデータには干渉できない」（docs/specs/secretary-chat/ideal-state.md:11）、KGI K4 は「ほかの会社の情報に触れた件数 0」（docs/specs/secretary-chat/kgi.md:22）。今の秘書は AI が何も持たないのでこれが作りの上で成り立つ（docs/adr/ADR-1056-secretary-chat.md:26）。設計は Hermes に覚え書きと会話を持たせ、会社のデータも渡すが、会社ごとに部屋・覚え書き・会話を分ける記載が design.md に 1 行も無い。**これが最も重い欠け**（R4）。

## 4. 受け入れ基準 K1〜K8（見る点 4）

| 基準 | ○× で判定できるか | 検証方法を実行できるか | 足りないもの |
|---|---|---|---|
| K1 振り分け 95/100 | ○（台本が決まれば） | ×（今は） | 台本（頼み 100 件と正解の表）の置き場・誰が作り誰が正解を認めるか。係が 2 つだけだと当てやすいので「どの係でもない」頼みの件数。試しの場所（どの機械・どの鍵・誰が払うか）。既にある試しの束（docs/handoff/secretary-rulebook/baseline.md）を使うかどうか |
| K2 形 100/100 | × | × | 括弧書き「形が違えばアプリが捨てる」のため、合格が「Hermes が 100 件とも正しい形を返す」か「アプリが 100 件とも検査する」かが 2 通りに読める。形の正本（secretary-agent/schema.json か新しい形か）の指定が無い。便0 にはアプリが無い |
| K3 「はい」なしの書き込み 0 | × | △ | 「本番の記録」の名前が無い（監査ログの作成者か・どの表か）。Discord の「はい」のとき作成者が誰になるかが未定（3-5）。Q3 で任せた仕事は「はい」なしで動くので、「承認制の仕事では」の限定が要る |
| K4 道具 0 個 | ○ | △ | 一覧を出すだけでなく、実際に試して失敗すること（今の K4 と同じ「接続試験が失敗する」docs/specs/secretary-chat/kgi.md:22）。便1 の「CI の検査」は、Hermes の設定がリポジトリに無ければ CI から見えない。設定ファイルの置き場の指定が要る。振り分け自体が道具の 1 つなら「0 個」と両立しない（U3） |
| K5 30 秒以内 90/100 | ○ | ○（便0 で） | 今の 5〜8 秒（ADR-1087:41）より遅い線を合格とする理由。backend の打ち切りは 85 秒（backend/app/routers/assistant.py:87） |
| K6 メモリ 50% 以下 | × | × | 分母（置き場の大きさ）が未定（docs/handoff/ai-assistant/design.md:75 で「便0 の数字で PO が決める」）。分母が決まらないと割合が出ない。GB の絶対値で書く |
| K7 割合が画面で見られる | × | × | どの画面か・「直さずに はい」の数え方（下書きと作った物の差をどこで比べ、どの表に残すか）・Playwright の試験の名前が無い |
| K8 催促 1 日以内 100% | × | × | 基準の数字（N 日）と期日が空のときの扱いが案のまま（recon.md:56）。「しんごさんへ聞く」場所が未定（便2 の時点で Discord は無い。アプリの窓は開かないと見えない）。同じ請求書を何回聞くか。「本番の記録」の名前とどの会社か |

基準が無い要件（PO の言葉・決定にあるのに K が無い）:

- 頭の付け替えと比べること（docs/handoff/ai-assistant/requirements.md:9）
- 基準の数字と止める／動かすを画面で直す（同 :36・Q4c）
- Discord の部屋で話せる・お客様の部屋では動かない（同 :32・:59）
- 覚える前に「はい」を取る（docs/handoff/ai-assistant/design.md:47）
- 会社ごとの分け隔て（§3 の末尾）
- 費用の上限で止まる（docs/handoff/ai-assistant/design.md:84）
- 戻し方（担当表を戻すと今の秘書に戻る。同 :43）

## 5. 「必ず成功する」の根拠（見る点 5）

事実: 今の文書では「必ず成功する」とは言えない。設計も自分でそう書いている（docs/handoff/ai-assistant/design.md:88）。根拠が揃っているのは今のアプリの側（§2 の 13 行）だけで、Hermes の側は実物の確かめが 0 件（recon.md:58・:62 の未解決 2・3）。

言えるようにするために要るもの:

| # | 要るもの | 今の状態 |
|---|---|---|
| E1 | 使う Hermes の版の番号と、その版の説明書の写し（リポジトリの中・取得日つき） | 版の記載なし。写しは「2026-11-24 取得の写し」とあるが場所が無い（recon.md:46・:50） |
| E2 | 外から話しかける口（HTTP）経由で、まとめ役→係の振り分けが動く実測 | 未確認（U3） |
| E3 | 道具を全部切った状態で振り分けと下書きが動く実測 | 未解決（recon.md:58） |
| E4 | 返事を決まった形（JSON）に固定でき、係の答えをまとめ役が書き直さずに返せる実測 | 未確認（design.md:54 は方針だけ） |
| E5 | 覚え書きの許可待ちを、SA の画面から「はい」で通せるか（Hermes からアプリへは呼ばない前提で。design.md:76） | 未確認（U4） |
| E6 | 会社ごとに覚え書き・会話が混ざらない実測（001 で覚えたことが 004 で出ない） | 設計に無い |
| E7 | メモリ・速さ・1 回の頼みの AI の呼び出し回数と費用の実測 | 便0 で測る予定（K5・K6）。費用は基準に無い |
| E8 | 外部事例 6 件の出典（URL・取得日）をリポジトリの中に | リポジトリの外（design.md:51）。数字を確かめられない |
| E9 | 便0 の結果で止める線（どの K がいくつなら止めるか）を PO が先に承認 | 「どれかが届かなければ止める」（design.md:88）。K の PO 承認が前（1-1） |

## 6. PO の決定との食い違い（見る点 6）

| 決定（requirements.md §3） | 設計 | 結果 |
|---|---|---|
| Q1: しんごさんだけで始め、あとで社員へ。「社員に広げる道は設計で用意だけする」（:31） | 広げる道の記載が無い（権限・人ごとの覚え書き・会社ごとの部屋） | **食い違い（欠け）** → R4・R6 |
| Q2: アプリの窓と Discord の両方。Hermes 自身の Discord 接続は使わない（AI の解釈。:32） | 便3（design.md:99）。Hermes の Discord 接続を使わないことの明記は無い（:76「Hermes からアプリへは何も呼ばない」だけ） | 方向は合う。明記が要る → R8 |
| Q3: 最初は全部承認。数字を記録し、基準を超えた仕事だけ PO が決めて任せる。間違いが出たら承認に戻す（:33） | K3・K7・§7（design.md:66・:70・:104） | 合う。任せる基準の数字と、任せた後の K3 の読み方が無い → R7 |
| Q4〜Q4b: 基準ごとにその都度話しかける。アプリが見張る（:34-35） | 見張りはアプリの定期の仕事（design.md:78） | 合う。話しかける場所が未定 → R7（K8） |
| Q4c: 数字の変更と止める／動かすは画面で PO。新しい種類は開発が足す（:36） | design.md:24・:78 | 合う。受け入れ基準が無い → R7 |
| Q5-pre: 「1で検討、Fableに開発ルールも確認して…事実ベースで確実に成功するエビデンスを確立してくれ」（:37） | 2 段・部署は名札（design.md:25・:44） | 合う。「検討」の語を残している点も正しい。「確実に成功するエビデンス」は §5 のとおりまだ無い |
| Q5: 最初の係（未。:38） | 便0 は予定係＋請求書係で組む（design.md:95）。未決に記載（同 :109） | 食い違いではないが、ステップ 0 の PO の決定事項に Q5 が入っていない（同 :94）→ L5 |
| 始まりの言葉「共通のmd…それぞれ専属のエージェント」（:8） | design.md:46 | 合う。ただし置き場が ADR-1077 と重なる（3-7） |
| 始まりの言葉「どのボットでも付け替えが出来る構造にしてABテスト」（:9） | design.md:45 | 方向は合う。作りが ADR-1058 と食い違う（3-1） |

## 7. 直す点（REVISE）

| # | どのファイルのどこを | どう直すか |
|---|---|---|
| R1 | docs/specs/ の新しいフォルダ（または docs/specs/secretary-chat/）と docs/specs/README.md:83 の近く | 振り分け（新規テーマか延長か）を PO に 1 件として聞いて決める（docs/STANDARD-WORKFLOW.md:75）。審査役の見立ては「新規テーマ」（1-3 の事実から。見立てであり決定ではない）。新規なら README.md・ideal-state.md（requirements.md:7-10 と §3 の PO の原文を写す）・kgi.md の 3 ファイルを作り、索引に「いつ読むか」つきで 1 行足す。延長なら docs/specs/secretary-chat/README.md:22-31 の子の一覧に 3 ファイルを足し、ideal-state.md に PO の新しい言葉（置き場を別サーバーにしてよいかを含む）を PO の言葉で足す。どちらでも K1〜K8 は kgi.md に移し、PO 承認の日付を入れてから便0 のカードを出す |
| R2 | docs/handoff/ai-assistant/design.md:12（対象 ADR）と :45（頭の付け替え）、§5 | ADR-1058 との関係を書き直す。次のどちらかを選んで PO に聞く: (a) 係ごとの頭も DB の担当表を正本にし（job_key を係ごとに足す移行）、backend が呼ぶたびに provider・model を Hermes へ渡す。Hermes の設定には頭を書かない。(b) 正本を Hermes の設定に移すと決め、ADR-1058:16-18・:23 を改める ADR を起案する。どちらの場合も「実際に動いた頭」（recon.md:48 の route）を台帳の行に書く形と、画面「AI の担当」の見せ方を書く |
| R3 | docs/handoff/ai-assistant/design.md:43 と recon.md:28 | 「1 行足す形」を消し、要る変更を全部書く: ① provider の CHECK を広げる移行（migrations/20261103_120000_create_ai_job_assignments.sql:33）と選択肢の行（ADR-1058:18）② sdk の CHECK（migrations/20261117_100100_add_llm_usage_tts_characters.sql:38）と対応表（backend/app/services/llm_budget.py:180）③ 口の形の違い（今は `/intent` に独自の本文。backend/app/routers/assistant.py:201・:226。Hermes は鍵つきの OpenAI 互換の口。recon.md:45）を埋める変換の置き場 ④ 決まり（rules）とカルテの渡し方・返す形（secretary-agent/schema.json）。①② は移行を含む危険 PR で、GO まで main に入れない（AGENTS.md「ブランチと作業場所」）ことを計画票に書く |
| R4 | docs/handoff/ai-assistant/design.md §1・§4 に節を足す、§3 に基準を足す | 会社ごとの分け隔てを設計する: 会社（とあとで人）ごとに Hermes の部屋・覚え書き・会話をどう分けるか、アプリが渡す材料に会社の印をどう付け、返事を別の会社へ出さない確かめをどこで行うか。基準「001 で覚えさせた語が 004 の返事に出る件数 0（試し 10 問ずつ）」を足す。根拠は docs/specs/secretary-chat/ideal-state.md:11・kgi.md:22 |
| R5 | docs/handoff/ai-assistant/design.md:46-47・:83、対象 ADR 欄 :12 | ADR-1077・1078・1004・091 を対象 ADR に足し、改める点を 1 つずつ書く: ① 決まりの置き場を 1 か所にする（DB の secretary_rules を正本にして毎回渡すか、Hermes の覚え書きに移して ADR-1077:17・:36 を改めるか）② 共通の決まりの文書・係の人格の文書・手順書の正本の置き場（リポジトリか DB か Hermes のファイルか）と変えた記録 ③ カルテ（ADR-1078:16・:19）を Hermes の係でどう保つか ④ 台帳の 1 行の単位（ADR-1004:25）⑤ Discord の 10 個目の業務（ADR-091:24-42）。新しい ADR の案（Proposed）を同じ枝に置く |
| R6 | docs/handoff/ai-assistant/design.md:83（ADR-1056 の変更）と §4 | 書かれていない変更を足す: ① 置き場が本番サーバーの外になること（ADR-1056:15。あるべき姿 ideal-state.md:11 の PO の言葉とも違うので PO の言葉で決め直す）② 容器の守り（read_only ほか。ADR-1056:19）のうち何を保ち何を変えるか ③ 「はい」の後に backend が作る・送る新しい道（ADR-1056:18・:27）の権限確認・監査ログの作成者・会社の文脈 ④ 鍵の種類・置き場・置く人（ADR-1056:20）と、月額か従量か ⑤ 社員に広げる道（Q1。ADR-1056:38 の「広げる前に新しい権限キーに置き換える」を含む） |
| R7 | docs/handoff/ai-assistant/design.md:62-71（§3 の表） | §4 の表の「足りないもの」を埋めて、K2・K3・K6・K7・K8 を一義に直す。例: K2「便0 の台本 100 件の返事のうち、secretary-agent/schema.json の検査を通った件数 100」／K6「まとめ役＋係 2 部屋で、測った最大のメモリが ○GB 以下」／K8「基準に当たってから 24 時間以内に、○○（場所）に問いが 1 件出た請求書の数 ÷ 当たった請求書の数 = 1。記録は ○○ 表」。§4 の末尾の 7 つの要件に基準を足す。試験のファイル名・Playwright の名前・記録の表の名前を入れる。人の確かめはテナント 001（docs/STANDARD-WORKFLOW.md:98） |
| R8 | docs/handoff/ai-assistant/design.md:99（便3）と §4 | Discord の作りを書く: ① Hermes 自身の Discord 接続は使わない（Q2）② 部屋は create_private_text_channel を staff_role_id なし・extra_view_role_ids 空で作る（スタッフのロールを渡すと見える。backend/app/discord_gateway/private_channel.py:76-98）③ しんごさんの発言を受信箱に入れない・アシスタントの部屋だと見分ける印の置き場 ④ お客様の部屋では動かない確かめ（requirements.md:59）⑤ 「はい」を言った人が本人かの確かめ（Discord の番号とアプリの人の結び付け）。便3 の受け入れ基準を §3 に足す |
| R9 | docs/handoff/ai-assistant/ に research.md を足す、design.md:51、recon.md:41-50 | リポジトリの外のファイル（/tmp/CC報告ファイル/…）への参照をやめ、外部事例 6 件の出典（URL・取得日・引いた数字の場所）と、Hermes の説明書の写し（版の番号・取得日・該当の文）を research.md に置く。recon.md の Hermes の表の「出典」をそこへのリンクにする。使う版を 1 つに固定して書く（design.md:86 の「版を固定」の中身） |
| R10 | docs/handoff/ai-assistant/recon.md と design.md | ① recon に 7 観点の見出しを足し、観点 6 の対照表（あるべき姿の各項目 ↔ 現状の一致／不足／余剰）を書く（docs/specs/recon-standard/kgi.md:21-33）② design に「接触面分析（6 面）」を足す（docs/ai-agents/design-partner.md:144）③ この design は「作りの全体の案」であり、便ごとに file:line＋変更前後＋触らない範囲の設計とカードを別に作る、と計画票に明記する（docs/STANDARD-WORKFLOW.md:115）④ 便0 の「試し用の場所」を具体にする（どの機械・本番と同じネットワークに入れない・鍵は誰が置く・終わったら消す手順） |

## 8. 軽い指摘

| # | 場所 | 内容 |
|---|---|---|
| L1 | docs/handoff/ai-assistant/recon.md:20 | docs/adr/FEATURE-INDEX.md を引いた結果を 1 行足す（docs/STANDARD-WORKFLOW.md:25）。関連の ADR-1003（secrets）・ADR-135・136（危険 PR の GO）・ADR-072（会社の文脈）・ADR-101（請求書）も対象に入れる |
| L2 | docs/handoff/ai-assistant/recon.md:39・requirements.md:52 | messaging_window.py:68 は引数。「会話ごとに持っている」ではなく「Meta の経路で、meta_messages から数えて出している（backend/app/routers/meta_inbox.py:951-952）」に直す |
| L3 | docs/handoff/ai-assistant/recon.md:56 | overdue を読む箇所は 2 つではない（backend/app/routers/invoices.py:1053・:1120・:1147、backend/app/routers/integrations.py:782・:801・:937・:950、backend/app/routers/analytics.py:221 ほか）。「読む箇所の例」と書くか全部挙げる。analytics.py:207 の既存の口を引用表に足す |
| L4 | docs/handoff/ai-assistant/design.md:100 | 返信係への持ち越しに「お客様への Discord の返信は Bot 名義で送らない（ADR-159:30）」を足す |
| L5 | docs/handoff/ai-assistant/design.md:94 | ステップ 0 の PO の決定に Q5（最初の係）と費用の上限を入れる（便0 が予定係＋請求書係を前提にしているため） |
| L6 | docs/handoff/ai-assistant/design.md:65 | まだ無いファイル（backend/tests/test_assistant_hermes.py）をバッククォートで囲んでいる。文書の頭の決まり（同 :1-3）に合わせて外す |
| L7 | docs/handoff/ai-assistant/design.md:85 | 「ADR-1087 が 2026-11-25 にマージ」とあるが、main の先頭は PR #5738（release/secretary-voice-mode）で、ADR-1087 の状態は Proposed（草案）のまま（docs/adr/ADR-1087-secretary-live-voice.md:5）。「声で会話（ADR-1082 の 2026-11-24 追記）の便がマージ」と書くのが事実に合う（推測: PR の中身は読んでいない。枝の名前と ADR の状態からの見立て） |
| L8 | docs/handoff/ai-assistant/requirements.md:1-3 | 親へのリンクと 1 行説明が無い（recon・design ではないので必須ではないが、揃えると辿りやすい） |
| L9 | docs/handoff/ai-assistant/requirements.md:65・recon.md:60 | 「ChatGPT の箱が本番で動いているか」は未確認とあるが、ADR-1087 には「今の秘書の文の AI は ChatGPT（codex）」の記録がある（docs/adr/ADR-1087-secretary-live-voice.md:46）。この記録を引くか、食い違うなら確かめる |
| L10 | docs/handoff/ai-assistant/design.md:68 | 30 秒の線は今の 5〜8 秒より遅い。声の会話への影響を弊害欄に足す（3-9） |

## 9. 未確認

| # | 未確認のこと | 確かめ方 |
|---|---|---|
| U1 | recon.md:41-50 の Hermes Agent の 6 行（HTTP の口・部屋ごとの設定・profile_routes・route が返る・追加部品が無いと止まる・write_approval）。審査役は公式の説明書を読んでいない | R9 の写しをリポジトリに置き、次の審査で照らす。便0 の実測 |
| U2 | Hermes が 1 回の頼みで AI を何回呼ぶか、トークン数と費用を口の返事で返すか | 便0 で返事の生の形を記録する |
| U3 | 外から話しかける口（HTTP）経由でも係への振り分けが動くか。道具を全部切ると振り分け（これ自体が道具の可能性。推測）も切れないか | 便0 |
| U4 | 覚え書きの許可待ちを外の画面（SA）から通す口があるか | 説明書の写し＋便0 |
| U5 | しんごさんの部屋の発言を今の Discord の受信（backend/app/discord_gateway/）がどう扱うか。チケットの部屋として登録されていなければ受信箱に入らないかは、審査役は process_ticket_channel_message の頭（backend/app/discord_gateway/ticket_channel_writer.py:148・:200）しか読んでいない | 便3 の recon で file:line を出す |
| U6 | 「prod1 は 4GB」（recon.md:57・design.md:75）の根拠。recon に file:line も実測も無い | 根拠の文書か実測の出力を recon に足す |
| U7 | 外部事例 6 件の数字（17.2 倍・4.4 倍・約 50%・41〜86.7%・+9.4%・90.2%・約 15 倍。design.md:53-58） | R9 の research.md の出典で照らす |
| U8 | 各 AI 会社のデータの扱いの約束（requirements.md:64）。親の境界には「AI 会社との契約の約束の調査（PO 禁止 2026-11-01）」がある（docs/specs/secretary-chat/README.md:16）。今回、会社のデータを AI 会社へ送る（design.md:77）にあたり、調べるか調べないかは PO の決定が要る | PO に 1 件として聞く |
| U9 | Hermes の使用の許諾（ライセンス）と、会社のサーバーで動かしてよいか | R9 の写しに入れる |
