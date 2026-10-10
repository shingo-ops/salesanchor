// AY-2d: 登録画面の生 text 系 input 45 件（ay2d-targets.tsv）を TextFieldControl へ置換し、className="input" を外し、import を追加する。
// 使い方: node ay2d-apply.cjs
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const TARGETS = fs.readFileSync(path.join(__dirname, "ay2d-targets.tsv"), "utf8").trim().split("\n").slice(1).map((l) => l.split("\t")[0]);
const MOLD = path.join(ROOT, "frontend/src/components/TextField");
const byFile = new Map();
for (const s of TARGETS) { const i = s.lastIndexOf(":"); const f = s.slice(0, i); (byFile.get(f) || byFile.set(f, []).get(f)).push(Number(s.slice(i + 1))); }
let total = 0;
for (const [rel, lines] of byFile) {
  const abs = path.join(ROOT, rel);
  let text = fs.readFileSync(abs, "utf8");
  const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const edits = []; const want = new Set(lines); const done = new Set();
  const visit = (n) => {
    if (ts.isJsxSelfClosingElement(n) || ts.isJsxElement(n)) {
      const open = ts.isJsxElement(n) ? n.openingElement : n;
      const line = sf.getLineAndCharacterOfPosition(open.getStart(sf)).line + 1;
      if (open.tagName.getText(sf) === "input" && want.has(line)) {
        if (ts.isJsxElement(n)) throw new Error(rel + ":" + line + " is not self-closing");
        const cn = open.attributes.properties.find((a) => ts.isJsxAttribute(a) && a.name.getText(sf) === "className");
        if (!cn || cn.initializer.getText(sf) !== '"input"') throw new Error(rel + ":" + line + " className is not \"input\"");
        edits.push({ s: open.tagName.getStart(sf), e: open.tagName.getEnd(), t: "TextFieldControl" });
        // className="input" とその直前の空白（改行インデント）を除去
        let s = cn.getStart(sf); while (/\s/.test(text[s - 1])) s--;
        edits.push({ s, e: cn.getEnd(), t: "" });
        done.add(line);
      }
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  if (done.size !== want.size) throw new Error(rel + " missing " + [...want].filter((l) => !done.has(l)));
  let imp = null, lastImp = null;
  for (const st of sf.statements) if (ts.isImportDeclaration(st)) {
    lastImp = st;
    if (path.resolve(path.dirname(abs), st.moduleSpecifier.text) === MOLD) imp = st;
  }
  if (imp) throw new Error(rel + " already imports mold");
  let r = path.relative(path.dirname(abs), MOLD); if (!r.startsWith(".")) r = "./" + r;
  edits.push({ s: lastImp.getEnd(), e: lastImp.getEnd(), t: '\nimport { TextFieldControl } from "' + r + '";' });
  edits.sort((a, b) => b.s - a.s);
  for (const x of edits) text = text.slice(0, x.s) + x.t + text.slice(x.e);
  fs.writeFileSync(abs, text);
  total += done.size;
  console.log(rel, done.size, "import-added");
}
console.log("replaced", total);
