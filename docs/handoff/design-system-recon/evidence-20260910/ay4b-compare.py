# AY-4b: ay4b-measure.json から ay4b-measure-compare.txt を作る。使い方: python3 ay4b-compare.py ay4b-measure.json ay4b-measure-compare.txt
import json, sys, re, collections
src, out = sys.argv[1], sys.argv[2]
R = json.load(open(src))
rows = R["results"]
def num(v):
    try: return float(str(v).replace("px", ""))
    except: return None
ITEMS = [("inputW","input の幅"),("inputH","input の高さ"),("accentColor","accent-color"),("textFontSize","文字 font-size"),("textFontWeight","文字 font-weight"),("textColor","文字 color"),("textLineHeight","文字 line-height"),("inputToTextGap","input と文字の間隔"),("rootW","label(金型 root) の幅"),("rootH","label(金型 root) の高さ"),("vCenterOffsetInputMinusText","input と文字の縦の中心のずれ(input-文字)"),("vCenterOffsetInputMinusLeftField","input と左の TextField 入力枠の縦の中心のずれ"),("gapAbove","上の要素との間隔"),("gapBelow","下の要素との間隔"),("rootDisplay","root の display"),("rootAlignItems","root の align-items"),("sampleH","親(断片)全体の高さ"),("cellW","td の幅"),("cellH","td の高さ"),("inputCenterXInCell","input の横中心の td 中心とのずれ")]
TYPES = sorted({r["type"] for r in rows})
# key: (type,vw,id,theme,state) -> {before:o, after:o, tok}
idx = {}
for r in rows:
    k = (r["type"], r["vw"], r["id"], r["theme"], r["state"])
    idx.setdefault(k, {})[r["side"]] = r["o"]; idx[k]["tok"] = r["tok"] if r["side"] == "after" else idx[k].get("tok")
def judge(item, b, a, tok, typ):
    same = (b == a)
    ctl = typ.startswith("F")
    fs = num(a.get("textFontSize")) if a.get("textFontSize") else None
    if item == "accentColor": return ("○", "アプリの基本色 --accent（PO 決定 2026-10-15）") if a[item] == tok["tokAccent"] else ("×", "後が --accent と一致しない")
    if item == "textFontSize": return ("○", "金型の font-size var(--font-sm)=%s（Checkbox.css:12）" % tok["tokFont"]) if a[item] == tok["tokFont"] else ("×", "金型の値と不一致")
    if item == "textFontWeight": return ("○", "金型の var(--font-weight-medium)（Checkbox.css 文字 span）") if a[item] == tok["tokWeight"] else ("×", "金型の値と不一致")
    if item == "textColor": return ("○", "金型の var(--text-primary)（Checkbox.css:13）") if a[item] == tok["tokText"] else ("×", "金型の値と不一致")
    if item == "textLineHeight":
        exp = num(tok["tokLH"]) / 16 * fs
        return ("○", "金型の line-height var(--line-height-base) × font-size") if abs(num(a[item]) - exp) < 0.05 else ("×", "金型の値と不一致")
    if item in ("inputW", "inputH"):
        exp = 16 if ctl else 1.1 * num(a["inputFontSize"])
        return ("○", ("CheckboxControl の var(--size-checkbox)=16px" if ctl else "Checkbox の 1.1em（Checkbox.css input 1.1em。em は input 自身の font-size %s 基準）" % a["inputFontSize"]) ) if abs(num(a[item]) - exp) < 0.02 else ("×", "金型の値と不一致")
    if item == "inputToTextGap": return ("○", "金型の gap var(--space-2)=%s" % tok["tokGap"]) if abs(num(a[item]) - num(tok["tokGap"])) < 0.02 else ("×", "金型の値と不一致")
    if item == "rootDisplay": return ("○", "Checkbox.css:9 inline-flex（grid/flex の子では blockify される）") if a[item] in ("inline-flex", "flex", "block") else ("×", "想定外")
    if item == "rootAlignItems": return ("○", "Checkbox.css:10 align-items: flex-start") if a[item] == "flex-start" else ("×", "金型の値と不一致")
    return None
DERIVED = {
 "rootH": "文字の line-height（金型 line-height×font-size）と input 1.1em で決まる高さ",
 "rootW": "金型 root の inline-flex（文字の幅まで縮む）／input 1.1em・16px で決まる幅",
 "vCenterOffsetInputMinusText": "Checkbox.css:10 align-items:flex-start で input が行の上端寄せになる",
 "vCenterOffsetInputMinusLeftField": "Checkbox.css:10 align-items:flex-start（旧は center）で、セルの上端寄せになる",
 "gapAbove": "旧 .lv-check-label の margin-top(space-2) が無くなる（設計 §3-2）／行ボックスの差",
 "gapBelow": "root の高さ・余白の差",
 "sampleH": "上の root の高さの差の合計",
 "cellW": "input 13→16px で列幅が広がる",
 "cellH": "行の高さの差",
 "inputCenterXInCell": "text-align:center のまま中心に入る",
}
lines = []
lines.append("# AY-4b 前後実測 比較表（%s）" % R["chromium"])
lines.append("前: origin/main の vite build CSS ＋ 実ファイルから写した変更前マークアップ。後: 作業ツリーの vite build CSS ＋ 本物の金型 DOM（renderToStaticMarkup）。")
lines.append("条件: 幅 390 / 1280 × ライト/ダーク × 未チェック/チェック × 試料（型ごとの実物の親。ay4b-render.tsx の ref）。測定した行数: %d（前後別）。" % len(rows))
lines.append("親の再現範囲: Drawer 本体の幅と余白（--drawer-panel-w-default, padding space-5/space-6）、grid/flex の実ファイルどおりの構造、変更していない TextField 等は本物を描画。Drawer の外枠（影・ヘッダー）は含まない。")
lines.append("")
lines.append("## 試料")
byt = collections.OrderedDict()
for s in R["samples"]: byt.setdefault(s["type"], []).append(s)
for t, ss in byt.items():
    for s in ss: lines.append("- %s | %s | %s" % (t, s["id"], s["ref"]))
lines.append("")
lines.append("## 比較表（型｜項目｜幅｜前｜後｜差｜金型どおりの差か）  差 0 の項目も出す。値が複数ある所は試料/条件ごとの異なる値を / で並べる。")
lines.append("型｜項目｜幅｜前｜後｜差｜金型どおりの差か（○/×と理由1行）")
unexpl = []; diffs = []
ZERO = 0; NZ = 0
for t in TYPES:
    for item, jp in ITEMS:
        for vw in (390, 1280):
            bs, as_, ds, cnt = [], [], [], 0; jg = set(); pairs = set()
            for k, v in idx.items():
                if k[0] != t or k[1] != vw: continue
                b, a = v.get("before", {}), v.get("after", {})
                if item not in b and item not in a: continue
                bv, av = b.get(item, "なし"), a.get(item, "なし")
                cnt += 1
                if bv not in bs: bs.append(bv)
                if av not in as_: as_.append(av)
                pairs.add((str(bv), str(av)))
                nb, na = num(bv), num(av)
                d = ("%+.2f" % (na - nb)).rstrip("0").rstrip(".") if (nb is not None and na is not None and bv != "なし" and av != "なし") else ("0" if bv == av else "変化")
                if d in ("+0", "-0", "+"): d = "0"
                if d not in ds: ds.append(d)
                if item in ("accentColor","textFontSize","textFontWeight","textColor","textLineHeight","inputW","inputH","inputToTextGap","rootDisplay","rootAlignItems") and av != "なし":
                    jg.add(judge(item, b, a, v["tok"], t) or ("?", ""))
            if cnt == 0: continue
            nonzero = any(d != "0" for d in ds)
            if jg:
                marks = {m for m, _ in jg}
                j = ("○ " if marks == {"○"} else "× ") + "/".join(sorted({r for _, r in jg}))[:160]
                if "×" in marks: unexpl.append((t, item, vw))
            else:
                j = ("○(派生) " + DERIVED.get(item, "金型の値から決まる差")) if nonzero else "差なし"
            if nonzero: NZ += 1; diffs.append((t, item, vw, bs, as_, ds, j))
            else: ZERO += 1
            lines.append("｜".join([t, jp, str(vw), " / ".join(map(str, bs)), " / ".join(map(str, as_)), " / ".join(ds), j]))
lines.append("")
lines.append("## 集計")
lines.append("行数: 差あり %d / 差なし %d。金型の定義値と不一致（×）: %d 件 %s" % (NZ, ZERO, len(unexpl), unexpl))
# 条件間の安定性: テーマ・状態で値が変わったか
unstable = []
for k, v in idx.items():
    t, vw, i, th, st = k
    for o2 in ("light","dark"):
        pass
for t in TYPES:
    for item, _ in [x for x in ITEMS if x[0] not in ("accentColor","textColor")]:
        for vw in (390, 1280):
            for sid in {k[2] for k in idx if k[0] == t}:
                for side in ("before", "after"):
                    vals = {str(idx[k][side].get(item)) for k in idx if k[0]==t and k[1]==vw and k[2]==sid and side in idx[k]}
                    if len(vals) > 1: unstable.append((t, sid, item, vw, side, sorted(vals)))
lines.append("テーマ・チェック状態で値が変わった (型,試料,項目,幅,側) の数: %d %s" % (len(unstable), unstable[:10]))
open(out, "w").write("\n".join(lines) + "\n")
print("diff rows", NZ, "zero rows", ZERO, "x", len(unexpl), "unstable", len(unstable))
