# 調査 raw: 〆が直前の1品名だけに掛かり、品名だけの行1が拾われなかった件

- 基準: origin/main = a3e93f053208db71c281e3ff4a0cdaec5d9547bb
- 下の各コード片は origin/main の該当行を、行番号つきでそのまま写したもの（要約なし）。形は「行番号: 本文」。
- 推測は書かない。分からないことは「未確認」。

## (a) 投稿を行の塊（extraction item）に切る処理／品名だけで値段の無い行の扱い

事実の置き場: 塊（件）を作るのは Gemini（プロンプト backend/app/prompts/raw_copy_v101_e.txt）で、コードは返った件を検査するだけ。コード側に「品名だけの行を件にする」処理は、下に写した範囲では見当たらない（未確認: 全ファイルの網羅検索はしていない）。

#### origin/main:backend/app/prompts/raw_copy_v101_e.txt:5-14
```
5: 価格が書かれた行ごとに1件とし、その件に関係する行の番号と、価格・数量の文字だけを書き出す。
6: 商品名・状態・発送日がどれかは決めない。システムが、書き出した行番号の行から読み取る。
7: いちばん大切なのは、その件の行を、多すぎず少なすぎず書くことである。
8: 
9: # 1. 価格の行を見つけて、件を作る
10: - 価格が書かれた行ごとに1件を作る。
11: - 同じ商品の下に価格の行が複数ある場合（状態違い・梱包違いなど）は、それぞれ別の1件にする。
12: - 価格が無く「完売」「残りN」などだけが書かれた商品も1件にする。
13: - 1つの行に価格が2つある場合（セット価格と1個の価格など）は、1件にする。
14: - 名前と価格が同じ行にあるときは、次の行が名前の無い価格の行でも、その行はそれ自体で1件である。
```

#### origin/main:backend/app/prompts/raw_copy_v101_e.txt:93-105
```
93: # 6. 価格と数量の文字を写す
94: - price：その件の価格の文字を、そのまま写す。無ければ none。1つの行に価格が2つあれば、両方を原文のまま「／」でつなぐ。
95: - quantity：その件の数量の文字を、そのまま写す（「残り」「在庫」などの言葉が付いていればそのまま）。原文に数量が無ければ none。「1」などを推測で入れない。
96: 例:
97: [L0091] BEYOND THE PEAK
98: [L0093] カートン　@160,000円
99: [L0095] ◆スカーレットex
100: [L0097] 完売
101: [L0099] パック@150円
102: 出力例（3件。1件目は数量が書かれていないので none。「完売」だけの行はパックの件に入れない）:
103: {"lines":[91,93],"price":"160,000円","quantity":"none"}
104: {"lines":[95,97],"price":"none","quantity":"none"}
105: {"lines":[95,99],"price":"150円","quantity":"none"}
```

#### origin/main:backend/app/services/gemini_raw_copy_v101.py:87-100
```
87: _LINE_ARRAY = {"type": "array", "items": {"type": "integer"}}
88: V101_RESPONSE_SCHEMA: dict[str, Any] = {
89:     "type": "object",
90:     "properties": {
91:         "items": {
92:             "type": "array",
93:             "items": {
94:                 "type": "object",
95:                 "properties": {"lines": _LINE_ARRAY, "price": {"type": "string"}, "quantity": {"type": "string"}},
96:                 "required": ["lines", "price", "quantity"],
97:             },
98:         }
99:     },
100:     "required": ["items"],
```

#### origin/main:backend/app/services/gemini_raw_copy_v101.py:189-210
```
189: def _unpriced_line(numbers: list[int], lines: list[str], quantity: str, status_entries: list[dict] | None) -> int:
190:     """価格が none の件：数量の文字か売り切れの言葉を含む最初の行。無ければ lines の最後の行。"""
191:     for n in numbers:
192:         text = lines[n - 1]
193:         has_quantity = quantity != _NONE and bool(_squash(quantity)) and _squash(quantity) in _squash(text)
194:         if has_quantity or _is_sold_out(text, status_entries):
195:             return n
196:     return numbers[-1]
197: 
198: 
199: def _is_sold_out(text: str, status_entries: list[dict] | None) -> bool:
200:     return bool(status_entries) and resolve_status_v2(text, status_entries)[1] == "excluded"
201: 
202: 
203: def _price_line(
204:     obj: dict, numbers: list[int], lines: list[str], status_entries: list[dict] | None, *, half_width_slash: bool = False,
205:     yen_free: bool = False,
206: ) -> tuple[int | None, bool]:
207:     """(価格の行, 円を除いた探し直しで見つけたか)。"""
208:     if obj["price"].strip().lower() != _NONE:
209:         return _priced_line(numbers, lines, obj["price"], half_width_slash=half_width_slash, yen_free=yen_free)
210:     return _unpriced_line(numbers, lines, obj["quantity"].strip(), status_entries), False
```

#### origin/main:backend/app/services/gemini_raw_copy_v101.py:231-278
```
231: def parse_v101_response(
232:     response_text: str, raw_text: str, *, status_entries: list[dict] | None = None, keep_rejected: bool = False,
233: ) -> tuple[list[dict], list[dict]]:
234:     """JSON を読み、件ごとに設計 §3-3 の検査をする。戻り値は (items, errors)。
235: 
236:     items のキーは lines（重複なし・昇順）, price, quantity, price_line。
237:     status_entries は価格が none の件の price_line（売り切れの言葉の行）を決めるのに使う（無ければ使わない）。
238:     keep_rejected（試作版 v102）が True のときだけ、落とす件（形の違反・価格の行なし・価格の行が重複）を捨てずに、
239:     rejected・gemini_index などを付けて items の後ろに足し、半角「/」でつないだ価格も最初の価格で探す。
240:     このとき受理した件にも gemini_index（応答の中の位置）を付ける（件の対応付け用。便G）。
241:     円・¥ を除いた探し直しで価格の行を見つけた件だけ price_basis も付ける。False のときの出力は変えない。
242:     """
243:     lines = raw_text.split("\n")
244:     objs, whole_errors = v8._load_items(response_text)
245:     if objs is None:
246:         return [], whole_errors
247: 
248:     items: list[dict] = []
249:     rejected: list[dict] = []
250:     errors: list[dict] = []
251:     seen_price_lines: set[int] = set()
252:     for index, obj in enumerate(objs):
253:         reason = _shape_error(obj, len(lines))
254:         if reason is not None:
255:             errors.append({"index": index, "error": reason, "item": obj})
256:             rejected.append(_rejected_entry(REJECTED_SHAPE, index, obj, reason, len(lines)))
257:             continue
258:         numbers = sorted(set(obj["lines"]))
259:         price_line, via_yen_free = _price_line(
260:             obj, numbers, lines, status_entries, half_width_slash=keep_rejected, yen_free=keep_rejected,
261:         )
262:         if price_line is None:
263:             errors.append({"index": index, "error": "価格の行が見つからない", "item": obj})
264:             rejected.append(_rejected_entry(REJECTED_PRICE, index, obj, "価格の行が見つからない", len(lines)))
265:             continue
266:         if price_line in seen_price_lines:
267:             message = f"price_line {price_line} がほかの件と同じ"
268:             errors.append({"index": index, "error": message, "item": obj})
269:             rejected.append(_rejected_entry(REJECTED_DUPLICATE, index, obj, message, len(lines), price_line))
270:             continue
271:         seen_price_lines.add(price_line)
272:         accepted = {"lines": numbers, "price": obj["price"], "quantity": obj["quantity"], "price_line": price_line}
273:         if keep_rejected:
274:             accepted = {**accepted, "gemini_index": index}
275:             if via_yen_free:
276:                 accepted = {**accepted, "price_basis": PRICE_BASIS_YEN_FREE}
277:         items.append(accepted)
278:     return ([*items, *rejected] if keep_rejected else items), errors
```

#### origin/main:backend/app/services/gemini_raw_copy_v101.py:1072-1082
```
1072: def _possible_missing_lines(items: list[dict], lines: list[str], *, until_last_price_line: bool = False) -> list[int]:
1073:     """最初の件の最初の行から最後の件の最後の行までの間にある、price_line でない価格の形の行。
1074: 
1075:     until_last_price_line（v10.2 F5）のときは、終わりを最後の price_line にする（末尾の連絡の行を含めない）。
1076:     """
1077:     if not items:
1078:         return []
1079:     first = min(n for it in items for n in it["lines"])
1080:     last = max(it["price_line"] for it in items) if until_last_price_line else max(n for it in items for n in it["lines"])
1081:     price_set = {it["price_line"] for it in items}
1082:     return [n for n in range(first, last + 1) if n not in price_set and _is_price_shaped(lines[n - 1])]
```

#### origin/main:backend/app/services/v102_gap_lines.py:1-8
```
1: """v102 の「間の行」の検知（段1：記録だけ）。純粋な関数だけ。DB も Gemini も呼ばない。
2: 
3: 設計: docs/handoff/v102-gap-detect-record/design.md §3 PR②。
4: - 分類  : 受理された件のどれにも使われていない空でない行を gap / pre / span / trail に分ける。
5: - T1    : gap の行のうち、価格と数量の形がある行（取りこぼしの疑い）。
6: - T2/H2 : gap・pre の行を支えにして、商品が決まっていない件（unmatched）の候補を作る。
7: 記録するのは行番号と商品 id だけで、原文は入れない（docs/handoff/v102-no-silent-drop/design.md:31）。
8: """
```

#### origin/main:backend/app/services/v102_gap_lines.py:90-119
```
90: def classify_lines(sorted_items: Sequence[Mapping], lines: Sequence[str]) -> dict[int, tuple[str, int | None]]:
91:     """空でない行（1 始まりの行番号）→ (分類, 直後の件の位置)。sorted_items は accepted_items の結果。
92: 
93:     直後の件の位置は、sorted_items の中でその行より後に最初の行がある最初の件（trail と used は None）。
94:     gap は「それより前の件が使った最後の行」より後の行。前の件の最終行は累積最大を先に作って引く（行数に比例）。
95:     """
96:     used: set[int] = set()
97:     reach_before: list[int] = []  # reach_before[k] = 件 0..k-1 が使った最後の行（k=0 は 0）
98:     running_max = 0
99:     for it in sorted_items:
100:         reach_before.append(running_max)
101:         rows = _item_rows(it)
102:         used |= rows
103:         running_max = max(running_max, max(rows))
104:     firsts = [_first_line(it) for it in sorted_items]  # 昇順（accepted_items の並び）
105:     classes: dict[int, tuple[str, int | None]] = {}
106:     for number, text in enumerate(lines, start=1):
107:         if not text.strip():
108:             continue
109:         if number in used:
110:             classes[number] = (CLASS_USED, None)
111:             continue
112:         k = bisect_right(firsts, number)  # 最初の行が number より後の最初の件
113:         if k == len(firsts):
114:             classes[number] = (CLASS_TRAIL, None)
115:         elif k == 0:
116:             classes[number] = (CLASS_PRE, 0)
117:         else:
118:             classes[number] = (CLASS_GAP, k) if number > reach_before[k] else (CLASS_SPAN, k)
119:     return classes
```

## (b) 〆・完売の行がどの品名の行に掛かるか決める処理

#### origin/main:backend/app/prompts/raw_copy_v101_e.txt:25-28
```
25: # 2. 件の商品名の行を足す
26: - その件の商品名の行（見出し）を lines に足す。名前が2行に分かれていれば、続きの行も足す。
27: - 同じ見出しの下に価格の行が複数あるときは、その見出しを全部の件に足す。
28: - 名前の無い価格の行（例「カートン 250,000円」）の件には、その商品の名前が書かれた前の件の行を足す。
```

#### origin/main:backend/app/services/gemini_raw_copy_v101.py:419-439
```
419: def line_role(text: str, ctx: V101Context, *, is_price_line: bool) -> str:
420:     """1行の役割。price → 在庫の言葉で始まる行（stock）→ ship → condition → stock → name の順に決める。"""
421:     if is_price_line:
422:         return ROLE_PRICE
423:     if _STOCK_START_RE.match(_nfkc(text).strip().lower()):
424:         return ROLE_STOCK
425:     if _SHIP_RE.search(_nfkc(text)):
426:         return ROLE_SHIP
427:     if _is_state_line(text, ctx):
428:         return ROLE_CONDITION
429:     if _is_stock_line(text, ctx):
430:         return ROLE_STOCK
431:     return ROLE_NAME
432: 
433: 
434: def assign_roles(items: list[dict], lines: list[str], ctx: V101Context) -> list[dict[int, str]]:
435:     """件ごとに、lines の各行の役割（行番号→役割）を返す。items と同じ順。"""
436:     return [
437:         {n: line_role(lines[n - 1], ctx, is_price_line=(n == item["price_line"])) for n in item["lines"]}
438:         for item in items
439:     ]
```

#### origin/main:backend/app/services/gemini_raw_copy_v101.py:1464-1479
```
1464:     rejected_rows = [_rejected_row(r, ctx) for r in rejected or []]
1465:     if not items:
1466:         empty: dict = {"possible_missing_item": [], "quantity_no_number": [], "possible_footer_line": []}
1467:         if review_reasons:
1468:             empty["post_review"] = _post_review_reasons(item_count=len(rejected_rows), flags=empty, owned_lines=set())
1469:         return rejected_rows, empty
1470:     items, f1_fixes = ((items, {}) if gemini_trust else _apply_f1(items, assign_roles(items, lines, ctx), lines, ctx))
1471:     roles = assign_roles(items, lines, ctx)
1472:     roles, f3_fixes = _apply_f3(items, roles, lines, ctx)
1473:     name_roles, f5_fixes, footer_lines = _apply_f5(items, roles, lines, ctx)
1474:     owners = {it["price_line"]: it for it in items}
1475:     shared = _shared_line_numbers(items)
1476:     f2 = _f2_prefixes(items, name_roles, lines, owners, shared, ctx)
1477: 
1478:     status_context = _status_context(ctx, items, rejected or [])
1479: 
```

#### origin/main:backend/app/services/gemini_raw_copy_v101.py:1497-1512
```
1497:     extracted = [build(i) for i in range(len(items))]
1498:     no_number = [it["price_line"] for it in items if _has_no_digit(it["quantity"])]
1499:     if ctx.product_first is not None:
1500:         extracted = _apply_context_work(extracted, build, ctx.product_first.product_entries)
1501:         if followup_ref is not None:
1502:             extracted = _apply_followup(
1503:                 extracted, build, lines, ctx.product_first, followup_ref, ctx.unit_alias_to_info, fixed_products
1504:             )
1505:         if soldout_posts:
1506:             extracted = _apply_soldout_ref(
1507:                 extracted, build, lines, ctx.product_first, soldout_posts, ctx.unit_alias_to_info, ctx.sold_out_words,
1508:                 fixed_products,
1509:             )
1510:             extracted = _apply_soldout_inherit(
1511:                 extracted, soldout_posts, fixed_products, ctx.product_first.shime_box_all_states, "\n".join(lines),
1512:             )
```

#### origin/main:backend/app/services/line_analysis_v102_svc.py:1127-1160
```
1127: def _sell_out_stock_closed_in_the_same_post(
1128:     pairs: list, base_values: list[dict], decisions: dict[str, Decisions], unit_ids: dict, status_entries: list[dict],
1129: ) -> list[dict]:
1130:     """規則13（docs/handoff/v102-shime-same-post-stock/design.md §3）：同じ投稿の〆が範囲に含む、同じ商品・状態の在庫の件を Sold out にする。
1131: 
1132:     〆は自分の価格・数量が無く、引き継ぎ先も無いものだけ。人が判断した件は〆にも在庫にも使わない。元の base_values は変えない。
1133:     """
1134:     closers = [
1135:         (values["product_id"], values["condition_id"], getattr(row, "line_start", None), getattr(row, "line_end", None))
1136:         for values, (item, row) in zip(base_values, pairs)
1137:         if values["status"] == STATUS_SOLD_OUT and values["exclusion"] == "excluded"
1138:         and not _has_raw_value(getattr(row, "raw_price", None)) and not _has_raw_value(getattr(row, "raw_quantity", None))
1139:         and not item.get("soldout_targets")
1140:         and not _has_human_judgement(decisions.get(str(row.id)))
1141:         and None not in (values["product_id"], values["condition_id"], getattr(row, "line_start", None), getattr(row, "line_end", None))
1142:     ]
1143:     if not closers:
1144:         return base_values
1145:     out = []
1146:     for values, (_item, row) in zip(base_values, pairs):
1147:         decision = decisions.get(str(row.id))
1148:         start_line, end_line = getattr(row, "line_start", None), getattr(row, "line_end", None)
1149:         closed = (
1150:             values["status"] != STATUS_SOLD_OUT and values["exclusion"] is None
1151:             and (decision is None or decision.values.status is None)
1152:             and not _has_human_judgement(decision)
1153:             and start_line is not None and end_line is not None
1154:             and any(
1155:                 pid == values["product_id"] and cid == values["condition_id"] and start <= start_line and end_line <= end
1156:                 for pid, cid, start, end in closers
1157:             )
1158:         )
1159:         out.append(apply_value_overrides(values, ValueOverrides(status=STATUS_SOLD_OUT), unit_ids, status_entries) if closed else values)
1160:     return out
```

#### origin/main:backend/app/services/gemini_raw_copy_v102_soldout_ref.py:155-160
```
155: def soldout_targets(extracted: Sequence[Mapping[str, Any]]) -> list[int]:
156:     """規則1：〆で商品が決まっていない件の添字（落とした件は除く）。"""
157:     return [
158:         i for i, row in enumerate(extracted)
159:         if row.get("status_effect") == _EXCLUDED and row.get("match_status") in _UNDECIDED_STATUSES and not row.get("rejected")
160:     ]
```

#### origin/main:backend/app/services/gemini_raw_copy_v102_soldout_ref.py:298-328
```
298: def _decide_one(
299:     row: Mapping[str, Any], lines: Sequence[str], rows: Sequence[RefRow], sold: frozenset[int], rules: _Rules,
300: ) -> SoldoutRefDecision | None:
301:     text = "\n".join(lines[n - 1] for n in row.get("lines", []) if 1 <= n <= len(lines))
302:     is_plural = _has_any(text, rules.plural_words)  # 規則8：複数を指す言葉
303:     found = _matched_works(text, rules.works) if is_plural else {}
304:     if len(found) >= 2:
305:         return None  # 規則9：含まれる中分類が2つ以上
306:     work_id, work_names = next(iter(found.items()), (None, ()))
307:     codes, names = _clue_tokens(text, rules, work_names)
308:     if work_id is None and not codes and not names:
309:         return None  # 規則5・9：作品名の〆でなく、残った語が0
310:     hits = _hit_rows(rows, codes, names, work_id, rules)
311:     stock = [r for r in hits if not r.is_sold and r.order not in sold]
312:     products = {r.product_id for r in stock}
313:     if not products or (not is_plural and len(products) != 1):
314:         return None  # 規則10：0（すでに〆）、複数語なしで2つ以上
315:     post = rules.posts[hits[0].post_index] if hits[0].post_index < len(rules.posts) else None
316:     if is_plural and work_id is None and _has_unresolved_clue_line(
317:         post, frozenset(r.line_no for r in rows if r.post_index == hits[0].post_index), codes, names, rules.sold_out_words,
318:     ):
319:         return None  # 規則10：語が当たるのに商品が決まらない行がある
320:     if row.get("match_status") == "ambiguous" and not products <= set(row.get("match_candidates") or []):
321:         return None  # 規則7・10：候補に無い商品が混ざる
322:     targets = _targets_of(stock, post)
323:     if targets is None and is_plural:
324:         return None  # 規則11：複数語で、相手が見つからない在庫の行がある
325:     narrowed = _narrow_by_condition(targets or (), row, is_plural)
326:     if narrowed is None:
327:         return None  # 規則11b：複数語で、〆の件の状態と同じ相手が無い
328:     return _decision(stock, narrowed, (*codes, *names))
```

## (c) 設計書で、まとめて閉じる形について書かれた所

注: 2つの design.md に「〆が直前の1品名だけに掛かる」「品名だけの行は件にしない」と直接書いた行は、grep（直前・1行・複数の・まとめて 等）で見つからなかった（未確認を含む）。下はまとめて閉じる形を書いた所。

#### origin/main:docs/handoff/shime-review-exclude/design.md:9-10
```
9: > この文書は何か: 相手の在庫が既に在庫表から消えている「価格のない〆・完売」の行を、要確認一覧から外す設計書。取り違えが疑われる行は残す。
10: > 親: docs/handoff/v102-shime-same-post-stock/design.md（規則13。〆を在庫の件に効かせる側）
```

#### origin/main:docs/handoff/shime-review-exclude/design.md:52-62
```
52: 価格のない〆・完売の行は、次をすべて満たすとき「確認済み扱い」とし、理由 price_unresolved と excluded を付けない。
53: 
54: | # | 条件 | SQL での形 |
55: |---|---|---|
56: | 形 | status が sold out、exclusion が excluded、価格と数量が NULL、商品と状態が決まっている | `lower(btrim(COALESCE(status,''))) IN ('sold out','soldout')`・`exclusion = 'excluded'`・`price_normalized IS NULL`・`quantity_normalized IS NULL`・`product_id`・`condition_id` が NULL でない |
57: | ① | 状態が FLAG でない | condition_canonical・condition_basis に FLAG を含まない |
58: | ② | 同じ仕入れ窓口に、同じ商品・同じ状態の過去の在庫がある | 別の行で、同じ sm.supplier_channel_id・同じ product_id・同じ condition_id・価格あり・売り切れでない・投稿が自分以前 |
59: | ③ | その商品の在庫が在庫表に今は残っていない（近似） | 同じ窓口・同じ product_id の別の行で、is_current・pid/unit 解決・excluded でない・価格あり・投稿が 48 時間以内・condition_canonical が FLAG_ でない・売り切れでない、が1行も無い |
60: | ④ | 人の修正が無い | その行の item_corrections が1件も無い（cr_latest.id IS NULL） |
61: 
62: 適用範囲: 新しい規則は prompt_version を見ないので、v102 以外（旧エンジン）の〆の形の行にも効く。意図した範囲（人の修正が無く相手の在庫が消えた〆は、どちらのエンジンでも確認が要らない）。直近7日の画面の範囲では v102 以外の該当は 0 行（再審査 a1.out）なので KGI には影響しない。
```

#### origin/main:docs/handoff/shime-box-all-states/design.md:1-1
```
1: # design: 状態を書かない箱の〆は、箱の仲間の状態をまとめて完売にする（規則12h）
```

#### origin/main:docs/handoff/shime-box-all-states/design.md:25-36
```
25: - 変更前（recon §2-1）: 候補の〆で、〆と同じ状態の在庫が前の投稿にあると 12d で何もしない（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:427-428`。便1 の後の main では `:462-467`）。
26: - 変更後: 12d で何もしない所の手前に 12h を足す。次の全部を満たすときだけ、〆の状態と、取り残された箱の仲間の状態を全部、完売の相手にする。
27:   1. 設定 `v102_shime_box_all_states` が読めている（無い・形が違うときは今と同じ）。
28:   2. 〆の件の状態が箱の仲間（状態マスタ `value_group='box'`）。
29:   3. 〆の状態が語で決まっていない（今の候補の条件のまま。語で決まった〆は候補に来ない）。
30:   4. 〆の状態の在庫が前の投稿にある（12d に来た形）。
31:   5. 取り残し（`_stranded_stock`）のうち〆の状態以外が 1 つ以上あり、その全部が箱の仲間。カートン・パック等が 1 つでも混ざれば今と同じ（何もしない）。
32:   6. 今の投稿の原文に、設定の `keep_words` のどれも含まれない（NFKC にして部分一致）。
33:   7. 〆の件に値段も数も無い（`price_normalized` と `quantity_normalized` がどちらも None）。どちらかがあれば今と同じ（12d で何もしない）。値段や数を書いた〆は「その行の品が売り切れた」意味で、商品の全部の状態の売り切れではないため（便3 の判定。§3-2）。
34: - 相手の並び: 先頭に〆の状態（最も新しい在庫の投稿の行）、続けて残りを `value_rank` の小さい順。先頭が〆の状態なので、〆の件の状態は変わらない（`backend/app/services/line_analysis_v102_svc.py:941-964` が先頭で上書きするため）。2 つ目以降は既にある表 `analysis_soldout_extra_targets` に入り、在庫表の今の行から外れる（recon §2-2）。
35: - 印は今の 12 と同じ `SOLDOUT_INHERIT`。
36: - 語と箱の仲間をコードに書かない: 語は設定、箱の仲間は状態マスタの `value_group` から読む（ADR-1041 の前例）。
```

## (d) 同じ形を扱う試験（git grep）

注: 「品名だけの行が複数＋〆だけの行」（Fb-09 / Fb-10 / 〆 の形）をそのまま扱う試験は、git grep（Fb-0・Fb-1・〆の直前・まとめて閉）で見つからなかった。近い形を扱う試験を写す。

#### origin/main:backend/tests/test_gemini_raw_copy_v101.py:87-102
```
87: def test_price_none_uses_first_line_with_quantity_text():
88:     raw = "商品A\n在庫 残り3"
89:     items, _ = _parse(raw, _it([1, 2], "none", "残り3"))
90:     assert items[0]["price_line"] == 2
91: 
92: 
93: def test_price_none_uses_sold_out_word_line_when_quantity_is_none():
94:     raw = "◆スカーレット\n完売\nメモ"
95:     items, _ = _parse(raw, _it([1, 2, 3], "none", "none"))
96:     assert items[0]["price_line"] == 2
97: 
98: 
99: def test_price_none_without_clue_uses_last_line():
100:     raw = "商品A\nメモ1\nメモ2"
101:     items, _ = _parse(raw, _it([1, 2, 3], "none", "none"))
102:     assert items[0]["price_line"] == 3
```

#### origin/main:backend/tests/test_gemini_raw_copy_v101.py:331-335
```
331: def test_sold_out_only_item_takes_the_heading_name_without_the_sold_out_word():
332:     raw = "◆スカーレットex\n完売\nパック@150円"
333:     r, _ = _extract(raw, _it([1, 2], "none", "none"), _it([1, 3], "150円", "none"))
334:     assert r[0]["name"] == "◆スカーレットex" and (r[0]["status"], r[0]["status_effect"]) == ("sold_out", "excluded")
335:     assert r[1]["status"] == "active" and r[1]["unit"] == "パック"
```

#### origin/main:backend/tests/test_v102_gap_lines.py:145-152
```
145: def test_t2_skips_items_without_price_or_quantity():
146:     lines = ["BASESHOP", "matA", "完売", "BASESHOP", "matA", "3,000円"]
147:     items = [
148:         item(0, [2, 3], 3, price=None, quantity="2"),
149:         item(1, [5, 6], 6, price="3,000円", quantity="none"),
150:     ]
151: 
152:     assert gap_name_candidates(accepted_items(items), lines, masters(entry(1001, "BASESHOP matA"))) == []
```

#### origin/main:backend/tests/test_gemini_raw_copy_v102_soldout_ref.py:158-176
```
158: def test_sold_out_cancels_per_product_not_per_post():
159:     post = _post("p1", "ふぁいぶ ABC-123 3@1,500円\nぴよぴよ ABC-123 3@1,500円\nふぁいぶ 〆")
160:     assert _extract("ABC-123 〆", (post,))[0]["product_id"] == 63  # 62 はすでに〆、残るのは 63 だけ
161: 
162: 
163: def test_two_products_hit_does_not_decide():
164:     row = _extract("ABC-123 〆", (_post("p1", "ふぁいぶ ABC-123 3@1,500円\nぴよぴよ ABC-123 3@1,500円"),))[0]
165:     assert row["match_status"] == "unmatched" and row["product_id"] is None
166: 
167: 
168: def test_all_tokens_must_hit_one_reference_row():
169:     row = _extract("ABC-123 DEF-456 〆", (_post("p1", STOCK),))[0]  # 2語は別々の行に当たる
170:     assert row["match_status"] == "unmatched" and row["product_id"] is None
171: 
172: 
173: def test_no_token_does_not_decide():
174:     for raw in ("〆", "BOX 〆"):  # 語が残らない／単位の語だけ
175:         row = _extract(raw, (_post("p1", "ふぁいぶ BOX 3@1,500円"),))[0]
176:         assert row["match_status"] == "unmatched" and row["product_id"] is None
```

#### origin/main:backend/tests/test_gemini_raw_copy_v102_soldout_ref.py:268-299
```
268: def test_work_name_soldout_decides_every_product_of_that_work():
269:     row = _extract("ドラゴンアイル 全て〆", (_post("p1", _WORK_POST_RAW, stock_items=_WORK_STOCK),), _PLURAL, master=_MASTER_W)[0]
270:     assert (row["match_status"], row["product_id"]) == ("matched_soldout_ref", 81)
271:     assert _targets(row) == [(81, _COND_A, "p1", 1), (82, _COND_B, "p1", 2)]  # 中分類 3 の 91 は入らない
272:     assert row["product_soldout_ref"]["tokens"] == []  # 作品名の語は手がかりから外れる
273: 
274: 
275: def test_work_name_is_not_used_without_a_plural_word():
276:     row = _extract("ドラゴンアイル 〆", (_post("p1", _WORK_POST_RAW, stock_items=_WORK_STOCK),), _PLURAL, master=_MASTER_W)[0]
277:     assert row["match_status"] == "unmatched" and row["product_id"] is None
278: 
279: 
280: def test_work_name_soldout_with_two_work_names_does_not_decide():
281:     row = _extract("ドラゴンアイル ポケモンアイル 全て〆", (_post("p1", _WORK_POST_RAW, stock_items=_WORK_STOCK),), _PLURAL, master=_MASTER_W)[0]
282:     assert row["match_status"] == "unmatched" and row["product_id"] is None
283: 
284: 
285: def test_work_name_soldout_requires_the_remaining_tokens_to_hit_too():
286:     raw = "どらごん甲 ZZZ-111 3@1,500円\nどらごん乙 3@1,500円"
287:     row = _extract("ドラゴンアイル ZZZ-111 全て〆", (_post("p1", raw, stock_items=(_si([1], 81), _si([2], 82))),), _PLURAL, master=_MASTER_W)[0]
288:     assert _targets(row) == [(81, _COND_A, "p1", 1)]
289: 
290: 
291: def test_work_name_soldout_ignores_a_clue_line_without_product():
292:     raw = "どらごん甲 3@1,500円\nなぞの行 3@1,500円"
293:     row = _extract("ドラゴンアイル 全て〆", (_post("p1", raw, stock_items=(_si([1], 81),)),), _PLURAL, master=_MASTER_W)[0]
294:     assert (row["product_id"], _targets(row)) == (81, [(81, _COND_A, "p1", 1)])
295: 
296: 
297: def test_work_name_soldout_with_a_stock_row_without_counterpart_does_not_decide():
298:     row = _extract("ドラゴンアイル 全て〆", (_post("p1", _WORK_POST_RAW, stock_items=(_si([1], 81),)),), _PLURAL, master=_MASTER_W)[0]
299:     assert row["match_status"] == "unmatched" and row["product_id"] is None
```

## 行1が拾われなかった理由（事実。すべて上に写した行）

1. 件を作る規則は Gemini のプロンプトにあり、価格の行ごとに1件。価格が無い件は「完売」「残りN」などだけが書かれた商品に限る（`backend/app/prompts/raw_copy_v101_e.txt:10`・`:12`）。品名だけの行（価格も完売の語も無い）を件にする規則は、写した範囲に無い。
2. コードは Gemini が返した件だけを受理する（`backend/app/services/gemini_raw_copy_v101.py:252-277`）。価格が none の件の price_line は、数量の文字か売り切れの語を含む最初の行、無ければ lines の最後の行（同 `:189-196`）。
3. どの件にも使われない行は「記録だけ」の分類になる。最初の件より前の行は pre（`backend/app/services/v102_gap_lines.py:115-116`）。行1が pre になったかは未確認（Gemini の返した lines は見ていない）。
4. 〆を在庫の件に効かせる規則13は、〆の件の line_start〜line_end に収まる同じ商品・状態の件だけを Sold out にする（`backend/app/services/line_analysis_v102_svc.py:1155`）。件の無い行1の品名には掛からない。
5. 未確認: Gemini の実際の応答（行1を lines に含めたか）、本番の仕入元の書き方の設定、状態マスタに〆があるか。
