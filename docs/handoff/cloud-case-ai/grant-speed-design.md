# 権限の付け直しの時間切れを直す — 設計（ADR-1052 段2 の部品の手直し）

> この文書は何か: 本番反映の最後に流れる「AI の値を返す口の持ち主（ai_unmask_owner）の権限の付け直し」が、30 秒の打ち切りに近づき、2 回の本番反映で時間切れになった件の、現在地（実測）と直し方です。付ける権限・外す権限は変えず、計算の順番だけを直します。

- 対象ADR: ADR-1052（`docs/adr/ADR-1052-cloud-case-ai.md`）。部品の設計は `docs/handoff/cloud-case-ai/design.md` §4-3
- 状態: 設計案作成済み。実装前の本番照合で K2・K3 合格（10-1）。設計審査は未実施（クラウドで行う）。PO は直し方の方向（計算の順番だけを直す）を選択済み（PO「1」2026-11-17。問いは「案のとおり、計算の順番だけを直す【おすすめ】」）。実装は未着手（実装の承認は審査のあとに PO へ聞く）
- 危険便: はい（`migrations/` を変える。ADR-135・ADR-136。GO #番号が要る）
- 段取り表: `docs/handoff/cloud-case-ai/grant-speed-card.md`

## 1. 目的と成功条件（KGI・KPI）

目的: 本番反映のたびに、AI の値を返す口の権限が「今の AI の窓に合った表」へ確実に付け直されるようにする。時間切れで付け直しが抜けると、新しく足した表に権限が付かず、拒否に変わった表から権限が外れない（`scripts/run_all_migrations.sh:268` の警告「値を返す口は前の権限のまま」）。

| 記号 | 基準 | 検証方法 |
|---|---|---|
| K1 | 直した版が本番に出た本番反映で、付け直しの所要が 6 秒以下・失敗の警告 0 行 | 本番反映の記録の `>>> [final] grant ai_unmask_owner done in Ns` の N と、`⚠️ ai_unmask_owner の権限の付け直しに失敗` の行数 |
| K2 | 直した計算と元の計算で、付けるべき表の一覧が本番で完全に同じ | 本番で読み取りだけの照合（段取り表 §6）: 2 つの配列を並べ替えて比べ、`same=t` |
| K3 | 直した計算の所要が本番で 3 秒以下（今は 14.7 秒） | 本番で読み取りだけの `EXPLAIN (ANALYZE)` の Execution Time |
| K4 | 判定（`ops_case.is_denied_source`）を呼ぶ回数が、元の表の名前の数以下 | CI の試験（段取り表 §4 の新しい試験）。元のコードでは失敗し、直したコードで通ること |
| K5 | 付ける・外す表の振る舞いが変わらない | 既存の試験 `backend/tests/ops/test_ops_case_db.py:627`・`:680`・`:697` がそのまま通る |

## 2. 現在地（実測。推測を入れない）

### 2-1. 本番反映での所要（`docs/handoff/cloud-case-ai/grant-speed-evidence/deploy-grant-seconds.txt`）

- 2026-11-10〜11-16 の本番反映 54 回の記録を全部読んだ。成功 52 回・時間切れ 2 回（run 43248537710 と 43813711040。後者は再実行も時間切れで、試行としては 3 回）。
- 成功の回の所要は 11/10〜11 で約 14 秒、11/12〜13 で 15〜16 秒、11/14 で 17〜18 秒、11/15〜16 で 16〜17 秒。11/12 に 28.5 秒の回が 1 回ある（run 43142604068）。
- 成功の回の戻り値（付け直した表の数）はすべて 0。
- 打ち切りは 30 秒（`scripts/run_all_migrations.sh:235` `AI_CLOUD_CREATE_TIMEOUT` の既定、`:267` で `statement_timeout` に渡す）。
- 付け直しのコードは 2026-11-16 の baf555c6d 以後変わっていない（`git log` で確認）。

### 2-2. 本番での内訳（`docs/handoff/cloud-case-ai/grant-speed-evidence/prod-timing-20261117.txt`。2026-11-16 20:02 UTC、読み取りだけの接続 `transaction_read_only=on`）

| 測ったもの | 値 |
|---|---|
| `ai_cloud_meta.build_columns` の行（列の数） | 6,749 |
| その中の元の表の名前（source）の数 | 571 |
| pg_class の行 / 表（r・p） | 5,327 / 666 |
| (B) 付けるべき表を決める計算（`migrations/20261031_210000_create_ops_case.sql:398-405` と同じ文） | 14,705.8 ms・shared hit 2,254,989 |
| (B) の中で判定を呼んだ行 | build_columns の各行（Seq Scan の actual rows 5,857 ＋ Rows Removed by Filter 892 ＝ 6,749） |
| (C) 判定を抜いた同じ突き合わせ | 4.2 ms |
| (D) 今付いている権限を調べる計算（REVOKE の候補の元） | 1.8 ms |
| 判定 1 回（`one_is_denied`。min(source) を探す分を含む） | 8.2 ms |

読み取れる事実:
- 付け直し全体（約 16〜17 秒）のうち 14.7 秒が (B) の 1 文。
- (B) では、判定 `NOT ops_case.is_denied_source(s.source)` が、`DISTINCT` でまとめる前の build_columns の各行（6,749 行）に押し込まれて実行された（計画の `Seq Scan on build_columns b ... Filter: (NOT ops_case.is_denied_source(source))`）。
- 1 回あたり 14,705.8 ÷ 6,749 ＝ 約 2.18 ms・約 334 バッファ。判定の中で pg_class を名前の文字列で探す（`migrations/20261031_210000_create_ops_case.sql:217-222`）ため。
- 親の条件が副問い合わせの中へ押し込まれたことは、上の計画で直接見えている。押し込みを止める方法として公式に書かれているのが `MATERIALIZED`（3-2）。押し込みが費用の見積もりで決まるかどうかは確かめていない（K4 の試験が、小さい試験の DB でも元のコードで赤になることで確かめる）。
- 列は AI の窓に表や列が足されるたびに増える。所要が日ごとに伸びたことと合う。

### 2-3. 判定の関数を呼ぶ場所（`git grep is_denied_source origin/main`、7faae9090）

- backend の申請の受付: 1 申請に 1 回（`backend/app/routers/ops_case.py:572`）
- 値を返す口 `ops_case.unmask_fetch`: 1 回の読み出しに 1 回（`migrations/20261031_210000_create_ops_case.sql:315`）
- 権限の付け直し `ops_case.grant_unmask_owner`: 今回の対象（同 :405）

前の 2 か所は 1 回だけ呼ぶので、1 回あたり数ミリ秒（2-2 の 2.18〜8.2 ms）。今回は変えない。

## 3. 直し方

### 3-1. 変更前（`migrations/20261031_210000_create_ops_case.sql:397-405`）

```sql
    -- 1. 付けるべき表: build_columns の source のうち、拒否に当たらないもの
    SELECT coalesce(array_agg(DISTINCT c.oid), '{}'::oid[])
      INTO v_want
      FROM (SELECT DISTINCT b.source FROM ai_cloud_meta.build_columns b) s
      JOIN pg_catalog.pg_namespace n ON true
      JOIN pg_catalog.pg_class c ON c.relnamespace = n.oid
     WHERE n.nspname || '.' || c.relname = s.source
       AND c.relkind IN ('r', 'p')
       AND NOT ops_case.is_denied_source(s.source);
```

### 3-2. 変更後

```sql
    -- 1. 付けるべき表: build_columns の source のうち、拒否に当たらないもの
    --    判定は source ごとに 1 回だけ呼ぶ。MATERIALIZED で、判定が build_columns の各行へ押し込まれるのを止める
    --    （押し込まれると列の数だけ呼ばれ、本番で 14.7 秒かかった。docs/handoff/cloud-case-ai/grant-speed-design.md）
    WITH s AS MATERIALIZED (
        SELECT DISTINCT b.source FROM ai_cloud_meta.build_columns b
    )
    SELECT coalesce(array_agg(DISTINCT c.oid), '{}'::oid[])
      INTO v_want
      FROM s
      JOIN pg_catalog.pg_namespace n ON true
      JOIN pg_catalog.pg_class c ON c.relnamespace = n.oid
     WHERE n.nspname || '.' || c.relname = s.source
       AND c.relkind IN ('r', 'p')
       AND NOT ops_case.is_denied_source(s.source);
```

- 条件・結合・戻す配列は変えない。変えるのは「判定をどの行に当てるか」だけ。判定は STABLE（`:206`）で、1 つの文の中では同じ source に同じ答えを返すので、付けるべき表の一覧は変わらない（K2 で本番の実物で照合する）。
- `MATERIALIZED` は、親の条件を WITH の中へ押し込まない（PostgreSQL 公式 sql-select「WITH Clause」: 「such folding can be prevented by marking the WITH query as MATERIALIZED」）。本番は PostgreSQL 16（12 以上で使える）。
- PL/pgSQL の `INTO` は文のほぼどこに置いてもよく、WITH から始まる SELECT も同じ（公式 plpgsql-statements 41.5.3）。
- 見込み（推測。K1・K3 で実測して確かめる）: 判定が 571 回以下になり、2.18 ms × 571 ＝ 約 1.2 秒。付け直し全体は 約 16〜17 秒 − 14.7 秒 ＋ 1.2 秒 ＝ 約 3〜4 秒。PO への前の説明「約 1〜2 秒」は計算 (B) だけの見込みで、手順全体では約 3〜4 秒になる。

### 3-3. ファイルの直し方

- 移行のファイル `migrations/20261031_210000_create_ops_case.sql` をその場で直す。理由: このファイルは本番反映のたびに全部流れ（`CREATE OR REPLACE FUNCTION`）、これまでもその場で直してきた（`git log` で fd75ee6cb・108da716a）。新しいファイルを足すと、同じ関数の定義が 2 か所に分かれる。
- 試験を 1 つ足す（段取り表 §4）。

## 4. 対象と対象外

- 対象: `migrations/20261031_210000_create_ops_case.sql` の :397-405 の 1 文（説明の注記を含む）、`backend/tests/ops/test_ops_case_db.py` に試験 1 つ。
- 対象外: `ops_case.is_denied_source` の中身（3 か所が呼ぶ正本。§6 の案 D）、REVOKE・GRANT・USAGE の繰り返し（§2-2 の (D) は 1.8 ms）、`scripts/run_all_migrations.sh` の打ち切り 30 秒、`.github/workflows/`、backend のコード。

## 5. 影響範囲

- 関数 `ops_case.grant_unmask_owner()` を呼ぶのは本番反映の最後の 1 か所だけ（`scripts/run_all_migrations.sh:267`）と試験（`backend/tests/ops/test_ops_case_db.py:489,501,506,631,686,694,702,709`）。`git grep grant_unmask_owner origin/main -- backend/app` は 0 件。
- 付ける・外す権限は変わらない（K2・K5）。AI が読める表は増えも減りもしない。
- 移行の CI（`.github/workflows/migration-test.yml`）は、変えた SQL ファイルを 2 回流して冪等を確かめる。この関数は `CREATE OR REPLACE` なので 2 回流せる。

## 6. 代わりの案と選ばない理由

| 案 | 中身 | 選ばない理由 |
|---|---|---|
| A（採る） | WITH ... MATERIALIZED で判定を名前ごとに 1 回にする | — |
| B | 副問い合わせに `OFFSET 0` を付けて押し込みを止める | 効き目は同じだが、意図が読み取りにくい。公式に書かれた止め方は MATERIALIZED |
| C | 打ち切りの 30 秒を延ばす | PO が選ばなかった案。列が増えるたびにまた伸びる |
| D | 判定の関数の中を速くする（名前の文字列で探すのをやめる等） | 3 か所が呼ぶ正本で、影響が広い。1 回だけ呼ぶ 2 か所は今 数ミリ秒で困っていない。A のあとで K1 が外れたときの次の手 |
| E | 付け直しの中に拒否の条件を書き直して集合で計算する | 拒否の決まりが 2 か所に分かれる（正本は 1 つに保つ決まり） |

## 7. リスクと対処

- 計画がまた変わって押し込まれる: MATERIALIZED は押し込みを止めると公式に書かれている。K4 の試験が呼ぶ回数を CI で毎回数えるので、戻れば赤になる。
- 付ける表の一覧が変わる: 条件は同じ文のまま。K2 で本番の実物で照合する。外れたら、次の本番反映の前に PR を戻す。
- 試験の `SET LOCAL track_functions` が CI の DB の権限で拒まれる: 実装担当は迂回せず止まって報告する（段取り表 §5）。
- 戻し方: PR を戻す PR を出して本番反映する。移行は毎回全部流れるので、戻した版の関数がそのまま入る。データは変えない。

## 8. 外部事例

不要。理由: 原因は本番の実行計画で直接見えており（2-2）、直し方は PostgreSQL 公式に書かれた機能そのもの。効果は自分の本番で K1・K3 として実測する。

## 9. 維持の仕組み

- K4 の試験が、判定を呼ぶ回数を CI で毎回数える（同じ種類の遅れが戻ったら PR の段階で赤）。
- 既存の試験 `backend/tests/ops/test_ops_case_db.py:689`（1 回目が 5 秒未満）はそのまま残す。
- 本番の所要は、本番反映の記録の `done in Ns` に毎回出る（`scripts/run_all_migrations.sh:270`）。2026-12-01 ごろに、直した版のあとの本番反映の N を数え直す（担当: Opus）。

## 10. 未確認

- 直したあとの本番反映の記録の所要（K1）。直した計算だけの所要（K3）は 10-1 で実装前に実測済み。
- 28.5 秒の回（run 43142604068）が他の回より 10 秒以上遅かった理由。その時刻の他の処理との重なりは確かめていない。直したあとは判定の回数が約 12 分の 1 になるので、同じ重なりでも 30 秒に届かない見込み（推測）。

## 10-1. 実装前の本番の照合（2026-11-17 05:36 JST・読み取りだけ・PO が実行）

原本: `docs/handoff/cloud-case-ai/grant-speed-evidence/prod-precheck-20261117.txt`（`transaction_read_only` は on・db_exit 0）。直した計算は SQL の文として本番で流せるので、関数を変える前に照合した。

| 基準 | 判定基準 | 実測 | 判定 |
|---|---|---|---|
| K2 | 新旧の一覧が同じ `same=t` | `same\|t\|506\|506`（新旧とも 506 表） | ○ |
| K3 | Execution Time ≤ 3000 ms | 2172.222 ms（元の計算は 14.7 秒） | ○ |
| 判定を当てる行 | 名前の数（571）だけ | `CTE Scan on s` の Filter に判定が付き、通過 506 ＋ 除外 65 ＝ 571 行。元の計算は build_columns の 6,749 行に付いていた | ○ |

- 判定 1 回あたりの読み取りは 191,580 ÷ 571 ≒ 335 ページで、元の計算（約 334）と同じ。判定そのものの重さは変わらず、回数だけが 6,749 → 571 に減った。
- 見込み（推測）: 付け直し全体は 約 16〜17 秒 − 14.7 秒 ＋ 2.2 秒 ＝ 約 4 秒。K1 の判定基準（6 秒以下）に入る。本番反映の記録で K1 として確かめる。
