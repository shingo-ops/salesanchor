from pathlib import Path
from html import escape
import json
out=Path('/tmp/frontend-mold-recon-20260910')
defs=json.loads((out/'css-inventory.json').read_text())['defs']
def palette(dark):
 d={r['name']:r['value'] for r in defs if r['selector']==':root' and not r['conditions']}
 if dark:d.update({r['name']:r['value'] for r in defs if r['selector']==':root.force-dark' and not r['conditions']})
 return d
parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="1280" viewBox="0 0 1280 1280"><style>text{font-family:"Hiragino Sans","Yu Gothic",sans-serif}</style>']
def rect(x,y,w,h,color,r=0,stroke=None):parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}"'+(f' stroke="{stroke}"' if stroke else '')+'/>')
def text(x,y,s,c='#1a202c',size=16,weight=400):parts.append(f'<text x="{x}" y="{y}" fill="{c}" font-size="{size}" font-weight="{weight}">{escape(s)}</text>')
rect(0,0,1280,1280,'#f5f7fa');text(40,53,'Sales Anchor  共通部品の見本案',size=28,weight=600);text(40,88,'同じ用途の部品は、どのページでも同じ色・形に。',size=17);text(40,117,'外観の提案です。実画面の再現・動作検証ではありません。',c='#4a5568',size=14)
for i,dark in enumerate([False,True]):
 p=palette(dark);x=40+i*616;y=148;bg=p['--bg-surface'];primary_text=p['--bg-primary'] if dark else p['--on-accent'];body=p['--text-primary'];sub=p['--text-secondary'];border=p['--border'];danger=p['--danger'] if dark else p['--danger-text']
 rect(x,y,584,642,bg,8,border);text(x+24,y+40,'ダーク表示' if dark else 'ライト表示',body,21,600)
 text(x+24,y+82,'ボタン',body,16,600)
 for j,(label,fill,fg,outline) in enumerate([('保存',p['--accent'],primary_text,None),('キャンセル',bg,sub,border),('設定',bg,sub,None),('削除',bg,danger,p['--danger'])]):
  bx=x+24+j*137;rect(bx,y+100,122,36,fill,6,outline);text(bx+18,y+124,label,fg,14,500)
 text(x+24,y+161,'同じ角丸。用途は色と文言で区別。',sub,13)
 text(x+24,y+206,'トグル',body,16,600)
 for j,on in enumerate([False,True]):
  bx=x+24+j*210;by=y+226;rect(bx,by,40,22,p['--accent'] if on else border,11);parts.append(f'<circle cx="{bx+(29 if on else 11)}" cy="{by+11}" r="8" fill="{bg}"/>');text(bx+54,by+17,'オン' if on else 'オフ',body,14)
 text(x+24,y+275,'見える形と、押せる範囲を分けて確保。',sub,13)
 text(x+24,y+320,'データテーブル',body,16,600)
 ty=y+340;rect(x+24,ty,536,220,bg,8,border);rect(x+25,ty+1,534,43,p['--bg-subtle'],7)
 for xx,label in [(x+40,'取引先'),(x+255,'状態'),(x+446,'金額')]:text(xx,ty+28,label,p['--text-muted'],13,600)
 for n,(name,status,amount) in enumerate([('取引先 A','確認中','¥128,000'),('取引先 B','対応済み','¥64,000'),('取引先 C','確認中','¥32,000')]):
  ry=ty+44+n*56;parts.append(f'<path d="M{x+25} {ry} H{x+559}" stroke="{border}"/>');text(x+40,ry+34,name,sub,14);text(x+255,ry+34,status,sub,14);text(x+430,ry+34,amount,sub,14)
 text(x+24,y+600,'列の内容や操作が違っても、表の外観は共通。',sub,13)
text(40,830,'読みやすさの調整案',size=15,weight=600);text(40,858,'ダークの保存ボタンは濃い文字に。ライトの削除文字は濃い赤に。既存の色を用途別に参照します。',size=14,c='#4a5568')
parts.append('</svg>');(out/'proposed-controls.svg').write_text('\n'.join(parts))
print(out/'proposed-controls.svg')
