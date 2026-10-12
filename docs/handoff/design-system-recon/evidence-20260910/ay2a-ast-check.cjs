// AY-2a: 対象33件の一行入力を TextFieldControl へ移管した前後で、タグ名・className・variant・import 以外の
// 属性と children の原文が不変であることを TypeScript AST で機械照合する（ax2a-ast-check.cjs と同方式）。
// 使い方: node ay2a-ast-check.cjs before | after
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const OUT = path.join(__dirname, "ay2a-ast-check.json");
const FILES = [
  "frontend/src/pages/inbox/InboxKartePanel.tsx",
  "frontend/src/pages/inbox/InboxProfileModal.tsx",
  "frontend/src/pages/inbox/SalesFormMultiSelect.tsx",
  "frontend/src/pages/inbox/InboxConversationList.tsx",
  "frontend/src/pages/schedule/SchedulePageImpl.tsx",
  "frontend/src/pages/dashboard/PriorityProspectsSection.tsx",
  "frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx",
];
const OLD_CLASSES = ["right-panel-field", "search-input-field", "schedule-input", "db-weekly-composer-input"];
const EXPECT = { // 変更前 className の原文 → [追加される variant, 変更後 className の原文（無ければ null）]
  '"right-panel-field"': ['"karte"', null],
  '{`right-panel-field${!cardForm.next_action_date ? " karte-field-empty" : ""}`}': ['"karte"', '{!cardForm.next_action_date ? "karte-field-empty" : undefined}'],
  '"right-panel-field sales-form-other-input"': ['"karte"', '"sales-form-other-input"'],
  '"search-input-field inbox-search-input"': ['"search"', '"inbox-search-input"'],
  '"schedule-input"': ['"schedule"', null],
  '"db-weekly-composer-input"': ['"composer"', null],
};
function extract(relPath, mode) {
  const text = fs.readFileSync(path.join(ROOT, relPath), "utf8");
  const sf = ts.createSourceFile(relPath, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const found = [];
  const visit = (node) => {
    if (ts.isJsxSelfClosingElement(node) || ts.isJsxElement(node)) {
      const open = ts.isJsxElement(node) ? node.openingElement : node;
      const tag = open.tagName.getText(sf);
      const attrs = {}; let className = null; let spread = 0;
      for (const a of open.attributes.properties) {
        if (ts.isJsxSpreadAttribute(a)) { spread += 1; continue; }
        const name = a.name.getText(sf); const value = a.initializer ? a.initializer.getText(sf) : "true";
        if (name === "className") className = value; else attrs[name] = value;
      }
      const hit = mode === "before" ? (tag === "input" && className !== null && OLD_CLASSES.some((c) => className.includes(c))) : (tag === "TextFieldControl" && "variant" in attrs);
      if (hit) found.push({ file: relPath, line: sf.getLineAndCharacterOfPosition(open.getStart(sf)).line + 1, tag, selfClosing: ts.isJsxSelfClosingElement(node), className, attrs, spread,
        children: ts.isJsxElement(node) ? text.slice(open.end, node.closingElement.pos) : "" });
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return found;
}
const collect = (mode) => FILES.flatMap((f) => extract(f, mode));
function compare(before, after) {
  if (before.length !== after.length) return [{ error: `count mismatch before=${before.length} after=${after.length}` }];
  return before.map((b, i) => {
    const a = after[i]; const diffs = [];
    if (b.file !== a.file) diffs.push(`file ${b.file} -> ${a.file}`);
    if (a.tag !== "TextFieldControl") diffs.push(`after tag ${a.tag}`);
    if (b.spread !== a.spread) diffs.push("spread attrs differ");
    if (b.children !== a.children) diffs.push("children differ");
    const aKeys = Object.keys(a.attrs).filter((k) => k !== "variant");
    for (const k of new Set([...Object.keys(b.attrs), ...aKeys])) if (b.attrs[k] !== a.attrs[k]) diffs.push(`attr ${k}: ${b.attrs[k]} -> ${a.attrs[k]}`);
    const exp = EXPECT[b.className];
    if (!exp) diffs.push(`unexpected before className ${b.className}`);
    else {
      if (a.attrs.variant !== exp[0]) diffs.push(`variant ${a.attrs.variant} != ${exp[0]}`);
      if (a.className !== exp[1]) diffs.push(`after className ${a.className} != ${exp[1]}`);
    }
    return { index: i + 1, file: b.file, beforeLine: b.line, afterLine: a.line, beforeClass: b.className, afterClass: a.className, variant: a.attrs.variant, diffs };
  });
}
const mode = process.argv[2];
if (mode === "before") {
  const before = collect("before");
  fs.writeFileSync(OUT, JSON.stringify({ before, after: null, result: null }, null, 2) + "\n");
  console.log(`before: ${before.length} elements saved to ${path.relative(ROOT, OUT)}`);
  process.exit(before.length === 33 ? 0 : 1);
} else if (mode === "after") {
  const saved = JSON.parse(fs.readFileSync(OUT, "utf8"));
  const after = collect("after"); const rows = compare(saved.before, after);
  const totalDiffs = rows.reduce((n, r) => n + (r.error ? 1 : r.diffs.length), 0);
  const result = { elements: after.length, totalDiffs, rows };
  fs.writeFileSync(OUT, JSON.stringify({ before: saved.before, after, result }, null, 2) + "\n");
  console.log(JSON.stringify(result, null, 2));
  process.exit(totalDiffs === 0 && after.length === 33 ? 0 : 1);
} else { console.error("usage: node ay2a-ast-check.cjs before|after"); process.exit(2); }
