# design: v102 で円・¥を除いた探し直しで価格の行を見つけた件に price_basis の印を残す

関連 recon: `docs/handoff/v102-price-basis/recon.md`

関連 ADR: ADR-1007（migration は構造だけ・冪等）、ADR-135・ADR-136（migrations/ を含む PR は PO の「GO #PR番号」まで main にマージしない）、ADR-154（配信は needs_review=false に限る。今回は needs_review を変えない）。

## 目的（KGI・○×で判定）
PR #4135 の探し直し（円・¥・￥を除いて価格の行を探す）を通った件を、後から件単位で数えられるようにする。PO 2026-10-11「記録は残したい」、進め方 PO「y」（列を足す設計、migration の前に GO）。
- ○：探し直しで見つけた件の analysis_results.price_basis が `V102:yen_free`。
- ○：それ以外の件の price_basis は NULL。
- ○：needs_review・review_reasons・配信の対象・画面は、変更前と1件も変わらない。

## 2つの PR に分ける理由（事実）
本番の反映は、コンテナの入れ替え（`.github/workflows/deploy.yml:348`〜`:397`）が先、migration（`.github/workflows/deploy.yml:504`〜`:518`）が後。列が無いまま新しいコードが analysis_results に書くと、その間の v102 の解析が失敗する。そこで先に列だけを足し（PR①）、本番で列を確かめてからコードを入れる（PR②）。

## PR①：列を足す（migration のみ・コード変更なし）
- 新規 `migrations/20261011_150000_add_analysis_results_price_basis.sql`：
```sql
-- 構造のみ。値の操作は含めない（ADR-1007）。冪等。
ALTER TABLE public.analysis_results ADD COLUMN IF NOT EXISTS price_basis VARCHAR(100);
COMMENT ON COLUMN public.analysis_results.price_basis IS
    '価格の行の決め方の印（v102）。円・¥を除いた探し直しで見つけた件は V102:yen_free、それ以外は NULL';
```
- `scripts/run_all_migrations.sh` の末尾（`run_sql migrations/20261010_120000_create_analysis_soldout_extra_targets.sql` の後）に、コメント1行「# v102 価格の行の決め方の印 price_basis 列（構造のみ・冪等・ADR-1007）」と `run_sql migrations/20261011_150000_add_analysis_results_price_basis.sql` を追記。
- 型は既存の pid_basis・condition_basis と同じ VARCHAR(100)。DEFAULT なし（既存行は NULL のまま、値の書き換えは起きない）。
- 触らない：コード、他の表、tenant_001.analysis_results（v102 は書かない）。

## PR②：印を書く（PR① の本番反映と列の存在確認の後）
`backend/app/services/gemini_raw_copy_v101.py`
| 箇所 | 前 | 後 |
|---|---|---|
| 定数（`_YEN_MARKS_RE` の隣） | なし | `PRICE_BASIS_YEN_FREE = "yen_free"` |
| `_priced_line`（:162） | 戻り値 `int \| None` | 戻り値 `tuple[int \| None, bool]`＝(行番号, 円を除いた探し直しで見つけたか)。:174 の分岐で見つけたときだけ True |
| `_price_line`（:195） | `int \| None` | `tuple[int \| None, bool]`。`_unpriced_line` の結果は `(n, False)` |
| `parse_v101_response`（:249・:260-261） | `price_line = _price_line(...)` | `price_line, via_yen_free = _price_line(...)`。受理の辞書に、via_yen_free のときだけ `"price_basis": PRICE_BASIS_YEN_FREE` を足す（それ以外はキーを足さない） |
| `build()`（:1341-1342） | gemini_index だけ引き継ぐ | 同じ形で `if "price_basis" in item: one = {**one, "price_basis": item["price_basis"]}` を足す |

`backend/app/services/line_analysis_v102_svc.py`
| 箇所 | 前 | 後 |
|---|---|---|
| 定数（`_PID_BASIS_MAX` :99 の隣） | なし | `_PRICE_BASIS_MAX = 100` |
| `_analysis_values`（:590 付近） | price_basis なし | `"price_basis": (f"V102:{item['price_basis']}"[:_PRICE_BASIS_MAX] if item.get("price_basis") else None)` |
| `_UPSERT_SQL`（:603-620） | 22列 | 列一覧・VALUES・ON CONFLICT の3か所に price_basis を足す（`price_basis = EXCLUDED.price_basis`） |

触らない：needs_review・review_reasons の作り方（:590-598 の reasons）、配信（`backend/app/services/tcg_distribution_svc.py`）、画面・API・i18n、`_extract_one`、#4135 の探し直しの条件そのもの、v10.1 以前の経路（keep_rejected=False ではキーを足さない）。

## 検証基準
|基準|検証方法|
|---|---|
| PR①：migration が素の DB と既存の列がある DB の両方で通る（冪等） | CI「マイグレーションSQL 実行テスト（実DB）」＋ 手元で2回流す |
| PR①：本番で `public.analysis_results.price_basis` が VARCHAR(100)・NULL 許容で存在、既存行は全部 NULL | 本番 SQL（読み取り） |
| PR②：探し直しで見つけた件の受理の辞書に price_basis=yen_free、そのまま見つかる件・v10.1 以前にはキーが無い | 単体試験（`backend/tests/test_gemini_raw_copy_v101.py` の円の試験に追記） |
| PR②：price_basis が抽出（build）を通って v102_items に残る | 単体試験（`_extract_keep` で gemini_trust=True） |
| PR②：`_analysis_values` が `V102:yen_free` / None を返し、needs_review・review_reasons は印の有無で変わらない | 単体試験（`backend/tests/test_line_analysis_v102_svc.py`） |
| PR②：INSERT のバインド値に price_basis が入る | 単体試験（`_statements(...)` の型） |
| PR②：実 DB で書いて読める | PG 試験（migration を試験用スキーマに当てる前例 `backend/tests/test_line_analysis_v102_pg.py:37-45`） |
| PR②：保存済み応答 1,021 回で、変更前と比べた違いは救われた 44 件に price_basis が付くことだけ（needs_review・review の違い 0） | 手元の前後比較 |
| PR②：本番反映後、新しい解析で price_basis が NULL の件が書かれ、解析の失敗 0 | 本番 SQL（読み取り） |

## ロールバック
- PR②：revert（列には NULL か印が残るだけで、読み手が無いので無害）。
- PR①：列を消すのは DROP COLUMN（元に戻せない操作）なので行わない。残しても無害（読み手なし・NULL 許容）。

## 外部・過去事例の参照と我々への応用
外部事例は不要。理由：既存の根拠の列（pid_basis・condition_basis・unit_basis）と同じ型の列を1本足すだけで、社内の前例（`migrations/20261009_180000_v102_engine_columns.sql`、`migrations/20260923_120000_add_work_id_to_analysis_results.sql`）に従う。過去事例からの応用：本番の反映はコンテナの入れ替えが migration より先なので、列の追加とその列に書くコードを別の PR・別の反映に分ける。

## 維持の仕組み
守り手: `backend/tests/test_line_analysis_v102_svc.py`（price_basis の値と、印で needs_review が変わらないことを試験で固定）。印の数え方は `docs/specs/line-analysis-tuning/README.md` §3 の表に1行で記録。
