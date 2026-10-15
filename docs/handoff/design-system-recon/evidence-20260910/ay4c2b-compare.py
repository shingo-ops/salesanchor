# 使い方: python3 ay4c2b-compare.py <measure.json> > ay4c2b-measure-compare.txt
# 前後の全指標を突き合わせ、差を「金型どおり（期待）」か「×（想定外）」に分類する。
import json, sys, re
d = json.load(open(sys.argv[1]))
by = {}
for r in d["results"]:
    by.setdefault((r["vw"], r["theme"], r["state"]), {})[r["side"]] = r
EXPECT = {  # 期待する差: (指標の末尾, 行番号 or None) -> (前, 後, 理由)
    ("cursor", 1): ("pointer", "not-allowed", "金型 CheckboxControl.css:4 の disabled（設計 §5 の予想差）"),
}
print("chromium", d["chromium"])
n_same = n_exp = n_x = 0
lines = []
for key in sorted(by):
    b, a = by[key]["before"], by[key]["after"]
    for k in sorted(set(b) | set(a)):
        if k in ("side", "vw", "theme", "state"): continue
        bv, av = b.get(k), a.get(k)
        if bv == av: n_same += 1; continue
        m = re.match(r"r(\d+)_(.*)", k)
        row, name = (int(m.group(1)), m.group(2)) if m else (None, k)
        e = EXPECT.get((name, row))
        if e and str(bv) == e[0] and str(av) == e[1]:
            n_exp += 1; lines.append(f"{key} {k}: {bv} -> {av}  金型どおり（期待）: {e[2]}")
        else:
            n_x += 1; lines.append(f"{key} {k}: {bv} -> {av}  ×（想定外）")
print(f"比較した組: {len(by)}（幅2 x テーマ2 x 状態2）  同じ指標: {n_same}  期待の差: {n_exp}  想定外の差(×): {n_x}")
print("\n".join(lines))
# 要点（accent-color 全行一致・色見本一致）
bad = [(k, r) for k, v in by.items() for r in [v["after"]] if any(r.get(f"r{i}_swatchEqAccent") != "一致" for i in (1,2,3))]
print("色見本とチェック欄の色が不一致の組(後):", len(bad))
bad = [k for k, v in by.items() if any(v["before"][f"r{i}_accentColor"] != v["after"][f"r{i}_accentColor"] for i in (1,2,3))]
print("accent-color が前後で違う組:", len(bad))
