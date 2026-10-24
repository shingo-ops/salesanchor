import json,os,sys
D=sys.argv[1]
gold={'T1':['docs/CC_UI_GOVERNANCE.md'],'T2':['docs/specs/branch-operations/README.md','docs/PARALLEL_TERMINAL_GUIDE.md'],
'T3':['docs/ai-agents/executor-checklist.md'],'T4':['docs/STANDARD-WORKFLOW.md'],'T5':['docs/runbooks/secret-rotation.md'],
'T6':['docs/runbooks/alerts.md'],'T7':['docs/runbooks/weekly-stale-tasks.md'],'T8':['docs/runbooks/bundle-sale-new-wording.md'],
'T9':['docs/ai-agents/design-partner.md'],'T10':['frontend/CLAUDE.md','frontend/AGENTS.md']}
exits={}
for l in open(D+'/exits.txt'):
    p=l.split()
    if len(p)==2 and p[1].startswith('exit='): exits[p[0]]=p[1][5:]
rows=[]
for t in gold:
  for k in (1,2):
    f=f'{D}/{t}-{k}.jsonl'
    op=ix=n=0; cost=''; last=''; autoload=0
    for line in open(f,errors='replace'):
        line=line.strip()
        if not line: continue
        try: d=json.loads(line)
        except Exception: continue
        last=d.get('type')
        if d.get('type')=='result': cost=d.get('total_cost_usd','')
        if d.get('type')=='assistant':
            for c in d.get('message',{}).get('content',[]):
                if c.get('type')=='tool_use':
                    n+=1; s=json.dumps(c.get('input'),ensure_ascii=False)
                    if any(g in s for g in gold[t]): op=1
                    if 'docs/INDEX.md' in s: ix=1
        elif t=='T10' and d.get('type')!='result' and 'frontend/CLAUDE.md' in line and d.get('type') in ('system','attachment','user'):
            autoload=1
    rows.append((t,k,op,ix,n,cost,exits.get(f'{t}-{k}','?'),last,autoload if t=='T10' else ''))
with open(D+'/result.tsv','w') as o:
    o.write('題\t回\t開いた\tINDEX\ttool_use数\ttotal_cost_usd\t終了コード\t最終行type\tT10自動読込(system/user行に文字列)\n')
    for r in rows: o.write('\t'.join(map(str,r))+'\n')
print(open(D+'/result.tsv').read())
print('K12',sum(r[2] for r in rows),'K10',sum(r[3] for r in rows),'cost',sum(float(r[5] or 0) for r in rows))
