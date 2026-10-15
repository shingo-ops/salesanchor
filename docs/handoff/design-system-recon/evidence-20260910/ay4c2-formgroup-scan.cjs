// AY-4c-2a §5-2: .form-group を祖先に持つ <Checkbox / <CheckboxControl の全数。使い方: node ay4c2-formgroup-scan.cjs > out.txt
const path = require("path"), fs = require("fs");
const FRONT = path.resolve(__dirname, "../../../../frontend");
const ts = require(path.join(FRONT, "node_modules/typescript"));
const SRC = path.join(FRONT, "src");
const files = [];
(function walk(d) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p); else if (p.endsWith(".tsx")) files.push(p); } })(SRC);
const rel = (p) => "frontend/src/" + path.relative(SRC, p);
const parsed = files.map((f) => { const text = fs.readFileSync(f, "utf8"); return { f, text, sf: ts.createSourceFile(f, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX) }; });
const line = (sf, n) => sf.getLineAndCharacterOfPosition(n.getStart()).line + 1;
const tagName = (n) => { const t = ts.isJsxElement(n) ? n.openingElement.tagName : n.tagName; return t.getText(); };
const openOf = (n) => (ts.isJsxElement(n) ? n.openingElement : n);
const isJsx = (n) => ts.isJsxElement(n) || ts.isJsxSelfClosingElement(n);
const fgInfo = (n) => { // この要素自身の className が form-group を含むか。dynamic: 文字列で読めない className
  const attrs = openOf(n).attributes.properties.filter((a) => ts.isJsxAttribute(a) && a.name.getText() === "className");
  for (const a of attrs) { if (!a.initializer) continue; const txt = a.initializer.getText(); if (/form-group/.test(txt)) return "yes"; if (ts.isJsxExpression(a.initializer) && a.initializer.expression && !ts.isStringLiteralLike(a.initializer.expression) && !ts.isTemplateExpression(a.initializer.expression)) return "dynamic"; }
  return null;
};
const ancestorsFG = (n) => { let r = { fg: null, dyn: [] }; for (let p = n.parent; p; p = p.parent) { if (isJsx(p)) { const i = fgInfo(p); if (i === "yes" && !r.fg) r.fg = p; if (i === "dynamic") r.dyn.push(p); } } return r; };
const fnLike = (i) => i && (ts.isArrowFunction(i) || ts.isFunctionExpression(i) || (ts.isCallExpression(i) && i.arguments.some((a) => ts.isArrowFunction(a) || ts.isFunctionExpression(a))));
const encl = (n) => { for (let p = n.parent; p; p = p.parent) { if (ts.isFunctionDeclaration(p) && p.name && /^[A-Z]/.test(p.name.text)) return p.name.text; if (ts.isVariableDeclaration(p) && ts.isIdentifier(p.name) && /^[A-Z]/.test(p.name.text) && fnLike(p.initializer)) return p.name.text; if (ts.isClassDeclaration(p) && p.name) return p.name.text; } return null; };
const isTestLike = (f) => /\.(test|stories)\.tsx$/.test(f);
const isMold = (n) => ["Checkbox", "CheckboxControl"].includes(tagName(n));
const out = [];
const uses = (pred, withTests) => { const r = []; for (const P of parsed) if (withTests || !isTestLike(P.f)) (function v(n) { if (isJsx(n) && pred(n, P)) r.push({ P, n }); ts.forEachChild(n, v); })(P.sf); return r; };

out.push("# AY-4c-2a §5-2 .form-group を祖先に持つ金型の全数（TypeScript 構文木。スクリプト: docs/handoff/design-system-recon/evidence-20260910/ay4c2-formgroup-scan.cjs）");
out.push(`# 走査 tsx: ${files.length} ファイル（1 は試験・stories 含む、2 は *.test.tsx・*.stories.tsx を除く本番コードのみ）。.form-group は全て intrinsic 要素の className リテラルで付与（git grep で確認: 58 ファイル、動的付与は 0）。`);
out.push("");
out.push("## 1. 同じファイルの中");
const direct = uses((n) => isMold(n), true);
out.push(`金型の使用 JSX 総数: ${direct.length}（Checkbox ${direct.filter((x) => tagName(x.n) === "Checkbox").length} / CheckboxControl ${direct.filter((x) => tagName(x.n) === "CheckboxControl").length}）、ファイル ${new Set(direct.map((x) => x.P.f)).size}`);
const inFG = [], dynList = [];
for (const { P, n } of direct) { const a = ancestorsFG(n); const loc = `${rel(P.f)}:${line(P.sf, n)} <${tagName(n)}> 祖先 form-group=${a.fg ? rel(P.f) + ":" + line(P.sf, a.fg) : "なし"}`; if (a.fg) inFG.push(loc); if (a.dyn.length) dynList.push(loc + " 動的className祖先=" + a.dyn.map((d) => line(P.sf, d)).join(",")); }
out.push(`form-group を祖先に持つもの: ${inFG.length} 件`); inFG.forEach((l) => out.push("  " + l));
out.push(`祖先に読めない（動的）className がある金型: ${dynList.length} 件`); dynList.forEach((l) => out.push("  " + l));
out.push("");
out.push("## 2. ファイルをまたぐもの（金型を描く部品 -> その部品を使う JSX の祖先に form-group があるか）");
const seen = new Set(), queue = [], chains = [], unresolved = [];
const compOf = (P, n) => encl(n);
for (const { P, n } of direct.filter((x) => !isTestLike(x.P.f))) { const c = compOf(P, n); if (c && !seen.has(c)) { seen.add(c); queue.push({ name: c, chain: [`${c}(${rel(P.f)})`] }); } else if (!c) unresolved.push(`${rel(P.f)}:${line(P.sf, n)} 囲む部品名が取れない`); }
out.push(`金型を直接描く部品（名前）: ${seen.size} 個`);
while (queue.length) {
  const { name, chain } = queue.shift();
  const us = uses((n) => tagName(n) === name);
  // JSX タグ以外の参照（props で渡す・変数に入れる等）を拾う
  let nonJsx = 0, nonJsxLocs = [];
  for (const P of parsed) if (!isTestLike(P.f)) (function v(n) { if (ts.isIdentifier(n) && n.text === name) { const p = n.parent; const inTag = (ts.isJsxOpeningElement(p) || ts.isJsxSelfClosingElement(p) || ts.isJsxClosingElement(p)) && p.tagName === n; const decl = (ts.isFunctionDeclaration(p) || ts.isVariableDeclaration(p) || ts.isClassDeclaration(p)) && p.name === n; const imp = ts.isImportSpecifier(p) || ts.isImportClause(p) || ts.isExportSpecifier(p); const typ = ts.isTypeReferenceNode(p) || ts.isInterfaceDeclaration(p); if (!inTag && !decl && !imp && !typ) { nonJsx++; nonJsxLocs.push(`${rel(P.f)}:${line(P.sf, n)}`); } } ts.forEachChild(n, v); })(P.sf);
  out.push(`  部品 ${name}: JSX 使用 ${us.length} 件、JSX タグ以外の参照 ${nonJsx} 件${nonJsx ? " [" + nonJsxLocs.join(", ") + "]" : ""}`);
  if (nonJsx) unresolved.push(`部品 ${name}: JSX タグ以外の参照 ${nonJsxLocs.join(", ")}`);
  for (const { P, n } of us) {
    const a = ancestorsFG(n); const loc = `${rel(P.f)}:${line(P.sf, n)}`;
    if (a.fg) { chains.push(`${loc} <${name}> -> form-group ${rel(P.f)}:${line(P.sf, a.fg)}  経路: ${chain.join(" <- ")}`); continue; }
    if (a.dyn.length) unresolved.push(`${loc} <${name}> 祖先に動的 className`);
    const c = compOf(P, n);
    out.push(`    使用 ${loc} 囲む部品=${c || "(なし)"} form-group=なし`);
    if (c && !seen.has(c)) { seen.add(c); queue.push({ name: c, chain: [...chain, `${c}(${rel(P.f)})`] }); }
  }
}
out.push("");
out.push(`form-group に当たった（ファイルをまたぐ）経路: ${chains.length} 件`); chains.forEach((l) => out.push("  " + l));
out.push(`たどり切れないもの: ${unresolved.length} 件`); unresolved.forEach((l) => out.push("  " + l));
console.log(out.join("\n"));
