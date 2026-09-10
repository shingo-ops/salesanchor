from pathlib import Path
import json
p=Path(__file__).resolve().parent
defs=json.loads((p/'css-inventory.json').read_text())['defs']
def lum(h):
 a=[int(h[i:i+2],16)/255 for i in (1,3,5)]
 a=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in a]
 return sum(x*w for x,w in zip(a,[.2126,.7152,.0722]))
def ratio(a,b):
 lo,hi=sorted([lum(a),lum(b)]);return (hi+.05)/(lo+.05)
rows=[]
for theme in ['light','dark']:
 d={r['name']:r['value'] for r in defs if r['selector']==':root' and not r['conditions']}
 if theme=='dark': d.update({r['name']:r['value'] for r in defs if r['selector']==':root.force-dark' and not r['conditions']})
 for variant in ['primary','secondary','ghost','danger','outline','tab']:
  for state in ['normal','hover','active']+(['selected'] if variant=='tab' else []):
   for surface in ['--bg-primary','--bg-surface','--bg-subtle','--bg-hover','--bg-active']:
    bg=d[surface];fg=d['--text-primary']
    if variant=='primary':
     fg=d['--bg-primary'] if theme=='dark' else d['--on-accent']
     bg=d['--accent'] if state=='normal' else (d['--link'] if theme=='dark' else d['--accent-hover'])
    elif variant=='danger':
     fg=d['--danger-text']
     if state!='normal': bg=d['--danger-bg']
    elif variant=='tab' and state=='selected':
     bg=d['--link-active-bg'];fg=d['--text-primary'] if theme=='dark' else d['--accent']
    else:
     if variant in ['secondary','tab']:fg=d['--text-secondary']
     if variant=='secondary' and state=='normal':bg=d['--bg-surface']
     if state=='hover':bg=d['--bg-subtle']
     if state=='active':bg=d['--bg-hover']
    n=ratio(fg,bg);rows.append(dict(theme=theme,variant=variant,state=state,surface=surface,fg=fg,bg=bg,ratio=n,passNormalText=n>=4.5))
(p/'button-color-matrix.json').write_text(json.dumps(rows,indent=2))
bad=[r for r in rows if not r['passNormalText']]
print(json.dumps({'pairs':len(rows),'failed':bad,'minimum':min(rows,key=lambda r:r['ratio'])},indent=2))
