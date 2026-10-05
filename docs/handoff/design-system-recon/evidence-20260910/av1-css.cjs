const fs=require('fs'),path=require('path');
const walk=d=>fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(d,e.name)):[path.join(d,e.name)]);
const css=walk(process.argv[2]+'/frontend/src').filter(f=>f.endsWith('.css'));
const toks=process.argv.slice(4);const OUT=process.argv[3];
let out='';
for(const t of toks){
  out+=`\n### .${t}\n`;let found=0;
  const re=new RegExp('(^|[^\\w-])\\.'+t.replace(/[-]/g,'\\-')+'(?![\\w-])');
  for(const f of css){const s=fs.readFileSync(f,'utf8');
    // naive rule scan: selector{decls}
    const rr=/([^{}]+)\{([^{}]*)\}/g;let m;
    while((m=rr.exec(s))){const sel=m[1].replace(/\/\*[\s\S]*?\*\//g,'').trim();if(!re.test(sel))continue;
      const line=s.slice(0,m.index+m[0].indexOf(m[1].trim())).split('\n').length;
      found++;out+=`- ${path.relative(process.argv[2],f)}:${line}\n  \`${sel.replace(/\s+/g,' ')}\` { ${m[2].replace(/\s+/g,' ').trim()} }\n`;}}
  if(!found)out+='- 該当ルールなし（このsnapshotのCSSに無い）\n';
}
fs.writeFileSync(OUT+'/av1-css-rules.md','# AV-1 page select class CSS\n\n基準 SHA: '+(process.env.BASE_SHA||'(unset)')+' / TypeScript '+(process.env.TS_VERSION||'-')+'\n'+out);
console.log(out);
