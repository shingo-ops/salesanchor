// AV-2 recon: CSS rule model, matcher, cascade. Read-only.
const fs = require('fs'), path = require('path');
const NM = '/Users/tanizawashingo/salesanchor/frontend/node_modules';
const postcss = require(NM + '/postcss'), sp = require(NM + '/postcss-selector-parser');
const { ROOT, rel, allCss } = require('./av2-project.cjs');

const LAYOUT_PROPS = new Set(`display position inset top right bottom left z-index width min-width max-width height min-height max-height margin margin-top margin-right margin-bottom margin-left margin-inline margin-inline-start margin-inline-end margin-block margin-block-start margin-block-end flex flex-grow flex-shrink flex-basis align-self justify-self order grid-area grid-column grid-column-start grid-column-end grid-row grid-row-start grid-row-end`.split(/\s+/));
const kindOf = prop => (LAYOUT_PROPS.has(prop) ? 'layout' : 'decoration');

function splitTop(v) { const out = []; let d = 0, cur = ''; for (const ch of v.trim()) { if (ch === '(') d++; if (ch === ')') d--; if (/\s/.test(ch) && d === 0) { if (cur) out.push(cur); cur = ''; } else cur += ch; } if (cur) out.push(cur); return out; }
const normV = v => v.replace(/\s*!important\s*$/i, '').replace(/\s+/g, ' ').trim();
function sides(vals) { const [a, b = a, c = a, d = b] = vals; return [a, b, c, d]; }
function expandDecl(prop, value) { // -> [[longhand, value]]
  const v = normV(value); const t = splitTop(v);
  if (prop === 'padding' && t.length >= 1 && t.length <= 4) { const [T, R, B, L] = sides(t); return [['padding-top', T], ['padding-right', R], ['padding-bottom', B], ['padding-left', L]]; }
  if (prop === 'padding-inline' && t.length <= 2) { const [a, b = a] = t; return [['padding-left', a], ['padding-right', b]]; }
  if (prop === 'padding-block' && t.length <= 2) { const [a, b = a] = t; return [['padding-top', a], ['padding-bottom', b]]; }
  if (prop === 'background') {
    if (/url\(/.test(v) || t.length > 1) return [['background-color', 'shorthand:' + v], ['background-image', /url\(/.test(v) ? 'shorthand:' + v : 'none']];
    return [['background-color', v], ['background-image', 'none']];
  }
  if (prop === '-webkit-appearance') return [['appearance', v]];
  return [[prop, v]];
}

function parseSelectors(selStr) {
  // returns array of parsed selectors: {compounds:[{tag,classes,ids,attrs,pseudos,funcPseudos,pseudoEls,universal,comb}], spec}
  const out = [];
  sp(root => {
    root.each(selector => {
      const compounds = []; let cur = null;
      const fresh = () => ({ tag: null, classes: [], ids: [], attrs: [], pseudos: [], funcPseudos: [], pseudoEls: [], universal: false, comb: null });
      cur = fresh(); let spec = [0, 0, 0]; let nested = false;
      selector.nodes.forEach(n => {
        if (n.type === 'combinator') { cur.comb = n.value.trim() || ' '; compounds.push(cur); cur = fresh(); return; }
        if (n.type === 'tag') { cur.tag = n.value; spec[2]++; }
        else if (n.type === 'universal') cur.universal = true;
        else if (n.type === 'class') { cur.classes.push(n.value); spec[1]++; }
        else if (n.type === 'id') { cur.ids.push(n.value); spec[0]++; }
        else if (n.type === 'attribute') { cur.attrs.push(n.toString().trim()); spec[1]++; }
        else if (n.type === 'nesting') nested = true;
        else if (n.type === 'pseudo') {
          if (n.value.startsWith('::') || /^:(before|after|first-line|first-letter)$/.test(n.value)) { cur.pseudoEls.push(n.value); spec[2]++; }
          else if (n.nodes && n.nodes.length) { cur.funcPseudos.push(n.toString().trim()); if (n.value !== ':where') spec[1]++; }
          else { cur.pseudos.push(n.value); spec[1]++; }
        }
      });
      compounds.push(cur);
      out.push({ compounds, spec, nested, text: selector.toString().replace(/\s+/g, ' ').trim() });
    });
  }).processSync(selStr);
  return out;
}

const cssRules = []; let order = 0; const nestedRules = [];
for (const abs of allCss) {
  const isModule = /\.module\.css$/.test(abs);
  const root = postcss.parse(fs.readFileSync(abs, 'utf8'), { from: abs });
  root.walkRules(rule => {
    const ats = []; for (let p = rule.parent; p && p.type !== 'root'; p = p.parent) { if (p.type === 'atrule') ats.unshift('@' + p.name + ' ' + p.params); else if (p.type === 'rule') ats.unshift('NESTED-IN ' + p.selector); }
    if (ats.some(a => /^@(keyframes|-webkit-keyframes|font-face)/.test(a))) return;
    if (ats.some(a => a.startsWith('NESTED-IN'))) { nestedRules.push(rel(abs) + ':' + rule.source.start.line); return; }
    const decls = []; rule.each(d => { if (d.type === 'decl') decls.push({ prop: d.prop.toLowerCase(), value: d.value, important: !!d.important || /!important/i.test(d.value), line: d.source.start.line }); });
    if (!decls.length) return;
    let sels; try { sels = parseSelectors(rule.selector); } catch (e) { sels = []; }
    for (const s of sels) cssRules.push({ file: rel(abs), isModule, line: rule.source.start.line, selector: s.text, ruleSelector: rule.selector.replace(/\s+/g, ' '), parsed: s, media: ats.join(' | '), decls, order: order++ });
  });
}
// custom properties (for resolved display only)
const tokens = {};
for (const r of cssRules) if (!r.media && /^:root$/.test(r.selector)) for (const d of r.decls) if (d.prop.startsWith('--') && !(d.prop in tokens)) tokens[d.prop] = normV(d.value);
const resolveTok = (v, n = 0) => { const m = /^var\((--[\w-]+)\)$/.exec(v || ''); return m && tokens[m[1]] && n < 4 ? resolveTok(tokens[m[1]], n + 1) : v; };

const clsKey = (r, c) => (r.isModule ? 'mod:' + r.file + ':' + c : c);
const ORD = { yes: 0, maybe: 1, no: 2 };
const worse = (a, b) => (ORD[a] >= ORD[b] ? a : b);
function matchCompound(comp, e, rule) {
  if (e.k === 'unk') return { r: 'maybe', why: e.why };
  if (comp.tag && comp.tag !== e.tag) return { r: 'no' };
  let r = 'yes'; let why = null;
  for (const c of comp.classes) {
    const key = clsKey(rule, c);
    if (e.st.has(key)) continue;
    if (e.cond.has(key) || e.maybe.has(key)) { r = worse(r, 'maybe'); why = 'conditional/prop-propagated ancestor class .' + c; continue; }
    if (e.prefixes && [...e.prefixes].some(x => c.startsWith(x))) { r = worse(r, 'maybe'); why = 'ancestor className has dynamic suffix (.' + c + ' possible)'; continue; }
    if (e.unresolved) { r = worse(r, 'maybe'); why = 'ancestor className unresolved (.' + c + ' possible)'; continue; }
    return { r: 'no' };
  }
  if (comp.ids.length || comp.attrs.length || comp.funcPseudos.length) { r = worse(r, 'maybe'); why = why || 'ancestor id/attr/functional-pseudo unverified'; }
  return { r, why };
}
function matchAncestors(list, entries, rule) { // list: compounds left->right excluding the last; each .comb = combinator to the right
  const whys = new Set();
  const m = (i, start, adj) => {
    if (i < 0) return 'yes';
    if (start >= entries.length && !adj) return 'no';
    let best = 'no';
    const qs = adj ? [start] : Array.from({ length: Math.max(0, entries.length - start) }, (_, k) => start + k);
    for (const q of qs) {
      if (q >= entries.length) continue;
      const mc = matchCompound(list[i], entries[q], rule); if (mc.r === 'no') continue;
      if (mc.why) whys.add(mc.why);
      let sub;
      if (i === 0) sub = 'yes';
      else if (/[+~]/.test(list[i - 1].comb)) { sub = 'maybe'; whys.add('sibling combinator unverified'); }
      else sub = m(i - 1, q + 1, list[i - 1].comb === '>');
      const comb = worse(mc.r, sub);
      if (comb === 'yes') return 'yes';
      if (comb === 'maybe') best = 'maybe';
    }
    return best;
  };
  const adjFirst = list.length ? list[list.length - 1].comb === '>' : false;
  if (list.length && /[+~]/.test(list[list.length - 1].comb)) return { r: 'maybe', whys: new Set(['sibling combinator unverified']) };
  const r = m(list.length - 1, 0, adjFirst);
  return { r, whys };
}
const stateOf = (parsed, rule) => {
  const all = parsed.compounds.flatMap(c => [...c.pseudos, ...c.pseudoEls]);
  const last = parsed.compounds[parsed.compounds.length - 1];
  const lastS = [...last.pseudos, ...last.pseudoEls].join('');
  const ancS = parsed.compounds.slice(0, -1).flatMap(c => c.pseudos).join('');
  return [lastS ? 'self' + lastS : '', ancS ? 'ancestor' + ancS : '', rule.media ? 'media[' + rule.media + ']' : ''].filter(Boolean).join(' ') || 'base';
};

// sel: {tokens:{st,cond,unresolved}, id, chains:[{entries,closed}], fileFilter}
// returns {matched:[{rule,status,whys,origin}], universal:[...]}
function matchRules(sel, filter) {
  const matched = [];
  for (const rule of cssRules) {
    if (filter && !filter(rule)) continue;
    const p = rule.parsed; const last = p.compounds[p.compounds.length - 1];
    if (p.nested) continue;
    if (last.tag && last.tag !== 'select') continue;
    if (!last.tag && !last.classes.length && !last.ids.length && !last.attrs.length && !last.funcPseudos.length) { continue; } // universal handled elsewhere
    let status = 'definite'; const whys = new Set(); let ok = true;
    for (const c of last.classes) {
      const key = clsKey(rule, c);
      if (sel.tokens.st.has(key)) continue;
      if (sel.tokens.cond.has(key)) { status = 'conditional-class'; whys.add('own className contains .' + c + ' only conditionally'); continue; }
      if (sel.tokens.prefixes && [...sel.tokens.prefixes].some(x => c.startsWith(x))) { status = 'unconfirmed'; whys.add('own className dynamic suffix (.' + c + ' possible)'); continue; }
      if (sel.tokens.unresolved && !rule.isModule) { status = 'unconfirmed'; whys.add('own className unresolved/forwarded (.' + c + ' possible)'); continue; }
      ok = false; break;
    }
    if (!ok) continue;
    if (last.ids.length) {
      if (sel.idLit === undefined && !sel.spread) continue;
      if (sel.idLit !== undefined && sel.idLit !== null && !last.ids.every(i => i === sel.idLit)) continue;
      if (sel.idLit === null || sel.spread) { status = 'unconfirmed'; whys.add('id selector #' + last.ids.join('#') + ' vs dynamic/forwarded id'); }
    }
    let attrBad = false;
    for (const a of last.attrs) {
      const nm = (/^\[\s*([\w-]+)/.exec(a) || [])[1]; const hasOp = /[~|^$*]?=/.test(a);
      if (!(sel.attrNames || new Set()).has(nm) && !sel.spread) { attrBad = true; break; }
      if (hasOp || sel.spread) { if (status === 'definite') status = 'unconfirmed'; whys.add('attribute selector ' + a + ' value/forwarded attr unverified'); }
    }
    if (attrBad) continue;
    if (last.funcPseudos.length) { if (status === 'definite') status = 'unconfirmed'; whys.add('functional pseudo ' + last.funcPseudos.join('') + ' unverified'); }
    const anc = p.compounds.slice(0, -1);
    if (anc.length) {
      // alternatives across chains
      let results = sel.chains.map(ch => matchAncestors(anc, ch.entries, rule));
      const allNo = results.every(r => r.r === 'no'), allYes = results.every(r => r.r === 'yes');
      if (allNo) continue;
      if (!allYes) { status = 'unconfirmed'; results.forEach(r => r.whys.forEach(w => whys.add(w))); if (results.some(r => r.r === 'yes') && results.some(r => r.r === 'no')) whys.add('ancestor match differs between usage chains'); }
    }
    matched.push({ rule, status, whys: [...whys], origin: last.classes.length ? 'own-class' + (anc.length ? '+ancestor' : '') : 'tag-select' + (anc.length ? '+ancestor' : ''), state: stateOf(p, rule) });
  }
  return matched;
}
const universalRules = cssRules.filter(r => { const l = r.parsed.compounds[r.parsed.compounds.length - 1]; return !r.parsed.nested && !l.tag && !l.classes.length && !l.ids.length && !l.attrs.length && !l.funcPseudos.length && (l.universal || l.pseudos.length || l.pseudoEls.length) && !(l.pseudos.length === 1 && l.pseudos[0] === ':root' && !l.universal); });
const universalBase = universalRules.filter(r => r.parsed.compounds.length === 1 && r.parsed.compounds[0].universal && !r.parsed.compounds[0].pseudos.length && !r.parsed.compounds[0].pseudoEls.length && !r.media);

// effective base-state declarations (longhands)
function effective(matched, bucket = 'base', extra = []) {
  const items = []; // {prop, value, important, spec, order, file, line, ruleLine, selector}
  for (const m of matched) {
    if (m.state !== bucket) continue; const sp3 = m.rule.parsed.spec;
    for (const d of m.rule.decls) for (const [lp, lv] of expandDecl(d.prop, d.value)) items.push({ prop: lp, value: lv, important: d.important, spec: sp3, order: m.rule.order, file: m.rule.file, line: d.line, selector: m.rule.selector, srcProp: d.prop, status: m.status, universal: m.universal === true });
  }
  for (const x of extra) items.push(Object.assign({ spec: [1, 0, 0, 0], order: 1e9, important: false, file: 'inline', line: 0, selector: 'style={}', status: 'definite' }, x, { spec: [9, 9, 9] }));
  const by = {};
  for (const it of items) (by[it.prop] = by[it.prop] || []).push(it);
  const cmp = (a, b) => (a.important - b.important) || (a.spec[0] - b.spec[0]) || (a.spec[1] - b.spec[1]) || (a.spec[2] - b.spec[2]) || (a.file === b.file ? a.order - b.order : 0);
  const eff = {};
  for (const [prop, arr] of Object.entries(by)) {
    const sorted = arr.slice().sort(cmp); const top = sorted[sorted.length - 1]; const second = sorted[sorted.length - 2];
    const ambiguous = !!second && second.file !== top.file && second.important === top.important && second.spec.join() === top.spec.join() && normV(second.value) !== normV(top.value);
    eff[prop] = { universal: top.universal === true, value: normV(top.value), from: top.file + ':' + top.line, selector: top.selector, ambiguous, conditional: top.status !== 'definite', overridden: sorted.slice(0, -1).map(x => x.file + ':' + x.line + ' ' + x.value) };
  }
  return eff;
}

module.exports = { universalBase, cssRules, nestedRules, tokens, resolveTok, matchRules, effective, universalRules, kindOf, LAYOUT_PROPS, expandDecl, normV, splitTop, stateOf };
