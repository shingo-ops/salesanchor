<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。このPRに含まれない新しいファイルにはバッククォートを付けない。 -->
# 実装カード 段階4 便4 — 許可の後にサーバーが実行係を起こす（U1）・App の範囲の週次点検（P5）

> この文書は何か: AI 保守運用 24 時間化 段階4 の 4 便目の段取り表です。PO が直し方を許可したら、本番のサーバーがクラウドの実行係を起こします。GitHub の Claude の App が触れるリポジトリの範囲は、毎週読みます。障害が鳴ったときに調べ係を起こす道と、調べ係がコードを読む道（U2 案A）は、この便に入れません（§1「入れない」。審査 1 回目 R2）。

- 設計: `docs/handoff/ai-ops-247/stage4-design.md` §2（:40-77）・§3 U1（:78-101）・§4 U2（:103-119。この便では作らない。参考）・§5 U5（:121-127）・§13（:194-256）
- 要件: `docs/handoff/ai-ops-247/stage4-requirements.md` R4〜R6（:112-114）・B2・B3（:157-158）・O6（:171）
- 対象ADR: ADR-1012（段階4）、ADR-1052（相談係の伏せた窓）、ADR-135・ADR-136（本番 `scripts/` を含む PR の GO）
- 状態: 設計案作成済み。設計審査 1 回目は REVISE（審査の記録は枝 release/ai-ops-stage4-bin4-review1 の docs/handoff/ai-ops-247/review-architect-stage4-bin4-1.md）で、R1〜R3・L1〜L6 を直した。2 回目は REVISE（審査の記録は枝 release/ai-ops-stage4-bin4-review2 の docs/handoff/ai-ops-247/review-architect-stage4-bin4-2.md）で、R1・L1〜L6 を直した。3 回目は REVISE（審査の記録は枝 release/ai-ops-stage4-bin4-review3 の docs/handoff/ai-ops-247/review-architect-stage4-bin4-3.md）で、R1・L1〜L3 をこの版で直した。実装は未着手。PO の実装承認は未取得
- 危険便: 4a はいいえ（`backend/` のコードだけ）。4b ははい（本番 `scripts/` と prod1 の crontab・`.env`。GO #番号が要る。POの委任に基づくClaude Opus発行）。4c はいいえ（Mac の定期実行だけ）
- 実装担当: クラウドの Sonnet（RemoteTrigger の一回実行）。push して止まる。PR は Opus が作る
- 便の番号について: 要件の道のり表の順番 9（`docs/handoff/ai-ops-247/stage4-requirements.md:232`）は「便4＝許可の注記」「便5＝サーバーが起こす部品」と分けていた。PO 2026-11-24「1」で、この 2 つと P5 を 1 枚の段取り表にまとめた（4a・4b・4c）。本番の変更は 4a → 4b → 4c の順に 1 つずつ行う

## 0. 前提の事実（origin/main c3834ee5f で行番号を確かめた）

前の便の 24 時間の確かめ（2026-11-26 21:24〜21:30 JST・Opus が読み取りだけで実行。生の出力 /tmp/CC報告ファイル/ai-ops-stage4-bin3-24h/result.md）:
- 便3 の本番反映（2026-11-24 22:31 JST）から 24 時間が過ぎた（C6）。その後の本番反映 12 回はすべて成功。
- 伏せた窓の作り直しの記録は最新が 2026-11-26 03:24:27Z で ok・ビュー 586・失敗 0。ops_incidents の alertname・severity は allow、labels・annotations は mask のまま。
- 便3 の後に増えた障害記録は 1 件（BackendSseConnectionsHigh・解決済み）。直近 47 時間で、見張り対象の 5 つの箱の「不健康」は 0。
- 相談係の入口は鍵なしで 401 を返す（動いている）。鍵ありの読み取りは、この確かめでは行っていない。

記録の口（保守 API。`backend/app/routers/ops.py`）:
- 出来事の一覧 `GET /ops/events` は kind・service・since・limit（1〜100）で絞る（:359-392）。round の step では絞れない。返す列は id・incident_id・occurred_at・kind・actor・detail・alertname・service（:378-379）。
- round の形 `OpsRound` は step・n（1〜99）・at（時刻つき）が必須（:420-432）。
- 注記の口 `POST /ops/incidents/{id}/events`（:478-533）。kind は annotated・first_aid・ai の 3 つ（:463）。round は kind が ai のときだけ付けられる（:469-475）。
- round の step は start・launch_failed・kept・closed・measure・result・stop・notify_failed・suspicious の 9 つ（:420-430）。reason は 14 個（:436-451）。「許可」と「起こした」を表す値は無い。
- round を付けたときの note は 500 字まで（:42・:473-474）。detail 全体は 8000 バイトまで（:41・:493-494）。
- 注記を書いた鍵の種類は actor に残る（:526）。鍵は保守の鍵か super admin（`require_ops_reader`）。
- 全停止の状態は `GET /ops/control` の halt_all で読む（:738-755）。

出来事の表（`public.ops_incident_events`）:
- kind の決まりは `migrations/20261016_100000_create_ops_incident_tables.sql:54-55`、actor の決まりは :56-57。便2a で kind に case_report、actor に case_agent を足した（`migrations/20261113_200000_add_ops_case_report_kind.sql`）。
- detail は 8192 バイトまで（`migrations/20261016_100000_create_ops_incident_tables.sql:58`）。この便では表を変えない。

相談係の口（`backend/app/routers/ops_case.py`）:
- 札は管理者の鍵で作る `POST /ops/case/{incident_id}/ticket`（:273-305）。有効 24 時間（:50）。作り直すと上書き（:288-292）。札は応答で 1 回だけ返る（:305）。
- 鍵は 2 本。相談係の鍵 CASE_AGENT_TOKEN と管理者の鍵 CASE_ADMIN_TOKEN（:73-74）。同じ値なら両方の口を止める（:87-90）。
- 報告は 1 件に種類ごとに 1 通（便2b）。報告の本文は 32KB まで（:48）。報告を読む口は、管理者用にも相談係用にも無い（`@router` の一覧 :273・:308・:350・:392・:418・:498・:607・:674）。
- 相談係の入口 case-api では、決まった 4 つの道（:725 の読む窓・:745 の報告と申請・:765 の申請の状態・:785 の値の口）以外は 404（`nginx/nginx.conf:811-813`）。保守 API の注記の口には、相談係の入口から届かない。

サーバー側の前例（応急処置係）:
- `scripts/ops/first_aid.py` は prod1 の ubuntu の cron で毎分 1 回、flock で二重起動を防いで動く（:1-11）。鍵は prod1 の `.env` から読み、画面にもログにも出さない（:9）。全停止を読む（:141）。
- 保守 API の宛先は `https://app.salesanchor.jp/api/v1`（:34）。止めている間も印を書く（:376-378）。API の失敗は `ApiError` で抜け、本文を文面に入れない（:131-132・:393-396）。
- 動いた印を node_exporter の textfile に書き、見張り FirstAidEscalated・FirstAidStale（`monitoring/prometheus/alert_rules.yml:497-518`）が Discord に知らせる。
- cron への登録は PO の `!` 台本で行った（`docs/handoff/ai-ops-247/card-stage3-bin-g.md:1119`）。

/fire（routine を外から起こす口）:
- routine ごとの鍵を `Authorization: Bearer` に付け、`anthropic-beta: experimental-cc-routine-2026-04-01` と `anthropic-version: 2023-06-01` を付けて POST する。本文の text はそのまま文として渡る（`docs/handoff/ai-ops-247/card-stage4-bin1.md:81`。Context7 で 2026-11-13 確認）。
- 8227 字は欠けずに届いた。文は `<routine-fire-payload>` の包みの中に入り、英語の前置き 1 文が足される（設計 §13 K2 :209）。8000 字より長い文は試していない（`docs/handoff/ai-ops-247/stage4-design.md:262`）。
- 無効の routine に送ると HTTP 400「Routine is paused.」（設計 §13 K2 :209）。

調べ係の指示書と環境:
- 指示書は `docs/ai-agents/ops-incident-agent.md` §3。起こしてよい種類は 12 種（:118-120）。使う前の前提 P-1〜P-3 が揃うまで、AI を起こさない（:123-126）。
  - P-1 サーバーが起こす仕組み → この便の 4b は実行係を起こす道だけを作る。調べ係を起こす道は後の便（P-1 はそのとき「済み」にする）。
  - P-2 調べ係の環境 ops-investigate-3 にグラフの読み取りの鍵を足す → まだ。
  - P-3 グラフを読む道をクラウドから 1 回試す → まだ。
- 要件 O2「その場で直せる札は、まず直す係が処置し、直らなかったときだけ AI を起こす」・O4「急がない札は毎朝 9:00 にまとめて 1 回」（`docs/handoff/ai-ops-247/stage4-requirements.md:167-169`）。障害の札は `GET /ops/incidents` の tier で絞れる（`backend/app/routers/ops.py:297`）。調べ係を起こす道は、この 2 つを入れた形で後の便で作る。
- コードは raw.githubusercontent.com から 1 ファイルずつ読む（:134）。ops-investigate-3 には raw.githubusercontent.com と codeload.github.com のダミーの secret が入っている（`docs/handoff/ai-ops-247/card-stage4-bin1.md:57-59`）。届くことは試しで確かめた（設計 §13 P2）。調べ係を起こす便で、読む版を文で渡す形と一緒に指示書へ書く。

GitHub の App の範囲（P5）:
- 個人の導入先は API で読むと 403。組織の導入先は shingo-cc の鍵に admin:org が無く 404（設計 §13 P3 :200）。読む仕組みは今 0 件（設計 §13 P5 :202）。
- 2026-11-13 の時点で、組織は「指定したリポジトリだけ」で PO の一覧と同じ。salesanchor は個人の導入先の一覧にある（設計 §13 K3 :210）。

未確認（この便で確かめる。確かめるまで、それに頼る作業に進まない）:
- U-a prod1 の ubuntu から api.anthropic.com へ HTTPS で届くか（届かなければ止まって PO に聞く）。
- U-b prod1 の `/home/ubuntu/salesanchor/.env` に CASE_ADMIN_TOKEN が入っているか（入っていなければ止まる。新しく置くのは secret の変更）。名前だけを `grep -c '^CASE_ADMIN_TOKEN='` で数え、値は読まない。台本 3 のために、相談係の鍵 CASE_AGENT_TOKEN も同じく名前の数だけを数える（報告の口は相談係の鍵が要る。`backend/app/routers/ops_case.py:161`）。
- U-d prod1 の `/home/ubuntu/salesanchor` で `git rev-parse HEAD` が取れるか（実行係へ渡す「本番で動いている版」の取り方）。
- U-a・U-b・U-d は、§7（３）の台本 0（PO の `!`・読み取りだけ）で 4b の依頼の前に確かめる。
- U-c GitHub の App の範囲を、画面以外の道で毎週読めるか（§1 の 4c）。

## 1. 範囲

入れる:
- 4a（`backend/` のコードだけ・表は変えない）
  1. round の step に `approve`（PO の許可）・`wake`（サーバーが AI を起こす。起こす前に書く予約）・`wake_skipped`（起こさなかった）・`wake_failed`（起こせなかった）の 4 つを足す。reason に `limit`（上限）と `no_report`（使える報告が無い）を足す。`halt` は既にある
  2. `GET /ops/events` に `round_step` で絞る引数を足す（数えるため。§2 4a（２））
  3. 管理者の鍵で報告を読む口 `GET /ops/case/{incident_id}/reports` を足す。case-api には足さない。backend の口なので app と api の `/api/` からは届く（`nginx/nginx.conf:294`・:667。今の札の口と同じ。管理者の鍵が要る）
  4. 試験と `frontend/api-contract/openapi.json` の書き出し
- 4b（危険便）
  1. 起こす係 scripts/ops/ai_wake.py を新しく作る（first_aid.py と同じ形。標準ライブラリだけ）。起こすのは実行係だけ
  2. 見張り AIWakeStale・AIWakeSkipped を `monitoring/prometheus/alert_rules.yml` に足し、`docs/runbooks/alerts.md` に手順を書く
  3. PO の画面で実行係の routine 1 つと /fire の鍵 1 つを作る。鍵を prod1 の `.env` に置く（PO の `!` 台本）
  4. prod1 の crontab に 1 行足す（PO の `!` 台本）
- 4c（Mac の定期実行）
  1. GitHub の App の範囲を毎週読む点検を、agent-console の定期実行に足す（読み方は §2 4c で試してから決める）

入れない:
- 表の変更（migration）。kind・actor の決まりは変えない
- 効果確認（F9）と直ったかの確かめ（F7）で AI を起こすこと。この便では実行係だけを起こす。F7・F9 は 30 日の数（設計 :180）を見てから別の便で決める
- 障害が鳴ったときに調べ係を起こす道（P-1 の調べ係の分）・起こしてよい種類の一覧とその CI の検査・調べ係がコードを読む版を渡す形（U2 案A）。理由: 要件 O2・O4（札ごとの起こし方）をまだ設計していない。P-2・P-3 も揃っていない。O2・O4 を入れた形で、P-2・P-3 の後の便で作る（審査 1 回目 R2 の案 b）
- P-2・P-3（グラフの鍵と、その道の試し）。別に PO の画面で行う
- 札を作ること。実行係は札を使わない（札を作り直すと前の札が上書きされる。`backend/app/routers/ops_case.py:288-292`）。設計 §3 C1-2 の「起こすときに札を作り直す形」は、報告の proposal をサーバーが読んで文で渡す形（4a（３）・4b ⑦）に置き換えた
- 相談係の鍵・管理者の鍵の作り直し
- 値を見たい申請を調べ係が使うこと（設計 :54。v1 では使わない）
- 画面の変更（許可は v1 ではチャットで出す。設計 §12 D5 :191）
- サーバーに常駐する担当（`docs/handoff/ai-ops-247/server-agent-design.md`）。あちらは PO が話しかける担当で、この便の「自動で起こす」道とは別
- 報告を直す口・同じ件に同じ種類の報告を 2 通目として出す形。今は 1 件に種類ごとに 1 通で、2 通目は 409（`backend/app/routers/ops_case.py:518`・:533-534、一意は `migrations/20261113_200000_add_ops_case_report_kind.sql:22`）。表の権限も SELECT と INSERT だけ（`migrations/20261031_210000_create_ops_case.sql:499`）。表を変えない便なので、後の便の宿題にする（審査 3 回目 R1）

## 2. 作り方

### 4a ブランチ release/ai-ops-stage4-bin4a-round-steps

（１）`backend/app/routers/ops.py:420-430` の step の Literal に `"approve"`・`"wake"`・`"wake_skipped"`・`"wake_failed"` を足す。:436-451 の reason に `"limit"`・`"no_report"` を足す（no_report は 4b ⑥a。使える報告が無い件の approve）。並びは今の値の後ろ。ほかの値は変えない。

（２）`backend/app/routers/ops.py:359-392` の `list_events` に引数 `round_step: str | None = Query(None, pattern=r"^[a-z_]{1,32}$")` を足し、WHERE に `AND (CAST(:round_step AS text) IS NULL OR e.detail->'round'->>'step' = CAST(:round_step AS text))` を足す。値の正本は（１）の Literal で、ここでは形だけを確かめる（:361 の kind と同じ書き方）。
  - 理由: 1 日の上限を数えるのに `kind=ai` だけで読むと、Discord 発の件の回の記録（:416）も混ざり、100 行の上限（:364）を超えうる。

（３）`backend/app/routers/ops_case.py` に管理者の鍵で報告を読む口を足す。
  - 道: `GET /ops/case/{incident_id}/reports`、`dependencies=[Depends(require_case_admin)]`。
  - 返すもの: その件の報告の全部の列（種類ごとに 1 行）。なければ `{"items": []}`。
  - 読み方は同じファイルの管理者の口（:308-348 の `list_pending`）と同じ文脈の付け方・外し方にする。
  - case-api には出さない。`nginx/nginx.conf:745` の正規表現は `(report|unmask-requests)$` で、`reports` には当たらない（:811-813 の 404 に落ちる）。試験で確かめる（（５）の T4）。

（４）許可の注記の形（決まり。実装はしない。手元の Opus が書くときの形）:
  - `{"kind": "ai", "note": "<PO の言葉の写し。500 字まで>", "round": {"step": "approve", "n": <その件の許可の何回目か>, "at": "<許可を受けた時刻>"}}`
  - 報告の出来事（kind `case_report`）とは kind で見分ける。Discord 発の回の記録とは step で見分ける（便2 の案 A。`docs/handoff/ai-ops-247/card-stage4-bin2.md:78`）。

（５）試験（`backend/tests/` の ops と ops_case の試験に足す。本物の PostgreSQL で流す）:
  - T1 step に approve・wake・wake_skipped・wake_failed、reason に limit・no_report を付けた注記が 200 で入り、detail の round に残る。
  - T2 今の 9 つの step と 14 個の reason は今までどおり通る。知らない step（例 `approved`）は 422。
  - T3 `round_step=wake` で、wake の出来事だけが返る。case_report・Discord 発の start は返らない。
  - T4 `GET /ops/case/{id}/reports` は管理者の鍵で 200、相談係の鍵で 401、鍵なしで 401。nginx の case-api の道に当たらないことは、`nginx/nginx.conf` の正規表現を試験の中で `re` で当てて確かめる。
  - T5 approve の注記の note が 501 字なら 422。

（６）`frontend/api-contract/openapi.json` を書き出し直す（今の手順のまま）。

### 4b ブランチ release/ai-ops-stage4-bin4b-ai-wake（4a の本番反映の後に始める）

（１）scripts/ops/ai_wake.py（新しく作る）。first_aid.py の作りを写す（`.env` の読み方・API の呼び方 :110・全停止 :141・textfile の印・`main` の形 :373）。保守 API の宛先は first_aid と同じ `https://app.salesanchor.jp/api/v1`（`scripts/ops/first_aid.py:34`）。毎分 1 回、次の順で動く。
  ① 全停止（`GET /ops/control`）が入っていれば、何も起こさず印だけ書いて終わる（R6。first_aid の :376-378 と同じ形）。
  ② 読む: 同じ `since=<24 時間前>` で `GET /ops/events?kind=ai&round_step=<step>&limit=100` を approve・wake・wake_skipped・wake_failed の 4 回読む。
  ③ 数える: wake の行の数を 1 日の数、そのうち occurred_at が 1 時間以内の数を 1 時間の数にする。正本は記録の出来事だけで、手元に数を持たない（PO 決定 D4。設計 :190）。wake は起こす前に書く予約なので、/fire が失敗した回も 1 回に数える（多く数える側に外れる）。
  ④ 候補: approve の行のうち、同じ incident_id と同じ round の n を持つ wake・wake_skipped・wake_failed の行が 1 つも無いもの。古い approve から 1 回に 1 件だけ扱う。起こし直しは、PO が同じ件に新しい approve（n を 1 増やす）を書いたときだけ。
  ⑤ 上限（1 時間 20 回 B2・1 日 20 回 B3）に届いていれば起こさず、その approve に `wake_skipped`・reason `limit` を 1 回だけ注記し、textfile に印を書く（見張り AIWakeSkipped が Discord に知らせる。R5）。④ の条件で、同じ approve に 2 回目は書かない。
  ⑥ 起こすとき（この順を変えない）:
    a. 送る文を作る（⑦）。使える報告（⑦）が無ければ送らず、`wake_skipped`・reason `no_report` を注記して終わる。8000 字を超えるなら送らず、`wake_skipped`・reason `full` を注記して終わる。どちらも wake の行は書かないので、1 日の数に入らない。
    b. `wake` を先に注記する（起こす前の予約。これが数えの 1 回）。注記が失敗したら /fire を送らずに終わる（次の回にもう一度 ④ から始める）。この回は textfile の「動いた」印を書かない（first_aid が API の失敗で抜けるときと同じ形。`scripts/ops/first_aid.py:393-396`）。続けて失敗すると AIWakeStale が鳴る。
    c. /fire に送る（時間切れは 30 秒）。宛先は `https://api.anthropic.com/v1/claude_code/routines/<routine の id>/fire`。ヘッダは Authorization: Bearer <鍵>・`anthropic-beta: experimental-cc-routine-2026-04-01`・`anthropic-version: 2023-06-01`・Content-Type: application/json。本文は `{"text": <⑦ の文>}`（Context7 `/websites/code_claude` の routines の POST /fire。2026-11-26 に確かめた）。保守 API の呼び方（`scripts/ops/first_aid.py:35`・:113-114 の 127.0.0.1 固定）は写さず、証明書を確かめる普通の HTTPS でつなぐ。
    d. 2xx 以外・時間切れ・接続の失敗なら `wake_failed` を注記し、textfile に印を書く。この注記も失敗したときは、印だけ書いて終わる（wake の行があるので、④ で同じ approve をもう一度起こさない）。
  - 注記の形（4a（１）の値。round の n と at は必須。`backend/app/routers/ops.py:431-432`）:
    - wake: `{"kind": "ai", "note": "role=execute http=-", "round": {"step": "wake", "n": <approve の n>, "at": "<b の時刻>"}}`
    - wake_failed: note は `role=execute http=<数>` か `role=execute http=timeout`。n は approve の n。
    - wake_skipped: note は `role=execute`、reason は `limit`・`full`・`no_report` のどれか。n は approve の n。
    - note には係の名前と HTTP の数だけを書く。鍵・文の中身は書かない。
  ⑦ 実行係へ送る文: 件番号・許可した PO の言葉（approve の note）・報告の proposal・読むコードの版。
  - 使える報告: 4a（３）の口で読んだ行のうち、種類 `investigation`・status `reported` で、proposal が null・空の文字・空の一覧・空の辞書のどれでもない行（`backend/app/routers/ops_case.py:190-198` の ReportBody。proposal は任意の欄で、表の列は jsonb `migrations/20261031_210000_create_ops_case.sql:29`）。無ければ ⑥a の no_report。
  - proposal を文にする書き方: 文字ならそのまま、それ以外は `json.dumps(proposal, ensure_ascii=False, indent=2)`。8000 字は、文全体をこの書き出しの後の長さ（Python の len）で数える。
  - 読むコードの版: 本番で今動いている版。取り方は prod1 の作業場所の `git rev-parse HEAD`（U-d）とし、取れなければ `main` と書く。ずれは報告の risk に書かせる。
  - 鍵（保守の鍵・管理者の鍵・/fire の鍵）は `.env` から読む。画面・ログ・textfile に出さない。`set -x` 相当の出力をしない。

（２）試験 scripts/tests/test_ai_wake.py（新しく作る。first_aid の試験 `scripts/tests/test_first_aid.py` の作りを写す。API と /fire は偽物に差し替える）:
  - W1 全停止が入っていると、/fire を 1 回も呼ばない（R6）。
  - W2 24 時間の wake が 20 なら、次の approve では呼ばず wake_skipped・limit を書く（R5・B3）。1 時間の上限（B2）も同じ数え方で確かめる。ただし B2 と B3 はどちらも 20 なので、「1 日は 20 未満で 1 時間だけ 20」の形は作れない。試験は 1 時間の数え方（1 時間より前の wake を 1 時間の数に入れない）を別に確かめる。数えるのは b の wake の行。
  - W3 同じ approve で 2 回目は呼ばない（wake・wake_skipped・wake_failed のどれかがあれば飛ばす）。n を 1 増やした新しい approve では呼ぶ。
  - W4 文に札が入らない（実行係は札を使わない）。札の口を 1 回も呼ばない。
  - W5 /fire が 400 なら wake_failed を書き、textfile に印を書く。
  - W6 ログ・textfile・注記に、鍵の値が 0 件（偽の鍵の文字列で数える）。
  - W7 文が 8000 字を超えると送らず、wake_skipped・full を書く。
  - W8 wake の注記が失敗したら、/fire を呼ばない。
  - W9 wake_failed を書いた approve は、次の回に呼ばない。
  - W10 limit の wake_skipped を書いた approve に、次の回に wake_skipped を書き足さない。
  - W11 /fire が時間切れなら wake_failed（http=timeout）を書く。
  - W12 使える報告が無い件（報告なし・status investigating だけ・proposal が null か空）の approve では、/fire を呼ばず、wake の行を書かず、wake_skipped・no_report を 1 回だけ書く。次の回に書き足さない。
  - W13 proposal が日本語を含む辞書なら、文に ensure_ascii=False の形で入る。書き出した後の文が 8000 字を超えるなら full。

（３）見張り（`monitoring/prometheus/alert_rules.yml` の FirstAid の隣）:
  - AIWakeStale: 起こす係が 5 分動いていない（FirstAidStale :509-518 と同じ形）。
  - AIWakeSkipped: 直近 30 分に wake_skipped か wake_failed の印がある（FirstAidEscalated :497-506 と同じ形）。tier は ticket（人がすぐ動く必要は無いが、知る必要がある）。
  - 手順 `docs/runbooks/alerts.md` に 2 つの節を足す。手順には「上限で起こさなかった許可は、PO がもう一度許可を出すまで起こさない」を書く。報告は件ごと・種類ごとに 1 通で、出した後は直せない（§1「入れない」）。このため、(a) reason `no_report` で、その件に種類 investigation の報告がまだ 1 通も無いときだけ、相談係に報告を出させてから PO が新しい approve を出す。(b) reason `full` のとき、または reason `no_report` で使えない報告（status investigating だけ・proposal が空）が既にあるときは、その件は起こす係では起こせない。PO は、実行係を手で起こすか、何もしないかを決める。相談係の指示書に proposal の字数の目安は足さない（full の数は 30 日の見直しで数え、多ければ決め直す）。

（４）PO の画面での準備（実装の後、本番に入れる前）:
  - 実行係の routine: 置き場 salesanchor・コネクタなし。指示文は「文の proposal を設計として、実装を Sonnet に任せ、PR を出して止まる。merge しない」。API の口と鍵を足す。
  - 鍵は、便1 の K2 と同じく PO が Mac の「ターミナル」の窓で Keychain に入れる（`docs/handoff/ai-ops-247/card-stage4-bin1.md` の K2（２））。Opus は値を見ない。
  - Opus が RemoteTrigger の get で、routine に予定（cron）が無いこと・コネクタが空であることを確かめる。

（５）PO の `!` 台本（Opus が作業用のフォルダに置き、中身を会話で見せてから）:
  - 台本 0（読み取りだけ。4b の依頼の前）: prod1 の ubuntu で、api.anthropic.com への HTTPS の応答の数だけを出す（U-a）・`.env` の CASE_ADMIN_TOKEN と CASE_AGENT_TOKEN の行の数だけを出す（U-b。値は読まない）・`git -C /home/ubuntu/salesanchor rev-parse HEAD` の結果を出す（U-d）。
  - 台本 1: Keychain の鍵を読み、prod1 の `.env` に `AI_WAKE_EXECUTE_FIRE_TOKEN` と routine の id を足す。前に `.env` の控えを取る。値は引数に置かず、標準入力で渡す。終わったら名前の数だけを出す。
  - 台本 2: crontab の控え → cron と同じ条件で 1 回試す（rc=0 でなければ登録しない。出力に読むコードの版を 1 行出させ、U-d の結果と同じかを見る）→ `* * * * * /usr/bin/flock -n /tmp/ai-wake.lock /usr/bin/python3 /home/ubuntu/salesanchor/scripts/ops/ai_wake.py >> /tmp/ai-wake.log 2>&1` を足す（同じ行が既にあれば足さない）→ `crontab -l | grep ai_wake` と textfile の中身を出す。first_aid の台本（`docs/handoff/ai-ops-247/card-stage3-bin-g.md:1119`）と同じ作り。
  - 台本 3（V3 の前。PO の同意票を取ってから）: 先に 4a（３）の口で、試しの件の報告が 0 行かを確かめる（種類 investigation の報告が既にあれば 409 になる。あれば止まり、新しい試しの件を作るかを PO に聞く）。U-b で CASE_AGENT_TOKEN の行が 1 でなければ止まる。そのうえで prod1 で、管理者の鍵で試しの件の札を作り（`POST /ops/case/{incident_id}/ticket`）、その札と相談係の鍵で報告を 1 通出す（`POST /ops/case/{incident_id}/report`。`backend/app/routers/ops_case.py:498`）。報告は種類 investigation・status reported・proposal「試し: PR を作らず止まる」。鍵と札は画面に出さず、HTTP の数だけを出す。作った札は 24 時間有効のまま残る（`backend/app/routers/ops_case.py:50`）。試しの件だけの札で、値は画面に出していない。

### 4c ブランチなし（Mac の定期実行）→ 書類は release/ai-ops-stage4-bin4c-scope-check

（１）まず読み方を 1 回だけ試す（読み取りだけ。U-c）。試す順:
  - 道 1: Claude in Chrome で、PO のブラウザの GitHub の画面（個人の Settings → Applications → Installed GitHub Apps → Claude → Repository access）を開き、文字で読む。Chrome の操作は見張り（ADR-1085）の決まりに従う。
  - 道 2: 道 1 が使えなければ、毎週月曜に PO へ Discord で「画面を 1 回見てください」と知らせ、PO の答えを記録する（人手。見張りは知らせの送信だけ）。
（２）読めた形で、agent-console の定期実行（毎週月曜）を 1 件足す。読む中身: 「All repositories / Only select repositories」と、選ばれたリポジトリの名前。比べる正本は相談係 U10 の一覧（非公開の記録）。違えば Discord に知らせ、範囲は直さない（直すかは PO が決める）。
（３）組織の導入先も同じ形で読む（組織の画面）。読めなければ「組織は読めていない」と知らせの文に書く。
（４）結果は設計 §13 に書き、§11 の維持の仕組みの守り手の行（:176 の「【2026-11-12 P5】範囲を読む仕組みはまだ動いていない」）を直す。

## 3. 想定される分岐（ここに無い分岐は止まって報告）

| 場面 | すること |
|---|---|
| U-a: prod1 から api.anthropic.com に届かない | 4b の依頼を止め、PO に聞く（届かせる道は別の設計） |
| U-b: prod1 の `.env` に CASE_ADMIN_TOKEN が無い | 4b の依頼を止めて PO に聞く（新しく置くのは secret の変更） |
| U-d: prod1 で `git rev-parse HEAD` が取れない | 版は `main` と書く形で進める。取れない理由を設計 §13 に書く |
| 4a の T4 で case-api から reports に届く | 止める。nginx の道を直す設計を先にする |
| 4b の 1 回試しで rc≠0 | crontab に登録しない。ログの終わりを Opus が読み、直す |
| /fire が 400「Routine is paused.」 | routine が無効。PO に画面での有効化を頼む（勝手に有効にしない） |
| 起こした実行係が PR を作らずに終わる | 実行記録を読み、報告にまとめて PO に聞く。起こし直すのは PO が新しい許可を出したときだけ（approve 1 つに起こすのは 1 回） |
| 使える報告が無い件に approve が来た（報告がまだ 1 通も無い） | 起こさず no_report を注記する（⑥a）。PO に「相談係の報告を先に。出たら新しい許可を」と伝える |
| 使える報告が無い件に approve が来た（使えない報告が既にある）・full で起こさなかった | 報告は直せないので、その件は起こす係では起こせない。PO に「実行係を手で起こすか、何もしないか」を聞く |
| 台本 3 の前に、試しの件に種類 investigation の報告が既にある | 止まる。新しい試しの件を作るかを PO に聞く |
| 1 日に AIWakeSkipped が 2 回以上 | 上限 B3 の見直しを PO に聞く（設計 :119 の見込みと比べる） |
| 4c の道 1 で GitHub がログインを求める | 道 2 に切り替える。Opus がログインしない |

## 4. 本番での確かめ（Opus。本番反映の後）

- V1（4a）本番の `GET /ops/events?round_step=wake` が 200 で items 0。`GET /ops/case/<件>/reports` が api では管理者の鍵で 200、case-api では 404。
- V2（4b）crontab に 1 行・textfile の最後に動いた時刻が毎分進む（Grafana で `changes(...[5m]) > 0`）。
- V3（4b）試しの件で実行係を 1 回起こす: 先に台本 3 で、試しの件に使える報告を 1 通置く。そのうえで、PO が許可の注記を書く操作を、試しの件（`ops_incidents` の OpsPipelineTest。PO の同意票を取ってから作る）で 1 回行い、5 分以内に wake の出来事が 1 行増え、実行係の routine の実行記録が 1 件増える。実行係には「試しなので PR を作らず止まる」と note に書く。V3 の後、wake の行の数と実行係の routine の実行記録の数が同じかを比べる（wake の行だけ残り /fire が届いていない回を見つけるため）。/fire の時間切れで wake_failed（http=timeout）を書いた回は、実際には起きていることがあるので、別に数えて比べる。
- V4（4b）全停止を入れた 2 分間、wake が増えない。外した後に動き出す（R6）。PO の同意票を取ってから行う。
- V5（4b）24 時間、AIWakeStale が鳴らない。
- V6（4c）最初の週次点検が月曜に動き、記録が 1 件残る。

## 5. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K1 許可の注記と起こした記録が入る（4a） | CI の T1〜T5 が緑。本番 V1 |
| K2 PO が許可を書いてから 5 分以内に実行係が起きる（U1・R4） | V3 の時刻: 許可の出来事の occurred_at と wake の occurred_at の差が 300 秒以下 |
| K3 全停止中は 1 回も起こさない（R6） | 試験 W1 が緑。本番 V4 で wake の増え 0 |
| K4 1 時間 20 回・1 日 20 回を超えて起こさない（B2・B3・R5） | 試験 W2 が緑（便の完了で判定）。本番では 4b の本番反映から 30 日間、1 日の wake の数の最大が 20 以下（`round_step=wake` で日ごとに数える。30 日の後に別に判定） |
| K5 鍵がログ・記録・textfile に 0 件 | 試験 W6 が緑。本番で `/tmp/ai-wake.log` と textfile を、鍵の値で数えて 0（数えるときは値を引数に置かない） |
| K6 approve 1 つに起こすのは 1 回まで | 試験 W3・W8〜W10・W12 が緑。本番 V3 の後、同じ件・同じ n で、wake は 0 か 1、wake_skipped は 0 か 1 で wake と同時に無い、wake_failed は wake があるときだけ 0 か 1 |
| K8 GitHub の App の範囲を毎週読む（P5） | 4c の後、4 週続けて月曜の記録が 4 件（読めなかった週は「読めなかった」と残る。4 週の後に別に判定） |
| K9 実行係は PR を作るだけで、merge しない | 実行係の routine の実行記録に merge の呼び出し 0（E8 の見張りが止める。`scripts/agent-hooks/cloud/guard_pre_tool.py:413-432`） |

- 便の完了の判定は K1〜K3・K5・K6・K9 と V1〜V6。K4 の 30 日と K8 の 4 週は、その時点で別に判定する。
- K7（調べ係がコードを 1 ファイルずつ読める。U2 案A）はこの便から外した。調べ係を起こす便で判定する。

## 6. 戻し方

- 4a: 4b が本番で動いているときは、先に 4b の crontab の 1 行を消す（または全停止を入れる）。その後に revert の PR を出す。理由: 戻すと `round_step` の絞りが効かず kind ai の全部を数え、wake の注記が 422 になる（`backend/app/routers/ops.py:420-430` の外）。step と reason を足しただけなので、今ある記録は読めるまま（approve・wake の行は書けなくなるだけ）。
- 4b: まず prod1 の crontab の 1 行を消す（台本 2 の控えから戻す）。これで起こす係は次の分から止まる。次に revert の PR（GO #番号）。`.env` の 2 行は台本 1 の控えから戻す。routine の鍵は PO の画面で消す。
- すぐ止めたいとき: 全停止 `/ops/control/halt`。起こす係は次の 1 分から 1 回も起こさない（W1）。
- 4c: agent-console の定期実行を 1 件消す。

## 7. 実装を頼む手順（Opus）

（１）PO がこの段取り表を承認する（実装の承認）。
（２）4a をクラウドの Sonnet に頼む。依頼文は `bash scripts/new-worktree.sh release/ai-ops-stage4-bin4a-round-steps --claude` で場所を作ってから commit させる（クラウドの clone のまま commit しない）。push して止まる。Opus が PR を作る。審査役（reviewer・opus）の APPROVE と CI 緑で合流。本番反映を V1 で確かめる。
（３）4a の本番反映から 24 時間あけて（C6）、まず台本 0（§2 4b（５）。PO の `!`・読み取りだけ）で U-a・U-b・U-d を確かめる。U-a・U-b が ○ なら 4b を同じ形で頼む。危険便なので GO #番号を出す（GO 記録を PR 本文に書く）。合流と本番反映の後、PO の画面での準備（§2 4b（４））と台本 1・2 を PO に頼む。V2〜V5 を確かめる。
（４）4b の V5 の後に、4c の試し（§2 4c（１））を行う。
（５）結果は設計 §13 に書く（書類だけの PR）。

## 8. 外部・過去事例

- 社内の前例（実測）: 応急処置係 first_aid.py は、同じ「prod1 の cron で毎分・flock・`.env` の鍵・textfile の印・見張り 2 つ」の形で本番に入っている（`docs/handoff/ai-ops-247/card-stage3-bin-g.md:1119`）。応用: 新しい形を作らず、この形を写す。
- 社内の前例（実測）: /fire で 8227 字が欠けずに届いた（設計 §13 K2 :209）。応用: 文の上限を 8000 字に置き、超えたら送らない。
- 外部事例は使わない。理由: 判断の材料（届く長さ・回数の上限・鍵の置き方）はすべて社内の実測と要件で決まっており、外の事例で数を足す場面が無い。

## 9. 自己審査（Opus。同一 AI による審査で、独立した第二者レビューではない）

- 正本 1 か所: 起こした回数は出来事の表の wake の行だけで数え、手元に数を持たない（D4）。wake は /fire の前に書くので、数えから漏れる回が無い。
- 表の変更なし: step と reason は detail の中の値で、表の決まり（kind・actor）は変えない。
- 鍵: 新しく置くのは /fire の鍵 1 つだけ。CASE_ADMIN_TOKEN（報告を読むため）は既にあるかを U-b で確かめ、無ければ止まる。札は作らない。
- 試せていないこと: U-a・U-b・U-c・U-d・/fire の時間切れの振る舞い。U-a・U-b・U-d は台本 0、U-c は 4c（１）で、それに頼る作業の前に確かめる。時間切れは wake_failed に倒し、起こし直さない（W11）。
- 残る弊害: 保守の鍵を持つ者は誰でも approve を書ける。対処: 実行係にできるのは PR を作ることだけで、merge と本番反映は今の GO の決まりのまま（K9）。approve の note に PO の言葉の写しを必ず入れ、審査役が PR の審査で照らす。

## 維持の仕組み

- 守り手: 試験 W1〜W13（CI）・見張り AIWakeStale・AIWakeSkipped（Discord）・全停止（PO がいつでも入れられる）・4c の週次点検（Discord）。
- 関所なしの部分: approve の note の中身が PO の言葉どおりか。理由: 書くのは手元の Opus で、機械では照らせない。対処: 審査役が PR の審査で照らす。
- 担当: ADR-1012 のテーマとして Opus が持つ。
- 見直し: 4b の本番反映から 30 日で、日ごとの wake・wake_skipped・wake_failed の数を数え、wake の行の数と実行係の実行記録の数を比べ（wake_failed の http=timeout の回は別に数える）、full と no_report の数を数え、B3 と F7・F9 を起こすかを PO と決める（設計 :180）。調べ係を起こす便は、O2・O4 の形と P-2・P-3 が揃ってから段取り表を作る。報告を直す口（または 2 通目を許す形）は、full・no_report の数を見て後の便で決める。
