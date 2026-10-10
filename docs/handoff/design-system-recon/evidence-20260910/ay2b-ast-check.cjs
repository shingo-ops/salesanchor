// AY-2b: `.form-group` 配下の一行入力 143 件（ay2b-members.json の確定 target）を TextFieldControl へ移管した前後で、
// タグ名・variant・className（CSS定義の無い "input" の除去のみ）・style（外観宣言の除去のみ）・import 以外の属性と children の原文が不変であることを
// TypeScript AST で機械照合する（ax2b-ast-check.cjs と同方式）。対象外の input / TextFieldControl も前後で完全一致を要求する。
// 使い方: node ay2b-ast-check.cjs before | after
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const OUT = path.join(__dirname, "ay2b-ast-check.json");
const TARGETS = JSON.parse(String.raw`["frontend/src/components/ChannelTypeCombobox.tsx:91","frontend/src/components/CountryCombobox.tsx:90","frontend/src/components/InventoryPicker.tsx:217","frontend/src/components/OrderFinancialPanel.tsx:223","frontend/src/components/PurchaseDetailPanel.tsx:328","frontend/src/components/PurchaseDetailPanel.tsx:338","frontend/src/components/PurchaseDetailPanel.tsx:361","frontend/src/components/PurchaseDetailPanel.tsx:385","frontend/src/components/PurchaseDetailPanel.tsx:412","frontend/src/components/ShippingDetailPanel.tsx:401","frontend/src/components/ShippingDetailPanel.tsx:425","frontend/src/components/ShippingDetailPanel.tsx:449","frontend/src/components/ShippingDetailPanel.tsx:476","frontend/src/components/ShippingDetailPanel.tsx:487","frontend/src/components/ShippingDetailPanel.tsx:529","frontend/src/components/ShippingDetailPanel.tsx:539","frontend/src/pages/account-settings/ProfileSection.tsx:163","frontend/src/pages/account-settings/ProfileSection.tsx:169","frontend/src/pages/account-settings/ProfileSection.tsx:173","frontend/src/pages/account-settings/ProfileSection.tsx:180","frontend/src/pages/account-settings/ProfileSection.tsx:184","frontend/src/pages/account-settings/ProfileSection.tsx:191","frontend/src/pages/account-settings/ProfileSection.tsx:195","frontend/src/pages/account-settings/SecuritySection.tsx:67","frontend/src/pages/account-settings/SecuritySection.tsx:79","frontend/src/pages/account-settings/SecuritySection.tsx:91","frontend/src/pages/admin/TenantPolicyPage.tsx:192","frontend/src/pages/admin/TenantPolicyPage.tsx:207","frontend/src/pages/admin/TenantPolicyPage.tsx:222","frontend/src/pages/admin/TenantPolicyPage.tsx:238","frontend/src/pages/admin/TenantPolicyPage.tsx:253","frontend/src/pages/admin/TenantProfilePage.tsx:145","frontend/src/pages/admin/TenantProfilePage.tsx:158","frontend/src/pages/admin/TenantProfilePage.tsx:183","frontend/src/pages/admin/TenantProfilePage.tsx:196","frontend/src/pages/admin/TenantProfilePage.tsx:209","frontend/src/pages/admin/TenantProfilePage.tsx:222","frontend/src/pages/badges/BadgesPage.tsx:61","frontend/src/pages/badges/BadgesPage.tsx:62","frontend/src/pages/badges/BadgesPage.tsx:64","frontend/src/pages/badges/BadgesPage.tsx:66","frontend/src/pages/bots/BotFormFields.tsx:54","frontend/src/pages/bots/BotFormFields.tsx:83","frontend/src/pages/bots/BotFormFields.tsx:90","frontend/src/pages/bots/BotsPage.tsx:228","frontend/src/pages/bots/BotsPage.tsx:231","frontend/src/pages/bots/BotsPage.tsx:255","frontend/src/pages/bots/BotsPage.tsx:258","frontend/src/pages/buddy/BuddyPage.tsx:65","frontend/src/pages/buddy/BuddyPage.tsx:66","frontend/src/pages/companies/CompanyFormFields.tsx:37","frontend/src/pages/companies/CompanyFormFields.tsx:51","frontend/src/pages/companies/CompanyFormFields.tsx:58","frontend/src/pages/contacts/ContactEditPage.tsx:154","frontend/src/pages/contacts/ContactEditPage.tsx:157","frontend/src/pages/contacts/ContactEditPage.tsx:160","frontend/src/pages/contacts/ContactEditPage.tsx:163","frontend/src/pages/contacts/ContactEditPage.tsx:166","frontend/src/pages/contacts/ContactEditPage.tsx:175","frontend/src/pages/contacts/ContactEditPage.tsx:178","frontend/src/pages/contacts/ContactFormFields.tsx:56","frontend/src/pages/contacts/ContactFormFields.tsx:63","frontend/src/pages/contacts/ContactFormFields.tsx:70","frontend/src/pages/contacts/ContactFormFields.tsx:78","frontend/src/pages/integrations/CarrierCredentialForm.tsx:95","frontend/src/pages/integrations/CarrierCredentialForm.tsx:106","frontend/src/pages/integrations/CarrierCredentialForm.tsx:121","frontend/src/pages/integrations/FedexLabelValidationTab.tsx:334","frontend/src/pages/integrations/FedexLabelValidationTab.tsx:345","frontend/src/pages/integrations/FedexLabelValidationTab.tsx:356","frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx:162","frontend/src/pages/integrations/PaypalIntegrationPage.tsx:144","frontend/src/pages/integrations/PaypalIntegrationPage.tsx:154","frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:317","frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:419","frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:423","frontend/src/pages/leads/LeadEditPage.tsx:172","frontend/src/pages/leads/LeadEditPage.tsx:175","frontend/src/pages/leads/LeadEditPage.tsx:178","frontend/src/pages/leads/LeadEditPage.tsx:181","frontend/src/pages/leads/LeadEditPage.tsx:277","frontend/src/pages/leads/LeadFormFields.tsx:110","frontend/src/pages/leads/LeadFormFields.tsx:118","frontend/src/pages/leads/LeadFormFields.tsx:126","frontend/src/pages/leads/LeadsPage.tsx:330","frontend/src/pages/leads/LeadsPage.tsx:333","frontend/src/pages/leads/LeadsPage.tsx:336","frontend/src/pages/leads/LeadsPage.tsx:339","frontend/src/pages/leads/LeadsPage.tsx:427","frontend/src/pages/leads/LeadsPage.tsx:465","frontend/src/pages/leads/LeadsPage.tsx:468","frontend/src/pages/login/LoginPage.tsx:93","frontend/src/pages/login/LoginPage.tsx:104","frontend/src/pages/login/LoginPage.tsx:136","frontend/src/pages/notifications/NotificationsPage.tsx:63","frontend/src/pages/notifications/NotificationsPage.tsx:64","frontend/src/pages/orders/OrdersFormModal.tsx:72","frontend/src/pages/orders/OrdersFormModal.tsx:80","frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:191","frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:194","frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:197","frontend/src/pages/quote-create/QuoteCreatePage.tsx:165","frontend/src/pages/quote-create/QuoteCreatePage.tsx:268","frontend/src/pages/quote-create/QuoteCreatePage.tsx:273","frontend/src/pages/roles/RolesPage.tsx:494","frontend/src/pages/roles/RolesPage.tsx:556","frontend/src/pages/shifts/ShiftsPage.tsx:63","frontend/src/pages/shifts/ShiftsPage.tsx:64","frontend/src/pages/shifts/ShiftsPage.tsx:65","frontend/src/pages/shifts/ShiftsPage.tsx:66","frontend/src/pages/staff-reports/StaffReportsPage.tsx:90","frontend/src/pages/staff/StaffEditPage.tsx:161","frontend/src/pages/staff/StaffEditPage.tsx:164","frontend/src/pages/staff/StaffEditPage.tsx:167","frontend/src/pages/staff/StaffEditPage.tsx:170","frontend/src/pages/staff/StaffEditPage.tsx:173","frontend/src/pages/staff/StaffEditPage.tsx:176","frontend/src/pages/staff/StaffEditPage.tsx:179","frontend/src/pages/staff/StaffEditPage.tsx:182","frontend/src/pages/staff/StaffEditPage.tsx:203","frontend/src/pages/staff/StaffFormFields.tsx:43","frontend/src/pages/staff/StaffFormFields.tsx:51","frontend/src/pages/staff/StaffFormFields.tsx:59","frontend/src/pages/staff/StaffFormFields.tsx:82","frontend/src/pages/staff/StaffPage.tsx:238","frontend/src/pages/staff/StaffPage.tsx:241","frontend/src/pages/staff/StaffPage.tsx:244","frontend/src/pages/staff/StaffPage.tsx:247","frontend/src/pages/staff/StaffPage.tsx:250","frontend/src/pages/staff/StaffPage.tsx:253","frontend/src/pages/staff/StaffPage.tsx:256","frontend/src/pages/staff/StaffPage.tsx:259","frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:464","frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:467","frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:470","frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:516","frontend/src/pages/suppliers/SupplierFormFields.tsx:32","frontend/src/pages/suppliers/SupplierFormFields.tsx:40","frontend/src/pages/suppliers/SupplierFormFields.tsx:47","frontend/src/pages/suppliers/SupplierFormFields.tsx:55","frontend/src/pages/teams/TeamFormFields.tsx:28","frontend/src/pages/teams/TeamFormFields.tsx:36","frontend/src/pages/teams/TeamsPage.tsx:242"]`);
const LOGIN = ["frontend/src/pages/login/LoginPage.tsx:93","frontend/src/pages/login/LoginPage.tsx:104","frontend/src/pages/login/LoginPage.tsx:136"];
const FILES = [...new Set(TARGETS.map((s) => s.slice(0, s.lastIndexOf(":"))))].sort();
const TAGS = new Set(["input", "TextFieldControl"]);
const REMOVED_CLASSES = new Set(['"input"']);
const PLACEMENT = /^(width|minWidth|maxWidth|flex|flexGrow|flexShrink|flexBasis|margin[A-Za-z]*)$/;
const styleProps = (src) => {
  if (src === null) return null;
  const sf = ts.createSourceFile("s.tsx", `const x = <i style=${src} />;`, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  let obj = null; (function v(n) { if (ts.isObjectLiteralExpression(n) && !obj) obj = n; ts.forEachChild(n, v); })(sf);
  if (!obj) return { unparsed: src };
  return Object.fromEntries(obj.properties.map((p) => [p.name ? p.name.getText(sf) : p.getText(sf), p.initializer ? p.initializer.getText(sf) : p.getText(sf)]));
};
function extract(relPath) {
  const text = fs.readFileSync(path.join(ROOT, relPath), "utf8");
  const sf = ts.createSourceFile(relPath, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const found = [];
  const visit = (node) => {
    if (ts.isJsxSelfClosingElement(node) || ts.isJsxElement(node)) {
      const open = ts.isJsxElement(node) ? node.openingElement : node;
      const tag = open.tagName.getText(sf);
      if (TAGS.has(tag)) {
        const attrs = {}; let className = null; let style = null; let spread = 0;
        for (const a of open.attributes.properties) {
          if (ts.isJsxSpreadAttribute(a)) { spread += 1; attrs["..." + a.expression.getText(sf)] = "(spread)"; continue; }
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
  if (b.length !== a.length) return { rows: [{ error: `count mismatch before=${b.length} after=${a.length}` }], removedStyle: [] };
  const removedStyle = [];
  const rows = b.map((x, i) => {
    const y = a[i]; const diffs = [];
    const isTarget = TARGETS.includes(x.file + ":" + x.line); const isLogin = LOGIN.includes(x.file + ":" + x.line);
    if (x.file !== y.file) diffs.push(`file ${x.file} -> ${y.file}`);
    if (x.spread !== y.spread) diffs.push("spread attrs differ");
    if (x.children !== y.children) diffs.push("children differ");
    if (!isTarget) {
      if (x.tag !== y.tag) diffs.push(`non-target tag ${x.tag} -> ${y.tag}`);
      if (x.className !== y.className) diffs.push(`non-target className ${x.className} -> ${y.className}`);
      if (x.style !== y.style) diffs.push(`non-target style changed`);
      for (const k of new Set([...Object.keys(x.attrs), ...Object.keys(y.attrs)])) if (x.attrs[k] !== y.attrs[k]) diffs.push(`non-target attr ${k}: ${x.attrs[k]} -> ${y.attrs[k]}`);
      return { index: i + 1, file: x.file, beforeLine: x.line, afterLine: y.line, target: false, diffs };
    }
    if (x.tag !== "input") diffs.push(`before tag ${x.tag}`);
    if (y.tag !== "TextFieldControl") diffs.push(`after tag ${y.tag}`);
    const expAttrs = { ...x.attrs }; if (isLogin) expAttrs.variant = '"login"';
    for (const k of new Set([...Object.keys(expAttrs), ...Object.keys(y.attrs)])) if (expAttrs[k] !== y.attrs[k]) diffs.push(`attr ${k}: ${expAttrs[k]} -> ${y.attrs[k]}`);
    const expectClass = x.className !== null && REMOVED_CLASSES.has(x.className) ? null : x.className;
    if (x.className !== null && !REMOVED_CLASSES.has(x.className)) diffs.push(`unexpected before className ${x.className}`);
    if (y.className !== expectClass) diffs.push(`after className ${y.className} != ${expectClass}`);
    const bs = styleProps(x.style), as = styleProps(y.style);
    if (bs === null) { if (as !== null) diffs.push(`after style added ${y.style}`); }
    else {
      const placementB = Object.fromEntries(Object.entries(bs).filter(([k]) => PLACEMENT.test(k)));
      const removed = Object.entries(bs).filter(([k]) => !PLACEMENT.test(k));
      if (removed.length) removedStyle.push({ file: x.file, line: x.line, removed: removed.map(([k, v]) => `${k}: ${v}`) });
      const asObj = as || {};
      if (JSON.stringify(placementB) !== JSON.stringify(asObj)) diffs.push(`after style ${y.style} != placement-only of before ${JSON.stringify(placementB)}`);
    }
    return { index: i + 1, file: x.file, beforeLine: x.line, afterLine: y.line, target: true, beforeClass: x.className, afterClass: y.className, beforeStyle: x.style, afterStyle: y.style, diffs };
  });
  for (const f of FILES) if (after.uiAllow[f] !== before.uiAllow[f]) rows.push({ file: f, diffs: [`ui-allow count ${after.uiAllow[f]} != ${before.uiAllow[f]}`] });
  return { rows, removedStyle };
}
const mode = process.argv[2];
if (mode === "before") {
  const before = collect();
  const nTarget = before.elements.filter((e) => TARGETS.includes(e.file + ":" + e.line)).length;
  fs.writeFileSync(OUT, JSON.stringify({ before, after: null, result: null }, null, 2) + "\n");
  console.log(`before: ${before.elements.length} elements (input/TextFieldControl) in ${FILES.length} files, targets ${nTarget}, ui-allow total ${Object.values(before.uiAllow).reduce((n, v) => n + v, 0)} saved to ${path.relative(ROOT, OUT)}`);
  process.exit(nTarget === 143 && TARGETS.length === 143 && LOGIN.length === 3 ? 0 : 1);
} else if (mode === "after") {
  const saved = JSON.parse(fs.readFileSync(OUT, "utf8"));
  const after = collect(); const { rows, removedStyle } = compare(saved.before, after);
  const totalDiffs = rows.reduce((n, r) => n + (r.error ? 1 : r.diffs.length), 0);
  const nTarget = after.elements.filter((e) => e.tag === "TextFieldControl").length;
  const result = { elements: after.elements.length, targetsAfter: rows.filter((r) => r.target).length, totalDiffs, removedStyle, rows };
  fs.writeFileSync(OUT, JSON.stringify({ before: saved.before, after, result }, null, 2) + "\n");
  console.log(JSON.stringify({ elements: result.elements, targets: result.targetsAfter, totalDiffs, removedStyle, nonEmpty: rows.filter((r) => r.diffs.length) }, null, 2));
  process.exit(totalDiffs === 0 && result.targetsAfter === 143 ? 0 : 1);
} else { console.error("usage: node ay2b-ast-check.cjs before|after"); process.exit(2); }
