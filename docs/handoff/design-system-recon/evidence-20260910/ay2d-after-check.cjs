// AY-2d: before/after の採取 JSON(ay2d-capture.cjs) を突き合わせ、ay2d-after-check.md を標準出力へ。
const fs = require("fs"), path = require("path");
const dir = process.argv[2];
const B = require(path.join(dir, "ay2d-before/before.json")), A = require(path.join(dir, "ay2d-after/after.json"));
let md = "# AY-2d 変更後の実画面判定\n\n方法: vite build→preview（Chromium headless shell 1217、DPR2）。API は page.route で /api/v1/public/register を同一 JSON でモック（" + JSON.stringify(B.mock) + "）。Firebase 初期化用に VITE_FIREBASE_* はダミー値でビルド（before/after 同一）。/register は「別の配送先を登録」を選択した状態（全入力欄を表示）で採取。\n\n";
const change = new Map(); let bad = 0;
md += "## 判定表\n\n| 画面 | 幅 | DOM入力数 | scrollWidth/clientWidth before→after | 入力欄どうしの重なり before→after | ラベル文字との重なり before→after | 横はみ出し入力 after | tel 行が1行 after |\n|---|---|---|---|---|---|---|---|\n";
for (let i = 0; i < B.pages.length; i++) {
  const b = B.pages[i], a = A.pages[i];
  if (b.page !== a.page || b.w !== a.w || b.count !== a.count) { md += "ERR mismatch\n"; bad++; continue; }
  const tel = a.tels.filter((t) => "sameRow" in t).map((t) => t.sameRow);
  const ok = a.scrollWidth <= a.clientWidth && a.overlapsInputs.length === 0 && a.overlapsLabelText.length === 0 && a.outOfViewport.length === 0 && tel.every(Boolean);
  if (!ok) bad++;
  md += `| ${a.page} | ${a.w} | ${a.count} | ${b.scrollWidth}/${b.clientWidth} → ${a.scrollWidth}/${a.clientWidth} | ${b.overlapsInputs.length} → ${a.overlapsInputs.length} | ${b.overlapsLabelText.length} → ${a.overlapsLabelText.length} | ${a.outOfViewport.length} | ${tel.length ? tel.join(",") : "-"} |\n`;
  b.items.forEach((x, k) => { const y = a.items[k]; for (const p of Object.keys(x.cs)) if (x.cs[p] !== y.cs[p]) { const key = `${a.w}|${p}|${x.cs[p]} → ${y.cs[p]}`; change.set(key, (change.get(key) || 0) + 1); } });
}
md += "\n## computed style の差（幅|プロパティ|before → after: 件数。DOM入力欄のべ件数）\n\n| 幅 | プロパティ | before → after | 件数 |\n|---|---|---|---|\n";
for (const [k, n] of [...change].sort()) { const [w, p, v] = k.split("|"); md += `| ${w} | ${p} | ${v} | ${n} |\n`; }
const props = new Set([...change.keys()].map((k) => k.split("|")[1]));
const props1280 = [...props].sort();
md += `\n差のあったプロパティ: ${props1280.join(", ")}\n`;
md += `\n判定(はみ出し0・重なり0・tel1行): ${bad === 0 ? "PASS" : "FAIL(" + bad + ")"}\n`;
console.log(md); process.exit(bad ? 1 : 0);
