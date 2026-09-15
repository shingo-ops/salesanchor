from pathlib import Path
import json,csv,hashlib
src=Path('/tmp/frontend-raw-buttons-20260911');dst=Path('docs/handoff/design-system-recon/evidence-20260910')
p=src/'modal-browser-v4-result.json';x=json.loads(p.read_text());assert x['status']=='PASS' and len(x['cases'])==560 and not x['errors'] and not x['externalRequests']
rows=[]
for c in x['cases']:
 a=c['after'];b=c['before'];n=c['natural'];assert c['referenceMatched'] and c['beforeUnchanged'];assert all(y['inside'] and y['internalText'] and y['insideContent'] for y in a['children']);assert not a['overlaps']
 if n['fits']:assert a['children']==b['children'] and a['footer']==b['footer']
 assert [y['disabled'] for y in a['children']]==[y['disabled'] for y in b['children']]
 rows.append({**{k:c[k] for k in ['width','height','dark','lang','kind','mode','amount','equivalent200Percent']},'required':n['required'],'available':n['available'],'natural_fits':n['fits'],'reference_matched':c['referenceMatched'],'before_unchanged':c['beforeUnchanged'],'before_footer_height':b['footer']['height'],'after_footer_height':a['footer']['height'],'after_child_count':len(a['children']),'after_inside':True,'after_text_unclipped':True,'after_nonoverlap':True,'same_children':a['children']==b['children'],'body_client_height':a['body']['height'],'body_scroll_height':a['body']['scrollHeight'],'body_scroll_top':a['body']['scrollTop']})
with (dst/'modal-browser-v4-cases.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys(),lineterminator="\n");w.writeheader();w.writerows(rows)
summary={k:x[k] for k in ['base','status','errors','externalRequests','future','keyboard']};summary.update(pairs=len(rows),naturalFits=sum(r['natural_fits'] for r in rows),changedLayout=sum(not r['same_children'] for r in rows),referenceMatched=560,beforeUnchanged=560,rawResult={'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()},sourceNote='Full raw JSON retained locally; canonical CSV derives every condition. Actual reproducibility scripts and mocks accompany this report; environment paths are snapshot-specific.')
(dst/'modal-browser-v4-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
for name in ['modal-browser-v4.mjs','modal-browser-v4.log','modal-manifest.json']:
 (dst/name).write_text('\n'.join(t.rstrip() for t in (src/name).read_text().splitlines())+'\n')
for name in ['sample.tsx','mock-api.ts','mock-firebase.ts']:
 (dst/('modal-fixture-'+name)).write_bytes((src/'modal-fixture'/name).read_bytes())
print('PASS560; fits448 unchanged; wrap112; reference560; evidenceCSV written')
