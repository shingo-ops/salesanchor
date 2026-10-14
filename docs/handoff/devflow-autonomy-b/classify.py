# 監査用の分類（ADR-1015・design.md §3）。使い方:
# python3 classify.py 変更ファイルのJSON PR一覧のJSON 開始日 終了日 行データの出力先
# 日付は YYYY-MM-DD（UTC）。B は B-1/B-2/B-3 をまとめた区分。L は台帳だけ
import json,re,sys
from datetime import datetime
c=json.load(open(sys.argv[1]));fl={int(k):v for k,v in c['fl'].items()};wf={int(k):set(v) for k,v in c['wf'].items()}
tg=json.load(open(sys.argv[2]))
lo=datetime.fromisoformat(sys.argv[3]+'T00:00:00+00:00');hi=datetime.fromisoformat(sys.argv[4]+'T23:59:00+00:00')
def pd(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
tg=[p for p in tg if lo<=pd(p['mergedAt'])<=hi]
Apre=[r'^migrations/',r'^scripts/',r'^ops/',r'^tools/',r'^backend/tools/',r'^\.github/',r'^docs/adr/',
 r'^backend/app/tools/',r'^backend/app/tasks/',r'^frontend/scripts/',r'^backend/scripts/',r'^frontend/api-contract/']
def isA(f):
    p=f['filename']
    for a in Apre:
        if re.search(a,p):return True
    if p.lower().endswith('.sql'):return True
    if p.startswith('docs/ai-agents/') and not p.startswith('docs/ai-agents/lessons.d/'):return True
    if p=='docs/STANDARD-WORKFLOW.md' or p.split('/')[-1] in('CLAUDE.md','AGENTS.md'):return True
    if re.match(r'^docs/specs/',p) and p.split('/')[-1] in('ideal-state.md','kgi.md'):return True
    inscope=p.startswith('frontend/src/') or p.startswith('backend/app/') or '/' not in p
    if inscope and re.search(r'auth|oauth|session|permission|firebase|credential|secret|password|payment|billing|stripe',p,re.I):return True
    if inscope and re.search(r'token',p,re.I) and not p.endswith('.css'):return True
    if inscope and re.search(r'deploy|docker-compose',p):return True
    if f['status']=='added' and re.match(r'^(frontend/src/pages/|backend/app/routers/|backend/app/models)',p):return True
    return False
def isB(p):
    return bool(re.match(r'^(frontend/src/|backend/app/|backend/tests/|docs/|\.claude-pipeline/)',p) or (p.startswith('frontend/') and re.search(r'test|spec|stories',p)))
rows=[]
for p in sorted(tg,key=lambda p:-p['number']):
    n=p['number'];fs=fl[n]
    if any(isA(f) for f in fs):cl='A'
    elif all(isB(f['filename']) for f in fs):
        cl='L' if all(f['filename'].startswith('.claude-pipeline/') for f in fs) else 'B'
    else:cl='その他'
    pre=cl
    if cl=='B' and re.match(r'^\s*feat(:|\()',p['title'],re.I):cl='A'
    rows.append(dict(n=n,date=p['mergedAt'],cls=cl,pre_feat=pre,title=p['title']))
json.dump(rows,open(sys.argv[5],'w'),ensure_ascii=False)
from collections import Counter
print(len(rows),Counter(r['cls'] for r in rows))
# checks
auth9=['backend/app/routers/auth.py','backend/app/middleware/session_guard.py','backend/app/routers/discord_oauth.py','backend/app/services/oauth_state.py','backend/app/services/google_drive_oauth.py','frontend/src/contexts/AuthContext.tsx','frontend/src/lib/firebase-auth.ts','frontend/src/lib/firebase.ts','frontend/src/hooks/usePermissions.ts']
print('auth9',[(a,isA(dict(filename=a,status='modified'))) for a in auth9])
tk=[(r['n'],r['cls']) for r in rows if any(f['filename'].endswith('tokens.css') for f in fl[r['n']])]
print('tokens.css PRs',tk)
for n,_ in tk:print(n,[f['filename'] for f in fl[n] if isA(f)])
