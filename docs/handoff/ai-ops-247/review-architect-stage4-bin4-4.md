<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。 -->
# 設計審査（architect）第4回 — 段階4 便4 の段取り表

判定: **APPROVE**

- 理由1: 前回の R1・L1〜L3 は 4 件とも直っている（§1）。報告は直せないことを「入れない」に書き、full・no_report の後の戻り道を「報告がまだ無い／使えない報告が既にある」で分け、分岐表・見直しにも同じ分け方で入れた。書いた事実は実物の行と合う。
- 理由2: 足した物（台本 0 の相談係の鍵の数・台本 3 の前の 0 行の確かめ・時間切れの回を別に数えること・後の便の宿題）は、今のコードと表で出来る手順になっている。二重起こし・上限超え・鍵や札の漏れの新しい穴は無い（§2）。
- 理由3: 前回からの差分は指摘の場所だけ（`git diff 40ed344ea 39828fe1f`）で、前回 ○ の所は壊していない（§3）。残りは軽い指摘 4 件（L1〜L4）で、実装の依頼文か手順書を書くときに直せばよい。

審査した物: `origin/release/ai-ops-stage4-bin4-card` の `docs/handoff/ai-ops-247/card-stage4-bin4.md`（267 行、commit 39828fe1f。以下「カード」）。前回の指摘は `origin/release/ai-ops-stage4-bin4-review3` の `docs/handoff/ai-ops-247/review-architect-stage4-bin4-3.md`。照らした実物は同じ card の枝の `backend/app/routers/ops.py`・`backend/app/routers/ops_case.py`・`migrations/20261031_210000_create_ops_case.sql`・`migrations/20261113_200000_add_ops_case_report_kind.sql`・`nginx/nginx.conf`・`scripts/ops/first_aid.py` で、`git show <枝>:<パス> | cat -n` で自分で読んだ。

## 1. 前回の指摘が直ったか（見る点 1）

| 前回 | 結果 | 根拠 |
|---|---|---|
| R1 報告は出し直せないので full・no_report の後の戻り道が出来ない | ○ | 「入れない」に報告を直す口・2 通目の形を足した（カード :97）。根拠の行は実物と合う: 2 通目は `ON CONFLICT (incident_id, kind) DO NOTHING`（`backend/app/routers/ops_case.py:518`）で行が返らず 409（`:533-534`）、一意は `migrations/20261113_200000_add_ops_case_report_kind.sql:22`、表の権限は SELECT と INSERT だけ（`migrations/20261031_210000_create_ops_case.sql:499`）。古い一意（incident_id だけ。`migrations/20261031_210000_create_ops_case.sql:24`）は `migrations/20261115_110000_drop_ops_case_report_single_unique.sql` で外れているので、カード :38 の「種類ごとに 1 通（便2b）」とも合う。手順書の文（:169）を (a) 報告がまだ無い no_report だけ「報告を出させてから新しい approve」、(b) full と使えない報告が既にある no_report は「起こす係では起こせない。手で起こすか、何もしないか」に分けた。分岐表を 2 行に分けた（:202-203）。見直しに宿題を足した（:267）。前回の直し方 4（proposal の字数の目安）は「足さない。30 日の見直しで数える」と決めた（:169） |
| L1 reason `no_report` が §1 と T1 に無い | ○ | §1 の入れる物（:75）と T1（:119）に `no_report` を足した。4a（１）の Literal（:103）と揃った。今の reason は `backend/app/routers/ops.py:436-451` の 14 個で、足す先と合う |
| L2 台本 3 の前提 | ○ | (a) U-b（:66）と台本 0（:177）で CASE_AGENT_TOKEN の行の数も数え、台本 3 で 1 でなければ止まる（:180）。報告の口が相談係の鍵を要るのは `backend/app/routers/ops_case.py:161`（`require_case_agent`）で合う。(b) 台本 3 の前に 4a（３）の口で 0 行を確かめ、あれば止まって PO に聞く（:180）と分岐表（:204）。(c) 札が 24 時間有効のまま残る（:180。`backend/app/routers/ops_case.py:50`） |
| L3 時間切れの回の数え方 | ○ | V3（:212）と見直し（:267）に「wake_failed（http=timeout）の回は別に数える」を足した。K6（:226）は前回のまま正しい |

## 2. 足した物が実物と合い、出来る手順になっているか（見る点 2）

- 報告は直せないことの書き方（:97）: §1 の表のとおり実物と合う。報告を直す口が無いことは、`@router` の一覧（`backend/app/routers/ops_case.py:273`・`:308`・`:498` ほか。カード :38）と行の決まり（`migrations/20261031_210000_create_ops_case.sql:135-140` は select と insert だけ）で確かめた。表を変えない便（:88）と食い違わない。○
- full と no_report の後の戻り道の分け方（:169・:202-203）:
  - (a) 報告がまだ無い件: 相談係が報告を出せば 1 通目なので通る（`backend/app/routers/ops_case.py:518` で衝突しない）。PO が n を 1 増やした approve を書けば、④（:133）の「同じ n の wake・wake_skipped・wake_failed が無い」に当たり、次の回の候補になる。出来る。ただし相談係の報告が status investigating や proposal 空なら (b) に落ちて戻れない（L2）。
  - (b) 起こせない件: 起こす係は ④ で同じ approve を飛ばし、新しい approve を書いても同じ報告を読むので、また no_report か full になる。カードの「起こす係では起こせない」は正しい。手で起こした回は wake の行が無いので、見直しの比べ方にずれが出る（L3）。full は PO の note を短くすれば収まる場合がある（L4）。
- 分岐表の新しい行（:202-204）: どれも「止まって PO に聞く」か「no_report を注記する」で、勝手に先へ進む行は無い。○
- 台本 0 の前提（:177）: 名前の行の数だけを数え、値は読まない。U-b の書き方（:66）と同じ。○
- 台本 3 の前提（:180）: 0 行の確かめは 4a（３）の口（管理者の鍵）で出来る。札を作る口は件が無ければ 404（`backend/app/routers/ops_case.py:283-284`）、作ると上書き（`:288-292`）。報告の口は相談係の鍵＋札（`:159`・`:161`）で、道は case-api（`nginx/nginx.conf:745` の `(report|unmask-requests)$`）でも app・api の `/api/`（`nginx/nginx.conf:294`・`:667`）でも届く。どの件を使うかが決まっていない（L1）。
- 時間切れの回の数え方（:212・:267）: wake の後に wake_failed を書く順（:138-139）なので、http=timeout の回は wake の行で数えられ、別に数えれば比べられる。○
- 見直しの宿題（:267）: full・no_report の数を数えて、報告を直す口を後の便で決める。数えるのは 4a（２）の `round_step=wake_skipped` と note・reason で出来る。○
- 二重起こし・上限超え・鍵や札の漏れ: 起こす係の動き（④〜⑦ :133-149）は今回変わっていない。台本 3 は鍵と札を画面に出さず HTTP の数だけ（:180）。新しい穴は無い。

## 3. 前回 ○ だった所を壊していないか（見る点 3）

- 前回の版（40ed344ea）との差分は、状態の行（:9）・U-b（:66）・入れる物（:75）・入れない（:97）・T1（:119）・手順書（:169）・台本 0（:177）・台本 3（:180）・分岐表（:202-204）・V3（:212）・見直し（:267）だけ。
- 起こす順「予約の注記 → /fire → 失敗の注記」（:136-139）・④ の条件（:133）・⑤ の上限（:134）・4a（２）の `round_step`（:105。`backend/app/routers/ops.py:361`・`:382-384` と同じ形）・4a（３）の報告を読む口と case-api の 404（:108-112。`nginx/nginx.conf:745`・`:811-813`）・/fire のつなぎ方（:138。保守 API の固定 IP は `scripts/ops/first_aid.py:35`）・b の失敗のときの印（:137。`scripts/ops/first_aid.py:393-396`）・戻し方（:235-238）は前回のまま。壊していない。

---

## 直さないと作れない・壊れる物

なし。

## 軽い指摘（実装の依頼文・手順書を書くときに直す）

- L1 台本 3 と V3 の「試しの件」がどの件か決まっていない。V3（カード :212）は「`ops_incidents` の OpsPipelineTest。PO の同意票を取ってから作る」で、本番には便C の擬似アラートの件が既に 1 行ある（`docs/handoff/ai-ops-247/card-stage2-bin-c.md:247`・`docs/handoff/ai-ops-247/stage4-recon.md:49`）。今ある件を使うのか、新しく作るのか（作るなら便C の台本 B の形 `docs/handoff/ai-ops-247/card-stage2-bin-c.md:185`）を台本 3 の頭に書く。件が無いと札の口は 404（`backend/app/routers/ops_case.py:283-284`）で止まるだけなので危なくはない。あわせて、分岐表に「U-b で CASE_AGENT_TOKEN の行が 1 でない → 台本 3 を止めて PO に聞く（新しく置くのは secret の変更）」の行を足す（今は :180 の文だけで、§3 の U-b の行 :196 は管理者の鍵だけ）。
- L2 戻り道 (a)（:169・:202）で相談係に報告を出させるとき、「種類 investigation・status reported・proposal を入れて出す」ことを PO から相談係へ伝える文に入れる。status investigating や proposal 空で出すと、その件は (b) に落ちて二度と起こす係では起こせない（:97 の事実）。
- L3 (b) で PO が実行係を手で起こした回は wake の行が無いので、V3 の後と 30 日の見直し（:212・:267）の「wake の行の数 ＝ 実行記録の数」の比べ方で、実行記録が多く見える。手で起こしたときは、その件に note だけの注記（例 `kind ai`、round なし）を残すか、見直しで手で起こした回を別に数える、と 1 行足す。手で起こした回は上限 B2・B3 の数（:132）にも入らないことも書いておく。
- L4 full は「その件は起こす係では起こせない」（:169・:203）としているが、8000 字は PO の note（500 字まで。`backend/app/routers/ops.py:42`）を含む文全体で数える（:147）ので、note を短くした新しい approve で収まる場合がある。手順書に「note を短くして新しい approve を 1 回試してよい。それでも full なら手で起こすか何もしないか」と書くか、「試さない」と決める。

## 自己審査の範囲

- この審査は書類と実物のコードの読み合わせだけ。本番・DB・prod1 には触れていない。本番の OpsPipelineTest の件に報告や札があるか、prod1 の `.env` の CASE_AGENT_TOKEN の有無、/fire の URL（Context7 の中身）は確かめていない（未確認）。
