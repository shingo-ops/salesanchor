---
mode: handoff
---
<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 同じ投稿の〆を在庫行に効かせる（規則13）

> この文書は何か: 1つの投稿の中で「在庫の件」と「価格のない〆の件」に分かれたとき、在庫の件を完売にする規則13の設計書。
> 親: docs/handoff/tcg-import-latest-only/sold-out-rules-handoff.md（LINE完売ルールの認識合わせ。docs/specs/README.md の在庫管理の子）

**対象ADR**: ADR-158（変更なし。§9）  
**recon**: docs/handoff/v102-shime-same-post-stock/recon.md  
**日付**: 2026-10-19（改訂2: 審査2件の指摘を反映）  
**担当**: Planner（Opus）。状態: 設計審査済み（Reviewer APPROVE、§11）・PO 実装承認済み 2026-10-19（Opus の問い「直す作業に入り、本番に入れたあと、ゆうきさんの投稿1件だけを解析し直してよいですか」に PO「y」。job 0d3d2a98 の解析し直しを含む）  
**ADR-1015 の区分**: A（今は無い判定を新しく作る＝新機能。デプロイ後に本番データを1投稿だけ解析し直す）。PO の実装承認を取ってから実装に進む

---

## 1. 目的と成功条件（KGI、PO 承認済み 2026-10-19）

PO の言葉: 「〆が付いた品は在庫から消し、同じ投稿の中でもまだ売っている品は消さない」。

| # | 合格の条件（○×） |
|---|---|
| G1 | ゆうきさんの投稿 43e6cac8 の「9種セット 10個＠19,000円」が、在庫表に出ない |
| G2 | 倉田さんの投稿 a33d2338 の「セット/¥6,000 残り約400セット」が、在庫表に残る |

在庫表には「直近の投稿だけを出す」時間の窓がある。ゆうきさんの投稿（2026-10-18 07:25Z）は、デプロイの頃には窓の外に出ている可能性がある。窓の外に出ただけで「出ない」になると、直したかどうかの証明にならない。そのため G1・G2 は、画面に加えて「その行が配信の条件（時間の窓を除く）を満たすか」を本番DBで確かめて判定する（§7 の T3）。

## 2. 対象と対象外

- 対象
  - `backend/app/services/line_analysis_v102_svc.py`
    - import に `ValueOverrides` を足す（:69-76）
    - `_write_results`（:1009）に規則13の後処理を1か所足す（:1041 の後）
    - 規則13の純粋関数と、`_has_raw_value` を足す
    - `_inherit_price` の価格の有無の判定（:1219-1221）を `_has_raw_value` に置き換える（動きは同じ）
  - `backend/app/services/gemini_raw_copy_v102_soldout_ref.py` の docstring（:1-4）に、規則13の正本（この文書）の場所を1行足す
  - テスト `backend/tests/test_line_analysis_v102_svc.py` に規則13のテストを足す
  - デプロイ後に job 0d3d2a98 を1件だけ解析し直す（本番データの更新。§8。PO の実装承認に含めて承認を取る）
- 対象外
  - 〆の行そのものが要確認に出ること（今の設計どおり。全 Sold out 行 277 行に共通。変えるなら別の相談）
  - is_current の決め方（`_merge_supplier_products`）、配信の SQL、在庫表の API、GAS 在庫一覧
  - 旧エンジン（v5・v6）の行。v102 の経路を通らない
  - Gemini の書き写し（指示書）。1つの投稿を2件に分けたこと自体は変えない
  - 本文に〆があるのに Sold out 行が無い投稿（recon §5）
  - DB の列・migration・状態マスタ

## 3. 規則13（新規）

同じ投稿の中で、次の(a)〜(c)がすべて成り立つ「〆の件」と「在庫の件」の組について、在庫の件を「Sold out」にする。

- (a) 〆の件
  - 販売状況が Sold out、除外が excluded
  - 自分の価格と数量が無い。raw_price と raw_quantity がどちらも空か `none`（大文字小文字・前後の空白を無視）。判定は既存の作法（`backend/app/services/line_analysis_v102_svc.py:1220`）と同じ関数を使う
  - 〆の引き継ぎ先（規則8〜12 の `soldout_targets`。`backend/app/services/line_analysis_v102_svc.py:844` が読むキー）を持たない
  - 人がこの件の商品・状態を直していない（既存の `_has_human_judgement`、`backend/app/services/line_analysis_v102_svc.py:830`）
- (b) 在庫の件
  - 販売状況が Sold out ではなく、除外も無い
  - 人がこの件の販売状況を直していない（decisions の values.status が None）
  - 人がこの件の商品・状態を直していない（`_has_human_judgement` が偽）
- (c) 2つの件の関係
  - 同じ product_id・同じ condition_id（どちらも NULL でない）
  - 在庫の件の行の範囲（line_start〜line_end）が、〆の件の範囲の中にある（〆.line_start ≤ 在庫.line_start、かつ 在庫.line_end ≤ 〆.line_end。4つとも NULL でない）

在庫の件を Sold out にするときは、既存の `apply_value_overrides`（`backend/app/services/v102_human_decisions_svc.py:524`）に `ValueOverrides(status=STATUS_SOLD_OUT)` を渡して重ねる。exclusion は状態マスタの効果から決まる（:550）。excluded を直書きしない。

- 状態マスタの前提: `apply_value_overrides` は "Sold out" が状態マスタの canonical（effect が OUTPUT か EXCLUDE）に無いと、警告を出して重ねない（:547-548）。本番の `tcg_status_master` には canonical="Sold out" の行が11行あり、すべて effect=EXCLUDE・enabled（recon §1-2）。マスタから消えた場合は規則13が働かなくなるだけで、誤って消す側には倒れない。

なぜこの条件か（recon §1・§3 の実データ）
- ゆうきさんの〆は、価格・数量なし・範囲 1〜4。在庫の件の範囲 1〜2 を含む → Sold out にする。
- 倉田さんの完売は ¥7,000 と自分の価格がある。範囲 1〜7 も在庫 1〜11 を含まない → 変えない。
- source_lines の包含では判定できない。ゆうきさんの〆の source_lines は [1, 4] で、2行目を含まないため（recon §4 #2）。
- 引き継ぎ先がある〆は、ループ内の `_apply_soldout_targets`（:1045）で condition が変わりうる。組み合わせを避け、在庫を消さない側に倒す。
- 人の商品・状態の判断は、規則13の後のループ（`_apply_decisions`、:808）で重なる。規則13は人の判断が重なる前の値で比べるため、人が判断した件は〆にも在庫にも使わない。既存テスト `backend/tests/test_line_analysis_v102_svc.py:556`（人の判断を〆が上書きしない）と同じ作法。

## 4. 変更前と変更後

### 4-1. import（`backend/app/services/line_analysis_v102_svc.py:69-76`）

`from app.services.v102_human_decisions_svc import (...)` の並びに `ValueOverrides` を1つ足す（名前の並びは今の順に合わせる）。

変更前: `FIELD_V102_PRICE, Decisions, apply_value_overrides, load_v102_decisions, status_available_by_human, v102_analysis_lock_key`  
変更後: `FIELD_V102_PRICE, Decisions, ValueOverrides, apply_value_overrides, load_v102_decisions, status_available_by_human, v102_analysis_lock_key`

### 4-2. `_write_results`（`backend/app/services/line_analysis_v102_svc.py:1041`）

変更前（:1041-1042）
```python
    base_values = _buyback_units(session, pairs, base_values, unit_ids, extraction_job_id, decisions)  # 便BB。便UP の確認はこの後の単位・状態で走る
    mismatches = _unit_price_mismatches(session, extraction_job_id, base_values)
```

変更後
```python
    base_values = _buyback_units(session, pairs, base_values, unit_ids, extraction_job_id, decisions)  # 便BB。便UP の確認はこの後の単位・状態で走る
    base_values = _sell_out_stock_closed_in_the_same_post(pairs, base_values, decisions, unit_ids, status_entries)  # 規則13
    mismatches = _unit_price_mismatches(session, extraction_job_id, base_values)
```

### 4-3. 新しい関数（`_write_results` の直前に置く。DB を使わない純粋関数）

```python
def _has_raw_value(raw) -> bool:
    """仕入元が値を書いているか（空・none は書いていない）。"""
    return raw is not None and str(raw).strip().lower() not in ("", "none")


def _sell_out_stock_closed_in_the_same_post(
    pairs: list, base_values: list[dict], decisions: dict[str, Decisions], unit_ids: dict, status_entries: list[dict],
) -> list[dict]:
    """規則13（docs/handoff/v102-shime-same-post-stock/design.md §3）：同じ投稿の〆が範囲に含む、同じ商品・状態の在庫の件を Sold out にする。

    〆は自分の価格・数量が無く、引き継ぎ先も無いものだけ。人が判断した件は〆にも在庫にも使わない。元の base_values は変えない。
    """
    closers = [
        (values["product_id"], values["condition_id"], getattr(row, "line_start", None), getattr(row, "line_end", None))
        for values, (item, row) in zip(base_values, pairs)
        if values["status"] == STATUS_SOLD_OUT and values["exclusion"] == "excluded"
        and not _has_raw_value(getattr(row, "raw_price", None)) and not _has_raw_value(getattr(row, "raw_quantity", None))
        and not item.get("soldout_targets")
        and not _has_human_judgement(decisions.get(str(row.id)))
        and None not in (values["product_id"], values["condition_id"], getattr(row, "line_start", None), getattr(row, "line_end", None))
    ]
    if not closers:
        return base_values
    out = []
    for values, (_item, row) in zip(base_values, pairs):
        decision = decisions.get(str(row.id))
        start_line, end_line = getattr(row, "line_start", None), getattr(row, "line_end", None)
        closed = (
            values["status"] != STATUS_SOLD_OUT and values["exclusion"] is None
            and (decision is None or decision.values.status is None)
            and not _has_human_judgement(decision)
            and start_line is not None and end_line is not None
            and any(
                pid == values["product_id"] and cid == values["condition_id"] and start <= start_line and end_line <= end
                for pid, cid, start, end in closers
            )
        )
        out.append(apply_value_overrides(values, ValueOverrides(status=STATUS_SOLD_OUT), unit_ids, status_entries) if closed else values)
    return out
```

- 〆の件自身は自分の範囲を含むが、(b) で Sold out を外しているので、自分を変えることはない。
- 行の列はすべて `getattr(row, ..., None)` で読む。既存テストの行（`backend/tests/test_line_analysis_v102_svc.py:490` の SimpleNamespace）は line_start・line_end を持たないため、属性が無ければ規則13を当てない側に倒す。
- 人が販売状況を Sold out に直した件（価格・数量なし）は〆として扱う。人が「完売」と判断した件なので意図どおり（本番で人の販売状況の直しは0行。§7 T2）。
- decisions の鍵（`str(row.id)`）と `soldout_targets` のキー名は、実装カード 0-2 で今のコードと同じかを確かめる（§11）。

### 4-4. `_inherit_price` の判定の置き換え（`backend/app/services/line_analysis_v102_svc.py:1219-1221`、動きは同じ）

変更前
```python
    raw_price = getattr(row, "raw_price", None)
    if raw_price is not None and str(raw_price).strip().lower() not in ("", "none"):
        return values
```

変更後
```python
    if _has_raw_value(getattr(row, "raw_price", None)):
        return values
```

### 4-5. docstring（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:1-4`）

:4 の末尾に次の1行を足す: 「同じ投稿の〆が在庫の件を Sold out にする規則13は docs/handoff/v102-shime-same-post-stock/design.md §3（line_analysis_v102_svc._sell_out_stock_closed_in_the_same_post）。」

## 5. 代替案と選んだ理由

| 案 | 中身 | 採否と理由 |
|---|---|---|
| A（採用） | 解析の保存の直前に、在庫の件の販売状況を Sold out にする | 販売状況は解析結果の1列が正本。配信・在庫表・ダッシュボード・要確認がすべて同じ値を見る。既存の重ね方（apply_value_overrides）を使い回せる |
| B | 配信の SQL に「同じ投稿の〆が含む行は除く」条件を足す | 在庫表・配信は消えるが、DB 上は In Stock のまま残り、ダッシュボードや要確認と食い違う。重い配信の SQL に extraction_items との比較が増える（在庫表の高速化の取り組みに逆らう） |
| C | is_current（`_merge_supplier_products`）で在庫行を FALSE にする | is_current は「新しい投稿で置き換わった」の印で、意味が違う。行の status を見ない今の作りを崩す。既存テスト（同じ投稿の行は全部 TRUE）と衝突する |
| D | Gemini の指示書を直して1件にまとめさせる | 結果が決定的でない。他の投稿の書き写しにも波及する |
| E | 「〆があれば同じ投稿の同じ商品・状態を全部消す」 | 倉田さんの ¥6,000 残り約400セットを誤って消す（PO 承認の G2 に反する。recon §3） |
| F | 規則13をループの後（人の判断・引き継ぎ先を重ねた後の値）で判定する | ループは1件ずつ重ねて保存する作りで、全件がそろう場所が :1041 しかない。作りを大きく変えずに済む A を選び、人の判断がある件は使わないことで同じ安全を取る |
| G | 範囲（最小〜最大）でなく、Gemini が件に付けた行（source_lines）そのもので比べる | 本番の試算（2026-10-19、/tmp/CC報告ファイル/shime-same-post-20261019/t2b/）。「在庫の行を〆の行がすべて含む」は0件で、ゆうきさんの件（在庫{1,2}・〆{1,4}）も直らない。「同じ行を1つでも持つ」は3件で、斉藤さんの2投稿（c15162e6・02186351）の「◆FB06（259行）／完売（260）／(B品）1BOX@11,000円（261）」が当たる。完売は通常品だけで B品の在庫まで消す誤りになる。範囲で比べる A は 259〜260 が 261 を含まないので当たらない |

## 6. 影響範囲（呼び出し元・読み手の全走査）

- `_write_results` を呼ぶのは v102 の解析だけ（`run_v102_analysis`、`backend/app/services/line_analysis_v102_svc.py:1349` から）。新しい投稿の解析と、人の直し後の解析し直し（`backend/app/tasks/tcg_extraction.py:736`）の両方がここを通る。
- 本番の今の行で規則13に当たるのは、ゆうきさんの1組だけ（T2 の結果。§7）。
- 当たった在庫の件で変わる列: status（In Stock → Sold out）と exclusion（なし → excluded）だけ。数量・価格・単位・商品・状態・備考は変えない。
- `_inherit_price` の価格の有無の判定は `_has_raw_value` 経由になる。式は同じなので結果は変わらない（T1b の既存テストで確かめる）。
- 値が変わったことで、次の読み手の結果が変わる（どれも意図どおり。完売の品として扱われる）
  - 配信・在庫表（`backend/app/services/tcg_distribution_svc.py:242`・:362）: 当たった件が出なくなる（G1 の目的）
  - 完売の一覧（`backend/app/services/tcg_sold_out_results_svc.py:52` `WHERE ar.status = 'Sold out'`）: 当たった件が新しく出る。完売の品なので正しい
  - ダッシュボードの配信可能件数（`backend/app/services/tcg_analysis_dashboard_svc.py:465-480`）: 当たった件の分だけ減る
  - 要確認（`backend/app/services/tcg_condition_review_svc.py:228-245`）: 当たった件に「除外」の理由が付く（§10 R-b）
  - 同じ仕入元の後の投稿の〆の参照（`_STOCK_ITEMS_SQL` :1252・`_SOLD_ITEMS_SQL` :1267）と価格の引き継ぎ（`_INHERIT_PRICE_SQL` :1177-1187 `status IS DISTINCT FROM :sold_out`）: 当たった件は「在庫の参照」から外れ「完売の参照」に入る。完売した品の価格を後の投稿に引き継がなくなる。どれも完売の品の正しい扱い

### 接触面分析（6面）

| 面 | 影響 |
|---|---|
| ①人 | PO・仕入元担当: 在庫表から完売の品が消える（G1）。要確認に「除外」が1投稿あたり1件増えうる（R-b）。誤って消えた場合は要確認で販売状況を直せば戻る |
| ②エージェント | 〆の規則を読む担当は、`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:1` の docstring からこの文書に来る（§4-5）。並行セッション: `.claude-pipeline/active-work.d/` に本件の台帳を置く |
| ③機械 | CI の backend pytest が T1・T1b を毎回回す。新しいフック・定期 job は無い |
| ④データ | analysis_results の status・exclusion だけが変わる。新しい投稿から効き、今の行は job 0d3d2a98 の解析し直しだけで変わる。テナント別の表は触らない |
| ⑤本番 | 普通のデプロイ（migrations・deploy.yml・本番 scripts を含まない）。デプロイ後に1投稿だけ解析し直す（§8 step 4） |
| ⑥外部 | 在庫表を見るお客さん: 完売の品が消える。Gemini は呼ばない（解析し直しは保存済みの書き写しを使う） |

## 7. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| T1 規則13の判定 | `pytest backend/tests/test_line_analysis_v102_svc.py -k same_post_closed`。テストの status_entries には canonical="Sold out"・effect="EXCLUDE" の1行を必ず入れる（今の `_MASTERS` は status_entries が空で、そのままだと①が通らないため）。純粋関数に次の9つの形を渡す。①ゆうきの形（〆 1〜4・価格数量なし、在庫 1〜2）→ 在庫が Sold out・excluded。②倉田の形（完売 1〜7・¥7,000、在庫 1〜11）→ 変わらない。③〆に価格だけある → 変わらない。④状態が違う → 変わらない。⑤範囲の外（〆 5〜6、在庫 1〜2）→ 変わらない。⑥人が在庫の件の販売状況を直している → 変わらない。⑦〆に引き継ぎ先がある → 変わらない。⑧人が在庫の件の商品か状態を直している → 変わらない。⑨人が〆の件の商品か状態を直している → 変わらない。あわせて、元の base_values が変わらないことを確かめる。テスト名にはすべて same_post_closed を入れる |
| T1b 既存の判定が変わらない | CI の backend pytest が全部通る（`backend/tests/test_line_analysis_v102_svc.py`・`backend/tests/test_gemini_raw_copy_v102_soldout_ref.py`・`backend/tests/test_same_post_rows_pg.py`・`backend/tests/test_v102_soldout_extra_targets_pg.py` を含む） |
| T2 置き換え試験（本番の読み取りのみ・実施済み 2026-10-19） | 下の SQL を ai_ro で実行。合格: 結果が 43e6cac8 の件0（job 0d3d2a98、440301・状態14・範囲1〜2）の1行だけ。結果: 1行だけ（○）。a33d2338・0f12b467 の在庫の件は含まれない。人の販売状況の直し（override_status）は本番で0行。job 0d3d2a98 と a33d2338 の job 4cc7a57b には人の直しが1行も無い（recon §1-2）。マージ直前にもう一度実行し、1行でなければ止めて Opus へ |
| T3 本番の確認（デプロイ後に job 0d3d2a98 を解析し直した後） | G1: 43e6cac8 の件0 が status=Sold out・exclusion=excluded になり、配信の条件（時間の窓を除く）を満たさない。G2: a33d2338 の件1（item bc62b077）が status=In Stock・exclusion 空のままで、配信の条件を満たす。G2 の行の is_current が FALSE になっていたら、より新しい倉田さんの投稿で置き換わったのかを確かめ、理由を記録する（規則13が原因でないことを示す）。両方とも在庫表の画面でも確かめる（窓の内なら表示の有無、窓の外なら「窓の外」と記録） |
| T4 他の値が変わらない | job 0d3d2a98 の2件について、解析し直しの前後で product_id・condition_id・unit_id・unit_canonical・price_normalized・quantity_normalized・note_ja を比べ、変化が0件。件0 の status・exclusion だけが変わる。前の値は recon §1-2 の表。解析し直しは今のマスタで行うため、ほかの値が変わることがある。1つでも変わったら、そこで止めて記録し、Opus へ回す（自動で戻さない） |

T2 の SQL（ai_ro のビュー。書き込みなし）
```sql
WITH ar AS (SELECT ar.*, ei.extraction_job_id, ei.line_start, ei.line_end, ei.raw_price, ei.raw_quantity FROM ai_ro.public__analysis_results ar JOIN ai_ro.public__extraction_items ei ON ei.id=ar.extraction_item_id WHERE ar.engine_version LIKE 'v102%'),
shime AS (SELECT s.* FROM ar s WHERE lower(btrim(s.status))='sold out' AND s.exclusion='excluded' AND lower(btrim(coalesce(s.raw_price,''))) IN ('','none') AND lower(btrim(coalesce(s.raw_quantity,''))) IN ('','none') AND s.product_id IS NOT NULL AND s.condition_id IS NOT NULL AND s.line_start IS NOT NULL AND s.line_end IS NOT NULL AND NOT EXISTS (SELECT 1 FROM ai_ro.public__analysis_soldout_extra_targets et WHERE et.analysis_result_id=s.id)),
hit AS (SELECT DISTINCT ON (k.id) k.id AS stock_id, s.id AS shime_id FROM ar k JOIN shime s ON s.extraction_job_id=k.extraction_job_id AND s.product_id=k.product_id AND s.condition_id=k.condition_id AND s.id<>k.id AND s.line_start<=k.line_start AND k.line_end<=s.line_end WHERE lower(btrim(k.status))<>'sold out' AND k.exclusion IS NULL AND k.line_start IS NOT NULL AND k.line_end IS NOT NULL AND NOT EXISTS (SELECT 1 FROM ai_ro.public__item_corrections c WHERE c.extraction_item_id=k.extraction_item_id AND c.field_name='override_status') ORDER BY k.id, s.id)
SELECT ar.extraction_job_id, ar.product_id, ar.condition_id, ar.status, ar.line_start, ar.line_end, ar.is_current FROM hit h JOIN ar ON ar.id=h.stock_id
```
この SQL は人の商品・状態の判断（(a)(b) の `_has_human_judgement`）を見ていない。そのため実装より当たる件が多いか同じになる側の数え方で、1行という結果は上限として使える。

### 結果（2026-10-19）

T3・T4 の結果（事実のみ）。

- デプロイ: deploy 39187571868（headSha f1497588e、c7481387e を含む）が2回目の試行で success。1回目の 39187148522 と 39187571868 の1回目は、PR と無関係な migration の deadlock で失敗した。
- 再解析: job 0d3d2a98 を 02:35:44Z に reanalyze_v102_job で1回実行。status reanalyzed、total 2、needs_review 0。
- T3/G1 ○: 件0 484a573f が In Stock/空 から Sold out/excluded に変わった。在庫表の条件（tcg_distribution_svc.py の dist_base）を DB で再現すると出ない。
- T3/G2 ○: bc62b077 は 466088/14/6000/400/In Stock/空/is_current TRUE のまま変わっておらず、条件を通る。ただし要確認判定（cr）は ai_ro では再現できず、近似で判定した。画面での目視は未実施。
- T4 ○: 2件とも product/condition/unit/price/qty/note/is_current は不変。件1は値が同じで updated_at だけ更新された。
- 斉藤（02186351・c15162e6）と 0f12b467 の在庫件数は前後で同じ。
- 生出力は Mac の /tmp/CC報告ファイル/shime-same-post-20261019/reanalyze/ にある（社外秘のため PR には載せない）。

## 8. 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 0 | 実装カードの事前点検（§11 の 0-1〜0-3）。合わなければ止めて Opus へ | Sonnet |
| 1 | §4 のとおり実装し、T1 のテストを足す | Sonnet |
| 2 | T2 をもう一度実行（本番の読み取りのみ） | Sonnet |
| 3 | Reviewer 審査 → CI 緑 → マージ（危険パスを含まない。migrations・deploy.yml・本番 scripts は触らない） | Opus |
| 4 | デプロイ後、job 0d3d2a98 だけを解析し直す（下の手順）。PO の実装承認にこの1件の解析し直しを含めて承認を取る | Sonnet（Opus が直前に対象・件数を確認） |
| 5 | T3・T4 を観測し、記録を残す | Sonnet が観測、Opus が判定 |

step 4 の手順（本番データの更新は job 0d3d2a98 の2件だけ）
1. 事前の確認（ai_ro・読み取り）: job 0d3d2a98 の解析結果が2件で、値が recon §1-2 の表と同じ。デプロイが成功し、本番のコードに規則13が入っている。違えば止める。
2. 解析し直し: 既存のタスク `reanalyze_v102_job("0d3d2a98-0138-45d4-9ccc-869c2315bdf6")`（`backend/app/tasks/tcg_extraction.py:736`、引数は job の id 1つ。Gemini は呼ばない）を1回だけ実行する。呼び出し方は過去の解析し直し（docs/handoff/g28-bulk-price/design.md:62・:88 と同じタスク）で使った方法に合わせ、実装カードに具体的なコマンドを書く。Opus が直前にコマンドと対象の id を確かめる。
3. 事後の確認: T3・T4。

戻し方: PR を revert してデプロイし、job 0d3d2a98 をもう一度同じ手順で解析し直す（件0 が In Stock に戻る）。DB の列・migration は無いので、データの戻しはこの解析し直しだけで済む（前例: docs/handoff/g28-bulk-price/design.md:88）。

## 9. ADR を作らない理由

〆の規則1〜12f は、すべて docs/handoff/v102-shime-*/design.md を正本とし、コードの docstring からそこを指す作法で管理されている（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:1`）。規則13もその並びに置く。ADR-158 の決定（is_current の考え方・配信が is_current を見る）は変えない。

## 外部・過去事例の参照と我々への応用

- 該当なし：〆の書き方（同じ投稿の中で、在庫の行の後ろに価格のない〆を1行置く）は、この業務の仕入元の原文に固有の書き方。外部事例で判定の正しさは示せないため、成功の根拠は本番の実データ（recon §3）と T2・T3 の実測で示す。
- 過去事例: 便SP（docs/handoff/v102-same-post-rows/design.md）は、マージ前に本番の読み取りで全件を当てて前後を比べてから出した。今回も同じく T2 で全件に当ててからマージする。

## 10. 弊害・トレードオフ

- R-a: 仕入元が「在庫の行の後ろに、価格のない〆」を書いたのに、実は別の品の〆だった場合、在庫を誤って消す。
  → 同じ商品・同じ状態に限り、範囲の包含も必要にして狭くしている。T2 で全件を見てから出す。誤りが出たら、要確認の画面で販売状況を In Stock に直せば、(b) の人の判断が優先されて戻る。
  → 過去の投稿を見て商品が決まった〆（matched_soldout_ref で、引き継ぎ先を持たないもの）も、(a) を満たせば規則13の〆になる。この場合も同じ商品・状態・範囲の包含が要るので、当たるのは同じ投稿の中に同じ品の在庫の件があるときだけ。今の本番では T2 の1行以外に当たる件は無い。
- R-b: Sold out にした在庫の件も、要確認に「除外」で出る。確認の手間が1投稿あたり1件増える。
  → 他の Sold out 行と同じ扱い。〆の行を要確認に出すかどうかは別の相談（§2 対象外）。
- R-c: 〆に引き継ぎ先がある場合、または人が商品・状態を判断した件は、規則13を当てない。そのため在庫が残る組がありうる。
  → 今の本番では0組（T2・recon §1-2）。出たら T2 と同じ SQL で見つけられる。
- R-d: 状態マスタから canonical="Sold out" が消えると、規則13は警告を出して何もしない。
  → 消さない側に倒れる。今の本番では11行あり、すべて EXCLUDE（recon §1-2）。

## 継続

- 守り手: `backend/tests/test_line_analysis_v102_svc.py`
- 規則の正本はこの文書の §3。コードの docstring（§4-3・§4-5）から指す。
- 完了後の監視: T2 の SQL（§7）を使い、〆の扱いに不満が出たら同じ SQL で当たった件を数え直す。
- 次への引き継ぎ: 「〆の行そのものを要確認に出さない」かは、PO から求めがあれば別の便で相談する。

## 11. 審査

### 11-1. 審査の記録
| 回 | 審査者 | 判定 | 主な指摘 | 反映 |
|---|---|---|---|---|
| 1 | Reviewer（Opus のレビュアー担当） | REVISE（軽い） | 人の商品・状態の判断の後で比べていない／import 不足／引き継ぎ先のキーの確定／T2 の SQL と合格の条件／解析し直しの手順と承認の範囲／T4 の列名と止め方／`_has_raw_value` の前後／R-a の追記 | §3・§4-1・§4-3・§4-4・§7・§8・§10 |
| 1 | Fable（開発ルールの審査） | REVISE | import 不足／人の判断の順序／状態マスタに Sold out が無いと黙って重ねない（テストの status_entries）／下流の読み手の漏れ／様式（mode・この文書は何か・既存 ADR の検索・接触面・ADR-1015 の区分） | 冒頭・§3・§6・§7・§10 R-d、recon §0・§1-2 |
| 2 | Reviewer（再審査） | APPROVE | 前回の指摘14件すべて○。注意1件: 行の line_start・line_end を属性で直接読むと、既存テストの行（line_start を持たない）で落ちうる | §4-3 を getattr に統一 |
| 3 | Reviewer（最終版 0c634a941） | APPROVE | getattr・案 G・T2 が実物と生出力に一致。斉藤さんの件は範囲で当たらない（261 ≤ 260 が偽）。既存の `_write_results` を通る単体テストで規則13が働く場面は無い。注意: 案 G の安全は Gemini が〆を 259〜260 に付けることに依る | 案 G の前提として記録（Fable の再審査は PO の判断で行わない。2026-10-19） |

Fable の指摘のうち「`_sold_out_filter` は ADR-1014 由来」は、`git grep ADR-1014` で `backend/app/services/tcg_distribution_svc.py` に0件のため、根拠が確かめられなかった。recon §0 に検索結果だけを書く。

### 11-2. Opus による自己審査（独立した第二者のレビューではない）
- 判定: APPROVE（条件付き）。条件は実装カード 0-1〜0-3 が合うこと。合わなければ実装を止める。
  - 0-1: `_write_results` の :1041-1042 と `_inherit_price` の :1219-1221 が §4 の変更前と同じ
  - 0-2: decisions の鍵が `str(row.id)`、v102 の件の引き継ぎ先のキーが `soldout_targets`（:844）であること
  - 0-3: `_has_human_judgement`（:830）が decision=None を受けて偽を返すこと
- 照らし合わせたもの
  - PO の KGI → G1・G2 を T3 で○×判定できる。時間の窓の問題は §1 で扱った
  - ADR-158 → is_current は変えない。行の status だけを変える
  - 人の判断の尊重 → (a)(b) と T1 ⑥⑧⑨
  - SSOT → 販売状況の重ね方は apply_value_overrides、価格の有無の判定は `_has_raw_value` の1か所
  - 検証できるか → T1〜T4 はどれも○×で判定できる
- 未解決: なし（〆の行が要確認に出る件は対象外として明記）
