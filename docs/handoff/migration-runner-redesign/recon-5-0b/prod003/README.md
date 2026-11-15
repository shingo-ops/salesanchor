---
mode: handoff
---
# 本番 tenant_003 の形（構造だけ・値なし・Opus・2026-11-15）

- 道: reader 鍵（読み取り専用）。1回1文。出力は1行目が見出しの TSV。会社名は `X` に置き換え済み。
- 合計: 表 79・列 1006・索引 256・制約 264・トリガ 28・方針 64・連番 72・関数 15・ビュー 2（`recon-5-0-opus-prod.md` §2 の数と一致）。
- 5-0b で使うときは `'tenant_003'` を調べる会社の名前に変える（`replace(...,'tenant_003','X')` の中も同じ名前に変える）。

## 9本の問い合わせ（全文）

```sql
-- columns.tsv
SELECT c.relname, count(*) AS n, string_agg(a.attname||'|'||format_type(a.atttypid,a.atttypmod)||'|'||a.attnotnull::text||'|'||coalesce(replace(pg_get_expr(d.adbin,d.adrelid),'tenant_003','X'),''), ' ;; ' ORDER BY a.attname) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE n.nspname='tenant_003' AND c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped GROUP BY 1 ORDER BY 1 LIMIT 150;

-- indexes.tsv
SELECT t.relname, count(*) AS n, string_agg(replace(pg_get_indexdef(i.indexrelid),'tenant_003','X'), ' ;; ' ORDER BY ic.relname) FROM pg_index i JOIN pg_class ic ON ic.oid=i.indexrelid JOIN pg_class t ON t.oid=i.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='tenant_003' GROUP BY 1 ORDER BY 1 LIMIT 150;

-- constraints.tsv
SELECT c.relname, count(*) AS n, string_agg(k.conname||'|'||k.contype::text||'|'||replace(pg_get_constraintdef(k.oid),'tenant_003','X'), ' ;; ' ORDER BY k.conname) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=k.connamespace WHERE n.nspname='tenant_003' GROUP BY 1 ORDER BY 1 LIMIT 150;

-- triggers.tsv
SELECT c.relname, count(*) AS n, string_agg(replace(pg_get_triggerdef(g.oid),'tenant_003','X'), ' ;; ' ORDER BY g.tgname) FROM pg_trigger g JOIN pg_class c ON c.oid=g.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_003' AND NOT g.tgisinternal GROUP BY 1 ORDER BY 1 LIMIT 150;

-- policies.tsv
SELECT c.relname, count(*) AS n, string_agg(p.polname||'|'||p.polcmd::text||'|'||p.polpermissive::text||'|'||coalesce(array_to_string(ARRAY(SELECT CASE WHEN r=0 THEN 'public' ELSE pg_get_userbyid(r) END FROM unnest(p.polroles) r ORDER BY 1),','),'')||'|'||coalesce(replace(pg_get_expr(p.polqual,p.polrelid),'tenant_003','X'),'')||'|'||coalesce(replace(pg_get_expr(p.polwithcheck,p.polrelid),'tenant_003','X'),''), ' ;; ' ORDER BY p.polname) FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_003' GROUP BY 1 ORDER BY 1 LIMIT 150;

-- table_flags.tsv
SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, pg_get_userbyid(c.relowner), c.relacl::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_003' AND c.relkind IN ('r','p') ORDER BY 1 LIMIT 150;

-- sequences.tsv
SELECT c.relname, format_type(s.seqtypid,NULL), s.seqstart, s.seqincrement, s.seqcycle, c.relacl::text FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_003' ORDER BY 1 LIMIT 150;

-- functions.tsv
SELECT p.proname, pg_get_function_identity_arguments(p.oid), md5(replace(p.prosrc,'tenant_003','X')), p.prosecdef FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='tenant_003' ORDER BY 1 LIMIT 150;

-- views.tsv
SELECT c.relname, md5(replace(pg_get_viewdef(c.oid),'tenant_003','X')), c.relacl::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_003' AND c.relkind='v' ORDER BY 1 LIMIT 150;

```
