# 実装カード 便1: 区分「シングルセット系」をコードに足す（行が無いうちは今と同じ動き）

> What this document is, in one line:
> Add the product category "シングルセット系" to the v102 analysis code: condition judged like シングル系, unit always Set, and excluded from the bundle-sale reading (ADR-1027). No DB change; nothing changes until a category row exists.

- 親: `docs/handoff/single-set-category/design.md` §5 便1 の表 #1〜#13・§8 受入 K1a〜K2。決めごとは `docs/adr/ADR-1031-single-and-promo-pack-conditions.md` What 6 と `docs/adr/ADR-1027-bundle-sale-reading.md` の追記
- PO の承認: 方針 2026-11-11「1」、作業開始 2026-11-12「1」（作り方の書類を保存して作業を始める）
- 基準: origin/main b0001402d。行番号はすべて、この版で Opus が読んで確かめた
- ブランチ: `release/single-set-category-bin1`（このカードと同じ枝）。既にある枝を checkout して、その上に commit する
- 読んだ決まり: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・10-executor.md
  - 照合: 手順のコマンドは cd で始める・1手順1コマンド・出力に head／tail を付ける・sleep で待たない・gh run view を使わない・プレースホルダを置かない・既存ファイルの直しは前後の文字列を逐語で示す
- 受領確認: 着手の前に、§0 を満たしたかを1行で返してから始める
- 起票: Opus が手元で行う。担当は push までとする（PR は作らない）
  - `scripts/` を触るので、PR は ADR-136 の GO の手順を通す。マージと本番反映は担当が行わない

## なぜ

シングルカードのまとめ売り（例: N種コンプリートセット）が、区分セット系のため状態「Sealed box」になり、単位が枚や Set に揺れて出る。PO の決定で区分「シングルセット系」を作り、状態はシングル系と同じ・単位は Set にそろえ、まとめ売りの読み取りには当てない。この便はコードだけ。区分の行（便2）が本番に無いうちは、どの商品もこの区分に入らないので、解析の結果は変わらない。

## 禁止

- §8 の「触らない」に書いた所を変えない
- 既存の試験ファイルを変えない（新しい試験ファイル 1 本だけ足す）
- 試験の期待値が合わないとき、期待値を書き換えない。止まって NEEDS_DECISION: で返す
- 手元で試験を回さない。CI の結果を読む
- PR を作らない・マージしない・本番に触らない
- force-push しない

## 0. 着手条件（満たさなければ止まって BLOCKED: で返す）

origin/main の次の行が、下の表の「基準の中身」で始まること。1 つでも違えば BLOCKED: で差を返す。

| 場所 | 基準の中身（先頭の語） |
|---|---|
| `backend/app/services/gemini_raw_copy_v102_product_first.py:53` | `PRODUCT_KUBUN_SET = "セット系"` |
| `backend/app/services/gemini_raw_copy_v102_product_first.py:79` | `UNIT_BASIS_FROM_CATEGORY = "from_category"` |
| `backend/app/services/gemini_raw_copy_v102_product_first.py:764` | `_KUBUN_TO_VALUE_GROUP = {` |
| `backend/app/services/gemini_raw_copy_v102_product_first.py:782` | `cond, _cid, basis = resolve_condition_v2(` |
| `backend/app/services/gemini_raw_copy_v102_product_first.py:858` | `def _resolve_unit_from_state(` |
| `backend/app/services/line_analysis_v102_svc.py:54` | `PRODUCT_KUBUN_SINGLE,` |
| `backend/app/services/line_analysis_v102_svc.py:690` | `_SCOPED_GROUP_OF_KUBUN = {` |
| `backend/app/services/line_analysis_v102_svc.py:1070` | `def _apply_bundle(` |
| `backend/app/services/line_analysis_v102_svc.py:1184` | `base_values = [` |
| `scripts/dev/bundle_replay.py:36` | `_BULK_KUBUN = "バルク系"` |
| `scripts/accuracy/llm_compare/fhd_snapshot.py:87` | `vals = [S._apply_bundle(` |

## 1. 手順（この順）

手順1 事前確認（どちらかが失敗したら BLOCKED:）
    cd "$(git rev-parse --show-toplevel)" && git config user.name shingo-cc
    cd "$(git rev-parse --show-toplevel)" && git rev-parse --verify origin/main

手順2 §0 の表の行を読む（例。表の全行を同じ形で読む）
    cd "$(git rev-parse --show-toplevel)" && git show origin/main:backend/app/services/gemini_raw_copy_v102_product_first.py | sed -n '53p;79p;764p;782p;858p'
    cd "$(git rev-parse --show-toplevel)" && git show origin/main:backend/app/services/line_analysis_v102_svc.py | sed -n '54p;690p;1070p;1184p'
    cd "$(git rev-parse --show-toplevel)" && git show origin/main:scripts/dev/bundle_replay.py | sed -n '36p'
    cd "$(git rev-parse --show-toplevel)" && git show origin/main:scripts/accuracy/llm_compare/fhd_snapshot.py | sed -n '87p'

手順3 §2〜§5 の直しを、書いた前後の文字列のとおりに当てる（Edit で 1 か所ずつ）

手順4 §6 の新しい試験ファイルを丸ごと書く

手順5 構文と書式の確かめ（失敗したら直してから進む。§2〜§6 の外を直す必要が出たら NEEDS_DECISION:）
    cd "$(git rev-parse --show-toplevel)" && python3 -m py_compile backend/app/services/gemini_raw_copy_v102_product_first.py backend/app/services/line_analysis_v102_svc.py scripts/dev/bundle_replay.py scripts/accuracy/llm_compare/fhd_snapshot.py backend/tests/test_single_set_category.py
    cd "$(git rev-parse --show-toplevel)/backend" && ruff check app/services/gemini_raw_copy_v102_product_first.py app/services/line_analysis_v102_svc.py tests/test_single_set_category.py 2>&1 | tail -20

手順6 README の sha256 を書き換える（§5-2）
    cd "$(git rev-parse --show-toplevel)" && shasum -a 256 scripts/accuracy/llm_compare/fhd_snapshot.py

手順7 §7 の検索を流す（出力は報告に入れる）

手順8 commit する（§9 の文）
    cd "$(git rev-parse --show-toplevel)" && git add backend/app/services/gemini_raw_copy_v102_product_first.py backend/app/services/line_analysis_v102_svc.py scripts/dev/bundle_replay.py scripts/accuracy/llm_compare/fhd_snapshot.py scripts/accuracy/llm_compare/README.md backend/tests/test_single_set_category.py
    cd "$(git rev-parse --show-toplevel)" && git commit -F /tmp/bin1-commit-msg.txt

手順9 push する（単独で）
    cd "$(git rev-parse --show-toplevel)" && git push -u origin release/single-set-category-bin1

手順10 push を確かめる
    cd "$(git rev-parse --show-toplevel)" && git log --oneline -3
    cd "$(git rev-parse --show-toplevel)" && git rev-parse HEAD origin/release/single-set-category-bin1
    cd "$(git rev-parse --show-toplevel)" && git diff origin/main...HEAD --name-only

## 2. 直し: `backend/app/services/gemini_raw_copy_v102_product_first.py`

### 2-1（#1）区分の定数を足す（:53 の次）

前:
```python
PRODUCT_KUBUN_SET = "セット系"  # 単位の語が無ければ単位を Set にし、状態は箱系と同じく既定で Sealed box にする
PRODUCT_KUBUN_SUPPLY = "サプライ系"
```
（2 行目は先頭だけ示した。行の残りは変えない）

後: :53 と :54 の間に次の 1 行を入れる。
```python
PRODUCT_KUBUN_SINGLE_SET = "シングルセット系"  # 状態はシングル系と同じ群・同じ既定（Single）。単位は書かれた語に関わらず Set（ADR-1031 What 6）
```

### 2-2（#5 の定数）unit_basis のキーを足す（:79 の次）

前:
```python
UNIT_BASIS_FROM_CATEGORY = "from_category"  # 分類から単位を決めたときの unit_basis のキー
```
後: この行の次に 1 行入れる。
```python
UNIT_BASIS_SINGLE_SET_FROM = "single_set_unit_from"  # シングルセット系で Set に置き換える前の、書かれた単位（Set 以外のときだけ）
```

### 2-3（#2・#3）状態の群の表に 1 行・当てるときの区分名の表を足す（:764-769）

前:
```python
_KUBUN_TO_VALUE_GROUP = {
    PRODUCT_KUBUN_SINGLE: (VALUE_GROUP_SINGLE, CONDITION_SINGLE_DEFAULT, BASIS_SINGLE_DEFAULT),
    PRODUCT_KUBUN_PROMO_PACK: (VALUE_GROUP_PROMO_PACK, CONDITION_PROMO_PACK_DEFAULT, BASIS_PROMO_PACK_DEFAULT),
    PRODUCT_KUBUN_BOOKLET: (VALUE_GROUP_BOOKLET, CONDITION_BOOKLET_DEFAULT, BASIS_BOOKLET_DEFAULT),
    PRODUCT_KUBUN_SUPPLY: (VALUE_GROUP_SUPPLY, CONDITION_SUPPLY_DEFAULT, BASIS_SUPPLY_DEFAULT),
}
```
後:
```python
_KUBUN_TO_VALUE_GROUP = {
    PRODUCT_KUBUN_SINGLE: (VALUE_GROUP_SINGLE, CONDITION_SINGLE_DEFAULT, BASIS_SINGLE_DEFAULT),
    PRODUCT_KUBUN_SINGLE_SET: (VALUE_GROUP_SINGLE, CONDITION_SINGLE_DEFAULT, BASIS_SINGLE_DEFAULT),
    PRODUCT_KUBUN_PROMO_PACK: (VALUE_GROUP_PROMO_PACK, CONDITION_PROMO_PACK_DEFAULT, BASIS_PROMO_PACK_DEFAULT),
    PRODUCT_KUBUN_BOOKLET: (VALUE_GROUP_BOOKLET, CONDITION_BOOKLET_DEFAULT, BASIS_BOOKLET_DEFAULT),
    PRODUCT_KUBUN_SUPPLY: (VALUE_GROUP_SUPPLY, CONDITION_SUPPLY_DEFAULT, BASIS_SUPPLY_DEFAULT),
}

# 状態の行の適用区分（app_kubun）と当てるときに使う区分名。app_kubun は区分名の部分一致で当てる
# （tcg_analyzer_svc.app_kubun_matches）ので、適用区分「シングル系」の行は「シングルセット系」に当たらない。
# シングルセット系はシングル系の名前で当てる（ADR-1031 What 6）。
_KUBUN_MATCHED_AS = {PRODUCT_KUBUN_SINGLE_SET: PRODUCT_KUBUN_SINGLE}
```

### 2-4（#4）`_resolve_scoped_condition` の 3 番目の引数（:782-784）

前:
```python
    cond, _cid, basis = resolve_condition_v2(
        block, "", product_kubun, entries, cond_canonical_to_uuid, raw_memo=block, prefer_lowest_value=True
    )
```
後:
```python
    cond, _cid, basis = resolve_condition_v2(
        block, "", _KUBUN_MATCHED_AS.get(product_kubun, product_kubun), entries, cond_canonical_to_uuid,
        raw_memo=block, prefer_lowest_value=True,
    )
```
プロモパック系の要確認の分岐（:788-795 の `app_kubun_matches(..., product_kubun)`）は変えない。

### 2-5（#5）`_resolve_unit_from_state` の説明文と最初の分岐（:862-869）

前:
```python
    """(単位, 単位の区分, unit_basis)。分類と状態から単位を決め直す。

    セット系：単位の語が無ければ単位 Set（状態の単位では置き換えない）。書かれた単位はそのまま。
```
後:
```python
    """(単位, 単位の区分, unit_basis)。分類と状態から単位を決め直す。

    シングルセット系：masters.set_unit があれば、書かれた単位・単位の語の有無に関わらず単位 Set。書かれた単位が
    Set 以外なら unit_basis の single_set_unit_from に残す（ADR-1031 What 6）。set_unit が無ければ、下のほかの区分の規則と同じ。
    セット系：単位の語が無ければ単位 Set（状態の単位では置き換えない）。書かれた単位はそのまま。
```

前（説明文の閉じの直後の分岐の先頭）:
```python
    if product_kubun == PRODUCT_KUBUN_SET:
        if unit is None and masters.set_unit:
```
後: `if product_kubun == PRODUCT_KUBUN_SET:` の行の前に、次の 4 行を入れる（セット系の分岐は変えない）。
```python
    if product_kubun == PRODUCT_KUBUN_SINGLE_SET and masters.set_unit:
        set_unit, set_kubun, _resolved = resolve_unit_v2(masters.set_unit, unit_alias_to_info)
        extra = {UNIT_BASIS_SINGLE_SET_FROM: unit} if unit and unit != set_unit else {}
        return set_unit, set_kubun, {**unit_basis, UNIT_BASIS_FROM_CATEGORY: PRODUCT_KUBUN_SINGLE_SET, **extra}
```

`PRODUCT_KUBUNS_DEFAULTING_TO_BOX`（:72）は変えない（#6）。

## 3. 直し: `backend/app/services/line_analysis_v102_svc.py`

### 3-1（#9）読み込み（:54）

前:
```python
    PRODUCT_KUBUN_SINGLE,
    PRODUCT_KUBUN_SUPPLY,
```
後:
```python
    PRODUCT_KUBUN_SINGLE,
    PRODUCT_KUBUN_SINGLE_SET,
    PRODUCT_KUBUN_SUPPLY,
```

### 3-2（#7）`_SCOPED_GROUP_OF_KUBUN`（:690-695）

前:
```python
    PRODUCT_KUBUN_SINGLE: VALUE_GROUP_SINGLE,
    PRODUCT_KUBUN_PROMO_PACK: VALUE_GROUP_PROMO_PACK,
```
後:
```python
    PRODUCT_KUBUN_SINGLE: VALUE_GROUP_SINGLE,
    PRODUCT_KUBUN_SINGLE_SET: VALUE_GROUP_SINGLE,
    PRODUCT_KUBUN_PROMO_PACK: VALUE_GROUP_PROMO_PACK,
```

### 3-3（#10）`_reads_bundle` を `_apply_bundle` の直前に足す・説明文（:1070-1073）

前:
```python
def _apply_bundle(
    values: dict, block: str, unit_words: dict[str, str], set_words: frozenset[str], unit_ids: dict, bulk_shapes: bool = False,
) -> dict:
    """まとめ売り（N単位セット）を読む（ADR-1027。規則は v102_bundle_svc）。全ての行に当てる。
```
後:
```python
def _reads_bundle(item: dict) -> bool:
    """まとめ売りの読み取り（ADR-1027）を当てる件か。シングルセット系は当てない（ADR-1027 追記 2026-11-11・PO「1」）。"""
    return item.get("product_category") != PRODUCT_KUBUN_SINGLE_SET


def _apply_bundle(
    values: dict, block: str, unit_words: dict[str, str], set_words: frozenset[str], unit_ids: dict, bulk_shapes: bool = False,
) -> dict:
    """まとめ売り（N単位セット）を読む（ADR-1027。規則は v102_bundle_svc）。全ての行に当てる（シングルセット系を除く。ADR-1027 追記 2026-11-11）。
```
説明文の 1 行が 120 字を超えて ruff が止めるときは、括弧の部分を次の行に折る（中身の語は変えない）。

### 3-4（#10）呼ぶ所（:1184-1187）

前:
```python
    base_values = [
        _apply_bundle(values, block, unit_words, set_words, unit_ids, bulk_shapes=item.get("product_category") == PRODUCT_KUBUN_BULK)
        for values, (item, _row), block in zip(base_values, pairs, blocks)
    ]  # ADR-1027：全ての行。バルク系だけ P1・P2 も見る
```
後:
```python
    base_values = [
        _apply_bundle(values, block, unit_words, set_words, unit_ids, bulk_shapes=item.get("product_category") == PRODUCT_KUBUN_BULK)
        if _reads_bundle(item) else values
        for values, (item, _row), block in zip(base_values, pairs, blocks)
    ]  # ADR-1027：全ての行（シングルセット系を除く。ADR-1027 追記 2026-11-11）。バルク系だけ P1・P2 も見る
```
`_apply_bundle` の中・`_apply_bulk_price`・買取の処理・相場の照らし合わせは変えない。

## 4. 直し: `scripts/dev/bundle_replay.py`（#11）

### 4-1 説明文（:13）

前:
```text
kubun_type がバルク系の行は detect_bundle を bulk_shapes=True で読む（design.md §12）。summary.txt は
```
（行の先頭だけ示した。行の残りは変えない）
後: この行の次に 1 行入れる。
```text
kubun_type がシングルセット系の行は当てない（本番と同じ。ADR-1027 追記 2026-11-11）。区分名は _BULK_KUBUN と同じ理由で写す。
```

### 4-2 定数（:36 の次）

前:
```python
_BULK_KUBUN = "バルク系"  # = gemini_raw_copy_v102_product_first.PRODUCT_KUBUN_BULK（:49）。台本は純関数だけを import するので写し、一致は test_v102_bundle.py で固定
```
後: この行の次に 1 行入れる。
```python
_SINGLE_SET_KUBUN = "シングルセット系"  # = gemini_raw_copy_v102_product_first.PRODUCT_KUBUN_SINGLE_SET。一致は test_single_set_category.py で固定
```

### 4-3 1 行の読みを関数にする（`_signature` の後・`main` の前）

前:
```python
def _signature(res: object) -> tuple:
    return (None, None, None) if res is None else (res.kind, res.n, res.unit)  # type: ignore[attr-defined]
```
後: この 2 行の後に、空行 2 つを置いて次の関数を入れる。
```python
def replay_row(r: dict[str, str], unit_words: dict[str, str], set_words: frozenset[str]) -> tuple:
    """1 行を今の規則と新しい規則で読む → (before, res, is_bulk)。シングルセット系は当てない（本番と同じ。ADR-1027 追記 2026-11-11）。"""
    kubun = r.get("kubun_type") or ""
    is_bulk = kubun == _BULK_KUBUN
    if kubun == _SINGLE_SET_KUBUN:
        return None, None, is_bulk
    block = r["body"].replace(_BODY_SEPARATOR, "\n")
    price = (r["price_normalized"] or "").strip() or None
    quantity = read_quantity(r) or None
    before = detect_bundle(block, unit_words, set_words, price, quantity, bulk_shapes=False)  # 今の規則
    res = detect_bundle(block, unit_words, set_words, price, quantity, bulk_shapes=is_bulk)  # 新しい規則
    return before, res, is_bulk
```

### 4-4 `main` のループ（:98-106）

前:
```python
    for r in rows:
        block = r["body"].replace(_BODY_SEPARATOR, "\n")
        price = (r["price_normalized"] or "").strip() or None
        quantity = read_quantity(r) or None
        is_bulk = (r.get("kubun_type") or "") == _BULK_KUBUN
        before = detect_bundle(block, unit_words, set_words, price, quantity, bulk_shapes=False)  # 今の規則
        res = detect_bundle(block, unit_words, set_words, price, quantity, bulk_shapes=is_bulk)  # 新しい規則
        changed = _signature(before) != _signature(res)
```
後:
```python
    for r in rows:
        before, res, is_bulk = replay_row(r, unit_words, set_words)
        changed = _signature(before) != _signature(res)
```
その次の `results.append(...)` の行と、ループの後は変えない。

## 5. 直し: 精度試験の変換器（#12・#12b）

### 5-1 `scripts/accuracy/llm_compare/fhd_snapshot.py:87-88`

前:
```python
    vals = [S._apply_bundle(v, b, unit_words, set_words, unit_ids, bulk_shapes=it.get("product_category") == bulk)
            for v, (it, _r), b in zip(vals, pairs, blocks)]
```
後:
```python
    vals = [S._apply_bundle(v, b, unit_words, set_words, unit_ids, bulk_shapes=it.get("product_category") == bulk)
            if S._reads_bundle(it) else v
            for v, (it, _r), b in zip(vals, pairs, blocks)]
```

### 5-2 `scripts/accuracy/llm_compare/README.md:21`

前（行の後半）:
```text
をそのまま複製。sha256 = `cd63545e1f5fa8a23420385d57285a60805dfa80fe01e11cef0f5916bfbe6987`
```
後:
```text
を複製し、2026-11-12 にシングルセット系をまとめ売りの読み取りから外した（ADR-1027 追記。87-89 行。便1 の本番反映の後に使う）。sha256 = `NEWHASH`
```
`NEWHASH` は、§5-1 を当てた後に手順6 で出た 64 文字に置き換える（`NEWHASH` の語を残さない）。行の前半（元の場所の説明）は変えない。

## 6. 新しい試験ファイル `backend/tests/test_single_set_category.py`（#13。丸ごとこの中身で作る）

```python
"""区分「シングルセット系」（ADR-1031 What 6・ADR-1027 追記 2026-11-11）の試験。DB なし。原文は作り例のみ。

設計: docs/handoff/single-set-category/design.md 便1・受入 K1a〜K1c
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import app.services.gemini_raw_copy_v102_product_first as pf
from app.services import gemini_raw_copy_v101 as v101
from app.services import line_analysis_v102_svc as svc
from app.services import v102_buyback_unit_svc as bb
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from app.services.v102_bundle_svc import KIND_DECIDED
from tests.test_adr1031_single_promo_pack import _COND, _SINGLE, _STATUS
from tests.test_v102_unit_price_check import _MASTERS as _WRITE_MASTERS
from tests.test_v102_unit_price_check import _WriteSession

SS, S, SET = pf.PRODUCT_KUBUN_SINGLE_SET, pf.PRODUCT_KUBUN_SINGLE, pf.PRODUCT_KUBUN_SET
_UNITS = {
    "枚": ("Piece", "枚系"), "piece": ("Piece", "単品系"), "Piece": ("Piece", "単品系"),
    "セット": ("Set", "複合"), "Set": ("Set", "複合"), "Box": ("Box", "箱系"),
}
_PRODUCTS = (
    ProductEntry(id=7, product_code=None, mark=None, work_id=1, search_keywords=("作りまとめ",), exclude_keywords=()),
)
_REPO = Path(svc.__file__).resolve().parents[3]


def _masters(kubun=SS, set_unit="Set"):
    return ProductFirstMasters(
        product_entries=_PRODUCTS, product_kubun={"7": kubun}, condition_unit={"Sealed box": "Box"}, ignore_phrases=(),
        scoped_cond_entries={"single": _SINGLE}, set_unit=set_unit,
    )


def _one(text, line2="3@500円", quantity="3", masters=None):
    raw = f"{text}\n{line2}"
    parsed, errors = v101.parse_v101_response(
        json.dumps({"items": [{"lines": [1, 2], "price": "500円", "quantity": quantity}]}, ensure_ascii=False),
        raw, status_entries=_STATUS,
    )
    assert errors == []
    (row,), _f = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=masters or _masters(),
        cond_entries=_COND, cond_canonical_to_uuid={}, unit_alias_to_info=_UNITS, status_entries=_STATUS,
    )
    return row


def _unit(unit, unit_kubun, kubun=SS, set_unit="Set"):
    return pf._resolve_unit_from_state(
        unit=unit, unit_kubun=unit_kubun, unit_basis={"alias": unit}, product_kubun=kubun, condition="Single",
        basis=pf.BASIS_SINGLE_DEFAULT, masters=_masters(kubun, set_unit), unit_alias_to_info=_UNITS,
    )


# --- 表（区分の置き場は 1 か所） -------------------------------------------------------------------


def test_tables_treat_single_set_like_single():
    assert SS == "シングルセット系"
    assert pf._KUBUN_TO_VALUE_GROUP[SS] == pf._KUBUN_TO_VALUE_GROUP[S]
    assert pf._KUBUN_MATCHED_AS == {SS: S}
    assert svc._SCOPED_GROUP_OF_KUBUN[SS] == pf.VALUE_GROUP_SINGLE
    assert SS not in pf.PRODUCT_KUBUNS_DEFAULTING_TO_BOX


# --- K1a 判定の段 -------------------------------------------------------------------------------


def test_k1a_without_unit_word_is_set_and_single_r7():
    row = _one("作りまとめ")
    assert row["product_category"] == SS
    assert (row["condition"], row["condition_basis"], row["unit"]) == ("Single", "R7:単品既定", "Set")
    assert row["unit_basis"][pf.UNIT_BASIS_FROM_CATEGORY] == SS
    assert pf.UNIT_BASIS_SINGLE_SET_FROM not in row["unit_basis"]


def test_k1a_piece_count_in_parentheses_is_still_set():
    row = _one("作りまとめ (12枚)")
    assert (row["condition"], row["unit"]) == ("Single", "Set")


def test_k1a_written_set_unit_is_set():
    row = _one("作りまとめ", line2="3セット@500円")
    assert (row["condition"], row["unit"]) == ("Single", "Set")
    assert pf.UNIT_BASIS_SINGLE_SET_FROM not in row["unit_basis"]


def test_k1a_psa10_word_is_psa10():
    assert _one("作りまとめ PSA10")["condition"] == "PSA10"


def test_k1a_unit_rule_piece_becomes_set_and_keeps_the_written_unit():
    assert _unit("Piece", "枚系") == (
        "Set", "複合", {"alias": "Piece", pf.UNIT_BASIS_FROM_CATEGORY: SS, pf.UNIT_BASIS_SINGLE_SET_FROM: "Piece"},
    )


def test_k1a_unit_rule_no_unit_and_set_unit_do_not_add_the_written_unit():
    assert _unit(None, "") == ("Set", "複合", {"alias": None, pf.UNIT_BASIS_FROM_CATEGORY: SS})
    assert _unit("Set", "複合") == ("Set", "複合", {"alias": "Set", pf.UNIT_BASIS_FROM_CATEGORY: SS})


def test_k1a_without_set_unit_in_masters_is_same_as_single():
    for unit, unit_kubun in (("Piece", "枚系"), (None, "")):
        assert _unit(unit, unit_kubun, set_unit=None) == _unit(unit, unit_kubun, kubun=S, set_unit=None)


def test_k1a_single_unit_is_unchanged():
    assert _unit("Piece", "枚系", kubun=S) == ("Piece", "枚系", {"alias": "Piece"})


def test_k1a_set_category_is_unchanged():
    row = _one("作りまとめ", masters=_masters(SET))
    assert (row["condition"], row["unit"]) == ("Sealed box", "Set")


# --- K1b 書き込みの段（本物の _write_results） ---------------------------------------------------

_RAW = "【見出し】\n作りまとめ 100枚セット\n5セット@26,000円"
_W_MASTERS = {**_WRITE_MASTERS, "product_first": _masters(), "unit_alias_to_info": _UNITS}


def _written(kubun):
    item = {
        "unit": "Set", "product_id": 1, "match_status": "matched", "condition": "Single",
        "condition_basis": pf.BASIS_SINGLE_DEFAULT, "price_normalized": 26000, "quantity_normalized": 5,
        "product_category": kubun, "unit_basis": {"alias": None},
    }
    rows = [SimpleNamespace(id="row0", gemini_index=0, source_lines=[2, 3], line_start=2, line_end=3, raw_price=None)]
    session = _WriteSession([], [])
    svc._write_results(
        session, "job1", {"v102_items": [{"lines": [2, 3], "gemini_index": 0, **item}], "v102_flags": {}},
        rows, _W_MASTERS, {"Piece": 12, "Set": 13}, None, _RAW,
    )
    (row,) = [p for sql, p in session.calls if "INSERT INTO public.analysis_results" in sql]
    return item, row


def test_k1b_single_set_is_not_read_as_bundle():
    _item, row = _written(SS)
    assert (row["unit_canonical"], row["bundle_size"]) == ("Set", None)
    assert (row["price_normalized"], row["quantity_normalized"]) == (26000, 5)
    assert row["review_reasons"] is None


def test_k1b_single_set_condition_id_is_from_single_group():
    _item, row = _written(SS)
    assert row["condition_id"] == svc._scoped_condition_id("Single", S, _W_MASTERS)


def test_k1b_set_and_single_still_read_as_bundle():
    for kubun in (SET, S):
        _item, row = _written(kubun)
        assert (row["unit_canonical"], row["bundle_size"]) == ("Piece", 100)


def test_k1b_single_set_is_not_a_buyback_candidate():
    item, _row = _written(SS)
    values = {"pid_resolved": True, "product_id": 1, "price_normalized": 26000, "bundle_size": None}
    assert bb.is_candidate(item, values, _UNITS) is False


# --- K1c 当て直しの台本と精度試験の変換器 ----------------------------------------------------------


def _replay_module():
    spec = importlib.util.spec_from_file_location("bundle_replay_single_set", _REPO / "scripts" / "dev" / "bundle_replay.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # `if __name__ == "__main__"` のため main は走らない
    return module


def test_k1c_replay_constant_matches_product_first():
    assert _replay_module()._SINGLE_SET_KUBUN == SS


def test_k1c_replay_row_skips_single_set_and_keeps_others():
    m = _replay_module()
    unit_words, set_words = m.split_unit_words({"枚": "Piece", "セット": "Set", "set": "Set"})
    base = {"body": "作りまとめ 100枚セット / 5セット@26,000円", "price_normalized": "26000", "quantity_normalized": "5", "price_basis": ""}
    assert m.replay_row({**base, "kubun_type": SS}, unit_words, set_words) == (None, None, False)
    before, res, is_bulk = m.replay_row({**base, "kubun_type": SET}, unit_words, set_words)
    assert is_bulk is False and (res.kind, res.n) == (KIND_DECIDED, 100) and (before.kind, before.n) == (KIND_DECIDED, 100)


def test_k1c_reads_bundle_is_false_only_for_single_set():
    assert svc._reads_bundle({"product_category": SS}) is False
    for kubun in (SET, S, pf.PRODUCT_KUBUN_BULK, pf.PRODUCT_KUBUN_BOX, None):
        assert svc._reads_bundle({"product_category": kubun}) is True


def test_k1c_fhd_snapshot_uses_reads_bundle():
    text = (_REPO / "scripts" / "accuracy" / "llm_compare" / "fhd_snapshot.py").read_text(encoding="utf-8")
    assert "S._reads_bundle(" in text
```

ruff が行の長さ（120 字）で止めた行は、引数の切れ目で折る。中身の値・期待値は変えない。

## 7. 検索（出力を報告に入れる）

手順7 の命令
    cd "$(git rev-parse --show-toplevel)" && git grep -n "PRODUCT_KUBUN_SINGLE_SET\|_SINGLE_SET_KUBUN\|_reads_bundle\|_KUBUN_MATCHED_AS\|UNIT_BASIS_SINGLE_SET_FROM" -- backend scripts | head -40
    cd "$(git rev-parse --show-toplevel)" && git grep -n "NEWHASH" -- scripts | head -5
    cd "$(git rev-parse --show-toplevel)" && git diff origin/main --stat | tail -10

期待: 1 つ目は §2〜§6 で足した所だけ。2 つ目は 0 行。3 つ目は §8 の 6 ファイルだけ。

## 8. 変えるファイル（これ以外は変えない）

- `backend/app/services/gemini_raw_copy_v102_product_first.py`
- `backend/app/services/line_analysis_v102_svc.py`
- `scripts/dev/bundle_replay.py`
- `scripts/accuracy/llm_compare/fhd_snapshot.py`
- `scripts/accuracy/llm_compare/README.md`
- `backend/tests/test_single_set_category.py`（新規）

触らない:
- `_apply_bundle`・`detect_bundle`（`backend/app/services/v102_bundle_svc.py`）の中
- 買取の処理（`backend/app/services/v102_buyback_unit_svc.py`）・相場の照らし合わせ（`backend/app/services/v102_unit_price_check_svc.py`）
- `PRODUCT_KUBUNS_DEFAULTING_TO_BOX`・セット系とシングル系の分岐・プロモパック系の要確認の分岐
- 既存の試験ファイル（`backend/tests/test_v102_bundle.py` 等）
- DB（line_conditions・tcg_product_categories）・migrations/・deploy.yml・.github/・frontend/

## 9. commit の文

手順8 の前に、次の中身で `/tmp/bin1-commit-msg.txt` を作る（ヒアドキュメントで丸ごと書く）。

```text
feat(v102): add product category シングルセット系 (single-card bundle sets)

- condition judged with the single group (default Single, R7), matched as シングル系
- unit always Set when the Set unit row exists; keep the written unit in unit_basis.single_set_unit_from
- exclude シングルセット系 from the bundle-sale reading (ADR-1027 addendum): _reads_bundle in one place,
  used by _write_results, fhd_snapshot.py and bundle_replay.py
- tests: backend/tests/test_single_set_category.py (K1a-K1c)

No DB change. Nothing changes until the category row (bin 2) exists.
Design: docs/handoff/single-set-category/design.md

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

## 10. 分岐（起きたこと → どうする）

| 起きたこと | どうする |
|---|---|
| §0 の行が基準と違う | BLOCKED: で差を返す |
| §2〜§5 の「前」の文字列が見つからない | 直さずに BLOCKED: で、探した文字列と近くの実物の行を返す |
| ruff が行の長さで止める | 折り返すだけで直す。中身を変えない |
| ruff が上の外の指摘を出す（今ある指摘） | 直さない。報告に生の出力を入れる |
| py_compile が失敗する | 自分の直しの誤りなら直す。分からなければ BLOCKED: |
| 試験の期待値が合わない（CI で分かる） | 期待値を変えない。担当は CI を待たないので、この分岐は Opus が扱う |
| §6 の import 先の名前（`_COND`・`_SINGLE`・`_STATUS`・`_MASTERS`・`_WriteSession`・`KIND_DECIDED`）が無い | 作らずに BLOCKED: で、どの名前が無いかを返す |
| push が拒まれる | 回り道をしない。BLOCKED: で生の出力 |

## 11. 合格の基準

| 基準 | 確かめ方 | 誰が |
|---|---|---|
| §8 の 6 ファイルだけが変わる | 手順10 の `git diff origin/main...HEAD --name-only` | 担当 |
| 構文と書式 | 手順5 | 担当 |
| K1a〜K1c | CI（新しい試験ファイル） | Opus が PR の CI を読む |
| K2 既存の試験が通る・既存の試験ファイルが変わらない | CI と name-only | Opus |
| README に `NEWHASH` の語が残っていない・sha256 が実物と合う | 手順7 の 2 つ目 | 担当 |

## 12. 終わりの報告

- `DONE`／`BLOCKED: 理由`／`NEEDS_DECISION: 問い` のどれかで始める
- 停止したときは、その場で手を止める。止まった手順・命令・生の出力を返す。自分で回り道を作らない
- 報告に入れるもの:
  - push した HEAD（40 桁）と `git log --oneline -3` の生の出力
  - 手順5 の ruff の生の出力
  - 手順6 の shasum の生の出力
  - §7 の 3 つの検索の生の出力
  - `git diff origin/main...HEAD --name-only` の生の出力
- 推測で埋めない。読めなかった出力は「読めなかった」と書く

## 13. 反映の後（Opus と PO が行う。担当はしない）

- PR の CI と、新しく起動した審査役の APPROVE を Opus が確かめる
- ADR-136: Opus が PO に対象・変更 3 行・直前のバックアップを見せ、PO の「GO #番号」を受けてからマージする
- K3: 反映の時点で、シングルセット系の商品が 0 件であることを reader で数える

END OF CARD
