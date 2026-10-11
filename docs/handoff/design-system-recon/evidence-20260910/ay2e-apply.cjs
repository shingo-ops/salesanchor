// AY-2e: 規則なし一行入力6件（ay2e-targets.tsv）を TextFieldControl へ置換。style_auto=1 は style={{ width: "auto" }} を付与、class_to_remove は className を削除、import 追加。
const fs = require("fs"), path = require("path");
const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const rows = fs.readFileSync(path.join(__dirname, "ay2e-targets.tsv"), "utf8").split("\n").slice(1).filter(Boolean).map((l) => { const [t, a, c] = l.split("\t"); const i = t.lastIndexOf(":"); return { file: t.slice(0, i), line: Number(t.slice(i + 1)), auto: a === "1", cls: c || "" }; });
const MOLD = path.join(ROOT, "frontend/src/components/TextField");
const byFile = new Map(); for (const r of rows) (byFile.get(r.file) || byFile.set(r.file, []).get(r.file)).push(r);
for (const [rel, list] of byFile) {
  const abs = path.join(ROOT, rel); let text = fs.readFileSync(abs, "utf8");
  const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const edits = []; const done = new Set();
  (function v(n) {
    if (ts.isJsxSelfClosingElement(n)) {
      const line = sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
      const r = list.find((x) => x.line === line);
      if (r && n.tagName.getText(sf) === "input") {
        const props = n.attributes.properties;
        if (props.some((a) => ts.isJsxAttribute(a) && a.name.getText(sf) === "style")) throw new Error(rel + ":" + line + " has style");
        edits.push({ s: n.tagName.getStart(sf), e: n.tagName.getEnd(), t: "TextFieldControl" });
        const cn = props.find((a) => ts.isJsxAttribute(a) && a.name.getText(sf) === "className");
        if (r.cls) {
          if (!cn || cn.initializer.getText(sf) !== '"' + r.cls + '"') throw new Error(rel + ":" + line + " className mismatch");
          let s = cn.getStart(sf); while (/\s/.test(text[s - 1])) s--;
          edits.push({ s, e: cn.getEnd(), t: "" });
        } else if (cn) throw new Error(rel + ":" + line + " unexpected className");
        if (r.auto) {
          const last = props[props.length - 1]; const ind = text.slice(text.lastIndexOf("\n", last.getStart(sf)) + 1, last.getStart(sf));
          edits.push({ s: last.getEnd(), e: last.getEnd(), t: "\n" + ind + 'style={{ width: "auto" }}' });
        }
        done.add(line);
      }
    }
    ts.forEachChild(n, v);
  })(sf);
  if (done.size !== list.length) throw new Error(rel + " missing");
  let imp = null, lastImp = null;
  for (const st of sf.statements) if (ts.isImportDeclaration(st)) { lastImp = st; if (path.resolve(path.dirname(abs), st.moduleSpecifier.text) === MOLD) imp = st; }
  if (imp) throw new Error(rel + " already imports mold");
  let r2 = path.relative(path.dirname(abs), MOLD); if (!r2.startsWith(".")) r2 = "./" + r2;
  edits.push({ s: lastImp.getEnd(), e: lastImp.getEnd(), t: '\nimport { TextFieldControl } from "' + r2 + '";' });
  edits.sort((a, b) => b.s - a.s);
  for (const x of edits) text = text.slice(0, x.s) + x.t + text.slice(x.e);
  fs.writeFileSync(abs, text); console.log(rel, list.length, "ok");
}
