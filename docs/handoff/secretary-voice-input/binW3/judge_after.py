"""probe_after の結果を kgi.md §8 Y1/Y2/Y4 で数える。1件ずつ判定を出す。"""
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")]
print("rows", len(rows), "status!=200", sum(1 for r in rows if r["status"] != 200))
def hour(v):
    return int(v[11:13]) if v and len(v) >= 13 else None
y1 = [0, 0]; y2 = [0, 0]; ye = [0, 0]; yy = [0, 0]
for r in rows:
    i = r["id"]; f = r["final"] or {}
    if i.startswith(("new_", "edit_asatte_", "edit_only_")):
        h = int(i.split("_")[1] if i.startswith("new_") else i.split("_")[-1])
        got = hour(f.get("start"))
        want = h + 12 if h <= 6 else h
        ok = got == want
        b = y1 if h <= 6 else y2
        b[0] += ok; b[1] += 1
        if not ok:
            print("NG", r["round"], i, r["text"], "start", f.get("start"), "ai", (r["intent"] or {}).get("event", {}).get("start") if isinstance(r["intent"], dict) else r["intent"])
    elif i.startswith("yes_"):
        n = int(i[4:])
        if n <= 7:
            ok = bool(f.get("edited")) or bool(f.get("edit_dropped"))
            if n == 7:
                ok = ok and f.get("add_meet") is True
            ye[0] += ok; ye[1] += 1
        else:
            ok = f.get("edited") is False and f.get("edit_dropped") is False
            yy[0] += ok; yy[1] += 1
        print("YES", "ok" if ok else "NG", r["round"], i, r["text"], "edited", f.get("edited"), "dropped", f.get("edit_dropped"), "start", f.get("start"), "end", f.get("end"), "loc", f.get("location"), "title", f.get("title"), "meet", f.get("add_meet"))
print("Y1 午後になった", y1); print("Y2 朝のまま", y2); print("Y4 直しの読み落としなし", ye); print("Y4 お願いします類で作られる", yy)
secs = sorted(r["sec"] for r in rows); print("sec median", secs[len(secs)//2], "max", secs[-1])
