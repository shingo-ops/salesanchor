"""便W2 反映後の試し: probe_followup.py と同じ 9 件に「あさって4時にして」を足し、3 回ずつ流す。
AI の答えに、本番の口の直す道と同じ順（Meet 外しなし・same_time/same_day・apply_day・merge_edit・settle_dates）を当てた最終の始まりも出す。
読むだけ（記録・予定は作られない）。"""
import datetime, json, sys, time
sys.path.insert(0, ".")
import httpx
from app.schemas.assistant import IntentEvent, KarteIn
from app.services.secretary_dates import apply_day, same_day
from app.services.secretary_karte import merge_edit, same_time, settle_dates

KARTE = {"title": "打ち合わせ", "start": "2026-11-30T15:00:00+09:00", "end": "2026-11-30T16:00:00+09:00", "is_all_day": False}
NOW = "2026-11-25T20:00:00+09:00"
TODAY = datetime.date(2026, 11, 25)
TEXTS = [
    ("d1", "4時に変えて、説明に明日と入れて"),
    ("d2", "16時にして、メモは明日の資料"),
    ("d3", "説明に今日の議事録と入れて4時にして"),
    ("d4", "時間を4時にしてメモに明日持参"),
    ("d5", "4時に変えて"),
    ("a1", "あさって4時にして"),
    ("y1", "はい、場所は渋谷にして"),
    ("y2", "オッケー、説明に資料と入れて"),
    ("y3", "はい、お願いします"),
    ("y4", "うん、それで"),
]
karte = KarteIn(**KARTE)
with httpx.Client(timeout=85.0) as c:
    for rnd in (1, 2, 3):
        for cid, text in TEXTS:
            body = {"text": text, "now": NOW, "model": "gpt-5.6-terra", "rules": [], "karte": KARTE, "asked": None}
            t0 = time.time()
            final = None
            try:
                r = c.post("http://secretary-codex:8090/intent", json=body)
                st = r.status_code
                out = r.json().get("intent") if st == 200 else r.text[:200]
                if st == 200 and isinstance(out, dict) and out.get("kind") == "event" and out.get("event"):
                    ai_ev = IntentEvent(**out["event"])
                    if ai_ev.start is not None and (karte.start is None or (not same_time(ai_ev.start, karte.start) and not same_day(ai_ev.start, karte.start))):
                        ai_ev = apply_day(ai_ev, text, TODAY, None)
                    fev, edited = merge_edit(ai_ev, karte)
                    fev = settle_dates(fev)
                    final = {"start": fev.start, "end": fev.end, "location": fev.location, "description": fev.description, "edited": edited}
            except Exception as e:  # noqa: BLE001
                st, out = None, type(e).__name__
            print(json.dumps({"round": rnd, "id": cid, "status": st, "sec": round(time.time() - t0, 2), "intent": out, "final": final}, ensure_ascii=False), flush=True)
