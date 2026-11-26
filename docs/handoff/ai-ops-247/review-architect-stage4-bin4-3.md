<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。 -->
# 設計審査（architect）第3回 — 段階4 便4 の段取り表

判定: **REVISE**

- 理由1: 前回の R1・L1〜L6 は全部、カードの文としては直っている（§1）。reason `no_report`・使える報告の決まり・proposal の書き出し方・/fire の宛先とつなぎ方・W12・W13・K6 は実物と合い、二重起こし・上限超え・鍵や札の漏れの新しい穴は無い（§2）。
- 理由2: ただし、前回 L6 で足した「proposal を短くした報告を出し直させてから新しい approve」（カード :168）と「相談係に報告を出させてから」（:168・:201）は、今の表とコードでは出来ない。報告は 1 件に種類ごとに 1 通で、2 通目は 409、報告を直す口も UPDATE の権限も無い。手順書に書けば、PO が従うと必ず止まる（R1）。
- 理由3: ほかは軽い指摘（T1 と §1 に no_report が無い・台本 3 が相談係の鍵の有無と試しの件の既存の報告を確かめていない など。L1〜L3）。

審査した物: `origin/release/ai-ops-stage4-bin4-card` の `docs/handoff/ai-ops-247/card-stage4-bin4.md`（264 行。以下「カード」）。前回の指摘は `origin/release/ai-ops-stage4-bin4-review2` の `docs/handoff/ai-ops-247/review-architect-stage4-bin4-2.md`。照らした実物は同じ card の枝の各ファイルで、`git show <枝>:<パス> | cat -n` で自分で読んだ。

## 1. 前回の指摘が直ったか（見る点 1）

| 前回 | 結果 | 根拠 |
|---|---|---|
| R1 報告が無い件の扱い | ○（文として。戻り道は下の R1） | 案 x を採った。⑥a で使える報告が無ければ `wake_skipped`・`no_report`、wake は書かない（カード :135）。reason `no_report` を 4a（１）の Literal に足す（:102。今の reason は `backend/app/routers/ops.py:436-451` の 14 個で、足す先と合う）。使える報告の決まり（:145）、書き出し方（:146）、W12・W13（:162-163）、V3 の前に台本 3 で報告を置く（:179・:209）。分岐表に行を足した（:201） |
| L1 /fire のつなぎ方と宛先の出どころ | ○ | ⑥c（カード :137）に宛先の URL・ヘッダ・本文・出どころ（Context7、2026-11-26）と「`scripts/ops/first_aid.py:35`・:113-114 の 127.0.0.1 固定は写さず、証明書を確かめる普通の HTTPS」。実物の固定 IP は `scripts/ops/first_aid.py:35`・`:113-114` で合う。Context7 の中身はこの審査では確かめていない（未確認） |
| L2 b の失敗のときの印・wake だけ残る穴 | ○ | ⑥b（カード :136）で「動いた印を書かない。first_aid が API の失敗で抜けるときと同じ形」（`scripts/ops/first_aid.py:393-396` は印を書かずに 1 を返す。合う）。V3 の後（:209）と 30 日の見直し（:264）で wake の行の数と実行記録の数を比べる |
| L3 K6 の判定の文 | ○ | カード :223 が前回の提案どおり。⑥b〜d の決まり（wake の後にだけ wake_failed、wake_skipped は wake を書かない回だけ）と合う |
| L4 冒頭の参照・tier の語 | ○ | :6 に「この便では作らない。参考」。:167 が「tier は ticket」 |
| L5 404 の行 | ○ | カード :39・:111 が `nginx/nginx.conf:811-813`。実物 :811-813 が `location / { return 404; }`、:814 は閉じ括弧で合う |
| L6 reason full のときの手順 | × | 文は足した（カード :168）が、書いた手順が出来ない。下の R1 |

## 2. 新しく足した物が実物と合い、作れて、穴を作っていないか（見る点 2）

- reason `no_report`: 4a（１）で Literal の後ろに足すだけ（カード :102）。step と result の決まり（`backend/app/routers/ops.py:453-457`）は step `result` にだけ効くので当たらない。作れる。
- 使える報告の決まり（カード :145）: 種類 `investigation`・status `reported`（列の決まり `migrations/20261031_210000_create_ops_case.sql:25`、種類は `migrations/20261113_200000_add_ops_case_report_kind.sql:5`・`:12`）。proposal は jsonb（`migrations/20261031_210000_create_ops_case.sql:29`）で、書くときは `json.dumps(..., ensure_ascii=False)` を jsonb に入れる（`backend/app/routers/ops_case.py:508-509`・`:517`・`:527`）。読み出すと Python の None・str・list・dict のどれかになるので、:145 の「null・空の文字・空の一覧・空の辞書」で判定できる。数や真偽だけの proposal は「使える」側に入るが、害は無い。○
- proposal の書き出し方（カード :146）: 文字ならそのまま、ほかは `json.dumps(..., ensure_ascii=False, indent=2)`、8000 字は文全体の len。/fire で 8227 字が届いた実測（:49）の内側。○
- /fire の宛先とつなぎ方（カード :137）: 保守 API の固定 IP と分けた。時間切れ 30 秒・2xx 以外は wake_failed（:138）。○（宛先の URL そのものは未確認。U-a が台本 0 で届くかだけを見る）
- 台本 3（カード :179）: 札を作る口 `backend/app/routers/ops_case.py:273`（管理者の鍵）、報告の口 `:498`（相談係の鍵＋札。札は `X-Case-Ticket` の頭書き `:159`、鍵は `:161`）。道は合う。足りない確かめは L2。
- W12・W13（カード :162-163）: ⑥a・⑦ の決まりと合う。no_report の wake_skipped は ④ の条件（:132）で次の回に飛ばされるので、書き足しは起きない。○
- K6 の文（カード :223）: §1 L3 のとおり ○。
- V3 の前提と比べ方（カード :209）: 台本 3 で報告を置き、approve を書き、5 分以内に wake 1 行・実行記録 1 件、その後に wake の行の数と実行記録の数を比べる。K2 は approve と wake の occurred_at の差（:219）で判定できる。○
- 二重起こし: 毎分 1 本（flock -n。カード :178）、④ は 3 種のどれかがあれば飛ばす（:132）、no_report・full は wake を書かない（:135）。新しい穴は無い。
- 上限超え: no_report・full は wake を書かないので 1 日の数に入らず、/fire も呼ばない。数えは wake の行だけ（:131）。新しい穴は無い。
- 鍵や札の漏れ: 起こす係は札を作らず札の口を呼ばない（:92・W4）。注記の note は係の名前と HTTP の数だけ（:143）。台本 3 は鍵と札を画面に出さず HTTP の数だけ（:179）。新しい穴は無い。台本 3 で作った試しの件の札は 24 時間有効のまま残る（`backend/app/routers/ops_case.py:50`）が、試しの件だけで値は出さないので軽い（L2 に添える）。

## 3. 前回 ○ だった所を壊していないか（見る点 3）

- 起こす順「予約の注記 → /fire → 失敗の注記」（カード :134-138）・④ の条件（:132）・⑤ の上限（:133）は前回のまま。⑥a の前に ⑤ があるので、上限に届いた件は no_report より先に limit になる。どちらも wake を書かず、④ で 2 回目は無い。壊していない。
- 4a の戻し方（:232）・4b の戻し方（:233）・全停止（:234）は前回のまま。
- 4a（２）の `round_step`（:104）と WHERE は `backend/app/routers/ops.py:361`・`:382-384` と同じ形のまま。
- 4a（３）の報告を読む口と case-api の 404（:107-111）は前回のまま。`nginx/nginx.conf:745` の正規表現は `(report|unmask-requests)$` で `reports` に当たらない。

---

## 直さないと作れない・壊れる物

### R1 報告は出し直せないので、full と no_report の後の戻り道（手順書・分岐表）が出来ない

場所: カード §2 4b（３）の手順書の文（:168）、分岐表の no_report の行（:201）、W12 の「status investigating だけ」の場合（:162）。

事実:
- 報告は 1 件に種類ごとに 1 通。2 通目は `ON CONFLICT (incident_id, kind) DO NOTHING` で行が返らず 409（`backend/app/routers/ops_case.py:518`・`:533-534`、一意は `migrations/20261113_200000_add_ops_case_report_kind.sql:22`）。
- 報告を直す口は無い（`@router` の一覧 `backend/app/routers/ops_case.py:273`・`:308`・`:350`・`:392`・`:418`・`:498`・`:607`・`:674` に報告の更新が無い）。表の権限も SELECT と INSERT だけ（`migrations/20261031_210000_create_ops_case.sql:499`）、行の決まりも select と insert だけ（`:135-140`）。
- このため次の 2 つは、同じ件では出来ない:
  - reason `full`: 「proposal を短くした報告を相談係に出し直させてから、PO が新しい approve」（:168）。種類 investigation の報告は既にあるので 409。
  - reason `no_report` で、その件に status `investigating` の報告だけがある・proposal が空の報告がある場合（W12 の対象 :162）: 「相談係に報告を出させてから」（:168・:201）が 409。この件は 4a・4b の範囲では永久に起こせない。
- カードは「表の変更なし」（:88・:254）なので、報告を直す口をこの便で足すことも出来ない。

直し方（カードの文だけ。4a の値は変えなくてよい）:
1. :168 の full と no_report の手順を、出来る形に書き直す。例: 「報告は件ごと・種類ごとに 1 通で直せない。その件は起こす係では起こせない。PO は (i) 実行係を手で起こすか、(ii) 何もしないかを決める。報告を直せる口は後の便の宿題」。報告がまだ 1 通も無い no_report の場合だけ「相談係に報告を出させてから新しい approve」が使える、と分けて書く。
2. 分岐表 :201 を同じく 2 つに分ける（報告がまだ無い／出せない報告が既にある）。
3. 見直し（:264）か「入れない」（:87-96）に、報告を直す口（または 2 通目を許す形）を後の便の宿題として 1 行足す。
4. ⑦ の 8000 字で full になるのは、proposal が長いときだけでなく、PO の note（500 字まで）・件番号・版を足した全体なので、相談係の指示書に「proposal は 7000 字以内」などの目安を渡すかを 1 行決める（任意。決めないなら「決めない」と書く）。

---

## 軽い指摘

- L1 reason `no_report` が、§1 の入れる物（カード :75「reason に `limit`（上限）を足す」）と試験 T1（:118「reason に limit を付けた注記」）に無い。:102 の Literal には足しているので、:75・:118 に `no_report` を足す（T1 で 200 になることを確かめないと、4a の本番反映後に 4b の no_report の注記が 422 になっても CI で気づけない）。
- L2 台本 3（カード :179）の前提を足す。(a) 相談係の鍵 CASE_AGENT_TOKEN が prod1 の `.env` にあるか（報告の口は相談係の鍵が要る `backend/app/routers/ops_case.py:161`。台本 0 の U-b は管理者の鍵だけを数える :66・:176）。台本 0 で同じく名前の数だけを出す。(b) 試しの件 OpsPipelineTest に種類 investigation の報告が既にあれば 409 になる（R1 の事実）ので、台本 3 の前に 4a（３）の口で 0 行を確かめ、あれば新しい試しの件を作るかを PO に聞く、と分岐表に足す。(c) 作った札は 24 時間有効のまま残る（`backend/app/routers/ops_case.py:50`）ことを書く。
- L3 /fire の時間切れ（30 秒）で wake_failed を書いても、実際には routine が起きている場合がある（返事だけ届かない）。K6 の文（:223）では wake と wake_failed の 2 行で正しいが、V3 の比べ方（:209）では「wake の数 ＝ 実行記録の数」にならない。比べるときは wake_failed（http=timeout）の回を別に数える、と 1 行足す。

## 自己審査の範囲

- この審査は書類と実物のコードの読み合わせだけ。本番・DB・prod1 には触れていない。今の本番の報告の行数、試しの件に報告があるか、prod1 の `.env` の CASE_AGENT_TOKEN の有無、/fire の URL（Context7 の中身）は確かめていない（未確認）。
