# design: 現行行の復活止め

関連: docs/handoff/revival-guard/recon.md（現在地）、docs/adr/ADR-1032-current-row-revival-guard.md、docs/adr/ADR-158-product-level-supersession.md、docs/adr/ADR-1027-bundle-sale-reading.md。
PO 決定（2026-10-19, n）: 現行の規則「商品×状態の組ごとに最新の投稿の行が現行」を保つ（2026-09-25 の d24d13249 の設計を守る。古い投稿の別の状態の行は残る）。直すのは「再解析で行の状態や商品が変わったとき、新しい投稿に隠されていた古い投稿の行を現行に戻さない」ことだけ。

## 1. 規則（復活止め）

付け直しで、ある行が「新しく現行になる」（前は現行でなかった行が TRUE になる、または新しく作られた行が TRUE のまま残る）のは、次のどちらかを満たすときだけ。満たさなければ FALSE にする。

- (i) 同じ仕入元の、より新しい投稿（received_at が大きい）に、同じ商品の行（仮の行を含む）が無い。
- (ii) その行の (投稿, 商品, 状態) が、この付け直しの前から現行だった。

すでに現行の行はこの規則では落とさない（落ちるのは今まで通り、より新しい投稿に同じ組があるときだけ）。

## 2. 実装の場所と前後の差

実装先（設計の時点では変更していない。→ 2026-10-19 #4533 で実装・本番反映済み。結果は ADR-1032 末尾）: `backend/app/services/tcg_analyzer_svc.py:2083`（`ranked`）と `:1964`（引数）。控えを取る読みは `backend/app/services/line_analysis_v102_svc.py:1461`（`_load_resolved_pairs` の隣に `_load_current_pairs` を足す）。試験用の完全な関数は `docs/handoff/revival-guard/sandbox/merge_guard.sql`。

SQL 前（`backend/app/services/tcg_analyzer_svc.py:2083-2088`）:
```sql
ranked AS (
    SELECT c.id, (c.job_id = t.job_id) AS should_be_current
    FROM candidates c JOIN top_job t ON t.product_id = c.product_id AND t.condition_id = c.condition_id
)
```
SQL 後（`candidates` の実の行に `was_current` を足す。仮の行は TRUE）:
```sql
-- candidates の実の行に追加
CASE WHEN ej.id = :job_id AND CAST(:prior_pids AS integer[]) IS NOT NULL
     THEN EXISTS (SELECT 1 FROM unnest(CAST(:prior_pids AS integer[]), CAST(:prior_cids AS integer[])) AS pr(product_id, condition_id)
                   WHERE pr.product_id = ar.product_id AND pr.condition_id IS NOT DISTINCT FROM ar.condition_id)
     ELSE ar.is_current END AS was_current
-- ranked
SELECT c.id,
       (c.job_id = t.job_id)
       AND (NOT :revival_guard OR c.was_current
            OR NOT EXISTS (<同じ仕入元で received_at が c より大きい投稿に、同じ product_id の行 または 仮の行>)) AS should_be_current
```
Python 前後（`backend/app/services/tcg_analyzer_svc.py:1964`）:
```python
# 前
def _merge_supplier_products(session, extraction_job_id, schema, extra_pairs=()):
# 後
def _merge_supplier_products(session, extraction_job_id, schema, extra_pairs=(),
                             prior_current_pairs=None, revival_guard=True):
    # prior_current_pairs=None: 控え無し（行の今の is_current を「前から現行」とみなす）
    prior = None if prior_current_pairs is None else sorted({(int(p), int(c)) for p, c in prior_current_pairs})
    # バインド: prior_pids = None if prior is None else [p for p, _ in prior]、prior_cids も同様。revival_guard
```
`backend/app/services/line_analysis_v102_svc.py:1461` の隣: `prior_current = _load_current_pairs(...) if previous_pairs else None`（前の行が 1 つも無い＝初回は None）。`:1476` で `prior_current_pairs=prior_current` を渡す。

## 3. 呼び出し元 5 か所への効き方

| # | 呼び出し | 渡すもの | 効き方 |
|---|---|---|---|
| 1 | v6 解析 `backend/app/services/tcg_analyzer_svc.py:1956` | 控え無し・guard あり | 新しい行は既定 TRUE なので ELSE 側で TRUE＝規則は働かない（初回は今と同じ）。同じ件を再解析して組が変わった行は古い is_current を持ち越すので、FALSE だった行は戻らない |
| 2 | v102 解析 `backend/app/services/line_analysis_v102_svc.py:1476` | 書く前の「現行だった組」。前の行が無ければ None | 本件の主対象。R1・R3a・R3c・R5 を止める |
| 3 | 件の削除 `backend/app/services/v102_transcription_svc.py:382`（組は `:370` で読む） | guard なし（`revival_guard=False`） | 削除は再解析ではない。試験 D1 で、guard ありだと新しい投稿に同商品の別状態が残るとき古い行が戻らなくなることを確認した。今まで通り戻す（D1b）。G5（`backend/app/services/v102_transcription_svc.py:381` のコメント）の「削除した件が最新だった組は次に新しい投稿の件を最新に戻す」を守るため |
| 4 | 再抽出ツール `backend/app/tools/reextract_v6_with_v102.py:353` | 組を控える `:434` と同時に「現行だった組」も控え、`:439` の保存ファイルに載せる。前の行が無ければ None | 再抽出は件を作り直し新しい行が TRUE になるため、控えが無いと規則が使えない。控えて渡す |
| 5 | 取り消し `backend/app/tools/reextract_v6_with_v102.py:741` | guard なし | 取り消しは保存した行を戻す操作。現行を動かさない方に倒す（今と同じ）。【未確認】guard ありで問題が出るか |

- 既知の限界（実装便で確認）: Celery の抽出やり直し経路（`backend/app/tasks/tcg_extraction.py:470-476`）では、抽出（`backend/app/services/line_analysis_v102_svc.py:519` の件の削除）で行が消え、続く `run_v102_analysis`（`:1461`）に着く時点で前の行が無い。`previous_pairs` も控えも空（None）になり、初回の解析（S1）と同じ扱いで、その job 自身の行（R3a 型）は復活止めが働かない。他の投稿の行（R1・R3c・R5）は今の `is_current` を控えに使うので、どの経路でも止まる。試験 `test_extraction_restart_path_has_no_prior_and_behaves_like_first_analysis` で「初回と同じ（TRUE のまま）」を固定した。

## 4. 試験の結果（試験用 PG 16.15, port 55460。原本 logs/sandbox_old.txt・logs/sandbox_guard.txt）

作り方: 本物の再解析は件を作り直す（`backend/app/services/line_analysis_v102_svc.py:519`）。試験では行を消す代わりに `extraction_items.gone` 列で印を付け、古い件を gone=true にして新しい id で入れ直した。現行 SQL（old）と案（guard）の両方の関数は gone=false の件だけを見る。old と guard は、場面ごとに空の使い捨て DB を新しく作って同じ入力を流した（DB の作り直しは使っていない）。

| シナリオ | 行 | old（現行SQL） | guard（案） | 期待 | 判定 |
|---|---|---|---|---|---|
| S1 新 A/Single・旧 A/Error（初回） | 旧 A/Error | TRUE | TRUE | 同じ（別状態は残る） | ○ |
| S2 新に A 無し | 旧 A / 旧 B | TRUE / FALSE | TRUE / FALSE | 同じ | ○ |
| S3 〆だけの投稿 | 旧 A | TRUE | TRUE | 同じ | ○ |
| S5 仮の行 | 旧 A/Box / A/Case | FALSE / TRUE | FALSE / TRUE | 同じ | ○ |
| S6 同投稿の複数行 | 3 行 | 全 TRUE | 全 TRUE | 同じ | ○ |
| S7 同順位 | a / b | TRUE / TRUE | TRUE / TRUE | 同じ | ○ |
| S8 旧 A/Box・A/Case、新 A/Box | 旧 A/Box / A/Case | FALSE / TRUE | FALSE / TRUE | 同じ | ○ |
| S9 古い投稿を後から初回解析 | 旧 A/Error | TRUE | TRUE | 同じ（控え無し） | ○ |
| R1（S4）最新の再解析 A/Error→A/Single | 旧 A/Error / 新 A/Single | TRUE / TRUE | FALSE / TRUE | 復活しない | ○ |
| R2 最新の再解析 A→B | 旧 A / 新 B | TRUE / TRUE | TRUE / TRUE | 旧 A は戻る | ○ |
| R3a 古い X を再解析 (A,Error)→(A,Single)、Y に A あり | X A/Single / X A/Damaged | TRUE / TRUE | FALSE / TRUE | FALSE・Damaged は残る | ○ |
| R3b 同じ、Y に A 無し | X A/Single / X A/Damaged | TRUE / TRUE | TRUE / TRUE | TRUE・Damaged は残る | ○ |
| R3c 隠れていた最古 Z の行 | Z A/Error | TRUE | FALSE | 復活しない | ○ |
| R5（9/25 の設計）新 A/Sealed→A/Single | 旧 A/Sealed / 旧 A/Damaged | TRUE / TRUE | FALSE / TRUE | Sealed は戻らず Damaged は残る | ○ |
| R6（9/25 の設計）再解析で変わらない | 旧 A/Sealed / 旧 A/Damaged | FALSE / TRUE | FALSE / TRUE | 変化なし | ○ |
| D1 件の削除（guard あり） | 旧 A/Single | TRUE | FALSE | 戻したい → 削除では guard を切る | 要注意 |
| D1b 件の削除（guard なし） | 旧 A/Single | TRUE | TRUE | 戻る | ○ |
| D2 新の A を全部消した | 旧 A/Single | TRUE | TRUE | 戻る | ○ |
| 冪等（全投稿を控え無しでもう 1 回） | 変化した行 | 0 | 0 | 0 | ○ |

- 4 行（R1・R3a・R3c・R5）が old と guard で違う。ほかは全部同じ。
- 本物の pytest（`backend/tests/test_v102_human_decisions_pg.py:215-230` の A→B を含む）は、コードを変えていないので走らせていない。→ 2026-10-19 #4533 の CI で実コードの pytest が通った（K1 ○）。

### 試験の記録

- 途中で、中身が空の使い捨て DB（rg_data、モックの作成に失敗した DB）を 1 つ消すコマンドを 1 回実行した。本番にもリポジトリにも影響はない。以後は DB を消さず、新しい名前で作った。

## 5. 受け入れ条件

| 基準 | 検証方法 |
|---|---|
| K1 試験の全シナリオが通る | 実装便で R1・R2・R3a・R3b・R3c・R5・R6・S1・D1b・冪等を実コードの pytest（`backend/tests/`）に移し、CI の pytest で全部通る。サンドボックスの `logs/sandbox_guard.txt` と同じ期待値 |
| K2 再解析の痕跡が無い現行行の変化は 0 | デプロイ直前と直後（修正 SQL の前）に本番 reader で全 `analysis_results` の (id, is_current) を控え、差が出た行がすべて「その間に新しく解析された投稿の仕入元」の行であること（それ以外の差 0 件） |
| K3 修正 SQL の後、一覧の行の現行数は 0 | `docs/handoff/revival-guard/data/03_postcheck.sql`（一覧 2 件が現行 0 件、監査行 1 件） |
| K4 配信行数の変化 = 一覧の配信行数 | 修正 SQL の直前と直後に、対象 2 組（仕入元×商品 440569・458213）の配信行数を数え、減った数が 2、ほかの組の配信行数の差が 0 |
| K5 反映後の再解析で復活が 0 | 修正 SQL の後、対象 2 件の仕入元の、より新しい投稿の job を v102 で再解析し、2 件が FALSE のままで、`updated_at > computed_at` かつ FALSE→TRUE になった「より新しい投稿に同じ商品がある」行が 0 件 |

修正 SQL の試験（モックの public スキーマで 01→02→03→04 を通した結果は `logs/data_dryrun_mock.txt`）: 01 precheck ○、02 apply で 2 行 FALSE・監査 1 行、03 postcheck ○、04 rollback で 2 行が元の値（is_current と updated_at）に戻る、戻した後の 03 は K3 NG で止まる（意図どおり）。本物の DB での実行は未実施。→ 2026-10-19 本番で 01→02（試し実行のあと本実行）→03 を実行、K1〜K5 すべて ○（ADR-1032 末尾「本番反映の記録」）。

## 6. 外部・過去事例の参照と我々への応用

【未確認】Context7 の月間枠が上限で使えず、PostgreSQL の `INSERT ... ON CONFLICT DO UPDATE` の公式記述を引けなかった。本リポジトリ内の根拠は `backend/app/services/line_analysis_v102_svc.py:760-769` の実コードで、`is_current` が SET に無いことを確認済み。同じ形の先行例は `docs/handoff/dup-product-merge/`（`audit_log` に変更前の値と対象 id を残し、件数の守りと rollback を持つ）で、修正 SQL はこれに合わせた。

## 7. 未確認 626 件の扱い（PO 決定: 直さない）

- 定義: 現在 is_current=TRUE の行で、同じ仕入元のより新しい投稿に同じ商品がある行を、残った痕跡で分けた。B（v102・痕跡消失）252 件、C（v6・`updated_at > computed_at` あり）374 件。計 626 件。うち配信中（近似）は B 222・C 153。
- 判定できない理由: 本番に is_current の履歴が無い。v102 の再解析は行を書き直すたびに `updated_at` を `computed_at` と同じ値で上書きする（`backend/app/services/line_analysis_v102_svc.py:767`, `:1131`）ので、付け直しが行を戻した痕跡が次の書き込みで消える。v6 は一括の書き込みと付け直しの `updated_at` が区別できない。B・C の多くは「初回の解析のまま古い投稿の別の状態の行が残っている」（設計どおり）で、復活かどうかが読み取れない。
- 今後の判定手段（この ADR の範囲外・別便）: 付け直しが行の is_current を変えたとき、その変更を履歴に 1 行ずつ残せば、復活は履歴で確実に分かる。書き込み量の見積りが要るため、今回の実装便には入れない（変更は一度に 1 つ）。反映前の分は分からないままなので、K5 は「反映後の再解析で復活 0」で測る。
- 一覧の原本は `/tmp/CC報告ファイル/revival_guard/candidates.tsv`（未確認分は unconfirmed.tsv）。リポジトリには確認済 2 件の `logs/confirmed.tsv` だけを置く。

## 8. 触らない範囲・戻し方・維持の仕組み

- 触る（実装便）: `backend/app/services/tcg_analyzer_svc.py`（`_merge_supplier_products` の引数と SQL）、`backend/app/services/line_analysis_v102_svc.py`（`_load_current_pairs` 新設と呼び出し）、`backend/app/services/v102_transcription_svc.py`（`revival_guard=False`）、`backend/app/tools/reextract_v6_with_v102.py`（現行だった組の控え（出力先の current_pairs フォルダに job ごとの JSON）・取り消しは `revival_guard=False`）、`backend/tests/test_adr1032_revival_guard.py`（新設）。
- 試験の確認先: PG を使う試験は CI の `.github/workflows/test.yml` で確認する（ローカルは role 作成がフックで止まるため未実行）。ローカルで走らせたのは PG を使わない関連試験のみ。
- 触らない: 商品×状態の最新の投稿が現行という規則そのもの、`is_current` の初回の決め方、配信の条件、v6 の解析、`migrations/`、`.github/workflows/deploy.yml`、仮の行（完売の相手）の作り方、未確認 626 件。
- 戻し方: コード（実装便）は PR の revert。データ修正は `docs/handoff/revival-guard/data/04_rollback.sql`（監査行の変更前の値に戻す。新しい PO 判断が必要）。
- 守り手: backend/tests/test_adr1032_revival_guard.py（CI の test.yml の PG テストで実行）
- 維持の仕組み: 試験 `docs/handoff/revival-guard/sandbox/scenarios.sql` の場面を、実装便で `backend/tests/` の pytest に移して CI で走らせる（K1）。履歴を残す変更（§7）は別便。

## 9. 審査（Opus, 2026-10-19）

- 判定: APPROVE（修正込み）。同一 AI による自己審査で、独立した第二者レビューではない。
- 直した点: ①K2 を「その間に新しく解析された投稿の仕入元」を除いた差 0 に（新着の投稿で差が出るため）②K4 を対象 2 組に限定 ③K5 を実際に回す再解析（対象 2 件の仕入元の新しい投稿の job）に具体化 ④K1 を実コードの pytest に ⑤§7 の履歴は範囲外・別便 ⑥ADR に「結果は経緯で変わる」性質を明記。
- 確かめた点: 他の job の行は `ar.is_current` を控えとして使うので、v6 の呼び出し（控え無し）でも古い投稿の行の復活は止まる。止まらないのは「その job 自身の作り直した行」で、v102 と再抽出ツールは控えを渡す。確認済み 2 件はどちらも、updated_at が computed_at より後に進んでいる（付け直しで FALSE→TRUE に変わった印。`WHERE is_current IS DISTINCT FROM` のため変化した時だけ更新される）。
- 未解決: 取り消し（#5）で guard を切ることの影響は【未確認】（今と同じ動きなので悪くはならない）。
- 危険パス: 実装便が `migrations/` を含めば ADR-135/136 の GO 手順に従う。この下書きは含まない。
- 2026-10-19 追記: 実装便 #4533 は `migrations/` を含まない。本番反映と K1〜K5 の結果は ADR-1032 末尾。ADR-1032 は Accepted。
