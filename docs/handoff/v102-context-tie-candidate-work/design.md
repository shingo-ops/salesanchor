# design: v102 の前後の作品の多数決で、同数のとき候補を持つ作品が1つだけなら決める

この文書は何か：前後の商品の作品が同数で止まっている件を、「その件の候補に無い作品」を除いて決められるようにする小さな変更の設計。
親（設計仕様書）: [docs/specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)（子: [recon.md](recon.md)）

- recon: docs/handoff/v102-context-tie-candidate-work/recon.md
- 状態: Opus 設計、PO 承認済み（2026-10-19「y」。原文は recon.md §1）。
- 参照 ADR: ADR-154（docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:43「作品をまたぐ誤商品判定の防止」。作品をまたぐ誤判定を防ぐ方針と矛盾しない：競合の作品が投稿にあれば決めない条件を維持）。設計仕様書: docs/specs/line-analysis-tuning/README.md（既存・追記なし）。

## 1. 目的
上がドラゴンボール・下が遊戯王のように前後の作品が同数でも、その件の候補に遊戯王が無ければ遊戯王は当てはまらないので、ドラゴンボールで決める。候補を持つ作品が2つ以上同数（例：ドラゴンボールとワンピース）なら今までどおり要確認に回す。

## 2. 変更（backend/app/services/gemini_raw_copy_v102_context_work.py だけ）
- 定数 `RULE_TIE_ONLY_CANDIDATE_WORK = "d"` を RULE_MAJORITY の下に足す。
- モジュール説明の (c) の下に1行足す：`(d) (c) が同数のとき、同数の作品のうち候補を持つ作品が1つだけなら (b) と同じ条件で決める（PO 決定 2026-10-19）`。
- 同数の分岐（:126-128）を次に置き換える。
```python
    ranked = Counter(c.work_id for c in near).most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        top = ranked[0][1]
        candidate_works = {work_of.get(c) for c in candidates}
        tied = [w for w, n in ranked if n == top and w in candidate_works]
        if len(tied) != 1:
            return _undecided(REASON_TIE)
        chosen, _reason = _pick(tied[0], candidates, work_of, post_works, check_competitor=True)
        if chosen is None:
            return _undecided(REASON_TIE)
        return _decided(RULE_TIE_ONLY_CANDIDATE_WORK, chosen, candidates, near)
```
- 触らない: `_clues_near`、規則 (a)(b)(c)、v101、画面、DB、migration。
- 追加テスト: backend/tests/test_gemini_raw_copy_v102_context_work.py（(d) の3件）。

## 3. 受入基準
| 基準 | 検証方法 |
|---|---|
| K1 既存テストが通る | pytest（context_work・followup・score_select・soldout_ref・line_analysis_v102_svc・v102_human_decisions）。DB 必須の12件は CI 専用で手元では動かない（事実：`Disposable CI service required`）ので CI で確認 |
| K2(i) 前にDB2・後ろに遊戯王2、候補 DB/ほか2作品 → DB で決まり rule "d" | 新規単体テスト |
| K2(ii) 前にDB2・後ろにOP2、候補に DB と OP → 決めない（tie） | 新規単体テスト |
| K2(iii) DB1・遊戯王1・ガンダム1の3者同数、候補 DB/ガンダム → 決めない（tie） | 新規単体テスト |
| K3 本番相当の試算で、旧→新で変わる行を全件列挙し、期待の job 6a431a3c-0a69-4f6c-898c-fee0759d928e の 59-60 行が 231 に決まる | ri/fix/tie/sim の出力（手元・社外秘） |

## 4. 弊害とリスク
| # | 弊害 | 対策 |
|---|---|---|
| 1 | 候補外の作品を除くことで、本当は別作品の商品に誤って決める | (b) と同じ競合チェック（落とす候補の作品がその投稿に無いこと）を必須にする。試算で変わる全行を一覧にして確認 |
| 2 | 同数で要確認だった件が減る（意図した効果） | 候補を持つ作品が2つ以上同数なら今までどおり要確認 |

## 5. 戻し方
PR を revert（データ変更なし）。変わった件は再解析で元に戻せる。

## 6. 外部・過去事例の参照と我々への応用
- 外部事例: 不要。理由：自社の投稿データと既存の規則 (b)(c) の条件を同数の場合に当てはめるだけで、新しい手法・依存を入れないため。
- 過去事例（自社）: #4037「前後の商品で作品を決める」の規則 a / b / c の延長。

## 7. 維持の仕組み
- 守り手: backend/tests/test_gemini_raw_copy_v102_context_work.py
- 対象: 同数のときの (d) の決め方と、2作品以上同数なら決めない条件が壊れると困る。CI の backend tests が必須チェックで守る。
