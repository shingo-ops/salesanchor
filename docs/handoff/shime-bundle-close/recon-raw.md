# 〆の束ね（Fb-09／Fb-10／〆）調査メモ 2回目（読むだけ・推測なし）

基準: origin/main 9d4b1e7285a39f3ddabaef5eb6c6747bdf3ed822。パスはリポジトリ直下から。コードはそのまま写した。分からないことは「未確認」。

## (a) price_line が件ごとに一意だと前提している所

### 重複を落とす所（案の直す対象）

`backend/app/services/gemini_raw_copy_v101.py:251-251`
```python
    seen_price_lines: set[int] = set()
```

`backend/app/services/gemini_raw_copy_v101.py:259-271`
```python
        price_line, via_yen_free = _price_line(
            obj, numbers, lines, status_entries, half_width_slash=keep_rejected, yen_free=keep_rejected,
        )
        if price_line is None:
            errors.append({"index": index, "error": "価格の行が見つからない", "item": obj})
            rejected.append(_rejected_entry(REJECTED_PRICE, index, obj, "価格の行が見つからない", len(lines)))
            continue
        if price_line in seen_price_lines:
            message = f"price_line {price_line} がほかの件と同じ"
            errors.append({"index": index, "error": message, "item": obj})
            rejected.append(_rejected_entry(REJECTED_DUPLICATE, index, obj, message, len(lines), price_line))
            continue
        seen_price_lines.add(price_line)
```

価格 none の件の price_line を決める所（二つの件が同じ〆の行に決まる理由）:

`backend/app/services/gemini_raw_copy_v101.py:187-210`
```python


def _unpriced_line(numbers: list[int], lines: list[str], quantity: str, status_entries: list[dict] | None) -> int:
    """価格が none の件：数量の文字か売り切れの言葉を含む最初の行。無ければ lines の最後の行。"""
    for n in numbers:
        text = lines[n - 1]
        has_quantity = quantity != _NONE and bool(_squash(quantity)) and _squash(quantity) in _squash(text)
        if has_quantity or _is_sold_out(text, status_entries):
            return n
    return numbers[-1]


def _is_sold_out(text: str, status_entries: list[dict] | None) -> bool:
    return bool(status_entries) and resolve_status_v2(text, status_entries)[1] == "excluded"


def _price_line(
    obj: dict, numbers: list[int], lines: list[str], status_entries: list[dict] | None, *, half_width_slash: bool = False,
    yen_free: bool = False,
) -> tuple[int | None, bool]:
    """(価格の行, 円を除いた探し直しで見つけたか)。"""
    if obj["price"].strip().lower() != _NONE:
        return _priced_line(numbers, lines, obj["price"], half_width_slash=half_width_slash, yen_free=yen_free)
    return _unpriced_line(numbers, lines, obj["quantity"].strip(), status_entries), False
```

→ lines が [品名の行, 〆の行] の件が2つあると、`_unpriced_line` は数量の語か売り切れの語の最初の行、無ければ `numbers[-1]`（〆の行）を返す。どちらの場合も2件とも〆の行になる（コードから読める事実。実データでの確認は未確認）。

### price_line をキーに辞書を作る所（同じ値が2件あると後の件が前の件を上書きする）

`backend/app/services/gemini_raw_copy_v101.py:602-602`
```python
    by_price_line = {it["price_line"]: i for i, it in enumerate(items)}
```

`backend/app/services/gemini_raw_copy_v101.py:605-607`
```python
    review: dict[int, list[dict]] = {}
    for n, kind in sorted(ambiguous.items()):
        up_i, low_i = by_price_line[prev[n]], by_price_line[nxt[n]]
```

`backend/app/services/gemini_raw_copy_v101.py:615-615`
```python
        target_i = by_price_line[decision[0]["price_line"]]
```

`backend/app/services/gemini_raw_copy_v101.py:1212-1216`
```python
    by_price_line = {it["price_line"]: i for i, it in enumerate(items)}
    found: dict[int, tuple[str, dict]] = {}
    for i, item in enumerate(items):
        before = prev.get(item["price_line"])
        j = by_price_line.get(before) if before is not None else None
```

`backend/app/services/gemini_raw_copy_v101.py:1474-1474`
```python
    owners = {it["price_line"]: it for it in items}
```

`backend/app/services/gemini_raw_copy_v101.py:1571-1571`
```python
    owners = {it["price_line"]: it for it in adjusted}
```

`owners`（1474・1571）の使い道:

`backend/app/services/gemini_raw_copy_v101.py:700-717`
```python
def _name_parts(
    item: dict, roles: dict[int, str], lines: list[str], owners: dict[int, dict], ctx: V101Context,
) -> list[str]:
    parts: list[str] = []
    for n in item["lines"]:
        text, role = lines[n - 1], roles[n]
        owner = owners.get(n)
        if role == ROLE_PRICE or (role == ROLE_NAME and owner is not None):
            part = _price_line_name(text, owner or item, ctx)
        elif role == ROLE_NAME:
            part = text.strip(v10._EDGE_CHARS)
        elif role == ROLE_SHIP and _is_heading_position(item, roles, n):
            part = _split_ship(text, is_heading=True)[1].strip(v10._EDGE_CHARS)
        else:
            part = ""
        if part.strip():
            parts.append(part.strip())
    return parts
```

### 集合・最大・最小で使う所（同じ値が重複しても動く）
- `backend/app/services/gemini_raw_copy_v101.py:528`・`:543`・`:1081`・`:1115` … `price_set = {it["price_line"] for it in items}`
- `:1080`・`:1177` … `max(it["price_line"] ...)`
- `:1498` … `no_number = [it["price_line"] for it in items if _has_no_digit(it["quantity"])]`
- `backend/app/services/line_analysis_v102_svc.py:253` … `price_lines = {it["price_line"] for it in extracted if isinstance(it.get("price_line"), int)}`
- `backend/app/services/v102_gap_lines.py:132` … `price_lines = {it["price_line"] for it in sorted_items if isinstance(it.get("price_line"), int)}`
- `backend/app/services/gemini_raw_copy_v101.py:299-336` parse_v102_unsure … candidates は price_lines の集合に入っているかだけ見る（`:312`）。

### 件ごとに1つ使う所（一意かどうかは見ない）
- `gemini_raw_copy_v101.py:437`（役割）・`:496`（own_lines）・`:562-567`（単位の比較）・`:726-727`（名前の予備）・`:737-739`（単位）・`:828`・`:942`・`:981`・`:1391-1407`・`:1424-1431`（まとまりの中の最小）
- `gemini_raw_copy_v102_context_work.py:73-85`（距離で手がかりを選ぶ。同じ price_line の件は距離0で手がかりから外れる）
- `gemini_raw_copy_v102_product_first.py:653-655`・`:671`
- `line_analysis_v102_svc.py:264`・`:300`（`item.get("price_line") in u["candidates"]` → 同じ price_line の2件に同じ gemini_unsure が両方付く）・`:333`・`:641`（`_lines_agree`：`price_line in source`）
- `v102_gap_lines.py:80`・`:86`

### 件の対応付けは price_line を使わない
DB の行との対応は gemini_index（`line_analysis_v102_svc.py:654-666` `_items_by_position`）。price_line が同じでも対応付けは壊れない（コードから読める範囲）。

### v10 系（別経路）
`backend/app/services/gemini_raw_copy_v10.py:369` `owner_by_price_line = {it["price_line"]: it for it in items}`。v10 は自前の検査（`:85` `price_line が item_lines に無い`）で、parse_v101_response を通らない。v101 の経路から呼ばれるのは `v10._strip_price_line_name`（`:259`）だけ（`gemini_raw_copy_v101.py:680`）。

## (b) 価格 none の件の商品名・状態をどの行から読むか

役割の決め方:

`backend/app/services/gemini_raw_copy_v101.py:419-433`
```python
def line_role(text: str, ctx: V101Context, *, is_price_line: bool) -> str:
    """1行の役割。price → 在庫の言葉で始まる行（stock）→ ship → condition → stock → name の順に決める。"""
    if is_price_line:
        return ROLE_PRICE
    if _STOCK_START_RE.match(_nfkc(text).strip().lower()):
        return ROLE_STOCK
    if _SHIP_RE.search(_nfkc(text)):
        return ROLE_SHIP
    if _is_state_line(text, ctx):
        return ROLE_CONDITION
    if _is_stock_line(text, ctx):
        return ROLE_STOCK
    return ROLE_NAME


```

- price_line の行は ROLE_PRICE。それ以外は stock → ship → condition → stock → name の順。
- 〆の語が `ctx.sold_out_words` と行全体で一致すれば ROLE_STOCK（`:413`）。一致しない行（例: 〆に文が続く）は ROLE_NAME になりうる（未確認：本番の sold_out_words の中身）。

名前:

`backend/app/services/gemini_raw_copy_v101.py:722-727`
```python
) -> str:
    name = " ".join(_name_parts(item, roles, lines, owners, ctx))
    if name:
        return name
    unfiltered = _price_line_name(lines[item["price_line"] - 1], item, ctx, filtered=False)
    return unfiltered or lines[item["price_line"] - 1].strip()
```

- 名前は lines の各行を順に見る（`:700-717` 上記）。ROLE_PRICE の行は `_price_line_name`（`:668-686`）で価格・数量・完売の語・状態の語を除いた残りだけ使う。ROLE_NAME の行は丸ごと使う。
- 〆の行が price_line なら、そこから出る名前は空になり、品名の行（ROLE_NAME）が名前になる。既存の試験が同じ形：`backend/tests/test_gemini_raw_copy_v101.py:331-335`（`◆スカーレットex` / `完売` → 名前は `◆スカーレットex`、status は sold_out）。

状態・ステータス:

`backend/app/services/gemini_raw_copy_v101.py:925-926`
```python
    block = "\n".join(lines[n - 1] for n in item["lines"])
    own_text = "\n".join(lines[n - 1] for n in _own_lines(item, shared))
```

`backend/app/services/gemini_raw_copy_v101.py:945-948`
```python
        condition, _cond_id, basis = resolve_condition_v2(
            block, "", kubun, ctx.cond_entries, ctx.cond_canonical_to_uuid, raw_memo=block
        )
    status, effect = resolve_status_v2(block, ctx.status_entries, raw_memo=block)
```

- 状態（condition）・ステータスは `block`＝その件の lines の全行をつないだ文字から読む（役割に関係なく〆の行も入る）。単位は `_find_unit`（`:735-749`）が price_line → 在庫の行の順。

## (c) 案A・案Bでどこが壊れるか

前提: 品名の行が n1・n2、〆の行が m。件1 lines=[n1,m]、件2 lines=[n2,m]。

### 案A（二つの件で price_line=m を共有）
壊れる所（辞書の後勝ち）:
1. `gemini_raw_copy_v101.py:602`（`by_price_line`）→ `:607`・`:615`。迷う行が〆の直後にあると、前後の件が件2だけに解決され、件1に付くはずの行が件2に寄る。
2. `gemini_raw_copy_v101.py:1212`（F2 の `by_price_line`）→ `:1216`。〆の直後の件の名前が空のとき、前の件として件2だけが選ばれる。
3. `gemini_raw_copy_v101.py:1474`（`owners`）→ `:706-708`。〆の行の ROLE_PRICE の名前取りで、件1の〆の行が件2の price・quantity で除かれる（none どうしなら結果は同じ。price が違う件が混ざると違う：未確認）。
4. `gemini_raw_copy_v101.py:1571`（`owners`、v102 でない経路）→ 同上。
直す対象（壊れるのではなく変える所）: `:251`・`:266-271` の重複判定。`backend/tests/test_gemini_raw_copy_v101.py:837`・`:870` は価格ありの重複を期待しているので、価格 none だけ除外する形にすれば残る。
壊れない: 名前（品名の行が ROLE_NAME）・状態（block に〆が入る）・gemini_index での対応付け・集合で使う所。

### 案B（件2の price_line=n2、lines=[n2,m]）
辞書の衝突は無くなるが、次が変わる:
1. `:419-421` 品名の行 n2 が ROLE_PRICE になり、名前が `_price_line_name`（`:668-686`）の絞り込みを通る。名前に状態の語・発送の語・「残り」「在庫」の語・数量の形が入っていると削られる（`_is_dropped_word` `:658-665`）。
2. `:496` `_own_lines`：〆の行 m は件1・件2の両方が持つ共有行で、件2の price_line ではないので件2の own から外れる。`:926` の `own_text`、`:737` `_find_unit`、`:828` `_ship_for` が件1と件2で非対称になる。
3. `:413-415`＋`:419-433`：件2では m が price_line でないので、行全体が sold_out_words と一致しないと ROLE_NAME になり、`:709-710` で名前に混ざる。
4. `:1212-1216`：件1の price_line=m の直前の行 n2 が件2の price_line になるので、件1の名前が空のとき件2の名前を前に付ける（F2 が誤って働く）。
5. 価格 none の件の price_line を決める `:187-210` に「2件目は自分の品名の行」という規則を足す必要があり、1件目との順序（gemini_index）で決まる。
加えて、unsure の candidates（`gemini_raw_copy_v101.py:312`）が価格の行でなく品名の行を価格の行として許すことになる（意味が変わる）。

件数: 案A 4（＋重複判定の変更1）、案B 5。

## (d) 価格 none の件・〆の件の既存の試験
1. `backend/tests/test_gemini_raw_copy_v101.py:87` price none ＋ 数量の語の行
2. `backend/tests/test_gemini_raw_copy_v101.py:93` price none ＋ 売り切れの語の行
3. `backend/tests/test_gemini_raw_copy_v101.py:99` price none ＋ 手がかり無し→最後の行
4. `backend/tests/test_gemini_raw_copy_v101.py:331` 完売のみの件が見出しの名前を取る
5. `backend/tests/test_gemini_raw_copy_v101.py:837` 重複は `duplicate_price_line` で残る（keep_rejected）
6. `backend/tests/test_gemini_raw_copy_v101.py:870` 同じ件の review の kind
7. `backend/tests/test_v102_gap_lines.py:70` rejected="duplicate_price_line" の件
8. `backend/tests/test_review_reason_codes_consistency.py:41` REJECTED_DUPLICATE の理由コード
9. `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py:95-169` 〆の件の商品決め（status_entries の〆は `:32`、sold_out_words は `:36`）

価格 none の件2つが同じ〆の行を共有する形の試験は、grep では見つからなかった（網羅の確認は未確認）。

## 未確認
- 本番の sold_out_words・status_entries に〆以外の語（〆に文が続く形）がどう入っているか。
- 実際の「Fb-09／Fb-10／〆」の原文の行の並びと Gemini の実出力（読んでいない）。
- v10 経路が現在も呼ばれているか。
