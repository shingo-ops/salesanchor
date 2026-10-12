// AY-2b: 非 text input に当たりうる競合規則（ay2b-nontext-competing.json）の祖先クラスが、.form-group と同じ input の祖先に並ぶ組み合わせを JSX の字面から列挙する。
// 使い方: node ay2b-nontext-ancestry.cjs <competing.json> <出力md>
const fs = require("fs"), path = require("path");
const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const comp = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const SKIP_CLS = new Set(["form-group"]);
const classesOf = (sel) => { const out = new Set(); const subjAnc = sel.split(/\s*[>+~ ]\s*/).slice(0, -1); for (const part of subjAnc) for (const m of part.matchAll(/\.([A-Za-z0-9_-]+)/g)) out.add(m[1]); return out; };
const X = new Map(); // class -> [rules]
for (const r of comp.inRange) { if (/^\.form-group input\[type=/.test(r.selector)) continue; for (const c of classesOf(r.selector)) { if (!X.has(c)) X.set(c, []); X.get(c).push(r.file + ":" + r.line + " `" + r.selector + "`"); } }
const files = []; (function walk(d) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) { if (e.name !== "__tests__") walk(p); } else if (/\.tsx$/.test(e.name) && !/\.(test|stories)\.tsx$/.test(e.name)) files.push(p); } })(path.join(ROOT, "frontend/src"));
const NON = new Set(["checkbox", "radio", "range", "file"]);
const rows = []; const nonTextAll = [];
for (const f of files) {
  const text = fs.readFileSync(f, "utf8"); const sf = ts.createSourceFile(f, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const info = (n) => { const o = ts.isJsxElement(n) ? n.openingElement : n; const tag = o.tagName.getText(sf); let cls = ""; let type = null;
    for (const a of o.attributes.properties) if (ts.isJsxAttribute(a)) { const nm = a.name.getText(sf); const v = a.initializer ? a.initializer.getText(sf) : ""; if (nm === "className") cls = v; if (nm === "type") type = v.replace(/["'{}]/g, ""); }
    return { tag, cls, type, line: sf.getLineAndCharacterOfPosition(o.getStart(sf)).line + 1 }; };
  const stack = [];
  const visit = (n) => {
    const isEl = ts.isJsxElement(n) || ts.isJsxSelfClosingElement(n);
    if (isEl) {
      const i = info(n);
      if (i.tag === "input" && NON.has(i.type)) {
        const anc = stack.map((s) => s.cls).join(" ");
        const inFG = /(^|[^A-Za-z0-9_-])form-group([^A-Za-z0-9_-]|$)/.test(anc);
        const hit = [...X.keys()].filter((c) => new RegExp("(^|[^A-Za-z0-9_-])" + c + "([^A-Za-z0-9_-]|$)").test(anc + " " + i.cls));
        nonTextAll.push({ file: path.relative(ROOT, f), line: i.line, type: i.type, inFG, competingAncestors: hit, chain: stack.map((s) => s.tag + (s.cls ? "[" + s.cls.replace(/\s+/g, " ").slice(0, 60) + "]" : "")).slice(-6).join(" > ") });
      }
      stack.push(i); ts.forEachChild(n, visit); stack.pop();
    } else ts.forEachChild(n, visit);
  };
  visit(sf);
}
let md = "# 非 text input の祖先連鎖と競合規則クラス（字面ベース）\n\n手法: frontend/src の非テスト TSX（" + files.length + " ファイル）の JSX を TypeScript AST で走査し、type が checkbox/radio/range/file の <input> ごとに、同一ファイル内の JSX 祖先の className に form-group があるか、競合規則（nontext-competing-rules.md の範囲内規則）の祖先クラスがあるかを判定。部品経由（別ファイルから描画される場合）は字面では分からないため、ay2b-unresolved-trace.md（描画元の全洗い）と、nontext-after.md の網羅 fixture（競合クラス × .form-group の全組み合わせ）で補う。\n\n## 競合規則の祖先クラス\n\n| class | 規則 |\n|---|---|\n";
for (const [c, rs] of X) md += `| ${c} | ${rs.join("<br>")} |\n`;
md += "\n## 非 text input 全件（字面で .form-group の内側にあるもの、または競合クラスが祖先にあるもの）\n\n| file:line | type | 字面上 .form-group の内側 | 祖先にある競合クラス | 祖先連鎖（近い6段） |\n|---|---|---|---|---|\n";
const sel = nonTextAll.filter((r) => r.inFG || r.competingAncestors.length);
for (const r of sel) md += `| ${r.file}:${r.line} | ${r.type} | ${r.inFG ? "はい" : "いいえ"} | ${r.competingAncestors.join(", ") || "-"} | ${r.chain} |\n`;
md += `\n非 text input 全 ${nonTextAll.length} 件のうち、字面で .form-group の内側: ${nonTextAll.filter((r) => r.inFG).length} 件、競合クラスが祖先: ${nonTextAll.filter((r) => r.competingAncestors.length).length} 件、両方: ${nonTextAll.filter((r) => r.inFG && r.competingAncestors.length).length} 件。\n`;
fs.writeFileSync(process.argv[3], md); console.log(nonTextAll.length, sel.length);
