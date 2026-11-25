"""声で直す便の次の便の下調べ: 秘書の容器の答えを見るだけ（記録・予定は作られない）。"""
import json, time, httpx

KARTE = {"title": "打ち合わせ", "start": "2026-11-30T15:00:00+09:00", "end": "2026-11-30T16:00:00+09:00", "is_all_day": False}
NOW = "2026-11-25T20:00:00+09:00"
TEXTS = [
    ("d1", "4時に変えて、説明に明日と入れて"),
    ("d2", "16時にして、メモは明日の資料"),
    ("d3", "説明に今日の議事録と入れて4時にして"),
    ("d4", "時間を4時にしてメモに明日持参"),
    ("d5", "4時に変えて"),
    ("y1", "はい、場所は渋谷にして"),
    ("y2", "オッケー、説明に資料と入れて"),
    ("y3", "はい、お願いします"),
    ("y4", "うん、それで"),
]
with httpx.Client(timeout=85.0) as c:
    for rnd in (1, 2, 3):
        for cid, text in TEXTS:
            body = {"text": text, "now": NOW, "model": "gpt-5.6-terra", "rules": [], "karte": KARTE, "asked": None}
            t0 = time.time()
            try:
                r = c.post("http://secretary-codex:8090/intent", json=body)
                out = r.json().get("intent") if r.status_code == 200 else r.text[:200]
                st = r.status_code
            except Exception as e:  # noqa: BLE001
                st, out = None, type(e).__name__
            print(json.dumps({"round": rnd, "id": cid, "status": st, "sec": round(time.time() - t0, 2), "intent": out}, ensure_ascii=False), flush=True)
