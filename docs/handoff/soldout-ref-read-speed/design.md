# design — 「売り切れの参照」の読み取りを速くする（1 投稿 約 1 秒 → 2 つの SQL の合計を 3 回の真ん中の値で 0.15 秒未満）

- 状態: 設計案（Opus 作成・自己審査済み）。PO 承認はまだ。実装は未着手。2026-11-10 に §8（外の事例）と §9（維持の仕組みを実物で確かめた表）を書き足した。
- 根拠: docs/handoff/soldout-ref-read-speed/recon.md（行番号は origin/main 11838e9d0）。
- 前の件: docs/handoff/replay-tx-release/design.md の P4 で K2（1 投稿の読み取りの最長が 1 秒未満）が ×。この設計はその続き。
- 関係する決まり: ADR-135・ADR-136（危険なパスの扱い。この設計は migrations・deploy.yml・本番 scripts に触らない）・ADR-1037（移行の鍵待ち 1 秒）・ADR-1070（接続の返却時の後始末）。

## 1. 目的（KGI）

〆（売り切れ）の件が参照する過去の投稿の解析結果を読む時間を、1 投稿あたり、2 つの SQL の合計を 3 回流した真ん中の値で 0.15 秒未満、どの回も 0.2 秒未満にする。読む中身は 1 行も変えない。

- 利用者に見える変化: LINE 解析で、過去の投稿を参照する投稿（20 投稿中 15）の処理が 1 投稿あたり約 0.8〜2.2 秒短くなる（recon §1-1）。本番の解析はこの読み取りを投稿ごとの鍵を持った取引の中で行う（recon §1-3）。そのため、取引の長さも同じだけ短くなる。
- 試しの道具（再生・試算）でも同じだけ短くなる。前の件の K2 が ○ になる。

## 2. 対象と対象外

| 区分 | 中身 | 理由 |
|---|---|---|
| 対象 | `backend/app/services/line_analysis_v102_svc.py:1424-1437` `_STOCK_ITEMS_SQL` の FROM と最新の job の条件 | 遅さの元（recon §1-4） |
| 対象 | `backend/app/services/line_analysis_v102_svc.py:1440-1451` `_SOLD_ITEMS_SQL` の同じ部分 | 同上 |
| 対象 | 試験 `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py`（CI の使い捨て PostgreSQL）・`backend/tests/test_line_analysis_v102_svc.py` に足す | 中身が変わらないことと、遅い形に戻らないことを機械で守る |
| 対象外 | `_INHERIT_PRICE_SQL`（前の価格の引き継ぎ。同じ形で 1 回最大 2.3 秒） | 本番で何回呼ばれるかをまだ測っていない（recon §4・§6）。測ってから次の段で設計する（§9） |
| 対象外 | 索引の追加（extraction_items.extraction_job_id・extraction_jobs.source_message_id） | 移行が要り ADR-135/136 の危険なパスになる。書き換えだけで目的（§1）に届くので今は要らない（§4） |
| 対象外 | DB 全体の JIT の設定 | ほかの全部の問い合わせの動きが変わる。その影響を測っていない（§4） |
| 対象外 | 外側の並べ方（ORDER BY）・選ぶ列・その他の条件・行を組む関数 | 読む中身を変えないため。触らない |

## 3. 変更前と変更後

### C1 `_STOCK_ITEMS_SQL`（`backend/app/services/line_analysis_v102_svc.py:1424-1437`）

変更前（:1428-1433 の部分）:

```sql
    FROM {schema}.extraction_jobs ej
    JOIN {schema}.extraction_items ei ON ei.extraction_job_id = ej.id
    JOIN {schema}.analysis_results ar ON ar.extraction_item_id = ei.id
    WHERE ej.source_message_id = ANY(CAST(:ids AS uuid[]))
      AND ej.id = (SELECT j2.id FROM {schema}.extraction_jobs j2 WHERE j2.source_message_id = ej.source_message_id
                   ORDER BY j2.created_at DESC, j2.id DESC LIMIT 1)
      AND ar.pid_resolved = TRUE ...
```

変更後:

```sql
    FROM (SELECT DISTINCT ON (j.source_message_id) j.id, j.source_message_id FROM {schema}.extraction_jobs j
          WHERE j.source_message_id = ANY(CAST(:ids AS uuid[]))
          ORDER BY j.source_message_id, j.created_at DESC, j.id DESC) ej
    JOIN {schema}.extraction_items ei ON ei.extraction_job_id = ej.id
    JOIN {schema}.analysis_results ar ON ar.extraction_item_id = ei.id
    WHERE ar.pid_resolved = TRUE ...
```

- SELECT の列（:1425-1427）・残りの条件・ORDER BY（:1436）はそのまま。`ej.source_message_id` の名前もそのまま使える（副問い合わせが同じ名前の列を返す）。
- 「その投稿の最新の job」の決め方（created_at の新しい順・同じなら id の大きい順）は変えない。この決め方は 2 か所（C1・C2）に同じ文で書く。今もそうなっている。

### C2 `_SOLD_ITEMS_SQL`（`backend/app/services/line_analysis_v102_svc.py:1440-1451`）

C1 と同じ置き換え。`AND ar.status = :sold_out` と ORDER BY（:1450）はそのまま。

### C3 試験

1. `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py`（CI の使い捨て PostgreSQL・:438 の試験の隣）に足す: 同じ投稿に created_at が同じで id だけ違う job が 2 つあるとき、id の大きい job の結果だけを読む（stock と sold の両方）。
2. 同じファイルに足す: 参照する投稿が 2 つあり、それぞれ古い job と最新の job を持つとき、投稿ごとに最新の job の結果だけを読み、外側の並べ方（投稿・行の順）が変わらない。
3. `backend/tests/test_line_analysis_v102_svc.py`（:1044 の隣）に足す: 2 つの SQL に相関副問い合わせの文（`j2.source_message_id = ej.source_message_id`）が無く、`DISTINCT ON (j.source_message_id)` と `ORDER BY j.source_message_id, j.created_at DESC, j.id DESC` があること（遅い形に戻すと赤になる）。
- 今ある試験（recon §5）は変えずに緑のままであること。

## 4. 代替案と選んだ理由

| 案 | 中身 | 本番での実測（recon） | 判定 |
|---|---|---|---|
| A（採用） | 問い合わせの形を直す（C1・C2） | 14.9〜84.8 ms・JIT 0/15・行と順番が全部一致 | 遅さの元（見積もりの大きさ）を直に消す。設定も移行も要らない |
| B | 読む前に `SET LOCAL jit = off` | 42.7〜101.4 ms・行が全部一致 | A より遅い。本番の解析の取引では、後の書き込みの文にも設定が残る（PostgreSQL の SET LOCAL は取引の終わりまで効く）。戻す手間と、途中で失敗したときの扱いが増える |
| C | 索引を 2 つ足す（移行） | 測っていない | 危険なパスになる。大きな表に索引を作る間の鍵の扱いが要る。A で届くので今は要らない。表が大きくなり A でも K1 が × になったら考える（§9） |
| D | DB 全体で JIT を止める | 測っていない | ほかの全部の問い合わせに効く。影響を測っていない |

## 5. 計画（順番に。変更は一度に 1 つ）

| 順 | 中身 | 担当 | 止まる条件 |
|---|---|---|---|
| P0 | この設計を PO が承認（KGI と実装の許可） | PO | 不承認 |
| P1 | 実装カードを書き、クラウドの Sonnet が C1〜C3 を実装 | Opus→Sonnet | 試験が赤 |
| P2 | マージ前の審査役（opus）・CI 緑・GO・マージ・本番反映 | Opus | 審査 REVISE |
| P3 | 測定: 本番反映の後、前の件の 20 投稿で K1〜K3 を測る（前の件の P4 と同じ台本。直す前のファイルを差し込んだ箱と、本番の版の箱を続けて流す） | Opus | K のどれかが × |

戻し方: P3 で K3（読む中身が同じ）が ×、または本番の解析の結果が変わったと分かったときは、実装の PR を `git revert -m 1 <マージの記録>` で打ち消す PR を出し、マージ前の審査役・CI 緑・GO を経て本番に反映し直す。反映の後、P3 と同じ台本で再生の出力を取り、直す前の出力と cmp で 1 バイトも違わないことを確かめる。K1・K2・K5 だけが × のとき（中身は同じで速さが足りないとき）は戻さず、案 C（索引）の設計に進む。変更は SQL の文と試験だけなので、DB とデータの戻しは要らない。

## 6. 受入条件（KPI）

| 基準 | 検証方法 |
|---|---|
| K1 2 つの SQL の時間: 参照のある全投稿で、それぞれどの回も 100 ms 未満。1 投稿の 2 つの合計は 3 回の真ん中の値で 150 ms 未満、どの回も 200 ms 未満（書き換え案の本番の試し: それぞれ最大 84.8 ms、同じ回同士を足した合計の 3 回の真ん中の値の最大 98.3 ms、合計の各回の最大 132.0 ms・45 回中 9 回が 100 ms 以上） | P3 で本番の版の SQL を 20 投稿に 3 回ずつ流して計る（recon §3 と同じ台本）。直す前の値（recon §3: 387.8〜1378.3 ms）と表で並べる |
| K2 前の件の K2: 再生の道具の 1 投稿の読み取り（read_ms）の最大が 1000 ms 未満 | P3 で再生を 20 投稿流し、ログの read_ms の最大を見る。直す前の値は前の件の P4（最大 1129 ms・1000 以上 5 件） |
| K3 読む中身が直す前と同じ | P3 で直す前と後の再生の出力（20 投稿・1,018 品目）が 1 バイトも違わない（cmp）。diff の changed 0。2 回の間のマスタの最終更新時刻を併記 |
| K4 試験 | C3 の 3 つが CI の使い捨て PostgreSQL で緑。今ある試験も緑 |
| K5 書き換えた SQL に JIT が付かない | P3 で 20 投稿の EXPLAIN に「JIT:」の行が 0 |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 書き換えで読む中身が変わる | recon §3 で 15 投稿×2 SQL×6 回が全部一致（行と順番）。C3 の 1・2 で同点と複数投稿を試験する。P3 の K3 で 20 投稿の結果をバイト単位で比べる |
| 表が大きくなると、また遅くなる | 今の残りの時間は extraction_items 全件の読み（recon §2 の JIT なしの計画で約 9 ms＋Memoize）。行が増えるとほぼ比例して増える。K1 が × になったら案 C（索引）を設計する。見張りは §9 |
| 本番の解析の結果が変わる | 本番の解析も同じ関数を通る（recon §1-3）。K3 は同じ関数の結果を比べるので、本番の解析の読み取りも同じことを確かめている。書き込みの部分には触らない |
| K1 の境目と実測の余裕が小さい | 書き換え案の本番の試しで、余裕は SQL それぞれ 15.2 ms（最大 84.8 ms／境目 100 ms）、合計の真ん中の値 51.7 ms（最大 98.3 ms／境目 150 ms）、合計の各回 68.0 ms（最大 132.0 ms／境目 200 ms）。最初の案は合計の真ん中の値の境目を 100 ms にしていたが、計算の誤り（SQL ごとの真ん中の値を足した 83.9 ms を使った）で余裕を大きく見ていた。正しい値 98.3 ms では余裕 1.7 ms で、回ごとの揺れ（recon §3）だけで × になるため、境目を 150 ms に直した。PO 承認前の設計案の数で、PO の言葉を変えたものではない。P3 で × のときは §5 の戻し方のとおり、中身が同じなら戻さず原因を測る |
| DISTINCT ON で残る行が決まらない（§8-2 F1） | 並べ方の最後に id の大きい順を入れ、同じ時刻でも 1 つに決める（§3）。C3 の 1 で同じ時刻の 2 つの job を試す |

## 8. 外部・過去事例の参照と我々への応用

2026-11-10 に調べた。ページの本文を開く道は 2 つとも使えなかった。手元でページを読む係は、手元で起動できる担当の決まり（PO 2026-10-26・10-30）の見張りが止めた。クラウドの係は、6 つのサイトに名前解決できなかった（getaddrinfo ENOTFOUND。クラウドの通信の許可先の外）。そのため、下の他社の数値は Opus の WebSearch（extended）が返した要約の値で、ページ本文の文字どおりかはまだ確かめていない（【未確認】）。PostgreSQL 公式文書の 2 件は Context7（/websites/postgresql）で本文を確かめた（【事実】）。

### 8-1. 成功事例（5W2H）

| 事例 | いつ・誰が | どこで・何を | なぜ（原因） | どうやって | どれだけ（数値） |
|---|---|---|---|---|---|
| S1 | 2023-11-09・Adam Johnson（Django の開発者） | Django の多段の結合の問い合わせ（PostgreSQL） | 結合が多く見積もりの費用が大きくなり、JIT が走った。返す行は少ない。JIT の翻訳が実行時間の 99.7% | 接続の設定で jit=off | 試験 1 本が 3.5 秒 → 10 ミリ秒（[adamj.eu](https://adamj.eu/tech/2023/11/09/django-disable-postgresql-jit/)、[Scaling Postgres 290](https://www.scalingpostgres.com/episodes/290-postgres-releases-equals-reindexing/)）【未確認】 |
| S2 | 2019-10・PostgreSQL の不具合報告 #16076（PostgreSQL 12.0） | 複雑な問い合わせ 1 本 | JIT | jit=off | 5〜10 秒 → ミリ秒台（[postgrespro.com](https://postgrespro.com/list/thread-id/2463538)）【未確認】 |
| S3 | 2020-01〜10・osm2pgsql（地図データの取り込み道具） | 更新の取り込みの問い合わせ | JIT と並列。PostgreSQL 12 で JIT が既定で on になった | jit=off と並列 0 | 実行 0.079 ms（止めた後。止める前の値は要約に無い）。道具の側で JIT を止める直しを入れた（[osm2pgsql 2020-10-21](https://osm2pgsql.org/news/2020/10/21/problems-with-postgresql-jit.html)、[PR #1256](https://github.com/openstreetmap/osm2pgsql/pull/1256)）【未確認】 |
| S4 | 2026-04-02・PostgreSQL 本体（Tomas Vondra が反映、Jelte Fennema-Nio の案） | PostgreSQL 19 の既定値 | 関係の薄い変更（INSERT を数件足す等）で見積もりが境目を越え、急に遅くなる（性能の崖）。大きな運用者の多くは既に JIT を止めている | jit の既定を off に。境目の値は変えない | 数値なし（[commit の告知](https://www.postgresql.org/message-id/E1w8GWU-002bSL-31@gemulon.postgresql.org)、[Neon の 19 の変更一覧](https://neon.com/postgresql/postgresql-19/breaking-changes)）【未確認】 |

我々への応用:
- 我々の件も同じ形だった。返す行は少ない（1 投稿で数十行）。見積もりだけが 1,219,003 に膨らみ、境目 100,000 を越えて翻訳が実行 876 ms のうち 760 ms（約 87%）を占めた（recon §1-4・自社の本番実測）。S1 の 99.7% と同じ種類の遅さ。
- S4 の「関係の薄い変更で急に遅くなる」は、我々の表が育つと他の問い合わせでも起こりうる。本番は PostgreSQL 16.13・jit on・jit_above_cost 100000（2026-11-10 reader の道で SHOW。§9）。
- 他社は「JIT を止める」で直した。我々は「問い合わせの形を直して見積もりを 3,318〜3,412 に下げる」で直す（案 A）。理由は §4（止める設定は取引の後の書き込みにも残る）。形を直すと JIT の境目から遠くなるので、S4 の崖からも離れる。

### 8-2. 失敗事例・限界（5W2H）

| 事例 | いつ・誰が | 何を | 何が起きたか・起こりうるか | 数値 |
|---|---|---|---|---|
| F1 | PostgreSQL 公式文書（SELECT の DISTINCT の節） | DISTINCT ON | ORDER BY で順番を十分に決めないと、各組で残る行が予測できない。DISTINCT ON の式は ORDER BY の左端と一致が要る | 数値なし（Context7 で本文確認【事実】） |
| F2 | 2019-06・HighGo（PostgreSQL 11 の測定） | JIT を止める側の損 | 重い集計の問い合わせでは JIT が効く。TPC-H 22 本の合計で JIT on が約 6.1% 速い。Q1 では PostgreSQL 10 比で 29.31% 速い（20.5 秒 対 29 秒） | 上のとおり（[HighGo](https://www.highgo.ca/2019/06/12/the-jit-benchmarking-results-and-findings-in-postgresql-11/)）【未確認】 |
| F3 | WebSearch の要約が挙げた古いスレッド | JIT を止めて遅くなった例 | 商品検索の問い合わせで JIT off 2.5 秒・on 0.4 秒 | 出典の URL を特定できなかった。根拠に使わない |

我々への応用:
- F1 の対策は設計に入っている。並べ方を「投稿 → 作った時刻の新しい順 → id の大きい順」にして、同じ時刻でも残る行が 1 つに決まる（§3）。C3 の 1 が同じ時刻の 2 つの job で試す。本番の試しでも 15 投稿 × 2 SQL × 6 回の行と順番が全部一致した（recon §3）。
- F2 のとおり、DB 全体で JIT を止めると重い集計が遅くなるおそれがある。だから DB 全体の設定（案 D）は採らない。今回の直しは 2 つの問い合わせの形だけで、ほかの問い合わせの JIT には触らない。
- 「DISTINCT ON に書き換えて遅くなった」という数値つきの外の事例は見つからなかった。速さの根拠は自社の本番の実測（同じ投稿・同じデータで前後を比べた値。recon §3）だけにする。他社の数値は設計の成否の証明に使わない。

### 8-3. 自社の過去事例

- 前の件の P4 の実測（K2 ×・最大 1129 ms）。

## 9. 維持の仕組み（2026-11-10 に実物で確かめた）

| 守ること | 仕組み | 今あるか | 根拠 |
|---|---|---|---|
| 遅い形（相関副問い合わせ）に戻らない | C3 の 3（文の形を調べる試験） | 実装の後にできる | §3 C3 |
| 読む中身が変わらない | C3 の 1・2 と今ある `test_sold_items_and_stock_items_are_read_apart_from_the_latest_job_with_resolved_products`（本物の PostgreSQL） | 今あるものは有り。足す 2 本は実装の後 | `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py:438` |
| 試験が、backend を変えた PR では毎回、本物の PostgreSQL で流れる | 本線の必須チェック「pytest (SQLite + PostgreSQL RLS)」。backend を変えたときに全部の試験を postgres:16 で流す（変えないときは試験を飛ばして通る。`.github/workflows/test.yml:117`）。実装の PR は backend を変えるので必ず流れる | 有り | `gh api repos/shingo-ops/salesanchor/rules/branches/main` の必須チェック一覧、`.github/workflows/test.yml:122-123`・`:218`・`:253` |
| 本物の DB が無いときに試験が黙って飛ばされない | DB の接続先が無いと失敗する（飛ばさない） | 有り | `backend/tests/test_tcg_work_matching_integration.py:388`（assert） |
| 本番で遅い問い合わせが出たら気づく | 遅い問い合わせの記録・集計 | **無い** | 本番 2026-11-10 reader の道: `log_min_duration_statement` = -1（記録しない）、拡張は pg_trgm・plpgsql だけ（pg_stat_statements 無し）、auto_explain の設定は無い（42704）。docs/adr・docs/specs に遅い問い合わせの見張りを決めた ADR は無い（git grep 0 件。precision-benchmark.md の 1 件は別の話） |

- 守り手: 実装の後は、遅い形に戻すと必須チェックが赤になり、本線に入れられない。中身が変わっても赤になる。
- 足りないもの: 本番で、ほかの問い合わせが同じ種類の遅さ（S4 の性能の崖）になっても、今は機械で気づけない。`_INHERIT_PRICE_SQL` が既に同じ形で 1 回最大 2.3 秒かかる（recon §4）のも、手で測って見つけた。
- 足りないものへの手当て（この設計の外・別の設計）: 本番の DB に遅い問い合わせの記録（例: log_min_duration_statement か pg_stat_statements）を入れ、決まった時間を超えたら知らせる。DB の設定を変えるので、PO の判断と別の設計（ADR 級）が要る。この設計では作らない。
- 次の段（別の設計）: `_INHERIT_PRICE_SQL` の本番での呼ばれる回数を測ってから、同じ直し方が使えるかを設計する。数える SELECT は見張りに止められたので、読み取り専用の道（reader）で流す方法を次の段の最初に決める。
- PostgreSQL 19 への上げ（S4）: 19 は jit の既定が off。上げるときは、JIT に頼る重い集計が遅くならないかを測る。今の本番は 16.13 で、上げる予定を決めた記録は見ていない（【未確認】）。

## 10. 自己審査（Architect・同じ AI による。独立した第二者の審査ではない）

- 判定: APPROVE（設計として合格）。ただし実装開始は P0 の PO 承認の後。
- 確かめたこと: 既存の ADR と食い違わない（JIT・この 2 つの索引を決めた ADR と移行は無い。recon §0）。触るファイルは backend/app/services の 2 つの SQL の文と試験だけで、migrations・deploy.yml・本番 scripts を含まない（ADR-136 の危険な PR ではない。マージ前の審査と GO は要る）。受入条件は全部、数か ○× で測れる。変更前と変更後の文、触らない範囲を書いた。
- 残る未確認: recon §6 の 3 点。1 点目（今の形の時間の振れ）は成否に効かない。2 点目（引き継ぎの回数）は対象外にした。3 点目（20 投稿での一致）は P3 の K3 で確かめる。
- 2026-11-10 の追記（§8・§9）の自己審査: 外の事例は設計を変えなかった（他社は JIT を止めて直し、我々は形を直す。理由は §4）。DISTINCT ON の落とし穴（§8-2 F1）は §3 の並べ方と C3 の 1 で既に塞いでいる。維持の仕組みのうち「本番で遅い問い合わせに気づく」だけが無い（§9）。これはこの設計の受入条件に効かないので、この設計の判定は APPROVE のまま。別の設計として PO に示す。
