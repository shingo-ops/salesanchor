# design — 試しの道具が計算の間に取引を開いたままにしない（本番反映の移行を止めない）

- 状態: C1〜C4 は PO 承認済み（2026-11-10 PO「1」＝この設計で作る）・実装済み（PR #5340、2026-11-09T19:27:59Z マージ、2026-11-10 04:28 JST 本番反映）。P1 基準値は測定済み（§11）。P4（本番での前後の測定）はまだ測っていない。追補 C5・C6 と K の直し（§13、2026-11-10）と §14 の直しは設計審査済み（クラウドの Architect＝Opus の審査 APPROVE、2026-11-10。中4 は §14 で反映）・実装未着手。
- 根拠: docs/handoff/replay-tx-release/recon.md（行番号は origin/main 96a63df05）。
- 実装: release/replay-tx-impl（クラウドの Sonnet・card.md §1〜§8 のとおり）。マージ前の審査・本番での測定（P4）はその PR で行う。
- 関係する決まり: ADR-1037（移行の鍵待ち 1 秒）・ADR-1070（接続の返却時の後始末）・docs/handoff/deploy-db-stall/design.md §17（段4 接続の名前）・docs/handoff/migration-runner-redesign/design.md §5（段5 全件の流し直しをやめる）。

## 1. 目的（KGI）

本番で試しの道具（読み取りだけの再生・試算）を流している間も、本番反映の移行が鍵待ちで失敗しない。

- 利用者に見える変化: 試しを流している日でも、画面の更新（本番反映）が止まらない。11/9 は試しの約 2 時間 45 分の間に本番反映が 7 回続けて失敗した（recon §1）。

## 2. 対象と対象外

| 区分 | 中身 | 理由 |
|---|---|---|
| 対象 | backend/app/tools/v102_replay_diff.py | 11/9 の握り手（recon §1・§2-1） |
| 対象 | backend/app/tools/prompt_ab_recompute.py | 同じ型（recon §2-3） |
| 対象 | backend/app/tools/prompt_ab.py | 同じ型。Gemini を待つ間が長い（recon §2-3） |
| 対象 | 上の 3 つが共通で使う 1 つの関数（新しい置き場は backend/app/tools/_tx_guard.py） | 同じ決まりを 1 か所に置く（SSOT） |
| 対象 | 試験 backend/tests/test_v102_replay_diff.py（新規）・backend/tests/test_prompt_ab_recompute.py・backend/tests/test_prompt_ab*.py（既存に足す） | 再発を機械で止める |
| 対象外 | scripts/accuracy/llm_compare/fhd_snapshot.py | わざと 1 つの写しで読む作り（recon §2-3）。短い 1 回の判定で、計算の待ちは無い |
| 対象外 | 本番の解析 run_v102_analysis | 書き込みと投稿ごとの鍵があり、取引の切り方を変えると結果が変わりうる。別の設計で扱う |
| 対象外 | 接続の名前（application_name） | 名前の正本は段4の表（deploy-db-stall §17-2）。ここで別の名前を作ると正本が 2 つになる。段4 の追補で道具の名前を表に足す（§9） |
| 対象外 | 本番反映側（run_all_migrations.sh・deploy.yml） | 根本の直しは段5（全件の流し直しをやめる）。この設計は道具の側だけ |
| 対象外 | DB 全体の設定（postgresql.conf の idle_in_transaction_session_timeout） | アプリ全体の動きを変える。段4 §17-7 と同じ判断 |

## 3. 変更前と変更後

### C1 v102_replay_diff.replay_post（`backend/app/tools/v102_replay_diff.py:77-97`）

- 前: :94 で投稿日を読んだ後、取引を開いたまま :96 の計算（約 11 秒）に入る。取引を閉じるのは :120 の finally。
- 後: :94 の後・:96 の前で `session.rollback()` を呼ぶ。読み取り専用なので捨てて困る書き込みは無い。計算に渡る値はただの値（recon §2-2）なので、結果は変わらない。:120 の rollback は残す（失敗時の後始末）。

### C2 prompt_ab_recompute._recompute_row（`backend/app/tools/prompt_ab_recompute.py:87-90`）

- 前: :87 で投稿日を読み、取引を開いたまま :90 の計算に入る。成功の行では rollback しない。
- 後: :87 の後・:90 の前で `session.rollback()`。

### C3 prompt_ab.run_ab（`backend/app/tools/prompt_ab.py:537-602`）

- 前: :537 の文脈の読み取り・:602 の合計の SELECT の後、取引を開いたまま :549/:556 の Gemini 呼び出し（数十秒）に入る。
- 後（実装済みの位置。§13 で明記）: 上限は run_ab の最初（`backend/app/tools/prompt_ab.py:485`）で 1 回置く。取引を閉じるのは、繰り返しの中の各回で Gemini を呼ぶ直前（`backend/app/tools/prompt_ab.py:547`）。2 回目以降の呼び出しの前にも同じ行を通るので、前の回の台帳の commit と合計の読み取りの後にも閉じる。設計時の書き方は次のとおり: Gemini を呼ぶ繰り返しの直前で取引を閉じる。ただし閉じる前に「取引の中にまだ commit していない書き込みが無い」ことを実装役が確かめる（:601 の台帳の commit の後なら無い見込み。確かめられなければ止めて設計へ戻す）。閉じ方は `session.commit()` ではなく `session.rollback()`（書き込みが無いことを試験で確かめた上で）。

### C4 共通の関数（新規 backend/app/tools/_tx_guard.py）

- 中身は 2 つだけ:
  1. `release_before_compute(session)`: 取引中なら rollback する（C1〜C3 はこれを呼ぶ。直に rollback を書かない）。
  2. `set_idle_tx_limit(session, seconds=30)`: `SET idle_in_transaction_session_timeout = '30s'` を流して commit する（rollback で消えないように）。replay()・recompute()・run_ab() の最初に 1 回呼ぶ。
- 2 の意味: C1〜C3 で抜けがあっても、30 秒を超えて取引を開いたまま待てば DB がその接続を切る＝本番反映の待ちは最大でも約 30 秒＋3 秒×数回で済み、合計 40 回（約 2 分）の枠の中で通る。
- 30 秒にする条件: P1 の基準値で「読み取りの途中の文と文の間の待ち」の最長が 30 秒よりずっと短い（5 秒以下）こと。超えていたら止めて設計し直す。

## 4. 代替案と選んだ理由

| 案 | 中身 | 判定 |
|---|---|---|
| A（採用） | 道具の側で計算の前に取引を閉じる＋接続ごとに待ちの上限 | 原因（計算の間の取引）を直に消す。本番アプリに触らない |
| B | 本番反映を試しの道具が動いていない時だけ流す | 人の段取りに頼り、11/9 と同じく気づかずに重なる |
| C | DB 全体に idle_in_transaction_session_timeout を入れる | アプリ全体の動きが変わる。段4 §17-7 で外した判断と食い違う |
| D | 段5（全件の流し直しをやめる）を先にやる | 根本の直し。ただ規模が大きく、その間も試しは流れる。A と両方やる |

## 5. 計画（順番に。変更は一度に 1 つ）

| 順 | 中身 | 担当 | 止まる条件 |
|---|---|---|---|
| P0 | この設計を PO が承認（KGI と実装の許可） | PO | 不承認 |
| P1 | 基準値: 今のコードで本番の再生を 20 投稿だけ流し、1 秒ごとに pg_stat_activity を写す（読むだけ） | Opus（本番は reader の道・別の箱） | 取引を開いたまま待つ最長が 5 秒を超える読み取りがある→C4 の 30 秒を見直す |
| P2 | 実装カードを書き、クラウドの Sonnet が C1〜C4 を実装（#5340 で済み）。追補 C5・C6 は §13 の審査の後に別の便で実装 | Opus→Sonnet | 試験が赤 |
| P3 | マージ前の審査役（opus）・CI 緑・GO・マージ・本番反映 | Opus | 審査 REVISE |
| P4 | 測定: 本番反映の後、同じ 20 投稿を「直す前のファイルを差し込んだ箱」と「直した後の箱」で続けて流し、同じ写しで K1〜K3・K5 を測る（§12） | Opus | K のどれかが × |

## 6. 受入条件（KPI）

| 基準 | 検証方法 |
|---|---|
| K1 道具の接続が「取引を開いたまま 1 秒以上待つ」写しの数が 0 | P4 で 1 秒ごとに pg_stat_activity を写し、`state='idle in transaction' AND now()-state_change >= 1s` の行を数える。P1 の基準値（直す前）と並べて表で示す。測る道は jarvis（prod1 で `docker exec astro-webapp-postgres-1 psql`、SELECT だけ。移行の段の点検と同じ道）。reader 鍵の道はほかのユーザーの接続の state が空（null）になるので K1 には使えない（deploy-db-stall §18-11 の末尾）。P1 の写しは state が入っているので reader 鍵の道ではないが、どの道で取ったかの記録は残っていない（未確認）。P4 では道を記録に書く。道具の箱の接続は client_addr（箱の IP）で絞る |
| K2 1 投稿の読み取りにかかる時間の最長が 1 秒未満 | P4 の「直した後の箱」のログの `[v102_replay_diff] job=… read_ms=…` の行（`backend/app/tools/v102_replay_diff.py:99`、#5340 で実装済み）の最大値が 1000 未満。20 投稿で 20 行あること。直す前の値は取れない（§12-2） |
| K3 再生の結果が直す前と同じ | P4 で続けて流した「直す前」と「直した後」の出力（20 投稿の各品目の結果）を `python -m app.tools.v102_replay_diff diff` で比べて差が 0 行。2 回の間のマスタの最終更新時刻も併記する（§12-3） |
| K4 C1〜C3 で「計算の前に取引を閉じる」を試験で確かめる | 呼んだ順を記録する試験（session の偽物）で、計算の関数より前に rollback が 1 回あり、その間に execute が無いことを確かめる。3 道具とも緑。prompt_ab は 2 回呼ぶ形（repeat=2）で、2 回目の Gemini の呼び出しの直前にも rollback があり、その間に execute が無いこと（台帳の書き込みと合計の読み取りの後にも閉じる。§13 で足す） |
| K5 待ちの上限が効いている | 試験で `set_idle_tx_limit` が SET・commit・SHOW・rollback をこの順で呼ぶこと。P4 で道具のログの `[tx_guard] idle_in_transaction_session_timeout=` の値が 30s（§12-1）。§13 で足す: C5 の試験で、作り直した接続（受け手を直に呼ぶ偽の DBAPI 接続）にも SET と commit が流れること、set_idle_tx_limit を 2 回呼んでも受け手は 1 つだけであること §14 で置き換え: 登録の確かめは C5'・K5' のとおり本物の Engine で行い、MagicMock では数えない |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 計算が DB の物を読み直していて、rollback 後に読み直しが走る | recon §2-2 で ORM の物を使っていないことを確認済み。K3 で結果が同じことを確かめる |
| prompt_ab で commit 前の書き込みを捨てる | C3 は書き込みが無いことを確かめてから。試験で台帳の commit が rollback より前にあることを確かめる |
| 30 秒の上限で、長い読み取りの途中の道具が切られる | P1 で最長を測ってから決めた（§11）。切られた接続は捨てられ、次は新しい接続になる。replay()・recompute() は 1 件の失敗を記録して次へ進むので、失敗の後に rollback と set_idle_tx_limit を流し直す（§12-4）。prompt_ab は失敗で止まる。どの場合も本番のデータは変わらない（読み取りだけ） |
| 別セッションの再生台本 replay_words.py | v102_replay_diff.replay を呼ぶだけなので C1 と C4 がそのまま効く（recon §2-1）。その枝には触らない。持ち主へは引き継ぎに書く |

## 8. 外部・過去事例の参照と我々への応用

- 過去事例（自社）: 2026-11-09 の 7 回の失敗（recon §1）。握り手は試しの再生の箱で、計算の間の開いた取引だった。応用: 道具の側で計算の前に閉じる（C1〜C3）。

- PostgreSQL 公式文書（runtime-config-client、Context7 /websites/postgresql で 2026-11-10 確認）: idle_in_transaction_session_timeout は「開いた取引の中で待っている接続を、指定の時間で終わらせる」。目的として「取引を開いたままの接続が鍵を持ち続けるのを防ぐ」と書かれている。この設計の C4 はこの使い方そのもの。
- SQLAlchemy 2.0 公式文書（Session の基本、Context7 /websites/sqlalchemy_en_20_orm で 2026-11-10 確認）: Session は最初の execute で取引を始め、commit か rollback まで閉じない（autobegin）。計算の前に閉じる C1〜C3 はこの仕組みに沿う。
- 数値の入った他社の導入事例: 探していない。この件は自社の 11/9 の実測（7 回失敗・握り手の特定）が直接の根拠で、他社の数値は設計の成否の証明に使わないため不要と判断した。

## 9. 維持の仕組み

- 守り手: backend/tests/test_prompt_ab_recompute.py（今ある試験。実装便で C2 の確かめを足し、C1 用に backend/tests/test_v102_replay_diff.py、C3 用に prompt_ab の試験を足す。CI の必須チェックで毎回走る）
- K4 の試験が CI の必須チェックの中で毎回走る。新しい道具を足すときは `_tx_guard` を使う。§13 の C6 で、使わない道具は必須の pytest が赤にする（審査役の目だけに頼らない）。
- 段4（接続の名前）の追補: 道具 3 つの名前を段4 の名前の表に足す。足す時期は段4 の実装のとき（段4 の担当へ引き継ぐ）。
- 段5（全件の流し直しをやめる）は別の設計のまま進める。

## 10. 自己審査（Architect・同じ AI による。独立した第二者の審査ではない）

- 判定: APPROVE（設計として合格）。ただし実装開始は P0 の PO 承認と、P1 の基準値が条件を満たすことの 2 つが揃ってから。
- 確かめたこと: 既存 ADR・段4・段5 と食い違わない（段4 §17-7 が外した DB 全体の設定には触らない・名前の正本を作らない）。受入条件は全部、数か ○× で測れる。触るファイルは backend/app/tools と試験だけで、migrations・deploy.yml・本番 scripts を含まない（ADR-136 の危険 PR ではない。ただしマージ前の GO は要る）。
- 残る未確認: recon §3 の 3 点。1 点目・2 点目は P1 で測る。3 点目（最初の失敗の握り手）はこの設計の成否に影響しない。

## 11. P1 基準値（2026-11-10 測定・直す前のコード）

- 流したもの: 本番 prod1 で、今の main の v102_replay_diff を 20 投稿（condwords/posts.txt の先頭 20 行）。別の箱 replaytx-base（読むだけ）。2026-11-09T17:11:18Z〜17:15:08Z（日本時間 11/10 02:11〜02:15）。結果 `{'posts': 20, 'items': 1018, 'errors': 0}`。
- 写し: 1 秒あけて（実際は約 1.16 秒ごと）その箱の接続の pg_stat_activity を 193 回。生の記録は prod1 /home/ubuntu/fhd-test/replaytx/base.samples、手元の写しは /tmp/CC報告ファイル/replay-tx/p1/。

| 数えたもの | 値 |
|---|---|
| 写しの数 | 193 |
| 取引を開いたまま待っていた写し（idle in transaction） | 183 |
| そのうち 1 秒以上待っていた写し（K1 の数え方） | 167 |
| 待っていた写しのうち、最後の文が投稿日の SELECT のもの | 183（全部） |
| 投稿日の SELECT 以外（読み取りの途中）で待っていた写し | 0 |
| 1 回の待ちの最長 | 49.44 秒 |
| 1 回の取引の長さの最長 | 50.42 秒 |

- 判定: 読み取りの途中で 5 秒を超えて待つ所は写っていない（§3 C4 の条件を満たす）。待ちは全部、計算の間（C1 で消す所）。上限 30 秒はこのまま使う。
- 限界: 写しは約 1.16 秒ごと。1 秒より短い待ちは数えられない（K1 の数え方も同じなので、前後の比べには使える）。

## 12. マージ前の審査（2026-11-10・REVISE）の直し

審査役（opus）の判定は REVISE。指摘 5 点をこう直した。

1. K5 の後半は SHOW を外から測れない（SHOW は自分の接続の値しか返さない）。→ `set_idle_tx_limit` が SET・commit の後に SHOW を流し、値をログへ `[tx_guard] idle_in_transaction_session_timeout=<値>` と出し、rollback で閉じる。K5 はそのログの値で判定する。
2. K2 に直す前の値が無い。→ 直す前の値は取れない（read_ms は C1 で足すログ）。1 秒にした理由: §11 で、読み取りの途中で待っていた写しは 0 件だった。読み取りは投稿ごとに SELECT が数本だけ。1 秒は「読み取りの間に計算が混ざっていない」ことを見分ける境目として置く。
3. K3 は P1 から P4 の間にマスタが変わると、この直しと関係なく × になる。→ P4 で「直す前の v102_replay_diff.py（origin/main 96a63df05 の版）を読むだけで差し込んだ箱」と「直した後の箱」を続けて流して比べる。2 回の前後でマスタの最終更新時刻も記録する。直す前の箱の写しは K1 の比べにも使う（§11 は参考の値として残す）。
4. カードの書き方の曖昧な 2 か所を直した（card.md §8）。
5. 30 秒で切られた場合の動き。→ replay()・recompute() は失敗した 1 件の後に `session.rollback()` と `set_idle_tx_limit(session)` を流し直してから次へ進む（切られた後の新しい接続にも上限を置く）。試験で確かめる。prompt_ab は今のとおり止まる。

## 13. 追補（2026-11-10）— クラウドの Architect の審査（deploy-db-stall §18 第3.2版と一緒に審査、REVISE）の直し

審査の指摘のうち、この設計に関わるもの（deploy-db-stall §18-12 の指摘 1・2・5）をこう直す。行番号は origin/main 11838e9d0。

### C5 接続を作り直しても上限が付く（指摘 1）

- 事実: 道具の接続は `backend/app/tasks/tcg_extraction.py:94` の `_engine = create_engine(_DB_URL, echo=False)` から作る。接続ごとの設定は無い。`set_idle_tx_limit`（`backend/app/tools/_tx_guard.py:23`）の SET は、そのとき使っている 1 本の接続にだけ効く。失敗の後の置き直し（§12-5。`v102_replay_diff.py:126`・`prompt_ab_recompute.py:116`）は入っているが、失敗を経ずに接続が作り直された場合（プールが接続を捨てて新しく作る等）は上限が無い。
- 前: `set_idle_tx_limit` は SET・commit・SHOW・rollback だけ。
- （§14 C5' で置き換え: 登録は別の関数に分け、bind が Engine のときだけ呼ぶ。）
- 後: `set_idle_tx_limit` が、`session.get_bind()` で得た engine に、SQLAlchemy の "connect" の受け手を 1 回だけ登録する（`sqlalchemy.event.contains` で登録済みかを見て、2 回目以降は登録しない）。受け手は新しい DBAPI 接続ができるたびに `cursor.execute("SET idle_in_transaction_session_timeout = '<秒>s'")`・`cursor.close()`・`dbapi_connection.commit()` を流す（commit しないと、プールへ返すときの rollback で SET が消えるため）。秒は `IDLE_TX_LIMIT_SECONDS`（`_tx_guard.py:16`）を正本にし、別の値を書かない。今の SET・commit・SHOW・rollback・ログはそのまま残す（今の接続の分）。
- 根拠: SQLAlchemy 2.0 の文書（Context7 /websites/sqlalchemy_en_20_core で 2026-11-10 確認。engines.html「Modify DBAPI connection after connect」）は、"connect" の受け手を engine に付けると、新しい接続ができるたびに使われる前に呼ばれ、cursor で SET を流す例を示す。同じ文書（events.html の PoolEvents.reset・SQL Execution and Connection Events）は、プールが既定（reset_on_return='rollback'）で接続を返すときに rollback すると書く。PostgreSQL の SET は取引の中で流すと rollback で取り消されるので、受け手は commit まで流す。
- 効く範囲: 受け手を登録するのは `set_idle_tx_limit` を呼んだ処理（道具の一時コンテナ）の中だけ。`backend/app` の中で `app.tools` を読み込む所は道具自身のほかに無い（`grep -rn "app\.tools" backend/app` で `backend/app/tools/` の外は 0 件）。アプリ・Celery の処理は `set_idle_tx_limit` を呼ばないので、同じ `_engine` を使っていても受け手は付かない（engine は処理（プロセス）ごとに別に作られる）。
- 戻し方: 受け手の登録の数行を消す PR を revert。DB は変えない。

### C6 共通の関数を使わない道具を機械で止める（指摘 2）

- 新しい試験 backend/tests/test_tools_tx_guard_required.py（必須チェック「pytest (SQLite + PostgreSQL RLS)」の中で走る）。
- 中身: `backend/app/tools/*.py` を全部読み（`__init__.py` と `_tx_guard.py` を除く）、本文に `_get_sync_session` か `Session(` があるのに `app.tools._tx_guard` を import していないファイルがあれば赤。理由つきの例外表（ファイル名 → 理由）にあるものは除く。例外表に載っているのに本文に `_get_sync_session` も `Session(` も無いファイルがあっても赤（古い例外を残さない）。
- 例外表（2026-11-10 の実物）: `reextract_v6_with_v102.py` → 書き込み（`_insert_rows`・`_update_job`）を含み、投稿ごとに読み取りの後で取引を閉じる（`backend/app/tools/reextract_v6_with_v102.py:456`）。共通の関数の rollback を足すと書き込みを捨てうるので対象外。開いたままの握りは本番反映の前の点検（deploy-db-stall §18 便2）が見つける。
- `sync_review_reason_labels.py` は Session を使わないので例外表に載せない（試験は何もしない）。
- 範囲外: `scripts/` の下の道具（`scripts/accuracy/llm_compare/fhd_snapshot.py` など）。わざと 1 つの写しで読む作りで計算の待ちが無い（§2）。数が多く形もばらばらなので、本番反映の前の点検に任せる。
- 赤の実演（実装 PR で 1 回、結果を PR に貼る）: (1) prompt_ab.py の `_tx_guard` の import を消すと赤 (2) 例外表から reextract_v6_with_v102.py を消すと赤 (3) 例外表に存在しないファイル名を足すと赤。

### 受入条件のあいまいさの直し（指摘 5）

- K1: 測る道を jarvis に決めた（§6 の K1）。
- K2: ログの行と数え方を決めた（§6 の K2）。
- P2: 「C5」は無かった。C1〜C4 に直した（§5）。追補の C5 は本節で新しく決めたもの。
- K4: prompt_ab の 2 回目の呼び出しを足した（§6 の K4）。deploy-db-stall §18 第3.2版の T1〜T3 はこの K4 に移した。
- C3: 実装済みの位置（:485・:547）を書いた（§3 C3）。

### 計画（追補の便）

| 順 | 中身 | 担当 | 止まる条件 |
|---|---|---|---|
| Q1 | 本節と deploy-db-stall §18 第4版をクラウドの Architect（新しく起動）で審査 | Opus | REVISE・REJECT |
| Q2 | 設計 PR → reviewer（opus）→ マージ → PO に結果を伝える | Opus | 審査 REVISE |
| Q3 | 実装カード（C5・C6・K4 の足し・K5 の足し）→ クラウドの Sonnet が実装・赤の実演 | Opus→Sonnet | 試験が赤・カードと実物の食い違い |
| Q4 | reviewer（opus）・CI 緑・GO・マージ・本番反映。migrations・deploy.yml・本番 scripts を含まない | Opus | 審査 REVISE |
| Q5 | P4 の測定（K1〜K3・K5）。C5 の後で測る | Opus | K のどれかが × |

Q1 の結果: APPROVE（2026-11-10 01:38Z、クラウドの Architect＝Opus、読むだけ）。指摘 中4 は §14 で直した。Q3 のカードは §13 と §14 の両方を入れる。

## 14. 追補の直し（2026-11-10）— §13 の審査 APPROVE の指摘 中1〜中4

行番号は origin/main c5bd38863（Opus が読み直した）。

### C5' 受け手の登録は本物の engine のときだけ（中2）

- 事実: `backend/tests/test_v102_replay_diff.py` :18 は `session = MagicMock()` で、本物の `set_idle_tx_limit` をそのまま通す。差し替えているのは `test_prompt_ab.py` :50 と `test_prompt_ab_recompute.py` :74 だけ。`test_tx_guard.py` も MagicMock を使う。
- 後: 受け手の登録を `set_idle_tx_limit` の中に直に書かず、別の関数（例 `install_idle_tx_listener(bind)`）に分ける。`set_idle_tx_limit` は `session.get_bind()` が `sqlalchemy.engine.Engine` のときだけその関数を呼ぶ（偽物の session のときは登録しない）。登録の関数は `event.contains` で登録済みなら何もしない。
- カードに書くこと: MagicMock を使う今の試験（上の3か所と test_tx_guard.py）が C5 の後も緑のままであること。赤になったら、試験の側でなく上の「Engine のときだけ」の判定を確かめる。

### K5' 本物のプールを通しても上限が残る（中3）

- 事実: アプリの async の engine には ADR-1070 の返却時の処理がある（`backend/app/database.py` :37 `_reset_session_state` が rollback → RESET ALL → commit、:50 `install_pool_reset` で async の engine の pool にだけ付ける、作る所は :33 `pool_reset_on_return=None`）。道具の `_engine`（`backend/app/tasks/tcg_extraction.py` :94）には付いていない。もし付けば RESET ALL が SET を毎回消す。
- 文書（Opus が Context7 で 2026-11-10 確認。審査では読めず未確認だった点）: SQLAlchemy 2.0 の PoolEvents.connect は「新しい DBAPI 接続がプールのために初めて作られた時」に呼ばれる（/websites/sqlalchemy_en_20_core、events.html）。プールの既定 `pool_reset_on_return='rollback'` は返すときに DBAPI の rollback を呼ぶ（pooling.html「Reset On Return」）。PostgreSQL の SET は「取引が commit されたら、その後は接続が終わるまで残る。取引が中止されたら消える」（/websites/postgresql、sql-set.html）。だから C5 の受け手が commit まで流せば、既定の返却の rollback では消えない。
- 足す試験（pytest-run の本物の PostgreSQL で。SQLite では飛ばす）: 試験の中で専用の engine を `create_engine(..., pool_size=1, max_overflow=0)` で作り、C5' の登録の関数を呼ぶ。(1) 接続を取って返し、取り直して `SHOW idle_in_transaction_session_timeout` が `30s` (2) 取った接続を `invalidate()` してから取り直し、新しい接続でも `30s` (3) 試験の後で `event.remove` で受け手を外し、engine を `dispose()`。30 の値は `IDLE_TX_LIMIT_SECONDS` から作り、試験に数字を書かない。
- 守り: もし将来、道具の `_engine` に RESET ALL の返却処理が付けば (1) が赤になる。
- 足す試験（PR #5348 の審査の推奨1）: 同じ本物の PostgreSQL の Engine に結びついた Session を作り、`set_idle_tx_limit(session)` を2回呼ぶ。`event.contains(engine, "connect", <受け手>)` が True で、受け手が1つだけ（2回目で増えない）こと。§6 K5 の「2 回呼んでも受け手は 1 つ」はこの試験で確かめ、MagicMock では確かめない（MagicMock では受け手が0件でも緑になりうるため）。赤の実演 (7): 「bind が Engine か」の判定を常に偽にすると、この試験が赤。
- 未確認（実装のときに上の試験で分かる）: `event.contains` に Engine を渡したとき、pool 側に付いた受け手を見つけるか。見つけない場合は、登録と確かめを同じ相手（Engine か pool のどちらか1つ）にそろえ、カードと食い違えば止まって Opus に戻す。

### C6' 見張りの範囲を広げる（中1・中4）

§13 の C6 をこう置き換える（同じ試験ファイル backend/tests/test_tools_tx_guard_required.py）。

- 見る範囲: `backend/app/tools/` の下を下のフォルダまで（`rglob("*.py")`）。`__init__.py` と `_tx_guard.py` は除く。
- DB を使う道具の見分け方: 本文が次の正規表現のどれかに当たる（語の区切りを付ける。PR #5348 の審査の推奨2）。`\b_get_sync_session\b`・`\bSession\(`・`\bSessionLocal\(`・`\bAsyncSessionLocal\(`・`\b_engine\b`・`\bcreate_engine\(`・`\bsessionmaker\(`・`\.connect\(`・`from app\.database import`。例: `get_engine(`（reextract_v6_with_v102.py :214、解析の版の話）は `\b_engine\b` に当たらない（前が `get` で語の区切りが無い）。`SessionLocal(` は当たる。
- 範囲外: 上の正規表現に当たらない取り方（別のモジュールの関数を通して接続を得る等）は、試験では見つけない。本番反映の前の点検（deploy-db-stall §18 便2）に任せる。
- 判定: DB を使う道具なのに、本文で `set_idle_tx_limit(` を呼んでいなければ赤（import だけでは通さない）。例外表の扱いは §13 のまま（例外表にあるのに上の語が1つも無ければ赤）。
- 漏れの見張り（中4）: `backend/app/` の下で `backend/app/tools/` の外にあるファイルが `app.tools` を読み込んでいたら赤（`from app.tools`・`import app.tools`・`from app import tools` の3つの書き方を探す）。2026-11-10 の origin/main c5bd38863 で `git grep` して該当は0件。
- 赤の実演（§13 の3つに足す。実装 PR で1回、結果を PR に貼る）: (4) prompt_ab.py の `_tx_guard` の import を残して `set_idle_tx_limit(` の呼び出しだけを消すと赤 (5) 試験の中で一時のフォルダに backend/app/tools/sub/x.py 相当の偽のファイル（`_engine.connect(` だけを持つ）を置いて見せると赤（実物のリポジトリにはファイルを足さない形で、見る根を引数で渡せる関数にして確かめる） (6) `backend/app/tasks/` の下の一時の写しに `from app.tools import prompt_ab` を置いて見せると赤（同じく根を引数で渡す）。
- 今の道具の当てはめ（2026-11-10 実物）: prompt_ab・prompt_ab_recompute・v102_replay_diff は `set_idle_tx_limit(` を呼ぶので通る。reextract_v6_with_v102 は例外表。sync_review_reason_labels は上の語が無いので対象外。実装のときに一致しなければ止まって Opus に戻す。

## 15. P4 本番測定の結果（2026-11-10 JST 04:33〜04:42・prod1・同じ 20 投稿 / 1,018 品目）

- 本番の版: 462837bee（実装のマージ 21c15eb92 を含む）。Deploy to VPS run 42683601513 success 2026-11-09T19:32:01Z。
- 生の記録: prod1 /home/ubuntu/fhd-test/replaytx/（before.*・after.*・k3/）。

| 回 | 版 | 写し数 | 取引を開いて待つ写し | うち 1 秒以上（K1） | 最長の待ち |
|---|---|---|---|---|---|
| base（§11・参考） | 直す前 | 193 | 183 | 167 | 49.44 秒 |
| before | 直す前（96a63df05 の版を差し込み） | 197 | 184 | 168 | 50.58 秒 |
| after | 直した後（本番の版） | 194 | 0 | 0 | 0 |

- K1 ○: after の 1 秒以上の写し 0（before 168）。
- K2 ×: read_ms 20 件 最小 19 / 最大 1129。1,000 以上が 5 件（1129・1001・1000・1008・1030）。その間の接続は SELECT の実行中（active）で、待ちではない。取引の長さの最大 0.90 秒。→ 遅さの元は「売り切れの参照」の 2 つの SQL（docs/handoff/soldout-ref-read-speed/recon.md）。直しは docs/handoff/soldout-ref-read-speed/design.md で扱う。
- K3 ○: 1,018 品目の比べで違い 0。before.jsonl と after.jsonl はバイト単位で同一。マスタの最終更新時刻は 4 回とも products / product_search_keywords = 2026-10-30 06:08:45 UTC。
- K4 ○: CI の必須チェックで緑（実装の PR）。
- K5 ○: ログ `[tx_guard] idle_in_transaction_session_timeout=30s`。
- KGI（試しを流しても本番反映の移行が鍵待ちで止まらない）の直接の原因（計算の間の開いた取引）は K1 で 0 になった。
