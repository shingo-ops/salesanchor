import json,subprocess,re,collections
p='/tmp/frontend-raw-buttons-20260911/raw-audit.json';j=json.load(open(p));old=json.loads(subprocess.check_output(['git','show',j['summary']['sha']+':docs/handoff/design-system-recon/evidence-20260910/button-semantic-audit.json'],cwd='/Users/tanizawashingo/salesanchor'))
norm=lambda s:re.sub(r'\s+','',s)
for r in j['rows']:
 r['legacySelectorKind']='btn-prefix' if re.search(r'["`\s]btn-',str(r['attrs']['className'])) else 'dedicated-btn-substring'
 matches=[o for o in old['rows'] if 'frontend/'+o['file']==r['file'] and norm(o['jsx'])==norm(r['element'])]
 if len(matches)==1:
  o=matches[0];r['existingBSA']={k:o.get(k) for k in ['id','destination','proposed_button_props','appearance_owner','appearance_plan']};r['classification']=o['destination'];r['classificationEvidence']='same file and whitespace-normalized JSX match to existing BSA'
 elif r['tag'] in ['a','Link']:r['classificationEvidence']='native anchor or router Link tag, href/to retained'
 else:r['classification']='unclassified-current';r['classificationEvidence']='no unique unchanged JSX match; requires current source classification'
j['summary']['selectorKinds']=dict(collections.Counter(r['legacySelectorKind'] for r in j['rows']))
j['summary']['classifications']=dict(collections.Counter(r['classification'] for r in j['rows']))
j['summary']['groups']=dict(collections.Counter('components' if r['file'].startswith('frontend/src/components/') else r['group'] for r in j['rows']))
j['summary']['allEventAttributes']=dict(collections.Counter(k for r in j['rows'] for k in r['attrs'] if re.match(r'on[A-Z]',k)))
j['summary']['allAriaAttributes']=dict(collections.Counter(k for r in j['rows'] for k in r['attrs'] if k.startswith('aria-')))
json.dump(j,open(p,'w'),ensure_ascii=False,indent=2)
print(j['summary']['classifications'])
for r in j['rows']:
 if r['classification']=='unclassified-current':print(r['file']+':'+str(r['line']),r['attrs'],re.sub(r'\s+',' ',r['element'])[-90:])
print('PANELS')
for r in j['rows']:
 if '/components/' in r['file']:print(r['file']+':'+str(r['line']),r.get('existingBSA',{}).get('id'),r['attrs'])
