// AY-2e: 6件の置換が「タグ名・className 削除・style 追加・import 以外の差分0」であることを TypeScript AST で照合。before=origin/main、after=作業ツリー。
const fs = require("fs"), path = require("path"), cp = require("child_process");
const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const rows = fs.readFileSync(path.join(__dirname, "ay2e-targets.tsv"), "utf8").split("\n").slice(1).filter(Boolean).map((l) => { const [t, a, c] = l.split("\t"); const i = t.lastIndexOf(":"); return { file: t.slice(0, i), line: Number(t.slice(i + 1)), auto: a === "1", cls: c || "" }; });
const FILES = [...new Set(rows.map((r) => r.file))].sort();
const before = (f) => cp.execFileSync("git", ["show", "origin/main:" + f], { cwd: ROOT, encoding: "utf8", maxBuffer: 1 << 26 });
function elems(f, text) {
  const sf = ts.createSourceFile(f, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX); const out = [];
  (function v(n) { if (ts.isJsxSelfClosingElement(n) || ts.isJsxElement(n)) { const o = ts.isJsxElement(n) ? n.openingElement : n;
    out.push({ line: sf.getLineAndCharacterOfPosition(o.getStart(sf)).line + 1, tag: o.tagName.getText(sf), sc: ts.isJsxSelfClosingElement(n), attrs: o.attributes.properties.map((a) => a.getText(sf).replace(/\s+/g, " ")), close: ts.isJsxElement(n) ? n.closingElement.tagName.getText(sf) : null, children: ts.isJsxElement(n) ? text.slice(o.end, n.closingElement.pos) : "" }); }
    ts.forEachChild(n, v); })(sf);
  return { out, imports: sf.statements.filter(ts.isImportDeclaration).map((s) => s.getText(sf)) };
}
const CLS = [...new Set(rows.map((r) => r.cls).filter(Boolean))];
// 祖先要素の本文/属性に含まれる置換箇所を正規化（after 側を before 形に戻す）。
const norm = (t) => t.replace(/TextFieldControl/g, "input").replace(/\s*style=\{\{ width: "auto" \}\}/g, "").replace(/\s+/g, " ");
const normB = (t) => { let u = t; for (const c of CLS) u = u.replace(new RegExp('\\s*className="' + c.replace(/[-]/g, "\\-") + '"', "g"), ""); return u.replace(/\s+/g, " "); };
let md = "# AY-2e AST 照合（6件、タグ名・className 削除・style 追加・import 以外の差分0）\n\nbefore=origin/main、after=作業ツリー。\n\n| ファイル | 対象 | 要素数 before/after | 差分 |\n|---|---|---|---|\n"; let total = 0, bad = 0;
for (const f of FILES) {
  const mine = rows.filter((r) => r.file === f); const b = elems(f, before(f)), a = elems(f, fs.readFileSync(path.join(ROOT, f), "utf8")); const diffs = []; let t = 0;
  if (b.out.length !== a.out.length) diffs.push("element count");
  for (let i = 0; i < Math.min(b.out.length, a.out.length); i++) {
    const x = b.out[i], y = a.out[i], r = x.tag === "input" && mine.find((m) => m.line === x.line); let xa = x.attrs;
    if (r) { t++;
      if (y.tag !== "TextFieldControl") diffs.push(x.line + ": tag");
      if (!x.sc || !y.sc) diffs.push(x.line + ": not self-closing");
      if (r.cls) { const c = `className="${r.cls}"`; if (x.attrs.filter((s) => s === c).length !== 1) diffs.push(x.line + ": className count"); xa = xa.filter((s) => s !== c); }
      if (y.attrs.some((s) => /^className/.test(s))) diffs.push(x.line + ": className remains");
      if (r.auto) { const st = 'style={{ width: "auto" }}'; if (y.attrs.filter((s) => s === st).length !== 1) diffs.push(x.line + ": style missing"); xa = [...xa, st]; }
    } else if (x.tag !== y.tag) diffs.push(x.line + ": non-target tag");
    if (r ? JSON.stringify(xa) !== JSON.stringify(y.attrs) : JSON.stringify(x.attrs.map(normB)) !== JSON.stringify(y.attrs.map(norm))) diffs.push(x.line + ": attrs differ");
    if (normB(x.children) !== norm(y.children) || x.close !== y.close) diffs.push(x.line + ": children/close differ");
  }
  const added = a.imports.filter((s) => !b.imports.includes(s)), removed = b.imports.filter((s) => !a.imports.includes(s));
  if (!(added.length === 1 && /^import \{ TextFieldControl \} from "\.\.\/\.\.\/components\/TextField";$/.test(added[0]) && removed.length === 0)) diffs.push("import diff unexpected");
  if (diffs.length || t !== mine.length) bad++; total += t;
  md += `| ${f} | ${t} | ${b.out.length}/${a.out.length} | ${diffs.length ? diffs.join("; ") : "0"} |\n`;
}
md += `\n対象 ${total} 件 / 想定 ${rows.length} 件。不一致ファイル数 ${bad}。\n\n判定: ${bad === 0 && total === rows.length ? "PASS" : "FAIL"}\n`;
console.log(md); process.exit(bad === 0 && total === rows.length ? 0 : 1);
