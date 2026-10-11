// AY-2d: 登録画面45件の置換が「タグ名・className="input" 削除・import 追加以外の差分0」であることを TypeScript AST で照合する。
// before = git show origin/main:<file>、after = 作業ツリー。使い方: node ay2d-ast-check.cjs > ay2d-ast-check.md
const fs = require("fs"), path = require("path"), cp = require("child_process");
const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const tsv = fs.readFileSync(path.join(__dirname, "ay2d-targets.tsv"), "utf8").trim().split("\n").slice(1).map((l) => l.split("\t")[0]);
const TARGETS = new Set(tsv);
const FILES = [...new Set(tsv.map((s) => s.slice(0, s.lastIndexOf(":"))))].sort();
const before = (f) => cp.execFileSync("git", ["show", "origin/main:" + f], { cwd: ROOT, encoding: "utf8", maxBuffer: 1 << 26 });
function elems(f, text) {
  const sf = ts.createSourceFile(f, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const out = [];
  (function v(n) {
    if (ts.isJsxSelfClosingElement(n) || ts.isJsxElement(n)) {
      const o = ts.isJsxElement(n) ? n.openingElement : n;
      out.push({ line: sf.getLineAndCharacterOfPosition(o.getStart(sf)).line + 1, tag: o.tagName.getText(sf), selfClosing: ts.isJsxSelfClosingElement(n),
        attrs: o.attributes.properties.map((a) => a.getText(sf)),
        closeTag: ts.isJsxElement(n) ? n.closingElement.tagName.getText(sf) : null,
        children: ts.isJsxElement(n) ? text.slice(o.end, n.closingElement.pos) : "" });
    }
    ts.forEachChild(n, v);
  })(sf);
  return { out, imports: sf.statements.filter(ts.isImportDeclaration).map((s) => s.getText(sf)) };
}
let md = "# AY-2d AST 照合（登録画面45件、タグ名・className=\"input\" 削除・import 追加以外の差分0）\n\nbefore=origin/main、after=作業ツリー。\n\n| ファイル | 対象 | 要素数 before/after | 差分 |\n|---|---|---|---|\n";
let totalT = 0, bad = 0;
for (const f of FILES) {
  const b = elems(f, before(f)), a = elems(f, fs.readFileSync(path.join(ROOT, f), "utf8"));
  const diffs = []; let t = 0;
  if (b.out.length !== a.out.length) diffs.push(`element count ${b.out.length}/${a.out.length}`);
  for (let i = 0; i < Math.min(b.out.length, a.out.length); i++) {
    const x = b.out[i], y = a.out[i], isT = x.tag === "input" && TARGETS.has(f + ":" + x.line);
    let xa = x.attrs;
    if (isT) {
      t++;
      if (y.tag !== "TextFieldControl") diffs.push(`${x.line}: tag ${x.tag}->${y.tag}`);
      if (!x.selfClosing || !y.selfClosing) diffs.push(`${x.line}: not self-closing`);
      if (x.attrs.filter((s) => s === 'className="input"').length !== 1) diffs.push(`${x.line}: className="input" count`);
      xa = x.attrs.filter((s) => s !== 'className="input"');
      if (y.attrs.some((s) => /^className/.test(s))) diffs.push(`${x.line}: className remains`);
    } else if (x.tag !== y.tag) diffs.push(`${x.line}: non-target tag ${x.tag}->${y.tag}`);
    if (JSON.stringify(xa) !== JSON.stringify(y.attrs)) diffs.push(`${x.line}: attrs differ`);
    const nb = x.children.replace(/\s*className="input"/g, ""), na = y.children.replace(/TextFieldControl/g, "input");
    if (nb !== na) diffs.push(`${x.line}: children differ`);
    if (x.closeTag !== y.closeTag) diffs.push(`${x.line}: closing tag differs`);
  }
  const added = a.imports.filter((s) => !b.imports.includes(s)), removed = b.imports.filter((s) => !a.imports.includes(s));
  if (!(added.length === 1 && /^import \{ TextFieldControl \} from "[./]+\/components\/TextField";$|^import \{ TextFieldControl \} from "\.\.\/\.\.\/components\/TextField";$/.test(added[0]) && removed.length === 0)) diffs.push("import diff unexpected: +" + added.join("|") + " -" + removed.join("|"));
  const expected = tsv.filter((s) => s.startsWith(f + ":")).length;
  if (diffs.length || t !== expected) bad++;
  totalT += t;
  md += `| ${f} | ${t} | ${b.out.length}/${a.out.length} | ${diffs.length ? diffs.join("; ") : "0"} |\n`;
}
let lineBad = 0;
for (const f of FILES) {
  const d = cp.execFileSync("git", ["diff", "-U0", "origin/main", "--", f], { cwd: ROOT, encoding: "utf8" }).split("\n").filter((l) => /^[+-]/.test(l) && !/^(\+\+\+|---)/.test(l));
  const minus = d.filter((l) => l[0] === "-").map((l) => l.slice(1)), plus = d.filter((l) => l[0] === "+").map((l) => l.slice(1));
  const plusRest = plus.filter((l) => !/^import \{ TextFieldControl \} from /.test(l));
  const conv = minus.filter((l) => l.trim() !== 'className="input"').map((l) => l.replace(/<input(?=[\s/>]|$)/g, "<TextFieldControl"));
  const nClass = minus.filter((l) => l.trim() === 'className="input"').length;
  if (JSON.stringify(conv) !== JSON.stringify(plusRest)) lineBad++;
  if (nClass !== tsv.filter((s) => s.startsWith(f + ":")).length) lineBad++;
}
md += `\n対象 ${totalT} 件 / 想定 ${TARGETS.size} 件。要素単位の不一致ファイル数 ${bad}。行単位 diff の不一致ファイル数 ${lineBad}。\n\n判定: ${bad === 0 && lineBad === 0 && totalT === TARGETS.size ? "PASS（タグ名・className=\"input\" 削除・import 追加以外の差分 0）" : "FAIL"}\n`;
console.log(md);
process.exit(bad === 0 && lineBad === 0 && totalT === TARGETS.size ? 0 : 1);
