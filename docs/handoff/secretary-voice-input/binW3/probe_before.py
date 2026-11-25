"""便W3 下調べ: ①「N時」(1〜11) を AI が午前・午後どちらで読むか ②「はい＋直し」で直しが読まれるか。
本番の口の直す道と同じ順（same_time/same_day・apply_day・merge_edit・settle_dates・日時を失えば前のまま・変化なしなら偽）で最終の値も出す。
読むだけ（記録・予定は作られない）。1 件ずつ順に流す（AI は同時に 1 件だけ受ける・並べると 429 busy）。"""
import datetime, json, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, ".")
import httpx
from app.schemas.assistant import IntentEvent, KarteIn
from app.services.secretary_dates import apply_day, same_day
from app.services.secretary_karte import edit_changed, merge_edit, same_time, settle_dates

KARTE = {"title": "打ち合わせ", "start": "2026-11-30T15:00:00+09:00", "end": "2026-11-30T16:00:00+09:00", "is_all_day": False, "edit": True}
TODAY = datetime.date(2026, 11, 25)
cases = []
for rnd in (1, 2):
    for h in range(1, 12):
        for now in ("2026-11-25T20:00:00+09:00", "2026-11-25T09:00:00+09:00"):
            cases.append({"round": rnd, "id": f"new_{h}_{now[11:13]}", "text": f"明日{h}時に打ち合わせ", "now": now, "karte": None})
        cases.append({"round": rnd, "id": f"edit_asatte_{h}", "text": f"あさって{h}時にして", "now": "2026-11-25T20:00:00+09:00", "karte": KARTE})
        cases.append({"round": rnd, "id": f"edit_only_{h}", "text": f"{h}時に変えて", "now": "2026-11-25T20:00:00+09:00", "karte": KARTE})
    for i, text in enumerate([
        "はい、場所は渋谷にして", "はい、3時からにして", "うん、題名を定例会議にして", "はい、明日にして",
        "オッケー、終わりは5時にして", "はい、説明に資料持参と入れて", "はい、1時間半にして", "はい、Meetも付けて",
        "はい、お願いします", "うん、それで", "はい、それでお願い", "はい、大丈夫です", "はい、それでいいです",
        "はい、よろしく", "はい、作ってください",
    ]):
        cases.append({"round": rnd, "id": f"yes_{i:02d}", "text": text, "now": "2026-11-25T20:00:00+09:00", "karte": KARTE})


def run(c, case):
    body = {"text": case["text"], "now": case["now"], "model": "gpt-5.6-terra", "rules": [], "karte": None, "asked": None}
    karte = None
    if case["karte"] is not None:
        karte = KarteIn(**case["karte"])
        body["karte"] = {"title": karte.title, "start": karte.start, "end": karte.end, "is_all_day": karte.is_all_day}
    t0 = time.time()
    final = None
    try:
        r = c.post("http://secretary-codex:8090/intent", json=body)
        st = r.status_code
        out = r.json().get("intent") if st == 200 else r.text[:200]
        if st == 200 and karte is not None:
            ai_ev = IntentEvent(**out["event"]) if out.get("kind") == "event" and out.get("event") else None
            if ai_ev is not None and ai_ev.start is not None and (karte.start is None or (not same_time(ai_ev.start, karte.start) and not same_day(ai_ev.start, karte.start))):
                ai_ev = apply_day(ai_ev, case["text"], TODAY, None)
            fev, edited = merge_edit(ai_ev, karte)
            fev = settle_dates(fev)
            base, _ = merge_edit(None, karte)
            if (base.start is not None and fev.start is None) or (base.end is not None and fev.end is None):
                fev, edited = base, False
            elif edited and not edit_changed(fev, base):
                edited = False
            final = {"title": fev.title, "start": fev.start, "end": fev.end, "location": fev.location, "description": fev.description, "add_meet": fev.add_meet, "edited": edited}
    except Exception as e:  # noqa: BLE001
        st, out = None, f"{type(e).__name__}: {e}"[:200]
    return {"round": case["round"], "id": case["id"], "text": case["text"], "now": case["now"], "status": st, "sec": round(time.time() - t0, 2), "intent": out, "final": final}


with httpx.Client(timeout=85.0) as c, ThreadPoolExecutor(1) as ex:
    for res in ex.map(lambda cs: run(c, cs), cases):
        print(json.dumps(res, ensure_ascii=False), flush=True)
print("DONE", len(cases), flush=True)
