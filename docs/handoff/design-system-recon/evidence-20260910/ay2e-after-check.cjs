// AY-2e: before/after JSON（ay2e-capture.cjs の出力）から判定表を作る。使い方: node ay2e-after-check.cjs <before.json> <after.json> > ay2e-after-check.md
const fs = require("fs");
const B = JSON.parse(fs.readFileSync(process.argv[2], "utf8")), A = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const isT = (s, i) => s === "discord-announce" ? /^例: 1288/.test(i.ph) : s === "manual-record" ? i.id === "manual-occurred-at" : s === "channel-masters" ? true : s === "commission" ? /^settings-value-/.test(i.testid || "") : s === "own-inventory" ? true : false;
const f = (n) => (Math.round(n * 100) / 100).toString();
const R = (r) => `${f(r.x)},${f(r.y)} ${f(r.w)}x${f(r.h)}`;
let md = "# AY-2e 実画面 前後比較（幅1280、DPR2）\n\n"; let pass = true; const fails = [];
const ALLOWED = new Set(["padding-top","padding-right","padding-bottom","padding-left","border-top-width","border-top-style","border-top-color","border-top-left-radius","font-size","font-family","font-weight","line-height","color","background-color","height","width","box-sizing","outline-style","display","vertical-align","margin-left","margin-top","flex-grow"]);
for (const sb of B.screens.filter((s) => s.w === 1280)) {
  const sa = A.screens.find((s) => s.screen === sb.screen && s.w === 1280);
  md += `## ${sb.screen}\n\n- 描画 before=${sb.ok} after=${sa.ok}、scrollWidth/clientWidth before=${sb.scrollWidth}/${sb.clientWidth} after=${sa.scrollWidth}/${sa.clientWidth}\n- 重なり(操作要素) before=${sb.overlaps.length} after=${sa.overlaps.length}、入力と文字の重なり before=${sb.textOverlaps.length} after=${sa.textOverlaps.length}、右はみ出し(操作要素) before=${JSON.stringify(sb.outRight)} after=${JSON.stringify(sa.outRight)}\n`;
  if (!sa.ok || sa.scrollWidth > sa.clientWidth || sa.overlaps.length || sa.textOverlaps.length) { pass = false; fails.push(sb.screen + ": 描画/はみ出し/重なり"); }
  if (JSON.stringify(sb.outRight) !== JSON.stringify(sa.outRight)) { pass = false; fails.push(sb.screen + ": 右はみ出しが前後で違う"); }
  const tb = sb.items.filter((i) => isT(sb.screen, i)), ta = sa.items.filter((i) => isT(sa.screen, i));
  if (tb.length !== ta.length) { pass = false; fails.push(sb.screen + " target count"); }
  tb.forEach((b, k) => {
    const a = ta[k]; const name = b.testid || b.id || b.ph || b.aria;
    md += `\n### ${sb.screen} / ${name} (${b.type})\n\n| 項目 | before | after |\n|---|---|---|\n| bbox | ${R(b.rect)} | ${R(a.rect)} |\n| className | ${b.cls} | ${a.cls} |\n| style属性 | ${b.style} | ${a.style} |\n`;
    const diffs = []; for (const k2 of Object.keys(b.cs)) if (b.cs[k2] !== a.cs[k2]) diffs.push(k2);
    md += `| computed差(項目) | ${diffs.length} 項目 | ${diffs.join(", ")} |\n\n| computed | before | after |\n|---|---|---|\n`;
    for (const k2 of diffs) md += `| ${k2} | ${b.cs[k2]} | ${a.cs[k2]} |\n`;
    const bad = diffs.filter((d) => !ALLOWED.has(d)); if (bad.length) { pass = false; fails.push(name + " computed差想定外 " + bad); }
    md += `\n同じ行の兄弟（親 ${b.parentTag}.${b.parentCls}）:\n\n| 兄弟 | before | after |\n|---|---|---|\n`;
    b.siblings.forEach((s, j) => { const s2 = a.siblings[j]; md += `| ${s.tag} "${s.text}" | ${R(s)} | ${s2 ? R(s2) : "-"} |\n`; });
    b.parentText.forEach((s, j) => { const s2 = a.parentText[j]; md += `| 文字 "${s.t}" | ${R(s)} | ${s2 ? R(s2) : "-"} |\n`; });
    md += `| 親 bbox | ${R(b.parentRect)} | ${R(a.parentRect)} |\n`;
    if (b.row) { md += `\n表の行（td）:\n\n| td | before | after |\n|---|---|---|\n`; b.row.forEach((c, j) => { md += `| ${j} | ${R(c)} | ${R(a.row[j])} |\n`; }); }
  });
  if (sb.screen === "channel-masters" || sb.screen === "own-inventory" || sb.screen === "manual-record") {
    // 行判定: top 差
  }
  if (sb.ths) { md += `\n表の列幅（th）:\n\n| th | before w | after w | 差 |\n|---|---|---|---|\n`; sb.ths.forEach((t, j) => { md += `| ${t.t} | ${f(t.w)} | ${f(sa.ths[j].w)} | ${f(sa.ths[j].w - t.w)} |\n`; }); md += `| table | ${R(sb.tableRect)} | ${R(sa.tableRect)} | |\n`; }
  md += "\n";
}
// 配置判定
const g = (S, k, st) => S.screens.find((s) => s.screen === k && s.w === 1280).items.filter((i) => isT(k, i));
const ch = g(A, "channel-masters"); const chSib = A.screens.find((s) => s.screen === "channel-masters" && s.w === 1280).items[0].siblings.find((s) => s.tag === "button");
const tops = [ch[0].rect.y, ch[1].rect.y, chSib.y];
const chRow = Math.abs(tops[0] - tops[1]) < 1 && Math.abs(ch[0].rect.y + ch[0].rect.h / 2 - (chSib.y + chSib.h / 2)) < 20;
md += `## 判定\n\n- #3/#4 入力2つの top: ${tops.slice(0, 2).map(f)}、ボタン top ${f(tops[2])}、中心差 ${f(Math.abs(ch[0].rect.y + ch[0].rect.h / 2 - (chSib.y + chSib.h / 2)))} → ${chRow ? "1行" : "NG"}\n`;
if (!chRow) { pass = false; fails.push("#3/#4 1行でない"); }
const dis = g(A, "discord-announce")[0], disP = A.screens.find((s) => s.screen === "discord-announce" && s.w === 1280).items[0];
md += `- #1 横幅: input ${f(dis.rect.w)} / 親 ${f(disP.parentRect.w)} → ${Math.abs(dis.rect.w - disP.parentRect.w) < 1 ? "親いっぱい" : "NG"}\n`;
if (Math.abs(dis.rect.w - disP.parentRect.w) >= 1) { pass = false; fails.push("#1 幅"); }
const mr = g(A, "manual-record")[0]; md += `- #2 横幅: input ${f(mr.rect.w)} / 親 ${f(mr.parentRect.w)}（label の下の行: label 文字 ${mr.parentText.map((t) => t.t + " y=" + f(t.y)).join(", ")}、input y=${f(mr.rect.y)}）\n`;
if (Math.abs(mr.rect.w - mr.parentRect.w) >= 1) { pass = false; fails.push("#2 幅"); }
const oi = g(A, "own-inventory")[0]; const lab = oi.parentText.find((t) => t.t === "数量");
const same = lab && Math.abs((oi.rect.y + oi.rect.h / 2) - (lab.y + lab.h / 2)) < 12 && oi.rect.x >= lab.x + lab.w - 0.5;
md += `- #6 「数量」文字 y中心 ${lab ? f(lab.y + lab.h / 2) : "-"}、入力 y中心 ${f(oi.rect.y + oi.rect.h / 2)}、入力 x=${f(oi.rect.x)} 文字右端=${lab ? f(lab.x + lab.w) : "-"} → ${same ? "1行" : "NG"}\n`;
if (!same) { pass = false; fails.push("#6 1行でない"); }
md += `\n判定: ${pass ? "PASS" : "FAIL: " + fails.join(" / ")}\n`;
console.log(md); process.exit(pass ? 0 : 1);
