# AY-4c-2a: ay4c2-measure.json から ay4c2-measure-compare.txt を作る。使い方: python3 ay4c2-compare.py ay4c2-measure.json ay4c2-measure-compare.txt
import json, sys, collections
src, out = sys.argv[1], sys.argv[2]
R = json.load(open(src)); rows = R["results"]
def num(v):
    try: return float(str(v).replace("px", ""))
    except: return None
CTL = ("H1-1", "H1-6", "H1-7")          # 外側の label はそのまま、input だけ CheckboxControl
LBL = ("H2", "H2-3", "H2-4", "H2N", "H3")  # label 型 Checkbox
STACK = ("H2-3", "H2-4", "H2N")         # 縦に並ぶ複数の欄
ITEMS = [("inputW","input の幅"),("inputH","input の高さ"),("accentColor","accent-color"),("textFontSize","文字 font-size"),("textFontWeight","文字 font-weight"),("textColor","文字 color"),("textLineHeight","文字 line-height"),("inputToTextGap","input と文字の間隔"),("rootW","root(label) の幅"),("rootH","root(label) の高さ"),("row2_rootH","2 つ目の欄の高さ"),("row3_rootH","3 つ目の欄の高さ"),("vCenterOffsetInputMinusText","input と文字の縦の中心のずれ(input-文字)"),("row1_topOffsetInputMinusText","input の上端と文字の上端のずれ(1 つ目)"),("row3_topOffsetInputMinusText","input の上端と文字の上端のずれ(3 つ目)"),("rootDisplay","root の display"),("rootAlignItems","root の align-items"),("inputFlexShrink","input の flex-shrink"),("inputBorder","input の枠"),("inputBg","input の背景"),("inputPadding","input の padding"),("fgH",".form-group の高さ"),("fgMarginBottom",".form-group の margin-bottom"),("gapBelow","下の要素との間隔"),("gapAbove","上の要素との間隔"),("headDisplay","見出し label の display"),("headColor","見出し label の color"),("headFontSize","見出し label の font-size"),("headFontWeight","見出し label の font-weight"),("headMarginBottom","見出し label の margin-bottom"),("headH","見出し label の高さ"),("headW","見出し label の幅"),("stackPitch12","1 つ目と 2 つ目の欄の top の差"),("stackPitch23","2 つ目と 3 つ目の欄の top の差"),("stackLeftSame","3 つの欄の left が同じか"),("sampleH","親(断片)全体の高さ"),("titleOn","title の付く要素")]
# 欄どうしの縦並び（H2-3・H2-4・H2N）の派生指標
for r in rows:
    o = r["o"]
    if r["type"] in STACK and o.get("nInputs", 0) >= 3:
        o["stackPitch12"] = round(o["row2_rootTop"] - o["row1_rootTop"], 2); o["stackPitch23"] = round(o["row3_rootTop"] - o["row2_rootTop"], 2)
        o["stackLeftSame"] = "同じ" if o["row1_rootLeft"] == o["row2_rootLeft"] == o["row3_rootLeft"] else "ずれる"
TYPES = [t for t in dict.fromkeys(r["type"] for r in rows)]
idx = {}
for r in rows:
    k = (r["type"], r["vw"], r["id"], r["theme"], r["state"])
    idx.setdefault(k, {})[r["side"]] = r["o"]; idx[k]["tok"] = r["tok"] if r["side"] == "after" else idx[k].get("tok")
# 外側がそのまま（H1）なので前後で同じでなければならない項目
H1_SAME = {"textFontSize","textFontWeight","textColor","textLineHeight","inputToTextGap","rootW","rootDisplay","rootAlignItems","titleOn","gapBelow","gapAbove","sampleW"}
H1_PRESENT = {"rootH","row2_rootH","row3_rootH","sampleH"}     # 行の高さ: 変わったら差として提示（× にはしない。設計 §5-1・§7）
def judge(t, item, b, a, tok):
    bv, av = b.get(item), a.get(item)
    same = (bv == av)
    if item == "accentColor":
        return ("○", "アプリの基本色 --accent（PO 決定 2026-10-15）") if av == tok["tokAccent"] else ("×", "後が --accent と一致しない")
    if item in ("inputW", "inputH"):
        if t in CTL:
            return ("○", "CheckboxControl の var(--size-checkbox)=%s（CheckboxControl.css:2）" % tok["tokSizeCb"]) if abs(num(av) - num(tok["tokSizeCb"])) < 0.02 else ("×", "金型の値と不一致")
        exp = 1.1 * num(a["inputFontSize"])
        return ("○", "Checkbox の 1.1em（Checkbox.css input。em は input 自身の font-size %s 基準）" % a["inputFontSize"]) if abs(num(av) - exp) < 0.02 else ("×", "金型の値と不一致")
    if t in CTL:
        if item in H1_SAME: return ("○", "外側の label・文字は今のまま。前後で同じ") if same else ("×", "外側は変えない設計なのに前後で違う")
        if item in H1_PRESENT: return ("○(提示)", "行の高さの前後差を提示（設計 §5-1）") if not same else ("○", "前後で同じ")
        if item == "row1_topOffsetInputMinusText" or item == "row3_topOffsetInputMinusText":
            if t == "H1-7": return ("○", "カードの文字の 1 行目と input の上端の配置が前後で同じ（pages-layout.css:635 の margin-top を残したため。設計 §7）") if same else ("×", "上端のずれが前後で違う（設計 §7 は同じを要求）")
            return None
        if item == "inputFlexShrink": return ("○", "H1-7 は pages-layout.css:635-638 の flex-shrink:0 を残した") if (t == "H1-7" and same) else None
        return None
    # label 型
    if item == "textFontSize": return ("○", "金型の var(--font-sm)=%s（Checkbox.css:12）" % tok["tokFont"]) if av == tok["tokFont"] else ("×", "金型の値と不一致")
    if item == "textFontWeight":
        if t == "H3": return ("○", "金型の var(--font-weight-medium)。旧 .right-panel-value の 500 と同じ値") if av == tok["tokWeight"] else ("×", "金型の値と不一致")
        return ("○", "金型の var(--font-weight-medium)（Checkbox.css 文字 span）") if av == tok["tokWeight"] else ("×", "金型の値と不一致")
    if item == "textColor": return ("○", "金型の var(--text-primary)（Checkbox.css:13）") if av == tok["tokText"] else ("×", "金型の値と不一致")
    if item == "textLineHeight":
        exp = num(tok["tokLH"]) / 16 * num(a["textFontSize"])
        return ("○", "金型の line-height var(--line-height-base) × font-size") if abs(num(av) - exp) < 0.05 else ("×", "金型の値と不一致")
    if item == "inputToTextGap": return ("○", "金型の gap var(--space-2)=%s" % tok["tokGap"]) if abs(num(av) - num(tok["tokGap"])) < 0.02 else ("×", "金型の値と不一致")
    if item == "rootDisplay": return ("○", "Checkbox.css:9 inline-flex（flex の子では blockify されて flex）") if av in ("inline-flex", "flex") else ("×", "想定外")
    if item == "rootAlignItems": return ("○", "Checkbox.css:10 align-items: flex-start") if av == "flex-start" else ("×", "金型の値と不一致")
    if item == "inputBorder" or item == "inputBg" or item == "inputPadding":
        return None
    if t in ("H2", "H2-3", "H2-4") and item in ("gapBelow", "fgMarginBottom"):
        return ("○", ".form-group の下の間隔 space-4 を保つ（設計 §3-2・§7）。前後で同じ") if same else ("×", "下の間隔が変わった（設計は保つ）")
    if t == "H2N" and item.startswith("head"):
        return ("○", "見出し label は今のまま（:where で詳細度 0,1,1 を保つ。設計 §7）。前後で同じ") if same else ("×", "見出し label の値が変わった（設計 §7）")
    if t == "H2N" and item == "stackLeftSame":
        return ("○", "3 つの欄が縦に並ぶ（left が同じ）") if av == "同じ" else ("×", "3 つの欄が横に並んだ")
    if t == "H2N" and item in ("stackPitch12", "stackPitch23"):
        return ("○", "各欄の top が増えていく（縦に並ぶ）") if num(av) > 0 else ("×", "縦に並んでいない")
    if t in STACK and item in ("stackPitch12", "stackPitch23", "stackLeftSame"):
        if item == "stackLeftSame": return ("○", "縦に並ぶ（left が同じ）") if av == "同じ" else ("×", "縦に並んでいない")
        return ("○", "各欄の top が増えていく") if num(av) > 0 else ("×", "縦に並んでいない")
    return None
DERIVED = {
 "rootW": "金型 root の inline-flex（文字の幅まで縮む）。押せる範囲が全幅から欄と文字の幅に縮む（設計 §3-2 の差①）",
 "rootH": "文字の line-height（金型 line-height×font-size）と input 1.1em で決まる高さ",
 "row2_rootH": "同上", "row3_rootH": "同上",
 "vCenterOffsetInputMinusText": "Checkbox.css:10 align-items:flex-start で input が行の上端寄せになる／input の寸法の差",
 "row1_topOffsetInputMinusText": "Checkbox.css:10 の上寄せ／input の寸法の差", "row3_topOffsetInputMinusText": "同上",
 "inputFlexShrink": "Checkbox.css の flex-shrink:0 が入る",
 "inputBorder": "金型の枠（1px solid var(--border)）／旧 .form-group の規則が外れた", "inputBg": "金型の背景 var(--bg-surface)", "inputPadding": "旧 .form-group の padding(space-2/space-3) が外れた",
 "fgH": "root の高さが金型の寸法に変わる（設計 §3-2 の差③⑤）", "gapBelow": "root の高さ・余白の差", "gapAbove": "root の高さ・余白の差",
 "sampleH": "上の欄の高さの差の合計", "titleOn": "title の付く要素",
 "stackPitch12": "行の高さの差（label の margin-bottom space-1 が無くなる）", "stackPitch23": "同上",
}
L = []
L.append("# AY-4c-2a 前後実測 比較表（%s）" % R["chromium"])
L.append("前: origin/main 52b8a4003 の vite build CSS ＋ 実ファイルから写した変更前マークアップ。後: 作業ツリーの vite build CSS ＋ 本物の金型 DOM（renderToStaticMarkup）。")
L.append("条件: 幅 390 / 1280 × ライト/ダーク × 未チェック/チェック × 試料（型ごとの実物の親。ay4c2-render.tsx の ref）。測定した行数: %d（前後別）。" % len(rows))
L.append("親の再現範囲: 実ファイルの class・構造どおり。Popover（MultiSelect）の枠は .comp-popover の padding と枠を再現（位置指定・影は含まない）。TextFieldControl など変更していない部品は本物を描画。")
L.append("")
L.append("## 試料")
for s in R["samples"]: L.append("- %s | %s | %s" % (s["type"], s["id"], s["ref"]))
L.append("")
L.append("## 比較表（型｜項目｜幅｜前｜後｜差｜金型どおりの差か）  差 0 の項目も出す。値が複数ある所は条件（テーマ・状態）ごとの異なる値を / で並べる。")
L.append("型｜項目｜幅｜前｜後｜差｜金型どおりの差か（○/×と理由1行）")
unexpl = []; NZ = 0; ZERO = 0
for t in TYPES:
    for item, jp in ITEMS:
        for vw in (390, 1280):
            bs, as_, ds = [], [], []; cnt = 0; jg = set()
            for k, v in idx.items():
                if k[0] != t or k[1] != vw: continue
                b, a = v.get("before", {}), v.get("after", {})
                if item not in b and item not in a: continue
                bv, av = b.get(item, "なし"), a.get(item, "なし")
                cnt += 1
                if bv not in bs: bs.append(bv)
                if av not in as_: as_.append(av)
                nb, na = num(bv), num(av)
                d = ("%+.2f" % (na - nb)).rstrip("0").rstrip(".") if (nb is not None and na is not None and bv != "なし" and av != "なし") else ("0" if bv == av else "変化")
                if d in ("+0", "-0", "+", "-"): d = "0"
                if d not in ds: ds.append(d)
                if av != "なし":
                    j = judge(t, item, b, a, v["tok"])
                    if j: jg.add(j)
            if cnt == 0: continue
            nonzero = any(d != "0" for d in ds)
            if jg:
                marks = {m[0] for m in jg}
                mk = "×" if "×" in marks else ("○(提示)" if "○(提示)" in marks else "○")
                j = mk + " " + "/".join(sorted({r for _, r in jg}))[:170]
                if mk == "×": unexpl.append((t, item, vw))
            else:
                j = ("○(派生) " + DERIVED.get(item, "金型の値から決まる差")) if nonzero else "差なし"
            if nonzero: NZ += 1
            else: ZERO += 1
            L.append("｜".join([t, jp, str(vw), " / ".join(map(str, bs)), " / ".join(map(str, as_)), " / ".join(ds), j]))
L.append("")
L.append("## 集計")
L.append("行数: 差あり %d / 差なし %d。金型どおりでない（×）: %d 件 %s" % (NZ, ZERO, len(unexpl), unexpl))
unstable = []
for t in TYPES:
    for item, _ in [x for x in ITEMS if x[0] not in ("accentColor", "textColor", "headColor", "inputBg")]:
        for vw in (390, 1280):
            for side in ("before", "after"):
                vals = {str(idx[k][side].get(item)) for k in idx if k[0] == t and k[1] == vw and side in idx[k] and item in idx[k][side]}
                if len(vals) > 1: unstable.append((t, item, vw, side, sorted(vals)))
L.append("テーマ・チェック状態で値が変わった (型,項目,幅,側) の数: %d %s" % (len(unstable), unstable[:12]))
open(out, "w").write("\n".join(L) + "\n")
print("diff rows", NZ, "zero rows", ZERO, "x", len(unexpl), unexpl, "unstable", len(unstable))
