# ay2-handlers

base HEAD 08f59418c772fab0bed6137e818d5e87de5c91f2。text-like page-side input のうち ref または onKeyDown を持つもの: 7 件（ref 2 / onKeyDown 7 / 両方 2）。付随して onFocus/onBlur/autoFocus/tabIndex/inputMode も併記。

TextFieldControl は forwardRef で `...rest` を input に渡すため（frontend/src/components/TextField.tsx）、ref・onKeyDown・onFocus 等はそのまま渡る（事実: TextField.tsx のソース）。

## frontend/src/components/InventoryPicker.tsx:217  G28  type=text

```tsx
217:       <input
218:         ref={inputRef}
219:         type="text"
220:         value={query}
221:         onChange={(e) => {
222:           setQuery(e.target.value);
223:           setOpen(true);
224:         }}
225:         onFocus={() => setOpen(true)}
226:         onKeyDown={onKeyDown}
227:         disabled={disabled}
228:         placeholder={placeholderText}
229:         data-testid={`${testIdPrefix}-input`}
230:         style={{
231:           width: "100%",
232:           minWidth: "var(--min-width-input-sm)",
233:           padding: "var(--space-6px) var(--space-2)",
234:         }}
235:         aria-label={placeholderText}
236:       />
```

- 付随属性: onFocus
- ref = `inputRef` の使用箇所（同一ファイル内）:
  - 93: const inputRef = useRef<HTMLInputElement | null>(null);
  - 100: if (!inputRef.current) return;
  - 101: const r = inputRef.current.getBoundingClientRect();
  - 125: if (inputRef.current?.contains(target)) return;
  - 218: ref={inputRef}
- onKeyDown = `onKeyDown`
- ハンドラ定義 (188-204):
```tsx
188:   const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
189:     if (!open || results.length === 0) return;
190:     if (e.key === "ArrowDown") {
191:       e.preventDefault();
192:       setActiveIndex((i) => Math.min(i + 1, results.length - 1));
193:     } else if (e.key === "ArrowUp") {
194:       e.preventDefault();
195:       setActiveIndex((i) => Math.max(i - 1, 0));
196:     } else if (e.key === "Enter") {
197:       if (activeIndex >= 0 && activeIndex < results.length) {
198:         e.preventDefault();
199:         handleSelect(results[activeIndex]);
200:       }
201:     } else if (e.key === "Escape") {
202:       setOpen(false);
203:     }
204:   };
```

## frontend/src/components/InventorySearchBar.tsx:272  G47  type=text

```tsx
272:         <input
273:           ref={inputRef}
274:           type="text"
275:           value={query}
276:           onChange={(e) => {
277:             setQuery(e.target.value);
278:             setOpen(true);
279:           }}
280:           onFocus={() => setOpen(true)}
281:           onKeyDown={onKeyDown}
282:           disabled={disabled}
283:           placeholder={placeholderText}
284:           data-testid={`${testIdPrefix}-input`}
285:           style={{ flex: 1, minWidth: "var(--min-width-input-sm)", padding: "var(--space-6px) var(--space-2)" }}
286:           aria-label={t("inventory.search.placeholder")}
287:         />
```

- 付随属性: onFocus
- ref = `inputRef` の使用箇所（同一ファイル内）:
  - 119: const inputRef = useRef<HTMLInputElement | null>(null);
  - 126: if (!inputRef.current) return;
  - 127: const r = inputRef.current.getBoundingClientRect();
  - 152: if (inputRef.current?.contains(target)) return;
  - 273: ref={inputRef}
- onKeyDown = `onKeyDown`
- ハンドラ定義 (231-247):
```tsx
231:   const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
232:     if (!open || results.length === 0) return;
233:     if (e.key === "ArrowDown") {
234:       e.preventDefault();
235:       setActiveIndex((i) => Math.min(i + 1, results.length - 1));
236:     } else if (e.key === "ArrowUp") {
237:       e.preventDefault();
238:       setActiveIndex((i) => Math.max(i - 1, 0));
239:     } else if (e.key === "Enter") {
240:       if (activeIndex >= 0 && activeIndex < results.length) {
241:         e.preventDefault();
242:         handleSelect(results[activeIndex]);
243:       }
244:     } else if (e.key === "Escape") {
245:       setOpen(false);
246:     }
247:   };
```

## frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:470  G07  type=omitted

```tsx
470:           <input
471:             value={query}
472:             onChange={(e) => setQuery(e.target.value)}
473:             onKeyDown={(e) => { if (e.key === 'Enter') search(); }}
474:             placeholder={t('superAdmin.supplierQuality.productAssign.searchPlaceholder')}
475:           />
```

- 付随属性: なし
- onKeyDown = `(e) => { if (e.key === 'Enter') search(); }`

## frontend/src/pages/inventory/InventoryPage.tsx:384  G12  type=search

```tsx
384:               <input
385:                 type="search"
386:                 className="field-h-md field-w-md"
387:                 placeholder={t("inventory.view.searchPlaceholder")}
388:                 data-testid="inventory-search"
389:                 value={searchQ}
390:                 onChange={(e) => {
391:                   setSearchQ(e.target.value);
392:                   setPage(1);
393:                 }}
394:                 onKeyDown={(e) => { if (e.key === "Enter") runSearch(); }}
395:               />
```

- 付随属性: なし
- onKeyDown = `(e) => { if (e.key === "Enter") runSearch(); }`

## frontend/src/pages/super-admin/DexTab.tsx:200  G02  type=omitted

```tsx
200:         <input
201:           placeholder={t("common.search")}
202:           value={search}
203:           onChange={(e) => setSearch(e.target.value)}
204:           onKeyDown={(e) => {
205:             if (e.key === "Enter") load();
206:           }}
207:         />
```

- 付随属性: なし
- onKeyDown = `(e) => { if (e.key === "Enter") load(); }`

## frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:295  G22  type=omitted

```tsx
295:           <input
296:             placeholder={t("common.search")}
297:             value={ruleSearch}
298:             data-testid="rules-search"
299:             onChange={(e) => setRuleSearch(e.target.value)}
300:             onKeyDown={(e) => { if (e.key === "Enter") loadRules(ruleSearch); }}
301:             style={{ width: SEARCH_WIDTH, maxWidth: "100%" }}
302:           />
```

- 付随属性: なし
- onKeyDown = `(e) => { if (e.key === "Enter") loadRules(ruleSearch); }`

## frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:374  G22  type=omitted

```tsx
374:           <input
375:             placeholder={t("common.search")}
376:             value={aliasSearch}
377:             data-testid="aliases-search"
378:             onChange={(e) => setAliasSearch(e.target.value)}
379:             onKeyDown={(e) => { if (e.key === "Enter") loadAliases(aliasSearch); }}
380:             style={{ width: SEARCH_WIDTH, maxWidth: "100%" }}
381:           />
```

- 付随属性: なし
- onKeyDown = `(e) => { if (e.key === "Enter") loadAliases(aliasSearch); }`
