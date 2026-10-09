// AW-2a: 13件の select を SelectControl へ移管した前後で、タグ名・className 以外の
// 属性と children の原文が不変であることを TypeScript AST で機械照合する。
// 使い方: node aw2a-ast-check.cjs before | after
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const OUT = path.join(__dirname, "aw2a-ast-check.json");

const FILES = [
  "frontend/src/pages/inbox/InboxKartePanel.tsx",
  "frontend/src/pages/inbox/InboxProfileModal.tsx",
  "frontend/src/pages/dashboard/DashboardPage.tsx",
  "frontend/src/pages/inbox/InboxPage.tsx",
  "frontend/src/pages/inbox/InboxMessageThread.tsx",
];
const TARGET_TAGS = new Set(["select", "SelectControl"]);
const ADDED_ATTRS = new Set(["variant", "fullWidth"]);

function extract(relPath) {
  const text = fs.readFileSync(path.join(ROOT, relPath), "utf8");
  const sf = ts.createSourceFile(relPath, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const found = [];
  const visit = (node) => {
    if (ts.isJsxElement(node)) {
      const open = node.openingElement;
      const tag = open.tagName.getText(sf);
      if (TARGET_TAGS.has(tag)) {
        const attrs = {};
        let className = null;
        let spread = 0;
        for (const a of open.attributes.properties) {
          if (ts.isJsxSpreadAttribute(a)) { spread += 1; continue; }
          const name = a.name.getText(sf);
          const value = a.initializer ? a.initializer.getText(sf) : "true";
          if (name === "className") className = value;
          else attrs[name] = value;
        }
        found.push({
          file: relPath,
          line: sf.getLineAndCharacterOfPosition(open.getStart(sf)).line + 1,
          tag,
          className,
          attrs,
          spread,
          children: text.slice(open.end, node.closingElement.pos),
        });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return found;
}

function collect() {
  return FILES.flatMap(extract);
}

function compare(before, after) {
  const rows = [];
  if (before.length !== after.length) {
    rows.push({ error: `count mismatch before=${before.length} after=${after.length}` });
    return rows;
  }
  before.forEach((b, i) => {
    const a = after[i];
    const diffs = [];
    if (b.file !== a.file) diffs.push(`file ${b.file} -> ${a.file}`);
    if (a.tag !== "SelectControl") diffs.push(`after tag ${a.tag}`);
    if (b.spread !== a.spread) diffs.push("spread attrs differ");
    if (b.children !== a.children) diffs.push("children differ");
    const bKeys = Object.keys(b.attrs);
    const aKeys = Object.keys(a.attrs).filter((k) => !ADDED_ATTRS.has(k));
    for (const k of new Set([...bKeys, ...aKeys])) {
      if (b.attrs[k] !== a.attrs[k]) diffs.push(`attr ${k}: ${b.attrs[k]} -> ${a.attrs[k]}`);
    }
    const added = Object.keys(a.attrs).filter((k) => ADDED_ATTRS.has(k)).sort();
    const bClass = b.className;
    let expectedAdded;
    let expectedClass;
    if (bClass === '"right-panel-field"') { expectedAdded = ["fullWidth", "variant"]; expectedClass = null; }
    else if (bClass === '"page-header-select"') { expectedAdded = ["variant"]; expectedClass = null; }
    else if (bClass === '"inbox-platform-select"') { expectedAdded = ["variant"]; expectedClass = '"inbox-platform-select"'; }
    else { diffs.push(`unexpected before className ${bClass}`); }
    if (expectedAdded) {
      if (JSON.stringify(added) !== JSON.stringify(expectedAdded)) diffs.push(`added attrs ${added} != ${expectedAdded}`);
      if (a.className !== expectedClass) diffs.push(`after className ${a.className} != ${expectedClass}`);
    }
    rows.push({
      index: i + 1,
      file: b.file,
      beforeLine: b.line,
      afterLine: a.line,
      beforeClass: bClass,
      afterClass: a.className,
      addedAttrs: added.map((k) => `${k}=${a.attrs[k]}`),
      diffs,
    });
  });
  return rows;
}

const mode = process.argv[2];
if (mode === "before") {
  const before = collect();
  fs.writeFileSync(OUT, JSON.stringify({ before, after: null, result: null }, null, 2) + "\n");
  console.log(`before: ${before.length} elements saved to ${path.relative(ROOT, OUT)}`);
  process.exit(before.length === 13 ? 0 : 1);
} else if (mode === "after") {
  const saved = JSON.parse(fs.readFileSync(OUT, "utf8"));
  const after = collect();
  const rows = compare(saved.before, after);
  const totalDiffs = rows.reduce((n, r) => n + (r.error ? 1 : r.diffs.length), 0);
  const result = { elements: after.length, totalDiffs, rows };
  fs.writeFileSync(OUT, JSON.stringify({ before: saved.before, after, result }, null, 2) + "\n");
  console.log(JSON.stringify(result, null, 2));
  process.exit(totalDiffs === 0 && after.length === 13 ? 0 : 1);
} else {
  console.error("usage: node aw2a-ast-check.cjs before|after");
  process.exit(2);
}
