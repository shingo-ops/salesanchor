// AY-2b 非 text input に当たりうる CSS 規則のうち、詳細度が絞り込み前後で勝敗を変えうるものを全列挙する。
// 使い方: node ay2b-nontext-competing.cjs <出力md>   （作業ツリーの frontend/src/**/*.css を走査）
const fs = require("fs"), path = require("path");
const ROOT = path.resolve(__dirname, "../../../..");
const postcss = require(path.join(ROOT, "frontend/node_modules/postcss"));
const psp = require(path.join(ROOT, "frontend/node_modules/postcss-selector-parser"));
const files = [];
(function walk(d) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p); else if (e.name.endsWith(".css")) files.push(p); } })(path.join(ROOT, "frontend/src"));
const spec = (node) => { // [a,b,c]
  let a = 0, b = 0, c = 0;
  node.walk((n) => {
    if (n.type === "id") a++;
    else if (n.type === "class" || n.type === "attribute") b++;
    else if (n.type === "tag") c++;
    else if (n.type === "pseudo") {
      const v = n.value.toLowerCase();
      if (v === ":where") return;
      if (v === ":not" || v === ":is" || v === ":has" || v === ":matches") {
        let m = [0, 0, 0]; n.each((arg) => { const s = spec(arg); if (s[0] > m[0] || (s[0] === m[0] && (s[1] > m[1] || (s[1] === m[1] && s[2] > m[2])))) m = s; });
        a += m[0]; b += m[1]; c += m[2]; n.__skip = true;
      } else if (v.startsWith("::") || [":before", ":after", ":first-line", ":first-letter"].includes(v)) c++; else b++;
    }
  });
  // :not 等の中身は walk で二重加算されるので引く
  node.walk((n) => { if (n.type === "pseudo" && n.__skip) n.walk((m) => { if (m === n) return; if (m.type === "id") a--; else if (m.type === "class" || m.type === "attribute") b--; else if (m.type === "tag") c--; else if (m.type === "pseudo") { const v = m.value.toLowerCase(); if (v !== ":where") { if (v.startsWith("::")) c--; else b--; } } }); });
  return [a, b, c];
};
const cmp = (x, y) => x[0] - y[0] || x[1] - y[1] || x[2] - y[2];
const rows = []; const total = { rules: 0, selectors: 0 };
for (const f of files) {
  const rel = path.relative(ROOT, f); const root = postcss.parse(fs.readFileSync(f, "utf8"), { from: rel });
  root.walkRules((r) => {
    if (r.parent && r.parent.type === "atrule" && /keyframes/.test(r.parent.name)) return;
    total.rules++;
    const at = []; for (let p = r.parent; p && p.type === "atrule"; p = p.parent) at.push("@" + p.name + " " + p.params);
    for (const sel of r.selectors) {
      total.selectors++;
      let ast; try { ast = psp().astSync(sel); } catch (e) { continue; }
      const s0 = ast.nodes[0]; // 複合セレクタの列から主語（最後の複合）を取る
      let subj = []; for (const n of s0.nodes) { if (n.type === "combinator") subj = []; else subj.push(n); }
      const hasTag = subj.find((n) => n.type === "tag"); const tagName = hasTag ? hasTag.value.toLowerCase() : null;
      const typeAttr = subj.find((n) => n.type === "attribute" && n.attribute === "type");
      const universal = subj.find((n) => n.type === "universal");
      const only = subj.every((n) => n.type === "pseudo");
      // 主語が input、または type 属性だけ、または * / 疑似クラスだけ（クラス名なし）の規則 = クラスを持たない input に当たりうる
      const hasClass = subj.some((n) => n.type === "class" || n.type === "id");
      const target = tagName === "input" || (!tagName && typeAttr && !hasClass) || ((universal || only || (!tagName && subj.every((n) => n.type === "pseudo"))) && !hasClass);
      if (!target) continue;
      const sp = spec(s0);
      const decls = []; r.walkDecls((d) => decls.push(d.prop + ": " + d.value));
      rows.push({ file: rel, line: r.source.start.line, selector: sel.replace(/\s+/g, " "), spec: sp, at: at.join(" "), decls, focusLike: /:focus|:active|:checked|:disabled|:hover/.test(sel), tag: tagName || "-" });
    }
  });
}
const lo = [0, 1, 1], hi = [0, 3, 1];
const inRange = rows.filter((r) => cmp(r.spec, lo) >= 0 && cmp(r.spec, hi) <= 0).sort((x, y) => cmp(x.spec, y.spec) || x.file.localeCompare(y.file) || x.line - y.line);
const fmt = (s) => `(${s.join(",")})`;
let md = `# 非 text input に当たりうる CSS 規則（詳細度 (0,1,1)〜(0,3,1)）\n\n走査: frontend/src の CSS ${files.length} ファイル、規則 ${total.rules}、セレクタ ${total.selectors}。主語が input、または type 属性だけ、または * / 疑似クラスだけ（クラス・id を持たない input に当たりうる）規則のうち、候補全体 ${rows.length} 件。\n範囲の根拠: 通常状態は旧 .form-group input (0,1,1) → 新 .form-group input[type] (0,2,1)、:focus は旧 (0,2,1) → 新 (0,3,1)。この間にある規則は勝敗が変わりうる。\n\n対象範囲内: ${inRange.length} 件\n\n| file:line | selector | 詳細度 | at-rule | 宣言 |\n|---|---|---|---|---|\n`;
for (const r of inRange) md += `| ${r.file}:${r.line} | \`${r.selector}\` | ${fmt(r.spec)} | ${r.at || "-"} | ${r.decls.join("; ").replace(/\|/g, "\\|")} |\n`;
md += `\n## 参考: 範囲外の候補（詳細度が範囲外、勝敗は絞り込み前後で変わらない）: ${rows.length - inRange.length} 件\n`;
fs.writeFileSync(process.argv[2], md); fs.writeFileSync(process.argv[2].replace(/\.md$/, ".json"), JSON.stringify({ total, inRange, all: rows }, null, 1));
console.log(JSON.stringify({ files: files.length, ...total, candidates: rows.length, inRange: inRange.length }));
