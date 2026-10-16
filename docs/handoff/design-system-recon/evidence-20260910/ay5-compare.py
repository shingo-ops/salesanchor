# 使い方: python3 ay5-compare.py <measure.json> > ay5-measure-compare.txt
# 前後の全指標を突き合わせ、設計 docs/handoff/ay5-radio/design.md §5 の「想定内の差」の一覧で分類する。一覧に無い差は全部「×（想定外）」。
import json, sys, re
d = json.load(open(sys.argv[1]))
by = {}
for r in d["results"]:
    by.setdefault((r["vw"], r["theme"], r["scene"], r["state"]), {})[r["side"]] = r

# 想定内の差（設計 §5）。キー: 場面 -> {指標名(i{n}_ を除いた名前): 理由}
R1_SIZE = "丸の大きさ（ブラウザ標準 → 1.1em）"
R1_POS = "丸・文字の位置、行の高さ、2 行の縦の間隔（display・gap・font-size・align-items・line-height の変更に伴う）"
EXP = {
  "r1": {
    "w": R1_SIZE, "h": R1_SIZE, "cssWidth": R1_SIZE, "cssHeight": R1_SIZE,
    "accentColor": "accent-color（auto → --accent）",
    "parentDisplay": "label の display（flex → inline-flex）", "rootDisplay": "label の display（flex → inline-flex）",
    "parentW": "label の幅（行いっぱい → 中身の幅）", "rootW": "label の幅（行いっぱい → 中身の幅）",
    "labelColumnGap": "gap（今の値 → --space-2）", "labelRowGap": "gap（今の値 → --space-2）", "rootColumnGap": "gap（今の値 → --space-2）", "rootRowGap": "gap（今の値 → --space-2）",
    "labelFontSize": "font-size（継承 → --font-sm）", "rootFontSize": "font-size（継承 → --font-sm）", "textFontSize": "font-size（継承 → --font-sm）",
    "labelFontWeight": "font-weight（継承 → medium）", "rootFontWeight": "font-weight（継承 → medium）", "textFontWeight": "font-weight（継承 → medium）",
    "labelAlignItems": "align-items（center → flex-start）", "rootAlignItems": "align-items（center → flex-start）",
    "labelLineHeight": R1_POS, "rootLineHeight": R1_POS,
    "left": R1_POS, "top": R1_POS, "parentLeft": R1_POS, "parentTop": R1_POS, "parentH": R1_POS, "rootH": R1_POS, "rootTop": R1_POS, "rootLeft": R1_POS,
    "textLeft": R1_POS, "textTop": R1_POS, "textW": R1_POS, "textH": R1_POS, "gapInputToText": R1_POS, "inputCenterY": R1_POS, "textCenterY": R1_POS,
    "rowTopDiff": R1_POS, "rowGapBetween": R1_POS, "inputTopDiff": R1_POS, "sampleH": R1_POS,
    "cursor": "input の cursor（default → pointer）（設計 §5 実測 r1 の追記）",
  },
  "r34": {"accentColor": "accent-color（auto → --accent。欄が透明なので見た目は変わらない）"},
  "r5": {
    "w": "width（標準 → 16px）", "h": "height（標準 → 16px）", "cssWidth": "width（標準 → 16px）", "cssHeight": "height（標準 → 16px）",
    "accentColor": "accent-color（標準 → --accent）", "cursor": "cursor（標準 → pointer）",
    "top": "行の高さ（丸の大きさに伴う）", "parentH": "行の高さ（丸の大きさに伴う）", "parentTop": "行の高さ（丸の大きさに伴う）",
    "trH": "行の高さ（丸の大きさに伴う）", "trTop": "行の高さ（丸の大きさに伴う）", "tdH": "行の高さ（丸の大きさに伴う）",
    "rowTopDiff": "行の高さ（丸の大きさに伴う）", "sampleH": "行の高さ（丸の大きさに伴う）",
    "tdW": "td の幅（丸が大きくなったぶん）（設計 §5 実測 r1 の追記）", "parentW": "td の幅（丸が大きくなったぶん）（設計 §5 実測 r1 の追記）",
  },
}
# 値の確認（想定内でも値が設計と違えば ×）
def val_ok(scene, name, bv, av, side_after):
    if name == "accentColor": return bv == "auto" and av == side_after["accentToken"]
    if name in ("parentDisplay", "rootDisplay"): return (bv, av) == ("flex", "inline-flex") if scene == "r1" else True
    if name in ("labelAlignItems", "rootAlignItems"): return (bv, av) == ("center", "flex-start")
    if name in ("labelFontWeight", "rootFontWeight", "textFontWeight"): return (bv, av) == ("400", "500")
    if name in ("labelColumnGap", "labelRowGap", "rootColumnGap", "rootRowGap"): return av == "8px"
    if scene == "r5" and name in ("cssWidth", "cssHeight"): return av == "16px"
    if scene == "r5" and name == "cursor": return av == "pointer"
    if name == "cursor": return (bv, av) == ("default", "pointer")
    if scene == "r5" and name in ("tdW", "parentW"): return (bv, av) == (45, 48)
    return True

print("chromium", d["chromium"])
n_same = n_exp = n_x = 0
exp_lines, x_lines, exp_sum = [], [], {}
for key in sorted(by):
    b, a = by[key]["before"], by[key]["after"]
    scene = key[2]
    for k in sorted(set(b) | set(a)):
        if k in ("side", "vw", "theme", "scene", "state", "accentToken"): continue
        bv, av = b.get(k), a.get(k)
        if bv == av: n_same += 1; continue
        m = re.match(r"i(\d+)_(.*)", k)
        name = m.group(2) if m else k
        why = EXP[scene].get(name)
        if why and val_ok(scene, name, bv, av, a):
            n_exp += 1; exp_sum.setdefault((scene, name, why), []).append((key, k, bv, av))
        else:
            n_x += 1; x_lines.append(f"{key} {k}: {bv} -> {av}  ×（想定外）" + ("" if not why else "（想定内の項目だが値が設計と違う）"))
print(f"比較した組: {len(by)}（場面 R1・R3/R4・R5 × 幅2 × テーマ2 × 状態）")
print(f"指標の総数（前後を突き合わせた数）: {n_same + n_exp + n_x}  同じ指標: {n_same}  想定内の差: {n_exp}  想定外の差(×): {n_x}")
print("\n=== 想定内の差（指標ごと。件数と最初の1例）===")
for (scene, name, why), v in sorted(exp_sum.items()):
    key, k, bv, av = v[0]
    print(f"[{scene}] {name} x{len(v)}: {why}  例 {key} {k}: {bv} -> {av}")
print(f"\n=== 想定外の差（全件・{n_x} 件）===")
print("\n".join(x_lines) if x_lines else "なし")
print("\n=== R1 の今（前）の gap・marginTop の computed 値 ===")
for key in sorted(by):
    if key[2] == "r1":
        b = by[key]["before"]
        print(key, "label1 columnGap/rowGap:", b["i1_rootColumnGap"], b["i1_rootRowGap"], " label1 marginTop:", b["i1_rootMarginTop"], " label2 columnGap/rowGap:", b["i2_rootColumnGap"], b["i2_rootRowGap"], " label2 marginTop:", b["i2_rootMarginTop"], " 2行の縦の間隔(前):", b["rowTopDiff"], "(後):", by[key]["after"]["rowTopDiff"])
print("\n=== R3・R4 の幅・高さ・位置・opacity・cursor の前後差 ===")
bad = [(k, n) for k, v in by.items() if k[2] == "r34" for n in v["before"] if re.match(r"i\d+_(w|h|left|top|cssWidth|cssHeight|opacity|cursor|position)$", n) and v["before"][n] != v["after"][n]]
print("差のある組・指標:", len(bad), bad[:5])
