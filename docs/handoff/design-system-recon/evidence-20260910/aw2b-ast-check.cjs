// AW-2b: 一般フォームの生 select 53件を SelectControl へ移管した前後で、
// タグ名・className・style 以外の属性と children の原文が不変であることを TypeScript AST で機械照合する。
// 使い方: node aw2b-ast-check.cjs before | after
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../../../..");
const ts = require(path.join(ROOT, "frontend/node_modules/typescript"));
const OUT = path.join(__dirname, "aw2b-ast-check.json");
const plan = JSON.parse(fs.readFileSync(path.join(__dirname, "aw2b-plan.json"), "utf8"));

const FILES = [...new Set(plan.plans.map((p) => p.file))];
const PLAN_BY_FILE = {};
for (const p of plan.plans) (PLAN_BY_FILE[p.file] ??= []).push(p);
const TARGET_TAGS = new Set(["select", "SelectControl"]);
const ADDED_ATTRS = new Set(["size", "fullWidth"]);
const KEEP_CLASSES = new Set(["field-w-sm", "gs-select", "account-settings-lang-select"]);

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
        let style = null;
        let spread = 0;
        for (const a of open.attributes.properties) {
          if (ts.isJsxSpreadAttribute(a)) { spread += 1; continue; }
          const name = a.name.getText(sf);
          const value = a.initializer ? a.initializer.getText(sf) : "true";
          if (name === "className") className = value;
          else if (name === "style") style = value;
          else attrs[name] = value;
        }
        found.push({
          file: relPath,
          line: sf.getLineAndCharacterOfPosition(open.getStart(sf)).line + 1,
          tag,
          className,
          style,
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

const collect = () => FILES.flatMap(extract);

function expectedClass(beforeClass) {
  if (beforeClass === null) return null;
  const tokens = beforeClass.replace(/^"|"$/g, "").split(/\s+/).filter((t) => KEEP_CLASSES.has(t));
  return tokens.length ? `"${tokens.join(" ")}"` : null;
}

function compare(before, after) {
  const rows = [];
  if (before.length !== after.length) {
    rows.push({ error: `count mismatch before=${before.length} after=${after.length}` });
    return rows;
  }
  const rawIndexByFile = {};
  before.forEach((b, i) => {
    const a = after[i];
    const diffs = [];
    if (b.file !== a.file) diffs.push(`file ${b.file} -> ${a.file}`);
    if (b.spread !== a.spread) diffs.push("spread attrs differ");
    if (b.children !== a.children) diffs.push("children differ");
    const isRaw = b.tag === "select";
    let planRow = null;
    let added = [];
    if (isRaw) {
      const k = (rawIndexByFile[b.file] = (rawIndexByFile[b.file] ?? -1) + 1);
      planRow = PLAN_BY_FILE[b.file][k];
      if (a.tag !== "SelectControl") diffs.push(`after tag ${a.tag}`);
    } else if (a.tag !== b.tag) {
      diffs.push(`preexisting tag ${b.tag} -> ${a.tag}`);
    }
    const bKeys = Object.keys(b.attrs);
    const aKeys = Object.keys(a.attrs).filter((k) => !(isRaw && ADDED_ATTRS.has(k)));
    for (const k of new Set([...bKeys, ...aKeys])) {
      if (b.attrs[k] !== a.attrs[k]) diffs.push(`attr ${k}: ${b.attrs[k]} -> ${a.attrs[k]}`);
    }
    if (isRaw) {
      added = Object.keys(a.attrs).filter((k) => ADDED_ATTRS.has(k)).sort();
      const expAdded = [];
      if (planRow.fullWidth) expAdded.push("fullWidth");
      if (planRow.moldSize !== "md") expAdded.push("size");
      expAdded.sort();
      if (JSON.stringify(added) !== JSON.stringify(expAdded)) diffs.push(`added attrs ${added} != ${expAdded}`);
      if (a.attrs.size !== undefined && a.attrs.size !== `"${planRow.moldSize}"`) diffs.push(`size ${a.attrs.size} != ${planRow.moldSize}`);
      if (a.attrs.fullWidth !== undefined && a.attrs.fullWidth !== "true") diffs.push(`fullWidth ${a.attrs.fullWidth}`);
      if (a.className !== expectedClass(b.className)) diffs.push(`after className ${a.className} != ${expectedClass(b.className)}`);
      if (a.style !== null) diffs.push(`after style remains ${a.style}`);
      if (b.style !== null && !planRow.inlineStyleText) diffs.push(`unexpected before style ${b.style}`);
    } else {
      if (b.className !== a.className) diffs.push(`preexisting className ${b.className} -> ${a.className}`);
      if (b.style !== a.style) diffs.push(`preexisting style ${b.style} -> ${a.style}`);
    }
    rows.push({
      index: i + 1,
      file: b.file,
      raw: isRaw,
      beforeLine: b.line,
      afterLine: a.line,
      beforeClass: b.className,
      afterClass: a.className,
      beforeStyle: b.style,
      addedAttrs: added.map((k) => `${k}=${a.attrs[k]}`),
      diffs,
    });
  });
  return rows;
}

const mode = process.argv[2];
if (mode === "before") {
  const before = collect();
  const raw = before.filter((e) => e.tag === "select").length;
  fs.writeFileSync(OUT, JSON.stringify({ before, after: null, result: null }, null, 2) + "\n");
  console.log(`before: ${before.length} elements (raw select ${raw}) in ${FILES.length} files saved to ${path.relative(ROOT, OUT)}`);
  process.exit(raw === 53 ? 0 : 1);
} else if (mode === "after") {
  const saved = JSON.parse(fs.readFileSync(OUT, "utf8"));
  const after = collect();
  const rows = compare(saved.before, after);
  const totalDiffs = rows.reduce((n, r) => n + (r.error ? 1 : r.diffs.length), 0);
  const rawAfter = after.filter((e) => e.tag === "select").length;
  const result = { elements: after.length, rawSelectRemaining: rawAfter, totalDiffs, rows };
  fs.writeFileSync(OUT, JSON.stringify({ before: saved.before, after, result }, null, 2) + "\n");
  console.log(JSON.stringify(result, null, 2));
  process.exit(totalDiffs === 0 && rawAfter === 0 ? 0 : 1);
} else {
  console.error("usage: node aw2b-ast-check.cjs before|after");
  process.exit(2);
}
