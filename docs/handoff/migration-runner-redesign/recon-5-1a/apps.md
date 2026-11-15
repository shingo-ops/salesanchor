# 5-1a 手順5: `backend/app` が値を書く表を探した台本と出力

本報告はカード 5-1a の実行結果である。
読んだ commit: `a6d59cc361e3174c71bdc87136ed1dcd42737ffd`

## 使った命令（全文）
```
python3.12 -m venv /tmp/recon/venv          # 台本の Python は 3.12 の venv（card-5-0b.md 手順4b）。システムの python3 は 3.11.18 だったため
/tmp/recon/venv/bin/python -I /tmp/recon/apps.py > /tmp/recon/apps.out
```
（カードの命令 `python3 -I /tmp/recon/apps.py > /tmp/recon/apps.out` の `python3` を venv の 3.12.3 の `python` に替えて流した。台本は標準ライブラリだけ。）

## 探し方（限界）
- 走査: `backend/app` 以下の `*.py` 447ファイル。`backend/tests` は見ていない。
- 当たりの条件: 表名が `INSERT INTO`／`UPDATE`／`DELETE FROM` の直後（スキーマ前置き `xxx.`・`{schema}.`・`%s.` を許す）に出る行。大文字小文字は問わない。文字の一致だけで、SQLAlchemy の `insert()`・ORM の `session.add()` など、文の語を書かない書き方は見えない（`__tablename__` で表名を持つ ORM モデルは参考として別に出した。当たりは `users`（`backend/app/models.py:23`）だけ）。
- `○` は最初の1か所（ファイル:行）と、見つかった件数。`×` は当たり無し。同じ表名が別の文脈（例: 他の表名の一部・コメント）で当たった可能性、および表名を変数で組み立てた文は見えない（未確認）。
- `p11-detail.md` の「アプリが書き換えるか」は、この出力を表の行ごとに引いたもの。

## 台本の全文（`/tmp/recon/apps.py`）
```python
"""card 5-1a step5: backend/app が値を書く表を探す（読むだけ）。
表名が INSERT INTO / UPDATE / DELETE FROM の直後（スキーマ前置き可）に出る所を最初の1か所まで報告する。
ORM の __tablename__ は参考として別に出す。"""
import re
from pathlib import Path

ROOT = Path("/root/worktrees/salesanchor/release-migration-p11-classify/backend/app")

TARGETS = {
    1: ["customer_contact_channels"],
    2: ["deals", "orders", "quotes", "invoices"],
    3: ["users"],
    4: ["products_category_classification_backup"],
    5: ["company_discord"],
    6: ["products"],
    7: ["product_attribute_masters"],
    8: ["tenant_carrier_credentials"],
    9: ["invoices"],
    10: ["lead_channels", "leads"],
    11: ["tenant_sales_form_options"],
    12: ["meta_messages"],
    13: ["inventory"],
    14: ["leads", "companies"],
    15: ["conditions"],
    16: ["tcg_major_categories", "tcg_series", "tcg_manufacturers", "tcg_product_categories"],
    17: ["tcg_unit_evidence_rules"],
    18: ["tcg_note_master"],
    19: ["tcg_status_master"],
    20: ["tcg_normalization_rules"],
    21: ["tcg_products"],
    22: ["tcg_normalization_rules"],
    23: ["tcg_distribution_settings"],
    24: ["tcg_suppliers", "supplier_channels"],
    25: ["tcg_suppliers", "supplier_channels"],
    26: ["tcg_major_categories", "tcg_series", "tcg_manufacturers", "tcg_product_categories", "tcg_suppliers", "supplier_channels"],
    27: ["extraction_jobs"],
    28: ["tcg_note_master"],
    29: ["extraction_jobs"],
    30: ["extraction_jobs"],
    31: ["source_messages"],
    32: ["tcg_note_master", "tcg_normalization_rules"],
    33: ["extraction_jobs"],
    34: ["tcg_note_master"],
    35: ["conditions"],
    36: ["product_exclude_keywords"],
    37: ["products"],
    38: ["product_search_keywords", "product_exclude_keywords", "products_logistics", "analysis_results"],
    39: ["analysis_policies"],
    40: ["analysis_results"],
    41: ["line_import_devices"],
    42: ["extraction_prompt_config"],
    43: ["source_messages"],
    44: ["tenant_discord_ticket_config"],
    45: ["llm_usage_events"],
    46: ["app_fx_rate_history"],
    47: ["build_columns"],
    48: ["deny_tables"],
    49: ["tenant_features"],
    50: ["ai_job_choices", "ai_job_assignments"],
    51: ["ai_job_choices"],
    52: ["meta_page_routing"],
}

PREFIX = r"""(?:[\w\.\{\}\$\"'%()\[\]]*\.)?\"?"""
VERBS = {
    "INSERT": r"INSERT\s+INTO\s+",
    "UPDATE": r"(?<![A-Za-z_])UPDATE\s+(?:ONLY\s+)?",
    "DELETE": r"DELETE\s+FROM\s+(?:ONLY\s+)?",
}

files = sorted(p for p in ROOT.rglob("*.py"))
texts = {}
for p in files:
    try:
        texts[p] = p.read_text(encoding="utf-8")
    except Exception as e:  # 読めない物は報告して続ける
        print("READ-ERROR", p, e)


def lineno(text, pos):
    return text.count("\n", 0, pos) + 1


def first_hit(table):
    hits = []
    for verb, vre in VERBS.items():
        rx = re.compile(vre + PREFIX + re.escape(table) + r"\b", re.I)
        for p, t in texts.items():
            m = rx.search(t)
            if m:
                hits.append((p.relative_to(ROOT.parent.parent), lineno(t, m.start()), verb))
    hits.sort(key=lambda h: (str(h[0]), h[1]))
    return hits


def orm_hit(table):
    rx = re.compile(r"__tablename__\s*=\s*[\"']" + re.escape(table) + r"[\"']")
    out = []
    for p, t in texts.items():
        m = rx.search(t)
        if m:
            out.append((p.relative_to(ROOT.parent.parent), lineno(t, m.start())))
    return out


print("# 走査したファイル数:", len(texts))
cache = {}
for n, tables in TARGETS.items():
    for tb in tables:
        if tb not in cache:
            cache[tb] = (first_hit(tb), orm_hit(tb))
        hits, orm = cache[tb]
        if hits:
            h = hits[0]
            summary = "○ {}:{} ({}) 計{}か所".format(h[0], h[1], h[2], len(hits))
        else:
            summary = "×"
        o = "ORM: {}:{}".format(orm[0][0], orm[0][1]) if orm else "ORM: なし"
        print("{}\t{}\t{}\t{}".format(n, tb, summary, o))
```

## 出力の全文（`/tmp/recon/apps.out`。列: 表の番号／表名／結果／ORM）
```
# 走査したファイル数: 447
1	customer_contact_channels	×	ORM: なし
2	deals	○ backend/app/routers/companies.py:476 (UPDATE) 計2か所	ORM: なし
2	orders	○ backend/app/routers/companies.py:789 (UPDATE) 計3か所	ORM: なし
2	quotes	○ backend/app/routers/companies.py:793 (UPDATE) 計4か所	ORM: なし
2	invoices	○ backend/app/routers/companies.py:797 (UPDATE) 計5か所	ORM: なし
3	users	○ backend/app/discord_gateway/staff_join.py:359 (UPDATE) 計4か所	ORM: backend/app/models.py:23
4	products_category_classification_backup	×	ORM: なし
5	company_discord	○ backend/app/routers/companies.py:160 (INSERT) 計2か所	ORM: なし
6	products	○ backend/app/routers/purchase_orders.py:265 (UPDATE) 計5か所	ORM: なし
7	product_attribute_masters	○ backend/app/routers/product_masters.py:86 (INSERT) 計3か所	ORM: なし
8	tenant_carrier_credentials	○ backend/app/services/carrier_credentials.py:174 (INSERT) 計3か所	ORM: なし
9	invoices	○ backend/app/routers/companies.py:797 (UPDATE) 計5か所	ORM: なし
10	lead_channels	○ backend/app/discord_gateway/dm_writer.py:57 (INSERT) 計3か所	ORM: なし
10	leads	○ backend/app/discord_gateway/dm_writer.py:140 (INSERT) 計8か所	ORM: なし
11	tenant_sales_form_options	×	ORM: なし
12	meta_messages	○ backend/app/discord_gateway/dm_writer.py:197 (INSERT) 計5か所	ORM: なし
13	inventory	○ backend/app/routers/inventory_offers.py:619 (INSERT) 計4か所	ORM: なし
14	leads	○ backend/app/discord_gateway/dm_writer.py:140 (INSERT) 計8か所	ORM: なし
14	companies	○ backend/app/routers/companies.py:409 (INSERT) 計5か所	ORM: なし
15	conditions	○ backend/app/routers/conditions.py:232 (INSERT) 計4か所	ORM: なし
16	tcg_major_categories	×	ORM: なし
16	tcg_series	×	ORM: なし
16	tcg_manufacturers	×	ORM: なし
16	tcg_product_categories	○ backend/app/routers/product_categories.py:140 (INSERT) 計4か所	ORM: なし
17	tcg_unit_evidence_rules	×	ORM: なし
18	tcg_note_master	○ backend/app/routers/note_master.py:174 (INSERT) 計6か所	ORM: なし
19	tcg_status_master	○ backend/app/routers/status_master.py:164 (INSERT) 計4か所	ORM: なし
20	tcg_normalization_rules	×	ORM: なし
21	tcg_products	×	ORM: なし
22	tcg_normalization_rules	×	ORM: なし
23	tcg_distribution_settings	○ backend/app/services/tcg_distribution_svc.py:862 (UPDATE) 計1か所	ORM: なし
24	tcg_suppliers	×	ORM: なし
24	supplier_channels	○ backend/app/routers/tcg_line_import.py:532 (INSERT) 計2か所	ORM: なし
25	tcg_suppliers	×	ORM: なし
25	supplier_channels	○ backend/app/routers/tcg_line_import.py:532 (INSERT) 計2か所	ORM: なし
26	tcg_major_categories	×	ORM: なし
26	tcg_series	×	ORM: なし
26	tcg_manufacturers	×	ORM: なし
26	tcg_product_categories	○ backend/app/routers/product_categories.py:140 (INSERT) 計4か所	ORM: なし
26	tcg_suppliers	×	ORM: なし
26	supplier_channels	○ backend/app/routers/tcg_line_import.py:532 (INSERT) 計2か所	ORM: なし
27	extraction_jobs	○ backend/app/services/line_analysis_v102_svc.py:587 (UPDATE) 計7か所	ORM: なし
28	tcg_note_master	○ backend/app/routers/note_master.py:174 (INSERT) 計6か所	ORM: なし
29	extraction_jobs	○ backend/app/services/line_analysis_v102_svc.py:587 (UPDATE) 計7か所	ORM: なし
30	extraction_jobs	○ backend/app/services/line_analysis_v102_svc.py:587 (UPDATE) 計7か所	ORM: なし
31	source_messages	○ backend/app/services/tcg_line_import_svc.py:455 (INSERT) 計2か所	ORM: なし
32	tcg_note_master	○ backend/app/routers/note_master.py:174 (INSERT) 計6か所	ORM: なし
32	tcg_normalization_rules	×	ORM: なし
33	extraction_jobs	○ backend/app/services/line_analysis_v102_svc.py:587 (UPDATE) 計7か所	ORM: なし
34	tcg_note_master	○ backend/app/routers/note_master.py:174 (INSERT) 計6か所	ORM: なし
35	conditions	○ backend/app/routers/conditions.py:232 (INSERT) 計4か所	ORM: なし
36	product_exclude_keywords	○ backend/app/services/tcg_product_master_svc.py:637 (INSERT) 計1か所	ORM: なし
37	products	○ backend/app/routers/purchase_orders.py:265 (UPDATE) 計5か所	ORM: なし
38	product_search_keywords	○ backend/app/services/tcg_product_master_svc.py:621 (INSERT) 計1か所	ORM: なし
38	product_exclude_keywords	○ backend/app/services/tcg_product_master_svc.py:637 (INSERT) 計1か所	ORM: なし
38	products_logistics	×	ORM: なし
38	analysis_results	○ backend/app/routers/tcg_product_import.py:478 (UPDATE) 計10か所	ORM: なし
39	analysis_policies	×	ORM: なし
40	analysis_results	○ backend/app/routers/tcg_product_import.py:478 (UPDATE) 計10か所	ORM: なし
41	line_import_devices	○ backend/app/services/line_import_devices.py:51 (DELETE) 計3か所	ORM: なし
42	extraction_prompt_config	○ backend/app/routers/super_admin_suppliers.py:1102 (INSERT) 計1か所	ORM: なし
43	source_messages	○ backend/app/services/tcg_line_import_svc.py:455 (INSERT) 計2か所	ORM: なし
44	tenant_discord_ticket_config	○ backend/app/routers/discord_auto_setup.py:391 (INSERT) 計2か所	ORM: なし
45	llm_usage_events	○ backend/app/services/llm_budget.py:277 (INSERT) 計1か所	ORM: なし
46	app_fx_rate_history	○ backend/app/routers/fx_rate_admin.py:140 (INSERT) 計2か所	ORM: なし
47	build_columns	×	ORM: なし
48	deny_tables	×	ORM: なし
49	tenant_features	×	ORM: なし
50	ai_job_choices	×	ORM: なし
50	ai_job_assignments	○ backend/app/services/ai_assignment.py:76 (UPDATE) 計1か所	ORM: なし
51	ai_job_choices	×	ORM: なし
52	meta_page_routing	○ backend/app/services/tenant.py:1816 (DELETE) 計2か所	ORM: なし
```
