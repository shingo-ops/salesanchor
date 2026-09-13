from pathlib import Path
import urllib.request,re,json,hashlib,datetime
out=Path('/tmp/an-release'); out.mkdir(parents=True, exist_ok=True)
def get(url):
 import subprocess
 raw=subprocess.check_output(['curl','--fail','--silent','--show-error','--max-time','30','-H','Cache-Control: no-cache','-w','\n%{http_code}',url])
 body,status=raw.rsplit(b'\n',1)
 return int(status),body

status,html=get('https://app.salesanchor.jp/');asset=re.search(r'src="(/assets/[^\"]+\.js)"',html.decode())[1];assetstatus,b=get('https://app.salesanchor.jp'+asset);s=b.decode();anchors=list(re.finditer(re.escape('bots.newBot'),s));assert anchors
start=anchors[0].start();positions=[m.start() for m in re.finditer('form-actions',s[start:start+10000])][:2];assert len(positions)==2
excerpts=[s[start+p:start+p+430].split(']})')[0] for p in positions]
full=[s[m.start():m.start()+430].split(']})')[0] for m in re.finditer('form-actions',s) if '`/bots`' in s[m.start():m.start()+430]]
assert len(full)==1
excerpts.append(full[0])
for i,e in enumerate(excerpts):
 assert len(re.findall(r'variant:[`\"]secondary[`\"]',e))==1,e
 assert len(re.findall(r'variant:[`\"]primary[`\"]',e))==1,e
 assert len(re.findall(r'size:[`\"]md[`\"]',e))==2,e
 assert 'type:`button`' in e and 'type:`submit`' in e,e
 assert e.count('disabled:')==(2 if i==0 else 0),e
assert 'common.submitting' in excerpts[0] and 'bots.registerIssueKey' in excerpts[0]
assert '`/bots`' in excerpts[2]
api,raw=get('https://api.salesanchor.jp/api/health');health=json.loads(raw);assert health['status']=='ok';assert all(health[x]=='connected' for x in ['database','redis','celery'])
j={'checkedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'asset':asset,'assetHTTP':assetstatus,'sha256':hashlib.sha256(b).hexdigest(),'targetForms':3,'targetButtons':6,'excerpts':excerpts,'appHTTP':status,'apiHTTP':api,'apiPath':'/api/health','health':health,'limits':'公開資産とhealthの読取確認。本番認証付きフォーム送信・PO目視は未実施。'}
(out/'an-production-verification.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');print(json.dumps(j,ensure_ascii=False,indent=2))
