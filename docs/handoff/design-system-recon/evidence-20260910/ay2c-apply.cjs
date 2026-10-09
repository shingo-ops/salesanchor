// AY-2c: 生 text 系 input 49 件（ay2c-targets.tsv の確定 target）を TextFieldControl へ置換し import を追加する。
// 使い方: node ay2c-apply.cjs   （リポジトリルートの frontend/node_modules/typescript を使う）
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const TARGETS = JSON.parse(String.raw`["frontend/src/components/MergeLeadModal.tsx:146", "frontend/src/pages/companies/CompaniesPage.tsx:452", "frontend/src/pages/companies/CompaniesPage.tsx:456", "frontend/src/pages/companies/CompaniesPage.tsx:460", "frontend/src/pages/companies/CompaniesPage.tsx:464", "frontend/src/pages/companies/CompaniesPage.tsx:468", "frontend/src/pages/companies/CompaniesPage.tsx:472", "frontend/src/pages/companies/CompaniesPage.tsx:476", "frontend/src/pages/companies/CompaniesPage.tsx:480", "frontend/src/pages/companies/CompaniesPage.tsx:484", "frontend/src/pages/companies/CompaniesPage.tsx:488", "frontend/src/pages/companies/CompaniesPage.tsx:492", "frontend/src/pages/companies/CompaniesPage.tsx:496", "frontend/src/pages/companies/CompaniesPage.tsx:504", "frontend/src/pages/companies/CompaniesPage.tsx:533", "frontend/src/pages/companies/CompaniesPage.tsx:535", "frontend/src/pages/companies/CompaniesPage.tsx:536", "frontend/src/pages/companies/CompaniesPage.tsx:539", "frontend/src/pages/companies/CompaniesPage.tsx:542", "frontend/src/pages/companies/CompaniesPage.tsx:543", "frontend/src/pages/companies/CompaniesPage.tsx:544", "frontend/src/pages/companies/CompaniesPage.tsx:545", "frontend/src/pages/companies/CompaniesPage.tsx:546", "frontend/src/pages/companies/CompaniesPage.tsx:547", "frontend/src/pages/companies/CompaniesPage.tsx:548", "frontend/src/pages/company-detail/CompanyBasicTab.tsx:38", "frontend/src/pages/company-detail/CompanyBasicTab.tsx:42", "frontend/src/pages/company-detail/CompanyBasicTab.tsx:46", "frontend/src/pages/company-detail/CompanyBasicTab.tsx:50", "frontend/src/pages/company-detail/CompanyBasicTab.tsx:54", "frontend/src/pages/company-detail/CompanyBasicTab.tsx:58", "frontend/src/pages/company-detail/CompanyBasicTab.tsx:62", "frontend/src/pages/company-detail/CompanyBasicTab.tsx:66", "frontend/src/pages/company-detail/CompanyBasicTab.tsx:70", "frontend/src/pages/company-detail/CompanyBasicTab.tsx:74", "frontend/src/pages/company-detail/CompanyBasicTab.tsx:78", "frontend/src/pages/company-detail/CompanyChannelsTab.tsx:32", "frontend/src/pages/company-detail/CompanyDiscordTab.tsx:53", "frontend/src/pages/company-detail/CompanyDiscordTab.tsx:62", "frontend/src/pages/company-detail/CompanyDiscordTab.tsx:71", "frontend/src/pages/company-detail/CompanyDiscordTab.tsx:80", "frontend/src/pages/contacts/ContactsPage.tsx:306", "frontend/src/pages/contacts/ContactsPage.tsx:316", "frontend/src/pages/contacts/ContactsPage.tsx:319", "frontend/src/pages/contacts/ContactsPage.tsx:322", "frontend/src/pages/contacts/ContactsPage.tsx:325", "frontend/src/pages/contacts/ContactsPage.tsx:328", "frontend/src/pages/contacts/ContactsPage.tsx:337", "frontend/src/pages/contacts/ContactsPage.tsx:340"]`);
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
        edits.push({ s: open.tagName.getStart(sf), e: open.tagName.getEnd(), t: "TextFieldControl" });
        done.add(line);
      }
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  if (done.size !== want.size) throw new Error(rel + " missing " + [...want].filter((l) => !done.has(l)));
  // import
  let imp = null, lastImp = null;
  for (const st of sf.statements) if (ts.isImportDeclaration(st)) {
    lastImp = st;
    const spec = st.moduleSpecifier.text;
    if (path.resolve(path.dirname(abs), spec) === MOLD) imp = st;
  }
  if (imp) {
    const nb = imp.importClause.namedBindings;
    if (!nb || !ts.isNamedImports(nb)) throw new Error(rel + " odd import");
    if (nb.elements.some((e) => e.name.text === "TextFieldControl")) throw new Error(rel + " already imports");
    const last = nb.elements[nb.elements.length - 1];
    edits.push({ s: last.getEnd(), e: last.getEnd(), t: ", TextFieldControl" });
  } else {
    let r = path.relative(path.dirname(abs), MOLD); if (!r.startsWith(".")) r = "./" + r;
    edits.push({ s: lastImp.getEnd(), e: lastImp.getEnd(), t: '\nimport { TextFieldControl } from "' + r + '";' });
  }
  edits.sort((a, b) => b.s - a.s);
  for (const x of edits) text = text.slice(0, x.s) + x.t + text.slice(x.e);
  fs.writeFileSync(abs, text);
  total += done.size;
  console.log(rel, done.size, imp ? "import-extended" : "import-added");
}
console.log("replaced", total);
