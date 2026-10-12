// AX-2b: 一般フォームの生 textarea 38件（ProductMasterDrawer.tsx の2件は i18n 警告のため保留で対象外）を TextareaControl（標準）へ移管した前後で、タグ名・className・style・textStyle・ui-allow・import
// 以外の属性と children の原文が不変であることを TypeScript AST で機械照合する（ax2a-ast-check.cjs と同方式）。
// 使い方: node ax2b-ast-check.cjs before | after
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const OUT = path.join(__dirname, "ax2b-ast-check.json");
const FILES = [
  "frontend/src/components/MergeLeadModal.tsx",
  "frontend/src/components/OrderFinancialPanel.tsx",
  "frontend/src/components/PriorityScoreOverride.tsx",
  "frontend/src/components/PurchaseDetailPanel.tsx",
  "frontend/src/components/ShippingDetailPanel.tsx",
  "frontend/src/features/tcg-analysis-review/ItemComparison.tsx",
  "frontend/src/pages/admin/DiscordAnnouncePage.tsx",
  "frontend/src/pages/admin/TenantProfilePage.tsx",
  "frontend/src/pages/badges/BadgesPage.tsx",
  "frontend/src/pages/buddy/BuddyPage.tsx",
  "frontend/src/pages/companies/CompaniesPage.tsx",
  "frontend/src/pages/companies/CompanyFormFields.tsx",
  "frontend/src/pages/company-detail/CompanyBasicTab.tsx",
  "frontend/src/pages/conditions/ConditionsPage.tsx",
  "frontend/src/pages/contacts/ContactEditPage.tsx",
  "frontend/src/pages/contacts/ContactsPage.tsx",
  "frontend/src/pages/inbox/ManualRecordSection.tsx",
  "frontend/src/pages/inbox/OutboundTranslationPreview.tsx",
  "frontend/src/pages/leads/LeadEditPage.tsx",
  "frontend/src/pages/leads/LeadFormFields.tsx",
  "frontend/src/pages/leads/LeadsPage.tsx",
  "frontend/src/pages/orders/OrdersFormModal.tsx",
  "frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx",
  "frontend/src/pages/roles/RolesPage.tsx",
  "frontend/src/pages/staff-reports/StaffReportsPage.tsx",
  "frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx",
  "frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx",
  "frontend/src/pages/suppliers/SupplierFormFields.tsx",
  "frontend/src/pages/teams/TeamFormFields.tsx"
];
const TARGET_TAGS = new Set(["textarea", "TextareaControl"]);
const REMOVED_CLASSES = new Set(['"outbound-translation-edit"', '"manual-record-textarea"', '"input w-full resize-y"', '"field field-h-md"']);
const STYLE_REMOVED_FILES = new Set([
  "frontend/src/pages/conditions/ConditionsPage.tsx",
  "frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx",
  "frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx",
]);
const TEXTSTYLE_FILES = new Set(["frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx"]);
function extract(relPath) {
  const text = fs.readFileSync(path.join(ROOT, relPath), "utf8");
  const sf = ts.createSourceFile(relPath, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const found = [];
  const visit = (node) => {
    if (ts.isJsxSelfClosingElement(node) || ts.isJsxElement(node)) {
      const open = ts.isJsxElement(node) ? node.openingElement : node;
      const tag = open.tagName.getText(sf);
      if (TARGET_TAGS.has(tag)) {
        const attrs = {}; let className = null; let style = null; let spread = 0;
        for (const a of open.attributes.properties) {
          if (ts.isJsxSpreadAttribute(a)) { spread += 1; continue; }
          const name = a.name.getText(sf); const value = a.initializer ? a.initializer.getText(sf) : "true";
          if (name === "className") className = value; else if (name === "style") style = value; else attrs[name] = value;
        }
        found.push({ file: relPath, line: sf.getLineAndCharacterOfPosition(open.getStart(sf)).line + 1, tag, selfClosing: ts.isJsxSelfClosingElement(node), className, style, attrs, spread,
          children: ts.isJsxElement(node) ? text.slice(open.end, node.closingElement.pos) : "" });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return { elements: found, uiAllow: (text.match(/ui-allow/g) || []).length };
}
function collect() {
  const elements = []; const uiAllow = {};
  for (const f of FILES) { const r = extract(f); elements.push(...r.elements); uiAllow[f] = r.uiAllow; }
  return { elements, uiAllow };
}
function compare(before, after) {
  const b = before.elements, a = after.elements;
  if (b.length !== a.length) return [{ error: `count mismatch before=${b.length} after=${a.length}` }];
  const rows = b.map((x, i) => {
    const y = a[i]; const diffs = [];
    if (x.file !== y.file) diffs.push(`file ${x.file} -> ${y.file}`);
    if (x.tag !== "textarea") diffs.push(`before tag ${x.tag}`);
    if (y.tag !== "TextareaControl") diffs.push(`after tag ${y.tag}`);
    if (x.spread !== y.spread) diffs.push("spread attrs differ");
    if (x.children !== y.children) diffs.push("children differ");
    const aKeys = Object.keys(y.attrs).filter((k) => k !== "textStyle");
    for (const k of new Set([...Object.keys(x.attrs), ...aKeys])) if (x.attrs[k] !== y.attrs[k]) diffs.push(`attr ${k}: ${x.attrs[k]} -> ${y.attrs[k]}`);
    const expectClass = x.className !== null && REMOVED_CLASSES.has(x.className) ? null : x.className;
    if (x.className !== null && !REMOVED_CLASSES.has(x.className)) diffs.push(`unexpected before className ${x.className}`);
    if (y.className !== expectClass) diffs.push(`after className ${y.className} != ${expectClass}`);
    const expectStyle = STYLE_REMOVED_FILES.has(x.file) ? null : x.style;
    if (y.style !== expectStyle) diffs.push(`after style ${y.style} != ${expectStyle}`);
    const expectTs = TEXTSTYLE_FILES.has(x.file) ? '"code"' : undefined;
    if (y.attrs.textStyle !== expectTs) diffs.push(`textStyle ${y.attrs.textStyle} != ${expectTs}`);
    return { index: i + 1, file: x.file, beforeLine: x.line, afterLine: y.line, beforeClass: x.className, afterClass: y.className, beforeStyle: x.style, afterStyle: y.style, textStyle: y.attrs.textStyle, diffs };
  });
  for (const f of FILES) {
    const want = f === "frontend/src/pages/conditions/ConditionsPage.tsx" ? 0 : before.uiAllow[f];
    if (after.uiAllow[f] !== want) rows.push({ file: f, diffs: [`ui-allow count ${after.uiAllow[f]} != ${want}`] });
  }
  return rows;
}
const IN_SCOPE = (e) => FILES.includes(e.file);
const mode = process.argv[2];
if (mode === "before") {
  const before = collect();
  fs.writeFileSync(OUT, JSON.stringify({ before, after: null, result: null }, null, 2) + "\n");
  console.log(`before: ${before.elements.length} elements, ui-allow total ${Object.values(before.uiAllow).reduce((n, v) => n + v, 0)} saved to ${path.relative(ROOT, OUT)}`);
  process.exit(before.elements.length === 38 ? 0 : 1);
} else if (mode === "after") {
  const saved0 = JSON.parse(fs.readFileSync(OUT, "utf8"));
  const saved = { ...saved0, before: { elements: saved0.before.elements.filter(IN_SCOPE), uiAllow: Object.fromEntries(Object.entries(saved0.before.uiAllow).filter(([f]) => FILES.includes(f))) } };
  const after = collect(); const rows = compare(saved.before, after);
  const totalDiffs = rows.reduce((n, r) => n + (r.error ? 1 : r.diffs.length), 0);
  const result = { elements: after.elements.length, totalDiffs, rows };
  fs.writeFileSync(OUT, JSON.stringify({ before: saved.before, after, result }, null, 2) + "\n");
  console.log(JSON.stringify({ elements: result.elements, totalDiffs, nonEmpty: rows.filter((r) => r.diffs.length) }, null, 2));
  process.exit(totalDiffs === 0 && after.elements.length === 38 ? 0 : 1);
} else { console.error("usage: node ax2b-ast-check.cjs before|after"); process.exit(2); }
