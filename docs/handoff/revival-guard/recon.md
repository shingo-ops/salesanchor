# recon: 現行行の「復活」と復活止め（現在地）

作成 2026-10-19 / 読み取りのみ（製品コード・migration・本番は変更していない）。引用は origin/main 70c3eda3d 時点のリポジトリ相対のフルパス:行。

## 0. 既存 ADR の検索（着手前）

- `git grep -i` 相当で `docs/adr/` を検索し、関係するのは次の 3 本: `docs/adr/ADR-158-product-level-supersession.md`（商品×状態ごとの最新の投稿が現行。`backend/app/services/tcg_analyzer_svc.py:1972` の docstring が ADR-158:26 を引用）、`docs/adr/ADR-1027-bundle-sale-reading.md`（まとめ売り。古い投稿の別状態の行を残す設計の前提）、`docs/adr/ADR-1030-drop-products-tcg-type.md`（無関係。除外）。
- 「復活止め」を扱う ADR は無い（新規 ADR-1032）。

## 1. 現行規則の実装（変更しない）

| 事実 | 場所 |
|---|---|
| 付け直しの関数 `_merge_supplier_products(session, extraction_job_id, schema, extra_pairs=())` | `backend/app/services/tcg_analyzer_svc.py:1964` |
| この投稿の (商品, 状態) の組と、extra_pairs（前の組）、〆の完売の相手（仮の行）を「触れる組」にする | `backend/app/services/tcg_analyzer_svc.py:2021-2037`（touched_triples） |
| 触れる組を持つ同じ仕入元の全投稿の行＋仮の行を候補にする | `backend/app/services/tcg_analyzer_svc.py:2038-2067`（candidates） |
| 組ごとに received_at → computed_at の最大 → job_id の降順で最新の投稿を 1 つ決める | `backend/app/services/tcg_analyzer_svc.py:2068-2082`（job_rank `:2068`, top_job `:2075`） |
| 最新の投稿の行だけ TRUE にし、値が変わる行だけ UPDATE（updated_at = NOW()） | `backend/app/services/tcg_analyzer_svc.py:2083-2094`（ranked `:2083`, UPDATE `:2089`、値が変わる行だけ `:2094`） |

つまり現行は「その組で最新の投稿の行 = 現行」だけで決まり、「その行が前から現行だったか」は見ていない。

## 2. 復活が起きる仕組み（事実）

1. v102 の再解析は `run_v102_analysis` の中で、書き直す前に `previous_pairs = _load_resolved_pairs(...)` を読み（`backend/app/services/line_analysis_v102_svc.py:1461`）、書いた後に `extra_pairs=previous_pairs` で付け直す（同 `:1476`）。`_load_resolved_pairs` は `:1161`。
2. 書き込みは `ON CONFLICT (extraction_item_id) DO UPDATE`（`backend/app/services/line_analysis_v102_svc.py:760`）。SET の列に `is_current` は無い（`:760-769` を確認）ので、既存の件の行は古い is_current を持ち越し、新しい件の行は既定値 TRUE で入る。v6 も同じ（`backend/app/services/tcg_analyzer_svc.py:1873` 以降の SET に `is_current` が無い）。
3. 古い投稿 X の再解析で組が変わる（例 (A,Error) → (A,Single)）と、前の組 (A,Error) が extra_pairs で「触れる組」に入る。そこで最新の投稿が X より古い Z の行になっていれば、Z の行が最新となり TRUE に戻る（復活）。現行 SQL は「Z の行が一度は新しい投稿に隠された行だった」ことを見ない。
4. 最新の投稿の再解析で A → B に変わる場合は、古い投稿の A の行が戻るのが正しい（`backend/tests/test_v102_human_decisions_pg.py:215-230`）。復活止めはこれを壊してはいけない。
5. 再抽出 `run_v102_extraction` は件を消して作り直す（`backend/app/services/line_analysis_v102_svc.py:519`）。件が消えると行も消えるため、その後の解析では「前の組」が空になる。

## 3. 呼び出し元 5 か所

| # | 呼び出し | 場所 | extra_pairs | 現行の動き |
|---|---|---|---|---|
| 1 | v6 解析 | `backend/app/services/tcg_analyzer_svc.py:1956` | 無し | 初回は新しい行が TRUE |
| 2 | v102 解析 | `backend/app/services/line_analysis_v102_svc.py:1476` | 書く前の全組 | 再解析で復活あり |
| 3 | 人の直しで件を削除 | `backend/app/services/v102_transcription_svc.py:382`（組は `:370` で読む） | 消した件の組 | 古い投稿の行が戻る（G5） |
| 4 | v6→v102 再抽出ツール | `backend/app/tools/reextract_v6_with_v102.py:353`（`_merge_pairs`、組は `:434` で控え、`:439` の `write_pairs` で保存） | 控えた v6 の組 | 復活あり |
| 5 | 再抽出の取り消し | `backend/app/tools/reextract_v6_with_v102.py:741`（組は `:736`） | v102 の組 | 取り消し後の付け直し |

## 4. 配信への効き方

配信は `is_current` が TRUE の行から出す（`backend/app/services/tcg_distribution_svc.py:368`、`:482`、`:525`）。復活した行は、新しい投稿の同じ商品の行と並んで二重に出る。

## 5. 本番の読み取り結果（reader 経由・読み取りのみ・2026-10-19 06:04Z 前後）

過去の is_current の履歴は本番に無い。痕跡で分類した（原本: `/tmp/CC報告ファイル/revival_guard/candidates.tsv`、列は id・時刻・商品・状態のみ。仕入元名・原文なし）。

| 区分 | 判定の条件（現在 is_current=TRUE の行で、より新しい投稿に同じ商品がある） | 件数 | うち配信中（近似） |
|---|---|---|---|
| A 確認済 | v102 で `updated_at > computed_at`（付け直しが後から立てた痕跡）かつ `updated_at` をほかのチャネルと共有しない | 2 | 2 |
| B 未確認 | v102、痕跡が上書きされて消えた。ただし computed_at が受信から 1 日超（再解析の痕跡） | 252 | 222 |
| C 未確認 | v6、`updated_at > computed_at` あり。ただし v6 の一括書き込みとの区別がつかない | 374 | 153 |
| 対象外 X | v6 で `updated_at` を複数チャネルが共有（一括書き込み。付け直しではない） | 618 | 28 |
| 対象外 Y | 痕跡なし＝初回の解析のまま（古い投稿の別の状態の行は残す設計） | 366 | 126 |

- 配信中は `backend/app/services/tcg_distribution_svc.py` の条件を式で写した近似。実際の配信行との完全一致は【未確認】。
- 確認済 2 件の id と根拠（`logs/confirmed.tsv`、本番の再読み取りで状態が一致）:

| analysis_results.id | 商品 | 状態 | 付け直し時刻（computed_at → updated_at） | この行の投稿の受信 | より新しい投稿（件数・最新受信・状態） | 新しい投稿の現行行 |
|---|---|---|---|---|---|---|
| 349eaef0-1958-4a82-80eb-74d9c6fe5212 | 440569 | 17 | 2026-10-18 00:08:01.95 → 00:08:02.03Z | 2026-10-08 00:20Z | 21 行・2026-10-19 05:19Z・状態 14,16 | 2 行 |
| f61f1ea7-40d4-454e-ac52-3e3e6e8fcffe | 458213 | 12 | 2026-10-18 00:21:58.36 → 00:21:58.43Z | 2026-10-11 18:09Z | 1 行・2026-10-16 11:42Z・状態 14 | 1 行 |

  どちらも、再解析の直後 0.07〜0.08 秒後に updated_at が進んでいる（付け直しが行を立てた痕跡）、v102、updated_at をほかのチャネルと共有しない、同じ商品に新しい投稿の現行行がある（配信が二重）。
- 【未確認】B・C が復活かどうか。理由: 本番に is_current の履歴がなく、v102 の再書き込みが updated_at を上書きして痕跡を消す（`backend/app/services/line_analysis_v102_svc.py:767` が computed_at と updated_at を書き込み値で置き換え、呼び出し側は両方に同じ `now` を渡す `:1131`）。今後の判定手段は design.md §7。

## 6. 試験の事実

試験用 PG（PostgreSQL 16.15, port 55460）で、現行 SQL と案を同じ入力で比べた。結果は `logs/sandbox_old.txt` と `logs/sandbox_guard.txt`、まとめは design.md §4。
