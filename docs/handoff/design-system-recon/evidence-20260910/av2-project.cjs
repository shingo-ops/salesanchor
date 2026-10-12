// AV-2 recon: project model (AST) + JSX ancestor chain resolution. Read-only.
const fs = require('fs'), path = require('path');
const NM = '/Users/tanizawashingo/salesanchor/frontend/node_modules';
const ts = require(NM + '/typescript');
const ROOT = '/private/tmp/claude-501/-Users-tanizawashingo-salesanchor/ead196df-e9c5-4196-8762-cd306d5785d4/scratchpad/av2';
const SRC = path.join(ROOT, 'frontend/src');

const walkDir = (d, pred, acc = []) => { for (const f of fs.readdirSync(d)) { const p = path.join(d, f); fs.statSync(p).isDirectory() ? walkDir(p, pred, acc) : pred(p) && acc.push(p); } return acc; };
const rel = p => path.relative(ROOT, p);
const allTs = walkDir(SRC, p => /\.(tsx|ts)$/.test(p) && !/\.(stories|test)\.(tsx|ts)$/.test(p) && !/\.d\.ts$/.test(p));
const allCss = walkDir(SRC, p => /\.css$/.test(p));

const files = new Map(); // abs -> info
for (const abs of allTs) {
  const src = fs.readFileSync(abs, 'utf8');
  const sf = ts.createSourceFile(abs, src, ts.ScriptTarget.Latest, true, abs.endsWith('x') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  files.set(abs, { abs, rel: rel(abs), src, sf, imports: new Map(), cssModules: new Map(), exports: new Map(), stars: [], defs: new Map() });
}
const exts = ['.tsx', '.ts', '/index.tsx', '/index.ts'];
function resolveSpec(fromAbs, spec) {
  if (!spec.startsWith('.')) return null;
  const base = path.resolve(path.dirname(fromAbs), spec);
  if (/\.css$/.test(spec)) return fs.existsSync(base) ? base : null;
  for (const e of exts) if (files.has(base + e)) return base + e;
  if (files.has(base)) return base;
  return null;
}
const txt = (n, sf) => n.getText(sf);
function fnNameOf(fn) {
  if (fn.name && ts.isIdentifier(fn.name)) return fn.name.text;
  if (ts.isFunctionDeclaration(fn) && fn.modifiers && fn.modifiers.some(m => m.kind === ts.SyntaxKind.DefaultKeyword)) return '__default';
  let p = fn.parent;
  while (p && (ts.isParenthesizedExpression(p) || ts.isAsExpression(p))) p = p.parent;
  if (p && ts.isCallExpression(p)) { // memo/forwardRef(...)
    const c = p.expression.getText(); if (/(^|\.)(memo|forwardRef)$/.test(c)) { p = p.parent; while (p && (ts.isParenthesizedExpression(p) || ts.isCallExpression(p) || ts.isAsExpression(p))) p = p.parent; } else return null;
  }
  if (p && ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text;
  if (p && ts.isExportAssignment(p)) return '__default';
  return null;
}
const isFn = n => ts.isFunctionDeclaration(n) || ts.isFunctionExpression(n) || ts.isArrowFunction(n) || ts.isMethodDeclaration(n);

for (const fi of files.values()) {
  const { sf } = fi;
  const visit = n => {
    if (ts.isImportDeclaration(n) && ts.isStringLiteral(n.moduleSpecifier)) {
      const spec = n.moduleSpecifier.text; const tgt = resolveSpec(fi.abs, spec);
      const ic = n.importClause;
      if (ic && tgt) {
        if (/\.css$/.test(spec)) { if (ic.name) fi.cssModules.set(ic.name.text, tgt); }
        else {
          if (ic.name) fi.imports.set(ic.name.text, { file: tgt, name: 'default' });
          if (ic.namedBindings) {
            if (ts.isNamedImports(ic.namedBindings)) ic.namedBindings.elements.forEach(e => fi.imports.set(e.name.text, { file: tgt, name: (e.propertyName || e.name).text }));
            else fi.imports.set(ic.namedBindings.name.text, { file: tgt, name: '*' });
          }
        }
      }
    }
    if (ts.isExportDeclaration(n)) {
      const tgt = n.moduleSpecifier && ts.isStringLiteral(n.moduleSpecifier) ? resolveSpec(fi.abs, n.moduleSpecifier.text) : null;
      if (n.exportClause && ts.isNamedExports(n.exportClause)) n.exportClause.elements.forEach(e => fi.exports.set(e.name.text, tgt ? { kind: 'from', file: tgt, name: (e.propertyName || e.name).text } : { kind: 'local', local: (e.propertyName || e.name).text }));
      else if (!n.exportClause && tgt) fi.stars.push(tgt);
    }
    if (ts.isExportAssignment(n) && ts.isIdentifier(n.expression)) fi.exports.set('default', { kind: 'local', local: n.expression.text });
    const hasExport = n.modifiers && n.modifiers.some(m => m.kind === ts.SyntaxKind.ExportKeyword);
    const hasDefault = n.modifiers && n.modifiers.some(m => m.kind === ts.SyntaxKind.DefaultKeyword);
    if (ts.isFunctionDeclaration(n) && (n.name || hasDefault)) {
      const nm = n.name ? n.name.text : '__default'; fi.defs.set(nm, n);
      if (hasExport) fi.exports.set(hasDefault ? 'default' : nm, { kind: 'local', local: nm });
    }
    if (ts.isVariableStatement(n)) for (const d of n.declarationList.declarations) if (ts.isIdentifier(d.name)) {
      if (hasExport) fi.exports.set(d.name.text, { kind: 'local', local: d.name.text });
      if (d.initializer) { let init = d.initializer; const cands = [init]; if (ts.isCallExpression(init)) init.arguments.forEach(a => cands.push(a)); const f = cands.find(isFn); if (f) fi.defs.set(d.name.text, f); }
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
}
function resolveExport(file, name, seen = new Set()) {
  const key = file + '#' + name; if (seen.has(key)) return null; seen.add(key);
  const fi = files.get(file); if (!fi) return null;
  const e = fi.exports.get(name);
  if (e) { if (e.kind === 'local') { const im = fi.imports.get(e.local); if (im && !fi.defs.has(e.local) && im.name !== '*') return resolveExport(im.file, im.name, seen); return { file, local: e.local }; } return resolveExport(e.file, e.name, seen); }
  if (name !== 'default') for (const s of fi.stars) { const r = resolveExport(s, name, seen); if (r) return r; }
  return null;
}

// ---------- className token extraction ----------
const split = s => s.split(/\s+/).filter(Boolean);
function emptyTok() { return { st: new Set(), cond: new Set(), unresolved: false, other: false, prefixes: new Set() }; }
function merge(a, b, asCond) { for (const t of b.st) (asCond ? a.cond : a.st).add(t); for (const t of b.cond) a.cond.add(t); if (b.unresolved) a.unresolved = true; if (b.other) a.other = true; b.prefixes.forEach(x => a.prefixes.add(x)); }
function possibleStrings(fi, e, d) {
  if (d > 4) return null;
  if (ts.isStringLiteral(e) || ts.isNoSubstitutionTemplateLiteral(e)) return [e.text];
  if (ts.isParenthesizedExpression(e)) return possibleStrings(fi, e.expression, d + 1);
  if (ts.isConditionalExpression(e)) { const a = possibleStrings(fi, e.whenTrue, d + 1), b = possibleStrings(fi, e.whenFalse, d + 1); return a && b ? a.concat(b) : null; }
  return null;
}
function classTokens(fi, expr, depth = 0) {
  const out = emptyTok(); if (!expr || depth > 6) { out.unresolved = out.other = true; return out; }
  const { sf } = fi;
  if (ts.isJsxExpression(expr)) return expr.expression ? classTokens(fi, expr.expression, depth) : out;
  if (ts.isStringLiteral(expr) || ts.isNoSubstitutionTemplateLiteral(expr)) { split(expr.text).forEach(t => out.st.add(t)); return out; }
  if (ts.isParenthesizedExpression(expr) || ts.isAsExpression(expr) || ts.isNonNullExpression(expr)) return classTokens(fi, expr.expression, depth);
  if (ts.isTemplateExpression(expr)) {
    const pieces = [expr.head.text, ...expr.templateSpans.map(s => s.literal.text)];
    const poss = expr.templateSpans.map(sp => possibleStrings(fi, sp.expression, 0));
    const cleanStart = i => !poss[i] || poss[i].every(x => x === '' || /^\s/.test(x)); // substitution i begins with ws/empty
    const cleanEnd = i => !poss[i] ? false : poss[i].every(x => x === '' || /\s$/.test(x));
    pieces.forEach((p, i) => {
      const toks = split(p);
      const touchPrev = i > 0 && p.length && !/^\s/.test(p) && !cleanEnd(i - 1);
      const touchNext = i < pieces.length - 1 && p.length && !/\s$/.test(p) && !(poss[i] && poss[i].every(x => x === '' || /^\s/.test(x)));
      toks.forEach((t, k) => {
        const headPartial = k === 0 && touchPrev; const tailPartial = k === toks.length - 1 && touchNext;
        if (headPartial) { out.unresolved = out.other = true; if (tailPartial) {} }
        else if (tailPartial) out.prefixes.add(t);
        else out.st.add(t);
      });
    });
    expr.templateSpans.forEach((sp, i) => { const iso = (pieces[i] === '' || /\s$/.test(pieces[i])) && (pieces[i + 1] === '' || /^\s/.test(pieces[i + 1])); if (poss[i] || iso) merge(out, classTokens(fi, sp.expression, depth + 1), true); });
    return out;
  }
  if (ts.isConditionalExpression(expr)) { merge(out, classTokens(fi, expr.whenTrue, depth + 1), true); merge(out, classTokens(fi, expr.whenFalse, depth + 1), true); return out; }
  if (ts.isBinaryExpression(expr)) {
    const op = expr.operatorToken.kind;
    if (op === ts.SyntaxKind.AmpersandAmpersandToken) { merge(out, classTokens(fi, expr.right, depth + 1), true); return out; }
    if (op === ts.SyntaxKind.BarBarToken || op === ts.SyntaxKind.QuestionQuestionToken) { merge(out, classTokens(fi, expr.left, depth + 1), true); merge(out, classTokens(fi, expr.right, depth + 1), true); return out; }
    if (op === ts.SyntaxKind.PlusToken) { merge(out, classTokens(fi, expr.left, depth + 1), false); merge(out, classTokens(fi, expr.right, depth + 1), false); return out; }
    out.unresolved = out.other = true; return out;
  }
  if (ts.isArrayLiteralExpression(expr)) { expr.elements.forEach(e => merge(out, classTokens(fi, e, depth + 1), false)); return out; }
  if (ts.isCallExpression(expr)) {
    const callee = expr.expression.getText(sf);
    if (/(^|\.)(clsx|cn|classNames|cx|classnames)$/.test(callee)) { expr.arguments.forEach(a => merge(out, classTokens(fi, a, depth + 1), false)); return out; }
    if (ts.isPropertyAccessExpression(expr.expression) && expr.expression.name.text === 'join') {
      let r = expr.expression.expression;
      while (ts.isCallExpression(r) && ts.isPropertyAccessExpression(r.expression) && /^(filter|map|flat)$/.test(r.expression.name.text)) r = r.expression.expression;
      return classTokens(fi, r, depth + 1);
    }
    if (ts.isPropertyAccessExpression(expr.expression) && /^(trim)$/.test(expr.expression.name.text)) return classTokens(fi, expr.expression.expression, depth + 1);
    out.unresolved = out.other = true; return out;
  }
  if (ts.isObjectLiteralExpression(expr)) { expr.properties.forEach(p => { if (ts.isPropertyAssignment(p)) { const k = p.name.getText(sf).replace(/^["'`]|["'`]$/g, ''); split(k).forEach(t => out.cond.add(t)); } else out.unresolved = out.other = true; }); return out; }
  if (ts.isPropertyAccessExpression(expr) || ts.isElementAccessExpression(expr)) {
    const base = expr.expression; const nm = ts.isPropertyAccessExpression(expr) ? expr.name.text : (ts.isStringLiteral(expr.argumentExpression) ? expr.argumentExpression.text : null);
    if (ts.isIdentifier(base) && fi.cssModules.has(base.text) && nm) { out.st.add('mod:' + rel(fi.cssModules.get(base.text)) + ':' + nm); return out; }
    out.unresolved = true; if (!(nm === 'className' && ts.isIdentifier(base) && base.text === 'props')) out.other = true; return out;
  }
  if (ts.isIdentifier(expr)) {
    if (expr.text === 'undefined') return out;
    let found = null;
    const v = n => { if (found) return; if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && n.name.text === expr.text && n.initializer && ts.isVariableDeclarationList(n.parent) && (n.parent.flags & ts.NodeFlags.Const)) found = n.initializer; ts.forEachChild(n, v); };
    v(sf);
    if (found) return classTokens(fi, found, depth + 1);
    out.unresolved = true; if (expr.text !== 'className') out.other = true; return out;
  }
  if (expr.kind === ts.SyntaxKind.NullKeyword || expr.kind === ts.SyntaxKind.FalseKeyword) return out;
  out.unresolved = out.other = true; return out;
}
const jsxAttr = (el, name) => { const op = ts.isJsxElement(el) ? el.openingElement : el; return op.attributes.properties.find(a => ts.isJsxAttribute(a) && a.name.getText() === name); };
const opening = el => ts.isJsxElement(el) ? el.openingElement : el;
const tagText = el => opening(el).tagName.getText();
const isJsx = n => ts.isJsxElement(n) || ts.isJsxSelfClosingElement(n);
const hasSpread = el => opening(el).attributes.properties.some(a => ts.isJsxSpreadAttribute(a));

// ---------- chains ----------
const TRANSPARENT = new Set(['Routes', 'Route', 'Suspense', 'BrowserRouter', 'Router', 'HashRouter', 'StrictMode', 'Fragment', 'Navigate', 'QueryClientProvider', 'Trans']);
const entryDom = (fi, el) => {
  const a = jsxAttr(el, 'className'); const t = a && a.initializer ? classTokens(fi, a.initializer) : emptyTok();
  return { k: 'dom', tag: tagText(el), st: t.st, cond: t.cond, maybe: new Set(), unresolved: t.unresolved && t.other, propFwd: t.unresolved && !t.other, prefixes: t.prefixes, spread: hasSpread(el), loc: fi.rel + ':' + (fi.sf.getLineAndCharacterOfPosition(el.getStart(fi.sf)).line + 1) };
};
const unk = why => ({ k: 'unk', why });
function defOf(fi, T) {
  if (T.includes('.')) return null;
  if (fi.defs.has(T) && !fi.imports.has(T)) return { file: fi.abs, name: T, node: fi.defs.get(T) };
  const im = fi.imports.get(T); if (!im) return null;
  const r = resolveExport(im.file, im.name); if (!r) return null;
  const tfi = files.get(r.file); const node = tfi && tfi.defs.get(r.local); return node ? { file: r.file, name: r.local, node } : null;
}
function findAll(node, pred, acc = []) { const v = n => { if (pred(n)) acc.push(n); ts.forEachChild(n, v); }; v(node); return acc; }
const childrenPlacements = defNode => findAll(defNode, n => ts.isJsxExpression(n) && n.expression && ((ts.isIdentifier(n.expression) && n.expression.text === 'children') || (ts.isPropertyAccessExpression(n.expression) && n.expression.name.text === 'children')));
const outletPlacements = root => findAll(root, n => isJsx(n) && tagText(n) === 'Outlet');
const callSites = (fi, name) => findAll(fi.sf, n => ts.isCallExpression(n) && ts.isIdentifier(n.expression) && n.expression.text === name);
const MAXALT = 24;
function applyUsageClass(ent, ufi, usageEl) {
  const targets = ent.filter(e => e.k === 'dom' && e.propFwd); if (!targets.length) return ent;
  const cls = jsxAttr(usageEl, 'className'); const ct = cls && cls.initializer ? classTokens(ufi, cls.initializer) : null;
  return ent.map(e => { if (!(e.k === 'dom' && e.propFwd)) return e; const c = Object.assign({}, e, { st: new Set(e.st), cond: new Set(e.cond), maybe: new Set(e.maybe), propFwd: false });
    if (ct) { ct.st.forEach(t => c.st.add(t)); ct.cond.forEach(t => c.cond.add(t)); if (ct.unresolved) c.unresolved = true; } return c; });
}

function outletFrom(fi, root, stopAt, depth, lvl) {
  // alternative entry arrays from Outlet position up to root (stopAt) / def boundary
  const res = []; if (lvl > 5) return res;
  for (const o of outletPlacements(root)) for (const a of walk(fi, o, depth + 1, stopAt ? { stopAt } : {})) res.push(a.entries);
  const comps = findAll(root, n => isJsx(n) && /^[A-Z]/.test(tagText(n)) && tagText(n) !== 'Outlet' && n !== root || (n === root && isJsx(n) && /^[A-Z]/.test(tagText(n)) && tagText(n) !== 'Outlet'));
  for (const u of comps) {
    const d = defOf(fi, tagText(u).replace(/^React\./, '')); if (!d) continue;
    const sub = outletFrom(files.get(d.file), d.node, null, depth + 1, lvl + 1); if (!sub.length) continue;
    const up = walk(fi, u, depth + 1, stopAt ? { stopAt } : {});
    for (const S of sub) for (const U of up) res.push(applyUsageClass(S, fi, u).concat(U.entries));
  }
  return res.slice(0, MAXALT);
}
function walk(fi, node, depth, opt = {}) {
  // returns [{entries, top}]
  if (depth > 10) return [{ entries: [unk('depth limit')], top: { kind: 'unknown' } }];
  let partial = [{ entries: [] }];
  let prev = node; let lastAttr = null;
  for (let p = node.parent; p; prev = p, p = p.parent) {
    if (ts.isJsxAttribute(p)) lastAttr = p;
    if (isJsx(p)) {
      const via = ts.isJsxSelfClosingElement(p) || (ts.isJsxElement(p) && prev === p.openingElement) ? 'attr' : 'children';
      const T = tagText(p).replace(/^React\./, '');
      let adds = null; // array of alternative entry arrays
      const expand = (d, placements) => {
        const out = []; const dfi = files.get(d.file);
        for (const q of placements) for (const a of walk(dfi, q, depth + 1)) {
          let ent = a.entries.slice();
          if (a.top.kind === 'component' && a.top.name !== d.name) ent = ent.concat([unk('placement inside inner component ' + a.top.name + ' of <' + T + '>')]);
          out.push(applyUsageClass(ent, fi, p));
        }
        return out;
      };
      if (/^[a-z]/.test(T)) adds = via === 'attr' ? [[unk('element in attr of <' + T + '>')]] : [[entryDom(fi, p)]];
      else if (T === 'Route') {
        if (via === 'attr') adds = [[]];
        else {
          const ea = jsxAttr(p, 'element'); const E = ea && ea.initializer && ts.isJsxExpression(ea.initializer) ? ea.initializer.expression : null;
          if (!E || !isJsx(E)) adds = [[]];
          else { const r = outletFrom(fi, E, E, depth + 1, 0); adds = r.length ? r : [[unk('layout route element without resolvable Outlet: ' + tagText(E))]]; }
        }
      } else if (TRANSPARENT.has(T) || T.endsWith('.Provider')) adds = [[]];
      else if (T === 'Link' || T === 'NavLink') adds = via === 'attr' ? [[unk('element in attr of ' + T)]] : [[Object.assign(entryDom(fi, p), { tag: 'a' })]];
      else if (via === 'attr') {
        const d = defOf(fi, T); const an = lastAttr ? lastAttr.name.getText() : null;
        const pls = d && an ? findAll(d.node, n => ts.isJsxExpression(n) && n.expression && ((ts.isIdentifier(n.expression) && n.expression.text === an) || (ts.isPropertyAccessExpression(n.expression) && n.expression.name.text === an))) : [];
        adds = pls.length ? expand(d, pls) : [[unk('element passed as prop ' + an + ' of <' + T + '> (placement not resolved)')]];
      } else {
        const d = defOf(fi, T);
        if (!d) adds = [[unk('external/unresolved component <' + T + '>')]];
        else { const pls = childrenPlacements(d.node); adds = pls.length ? expand(d, pls) : [[unk('<' + T + '> has no children placement')]]; }
      }
      const next = []; for (const pa of partial) for (const ad of adds) next.push({ entries: pa.entries.concat(ad) });
      partial = next.length > MAXALT ? [{ entries: [unk('too many alternatives')] }] : next;
      if (opt.stopAt && p === opt.stopAt) return partial.map(a => ({ entries: a.entries, top: { kind: 'stopped' } }));
      continue;
    }
    if (isFn(p)) {
      const nm = fnNameOf(p);
      if (!nm) continue; // inline callback: keep climbing
      if (/^[A-Z_]/.test(nm)) return partial.map(a => ({ entries: a.entries, top: { kind: 'component', file: fi.abs, name: nm } }));
      // lowercase helper
      const calls = callSites(fi, nm); if (!calls.length) return partial.map(a => ({ entries: a.entries.concat([unk('helper ' + nm + ' has no call site')]), top: { kind: 'unknown' } }));
      const res = []; for (const c of calls) for (const sub of walk(fi, c, depth + 1)) for (const pa of partial) res.push({ entries: pa.entries.concat(sub.entries), top: sub.top });
      return res.slice(0, MAXALT);
    }
  }
  return partial.map(a => ({ entries: a.entries, top: { kind: 'file' } }));
}
function usagesOf(file, name) {
  const out = []; let nonJsx = 0;
  const isDefault = (() => { const e = files.get(file).exports.get('default'); return e && e.kind === 'local' && e.local === name; })();
  for (const fi of files.values()) {
    const locals = new Map(); // local ident -> true
    if (fi.abs === file) locals.set(name, true);
    for (const [loc, im] of fi.imports) { if (im.name === '*') continue; const r = resolveExport(im.file, im.name); if (r && r.file === file && r.local === name) locals.set(loc, true); }
    const nsLocals = [...fi.imports].filter(([, im]) => im.name === '*').map(([l, im]) => ({ l, im }));
    if (!locals.size && !nsLocals.length) continue;
    const v = n => {
      if (isJsx(n)) {
        const T = tagText(n);
        if (locals.has(T)) out.push({ file: fi.abs, node: n });
        else if (T.includes('.')) { const [ns, mem] = T.split('.'); const nl = nsLocals.find(x => x.l === ns); if (nl) { const r = resolveExport(nl.im.file, mem); if (r && r.file === file && r.local === name) out.push({ file: fi.abs, node: n }); } }
      } else if (ts.isIdentifier(n) && locals.has(n.text)) {
        const p = n.parent;
        const isTag = p && ((ts.isJsxOpeningElement(p) || ts.isJsxClosingElement(p) || ts.isJsxSelfClosingElement(p)) && p.tagName === n);
        const isDecl = p && ((ts.isFunctionDeclaration(p) || ts.isVariableDeclaration(p)) && p.name === n);
        const isSpec = p && (ts.isImportSpecifier(p) || ts.isImportClause(p) || ts.isExportSpecifier(p) || ts.isNamespaceImport(p) || ts.isExportAssignment(p));
        if (!isTag && !isDecl && !isSpec) nonJsx++;
      }
      ts.forEachChild(n, v);
    };
    v(fi.sf);
  }
  return { usages: out, nonJsx };
}
const usageCache = new Map();
const usageOf = (file, name) => { const k = file + '#' + name; if (!usageCache.has(k)) usageCache.set(k, usagesOf(file, name)); return usageCache.get(k); };

function full(fi, node, depth, stack = []) {
  const alts = walk(fi, node, depth); const res = [];
  for (const a of alts) {
    if (a.top.kind === 'file') { res.push({ entries: a.entries, closed: true }); continue; }
    if (a.top.kind === 'stopped') { res.push({ entries: a.entries, closed: true }); continue; }
    if (a.top.kind !== 'component') { res.push({ entries: a.entries.concat(a.entries.some(e => e.k === 'unk') ? [] : [unk('unresolved top')]), closed: false }); continue; }
    const key = a.top.file + '#' + a.top.name;
    if (stack.includes(key) || depth > 10) { res.push({ entries: a.entries.concat([unk('recursion/depth at ' + a.top.name)]), closed: false }); continue; }
    const { usages, nonJsx } = usageOf(a.top.file, a.top.name);
    if (!usages.length) res.push({ entries: a.entries.concat([unk('no JSX usage found for ' + a.top.name + ' (' + files.get(a.top.file).rel + ')')]), closed: false });
    for (const u of usages) {
      const ufi = files.get(u.file);
      const base = applyUsageClass(a.entries, ufi, u.node);
      for (const sub of full(ufi, u.node, depth + 1, stack.concat([key]))) res.push({ entries: base.concat(sub.entries), closed: sub.closed });
      if (res.length > 200) break;
    }
    if (nonJsx) res.push({ entries: a.entries.concat([unk(a.top.name + ' referenced outside JSX tag ' + nonJsx + ' time(s)')]), closed: false });
    if (res.length > 200) { res.length = 200; res.push({ entries: [unk('too many usage chains')], closed: false }); }
  }
  return res;
}
module.exports = { ts, files, ROOT, SRC, rel, allCss, classTokens, full, walk, isJsx, tagText, jsxAttr, opening, hasSpread, emptyTok, split, unk, fnNameOf, resolveExport, usageOf };
