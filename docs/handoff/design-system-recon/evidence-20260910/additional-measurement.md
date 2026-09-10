# 追加測定の再現手順

親: [追加調査](../recon.md#2026-09-10-追加調査と訂正)

CSS構文解析: `node /tmp/frontend-mold-recon-20260910/css_inventory.cjs`。全CSSを走査し条件を保持する。初回の条件を落とした重複候補は採用せず、以下の修正版が採用値。

```js
const fs=require('fs'),path=require('path'),postcss=require('/Users/tanizawashingo/salesanchor/frontend/node_modules/postcss');
const walk=d=>fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(d,e.name)):[path.join(d,e.name)]);
let defs=[],rules=[];
for(const file of walk('frontend/src').filter(f=>f.endsWith('.css'))){const root=postcss.parse(fs.readFileSync(file,'utf8'),{from:file});root.walkRules(r=>{if(/btn-|toggle|comp-table|data-table|\.card\b|comp-card/.test(r.selector))rules.push({file,line:r.source.start.line,selector:r.selector});});root.walkDecls(d=>{if(d.prop.startsWith('--'))defs.push({file,line:d.source.start.line,name:d.prop,value:d.value,selector:d.parent.selector||d.parent.name,conditions:(()=>{let a=[],p=d.parent;while(p){if(p.type==='atrule')a.unshift('@'+p.name+' '+p.params);p=p.parent;}return a;})()});});}
const main=defs.filter(d=>['frontend/src/index.css','frontend/src/tokens.css'].includes(d.file)&&d.selector===':root'&&d.conditions.length===0);const by={};main.forEach(d=>(by[d.name]??=[]).push(d));const duplicated=Object.entries(by).filter(([k,v])=>v.length>1);
const other=defs.filter(d=>!['frontend/src/index.css','frontend/src/tokens.css'].includes(d.file));
const out={defs,rules,duplicated,other};fs.writeFileSync('/tmp/frontend-mold-recon-20260910/css-inventory.json',JSON.stringify(out,null,2));console.log(JSON.stringify({definitions:defs.length,rootNames:Object.keys(by).length,duplicates:duplicated,otherDefinitions:other.length,other:other.slice(0,12)},null,2));

```

全src JSX集計は既存measurement.mdのコードについてbaseをfrontend/srcへ、出力名をall-src-jsx-inventory.jsonへ変更して実行。JSX開始要素のみ、stories/test/spec・見本ページ除外。
タグ別TSVは当該構文木結果のfilterで作成。生タグの総数は共有実装内部も含む。
ボタン構文分類: className無し、静的文字列、動的式を区別し、静的文字列のトークンにbtn-始まりがあればshared_btn_static。分類の意味はCSS参照経路であり、操作の意味分類ではない。
