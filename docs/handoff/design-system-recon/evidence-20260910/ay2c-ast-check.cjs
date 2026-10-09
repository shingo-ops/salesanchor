// AY-2c: 生 text 系 input 49 件の TextFieldControl 置換が「タグ名・import 以外の差分0」であることを TypeScript AST で照合する。
// before = git show origin/main:<file>（実行時の HEAD の親ではなく origin/main）、after = 作業ツリー。
// 使い方: node ay2c-ast-check.cjs > ay2c-ast-check.md   （リポジトリ内で実行）
const fs = require("fs"), path = require("path"), cp = require("child_process");
const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const tsv = fs.readFileSync(path.join(__dirname, "ay2c-targets.tsv"), "utf8").trim().split("\n");
const head = tsv[0].split("\t");
const rows = tsv.slice(1).map((l) => Object.fromEntries(l.split("\t").map((v, i) => [head[i], v])));
const TARGETS = new Set(rows.filter((r) => r.baseRule !== "none(:not除外)").map((r) => r.file + ":" + r.line));
const FILES = [...new Set([...TARGETS].map((s) => s.slice(0, s.lastIndexOf(":"))))].sort();
const before = (f) => cp.execFileSync("git", ["show", "origin/main:" + f], { cwd: ROOT, encoding: "utf8", maxBuffer: 1 << 26 });
function elems(f, text) {
  const sf = ts.createSourceFile(f, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const out = [];
  (function v(n) {
    if (ts.isJsxSelfClosingElement(n) || ts.isJsxElement(n)) {
      const o = ts.isJsxElement(n) ? n.openingElement : n;
      out.push({ line: sf.getLineAndCharacterOfPosition(o.getStart(sf)).line + 1, tag: o.tagName.getText(sf), selfClosing: ts.isJsxSelfClosingElement(n),
        attrs: o.attributes.properties.map((a) => a.getText(sf)).join("\u0001"),
        closeTag: ts.isJsxElement(n) ? n.closingElement.tagName.getText(sf) : null,
        children: ts.isJsxElement(n) ? text.slice(o.end, n.closingElement.pos) : "" });
    }
    ts.forEachChild(n, v);
  })(sf);
  const imports = sf.statements.filter(ts.isImportDeclaration).map((s) => s.getText(sf));
  return { out, imports, nonJsx: text };
}
let md = "# AY-2c AST 照合（49件、タグ名・import 以外の差分0）\n\nbefore=origin/main、after=作業ツリー。\n\n| ファイル | 対象 | 要素数 before/after | 差分 |\n|---|---|---|---|\n";
let totalT = 0, bad = 0;
for (const f of FILES) {
  const b = elems(f, before(f)), a = elems(f, fs.readFileSync(path.join(ROOT, f), "utf8"));
  const diffs = [];
  if (b.out.length !== a.out.length) diffs.push(`element count ${b.out.length}/${a.out.length}`);
  let t = 0;
  for (let i = 0; i < Math.min(b.out.length, a.out.length); i++) {
    const x = b.out[i], y = a.out[i], isT = x.tag === "input" && TARGETS.has(f + ":" + x.line);
    if (isT) {
      t++;
      if (x.tag !== "input" || y.tag !== "TextFieldControl") diffs.push(`${x.line}: tag ${x.tag}->${y.tag}`);
      if (!x.selfClosing || !y.selfClosing) diffs.push(`${x.line}: not self-closing`);
    } else if (x.tag !== y.tag) diffs.push(`${x.line}: non-target tag ${x.tag}->${y.tag}`);
    if (x.attrs !== y.attrs.replace(/TextFieldControl/g, "input")) diffs.push(`${x.line}: attrs differ`);
    if (x.children !== y.children.replace(/TextFieldControl/g, "input")) diffs.push(`${x.line}: children differ`);
    if (x.closeTag !== y.closeTag) diffs.push(`${x.line}: closing tag differs`);
  }
  const addedImports = a.imports.filter((s) => !b.imports.includes(s));
  const removedImports = b.imports.filter((s) => !a.imports.includes(s));
  const okImport = a.imports.length - b.imports.length === (removedImports.length ? 0 : 1) && addedImports.every((s) => /TextFieldControl/.test(s)) && addedImports.length === 1;
  if (!okImport) diffs.push("import diff unexpected: +" + addedImports.join(" | ") + " -" + removedImports.join(" | "));
  // 要素・import 以外の本文（正規化: TextFieldControl→input、追加 import 除去）が一致
  const norm = (s, imps) => { let r = s; for (const i of imps) r = r.replace(i + "\n", "").replace("\n" + i, ""); return r.replace(/TextFieldControl/g, "input").replace(/, input/g, ""); };
  totalT += t; if (diffs.length || t !== rows.filter((r) => r.file === f && r.baseRule !== "none(:not除外)").length) bad++;
  md += `| ${f} | ${t} | ${b.out.length}/${a.out.length} | ${diffs.length ? diffs.join("; ") : "0"} |\n`;
}
// 行単位の差分（tag 名置換と import 追加以外の行が無いこと）
let lineBad = 0;
for (const f of [...FILES]) {
  const d = cp.execFileSync("git", ["diff", "-U0", "origin/main", "--", f], { cwd: ROOT, encoding: "utf8" }).split("\n").filter((l) => /^[+-]/.test(l) && !/^(\+\+\+|---)/.test(l));
  const minus = d.filter((l) => l[0] === "-").map((l) => l.slice(1)), plus = d.filter((l) => l[0] === "+").map((l) => l.slice(1));
  const addedImp = plus.filter((l) => /import \{.*TextFieldControl.*\} from/.test(l));
  const plusRest = plus.filter((l) => !addedImp.includes(l));
  const conv = minus.map((l) => l.replace(/<input(?=[\s/>]|$)/g, "<TextFieldControl"));
  const importExt = minus.filter((l) => /import \{.*\} from/.test(l));
  if (importExt.length) { /* 既存 import の拡張は無い想定 */ lineBad++; }
  if (JSON.stringify(conv) !== JSON.stringify(plusRest)) lineBad++;
}
md += `\n対象 ${totalT} 件 / 想定 ${TARGETS.size} 件。要素単位の不一致ファイル数 ${bad}。行単位 diff（'<input'→'<TextFieldControl' と import 1 行追加以外）の不一致ファイル数 ${lineBad}。\n\n判定: ${bad === 0 && lineBad === 0 && totalT === TARGETS.size ? "PASS（タグ名・import 以外の差分 0）" : "FAIL"}\n`;
console.log(md);
process.exit(bad === 0 && lineBad === 0 && totalT === TARGETS.size ? 0 : 1);
