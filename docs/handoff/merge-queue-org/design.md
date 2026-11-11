# 設計 — 会社名義へ移して、本線への合流を GitHub 純正の順番待ちの列に通す

- この文書は何か: 本線に入れる順番を GitHub に任せて、PR の追い越しとやり直しをなくすための設計書。
- 親の仕様書: [ブランチ運用](../../specs/branch-operations/README.md)（合流の手順を変えるため、その子として置く）
- 区分（STANDARD-WORKFLOW §1.8）: 既存の延長・修正（ブランチ運用の合流の手順を変える）。
- 状態: **PO 承認済み（2026-11-11「1」＝「承認して、下準備から始める」）**。画面の確認 6 件は R§9 で済み。U15・U16・U17・U19 と strict を外すことは、便2 の同意票の前に PO に聞く（便0 には影響しない）。設計審査の経緯: 設計審査 11 回目（b9b8010ac・2026-11-10）で APPROVE（必須 0・推奨 4。推奨 4 件は 7d0cfa833 で反映）。12 回目（7d0cfa833）は REVISE（必須 1「維持の仕組み」欄が無い・推奨 3）で、c9140f6c0 で全部直した。13 回目（c9140f6c0・2026-11-10）で APPROVE（必須 0・推奨 2。origin/main の validateDesignDoc・validateMaintenanceSection を当てて指摘 0）。推奨 2 件（§14 の効き始めの注・親子リンクの宿題）はこの版で反映。名義の移し・ruleset の変更は PO の最終確認（同意票）まで行わない。
- 下調べ: docs/handoff/merge-queue-org/recon.md（以下 R§）。ADR 案: docs/handoff/merge-queue-org/adr-draft.md
- PO の選択: 2026-11-10「1」＝「会社の名義に移して、GitHub純正の順番待ちの列を使う方向で設計する」
- 関連 ADR: ADR-135（本線＝本番投入可・:66 で merge queue を不採用）・ADR-136（危険 PR の GO）・ADR-1029（マージ前の審査をフックで強制）・ADR-1011（hooks は AI がパッチ・PO が `!` で反映）・ADR-1003（docs-only の合流）

## 1. 目的と、利用者に見える変化

- 何のため: 本線に入れる順番を機械が決めるようにして、PR が追い越されるたびに確かめをやり直す無駄（#5335 で 9 回）と、「若い番号に譲る」を AI が守れなかった問題（R§0）を、仕組みでなくす。
- 変化（前）: 合流ボタンを押した人が早い者勝ち。本線が進むと他の全 PR が「古い」になり、取り込み→16 の確かめ（20 分超）をやり直す。
- 変化（後）: PR は「列に入れる」だけ。GitHub が前の PR を含めた形で確かめ、通った順に 1 件ずつ本線に入れる。取り込みのやり直しは要らない。列を通らない合流は GitHub が拒む。

## 2. 成功条件（KGI・KPI。○×か数で判定）

| ID | 条件 | 測り方 | 基準値（変更前） |
|---|---|---|---|
| K1 | 本線への合流は全件が列を通る | `gh api repos/<新>/rulesets/<id>` に merge_queue の規則があり bypass_actors が空。導入後 14 日の合流 PR 全件で GraphQL `timelineItems(itemTypes:[ADDED_TO_MERGE_QUEUE_EVENT])` が 1 件以上 | 0%（列が無い） |
| K2 | 追い越しによる取り込みのやり直し | 導入後 14 日の合流 PR ごとに、起点（下の注）以降に入った「本線を取り込む commit」（親が 2 つで、片方が main の commit）の数。中央値 0・最大 1 以下 | 便0 で直近 14 日を同じ数え方で記録する（#5335 は 9） |
| K3 | 追い越しで長く待たされる PR が減る（案・U19 で PO が決める） | 同 14 日の合流 PR で (a) 時計の始まり（起点と GO の時刻の遅い方。下の注）→ `mergedAt` が 120 分を超えた PR の割合が、便0 の基準値の半分以下。全件と「台帳 DONE を除いた分」の両方で満たすこと。基準値で 120 分を超えた件数が 10 件未満なら (a) は判定しない。(b) `added_to_merge_queue` → `merged` の中央値が 60 分以下。中央値・p75・最大は記録だけ残し、判定には使わない（下の注） | 便0 で直近 14 日の (a) の割合と、中央値・p75・最大を記録する（前後で同じ起点・同じ数え方）。参考: 7 回目の審査が直近 20 件で数えた値は中央値 約 4.8 分・120 分超え 4 件（20%）・最大 400.8 分 |
| K4 | 列が止まったら気付く | 列の先頭の項目（`position` が一番小さい項目）の確かめ（列の commit の check suite の作成時刻のうち一番早い物から数える）が 40 分を超えても終わらないとき、次の見回り（15 分ごと）で Discord の PO 宛てに 1 通届く。確かめの制限時間 60 分（§4）より前に鳴る目安（40＋15＝55 分）。定時の起動は混む時間に遅れることがあるので、見回りごとに「予定の時刻と実際の起動時刻の差」を記録し、14 日で 5 分を超えた回数を数える。便2 の後、試しの PR が列にいる間に見張りを手で起動し、しきい値を 1 分にして 1 通届くことを確かめる | 見張り 0 |
| K5 | 移しで本番が壊れない | 移した直後の最初の配備で deploy 成功・smoke 成功・app と /api/health が 200 | — |
| K6 | 移しで設定が欠けない | secret 86=86・ruleset 2=2（中身一致）・自前の実行機の数が移す前と同じ・Pages が新 URL で開ける（中の参照の書き換えは便3） | R§6-3 の値 |

K3 の 60 分は「確かめ 1 回（20〜25 分）＋前に並ぶ分」の目安。PO の承認で確定する（U19 に含める）。

K3(a) の時計の始まり（設計審査 8 回目の必須指摘 1）: 危険な PR（ADR-136）は、PO の「GO #番号」が出るまで合流できない。この待ちは列を入れても減らないので、K3(a) では数えない。8 回目の審査で、直近 40 件の 120 分超え 5 件のうち #5345（149 分）は GO 待ちだった（本文の GO の日時 2026-11-10 18:32 JST＝09:32 UTC・合流 10:09 UTC。10:06 UTC のコメントにも「GO #5345」の文字はあるが文の途中なので、下の (2) の式には当たらない。12 回目の審査で確かめた）。
- 危険な PR の判定: `scripts/check-process-artifacts.js` の `classifyChanges` が返す `hasDangerous`（`DANGEROUS_PATTERNS`・:1023 以降。`migrations/`・`scripts/` 全部・`ops/launchd/`・`.github/workflows/deploy.yml` 等）と同じ判定を使う（9 回目の推奨。「migrations/・deploy.yml・本番 scripts/」だけと書くと数える集まりがずれる）。
- 決め方（9 回目の必須指摘 1・2 で替え、10 回目の必須指摘 1・2 で読み方を細かくした）: GO の時刻は次の順で取る。時計の始まりは「起点」と「GO の時刻」の遅い方。GO の時刻が合流の時刻より後なら（GO 記録を合流の後に書いた場合）、合流の時刻を GO の時刻とする（GO 待ちは合流までに終わっているため）。
  - 対象: 危険な PR に限らず、(1)(2) のどちらかで GO の時刻が取れた PR はすべてこの決め方を当てる（10 回目の推奨 1。process-artifacts gate は危険な道のほかにも PO の GO を求める場合があり、危険でないのに GO の日時を持つ合流 PR が直近 14 日で 126 件あった。GO 待ちは列で減らないので、危険かどうかで分けない）。どちらからも取れない PR は、危険な PR なら数から外して「外した割合」に入れ、危険でない PR なら起点のまま数える。
  - (1) 第一: PR 本文の `### GO記録` の「日時:」の値。読み方（10 回目の必須指摘 2）: 値の先頭にある日付と時刻（`YYYY-MM-DD HH:MM` か `YYYY-MM-DDTHH:MM[:SS]`）を取る。直後（間の空白は `\s*` で許す。11 回目の推奨 4）が `Z` か `UTC` なら UTC のまま、`JST` なら 9 時間引く、どちらも無ければ JST とみなす。時刻の無い値（例 #5057「2026-11-03 JST」）や日付の無い値（例 #4891「（マージ時刻は結果欄）」）は「取れない」として (2) へ進む。直近 14 日の危険な PR では UTC 書きが 3 件あった（例 #5324「2026-11-09T11:41Z ごろ」）。
  - (2) (1) が取れないときだけ: PR の issue comment のうち、行頭か「GO原文:」の直後にある GO に当たる一番早い物の `created_at`。式は `(?:^|GO原文:)[\s\-*>`'"]*GO\s*#<その PR の番号>(?!\d)`（複数行モード）。GO の前の空白・箇条書きの記号・逆引用符を許す（10 回目の必須指摘 1。#4891 のコメントは「- GO原文: `GO #4891`」で、記号を許さない式では当たらず、外れが 11.2% になった）。括弧（「」『』）で囲まれた引用は当たりにしない。
  - (3) 出し直しの GO（11 回目の推奨 1）: 合流のたびに GO を出し直し、本文に最後の GO を書いた PR がある（11 回目の審査の観測: 最初の GO のコメントと本文の時刻の差が 5 分を超えた PR は直近 14 日で 6 件・最大 65 分。#5191 は最初の GO のコメント 07:46:03 UTC・本文 08:43:41 UTC）。本文の時刻を使うと、最初の GO から合流までの追い越しの待ちが数えられない。そこで (1) が取れた PR でも (2) の式でコメントを読み、合流前に当たるコメントがあれば、(1) の時刻と合流前のコメントのうち一番早い時刻を GO の時刻とする。(2) の式は「GO原文:」の直後か行頭の GO だけに当たり、依頼文の引用（『GO #4973』）には当たらない（11 回目の審査で #4973 のコメントの当たりは 10:21:55 UTC と 10:50:20 UTC の 2 件だけだった）。
  - 記録（11 回目の推奨 2・3）: 前後とも、次の 3 つの数を記録する。①GO が取れず外した危険な PR の数 ②起点が取れず外した PR の数 ③GO の時刻を合流の時刻に置き換えた PR の数（11 回目の審査の観測: 直近 14 日で 14 件。置き換えた PR は待ち 0 分として数えられる）。「外した割合」は ①＋② を「その 14 日の合流全件」で割った値で、これが 5% を超えたらその 14 日の K2・K3 は判定しない。下の 8.1%・11.2%・1.0% は、9・10 回目の審査で危険な PR を分母にして数えた参考の値で、判定には使わない（全件を分母にすると 10 回目の式の外れは 1/544＝0.18%）。
  - 替えた理由（9 回目の審査の観測）: 直近 14 日の合流 530 件のうち危険な PR は 94 件。issue comment だけでは 43 件で GO が取れず（外れ 8.1%。§2 の「外した割合が 5% を超えたら判定しない」に当たる）。本文の日時を第一にすると、どちらからも取れないのは 94 件中 1 件（#5057）。また「一番早く当たるコメント」は GO を求める依頼文も拾う。#4973 では 03:18 UTC の依頼文「PO の『GO #4973』受領…」が先に当たり、実際の GO（本文の日時 19:20 JST＝10:20 UTC。GO のコメントは 10:21 UTC）より約 7 時間早く時計が始まった。`(?!\d)` が無いと #534 の式が「GO #5345」にも当たる。10 回目の審査の観測（直近 14 日の合流 543 件・危険な PR 98 件）: 記号を許す式にすると、どちらからも取れないのは #5057 の 1 件（1.0%）。
- カード（便0）で台本を流して確かめる（値は 2026-11-10 に PR 本文と合流時刻を読んで確かめた）:
  - #5345: 本文の日時「2026-11-10 18:32 JST」→ 09:32 UTC（(2) の式に当たるコメントは無い。9 回目に書いた期待値 10:06 UTC は誤りだったので直した）。
  - #4973: 本文の日時「2026-11-01 19:20 JST」→ 10:20 UTC（03:18 UTC ではない）。合流 10:54 UTC より前。
  - #4933: 本文の日時「2026-10-31 13:03 JST（04:03Z）」→ 04:03 UTC（JST の後ろの括弧書きの UTC と一致すること）。
  - #4891: 本文は取れず、コメント「- GO原文: `GO #4891`」12:14 UTC が当たる。合流 12:08 UTC より後なので 12:08 UTC になる。
  - #5057: 「外した」に入る。
  - #5191: 本文の日時 08:43:41 UTC より早い合流前の GO のコメント 07:46:03 UTC が当たり、07:46 UTC になる（(3) の確かめ）。
  - 上の期待値は (3) を足した後の決め方で出した値。#5345（本文 09:32 UTC・(2) に当たるコメント無し）と #4973（本文 10:20 UTC・コメント 10:21 UTC）は本文の方が早いので変わらない。#4933 は 12 回目の審査で (2) に当たるコメントが 0 件と確かめた（便0 の台本でも同じになることを確かめる）。12 回目の審査は直近 14 日の合流 550 件で、上の 6 件の期待値・(3) で 5 分超早まる 6 件（最大 64.5 分）・合流時刻への置き換え 14 件を再現した。危険な PR だけを数えた「GO が取れず外した数」は 12 回目では数え直していないので、便0 の台本で数える。
- 8 回目の審査の数え（直近 40 件・GO を考えない起点）: 120 分超え 5 件（12.5%）。台帳 DONE 14 件（0.1〜0.5 分）を除くと 5/26（19%）。数える集まりで割合が動くので、全件と台帳 DONE を除いた分の両方で判定する。台帳 DONE かどうかは `scripts/ci/is-ledger-done-pr.sh` と同じ判定を使う。
- 1 日の合流数の書き分け（10 回目の推奨 3）: 46 件＝R§1 の「1 日」の行（2026-11-03〜11-10 の調べ）。約 40 件＝R§1 の 7 日 283 件の 1 日平均。約 38 件＝9 回目の審査の 14 日 530 件（2026-10-27〜11-10）の 1 日平均。見積りには多い方の 46 件を使う。
- 判定できる件数の下限: 14 日で約 560 件（1 日約 40 件）なら、基準値 12.5% の半分は約 6.3% で数の上では判定できる。ただし 120 分超えが 10 件未満の基準値では、1〜2 件の差で結果が変わるので判定しない。

K3 を「中央値が基準値以下」から替えた理由（設計審査 7 回目の必須指摘 1）: 直近 20 件の「起点 → `mergedAt`」は 0.1 分が 6 件・25 分未満が 13 件で、中央値は約 4.8 分（台帳 DONE の自動の PR が多く、緑になってすぐ入る）。列を入れると、どの合流も列の中で確かめをもう 1 回（20〜25 分）流すので、中央値はその分だけ必ず増える。だから「中央値が基準値以下」は設計上満たせない。列で減らしたいのは追い越しで何時間も待たされる PR（直近では 400.8 分・369.7 分・239.2 分・149.0 分）なので、その長い待ちの割合で判定する。120 分は「列の確かめの制限時間 60 分（§4）の 2 回分」で、普通の待ちと追い越しの待ちを分ける目安。選ばなかった案: 台帳 DONE の自動の PR を K2・K3 から外す案（外す判定を `scripts/ci/is-ledger-done-pr.sh` に頼ることになり、前後で数える集まりが変わりやすい。記録では台帳 DONE かどうかの内訳を残す）、「後の中央値 ≤ 前の中央値＋25 分」の案（列の確かめの長さが変わると基準が動く）。

起点の決め方（設計審査 5 回目の必須指摘 1 で替えた）: 「PR の commit のうち、必須の確かめが初めて全部 success になった commit」の、その必須の確かめの完了時刻のうち一番遅い物。
- 「通った」と数える結果は check-run の conclusion が `success`・`skipped`・`neutral`、commit status の state が `success`（6 回目の推奨 1。便2 の後は乙の job が skipped になるため）。同じ名前の check-run が再実行で複数あるときは id が一番大きい物、同じ context の status が複数あるときは一番新しい物を使う。
- 2026-11-10 の 6 回目の審査で、直近の合流 PR 12 件を REST で読み、12 件とも起点が取れた（取れない割合 0%）。
- 替えた理由: 4 回目で決めた「最初の APPROVE」は、本線の ruleset で必要な承認数が 0（`required_approving_review_count: 0`）なので付かない PR が多い。2026-11-10 に合流した 30 件のうち APPROVE が付いていたのは 7 件（23%）だけだった（5 回目の審査の REST での数え）。約 8 割を外すと前後を比べられない。
- 新しい起点は合流した PR の全件で取れる: 本線の ruleset が必須の確かめを求めるので、合流した PR の最後の head は必ず全部 success になっている。
- 読み方: REST `pulls/{n}/commits` で commit を古い順に読み、各 commit の `commits/{sha}/check-runs`（job 型）と `commits/{sha}/status`（status 型。`guard-authoring/evaluation` 等）を読む。必須の名前は ruleset の `required_status_checks` から取る（前後で同じ名前の一覧を使い、一覧を記録に残す）。
- K2 はこの起点の commit より後に入った「本線を取り込む commit」を数える。
- 起点が取れなかった PR（管理者の飛ばし等）は数から外し、外した数と割合を一緒に記録する。外した割合が 5% を超えたら、その 14 日の K2・K3 は判定しない（前後どちらでも同じ扱い）。
- 前（便0 の基準値）と後（14 日後）で同じ起点・同じ式を使う。数える台本はカード（便0）で 1 本にし、前後で同じ台本を流す。台本は列の一時枝の commit（merge_group）を読まない（PR の commit だけを読む）。

K4 の 40 分の理由（設計審査 4 回目の必須指摘 3）: 列の確かめの制限時間は 60 分（§4）で、止まった項目は 60 分で列から外される。しきい値を 60 分にすると、鳴る前に外されて鳴らない。今の確かめは 20〜25 分なので、40 分は普通の確かめでは鳴らず、制限時間の前に鳴る。数えるのは「先頭の項目の確かめが始まってから」で、「列に入れてから」ではない（同時 5 本の後ろで待つ間は止まりではないため）。列の外し（制限時間切れ・赤）は GitHub が PR に記録し、作者に知らせる。作者は主に shingo-cc なので PO には届かない（5 回目の推奨 4）。そこで、外れたことは §9 の「外れの知らせ」（`pull_request_target` の `dequeued` で起きる workflow。8 回目の必須指摘 2）が、理由を起きたイベントの本体の `reason`（webhook の `dequeued`・決まった 12 個の値。§9 (3)。10 回目の必須指摘 3 で timeline の読み取りから替えた）から読んで、Discord で PO に知らせる案を置く（U15・PO が決める）。gh-pr-merge-safe.sh だけで読む形にしない。台本が「列に入れた」と報告して終わる場合や、画面から入れた場合に見落とすため（6 回目の推奨 2）。「position が 1」と書かないのは、公式スキーマの説明（`The position of this entry in the queue`）に 0 から数えるか 1 から数えるかが書かれていないため（5 回目の推奨 1）。

## 3. 選んだ案と、選ばなかった案

- 選んだ案 D: 既存の会社名義 GEN-RYU-System（free・PO が admin・shingo-cc が member・R§6-2）へ名前を変えずに移し、本線の ruleset に「merge queue 必須」を足す。
  - 理由1: 公式に「organization が持つ public リポジトリなら使える」（R§2）。会社名義は既にあり、新しく作る物が無い。
  - 理由2: 列を通らない合流を GitHub 自身が拒む。画面からの合流・自動合流・AI の合流のどの道でも効く。Shopify は v1 で「列を使わない道」を残して詰まり、v2 で普通の合流ボタンを止めて 90% 超を列に乗せた（R§7）。
  - 理由3: 列の中で確かめる。Shopify v1 の失敗（列の中で確かめず 50 件超が詰まった）を最初から避ける。Atlassian は合流起因の失敗を 7〜10% → ほぼ 0 にした（R§7）。
- 選ばなかった案 A: 個人名義のまま、合流台本に鍵を付けて 1 件ずつにする自作の列。画面と自動の合流に効かない。自作の列は見張りが無いと黙って止まる（R§7 mergify）。PO が選んだのは純正。
- 選ばなかった案 B: 外部サービス（Mergify 等）を個人名義に入れる。外部に書き込みの権限を渡すことになり、費用と規約は未調査。PO が選んだのは純正。
- 選ばなかった案 C: strict（最新の本線に揃っていること）を外すだけ。追い越しのやり直しは消えるが、「2 つの PR は単独では緑、合わせると壊れる」を本線に入れてしまう。Atlassian の 7〜10% はこの種類。

## 4. 列の設定（便2 で ruleset 15777895 に足す）

| 設定 | 値 | 理由 |
|---|---|---|
| 合流方式 | MERGE | 本リポジトリは merge commit のみ（ruleset の PR 規則・CLAUDE.md）。2026-04-23 の純正列の不具合は squash の場合で、merge は対象外（R§7） |
| 同時に確かめる数 | 5 | 1 日 46 件・25 分未満の間隔が 56%（R§1）。1 件ずつ順だと 1 日 72 件が上限（確かめ 20 分）で、昼の集中で待ちが延びる。5 本を先回りで確かめる。Atlassian は 300 件/日で 14 |
| 一度に本線へ入れる数 | 最小 1・最大 1 | 本線への 1 回の push＝1 回の配備＝1 つの PR に保つ。ADR-135/136 の「1 リリース 1 テーマ」「GO は PR 番号ごと」と食い違わない |
| 最小件数の待ち時間 | 0 分 | 最小 1 なので待たない |
| 確かめの制限時間 | 60 分 | 今の確かめは 20 分超。CI の 99% 止まり（memory: ci_pytest_99_hang）の 15 分取り消しを含めても余裕を持たせる |
| 失敗していない PR だけ合流 | 有効 | 赤を含む組み合わせを本線に入れない |
| strict（最新に揃っていること） | 無効にする | 列が「前の PR を含めた最新」で確かめるので不要。有効のままだと列に入る前の取り込み待ちが残り、K2 が下がらない。**便2 の同意票に明記して PO が判断する** |
| bypass_actors | 空のまま | 列を飛ばせる人を作らない。`gh pr merge --admin` も通らない（R§2 の gh の説明・ruleset は bypass に載った人だけ通す） |

develop の ruleset 16619490 は触らない（新しい作業に使わない・CLAUDE.md）。

## 5. 必須 16 件の、列の中での動かし方（便0）

方針: 全部の workflow の `on:` に `merge_group:` を足す（足さないと列で Pending のまま止まる・R§2）。そのうえで job ごとに次のどちらかにする。

- 甲「合わせた形で確かめ直す」: 2 つの PR を合わせたときに壊れうるもの。列では `github.event.merge_group.base_sha`..`head_sha` を比べる範囲に使う。
- 乙「列では飛ばす」: PR の本文・PR の差分だけで決まり、合わせても結果が変わらないもの。job に `if: github.event_name != 'merge_group'` を付ける（job を条件で飛ばすと Success と数えられる・R§2）。列に入った PR の中身は止まっている（列に入った後に push すると列から外れる）ので、PR で通った結果がそのまま使える。

| 必須の確かめ | 扱い | 理由 |
|---|---|---|
| pytest | 甲 | 合わせて壊れる代表 |
| テナントスキーマ整合性チェック | 甲 | 2 つの移行と model の組み合わせ |
| マイグレーションSQL 実行テスト（実DB） | 甲 | 移行の順番と組み合わせ |
| models.py に新 Column → … | 乙 | 1 つの PR の中で model と移行が揃っているかの確かめ |
| ADR-072 tenant schema lint | 甲 | 全体の走査 |
| Lint & Dark Mode Check | 甲 | 全体の走査。concurrency が `github.ref` なので列の枝ごとに分かれる（取り消し合わない） |
| gitleaks | 甲（部品をやめて本体を直接動かす形に作り直す・§5-1。U21 は PO 2026-11-11「1」で決定） | 軽い。合わせた差分も見る |
| CLAUDE.md line count | 甲 | 2 つの PR の追記で 90 行を超えうる |
| ADR index is up to date | 甲 | 2 つの PR が ADR を足すと索引が古くなる（合わせて壊れる典型） |
| UI governance gate | 乙 | PR の差分の部品を見る。カードで行を読み、全体走査なら甲に変える |
| dangling-route gate | 甲 | 片方が道を消し、片方がその道を使うと壊れる |
| warn-direct-lesson-edit | 乙 | PR の差分の警告（R§8 U7 をカードで確かめる） |
| guard-authoring/evaluation | 乙（ただし job の if では揃わない・下の注） | PR の差分に対する試験。concurrency が pull_request.number（R§4） |
| process-artifacts gate | 乙 | PR 本文と PR のファイル一覧を見る |
| API contract is up to date | 甲 | 2 つの PR の API 変更で生成物が古くなる |
| doc index reachability | 甲 | 全体の走査 |

- `github.event.pull_request.*`・head_ref・base_ref を使う甲の workflow（R§4 の列）は、列では merge_group の base_sha/head_sha を使う形に直す。行の変更前後はカード（便0）で全件書く。
- 注（設計審査 2026-11-10 の必須指摘 1）: `guard-authoring/evaluation` は job の名前ではない。`scripts/run-guard-evaluation.js:5` の `CONTEXT` で、`pull_request_target` の job（`.github/workflows/guard-authoring-gate.yml:16-18,43-44`・`statuses: write` は :51）が PR の head の commit に status を書く（同 js:18-19）。列の commit にはこの status が届かないので、job に if を付けても列で Pending のまま止まる。便0 では、merge_group のときに列の commit（`merge_group.head_sha`）へ同じ名前の status を書く job を足す。中身は「列に入った PR の head に success の status があることを API で読み、あれば success を書く」。PR の中身は列に入ると変わらないので、PR で通った結果を写すだけでよい。ほかの乙 4 件（migration-guard・UI governance・warn-direct-lesson-edit・process-artifacts）も、必須の名前が job の名前か status かをカードで 1 件ずつ確かめ、status なら同じ形にする。ruleset で integration_id 15368 に結び付いた 5 件（R§3）の、status を書く側の名義が合うかもカードで確かめる。
- 列の一時枝（`gh-readonly-queue/main/...`）で余計に走る push 起動の workflow（設計審査の必須指摘 2・origin/main の実物で確認）: branches の指定が無い `.github/workflows/backup-script-test.yml`・`.github/workflows/deploy-script-test.yml`、`branches-ignore: [main]` だけの `.github/workflows/active-work-lint.yml`・`.github/workflows/aeon-script-check.yml`・`.github/workflows/task-state-check.yml` の 5 本。便0 でそれぞれの `push:` の `branches-ignore` に `'gh-readonly-queue/**'` を足す（指定が無い 2 本は `branches-ignore: ['gh-readonly-queue/**']` を新たに置く）。数え方: `.github/workflows` 直下の 81 本（`_archive/` の 2 本は GitHub が動かさない）。一時枝で push の event が起きるかは、公式文書だけでは決まらない（§13 U18。8 回目の推奨 2）。起きなくても足して害はないので前もって足し、便2 の試しで確かめる。
- 個人名義のうちは merge_group が起きないので、便0 を入れても今の動きは変わらない（入れて安全）。

### 5-1. gitleaks の作り直し（U21・PO 2026-11-11「1」で (a) に決定。便0-B3）

なぜ: §13 U21 のとおり、今の部品 `gitleaks/gitleaks-action@v2` は (1) 列（`merge_group`）では必ず失敗し、(2) 会社名義では `GITLEAKS_LICENSE` が無いと全 PR で失敗する。部品の中身の検査道具 `gitleaks` 本体は MIT で、鍵の確認は部品の側にだけある（部品 v2 `src/index.js:109-115` の「missing gitleaks license」は部品の文。本体の README v8.30.1 の使い方に鍵は出てこない。Context7 `/gitleaks/gitleaks/v8.30.1` で確認）。

変更前（origin/main 00dfd6cb1 の `.github/workflows/secret-scan.yml`）:
- `:7-12` 起動は `pull_request`（枝の指定なし）と `push`（develop・main）。
- `:23-28` 手順は `uses: gitleaks/gitleaks-action@v2` 1 つ。`:27-28` の注「GITLEAKS_LICENSE は PR へのコメント機能が必要な場合のみ。未設定でも動作する（OSS / プライベートリポジトリ共通）」は、会社名義では誤り（部品の README「required for organizations」）。
- 部品が実際に流している命令（部品 v2 `src/gitleaks.js:93-117`・`src/index.js:137`）: 本体の版は `GITLEAKS_VERSION` が無いので既定の 8.24.3。`gitleaks detect --redact -v --exit-code=2 --report-format=sarif --report-path=results.sarif --log-level=debug --log-opts=--no-merges --first-parent <最初>^..<最後>`。PR では「最初」「最後」を PR の commit の一覧 API（`GET /pulls/{n}/commits`）から取る。見つかったら PR にコメントを書き、SARIF を成果物として残す。

変更後（同じファイルを書き換える。job の id `gitleaks` と name `gitleaks（シークレット漏洩検出）` は変えない＝必須の名前はそのまま）:
1. `on:` に `merge_group: types: [checks_requested] branches: [main]` を足す。`pull_request:`・`push:` はそのまま。
2. `permissions: contents: read` を置く（今は書いていない。部品が PR にコメントを書くための `GITHUB_TOKEN` は要らなくなる）。
3. 手順 1: `actions/checkout@v5`（`fetch-depth: 0` のまま）。
4. 手順 2「本体を入れる」: `https://github.com/gitleaks/gitleaks/releases/download/v8.24.3/gitleaks_8.24.3_linux_x64.tar.gz` を取り、sha256 が `9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c`（公式の `gitleaks_8.24.3_checksums.txt` を 2026-11-11 に `gh release download` で読んだ値）と一致しなければ失敗させる。`$RUNNER_TEMP` に展開し、`gitleaks version` を記録に出す。版は今の部品の既定と同じ 8.24.3 にする（検出の決まりを変えない。版を上げるのは別の変更で 1 つずつ）。
5. 手順 3「見る範囲を決める」: 値は `run:` に `${{ }}` で埋め込まず `env:` で渡す。
   - `pull_request`: `BASE=github.event.pull_request.base.sha`・`HEAD=github.event.pull_request.head.sha`。
   - `merge_group`: `BASE=github.event.merge_group.base_sha`・`HEAD=github.event.merge_group.head_sha`。
   - `push`: `BASE=github.event.before`・`HEAD=github.event.after`。
   - BASE か HEAD が空・全部 0・`git cat-file -e` で手元に無いときは、範囲を推測で決めずに失敗させる（fail-closed。`::error::` に理由を書く）。
6. 手順 4「調べる」: `gitleaks git --redact --verbose --no-banner --exit-code 1 --config .gitleaks.toml --log-opts="--no-merges ${BASE}..${HEAD}" .`。見つかれば終了コード 1 で job が赤になる。値は伏せ字で記録に出る（`--redact`）。
7. 変わること・やめること: PR へのコメントと SARIF の成果物はやめる（見つかった場所は job の記録に伏せ字で出る）。PR の commit 一覧 API の上限（250 件）に縛られなくなる。外部（keygen.sh）へ倉庫名を送る道が無くなる。
8. 直す注: `:27-28` の注を消し、`:3-5` の説明に「部品は使わず本体を直接動かす（会社名義・列のため。design §5-1）」を足す。`docs/B-11_credential_management_policy.md:87`・`docs/adr/ADR-075-github-secrets-only-policy.md:62,88` は workflow の名前を指すだけなので変えない（カードで読み直して確かめる）。

範囲 `BASE..HEAD` を選んだ理由: 部品の「最初^..最後」は PR の commit 一覧が 250 件を超えると先頭を取り違える。`BASE..HEAD` は「HEAD から辿れて BASE から辿れない commit」＝ PR（列では列に入った分）で増えた commit そのもの。`--no-merges` は部品と同じで、合流の commit 自体は見ない（中身は元の commit で見る）。列の一時の commit は合流の commit なので除かれ、元の PR の commit は `head_sha` から辿れるので見られる。

失敗したときの戻し方: この 1 ファイルを戻す PR（`git revert`）。必須の名前は変わらないので ruleset は触らない。

### 5-2. 列の起動漏れを機械で止める見張り（便0-B3 と同じ PR）

なぜ: 必須の確かめの workflow に `merge_group` が無いと、列は黙って待ち続ける（外部の失敗事例・§12）。今回の gitleaks のように「起動はあるが中身が列に対応しない」部品も同じ止まり方をする。人の注意ではなく、毎回の PR で機械に確かめさせる。

- 置き場: `scripts/ci/check_queue_triggers.py`（新規）と試験 `scripts/tests/test_check_queue_triggers.py`（新規）。`.github/workflows/test.yml` の必須の job `pytest`（`if: always()` で全 PR で動く。今も `:276-278` で `check_ci_aggregators.py` を流している）に 2 行足して流す。
- 中身: (1) `docs/specs/rule-enforcement/required-checks.txt` の名前のうち、`.github/workflows/*.yml` の job の `name` と一致する物について、その workflow の `on:` に `merge_group` があること。(2) どの workflow にも `gitleaks/gitleaks-action` が無いこと。(3) 名前が job の name と一致しない物（status 型。`guard-authoring/evaluation` 等・§5 の注）は、別の表 `QUEUE_STATUS_CHECKS`（台本の中）に載っていて、§5 の注の「status を写す job」があることを確かめる。どれにも当たらない名前があれば失敗。
- 効き始め: 便0 の B2（10 本）・B3（gitleaks）・status を写す job がそろった PR から。そろう前に入れると今の main で赤になるので、そろえる PR と同じ PR か、その後に入れる。
- `scripts/` は `scripts/check-process-artifacts.js:1025` の危険な道なので GO 記録が要る（ADR-1003 の委任の範囲）。
- 戻し方: `test.yml` の 2 行を消す PR。

## 6. 合流の道の直し（便0 に含める。列の前後どちらでも動く形）

| 道 | 直し |
|---|---|
| scripts/gh-pr-merge-safe.sh | `gh pr merge` の後、PR が MERGED か「列に入った」かを読み分ける。列に入ったら、MERGED になるまで待つか、「列に入れた」と報告して終わる（どちらにするかはカードで決め、K3 を測れる記録を残す）。worktree の片付けと台帳の DONE は MERGED を見てから |
| scripts/dev/check-pr-merge-ready.py | 名前の直書き（:14,:16,:166-169）を `gh repo view --json nameWithOwner` か環境変数から取る。CLEAN の判定は残す |
| .github/workflows/ledger-auto-done-main.yml | `gh pr merge --auto --merge` は列が必須の枝では「緑になったら列に入る」になる（R§2）。動きはそのまま。便2 の後に 1 件で確かめる |
| .github/workflows/ledger-done-update-branch.yml | 列が入ると不要。便3 で止める（便2 の前に止めると今の運用が詰まる） |
| scripts/agent-hooks/review-gate/gate.py:53 | STRICT_CHECK_REPOS に新しい名前を足す（旧と新の両方。大文字小文字は区別しない）。`--admin` を止める行を足す。手元の写し（~/.claude/scripts/review-gate）は ADR-1011 どおり PO が `!` で反映 |
| R§6-4 の直書き全部 | `${{ github.repository }}`・`gh repo view`・`GITHUB_REPOSITORY` から取る形に直す。試験の固定値（リポジトリ名として書かれた物）は新名へ。ただし次は例外（設計審査 5 回目の必須指摘 2）: `scripts/ci/is-ledger-done-pr.sh:21`（`LEDGER_PR_AUTHOR="shingo-ops"`）は PR の作者という人の名前なので変えない（変えると台帳 DONE の判定が壊れる）。`scripts/sop-health-collector.js:16,25` は便0 ではなく「移した直後の組」で変える。CODEOWNERS の `@shingo-ops` は人なので変えない。`backend/app/routers/discord_auto_setup.py:66`（手順書の URL）を変えると `frontend/api-contract/openapi.json:1552` の既定値も変わるので、同じ PR で API の契約を作り直す（必須の確かめ「API contract is up to date」）。この行は環境変数から取る形にせず、新しい名前の直書きにする（環境で値が変わると API の契約の比べ合わせが環境によって変わるため。6 回目の推奨 3）。`.github/workflows/publish-qa-checksheet.yml:5,60`（Pages の URL `shingo-ops.github.io`）は移すと URL が変わる物なので便3 で直す |
| 設計審査で見つかった漏れ（必須指摘 3） | `scripts/validate-pr-ownership.sh:142`（REPO_SLUG の既定値）・`scripts/dev/test-agent-hooks.sh:12,52,392`（試験の origin）・`.github/workflows/weekly-stale-tasks.yml:36`（案内の URL）・`tools/claude-channels/README.md:18`（clone 先）を新名か自動で取る形に（便0）。**本番の見張りの設定**は便0 では変えず、下の「移した直後の組」の行で扱う。人の名前としての `shingo-ops`（`.github/workflows/line-import-device.yml:29`・`.github/workflows/line-import-operations.yml:20`・`.github/workflows/sandbox-test.yml:18` の actor 比較・`.github/workflows/feedback-issue-triage.yml:42`・CODEOWNERS の `@shingo-ops`・AGENTS.md）は人を指すので変えない |
| .github/workflows/auto-merge-guard.yml（設計審査 2 回目の必須指摘 1） | 今は `pull_request_target` の `auto_merge_enabled`（:16）で起き、台帳 DONE の PR でなければ `gh pr merge --disable-auto`（:60）で予約を消す。列が必須の枝では、確かめが緑になる前に合流の命令を出すと auto-merge の予約になる（gh 2.85.0 の help・公式 merging-a-pull-request-with-a-merge-queue.md:53）。この見張りがその予約を消すので、PR は列に入らずに止まる。直し: (1) gh-pr-merge-safe.sh は必須の確かめが全部緑（check-pr-merge-ready.py の判定）になってから合流の命令を出す（今の動きのまま・カードで行を確かめる）。(2) 列に入れる操作で `auto_merge_enabled` が起きるかは未確認なので、§11 の試しの PR で確かめる。(3) 見張りは `pull_request_target` なので main 側の定義で動く（:7）。試しの PR で予約が消されると、見張りを直す PR も同じ見張りに消される。だから「列に入っている PR（GraphQL の `pullRequest.isInMergeQueue` が true。`gh pr view --json` には無い項目なので `gh api graphql` で読む。2026-11-10 に読めることを確認済み）は消さない」の判定は、起きるかどうかに関わらず便0 で前もって入れる（設計審査 3 回目の推奨 2）。判定の書き方と試験はカードで決める |
| 見張りの数え先（設計審査 2 回目の必須指摘 2） | `scripts/sop-health-collector.js:25`（`REPO` の既定値 `shingo-ops/salesanchor`）が記録に付ける名前と、`monitoring/grafana/provisioning/dashboards/json/sop-health.json` の `repo="shingo-ops/salesanchor"` の絞り込み 5 行（`:72,137,202,267,341`。設計審査 4 回目の必須指摘 2 で 3 行から直した）は組。片方だけ変えるとグラフが黙って空になる。直し: 両方を下の「移した直後の組」で新名に変える。移す前の記録は旧名のまま残るので、5 行とも絞り込みを旧名・新名の両方にする（`repo=~"shingo-ops/salesanchor|GEN-RYU-System/salesanchor"`） |
| 移した直後の組（設計審査 4 回目の必須指摘 1・2） | 新しい名前は移すまで存在しないので、次の 9 本は移す前には直せない。移した直後に 1 本の PR でまとめて新名に直す（2026-11-10 の origin/main で数えた。カードで最新の main で数え直す）。<br>(1) 本番 prod1 の GitHub の動きの記録: `docker-compose.yml:558`（`--owner=shingo-ops`・gha-exporter）。<br>(2) 監視用サーバー prod2 の設定: `docker-compose.monitoring.yml:111`（`GHA_OWNER=shingo-ops`）・`:157`（`GITHUB_REPO=shingo-ops/salesanchor`）・`monitoring/github-collector/collector.py:9,27`（説明と既定値）。<br>(3) 数え先とグラフの組: `scripts/sop-health-collector.js:16,25`・`monitoring/grafana/provisioning/dashboards/json/sop-health.json` の 5 行（上の行）。数え先は `.github/workflows/sop-health-reporter.yml:38` で `REPO: ${{ github.repository }}` を渡して動くので、移した時点で記録の名前は自動で新名に変わる（`:25` の既定値はこの道では使われない）。グラフの絞り込みを直すまで新しい点は表示されないが、記録そのものは残り、直した後に表示される。<br>(4) 手順書の URL と、その形を確かめる台本の組: `monitoring/prometheus/alert_rules.yml`（38 か所）・`monitoring/prometheus/tests/alert_rules_test.yml`（44 か所）・`monitoring/loki/rules/jarvis/alerts.yml:18,31,46,59,74,87`（6 か所）・`monitoring/scripts/check_alert_rules.py:18`（`URL_BASE`）。`monitoring/scripts/check_alert_rules.py:89` が「URL ＝ `URL_BASE`＋名前」を確かめ、`.github/workflows/monitoring-check.yml:61` で必ず流れるので、4 本は同じ PR で変える（片方だけだと赤）。<br>本番への届き方（設計審査 4 回目の推奨 3。origin/main の実物で確認）: `.github/workflows/deploy.yml` は (1) を作り直さない（Step 3d の `.github/workflows/deploy.yml:521-522` は `node-exporter promtail` だけを起こす）。(2)(4) の prod2 の設定は `.github/workflows/deploy.yml` では配られず、`/opt/salesanchor-monitoring` に置いた物と main のずれを毎日数えるだけ（`.github/workflows/monitoring-config-drift.yml:3,32`・`monitoring/scripts/check_config_drift.sh:16-23` の 6 本）。だから合流しただけでは本番は変わらない。合流の後、(1) は prod1 で gha-exporter を作り直し、(2)(4) は prod2 に置き直して監視の器を作り直す。どちらも本番のサーバーの作業なので PO の同意票。prod2 に置く手順の正本はカードで探して書く（U14）。届いたかは、`monitoring-config-drift` を手で起動して「ずれ 0」と、§11 の「グラフが途切れない」で確かめる |

## 7. 進め方（便ごとに 1 つ変え、測ってから次へ）

| 便 | 中身 | 本番への影響 | 承認 |
|---|---|---|---|
| 便0 | §5・§6 のコード。K2・K3 の基準値を数える | なし（個人名義では merge_group が起きない） | 実装カード＋PO の実装承認。合流は通常の審査 |
| 便1 | 名義の移し（PO が画面で行う）。§8 の手順 | 移す数分、合流を止める | **PO の同意票（不可逆）** |
| 便2 | ruleset に merge queue を足し strict を外す。列の見張り（§9）を入れる | 合流の仕方が変わる | **PO の同意票（ruleset の変更・permit-danger）** |
| 便3 | update-branch の自動作業を止める・Pages の URL の差し替え・覚え書き「若い番号に譲る」の廃止の提案・ADR を Accepted に | なし | 通常 |

戻し方:
- 便0: PR を戻す（merge_group の起動は個人名義では動かないので戻さなくても害はない）。
- 便1: **元の名前には戻せない前提**（R§8 U4）。git と Web の転送は残る。移した先で動かし続けることを前提に、便1 の前に §8 の点検を全部済ませる。
- 便2: 先に列を空にする（設計審査 4 回目の推奨 2）。列にいる PR を GraphQL の `dequeuePullRequest`（2026-11-10 に Mutation の一覧にあることを確認済み）で外し、外した PR の番号を記録する。その後、ruleset から merge queue の規則を外し strict を戻す（API 1 回・PO の同意票）。保存しておいた変更前の JSON に戻す。外した PR は今までの手順で 1 件ずつ合流し直す。`dequeuePullRequest` で外すたびに §9 の「外れの知らせ」が `MANUAL` の理由で PO に 1 通ずつ届く見込み（11 回目の推奨 4・推測。便2 の試しで確かめる）。戻しの同意票に「外す PR の数だけ知らせが届く」と書いておく。

## 8. 便1 の手順（名義の移し）

移す前（Opus）:
1. ruleset 2 件・リポジトリの設定・secret の名前の一覧（値は読めない・名前だけ）・Pages の設定を JSON で保存する。
2. 開いている PR の数と、列の代わりに合流を止める時間帯を PO と決める（移す数分間は合流しない）。
3. 便0 が本線に入り、直書きが残っていないことを確かめる（設計審査 5 回目の必須指摘 2 で、分け方を機械で決まる形に直した）。`shingo-ops` を含む行を、書き方で 2 つに分ける。
   - 甲（リポジトリの名前）: 正規表現 `shingo-ops(/|__)salesanchor|shingo-ops\.github\.io` に当たる行。数える範囲は甲・乙とも同じ1つの指定 `-- ':!docs' ':!.claude-pipeline' ':!tasks' ':!*.md'` に揃える（6 回目の必須指摘）。`git grep -n -E '<この式>' <この範囲>` から、§6「移した直後の組」の 9 本と `.github/workflows/publish-qa-checksheet.yml`（便3）を除いた残りが 0 件。
   - 範囲の外の \*.md で甲に当たる行は、2026-11-10 の bb9d147a9 で `tools/claude-channels/README.md:18`（clone の URL）の 1 行だけ。これは便0 で直す物として別に数え、便0 の後に `git grep -n -E '<この式>' -- '*.md' ':!docs' ':!.claude-pipeline' ':!tasks'` が 0 件であることを確かめる。
   - 乙（人の名前）: `shingo-ops` を含み、甲の式に当たらない行。動かさない。ただし「移した直後の組」の `docker-compose.yml:558`（`--owner=shingo-ops`）と `docker-compose.monitoring.yml:111`（`GHA_OWNER=shingo-ops`）は持ち主の名前なので組で変える。乙は同じ範囲で、2026-11-10 の origin/main（bb9d147a9）に 12 本・42 行ある（`git grep -n 'shingo-ops' <この範囲> | grep -v -E '<甲の式>'` で数えた）。うち docker-compose の 2 本・2 行は上のとおり組で変える。残りの動かさない乙は次の 10 本・40 行（6 回目の必須指摘で 39 行を直した）: `.github/CODEOWNERS`（14 行）・`.github/workflows/feedback-issue-triage.yml:42`・`.github/workflows/line-import-device.yml:29`・`.github/workflows/line-import-operations.yml:20`・`.github/workflows/sandbox-test.yml:18`・`scripts/check-process-artifacts.js:43,1230,1277,1280`（GO の発行者）・`scripts/ci/is-ledger-done-pr.sh:21`・`scripts/tests/test-is-ledger-done-pr.sh:9,44`・`scripts/tests/test-pr-lifecycle.py:42`・`scripts/tests/test-process-artifacts.js`（14 行）。カードで最新の main で数え直し、この一覧と食い違ったら止める。
   - 甲の件数（同じ main・同じ範囲で 164 行。範囲の外の README.md:18 を足すと 165 行）と除いた件数は、移した直後の組の PR の前後で数えて記録する。移した直後の組の PR の後は、甲を `.github/workflows/publish-qa-checksheet.yml` だけ除いて数えて 0 件（§11）。便3 の後は除かずに 0 件。
4. （設計審査 2 回目の必須指摘 3）`PIPELINE_PAT` の種類を PO に画面で確かめてもらう（U9）。使う所は 8 本・14 か所（`.github/workflows/deploy.yml:66,1161-1162`・`.github/workflows/auto-merge-guard.yml:33`・`.github/workflows/ledger-auto-done-main.yml:45,87,170,175`・`.github/workflows/ledger-done-update-branch.yml:27`・`.github/workflows/active-work-auto-done.yml:26,139`・`.github/workflows/active-work-auto-review.yml:25`・`.github/workflows/external-state-snapshot.yml:84`・`.github/workflows/monthly-secret-expiry.yml:18`）。公式文書では、細かく権限を絞る型の鍵は「持ち主を 1 つ選び、その持ち主の物しか触れない」（github/docs managing-your-personal-access-tokens.md:108）。この型で持ち主が個人名義なら、移した後は 14 か所が全部失敗する。`.github/workflows/deploy.yml:72` の「前回の配備が成功したか」の確かめも失敗し、毎回すべての移行を走らせる側に倒れる。手当て: この型なら、移す前に持ち主を GEN-RYU-System にした鍵を PO に作ってもらう（会社が鍵の承認を求める設定なら、その承認も）。移した直後、最初の合流より前に secret を差し替える（§8 移した直後 1）。古い型の鍵なら、会社が古い型の鍵を許しているかを確かめる。

移す前（PO・画面で読むだけ）: R§8 の U2（実行機）・U3（webhook・deploy key・GitHub App）を読む。個人名義に入れた App（claude.ai の GitHub 連携を含む）が会社名義で要るかを決める。

移す（PO・画面）: Settings → Danger Zone → Transfer → GEN-RYU-System・名前は salesanchor のまま。

移した直後（Opus）:
1. K6: secret 86・ruleset 2 件の中身を保存した JSON と突き合わせ。欠けていたら保存した JSON で作り直す案を PO に同意票で出す。U9 で鍵の差し替えが要るときは、最初の合流より前に `PIPELINE_PAT` を差し替える（secrets の変更なので PO の同意票）。差し替えた後、読むだけの API を 1 回呼んで新名のリポジトリに届くことを確かめる。
2. 手元の全 worktree と本店の `git remote set-url origin`（新 URL）。
3. ~/.claude/settings.json の自動判定の文（R§6-5）と agent-console の routines.json（11 か所）を新名に直す（settings は ADR-1034 の権限の足し引きの手順）。
4. 自前の実行機の確認（U2）。消えていたら scripts/setup-vps-runner.sh で登録し直す（本番の VPS の作業は PO の同意）。
5. 次の本線への合流で、K5（配備・smoke・200）を確かめる。その後、§6「移した直後の組」の PR を合流し、PO の同意票で prod1 の gha-exporter の作り直しと prod2 への置き直しを行う。新名で GitHub の動きの記録が続いていることと、`monitoring-config-drift` のずれ 0 を確かめる。
6. クラウドの依頼を 1 本（読むだけ）流して clone できるか（U5）。

## 9. 続ける仕組み（標準化・機械で守らせる）

| 仕組み | 中身 | 守らせ方 |
|---|---|---|
| 列そのもの | ruleset の merge queue 必須・bypass 空 | GitHub が列を通らない合流を拒む（人も AI も） |
| 列の見張り | 新しい workflow（schedule 15 分ごと・public なので無料・手で起動するときはしきい値を入力で変えられる）。GraphQL `repository.mergeQueue(branch:"main").entries` のうち `position` が一番小さい項目の `headCommit.checkSuites` の `createdAt` のうち一番早い物から 40 分を超えて、まだ合流していなければ scripts/notify/discord-owner-ping.sh で PO に知らせる（MergeQueueEntry に `position`・`headCommit`・`state`・`enqueuedAt` があること、CheckSuite に `createdAt` があることは 2026-11-10 に公式スキーマで確認済み）。列が作り直されると先頭の commit が変わり時刻もやり直しになる。`headCommit` が null、または `checkSuites` が 0 件のときは、その回は数えずに記録だけ残す（6 回目の推奨 4）。便2 の試しの PR で、この時刻と列から外れた時刻の差を記録する（5 回目の推奨 2）。<br>列から外れたことの知らせ（U15 で PO が知らせると決めた場合）は、定時の見回りとは別の workflow にし、外れた時に GitHub が直接起こす形にする（設計審査 8 回目の必須指摘 2。7 回目の案「定時の検索 updated:>=T」は、外れたときに PR の更新時刻が変わるかが公式文書に無く、検索の遅れで取りこぼし、回の重なりで二重に届くため替えた）。<br>(1) 起動: `on: pull_request_target: types: [dequeued]`。公式 events-that-trigger-workflows.md の `pull_request_target` の種類に `enqueued`・`dequeued` がある（2026-11-10 に github/docs の main で確認。github.com 向け）。`pull_request_target` は main 側の定義で動き PR の中のコードを動かさないので、Discord の鍵を渡しても PR から書き換えられない。PR の中身は checkout しない。PR の題名・reason などの値は `run:` の中に `${{ }}` で埋め込まず `env:` で渡す。Discord の文は PR 番号と reason の決まった値だけにし、`allowed_mentions` を PO の宛先だけに絞って @everyone 等が効かないようにする（9 回目の推奨 1）。<br>(2) 外れ 1 回につき run が 1 回なので、検索も前回の時刻も要らず、取りこぼしと二重は起きない（run が失敗したときは Actions の失敗として残り、§9「設定のずれの見張り」とは別に作者に届く）。<br>(3) 合流で列を出たときにも `dequeued` が起きるかは未確認（U20）。そこで run の中で PR を読み直し（`gh api repos/<新>/pulls/<番号>` の `merged`）、合流済みなら知らせない。合流と `dequeued` がほぼ同時のとき `merged` がまだ false の瞬間がありうる（9 回目の推奨 2・推測）。そこで、起きたイベントの本体にある `reason`（`github.event.reason`）も見て、`MERGE` か `ALREADY_MERGED` のときも知らせない（10 回目の必須指摘 3。GraphQL の timeline の `reason` は String 型で値の一覧が無いため、判定には使わない）。webhook の `pull_request` の `dequeued` の `reason` は決まった 12 個の値を持つ: `UNKNOWN_REMOVAL_REASON`・`MANUAL`・`MERGE`・`MERGE_CONFLICT`・`CI_FAILURE`・`CI_TIMEOUT`・`ALREADY_MERGED`・`QUEUE_CLEARED`・`ROLL_BACK`・`BRANCH_PROTECTIONS`・`GIT_TREE_INVALID`・`INVALID_MERGE_COMMIT`（github/docs src/webhooks/data/fpt/pull_request.json の `dequeued`・commit 404a5f4de・2026-11-10 に読んだ）。<br>(4) 外れた理由は、同じ `github.event.reason` を `env:` で受け、上の 12 個のどれかのときだけ知らせに書く。どれでもない・空のときは「理由不明」と書く。<br>(5) リポジトリの Actions の設定で `pull_request_target` が動かせる状態かを、カード（便2）で設定を読んで確かめる（会社名義に移した後の設定で読む） | K4。Mergify の指摘「黙って止まる」への手当て |
| 設定のずれの見張り | 週 1 で ruleset を読み、merge queue の規則が無い・bypass が空でない・strict が有効、のどれかで Discord | 誰かが外したら気付く |
| 審査の見張り | review-gate に `--admin` を止める行 | 列を飛ばす命令を AI が出せない |
| 数える | 週 1 で K2・K3 を数えて記録（14 日で判定） | 効果を数で確かめる |
| 決まりの置き場 | ADR（adr-draft.md）で ADR-135:66 の「採らない」を置き換える。覚え書き「若い番号に譲る」は便2 の後に廃止を PO に提案（覚え書きの削除は PO 判断） | 決まりを 1 か所に |

## 10. 危険と手当て

| 危険 | 手当て |
|---|---|
| 移した後、旧名に戻せない | §8 の点検を移す前に全部済ませる。戻さない前提の計画 |
| App・クラウドの連携が会社名義のリポジトリを読めない | U3・U5 を移す前と直後に確かめる。読めなければ会社名義に App を入れる（PO の画面操作）。本番の見張りも GitHub App と GITHUB_TOKEN を使う（`docker-compose.monitoring.yml:109-110,156`・`docker-compose.yml:551-556`）ので、U3 の確認先にこの App を名前で入れる（設計審査 3 回目の推奨 5） |
| 便0 で入れた見張りの判定が効かず、試しの PR の列入りが消される（3 回目の推奨 2） | §7 の便2 の戻し（ruleset から列の規則を外す）を先に行い、見張りを直してから便2 をやり直す |
| ruleset が移しで消える | 保存した JSON から作り直す（U1） |
| 移してから「移した直後の組」が本番に届くまで、見張りの表示や GitHub の動きの記録が欠ける（4 回目の必須指摘 1） | 移した当日に組の PR を合流し、同じ日に PO の同意票で prod1・prod2 に届ける。sop-health の点は記録が残るので後から表示される。gha-exporter が旧名で読めるか（GitHub の転送が API で効くか）は未確認なので、欠けた時間を記録に残す |
| 列の中の確かめが長くなり待ちが延びる | 同時 5 本・制限 60 分。K3 で測り、数を見て変える。見積り（8 回目の推奨 3）: 台帳 DONE の PR も列を通るので、1 日 46 件（台帳 15・作業 31。R§1）が全部列に入る。確かめ 25 分・同時 5 本なら 1 時間に約 12 件を流せる。1 時間に 12 件を超えて入る時間帯があると待ちが延びる。便0 で直近 14 日の「1 時間あたりの合流数の最大」を数えて記録し、12 件を超える時間帯があれば同時の数を見直す案を PO に出す。9 回目の審査の数え（2026-10-27〜11-10・合流 530 件・1 日約 38 件）: 決まった 1 時間の最大 7 件（2026-11-10 02 時 UTC）、どこから数えた 60 分でも最大 7 件、12 件を超えた時間 0。12 件/時は「列の中で赤が出ない」前提の値で、赤が出て列が作り直されると減る。また合流の数は列に入る数の代わりなので、便2 の後は列に入った時刻（`added_to_merge_queue`）でも数える（9 回目の推奨） |
| 列が止まって誰も気付かない | §9 の見張り（K4） |
| 純正の列の不具合（2026-04-23 例） | merge 方式は当時の対象外。列の見張りと K1 の照合で気付く |
| 乙に分けた確かめが、合わせた形の問題を見逃す | 乙は PR 本文・PR 差分だけで決まる物に限る。カードで行を読んで決め、迷ったら甲 |
| 個人名義を持ち主にした鍵が、会社名義のリポジトリで使えない（2 回目の必須指摘 3） | §8 移す前 4・移した直後 1。差し替えるまで合流しない |
| 列で合流が続き、配備の待ちが置き換わる（公式 actions-group-concurrency.md: 同じ組で待てるのは 1 本だけで、古い待ちは取り消される。2 回目の推奨） | `.github/workflows/deploy.yml:63-75` が「前回成功した配備の commit」と `github.event.before` を比べ、違えば全部の移行を走らせる側に倒れる。この確かめは `PIPELINE_PAT` を使うので、鍵の差し替え（上の行）が前提。便2 の後の 14 日で、取り消された配備の数を K3 と一緒に数える |
| 危険 PR（§2 と同じ `hasDangerous` の判定）の GO | 「列に入れる」＝「合流の操作」とみなし、GO（ADR-136）は列に入れる前に受け取る。最大 1 件ずつなので 1 PR＝1 配備は変わらない |

## 11. 受け入れ基準と検証方法

| 基準 | 検証方法 |
|---|---|
| 便0: 16 件全部に merge_group | `git grep -L 'merge_group' -- <16 本>` が空 |
| 便0-B3: gitleaks が鍵なしで動き、漏れを止める | (1) 写しの使い捨ての倉庫で、偽の鍵の形（gitleaks の既定の決まりに当たる作り物）を入れた commit に §5-1 の命令を流し終了コード 1・記録の値が伏せ字。(2) 偽の鍵が無い commit では 0。(3) `.gitleaks.toml` の allowlist の道（`.env.example`）に入れた場合は 0。(4) 直近 14 日の main の合流 PR から 5 件を選び、部品（8.24.3・`detect`）と §5-1 の命令（8.24.3・`git`）で同じ範囲を流して、見つかった件数が一致（どちらも 0 を想定）。(5) この PR 自身の `gitleaks（シークレット漏洩検出）` が緑で、記録に `gitleaks version` が 8.24.3・sha256 一致の行がある |
| 便0-B3: 列の起動漏れの見張り | 試験で「merge_group の無い必須 workflow」「gitleaks-action を使う workflow」「表に無い status 型の名前」の 3 つの作り物がそれぞれ失敗、今の main（便0 の後）で 0 件。`test.yml` の `pytest` の記録にその行が出る |
| 便1 直後: gitleaks が会社名義で緑 | 移した後の最初の PR で `gitleaks（シークレット漏洩検出）` が緑。`GITLEAKS_LICENSE` は 0 件のまま |
| 便2: gitleaks が列で動く | 試しの PR の merge_group の run で `gitleaks（シークレット漏洩検出）` が緑、記録の範囲が `merge_group.base_sha..head_sha` |
| 便0: 乙の job は列で飛ぶ | 便2 の後の試しの PR で、乙の確かめが merge_group の run で skipped・Success |
| 便0: status 型の必須（guard-authoring/evaluation 等）が列で揃う | 便2 の後の試しの PR で、列の commit の `gh api repos/<新>/commits/<head_sha>/status` にその名前が success で載る |
| 便0: 一時枝で余計に走らない | 5 本の `push:` に `gh-readonly-queue/**` の除外がある。便2 の後の試しの PR で、その 5 本の run が一時枝で 0 件 |
| 便0: 直書き 0 | §8 移す前 3 の甲の grep が、移した直後の組の 9 本と `.github/workflows/publish-qa-checksheet.yml` を除いて 0 件。*.md の甲も 0 件（README.md:18 を直した後）。動かさない乙が §8 の 10 本・40 行と一致 |
| 便0: K2・K3 の起点が取れる | 便0 の台本を直近 14 日の合流 PR に流し、起点が取れなかった割合が 5% 以下 |
| 便1 直後: 移した直後の組 | その PR の後、§8 移す前 3 の甲の grep が `.github/workflows/publish-qa-checksheet.yml` だけを除いて 0 件。`.github/workflows/monitoring-check.yml` が緑。`monitoring-config-drift` の手動起動でずれ 0（ずれの点検の 6 本に `monitoring/grafana/provisioning/dashboards/json/sop-health.json` は入っていないので、グラフは下の「見張りのグラフが途切れない」で確かめる。5 回目の推奨 6） |
| 便1: K5・K6 | §8 移した直後 1・5 |
| 便1: 鍵が新名で使える | 移した直後、`PIPELINE_PAT` を使う読むだけの workflow（monthly-secret-expiry の手動起動）が成功。最初の配備で `.github/workflows/deploy.yml` の「Check previous deploy completed」が「差分どおり」を出す |
| 便2: 列に入れても見張りが消さない | 試しの PR（台帳 DONE ではない普通の PR）を、確かめが緑になってから gh-pr-merge-safe.sh で列に入れる。auto-merge-guard の run が無いか、あっても予約を消していない。PR が MERGED になる |
| 便1 直後: 見張りのグラフが途切れない | Grafana の sop-health で、移す前と後の両方の点が 1 本のグラフに出る |
| 便2: K1 の設定 | ruleset の JSON に merge_queue（MERGE・同時 5・最大 1・制限 60）・strict=false・bypass 空 |
| 便2: K4 | 試しの PR が列にいる間に、列の見張りをしきい値 1 分で手で起動し、Discord に 1 通。普段のしきい値 40 分は workflow の既定値で確かめる（§2 K4） |
| 便2: 外れの知らせ（U15 で知らせると決めた場合） | わざと赤にした試しの PR を列に入れ、外れたときに `dequeued` の run が 1 回起き、Discord に 1 通だけ届く。合流した試しの PR では知らせが 0 通（U20 の記録も同時に取る） |
| 14 日後: K1〜K3 | §2 の測り方 |

## 12. 外部・過去事例の参照と我々への応用

R§7（出典・日付・数値・適用の限界は scratchpad の mq-web/evidence.md、要点は recon.md に転記）。どの事例も「このリポジトリで確実に成功する」証明ではない。数値は他社の規模（500〜800 人・1 日 300〜400 件）のもので、ここ（1 日 46 件）にそのまま当てはめない。当てはめるのは仕組み（列の中で確かめる・列を通らない道を塞ぐ・同時数を量に合わせる・見張る）だけ。

## 13. 未解決（設計合格の前に決める・確かめる）

- R§8 の U1〜U8。とくに U2・U3・U5 は PO の画面の確認が要る。
- strict を外すこと（§4）を PO が認めるか。
- U19（PO が決める）: K3 の判定を §2 の案（GO 待ちを除いた時計で 120 分を超えた PR の割合が基準値の半分以下＋列の中の中央値 60 分以下）にするか。60 分の目安もここで決める。列を入れると合流のたびに確かめが 1 回増えるので、合流までの中央値は今より約 20〜25 分長くなる（7 回目の必須指摘 1）。PO が中央値で比べたいなら、その増え方を受け入れた上での上限を PO が決める。
- U20（便2 の試しで埋まる）: 列から合流したときにも `pull_request_target` の `dequeued` が起きるか（8 回目の必須指摘 2）。webhook の `dequeued` の `reason` の値に `MERGE` があるので、起きると読める（推測。公式文書にどのときに起きるかの文は無い）。§9 は `merged` と `reason`（`MERGE`・`ALREADY_MERGED`）の両方で合流済みの PR を知らせない形にしてあるので、起きても起きなくても誤って鳴らない。試しの PR（合流する 1 件と、わざと赤にして外れる 1 件）で、起きたか・`github.event.reason` に何が入ったかを記録する。外れる 1 件で知らせが 1 通だけ届くことを確かめる。
- U21 は PO 2026-11-11「1」（部品をやめ本体を直接動かす）で決定。中身は §5-1・§5-2。以下は見つけたときの記録。
- U21（決定済み。便0-B2 のカード作成時 2026-11-11 に見つけた設計の漏れ）: 必須の確かめ `gitleaks（シークレット漏洩検出）` は `.github/workflows/secret-scan.yml:24` で部品 `gitleaks/gitleaks-action@v2` を使う。この部品の元（v2 と最新 v3.0.0 の `src/index.js`。`gh api repos/gitleaks/gitleaks-action/contents/src/index.js` で読んだ）には次の 2 つがある。(1) 対応する起動は `push`・`pull_request`・`workflow_dispatch`・`schedule` だけで、それ以外は「not yet supported」で失敗する（:36-46）。だから列（`merge_group`）では必ず赤になる。(2) 倉庫の持ち主が会社（Organization）だと、`GITLEAKS_LICENSE` の secret が無ければ失敗する（v2 :48-115。公式 README「required for organizations, not required for user accounts」）。今の倉庫には `GITLEAKS_LICENSE` が無い（`gh secret list` の名前で 0 件）。だから会社名義へ移した直後から、列とは関係なく全 PR でこの必須の確かめが赤になり、合流が全部止まる。選択肢: (a) 部品をやめ、本体の `gitleaks`（MIT・v8.30.1）を workflow の中で直接動かす。鍵も外部への登録も要らず、列では `merge_group.base_sha`..`head_sha` を見られる。必須の名前は job の name なので変わらない。(b) gitleaks.io の無料の鍵を申し込み（名前・メール・会社名の入力。README「How do I get a free license key?」）、secret に入れる。ただし (1) は直らないので、列では乙（飛ばす）にする必要がある。鍵の確認のため倉庫名と持ち主名が外部（keygen.sh）に送られる（README）。(c) 移すのをやめる。設計の推奨は (a)。決まるまで便0-B2 から gitleaks を外し、別のカードにする。便1（名義の移し）の同意票はこの件が片付くまで出さない。
- U9: `PIPELINE_PAT` の種類と持ち主（PO の画面の確認）。細かく絞る型で持ち主が個人なら、会社を持ち主にした鍵を作り直す。
- U10: 列に入れたときに `auto_merge_enabled` が起きるか（公式 events-that-trigger-workflows.md:666 では `enqueued` と別の種類・未確認）。便2 の試しの PR で確かめる（§11）。便0 の見張りの判定はどちらでも安全な形にする（§6）。
- U11: 本番の見張り（docker-compose の GitHub App）が会社名義のリポジトリを読めるか（§10・U3 と一緒に確かめる）。
- U12: 会社が鍵の承認と寿命の上限を求めているか（managing-your-personal-access-tokens.md:104-118）。U9 で作り直すときに PO が画面で確かめる。
- U13: 会社名の綴り（大文字小文字）。§6 の置き換えと review-gate の照合は大文字小文字を区別しない形にするが、表示の綴りは移した後の API の値で確かめる。
- U15（PO が決める）: 列から外れたとき PO にも Discord で知らせるか（§2 K4 の注）。知らせない場合、外れたことに気付くのは作者（shingo-cc）だけになる。
- U16（PO が決める）: K4 のしきい値を 40 分のままにするか、定時の起動の遅れに備えて 35 分にするか。設計の推奨は 40 分のまま遅れを数える（35 分だと普通の確かめ 20〜25 分との差が 10 分になり、混んだ日に誤って鳴りやすい）。14 日で遅れが 5 分を超えた回数が 1 回以上なら 35 分に下げる案を出す。
- U17（PO が決める）: 便1（名義の移し）の間、本線への合流を止める時間帯（6 回目の観点 f）。移している最中の合流は行き先が変わる途中で起きるため、止める時間を決めてから同意票を出す。
- U18（便2 の試しで埋まる）: 列の一時枝（gh-readonly-queue/…）が作られたとき Actions の `push:` で workflow が起きるか。7 回目の審査で公式文書を読んだ結果: managing-a-merge-queue.md:49 は「外部の CI は gh-readonly-queue/{base_branch} の枝が push されたときに動かすべき」と書くが、Actions の `push:` が起きるかは events-that-trigger-workflows.md に書かれていない。文書だけでは決まらないので、便0 で `push:` の 5 本に `gh-readonly-queue/**` の除外を前もって入れ（起きても起きなくても安全）、§11「一時枝で余計に走らない」の試しで実際に起きたか（除外が無ければ起きていたか）を記録する。
- `push:` で動く workflow の一覧（§11 の 5 本）は、7 回目の審査の抜き出しが空で返り確かめ直せていない。カード（便0）を作るとき、最新の main で .github/workflows/\*.yml の `on.push` を YAML として読み（行の抜き出しではなく）、枝の指定ごとに一覧を作り直す。5 本と食い違ったら止める。
- U14: prod2（監視用サーバー）の `/opt/salesanchor-monitoring` に設定を置く正式な手順と担当（§6「移した直後の組」）。カードを作る前に正本を探し、無ければ PO に聞く。
- 行番号: この設計の file:行 は 2026-11-10 の origin/main（2bf29d9e〜53b3b308）の値。カードを作るときに最新の main で確かめ直す（3 回目の推奨 4）。

## 14. 維持の仕組み

- 守り手: scripts/agent-hooks/review-gate/gate.py（便0 で `--admin` を止める行を足し、列を飛ばす合流の命令を AI が出せないようにする。この行が効き始めるのは便0 の後から。それまでは列がまだ無いので、守る対象も無い）。列そのものは GitHub の ruleset が守る（ファイルではないので、下の見張りで外れに気付く）。
- 列の起動漏れの見張り `scripts/ci/check_queue_triggers.py`（§5-2・便0-B3 で作る。必須の job `pytest` で全 PR に流れる）。必須の確かめに `merge_group` が無い・列に対応しない gitleaks の部品が戻る、のどちらも PR の段で赤にする。
- 便0・便2 で作る見張りの workflow（列の見張り・外れの知らせ・設定のずれの見張り。§9）は、まだファイルが無い。作ったら、この欄の守り手にパスを足す（便3 の片付けで行う）。
- 対象: 本線への合流が全件列を通ること（ruleset の merge queue の規則・bypass が空・strict が無効）。列が止まったときに PO に知らせが届くこと（K4）。
- 親子リンクの宿題（STANDARD-WORKFLOW §1.6）: 親の仕様書 docs/specs/branch-operations/README.md の §7 に、この recon.md・design.md へのリンクがまだ無い。設計を PO が承認した直後の文書だけの変更で足す（遅くとも便3 の片付けで）。
- 中身の詳しい表: §9「続ける仕組み」。
