<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — api-error-retry-governance（自動の送り直しを続ける仕組み）

親: docs/handoff/api-error-auto-retry/design.md
素人向け1行: 送り直しても駄目だった投稿はその場で Discord に知らせ、毎週月曜に1週間分の数を Discord に届け、決めた理由を正式な記録に残す。

**対象ADR**: ADR-1050（本設計で起案）／ADR-154（試行記録で失敗回数を数える）／ADR-1003（GO委任）
**recon**: docs/handoff/api-error-retry-governance/recon.md
**日付**: 2026-10-29（第1版）
**担当**: Opus（Planner・Architect 兼務の自己審査。独立の第二者審査ではない）
**状態**: 設計審査済み（自己）・PO 承認済み（2026-10-30「1」＝この設計で作り始め、作る・試す・本番に出すまで進める）・実装カード発行済み（card-1.md）

---

## 目的（PO の言葉）

- PO「この仕組みを標準化して管理定着させて継続させるための仕組みも出来ているか事実ベースでエビデンスを確立してくれ」（2026-10-29）。
- 点検の結果、8項目のうち4項目が ×（recon.md §1）。PO「1」（2026-10-29。選択肢「4点をまとめて埋める設計を作る」）。

## KGI（○×で判定）

8項目の点検をやり直したとき、8項目すべてが ○ になる。

## 対象と対象外

対象:
- A. 諦めた投稿の知らせ（項目4）
- B. 毎週月曜の数の知らせ（項目5・7）
- C. ADR-1050 と FEATURE-INDEX の1行（項目3）
- D. 担当欄と、元の設計書の守り手の書き直し（項目7・補足）

対象外:
- 送り直しの回数・待ち時間・条件（#4854 のまま。変えない）
- 画面（アプリの画面は触らない）
- Grafana の画面と Prometheus の指標（下の「選ばなかった案」）
- その場の送り直し（2秒・8秒）の成功回数。DB に残らないため、週の知らせには入れない。必要なときはログを数える（`backend/app/services/line_analysis_v102_svc.py:521` の行）。
- v102 以外の解析の経路

## 変更前と変更後

| | 変更前 | 変更後 |
|---|---|---|
| 3回とも失敗した投稿 | だれにも知らされない | 次の見回り（10分以内）で Discord に1回だけ届く |
| 送り直しの数 | ログを読まないと分からない | 毎週月曜 09:10 に1週間分の数が Discord に届く |
| 決めた理由 | 途中経過の資料だけ | ADR-1050 に残り、FEATURE-INDEX から辿れる |
| 担当と見直し | 担当欄が空・予定なし | 担当は Opus。週の知らせに「要調査」が付いたら調べる |

## 作り方

### A. 諦めた投稿の知らせ

- 場所: `backend/app/tasks/tcg_extraction_recovery.py` に関数 notify_given_up_api_error_jobs を足す。`backend/app/tasks/tcg_extraction_recovery.py:362` の _run_recovery の最後で呼ぶ。新しい定期処理は足さない。
- 「諦めた」の条件。`backend/app/tasks/tcg_extraction_recovery.py:297` の条件と次の点だけが違う:
  - 試行の数が3以上。または、作られてから24時間を過ぎた（見回りの対象から外れた）。
  - 作られてから48時間以内（古い分を何度も読まないため）。
  - 最新の試行が5分より前、という条件は使わない。
- 二度送らない: Redis キー api_error_given_up:notified:<job id>。期限は7日。`backend/app/tasks/viewer_share_flag_monitor.py:72` と同じ順にする。キーがあれば飛ばす。送れたときだけキーを置く。
- 1回の見回りで送るのは1通だけ。中身は件数と、先頭10件の「仕入元の名前・投稿の時刻（日本時間）・最後の断られ方（HTTP の番号）」。
- 送り先: ADMIN_NOTIFICATION_DISCORD_WEBHOOK。送信は `backend/app/services/discord_notifier.py:45` の _post_discord_webhook を使う。
- 送り先の設定が空のときや、Redis につながらないときは、ログに warning を1行出して何もしない。そのときも送り直しの処理は止めない。
- 戻り値に given_up_notified（送った件数）を足す。

### B. 毎週月曜の数の知らせ

- 新しいファイル backend/app/tasks/api_error_retry_weekly.py に、タスク report_api_error_retry_weekly を作る。型は `backend/app/tasks/bundle_bulk_monitor.py:93` と同じ。
- beat: `backend/app/celery_app.py:207` の後ろに、月曜 09:10（日本時間）の予定を足す。include にも足す（`backend/app/celery_app.py:44`）。
- 数える期間: 直前の7日（作られた時刻）。数えるのは v102 の job だけ。
  - 一時的に断られた投稿の数: 試行のどれかが、一時的な断られ方で失敗した job（条件の判定は A と同じ）
  - そのうち送り直しで解析が終わった数: status が done
  - そのうち諦めた数: A の条件に当たる
- 「要調査」を付ける目安: 諦めた数が1以上。または、一時的に断られた投稿が20件以上。
- 0件の週も送る。知らせが来ないこと自体で、定期処理が止まったと気づけるようにする。

### C. ADR-1050

- docs/adr/ADR-1050-api-error-auto-retry.md を本設計の PR で起案する（ステータス Proposed）。中身は #4854 の作り方（その場で2回・数分後に合計3回まで・24時間・1回20件・v102 だけ）と、本設計の A・B。
- `docs/adr/FEATURE-INDEX.md:20` の補足欄に「一時的に断られた解析の送り直し → ADR-1050」を足す。
- node scripts/generate-adr-index.js を実行して docs/adr/README.md を作り直す。

### D. 担当と守り手

- `.claude-pipeline/active-work.d/release-api-error-auto-retry-design.md` の担当欄を「Opus（解析の送り直し）」にする。
- `docs/handoff/api-error-auto-retry/design.md:141` の守り手を `backend/tests/test_api_error_auto_retry.py` に差し替える。
- 本設計の守り手は実装の試験（下の「維持の仕組み」）。

## 選ばなかった案

- Prometheus の指標と Grafana の画面: worker の値は Redis を経由して backend が出す作りになっている（`backend/app/celery_health.py:48`）。そのため、足す場所が3か所になる。週に数件の出来事なので、週1回の Discord で足りる。数が増えたら別の設計で足す。
- 通知済みの列を DB に足す: DB の変更（migration）が要る。本番の反映が止まる危険が増える（10/29 の反映の止まり）。Redis の型が既にある。
- Loki の規則でログを数えて警告する: 本番の Loki に規則が読み込まれているかが未確認（recon.md §4）。

## 弊害と対処

| 弊害 | 対処 |
|---|---|
| Redis が消えると同じ投稿をもう一度知らせる | 48時間の窓で上限がある。1回の見回りで1通だけ |
| 一度に大量に諦めると知らせが長くなる | 先頭10件と件数だけにする（1800字で切れる、`backend/app/services/discord_notifier.py:45`） |
| 定期処理そのものが止まると、知らせも止まる | 月曜の知らせは0件でも送る。届かなければ止まっていると分かる |
| 知らせの処理の失敗で送り直しが止まる | 例外はその場で捕まえてログに出す。送り直しの結果は返す（T4） |

## 受入条件

| 基準 | 検証方法 |
|---|---|
| T1 3試行で失敗した job が知らせの対象になる | 試験: 3試行・最新が HTTP 503 の job を作り、対象に入る |
| T2 2試行の job、成功した job、永続的な失敗（HTTP 400）は対象外 | 試験: それぞれ対象に入らない |
| T3 同じ job は2回目の見回りで送られない | 試験: Redis の偽物にキーがあれば送信を呼ばない。送信が失敗したらキーを置かない |
| T4 送り先が空、Redis が無い、送信の例外のどれでも、送り直しの結果は返る | 試験: _run_recovery の戻り値に送り直しの件数がある |
| T5 週の知らせの3つの数と「要調査」の目安 | 試験: 用意した job で数が一致する。諦め1件で「要調査」が付く |
| T6 週の知らせの予定が beat にあり登録されている | 試験: `backend/tests/test_celery_beat_registered.py` が通る。予定が月曜 09:10 |
| T7 ADR の目次が最新 | CI「ADR index is up to date」が緑 |
| K1 本番: 月曜 09:10 に Discord の管理者用の部屋に知らせが届く | 2026-11-02（月）の届いた知らせを PO が目で見る |
| K2 本番: 8項目の点検をやり直して8項目すべて ○ | 実装の反映後に、点検の担当がもう一度読むだけで調べる |

## KPI

- 8項目のうち ○ の数: 今は 4 → 8
- 諦めた投稿が知らされるまでの時間: 今は「知らされない」→ 10分以内

## 外部・過去事例

- 過去事例（このリポジトリ）: `backend/app/tasks/viewer_share_flag_monitor.py:72` は、新しく見つかった件を Redis キーで1回だけ Discord に送る。同じ型を使う。
- 過去事例: `backend/app/tasks/bundle_bulk_monitor.py:93` は、月曜の朝に件数を Discord に送る。0件の週の扱いは本設計で「送る」に決めた。
- 外部の数値事例は使わない。理由: 足すのは社内の知らせと記録だけで、外部の性能の数値に依る判断が無いため。

## 計画

1. 1つの PR に、文書（recon.md・design.md・card-1.md・ADR-1050（Proposed）・FEATURE-INDEX の1行・README の作り直し・担当欄・元の設計書の守り手）と、実装 A・B と試験 T1〜T6（Sonnet）を入れる。DB の変更なし。反映の設定の変更なし。
3. 反映後: K1（11/2 月曜）と K2。両方 ○ なら ADR-1050 を採用に上げる。

## 戻し方

- 実装 PR を戻す（revert）。DB の変更が無いので、コードを戻すだけで元に戻る。Redis キーは7日で消える。

## 維持の仕組み

- 守り手: 人手で守る（実装 PR で新しい試験 backend/tests/test_api_error_retry_governance.py を守り手に差し替える）
- 対象: 諦めた投稿の知らせの条件と二度送らない仕組み、毎週月曜の数の知らせ
- 関所なしの場合: 条件・目安・予定を変える PR は、この design.md の受入条件と ADR-1050 を見直してから出す。

## 設計審査（Architect・自己審査）

- 判定: APPROVE（設計合格。PO 承認ではない）
- 根拠:
  - 既存の型を2つ使う（Redis で1回だけ／月曜の件数）。新しい技術は足さない。DB の変更も無い。
  - 送り直しの条件は変えない。T4 で、知らせが失敗しても送り直しが止まらないことを確かめる。
  - 受入条件はすべて試験か、目で見て○×が付く形。
- 未解決: 定期処理の停止を自動で警告する仕組みは今回作らない。月曜の知らせが届かないことで気づく形にとどめる（弊害欄）。
