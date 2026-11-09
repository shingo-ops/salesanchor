# design — 試しの道具が計算の間に取引を開いたままにしない（本番反映の移行を止めない）

- 状態: 設計案（Opus 作成・自己審査済み）。PO 承認前。実装は未着手。
- 根拠: 同じ場所の recon.md（行番号は origin/main 96a63df05）。
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
- 後: Gemini を呼ぶ繰り返しの直前で取引を閉じる。ただし閉じる前に「取引の中にまだ commit していない書き込みが無い」ことを実装役が確かめる（:601 の台帳の commit の後なら無い見込み。確かめられなければ止めて設計へ戻す）。閉じ方は `session.commit()` ではなく `session.rollback()`（書き込みが無いことを試験で確かめた上で）。

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
| P2 | 実装カードを書き、クラウドの Sonnet が C1〜C5 を実装 | Opus→Sonnet | 試験が赤 |
| P3 | マージ前の審査役（opus）・CI 緑・GO・マージ・本番反映 | Opus | 審査 REVISE |
| P4 | 測定: 本番で同じ 20 投稿を流し、同じ写しで K1〜K3 を測る | Opus | K のどれかが × |

## 6. 受入条件（KPI）

| 基準 | 検証方法 |
|---|---|
| K1 道具の接続が「取引を開いたまま 1 秒以上待つ」写しの数が 0 | P4 で 1 秒ごとに pg_stat_activity を写し、`state='idle in transaction' AND now()-state_change >= 1s` の行を数える。P1 の基準値（直す前）と並べて表で示す |
| K2 1 投稿の読み取りにかかる時間の最長が 1 秒未満 | 道具が投稿ごとに read_ms をログへ出す（C1 で足す）。最大値を見る |
| K3 再生の結果が直す前と同じ | P1 と P4 の出力（20 投稿の各品目の結果）を diff して差が 0 行 |
| K4 C1〜C3 で「計算の前に取引を閉じる」を試験で確かめる | 呼んだ順を記録する試験（session の偽物）で、計算の関数より前に rollback が 1 回あり、その間に execute が無いことを確かめる。3 道具とも緑 |
| K5 待ちの上限が効いている | 試験で `set_idle_tx_limit` が SET と commit をこの順で呼ぶこと。P4 で道具の接続の `SHOW idle_in_transaction_session_timeout` が 30s |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 計算が DB の物を読み直していて、rollback 後に読み直しが走る | recon §2-2 で ORM の物を使っていないことを確認済み。K3 で結果が同じことを確かめる |
| prompt_ab で commit 前の書き込みを捨てる | C3 は書き込みが無いことを確かめてから。試験で台帳の commit が rollback より前にあることを確かめる |
| 30 秒の上限で、長い読み取りの途中の道具が切られる | P1 で最長を測ってから決める。切られた場合は道具がエラーで止まるだけで、本番のデータは変わらない（読み取りだけ） |
| 別セッションの再生台本 replay_words.py | v102_replay_diff.replay を呼ぶだけなので C1 と C4 がそのまま効く（recon §2-1）。その枝には触らない。持ち主へは引き継ぎに書く |

## 8. 外部・過去事例の参照と我々への応用

- 過去事例（自社）: 2026-11-09 の 7 回の失敗（recon §1）。握り手は試しの再生の箱で、計算の間の開いた取引だった。応用: 道具の側で計算の前に閉じる（C1〜C3）。

- PostgreSQL 公式文書（runtime-config-client、Context7 /websites/postgresql で 2026-11-10 確認）: idle_in_transaction_session_timeout は「開いた取引の中で待っている接続を、指定の時間で終わらせる」。目的として「取引を開いたままの接続が鍵を持ち続けるのを防ぐ」と書かれている。この設計の C4 はこの使い方そのもの。
- SQLAlchemy 2.0 公式文書（Session の基本、Context7 /websites/sqlalchemy_en_20_orm で 2026-11-10 確認）: Session は最初の execute で取引を始め、commit か rollback まで閉じない（autobegin）。計算の前に閉じる C1〜C3 はこの仕組みに沿う。
- 数値の入った他社の導入事例: 探していない。この件は自社の 11/9 の実測（7 回失敗・握り手の特定）が直接の根拠で、他社の数値は設計の成否の証明に使わないため不要と判断した。

## 9. 維持の仕組み

- 守り手: backend/tests/test_prompt_ab_recompute.py（今ある試験。実装便で C2 の確かめを足し、C1 用に backend/tests/test_v102_replay_diff.py、C3 用に prompt_ab の試験を足す。CI の必須チェックで毎回走る）
- K4 の試験が CI の必須チェックの中で毎回走る。新しい道具を足すときは `_tx_guard` を使う（使わない道具は審査役が指摘する。docs/ai-agents/executor-checklist.md への追記は実装便で行う）。
- 段4（接続の名前）の追補: 道具 3 つの名前を段4 の名前の表に足す。足す時期は段4 の実装のとき（段4 の担当へ引き継ぐ）。
- 段5（全件の流し直しをやめる）は別の設計のまま進める。

## 10. 自己審査（Architect・同じ AI による。独立した第二者の審査ではない）

- 判定: APPROVE（設計として合格）。ただし実装開始は P0 の PO 承認と、P1 の基準値が条件を満たすことの 2 つが揃ってから。
- 確かめたこと: 既存 ADR・段4・段5 と食い違わない（段4 §17-7 が外した DB 全体の設定には触らない・名前の正本を作らない）。受入条件は全部、数か ○× で測れる。触るファイルは backend/app/tools と試験だけで、migrations・deploy.yml・本番 scripts を含まない（ADR-136 の危険 PR ではない。ただしマージ前の GO は要る）。
- 残る未確認: recon §3 の 3 点。1 点目・2 点目は P1 で測る。3 点目（最初の失敗の握り手）はこの設計の成否に影響しない。
