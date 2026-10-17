# ADR-1023: 状態の価値順 — 複数の状態語が当たったら価値の低い状態を採る（v102）

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 備考 | PO 2026-10-17「y」（解析の誤りを直す設計をして本番まで）と、状態の価値順の決定。値の本番投入は Opus が DRY-RUN → COMMIT で行う（ADR-1007）。カートン（case）の順は PO の明示の y が無いため、値の投入前に PO へ再確認する |
| 起案日 | 2026-10-17 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1007（値は migration でなく記録した SQL で入れる）、ADR-1021（Bulk の状態。様式の前例） |

---

## What（何を決めたか）

PO の言葉:

> 状態は悪いものから優先的に採用するように出来る？

> 状態全体の順位を調整する列を新設することは出来る？BoxはSealed box>Damaged sealed box>No shrink box>Opened boxの価値順なので価値の低いものの検索ワードが含まれる場合は価値の低い順番に割り当てをする

> Unsearched pack>Searched pack>AR confirmed pack

> Sealed box > Damaged sealed box > No shrink box  > Opened box > Searched box

1. 状態マスタ `public.line_conditions` に列を 2 つ足す（構造のみ。migration `20261017_120000_line_conditions_value_rank.sql`）。
   - `value_group`（box / case / pack。NULL＝価値順の対象外）
   - `value_rank`（群の中の順位。1＝価値が高い。数字が大きいほど価値が低い）
2. v102 の状態の判定（`_resolve_condition`）だけが `resolve_condition_v2(..., prefer_lowest_value=True)` を使う。
3. 判定の規則（`prefer_lowest_value=True` のとき。主ループで複数の行が当たった場合）:
   - 当たりが 1 つ → それ（今と同じ）。
   - 当たった行の `value_group` が全て同じ（NULL でない）で `value_rank` も全てある → `value_rank` が最大の行（同じ値なら並びの先）。
   - それ以外（NULL を含む・群が違う）→ 並びで最初に当たった行（今と同じ）。
   - R1 の事前検査・R4・R5・R4c の判定は変えない。R4c の内側の再帰呼び出しには同じ指定を渡す。
   - 例: 「シュリンク無し美品」は「美品」（Damaged sealed box）と「シュリンク無し」（No shrink box）の両方に当たる。今は並びが先の Damaged sealed box。この規則では価値の低い No shrink box を採る。
4. 値の表（記録 SQL で入れる。migration には書かない）:
   - box: CN0003 Sealed box 1・CN0004 Damaged sealed box 2・CN0005 No shrink box 3・CN0006 Opened box 4・CN20261008072213 Searched box 5
   - case: CN0001 Case 1・CN0002 Damaged case 2・CN0009 Opened case 3
   - pack: CN0007 Unsearched pack 1・CN0010 Searched pack 2・CN0013 AR confirmed pack 3
   - NULL（対象外）: Empty box・FLAG_SINGLE・Error・Bulk・空箱 Case
5. `load_condition_entries` は `value_rank` の列が `information_schema` に無い DB では列を読まず None を返す（deploy はアプリの入れ替えが migration より先のため）。
6. v102 以外の経路（v6・v10・単位の復元・道具）は変えない（引数の既定は False）。管理画面での表示・編集は別便。

## Why

- 価値の違う状態語が同じ文に混ざると、並び順（priority）で先の状態になり、価値の高い側に寄って配信価格の根拠を誤らせる行がある。
- priority は R1〜R4 の規則の段を兼ねていて、入れ替えると別の判定が変わるため、価値順の専用の列を足す（既定 NULL で今と同じ）。
- 検索語から「美品」を外す案は、美品＝傷ありという PO の 2026-10-08 の決定を覆すため採らない。

## 戻し方

- 値: `docs/handoff/condition-value-rank/data/value_rank_rollback.sql`（11 行を NULL に戻す）→ 判定は今と同じ。
- コード: PR を revert。列は残っても害が無い（NULL）。

## 測り方

- 単体テスト（`TestResolveConditionValueRank`・`TestLoadConditionEntriesValueRank`・v102 の `_resolve_condition` のテスト）が CI で毎回走る。
- 本番: 値の投入後、対象の job を再解析し、前後で現行行の数・状態・単位を数える（`docs/handoff/condition-value-rank/design.md` K6）。

## 維持の仕組み

状態を足すときは、群と順位を決めて値を入れる。recon / design: `docs/handoff/condition-value-rank/`。
