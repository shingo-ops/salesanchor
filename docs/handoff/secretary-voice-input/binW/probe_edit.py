"""声で下書きを直す設計の下調べ: 秘書の容器が「下書きを直す言い方」をどう返すかを見る（読むだけ・記録に行は入らない）。"""
import json, time, httpx

KARTE = {"start": "2026-11-26T15:00:00+09:00", "end": "2026-11-26T16:00:00+09:00", "is_all_day": False}
NOW = "2026-11-25T20:00:00+09:00"
TEXTS = [
    ("p1", "説明にテスト 消していい って入力して"),
    ("p2", "場所は渋谷の事務所にして"),
    ("p3", "メモに資料を持っていくと書いて"),
    ("p4", "時間を4時に変えて"),
    ("p5", "タイトルを定例会議に変えて"),
    ("p6", "Meetも付けて"),
]
with httpx.Client(timeout=85.0) as c:
    for rnd in (1, 2):
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
