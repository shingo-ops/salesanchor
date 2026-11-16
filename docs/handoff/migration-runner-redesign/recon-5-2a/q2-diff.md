---
mode: handoff
---

# Q2 3つの形の比べ（本番 003・ひな形の直後・ひな形に全件を流した後）

本報告はカード 前調査 5-2a の実行結果である。

- 読んだ commit: `39b73e9b7b2fec00426ec708e471eaf0c9de3d22`（`origin/main`）
- 手順2〜5・Q1 の試験のファイル・命令: `q1-run.md`。
- 比べ方: `card-5-0b.md` の「比べ方」と同じ単位。台本 `diff_shape.py` は `recon-5-0b/common.md` の全文（「比べる台本」）を、ファイルに取り出して使った（本文は同じ。カードは Write で書くよう指示しているが、取り出しは `awk` で `common.md` から行った。これが偏差）。下の `marks.py` は印付けのため新しく書いた。DB にはつながない。

## 使った命令（全文。いずれも `docs/handoff/migration-runner-redesign/` で流した）
```
/tmp/recon/venv/bin/python -I /tmp/recon/diff_shape.py recon-5-0b/prod003 recon-5-2a/q1-shape > /tmp/recon/q2-A.out
/tmp/recon/venv/bin/python -I /tmp/recon/diff_shape.py recon-5-0b/p01-shape/after-bootstrap recon-5-2a/q1-shape > /tmp/recon/q2-B.out
/tmp/recon/venv/bin/python -I /tmp/recon/marks.py recon-5-0b/prod003 recon-5-0b/p01-shape/after-bootstrap recon-5-2a/q1-shape > /tmp/recon/q2-marks.out
```

## 台本 `/tmp/recon/diff_shape.py` の全文
```python
"""形の比べ台本（DB にはつながない）。

使い方: python -I diff_shape.py <本番のフォルダ> <使い捨てのフォルダ> [--tables-file <表名を1行ずつ書いたファイル>]
出力: markdown（差の全件の表 → 種類ごとの件数の表）。
--tables-file を付けると、その表に属する差に「印=T」を付け、印の無い差だけの表も出す。
"""
import re
import sys
from pathlib import Path

SEP = " ;; "


def read_tsv(path: Path):
    lines = path.read_text(encoding="utf-8").split("\n")
    rows = [ln.split("\t") for ln in lines[1:] if ln != ""]
    return rows


def parse(folder: Path):
    """種類 -> {キー: (表示名, 表, 中身)}"""
    out = {}
    # 列
    d = {}
    for r in read_tsv(folder / "columns.tsv"):
        table = r[0]
        for item in r[2].split(SEP):
            name = item.split("|")[0]
            d[(table, name)] = (f"{table}.{name}", table, item)
    out["列"] = d
    # 索引
    d = {}
    for r in read_tsv(folder / "indexes.tsv"):
        table = r[0]
        for item in r[2].split(SEP):
            m = re.search(r"INDEX (\S+) ON", item)
            name = m.group(1)
            d[name] = (name, table, item)
    out["索引"] = d
    # 制約
    d = {}
    for r in read_tsv(folder / "constraints.tsv"):
        table = r[0]
        for item in r[2].split(SEP):
            name = item.split("|")[0]
            d[(table, name)] = (f"{name} (表 {table})", table, item)
    out["制約"] = d
    # トリガ
    d = {}
    for r in read_tsv(folder / "triggers.tsv"):
        table = r[0]
        for item in r[2].split(SEP):
            m = re.search(r"TRIGGER (\S+) ", item)
            name = m.group(1)
            d[(table, name)] = (f"{name} (表 {table})", table, item)
    out["トリガ"] = d
    # 方針
    d = {}
    for r in read_tsv(folder / "policies.tsv"):
        table = r[0]
        for item in r[2].split(SEP):
            name = item.split("|")[0]
            d[(table, name)] = (f"{table}.{name}", table, item)
    out["方針"] = d
    # 表の印
    d = {}
    for r in read_tsv(folder / "table_flags.tsv"):
        d[r[0]] = (r[0], r[0], "|".join(r[1:]))
    out["表の印"] = d
    # 連番
    d = {}
    for r in read_tsv(folder / "sequences.tsv"):
        d[r[0]] = (r[0], None, "|".join(r[1:]))
    out["連番"] = d
    # 関数
    d = {}
    for r in read_tsv(folder / "functions.tsv"):
        key = f"{r[0]}({r[1]})"
        d[key] = (key, None, "|".join(r[2:]))
    out["関数"] = d
    # ビュー
    d = {}
    for r in read_tsv(folder / "views.tsv"):
        d[r[0]] = (r[0], None, "|".join(r[1:]))
    out["ビュー"] = d
    return out


def cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def main():
    args = sys.argv[1:]
    tables = set()
    if "--tables-file" in args:
        i = args.index("--tables-file")
        tables = {ln.strip() for ln in Path(args[i + 1]).read_text(encoding="utf-8").splitlines() if ln.strip()}
        del args[i:i + 2]
    prod = parse(Path(args[0]))
    disp = parse(Path(args[1]))
    kinds = list(prod.keys())

    def table_of(kind, key, entry):
        t = entry[1]
        if t is None and kind == "連番":
            name = entry[0]
            for tb in tables:
                if name.startswith(tb + "_"):
                    return tb
        return t

    diffs = []  # (種類, 分け方, 名前, 本番の中身, 使い捨ての中身, 印)
    counts = {}
    for kind in kinds:
        p, d = prod[kind], disp[kind]
        only_p = only_d = diff = 0
        for key in sorted(set(p) | set(d), key=lambda k: str(k)):
            pe, de = p.get(key), d.get(key)
            e = pe or de
            mark = "T" if (tables and table_of(kind, key, e) in tables) else ""
            if pe and not de:
                only_p += 1
                diffs.append((kind, "本番だけ", e[0], pe[2], "", mark))
            elif de and not pe:
                only_d += 1
                diffs.append((kind, "使い捨てだけ", e[0], "", de[2], mark))
            elif pe[2] != de[2]:
                diff += 1
                diffs.append((kind, "中身が違う", e[0], pe[2], de[2], mark))
        counts[kind] = (len(p), len(d), only_p, only_d, diff)

    def emit(rows, title):
        print(f"\n## {title}（{len(rows)}件）\n")
        print("| 種類 | 分け方 | 名前 | 本番の中身 | 使い捨ての中身 | 印 |")
        print("|---|---|---|---|---|---|")
        for r in rows:
            print("| " + " | ".join(cell(x) for x in r) + " |")

    emit(diffs, "差の全件")
    if tables:
        others = [r for r in diffs if r[5] != "T"]
        emit(others, "差のうち、指定した表に属さない物")
    print("\n## 種類ごとの件数\n")
    print("| 種類 | 本番の数 | 使い捨ての数 | 本番だけ | 使い捨てだけ | 中身が違う |")
    print("|---|---|---|---|---|---|")
    tot = [0] * 5
    for kind in kinds:
        c = counts[kind]
        print(f"| {kind} | " + " | ".join(str(x) for x in c) + " |")
        tot = [a + b for a, b in zip(tot, c)]
    print("| 合計 | " + " | ".join(str(x) for x in tot) + " |")
    if tables:
        print("\n### 指定した表に属さない差の件数\n")
        print("| 種類 | 本番だけ | 使い捨てだけ | 中身が違う |")
        print("|---|---|---|---|")
        for kind in kinds:
            c = {"本番だけ": 0, "使い捨てだけ": 0, "中身が違う": 0}
            for r in diffs:
                if r[0] == kind and r[5] != "T":
                    c[r[1]] += 1
            print(f"| {kind} | {c['本番だけ']} | {c['使い捨てだけ']} | {c['中身が違う']} |")


if __name__ == "__main__":
    main()
```

## 台本 `/tmp/recon/marks.py` の全文
```python
"""印付けの台本（DB にはつながない）。

使い方: python -I marks.py <本番のフォルダ> <ひな形の直後のフォルダ> <全件の後のフォルダ>
出力: markdown（印付きの全件の表 → 印ごとの件数 → 種類×印の件数）。判断は書かない。
"""
import importlib.util
import sys
from collections import Counter
from pathlib import Path

spec = importlib.util.spec_from_file_location("diff_shape", "/tmp/recon/diff_shape.py")
ds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ds)


def cell(s):
    return ds.cell(s)


def main():
    prod = ds.parse(Path(sys.argv[1]))
    boot = ds.parse(Path(sys.argv[2]))
    q1 = ds.parse(Path(sys.argv[3]))
    rows = []
    for kind in prod.keys():
        p, b, q = prod[kind], boot[kind], q1[kind]
        keys = sorted(set(p) | set(b) | set(q), key=lambda k: str(k))
        for key in keys:
            pe, be, qe = p.get(key), b.get(key), q.get(key)
            name = (pe or be or qe)[0]
            pc = pe[2] if pe else ""
            bc = be[2] if be else ""
            qc = qe[2] if qe else ""
            # 組 B（ひな形の直後 対 本番）での分類
            if pe and not be:
                d0 = "本番だけ"
            elif be and not pe:
                d0 = "使い捨てだけ"
            elif pe and be and pe[2] != be[2]:
                d0 = "中身が違う"
            else:
                d0 = ""
            # 全件の後 対 本番 での分類
            if pe and not qe:
                d1 = "本番だけ"
            elif qe and not pe:
                d1 = "使い捨てだけ"
            elif pe and qe and pe[2] != qe[2]:
                d1 = "中身が違う"
            else:
                d1 = ""
            mark = ""
            if d0 == "本番だけ":
                mark = "印1:全件の後に有る" if qe else "印1:全件の後も無い"
            elif d0 == "使い捨てだけ":
                mark = "印2:残っている" if qe else "印2:消えた"
            elif d0 == "中身が違う":
                if not qe:
                    mark = "印3:全件の後に無い"
                elif qc == pc:
                    mark = "印3:本番と同じになった"
                elif qc == bc:
                    mark = "印3:ひな形のまま"
                else:
                    mark = "印3:どちらとも違う"
            elif d1:
                mark = "印4:新しい差(" + d1 + ")"
            if mark:
                rows.append((kind, name, pc, bc, qc, mark))

    print(f"## 印付きの全件の表（{len(rows)}件）\n")
    print("| 種類 | 名前 | 本番の中身 | ひな形の直後の中身 | 全件の後の中身 | 印 |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(cell(x) for x in r) + " |")

    print("\n## 印ごとの件数\n")
    c = Counter(r[5] for r in rows)
    print("| 印 | 件数 |")
    print("|---|---|")
    for k in sorted(c):
        print(f"| {k} | {c[k]} |")
    print(f"| 合計 | {sum(c.values())} |")

    print("\n## 種類ごと・印ごとの件数\n")
    marks = sorted(c)
    kinds = list(prod.keys())
    print("| 種類 | " + " | ".join(marks) + " | 合計 |")
    print("|---|" + "---|" * (len(marks) + 1))
    cc = Counter((r[0], r[5]) for r in rows)
    for k in kinds:
        vals = [cc[(k, m)] for m in marks]
        print(f"| {k} | " + " | ".join(str(v) for v in vals) + f" | {sum(vals)} |")
    tot = [sum(cc[(k, m)] for k in kinds) for m in marks]
    print("| 合計 | " + " | ".join(str(v) for v in tot) + f" | {sum(tot)} |")


if __name__ == "__main__":
    main()
```

## 印の定義（機械で付けた。判断は書いていない）
- 組 B の差（ひな形の直後 対 本番 = `p01.md` の after-bootstrap の差の全件 793 件）を基準に、1件ずつ `q1-shape/` を見た。
- 印1: 「本番だけ」だった物が全件の後に有るか無いか。
- 印2: 「使い捨てだけ（ひな形だけ）」だった物が残っているか消えたか。
- 印3: 「中身が違う」だった物の全件の後の中身が、本番と同じ／ひな形の直後のまま／どちらとも違う／無い、のどれか。
- 印4: 基準の 793 件に無く、全件を流した後に本番との差として現れた物（新しい差）。
- 注: 基準の 793 件は `p01.md` の after-bootstrap の件数（793）と一致した。

## 組 (A) 本番 003 対 全件の後（`q1-shape/`）

（「使い捨て」の列は全件の後。台本の出力そのまま。）


## 差の全件（147件）

| 種類 | 分け方 | 名前 | 本番の中身 | 使い捨ての中身 | 印 |
|---|---|---|---|---|---|
| 列 | 本番だけ | badge_definitions.created_at | created_at\|timestamp with time zone\|false\|now() |  |  |
| 列 | 本番だけ | badge_definitions.criteria | criteria\|character varying(500)\|false\| |  |  |
| 列 | 本番だけ | badge_definitions.description | description\|character varying(500)\|false\| |  |  |
| 列 | 本番だけ | badge_definitions.icon | icon\|character varying(10)\|false\| |  |  |
| 列 | 本番だけ | badge_definitions.id | id\|integer\|true\|nextval('X.badge_definitions_id_seq'::regclass) |  |  |
| 列 | 本番だけ | badge_definitions.is_active | is_active\|boolean\|false\|true |  |  |
| 列 | 本番だけ | badge_definitions.name | name\|character varying(100)\|true\| |  |  |
| 列 | 本番だけ | badge_definitions.points | points\|integer\|false\|0 |  |  |
| 列 | 本番だけ | badge_definitions.tenant_id | tenant_id\|integer\|true\|3 |  |  |
| 列 | 本番だけ | buddy_feedbacks.context | context\|text\|false\| |  |  |
| 列 | 本番だけ | buddy_feedbacks.created_at | created_at\|timestamp with time zone\|false\|now() |  |  |
| 列 | 本番だけ | buddy_feedbacks.created_by | created_by\|integer\|true\| |  |  |
| 列 | 本番だけ | buddy_feedbacks.feedback_type | feedback_type\|character varying(10)\|true\| |  |  |
| 列 | 本番だけ | buddy_feedbacks.id | id\|integer\|true\|nextval('X.buddy_feedbacks_id_seq'::regclass) |  |  |
| 列 | 本番だけ | buddy_feedbacks.pair_id | pair_id\|integer\|true\| |  |  |
| 列 | 本番だけ | buddy_feedbacks.reason | reason\|text\|false\| |  |  |
| 列 | 本番だけ | buddy_feedbacks.tenant_id | tenant_id\|integer\|true\|3 |  |  |
| 列 | 本番だけ | buddy_pairs.coach_user_id | coach_user_id\|integer\|true\| |  |  |
| 列 | 本番だけ | buddy_pairs.ended_at | ended_at\|timestamp with time zone\|false\| |  |  |
| 列 | 本番だけ | buddy_pairs.id | id\|integer\|true\|nextval('X.buddy_pairs_id_seq'::regclass) |  |  |
| 列 | 本番だけ | buddy_pairs.is_active | is_active\|boolean\|false\|true |  |  |
| 列 | 本番だけ | buddy_pairs.mentee_user_id | mentee_user_id\|integer\|true\| |  |  |
| 列 | 本番だけ | buddy_pairs.notes | notes\|text\|false\| |  |  |
| 列 | 本番だけ | buddy_pairs.started_at | started_at\|timestamp with time zone\|false\|now() |  |  |
| 列 | 本番だけ | buddy_pairs.tenant_id | tenant_id\|integer\|true\|3 |  |  |
| 列 | 本番だけ | calendar_events.category | category\|character varying(50)\|true\|'meeting'::character varying |  |  |
| 列 | 本番だけ | calendar_owner_settings.color | color\|character varying(32)\|true\|'#1a73e8'::character varying |  |  |
| 列 | 本番だけ | calendar_owner_settings.is_visible | is_visible\|boolean\|true\|false |  |  |
| 列 | 本番だけ | calendar_owner_settings.share_mode | share_mode\|character varying(16)\|true\|'self'::character varying |  |  |
| 列 | 本番だけ | calendar_owner_settings.staff_id | staff_id\|integer\|true\| |  |  |
| 列 | 本番だけ | calendar_owner_settings.updated_at | updated_at\|timestamp with time zone\|true\|now() |  |  |
| 列 | 中身が違う | close_reasons.created_at | created_at\|timestamp with time zone\|true\|now() | created_at\|timestamp with time zone\|false\|now() |  |
| 列 | 中身が違う | close_reasons.is_active | is_active\|boolean\|true\|true | is_active\|integer\|true\|1 |  |
| 列 | 中身が違う | companies.tenant_id | tenant_id\|integer\|true\| | tenant_id\|integer\|true\|3 |  |
| 列 | 中身が違う | contacts.tenant_id | tenant_id\|integer\|true\| | tenant_id\|integer\|true\|3 |  |
| 列 | 中身が違う | deal_close_reasons.is_primary | is_primary\|boolean\|true\|false | is_primary\|integer\|true\|0 |  |
| 列 | 中身が違う | leads.lead_code | lead_code\|character varying(20)\|true\|('LD-'::text \|\| lpad((nextval('X.lead_code_seq'::regclass))::text, 5, '0'::text)) | lead_code\|character varying(20)\|false\| |  |
| 列 | 本番だけ | orders.currency | currency\|character varying(10)\|false\|'JPY'::character varying |  |  |
| 列 | 本番だけ | orders.delivered_at | delivered_at\|timestamp with time zone\|false\| |  |  |
| 列 | 本番だけ | orders.invoice_id | invoice_id\|integer\|false\| |  |  |
| 列 | 本番だけ | orders.shipped_at | shipped_at\|timestamp with time zone\|false\| |  |  |
| 列 | 本番だけ | orders.shipping_carrier | shipping_carrier\|character varying(50)\|false\| |  |  |
| 列 | 本番だけ | orders.shipping_country | shipping_country\|character varying(100)\|false\| |  |  |
| 列 | 本番だけ | orders.shipping_fee | shipping_fee\|numeric(15,2)\|false\| |  |  |
| 列 | 本番だけ | orders.tracking_number | tracking_number\|character varying(200)\|false\| |  |  |
| 列 | 本番だけ | staff_ui_preferences.show_buddy_menu | show_buddy_menu\|boolean\|true\|true |  |  |
| 列 | 使い捨てだけ | suppliers.address |  | address\|text\|false\| |  |
| 列 | 使い捨てだけ | suppliers.contact_name |  | contact_name\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | suppliers.created_at |  | created_at\|timestamp with time zone\|false\|now() |  |
| 列 | 使い捨てだけ | suppliers.email |  | email\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | suppliers.id |  | id\|integer\|true\|nextval('X.suppliers_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | suppliers.is_active |  | is_active\|boolean\|false\|true |  |
| 列 | 使い捨てだけ | suppliers.name |  | name\|character varying(255)\|true\| |  |
| 列 | 使い捨てだけ | suppliers.notes |  | notes\|text\|false\| |  |
| 列 | 使い捨てだけ | suppliers.phone |  | phone\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | suppliers.supplier_code |  | supplier_code\|character varying(20)\|false\| |  |
| 列 | 使い捨てだけ | suppliers.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 使い捨てだけ | suppliers.updated_at |  | updated_at\|timestamp with time zone\|false\|now() |  |
| 列 | 本番だけ | user_badges.badge_id | badge_id\|integer\|true\| |  |  |
| 列 | 本番だけ | user_badges.earned_at | earned_at\|timestamp with time zone\|false\|now() |  |  |
| 列 | 本番だけ | user_badges.id | id\|integer\|true\|nextval('X.user_badges_id_seq'::regclass) |  |  |
| 列 | 本番だけ | user_badges.tenant_id | tenant_id\|integer\|true\|3 |  |  |
| 列 | 本番だけ | user_badges.user_id | user_id\|integer\|true\| |  |  |
| 索引 | 本番だけ | badge_definitions_pkey | CREATE UNIQUE INDEX badge_definitions_pkey ON X.badge_definitions USING btree (id) |  |  |
| 索引 | 本番だけ | buddy_feedbacks_pkey | CREATE UNIQUE INDEX buddy_feedbacks_pkey ON X.buddy_feedbacks USING btree (id) |  |  |
| 索引 | 本番だけ | buddy_pairs_pkey | CREATE UNIQUE INDEX buddy_pairs_pkey ON X.buddy_pairs USING btree (id) |  |  |
| 索引 | 本番だけ | buddy_pairs_tenant_id_coach_user_id_mentee_user_id_key | CREATE UNIQUE INDEX buddy_pairs_tenant_id_coach_user_id_mentee_user_id_key ON X.buddy_pairs USING btree (tenant_id, coach_user_id, mentee_user_id) |  |  |
| 索引 | 本番だけ | calendar_owner_settings_pkey | CREATE UNIQUE INDEX calendar_owner_settings_pkey ON X.calendar_owner_settings USING btree (staff_id) |  |  |
| 索引 | 本番だけ | idx_bots_status | CREATE INDEX idx_bots_status ON X.bots USING btree (status) |  |  |
| 索引 | 本番だけ | idx_calendar_owner_settings_staff_id | CREATE INDEX idx_calendar_owner_settings_staff_id ON X.calendar_owner_settings USING btree (staff_id) |  |  |
| 索引 | 本番だけ | idx_invoices_status | CREATE INDEX idx_invoices_status ON X.invoices USING btree (status) |  |  |
| 索引 | 本番だけ | idx_leads_assigned_to | CREATE INDEX idx_leads_assigned_to ON X.leads USING btree (assigned_to) |  |  |
| 索引 | 本番だけ | idx_leads_status | CREATE INDEX idx_leads_status ON X.leads USING btree (status) |  |  |
| 索引 | 本番だけ | idx_po_status | CREATE INDEX idx_po_status ON X.purchase_orders USING btree (status) |  |  |
| 索引 | 本番だけ | idx_po_supplier | CREATE INDEX idx_po_supplier ON X.purchase_orders USING btree (supplier_id) |  |  |
| 索引 | 本番だけ | idx_products_category | CREATE INDEX idx_products_category ON X.products USING btree (category) |  |  |
| 索引 | 本番だけ | idx_products_status | CREATE INDEX idx_products_status ON X.products USING btree (status) |  |  |
| 索引 | 本番だけ | idx_quotes_status | CREATE INDEX idx_quotes_status ON X.quotes USING btree (status) |  |  |
| 索引 | 本番だけ | idx_shipping_rates_lookup | CREATE INDEX idx_shipping_rates_lookup ON X.shipping_rates USING btree (carrier, zone) |  |  |
| 索引 | 本番だけ | idx_team_members_team | CREATE INDEX idx_team_members_team ON X.team_members USING btree (team_id) |  |  |
| 索引 | 本番だけ | idx_team_members_user | CREATE INDEX idx_team_members_user ON X.team_members USING btree (user_id) |  |  |
| 索引 | 本番だけ | idx_user_roles_user | CREATE INDEX idx_user_roles_user ON X.user_roles USING btree (user_id) |  |  |
| 索引 | 本番だけ | leads_tenant_id_lead_code_key | CREATE UNIQUE INDEX leads_tenant_id_lead_code_key ON X.leads USING btree (tenant_id, lead_code) |  |  |
| 索引 | 使い捨てだけ | suppliers_pkey |  | CREATE UNIQUE INDEX suppliers_pkey ON X.suppliers USING btree (id) |  |
| 索引 | 本番だけ | user_badges_pkey | CREATE UNIQUE INDEX user_badges_pkey ON X.user_badges USING btree (id) |  |  |
| 索引 | 本番だけ | user_badges_tenant_id_user_id_badge_id_key | CREATE UNIQUE INDEX user_badges_tenant_id_user_id_badge_id_key ON X.user_badges USING btree (tenant_id, user_id, badge_id) |  |  |
| 制約 | 本番だけ | badge_definitions_pkey (表 badge_definitions) | badge_definitions_pkey\|p\|PRIMARY KEY (id) |  |  |
| 制約 | 使い捨てだけ | bots_owner_staff_id_fkey (表 bots) |  | bots_owner_staff_id_fkey\|f\|FOREIGN KEY (owner_staff_id) REFERENCES users(id) |  |
| 制約 | 本番だけ | buddy_feedbacks_pair_id_fkey (表 buddy_feedbacks) | buddy_feedbacks_pair_id_fkey\|f\|FOREIGN KEY (pair_id) REFERENCES X.buddy_pairs(id) ON DELETE CASCADE |  |  |
| 制約 | 本番だけ | buddy_feedbacks_pkey (表 buddy_feedbacks) | buddy_feedbacks_pkey\|p\|PRIMARY KEY (id) |  |  |
| 制約 | 本番だけ | buddy_pairs_pkey (表 buddy_pairs) | buddy_pairs_pkey\|p\|PRIMARY KEY (id) |  |  |
| 制約 | 本番だけ | buddy_pairs_tenant_id_coach_user_id_mentee_user_id_key (表 buddy_pairs) | buddy_pairs_tenant_id_coach_user_id_mentee_user_id_key\|u\|UNIQUE (tenant_id, coach_user_id, mentee_user_id) |  |  |
| 制約 | 本番だけ | calendar_events_category_check (表 calendar_events) | calendar_events_category_check\|c\|CHECK (((category)::text = ANY ((ARRAY['meeting'::character varying, 'personal'::character varying, 'procurement'::character varying, 'shipping'::character varying, 'billing'::character varying, 'release'::character varying, 'holiday'::character varying])::text[]))) |  |  |
| 制約 | 本番だけ | calendar_owner_settings_pkey (表 calendar_owner_settings) | calendar_owner_settings_pkey\|p\|PRIMARY KEY (staff_id) |  |  |
| 制約 | 本番だけ | calendar_owner_settings_share_mode_check (表 calendar_owner_settings) | calendar_owner_settings_share_mode_check\|c\|CHECK (((share_mode)::text = ANY ((ARRAY['self'::character varying, 'view'::character varying, 'edit'::character varying])::text[]))) |  |  |
| 制約 | 本番だけ | fk_calendar_owner_settings_staff_id_user (表 calendar_owner_settings) | fk_calendar_owner_settings_staff_id_user\|f\|FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE CASCADE |  |  |
| 制約 | 本番だけ | close_reasons_type_check (表 close_reasons) | close_reasons_type_check\|c\|CHECK (((type)::text = ANY ((ARRAY['won'::character varying, 'lost'::character varying])::text[]))) |  |  |
| 制約 | 本番だけ | companies_lead_id_fkey (表 companies) | companies_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  |  |
| 制約 | 使い捨てだけ | fk_companies_lead (表 companies) |  | fk_companies_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  |
| 制約 | 本番だけ | contacts_lead_id_fkey (表 contacts) | contacts_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  |  |
| 制約 | 使い捨てだけ | fk_contacts_lead (表 contacts) |  | fk_contacts_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  |
| 制約 | 使い捨てだけ | deal_close_reasons_lead_id_fkey (表 deal_close_reasons) |  | deal_close_reasons_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  |
| 制約 | 本番だけ | leads_initiative_check (表 leads) | leads_initiative_check\|c\|CHECK (((initiative IS NULL) OR ((initiative)::text = ANY ((ARRAY['outbound'::character varying, 'inbound'::character varying])::text[])))) |  |  |
| 制約 | 本番だけ | leads_tenant_id_lead_code_key (表 leads) | leads_tenant_id_lead_code_key\|u\|UNIQUE (tenant_id, lead_code) |  |  |
| 制約 | 本番だけ | fk_orders_invoice (表 orders) | fk_orders_invoice\|f\|FOREIGN KEY (invoice_id) REFERENCES X.invoices(id) |  |  |
| 制約 | 使い捨てだけ | fk_products_supplier_default (表 products) |  | fk_products_supplier_default\|f\|FOREIGN KEY (supplier_default_id) REFERENCES suppliers(id) |  |
| 制約 | 本番だけ | products_supplier_default_id_fkey (表 products) | products_supplier_default_id_fkey\|f\|FOREIGN KEY (supplier_default_id) REFERENCES suppliers(id) |  |  |
| 制約 | 使い捨てだけ | purchase_order_items_order_item_id_fkey (表 purchase_order_items) |  | purchase_order_items_order_item_id_fkey\|f\|FOREIGN KEY (order_item_id) REFERENCES X.order_items(id) |  |
| 制約 | 使い捨てだけ | quotes_lead_id_fkey (表 quotes) |  | quotes_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  |
| 制約 | 使い捨てだけ | suppliers_pkey (表 suppliers) |  | suppliers_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 中身が違う | chk_tenant_issuer_profiles_phone (表 tenant_issuer_profiles) | chk_tenant_issuer_profiles_phone\|c\|CHECK (((phone IS NULL) OR ((country_code = 'JP'::bpchar) AND ((phone)::text ~ '^[0-9]{10,11}$'::text)) OR ((country_code <> 'JP'::bpchar) AND ((phone)::text ~ '^\\+[0-9]{6,15}$'::text)))) | chk_tenant_issuer_profiles_phone\|c\|CHECK (((phone IS NULL) OR ((country_code = 'JP'::bpchar) AND ((phone)::text ~ '^[0-9]{10,11}$'::text)) OR ((country_code <> 'JP'::bpchar) AND ((phone)::text ~ '^\+[0-9]{6,15}$'::text)))) |  |
| 制約 | 使い捨てだけ | tenant_meta_config_connected_by_staff_id_fkey (表 tenant_meta_config) |  | tenant_meta_config_connected_by_staff_id_fkey\|f\|FOREIGN KEY (connected_by_staff_id) REFERENCES users(id) ON DELETE SET NULL |  |
| 制約 | 本番だけ | user_badges_badge_id_fkey (表 user_badges) | user_badges_badge_id_fkey\|f\|FOREIGN KEY (badge_id) REFERENCES X.badge_definitions(id) ON DELETE CASCADE |  |  |
| 制約 | 本番だけ | user_badges_pkey (表 user_badges) | user_badges_pkey\|p\|PRIMARY KEY (id) |  |  |
| 制約 | 本番だけ | user_badges_tenant_id_user_id_badge_id_key (表 user_badges) | user_badges_tenant_id_user_id_badge_id_key\|u\|UNIQUE (tenant_id, user_id, badge_id) |  |  |
| トリガ | 使い捨てだけ | trg_lead_playbook_updated_at (表 lead_playbook) |  | CREATE TRIGGER trg_lead_playbook_updated_at BEFORE UPDATE ON X.lead_playbook FOR EACH ROW EXECUTE FUNCTION X.trg_set_updated_at() |  |
| 方針 | 本番だけ | badge_definitions.tenant_isolation_badge_definitions | tenant_isolation_badge_definitions\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |  |
| 方針 | 中身が違う | bots.tenant_isolation_bots | tenant_isolation_bots\|*\|true\|public\|(tenant_id = current_tenant_id())\| | tenant_isolation_bots\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 本番だけ | buddy_feedbacks.tenant_isolation_buddy_feedbacks | tenant_isolation_buddy_feedbacks\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |  |
| 方針 | 本番だけ | buddy_pairs.tenant_isolation_buddy_pairs | tenant_isolation_buddy_pairs\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |  |
| 方針 | 中身が違う | companies.tenant_isolation_companies | tenant_isolation_companies\|*\|true\|public\|(tenant_id = current_tenant_id())\| | tenant_isolation_companies\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 中身が違う | company_addresses.tenant_isolation_company_addresses | tenant_isolation_company_addresses\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_addresses.company_id) AND (c.tenant_id = current_tenant_id()))))\| | tenant_isolation_company_addresses\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_addresses.company_id) AND (c.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| |  |
| 方針 | 中身が違う | company_discord.tenant_isolation_company_discord | tenant_isolation_company_discord\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_discord.company_id) AND (c.tenant_id = current_tenant_id()))))\| | tenant_isolation_company_discord\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_discord.company_id) AND (c.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| |  |
| 方針 | 中身が違う | company_sales_channels.tenant_isolation_company_sales_channels | tenant_isolation_company_sales_channels\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_sales_channels.company_id) AND (c.tenant_id = current_tenant_id()))))\| | tenant_isolation_company_sales_channels\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_sales_channels.company_id) AND (c.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| |  |
| 方針 | 中身が違う | contact_contact_channels.tenant_isolation_contact_contact_channels | tenant_isolation_contact_contact_channels\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_contact_channels.contact_id) AND (ct.tenant_id = current_tenant_id()))))\| | tenant_isolation_contact_contact_channels\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_contact_channels.contact_id) AND (ct.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| |  |
| 方針 | 中身が違う | contact_discord.tenant_isolation_contact_discord | tenant_isolation_contact_discord\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_discord.contact_id) AND (ct.tenant_id = current_tenant_id()))))\| | tenant_isolation_contact_discord\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_discord.contact_id) AND (ct.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| |  |
| 方針 | 中身が違う | contact_emails.tenant_isolation_contact_emails | tenant_isolation_contact_emails\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_emails.contact_id) AND (ct.tenant_id = current_tenant_id()))))\| | tenant_isolation_contact_emails\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_emails.contact_id) AND (ct.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| |  |
| 方針 | 中身が違う | contacts.tenant_isolation_contacts | tenant_isolation_contacts\|*\|true\|public\|(tenant_id = current_tenant_id())\| | tenant_isolation_contacts\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 中身が違う | staff.tenant_isolation_staff | tenant_isolation_staff\|*\|true\|public\|(tenant_id = current_tenant_id())\| | tenant_isolation_staff\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 中身が違う | staff_emails.tenant_isolation_staff_emails | tenant_isolation_staff_emails\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.staff s\n  WHERE ((s.id = staff_emails.staff_id) AND (s.tenant_id = current_tenant_id()))))\| | tenant_isolation_staff_emails\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.staff s\n  WHERE ((s.id = staff_emails.staff_id) AND (s.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| |  |
| 方針 | 中身が違う | staff_ui_preferences.tenant_isolation_staff_ui_preferences | tenant_isolation_staff_ui_preferences\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.staff s\n  WHERE ((s.id = staff_ui_preferences.staff_id) AND (s.tenant_id = current_tenant_id()))))\| | tenant_isolation_staff_ui_preferences\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.staff s\n  WHERE ((s.id = staff_ui_preferences.staff_id) AND (s.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| |  |
| 方針 | 使い捨てだけ | suppliers.tenant_isolation_suppliers |  | tenant_isolation_suppliers\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 本番だけ | user_badges.tenant_isolation_user_badges | tenant_isolation_user_badges\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |  |
| 表の印 | 本番だけ | badge_definitions | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |  |
| 表の印 | 本番だけ | buddy_feedbacks | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |  |
| 表の印 | 本番だけ | buddy_pairs | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |  |
| 表の印 | 本番だけ | calendar_owner_settings | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |  |
| 表の印 | 使い捨てだけ | suppliers |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 本番だけ | user_badges | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |  |
| 連番 | 本番だけ | badge_definitions_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  |
| 連番 | 本番だけ | buddy_feedbacks_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  |
| 連番 | 本番だけ | buddy_pairs_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  |
| 連番 | 本番だけ | customer_code_seq | bigint\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  |
| 連番 | 本番だけ | deal_code_seq | bigint\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  |
| 連番 | 本番だけ | lead_code_seq | bigint\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  |
| 連番 | 使い捨てだけ | suppliers_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 本番だけ | user_badges_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  |

## 種類ごとの件数

| 種類 | 本番の数 | 使い捨ての数 | 本番だけ | 使い捨てだけ | 中身が違う |
|---|---|---|---|---|---|
| 列 | 1006 | 973 | 45 | 12 | 6 |
| 索引 | 256 | 235 | 22 | 1 | 0 |
| 制約 | 264 | 254 | 19 | 9 | 1 |
| トリガ | 28 | 29 | 0 | 1 | 0 |
| 方針 | 64 | 61 | 4 | 1 | 12 |
| 表の印 | 79 | 75 | 5 | 1 | 0 |
| 連番 | 72 | 66 | 7 | 1 | 0 |
| 関数 | 15 | 15 | 0 | 0 | 0 |
| ビュー | 2 | 2 | 0 | 0 | 0 |
| 合計 | 1786 | 1710 | 102 | 26 | 19 |


## 組 (B) ひな形の直後 対 全件の後（`q1-shape/`）

（台本の「本番」の列に当たる側がひな形の直後、「使い捨て」の列が全件の後。台本の出力そのまま。）


## 差の全件（648件）

| 種類 | 分け方 | 名前 | 本番の中身 | 使い捨ての中身 | 印 |
|---|---|---|---|---|---|
| 列 | 使い捨てだけ | archives.archived_at |  | archived_at\|timestamp with time zone\|false\|now() |  |
| 列 | 使い捨てだけ | archives.archived_by |  | archived_by\|integer\|false\| |  |
| 列 | 使い捨てだけ | archives.archived_data |  | archived_data\|jsonb\|true\| |  |
| 列 | 使い捨てだけ | archives.id |  | id\|integer\|true\|nextval('X.archives_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | archives.restored_at |  | restored_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | archives.restored_by |  | restored_by\|integer\|false\| |  |
| 列 | 使い捨てだけ | archives.source_id |  | source_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | archives.source_table |  | source_table\|character varying(100)\|true\| |  |
| 列 | 使い捨てだけ | archives.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 使い捨てだけ | calendar_events.calendar_type |  | calendar_type\|character varying(10)\|true\|'shared'::character varying |  |
| 列 | 使い捨てだけ | calendar_events.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | calendar_events.created_by_user_id |  | created_by_user_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | calendar_events.description |  | description\|text\|false\| |  |
| 列 | 使い捨てだけ | calendar_events.end_datetime |  | end_datetime\|timestamp with time zone\|true\| |  |
| 列 | 使い捨てだけ | calendar_events.google_calendar_id |  | google_calendar_id\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | calendar_events.google_event_id |  | google_event_id\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | calendar_events.id |  | id\|integer\|true\|nextval('X.calendar_events_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | calendar_events.is_all_day |  | is_all_day\|boolean\|true\|false |  |
| 列 | 使い捨てだけ | calendar_events.is_cancelled |  | is_cancelled\|boolean\|true\|false |  |
| 列 | 使い捨てだけ | calendar_events.last_synced_at |  | last_synced_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | calendar_events.location |  | location\|text\|false\| |  |
| 列 | 使い捨てだけ | calendar_events.meet_url |  | meet_url\|text\|false\| |  |
| 列 | 使い捨てだけ | calendar_events.original_start_datetime |  | original_start_datetime\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | calendar_events.recurrence_rule |  | recurrence_rule\|text\|false\| |  |
| 列 | 使い捨てだけ | calendar_events.recurring_event_id |  | recurring_event_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | calendar_events.source |  | source\|character varying(10)\|true\|'app'::character varying |  |
| 列 | 使い捨てだけ | calendar_events.start_datetime |  | start_datetime\|timestamp with time zone\|true\| |  |
| 列 | 使い捨てだけ | calendar_events.sync_origin_id |  | sync_origin_id\|character varying(500)\|false\| |  |
| 列 | 使い捨てだけ | calendar_events.sync_status |  | sync_status\|character varying(10)\|false\|'synced'::character varying |  |
| 列 | 使い捨てだけ | calendar_events.title |  | title\|character varying(500)\|true\| |  |
| 列 | 使い捨てだけ | calendar_events.updated_at |  | updated_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | calendar_events.user_id |  | user_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | company_discord.guild_id |  | guild_id\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | contact_contact_channels.guild_id |  | guild_id\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.analysis |  | analysis\|jsonb\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.channel_identity |  | channel_identity\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.channel_type |  | channel_type\|character varying(30)\|true\| |  |
| 列 | 使い捨てだけ | conversation_logs.company_id |  | company_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.contact_id |  | contact_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.content_text |  | content_text\|text\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | conversation_logs.deal_id |  | deal_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.deleted_at |  | deleted_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.direction |  | direction\|character varying(10)\|true\| |  |
| 列 | 使い捨てだけ | conversation_logs.external_message_id |  | external_message_id\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.id |  | id\|integer\|true\|nextval('X.conversation_logs_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | conversation_logs.is_manual |  | is_manual\|boolean\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.lead_id |  | lead_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | conversation_logs.occurred_at |  | occurred_at\|timestamp with time zone\|true\| |  |
| 列 | 使い捨てだけ | conversation_logs.original_language |  | original_language\|character varying(10)\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.raw_payload |  | raw_payload\|jsonb\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.recorded_by_user_id |  | recorded_by_user_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.sender |  | sender\|character varying(100)\|false\| |  |
| 列 | 使い捨てだけ | conversation_logs.status |  | status\|character varying(20)\|false\|'sent'::character varying |  |
| 列 | 使い捨てだけ | conversation_logs.tenant_id |  | tenant_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | conversation_logs.translated_text |  | translated_text\|text\|false\| |  |
| 列 | 使い捨てだけ | customer_scores.calibration_id |  | calibration_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | customer_scores.confidence |  | confidence\|numeric(4,3)\|true\| |  |
| 列 | 使い捨てだけ | customer_scores.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | customer_scores.id |  | id\|integer\|true\|nextval('X.customer_scores_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | customer_scores.is_cold_start |  | is_cold_start\|boolean\|true\|true |  |
| 列 | 使い捨てだけ | customer_scores.lead_id |  | lead_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | customer_scores.override_at |  | override_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | customer_scores.override_by |  | override_by\|integer\|false\| |  |
| 列 | 使い捨てだけ | customer_scores.override_note |  | override_note\|text\|false\| |  |
| 列 | 使い捨てだけ | customer_scores.override_score |  | override_score\|numeric(5,3)\|false\| |  |
| 列 | 使い捨てだけ | customer_scores.sample_size |  | sample_size\|integer\|true\|0 |  |
| 列 | 使い捨てだけ | customer_scores.score |  | score\|numeric(5,3)\|true\| |  |
| 列 | 使い捨てだけ | customer_scores.scored_at |  | scored_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | customer_scores.signal_summary |  | signal_summary\|jsonb\|true\|'{}'::jsonb |  |
| 列 | 使い捨てだけ | customer_scores.tenant_id |  | tenant_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | customer_scores.tier |  | tier\|character varying(10)\|true\| |  |
| 列 | 中身が違う | deal_close_reasons.lead_id | lead_id\|integer\|false\| | lead_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | discord_channel_webhooks.channel_id |  | channel_id\|text\|true\| |  |
| 列 | 使い捨てだけ | discord_channel_webhooks.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | discord_channel_webhooks.id |  | id\|integer\|true\|nextval('X.discord_channel_webhooks_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | discord_channel_webhooks.tenant_id |  | tenant_id\|integer\|true\|(current_setting('app.tenant_id'::text, true))::integer |  |
| 列 | 使い捨てだけ | discord_channel_webhooks.webhook_id |  | webhook_id\|text\|true\| |  |
| 列 | 使い捨てだけ | discord_channel_webhooks.webhook_token_encrypted |  | webhook_token_encrypted\|text\|true\| |  |
| 列 | 使い捨てだけ | erp_sync_logs.completed_at |  | completed_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | erp_sync_logs.created_by |  | created_by\|integer\|false\| |  |
| 列 | 使い捨てだけ | erp_sync_logs.direction |  | direction\|character varying(10)\|true\|'export'::character varying |  |
| 列 | 使い捨てだけ | erp_sync_logs.error_message |  | error_message\|text\|false\| |  |
| 列 | 使い捨てだけ | erp_sync_logs.id |  | id\|integer\|true\|nextval('X.erp_sync_logs_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | erp_sync_logs.record_count |  | record_count\|integer\|false\|0 |  |
| 列 | 使い捨てだけ | erp_sync_logs.started_at |  | started_at\|timestamp with time zone\|false\|now() |  |
| 列 | 使い捨てだけ | erp_sync_logs.status |  | status\|character varying(20)\|false\|'pending'::character varying |  |
| 列 | 使い捨てだけ | erp_sync_logs.sync_type |  | sync_type\|character varying(50)\|true\| |  |
| 列 | 使い捨てだけ | erp_sync_logs.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 中身が違う | invoices.company_id | company_id\|integer\|false\| | company_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | lead_attachments.content_type |  | content_type\|character varying(128)\|false\| |  |
| 列 | 使い捨てだけ | lead_attachments.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | lead_attachments.file_path |  | file_path\|text\|true\| |  |
| 列 | 使い捨てだけ | lead_attachments.file_size |  | file_size\|bigint\|true\| |  |
| 列 | 使い捨てだけ | lead_attachments.id |  | id\|integer\|true\|nextval('X.lead_attachments_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | lead_attachments.lead_id |  | lead_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | lead_attachments.message_id |  | message_id\|character varying(64)\|true\| |  |
| 列 | 使い捨てだけ | lead_attachments.original_filename |  | original_filename\|text\|false\| |  |
| 列 | 使い捨てだけ | lead_attachments.platform |  | platform\|character varying(32)\|true\| |  |
| 列 | 使い捨てだけ | lead_attachments.tenant_id |  | tenant_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | lead_attachments.updated_at |  | updated_at\|timestamp with time zone\|true\|now() |  |
| 列 | 本番だけ | leads.converted_deal_id | converted_deal_id\|integer\|false\| |  |  |
| 列 | 使い捨てだけ | leads.discord_dm_channel_id |  | discord_dm_channel_id\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | leads.discord_guild_channel_id |  | discord_guild_channel_id\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | leads.discord_id |  | discord_id\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | leads.discord_role_sync_at |  | discord_role_sync_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | leads.discord_role_sync_status |  | discord_role_sync_status\|character varying(20)\|false\| |  |
| 列 | 使い捨てだけ | leads.discord_user_id |  | discord_user_id\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | leads.english_name |  | english_name\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | leads.instagram_link |  | instagram_link\|character varying(1000)\|false\| |  |
| 列 | 使い捨てだけ | leads.messenger_link |  | messenger_link\|character varying(1000)\|false\| |  |
| 列 | 使い捨てだけ | leads.whatsapp_link |  | whatsapp_link\|character varying(1000)\|false\| |  |
| 列 | 使い捨てだけ | message_labels.confidence |  | confidence\|numeric(4,3)\|true\| |  |
| 列 | 使い捨てだけ | message_labels.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | message_labels.direction |  | direction\|character varying(10)\|true\| |  |
| 列 | 使い捨てだけ | message_labels.id |  | id\|integer\|true\|nextval('X.message_labels_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | message_labels.label |  | label\|character varying(30)\|true\| |  |
| 列 | 使い捨てだけ | message_labels.lead_id |  | lead_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | message_labels.message_id |  | message_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | message_labels.override_at |  | override_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | message_labels.override_by |  | override_by\|integer\|false\| |  |
| 列 | 使い捨てだけ | message_labels.source |  | source\|character varying(20)\|true\|'rule'::character varying |  |
| 列 | 使い捨てだけ | message_labels.tenant_id |  | tenant_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | message_translations.confidence |  | confidence\|real\|false\| |  |
| 列 | 使い捨てだけ | message_translations.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | message_translations.engine |  | engine\|character varying(50)\|true\|'gemini-2.5-flash'::character varying |  |
| 列 | 使い捨てだけ | message_translations.id |  | id\|integer\|true\|nextval('X.message_translations_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | message_translations.message_id |  | message_id\|text\|true\| |  |
| 列 | 使い捨てだけ | message_translations.original_language |  | original_language\|character varying(10)\|false\| |  |
| 列 | 使い捨てだけ | message_translations.target_language |  | target_language\|character varying(10)\|true\| |  |
| 列 | 使い捨てだけ | message_translations.tenant_id |  | tenant_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | message_translations.translated_text |  | translated_text\|text\|true\| |  |
| 列 | 使い捨てだけ | meta_message_reactions.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | meta_message_reactions.emoji_animated |  | emoji_animated\|boolean\|false\|false |  |
| 列 | 使い捨てだけ | meta_message_reactions.emoji_id |  | emoji_id\|text\|false\| |  |
| 列 | 使い捨てだけ | meta_message_reactions.emoji_name |  | emoji_name\|text\|true\| |  |
| 列 | 使い捨てだけ | meta_message_reactions.id |  | id\|integer\|true\|nextval('X.meta_message_reactions_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | meta_message_reactions.is_bot_reaction |  | is_bot_reaction\|boolean\|false\|false |  |
| 列 | 使い捨てだけ | meta_message_reactions.meta_message_id |  | meta_message_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | meta_message_reactions.reactor_discord_user_id |  | reactor_discord_user_id\|text\|true\| |  |
| 列 | 使い捨てだけ | meta_message_reactions.reactor_display_name |  | reactor_display_name\|text\|false\| |  |
| 列 | 使い捨てだけ | meta_message_reactions.tenant_id |  | tenant_id\|integer\|true\|(current_setting('app.tenant_id'::text, true))::integer |  |
| 列 | 使い捨てだけ | meta_messages.attachment_type |  | attachment_type\|character varying(20)\|false\| |  |
| 列 | 使い捨てだけ | meta_messages.attachment_url |  | attachment_url\|text\|false\| |  |
| 列 | 使い捨てだけ | meta_messages.error_code |  | error_code\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | meta_messages.error_message |  | error_message\|text\|false\| |  |
| 列 | 使い捨てだけ | meta_messages.message_tag |  | message_tag\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | meta_messages.messaging_type |  | messaging_type\|character varying(20)\|false\| |  |
| 列 | 使い捨てだけ | meta_messages.page_id |  | page_id\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | meta_messages.recipient_id |  | recipient_id\|character varying(100)\|false\| |  |
| 列 | 使い捨てだけ | meta_messages.seen_at |  | seen_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | meta_messages.seen_by_staff_id |  | seen_by_staff_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | meta_messages.sent_by_staff_id |  | sent_by_staff_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | notification_channels.blueprint_key |  | blueprint_key\|text\|false\| |  |
| 列 | 使い捨てだけ | notification_channels.channel_name |  | channel_name\|character varying(100)\|true\| |  |
| 列 | 使い捨てだけ | notification_channels.channel_type |  | channel_type\|character varying(20)\|true\|'discord'::character varying |  |
| 列 | 使い捨てだけ | notification_channels.created_at |  | created_at\|timestamp with time zone\|false\|now() |  |
| 列 | 使い捨てだけ | notification_channels.event_types |  | event_types\|text\|false\|'[]'::text |  |
| 列 | 使い捨てだけ | notification_channels.id |  | id\|integer\|true\|nextval('X.notification_channels_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | notification_channels.is_active |  | is_active\|boolean\|false\|true |  |
| 列 | 使い捨てだけ | notification_channels.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 使い捨てだけ | notification_channels.updated_at |  | updated_at\|timestamp with time zone\|false\|now() |  |
| 列 | 使い捨てだけ | notification_channels.webhook_url |  | webhook_url\|character varying(500)\|true\| |  |
| 列 | 使い捨てだけ | notification_logs.channel_id |  | channel_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | notification_logs.created_at |  | created_at\|timestamp with time zone\|false\|now() |  |
| 列 | 使い捨てだけ | notification_logs.error_message |  | error_message\|text\|false\| |  |
| 列 | 使い捨てだけ | notification_logs.event_type |  | event_type\|character varying(50)\|true\| |  |
| 列 | 使い捨てだけ | notification_logs.id |  | id\|integer\|true\|nextval('X.notification_logs_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | notification_logs.message |  | message\|text\|false\| |  |
| 列 | 使い捨てだけ | notification_logs.sent_at |  | sent_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | notification_logs.status |  | status\|character varying(20)\|false\|'pending'::character varying |  |
| 列 | 使い捨てだけ | notification_logs.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 使い捨てだけ | notification_logs.title |  | title\|character varying(255)\|true\| |  |
| 列 | 使い捨てだけ | order_commissions.calculated_amount |  | calculated_amount\|numeric(14,2)\|true\|0 |  |
| 列 | 使い捨てだけ | order_commissions.calculated_at |  | calculated_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | order_commissions.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | order_commissions.id |  | id\|integer\|true\|nextval('X.order_commissions_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | order_commissions.notes |  | notes\|text\|false\| |  |
| 列 | 使い捨てだけ | order_commissions.order_id |  | order_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | order_commissions.role |  | role\|text\|true\| |  |
| 列 | 使い捨てだけ | order_commissions.staff_id |  | staff_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | order_commissions.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 使い捨てだけ | order_commissions.updated_at |  | updated_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | order_financials.ad_cost |  | ad_cost\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_financials.commission_base_amount |  | commission_base_amount\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_financials.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | order_financials.exchange_fee |  | exchange_fee\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_financials.id |  | id\|integer\|true\|nextval('X.order_financials_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | order_financials.notes |  | notes\|text\|false\| |  |
| 列 | 使い捨てだけ | order_financials.order_id |  | order_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | order_financials.outsource_fee |  | outsource_fee\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_financials.packing_fee |  | packing_fee\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_financials.paypal_fee |  | paypal_fee\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_financials.purchase_cost |  | purchase_cost\|numeric(14,2)\|false\| |  |
| 列 | 使い捨てだけ | order_financials.purchase_shipping |  | purchase_shipping\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_financials.refund_amount |  | refund_amount\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_financials.return_fee |  | return_fee\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_financials.revenue_amount |  | revenue_amount\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_financials.tax_refund |  | tax_refund\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_financials.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 使い捨てだけ | order_financials.updated_at |  | updated_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | order_financials.wise_fee |  | wise_fee\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_purchase_details.carrier_name |  | carrier_name\|text\|false\| |  |
| 列 | 使い捨てだけ | order_purchase_details.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | order_purchase_details.id |  | id\|integer\|true\|nextval('X.order_purchase_details_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | order_purchase_details.order_id |  | order_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | order_purchase_details.purchase_amount |  | purchase_amount\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_purchase_details.purchase_date |  | purchase_date\|date\|false\| |  |
| 列 | 使い捨てだけ | order_purchase_details.purchase_note |  | purchase_note\|text\|false\| |  |
| 列 | 使い捨てだけ | order_purchase_details.purchase_quantity |  | purchase_quantity\|integer\|false\|0 |  |
| 列 | 使い捨てだけ | order_purchase_details.purchase_shipping |  | purchase_shipping\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_purchase_details.purchase_staff |  | purchase_staff\|text\|false\| |  |
| 列 | 使い捨てだけ | order_purchase_details.purchase_status |  | purchase_status\|text\|true\|''::text |  |
| 列 | 使い捨てだけ | order_purchase_details.purchase_total |  | purchase_total\|numeric(14,2)\|false\|0 |  |
| 列 | 使い捨てだけ | order_purchase_details.supplier_name |  | supplier_name\|text\|false\| |  |
| 列 | 使い捨てだけ | order_purchase_details.supplier_url |  | supplier_url\|text\|false\| |  |
| 列 | 使い捨てだけ | order_purchase_details.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 使い捨てだけ | order_purchase_details.transaction_no |  | transaction_no\|text\|false\| |  |
| 列 | 使い捨てだけ | order_purchase_details.updated_at |  | updated_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | order_purchase_details.waybill_no |  | waybill_no\|text\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.address1 |  | address1\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.address2 |  | address2\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.address3 |  | address3\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.address_type |  | address_type\|character varying(20)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.box_count |  | box_count\|integer\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.carrier |  | carrier\|character varying(20)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.city |  | city\|character varying(100)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.confirmed_currency |  | confirmed_currency\|character varying(10)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.confirmed_shipping_fee |  | confirmed_shipping_fee\|numeric(12,2)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.country_code |  | country_code\|character varying(10)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | order_shipping_details.email |  | email\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.est_shipping_fee |  | est_shipping_fee\|numeric(12,2)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.exchange_rate |  | exchange_rate\|numeric(12,6)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.fedex_id |  | fedex_id\|character varying(100)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.height_cm |  | height_cm\|numeric(8,2)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.hs_code |  | hs_code\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.id |  | id\|integer\|true\|nextval('X.order_shipping_details_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | order_shipping_details.inspection_status |  | inspection_status\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.item_description |  | item_description\|character varying(500)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.item_price_usd |  | item_price_usd\|numeric(12,2)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.label_drive_url |  | label_drive_url\|text\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.label_issued_at |  | label_issued_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.length_cm |  | length_cm\|numeric(8,2)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.notified_at |  | notified_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.order_id |  | order_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | order_shipping_details.packing_memo |  | packing_memo\|text\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.packing_type |  | packing_type\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.phone |  | phone\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.pickup_confirmation_code |  | pickup_confirmation_code\|character varying(100)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.pickup_requested_at |  | pickup_requested_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.recipient_name |  | recipient_name\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.ship_date |  | ship_date\|date\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.ship_memo |  | ship_memo\|text\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.ship_method |  | ship_method\|character varying(50)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.shipped_at |  | shipped_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.state_code |  | state_code\|character varying(20)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.surcharges |  | surcharges\|jsonb\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.tax_id |  | tax_id\|character varying(100)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.tax_number |  | tax_number\|character varying(100)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 使い捨てだけ | order_shipping_details.tracking_number |  | tracking_number\|character varying(200)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.updated_at |  | updated_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | order_shipping_details.volume_g |  | volume_g\|numeric(10,2)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.weight_kg |  | weight_kg\|numeric(8,3)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.width_cm |  | width_cm\|numeric(8,2)\|false\| |  |
| 列 | 使い捨てだけ | order_shipping_details.zip_code |  | zip_code\|character varying(50)\|false\| |  |
| 列 | 中身が違う | orders.company_id | company_id\|integer\|false\| | company_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.confidence |  | confidence\|real\|false\| |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.confirmed_at |  | confirmed_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.draft_text |  | draft_text\|text\|true\| |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.final_text |  | final_text\|text\|false\| |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.flagged_terms |  | flagged_terms\|jsonb\|false\| |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.id |  | id\|integer\|true\|nextval('X.outbound_translation_drafts_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.is_edited |  | is_edited\|boolean\|false\| |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.lead_id |  | lead_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.meta_message_id |  | meta_message_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.model |  | model\|character varying(50)\|true\| |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.original_text |  | original_text\|text\|true\| |  |
| 列 | 使い捨てだけ | outbound_translation_drafts.tenant_id |  | tenant_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | paypal_disputes.amount |  | amount\|numeric(15,2)\|false\| |  |
| 列 | 使い捨てだけ | paypal_disputes.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | paypal_disputes.currency |  | currency\|text\|false\| |  |
| 列 | 使い捨てだけ | paypal_disputes.dispute_id |  | dispute_id\|text\|true\| |  |
| 列 | 使い捨てだけ | paypal_disputes.id |  | id\|integer\|true\|nextval('X.paypal_disputes_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | paypal_disputes.invoice_id |  | invoice_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | paypal_disputes.pp_status |  | pp_status\|text\|false\| |  |
| 列 | 使い捨てだけ | paypal_disputes.raw |  | raw\|jsonb\|false\| |  |
| 列 | 使い捨てだけ | paypal_disputes.reason |  | reason\|text\|false\| |  |
| 列 | 使い捨てだけ | paypal_disputes.updated_at |  | updated_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | purchase_orders.company_name_snapshot |  | company_name_snapshot\|character varying(255)\|false\| |  |
| 列 | 使い捨てだけ | purchase_orders.contact_info_snapshot |  | contact_info_snapshot\|text\|false\| |  |
| 列 | 中身が違う | quotes.company_id | company_id\|integer\|false\| | company_id\|integer\|true\| |  |
| 列 | 中身が違う | quotes.lead_id | lead_id\|integer\|false\| | lead_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | shifts.created_at |  | created_at\|timestamp with time zone\|false\|now() |  |
| 列 | 使い捨てだけ | shifts.end_time |  | end_time\|time without time zone\|true\| |  |
| 列 | 使い捨てだけ | shifts.id |  | id\|integer\|true\|nextval('X.shifts_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | shifts.notes |  | notes\|text\|false\| |  |
| 列 | 使い捨てだけ | shifts.shift_date |  | shift_date\|date\|true\| |  |
| 列 | 使い捨てだけ | shifts.shift_type |  | shift_type\|character varying(20)\|false\|'normal'::character varying |  |
| 列 | 使い捨てだけ | shifts.start_time |  | start_time\|time without time zone\|true\| |  |
| 列 | 使い捨てだけ | shifts.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 使い捨てだけ | shifts.updated_at |  | updated_at\|timestamp with time zone\|false\|now() |  |
| 列 | 使い捨てだけ | shifts.user_id |  | user_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | staff.avatar_token |  | avatar_token\|text\|false\| |  |
| 列 | 使い捨てだけ | staff.is_employee |  | is_employee\|boolean\|true\|false |  |
| 列 | 使い捨てだけ | staff.phone |  | phone\|character varying(20)\|false\| |  |
| 列 | 使い捨てだけ | staff_reports.ai_feedback |  | ai_feedback\|text\|false\| |  |
| 列 | 使い捨てだけ | staff_reports.challenges |  | challenges\|text\|false\| |  |
| 列 | 使い捨てだけ | staff_reports.created_at |  | created_at\|timestamp with time zone\|false\|now() |  |
| 列 | 使い捨てだけ | staff_reports.goals |  | goals\|text\|false\| |  |
| 列 | 使い捨てだけ | staff_reports.id |  | id\|integer\|true\|nextval('X.staff_reports_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | staff_reports.period |  | period\|character varying(20)\|true\| |  |
| 列 | 使い捨てだけ | staff_reports.report_code |  | report_code\|character varying(20)\|false\| |  |
| 列 | 使い捨てだけ | staff_reports.report_type |  | report_type\|character varying(20)\|true\| |  |
| 列 | 使い捨てだけ | staff_reports.review |  | review\|text\|false\| |  |
| 列 | 使い捨てだけ | staff_reports.reviewed_at |  | reviewed_at\|timestamp with time zone\|false\| |  |
| 列 | 使い捨てだけ | staff_reports.reviewer_comment |  | reviewer_comment\|text\|false\| |  |
| 列 | 使い捨てだけ | staff_reports.reviewer_id |  | reviewer_id\|integer\|false\| |  |
| 列 | 使い捨てだけ | staff_reports.self_evaluation |  | self_evaluation\|text\|false\| |  |
| 列 | 使い捨てだけ | staff_reports.submitted_at |  | submitted_at\|timestamp with time zone\|false\|now() |  |
| 列 | 使い捨てだけ | staff_reports.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 使い捨てだけ | staff_reports.updated_at |  | updated_at\|timestamp with time zone\|false\|now() |  |
| 列 | 使い捨てだけ | staff_reports.user_id |  | user_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | tenant_calibrations.calibrated_at |  | calibrated_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | tenant_calibrations.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | tenant_calibrations.id |  | id\|integer\|true\|nextval('X.tenant_calibrations_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | tenant_calibrations.is_cold_start |  | is_cold_start\|boolean\|true\|true |  |
| 列 | 使い捨てだけ | tenant_calibrations.label_weights |  | label_weights\|jsonb\|true\|'{}'::jsonb |  |
| 列 | 使い捨てだけ | tenant_calibrations.loss_sample_size |  | loss_sample_size\|integer\|true\|0 |  |
| 列 | 使い捨てだけ | tenant_calibrations.tenant_id |  | tenant_id\|integer\|true\| |  |
| 列 | 使い捨てだけ | tenant_calibrations.win_sample_size |  | win_sample_size\|integer\|true\|0 |  |
| 列 | 使い捨てだけ | tenant_commission_settings.commission_rates |  | commission_rates\|jsonb\|true\|'{"ship": {"type": "fixed", "value": 200}, "order": {"type": "rate", "value": 0.10}, "sales": {"type": "rate", "value": 0.10}, "trouble": {"type": "fixed", "value": 500}, "purchase": {"type": "fixed", "value": 100}}'::jsonb |  |
| 列 | 使い捨てだけ | tenant_commission_settings.created_at |  | created_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | tenant_commission_settings.id |  | id\|integer\|true\|nextval('X.tenant_commission_settings_id_seq'::regclass) |  |
| 列 | 使い捨てだけ | tenant_commission_settings.tenant_id |  | tenant_id\|integer\|true\|3 |  |
| 列 | 使い捨てだけ | tenant_commission_settings.updated_at |  | updated_at\|timestamp with time zone\|true\|now() |  |
| 列 | 使い捨てだけ | tenant_meta_config.granted_scopes |  | granted_scopes\|jsonb\|false\| |  |
| 索引 | 使い捨てだけ | archives_pkey |  | CREATE UNIQUE INDEX archives_pkey ON X.archives USING btree (id) |  |
| 索引 | 使い捨てだけ | calendar_events_exception_unique_idx |  | CREATE UNIQUE INDEX calendar_events_exception_unique_idx ON X.calendar_events USING btree (recurring_event_id, original_start_datetime) WHERE (recurring_event_id IS NOT NULL) |  |
| 索引 | 使い捨てだけ | calendar_events_pkey |  | CREATE UNIQUE INDEX calendar_events_pkey ON X.calendar_events USING btree (id) |  |
| 索引 | 使い捨てだけ | conversation_logs_external_message_id_key |  | CREATE UNIQUE INDEX conversation_logs_external_message_id_key ON X.conversation_logs USING btree (external_message_id) |  |
| 索引 | 使い捨てだけ | conversation_logs_pkey |  | CREATE UNIQUE INDEX conversation_logs_pkey ON X.conversation_logs USING btree (id) |  |
| 索引 | 使い捨てだけ | customer_scores_pkey |  | CREATE UNIQUE INDEX customer_scores_pkey ON X.customer_scores USING btree (id) |  |
| 索引 | 使い捨てだけ | discord_channel_webhooks_pkey |  | CREATE UNIQUE INDEX discord_channel_webhooks_pkey ON X.discord_channel_webhooks USING btree (id) |  |
| 索引 | 使い捨てだけ | erp_sync_logs_pkey |  | CREATE UNIQUE INDEX erp_sync_logs_pkey ON X.erp_sync_logs USING btree (id) |  |
| 索引 | 使い捨てだけ | idx_archives_source |  | CREATE INDEX idx_archives_source ON X.archives USING btree (source_table, source_id) |  |
| 索引 | 使い捨てだけ | idx_calendar_events_google_id |  | CREATE INDEX idx_calendar_events_google_id ON X.calendar_events USING btree (google_event_id) WHERE (google_event_id IS NOT NULL) |  |
| 索引 | 使い捨てだけ | idx_calendar_events_range |  | CREATE INDEX idx_calendar_events_range ON X.calendar_events USING btree (start_datetime, end_datetime) |  |
| 索引 | 使い捨てだけ | idx_calendar_events_sync_origin |  | CREATE INDEX idx_calendar_events_sync_origin ON X.calendar_events USING btree (sync_origin_id) WHERE (sync_origin_id IS NOT NULL) |  |
| 索引 | 使い捨てだけ | idx_calendar_events_user_type |  | CREATE INDEX idx_calendar_events_user_type ON X.calendar_events USING btree (user_id, calendar_type) |  |
| 索引 | 使い捨てだけ | idx_ccc_unique_channel_purpose |  | CREATE UNIQUE INDEX idx_ccc_unique_channel_purpose ON X.contact_contact_channels USING btree (contact_id, channel, COALESCE(purpose, ''::character varying)) |  |
| 索引 | 使い捨てだけ | idx_conv_logs_company_id |  | CREATE INDEX idx_conv_logs_company_id ON X.conversation_logs USING btree (company_id) |  |
| 索引 | 使い捨てだけ | idx_conv_logs_contact_id |  | CREATE INDEX idx_conv_logs_contact_id ON X.conversation_logs USING btree (contact_id) |  |
| 索引 | 使い捨てだけ | idx_conv_logs_deleted_at |  | CREATE INDEX idx_conv_logs_deleted_at ON X.conversation_logs USING btree (deleted_at) WHERE (deleted_at IS NOT NULL) |  |
| 索引 | 使い捨てだけ | idx_conv_logs_occurred_at |  | CREATE INDEX idx_conv_logs_occurred_at ON X.conversation_logs USING btree (occurred_at DESC) |  |
| 索引 | 使い捨てだけ | idx_conv_logs_tenant_id |  | CREATE INDEX idx_conv_logs_tenant_id ON X.conversation_logs USING btree (tenant_id) |  |
| 索引 | 使い捨てだけ | idx_customer_scores_tier |  | CREATE INDEX idx_customer_scores_tier ON X.customer_scores USING btree (tier) |  |
| 索引 | 使い捨てだけ | idx_dcw_tenant |  | CREATE INDEX idx_dcw_tenant ON X.discord_channel_webhooks USING btree (tenant_id) |  |
| 索引 | 使い捨てだけ | idx_la_lead_id |  | CREATE INDEX idx_la_lead_id ON X.lead_attachments USING btree (lead_id) |  |
| 索引 | 使い捨てだけ | idx_la_message_id |  | CREATE UNIQUE INDEX idx_la_message_id ON X.lead_attachments USING btree (message_id) |  |
| 索引 | 使い捨てだけ | idx_la_tenant_created |  | CREATE INDEX idx_la_tenant_created ON X.lead_attachments USING btree (tenant_id, created_at) |  |
| 索引 | 使い捨てだけ | idx_leads_channel_type |  | CREATE INDEX idx_leads_channel_type ON X.leads USING btree (channel_type) |  |
| 索引 | 使い捨てだけ | idx_leads_discord_guild_channel_id |  | CREATE INDEX idx_leads_discord_guild_channel_id ON X.leads USING btree (tenant_id, discord_guild_channel_id) WHERE (discord_guild_channel_id IS NOT NULL) |  |
| 索引 | 使い捨てだけ | idx_leads_discord_user_id |  | CREATE INDEX idx_leads_discord_user_id ON X.leads USING btree (tenant_id, discord_user_id) WHERE (discord_user_id IS NOT NULL) |  |
| 索引 | 使い捨てだけ | idx_leads_initiative |  | CREATE INDEX idx_leads_initiative ON X.leads USING btree (initiative) WHERE (initiative IS NOT NULL) |  |
| 索引 | 使い捨てだけ | idx_message_labels_lead_id |  | CREATE INDEX idx_message_labels_lead_id ON X.message_labels USING btree (lead_id) |  |
| 索引 | 使い捨てだけ | idx_message_labels_message_id |  | CREATE INDEX idx_message_labels_message_id ON X.message_labels USING btree (message_id) |  |
| 索引 | 使い捨てだけ | idx_message_translations_message_id |  | CREATE INDEX idx_message_translations_message_id ON X.message_translations USING btree (message_id) |  |
| 索引 | 使い捨てだけ | idx_meta_messages_discord |  | CREATE INDEX idx_meta_messages_discord ON X.meta_messages USING btree (tenant_id, platform, lead_id) WHERE ((platform)::text = 'discord'::text) |  |
| 索引 | 使い捨てだけ | idx_meta_messages_lead_created |  | CREATE INDEX idx_meta_messages_lead_created ON X.meta_messages USING btree (lead_id, created_at DESC) |  |
| 索引 | 使い捨てだけ | idx_meta_messages_lead_unread |  | CREATE INDEX idx_meta_messages_lead_unread ON X.meta_messages USING btree (lead_id) WHERE (((direction)::text = 'inbound'::text) AND (seen_at IS NULL)) |  |
| 索引 | 使い捨てだけ | idx_meta_messages_tenant_page |  | CREATE INDEX idx_meta_messages_tenant_page ON X.meta_messages USING btree (tenant_id, page_id) WHERE (page_id IS NOT NULL) |  |
| 索引 | 使い捨てだけ | idx_mmr_meta_message_id |  | CREATE INDEX idx_mmr_meta_message_id ON X.meta_message_reactions USING btree (meta_message_id) |  |
| 索引 | 使い捨てだけ | idx_mmr_tenant |  | CREATE INDEX idx_mmr_tenant ON X.meta_message_reactions USING btree (tenant_id) |  |
| 索引 | 使い捨てだけ | idx_order_commissions_order |  | CREATE INDEX idx_order_commissions_order ON X.order_commissions USING btree (order_id) |  |
| 索引 | 使い捨てだけ | idx_order_commissions_staff |  | CREATE INDEX idx_order_commissions_staff ON X.order_commissions USING btree (staff_id) |  |
| 索引 | 使い捨てだけ | idx_order_commissions_tenant |  | CREATE INDEX idx_order_commissions_tenant ON X.order_commissions USING btree (tenant_id) |  |
| 索引 | 使い捨てだけ | idx_order_commissions_tenant_calc |  | CREATE INDEX idx_order_commissions_tenant_calc ON X.order_commissions USING btree (tenant_id, calculated_at) |  |
| 索引 | 使い捨てだけ | idx_order_financials_created_at |  | CREATE INDEX idx_order_financials_created_at ON X.order_financials USING btree (created_at) |  |
| 索引 | 使い捨てだけ | idx_order_financials_order |  | CREATE INDEX idx_order_financials_order ON X.order_financials USING btree (order_id) |  |
| 索引 | 使い捨てだけ | idx_order_financials_tenant |  | CREATE INDEX idx_order_financials_tenant ON X.order_financials USING btree (tenant_id) |  |
| 索引 | 使い捨てだけ | idx_order_purchase_details_order |  | CREATE INDEX idx_order_purchase_details_order ON X.order_purchase_details USING btree (order_id) |  |
| 索引 | 使い捨てだけ | idx_order_purchase_details_status |  | CREATE INDEX idx_order_purchase_details_status ON X.order_purchase_details USING btree (purchase_status) |  |
| 索引 | 使い捨てだけ | idx_order_purchase_details_tenant |  | CREATE INDEX idx_order_purchase_details_tenant ON X.order_purchase_details USING btree (tenant_id) |  |
| 索引 | 使い捨てだけ | idx_order_purchase_details_tenant_supplier |  | CREATE INDEX idx_order_purchase_details_tenant_supplier ON X.order_purchase_details USING btree (tenant_id, supplier_name) |  |
| 索引 | 使い捨てだけ | idx_order_shipping_details_carrier |  | CREATE INDEX idx_order_shipping_details_carrier ON X.order_shipping_details USING btree (carrier) |  |
| 索引 | 使い捨てだけ | idx_order_shipping_details_order |  | CREATE INDEX idx_order_shipping_details_order ON X.order_shipping_details USING btree (order_id) |  |
| 索引 | 使い捨てだけ | idx_order_shipping_details_tenant |  | CREATE INDEX idx_order_shipping_details_tenant ON X.order_shipping_details USING btree (tenant_id) |  |
| 索引 | 使い捨てだけ | idx_order_shipping_details_tracking |  | CREATE INDEX idx_order_shipping_details_tracking ON X.order_shipping_details USING btree (tracking_number) |  |
| 索引 | 使い捨てだけ | idx_outbound_drafts_tenant_lead |  | CREATE INDEX idx_outbound_drafts_tenant_lead ON X.outbound_translation_drafts USING btree (tenant_id, lead_id) |  |
| 索引 | 使い捨てだけ | idx_outbound_drafts_unconfirmed |  | CREATE INDEX idx_outbound_drafts_unconfirmed ON X.outbound_translation_drafts USING btree (tenant_id, confirmed_at) WHERE (confirmed_at IS NULL) |  |
| 索引 | 使い捨てだけ | idx_paypal_disputes_invoice |  | CREATE INDEX idx_paypal_disputes_invoice ON X.paypal_disputes USING btree (invoice_id) |  |
| 索引 | 使い捨てだけ | idx_poi_order_item_id |  | CREATE INDEX idx_poi_order_item_id ON X.purchase_order_items USING btree (order_item_id) |  |
| 索引 | 使い捨てだけ | idx_shifts_date |  | CREATE INDEX idx_shifts_date ON X.shifts USING btree (shift_date) |  |
| 索引 | 使い捨てだけ | idx_shifts_user |  | CREATE INDEX idx_shifts_user ON X.shifts USING btree (user_id) |  |
| 索引 | 使い捨てだけ | idx_staff_phone |  | CREATE INDEX idx_staff_phone ON X.staff USING btree (phone) WHERE (phone IS NOT NULL) |  |
| 索引 | 使い捨てだけ | idx_staff_reports_type |  | CREATE INDEX idx_staff_reports_type ON X.staff_reports USING btree (report_type) |  |
| 索引 | 使い捨てだけ | idx_staff_reports_user |  | CREATE INDEX idx_staff_reports_user ON X.staff_reports USING btree (user_id) |  |
| 索引 | 使い捨てだけ | idx_tenant_calibrations_latest |  | CREATE INDEX idx_tenant_calibrations_latest ON X.tenant_calibrations USING btree (tenant_id, calibrated_at DESC) |  |
| 索引 | 使い捨てだけ | idx_tenant_commission_settings_tenant |  | CREATE INDEX idx_tenant_commission_settings_tenant ON X.tenant_commission_settings USING btree (tenant_id) |  |
| 索引 | 使い捨てだけ | lead_attachments_pkey |  | CREATE UNIQUE INDEX lead_attachments_pkey ON X.lead_attachments USING btree (id) |  |
| 索引 | 使い捨てだけ | message_labels_pkey |  | CREATE UNIQUE INDEX message_labels_pkey ON X.message_labels USING btree (id) |  |
| 索引 | 使い捨てだけ | message_translations_pkey |  | CREATE UNIQUE INDEX message_translations_pkey ON X.message_translations USING btree (id) |  |
| 索引 | 使い捨てだけ | meta_message_reactions_pkey |  | CREATE UNIQUE INDEX meta_message_reactions_pkey ON X.meta_message_reactions USING btree (id) |  |
| 索引 | 使い捨てだけ | notification_channels_pkey |  | CREATE UNIQUE INDEX notification_channels_pkey ON X.notification_channels USING btree (id) |  |
| 索引 | 使い捨てだけ | notification_logs_pkey |  | CREATE UNIQUE INDEX notification_logs_pkey ON X.notification_logs USING btree (id) |  |
| 索引 | 使い捨てだけ | order_commissions_order_id_role_key |  | CREATE UNIQUE INDEX order_commissions_order_id_role_key ON X.order_commissions USING btree (order_id, role) |  |
| 索引 | 使い捨てだけ | order_commissions_pkey |  | CREATE UNIQUE INDEX order_commissions_pkey ON X.order_commissions USING btree (id) |  |
| 索引 | 使い捨てだけ | order_financials_order_id_key |  | CREATE UNIQUE INDEX order_financials_order_id_key ON X.order_financials USING btree (order_id) |  |
| 索引 | 使い捨てだけ | order_financials_pkey |  | CREATE UNIQUE INDEX order_financials_pkey ON X.order_financials USING btree (id) |  |
| 索引 | 使い捨てだけ | order_purchase_details_order_id_key |  | CREATE UNIQUE INDEX order_purchase_details_order_id_key ON X.order_purchase_details USING btree (order_id) |  |
| 索引 | 使い捨てだけ | order_purchase_details_pkey |  | CREATE UNIQUE INDEX order_purchase_details_pkey ON X.order_purchase_details USING btree (id) |  |
| 索引 | 使い捨てだけ | order_shipping_details_order_id_key |  | CREATE UNIQUE INDEX order_shipping_details_order_id_key ON X.order_shipping_details USING btree (order_id) |  |
| 索引 | 使い捨てだけ | order_shipping_details_pkey |  | CREATE UNIQUE INDEX order_shipping_details_pkey ON X.order_shipping_details USING btree (id) |  |
| 索引 | 使い捨てだけ | outbound_translation_drafts_pkey |  | CREATE UNIQUE INDEX outbound_translation_drafts_pkey ON X.outbound_translation_drafts USING btree (id) |  |
| 索引 | 使い捨てだけ | paypal_disputes_dispute_id_key |  | CREATE UNIQUE INDEX paypal_disputes_dispute_id_key ON X.paypal_disputes USING btree (dispute_id) |  |
| 索引 | 使い捨てだけ | paypal_disputes_pkey |  | CREATE UNIQUE INDEX paypal_disputes_pkey ON X.paypal_disputes USING btree (id) |  |
| 索引 | 使い捨てだけ | shifts_pkey |  | CREATE UNIQUE INDEX shifts_pkey ON X.shifts USING btree (id) |  |
| 索引 | 使い捨てだけ | shifts_tenant_id_user_id_shift_date_key |  | CREATE UNIQUE INDEX shifts_tenant_id_user_id_shift_date_key ON X.shifts USING btree (tenant_id, user_id, shift_date) |  |
| 索引 | 使い捨てだけ | staff_reports_pkey |  | CREATE UNIQUE INDEX staff_reports_pkey ON X.staff_reports USING btree (id) |  |
| 索引 | 使い捨てだけ | tenant_calibrations_pkey |  | CREATE UNIQUE INDEX tenant_calibrations_pkey ON X.tenant_calibrations USING btree (id) |  |
| 索引 | 使い捨てだけ | tenant_commission_settings_pkey |  | CREATE UNIQUE INDEX tenant_commission_settings_pkey ON X.tenant_commission_settings USING btree (id) |  |
| 索引 | 使い捨てだけ | tenant_commission_settings_tenant_id_key |  | CREATE UNIQUE INDEX tenant_commission_settings_tenant_id_key ON X.tenant_commission_settings USING btree (tenant_id) |  |
| 索引 | 使い捨てだけ | uq_calendar_events_google_event_id |  | CREATE UNIQUE INDEX uq_calendar_events_google_event_id ON X.calendar_events USING btree (google_event_id) WHERE (google_event_id IS NOT NULL) |  |
| 索引 | 使い捨てだけ | uq_customer_scores_lead_id |  | CREATE UNIQUE INDEX uq_customer_scores_lead_id ON X.customer_scores USING btree (lead_id) |  |
| 索引 | 使い捨てだけ | uq_discord_channel_webhooks_channel |  | CREATE UNIQUE INDEX uq_discord_channel_webhooks_channel ON X.discord_channel_webhooks USING btree (channel_id) |  |
| 索引 | 使い捨てだけ | uq_message_translations |  | CREATE UNIQUE INDEX uq_message_translations ON X.message_translations USING btree (message_id, target_language) |  |
| 索引 | 使い捨てだけ | uq_notification_channels_blueprint_key |  | CREATE UNIQUE INDEX uq_notification_channels_blueprint_key ON X.notification_channels USING btree (blueprint_key) WHERE (blueprint_key IS NOT NULL) |  |
| 索引 | 使い捨てだけ | uq_order_financials_tenant_order |  | CREATE UNIQUE INDEX uq_order_financials_tenant_order ON X.order_financials USING btree (tenant_id, order_id) |  |
| 索引 | 使い捨てだけ | uq_order_purchase_details_tenant_order |  | CREATE UNIQUE INDEX uq_order_purchase_details_tenant_order ON X.order_purchase_details USING btree (tenant_id, order_id) |  |
| 索引 | 使い捨てだけ | uq_order_shipping_details_tenant_order |  | CREATE UNIQUE INDEX uq_order_shipping_details_tenant_order ON X.order_shipping_details USING btree (tenant_id, order_id) |  |
| 索引 | 使い捨てだけ | uq_reaction_per_user_emoji |  | CREATE UNIQUE INDEX uq_reaction_per_user_emoji ON X.meta_message_reactions USING btree (meta_message_id, emoji_name, emoji_id, reactor_discord_user_id) |  |
| 制約 | 使い捨てだけ | archives_pkey (表 archives) |  | archives_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | fk_bots_owner_staff_id_user (表 bots) |  | fk_bots_owner_staff_id_user\|f\|FOREIGN KEY (owner_staff_id) REFERENCES users(id) |  |
| 制約 | 使い捨てだけ | calendar_events_calendar_type_check (表 calendar_events) |  | calendar_events_calendar_type_check\|c\|CHECK (((calendar_type)::text = ANY ((ARRAY['shared'::character varying, 'personal'::character varying])::text[]))) |  |
| 制約 | 使い捨てだけ | calendar_events_cancelled_exception_check (表 calendar_events) |  | calendar_events_cancelled_exception_check\|c\|CHECK (((NOT is_cancelled) OR (recurring_event_id IS NOT NULL))) |  |
| 制約 | 使い捨てだけ | calendar_events_created_by_user_id_fkey (表 calendar_events) |  | calendar_events_created_by_user_id_fkey\|f\|FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL |  |
| 制約 | 使い捨てだけ | calendar_events_exception_pair_check (表 calendar_events) |  | calendar_events_exception_pair_check\|c\|CHECK (((recurring_event_id IS NULL) = (original_start_datetime IS NULL))) |  |
| 制約 | 使い捨てだけ | calendar_events_pkey (表 calendar_events) |  | calendar_events_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | calendar_events_recurrence_role_check (表 calendar_events) |  | calendar_events_recurrence_role_check\|c\|CHECK ((NOT ((recurrence_rule IS NOT NULL) AND (recurring_event_id IS NOT NULL)))) |  |
| 制約 | 使い捨てだけ | calendar_events_recurrence_rule_format_check (表 calendar_events) |  | calendar_events_recurrence_rule_format_check\|c\|CHECK ((recurrence_rule ~ '^FREQ=(DAILY\|WEEKLY\|MONTHLY\|YEARLY)(;[A-Z]+=[A-Z0-9,+-]+)*$'::text)) |  |
| 制約 | 使い捨てだけ | calendar_events_recurring_event_id_fkey (表 calendar_events) |  | calendar_events_recurring_event_id_fkey\|f\|FOREIGN KEY (recurring_event_id) REFERENCES X.calendar_events(id) ON DELETE CASCADE |  |
| 制約 | 使い捨てだけ | calendar_events_source_check (表 calendar_events) |  | calendar_events_source_check\|c\|CHECK (((source)::text = ANY ((ARRAY['app'::character varying, 'google'::character varying])::text[]))) |  |
| 制約 | 使い捨てだけ | calendar_events_sync_status_check (表 calendar_events) |  | calendar_events_sync_status_check\|c\|CHECK (((sync_status)::text = ANY ((ARRAY['synced'::character varying, 'pending'::character varying, 'failed'::character varying])::text[]))) |  |
| 制約 | 使い捨てだけ | calendar_events_user_id_fkey (表 calendar_events) |  | calendar_events_user_id_fkey\|f\|FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL |  |
| 制約 | 使い捨てだけ | conversation_logs_direction_check (表 conversation_logs) |  | conversation_logs_direction_check\|c\|CHECK (((direction)::text = ANY ((ARRAY['inbound'::character varying, 'outbound'::character varying])::text[]))) |  |
| 制約 | 使い捨てだけ | conversation_logs_external_message_id_key (表 conversation_logs) |  | conversation_logs_external_message_id_key\|u\|UNIQUE (external_message_id) |  |
| 制約 | 使い捨てだけ | conversation_logs_pkey (表 conversation_logs) |  | conversation_logs_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | fk_conversation_logs_lead (表 conversation_logs) |  | fk_conversation_logs_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) ON UPDATE RESTRICT ON DELETE RESTRICT |  |
| 制約 | 使い捨てだけ | customer_scores_confidence_check (表 customer_scores) |  | customer_scores_confidence_check\|c\|CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))) |  |
| 制約 | 使い捨てだけ | customer_scores_override_score_check (表 customer_scores) |  | customer_scores_override_score_check\|c\|CHECK (((override_score IS NULL) OR ((override_score >= (0)::numeric) AND (override_score <= (1)::numeric)))) |  |
| 制約 | 使い捨てだけ | customer_scores_pkey (表 customer_scores) |  | customer_scores_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | customer_scores_score_check (表 customer_scores) |  | customer_scores_score_check\|c\|CHECK (((score >= (0)::numeric) AND (score <= (1)::numeric))) |  |
| 制約 | 使い捨てだけ | customer_scores_tier_check (表 customer_scores) |  | customer_scores_tier_check\|c\|CHECK (((tier)::text = ANY ((ARRAY['要観察'::character varying, '有望'::character varying, '最有望'::character varying])::text[]))) |  |
| 制約 | 使い捨てだけ | fk_deal_close_reasons_lead (表 deal_close_reasons) |  | fk_deal_close_reasons_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  |
| 制約 | 使い捨てだけ | discord_channel_webhooks_pkey (表 discord_channel_webhooks) |  | discord_channel_webhooks_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | uq_discord_channel_webhooks_channel (表 discord_channel_webhooks) |  | uq_discord_channel_webhooks_channel\|u\|UNIQUE (channel_id) |  |
| 制約 | 使い捨てだけ | erp_sync_logs_pkey (表 erp_sync_logs) |  | erp_sync_logs_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 中身が違う | goals_kpi_type_check (表 goals) | goals_kpi_type_check\|c\|CHECK (((kpi_type)::text = ANY ((ARRAY['revenue'::character varying, 'deal_count'::character varying, 'close_rate'::character varying, 'lead_count'::character varying, 'conversion_rate'::character varying])::text[]))) | goals_kpi_type_check\|c\|CHECK (((kpi_type)::text = ANY ((ARRAY['revenue'::character varying, 'deal_count'::character varying, 'close_rate'::character varying, 'lead_count'::character varying, 'conversion_rate'::character varying, 'won_count'::character varying, 'gross_profit'::character varying])::text[]))) |  |
| 制約 | 本番だけ | invoice_items_product_id_fkey (表 invoice_items) | invoice_items_product_id_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) |  |  |
| 制約 | 使い捨てだけ | invoice_items_product_id_public_fkey (表 invoice_items) |  | invoice_items_product_id_public_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT |  |
| 制約 | 使い捨てだけ | lead_attachments_lead_id_fkey (表 lead_attachments) |  | lead_attachments_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) ON DELETE CASCADE |  |
| 制約 | 使い捨てだけ | lead_attachments_pkey (表 lead_attachments) |  | lead_attachments_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | message_labels_confidence_check (表 message_labels) |  | message_labels_confidence_check\|c\|CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))) |  |
| 制約 | 使い捨てだけ | message_labels_direction_check (表 message_labels) |  | message_labels_direction_check\|c\|CHECK (((direction)::text = ANY ((ARRAY['inbound'::character varying, 'outbound'::character varying])::text[]))) |  |
| 制約 | 使い捨てだけ | message_labels_label_check (表 message_labels) |  | message_labels_label_check\|c\|CHECK (((label)::text = ANY ((ARRAY['price_focus'::character varying, 'substance_talk'::character varying, 'self_disclosure'::character varying, 'early_purchase_signal'::character varying, 'other'::character varying])::text[]))) |  |
| 制約 | 使い捨てだけ | message_labels_pkey (表 message_labels) |  | message_labels_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | message_labels_source_check (表 message_labels) |  | message_labels_source_check\|c\|CHECK (((source)::text = ANY ((ARRAY['rule'::character varying, 'llm'::character varying, 'human'::character varying])::text[]))) |  |
| 制約 | 使い捨てだけ | message_translations_pkey (表 message_translations) |  | message_translations_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | uq_message_translations (表 message_translations) |  | uq_message_translations\|u\|UNIQUE (message_id, target_language) |  |
| 制約 | 使い捨てだけ | meta_message_reactions_meta_message_id_fkey (表 meta_message_reactions) |  | meta_message_reactions_meta_message_id_fkey\|f\|FOREIGN KEY (meta_message_id) REFERENCES X.meta_messages(id) ON DELETE CASCADE |  |
| 制約 | 使い捨てだけ | meta_message_reactions_pkey (表 meta_message_reactions) |  | meta_message_reactions_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | uq_reaction_per_user_emoji (表 meta_message_reactions) |  | uq_reaction_per_user_emoji\|u\|UNIQUE (meta_message_id, emoji_name, emoji_id, reactor_discord_user_id) |  |
| 制約 | 使い捨てだけ | fk_meta_messages_seen_by_staff_id_user (表 meta_messages) |  | fk_meta_messages_seen_by_staff_id_user\|f\|FOREIGN KEY (seen_by_staff_id) REFERENCES users(id) ON DELETE SET NULL |  |
| 制約 | 使い捨てだけ | fk_meta_messages_sent_by_staff_id_user (表 meta_messages) |  | fk_meta_messages_sent_by_staff_id_user\|f\|FOREIGN KEY (sent_by_staff_id) REFERENCES users(id) ON DELETE SET NULL |  |
| 制約 | 使い捨てだけ | notification_channels_pkey (表 notification_channels) |  | notification_channels_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | notification_logs_channel_id_fkey (表 notification_logs) |  | notification_logs_channel_id_fkey\|f\|FOREIGN KEY (channel_id) REFERENCES X.notification_channels(id) |  |
| 制約 | 使い捨てだけ | notification_logs_pkey (表 notification_logs) |  | notification_logs_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | fk_order_commissions_staff_id_user (表 order_commissions) |  | fk_order_commissions_staff_id_user\|f\|FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE SET NULL |  |
| 制約 | 使い捨てだけ | order_commissions_order_id_fkey (表 order_commissions) |  | order_commissions_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE |  |
| 制約 | 使い捨てだけ | order_commissions_order_id_role_key (表 order_commissions) |  | order_commissions_order_id_role_key\|u\|UNIQUE (order_id, role) |  |
| 制約 | 使い捨てだけ | order_commissions_pkey (表 order_commissions) |  | order_commissions_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | order_commissions_role_check (表 order_commissions) |  | order_commissions_role_check\|c\|CHECK ((role = ANY (ARRAY['sales'::text, 'order'::text, 'ship'::text, 'purchase'::text, 'trouble'::text]))) |  |
| 制約 | 使い捨てだけ | order_financials_order_id_fkey (表 order_financials) |  | order_financials_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE |  |
| 制約 | 使い捨てだけ | order_financials_order_id_key (表 order_financials) |  | order_financials_order_id_key\|u\|UNIQUE (order_id) |  |
| 制約 | 使い捨てだけ | order_financials_pkey (表 order_financials) |  | order_financials_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | order_purchase_details_order_id_fkey (表 order_purchase_details) |  | order_purchase_details_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE |  |
| 制約 | 使い捨てだけ | order_purchase_details_order_id_key (表 order_purchase_details) |  | order_purchase_details_order_id_key\|u\|UNIQUE (order_id) |  |
| 制約 | 使い捨てだけ | order_purchase_details_pkey (表 order_purchase_details) |  | order_purchase_details_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | order_purchase_details_purchase_status_check (表 order_purchase_details) |  | order_purchase_details_purchase_status_check\|c\|CHECK ((purchase_status = ANY (ARRAY[''::text, 'confirmed'::text]))) |  |
| 制約 | 使い捨てだけ | order_shipping_details_address_type_check (表 order_shipping_details) |  | order_shipping_details_address_type_check\|c\|CHECK (((address_type IS NULL) OR ((address_type)::text = ANY ((ARRAY['RESIDENTIAL'::character varying, 'BUSINESS'::character varying])::text[])))) |  |
| 制約 | 使い捨てだけ | order_shipping_details_carrier_check (表 order_shipping_details) |  | order_shipping_details_carrier_check\|c\|CHECK (((carrier IS NULL) OR ((carrier)::text = ANY ((ARRAY['elogi'::character varying, 'fedex'::character varying, 'dhl'::character varying, 'yamato'::character varying, 'other'::character varying])::text[])))) |  |
| 制約 | 使い捨てだけ | order_shipping_details_order_id_fkey (表 order_shipping_details) |  | order_shipping_details_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE |  |
| 制約 | 使い捨てだけ | order_shipping_details_order_id_key (表 order_shipping_details) |  | order_shipping_details_order_id_key\|u\|UNIQUE (order_id) |  |
| 制約 | 使い捨てだけ | order_shipping_details_pkey (表 order_shipping_details) |  | order_shipping_details_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | outbound_translation_drafts_pkey (表 outbound_translation_drafts) |  | outbound_translation_drafts_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | paypal_disputes_dispute_id_key (表 paypal_disputes) |  | paypal_disputes_dispute_id_key\|u\|UNIQUE (dispute_id) |  |
| 制約 | 使い捨てだけ | paypal_disputes_invoice_id_fkey (表 paypal_disputes) |  | paypal_disputes_invoice_id_fkey\|f\|FOREIGN KEY (invoice_id) REFERENCES X.invoices(id) ON DELETE SET NULL |  |
| 制約 | 使い捨てだけ | paypal_disputes_pkey (表 paypal_disputes) |  | paypal_disputes_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 中身が違う | fk_products_supplier_default (表 products) | fk_products_supplier_default\|f\|FOREIGN KEY (supplier_default_id) REFERENCES X.suppliers(id) | fk_products_supplier_default\|f\|FOREIGN KEY (supplier_default_id) REFERENCES suppliers(id) |  |
| 制約 | 使い捨てだけ | fk_poi_order_item (表 purchase_order_items) |  | fk_poi_order_item\|f\|FOREIGN KEY (order_item_id) REFERENCES X.order_items(id) |  |
| 制約 | 本番だけ | purchase_order_items_product_id_fkey (表 purchase_order_items) | purchase_order_items_product_id_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) |  |  |
| 制約 | 使い捨てだけ | purchase_order_items_product_id_public_fkey (表 purchase_order_items) |  | purchase_order_items_product_id_public_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT |  |
| 制約 | 中身が違う | purchase_orders_supplier_id_fkey (表 purchase_orders) | purchase_orders_supplier_id_fkey\|f\|FOREIGN KEY (supplier_id) REFERENCES X.suppliers(id) | purchase_orders_supplier_id_fkey\|f\|FOREIGN KEY (supplier_id) REFERENCES suppliers(id) |  |
| 制約 | 本番だけ | quote_items_product_id_fkey (表 quote_items) | quote_items_product_id_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) |  |  |
| 制約 | 使い捨てだけ | quote_items_product_id_public_fkey (表 quote_items) |  | quote_items_product_id_public_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT |  |
| 制約 | 使い捨てだけ | fk_quotes_lead (表 quotes) |  | fk_quotes_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  |
| 制約 | 使い捨てだけ | shifts_pkey (表 shifts) |  | shifts_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | shifts_tenant_id_user_id_shift_date_key (表 shifts) |  | shifts_tenant_id_user_id_shift_date_key\|u\|UNIQUE (tenant_id, user_id, shift_date) |  |
| 制約 | 使い捨てだけ | staff_reports_pkey (表 staff_reports) |  | staff_reports_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | tenant_calibrations_pkey (表 tenant_calibrations) |  | tenant_calibrations_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | tenant_commission_settings_pkey (表 tenant_commission_settings) |  | tenant_commission_settings_pkey\|p\|PRIMARY KEY (id) |  |
| 制約 | 使い捨てだけ | tenant_commission_settings_tenant_id_key (表 tenant_commission_settings) |  | tenant_commission_settings_tenant_id_key\|u\|UNIQUE (tenant_id) |  |
| 制約 | 使い捨てだけ | fk_tenant_meta_config_connected_by_staff_id_user (表 tenant_meta_config) |  | fk_tenant_meta_config_connected_by_staff_id_user\|f\|FOREIGN KEY (connected_by_staff_id) REFERENCES users(id) ON DELETE SET NULL |  |
| トリガ | 使い捨てだけ | trg_calendar_events_updated_at (表 calendar_events) |  | CREATE TRIGGER trg_calendar_events_updated_at BEFORE UPDATE ON X.calendar_events FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_calendar_events() |  |
| トリガ | 使い捨てだけ | trigger_set_updated_at_goals (表 goals) |  | CREATE TRIGGER trigger_set_updated_at_goals BEFORE UPDATE ON X.goals FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_goals() |  |
| トリガ | 使い捨てだけ | trg_la_updated_at (表 lead_attachments) |  | CREATE TRIGGER trg_la_updated_at BEFORE UPDATE ON X.lead_attachments FOR EACH ROW EXECUTE FUNCTION X.trg_set_updated_at() |  |
| トリガ | 使い捨てだけ | trigger_set_updated_at_lead_playbook (表 lead_playbook) |  | CREATE TRIGGER trigger_set_updated_at_lead_playbook BEFORE UPDATE ON X.lead_playbook FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_lead_playbook() |  |
| トリガ | 使い捨てだけ | trigger_set_updated_at_order_commissions (表 order_commissions) |  | CREATE TRIGGER trigger_set_updated_at_order_commissions BEFORE UPDATE ON X.order_commissions FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_commissions() |  |
| トリガ | 使い捨てだけ | trigger_set_updated_at_order_financials (表 order_financials) |  | CREATE TRIGGER trigger_set_updated_at_order_financials BEFORE UPDATE ON X.order_financials FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_financials() |  |
| トリガ | 使い捨てだけ | trigger_set_updated_at_order_purchase_details (表 order_purchase_details) |  | CREATE TRIGGER trigger_set_updated_at_order_purchase_details BEFORE UPDATE ON X.order_purchase_details FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_purchase_details() |  |
| トリガ | 使い捨てだけ | trigger_set_updated_at_order_shipping_details (表 order_shipping_details) |  | CREATE TRIGGER trigger_set_updated_at_order_shipping_details BEFORE UPDATE ON X.order_shipping_details FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_shipping_details() |  |
| トリガ | 使い捨てだけ | trigger_set_updated_at_tenant_commission_settings (表 tenant_commission_settings) |  | CREATE TRIGGER trigger_set_updated_at_tenant_commission_settings BEFORE UPDATE ON X.tenant_commission_settings FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_tenant_commission_settings() |  |
| トリガ | 使い捨てだけ | trigger_set_updated_at_tenant_meta_config (表 tenant_meta_config) |  | CREATE TRIGGER trigger_set_updated_at_tenant_meta_config BEFORE UPDATE ON X.tenant_meta_config FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_tenant_meta_config() |  |
| トリガ | 使い捨てだけ | trigger_set_updated_at_tenant_profile (表 tenant_profile) |  | CREATE TRIGGER trigger_set_updated_at_tenant_profile BEFORE UPDATE ON X.tenant_profile FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_tenant_profile() |  |
| 方針 | 使い捨てだけ | archives.tenant_isolation_archives |  | tenant_isolation_archives\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | conversation_logs.conversation_logs_tenant_isolation |  | conversation_logs_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | customer_scores.customer_scores_tenant_isolation |  | customer_scores_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | discord_channel_webhooks.tenant_isolation_discord_channel_webhooks |  | tenant_isolation_discord_channel_webhooks\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | erp_sync_logs.tenant_isolation_erp_sync_logs |  | tenant_isolation_erp_sync_logs\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | lead_attachments.tenant_isolation_lead_attachments |  | tenant_isolation_lead_attachments\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.leads l\n  WHERE ((l.id = lead_attachments.lead_id) AND (l.tenant_id = current_tenant_id()))))\| |  |
| 方針 | 使い捨てだけ | message_labels.message_labels_tenant_isolation |  | message_labels_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | message_translations.message_translations_tenant_isolation |  | message_translations_tenant_isolation\|*\|true\|public\|(tenant_id = (NULLIF(current_setting('app.tenant_id'::text, true), ''::text))::integer)\| |  |
| 方針 | 使い捨てだけ | meta_message_reactions.tenant_isolation_meta_message_reactions |  | tenant_isolation_meta_message_reactions\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | notification_channels.tenant_isolation_notification_channels |  | tenant_isolation_notification_channels\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | notification_logs.tenant_isolation_notification_logs |  | tenant_isolation_notification_logs\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | order_commissions.tenant_isolation_order_commissions |  | tenant_isolation_order_commissions\|*\|true\|public\|(tenant_id = current_tenant_id())\| |  |
| 方針 | 使い捨てだけ | order_financials.tenant_isolation_order_financials |  | tenant_isolation_order_financials\|*\|true\|public\|(tenant_id = current_tenant_id())\| |  |
| 方針 | 使い捨てだけ | order_purchase_details.tenant_isolation_order_purchase_details |  | tenant_isolation_order_purchase_details\|*\|true\|public\|(tenant_id = current_tenant_id())\| |  |
| 方針 | 使い捨てだけ | order_shipping_details.tenant_isolation_order_shipping_details |  | tenant_isolation_order_shipping_details\|*\|true\|public\|(tenant_id = current_tenant_id())\| |  |
| 方針 | 使い捨てだけ | shifts.tenant_isolation_shifts |  | tenant_isolation_shifts\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | staff_reports.tenant_isolation_staff_reports |  | tenant_isolation_staff_reports\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | tenant_calibrations.tenant_calibrations_tenant_isolation |  | tenant_calibrations_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |
| 方針 | 使い捨てだけ | tenant_commission_settings.tenant_isolation_tenant_commission_settings |  | tenant_isolation_tenant_commission_settings\|*\|true\|public\|(tenant_id = current_tenant_id())\| |  |
| 表の印 | 使い捨てだけ | archives |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | audit_logs | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | calendar_events |  | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | channel_masters | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | close_reasons | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | companies | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | company_addresses | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | company_discord | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | company_sales_channels | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | contact_contact_channels | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | contact_discord | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | contact_emails | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | contacts | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | conversation_logs |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | customer_scores |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | deal_close_reasons | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | discord_channel_webhooks |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} |  |
| 表の印 | 中身が違う | discord_retired_members | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | discord_retired_roles | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | erp_sync_logs |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | goals | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | invoice_items | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | invoices | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | lead_attachments |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | lead_channels | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | lead_playbook | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | lead_sales_form_selections | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | leads | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | message_labels |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | message_translations |  | True\|True\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | meta_message_reactions |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | meta_messages | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | notice_fallback_recipients | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | notification_channels |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | notification_logs |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | order_commissions |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | order_financials |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | order_items | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | order_purchase_details |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | order_shipping_details |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | orders | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | outbound_translation_drafts |  | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | own_inventory | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | paypal_disputes |  | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | products | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | purchase_order_items | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | purchase_orders | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | quote_items | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | quotes | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | role_permissions | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | roles | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | shifts |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | shipping_rates | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | shipping_zones | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | staff_emails | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | staff_reports |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | staff_ui_preferences | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | suppliers | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | team_members | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | teams | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | tenant_calibrations |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 使い捨てだけ | tenant_commission_settings |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | tenant_duty_rule_components | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | tenant_duty_rules | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | tenant_profile | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | tenant_sales_form_options | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | user_notices | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 表の印 | 中身が違う | user_roles | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |
| 連番 | 使い捨てだけ | archives_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | calendar_events_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | conversation_logs_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | customer_scores_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | discord_channel_webhooks_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | erp_sync_logs_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | lead_attachments_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | message_labels_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | message_translations_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | meta_message_reactions_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | notification_channels_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | notification_logs_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | order_commissions_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | order_financials_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | order_purchase_details_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | order_shipping_details_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | outbound_translation_drafts_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | paypal_disputes_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | shifts_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | staff_reports_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | tenant_calibrations_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 連番 | 使い捨てだけ | tenant_commission_settings_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |
| 関数 | 使い捨てだけ | set_updated_at_calendar_events() |  | 211737f15aee82dd881c47f7bcaae23e\|False |  |
| 関数 | 使い捨てだけ | set_updated_at_goals() |  | a49b07e555fbd6ad335a99b945ba0ee1\|False |  |
| 関数 | 使い捨てだけ | set_updated_at_lead_playbook() |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  |
| 関数 | 使い捨てだけ | set_updated_at_order_commissions() |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  |
| 関数 | 使い捨てだけ | set_updated_at_order_financials() |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  |
| 関数 | 使い捨てだけ | set_updated_at_order_purchase_details() |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  |
| 関数 | 使い捨てだけ | set_updated_at_order_shipping_details() |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  |
| 関数 | 使い捨てだけ | set_updated_at_tenant_commission_settings() |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  |
| 関数 | 使い捨てだけ | set_updated_at_tenant_meta_config() |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  |
| 関数 | 使い捨てだけ | set_updated_at_tenant_profile() |  | a49b07e555fbd6ad335a99b945ba0ee1\|False |  |
| 関数 | 中身が違う | trg_set_updated_at() | 06bcf30ac3d0a7f279a54cbf228a7bec\|False | a49b07e555fbd6ad335a99b945ba0ee1\|False |  |
| ビュー | 使い捨てだけ | v_company_stats |  | c5e051967e16a5b43635dd3285f34a93\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} |  |

## 種類ごとの件数

| 種類 | 本番の数 | 使い捨ての数 | 本番だけ | 使い捨てだけ | 中身が違う |
|---|---|---|---|---|---|
| 列 | 641 | 973 | 1 | 333 | 5 |
| 索引 | 140 | 235 | 0 | 95 | 0 |
| 制約 | 181 | 254 | 3 | 76 | 3 |
| トリガ | 18 | 29 | 0 | 11 | 0 |
| 方針 | 42 | 61 | 0 | 19 | 0 |
| 表の印 | 53 | 75 | 0 | 22 | 46 |
| 連番 | 44 | 66 | 0 | 22 | 0 |
| 関数 | 5 | 15 | 0 | 10 | 1 |
| ビュー | 1 | 2 | 0 | 1 | 0 |
| 合計 | 1125 | 1710 | 4 | 589 | 55 |


# 印付きの全件の表と印ごとの件数

## 印付きの全件の表（793件）

| 種類 | 名前 | 本番の中身 | ひな形の直後の中身 | 全件の後の中身 | 印 |
|---|---|---|---|---|---|
| 列 | archives.archived_at | archived_at\|timestamp with time zone\|false\|now() |  | archived_at\|timestamp with time zone\|false\|now() | 印1:全件の後に有る |
| 列 | archives.archived_by | archived_by\|integer\|false\| |  | archived_by\|integer\|false\| | 印1:全件の後に有る |
| 列 | archives.archived_data | archived_data\|jsonb\|true\| |  | archived_data\|jsonb\|true\| | 印1:全件の後に有る |
| 列 | archives.id | id\|integer\|true\|nextval('X.archives_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.archives_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | archives.restored_at | restored_at\|timestamp with time zone\|false\| |  | restored_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | archives.restored_by | restored_by\|integer\|false\| |  | restored_by\|integer\|false\| | 印1:全件の後に有る |
| 列 | archives.source_id | source_id\|integer\|true\| |  | source_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | archives.source_table | source_table\|character varying(100)\|true\| |  | source_table\|character varying(100)\|true\| | 印1:全件の後に有る |
| 列 | archives.tenant_id | tenant_id\|integer\|true\|3 |  | tenant_id\|integer\|true\|3 | 印1:全件の後に有る |
| 列 | badge_definitions.created_at | created_at\|timestamp with time zone\|false\|now() |  |  | 印1:全件の後も無い |
| 列 | badge_definitions.criteria | criteria\|character varying(500)\|false\| |  |  | 印1:全件の後も無い |
| 列 | badge_definitions.description | description\|character varying(500)\|false\| |  |  | 印1:全件の後も無い |
| 列 | badge_definitions.icon | icon\|character varying(10)\|false\| |  |  | 印1:全件の後も無い |
| 列 | badge_definitions.id | id\|integer\|true\|nextval('X.badge_definitions_id_seq'::regclass) |  |  | 印1:全件の後も無い |
| 列 | badge_definitions.is_active | is_active\|boolean\|false\|true |  |  | 印1:全件の後も無い |
| 列 | badge_definitions.name | name\|character varying(100)\|true\| |  |  | 印1:全件の後も無い |
| 列 | badge_definitions.points | points\|integer\|false\|0 |  |  | 印1:全件の後も無い |
| 列 | badge_definitions.tenant_id | tenant_id\|integer\|true\|3 |  |  | 印1:全件の後も無い |
| 列 | buddy_feedbacks.context | context\|text\|false\| |  |  | 印1:全件の後も無い |
| 列 | buddy_feedbacks.created_at | created_at\|timestamp with time zone\|false\|now() |  |  | 印1:全件の後も無い |
| 列 | buddy_feedbacks.created_by | created_by\|integer\|true\| |  |  | 印1:全件の後も無い |
| 列 | buddy_feedbacks.feedback_type | feedback_type\|character varying(10)\|true\| |  |  | 印1:全件の後も無い |
| 列 | buddy_feedbacks.id | id\|integer\|true\|nextval('X.buddy_feedbacks_id_seq'::regclass) |  |  | 印1:全件の後も無い |
| 列 | buddy_feedbacks.pair_id | pair_id\|integer\|true\| |  |  | 印1:全件の後も無い |
| 列 | buddy_feedbacks.reason | reason\|text\|false\| |  |  | 印1:全件の後も無い |
| 列 | buddy_feedbacks.tenant_id | tenant_id\|integer\|true\|3 |  |  | 印1:全件の後も無い |
| 列 | buddy_pairs.coach_user_id | coach_user_id\|integer\|true\| |  |  | 印1:全件の後も無い |
| 列 | buddy_pairs.ended_at | ended_at\|timestamp with time zone\|false\| |  |  | 印1:全件の後も無い |
| 列 | buddy_pairs.id | id\|integer\|true\|nextval('X.buddy_pairs_id_seq'::regclass) |  |  | 印1:全件の後も無い |
| 列 | buddy_pairs.is_active | is_active\|boolean\|false\|true |  |  | 印1:全件の後も無い |
| 列 | buddy_pairs.mentee_user_id | mentee_user_id\|integer\|true\| |  |  | 印1:全件の後も無い |
| 列 | buddy_pairs.notes | notes\|text\|false\| |  |  | 印1:全件の後も無い |
| 列 | buddy_pairs.started_at | started_at\|timestamp with time zone\|false\|now() |  |  | 印1:全件の後も無い |
| 列 | buddy_pairs.tenant_id | tenant_id\|integer\|true\|3 |  |  | 印1:全件の後も無い |
| 列 | calendar_events.calendar_type | calendar_type\|character varying(10)\|true\|'shared'::character varying |  | calendar_type\|character varying(10)\|true\|'shared'::character varying | 印1:全件の後に有る |
| 列 | calendar_events.category | category\|character varying(50)\|true\|'meeting'::character varying |  |  | 印1:全件の後も無い |
| 列 | calendar_events.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | calendar_events.created_by_user_id | created_by_user_id\|integer\|false\| |  | created_by_user_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | calendar_events.description | description\|text\|false\| |  | description\|text\|false\| | 印1:全件の後に有る |
| 列 | calendar_events.end_datetime | end_datetime\|timestamp with time zone\|true\| |  | end_datetime\|timestamp with time zone\|true\| | 印1:全件の後に有る |
| 列 | calendar_events.google_calendar_id | google_calendar_id\|character varying(255)\|false\| |  | google_calendar_id\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | calendar_events.google_event_id | google_event_id\|character varying(255)\|false\| |  | google_event_id\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | calendar_events.id | id\|integer\|true\|nextval('X.calendar_events_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.calendar_events_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | calendar_events.is_all_day | is_all_day\|boolean\|true\|false |  | is_all_day\|boolean\|true\|false | 印1:全件の後に有る |
| 列 | calendar_events.is_cancelled | is_cancelled\|boolean\|true\|false |  | is_cancelled\|boolean\|true\|false | 印1:全件の後に有る |
| 列 | calendar_events.last_synced_at | last_synced_at\|timestamp with time zone\|false\| |  | last_synced_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | calendar_events.location | location\|text\|false\| |  | location\|text\|false\| | 印1:全件の後に有る |
| 列 | calendar_events.meet_url | meet_url\|text\|false\| |  | meet_url\|text\|false\| | 印1:全件の後に有る |
| 列 | calendar_events.original_start_datetime | original_start_datetime\|timestamp with time zone\|false\| |  | original_start_datetime\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | calendar_events.recurrence_rule | recurrence_rule\|text\|false\| |  | recurrence_rule\|text\|false\| | 印1:全件の後に有る |
| 列 | calendar_events.recurring_event_id | recurring_event_id\|integer\|false\| |  | recurring_event_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | calendar_events.source | source\|character varying(10)\|true\|'app'::character varying |  | source\|character varying(10)\|true\|'app'::character varying | 印1:全件の後に有る |
| 列 | calendar_events.start_datetime | start_datetime\|timestamp with time zone\|true\| |  | start_datetime\|timestamp with time zone\|true\| | 印1:全件の後に有る |
| 列 | calendar_events.sync_origin_id | sync_origin_id\|character varying(500)\|false\| |  | sync_origin_id\|character varying(500)\|false\| | 印1:全件の後に有る |
| 列 | calendar_events.sync_status | sync_status\|character varying(10)\|false\|'synced'::character varying |  | sync_status\|character varying(10)\|false\|'synced'::character varying | 印1:全件の後に有る |
| 列 | calendar_events.title | title\|character varying(500)\|true\| |  | title\|character varying(500)\|true\| | 印1:全件の後に有る |
| 列 | calendar_events.updated_at | updated_at\|timestamp with time zone\|true\|now() |  | updated_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | calendar_events.user_id | user_id\|integer\|false\| |  | user_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | calendar_owner_settings.color | color\|character varying(32)\|true\|'#1a73e8'::character varying |  |  | 印1:全件の後も無い |
| 列 | calendar_owner_settings.is_visible | is_visible\|boolean\|true\|false |  |  | 印1:全件の後も無い |
| 列 | calendar_owner_settings.share_mode | share_mode\|character varying(16)\|true\|'self'::character varying |  |  | 印1:全件の後も無い |
| 列 | calendar_owner_settings.staff_id | staff_id\|integer\|true\| |  |  | 印1:全件の後も無い |
| 列 | calendar_owner_settings.updated_at | updated_at\|timestamp with time zone\|true\|now() |  |  | 印1:全件の後も無い |
| 列 | close_reasons.created_at | created_at\|timestamp with time zone\|true\|now() | created_at\|timestamp with time zone\|false\|now() | created_at\|timestamp with time zone\|false\|now() | 印3:ひな形のまま |
| 列 | close_reasons.is_active | is_active\|boolean\|true\|true | is_active\|integer\|true\|1 | is_active\|integer\|true\|1 | 印3:ひな形のまま |
| 列 | companies.tenant_id | tenant_id\|integer\|true\| | tenant_id\|integer\|true\|3 | tenant_id\|integer\|true\|3 | 印3:ひな形のまま |
| 列 | company_discord.guild_id | guild_id\|character varying(50)\|false\| |  | guild_id\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | contact_contact_channels.guild_id | guild_id\|character varying(50)\|false\| |  | guild_id\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | contacts.tenant_id | tenant_id\|integer\|true\| | tenant_id\|integer\|true\|3 | tenant_id\|integer\|true\|3 | 印3:ひな形のまま |
| 列 | conversation_logs.analysis | analysis\|jsonb\|false\| |  | analysis\|jsonb\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.channel_identity | channel_identity\|character varying(255)\|false\| |  | channel_identity\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.channel_type | channel_type\|character varying(30)\|true\| |  | channel_type\|character varying(30)\|true\| | 印1:全件の後に有る |
| 列 | conversation_logs.company_id | company_id\|integer\|false\| |  | company_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.contact_id | contact_id\|integer\|false\| |  | contact_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.content_text | content_text\|text\|false\| |  | content_text\|text\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | conversation_logs.deal_id | deal_id\|integer\|false\| |  | deal_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.deleted_at | deleted_at\|timestamp with time zone\|false\| |  | deleted_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.direction | direction\|character varying(10)\|true\| |  | direction\|character varying(10)\|true\| | 印1:全件の後に有る |
| 列 | conversation_logs.external_message_id | external_message_id\|character varying(255)\|false\| |  | external_message_id\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.id | id\|integer\|true\|nextval('X.conversation_logs_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.conversation_logs_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | conversation_logs.is_manual | is_manual\|boolean\|false\| |  | is_manual\|boolean\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.lead_id | lead_id\|integer\|true\| |  | lead_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | conversation_logs.occurred_at | occurred_at\|timestamp with time zone\|true\| |  | occurred_at\|timestamp with time zone\|true\| | 印1:全件の後に有る |
| 列 | conversation_logs.original_language | original_language\|character varying(10)\|false\| |  | original_language\|character varying(10)\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.raw_payload | raw_payload\|jsonb\|false\| |  | raw_payload\|jsonb\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.recorded_by_user_id | recorded_by_user_id\|integer\|false\| |  | recorded_by_user_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.sender | sender\|character varying(100)\|false\| |  | sender\|character varying(100)\|false\| | 印1:全件の後に有る |
| 列 | conversation_logs.status | status\|character varying(20)\|false\|'sent'::character varying |  | status\|character varying(20)\|false\|'sent'::character varying | 印1:全件の後に有る |
| 列 | conversation_logs.tenant_id | tenant_id\|integer\|true\| |  | tenant_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | conversation_logs.translated_text | translated_text\|text\|false\| |  | translated_text\|text\|false\| | 印1:全件の後に有る |
| 列 | customer_scores.calibration_id | calibration_id\|integer\|false\| |  | calibration_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | customer_scores.confidence | confidence\|numeric(4,3)\|true\| |  | confidence\|numeric(4,3)\|true\| | 印1:全件の後に有る |
| 列 | customer_scores.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | customer_scores.id | id\|integer\|true\|nextval('X.customer_scores_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.customer_scores_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | customer_scores.is_cold_start | is_cold_start\|boolean\|true\|true |  | is_cold_start\|boolean\|true\|true | 印1:全件の後に有る |
| 列 | customer_scores.lead_id | lead_id\|integer\|true\| |  | lead_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | customer_scores.override_at | override_at\|timestamp with time zone\|false\| |  | override_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | customer_scores.override_by | override_by\|integer\|false\| |  | override_by\|integer\|false\| | 印1:全件の後に有る |
| 列 | customer_scores.override_note | override_note\|text\|false\| |  | override_note\|text\|false\| | 印1:全件の後に有る |
| 列 | customer_scores.override_score | override_score\|numeric(5,3)\|false\| |  | override_score\|numeric(5,3)\|false\| | 印1:全件の後に有る |
| 列 | customer_scores.sample_size | sample_size\|integer\|true\|0 |  | sample_size\|integer\|true\|0 | 印1:全件の後に有る |
| 列 | customer_scores.score | score\|numeric(5,3)\|true\| |  | score\|numeric(5,3)\|true\| | 印1:全件の後に有る |
| 列 | customer_scores.scored_at | scored_at\|timestamp with time zone\|true\|now() |  | scored_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | customer_scores.signal_summary | signal_summary\|jsonb\|true\|'{}'::jsonb |  | signal_summary\|jsonb\|true\|'{}'::jsonb | 印1:全件の後に有る |
| 列 | customer_scores.tenant_id | tenant_id\|integer\|true\| |  | tenant_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | customer_scores.tier | tier\|character varying(10)\|true\| |  | tier\|character varying(10)\|true\| | 印1:全件の後に有る |
| 列 | deal_close_reasons.is_primary | is_primary\|boolean\|true\|false | is_primary\|integer\|true\|0 | is_primary\|integer\|true\|0 | 印3:ひな形のまま |
| 列 | deal_close_reasons.lead_id | lead_id\|integer\|true\| | lead_id\|integer\|false\| | lead_id\|integer\|true\| | 印3:本番と同じになった |
| 列 | discord_channel_webhooks.channel_id | channel_id\|text\|true\| |  | channel_id\|text\|true\| | 印1:全件の後に有る |
| 列 | discord_channel_webhooks.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | discord_channel_webhooks.id | id\|integer\|true\|nextval('X.discord_channel_webhooks_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.discord_channel_webhooks_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | discord_channel_webhooks.tenant_id | tenant_id\|integer\|true\|(current_setting('app.tenant_id'::text, true))::integer |  | tenant_id\|integer\|true\|(current_setting('app.tenant_id'::text, true))::integer | 印1:全件の後に有る |
| 列 | discord_channel_webhooks.webhook_id | webhook_id\|text\|true\| |  | webhook_id\|text\|true\| | 印1:全件の後に有る |
| 列 | discord_channel_webhooks.webhook_token_encrypted | webhook_token_encrypted\|text\|true\| |  | webhook_token_encrypted\|text\|true\| | 印1:全件の後に有る |
| 列 | erp_sync_logs.completed_at | completed_at\|timestamp with time zone\|false\| |  | completed_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | erp_sync_logs.created_by | created_by\|integer\|false\| |  | created_by\|integer\|false\| | 印1:全件の後に有る |
| 列 | erp_sync_logs.direction | direction\|character varying(10)\|true\|'export'::character varying |  | direction\|character varying(10)\|true\|'export'::character varying | 印1:全件の後に有る |
| 列 | erp_sync_logs.error_message | error_message\|text\|false\| |  | error_message\|text\|false\| | 印1:全件の後に有る |
| 列 | erp_sync_logs.id | id\|integer\|true\|nextval('X.erp_sync_logs_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.erp_sync_logs_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | erp_sync_logs.record_count | record_count\|integer\|false\|0 |  | record_count\|integer\|false\|0 | 印1:全件の後に有る |
| 列 | erp_sync_logs.started_at | started_at\|timestamp with time zone\|false\|now() |  | started_at\|timestamp with time zone\|false\|now() | 印1:全件の後に有る |
| 列 | erp_sync_logs.status | status\|character varying(20)\|false\|'pending'::character varying |  | status\|character varying(20)\|false\|'pending'::character varying | 印1:全件の後に有る |
| 列 | erp_sync_logs.sync_type | sync_type\|character varying(50)\|true\| |  | sync_type\|character varying(50)\|true\| | 印1:全件の後に有る |
| 列 | erp_sync_logs.tenant_id | tenant_id\|integer\|true\|3 |  | tenant_id\|integer\|true\|3 | 印1:全件の後に有る |
| 列 | invoices.company_id | company_id\|integer\|true\| | company_id\|integer\|false\| | company_id\|integer\|true\| | 印3:本番と同じになった |
| 列 | lead_attachments.content_type | content_type\|character varying(128)\|false\| |  | content_type\|character varying(128)\|false\| | 印1:全件の後に有る |
| 列 | lead_attachments.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | lead_attachments.file_path | file_path\|text\|true\| |  | file_path\|text\|true\| | 印1:全件の後に有る |
| 列 | lead_attachments.file_size | file_size\|bigint\|true\| |  | file_size\|bigint\|true\| | 印1:全件の後に有る |
| 列 | lead_attachments.id | id\|integer\|true\|nextval('X.lead_attachments_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.lead_attachments_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | lead_attachments.lead_id | lead_id\|integer\|true\| |  | lead_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | lead_attachments.message_id | message_id\|character varying(64)\|true\| |  | message_id\|character varying(64)\|true\| | 印1:全件の後に有る |
| 列 | lead_attachments.original_filename | original_filename\|text\|false\| |  | original_filename\|text\|false\| | 印1:全件の後に有る |
| 列 | lead_attachments.platform | platform\|character varying(32)\|true\| |  | platform\|character varying(32)\|true\| | 印1:全件の後に有る |
| 列 | lead_attachments.tenant_id | tenant_id\|integer\|true\| |  | tenant_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | lead_attachments.updated_at | updated_at\|timestamp with time zone\|true\|now() |  | updated_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | leads.converted_deal_id |  | converted_deal_id\|integer\|false\| |  | 印2:消えた |
| 列 | leads.discord_dm_channel_id | discord_dm_channel_id\|character varying(50)\|false\| |  | discord_dm_channel_id\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | leads.discord_guild_channel_id | discord_guild_channel_id\|character varying(50)\|false\| |  | discord_guild_channel_id\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | leads.discord_id | discord_id\|character varying(255)\|false\| |  | discord_id\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | leads.discord_role_sync_at | discord_role_sync_at\|timestamp with time zone\|false\| |  | discord_role_sync_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | leads.discord_role_sync_status | discord_role_sync_status\|character varying(20)\|false\| |  | discord_role_sync_status\|character varying(20)\|false\| | 印1:全件の後に有る |
| 列 | leads.discord_user_id | discord_user_id\|character varying(50)\|false\| |  | discord_user_id\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | leads.english_name | english_name\|character varying(255)\|false\| |  | english_name\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | leads.instagram_link | instagram_link\|character varying(1000)\|false\| |  | instagram_link\|character varying(1000)\|false\| | 印1:全件の後に有る |
| 列 | leads.lead_code | lead_code\|character varying(20)\|true\|('LD-'::text \|\| lpad((nextval('X.lead_code_seq'::regclass))::text, 5, '0'::text)) | lead_code\|character varying(20)\|false\| | lead_code\|character varying(20)\|false\| | 印3:ひな形のまま |
| 列 | leads.messenger_link | messenger_link\|character varying(1000)\|false\| |  | messenger_link\|character varying(1000)\|false\| | 印1:全件の後に有る |
| 列 | leads.whatsapp_link | whatsapp_link\|character varying(1000)\|false\| |  | whatsapp_link\|character varying(1000)\|false\| | 印1:全件の後に有る |
| 列 | message_labels.confidence | confidence\|numeric(4,3)\|true\| |  | confidence\|numeric(4,3)\|true\| | 印1:全件の後に有る |
| 列 | message_labels.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | message_labels.direction | direction\|character varying(10)\|true\| |  | direction\|character varying(10)\|true\| | 印1:全件の後に有る |
| 列 | message_labels.id | id\|integer\|true\|nextval('X.message_labels_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.message_labels_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | message_labels.label | label\|character varying(30)\|true\| |  | label\|character varying(30)\|true\| | 印1:全件の後に有る |
| 列 | message_labels.lead_id | lead_id\|integer\|false\| |  | lead_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | message_labels.message_id | message_id\|integer\|true\| |  | message_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | message_labels.override_at | override_at\|timestamp with time zone\|false\| |  | override_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | message_labels.override_by | override_by\|integer\|false\| |  | override_by\|integer\|false\| | 印1:全件の後に有る |
| 列 | message_labels.source | source\|character varying(20)\|true\|'rule'::character varying |  | source\|character varying(20)\|true\|'rule'::character varying | 印1:全件の後に有る |
| 列 | message_labels.tenant_id | tenant_id\|integer\|true\| |  | tenant_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | message_translations.confidence | confidence\|real\|false\| |  | confidence\|real\|false\| | 印1:全件の後に有る |
| 列 | message_translations.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | message_translations.engine | engine\|character varying(50)\|true\|'gemini-2.5-flash'::character varying |  | engine\|character varying(50)\|true\|'gemini-2.5-flash'::character varying | 印1:全件の後に有る |
| 列 | message_translations.id | id\|integer\|true\|nextval('X.message_translations_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.message_translations_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | message_translations.message_id | message_id\|text\|true\| |  | message_id\|text\|true\| | 印1:全件の後に有る |
| 列 | message_translations.original_language | original_language\|character varying(10)\|false\| |  | original_language\|character varying(10)\|false\| | 印1:全件の後に有る |
| 列 | message_translations.target_language | target_language\|character varying(10)\|true\| |  | target_language\|character varying(10)\|true\| | 印1:全件の後に有る |
| 列 | message_translations.tenant_id | tenant_id\|integer\|false\| |  | tenant_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | message_translations.translated_text | translated_text\|text\|true\| |  | translated_text\|text\|true\| | 印1:全件の後に有る |
| 列 | meta_message_reactions.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | meta_message_reactions.emoji_animated | emoji_animated\|boolean\|false\|false |  | emoji_animated\|boolean\|false\|false | 印1:全件の後に有る |
| 列 | meta_message_reactions.emoji_id | emoji_id\|text\|false\| |  | emoji_id\|text\|false\| | 印1:全件の後に有る |
| 列 | meta_message_reactions.emoji_name | emoji_name\|text\|true\| |  | emoji_name\|text\|true\| | 印1:全件の後に有る |
| 列 | meta_message_reactions.id | id\|integer\|true\|nextval('X.meta_message_reactions_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.meta_message_reactions_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | meta_message_reactions.is_bot_reaction | is_bot_reaction\|boolean\|false\|false |  | is_bot_reaction\|boolean\|false\|false | 印1:全件の後に有る |
| 列 | meta_message_reactions.meta_message_id | meta_message_id\|integer\|true\| |  | meta_message_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | meta_message_reactions.reactor_discord_user_id | reactor_discord_user_id\|text\|true\| |  | reactor_discord_user_id\|text\|true\| | 印1:全件の後に有る |
| 列 | meta_message_reactions.reactor_display_name | reactor_display_name\|text\|false\| |  | reactor_display_name\|text\|false\| | 印1:全件の後に有る |
| 列 | meta_message_reactions.tenant_id | tenant_id\|integer\|true\|(current_setting('app.tenant_id'::text, true))::integer |  | tenant_id\|integer\|true\|(current_setting('app.tenant_id'::text, true))::integer | 印1:全件の後に有る |
| 列 | meta_messages.attachment_type | attachment_type\|character varying(20)\|false\| |  | attachment_type\|character varying(20)\|false\| | 印1:全件の後に有る |
| 列 | meta_messages.attachment_url | attachment_url\|text\|false\| |  | attachment_url\|text\|false\| | 印1:全件の後に有る |
| 列 | meta_messages.error_code | error_code\|character varying(50)\|false\| |  | error_code\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | meta_messages.error_message | error_message\|text\|false\| |  | error_message\|text\|false\| | 印1:全件の後に有る |
| 列 | meta_messages.message_tag | message_tag\|character varying(50)\|false\| |  | message_tag\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | meta_messages.messaging_type | messaging_type\|character varying(20)\|false\| |  | messaging_type\|character varying(20)\|false\| | 印1:全件の後に有る |
| 列 | meta_messages.page_id | page_id\|character varying(50)\|false\| |  | page_id\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | meta_messages.recipient_id | recipient_id\|character varying(100)\|false\| |  | recipient_id\|character varying(100)\|false\| | 印1:全件の後に有る |
| 列 | meta_messages.seen_at | seen_at\|timestamp with time zone\|false\| |  | seen_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | meta_messages.seen_by_staff_id | seen_by_staff_id\|integer\|false\| |  | seen_by_staff_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | meta_messages.sent_by_staff_id | sent_by_staff_id\|integer\|false\| |  | sent_by_staff_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | notification_channels.blueprint_key | blueprint_key\|text\|false\| |  | blueprint_key\|text\|false\| | 印1:全件の後に有る |
| 列 | notification_channels.channel_name | channel_name\|character varying(100)\|true\| |  | channel_name\|character varying(100)\|true\| | 印1:全件の後に有る |
| 列 | notification_channels.channel_type | channel_type\|character varying(20)\|true\|'discord'::character varying |  | channel_type\|character varying(20)\|true\|'discord'::character varying | 印1:全件の後に有る |
| 列 | notification_channels.created_at | created_at\|timestamp with time zone\|false\|now() |  | created_at\|timestamp with time zone\|false\|now() | 印1:全件の後に有る |
| 列 | notification_channels.event_types | event_types\|text\|false\|'[]'::text |  | event_types\|text\|false\|'[]'::text | 印1:全件の後に有る |
| 列 | notification_channels.id | id\|integer\|true\|nextval('X.notification_channels_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.notification_channels_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | notification_channels.is_active | is_active\|boolean\|false\|true |  | is_active\|boolean\|false\|true | 印1:全件の後に有る |
| 列 | notification_channels.tenant_id | tenant_id\|integer\|true\|3 |  | tenant_id\|integer\|true\|3 | 印1:全件の後に有る |
| 列 | notification_channels.updated_at | updated_at\|timestamp with time zone\|false\|now() |  | updated_at\|timestamp with time zone\|false\|now() | 印1:全件の後に有る |
| 列 | notification_channels.webhook_url | webhook_url\|character varying(500)\|true\| |  | webhook_url\|character varying(500)\|true\| | 印1:全件の後に有る |
| 列 | notification_logs.channel_id | channel_id\|integer\|false\| |  | channel_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | notification_logs.created_at | created_at\|timestamp with time zone\|false\|now() |  | created_at\|timestamp with time zone\|false\|now() | 印1:全件の後に有る |
| 列 | notification_logs.error_message | error_message\|text\|false\| |  | error_message\|text\|false\| | 印1:全件の後に有る |
| 列 | notification_logs.event_type | event_type\|character varying(50)\|true\| |  | event_type\|character varying(50)\|true\| | 印1:全件の後に有る |
| 列 | notification_logs.id | id\|integer\|true\|nextval('X.notification_logs_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.notification_logs_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | notification_logs.message | message\|text\|false\| |  | message\|text\|false\| | 印1:全件の後に有る |
| 列 | notification_logs.sent_at | sent_at\|timestamp with time zone\|false\| |  | sent_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | notification_logs.status | status\|character varying(20)\|false\|'pending'::character varying |  | status\|character varying(20)\|false\|'pending'::character varying | 印1:全件の後に有る |
| 列 | notification_logs.tenant_id | tenant_id\|integer\|true\|3 |  | tenant_id\|integer\|true\|3 | 印1:全件の後に有る |
| 列 | notification_logs.title | title\|character varying(255)\|true\| |  | title\|character varying(255)\|true\| | 印1:全件の後に有る |
| 列 | order_commissions.calculated_amount | calculated_amount\|numeric(14,2)\|true\|0 |  | calculated_amount\|numeric(14,2)\|true\|0 | 印1:全件の後に有る |
| 列 | order_commissions.calculated_at | calculated_at\|timestamp with time zone\|false\| |  | calculated_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | order_commissions.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | order_commissions.id | id\|integer\|true\|nextval('X.order_commissions_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.order_commissions_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | order_commissions.notes | notes\|text\|false\| |  | notes\|text\|false\| | 印1:全件の後に有る |
| 列 | order_commissions.order_id | order_id\|integer\|true\| |  | order_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | order_commissions.role | role\|text\|true\| |  | role\|text\|true\| | 印1:全件の後に有る |
| 列 | order_commissions.staff_id | staff_id\|integer\|false\| |  | staff_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | order_commissions.tenant_id | tenant_id\|integer\|true\|3 |  | tenant_id\|integer\|true\|3 | 印1:全件の後に有る |
| 列 | order_commissions.updated_at | updated_at\|timestamp with time zone\|true\|now() |  | updated_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | order_financials.ad_cost | ad_cost\|numeric(14,2)\|false\|0 |  | ad_cost\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_financials.commission_base_amount | commission_base_amount\|numeric(14,2)\|false\|0 |  | commission_base_amount\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_financials.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | order_financials.exchange_fee | exchange_fee\|numeric(14,2)\|false\|0 |  | exchange_fee\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_financials.id | id\|integer\|true\|nextval('X.order_financials_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.order_financials_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | order_financials.notes | notes\|text\|false\| |  | notes\|text\|false\| | 印1:全件の後に有る |
| 列 | order_financials.order_id | order_id\|integer\|true\| |  | order_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | order_financials.outsource_fee | outsource_fee\|numeric(14,2)\|false\|0 |  | outsource_fee\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_financials.packing_fee | packing_fee\|numeric(14,2)\|false\|0 |  | packing_fee\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_financials.paypal_fee | paypal_fee\|numeric(14,2)\|false\|0 |  | paypal_fee\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_financials.purchase_cost | purchase_cost\|numeric(14,2)\|false\| |  | purchase_cost\|numeric(14,2)\|false\| | 印1:全件の後に有る |
| 列 | order_financials.purchase_shipping | purchase_shipping\|numeric(14,2)\|false\|0 |  | purchase_shipping\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_financials.refund_amount | refund_amount\|numeric(14,2)\|false\|0 |  | refund_amount\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_financials.return_fee | return_fee\|numeric(14,2)\|false\|0 |  | return_fee\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_financials.revenue_amount | revenue_amount\|numeric(14,2)\|false\|0 |  | revenue_amount\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_financials.tax_refund | tax_refund\|numeric(14,2)\|false\|0 |  | tax_refund\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_financials.tenant_id | tenant_id\|integer\|true\|3 |  | tenant_id\|integer\|true\|3 | 印1:全件の後に有る |
| 列 | order_financials.updated_at | updated_at\|timestamp with time zone\|true\|now() |  | updated_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | order_financials.wise_fee | wise_fee\|numeric(14,2)\|false\|0 |  | wise_fee\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_purchase_details.carrier_name | carrier_name\|text\|false\| |  | carrier_name\|text\|false\| | 印1:全件の後に有る |
| 列 | order_purchase_details.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | order_purchase_details.id | id\|integer\|true\|nextval('X.order_purchase_details_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.order_purchase_details_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | order_purchase_details.order_id | order_id\|integer\|true\| |  | order_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | order_purchase_details.purchase_amount | purchase_amount\|numeric(14,2)\|false\|0 |  | purchase_amount\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_purchase_details.purchase_date | purchase_date\|date\|false\| |  | purchase_date\|date\|false\| | 印1:全件の後に有る |
| 列 | order_purchase_details.purchase_note | purchase_note\|text\|false\| |  | purchase_note\|text\|false\| | 印1:全件の後に有る |
| 列 | order_purchase_details.purchase_quantity | purchase_quantity\|integer\|false\|0 |  | purchase_quantity\|integer\|false\|0 | 印1:全件の後に有る |
| 列 | order_purchase_details.purchase_shipping | purchase_shipping\|numeric(14,2)\|false\|0 |  | purchase_shipping\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_purchase_details.purchase_staff | purchase_staff\|text\|false\| |  | purchase_staff\|text\|false\| | 印1:全件の後に有る |
| 列 | order_purchase_details.purchase_status | purchase_status\|text\|true\|''::text |  | purchase_status\|text\|true\|''::text | 印1:全件の後に有る |
| 列 | order_purchase_details.purchase_total | purchase_total\|numeric(14,2)\|false\|0 |  | purchase_total\|numeric(14,2)\|false\|0 | 印1:全件の後に有る |
| 列 | order_purchase_details.supplier_name | supplier_name\|text\|false\| |  | supplier_name\|text\|false\| | 印1:全件の後に有る |
| 列 | order_purchase_details.supplier_url | supplier_url\|text\|false\| |  | supplier_url\|text\|false\| | 印1:全件の後に有る |
| 列 | order_purchase_details.tenant_id | tenant_id\|integer\|true\|3 |  | tenant_id\|integer\|true\|3 | 印1:全件の後に有る |
| 列 | order_purchase_details.transaction_no | transaction_no\|text\|false\| |  | transaction_no\|text\|false\| | 印1:全件の後に有る |
| 列 | order_purchase_details.updated_at | updated_at\|timestamp with time zone\|true\|now() |  | updated_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | order_purchase_details.waybill_no | waybill_no\|text\|false\| |  | waybill_no\|text\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.address1 | address1\|character varying(255)\|false\| |  | address1\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.address2 | address2\|character varying(255)\|false\| |  | address2\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.address3 | address3\|character varying(255)\|false\| |  | address3\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.address_type | address_type\|character varying(20)\|false\| |  | address_type\|character varying(20)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.box_count | box_count\|integer\|false\| |  | box_count\|integer\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.carrier | carrier\|character varying(20)\|false\| |  | carrier\|character varying(20)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.city | city\|character varying(100)\|false\| |  | city\|character varying(100)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.confirmed_currency | confirmed_currency\|character varying(10)\|false\| |  | confirmed_currency\|character varying(10)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.confirmed_shipping_fee | confirmed_shipping_fee\|numeric(12,2)\|false\| |  | confirmed_shipping_fee\|numeric(12,2)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.country_code | country_code\|character varying(10)\|false\| |  | country_code\|character varying(10)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | order_shipping_details.email | email\|character varying(255)\|false\| |  | email\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.est_shipping_fee | est_shipping_fee\|numeric(12,2)\|false\| |  | est_shipping_fee\|numeric(12,2)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.exchange_rate | exchange_rate\|numeric(12,6)\|false\| |  | exchange_rate\|numeric(12,6)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.fedex_id | fedex_id\|character varying(100)\|false\| |  | fedex_id\|character varying(100)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.height_cm | height_cm\|numeric(8,2)\|false\| |  | height_cm\|numeric(8,2)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.hs_code | hs_code\|character varying(50)\|false\| |  | hs_code\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.id | id\|integer\|true\|nextval('X.order_shipping_details_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.order_shipping_details_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | order_shipping_details.inspection_status | inspection_status\|character varying(50)\|false\| |  | inspection_status\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.item_description | item_description\|character varying(500)\|false\| |  | item_description\|character varying(500)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.item_price_usd | item_price_usd\|numeric(12,2)\|false\| |  | item_price_usd\|numeric(12,2)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.label_drive_url | label_drive_url\|text\|false\| |  | label_drive_url\|text\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.label_issued_at | label_issued_at\|timestamp with time zone\|false\| |  | label_issued_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.length_cm | length_cm\|numeric(8,2)\|false\| |  | length_cm\|numeric(8,2)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.notified_at | notified_at\|timestamp with time zone\|false\| |  | notified_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.order_id | order_id\|integer\|true\| |  | order_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | order_shipping_details.packing_memo | packing_memo\|text\|false\| |  | packing_memo\|text\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.packing_type | packing_type\|character varying(50)\|false\| |  | packing_type\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.phone | phone\|character varying(50)\|false\| |  | phone\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.pickup_confirmation_code | pickup_confirmation_code\|character varying(100)\|false\| |  | pickup_confirmation_code\|character varying(100)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.pickup_requested_at | pickup_requested_at\|timestamp with time zone\|false\| |  | pickup_requested_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.recipient_name | recipient_name\|character varying(255)\|false\| |  | recipient_name\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.ship_date | ship_date\|date\|false\| |  | ship_date\|date\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.ship_memo | ship_memo\|text\|false\| |  | ship_memo\|text\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.ship_method | ship_method\|character varying(50)\|false\| |  | ship_method\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.shipped_at | shipped_at\|timestamp with time zone\|false\| |  | shipped_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.state_code | state_code\|character varying(20)\|false\| |  | state_code\|character varying(20)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.surcharges | surcharges\|jsonb\|false\| |  | surcharges\|jsonb\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.tax_id | tax_id\|character varying(100)\|false\| |  | tax_id\|character varying(100)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.tax_number | tax_number\|character varying(100)\|false\| |  | tax_number\|character varying(100)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.tenant_id | tenant_id\|integer\|true\|3 |  | tenant_id\|integer\|true\|3 | 印1:全件の後に有る |
| 列 | order_shipping_details.tracking_number | tracking_number\|character varying(200)\|false\| |  | tracking_number\|character varying(200)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.updated_at | updated_at\|timestamp with time zone\|true\|now() |  | updated_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | order_shipping_details.volume_g | volume_g\|numeric(10,2)\|false\| |  | volume_g\|numeric(10,2)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.weight_kg | weight_kg\|numeric(8,3)\|false\| |  | weight_kg\|numeric(8,3)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.width_cm | width_cm\|numeric(8,2)\|false\| |  | width_cm\|numeric(8,2)\|false\| | 印1:全件の後に有る |
| 列 | order_shipping_details.zip_code | zip_code\|character varying(50)\|false\| |  | zip_code\|character varying(50)\|false\| | 印1:全件の後に有る |
| 列 | orders.company_id | company_id\|integer\|true\| | company_id\|integer\|false\| | company_id\|integer\|true\| | 印3:本番と同じになった |
| 列 | orders.currency | currency\|character varying(10)\|false\|'JPY'::character varying |  |  | 印1:全件の後も無い |
| 列 | orders.delivered_at | delivered_at\|timestamp with time zone\|false\| |  |  | 印1:全件の後も無い |
| 列 | orders.invoice_id | invoice_id\|integer\|false\| |  |  | 印1:全件の後も無い |
| 列 | orders.shipped_at | shipped_at\|timestamp with time zone\|false\| |  |  | 印1:全件の後も無い |
| 列 | orders.shipping_carrier | shipping_carrier\|character varying(50)\|false\| |  |  | 印1:全件の後も無い |
| 列 | orders.shipping_country | shipping_country\|character varying(100)\|false\| |  |  | 印1:全件の後も無い |
| 列 | orders.shipping_fee | shipping_fee\|numeric(15,2)\|false\| |  |  | 印1:全件の後も無い |
| 列 | orders.tracking_number | tracking_number\|character varying(200)\|false\| |  |  | 印1:全件の後も無い |
| 列 | outbound_translation_drafts.confidence | confidence\|real\|false\| |  | confidence\|real\|false\| | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.confirmed_at | confirmed_at\|timestamp with time zone\|false\| |  | confirmed_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.draft_text | draft_text\|text\|true\| |  | draft_text\|text\|true\| | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.final_text | final_text\|text\|false\| |  | final_text\|text\|false\| | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.flagged_terms | flagged_terms\|jsonb\|false\| |  | flagged_terms\|jsonb\|false\| | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.id | id\|integer\|true\|nextval('X.outbound_translation_drafts_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.outbound_translation_drafts_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.is_edited | is_edited\|boolean\|false\| |  | is_edited\|boolean\|false\| | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.lead_id | lead_id\|integer\|false\| |  | lead_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.meta_message_id | meta_message_id\|integer\|false\| |  | meta_message_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.model | model\|character varying(50)\|true\| |  | model\|character varying(50)\|true\| | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.original_text | original_text\|text\|true\| |  | original_text\|text\|true\| | 印1:全件の後に有る |
| 列 | outbound_translation_drafts.tenant_id | tenant_id\|integer\|true\| |  | tenant_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | paypal_disputes.amount | amount\|numeric(15,2)\|false\| |  | amount\|numeric(15,2)\|false\| | 印1:全件の後に有る |
| 列 | paypal_disputes.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | paypal_disputes.currency | currency\|text\|false\| |  | currency\|text\|false\| | 印1:全件の後に有る |
| 列 | paypal_disputes.dispute_id | dispute_id\|text\|true\| |  | dispute_id\|text\|true\| | 印1:全件の後に有る |
| 列 | paypal_disputes.id | id\|integer\|true\|nextval('X.paypal_disputes_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.paypal_disputes_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | paypal_disputes.invoice_id | invoice_id\|integer\|false\| |  | invoice_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | paypal_disputes.pp_status | pp_status\|text\|false\| |  | pp_status\|text\|false\| | 印1:全件の後に有る |
| 列 | paypal_disputes.raw | raw\|jsonb\|false\| |  | raw\|jsonb\|false\| | 印1:全件の後に有る |
| 列 | paypal_disputes.reason | reason\|text\|false\| |  | reason\|text\|false\| | 印1:全件の後に有る |
| 列 | paypal_disputes.updated_at | updated_at\|timestamp with time zone\|true\|now() |  | updated_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | purchase_orders.company_name_snapshot | company_name_snapshot\|character varying(255)\|false\| |  | company_name_snapshot\|character varying(255)\|false\| | 印1:全件の後に有る |
| 列 | purchase_orders.contact_info_snapshot | contact_info_snapshot\|text\|false\| |  | contact_info_snapshot\|text\|false\| | 印1:全件の後に有る |
| 列 | quotes.company_id | company_id\|integer\|true\| | company_id\|integer\|false\| | company_id\|integer\|true\| | 印3:本番と同じになった |
| 列 | quotes.lead_id | lead_id\|integer\|true\| | lead_id\|integer\|false\| | lead_id\|integer\|true\| | 印3:本番と同じになった |
| 列 | shifts.created_at | created_at\|timestamp with time zone\|false\|now() |  | created_at\|timestamp with time zone\|false\|now() | 印1:全件の後に有る |
| 列 | shifts.end_time | end_time\|time without time zone\|true\| |  | end_time\|time without time zone\|true\| | 印1:全件の後に有る |
| 列 | shifts.id | id\|integer\|true\|nextval('X.shifts_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.shifts_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | shifts.notes | notes\|text\|false\| |  | notes\|text\|false\| | 印1:全件の後に有る |
| 列 | shifts.shift_date | shift_date\|date\|true\| |  | shift_date\|date\|true\| | 印1:全件の後に有る |
| 列 | shifts.shift_type | shift_type\|character varying(20)\|false\|'normal'::character varying |  | shift_type\|character varying(20)\|false\|'normal'::character varying | 印1:全件の後に有る |
| 列 | shifts.start_time | start_time\|time without time zone\|true\| |  | start_time\|time without time zone\|true\| | 印1:全件の後に有る |
| 列 | shifts.tenant_id | tenant_id\|integer\|true\|3 |  | tenant_id\|integer\|true\|3 | 印1:全件の後に有る |
| 列 | shifts.updated_at | updated_at\|timestamp with time zone\|false\|now() |  | updated_at\|timestamp with time zone\|false\|now() | 印1:全件の後に有る |
| 列 | shifts.user_id | user_id\|integer\|true\| |  | user_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | staff.avatar_token | avatar_token\|text\|false\| |  | avatar_token\|text\|false\| | 印1:全件の後に有る |
| 列 | staff.is_employee | is_employee\|boolean\|true\|false |  | is_employee\|boolean\|true\|false | 印1:全件の後に有る |
| 列 | staff.phone | phone\|character varying(20)\|false\| |  | phone\|character varying(20)\|false\| | 印1:全件の後に有る |
| 列 | staff_reports.ai_feedback | ai_feedback\|text\|false\| |  | ai_feedback\|text\|false\| | 印1:全件の後に有る |
| 列 | staff_reports.challenges | challenges\|text\|false\| |  | challenges\|text\|false\| | 印1:全件の後に有る |
| 列 | staff_reports.created_at | created_at\|timestamp with time zone\|false\|now() |  | created_at\|timestamp with time zone\|false\|now() | 印1:全件の後に有る |
| 列 | staff_reports.goals | goals\|text\|false\| |  | goals\|text\|false\| | 印1:全件の後に有る |
| 列 | staff_reports.id | id\|integer\|true\|nextval('X.staff_reports_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.staff_reports_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | staff_reports.period | period\|character varying(20)\|true\| |  | period\|character varying(20)\|true\| | 印1:全件の後に有る |
| 列 | staff_reports.report_code | report_code\|character varying(20)\|false\| |  | report_code\|character varying(20)\|false\| | 印1:全件の後に有る |
| 列 | staff_reports.report_type | report_type\|character varying(20)\|true\| |  | report_type\|character varying(20)\|true\| | 印1:全件の後に有る |
| 列 | staff_reports.review | review\|text\|false\| |  | review\|text\|false\| | 印1:全件の後に有る |
| 列 | staff_reports.reviewed_at | reviewed_at\|timestamp with time zone\|false\| |  | reviewed_at\|timestamp with time zone\|false\| | 印1:全件の後に有る |
| 列 | staff_reports.reviewer_comment | reviewer_comment\|text\|false\| |  | reviewer_comment\|text\|false\| | 印1:全件の後に有る |
| 列 | staff_reports.reviewer_id | reviewer_id\|integer\|false\| |  | reviewer_id\|integer\|false\| | 印1:全件の後に有る |
| 列 | staff_reports.self_evaluation | self_evaluation\|text\|false\| |  | self_evaluation\|text\|false\| | 印1:全件の後に有る |
| 列 | staff_reports.submitted_at | submitted_at\|timestamp with time zone\|false\|now() |  | submitted_at\|timestamp with time zone\|false\|now() | 印1:全件の後に有る |
| 列 | staff_reports.tenant_id | tenant_id\|integer\|true\|3 |  | tenant_id\|integer\|true\|3 | 印1:全件の後に有る |
| 列 | staff_reports.updated_at | updated_at\|timestamp with time zone\|false\|now() |  | updated_at\|timestamp with time zone\|false\|now() | 印1:全件の後に有る |
| 列 | staff_reports.user_id | user_id\|integer\|true\| |  | user_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | staff_ui_preferences.show_buddy_menu | show_buddy_menu\|boolean\|true\|true |  |  | 印1:全件の後も無い |
| 列 | suppliers.address |  | address\|text\|false\| | address\|text\|false\| | 印2:残っている |
| 列 | suppliers.contact_name |  | contact_name\|character varying(255)\|false\| | contact_name\|character varying(255)\|false\| | 印2:残っている |
| 列 | suppliers.created_at |  | created_at\|timestamp with time zone\|false\|now() | created_at\|timestamp with time zone\|false\|now() | 印2:残っている |
| 列 | suppliers.email |  | email\|character varying(255)\|false\| | email\|character varying(255)\|false\| | 印2:残っている |
| 列 | suppliers.id |  | id\|integer\|true\|nextval('X.suppliers_id_seq'::regclass) | id\|integer\|true\|nextval('X.suppliers_id_seq'::regclass) | 印2:残っている |
| 列 | suppliers.is_active |  | is_active\|boolean\|false\|true | is_active\|boolean\|false\|true | 印2:残っている |
| 列 | suppliers.name |  | name\|character varying(255)\|true\| | name\|character varying(255)\|true\| | 印2:残っている |
| 列 | suppliers.notes |  | notes\|text\|false\| | notes\|text\|false\| | 印2:残っている |
| 列 | suppliers.phone |  | phone\|character varying(50)\|false\| | phone\|character varying(50)\|false\| | 印2:残っている |
| 列 | suppliers.supplier_code |  | supplier_code\|character varying(20)\|false\| | supplier_code\|character varying(20)\|false\| | 印2:残っている |
| 列 | suppliers.tenant_id |  | tenant_id\|integer\|true\|3 | tenant_id\|integer\|true\|3 | 印2:残っている |
| 列 | suppliers.updated_at |  | updated_at\|timestamp with time zone\|false\|now() | updated_at\|timestamp with time zone\|false\|now() | 印2:残っている |
| 列 | tenant_calibrations.calibrated_at | calibrated_at\|timestamp with time zone\|true\|now() |  | calibrated_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | tenant_calibrations.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | tenant_calibrations.id | id\|integer\|true\|nextval('X.tenant_calibrations_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.tenant_calibrations_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | tenant_calibrations.is_cold_start | is_cold_start\|boolean\|true\|true |  | is_cold_start\|boolean\|true\|true | 印1:全件の後に有る |
| 列 | tenant_calibrations.label_weights | label_weights\|jsonb\|true\|'{}'::jsonb |  | label_weights\|jsonb\|true\|'{}'::jsonb | 印1:全件の後に有る |
| 列 | tenant_calibrations.loss_sample_size | loss_sample_size\|integer\|true\|0 |  | loss_sample_size\|integer\|true\|0 | 印1:全件の後に有る |
| 列 | tenant_calibrations.tenant_id | tenant_id\|integer\|true\| |  | tenant_id\|integer\|true\| | 印1:全件の後に有る |
| 列 | tenant_calibrations.win_sample_size | win_sample_size\|integer\|true\|0 |  | win_sample_size\|integer\|true\|0 | 印1:全件の後に有る |
| 列 | tenant_commission_settings.commission_rates | commission_rates\|jsonb\|true\|'{"ship": {"type": "fixed", "value": 200}, "order": {"type": "rate", "value": 0.10}, "sales": {"type": "rate", "value": 0.10}, "trouble": {"type": "fixed", "value": 500}, "purchase": {"type": "fixed", "value": 100}}'::jsonb |  | commission_rates\|jsonb\|true\|'{"ship": {"type": "fixed", "value": 200}, "order": {"type": "rate", "value": 0.10}, "sales": {"type": "rate", "value": 0.10}, "trouble": {"type": "fixed", "value": 500}, "purchase": {"type": "fixed", "value": 100}}'::jsonb | 印1:全件の後に有る |
| 列 | tenant_commission_settings.created_at | created_at\|timestamp with time zone\|true\|now() |  | created_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | tenant_commission_settings.id | id\|integer\|true\|nextval('X.tenant_commission_settings_id_seq'::regclass) |  | id\|integer\|true\|nextval('X.tenant_commission_settings_id_seq'::regclass) | 印1:全件の後に有る |
| 列 | tenant_commission_settings.tenant_id | tenant_id\|integer\|true\|3 |  | tenant_id\|integer\|true\|3 | 印1:全件の後に有る |
| 列 | tenant_commission_settings.updated_at | updated_at\|timestamp with time zone\|true\|now() |  | updated_at\|timestamp with time zone\|true\|now() | 印1:全件の後に有る |
| 列 | tenant_meta_config.granted_scopes | granted_scopes\|jsonb\|false\| |  | granted_scopes\|jsonb\|false\| | 印1:全件の後に有る |
| 列 | user_badges.badge_id | badge_id\|integer\|true\| |  |  | 印1:全件の後も無い |
| 列 | user_badges.earned_at | earned_at\|timestamp with time zone\|false\|now() |  |  | 印1:全件の後も無い |
| 列 | user_badges.id | id\|integer\|true\|nextval('X.user_badges_id_seq'::regclass) |  |  | 印1:全件の後も無い |
| 列 | user_badges.tenant_id | tenant_id\|integer\|true\|3 |  |  | 印1:全件の後も無い |
| 列 | user_badges.user_id | user_id\|integer\|true\| |  |  | 印1:全件の後も無い |
| 索引 | archives_pkey | CREATE UNIQUE INDEX archives_pkey ON X.archives USING btree (id) |  | CREATE UNIQUE INDEX archives_pkey ON X.archives USING btree (id) | 印1:全件の後に有る |
| 索引 | badge_definitions_pkey | CREATE UNIQUE INDEX badge_definitions_pkey ON X.badge_definitions USING btree (id) |  |  | 印1:全件の後も無い |
| 索引 | buddy_feedbacks_pkey | CREATE UNIQUE INDEX buddy_feedbacks_pkey ON X.buddy_feedbacks USING btree (id) |  |  | 印1:全件の後も無い |
| 索引 | buddy_pairs_pkey | CREATE UNIQUE INDEX buddy_pairs_pkey ON X.buddy_pairs USING btree (id) |  |  | 印1:全件の後も無い |
| 索引 | buddy_pairs_tenant_id_coach_user_id_mentee_user_id_key | CREATE UNIQUE INDEX buddy_pairs_tenant_id_coach_user_id_mentee_user_id_key ON X.buddy_pairs USING btree (tenant_id, coach_user_id, mentee_user_id) |  |  | 印1:全件の後も無い |
| 索引 | calendar_events_exception_unique_idx | CREATE UNIQUE INDEX calendar_events_exception_unique_idx ON X.calendar_events USING btree (recurring_event_id, original_start_datetime) WHERE (recurring_event_id IS NOT NULL) |  | CREATE UNIQUE INDEX calendar_events_exception_unique_idx ON X.calendar_events USING btree (recurring_event_id, original_start_datetime) WHERE (recurring_event_id IS NOT NULL) | 印1:全件の後に有る |
| 索引 | calendar_events_pkey | CREATE UNIQUE INDEX calendar_events_pkey ON X.calendar_events USING btree (id) |  | CREATE UNIQUE INDEX calendar_events_pkey ON X.calendar_events USING btree (id) | 印1:全件の後に有る |
| 索引 | calendar_owner_settings_pkey | CREATE UNIQUE INDEX calendar_owner_settings_pkey ON X.calendar_owner_settings USING btree (staff_id) |  |  | 印1:全件の後も無い |
| 索引 | conversation_logs_external_message_id_key | CREATE UNIQUE INDEX conversation_logs_external_message_id_key ON X.conversation_logs USING btree (external_message_id) |  | CREATE UNIQUE INDEX conversation_logs_external_message_id_key ON X.conversation_logs USING btree (external_message_id) | 印1:全件の後に有る |
| 索引 | conversation_logs_pkey | CREATE UNIQUE INDEX conversation_logs_pkey ON X.conversation_logs USING btree (id) |  | CREATE UNIQUE INDEX conversation_logs_pkey ON X.conversation_logs USING btree (id) | 印1:全件の後に有る |
| 索引 | customer_scores_pkey | CREATE UNIQUE INDEX customer_scores_pkey ON X.customer_scores USING btree (id) |  | CREATE UNIQUE INDEX customer_scores_pkey ON X.customer_scores USING btree (id) | 印1:全件の後に有る |
| 索引 | discord_channel_webhooks_pkey | CREATE UNIQUE INDEX discord_channel_webhooks_pkey ON X.discord_channel_webhooks USING btree (id) |  | CREATE UNIQUE INDEX discord_channel_webhooks_pkey ON X.discord_channel_webhooks USING btree (id) | 印1:全件の後に有る |
| 索引 | erp_sync_logs_pkey | CREATE UNIQUE INDEX erp_sync_logs_pkey ON X.erp_sync_logs USING btree (id) |  | CREATE UNIQUE INDEX erp_sync_logs_pkey ON X.erp_sync_logs USING btree (id) | 印1:全件の後に有る |
| 索引 | idx_archives_source | CREATE INDEX idx_archives_source ON X.archives USING btree (source_table, source_id) |  | CREATE INDEX idx_archives_source ON X.archives USING btree (source_table, source_id) | 印1:全件の後に有る |
| 索引 | idx_bots_status | CREATE INDEX idx_bots_status ON X.bots USING btree (status) |  |  | 印1:全件の後も無い |
| 索引 | idx_calendar_events_google_id | CREATE INDEX idx_calendar_events_google_id ON X.calendar_events USING btree (google_event_id) WHERE (google_event_id IS NOT NULL) |  | CREATE INDEX idx_calendar_events_google_id ON X.calendar_events USING btree (google_event_id) WHERE (google_event_id IS NOT NULL) | 印1:全件の後に有る |
| 索引 | idx_calendar_events_range | CREATE INDEX idx_calendar_events_range ON X.calendar_events USING btree (start_datetime, end_datetime) |  | CREATE INDEX idx_calendar_events_range ON X.calendar_events USING btree (start_datetime, end_datetime) | 印1:全件の後に有る |
| 索引 | idx_calendar_events_sync_origin | CREATE INDEX idx_calendar_events_sync_origin ON X.calendar_events USING btree (sync_origin_id) WHERE (sync_origin_id IS NOT NULL) |  | CREATE INDEX idx_calendar_events_sync_origin ON X.calendar_events USING btree (sync_origin_id) WHERE (sync_origin_id IS NOT NULL) | 印1:全件の後に有る |
| 索引 | idx_calendar_events_user_type | CREATE INDEX idx_calendar_events_user_type ON X.calendar_events USING btree (user_id, calendar_type) |  | CREATE INDEX idx_calendar_events_user_type ON X.calendar_events USING btree (user_id, calendar_type) | 印1:全件の後に有る |
| 索引 | idx_calendar_owner_settings_staff_id | CREATE INDEX idx_calendar_owner_settings_staff_id ON X.calendar_owner_settings USING btree (staff_id) |  |  | 印1:全件の後も無い |
| 索引 | idx_ccc_unique_channel_purpose | CREATE UNIQUE INDEX idx_ccc_unique_channel_purpose ON X.contact_contact_channels USING btree (contact_id, channel, COALESCE(purpose, ''::character varying)) |  | CREATE UNIQUE INDEX idx_ccc_unique_channel_purpose ON X.contact_contact_channels USING btree (contact_id, channel, COALESCE(purpose, ''::character varying)) | 印1:全件の後に有る |
| 索引 | idx_conv_logs_company_id | CREATE INDEX idx_conv_logs_company_id ON X.conversation_logs USING btree (company_id) |  | CREATE INDEX idx_conv_logs_company_id ON X.conversation_logs USING btree (company_id) | 印1:全件の後に有る |
| 索引 | idx_conv_logs_contact_id | CREATE INDEX idx_conv_logs_contact_id ON X.conversation_logs USING btree (contact_id) |  | CREATE INDEX idx_conv_logs_contact_id ON X.conversation_logs USING btree (contact_id) | 印1:全件の後に有る |
| 索引 | idx_conv_logs_deleted_at | CREATE INDEX idx_conv_logs_deleted_at ON X.conversation_logs USING btree (deleted_at) WHERE (deleted_at IS NOT NULL) |  | CREATE INDEX idx_conv_logs_deleted_at ON X.conversation_logs USING btree (deleted_at) WHERE (deleted_at IS NOT NULL) | 印1:全件の後に有る |
| 索引 | idx_conv_logs_occurred_at | CREATE INDEX idx_conv_logs_occurred_at ON X.conversation_logs USING btree (occurred_at DESC) |  | CREATE INDEX idx_conv_logs_occurred_at ON X.conversation_logs USING btree (occurred_at DESC) | 印1:全件の後に有る |
| 索引 | idx_conv_logs_tenant_id | CREATE INDEX idx_conv_logs_tenant_id ON X.conversation_logs USING btree (tenant_id) |  | CREATE INDEX idx_conv_logs_tenant_id ON X.conversation_logs USING btree (tenant_id) | 印1:全件の後に有る |
| 索引 | idx_customer_scores_tier | CREATE INDEX idx_customer_scores_tier ON X.customer_scores USING btree (tier) |  | CREATE INDEX idx_customer_scores_tier ON X.customer_scores USING btree (tier) | 印1:全件の後に有る |
| 索引 | idx_dcw_tenant | CREATE INDEX idx_dcw_tenant ON X.discord_channel_webhooks USING btree (tenant_id) |  | CREATE INDEX idx_dcw_tenant ON X.discord_channel_webhooks USING btree (tenant_id) | 印1:全件の後に有る |
| 索引 | idx_invoices_status | CREATE INDEX idx_invoices_status ON X.invoices USING btree (status) |  |  | 印1:全件の後も無い |
| 索引 | idx_la_lead_id | CREATE INDEX idx_la_lead_id ON X.lead_attachments USING btree (lead_id) |  | CREATE INDEX idx_la_lead_id ON X.lead_attachments USING btree (lead_id) | 印1:全件の後に有る |
| 索引 | idx_la_message_id | CREATE UNIQUE INDEX idx_la_message_id ON X.lead_attachments USING btree (message_id) |  | CREATE UNIQUE INDEX idx_la_message_id ON X.lead_attachments USING btree (message_id) | 印1:全件の後に有る |
| 索引 | idx_la_tenant_created | CREATE INDEX idx_la_tenant_created ON X.lead_attachments USING btree (tenant_id, created_at) |  | CREATE INDEX idx_la_tenant_created ON X.lead_attachments USING btree (tenant_id, created_at) | 印1:全件の後に有る |
| 索引 | idx_leads_assigned_to | CREATE INDEX idx_leads_assigned_to ON X.leads USING btree (assigned_to) |  |  | 印1:全件の後も無い |
| 索引 | idx_leads_channel_type | CREATE INDEX idx_leads_channel_type ON X.leads USING btree (channel_type) |  | CREATE INDEX idx_leads_channel_type ON X.leads USING btree (channel_type) | 印1:全件の後に有る |
| 索引 | idx_leads_discord_guild_channel_id | CREATE INDEX idx_leads_discord_guild_channel_id ON X.leads USING btree (tenant_id, discord_guild_channel_id) WHERE (discord_guild_channel_id IS NOT NULL) |  | CREATE INDEX idx_leads_discord_guild_channel_id ON X.leads USING btree (tenant_id, discord_guild_channel_id) WHERE (discord_guild_channel_id IS NOT NULL) | 印1:全件の後に有る |
| 索引 | idx_leads_discord_user_id | CREATE INDEX idx_leads_discord_user_id ON X.leads USING btree (tenant_id, discord_user_id) WHERE (discord_user_id IS NOT NULL) |  | CREATE INDEX idx_leads_discord_user_id ON X.leads USING btree (tenant_id, discord_user_id) WHERE (discord_user_id IS NOT NULL) | 印1:全件の後に有る |
| 索引 | idx_leads_initiative | CREATE INDEX idx_leads_initiative ON X.leads USING btree (initiative) WHERE (initiative IS NOT NULL) |  | CREATE INDEX idx_leads_initiative ON X.leads USING btree (initiative) WHERE (initiative IS NOT NULL) | 印1:全件の後に有る |
| 索引 | idx_leads_status | CREATE INDEX idx_leads_status ON X.leads USING btree (status) |  |  | 印1:全件の後も無い |
| 索引 | idx_message_labels_lead_id | CREATE INDEX idx_message_labels_lead_id ON X.message_labels USING btree (lead_id) |  | CREATE INDEX idx_message_labels_lead_id ON X.message_labels USING btree (lead_id) | 印1:全件の後に有る |
| 索引 | idx_message_labels_message_id | CREATE INDEX idx_message_labels_message_id ON X.message_labels USING btree (message_id) |  | CREATE INDEX idx_message_labels_message_id ON X.message_labels USING btree (message_id) | 印1:全件の後に有る |
| 索引 | idx_message_translations_message_id | CREATE INDEX idx_message_translations_message_id ON X.message_translations USING btree (message_id) |  | CREATE INDEX idx_message_translations_message_id ON X.message_translations USING btree (message_id) | 印1:全件の後に有る |
| 索引 | idx_meta_messages_discord | CREATE INDEX idx_meta_messages_discord ON X.meta_messages USING btree (tenant_id, platform, lead_id) WHERE ((platform)::text = 'discord'::text) |  | CREATE INDEX idx_meta_messages_discord ON X.meta_messages USING btree (tenant_id, platform, lead_id) WHERE ((platform)::text = 'discord'::text) | 印1:全件の後に有る |
| 索引 | idx_meta_messages_lead_created | CREATE INDEX idx_meta_messages_lead_created ON X.meta_messages USING btree (lead_id, created_at DESC) |  | CREATE INDEX idx_meta_messages_lead_created ON X.meta_messages USING btree (lead_id, created_at DESC) | 印1:全件の後に有る |
| 索引 | idx_meta_messages_lead_unread | CREATE INDEX idx_meta_messages_lead_unread ON X.meta_messages USING btree (lead_id) WHERE (((direction)::text = 'inbound'::text) AND (seen_at IS NULL)) |  | CREATE INDEX idx_meta_messages_lead_unread ON X.meta_messages USING btree (lead_id) WHERE (((direction)::text = 'inbound'::text) AND (seen_at IS NULL)) | 印1:全件の後に有る |
| 索引 | idx_meta_messages_tenant_page | CREATE INDEX idx_meta_messages_tenant_page ON X.meta_messages USING btree (tenant_id, page_id) WHERE (page_id IS NOT NULL) |  | CREATE INDEX idx_meta_messages_tenant_page ON X.meta_messages USING btree (tenant_id, page_id) WHERE (page_id IS NOT NULL) | 印1:全件の後に有る |
| 索引 | idx_mmr_meta_message_id | CREATE INDEX idx_mmr_meta_message_id ON X.meta_message_reactions USING btree (meta_message_id) |  | CREATE INDEX idx_mmr_meta_message_id ON X.meta_message_reactions USING btree (meta_message_id) | 印1:全件の後に有る |
| 索引 | idx_mmr_tenant | CREATE INDEX idx_mmr_tenant ON X.meta_message_reactions USING btree (tenant_id) |  | CREATE INDEX idx_mmr_tenant ON X.meta_message_reactions USING btree (tenant_id) | 印1:全件の後に有る |
| 索引 | idx_order_commissions_order | CREATE INDEX idx_order_commissions_order ON X.order_commissions USING btree (order_id) |  | CREATE INDEX idx_order_commissions_order ON X.order_commissions USING btree (order_id) | 印1:全件の後に有る |
| 索引 | idx_order_commissions_staff | CREATE INDEX idx_order_commissions_staff ON X.order_commissions USING btree (staff_id) |  | CREATE INDEX idx_order_commissions_staff ON X.order_commissions USING btree (staff_id) | 印1:全件の後に有る |
| 索引 | idx_order_commissions_tenant | CREATE INDEX idx_order_commissions_tenant ON X.order_commissions USING btree (tenant_id) |  | CREATE INDEX idx_order_commissions_tenant ON X.order_commissions USING btree (tenant_id) | 印1:全件の後に有る |
| 索引 | idx_order_commissions_tenant_calc | CREATE INDEX idx_order_commissions_tenant_calc ON X.order_commissions USING btree (tenant_id, calculated_at) |  | CREATE INDEX idx_order_commissions_tenant_calc ON X.order_commissions USING btree (tenant_id, calculated_at) | 印1:全件の後に有る |
| 索引 | idx_order_financials_created_at | CREATE INDEX idx_order_financials_created_at ON X.order_financials USING btree (created_at) |  | CREATE INDEX idx_order_financials_created_at ON X.order_financials USING btree (created_at) | 印1:全件の後に有る |
| 索引 | idx_order_financials_order | CREATE INDEX idx_order_financials_order ON X.order_financials USING btree (order_id) |  | CREATE INDEX idx_order_financials_order ON X.order_financials USING btree (order_id) | 印1:全件の後に有る |
| 索引 | idx_order_financials_tenant | CREATE INDEX idx_order_financials_tenant ON X.order_financials USING btree (tenant_id) |  | CREATE INDEX idx_order_financials_tenant ON X.order_financials USING btree (tenant_id) | 印1:全件の後に有る |
| 索引 | idx_order_purchase_details_order | CREATE INDEX idx_order_purchase_details_order ON X.order_purchase_details USING btree (order_id) |  | CREATE INDEX idx_order_purchase_details_order ON X.order_purchase_details USING btree (order_id) | 印1:全件の後に有る |
| 索引 | idx_order_purchase_details_status | CREATE INDEX idx_order_purchase_details_status ON X.order_purchase_details USING btree (purchase_status) |  | CREATE INDEX idx_order_purchase_details_status ON X.order_purchase_details USING btree (purchase_status) | 印1:全件の後に有る |
| 索引 | idx_order_purchase_details_tenant | CREATE INDEX idx_order_purchase_details_tenant ON X.order_purchase_details USING btree (tenant_id) |  | CREATE INDEX idx_order_purchase_details_tenant ON X.order_purchase_details USING btree (tenant_id) | 印1:全件の後に有る |
| 索引 | idx_order_purchase_details_tenant_supplier | CREATE INDEX idx_order_purchase_details_tenant_supplier ON X.order_purchase_details USING btree (tenant_id, supplier_name) |  | CREATE INDEX idx_order_purchase_details_tenant_supplier ON X.order_purchase_details USING btree (tenant_id, supplier_name) | 印1:全件の後に有る |
| 索引 | idx_order_shipping_details_carrier | CREATE INDEX idx_order_shipping_details_carrier ON X.order_shipping_details USING btree (carrier) |  | CREATE INDEX idx_order_shipping_details_carrier ON X.order_shipping_details USING btree (carrier) | 印1:全件の後に有る |
| 索引 | idx_order_shipping_details_order | CREATE INDEX idx_order_shipping_details_order ON X.order_shipping_details USING btree (order_id) |  | CREATE INDEX idx_order_shipping_details_order ON X.order_shipping_details USING btree (order_id) | 印1:全件の後に有る |
| 索引 | idx_order_shipping_details_tenant | CREATE INDEX idx_order_shipping_details_tenant ON X.order_shipping_details USING btree (tenant_id) |  | CREATE INDEX idx_order_shipping_details_tenant ON X.order_shipping_details USING btree (tenant_id) | 印1:全件の後に有る |
| 索引 | idx_order_shipping_details_tracking | CREATE INDEX idx_order_shipping_details_tracking ON X.order_shipping_details USING btree (tracking_number) |  | CREATE INDEX idx_order_shipping_details_tracking ON X.order_shipping_details USING btree (tracking_number) | 印1:全件の後に有る |
| 索引 | idx_outbound_drafts_tenant_lead | CREATE INDEX idx_outbound_drafts_tenant_lead ON X.outbound_translation_drafts USING btree (tenant_id, lead_id) |  | CREATE INDEX idx_outbound_drafts_tenant_lead ON X.outbound_translation_drafts USING btree (tenant_id, lead_id) | 印1:全件の後に有る |
| 索引 | idx_outbound_drafts_unconfirmed | CREATE INDEX idx_outbound_drafts_unconfirmed ON X.outbound_translation_drafts USING btree (tenant_id, confirmed_at) WHERE (confirmed_at IS NULL) |  | CREATE INDEX idx_outbound_drafts_unconfirmed ON X.outbound_translation_drafts USING btree (tenant_id, confirmed_at) WHERE (confirmed_at IS NULL) | 印1:全件の後に有る |
| 索引 | idx_paypal_disputes_invoice | CREATE INDEX idx_paypal_disputes_invoice ON X.paypal_disputes USING btree (invoice_id) |  | CREATE INDEX idx_paypal_disputes_invoice ON X.paypal_disputes USING btree (invoice_id) | 印1:全件の後に有る |
| 索引 | idx_po_status | CREATE INDEX idx_po_status ON X.purchase_orders USING btree (status) |  |  | 印1:全件の後も無い |
| 索引 | idx_po_supplier | CREATE INDEX idx_po_supplier ON X.purchase_orders USING btree (supplier_id) |  |  | 印1:全件の後も無い |
| 索引 | idx_poi_order_item_id | CREATE INDEX idx_poi_order_item_id ON X.purchase_order_items USING btree (order_item_id) |  | CREATE INDEX idx_poi_order_item_id ON X.purchase_order_items USING btree (order_item_id) | 印1:全件の後に有る |
| 索引 | idx_products_category | CREATE INDEX idx_products_category ON X.products USING btree (category) |  |  | 印1:全件の後も無い |
| 索引 | idx_products_status | CREATE INDEX idx_products_status ON X.products USING btree (status) |  |  | 印1:全件の後も無い |
| 索引 | idx_quotes_status | CREATE INDEX idx_quotes_status ON X.quotes USING btree (status) |  |  | 印1:全件の後も無い |
| 索引 | idx_shifts_date | CREATE INDEX idx_shifts_date ON X.shifts USING btree (shift_date) |  | CREATE INDEX idx_shifts_date ON X.shifts USING btree (shift_date) | 印1:全件の後に有る |
| 索引 | idx_shifts_user | CREATE INDEX idx_shifts_user ON X.shifts USING btree (user_id) |  | CREATE INDEX idx_shifts_user ON X.shifts USING btree (user_id) | 印1:全件の後に有る |
| 索引 | idx_shipping_rates_lookup | CREATE INDEX idx_shipping_rates_lookup ON X.shipping_rates USING btree (carrier, zone) |  |  | 印1:全件の後も無い |
| 索引 | idx_staff_phone | CREATE INDEX idx_staff_phone ON X.staff USING btree (phone) WHERE (phone IS NOT NULL) |  | CREATE INDEX idx_staff_phone ON X.staff USING btree (phone) WHERE (phone IS NOT NULL) | 印1:全件の後に有る |
| 索引 | idx_staff_reports_type | CREATE INDEX idx_staff_reports_type ON X.staff_reports USING btree (report_type) |  | CREATE INDEX idx_staff_reports_type ON X.staff_reports USING btree (report_type) | 印1:全件の後に有る |
| 索引 | idx_staff_reports_user | CREATE INDEX idx_staff_reports_user ON X.staff_reports USING btree (user_id) |  | CREATE INDEX idx_staff_reports_user ON X.staff_reports USING btree (user_id) | 印1:全件の後に有る |
| 索引 | idx_team_members_team | CREATE INDEX idx_team_members_team ON X.team_members USING btree (team_id) |  |  | 印1:全件の後も無い |
| 索引 | idx_team_members_user | CREATE INDEX idx_team_members_user ON X.team_members USING btree (user_id) |  |  | 印1:全件の後も無い |
| 索引 | idx_tenant_calibrations_latest | CREATE INDEX idx_tenant_calibrations_latest ON X.tenant_calibrations USING btree (tenant_id, calibrated_at DESC) |  | CREATE INDEX idx_tenant_calibrations_latest ON X.tenant_calibrations USING btree (tenant_id, calibrated_at DESC) | 印1:全件の後に有る |
| 索引 | idx_tenant_commission_settings_tenant | CREATE INDEX idx_tenant_commission_settings_tenant ON X.tenant_commission_settings USING btree (tenant_id) |  | CREATE INDEX idx_tenant_commission_settings_tenant ON X.tenant_commission_settings USING btree (tenant_id) | 印1:全件の後に有る |
| 索引 | idx_user_roles_user | CREATE INDEX idx_user_roles_user ON X.user_roles USING btree (user_id) |  |  | 印1:全件の後も無い |
| 索引 | lead_attachments_pkey | CREATE UNIQUE INDEX lead_attachments_pkey ON X.lead_attachments USING btree (id) |  | CREATE UNIQUE INDEX lead_attachments_pkey ON X.lead_attachments USING btree (id) | 印1:全件の後に有る |
| 索引 | leads_tenant_id_lead_code_key | CREATE UNIQUE INDEX leads_tenant_id_lead_code_key ON X.leads USING btree (tenant_id, lead_code) |  |  | 印1:全件の後も無い |
| 索引 | message_labels_pkey | CREATE UNIQUE INDEX message_labels_pkey ON X.message_labels USING btree (id) |  | CREATE UNIQUE INDEX message_labels_pkey ON X.message_labels USING btree (id) | 印1:全件の後に有る |
| 索引 | message_translations_pkey | CREATE UNIQUE INDEX message_translations_pkey ON X.message_translations USING btree (id) |  | CREATE UNIQUE INDEX message_translations_pkey ON X.message_translations USING btree (id) | 印1:全件の後に有る |
| 索引 | meta_message_reactions_pkey | CREATE UNIQUE INDEX meta_message_reactions_pkey ON X.meta_message_reactions USING btree (id) |  | CREATE UNIQUE INDEX meta_message_reactions_pkey ON X.meta_message_reactions USING btree (id) | 印1:全件の後に有る |
| 索引 | notification_channels_pkey | CREATE UNIQUE INDEX notification_channels_pkey ON X.notification_channels USING btree (id) |  | CREATE UNIQUE INDEX notification_channels_pkey ON X.notification_channels USING btree (id) | 印1:全件の後に有る |
| 索引 | notification_logs_pkey | CREATE UNIQUE INDEX notification_logs_pkey ON X.notification_logs USING btree (id) |  | CREATE UNIQUE INDEX notification_logs_pkey ON X.notification_logs USING btree (id) | 印1:全件の後に有る |
| 索引 | order_commissions_order_id_role_key | CREATE UNIQUE INDEX order_commissions_order_id_role_key ON X.order_commissions USING btree (order_id, role) |  | CREATE UNIQUE INDEX order_commissions_order_id_role_key ON X.order_commissions USING btree (order_id, role) | 印1:全件の後に有る |
| 索引 | order_commissions_pkey | CREATE UNIQUE INDEX order_commissions_pkey ON X.order_commissions USING btree (id) |  | CREATE UNIQUE INDEX order_commissions_pkey ON X.order_commissions USING btree (id) | 印1:全件の後に有る |
| 索引 | order_financials_order_id_key | CREATE UNIQUE INDEX order_financials_order_id_key ON X.order_financials USING btree (order_id) |  | CREATE UNIQUE INDEX order_financials_order_id_key ON X.order_financials USING btree (order_id) | 印1:全件の後に有る |
| 索引 | order_financials_pkey | CREATE UNIQUE INDEX order_financials_pkey ON X.order_financials USING btree (id) |  | CREATE UNIQUE INDEX order_financials_pkey ON X.order_financials USING btree (id) | 印1:全件の後に有る |
| 索引 | order_purchase_details_order_id_key | CREATE UNIQUE INDEX order_purchase_details_order_id_key ON X.order_purchase_details USING btree (order_id) |  | CREATE UNIQUE INDEX order_purchase_details_order_id_key ON X.order_purchase_details USING btree (order_id) | 印1:全件の後に有る |
| 索引 | order_purchase_details_pkey | CREATE UNIQUE INDEX order_purchase_details_pkey ON X.order_purchase_details USING btree (id) |  | CREATE UNIQUE INDEX order_purchase_details_pkey ON X.order_purchase_details USING btree (id) | 印1:全件の後に有る |
| 索引 | order_shipping_details_order_id_key | CREATE UNIQUE INDEX order_shipping_details_order_id_key ON X.order_shipping_details USING btree (order_id) |  | CREATE UNIQUE INDEX order_shipping_details_order_id_key ON X.order_shipping_details USING btree (order_id) | 印1:全件の後に有る |
| 索引 | order_shipping_details_pkey | CREATE UNIQUE INDEX order_shipping_details_pkey ON X.order_shipping_details USING btree (id) |  | CREATE UNIQUE INDEX order_shipping_details_pkey ON X.order_shipping_details USING btree (id) | 印1:全件の後に有る |
| 索引 | outbound_translation_drafts_pkey | CREATE UNIQUE INDEX outbound_translation_drafts_pkey ON X.outbound_translation_drafts USING btree (id) |  | CREATE UNIQUE INDEX outbound_translation_drafts_pkey ON X.outbound_translation_drafts USING btree (id) | 印1:全件の後に有る |
| 索引 | paypal_disputes_dispute_id_key | CREATE UNIQUE INDEX paypal_disputes_dispute_id_key ON X.paypal_disputes USING btree (dispute_id) |  | CREATE UNIQUE INDEX paypal_disputes_dispute_id_key ON X.paypal_disputes USING btree (dispute_id) | 印1:全件の後に有る |
| 索引 | paypal_disputes_pkey | CREATE UNIQUE INDEX paypal_disputes_pkey ON X.paypal_disputes USING btree (id) |  | CREATE UNIQUE INDEX paypal_disputes_pkey ON X.paypal_disputes USING btree (id) | 印1:全件の後に有る |
| 索引 | shifts_pkey | CREATE UNIQUE INDEX shifts_pkey ON X.shifts USING btree (id) |  | CREATE UNIQUE INDEX shifts_pkey ON X.shifts USING btree (id) | 印1:全件の後に有る |
| 索引 | shifts_tenant_id_user_id_shift_date_key | CREATE UNIQUE INDEX shifts_tenant_id_user_id_shift_date_key ON X.shifts USING btree (tenant_id, user_id, shift_date) |  | CREATE UNIQUE INDEX shifts_tenant_id_user_id_shift_date_key ON X.shifts USING btree (tenant_id, user_id, shift_date) | 印1:全件の後に有る |
| 索引 | staff_reports_pkey | CREATE UNIQUE INDEX staff_reports_pkey ON X.staff_reports USING btree (id) |  | CREATE UNIQUE INDEX staff_reports_pkey ON X.staff_reports USING btree (id) | 印1:全件の後に有る |
| 索引 | suppliers_pkey |  | CREATE UNIQUE INDEX suppliers_pkey ON X.suppliers USING btree (id) | CREATE UNIQUE INDEX suppliers_pkey ON X.suppliers USING btree (id) | 印2:残っている |
| 索引 | tenant_calibrations_pkey | CREATE UNIQUE INDEX tenant_calibrations_pkey ON X.tenant_calibrations USING btree (id) |  | CREATE UNIQUE INDEX tenant_calibrations_pkey ON X.tenant_calibrations USING btree (id) | 印1:全件の後に有る |
| 索引 | tenant_commission_settings_pkey | CREATE UNIQUE INDEX tenant_commission_settings_pkey ON X.tenant_commission_settings USING btree (id) |  | CREATE UNIQUE INDEX tenant_commission_settings_pkey ON X.tenant_commission_settings USING btree (id) | 印1:全件の後に有る |
| 索引 | tenant_commission_settings_tenant_id_key | CREATE UNIQUE INDEX tenant_commission_settings_tenant_id_key ON X.tenant_commission_settings USING btree (tenant_id) |  | CREATE UNIQUE INDEX tenant_commission_settings_tenant_id_key ON X.tenant_commission_settings USING btree (tenant_id) | 印1:全件の後に有る |
| 索引 | uq_calendar_events_google_event_id | CREATE UNIQUE INDEX uq_calendar_events_google_event_id ON X.calendar_events USING btree (google_event_id) WHERE (google_event_id IS NOT NULL) |  | CREATE UNIQUE INDEX uq_calendar_events_google_event_id ON X.calendar_events USING btree (google_event_id) WHERE (google_event_id IS NOT NULL) | 印1:全件の後に有る |
| 索引 | uq_customer_scores_lead_id | CREATE UNIQUE INDEX uq_customer_scores_lead_id ON X.customer_scores USING btree (lead_id) |  | CREATE UNIQUE INDEX uq_customer_scores_lead_id ON X.customer_scores USING btree (lead_id) | 印1:全件の後に有る |
| 索引 | uq_discord_channel_webhooks_channel | CREATE UNIQUE INDEX uq_discord_channel_webhooks_channel ON X.discord_channel_webhooks USING btree (channel_id) |  | CREATE UNIQUE INDEX uq_discord_channel_webhooks_channel ON X.discord_channel_webhooks USING btree (channel_id) | 印1:全件の後に有る |
| 索引 | uq_message_translations | CREATE UNIQUE INDEX uq_message_translations ON X.message_translations USING btree (message_id, target_language) |  | CREATE UNIQUE INDEX uq_message_translations ON X.message_translations USING btree (message_id, target_language) | 印1:全件の後に有る |
| 索引 | uq_notification_channels_blueprint_key | CREATE UNIQUE INDEX uq_notification_channels_blueprint_key ON X.notification_channels USING btree (blueprint_key) WHERE (blueprint_key IS NOT NULL) |  | CREATE UNIQUE INDEX uq_notification_channels_blueprint_key ON X.notification_channels USING btree (blueprint_key) WHERE (blueprint_key IS NOT NULL) | 印1:全件の後に有る |
| 索引 | uq_order_financials_tenant_order | CREATE UNIQUE INDEX uq_order_financials_tenant_order ON X.order_financials USING btree (tenant_id, order_id) |  | CREATE UNIQUE INDEX uq_order_financials_tenant_order ON X.order_financials USING btree (tenant_id, order_id) | 印1:全件の後に有る |
| 索引 | uq_order_purchase_details_tenant_order | CREATE UNIQUE INDEX uq_order_purchase_details_tenant_order ON X.order_purchase_details USING btree (tenant_id, order_id) |  | CREATE UNIQUE INDEX uq_order_purchase_details_tenant_order ON X.order_purchase_details USING btree (tenant_id, order_id) | 印1:全件の後に有る |
| 索引 | uq_order_shipping_details_tenant_order | CREATE UNIQUE INDEX uq_order_shipping_details_tenant_order ON X.order_shipping_details USING btree (tenant_id, order_id) |  | CREATE UNIQUE INDEX uq_order_shipping_details_tenant_order ON X.order_shipping_details USING btree (tenant_id, order_id) | 印1:全件の後に有る |
| 索引 | uq_reaction_per_user_emoji | CREATE UNIQUE INDEX uq_reaction_per_user_emoji ON X.meta_message_reactions USING btree (meta_message_id, emoji_name, emoji_id, reactor_discord_user_id) |  | CREATE UNIQUE INDEX uq_reaction_per_user_emoji ON X.meta_message_reactions USING btree (meta_message_id, emoji_name, emoji_id, reactor_discord_user_id) | 印1:全件の後に有る |
| 索引 | user_badges_pkey | CREATE UNIQUE INDEX user_badges_pkey ON X.user_badges USING btree (id) |  |  | 印1:全件の後も無い |
| 索引 | user_badges_tenant_id_user_id_badge_id_key | CREATE UNIQUE INDEX user_badges_tenant_id_user_id_badge_id_key ON X.user_badges USING btree (tenant_id, user_id, badge_id) |  |  | 印1:全件の後も無い |
| 制約 | archives_pkey (表 archives) | archives_pkey\|p\|PRIMARY KEY (id) |  | archives_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | badge_definitions_pkey (表 badge_definitions) | badge_definitions_pkey\|p\|PRIMARY KEY (id) |  |  | 印1:全件の後も無い |
| 制約 | bots_owner_staff_id_fkey (表 bots) |  | bots_owner_staff_id_fkey\|f\|FOREIGN KEY (owner_staff_id) REFERENCES users(id) | bots_owner_staff_id_fkey\|f\|FOREIGN KEY (owner_staff_id) REFERENCES users(id) | 印2:残っている |
| 制約 | fk_bots_owner_staff_id_user (表 bots) | fk_bots_owner_staff_id_user\|f\|FOREIGN KEY (owner_staff_id) REFERENCES users(id) |  | fk_bots_owner_staff_id_user\|f\|FOREIGN KEY (owner_staff_id) REFERENCES users(id) | 印1:全件の後に有る |
| 制約 | buddy_feedbacks_pair_id_fkey (表 buddy_feedbacks) | buddy_feedbacks_pair_id_fkey\|f\|FOREIGN KEY (pair_id) REFERENCES X.buddy_pairs(id) ON DELETE CASCADE |  |  | 印1:全件の後も無い |
| 制約 | buddy_feedbacks_pkey (表 buddy_feedbacks) | buddy_feedbacks_pkey\|p\|PRIMARY KEY (id) |  |  | 印1:全件の後も無い |
| 制約 | buddy_pairs_pkey (表 buddy_pairs) | buddy_pairs_pkey\|p\|PRIMARY KEY (id) |  |  | 印1:全件の後も無い |
| 制約 | buddy_pairs_tenant_id_coach_user_id_mentee_user_id_key (表 buddy_pairs) | buddy_pairs_tenant_id_coach_user_id_mentee_user_id_key\|u\|UNIQUE (tenant_id, coach_user_id, mentee_user_id) |  |  | 印1:全件の後も無い |
| 制約 | calendar_events_calendar_type_check (表 calendar_events) | calendar_events_calendar_type_check\|c\|CHECK (((calendar_type)::text = ANY ((ARRAY['shared'::character varying, 'personal'::character varying])::text[]))) |  | calendar_events_calendar_type_check\|c\|CHECK (((calendar_type)::text = ANY ((ARRAY['shared'::character varying, 'personal'::character varying])::text[]))) | 印1:全件の後に有る |
| 制約 | calendar_events_cancelled_exception_check (表 calendar_events) | calendar_events_cancelled_exception_check\|c\|CHECK (((NOT is_cancelled) OR (recurring_event_id IS NOT NULL))) |  | calendar_events_cancelled_exception_check\|c\|CHECK (((NOT is_cancelled) OR (recurring_event_id IS NOT NULL))) | 印1:全件の後に有る |
| 制約 | calendar_events_category_check (表 calendar_events) | calendar_events_category_check\|c\|CHECK (((category)::text = ANY ((ARRAY['meeting'::character varying, 'personal'::character varying, 'procurement'::character varying, 'shipping'::character varying, 'billing'::character varying, 'release'::character varying, 'holiday'::character varying])::text[]))) |  |  | 印1:全件の後も無い |
| 制約 | calendar_events_created_by_user_id_fkey (表 calendar_events) | calendar_events_created_by_user_id_fkey\|f\|FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL |  | calendar_events_created_by_user_id_fkey\|f\|FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL | 印1:全件の後に有る |
| 制約 | calendar_events_exception_pair_check (表 calendar_events) | calendar_events_exception_pair_check\|c\|CHECK (((recurring_event_id IS NULL) = (original_start_datetime IS NULL))) |  | calendar_events_exception_pair_check\|c\|CHECK (((recurring_event_id IS NULL) = (original_start_datetime IS NULL))) | 印1:全件の後に有る |
| 制約 | calendar_events_pkey (表 calendar_events) | calendar_events_pkey\|p\|PRIMARY KEY (id) |  | calendar_events_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | calendar_events_recurrence_role_check (表 calendar_events) | calendar_events_recurrence_role_check\|c\|CHECK ((NOT ((recurrence_rule IS NOT NULL) AND (recurring_event_id IS NOT NULL)))) |  | calendar_events_recurrence_role_check\|c\|CHECK ((NOT ((recurrence_rule IS NOT NULL) AND (recurring_event_id IS NOT NULL)))) | 印1:全件の後に有る |
| 制約 | calendar_events_recurrence_rule_format_check (表 calendar_events) | calendar_events_recurrence_rule_format_check\|c\|CHECK ((recurrence_rule ~ '^FREQ=(DAILY\|WEEKLY\|MONTHLY\|YEARLY)(;[A-Z]+=[A-Z0-9,+-]+)*$'::text)) |  | calendar_events_recurrence_rule_format_check\|c\|CHECK ((recurrence_rule ~ '^FREQ=(DAILY\|WEEKLY\|MONTHLY\|YEARLY)(;[A-Z]+=[A-Z0-9,+-]+)*$'::text)) | 印1:全件の後に有る |
| 制約 | calendar_events_recurring_event_id_fkey (表 calendar_events) | calendar_events_recurring_event_id_fkey\|f\|FOREIGN KEY (recurring_event_id) REFERENCES X.calendar_events(id) ON DELETE CASCADE |  | calendar_events_recurring_event_id_fkey\|f\|FOREIGN KEY (recurring_event_id) REFERENCES X.calendar_events(id) ON DELETE CASCADE | 印1:全件の後に有る |
| 制約 | calendar_events_source_check (表 calendar_events) | calendar_events_source_check\|c\|CHECK (((source)::text = ANY ((ARRAY['app'::character varying, 'google'::character varying])::text[]))) |  | calendar_events_source_check\|c\|CHECK (((source)::text = ANY ((ARRAY['app'::character varying, 'google'::character varying])::text[]))) | 印1:全件の後に有る |
| 制約 | calendar_events_sync_status_check (表 calendar_events) | calendar_events_sync_status_check\|c\|CHECK (((sync_status)::text = ANY ((ARRAY['synced'::character varying, 'pending'::character varying, 'failed'::character varying])::text[]))) |  | calendar_events_sync_status_check\|c\|CHECK (((sync_status)::text = ANY ((ARRAY['synced'::character varying, 'pending'::character varying, 'failed'::character varying])::text[]))) | 印1:全件の後に有る |
| 制約 | calendar_events_user_id_fkey (表 calendar_events) | calendar_events_user_id_fkey\|f\|FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL |  | calendar_events_user_id_fkey\|f\|FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL | 印1:全件の後に有る |
| 制約 | calendar_owner_settings_pkey (表 calendar_owner_settings) | calendar_owner_settings_pkey\|p\|PRIMARY KEY (staff_id) |  |  | 印1:全件の後も無い |
| 制約 | calendar_owner_settings_share_mode_check (表 calendar_owner_settings) | calendar_owner_settings_share_mode_check\|c\|CHECK (((share_mode)::text = ANY ((ARRAY['self'::character varying, 'view'::character varying, 'edit'::character varying])::text[]))) |  |  | 印1:全件の後も無い |
| 制約 | fk_calendar_owner_settings_staff_id_user (表 calendar_owner_settings) | fk_calendar_owner_settings_staff_id_user\|f\|FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE CASCADE |  |  | 印1:全件の後も無い |
| 制約 | close_reasons_type_check (表 close_reasons) | close_reasons_type_check\|c\|CHECK (((type)::text = ANY ((ARRAY['won'::character varying, 'lost'::character varying])::text[]))) |  |  | 印1:全件の後も無い |
| 制約 | companies_lead_id_fkey (表 companies) | companies_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  |  | 印1:全件の後も無い |
| 制約 | fk_companies_lead (表 companies) |  | fk_companies_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) | fk_companies_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) | 印2:残っている |
| 制約 | contacts_lead_id_fkey (表 contacts) | contacts_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  |  | 印1:全件の後も無い |
| 制約 | fk_contacts_lead (表 contacts) |  | fk_contacts_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) | fk_contacts_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) | 印2:残っている |
| 制約 | conversation_logs_direction_check (表 conversation_logs) | conversation_logs_direction_check\|c\|CHECK (((direction)::text = ANY ((ARRAY['inbound'::character varying, 'outbound'::character varying])::text[]))) |  | conversation_logs_direction_check\|c\|CHECK (((direction)::text = ANY ((ARRAY['inbound'::character varying, 'outbound'::character varying])::text[]))) | 印1:全件の後に有る |
| 制約 | conversation_logs_external_message_id_key (表 conversation_logs) | conversation_logs_external_message_id_key\|u\|UNIQUE (external_message_id) |  | conversation_logs_external_message_id_key\|u\|UNIQUE (external_message_id) | 印1:全件の後に有る |
| 制約 | conversation_logs_pkey (表 conversation_logs) | conversation_logs_pkey\|p\|PRIMARY KEY (id) |  | conversation_logs_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | fk_conversation_logs_lead (表 conversation_logs) | fk_conversation_logs_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) ON UPDATE RESTRICT ON DELETE RESTRICT |  | fk_conversation_logs_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) ON UPDATE RESTRICT ON DELETE RESTRICT | 印1:全件の後に有る |
| 制約 | customer_scores_confidence_check (表 customer_scores) | customer_scores_confidence_check\|c\|CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))) |  | customer_scores_confidence_check\|c\|CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))) | 印1:全件の後に有る |
| 制約 | customer_scores_override_score_check (表 customer_scores) | customer_scores_override_score_check\|c\|CHECK (((override_score IS NULL) OR ((override_score >= (0)::numeric) AND (override_score <= (1)::numeric)))) |  | customer_scores_override_score_check\|c\|CHECK (((override_score IS NULL) OR ((override_score >= (0)::numeric) AND (override_score <= (1)::numeric)))) | 印1:全件の後に有る |
| 制約 | customer_scores_pkey (表 customer_scores) | customer_scores_pkey\|p\|PRIMARY KEY (id) |  | customer_scores_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | customer_scores_score_check (表 customer_scores) | customer_scores_score_check\|c\|CHECK (((score >= (0)::numeric) AND (score <= (1)::numeric))) |  | customer_scores_score_check\|c\|CHECK (((score >= (0)::numeric) AND (score <= (1)::numeric))) | 印1:全件の後に有る |
| 制約 | customer_scores_tier_check (表 customer_scores) | customer_scores_tier_check\|c\|CHECK (((tier)::text = ANY ((ARRAY['要観察'::character varying, '有望'::character varying, '最有望'::character varying])::text[]))) |  | customer_scores_tier_check\|c\|CHECK (((tier)::text = ANY ((ARRAY['要観察'::character varying, '有望'::character varying, '最有望'::character varying])::text[]))) | 印1:全件の後に有る |
| 制約 | deal_close_reasons_lead_id_fkey (表 deal_close_reasons) |  | deal_close_reasons_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) | deal_close_reasons_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) | 印2:残っている |
| 制約 | fk_deal_close_reasons_lead (表 deal_close_reasons) | fk_deal_close_reasons_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  | fk_deal_close_reasons_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) | 印1:全件の後に有る |
| 制約 | discord_channel_webhooks_pkey (表 discord_channel_webhooks) | discord_channel_webhooks_pkey\|p\|PRIMARY KEY (id) |  | discord_channel_webhooks_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | uq_discord_channel_webhooks_channel (表 discord_channel_webhooks) | uq_discord_channel_webhooks_channel\|u\|UNIQUE (channel_id) |  | uq_discord_channel_webhooks_channel\|u\|UNIQUE (channel_id) | 印1:全件の後に有る |
| 制約 | erp_sync_logs_pkey (表 erp_sync_logs) | erp_sync_logs_pkey\|p\|PRIMARY KEY (id) |  | erp_sync_logs_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | goals_kpi_type_check (表 goals) | goals_kpi_type_check\|c\|CHECK (((kpi_type)::text = ANY ((ARRAY['revenue'::character varying, 'deal_count'::character varying, 'close_rate'::character varying, 'lead_count'::character varying, 'conversion_rate'::character varying, 'won_count'::character varying, 'gross_profit'::character varying])::text[]))) | goals_kpi_type_check\|c\|CHECK (((kpi_type)::text = ANY ((ARRAY['revenue'::character varying, 'deal_count'::character varying, 'close_rate'::character varying, 'lead_count'::character varying, 'conversion_rate'::character varying])::text[]))) | goals_kpi_type_check\|c\|CHECK (((kpi_type)::text = ANY ((ARRAY['revenue'::character varying, 'deal_count'::character varying, 'close_rate'::character varying, 'lead_count'::character varying, 'conversion_rate'::character varying, 'won_count'::character varying, 'gross_profit'::character varying])::text[]))) | 印3:本番と同じになった |
| 制約 | invoice_items_product_id_fkey (表 invoice_items) |  | invoice_items_product_id_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) |  | 印2:消えた |
| 制約 | invoice_items_product_id_public_fkey (表 invoice_items) | invoice_items_product_id_public_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT |  | invoice_items_product_id_public_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT | 印1:全件の後に有る |
| 制約 | lead_attachments_lead_id_fkey (表 lead_attachments) | lead_attachments_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) ON DELETE CASCADE |  | lead_attachments_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) ON DELETE CASCADE | 印1:全件の後に有る |
| 制約 | lead_attachments_pkey (表 lead_attachments) | lead_attachments_pkey\|p\|PRIMARY KEY (id) |  | lead_attachments_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | leads_initiative_check (表 leads) | leads_initiative_check\|c\|CHECK (((initiative IS NULL) OR ((initiative)::text = ANY ((ARRAY['outbound'::character varying, 'inbound'::character varying])::text[])))) |  |  | 印1:全件の後も無い |
| 制約 | leads_tenant_id_lead_code_key (表 leads) | leads_tenant_id_lead_code_key\|u\|UNIQUE (tenant_id, lead_code) |  |  | 印1:全件の後も無い |
| 制約 | message_labels_confidence_check (表 message_labels) | message_labels_confidence_check\|c\|CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))) |  | message_labels_confidence_check\|c\|CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))) | 印1:全件の後に有る |
| 制約 | message_labels_direction_check (表 message_labels) | message_labels_direction_check\|c\|CHECK (((direction)::text = ANY ((ARRAY['inbound'::character varying, 'outbound'::character varying])::text[]))) |  | message_labels_direction_check\|c\|CHECK (((direction)::text = ANY ((ARRAY['inbound'::character varying, 'outbound'::character varying])::text[]))) | 印1:全件の後に有る |
| 制約 | message_labels_label_check (表 message_labels) | message_labels_label_check\|c\|CHECK (((label)::text = ANY ((ARRAY['price_focus'::character varying, 'substance_talk'::character varying, 'self_disclosure'::character varying, 'early_purchase_signal'::character varying, 'other'::character varying])::text[]))) |  | message_labels_label_check\|c\|CHECK (((label)::text = ANY ((ARRAY['price_focus'::character varying, 'substance_talk'::character varying, 'self_disclosure'::character varying, 'early_purchase_signal'::character varying, 'other'::character varying])::text[]))) | 印1:全件の後に有る |
| 制約 | message_labels_pkey (表 message_labels) | message_labels_pkey\|p\|PRIMARY KEY (id) |  | message_labels_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | message_labels_source_check (表 message_labels) | message_labels_source_check\|c\|CHECK (((source)::text = ANY ((ARRAY['rule'::character varying, 'llm'::character varying, 'human'::character varying])::text[]))) |  | message_labels_source_check\|c\|CHECK (((source)::text = ANY ((ARRAY['rule'::character varying, 'llm'::character varying, 'human'::character varying])::text[]))) | 印1:全件の後に有る |
| 制約 | message_translations_pkey (表 message_translations) | message_translations_pkey\|p\|PRIMARY KEY (id) |  | message_translations_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | uq_message_translations (表 message_translations) | uq_message_translations\|u\|UNIQUE (message_id, target_language) |  | uq_message_translations\|u\|UNIQUE (message_id, target_language) | 印1:全件の後に有る |
| 制約 | meta_message_reactions_meta_message_id_fkey (表 meta_message_reactions) | meta_message_reactions_meta_message_id_fkey\|f\|FOREIGN KEY (meta_message_id) REFERENCES X.meta_messages(id) ON DELETE CASCADE |  | meta_message_reactions_meta_message_id_fkey\|f\|FOREIGN KEY (meta_message_id) REFERENCES X.meta_messages(id) ON DELETE CASCADE | 印1:全件の後に有る |
| 制約 | meta_message_reactions_pkey (表 meta_message_reactions) | meta_message_reactions_pkey\|p\|PRIMARY KEY (id) |  | meta_message_reactions_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | uq_reaction_per_user_emoji (表 meta_message_reactions) | uq_reaction_per_user_emoji\|u\|UNIQUE (meta_message_id, emoji_name, emoji_id, reactor_discord_user_id) |  | uq_reaction_per_user_emoji\|u\|UNIQUE (meta_message_id, emoji_name, emoji_id, reactor_discord_user_id) | 印1:全件の後に有る |
| 制約 | fk_meta_messages_seen_by_staff_id_user (表 meta_messages) | fk_meta_messages_seen_by_staff_id_user\|f\|FOREIGN KEY (seen_by_staff_id) REFERENCES users(id) ON DELETE SET NULL |  | fk_meta_messages_seen_by_staff_id_user\|f\|FOREIGN KEY (seen_by_staff_id) REFERENCES users(id) ON DELETE SET NULL | 印1:全件の後に有る |
| 制約 | fk_meta_messages_sent_by_staff_id_user (表 meta_messages) | fk_meta_messages_sent_by_staff_id_user\|f\|FOREIGN KEY (sent_by_staff_id) REFERENCES users(id) ON DELETE SET NULL |  | fk_meta_messages_sent_by_staff_id_user\|f\|FOREIGN KEY (sent_by_staff_id) REFERENCES users(id) ON DELETE SET NULL | 印1:全件の後に有る |
| 制約 | notification_channels_pkey (表 notification_channels) | notification_channels_pkey\|p\|PRIMARY KEY (id) |  | notification_channels_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | notification_logs_channel_id_fkey (表 notification_logs) | notification_logs_channel_id_fkey\|f\|FOREIGN KEY (channel_id) REFERENCES X.notification_channels(id) |  | notification_logs_channel_id_fkey\|f\|FOREIGN KEY (channel_id) REFERENCES X.notification_channels(id) | 印1:全件の後に有る |
| 制約 | notification_logs_pkey (表 notification_logs) | notification_logs_pkey\|p\|PRIMARY KEY (id) |  | notification_logs_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | fk_order_commissions_staff_id_user (表 order_commissions) | fk_order_commissions_staff_id_user\|f\|FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE SET NULL |  | fk_order_commissions_staff_id_user\|f\|FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE SET NULL | 印1:全件の後に有る |
| 制約 | order_commissions_order_id_fkey (表 order_commissions) | order_commissions_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE |  | order_commissions_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE | 印1:全件の後に有る |
| 制約 | order_commissions_order_id_role_key (表 order_commissions) | order_commissions_order_id_role_key\|u\|UNIQUE (order_id, role) |  | order_commissions_order_id_role_key\|u\|UNIQUE (order_id, role) | 印1:全件の後に有る |
| 制約 | order_commissions_pkey (表 order_commissions) | order_commissions_pkey\|p\|PRIMARY KEY (id) |  | order_commissions_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | order_commissions_role_check (表 order_commissions) | order_commissions_role_check\|c\|CHECK ((role = ANY (ARRAY['sales'::text, 'order'::text, 'ship'::text, 'purchase'::text, 'trouble'::text]))) |  | order_commissions_role_check\|c\|CHECK ((role = ANY (ARRAY['sales'::text, 'order'::text, 'ship'::text, 'purchase'::text, 'trouble'::text]))) | 印1:全件の後に有る |
| 制約 | order_financials_order_id_fkey (表 order_financials) | order_financials_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE |  | order_financials_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE | 印1:全件の後に有る |
| 制約 | order_financials_order_id_key (表 order_financials) | order_financials_order_id_key\|u\|UNIQUE (order_id) |  | order_financials_order_id_key\|u\|UNIQUE (order_id) | 印1:全件の後に有る |
| 制約 | order_financials_pkey (表 order_financials) | order_financials_pkey\|p\|PRIMARY KEY (id) |  | order_financials_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | order_purchase_details_order_id_fkey (表 order_purchase_details) | order_purchase_details_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE |  | order_purchase_details_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE | 印1:全件の後に有る |
| 制約 | order_purchase_details_order_id_key (表 order_purchase_details) | order_purchase_details_order_id_key\|u\|UNIQUE (order_id) |  | order_purchase_details_order_id_key\|u\|UNIQUE (order_id) | 印1:全件の後に有る |
| 制約 | order_purchase_details_pkey (表 order_purchase_details) | order_purchase_details_pkey\|p\|PRIMARY KEY (id) |  | order_purchase_details_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | order_purchase_details_purchase_status_check (表 order_purchase_details) | order_purchase_details_purchase_status_check\|c\|CHECK ((purchase_status = ANY (ARRAY[''::text, 'confirmed'::text]))) |  | order_purchase_details_purchase_status_check\|c\|CHECK ((purchase_status = ANY (ARRAY[''::text, 'confirmed'::text]))) | 印1:全件の後に有る |
| 制約 | order_shipping_details_address_type_check (表 order_shipping_details) | order_shipping_details_address_type_check\|c\|CHECK (((address_type IS NULL) OR ((address_type)::text = ANY ((ARRAY['RESIDENTIAL'::character varying, 'BUSINESS'::character varying])::text[])))) |  | order_shipping_details_address_type_check\|c\|CHECK (((address_type IS NULL) OR ((address_type)::text = ANY ((ARRAY['RESIDENTIAL'::character varying, 'BUSINESS'::character varying])::text[])))) | 印1:全件の後に有る |
| 制約 | order_shipping_details_carrier_check (表 order_shipping_details) | order_shipping_details_carrier_check\|c\|CHECK (((carrier IS NULL) OR ((carrier)::text = ANY ((ARRAY['elogi'::character varying, 'fedex'::character varying, 'dhl'::character varying, 'yamato'::character varying, 'other'::character varying])::text[])))) |  | order_shipping_details_carrier_check\|c\|CHECK (((carrier IS NULL) OR ((carrier)::text = ANY ((ARRAY['elogi'::character varying, 'fedex'::character varying, 'dhl'::character varying, 'yamato'::character varying, 'other'::character varying])::text[])))) | 印1:全件の後に有る |
| 制約 | order_shipping_details_order_id_fkey (表 order_shipping_details) | order_shipping_details_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE |  | order_shipping_details_order_id_fkey\|f\|FOREIGN KEY (order_id) REFERENCES X.orders(id) ON DELETE CASCADE | 印1:全件の後に有る |
| 制約 | order_shipping_details_order_id_key (表 order_shipping_details) | order_shipping_details_order_id_key\|u\|UNIQUE (order_id) |  | order_shipping_details_order_id_key\|u\|UNIQUE (order_id) | 印1:全件の後に有る |
| 制約 | order_shipping_details_pkey (表 order_shipping_details) | order_shipping_details_pkey\|p\|PRIMARY KEY (id) |  | order_shipping_details_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | fk_orders_invoice (表 orders) | fk_orders_invoice\|f\|FOREIGN KEY (invoice_id) REFERENCES X.invoices(id) |  |  | 印1:全件の後も無い |
| 制約 | outbound_translation_drafts_pkey (表 outbound_translation_drafts) | outbound_translation_drafts_pkey\|p\|PRIMARY KEY (id) |  | outbound_translation_drafts_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | paypal_disputes_dispute_id_key (表 paypal_disputes) | paypal_disputes_dispute_id_key\|u\|UNIQUE (dispute_id) |  | paypal_disputes_dispute_id_key\|u\|UNIQUE (dispute_id) | 印1:全件の後に有る |
| 制約 | paypal_disputes_invoice_id_fkey (表 paypal_disputes) | paypal_disputes_invoice_id_fkey\|f\|FOREIGN KEY (invoice_id) REFERENCES X.invoices(id) ON DELETE SET NULL |  | paypal_disputes_invoice_id_fkey\|f\|FOREIGN KEY (invoice_id) REFERENCES X.invoices(id) ON DELETE SET NULL | 印1:全件の後に有る |
| 制約 | paypal_disputes_pkey (表 paypal_disputes) | paypal_disputes_pkey\|p\|PRIMARY KEY (id) |  | paypal_disputes_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | fk_products_supplier_default (表 products) |  | fk_products_supplier_default\|f\|FOREIGN KEY (supplier_default_id) REFERENCES X.suppliers(id) | fk_products_supplier_default\|f\|FOREIGN KEY (supplier_default_id) REFERENCES suppliers(id) | 印2:残っている |
| 制約 | products_supplier_default_id_fkey (表 products) | products_supplier_default_id_fkey\|f\|FOREIGN KEY (supplier_default_id) REFERENCES suppliers(id) |  |  | 印1:全件の後も無い |
| 制約 | fk_poi_order_item (表 purchase_order_items) | fk_poi_order_item\|f\|FOREIGN KEY (order_item_id) REFERENCES X.order_items(id) |  | fk_poi_order_item\|f\|FOREIGN KEY (order_item_id) REFERENCES X.order_items(id) | 印1:全件の後に有る |
| 制約 | purchase_order_items_order_item_id_fkey (表 purchase_order_items) |  | purchase_order_items_order_item_id_fkey\|f\|FOREIGN KEY (order_item_id) REFERENCES X.order_items(id) | purchase_order_items_order_item_id_fkey\|f\|FOREIGN KEY (order_item_id) REFERENCES X.order_items(id) | 印2:残っている |
| 制約 | purchase_order_items_product_id_fkey (表 purchase_order_items) |  | purchase_order_items_product_id_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) |  | 印2:消えた |
| 制約 | purchase_order_items_product_id_public_fkey (表 purchase_order_items) | purchase_order_items_product_id_public_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT |  | purchase_order_items_product_id_public_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT | 印1:全件の後に有る |
| 制約 | purchase_orders_supplier_id_fkey (表 purchase_orders) | purchase_orders_supplier_id_fkey\|f\|FOREIGN KEY (supplier_id) REFERENCES suppliers(id) | purchase_orders_supplier_id_fkey\|f\|FOREIGN KEY (supplier_id) REFERENCES X.suppliers(id) | purchase_orders_supplier_id_fkey\|f\|FOREIGN KEY (supplier_id) REFERENCES suppliers(id) | 印3:本番と同じになった |
| 制約 | quote_items_product_id_fkey (表 quote_items) |  | quote_items_product_id_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) |  | 印2:消えた |
| 制約 | quote_items_product_id_public_fkey (表 quote_items) | quote_items_product_id_public_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT |  | quote_items_product_id_public_fkey\|f\|FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT | 印1:全件の後に有る |
| 制約 | fk_quotes_lead (表 quotes) | fk_quotes_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) |  | fk_quotes_lead\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) | 印1:全件の後に有る |
| 制約 | quotes_lead_id_fkey (表 quotes) |  | quotes_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) | quotes_lead_id_fkey\|f\|FOREIGN KEY (lead_id) REFERENCES X.leads(id) | 印2:残っている |
| 制約 | shifts_pkey (表 shifts) | shifts_pkey\|p\|PRIMARY KEY (id) |  | shifts_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | shifts_tenant_id_user_id_shift_date_key (表 shifts) | shifts_tenant_id_user_id_shift_date_key\|u\|UNIQUE (tenant_id, user_id, shift_date) |  | shifts_tenant_id_user_id_shift_date_key\|u\|UNIQUE (tenant_id, user_id, shift_date) | 印1:全件の後に有る |
| 制約 | staff_reports_pkey (表 staff_reports) | staff_reports_pkey\|p\|PRIMARY KEY (id) |  | staff_reports_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | suppliers_pkey (表 suppliers) |  | suppliers_pkey\|p\|PRIMARY KEY (id) | suppliers_pkey\|p\|PRIMARY KEY (id) | 印2:残っている |
| 制約 | tenant_calibrations_pkey (表 tenant_calibrations) | tenant_calibrations_pkey\|p\|PRIMARY KEY (id) |  | tenant_calibrations_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | tenant_commission_settings_pkey (表 tenant_commission_settings) | tenant_commission_settings_pkey\|p\|PRIMARY KEY (id) |  | tenant_commission_settings_pkey\|p\|PRIMARY KEY (id) | 印1:全件の後に有る |
| 制約 | tenant_commission_settings_tenant_id_key (表 tenant_commission_settings) | tenant_commission_settings_tenant_id_key\|u\|UNIQUE (tenant_id) |  | tenant_commission_settings_tenant_id_key\|u\|UNIQUE (tenant_id) | 印1:全件の後に有る |
| 制約 | chk_tenant_issuer_profiles_phone (表 tenant_issuer_profiles) | chk_tenant_issuer_profiles_phone\|c\|CHECK (((phone IS NULL) OR ((country_code = 'JP'::bpchar) AND ((phone)::text ~ '^[0-9]{10,11}$'::text)) OR ((country_code <> 'JP'::bpchar) AND ((phone)::text ~ '^\\+[0-9]{6,15}$'::text)))) | chk_tenant_issuer_profiles_phone\|c\|CHECK (((phone IS NULL) OR ((country_code = 'JP'::bpchar) AND ((phone)::text ~ '^[0-9]{10,11}$'::text)) OR ((country_code <> 'JP'::bpchar) AND ((phone)::text ~ '^\+[0-9]{6,15}$'::text)))) | chk_tenant_issuer_profiles_phone\|c\|CHECK (((phone IS NULL) OR ((country_code = 'JP'::bpchar) AND ((phone)::text ~ '^[0-9]{10,11}$'::text)) OR ((country_code <> 'JP'::bpchar) AND ((phone)::text ~ '^\+[0-9]{6,15}$'::text)))) | 印3:ひな形のまま |
| 制約 | fk_tenant_meta_config_connected_by_staff_id_user (表 tenant_meta_config) | fk_tenant_meta_config_connected_by_staff_id_user\|f\|FOREIGN KEY (connected_by_staff_id) REFERENCES users(id) ON DELETE SET NULL |  | fk_tenant_meta_config_connected_by_staff_id_user\|f\|FOREIGN KEY (connected_by_staff_id) REFERENCES users(id) ON DELETE SET NULL | 印1:全件の後に有る |
| 制約 | tenant_meta_config_connected_by_staff_id_fkey (表 tenant_meta_config) |  | tenant_meta_config_connected_by_staff_id_fkey\|f\|FOREIGN KEY (connected_by_staff_id) REFERENCES users(id) ON DELETE SET NULL | tenant_meta_config_connected_by_staff_id_fkey\|f\|FOREIGN KEY (connected_by_staff_id) REFERENCES users(id) ON DELETE SET NULL | 印2:残っている |
| 制約 | user_badges_badge_id_fkey (表 user_badges) | user_badges_badge_id_fkey\|f\|FOREIGN KEY (badge_id) REFERENCES X.badge_definitions(id) ON DELETE CASCADE |  |  | 印1:全件の後も無い |
| 制約 | user_badges_pkey (表 user_badges) | user_badges_pkey\|p\|PRIMARY KEY (id) |  |  | 印1:全件の後も無い |
| 制約 | user_badges_tenant_id_user_id_badge_id_key (表 user_badges) | user_badges_tenant_id_user_id_badge_id_key\|u\|UNIQUE (tenant_id, user_id, badge_id) |  |  | 印1:全件の後も無い |
| トリガ | trg_calendar_events_updated_at (表 calendar_events) | CREATE TRIGGER trg_calendar_events_updated_at BEFORE UPDATE ON X.calendar_events FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_calendar_events() |  | CREATE TRIGGER trg_calendar_events_updated_at BEFORE UPDATE ON X.calendar_events FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_calendar_events() | 印1:全件の後に有る |
| トリガ | trigger_set_updated_at_goals (表 goals) | CREATE TRIGGER trigger_set_updated_at_goals BEFORE UPDATE ON X.goals FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_goals() |  | CREATE TRIGGER trigger_set_updated_at_goals BEFORE UPDATE ON X.goals FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_goals() | 印1:全件の後に有る |
| トリガ | trg_la_updated_at (表 lead_attachments) | CREATE TRIGGER trg_la_updated_at BEFORE UPDATE ON X.lead_attachments FOR EACH ROW EXECUTE FUNCTION X.trg_set_updated_at() |  | CREATE TRIGGER trg_la_updated_at BEFORE UPDATE ON X.lead_attachments FOR EACH ROW EXECUTE FUNCTION X.trg_set_updated_at() | 印1:全件の後に有る |
| トリガ | trg_lead_playbook_updated_at (表 lead_playbook) |  | CREATE TRIGGER trg_lead_playbook_updated_at BEFORE UPDATE ON X.lead_playbook FOR EACH ROW EXECUTE FUNCTION X.trg_set_updated_at() | CREATE TRIGGER trg_lead_playbook_updated_at BEFORE UPDATE ON X.lead_playbook FOR EACH ROW EXECUTE FUNCTION X.trg_set_updated_at() | 印2:残っている |
| トリガ | trigger_set_updated_at_lead_playbook (表 lead_playbook) | CREATE TRIGGER trigger_set_updated_at_lead_playbook BEFORE UPDATE ON X.lead_playbook FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_lead_playbook() |  | CREATE TRIGGER trigger_set_updated_at_lead_playbook BEFORE UPDATE ON X.lead_playbook FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_lead_playbook() | 印1:全件の後に有る |
| トリガ | trigger_set_updated_at_order_commissions (表 order_commissions) | CREATE TRIGGER trigger_set_updated_at_order_commissions BEFORE UPDATE ON X.order_commissions FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_commissions() |  | CREATE TRIGGER trigger_set_updated_at_order_commissions BEFORE UPDATE ON X.order_commissions FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_commissions() | 印1:全件の後に有る |
| トリガ | trigger_set_updated_at_order_financials (表 order_financials) | CREATE TRIGGER trigger_set_updated_at_order_financials BEFORE UPDATE ON X.order_financials FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_financials() |  | CREATE TRIGGER trigger_set_updated_at_order_financials BEFORE UPDATE ON X.order_financials FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_financials() | 印1:全件の後に有る |
| トリガ | trigger_set_updated_at_order_purchase_details (表 order_purchase_details) | CREATE TRIGGER trigger_set_updated_at_order_purchase_details BEFORE UPDATE ON X.order_purchase_details FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_purchase_details() |  | CREATE TRIGGER trigger_set_updated_at_order_purchase_details BEFORE UPDATE ON X.order_purchase_details FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_purchase_details() | 印1:全件の後に有る |
| トリガ | trigger_set_updated_at_order_shipping_details (表 order_shipping_details) | CREATE TRIGGER trigger_set_updated_at_order_shipping_details BEFORE UPDATE ON X.order_shipping_details FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_shipping_details() |  | CREATE TRIGGER trigger_set_updated_at_order_shipping_details BEFORE UPDATE ON X.order_shipping_details FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_order_shipping_details() | 印1:全件の後に有る |
| トリガ | trigger_set_updated_at_tenant_commission_settings (表 tenant_commission_settings) | CREATE TRIGGER trigger_set_updated_at_tenant_commission_settings BEFORE UPDATE ON X.tenant_commission_settings FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_tenant_commission_settings() |  | CREATE TRIGGER trigger_set_updated_at_tenant_commission_settings BEFORE UPDATE ON X.tenant_commission_settings FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_tenant_commission_settings() | 印1:全件の後に有る |
| トリガ | trigger_set_updated_at_tenant_meta_config (表 tenant_meta_config) | CREATE TRIGGER trigger_set_updated_at_tenant_meta_config BEFORE UPDATE ON X.tenant_meta_config FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_tenant_meta_config() |  | CREATE TRIGGER trigger_set_updated_at_tenant_meta_config BEFORE UPDATE ON X.tenant_meta_config FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_tenant_meta_config() | 印1:全件の後に有る |
| トリガ | trigger_set_updated_at_tenant_profile (表 tenant_profile) | CREATE TRIGGER trigger_set_updated_at_tenant_profile BEFORE UPDATE ON X.tenant_profile FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_tenant_profile() |  | CREATE TRIGGER trigger_set_updated_at_tenant_profile BEFORE UPDATE ON X.tenant_profile FOR EACH ROW EXECUTE FUNCTION X.set_updated_at_tenant_profile() | 印1:全件の後に有る |
| 方針 | archives.tenant_isolation_archives | tenant_isolation_archives\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | tenant_isolation_archives\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | badge_definitions.tenant_isolation_badge_definitions | tenant_isolation_badge_definitions\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |  | 印1:全件の後も無い |
| 方針 | bots.tenant_isolation_bots | tenant_isolation_bots\|*\|true\|public\|(tenant_id = current_tenant_id())\| | tenant_isolation_bots\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | tenant_isolation_bots\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印3:ひな形のまま |
| 方針 | buddy_feedbacks.tenant_isolation_buddy_feedbacks | tenant_isolation_buddy_feedbacks\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |  | 印1:全件の後も無い |
| 方針 | buddy_pairs.tenant_isolation_buddy_pairs | tenant_isolation_buddy_pairs\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |  | 印1:全件の後も無い |
| 方針 | companies.tenant_isolation_companies | tenant_isolation_companies\|*\|true\|public\|(tenant_id = current_tenant_id())\| | tenant_isolation_companies\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | tenant_isolation_companies\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印3:ひな形のまま |
| 方針 | company_addresses.tenant_isolation_company_addresses | tenant_isolation_company_addresses\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_addresses.company_id) AND (c.tenant_id = current_tenant_id()))))\| | tenant_isolation_company_addresses\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_addresses.company_id) AND (c.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | tenant_isolation_company_addresses\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_addresses.company_id) AND (c.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | 印3:ひな形のまま |
| 方針 | company_discord.tenant_isolation_company_discord | tenant_isolation_company_discord\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_discord.company_id) AND (c.tenant_id = current_tenant_id()))))\| | tenant_isolation_company_discord\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_discord.company_id) AND (c.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | tenant_isolation_company_discord\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_discord.company_id) AND (c.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | 印3:ひな形のまま |
| 方針 | company_sales_channels.tenant_isolation_company_sales_channels | tenant_isolation_company_sales_channels\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_sales_channels.company_id) AND (c.tenant_id = current_tenant_id()))))\| | tenant_isolation_company_sales_channels\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_sales_channels.company_id) AND (c.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | tenant_isolation_company_sales_channels\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.companies c\n  WHERE ((c.id = company_sales_channels.company_id) AND (c.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | 印3:ひな形のまま |
| 方針 | contact_contact_channels.tenant_isolation_contact_contact_channels | tenant_isolation_contact_contact_channels\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_contact_channels.contact_id) AND (ct.tenant_id = current_tenant_id()))))\| | tenant_isolation_contact_contact_channels\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_contact_channels.contact_id) AND (ct.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | tenant_isolation_contact_contact_channels\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_contact_channels.contact_id) AND (ct.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | 印3:ひな形のまま |
| 方針 | contact_discord.tenant_isolation_contact_discord | tenant_isolation_contact_discord\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_discord.contact_id) AND (ct.tenant_id = current_tenant_id()))))\| | tenant_isolation_contact_discord\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_discord.contact_id) AND (ct.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | tenant_isolation_contact_discord\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_discord.contact_id) AND (ct.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | 印3:ひな形のまま |
| 方針 | contact_emails.tenant_isolation_contact_emails | tenant_isolation_contact_emails\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_emails.contact_id) AND (ct.tenant_id = current_tenant_id()))))\| | tenant_isolation_contact_emails\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_emails.contact_id) AND (ct.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | tenant_isolation_contact_emails\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.contacts ct\n  WHERE ((ct.id = contact_emails.contact_id) AND (ct.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | 印3:ひな形のまま |
| 方針 | contacts.tenant_isolation_contacts | tenant_isolation_contacts\|*\|true\|public\|(tenant_id = current_tenant_id())\| | tenant_isolation_contacts\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | tenant_isolation_contacts\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印3:ひな形のまま |
| 方針 | conversation_logs.conversation_logs_tenant_isolation | conversation_logs_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | conversation_logs_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | customer_scores.customer_scores_tenant_isolation | customer_scores_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | customer_scores_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | discord_channel_webhooks.tenant_isolation_discord_channel_webhooks | tenant_isolation_discord_channel_webhooks\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | tenant_isolation_discord_channel_webhooks\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | erp_sync_logs.tenant_isolation_erp_sync_logs | tenant_isolation_erp_sync_logs\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | tenant_isolation_erp_sync_logs\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | lead_attachments.tenant_isolation_lead_attachments | tenant_isolation_lead_attachments\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.leads l\n  WHERE ((l.id = lead_attachments.lead_id) AND (l.tenant_id = current_tenant_id()))))\| |  | tenant_isolation_lead_attachments\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.leads l\n  WHERE ((l.id = lead_attachments.lead_id) AND (l.tenant_id = current_tenant_id()))))\| | 印1:全件の後に有る |
| 方針 | message_labels.message_labels_tenant_isolation | message_labels_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | message_labels_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | message_translations.message_translations_tenant_isolation | message_translations_tenant_isolation\|*\|true\|public\|(tenant_id = (NULLIF(current_setting('app.tenant_id'::text, true), ''::text))::integer)\| |  | message_translations_tenant_isolation\|*\|true\|public\|(tenant_id = (NULLIF(current_setting('app.tenant_id'::text, true), ''::text))::integer)\| | 印1:全件の後に有る |
| 方針 | meta_message_reactions.tenant_isolation_meta_message_reactions | tenant_isolation_meta_message_reactions\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | tenant_isolation_meta_message_reactions\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | notification_channels.tenant_isolation_notification_channels | tenant_isolation_notification_channels\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | tenant_isolation_notification_channels\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | notification_logs.tenant_isolation_notification_logs | tenant_isolation_notification_logs\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | tenant_isolation_notification_logs\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | order_commissions.tenant_isolation_order_commissions | tenant_isolation_order_commissions\|*\|true\|public\|(tenant_id = current_tenant_id())\| |  | tenant_isolation_order_commissions\|*\|true\|public\|(tenant_id = current_tenant_id())\| | 印1:全件の後に有る |
| 方針 | order_financials.tenant_isolation_order_financials | tenant_isolation_order_financials\|*\|true\|public\|(tenant_id = current_tenant_id())\| |  | tenant_isolation_order_financials\|*\|true\|public\|(tenant_id = current_tenant_id())\| | 印1:全件の後に有る |
| 方針 | order_purchase_details.tenant_isolation_order_purchase_details | tenant_isolation_order_purchase_details\|*\|true\|public\|(tenant_id = current_tenant_id())\| |  | tenant_isolation_order_purchase_details\|*\|true\|public\|(tenant_id = current_tenant_id())\| | 印1:全件の後に有る |
| 方針 | order_shipping_details.tenant_isolation_order_shipping_details | tenant_isolation_order_shipping_details\|*\|true\|public\|(tenant_id = current_tenant_id())\| |  | tenant_isolation_order_shipping_details\|*\|true\|public\|(tenant_id = current_tenant_id())\| | 印1:全件の後に有る |
| 方針 | shifts.tenant_isolation_shifts | tenant_isolation_shifts\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | tenant_isolation_shifts\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | staff.tenant_isolation_staff | tenant_isolation_staff\|*\|true\|public\|(tenant_id = current_tenant_id())\| | tenant_isolation_staff\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | tenant_isolation_staff\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印3:ひな形のまま |
| 方針 | staff_emails.tenant_isolation_staff_emails | tenant_isolation_staff_emails\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.staff s\n  WHERE ((s.id = staff_emails.staff_id) AND (s.tenant_id = current_tenant_id()))))\| | tenant_isolation_staff_emails\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.staff s\n  WHERE ((s.id = staff_emails.staff_id) AND (s.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | tenant_isolation_staff_emails\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.staff s\n  WHERE ((s.id = staff_emails.staff_id) AND (s.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | 印3:ひな形のまま |
| 方針 | staff_reports.tenant_isolation_staff_reports | tenant_isolation_staff_reports\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | tenant_isolation_staff_reports\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | staff_ui_preferences.tenant_isolation_staff_ui_preferences | tenant_isolation_staff_ui_preferences\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.staff s\n  WHERE ((s.id = staff_ui_preferences.staff_id) AND (s.tenant_id = current_tenant_id()))))\| | tenant_isolation_staff_ui_preferences\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.staff s\n  WHERE ((s.id = staff_ui_preferences.staff_id) AND (s.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | tenant_isolation_staff_ui_preferences\|*\|true\|public\|(EXISTS ( SELECT 1\n   FROM X.staff s\n  WHERE ((s.id = staff_ui_preferences.staff_id) AND (s.tenant_id = (current_setting('app.tenant_id'::text, true))::integer))))\| | 印3:ひな形のまま |
| 方針 | suppliers.tenant_isolation_suppliers |  | tenant_isolation_suppliers\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | tenant_isolation_suppliers\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印2:残っている |
| 方針 | tenant_calibrations.tenant_calibrations_tenant_isolation | tenant_calibrations_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  | tenant_calibrations_tenant_isolation\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| | 印1:全件の後に有る |
| 方針 | tenant_commission_settings.tenant_isolation_tenant_commission_settings | tenant_isolation_tenant_commission_settings\|*\|true\|public\|(tenant_id = current_tenant_id())\| |  | tenant_isolation_tenant_commission_settings\|*\|true\|public\|(tenant_id = current_tenant_id())\| | 印1:全件の後に有る |
| 方針 | user_badges.tenant_isolation_user_badges | tenant_isolation_user_badges\|*\|true\|public\|(tenant_id = (current_setting('app.tenant_id'::text, true))::integer)\| |  |  | 印1:全件の後も無い |
| 表の印 | archives | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | audit_logs | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | badge_definitions | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |  | 印1:全件の後も無い |
| 表の印 | buddy_feedbacks | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |  | 印1:全件の後も無い |
| 表の印 | buddy_pairs | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |  | 印1:全件の後も無い |
| 表の印 | calendar_events | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | calendar_owner_settings | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |  | 印1:全件の後も無い |
| 表の印 | channel_masters | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | close_reasons | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | companies | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | company_addresses | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | company_discord | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | company_sales_channels | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | contact_contact_channels | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | contact_discord | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | contact_emails | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | contacts | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | conversation_logs | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | customer_scores | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | deal_close_reasons | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | discord_channel_webhooks | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | 印1:全件の後に有る |
| 表の印 | discord_retired_members | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | discord_retired_roles | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | erp_sync_logs | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | goals | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | invoice_items | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | invoices | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | lead_attachments | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | lead_channels | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | lead_playbook | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | lead_sales_form_selections | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | leads | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | message_labels | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | message_translations | True\|True\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|True\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | meta_message_reactions | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | meta_messages | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | notice_fallback_recipients | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | notification_channels | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | notification_logs | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | order_commissions | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | order_financials | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | order_items | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | order_purchase_details | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | order_shipping_details | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | orders | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | outbound_translation_drafts | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | own_inventory | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | paypal_disputes | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | products | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | purchase_order_items | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | purchase_orders | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | quote_items | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | quotes | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | role_permissions | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | roles | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | shifts | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | shipping_rates | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | shipping_zones | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | staff_emails | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | staff_reports | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | staff_ui_preferences | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | suppliers |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印2:残っている |
| 表の印 | team_members | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | teams | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | tenant_calibrations | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | tenant_commission_settings | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印1:全件の後に有る |
| 表の印 | tenant_duty_rule_components | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | tenant_duty_rules | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | tenant_profile | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | tenant_sales_form_options | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | user_badges | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} |  |  | 印1:全件の後も無い |
| 表の印 | user_notices | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | False\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 表の印 | user_roles | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | True\|False\|jarvis\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis,ai_unmask_owner=r/jarvis} | 印3:本番と同じになった |
| 連番 | archives_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | badge_definitions_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  | 印1:全件の後も無い |
| 連番 | buddy_feedbacks_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  | 印1:全件の後も無い |
| 連番 | buddy_pairs_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  | 印1:全件の後も無い |
| 連番 | calendar_events_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | conversation_logs_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | customer_code_seq | bigint\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  | 印1:全件の後も無い |
| 連番 | customer_scores_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | deal_code_seq | bigint\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  | 印1:全件の後も無い |
| 連番 | discord_channel_webhooks_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | erp_sync_logs_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | lead_attachments_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | lead_code_seq | bigint\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  | 印1:全件の後も無い |
| 連番 | message_labels_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | message_translations_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | meta_message_reactions_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | notification_channels_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | notification_logs_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | order_commissions_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | order_financials_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | order_purchase_details_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | order_shipping_details_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | outbound_translation_drafts_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | paypal_disputes_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | shifts_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | staff_reports_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | suppliers_id_seq |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印2:残っている |
| 連番 | tenant_calibrations_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | tenant_commission_settings_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} | 印1:全件の後に有る |
| 連番 | user_badges_id_seq | integer\|1\|1\|False\|{jarvis=rwU/jarvis,salesanchor_app=rU/jarvis} |  |  | 印1:全件の後も無い |
| 関数 | set_updated_at_calendar_events() | 211737f15aee82dd881c47f7bcaae23e\|False |  | 211737f15aee82dd881c47f7bcaae23e\|False | 印1:全件の後に有る |
| 関数 | set_updated_at_goals() | a49b07e555fbd6ad335a99b945ba0ee1\|False |  | a49b07e555fbd6ad335a99b945ba0ee1\|False | 印1:全件の後に有る |
| 関数 | set_updated_at_lead_playbook() | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False | 印1:全件の後に有る |
| 関数 | set_updated_at_order_commissions() | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False | 印1:全件の後に有る |
| 関数 | set_updated_at_order_financials() | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False | 印1:全件の後に有る |
| 関数 | set_updated_at_order_purchase_details() | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False | 印1:全件の後に有る |
| 関数 | set_updated_at_order_shipping_details() | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False | 印1:全件の後に有る |
| 関数 | set_updated_at_tenant_commission_settings() | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False | 印1:全件の後に有る |
| 関数 | set_updated_at_tenant_meta_config() | 06bcf30ac3d0a7f279a54cbf228a7bec\|False |  | 06bcf30ac3d0a7f279a54cbf228a7bec\|False | 印1:全件の後に有る |
| 関数 | set_updated_at_tenant_profile() | a49b07e555fbd6ad335a99b945ba0ee1\|False |  | a49b07e555fbd6ad335a99b945ba0ee1\|False | 印1:全件の後に有る |
| 関数 | trg_set_updated_at() | a49b07e555fbd6ad335a99b945ba0ee1\|False | 06bcf30ac3d0a7f279a54cbf228a7bec\|False | a49b07e555fbd6ad335a99b945ba0ee1\|False | 印3:本番と同じになった |
| ビュー | v_company_stats | c5e051967e16a5b43635dd3285f34a93\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} |  | c5e051967e16a5b43635dd3285f34a93\|{jarvis=arwdDxt/jarvis,salesanchor_app=arwd/jarvis} | 印1:全件の後に有る |

## 印ごとの件数

| 印 | 件数 |
|---|---|
| 印1:全件の後に有る | 589 |
| 印1:全件の後も無い | 102 |
| 印2:残っている | 26 |
| 印2:消えた | 4 |
| 印3:ひな形のまま | 19 |
| 印3:本番と同じになった | 53 |
| 合計 | 793 |

## 種類ごと・印ごとの件数

| 種類 | 印1:全件の後に有る | 印1:全件の後も無い | 印2:残っている | 印2:消えた | 印3:ひな形のまま | 印3:本番と同じになった | 合計 |
|---|---|---|---|---|---|---|---|
| 列 | 333 | 45 | 12 | 1 | 6 | 5 | 402 |
| 索引 | 95 | 22 | 1 | 0 | 0 | 0 | 118 |
| 制約 | 76 | 19 | 9 | 3 | 1 | 2 | 110 |
| トリガ | 11 | 0 | 1 | 0 | 0 | 0 | 12 |
| 方針 | 19 | 4 | 1 | 0 | 12 | 0 | 36 |
| 表の印 | 22 | 5 | 1 | 0 | 0 | 45 | 73 |
| 連番 | 22 | 7 | 1 | 0 | 0 | 0 | 30 |
| 関数 | 10 | 0 | 0 | 0 | 0 | 1 | 11 |
| ビュー | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| 合計 | 589 | 102 | 26 | 4 | 19 | 53 | 793 |


## 本番 003 だけにある索引 13・制約 2・連番 3（`recon-5-0-opus-prod.md` §3・§5）が有るか（○有る・×無い）

| 種類 | 名前 | ひな形の直後 | 全件の後 |
|---|---|---|---|
| 索引 | idx_invoices_status | × | × |
| 索引 | idx_leads_assigned_to | × | × |
| 索引 | idx_leads_status | × | × |
| 索引 | leads_tenant_id_lead_code_key | × | × |
| 索引 | idx_products_category | × | × |
| 索引 | idx_products_status | × | × |
| 索引 | idx_po_status | × | × |
| 索引 | idx_po_supplier | × | × |
| 索引 | idx_quotes_status | × | × |
| 索引 | idx_shipping_rates_lookup | × | × |
| 索引 | idx_team_members_team | × | × |
| 索引 | idx_team_members_user | × | × |
| 索引 | idx_user_roles_user | × | × |
| 制約 | fk_orders_invoice | × | × |
| 制約 | leads_tenant_id_lead_code_key | × | × |
| 連番 | customer_code_seq | × | × |
| 連番 | deal_code_seq | × | × |
| 連番 | lead_code_seq | × | × |

