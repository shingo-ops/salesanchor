// AX-1 外観一致: ラベル付き Textarea 相当(L)と裸の TextareaControl 相当(B)の textarea の computed style を size×状態で比較する。
// 実行: node docs/handoff/design-system-recon/evidence-20260910/ax1-visual.cjs（作業台のルートから）
const fs=require('fs'),path=require('path'),os=require('os');
const ROOT=path.resolve(__dirname,'..','..','..','..');
const {chromium}=require(path.join(ROOT,'frontend','node_modules','playwright'));
const SRC=path.join(ROOT,'frontend','src');
const rd=f=>fs.readFileSync(path.join(SRC,f),'utf8');
const idx=rd('index.css').replace(/@import\s+"\.\/tokens\.css";/,()=>rd('tokens.css')).replace(/@import\s+"\.\/components\/field-size\.css";/,()=>rd('components/field-size.css'));
const css=[idx,rd('components/FormField.css')].map(c=>`<style>${c}</style>`).join('\n');
const props=['padding-top','padding-right','padding-bottom','padding-left','border-top-width','border-right-width','border-bottom-width','border-left-width','border-top-style','border-right-style','border-bottom-style','border-left-style','border-top-color','border-right-color','border-bottom-color','border-left-color','border-top-left-radius','border-top-right-radius','border-bottom-right-radius','border-bottom-left-radius','font-size','font-family','line-height','min-height','height','width','resize','background-color','color'];
const sizes=['sm','md','lg'];
const states=['normal','focus','disabled'];
(async()=>{
 const base=os.homedir()+'/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell';
 const b=await chromium.launch({executablePath:base});
 const ctx=await b.newContext({viewport:{width:1280,height:800}});
 const p=await ctx.newPage();
 const warns=[];p.on('console',m=>warns.push(m.type()+': '+m.text()));p.on('pageerror',e=>warns.push('pageerror '+e));
 const out={};const rows=[];
 for(const size of sizes) for(const st of states){
  const q=size==='md'?'':size;
  const L=`<div class="comp-field${q?' comp-field--'+q:''}"><textarea id="t" class="comp-field__textarea"></textarea></div>`;
  const B=`<textarea id="t" class="comp-field__textarea${q?' comp-field__textarea--'+q:''}"></textarea>`;
  const res={};
  for(const [k,html] of [['L',L],['B',B]]){
   await p.setContent(`<!doctype html><html><head><meta charset="utf-8">${css}</head><body>${html}</body></html>`);
   const h=p.locator('#t');
   if(st==='focus')await h.focus();
   if(st==='disabled')await h.evaluate(e=>e.disabled=true);
   await p.waitForTimeout(300);
   res[k]=await h.evaluate((e,ps)=>{const c=getComputedStyle(e);const o={};for(const x of ps)o[x]=c.getPropertyValue(x);o._active=document.activeElement===e;return o},props);
  }
  const diffs=[...props,'_active'].filter(x=>res.L[x]!==res.B[x]).map(x=>({prop:x,L:res.L[x],B:res.B[x]}));
  out[size+'/'+st]={L:res.L,B:res.B,diffs};
  rows.push({size,st,n:diffs.length,diffs});
 }
 const ver=b.version();
 const total=rows.reduce((a,r)=>a+r.n,0);
 let md=`# AX-1 外観一致（TextareaControl 裸 B ＝ ラベル付き Textarea 内 L）\n\nchromium ${ver}／幅1280／light／比較項目 ${props.length}（+focus 状態）／console 警告: ${warns.length?warns.join('; '):'なし'}\n\n| size | 状態 | 差分件数 |\n|---|---|---|\n`;
 for(const r of rows)md+=`| ${r.size} | ${r.st} | ${r.n} |\n`;
 md+=`\n合計差分: ${total}\n`;
 if(total){md+='\n## 差分の値\n\n| size/状態 | 項目 | L | B |\n|---|---|---|---|\n';for(const r of rows)for(const d of r.diffs)md+=`| ${r.size}/${r.st} | ${d.prop} | ${d.L} | ${d.B} |\n`;}
 fs.writeFileSync(path.join(__dirname,'ax1-visual.json'),JSON.stringify({chromium:ver,warnings:warns,total,out},null,1));
 fs.writeFileSync(path.join(__dirname,'ax1-visual.md'),md);
 console.log(md);
 await b.close();
})();
