# recon: 比較試験の道具に仕入元ルールを差し替える切り替えを足す

- 実測時の origin/main SHA: a77cfb1c08bc591ba654e98ae66dfb99c31a1eee
- 引用は origin/main のコード（変更前）。社外秘の仕入元名・原文は書かない。

## 1. 変更対象（backend/app/tools/prompt_ab.py）

### backend/app/tools/prompt_ab.py:320-325
```
320: def _supplier_context_without(supplier_context: dict | None, omit: list[str] | None) -> dict | None:
321:     """指定した欄を除いた写しを返す（元の辞書は変えない）。指定なしなら元のものをそのまま返す。"""
322:     if not omit or supplier_context is None:
323:         return supplier_context
324:     return {k: v for k, v in supplier_context.items() if k not in omit}
325: 
```

### backend/app/tools/prompt_ab.py:327-346
```
327: def _print_dry_run(
328:     summary: AbSummary, config: str, ctx, v8_prompt: str | None, omit_supplier_fields: list[str] | None = None,
329: ) -> None:
330:     print(f"[dry-run] target_count={summary.target_count}")
331:     if ctx is None:
332:         return
333:     supplier_context = _supplier_context_without(ctx.supplier_context, omit_supplier_fields)
334:     if config in ("v8", "v9", "v10", "v101", "v102"):
335:         prompt = build_prompt_v8(
336:             ctx.raw_text, prompt_text=v8_prompt or "", supplier_context=supplier_context,
337:             knowledge_links=ctx.knowledge_links,
338:         )
339:     else:  # 表示用の組み立て（実際の呼び出しは call_gemini_raw_copy 内で同じ材料から行われる）
340:         links = [lk for lk in (ctx.knowledge_links or []) if lk.get("category") == "block_delimiter"]
341:         note = _build_supplier_context_note(ctx.supplier_context or {}, knowledge_links=links)
342:         section = f"\n{note}\n" if note else ""
343:         prompt = f"{_load_db_raw_copy_prompt()}{section}\n原文:\n{format_prompt_input(ctx.raw_text)}"
344:     for line in prompt.split("\n")[:_DRY_RUN_PROMPT_LINES]:
345:         print(line)
346: 
```

### backend/app/tools/prompt_ab.py:348-353
```
348: def run_ab(
349:     session: Session, *, run_ids: list[str], config: str, repeat: int, max_cost_usd: Decimal,
350:     test_id: str, out_dir: Path, dry_run: bool, thinking_level: str | None,
351:     include_thoughts: bool, use_schema: bool, temperature: float | None, prompt_name: str | None = None,
352:     omit_supplier_fields: list[str] | None = None,
353: ) -> AbSummary:
```

### backend/app/tools/prompt_ab.py:383-410
```
383:             if row_prompt_name is not None:
384:                 row["prompt_name"] = row_prompt_name
385:             if omit_supplier_fields:
386:                 row["omitted_supplier_fields"] = sorted(set(omit_supplier_fields))
387:             try:
388:                 if job_id not in contexts:
389:                     ctx_loaded = load_extraction_context(session, job_id)
390:                     if ctx_loaded is None:
391:                         raise RuntimeError(f"job not found: {job_id}")
392:                     contexts[job_id] = ctx_loaded
393:                 ctx = contexts[job_id]
394:                 if config == "v7":
395:                     result = _call_v7(ctx)
396:                 else:
397:                     schemas = {
398:                         "v9": V9_RESPONSE_SCHEMA, "v10": V10_RESPONSE_SCHEMA,
399:                         "v101": V101_RESPONSE_SCHEMA, "v102": V101_RESPONSE_SCHEMA,
400:                     }
401:                     extra = {"response_schema": schemas[config]} if config in schemas else {}
402:                     result = call_gemini_raw_copy_v8(
403:                         ctx.raw_text, prompt_text=v8_prompt,
404:                         supplier_context=_supplier_context_without(ctx.supplier_context, omit_supplier_fields),
405:                         knowledge_links=ctx.knowledge_links, thinking_level=thinking_level,
406:                         include_thoughts=include_thoughts, use_schema=use_schema, temperature=temperature,
407:                         **extra,
408:                     )
409:             except Exception as exc:  # noqa: BLE001
410:                 session.rollback()
```

### backend/app/tools/prompt_ab.py:417-424
```
417: 
418:             item_count, errors = _parse(config, result["response_text"], ctx.raw_text, masters)
419:             _append_jsonl(out_path, {
420:                 **row, "response_text": result["response_text"],
421:                 "thought_summaries": result["thought_summaries"], "usage_raw": result["usage_raw"],
422:                 "item_count": item_count, "errors": errors,
423:                 **_master_row_fields(config, result["response_text"], ctx, masters),
424:                 "elapsed_sec": round(time.monotonic() - started, 3),
```

### backend/app/tools/prompt_ab.py:466-480
```
466:     p.add_argument("--omit-supplier-field", action="append", type=_supplier_field_name, default=None,
467:                    help="仕入元ルールの欄（extraction_ で始まる名前）を指示から外す。何回でも指定できる。v7 では効かない")
468:     p.add_argument("--dry-run", action="store_true", help="対象の件数と組み立てた指示の先頭30行だけ表示する（Gemini は呼ばない）")
469:     args = p.parse_args(argv)
470:     if args.thinking_level:
471:         args.thinking_level = args.thinking_level.upper()
472:     if args.config == "v7" and (
473:         args.thinking_level or args.no_thoughts or args.no_schema or args.temperature is not None
474:     ):
475:         p.error("--thinking-level / --no-thoughts / --no-schema / --temperature は --config v8・v9・v10・v101・v102 のときだけ使えます")
476:     if args.config == "v7" and args.omit_supplier_field:
477:         p.error("--omit-supplier-field は --config v8・v9・v10・v101・v102 のときだけ使えます")
478:     if args.prompt_name is not None:
479:         try:
480:             resolve_prompt_path(args.prompt_name, args.config)
```

### backend/app/tools/prompt_ab.py:505-515
```
505:     session = _get_sync_session()
506:     try:
507:         summary = run_ab(
508:             session, run_ids=run_ids, config=args.config, repeat=args.repeat,
509:             max_cost_usd=args.max_cost_usd, test_id=args.test_id, out_dir=args.out_dir,
510:             dry_run=args.dry_run, thinking_level=args.thinking_level,
511:             include_thoughts=not args.no_thoughts, use_schema=not args.no_schema,
512:             temperature=args.temperature, prompt_name=args.prompt_name,
513:             omit_supplier_fields=args.omit_supplier_field,
514:         )
515:     finally:
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

## 3. ctx の定義と supplier_id（変更しない）

### backend/app/tasks/tcg_extraction.py:248-254
```
248: class ExtractionContext(NamedTuple):
249:     """ジョブの原文・仕入元ルール・knowledge リンク・仕入元 ID。"""
250: 
251:     raw_text: str
252:     supplier_context: dict | None
253:     knowledge_links: list[dict] | None
254:     supplier_id: int | None
```

### backend/app/tasks/tcg_extraction.py:276-279
```
276:     # Knowledge リンクを取得（supplier_id がある場合のみ）
277:     knowledge_links: list[dict] | None = None
278:     supplier_id = row[10]
279:     if supplier_id is not None:
```

### backend/app/tasks/tcg_extraction.py:296-296
```
296:     return ExtractionContext(raw_text, supplier_context, knowledge_links, supplier_id)
```

- 事実: ExtractionContext に supplier_id: int | None がある（backend/app/tasks/tcg_extraction.py:254）。prompt_ab は load_extraction_context の戻り値 ctx を contexts[job_id] に持つ（backend/app/tools/prompt_ab.py:393）ので ctx.supplier_id を使える。
- 事実: テストの _CTX も supplier_id=7 を持つ（backend/tests/test_prompt_ab.py:20-24）。

## 4. 呼び出し元の git grep（origin/main）
```
$ git grep -n "run_ab\|_print_dry_run\|supplier_rules" a77cfb1c0 -- backend ":!backend/tests"
a77cfb1c0:backend/app/services/tcg_unit_recovery_svc.py:616:    _print_dry_run_results(e3a_result, e5_result, summary)
a77cfb1c0:backend/app/services/tcg_unit_recovery_svc.py:664:def _print_dry_run_results(
a77cfb1c0:backend/app/tools/prompt_ab.py:327:def _print_dry_run(
a77cfb1c0:backend/app/tools/prompt_ab.py:348:def run_ab(
a77cfb1c0:backend/app/tools/prompt_ab.py:368:        _print_dry_run(summary, config, ctx, v8_prompt, omit_supplier_fields)
a77cfb1c0:backend/app/tools/prompt_ab.py:507:        summary = run_ab(
```

## 5. ADR 検索
```
$ git grep -n -i "prompt_ab\|supplier_context\|omit-supplier\|supplier-rules" origin/main -- docs/adr
(exit=1; 出力なし=該当なし)
$ ls docs/adr | grep -E "ADR-(100|1004|085|154)[-_]"
ADR-085-supplier-prompts.md
ADR-100-sa-ingestion-analysis-pipeline.md
ADR-1004-llm-usage-ledger.md
ADR-154-tcg-parity02-gas-python-migration.md
```
- 該当 ADR は設計書の指定どおり ADR-100、ADR-1004、ADR-085、ADR-154。prompt_ab を名指しする ADR は無い。
