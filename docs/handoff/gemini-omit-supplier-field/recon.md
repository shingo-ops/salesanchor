# recon: 仕入元ルールの欄を外す切り替え

- 実測時の origin/main SHA: e4f976c22d2a60cd7adb1c3f9f01630ada21287a
- 引用は origin/main のコード（変更前）。社外秘の仕入元名・原文は書かない。

## 1. 変更対象（backend/app/tools/prompt_ab.py）

### backend/app/tools/prompt_ab.py:431-459
```
431: def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
432:     p = argparse.ArgumentParser(description="Gemini 書き写し v7/v8/v9/v10/v101/v102 の比較試験（結果は JSONL、DB は費用の台帳だけ）")
433:     p.add_argument("--runs-file", required=True, type=Path, help="対象の extraction_shadow_runs.id を1行1件で書いたファイル")
434:     p.add_argument("--config", required=True, choices=("v7", "v8", "v9", "v10", "v101", "v102"))
435:     p.add_argument("--prompt-name", help="--config v9・v101・v102 のみ。prompts/ の raw_copy_v9_<名前>.txt（v9）／raw_copy_v101_<名前>.txt（v101 は既定 raw_copy_v101_a、v102 は既定 raw_copy_v101_c）を指示書にする")
436:     p.add_argument("--thinking-level", type=str.lower, choices=_THINKING_LEVELS, help="v8・v9 のみ。未指定なら level を入れない")
437:     p.add_argument("--no-thoughts", action="store_true", help="v8・v9 のみ。考えた過程の要約を求めない")
438:     p.add_argument("--no-schema", action="store_true", help="v8・v9 のみ。JSON の型指定を付けない")
439:     p.add_argument("--temperature", type=float, default=None, help="v8・v9 のみ。未指定なら指定しない（既定 1.0）")
440:     p.add_argument("--repeat", type=int, required=True)
441:     p.add_argument("--max-cost-usd", type=Decimal, required=True, help="費用の累計の上限（USD）。超えたら止まる")
442:     p.add_argument("--test-id", required=True)
443:     p.add_argument("--out-dir", required=True, type=Path)
444:     p.add_argument("--dry-run", action="store_true", help="対象の件数と組み立てた指示の先頭30行だけ表示する（Gemini は呼ばない）")
445:     args = p.parse_args(argv)
446:     if args.thinking_level:
447:         args.thinking_level = args.thinking_level.upper()
448:     if args.config == "v7" and (
449:         args.thinking_level or args.no_thoughts or args.no_schema or args.temperature is not None
450:     ):
451:         p.error("--thinking-level / --no-thoughts / --no-schema / --temperature は --config v8・v9・v10・v101・v102 のときだけ使えます")
452:     if args.prompt_name is not None:
453:         try:
454:             resolve_prompt_path(args.prompt_name, args.config)
455:         except ValueError as exc:
456:             p.error(str(exc))
457:     if args.repeat < 1:
458:         p.error("--repeat は 1 以上")
459:     return args
```

### backend/app/tools/prompt_ab.py:368-386
```
368:                     ctx_loaded = load_extraction_context(session, job_id)
369:                     if ctx_loaded is None:
370:                         raise RuntimeError(f"job not found: {job_id}")
371:                     contexts[job_id] = ctx_loaded
372:                 ctx = contexts[job_id]
373:                 if config == "v7":
374:                     result = _call_v7(ctx)
375:                 else:
376:                     schemas = {
377:                         "v9": V9_RESPONSE_SCHEMA, "v10": V10_RESPONSE_SCHEMA,
378:                         "v101": V101_RESPONSE_SCHEMA, "v102": V101_RESPONSE_SCHEMA,
379:                     }
380:                     extra = {"response_schema": schemas[config]} if config in schemas else {}
381:                     result = call_gemini_raw_copy_v8(
382:                         ctx.raw_text, prompt_text=v8_prompt, supplier_context=ctx.supplier_context,
383:                         knowledge_links=ctx.knowledge_links, thinking_level=thinking_level,
384:                         include_thoughts=include_thoughts, use_schema=use_schema, temperature=temperature,
385:                         **extra,
386:                     )
```

### backend/app/tools/prompt_ab.py:317-320
```
317:         prompt = build_prompt_v8(
318:             ctx.raw_text, prompt_text=v8_prompt or "", supplier_context=ctx.supplier_context,
319:             knowledge_links=ctx.knowledge_links,
320:         )
```

### backend/app/tools/prompt_ab.py:397-403
```
397:             _append_jsonl(out_path, {
398:                 **row, "response_text": result["response_text"],
399:                 "thought_summaries": result["thought_summaries"], "usage_raw": result["usage_raw"],
400:                 "item_count": item_count, "errors": errors,
401:                 **_master_row_fields(config, result["response_text"], ctx, masters),
402:                 "elapsed_sec": round(time.monotonic() - started, 3),
403:             })
```

## 2. 仕入元ルールを指示書にする処理（変更しない）

### backend/app/services/gemini_raw_copy_v8.py:94-117
```
94: def build_supplier_note_v8(supplier_context: dict | None, knowledge_links: list[dict] | None) -> str:
95:     """v7 と同じ並び・文言の仕入元ルール。ただしデフォルト単位は入れない（設計 §1 ②）。
96: 
97:     既存の _build_supplier_context_note を（変更せずに）呼び、extraction_default_unit だけ
98:     除いた写しの辞書を渡す。knowledge_links は block_delimiter のみ、ship_format は末尾に足す（v7 と同じ）。
99:     """
100:     ctx = {k: v for k, v in (supplier_context or {}).items() if k != "extraction_default_unit"}
101:     filtered_links = [lnk for lnk in (knowledge_links or []) if lnk.get("category") == "block_delimiter"]
102:     note = _gem._build_supplier_context_note(ctx, knowledge_links=filtered_links)
103: 
104:     ship_format = ctx.get("extraction_ship_format")
105:     if ship_format:
106:         ship_line = f"- 発送日フォーマット: {ship_format}"
107:         note = f"{note}\n{ship_line}" if note else f"【仕入元固有の抽出ルール】\n{ship_line}"
108:     return note
109: 
110: 
111: def build_prompt_v8(
112:     raw_text: str, *, prompt_text: str, supplier_context: dict | None, knowledge_links: list[dict] | None
113: ) -> str:
114:     note = build_supplier_note_v8(supplier_context, knowledge_links)
115:     section = f"\n{note}\n" if note else ""
116:     prompt_input = format_prompt_input_v8(raw_text, keep_chars_from_links(knowledge_links))
117:     return f"{prompt_text}{section}\n原文:\n{prompt_input}"
```

### backend/app/services/gemini_raw_copy_v8.py:184-184
```
184:     full_prompt = build_prompt_v8(
```

## 3. 本番の取得処理（変更しない）

### backend/app/tasks/tcg_extraction.py:230-296
```
230:     return f"""
231:             SELECT ej.id, sm.raw_text,
232:                    s.extraction_price_format,
233:                    s.extraction_qty_format,
234:                    s.extraction_order_pattern,
235:                    s.extraction_default_unit,
236:                    s.extraction_notes,
237:                    s.extraction_state_format,
238:                    s.extraction_example_text,
239:                    s.extraction_ship_format,
240:                    sc.supplier_id
241:             FROM {TCG_SCHEMA}.extraction_jobs ej
242:             JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id
243:             LEFT JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
244:             LEFT JOIN public.suppliers s ON s.id = sc.supplier_id
245: """
246: 
247: 
248: class ExtractionContext(NamedTuple):
249:     """ジョブの原文・仕入元ルール・knowledge リンク・仕入元 ID。"""
250: 
251:     raw_text: str
252:     supplier_context: dict | None
253:     knowledge_links: list[dict] | None
254:     supplier_id: int | None
255: 
256: 
257: def _build_extraction_context(session: Session, row) -> ExtractionContext:
258:     """_context_select_sql() の1行から、原文・仕入元ルール・knowledge リンクを組み立てる。"""
259:     raw_text = row[1] or ""
260: 
261:     # 仕入元抽出ルールを取得して supplier_context を構築
262:     supplier_context: dict | None = None
263:     extraction_rules = {
264:         "extraction_price_format": row[2],
265:         "extraction_qty_format": row[3],
266:         "extraction_order_pattern": row[4],
267:         "extraction_default_unit": row[5],
268:         "extraction_notes": row[6],
269:         "extraction_state_format": row[7],
270:         "extraction_example_text": row[8],
271:         "extraction_ship_format": row[9],
272:     }
273:     if any(v for v in extraction_rules.values()):
274:         supplier_context = extraction_rules
275: 
276:     # Knowledge リンクを取得（supplier_id がある場合のみ）
277:     knowledge_links: list[dict] | None = None
278:     supplier_id = row[10]
279:     if supplier_id is not None:
280:         kl_rows = session.execute(
281:             text(
282:                 """
283:                 SELECT kr.category, kr.pattern, kr.normalized_to
284:                 FROM public.supplier_knowledge_links skl
285:                 JOIN public.knowledge_rules kr ON kr.id = skl.knowledge_rule_id
286:                 WHERE skl.supplier_id = :sid AND skl.is_active = TRUE AND kr.is_active = TRUE
287:                 """
288:             ),
289:             {"sid": supplier_id},
290:         ).fetchall()
291:         if kl_rows:
292:             knowledge_links = [
293:                 {"category": r[0], "pattern": r[1], "normalized_to": r[2]}
294:                 for r in kl_rows
295:             ]
296:     return ExtractionContext(raw_text, supplier_context, knowledge_links, supplier_id)
```

## 4. 呼び出し元の git grep（origin/main）
```
$ git grep -n "prompt_ab" origin/main -- backend ":!backend/tests"
origin/main:backend/app/services/gemini_raw_copy_v10.py:5:このモジュールは比較試験の道具（app/tools/prompt_ab.py）専用で、本番の経路からは呼ばれない。
origin/main:backend/app/services/gemini_raw_copy_v101.py:7:このモジュールは比較試験の道具（app/tools/prompt_ab.py）専用で、本番の経路からは呼ばれない。
origin/main:backend/app/services/gemini_raw_copy_v8.py:5:このモジュールは比較試験の道具（app/tools/prompt_ab.py）専用で、本番の経路からは呼ばれない。
origin/main:backend/app/services/gemini_raw_copy_v9.py:5:このモジュールは比較試験の道具（app/tools/prompt_ab.py）専用で、本番の経路からは呼ばれない。
origin/main:backend/app/tools/prompt_ab.py:9:起動: python -m app.tools.prompt_ab --runs-file F --config v7|v8|v9|v10|v101|v102 [--prompt-name raw_copy_v9_NAME|raw_copy_v101_NAME]
origin/main:backend/app/tools/prompt_ab.py:10:        [--thinking-level L] [--no-thoughts] [--no-schema] [--temperature T] --repeat N --max-cost-usd X --test-id ID --out-dir /tmp/prompt_ab/ID [--dry-run]
origin/main:backend/app/tools/prompt_ab.py:13:purpose="line_extraction_shadow"・source_ref="prompt_ab:<test_id>" で区別する。
origin/main:backend/app/tools/prompt_ab.py:74:_SOURCE_REF_PREFIX = "prompt_ab:"
origin/main:backend/app/tools/prompt_ab.py:358:            logger.error("[prompt_ab] run id not found: %s", run_id)
origin/main:backend/app/tools/prompt_ab.py:393:                logger.exception("[prompt_ab] stopped: run=%s repeat=%d", run_id, n)
origin/main:backend/app/tools/prompt_ab.py:415:                logger.exception("[prompt_ab] ledger write failed: run=%s repeat=%d", run_id, n)
origin/main:backend/app/tools/prompt_ab.py:422:                logger.warning("[prompt_ab] stopping: %s (cost=%s)", reason, totals.cost_usd)
$ git grep -n "run_ab\|_print_dry_run" origin/main -- backend ":!backend/tests"
origin/main:backend/app/services/tcg_unit_recovery_svc.py:616:    _print_dry_run_results(e3a_result, e5_result, summary)
origin/main:backend/app/services/tcg_unit_recovery_svc.py:664:def _print_dry_run_results(
origin/main:backend/app/tools/prompt_ab.py:310:def _print_dry_run(
origin/main:backend/app/tools/prompt_ab.py:330:def run_ab(
origin/main:backend/app/tools/prompt_ab.py:349:        _print_dry_run(summary, config, ctx, v8_prompt)
origin/main:backend/app/tools/prompt_ab.py:481:        summary = run_ab(
```

## 5. ADR 検索
```
$ git grep -n -i "prompt_ab\|supplier_context\|omit-supplier" origin/main -- docs/adr
(exit=1; 出力なし=該当なし)
$ ls docs/adr | grep -E "ADR-(100|1004|085|154)[-_]"
ADR-085-supplier-prompts.md
ADR-100-sa-ingestion-analysis-pipeline.md
ADR-1004-llm-usage-ledger.md
ADR-154-tcg-parity02-gas-python-migration.md
```
- 該当 ADR は設計書の指定どおり ADR-100、ADR-1004、ADR-085、ADR-154。prompt_ab を名指しする ADR は無い。
