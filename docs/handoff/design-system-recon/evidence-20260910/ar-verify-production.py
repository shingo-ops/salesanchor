from pathlib import Path
import subprocess,json,re,hashlib,datetime,shlex
expected='8862732e494ac5d92287d57aeea808cee05d3151'
def fetch(url,name):
 p=Path('/tmp')/name
 result=subprocess.run(['curl','--fail','--silent','--show-error','--max-time','30','--output',str(p),'--write-out','%{http_code}',url],text=True,capture_output=True,check=True)
 return result.stdout,p.read_bytes()
status,html=fetch('https://app.salesanchor.jp/','ar-live-index.html')
assets=re.findall(r'<script[^>]*src="(/assets/[^\"]+\.js)"',html.decode())
assert len(assets)==1,assets
asset=assets[0];assert re.fullmatch(r'/assets/[A-Za-z0-9_.-]+\.js',asset)
assetstatus,js=fetch('https://app.salesanchor.jp'+asset,'ar-live-asset.js')
apistatus,raw=fetch('https://api.salesanchor.jp/api/health','ar-live-health.json');health=json.loads(raw)
remote='git -C /home/ubuntu/salesanchor rev-parse HEAD && cd /home/ubuntu/salesanchor && docker compose exec -T frontend sha256sum /usr/share/nginx/html/index.html '+shlex.quote('/usr/share/nginx/html'+asset)
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=10','-i','/Users/tanizawashingo/.ssh/manual-only/id_ed25519','ubuntu@49.212.137.46',remote],capture_output=True,text=True,check=True)
lines=r.stdout.strip().splitlines();assert len(lines)==3,lines
record={'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expectedCommit':expected,'deployedCommit':lines[0],'appHTTP':status,'asset':asset,'assetHTTP':assetstatus,'apiHTTP':apistatus,'health':{k:health.get(k) for k in ['status','database','redis','celery']},'publicIndexSHA256':hashlib.sha256(html).hexdigest(),'containerIndexSHA256':lines[1].split()[0],'publicAssetSHA256':hashlib.sha256(js).hexdigest(),'containerAssetSHA256':lines[2].split()[0],'authenticatedUI':'skipped at PO request; unverified'}
record['pass']=lines[0]==expected and all(s=='200' for s in [status,assetstatus,apistatus]) and health.get('status')=='ok' and all(health.get(k)=='connected' for k in ['database','redis','celery']) and record['publicIndexSHA256']==record['containerIndexSHA256'] and record['publicAssetSHA256']==record['containerAssetSHA256']
Path('/tmp/ar-production-verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,ensure_ascii=False,indent=2));assert record['pass']
