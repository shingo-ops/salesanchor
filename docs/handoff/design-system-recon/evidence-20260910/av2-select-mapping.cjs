// AV-2 recon main: inventory + applied CSS + mold diff + classification. Read-only.
const fs = require('fs'), path = require('path');
const P = require('./av2-project.cjs'); const { ts, files, ROOT, rel, classTokens, full, isJsx, tagText, jsxAttr, opening, hasSpread, emptyTok } = P;
const C = require('./av2-css.cjs');
const OUT = path.join(ROOT, 'out');
const BASE_SHA = process.argv[2] || '(unknown)';

// ---------- A: inventory ----------
const SKIP_FILE = /frontend\/src\/components\/Select\.tsx$/;
const selects = [];
for (const fi of files.values()) {
  if (!fi.abs.endsWith('.tsx') || SKIP_FILE.test(fi.rel)) continue;
  const v = n => { if (isJsx(n) && tagText(n) === 'select') selects.push({ fi, el: n }); ts.forEachChild(n, v); };
  v(fi.sf);
}
selects.sort((a, b) => a.fi.rel.localeCompare(b.fi.rel) || a.el.getStart(a.fi.sf) - b.el.getStart(b.fi.sf));
const lineOf = (fi, n) => fi.sf.getLineAndCharacterOfPosition(n.getStart(fi.sf)).line + 1;
const norm = s => s.replace(/\s+/g, ' ').trim();
const cap = (s, n) => (s.length > n ? s.slice(0, n) + '…[cut]' : s);

// ---------- E helpers ----------
function arrayLiteralLabels(fi, recv) {
  if (!recv || !ts.isIdentifier(recv)) return null;
  let found = null;
  const v = n => { if (found) return; if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && n.name.text === recv.text && n.initializer) { let i = n.initializer; while (i && (ts.isAsExpression(i) || ts.isParenthesizedExpression(i))) i = i.expression; if (ts.isArrayLiteralExpression(i)) found = i; } ts.forEachChild(n, v); };
  v(fi.sf); if (!found) return null;
  const raw = []; let tCount = 0;
  const w = n => { if (ts.isPropertyAssignment(n) && /^(label|name|text|title|labelKey)$/.test(n.name.getText())) { const x = n.initializer; if (ts.isStringLiteral(x) || ts.isNoSubstitutionTemplateLiteral(x)) { if (n.name.getText() === 'labelKey') tCount++; else raw.push(x.text); } else if (/\bt\(/.test(x.getText())) tCount++; } if (ts.isStringLiteral(n) && n.parent && ts.isArrayLiteralExpression(n.parent)) raw.push(n.text); ts.forEachChild(n, w); };
  w(found); return { raw, tCount };
}
function optionFacts(fi, el) {
  const sf = fi.sf; const op = opening(el);
  const attr = n => { const a = jsxAttr(el, n); return a ? (a.initializer ? a.initializer.getText(sf) : 'true') : null; };
  const kids = ts.isJsxElement(el) ? el.children.filter(c => !(ts.isJsxText(c) && !c.getText(sf).trim())) : [];
  const optNodes = []; if (ts.isJsxElement(el)) { const fo = n => { if (isJsx(n) && tagText(n) === 'option') optNodes.push(n); ts.forEachChild(n, fo); }; fo(el); }
  let tLabels = 0, exprLabels = 0, hasDisabled = false; const rawLabels = [];
  for (const o of optNodes) {
    if (jsxAttr(o, 'disabled')) hasDisabled = true;
    if (ts.isJsxElement(o)) for (const c of o.children) {
      if (ts.isJsxText(c)) { const x = c.getText(sf).trim(); if (x) rawLabels.push(x); }
      else if (ts.isJsxExpression(c) && c.expression) { const x = c.expression.getText(sf); if (/\bt\(/.test(x)) tLabels++; else if (/^["'`]/.test(x)) rawLabels.push(x); else exprLabels++; }
    }
  }
  // map sources
  const mapSources = [];
  const fm = n => { if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && n.expression.name.text === 'map') { const r = n.expression.expression; const al = arrayLiteralLabels(fi, r); mapSources.push({ receiver: cap(r.getText(sf), 120), arrayLiteral: !!al, rawLiteralLabels: al ? al.raw : null, tLabelProps: al ? al.tCount : null }); } ts.forEachChild(n, fm); };
  if (ts.isJsxElement(el)) fm(el);
  const oc = attr('onChange'); let resolved = null;
  if (oc) { const m = oc.match(/^\{\s*([A-Za-z_$][\w$]*)\s*\}$/); if (m) { let f = null; const v = n => { if (f) return; if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && n.name.text === m[1] && n.initializer) f = n.initializer.getText(sf); else if (ts.isFunctionDeclaration(n) && n.name && n.name.text === m[1]) f = n.getText(sf); ts.forEachChild(n, v); }; v(sf); resolved = f; } }
  const hText = resolved || oc || '';
  const reads = []; if (/\.target\.value|\btarget\.value/.test(hText)) reads.push('target.value'); if (/selectedOptions|selectedIndex/.test(hText)) reads.push('selectedOptions/Index'); if (oc && !reads.length) reads.push(/\bvalue\b/.test(hText) ? 'other(value-ish)' : 'other/unresolved');
  const numeric = /Number\(|parseInt\(|parseFloat\(|\+\s*e\.target|\+\s*\w+\.target/.test(hText);
  const kinds = kids.map(c => { if (isJsx(c)) return tagText(c); if (ts.isJsxFragment(c)) return 'fragment'; if (ts.isJsxExpression(c)) { const e = c.expression; if (!e) return 'comment/empty'; const tx = e.getText(sf); if (/\.map\(/.test(tx)) return 'map'; if (ts.isConditionalExpression(e) || (ts.isBinaryExpression(e) && /&&|\|\|/.test(e.operatorToken.getText(sf)))) return 'conditional'; return 'expression'; } return 'text'; });
  return { onChange: cap(oc || '', 200), onChangeResolved: resolved ? cap(resolved, 200) : null, readsPattern: reads, numericConverted: numeric, childKinds: kinds, childPattern: kinds.includes('optgroup') ? 'optgroup' : kinds.includes('map') ? 'map' : kinds.every(k => k === 'option') ? 'static-option' : kinds.includes('conditional') ? 'conditional' : 'mixed', hasDisabledOption: hasDisabled, labelsT: tLabels, labelsExprUnresolved: exprLabels, labelsRaw: rawLabels, mapSources, value: attr('value'), id: attr('id') };
}
function uiAllowFor(fi, el) {
  const lines = fi.src.split('\n'); const start = lineOf(fi, el) - 1; const endL = fi.sf.getLineAndCharacterOfPosition(opening(el).getEnd()).line;
  const found = [];
  let i = start - 1; while (i >= 0 && lines[i].trim() === '') i--;
  while (i >= 0 && /ui-allow/.test(lines[i])) { found.unshift({ line: i + 1, text: lines[i].trim(), position: 'preceding' }); i--; }
  for (let l = start; l <= endL; l++) if (/ui-allow/.test(lines[l])) found.push({ line: l + 1, text: lines[l].trim(), position: 'in-opening-tag' });
  return found;
}
const kebab = s => s.replace(/[A-Z]/g, m => '-' + m.toLowerCase());
function inlineStyle(fi, el) {
  const a = jsxAttr(el, 'style'); if (!a) return { present: false, props: [], text: null, unresolved: false };
  const e = a.initializer && ts.isJsxExpression(a.initializer) ? a.initializer.expression : null;
  const text = a.initializer ? a.initializer.getText(fi.sf) : '';
  if (!e || !ts.isObjectLiteralExpression(e)) return { present: true, props: [], text: cap(text, 400), unresolved: true };
  const props = [];
  for (const p of e.properties) {
    if (!ts.isPropertyAssignment(p)) { props.push({ prop: '(spread/shorthand)', value: p.getText(fi.sf), dynamic: true, kind: 'unknown' }); continue; }
    const k = kebab(p.name.getText(fi.sf).replace(/^["']|["']$/g, '')); const x = p.initializer;
    const lit = ts.isStringLiteral(x) || ts.isNoSubstitutionTemplateLiteral(x);
    props.push({ prop: k, value: lit ? x.text : x.getText(fi.sf), dynamic: !lit && !ts.isNumericLiteral(x), kind: C.kindOf(k) });
  }
  return { present: true, props, text: cap(text, 400), unresolved: false };
}

// ---------- mold ----------
const moldFilter = r => r.file === 'frontend/src/components/FormField.css';
const moldSel = size => ({ attrNames: new Set(), idLit: undefined, spread: false, tokens: { prefixes: new Set(), st: new Set(['comp-select__control', ...(size !== 'md' ? ['comp-select__control--' + size] : [])]), cond: new Set(), unresolved: false }, chains: [{ entries: [], closed: true }] });
const mold = {};
for (const size of ['sm', 'md', 'lg']) {
  const m = C.matchRules(moldSel(size), moldFilter);
  const buckets = [...new Set(m.map(x => x.state))]; const eff = {};
  for (const b of buckets) eff[b] = C.effective(m, b);
  mold[size] = { eff, rules: m.map(x => ({ file: x.rule.file, line: x.rule.line, selector: x.rule.selector, state: x.state })) };
}
const moldBase = s => Object.fromEntries(Object.entries(mold[s].eff.base).map(([k, v]) => [k, v.value]));

const GROUPS = [['padding-top'], ['padding-right'], ['padding-bottom'], ['padding-left'], ['border'], ['border-radius'], ['font-size'], ['color'], ['background-color'], ['background-image'], ['height'], ['min-height'], ['line-height'], ['cursor'], ['appearance']];
function groupVal(effMap, g) { // effMap: prop -> value
  if (g === 'border') { const ks = Object.keys(effMap).filter(k => k.startsWith('border') && !k.startsWith('border-radius')).sort(); if (!ks.length) return null; if (ks.length === 1 && ks[0] === 'border') return effMap.border; return ks.map(k => k + ': ' + effMap[k]).join('; '); }
  return effMap[g] === undefined ? null : effMap[g];
}
const GROUP_KEYS = new Set(['padding-top', 'padding-right', 'padding-bottom', 'padding-left', 'border-radius', 'font-size', 'color', 'background-color', 'background-image', 'height', 'min-height', 'line-height', 'cursor', 'appearance']);
const inGroup = k => GROUP_KEYS.has(k) || (k.startsWith('border') && !k.startsWith('border-radius'));
const UNSET = '(unset: browser default)';
const rv = v => (v ? C.resolveTok(v) : v);
function diffAgainst(curEff, size) {
  const mb = moldBase(size); const rows = [];
  for (const [g] of GROUPS) {
    const before = groupVal(curEff, g), after = groupVal(mb, g);
    const equal = before !== null && after !== null && before === after;
    const row = { property: g, before: before === null ? UNSET : before, after: after === null ? '(none)' : after, equal };
    if (/^padding|^font-size$/.test(g) && before && after) { row.resolvedBefore = rv(before); row.resolvedAfter = rv(after); row.equalResolved = rv(before) === rv(after); }
    rows.push(row);
  }
  return rows;
}
const PAD = ['padding-top', 'padding-right', 'padding-bottom', 'padding-left'];

// ---------- main loop ----------
const rows = [];
for (const { fi, el } of selects) {
  const line = lineOf(fi, el);
  const cn = jsxAttr(el, 'className');
  const tokens = cn && cn.initializer ? classTokens(fi, cn.initializer) : emptyTok();
  const spread = hasSpread(el);
  const idAttr = jsxAttr(el, 'id');
  const style = inlineStyle(fi, el);
  // ancestors
  const chains = full(fi, el, 0);
  const attrNames = new Set(opening(el).attributes.properties.filter(a => ts.isJsxAttribute(a)).map(a => a.name.getText()));
  const idLit = idAttr ? (idAttr.initializer && ts.isStringLiteral(idAttr.initializer) ? idAttr.initializer.text : null) : undefined;
  const sel = { tokens, chains, attrNames, idLit, spread };
  const matched = C.matchRules(sel);
  const applied = matched.filter(m => m.status !== 'unconfirmed');
  const unconfirmed = matched.filter(m => m.status === 'unconfirmed');
  const ruleOut = m => ({ file: m.rule.file, line: m.rule.line, selector: m.rule.selector, state: m.state, media: m.rule.media || null, origin: m.origin, status: m.status, whys: m.whys, layout: m.rule.decls.filter(d => C.kindOf(d.prop) === 'layout').map(d => ({ prop: d.prop, value: C.normV(d.value), line: d.line, important: d.important })), decoration: m.rule.decls.filter(d => C.kindOf(d.prop) === 'decoration').map(d => ({ prop: d.prop, value: C.normV(d.value), line: d.line, important: d.important })) });
  // effective with inline
  const inlineItems = style.props.filter(p => p.kind !== 'unknown').flatMap(p => C.expandDecl(p.prop, String(p.value)).map(([k, v]) => ({ prop: k, value: v })));
  const curEff = {}; const buckets = [...new Set(applied.map(m => m.state))];
  const uniMatched = C.universalBase.map(rule => ({ rule, status: 'definite', state: 'base', universal: true }));
  const effBase = C.effective(applied.concat(uniMatched), 'base', inlineItems);
  const effBuckets = {}; for (const b of buckets) if (b !== 'base') effBuckets[b] = C.effective(applied, b);
  // decoration-only effective (longhands whose source prop is decoration)
  const decoBase = {}; for (const [k, v] of Object.entries(effBase)) { const src = (k.startsWith('padding-') ? 'padding' : k.startsWith('background-') ? 'background' : k); if (C.kindOf(src) === 'decoration' && !k.startsWith('--') && !v.universal) decoBase[k] = v.value; }
  const layoutDeclared = [...new Set([...applied.flatMap(m => m.rule.decls.filter(d => C.kindOf(d.prop) === 'layout').map(d => d.prop)), ...style.props.filter(p => p.kind === 'layout').map(p => p.prop)])];
  const hasDecoBase = Object.keys(decoBase).length > 0;
  const stateDeco = applied.filter(m => m.state !== 'base' && m.rule.decls.some(d => C.kindOf(d.prop) === 'decoration'));
  // compare to molds
  const perSize = {}; let best = null;
  for (const size of ['sm', 'md', 'lg']) {
    const table = diffAgainst(Object.fromEntries(Object.entries(effBase).map(([k, v]) => [k, v.value])), size);
    const mb = moldBase(size);
    const declDiff = Object.entries(decoBase).filter(([k, v]) => mb[k] !== v).map(([k, v]) => ({ property: k, before: v, after: mb[k] === undefined ? '(not in mold)' : mb[k] }));
    // state buckets
    const stateDiff = [];
    for (const [b, e] of Object.entries(effBuckets)) { const mbuck = mold[size].eff[b] || {}; for (const [k, v] of Object.entries(e)) { const src = (k.startsWith('padding-') ? 'padding' : k.startsWith('background-') ? 'background' : k); if (C.kindOf(src) !== 'decoration') continue; const mvv = mbuck[k] ? mbuck[k].value : undefined; if (mvv !== v.value) stateDiff.push({ state: b, property: k, before: v.value, after: mvv === undefined ? '(not in mold for this state)' : mvv }); } }
    const fontMis = !(effBase['font-size'] && effBase['font-size'].value === mb['font-size']);
    const padMis = PAD.filter(k => !(effBase[k] && effBase[k].value === mb[k])).length;
    const otherDeclMis = Object.entries(decoBase).filter(([k]) => !k.startsWith('padding-') && k !== 'font-size').filter(([k, v]) => mb[k] !== v).length;
    const score = fontMis * 100 + padMis * 10 + otherDeclMis;
    perSize[size] = { score, fontSizeExact: !fontMis, paddingSidesExact: 4 - padMis, declaredDecorationDiffers: declDiff, stateDecorationDiffers: stateDiff, table, exactDeclared: declDiff.length === 0 && stateDiff.length === 0 };
    const pref = { md: 0, sm: 1, lg: 2 }[size];
    if (!best || score < best.score || (score === best.score && pref < best.pref)) best = { size, score, pref };
  }
  const hasDirtyUnconfirmed = unconfirmed.length > 0 || (tokens.unresolved && !tokens.st.size && !tokens.cond.size) || spread;
  const exactSizes = ['sm', 'md', 'lg'].filter(s => perSize[s].exactDeclared);
  // classification
  const anyRule = applied.length > 0 || style.props.length > 0 || style.unresolved;
  let cls, clsReason = [];
  const ownClassUnresolved = (cn && tokens.unresolved) || spread;
  if (unconfirmed.length) { cls = 'v'; clsReason.push(unconfirmed.length + ' unconfirmed rule(s)'); }
  else if (ownClassUnresolved) { cls = 'v'; clsReason.push(spread && !(cn && tokens.unresolved) ? 'spread attributes may forward className/style' : 'own className expression not fully resolvable'); }
  else if (style.unresolved) { cls = 'v'; clsReason.push('style attribute not an object literal'); }
  else if (!anyRule) cls = 'i';
  else if (!hasDecoBase && !stateDeco.length && !style.props.some(p => p.kind === 'decoration')) cls = 'ii';
  else if (exactSizes.length) cls = 'iii';
  else cls = 'iv';
  const bestSize = cls === 'i' ? null : best.size;
  const chainSummary = chains.slice(0, 1).map(ch => ch.entries.map(e => e.k === 'dom' ? e.tag + [...e.st].map(t => '.' + t).join('') + ([...e.cond, ...e.maybe].length ? '(?' + [...e.cond, ...e.maybe].map(t => '.' + t).join('') + ')' : '') + (e.unresolved ? '(?className)' : '') : '?[' + e.why + ']'));
  const ancUnkWhys = [...new Set(chains.flatMap(ch => ch.entries.filter(e => e.k === 'unk').map(e => e.why)))];
  const opt = optionFacts(fi, el);
  rows.push({
    file: fi.rel, line, classification: cls, classificationReasons: clsReason,
    component: (() => { for (let p = el.parent; p; p = p.parent) if (ts.isFunctionLike(p)) { const n = P.fnNameOf(p); if (n) return n; } return null; })(),
    openingTag: cap(opening(el).getText(fi.sf), 600),
    className: { expression: cn && cn.initializer ? cap(cn.initializer.getText(fi.sf), 300) : null, staticTokens: [...tokens.st], conditionalTokens: [...tokens.cond], unresolved: tokens.unresolved, spreadAttributes: spread },
    id: idAttr && idAttr.initializer ? idAttr.initializer.getText(fi.sf) : null,
    inlineStyle: style,
    ancestors: { chainCount: chains.length, closedChains: chains.filter(c => c.closed).length, firstChainInnermostToOutermost: chainSummary[0] || [], unknownReasons: ancUnkWhys },
    appliedRules: applied.map(ruleOut),
    unconfirmedRules: unconfirmed.map(ruleOut),
    layoutProperties: layoutDeclared,
    effectiveBaseDecoration: Object.fromEntries(Object.entries(decoBase)),
    effectiveBaseAll: Object.fromEntries(Object.entries(effBase).map(([k, v]) => [k, { value: v.value, from: v.from, ambiguousAcrossFiles: v.ambiguous, conditional: v.conditional }])),
    stateDecorations: stateDeco.map(m => ({ state: m.state, file: m.rule.file, line: m.rule.line, selector: m.rule.selector })),
    ownedDimensionDeclared: layoutDeclared.filter(x => /^(height|min-height|max-height)$/.test(x)),
    iiiStrength: cls === 'iii' ? (Object.keys(decoBase).some(k => k === 'font-size' || k.startsWith('padding-')) ? 'declares font-size/padding' : 'weak: declares only ' + Object.keys(decoBase).join(',')) : null,
    nearestSize: bestSize, exactSizes, nearestIsExact: cls === 'iii',
    perSize,
    options: opt,
    uiAllow: uiAllowFor(fi, el),
  });
}

// ---------- A: compare with av1 ----------
const av1 = JSON.parse(fs.readFileSync(path.join(ROOT, 'docs/handoff/design-system-recon/evidence-20260910/av1-select-detail.json'), 'utf8'));
const keyer = list => { const seen = {}; return list.map(r => { const k = r.file + '|' + norm(r.openingTag); seen[k] = (seen[k] || 0) + 1; return Object.assign({ key: k + '#' + seen[k] }, r); }); };
const oldK = keyer(av1.map(r => ({ file: r.file, line: r.line, openingTag: cap(r.openingTag, 600) })));
const newK = keyer(rows.map(r => ({ file: r.file, line: r.line, openingTag: r.openingTag })));
// compare using un-capped normalized text of first 300 chars to avoid cap differences
const k2 = list => { const seen = {}; return list.map(r => { const k = r.file + '|' + norm(r.openingTag).slice(0, 300); seen[k] = (seen[k] || 0) + 1; return { key: k + '#' + seen[k], file: r.file, line: r.line }; }); };
const o2 = k2(av1.map(r => ({ file: r.file, line: r.line, openingTag: r.openingTag }))), n2 = k2(rows.map(r => ({ file: r.file, line: r.line, openingTag: r.openingTag })));
const oM = new Map(o2.map(r => [r.key, r])), nM = new Map(n2.map(r => [r.key, r]));
const inv = { av1Count: av1.length, newCount: rows.length, removedByKey: o2.filter(r => !nM.has(r.key)).map(r => r.file + ':' + r.line), addedByKey: n2.filter(r => !oM.has(r.key)).map(r => r.file + ':' + r.line), lineMoved: n2.filter(r => oM.has(r.key) && oM.get(r.key).line !== r.line).map(r => r.file + ': ' + oM.get(r.key).line + ' -> ' + r.line) };
// secondary: removed/added by file+line
const oL = new Set(av1.map(r => r.file + ':' + r.line)), nL = new Set(rows.map(r => r.file + ':' + r.line));
inv.fileLineOnlyRemoved = [...oL].filter(x => !nL.has(x)); inv.fileLineOnlyAdded = [...nL].filter(x => !oL.has(x));
// av1 option fact diffs for matched keys
const av1ByKey = new Map(); { const seen = {}; av1.forEach(r => { const k = r.file + '|' + norm(r.openingTag).slice(0, 300); seen[k] = (seen[k] || 0) + 1; av1ByKey.set(k + '#' + seen[k], r); }); }
{ const seen = {}; rows.forEach(r => { const k = r.file + '|' + norm(r.openingTag).slice(0, 300); seen[k] = (seen[k] || 0) + 1; const o = av1ByKey.get(k + '#' + seen[k]); if (!o) { r.vsAv1 = 'new-in-this-base'; return; } const diffs = []; if (o.numericConverted !== r.options.numericConverted) diffs.push('numericConverted'); if (JSON.stringify(o.readsPattern) !== JSON.stringify(r.options.readsPattern)) diffs.push('readsPattern'); if (JSON.stringify(o.labelsRaw) !== JSON.stringify(r.options.labelsRaw)) diffs.push('labelsRaw'); if (o.labelsT !== r.options.labelsT) diffs.push('labelsT'); if (o.childPattern !== r.options.childPattern) diffs.push('childPattern'); r.vsAv1 = diffs.length ? 'changed: ' + diffs.join(',') : 'unchanged'; }); }

const counts = {}; rows.forEach(r => { counts[r.classification] = (counts[r.classification] || 0) + 1; });
const result = { baseSha: BASE_SHA, generatedBy: 'av2-select-mapping.cjs', typescriptVersion: ts.version, definitions: {
  inventory: 'JSX <select> in frontend/src/**/*.tsx excluding *.stories.tsx, *.test.tsx and components/Select.tsx',
  applied: 'rules from every frontend/src/**/*.css (all assumed loaded) whose last compound can match the select; ancestor-scoped rules matched against JSX ancestor chain (in-file + component def children placement + JSX usage sites up to depth 10)',
  layout: 'property in the layoutClassName allowed list (final-ci-contract-audit.md lines 42-62); everything else is DECORATION (height/min-height are in the list; reported but Select owns them)',
  classes: { i: 'no matched rule and no inline style (browser default)', ii: 'matched rules/inline style exist but only LAYOUT declarations', iii: 'declared DECORATION (base + state buckets) is a subset of one mold bare size with identical values (declared-only; mold would additionally add unset properties)', iv: 'declared DECORATION differs from every mold size', v: 'any unconfirmed rule (ancestor unknown / conditional ancestor class / forwarded className / attr-id-functional-pseudo unverified) or className/style not resolvable' },
  universalRulesNote: 'rules whose last compound is only * / pseudo (no tag/class/id/attr) are NOT attached per select; listed once under universalRules',
  nestedCssNote: 'CSS nesting (rules inside rules) is not evaluated; count in nestedRulesSkipped' },
  counts, inventory: inv, mold: { sm: mold.sm, md: mold.md, lg: mold.lg }, tokens: C.tokens,
  universalBaselineAppliedToEverySelect: C.universalBase.map(r => r.file + ':' + r.line + ' ' + r.selector + ' { ' + r.decls.map(d => d.prop + ': ' + d.value).join('; ') + ' }'), universalRules: C.universalRules.map(r => ({ file: r.file, line: r.line, selector: r.selector, media: r.media || null, decls: r.decls.map(d => d.prop + ': ' + d.value) })), nestedRulesSkipped: C.nestedRules, rows };
fs.writeFileSync(path.join(OUT, 'av2-select-mapping.json'), JSON.stringify(result, null, 1));
console.log(JSON.stringify({ baseSha: BASE_SHA, total: rows.length, counts, inv: { av1: inv.av1Count, now: inv.newCount, removed: inv.removedByKey.length, added: inv.addedByKey.length, moved: inv.lineMoved.length, flRemoved: inv.fileLineOnlyRemoved.length, flAdded: inv.fileLineOnlyAdded.length }, universal: C.universalRules.length, nested: C.nestedRules.length }, null, 1));
