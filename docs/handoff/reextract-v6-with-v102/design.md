# design: 旧解析 v6 の投稿を新解析 v102 でやり直す（r5）

状態: 設計案 r3（Opus）。r2 の審査（REVISE、M1〜M6・m1〜m8）は review-opus.md「## r2 審査」。
- r1 の審査（REVISE、M1〜M6・m1〜m12）: /Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/docs/handoff/reextract-v6-with-v102/review-opus.md
- 事実: /Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/docs/handoff/reextract-v6-with-v102/recon.md（§5 が r2 で足した実測）
- PO 承認: recon §0

## 0. r1 からの変更（審査への答え）
- M4 / M5 / m2 / m3 / m7
  - 配信の待ち合わせ #8b は変えない（ADR-1019 の順序を保つ）。
  - job の status を pending / running にしない方式に変えた。
    - 道具は、run_v102_extraction を recorder なし（recorder=None。line_analysis_v102_svc.py:462 の既定）で直接呼ぶ。
    - この方式では、claim も extraction_attempts も通らない。
  - そのため、#8b・停滞回収・ダッシュボードの stale running に、やり直しの job が出ない。
  - Gemini の呼び出しには、道具側で 300秒の時間切れを付ける。
- M1: 実測しました（recon §5-1）。
  - received_at が NULL の投稿は 0。
  - 配信窓内の現行の組で、v6 の received_at が窓内以上になるものは 0。
  - 道具は念のため received_at が NULL の投稿を飛ばす。
- M2: 古い投稿から（line_posted_at ASC）流す。
- M3: 実測しました。原文が空のものは 0。いまの事前フィルタに当たるものは 1件（ej 443987d7）。
  - 道具はフィルタに当たる件を飛ばして記録する（v6 のまま残す）。
- M6: K2・K4・K5 を、観測できる形に直した（§1）。
- m1: 自動配信は、道具が呼ばない形にする（run_v102_analysis を直接呼ぶ）。tcg_extraction.py の変更は無し。
- m4: 最後に、要確認画面へ1回通知する。
- m6: 在庫表 API などの影響を §4 に足した。
- m8・m9: 費用は、処理した job の source_ref で集計する。道具の上限は $11。
- m10: 本番の実行と控えは、PO の離席一任（2026-10-15「SSHへの無制限鍵へのアクセス等、必要な権限は全て必要な場合は使用して良い」）で行う。
- m11: celery-worker とは別のコンテナ（`docker compose run --rm --no-deps`）で動かす。
- m12: 件数は時刻で変わる（recon §2 に注記）。

## 0-2. r2 からの変更（r2 審査への答え）
- M1（応答が読めないと empty で確定する）
  - 結果の区分に `unreadable` を足す。判定は、抽出後の job の review_reasons に response_unreadable を含むかで行う。
  - unreadable は連続の失敗に数える。
  - K4 に件数 0 を足す。
  - 出た件は、控えから戻すか（§5）、v102 の再解析ではなく、もう一度 Gemini で抽出し直す（`--repair` の対象）。
- M2（抽出の確定後に止まった件が取り残される）
  - 例外が出たら session を捨て、新しい session で job を読み直して区分を決める。
  - 解析の失敗は、review_reasons の extract_exception で判定する。
  - `--repair` モードを足す。
  - K7（取り残し 0）を足す。
- M3（v6 だけの組の is_current が付け直されない）
  - 抽出の前に `_load_resolved_pairs` で v6 の組を控える。
  - 解析の後に `_merge_supplier_products(extra_pairs=控えた組)` を呼ぶ。
  - 控えた組はファイルにも書く（--repair と戻しで使う）。
- M4（デプロイで別コンテナが消される）
  - コンテナ名を `reextract-v6-<日付>` にし、名前で消す対象（deploy.yml:409-411）から外す。
  - `docker compose stop celery-worker`（:407）と `up --remove-orphans`（:412）が run のコンテナに効くかは【未確認】。そのため、消されても続く作りにする。
    - ホスト側の繰り返し（§3 D6）で、やり直しを再開する。
    - 途中の件は `--repair` で直す。
  - main のマージは止めない（他の作業が多く、止める運用は守れない）。代わりに、実行中のデプロイのたびに、コンテナが生きているかと K7 を確かめる。
- M5: K1・K2・K3・K6 を直した（§1）。
- M6: 戻しを道具の `--rollback-from <控えのディレクトリ>` にし、PR に入れる（§5）。
- m1: 時間切れは2重にする。
  - 主: 道具の中だけで Gemini client を作るところを包み、HttpOptions(timeout=300000ms) を付ける。既存ファイルは変えない。本番の 2.8.0 で効くかは、実装で確かめる。
  - 予備: signal.alarm(330)。BaseException の子の独自例外を投げ、戻ったらすぐ alarm(0) にする。
- m2: 時間切れで切った呼び出しの費用は台帳に出ない。K3 に注記する。
- m3: 費用サマリと成功率にやり直し分が出ないことを、§4 と PO への報告に書く。
- m4: 追加の付け直しの直前に item_corrections を読み直し、行があれば飛ばす。
- m5: SQL は `public.` を付けて書く。除外の判定は、1件ごとの処理の直前にもう一度行う。
- m6: `run -T` を付ける。実行の前に `docker inspect` で Memory・RestartPolicy を実測する。
- m7: D2 の確かめに、knowledge_rules の除外系の件数が 1以上であることを足す。
- m8: 道具の ctx は、判定だけに使う。

## 0-3. r3 からの変更（r3 審査への答え）
- M1: 控えのファイルを、ホストのディレクトリに置く。
  - D6 のコマンドに `-v /home/ubuntu/reextract-v6:/work` を足す。
  - ホストのディレクトリは、コンテナの appuser の uid で書けるようにする（uid は Dockerfile と本番の `id` で実測する）。
  - 道具の `--out-dir` は /work。
  - pairs は、書いて fsync してから抽出に進む。
- M2: `--repair` は、処理順の一覧のうち v102 の件すべてに `_merge_supplier_products(extra_pairs=pairs)` をかける（冪等。Gemini は呼ばない）。
  - D4-8 で飛ばした件は skip_merge と記録する。
  - K8 を足す。
- m1: unreadable の件の Gemini のやり直しは、`--repair` で1件あたり2回までにする。
  - 回数は out-dir の repair_counts.json に残す。
  - 超えた件は、`--rollback-from --job-id` で v6 に戻す（job 単位で選べる）。
- m2: 最初の開始時刻を out-dir の started_at.txt に保存する。費用は、毎回その時刻からの台帳で数える。
- m3: K1・K4(a) の除外一覧には、実行記録の skip_* も含める。
- m4: K2(b) は、実行中に新しい投稿の job ができたときだけ判定する。
- m5: 戻しの前に、v102 の items に紐づく item_corrections を数える。
  - 1件以上ある job は戻さず、報告する。
  - INSERT が失敗した job は、job 単位で rollback して報告する。
- m6: コンテナ名の N は、繰り返しの回の番号にする。名前がぶつかったら、前の回のコンテナを docker rm してから進む。

## 1. 目的（KGI）
PO が要確認画面で見る過去の投稿（2026-09-09〜10-09、v6 で解析した 1010投稿）を、いまの新解析 v102 の結果に置き換える。

| 基準 | 検証方法 |
|---|---|
| K1 v6 で残る job が「dry-run の除外一覧（filtered・フィルタ該当・item_corrections あり）＋実行記録の skip_* の job」と一致する | `SELECT id FROM public.extraction_jobs WHERE prompt_version='raw-extraction-v6-rawcode-p1'` と、その一覧の差が 0 行 |
| K2 やり直しで、配信の待ち合わせが止まらない | 実行中に3回、次を見る。(a) 控えの job id のうち status が pending/running/extracted の件 = 0。(b) 実行中に新しい投稿の job ができたときだけ、配信の last_distributed_at がその後に1回以上進む（新着が無ければ判定しない） |
| K3 Gemini の費用が合計 $12 以下 | `SELECT sum(cost_usd), count(*) FILTER (WHERE cost_usd IS NULL) FROM public.llm_usage_events WHERE source_ref = ANY(<控えの job の 'extraction_job:'\|\|id>) AND occurred_at >= <開始>`。合計 ≤ 12 かつ NULL 件数 = 0（NULL が出たら道具は止まる）。時間切れで切った呼び出しは台帳に出ない（注記） |
| K4 抽出の失敗が残らない | 控えの job のうち次が 0。(a) prompt_version が v6 のまま（除外一覧を除く）。(b) review_reasons に response_unreadable を含む |
| K5 配信窓の中の現行の行が、やり直しのせいで現行から外れない | 実行前に、窓内の is_current=TRUE の analysis_results の id を控える。実行後、その中で FALSE になった行について、同じ組の新しい現行が「控えの job」のものである件数 = 0 |
| K6 PO が見た件（job 5d71f040）が v102 で解析し直されている | 次の3つを満たす。(a) prompt_version が `v102:` で始まる。(b) その items に紐づく analysis_results が 1件以上ある。(c) メモ「カートン」の行の商品・状態・数量・単価を一覧にし、PO 報告に添える（状態 Case の要否は、PO の回答待ちの別件） |
| K7 取り残しが 0 | 控えの job のうち、v102 で次のいずれかに当たる件 = 0。(a) items>0 かつ analysis_results=0。(b) review_reasons に extract_exception を含む |
| K8 v6 の組の現行が消えていない | pairs/ の組それぞれについて、analysis_results に行があるのに is_current=TRUE が 0行の組 = 0 |

## 2. 対象と対象外
- 対象: prompt_version='raw-extraction-v6-rawcode-p1' で、status が done / empty / error の件（10/16 時点で 1007件）。
- 対象から外す（dry-run で一覧ファイルに書く）
  - filtered の件。
  - いまの事前フィルタに当たる件。
  - received_at が NULL の投稿。
  - item_corrections に行がある投稿。
- 対象外
  - v3 / v4 / v5 の版。
  - 既存のコードは変えない。

## 3. 方式
新規の道具 backend/app/tools/reextract_v6_with_v102.py を1本作る。本番では、celery-worker とは別のコンテナで、1件ずつ直列に流す。既存のファイルは変えない。

### D1 動かし方（モード）
- 既定は dry-run。
  - 対象の件数、除外の内訳、最初の10件を出す。
  - `--out-dir` に「処理順の job id 一覧」と「除外の一覧」を書く。
  - DB には書かない。
- `--execute`：やり直す。`--job-id`、`--limit N`、`--max-cost-usd 11`、`--stop-after-errors 5`、`--timeout-sec 300` を付けられる。
- `--repair --ids-file <処理順の一覧>`：一覧の件を、次のとおり直す。
  - unreadable の件は、run_v102_extraction からやり直す。
    - やり直しは、1件あたり2回まで（回数は repair_counts.json）。
    - 超えた件は一覧に出し、`--rollback-from --job-id` で v6 に戻す。
  - 解析の取り残し（K7）の件は、run_v102_analysis をかける。
  - 一覧のうち v102 の件すべてに、`_merge_supplier_products(extra_pairs=pairs/<job>.json)` をかける。
    - 冪等で、Gemini は呼ばない。
    - item_corrections がある件は skip_merge とする。
- `--rollback-from <控えのディレクトリ> [--job-id <uuid>]`：§5 の戻し。job を選べる。
  - 既定は dry-run で、`--execute` のときだけ書く。

### D2 始める前の確かめ（違えば終了コード 2 で中止）
- get_engine() が v102 であること。
- 本番の指示書が読めること。
- knowledge_rules の除外系の件数が 1以上であること（m7）。

### D3 対象の選び方
```
SELECT ej.id, ej.source_message_id
FROM public.extraction_jobs ej
JOIN public.source_messages sm ON sm.id = ej.source_message_id
WHERE ej.prompt_version = 'raw-extraction-v6-rawcode-p1'
  AND ej.status IN ('done','empty','error')
  AND sm.received_at IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM public.item_corrections ic WHERE ic.source_message_id = ej.source_message_id)
ORDER BY sm.line_posted_at ASC, ej.id
```
- 途中で止まっても、流し直せば残りから続く（終わった job は v102 になり、選ばれない）。
- 事前フィルタの判定は Python 側で行う。

### D4 1件ごとの流れ（審査の「実装カードに書くべき注意点」1・2 に従う）
1. 新しい session を作る。
2. 除外の判定をもう一度行う。
   - job が v6 のままか。
   - item_corrections があるか。
   - ctx（判定にだけ使う）が事前フィルタに当たるか。
   - 当たれば skip_* と記録する。
3. `_load_resolved_pairs(session, job_id)` で v6 の組を控える（out-dir の pairs/<job_id>.json）。
4. 時間切れ付きで `run_v102_extraction(session, job_id)` を呼ぶ（recorder なし）。戻ったら、すぐ alarm(0) にする。
5. 例外のとき
   - rollback して session を捨てる。
   - 新しい session で job を読む。
     - v6 のままなら gemini_error。
     - v102 なら「確定後の例外」として 6 以降へ進む。
6. 新しい session で job を読み直す。review_reasons に response_unreadable があれば unreadable とし、解析を飛ばす。
7. `run_v102_analysis(session, job_id)` を呼ぶ。そのあと読み直し、extract_exception があれば analysis_error とする。
8. item_corrections を読み直す。無ければ `_merge_supplier_products(session, job_id, TCG_SCHEMA, extra_pairs=控えた組)` を呼び、commit する。
9. 費用を読み直す（occurred_at・NULL も見る）。上限以上、または NULL ありなら止める。
10. 1行を記録する。
    - 項目: job_id、区分（done / empty / unreadable / gemini_error / analysis_error / skip_*）、秒、累計費用。
    - item_corrections があり付け直しを飛ばした件は skip_merge とする。
    - unreadable・gemini_error・analysis_error は、連続の失敗に数える。それ以外の区分では、0 に戻す。

### D5 終わり
- 集計を出す。
- 1件以上を処理していれば、`_publish_review_changed()` を1回呼ぶ。
- 終了コードは次のとおり。
  - 全部済んだら 0。
  - 上限で止まったら 3。

### D6 本番の動かし方
- 場所は、ホストの compose のディレクトリ。
  ```
  docker compose run --rm --no-deps -T -v /home/ubuntu/reextract-v6:/work --name reextract-v6-YYYYMMDD-N celery-worker python -m app.tools.reextract_v6_with_v102 --out-dir /work [引数]
  ```
- 長く流すときは、ホストで小さな繰り返し（最大10回）を nohup で動かす。ログは /home/ubuntu/reextract-v6/ に出す。
  - 1回ごとに、`--execute` の後で `--repair` を流す。
  - 終了コードが 0 なら抜ける。3 なら止まる（上限）。
  - コンテナが消された（137 等）ときは、次の回へ進む。
- 実行の前に、別名の短い run コンテナを `docker inspect` し、Memory・RestartPolicy を実測する（m6）。

### 代替案と、選ばなかった理由
- A: pending に戻して Celery に流す（r1）
  - 新しい投稿の解析がキューの後ろに並ぶ。
  - #8b の待ち合わせが止まる。
  - #8b を変えると ADR-1019 とぶつかる。
- B: AttemptRecorder を、done から claim できるように変える
  - 共通部品の変更になる。
  - running の間は #8b に引っかかる。
- C: Claude が書き写す
  - PO が Gemini を選んだ。
- D: 実行中は main のマージを止める
  - 並行の作業が多く、守れない。消されても続く作りにした（D6・--repair）。

## 4. 弊害と対処
| 弊害 | 対処 |
|---|---|
| extraction_attempts を書かない。そのため、ダッシュボードの費用サマリ・日別リクエスト・成功率（tcg_analysis_dashboard.py:465-510, :857-883）に、やり直しの約 $7.5・約1000回が出ない。台帳起点の月別とは数字が合わない。診断の試行一覧には、v6 時代の試行だけが出る | 費用は llm_usage_events で追える。PO への報告に注記する。停滞回収は status を見るので、影響しない |
| 相場の点検（unit_price_mismatch）の母数に、v6 由来の行が加わる | 実行の前後で件数を報告する |
| 窓なしで読む画面（要確認タブ・相場点検・line_import_admin）は、is_current の変化をすぐ映す | M3 の付け直しで、組が消えないようにする。窓内は K5 で守る |
| 要確認の件数が増減する | 狙いどおり。前後の数を報告する |
| 人の直しと同時に動くと、直しが消える | item_corrections がある投稿は、処理の直前にも除く。付け直しの直前にも読み直す |
| Gemini の呼び出し中（最大300秒）に人がその投稿を直すと、直しが DELETE の後に孤立する（コード審査 m7。既存ファイルを変えない方針では塞げない） | 対象は過去の投稿（10/9 以前）なので、人が触る見込みは小さい。実行の後に「控えの job の投稿で、実行開始より後に作られた item_corrections」を数え、1件以上なら一覧にして PO に報告する |
| デプロイで、別コンテナが消され得る | 名前を外す（D6）。消されても、繰り返しと --repair で続ける。K7 で取り残しを 0 にする |
| 応答が読めないと、v6 の件が消える | unreadable と数え、連続5回で止める。--repair でもう一度抽出する。K4 で 0 にする |
| 古い items が消える | 実行前に控えを取る（§5） |

## 5. 控えと戻し方
- 控え（実行前。ホストの /home/ubuntu/reextract-v6/backups/。コンテナからは /work/backups/ で読める）
  - `\copy (...) TO ... WITH (FORMAT csv, HEADER true, FORCE_QUOTE *)` で、v6 対象の job の extraction_jobs（全列）・extraction_items・analysis_results を CSV にする。`NULL '\N'` は使わない（道具の読み取りは「引用符なしの空＝NULL」で区別する。コード審査 r2-m3）。
  - 最初に全件の dry-run を流してから、絞った実行に進む（コード審査 r2-m4。excluded.tsv は全件の実行でしか書かれない）。
  - dry-run の「処理順の job id 一覧」と「除外の一覧」。
  - D4-3 の組の控え（pairs/）。
- 戻しは `--rollback-from /work/backups [--job-id <uuid>] --execute`。job ごとに、1つの取引で次を行う。
  0. v102 の items に紐づく item_corrections を数える。1件以上なら戻さず、報告する。
  1. v102 が出していた組を、`_load_resolved_pairs` で控える。
  2. extraction_items を DELETE する（v102 の analysis_results・extra_targets も CASCADE で消える）。
  3. CSV から items、次に analysis_results の順に INSERT する（id はそのまま）。
  4. extraction_jobs を CSV の全列で UPDATE する。
  5. `_merge_supplier_products(extra_pairs=1 の組)` を呼んで、付け直す。
  - 途中で失敗した job は、その job だけ rollback して報告し、次の job へ進む。
- コードは、道具1本の revert で戻る（既存の動きに影響しない）。

## 6. 計画（便）
1. PR（道具・試験・本書）→ CI → コード審査 → GO → マージ → デプロイ。
2. 本番で、次の順に行う。
   1. docker inspect の実測。
   2. dry-run（一覧を書く）。
   3. 控え。
   4. K5 の控え。
   5. `--job-id 5d71f040-d9ae-496a-9c89-7708ec073d88 --execute` で1件 → K6・K7 を確かめる。
3. `--limit 20 --execute` で流し、K2・K3・K4・K5・K7・K8 を確かめる。
4. 残りを、繰り返しの nohup で流す。デプロイがあれば、そのたびにコンテナと K7・K8 を確かめる。
5. 終わったら K1〜K8 を確かめ、PO へ報告する。

## 7. 試験（Gemini と解析の中身は mock。DB は PG 試験の仕組みを使う）
- dry-run は DB に書かない。
- 対象の条件
  - filtered・v102・received_at が NULL・item_corrections がある件を除く。
  - 並べ方は ASC。
  - 処理の直前の再判定で、除外する。
- フィルタに当たる件は飛ばす。
- 区分の判定
  - Gemini の例外では、items が変わらず gemini_error になる。
  - 応答が読めない件は unreadable になる。
  - 解析の失敗（extract_exception）は analysis_error になる。
- 確定後の例外は、読み直しで正しく区分され、`--repair` で直る。
- v6 だけの組が、一つ前の投稿へ現行として戻る（M3）。
- 止める仕組み
  - 連続の失敗が 5回で止まる。
  - 費用の上限で止まる。
  - cost NULL で止まる。
  - 時間切れが gemini_error になり、BaseException の子の例外が台帳の except に飲まれない。
- _enqueue_auto_distribute を呼ばない。
- `--rollback-from` で、控えた items・results・job の列が元に戻る。
- 戻しは、item_corrections のある job を飛ばす。
- 付け直しの前に止まった件が、`--repair` で付け直される。
- unreadable のやり直しは、2回で止まる。
- started_at.txt からの費用の累計で止まる（プロセスをまたいでも数える）。
- pairs を書けないときは、抽出しない。
- コンテナ名の組み立てが、`astro-webapp-celery-worker` で始まらない（ホストの繰り返しスクリプトを PR に入れる場合）。

## 8. 維持の仕組み
- 道具は、一度きりの作業用。対象が 0件なら何もしない（dry-run で 0 を出す）。
- 既存のコードは変えない。
- 道具の動き（区分・止める仕組み・戻し）: 守り手: `backend/tests/test_reextract_v6_with_v102_pg.py`

## 9. 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし。社内の既存の関数を決まった順に呼ぶだけで、外部の数値事例は判断を変えない。
- 過去の自社事例: 費用と時間は v102 の本番実測（recon §4: 1件 $0.007424・14.5秒）に基づく。本番の重い作業は別コンテナで流す（社内の運用規律）を D6 に使った。
