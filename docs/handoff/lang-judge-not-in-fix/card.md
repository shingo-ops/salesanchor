# 実装カード：相手の言語の判定（recipient-language）が毎回 500 になる SQL の誤りを直す

- このカードは recon（現在地の確認）を兼ねる：`docs/handoff/lang-judge-not-in-fix/card.md`
- 発見の経緯：prod1 のメモリ見直し（PR #3909）の便②の受入確認の途中で見つかった。
  - 2026-10-04 04:51:48Z、PO が受信箱を開いたときに 500 が出た。
  - PO の決定（2026-10-05）：修正カードの作成に「y」。
- 関連する PR：#2542（2026-06-24、コミット 61d833b52）。このときに `backend/app/services/lang_judge.py` が新しく追加された。
- 対象の ADR：`docs/adr/ADR-110-sa-translation-subsystem.md`（ADR-110-sa-translation-subsystem。:72「送信ガード」の原則。#2542 の本文で参照）。今回の修正は、ADR の決定は変えず、SQL の書き方だけを直す。

## 現在地（事実）
- 本番の backend のログ（2026-10-04）：
  ```
  Database error: GET /api/v1/leads/4/recipient-language - (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.PostgresSyntaxError'>: syntax error at or near "$2"
    ... AND cl.channel_type    NOT IN $2
  [parameters: (4, ('phone', 'in_person'))]
  ```
- 件数（prod2 の Loki、nginx）：2026-09-25〜10-02 の recipient-language は 42 件で、42 件すべてが 500。200 は 0 件。
- 誤りの箇所
  - `backend/app/services/lang_judge.py:84`
  - `backend/app/services/lang_judge.py:122`
  - どちらも `text()` の中に `NOT IN :excluded_channels` と書き、`:31` のタプル `_EXCLUDED_MANUAL_CHANNELS = ("phone", "in_person")` を渡している。
- 同じ誤りは、ほかに無い（`git grep -n -E 'IN :[a-z_]+' origin/main -- backend/app` の該当は、この2行だけ）。
- リポジトリでの書き方：リストを渡すときは `= ANY(:名前)` が 20 か所（例：`backend/app/routers/leads.py:280`、`backend/app/routers/contact_channel_links.py:161`）。`expanding=True` は 0 件。
- 呼び出し元は `backend/app/routers/leads.py:3165` の1か所だけ（async、await 付き）。
- 既存のテスト `backend/tests/test_lang_judge.py` は、`db.execute` を偽物にしており、SQL の文字列と引数を確かめていない。そのため、この誤りを検出できなかった。

## 変更（変更前 → 変更後）
| # | 箇所 | 変更前 | 変更後 |
|---|---|---|---|
| s1 | `backend/app/services/lang_judge.py:84` | `AND cl.channel_type    NOT IN :excluded_channels` | `AND cl.channel_type    <> ALL(:excluded_channels)` |
| s2 | `backend/app/services/lang_judge.py:122` | 同上 | 同上 |
| s3 | `backend/app/services/lang_judge.py:92` と `:127` | `"excluded_channels": _EXCLUDED_MANUAL_CHANNELS,` | `"excluded_channels": list(_EXCLUDED_MANUAL_CHANNELS),` |

- 意味が変わらない根拠：PostgreSQL では、`x NOT IN (a, b)` と `x <> ALL(ARRAY[a, b])` は、x が NULL のときも含めて同じ結果になる。この点は、事前の確かめで、本番の DB に実際に流して確認する。
- それ以外の行（SELECT の列、JOIN、スキーマ名の f-string、多数決の論理）は変えない。

## テスト（TDD：先に赤を確認する）
- `backend/tests/test_lang_judge.py` に、次のテストを追加する。
  - `db.execute` に渡された SQL の文字列（`str(query)` または `query.text`）を記録する。
  - 2回の execute の両方で、次の2つを確かめる。
    - SQL に `NOT IN :excluded_channels` が含まれず、`<> ALL(:excluded_channels)` が含まれること。
    - params の `excluded_channels` が list であること。
  - 修正前は赤、修正後は緑になる。
  - 既存のテストの `fake_execute`（`:26`）の書き方に合わせる。
- 実際の PostgreSQL での確認は、次の「事前の確かめ」で行う。CI の SQLite では、この誤りを再現できないため。

## 事前の確かめ（マージの前。本番の DB に読み取りのみ）
- 修正後の2本の SELECT を、prod1 の postgres コンテナで `psql` を使って読み取りのみで実行する。
  - lead_id は 4、tenant は本番のログに出たリクエストのテナントにする（特定できなければ止める）。
  - `excluded_channels` には `ARRAY['phone','in_person']` を渡す。
  - 構文エラーが出ずに行が返ることと、件数の値を記録する。
- あわせて、`SELECT NULL::text <> ALL(ARRAY['phone','in_person']), NULL::text NOT IN ('phone','in_person'), 'line' <> ALL(ARRAY['phone','in_person']), 'line' NOT IN ('phone','in_person'), 'phone' <> ALL(ARRAY['phone','in_person']), 'phone' NOT IN ('phone','in_person');` の結果で、2つの書き方が同じ結果になることを確かめる。

## 受入条件（○×）
| 基準 | 検証方法 |
|---|---|
| s1〜s3 が表のとおりに変わっている | `git diff`、行ごとに○× |
| 新しいテストが、修正前に赤、修正後に緑 | CI。または、prod2 の使い捨てのコンテナでの red/green |
| 本番の DB で、修正後の SQL が構文エラーにならず、行を返す | 事前の確かめの psql の出力 |
| 反映した後、recipient-language が 200 を返す | nginx と Prometheus の status 別の件数（反映後に PO が受信箱でリードを開いたとき） |
| 範囲外のファイルを触っていない | `git diff --name-only` |

## 外部・過去事例の参照と我々への応用
- 公式の仕様：SQLAlchemy 2.0 の `text()` で IN にリストを渡すには、`bindparam(..., expanding=True)` が必要（Context7 `/websites/sqlalchemy_en_20_core`、`TextClause.bindparams` と `ColumnOperators.in_`）。このリポジトリでは、その代わりに PostgreSQL の配列演算子（`= ANY(:x)`）を 20 か所で使っているので、それに合わせて `<> ALL(:x)` にする。
- 外部の一般事例は使わない。

## 維持の仕組み
- 守り手: `backend/tests/test_lang_judge.py` の新しいテスト（SQL の文字列と、params の型を確かめる）。

## 戻し方
- PR を revert する（今は毎回 500 なので、戻しても悪くはならない）。
