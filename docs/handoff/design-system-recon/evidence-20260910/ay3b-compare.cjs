// AY-3b: 前後 JSON の差を場所ごとに集約して出す。node ay3b-compare.cjs before.json after.json
const fs = require("fs");
const B = JSON.parse(fs.readFileSync(process.argv[2])).results, A = JSON.parse(fs.readFileSync(process.argv[3])).results;
const GROUPS = { "Inbox(4)": [["modal", [0, 1, 2, 3]]], "Preferences(1)": [["pref", [0]]], "Schedule(3)": [["allday", [0]], ["settings", [0, 1]]] };
const EXPECT = new Set(["knobLeftEdge", "trackW", "trackH", "labelW", "labelH", "knobW", "knobH", "knobMove", "knobRightGap", "knobShadow", "radius", "trackTransition", "knobTransition", "trackShadow", "role", "name"]);
const agg = {}; // group -> field -> "b -> a" -> count
let total = 0, unexpected = [];
const add = (g, f, b, a, cond) => { const k = `${b} -> ${a}`; ((agg[g] ??= {})[f] ??= {})[k] ??= []; agg[g][f][k].push(cond); };
for (const key of Object.keys(B)) {
  const [vw, theme, page] = key.split("/");
  for (const [g, list] of Object.entries(GROUPS)) for (const [pg, idxs] of list) {
    if (pg !== page) continue;
    for (const st of ["off", "on"]) for (const i of idxs) {
      const b = B[key][st].toggles[i], a = A[key][st].toggles[i];
      for (const f of Object.keys(b)) { total++; if (JSON.stringify(b[f]) !== JSON.stringify(a[f])) { add(g, st + ":" + f, b[f], a[f], `${vw}/${theme}/${pg}#${i}`); if (!EXPECT.has(f)) unexpected.push([g, st, f, b[f], a[f], key, i]); } }
      // 状態の移動量: ON の knobLeftEdge は ON 状態で比較済み
    }
    B[key].on.rows.forEach((br, j) => { const ar = A[key].on.rows[j]; for (const f of Object.keys(br)) if (JSON.stringify(br[f]) !== JSON.stringify(ar[f])) add(g, "row." + f, br[f], ar[f], `${vw}/${theme}/${pg}/row${j}`); });
    B[key].focus.forEach((bf, j) => { const af = A[key].focus[j]; if (idxs.includes(j)) { if (bf.trackShadow !== af.trackShadow || bf.tabbed !== af.tabbed) add(g, "focus.trackShadow", bf.tabbed ? bf.trackShadow : "(not tabbed)", af.tabbed ? af.trackShadow : "(not tabbed)", `${vw}/${theme}/${pg}#${j}`); } });
  }
}
for (const [g, fs_] of Object.entries(agg)) { console.log("## " + g); for (const [f, m] of Object.entries(fs_)) for (const [k, conds] of Object.entries(m)) console.log(`${f}: ${k}  [${conds.length}件: ${[...new Set(conds.map((c) => c.split("/")[0] + "/" + c.split("/")[1]))].join(",")}]`); }
console.log("\n比較した値の数:", total, " 期待外の項目の差:", unexpected.length);
for (const u of unexpected) console.log("UNEXPECTED", JSON.stringify(u));
