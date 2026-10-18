<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 同じ投稿の〆を在庫行に効かせる（規則13）

**対象ADR**: ADR-158（変更なし。§9）  
**recon**: docs/handoff/v102-shime-same-post-stock/recon.md  
**日付**: 2026-10-19  
**担当**: Planner（Opus）。状態: 設計案作成済み・自己審査済み（§11）・PO の実装承認待ち

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
  - `backend/app/services/line_analysis_v102_svc.py` の `_write_results`（:1009）に、規則13の後処理を1か所足す
  - 同じファイルに、規則13の純粋関数を1つ足す
  - `backend/app/services/gemini_raw_copy_v102_soldout_ref.py` の docstring（:1-4）に、規則13の正本（この文書）の場所を1行足す
  - テスト `backend/tests/test_line_analysis_v102_svc.py` に規則13のテストを足す
  - デプロイ後に job 0d3d2a98 を1件だけ解析し直す（本番データの更新。§8）
- 対象外
  - 〆の行そのものが要確認に出ること（今の設計どおり。全 Sold out 行 277 行に共通。変えるなら別の相談）
  - is_current の決め方（`_merge_supplier_products`）、配信の SQL、在庫表の API、GAS 在庫一覧
  - 旧エンジン（v5・v6）の行。v102 の経路を通らない
  - Gemini の書き写し（指示書）。1つの投稿を2件に分けたこと自体は変えない
  - 本文に〆があるのに Sold out 行が無い投稿（recon §5）
  - DB の列・migration

## 3. 規則13（新規）

同じ投稿の中で、次の(a)〜(c)がすべて成り立つ「〆の件」と「在庫の件」の組について、在庫の件を「Sold out」にする。

- (a) 〆の件
  - 販売状況が Sold out、除外が excluded
  - 自分の価格と数量が無い。raw_price と raw_quantity がどちらも空か `none`（大文字小文字・前後の空白を無視）。判定は既存の作法（`backend/app/services/line_analysis_v102_svc.py:1220`）と同じにする
  - 〆の引き継ぎ先（規則8〜12 の soldout_targets）を持たない
- (b) 在庫の件
  - 販売状況が Sold out ではなく、除外も無い
  - 人がこの件の販売状況を直していない（decisions の values.status が None）
- (c) 2つの件の関係
  - 同じ product_id・同じ condition_id（どちらも NULL でない）
  - 在庫の件の行の範囲（line_start〜line_end）が、〆の件の範囲の中にある（〆.line_start ≤ 在庫.line_start、かつ 在庫.line_end ≤ 〆.line_end。4つとも NULL でない）

在庫の件を Sold out にするときは、既存の `apply_value_overrides`（`backend/app/services/v102_human_decisions_svc.py:524`）に `ValueOverrides(status=STATUS_SOLD_OUT)` を渡して重ねる。exclusion は状態マスタの効果から決まる（:550）。excluded を直書きしない。

なぜこの条件か（recon §1・§3 の実データ）
- ゆうきさんの〆は、価格・数量なし・範囲 1〜4。在庫の件の範囲 1〜2 を含む → Sold out にする。
- 倉田さんの完売は ¥7,000 と自分の価格がある。範囲 1〜7 も在庫 1〜11 を含まない → 変えない。
- source_lines の包含では判定できない。ゆうきさんの〆の source_lines は [1, 4] で、2行目を含まないため（recon §4 #2）。
- 引き継ぎ先がある〆は、ループ内の `_apply_soldout_targets`（:1045）で condition が変わりうる。組み合わせを避け、在庫を消さない側に倒す。

## 4. 変更前と変更後

### 4-1. `_write_results`（`backend/app/services/line_analysis_v102_svc.py:1041`）

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

### 4-2. 新しい関数（`_write_results` の直前に置く。DB を使わない純粋関数）

```python
def _sell_out_stock_closed_in_the_same_post(
    pairs: list, base_values: list[dict], decisions: dict[str, Decisions], unit_ids: dict, status_entries: list[dict],
) -> list[dict]:
    """規則13（docs/handoff/v102-shime-same-post-stock/design.md §3）：同じ投稿の〆が範囲に含む、同じ商品・状態の在庫の件を Sold out にする。

    〆は自分の価格・数量が無く、引き継ぎ先も無いものだけ。人が販売状況を直した在庫の件は変えない。元の base_values は変えない。
    """
    closers = [
        (values["product_id"], values["condition_id"], row.line_start, row.line_end)
        for values, (item, row) in zip(base_values, pairs)
        if values["status"] == STATUS_SOLD_OUT and values["exclusion"] == "excluded"
        and not _has_raw_value(row.raw_price) and not _has_raw_value(row.raw_quantity)
        and not item.get(<引き継ぎ先のキー。カード 0-3 で確定>)
        and None not in (values["product_id"], values["condition_id"], row.line_start, row.line_end)
    ]
    if not closers:
        return base_values
    out = []
    for values, (_item, row) in zip(base_values, pairs):
        decision = decisions.get(str(row.id))
        closed = (
            values["status"] != STATUS_SOLD_OUT and values["exclusion"] is None
            and (decision is None or decision.values.status is None)
            and row.line_start is not None and row.line_end is not None
            and any(
                pid == values["product_id"] and cid == values["condition_id"] and start <= row.line_start and row.line_end <= end
                for pid, cid, start, end in closers
            )
        )
        out.append(apply_value_overrides(values, ValueOverrides(status=STATUS_SOLD_OUT), unit_ids, status_entries) if closed else values)
    return out
```

- `_has_raw_value` は :1220 の判定（`raw is not None and str(raw).strip().lower() not in ("", "none")`）を小さな関数に切り出したもの。:1220 もこの関数を使うように置き換え、判定を1か所にする。
- 〆の件自身は自分の範囲を含むが、(b) で Sold out を外しているので、自分を変えることはない。

### 4-3. docstring（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:1-4`）

:4 の末尾に次の1行を足す: 「同じ投稿の〆が在庫の件を Sold out にする規則13は docs/handoff/v102-shime-same-post-stock/design.md §3（line_analysis_v102_svc._sell_out_stock_closed_in_the_same_post）。」

## 5. 代替案と選んだ理由

| 案 | 中身 | 採否と理由 |
|---|---|---|
| A（採用） | 解析の保存の直前に、在庫の件の販売状況を Sold out にする | 販売状況は解析結果の1列が正本。配信・在庫表・ダッシュボード・要確認がすべて同じ値を見る。既存の重ね方（apply_value_overrides）を使い回せる |
| B | 配信の SQL に「同じ投稿の〆が含む行は除く」条件を足す | 在庫表・配信は消えるが、DB 上は In Stock のまま残り、ダッシュボードや要確認と食い違う。重い配信の SQL に extraction_items との比較が増える（在庫表の高速化の取り組みに逆らう） |
| C | is_current（`_merge_supplier_products`）で在庫行を FALSE にする | is_current は「新しい投稿で置き換わった」の印で、意味が違う。行の status を見ない今の作りを崩す。既存テスト（同じ投稿の行は全部 TRUE）と衝突する |
| D | Gemini の指示書を直して1件にまとめさせる | 結果が決定的でない。他の投稿の書き写しにも波及する |
| E | 「〆があれば同じ投稿の同じ商品・状態を全部消す」 | 倉田さんの ¥6,000 残り約400セットを誤って消す（PO 承認の G2 に反する。recon §3） |

## 6. 影響範囲（呼び出し元の全走査）

- `_write_results` を呼ぶのは v102 の解析だけ（`run_v102_analysis`、`backend/app/services/line_analysis_v102_svc.py:1349` から）。新しい投稿の解析と、人の直し後の解析し直し（`backend/app/tasks/tcg_extraction.py:736`）の両方がここを通る。
- 本番の今の行で規則13に当たるのは、ゆうきさんの1組だけ（recon §3 の表。v102 の他3組は〆に価格がある）。マージ前に T2 で数え直す。
- 変わるもの: 当たった在庫の件の status（In Stock → Sold out）と exclusion（なし → excluded）だけ。数量・価格・単位・商品・状態・備考は変えない。
- 当たった在庫の件は、他の Sold out 行と同じく、要確認に「除外」で出る（§10 R-b）。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| T1 規則13の判定 | `pytest backend/tests/test_line_analysis_v102_svc.py -k same_post_closed` で、純粋関数に次の7つの形を渡す。①ゆうきの形（〆 1〜4・価格数量なし、在庫 1〜2）→ 在庫が Sold out・excluded。②倉田の形（完売 1〜7・¥7,000、在庫 1〜11）→ 変わらない。③〆に価格だけある → 変わらない。④状態が違う → 変わらない。⑤範囲の外（〆 5〜6、在庫 1〜2）→ 変わらない。⑥人が在庫の件の販売状況を直している → 変わらない。⑦〆に引き継ぎ先がある → 変わらない。あわせて、元の base_values が変わらないことを確かめる |
| T1b 既存の判定が変わらない | CI の backend pytest が全部通る（`backend/tests/test_line_analysis_v102_svc.py`・`backend/tests/test_gemini_raw_copy_v102_soldout_ref.py`・`backend/tests/test_same_post_rows_pg.py`・`backend/tests/test_v102_soldout_extra_targets_pg.py` を含む） |
| T2 置き換え試験（マージ前・本番の読み取りのみ） | 本番の v102 の現在の行に規則13を SQL で当てて（書き込まない）、当たる在庫の件を全部出す。43e6cac8 の件0 が含まれ、a33d2338・0f12b467 の在庫の件が含まれないこと。当たる件が他にあれば一覧を design に追記し、止めて確かめる |
| T3 本番の確認（デプロイ後に job 0d3d2a98 を解析し直した後） | G1: 43e6cac8 の件0 が status=Sold out・exclusion=excluded になり、配信の条件（時間の窓を除く）を満たさない。G2: a33d2338 の件1 が In Stock のままで、配信の条件を満たす。両方とも在庫表の画面でも確かめる（窓の内なら表示の有無、窓の外なら「窓の外」と記録） |
| T4 他の値が変わらない | job 0d3d2a98 の解析し直しの前後で、2件の product_id・condition_id・unit・price・quantity・note_ja を比べ、変化が0件。件0 の status・exclusion だけが変わる |

## 8. 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 0 | 実装カードの事前点検（カード 0-1〜0-3）。合わなければ止めて Opus へ | Sonnet |
| 1 | §4 のとおり実装し、T1 のテストを足す | Sonnet |
| 2 | T2 の置き換え試験（本番の読み取りのみ） | Sonnet |
| 3 | Reviewer 審査 → CI 緑 → マージ（危険パスを含まない。migrations・deploy.yml・本番 scripts は触らない） | Opus |
| 4 | デプロイ後、job 0d3d2a98 だけを `reanalyze_v102_job` で解析し直す（本番データの更新。PO 承認済みの設計の範囲） | Sonnet（Opus が直前に対象・件数を確認） |
| 5 | T3・T4 を観測し、記録を残す | Sonnet が観測、Opus が判定 |

戻し方: PR を revert してデプロイし、job 0d3d2a98 をもう一度解析し直す（件0 が In Stock に戻る）。DB の列・migration は無いので、データの戻しはこの解析し直しだけで済む。

## 9. ADR を作らない理由

〆の規則1〜12f は、すべて docs/handoff/v102-shime-*/design.md を正本とし、コードの docstring からそこを指す作法で管理されている（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:1`）。規則13もその並びに置く。ADR-158 の決定（is_current の考え方・配信が is_current を見る）は変えない。

## 外部・過去事例の参照と我々への応用

- 該当なし：〆の書き方（同じ投稿の中で、在庫の行の後ろに価格のない〆を1行置く）は、この業務の仕入元の原文に固有の書き方。外部事例で判定の正しさは示せないため、成功の根拠は本番の実データ（recon §3）と T2・T3 の実測で示す。
- 過去事例: 便SP（docs/handoff/v102-same-post-rows/design.md）は、マージ前に本番の読み取りで全件を当てて前後を比べてから出した。今回も同じく T2 で全件に当ててからマージする。

## 10. 弊害・トレードオフ

- R-a: 仕入元が「在庫の行の後ろに、価格のない〆」を書いたのに、実は別の品の〆だった場合、在庫を誤って消す。
  → 同じ商品・同じ状態に限り、範囲の包含も必要にして狭くしている。T2 で全件を見てから出す。誤りが出たら、要確認の画面で販売状況を In Stock に直せば、(b) の人の判断が優先されて戻る。
- R-b: Sold out にした在庫の件も、要確認に「除外」で出る。確認の手間が1投稿あたり1件増える。
  → 他の Sold out 行と同じ扱い。〆の行を要確認に出すかどうかは別の相談（§2 対象外）。
- R-c: 〆に引き継ぎ先がある場合は、規則13を当てない。そのため在庫が残る組がありうる。
  → 今の本番では0組（recon §3）。出たら T2 と同じ SQL で見つけられる。

## 継続

- 守り手: `backend/tests/test_line_analysis_v102_svc.py`
- 規則の正本はこの文書の §3。コードの docstring（§4-2・§4-3）から指す。
- 完了後の監視: T2 の SQL を記録に残す。〆の扱いに不満が出たら、同じ SQL で当たった件を数え直す。
- 次への引き継ぎ: 「〆の行そのものを要確認に出さない」かは、PO から求めがあれば別の便で相談する。

## 11. 審査（Opus による自己審査。独立した第二者のレビューではない）

- 判定: APPROVE（条件付き）。条件はカード 0-1〜0-3 が合うこと。合わなければ実装を止める。
  - 0-1: `_write_results` の :1041-1042 が §4-1 の変更前と同じ
  - 0-2: `STATUS_SOLD_OUT` と `Decisions`・`ValueOverrides`・`apply_value_overrides` が line_analysis_v102_svc.py から使える（import 済みか）
  - 0-3: v102 の件が〆の引き継ぎ先を持つときのキー名（`_apply_soldout_targets` が読むキー）を file:line で確定する
- 照らし合わせたもの
  - PO の KGI → G1・G2 を T3 で○×判定できる。時間の窓の問題は §1 で扱った
  - ADR-158 → is_current は変えない。行の status だけを変える
  - 人の判断の尊重 → (b) と T1 ⑥
  - SSOT → 販売状況の重ね方は apply_value_overrides、価格の有無の判定は :1220 と同じ関数の1か所
  - 検証できるか → T1〜T4 はどれも○×で判定できる
- 未解決: なし（〆の行が要確認に出る件は対象外として明記）
