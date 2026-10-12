// AY-2b: .form-group の内側（JSX 部分木）に置かれる部品を再帰的にたどり、競合規則の祖先クラスを持つ描画元がそこに到達しうるかを調べる。
// 使い方: node ay2b-nontext-reach.cjs <competing.json> <出力md>
const fs = require("fs"), path = require("path");
const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const SRC = path.join(ROOT, "frontend/src");
const comp = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const CLS = new Set(); for (const r of comp.inRange) { if (/^\.form-group input\[type=/.test(r.selector)) continue; for (const part of r.selector.split(/\s*[>+~ ]\s*/).slice(0, -1)) for (const m of part.matchAll(/\.([A-Za-z0-9_-]+)/g)) CLS.add(m[1]); }
const files = []; (function walk(d) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p); else if (/\.(tsx|ts)$/.test(e.name) && !/\.(test|stories)\.(tsx|ts)$/.test(e.name) && !p.includes("__tests__")) files.push(p); } })(SRC);
const resolve = (from, spec) => { if (!spec.startsWith(".")) return []; const base = path.resolve(path.dirname(from), spec); const c = [base + ".tsx", base + ".ts", path.join(base, "index.tsx"), path.join(base, "index.ts")]; return c.filter((x) => fs.existsSync(x)); };
const info = new Map(); // file -> {imports: Map(name->[files]), tags:Set, fgTags:Set, classes:Set, nonText:boolean, reexports:[files]}
for (const f of files) {
  const text = fs.readFileSync(f, "utf8"); const sf = ts.createSourceFile(f, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const imports = new Map(), reexports = [], tags = new Set(), fgTags = new Set(), classes = new Set(); let nonText = false;
  sf.forEachChild((n) => {
    if (ts.isImportDeclaration(n) && ts.isStringLiteral(n.moduleSpecifier)) { const rs = resolve(f, n.moduleSpecifier.text); const cl = n.importClause; if (cl) { if (cl.name) imports.set(cl.name.text, rs); if (cl.namedBindings && ts.isNamedImports(cl.namedBindings)) for (const e of cl.namedBindings.elements) imports.set(e.name.text, rs); } }
    if (ts.isExportDeclaration(n) && n.moduleSpecifier && ts.isStringLiteral(n.moduleSpecifier)) reexports.push(...resolve(f, n.moduleSpecifier.text));
  });
  const visit = (n, inFG) => {
    let fg = inFG;
    if (ts.isJsxElement(n) || ts.isJsxSelfClosingElement(n)) {
      const o = ts.isJsxElement(n) ? n.openingElement : n; const tag = o.tagName.getText(sf);
      let cls = ""; let type = null; for (const a of o.attributes.properties) if (ts.isJsxAttribute(a)) { const nm = a.name.getText(sf); const v = a.initializer ? a.initializer.getText(sf) : ""; if (nm === "className") cls = v; if (nm === "type") type = v.replace(/["'{}]/g, ""); }
      if (/^[A-Z]/.test(tag)) { tags.add(tag.split(".")[0]); if (inFG) fgTags.add(tag.split(".")[0]); }
      for (const c of CLS) if (new RegExp("(^|[^A-Za-z0-9_-])" + c + "([^A-Za-z0-9_-]|$)").test(cls)) classes.add(c);
      if (tag === "input" && ["checkbox", "radio", "range", "file"].includes(type)) nonText = true;
      if (/(^|[^A-Za-z0-9_-])form-group([^A-Za-z0-9_-]|$)/.test(cls)) fg = true;
    }
    ts.forEachChild(n, (c) => visit(c, fg));
  };
  visit(sf, false);
  info.set(f, { imports, reexports, tags, fgTags, classes, nonText });
}
const expand = (fs0) => { const out = new Set(); const st = [...fs0]; while (st.length) { const x = st.pop(); if (out.has(x)) continue; out.add(x); const i = info.get(x); if (i) for (const r of i.reexports) st.push(r); } return out; };
const filesOf = (f, tag) => { const i = info.get(f); return i && i.imports.has(tag) ? [...expand(i.imports.get(tag))] : []; };
// 起点: .form-group の部分木に出る部品
const reached = new Map(); // file -> via
const queue = [];
for (const [f, i] of info) for (const t of i.fgTags) for (const g of filesOf(f, t)) if (!reached.has(g)) { reached.set(g, `${path.relative(ROOT, f)} の form-group 内 <${t}>`); queue.push(g); }
while (queue.length) { const f = queue.shift(); const i = info.get(f); if (!i) continue; for (const t of i.tags) for (const g of filesOf(f, t)) if (!reached.has(g)) { reached.set(g, `${path.relative(ROOT, f)} <${t}> ← ${reached.get(f)}`); queue.push(g); } }
const hit = [...reached.keys()].filter((f) => info.get(f).classes.size && info.get(f).nonText);
const hitCls = [...reached.keys()].filter((f) => info.get(f).classes.size);
const hitNon = [...reached.keys()].filter((f) => info.get(f).nonText);
let md = `# 非 text input の競合クラスが .form-group の内側に到達しうるか（部品経由、再帰）\n\n手法: frontend/src の非テスト TS/TSX ${files.length} ファイルを AST で解析。(1) JSX の .form-group 要素の部分木に現れる部品タグを起点に、(2) その部品ファイルが描画する部品タグを再帰的にたどり（相対 import と barrel の re-export を解決）、(3) 到達した部品ファイル ${reached.size} 件のうち、競合規則の祖先クラス（${[...CLS].join(", ")}）を className に持つもの・checkbox/radio/range/file の input を持つものを抽出。\n\n## 結果\n\n- .form-group の内側に到達しうる部品ファイル: ${reached.size}\n- そのうち競合クラスを className に持つ: ${hitCls.length}\n- そのうち非 text の input を持つ: ${hitNon.length}\n- 両方を持つ（競合クラスと非 text input が同じ部品ファイルにある）: ${hit.length}\n\n`;
const sec = (title, arr) => { md += `### ${title}\n\n`; if (!arr.length) md += "なし\n\n"; else { md += "| ファイル | 競合クラス | 非 text input | 到達経路 |\n|---|---|---|---|\n"; for (const f of arr) md += `| ${path.relative(ROOT, f)} | ${[...info.get(f).classes].join(", ") || "-"} | ${info.get(f).nonText ? "あり" : "-"} | ${reached.get(f)} |\n`; md += "\n"; } };
sec("競合クラスを持つ到達ファイル", hitCls); sec("非 text input を持つ到達ファイル", hitNon);
fs.writeFileSync(process.argv[3], md); console.log(JSON.stringify({ files: files.length, reached: reached.size, hitCls: hitCls.length, hitNon: hitNon.length, both: hit.length }));
