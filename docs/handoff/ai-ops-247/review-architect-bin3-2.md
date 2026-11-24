# 設計審査（architect）2回目 — 段階4 便3 実装カード

判定: **APPROVE**（設計合格。R は 0 件、L は 3 件）

- 理由1: 1回目の R1 は直っている。§2（６）の手順（SQL を最終形にしてから sha を取り直し、:7 を直す）で `scripts/check-migration-value-writes.py` の diff と repo の両方が通る。列も 4 つのまま保てる。
- 理由2: 新しく書いた行番号（:164-174・:242-256・migration-guard.yml:441・migration-test.yml:1346・ops の表 :120-125）は origin/main の実物と合う。誤りは試験の :80-91 だけで、軽い（L1）。
- 理由3: L1〜L4（1回目）も反映済み。実装者が迷って作れない・壊れる点は見つからない。

審査した物: origin/release/ai-ops-stage4-bin3（3c67c2f20）の `docs/handoff/ai-ops-247/card-stage4-bin3.md`。1回目の審査は origin/release/ai-ops-stage4-bin3-review1 の `docs/handoff/ai-ops-247/review-architect-bin3-1.md`。実物は origin/main（f6d54446e0b4f2573b6331a515d23a087e65e2b5）。

## (1) 1回目の指摘が直っているか（1件ずつ）

`git diff 77c82caa9 3c67c2f20 -- docs/handoff/ai-ops-247/card-stage4-bin3.md` で確認。

| 指摘 | 結果 | 根拠 |
|---|---|---|
| R1 §1 の範囲に :7 を足す | 直った | §1 に `scripts/migration-guard/reference-allowlist.tsv` の :7 を追加。「触らない」の `scripts/` に「:7 の 1 行を除く」 |
| R1 §2 に sha 取り直しの手順 | 直った | §2（６）。「（１）を最終形にした後で、最後に行う」 |
| R1 §2 に repo 検査の終了コード 0 | 直った | §2（７）の 1 つ目 |
| R1 §5 に受け入れ基準 | 直った | §5 に migration-guard の repo 検査の行 |
| R1 §3 に分岐 | 直った | 「該当の行が無い・列が 4 つでない → 止まる」「repo が 0 で終わらない → 止まる」 |
| L1 行番号の範囲 | 直った | §0 が `:426`・`:445-448`・`:465` |
| L2 前例の根拠 | 直った | 3 つの sha と「フル履歴のある手元で」を明記 |
| L3 salesanchor_app の作成は不要 | 直った | §2（３）から作成を削除し、作らない理由を明記 |
| L4 revert で sha も戻す | 直った | §6 に追記 |

### R1 の手順が通るか（実物で確認）

- `scripts/migration-guard/reference-allowlist.tsv:7` は 4 列（`awk -F'\t'` で NF=4）。2 列目は現在 `de1a32db…caecf`。origin/main の `migrations/20261024_100300_create_ai_cloud_views.sql` の `sha256sum` と一致する。
- 読み込み側 `scripts/check-migration-value-writes.py:104-116`: 列は `\t` で分け、4 列未満か先頭 4 列に空があると SystemExit。理由欄に足す文字列にタブが無ければ 4 列のまま。カードの足す文「 / ai-ops-stage4-bin3（ops_incidents の alertname・severity を allow に変更）」にタブは無い。
- diff モード `scripts/check-migration-value-writes.py:164-174`: head の中身の sha256 が一覧の値と同じなら exempt。違えば failed8。一覧の値を最終形の sha に直せば通る。
- repo モード `scripts/check-migration-value-writes.py:242-256`: ファイルがある・`scripts/run_all_migrations.sh` にパスが書かれている・sha が一致、の 3 つ。パスは `scripts/run_all_migrations.sh:426` に書かれている。sha を取り直せば通る。
- 順番: SQL（:166・:168）を直す → sha を取る → :7 に入れる、がカードの順。SQL を後から触ると再び食い違うので、「最後に行う」の指定は正しい。
- sha 計算の同一性: 検査は `git show` のバイト列、手順は `sha256sum` でファイルのバイト列。同じ内容なら一致する。

## (2) 新しい行番号の確認（origin/main）

- `scripts/check-migration-value-writes.py:164-174`: 確かめ 8 の例外の判定と「中身が変わったので例外は効かない」。一致。
- 同 `:242-256`: `reference_allowlist_problems`。:257 が `return`。一致。
- `.github/workflows/migration-guard.yml:441`: `python3 scripts/check-migration-value-writes.py repo`。一致。
- `.github/workflows/migration-test.yml:1346`: `if: ... contains(steps.detect.outputs.changed_sql, 'migrations/20261024_100300_create_ai_cloud_views.sql')` の工程。一致。前提は 100000（meta）と 100100（reader）で、ops の表の移行は要らない（試験側で流すのでこの工程とは別）。
- `migrations/20261016_100000_create_ops_incident_tables.sql:120-125`: `salesanchor_app` の GRANT・REVOKE。:119 が `IF EXISTS (…rolname = 'salesanchor_app')`。:120-125 は中身と END。意味は一致。
- `backend/tests/ops/test_ai_cloud_views.py:80-91`: **ずれ**（L1）。
- そのほかの §0 の行番号（:166・:168・:169、tsv :232・:240 が 6 列、`ops-incident-agent.md:132`、試験 :486・:1017・:1060）は 1 回目から変わらず一致。

## (3) 実装者が迷わず作れるか

- 作れる。変える 5 ファイル（SQL・tsv・試験・指示書・allowlist）と台帳の順番が §2（１）〜（８）で一意。
- 新しい論点の確認: 変えた SQL の行は VALUES の組で、値の書き込み（確認 7）の検出に当たる文（INSERT INTO 対象表）を新しく足さない。確認 8 は sha 一致で exempt になる。
- 他の試験への波及: `backend/tests/` で alertname を伏せる前提の試験は見つからない（`git grep` で mask・伏せ・ai_cloud と同時に出る行は `docs/ai-agents/ops-incident-agent.md:132` のみ）。
- §4 の V1 の結果は事実の記録で、設計に影響しない。生の出力 手元の /tmp/CC報告ファイル/bin3/v1-out.txt はこの環境から見えないので、数値（13 組・1007 行）は**未確認**（審査の対象外）。

## 軽い指摘（L）

- L1: §2（３）の `backend/tests/ops/test_ai_cloud_views.py:80-91` は、`_Cluster.cleanup` が :92-96 で、:80-91 には入らない（:86-90 は `__init__`）。`:79-96` のように直すと正確。意味（cleanup は salesanchor_app を消さない）は合っている。
- L2: §2（６）は理由欄（3 列目）に書き足す指定。直近の前例（event-color card-bin1 など）は 4 列目（decision_ref）に足している（`scripts/migration-guard/reference-allowlist.tsv:7`）。3 列目はもともと「なぜ例外か」の文で、前例の card-s2-2c・card-E もそこに入っているので、どちらでも検査は通る。実装者が迷うなら「4 列目の末尾に足す」に寄せると直近の流儀と合う。
- L3: §3 の分岐に「`sha256sum` を取った後に :166・:168 を再び触った」場合の扱いは無いが、§2（６）の「最後に行う」と §2（７）の repo 検査で検出できる。足さなくてよい。
