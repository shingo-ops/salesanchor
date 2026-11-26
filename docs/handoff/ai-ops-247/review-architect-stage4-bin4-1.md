<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。 -->
# 設計審査（architect）第1回 — 段階4 便4 の段取り表

判定: **REVISE**

- 理由1: 4b の起こす順（札 → /fire → 注記）では、/fire の後に注記が書けないときと、/fire が失敗・時間切れのときに、同じ件をそのまま毎分起こし直す。二重に起こす穴と、数え（D4）から漏れて B2・B3 を超える穴がある（R1）。
- 理由2: 調べ係の候補（4b ①〜③）に、要件の順番 O2（直す係が先）・O4（急がない札はまとめて）が入っていない。今の書き方のまま試験 W3・W4・W9 を作ると、後で直しが要る（R2）。
- 理由3: 4a の戻し方が、4b が動いている間に行うと起こす係が壊れる順になっている（R3）。ほかの行番号・範囲外・受け入れ基準はおおむね合っている。

審査した物: `origin/release/ai-ops-stage4-bin4-card` の `docs/handoff/ai-ops-247/card-stage4-bin4.md`（249 行。以下「カード」）。照らした実物は同じ枝の各ファイル（`git show origin/release/ai-ops-stage4-bin4-card:<パス>` で読んだ）。

## 1. 行番号と中身の照合（見る点 1）

自分で `git show … | cat -n` で読んで確かめた。

| カードの記述 | 実物 | 結果 |
|---|---|---|
| `GET /ops/events` は kind・service・since・limit（:359-392）・limit 1〜100（:364） | `backend/app/routers/ops.py:359-392`・`:364` | 合う |
| 注記の口（:478-533）・kind 3 つ（:463）・round は ai だけ（:469-475） | `backend/app/routers/ops.py:478-533`・`:463`・`:469-475` | 合う |
| step 9 つ（:420-430）・reason 14 個（:436-451） | `backend/app/routers/ops.py:420-430`・`:436-451` | 合う |
| note 500 字（:42・:473-474）・detail 8000 バイト（:41・:493-494） | `backend/app/routers/ops.py:41-42`・`:473-474`・`:493-494` | 合う |
| actor（:526）・全停止 `GET /ops/control`（:738-755） | `backend/app/routers/ops.py:526`・`:738` | 合う |
| 札の口（:273-305）・24 時間（:50）・上書き（:288-292）・1 回だけ返す（:305） | `backend/app/routers/ops_case.py:273-305`・`:50`・`:288-292`・`:305` | 合う |
| 鍵 2 本（:73-74）・同じ値なら止める（:86-89） | `backend/app/routers/ops_case.py:73-74`・`:87-90` | ほぼ合う（1 行ずれ。L1） |
| 報告 32KB（:48）・`@router` の一覧 :273・:308・:350・:392・:418・:498・:607・:674 | `backend/app/routers/ops_case.py:48`・`@router` 8 か所が同じ行 | 合う |
| case-api の 4 つの道 :725・:745・:765・:785、それ以外 404（:811-814） | `nginx/nginx.conf:725`・`:745`・`:765`・`:785`・`:811-813` | 合う |
| 表の kind の決まり :55-58・detail 8192 バイト :59 | kind は `migrations/20261016_100000_create_ops_incident_tables.sql:54-55`、actor は `:56-57`、detail の大きさは `:58` | ずれ（L1） |
| first_aid.py :1-11・:9・:110・:141・:373 | `scripts/ops/first_aid.py:1-11`・`:9`・`:110`・`:141`・`:373` | 合う |
| FirstAidEscalated・FirstAidStale（:497-518）・:497-505・:509-518 | `monitoring/prometheus/alert_rules.yml:497-506`・`:509-518` | 合う |
| cron の台本 `card-stage3-bin-g.md:1119` | `docs/handoff/ai-ops-247/card-stage3-bin-g.md:1119` | 合う |
| /fire の形 `card-stage4-bin1.md:81`・ダミーの secret :57-59 | `docs/handoff/ai-ops-247/card-stage4-bin1.md:81`・`:57-59` | 合う |
| 便2 の案 A `card-stage4-bin2.md:78` | `docs/handoff/ai-ops-247/card-stage4-bin2.md:78` | 合う |
| 起こしてよい 12 種（:118-120）・P-1〜P-3（:123-126）・コード :134 | `docs/ai-agents/ops-incident-agent.md:118-120`・`:123-126`・`:134`。見出しは §3-2〜§3-13 の 12 個 | 合う |
| 設計 :93・:119・:176・:180・:190・:191・:200・:202・:209・:210・:54 | `docs/handoff/ai-ops-247/stage4-design.md` の同じ行 | 合う |
| 「8000 字より長い文は試していない（設計 :254）」（カード :47・:130） | 該当の文は `docs/handoff/ai-ops-247/stage4-design.md:262`。:254 は「相談係の入口は鍵なしで 401」 | ずれ（L1） |
| 要件 R4〜R6（:112-114）・B2・B3（:157-158）・O6（:171）・順番 9（:232） | `docs/handoff/ai-ops-247/stage4-requirements.md` の同じ行 | 合う |
| merge の見張り `guard_pre_tool.py:414-433` | `scripts/agent-hooks/cloud/guard_pre_tool.py:413-432`（`check_merge`） | ほぼ合う（1 行ずれ。L1） |

## 2. 4a（見る点 2）

- round_step の絞り: `kind` と同じ形の確かめ（`backend/app/routers/ops.py:361`）で、WHERE の書き方も今の 3 条件（`:382-384`）と同じ形。引数が無いときは今と同じ結果なので、今の呼び手（`scripts/ops/first_aid.py:381` は `/ops/incidents` を使い、`/ops/events` を使わない）を変えない。
- 報告を読む口が case-api から届かないこと: `nginx/nginx.conf:745` の正規表現は `(report|unmask-requests)$` で終わりが固定され、`reports` には当たらない。さらに `limit_except POST`（`:746`）。ほかの道は `location /` の 404（`:811-813`）。届かない。
- FastAPI の道の取り違え: 新しい `GET /ops/case/{incident_id}/reports` と、今の `GET /ops/case/unmask-requests/{request_id}`（`backend/app/routers/ops_case.py:674`）は段の数が同じだが、固定の語が別の段にあり、`incident_id` は uuid の型なので取り違えない。
- 既存の試験: step・reason の全部の並びを固定で比べる試験は `backend/tests/` に見つからなかった（`git grep` で `notify_failed` は別機能の `backend/tests/test_analysis_error_report_verify.py:109` だけ、`leftover` は試験に 0 件）。`frontend/api-contract/openapi.json:21345`・`:21402` に並びがあるので、（６）の書き出しで変わる。壊さない。
- 事実の注記: 「api.salesanchor.jp にだけ足す」（カード :72）は正確ではない。backend の口は `nginx/nginx.conf:294` の app と `:667` の api の両方の `location /api/` から届く（今の札の口 :273 も同じ）。管理者の鍵が要るので害は無い（L2）。

## 3. 4b の順と穴（見る点 3）

満たしている点:
- R6: ① で全停止を最初に読む。first_aid と同じく、止めている間も印を書くので AIWakeStale は鳴らない（`scripts/ops/first_aid.py:376-378` と同じ形）。
- R4: 一覧に無い種類は起こさない（③・W3）。一覧は指示書の見出しと CI で同じかを確かめる（（２））。見張りの 2 つの名前は一覧に入らない（`docs/ai-agents/ops-incident-agent.md` の見出しに無いので CI でも入らない）。
- D4: 数えは出来事の表だけ。1 日の wake は上限 20 なので、`limit` の最大 100（`backend/app/routers/ops.py:364`）に収まる。
- 鍵の漏れ: 保守の鍵・管理者の鍵・/fire の鍵は `.env` から読み、注記には係の名前と HTTP の数だけ。first_aid の `ApiError` は本文を文面に入れない（`scripts/ops/first_aid.py:131-132`）。W7 で数える。調べ係への文に札が入るのは設計どおり（`docs/handoff/ai-ops-247/stage4-design.md:51-52`）。

穴: R1・R2（下）。ほかは L3〜L6。

## 4. 未確認 U-a〜U-c（見る点 4）

- U-a・U-b は「確かめるまで進まない」（カード :61）と分岐表（:182-183）にあるが、§7 の順（:224-228）にどこで誰が確かめるかの段が無い（L4）。
- U-c は 4c（１）の試しで確かめ、道 1 → 道 2 の順。4b の V5 の後（:227）。順は合う。

## 5. 受け入れ基準（見る点 5）

- K1〜K6・K9 は、数か ○× で判定できる。
- K7 は P-2・P-3（範囲外。カード :87）が揃うまで判定できない。便の完了の判定に入れるなら「P-2・P-3 の後に判定」と書く（L5）。
- K4・K8 は 30 日・4 週の観測で、便の完了と別の時点で判定する旨を書くとよい（L5）。

## 6. 戻し方（見る点 6）

- 4b: crontab の 1 行を消せば次の分から動かない。全停止でも ① で止まる（W1）。止まる。
- 4a: R3。

## 7. 範囲外（見る点 7）

- 表の変更なし: step・reason は `detail` の中の値で、表の決まり（`migrations/20261016_100000_create_ops_incident_tables.sql:54-58`）は変えない。カードの「入れない」（:85）と合う。
- F7・F9 は起こさない（:86）。②〜⑧ も調べ係・実行係の 2 つだけ。守られている。

---

## 直さないと作れない・壊れる物

### R1 起こす順で、二重に起こす・毎分起こし直す・数えから漏れる

場所: カード §2 4b（１）⑥（:129）・③（:126）・④（:127）、試験（３）（:138-147）。

事実:
- ⑥ は「札 → /fire → 2xx なら wake、それ以外なら wake_failed を注記」。/fire が 2xx でも、その後の注記が失敗すると（保守 API の 5xx・接続の失敗。first_aid では `ApiError` で抜ける形 `scripts/ops/first_aid.py:393-396`）、wake の行が無いまま終わる。次の分の ③・④ はその件を「まだ起こしていない」と見て、もう一度 /fire を送る。数え（②）にも入らないので B2・B3 を超えうる。
- /fire の時間切れ（相手は受け取ったが返事が来ない）は「それ以外」で wake_failed になる。③ が飛ばすのは wake と wake_skipped だけ、④ は wake だけなので、wake_failed の件は次の分にまた起こす。/fire が 400（routine が無効。カード :186）の間は、毎分 /fire と wake_failed の注記が続く（1 日最大 1440 行）。
- ④ は「approve の後に wake が無い」だけを見るので、上限で wake_skipped・limit を書いた件は、上限が空くまで毎分 wake_skipped を書き続ける。分岐表の「もう一度起こさない（1 件 1 回）」（:187）とも合わない。

直し方（カードに書く）:
1. ⑥ の順を「a. 札を作る（調べ係だけ。L3）→ b. `wake` を先に注記する（起こす前の予約。これが数えの 1 回）→ c. /fire → d. 2xx 以外・時間切れなら `wake_failed` を注記」にする。b が失敗したら /fire を送らずに終わる。
2. ③・④ の「まだ起こしていない」の条件を「その件（④ は、その approve の後）に `wake`・`wake_skipped`・`wake_failed` のどれも無い」にする。起こし直しは PO が新しい approve（n を 1 増やす）を書いたときだけ。
3. wake・wake_skipped・wake_failed の注記の形を決める。`OpsRound` は `n` と `at` が必須（`backend/app/routers/ops.py:431-432`）。例: `note` は `role=investigate http=-`（b の時点）・`role=execute http=400` の決まった形、`n` は実行係なら対応する approve の n・調べ係なら 1、`at` は起こした時刻。④ は note の `role=execute` と n で approve と結ぶ。
4. 試験を足す: W10 wake の注記が失敗したら /fire を呼ばない。W11 wake_failed の件は次の回に呼ばない。W12 実行係で limit の wake_skipped を書いた後、次の回に wake_skipped を書き足さない。W2 の「21 回目」の数え方は b の wake の行で数える。

### R2 調べ係の候補に要件 O2・O4 が無い

場所: カード §2 4b（１）③（:126）、試験 W3・W4・W9（:141-147）。

事実:
- 要件 O2「その場で直せる札の通知は、まず直す係が処置する。直らなかったときだけ AI を起こす」、O4「急がない札の通知は毎朝 9:00 にまとめて 1 回」（`docs/handoff/ai-ops-247/stage4-requirements.md:167-169`）。
- 障害には札（`labels->>'tier'`）があり、`GET /ops/incidents` は `tier` で絞れる（`backend/app/routers/ops.py:297`・`:312`）。札の値は page・auto・ticket（`monitoring/scripts/check_alert_rules.py:19`）。応急処置係は札 auto の件を扱う（`scripts/ops/first_aid.py:381`）。
- ③ は「firing・一覧にある・まだ起こしていない」だけで、札を見ない。札 auto の件では応急処置の再起動と同じ時に調べ係を起こし、直った件でも枠を使う。

直し方（どちらかをカードに書く）:
- 案 a: ③ に札の条件を足す。auto は `first_aid_result` が `not_recovered` か `escalated` になってから。ticket（急がない）は O4 のまとめ方を別の便で決めるまで起こさない。page はすぐ。試験に「auto で処置中は呼ばない」「ticket は呼ばない」を足す。
- 案 b: 調べ係の道（③・⑧・W3・W4・W9）をこの便から外し、`AI_WAKE_INVESTIGATE_ENABLED` も作らない。O2・O4 を入れた調べ係の道は P-2・P-3 の後の便で作る。この便は実行係の道だけにする。

### R3 4a の戻しを 4b が動いている間に行うと、起こす係が壊れる

場所: カード §6（:217）。

事実:
- FastAPI は知らない問い合わせの引数を無視するので、4a を戻すと `round_step=wake` の絞りが効かず、kind ai の出来事全部を数える（多く数える側で、起こさない向きに外れる）。
- 戻した後は step `wake` の注記が 422 になる（Literal の外。`backend/app/routers/ops.py:420-430`）。今のカードの順（/fire の後に注記）では、/fire だけが通って注記が残らず、R1 の毎分起こし直しになる。

直し方: §6 の 4a の行に「4b が本番で動いているときは、先に 4b の crontab の 1 行を消す（または全停止を入れる）。その後に 4a を戻す」と書く。R1 の 1（先に注記）を入れれば、注記の 422 で /fire は送られなくなるが、順の決まりは残す。

---

## 軽い指摘

- L1 行番号のずれを直す: 鍵が同じなら止める `ops_case.py:86-89` → `:87-90`。表の決まり `create_ops_incident_tables.sql:55-58` → kind `:54-55`・actor `:56-57`、detail `:59` → `:58`。「8000 字より長い文は試していない（設計 :254）」→ `stage4-design.md:262`（カード :47・:130 の 2 か所）。`guard_pre_tool.py:414-433` → `:413-432`。
- L2 「api.salesanchor.jp にだけ足す」（:72・:194）は「case-api には足さない（app・api の `/api/` からは届く。管理者の鍵が要る）」と書く。起こす係の API の宛先は first_aid と同じ `https://app.salesanchor.jp/api/v1`（`scripts/ops/first_aid.py:34`）か api かを決めて書く。
- L3 ⑥ で実行係を起こすときも札を作り直す書き方になっている。実行係は札を使わない（W5）。札を作ると前の札が上書きされ（`backend/app/routers/ops_case.py:288-292`）、誰も持たない有効な札が 24 時間残る。札は調べ係を起こすときだけ作る、と書く。
- L4 U-a・U-b を確かめる段を §7（３）の 4b の依頼の前に置き、誰が・どの鍵で（読み取りだけ）行うかを書く。「本番で動いている版」の取り方（prod1 の `/home/ubuntu/salesanchor` で `git rev-parse HEAD` が取れるか）も未確認なので、台本 2 の 1 回試しの出力に版を出させて確かめる。
- L5 K7 は P-2・P-3 の後に判定、K4（30 日）・K8（4 週）は便の完了の後に判定、と判定の時点を書く。
- L6 ⑦ の proposal は報告の種類 `investigation` の行から読む、と書く（4a（３）の口は種類ごとの全部の行を返す）。B2（1 時間 20 回）は B3（1 日 20 回）と同じ数なので、1 時間の数えは実質効かない。要件どおり両方数えるのはよいが、W2 の 1 時間の場合は「1 日が 20 未満で 1 時間が 20」の形が作れないことを試験の書き方に注記する。③ と ④ を同じ回に両方扱うかも書く。

## 自己審査の範囲

- この審査は書類と実物のコードの読み合わせだけ。本番・DB・prod1 には触れていない。/fire の時間切れの振る舞い、prod1 の作業場所が git の作業場所かは確かめていない（未確認）。
