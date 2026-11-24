# 設計審査 1回目 — 審査役（Claude Opus・手元）

対象: commit d11438047 の requirements.md・recon.md・design.md（第1版 草案）。審査日 2026-11-25。読み取りだけ。

審査の結果は REVISE（直してから再審査）です。秘書の作り替え案（commit d11438047）を、ファイルを書き換えずに読み取りだけで確かめました。

理由は3つです。
- 設計の柱が、すでに決まっている ADR-1058・ADR-1077・ADR-1078・ADR-1056 と食い違っていて、その食い違いが「変える点」として書かれていません。
- 「Hermes に道具を渡さない」「係ごとに覚え書きを持つ」「下書きはまとめ役が書き直さずアプリへ渡す」の3点は、Hermes の公式説明書で確かめると、そのままでは成り立たないか、確かめられない部分があります。
- 受け入れ基準 K1〜K8 には、○×で決められないもの、今の秘書より緩いものが入っています。

「必ず成功する」と言える根拠はまだ揃っていません。

対象: `/Users/tanizawashingo/worktrees/salesanchor/release-ai-assistant-requirements/docs/handoff/ai-assistant/{requirements,recon,design}.md`

---

## 1. 指摘の一覧（必須）

**M1　ADR-1058（AI の担当表）の「正本は DB の1か所」を破る**
- 【事実】ADR-1058 の決まり:
  - `docs/adr/ADR-1058-ai-job-assignments.md:16`「仕事ごとの担当（provider と model）の正本は DB の public の表 `ai_job_assignments` の1か所」
  - 同 `:18`「選択肢は migration でだけ足す」
  - 同 `:23`「値の一覧の正本は DB の CHECK」
- 【事実】一方で design は、係の部屋ごとに頭を Hermes 側の設定で替える作りです（`design.md:45`）。頭の決め場所が DB と Hermes の2か所に割れますが、改める点として書かれていません。
- 【事実】`design.md:43` は「`agent_url()` に1行足す」「戻すのは担当表を戻すだけ」としています。しかし provider の値は DB で縛られています（`migrations/20261103_120000_create_ai_job_assignments.sql:33` `CHECK (provider IN ('gemini', 'codex', 'claude'))`）。
  - sdk の値も同じ migration の `:175`（CHECK）と `backend/app/services/llm_budget.py:180`（`USAGE_SDKS_BY_PROVIDER`）で決まっています。
  - つまり「hermes」を足すには migration が要ります。migration は危ない変更として PO の GO が要る扱いです（ADR-135/136）。
- 直し方: どちらにするかを ADR 案として書く。
  - (a) 係ごとの頭も `ai_job_assignments` を正本にし、アプリが Hermes に頭を指定する。Hermes の口は1回ごとに `model`・`provider` を受け付けます（Context7 api-server.md）。ただし振られた係でこれが効くかは未確認です。
  - (b) ADR-1058 を改める。
  - あわせて、migration の段と GO を計画票（`design.md:90-100`）に入れる。

**M2　ADR-1077（決まり帳）・ADR-1078（予定のカルテ）と矛盾する**
- 【事実】決まり帳の決まり:
  - `docs/adr/ADR-1077-secretary-rulebook.md:17`「決まりと候補は `public.secretary_rules` の 1 表…写しを作らない」
  - 同 `:18`「会話の全文は残さない」
  - 同 `:36`「別のベクトル DB は採らない（決まりの写しが外にでき…方針に反する）」
- 【事実】予定のカルテの決まり: `docs/adr/ADR-1078-secretary-event-karte.md:19`「保存しない。窓を閉じたら消える」。
- 【事実】一方で design は、Hermes の覚え書き・手順書・人格の文書を「覚える仕組み」にしています（`design.md:46-47`）。requirements にも部屋ごとに「会話」を持つと書かれています（`requirements.md:25`）。決まりの写しと会話が DB の外にできます。
- 【事実】design の対象 ADR（`design.md:12`）に ADR-1077/1078/1080/1082/1087 がありません。recon にも名前が並ぶだけで（`recon.md:13`）、中身を突き合わせた欄がありません。
- 直し方: 決まり帳を正本のまま残し、Hermes の覚え書きは切る（`memory_enabled: false`・`user_profile_enabled: false`）か、ADR-1077 の改めとして PO に決めてもらう。カルテの状態をどう受け渡すかも書く。

**M3　「Hermes に道具を渡さない」が、振り分けの機能と両立しない**
- 【事実】Context7 で確かめた公式の決まり:
  - 振られた係は、まとめ役の道具一式をそのまま引き継ぐ（delegation.md「Subagents inherit the parent's enabled toolsets」）。
  - 振り分けそのものが道具 `delegate_task` で動く。
  - 係には `execute_code`（プログラムを動かす道具）が残る（delegation-patterns.md「children keep `execute_code`」）。
- 【事実】したがって、まとめ役の道具を「全部切る」（`design.md:95`）と振り分けが動きません。K4「道具 0 個」（`design.md:66`）も判定の物差しとして成り立ちません。
- 【事実】`design.md:42` は根拠を「recon『Hermes』表の行 1」としています。しかしその行は外から話しかける口の説明で（`recon.md:45`）、道具を切る話ではありません。
- 直し方: 残す道具を名指しの一覧にする（例: 振り分けだけ）。`execute_code`・端末・ファイル・ウェブを全体で止める設定の名前を書く（公式の全体で止める欄・`platform_toolsets`）。K4 を「一覧の外の道具が 0 個」に書き直す。

**M4　係ごとの覚え書き・許可の「はい」は、公式の作りでは成り立たない**
- 【事実】振られた係からは覚え書きの道具が外される（delegation.md「Hermes still strips child-blocked tools such as `clarify`, `memory`, `send_message`」）。係が自分で覚える流れは作れません。
- 【事実】覚え書き・手順書の書き込みを許すのは `/memory approve`・`/skills approve` の命令です。使えるのは Hermes 自身の操作画面（CLI）か、Hermes が自分でつないだ会話の場所だけです（memory.md・configuration.md）。
- 【未確認】アプリの画面から HTTP で許可する口があるか。
- 【事実】`design.md:47`「しんごさんの『はい』で入る」は根拠がありません。Q2 の決定「Hermes 自身の Discord 接続は使わない」（`requirements.md:32`）とも食い違います。
- 直し方: M2 とまとめて、覚え書きは切って決まり帳を使う方向に寄せる。

**M5　「下書きはまとめ役が書き直さずそのまま渡す」「どの頭で動いたかを記録する」の作りが書かれていない**
- 【事実】`route`（どの部屋・どの頭で動いたか）が入るのは `delegate_task` の結果です（delegation-provider-plugin.md）。それを受け取るのは、まとめ役の AI です。
- 【未確認】外から呼ぶ口の返事（`/v1/chat/completions`）に、係の答えをそのままの形で、`route` 付きで出す方法があるか。
- 【推測】まとめ役の AI が最後の文を作り直すなら、事例 2（`design.md:54`）の「書き直さない」は守れません。頭の比べ（A/B）の記録も、AI の申告を信じることになります。
- 直し方の案: 公式の口は `/p/<profile>/` の付け方で部屋を指定して呼べます（api_server.py の profile_prefix_middleware）。アプリが係の部屋を直接呼ぶ道を便0 で比べる。どの部屋を呼んだかはアプリが記録し、AI の申告に頼らない。

**M6　PO の決定「本番サーバーの中に置く」を断りなく変えている**
- 【事実】PO の言葉の正本: `docs/specs/secretary-chat/ideal-state.md:11`「サーバーの中に置くが安全面も考慮する」。同じ決定が `docs/adr/ADR-1056-secretary-chat.md:5`・`:15` にもあります。
- 【事実】design は「本番 prod1 には置かない」「別のサーバーを借りる」としています（`design.md:75`）。しかし改める点（`design.md:83`）に載っていません。
- 【事実】STANDARD-WORKFLOW §1.5（`docs/STANDARD-WORKFLOW.md:34-35`）とあるべき姿の決まり（`docs/ai-agents/design-partner.md:120`）では、PO の言葉（あるべき姿）の書き換えは PO だけです。
- 【事実】「prod1 は 4GB で置かない方針」（`recon.md:57`）には file:line の根拠がありません。4GB という数は `docs/adr/ADR-081-monitoring-vps-final-operational-design.md:168` にありますが、「置かない方針」の出どころは見当たりません。
- 直し方: 置き場の変更を ADR 案の改める点に足し、PO が決めてからあるべき姿に足す。

**M7　PO が禁じた調べを「未確認」に挙げている**
- 【事実】`requirements.md:64` が「各 AI 会社のデータの扱いの約束」を未確認に挙げています。
- 【事実】PO は 2026-11-01 にこの調べを禁止しています（`docs/specs/secretary-chat/ideal-state.md:11`「（１）…→禁止」、`docs/specs/secretary-chat/README.md:16`「AI 会社との契約の約束の調査（PO 禁止 2026-11-01）」）。
- 【事実】それでも今回は、本番の会社（tenant_004）の請求書の行を外の AI に渡す作りです（`design.md:77`）。
- 直し方: 禁止を外すか、データを渡すこと自体を進めてよいかを PO に1件で聞く。

**M8　受け入れ基準（K1〜K8）が ○× で決まらない、または今より緩い**
- 【事実】今の秘書の実測（`docs/handoff/secretary-rulebook/baseline.md:26`・`:36`）:
  - 種類の当たりは 69/69。
  - 1件の秒数は真ん中 5.12 秒・最長 7.86 秒。
  - 試しの頼みは `backend/app/assistant_regression/cases.json` に既にあります。
- 【事実】これに対し、K1 は 95/100、K5 は 30 秒以内が 90/100 です（`design.md:64`・`:68`）。今より悪くても合格になります。今の試しの頼みも使っていません。
- 【事実】基準ごとの問題（`design.md:64-71`）:
  - K2: どの決まった形か（今の5種類・カルテ付き）が書かれていない。
  - K3: 30 日の数え方（どの記録をどう数えるか）が書かれていない。
  - K4: M3 のとおり成り立たない。
  - K6: 「置き場」の大きさが決まっていない。
  - K7:「画面で見られる」は抽象語で、粒度の決まり（`docs/STANDARD-WORKFLOW.md:107-108`）に反する。
  - K8: 何日で催促するかの数が未決（`recon.md:56`）なので判定できない。
- 直し方:
  - K1・K2・K5 は `cases.json` を使い、「今の秘書の実測以上」を線にする。
  - K3 は数える方法（監査の記録の作った人と、「はい」の記録の突き合わせ）を書く。
  - K7 は画面の名前・出す数・計算の式を書く。
  - K8 は N を決めてから載せる。

**M9　様式が足りない**
- 【事実】接触面分析（6面）の欄がありません。様式の正本は `docs/ai-agents/design-partner.md:146`（同書 §5 の10番目の欄）です。
- 【事実】recon に、調べの正本の7観点（`docs/specs/recon-standard/`）の欄がありません。決まりは `docs/ai-agents/design-partner.md:104` です。
- 【事実】設計に「file:line＋変更前後のコード＋触らない範囲」がありません。決まりは `docs/STANDARD-WORKFLOW.md:115`・`docs/ai-agents/design-partner.md:124` です。
- 【事実】親子リンクが片方だけです。親の `docs/specs/secretary-chat/README.md:22-31` の「ぶら下がる文書」に ai-assistant が載っていません（決まりは `docs/STANDARD-WORKFLOW.md:48`）。
- 【事実】ADR の検索に FEATURE-INDEX を引いた記録がありません（`recon.md:20` は `docs/specs/README.md` だけ）。決まりは `docs/STANDARD-WORKFLOW.md:25` です。なお FEATURE-INDEX の `:79` を引けば、秘書の ADR 一式が出ます。
- 直し方: 上の各欄を足す。草案の段階なので「未決」が残るのはよいですが、`design-partner.md:124` により実装カードを出す前には消すこと。

---

## 2. 指摘の一覧（推奨）

- **R1　開発記録の区分を PO に確かめる。**
  - 【事実】`recon.md:21` は本件を「既存の延長」としています。
  - 【事実】しかし外のサーバー、新しい表（基準の一覧）、AI から話しかける仕組みを含みます。区分の表（`docs/STANDARD-WORKFLOW.md:71`）の「新規テーマ」に当たる余地があります。
  - 直し方: 区分の決まり（`docs/STANDARD-WORKFLOW.md:75`）どおり、PO に聞く。

- **R2　Discord 担当の範囲を改める必要がある。**
  - 【事実】bot の担当業務は ADR-091 の9項目で決まっていて（`docs/adr/ADR-091-discord-bot-scope-definition.md:27-37`）、AI アシスタントとの会話は入っていません。
  - 直し方: 便3（`design.md:99`）で ADR-091 の改めを明記する。

- **R3　非公開の部屋に社員も入れる。**
  - 【事実】`backend/app/discord_gateway/private_channel.py:51` の部屋は、スタッフのロールにも見せる作りです（docstring と、同じファイル内の `staff_role_id` の扱い）。
  - 直し方: 「しんごさん専用」（`requirements.md:59`）にするなら、`staff_role_id=None` で呼ぶと設計に書く。

- **R4　費用の上限の仕組みが書かれていない。**
  - 【事実】`design.md:84` は「超えたら止めて知らせる」とあるだけです。
  - 【未確認】Hermes の返事に、振られた係の分も含めて使った量が入るか。
  - 【事実】使用の記録（ADR-1058）は今、月額契約として `cost_usd` を NULL にしています（`docs/adr/ADR-1058-ai-job-assignments.md:24`）。
  - 【未確認】Hermes を API キー（使った分だけ払う契約）で動かすのか。
  - 【事実】Hermes は会話のあとに、自分を直すための振り返りの処理を後ろで回します（memory.md）。その分の費用も数えていません。

- **R5　つなぎ方・鍵・便0 の置き場が書かれていない。**
  - 【事実】Hermes の口は既定で 127.0.0.1（自分のサーバーの中）だけで待ちます（environment-variables.md）。
  - 【事実】別のサーバーからつなぐ道（「外に公開しない道」`design.md:76` の中身）が書かれていません。
  - 【事実】鍵 `API_SERVER_KEY` と AI 会社の鍵の置き場所も書かれていません。秘密の値の変更は PO 本人の決定です（ADR-1003）。
  - 【事実】便0 の「試し用の場所」（`design.md:95`）がどこかも書かれていません。

- **R6　他の秘書の作業との重なり。**
  - 【事実】作業中の札に、秘書の札が40件以上あります（例: `release-secretary-voice-mode-design.md` などの `/Users/tanizawashingo/salesanchor/.claude-pipeline/active-work.d/release-secretary-*`）。
  - 【未確認】マージ前の PR との重なり。名前で探した範囲では、開いている PR は0件でした。
  - 【推測】声どうしの会話（ADR-1087）は、今の秘書の口 `POST /api/v1/assistant/messages` に頼みを流します（`docs/adr/ADR-1087-secretary-live-voice.md` What 2）。担当表を hermes に切り替えると、声の会話も Hermes に流れ、待ち時間（K5 の30秒）の影響を受けます。
  - 直し方: 弊害の欄（`design.md:85`）に足す。

- **R7　外部事例の詳しい記録がリポジトリの外にある。**
  - 【事実】詳細は `/tmp/CC報告ファイル/ai-employee-research/department-structure.md` で、ファイル自体は今ありますが、/tmp なので消えます。
  - 直し方: 他の秘書のテーマと同じく `docs/handoff/ai-assistant/research.md` に移す。前例は `docs/handoff/secretary-rulebook/research.md` です。

- **R8　会社ごとの分け方を書く。**
  - 【事実】Q1 の「あとで社員へ広げる」に対し、Hermes の覚え書き・会話は部屋ごとで、会社ごとではありません。
  - 【事実】一方、PO の決まりは「004 の AI は 004 以外に触れない」です（`docs/specs/secretary-chat/ideal-state.md:11`、`docs/specs/secretary-chat/kgi.md:22` の K4）。
  - 直し方: 広げる前に、会社ごとにどう分けるかを設計に書く。

- **R9　名前が同じ別の機能と混ざらないようにする。**
  - 【事実】`profile_routes` という名前の設定は、振り分けの追加部品の設定（`delegation.backends.profile_routes`）と、会話の場所の振り分け（`gateway.profile_routes`）の2つにあります（multi-profile-gateways.md）。
  - 直し方: design では前者だと明記する。

---

## 3. recon の file:line を全行確かめた結果

本文の引用は全部、実在する行でした（`awk 'NR==l'` で1行ずつ確かめた）。

| 引用 | 結果 |
|---|---|
| `backend/app/routers/assistant.py:85` | 合う（`SECRETARY_AGENT_URL` の既定は `http://secretary-agent:8090`） |
| `backend/app/routers/assistant.py:98` | 合う（`_SECRETARY_DEPENDENCIES`、守り4つ） |
| `backend/app/routers/assistant.py:106` | 関数はある。ただし「1行足せば呼べる」は不正確（M1。DB の CHECK と `llm_budget.py:180` も要る） |
| `backend/app/services/ai_assignment.py:33` | 合う |
| `backend/app/services/ai_assignment.py:47` | 合う |
| `docker-compose.secretary-agent.yml:19` | 合う（`read_only: true`） |
| `docker-compose.secretary-agent.yml:26` | 合う（`mem_limit: 512m`） |
| `backend/app/discord_gateway/private_channel.py:51` | 合う。ただしスタッフのロールも見られる（R3） |
| `backend/app/routers/invoices.py:153` | 合う |
| `backend/app/routers/invoices.py:899` | 合う |
| `backend/app/routers/invoices.py:592` | 合う |
| `backend/app/routers/dashboard.py:138` | 合う |
| `backend/app/services/messaging_window.py:68` | 内容がずれる。ここは関数 `compute_state` の引数で、「会話ごとに持っている」値ではない。会話ごとの値は `backend/app/routers/meta_inbox.py:952` の集計（`MAX(created_at)`）で、Meta の会話だけ。requirements の `:52` も同じずれ |
| 不明点表の `backend/app/routers/invoices.py:1008` | 合う |

Hermes の表（`recon.md:45-50`）を Context7 で照らした結果:
- 行1（外から話しかける口・鍵・既定は 127.0.0.1）: 合う。
- 行3（係の部屋へ振る機能）: 合う。
- 行5（追加部品が無いと失敗として止まる）: 合う。
- 行6（書き込みの許可待ち）: 合う。ただし M4 の制約があります。
- 行4（どの頭で動いたかが返る）: 返るのは「まとめ役の AI へ」で、アプリへ返るかは未確認（M5）。
- 行2（部屋ごとに頭・人格・手順書が別）: 合う（delegate_tool_routes.py）。出典の「2026-11-24 取得の写し」はリポジトリに無く、確かめられません。

---

## 4. 未確認の一覧

- U1: Hermes の口の返事に、係の答えをそのまま、`route` 付きで入れられるか（M5）。
- U2: 覚え書き・手順書の許可を、HTTP の口から出せるか（M4）。
- U3: 振られた係で、アプリが1回ごとに指定した頭（model・provider）が効くか（M1-a）。
- U4: 外から呼ぶ口で会話が Hermes のサーバーに保存されるか、保存を切れるか（M2）。
- U5: 返事の使った量に、振られた係の分が入るか（R4）。
- U6: 部屋の共通の文書を全員が読む作り（`requirements.md:25`）。今回の Context7 の照会では確かめていません。
- U7: Hermes をまとめ役と係2つで動かすメモリの量（`recon.md:57` と同じく、試しの便0 で測るしかない）。
- U8: 開いている PR との重なり。GitHub の一覧が 502 で失敗したため、作業の札の名前と PR 名で探した範囲だけです。

【推測】M3〜M5 は、「アプリが係の部屋を直接呼ぶ」作りにして、まとめ役の振り分けは使わない（またはアプリ側の分類で振る）と、まとめて解ける可能性があります。ただし PO の Q5-pre の決定（「まとめ役から係へ直接振る 2 段」`requirements.md:37`）を変えることになるので、PO に聞く事項です。

