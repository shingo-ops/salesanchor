// AY-1 外観一致: ラベル付き TextField 相当(L)と裸の TextFieldControl 相当(B)の input の computed style を 幅×size×状態で比較する。
// 実行: node docs/handoff/design-system-recon/evidence-20260910/ay1-visual.cjs（作業台のルートから）
const fs=require('fs'),path=require('path'),os=require('os');
const ROOT=path.resolve(__dirname,'..','..','..','..');
const {chromium}=require(path.join(ROOT,'frontend','node_modules','playwright'));
const SRC=path.join(ROOT,'frontend','src');
const rd=f=>fs.readFileSync(path.join(SRC,f),'utf8');
const idx=rd('index.css').replace(/@import\s+"\.\/tokens\.css";/,()=>rd('tokens.css')).replace(/@import\s+"\.\/components\/field-size\.css";/,()=>rd('components/field-size.css'));
const css=[idx,rd('components/FormField.css')].map(c=>`<style>${c}</style>`).join('\n');
const props=['padding-top','padding-right','padding-bottom','padding-left','border-top-width','border-right-width','border-bottom-width','border-left-width','border-top-style','border-right-style','border-bottom-style','border-left-style','border-top-color','border-right-color','border-bottom-color','border-left-color','border-top-left-radius','border-top-right-radius','border-bottom-right-radius','border-bottom-left-radius','font-size','font-family','line-height','min-height','height','width','background-color','color'];
const sizes=['sm','md','lg'];
const states=['normal','focus','disabled'];
const widths=[1280,375];
(async()=>{
 const base=os.homedir()+'/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell';
 const b=await chromium.launch({executablePath:base});
 const p0=null;
 const warns=[];
 const out={};const rows=[];
 for(const W of widths){ const ctx=await b.newContext({viewport:{width:W,height:800}}); const p=await ctx.newPage(); p.on('console',m=>warns.push(m.type()+': '+m.text())); p.on('pageerror',e=>warns.push('pageerror '+e));
 for(const size of sizes) for(const st of states){
  const q=size==='md'?'':size;
  const L=`<div class="comp-field${q?' comp-field--'+q:''}"><input id="t" class="comp-field__input"></div>`;
  const B=`<input id="t" class="comp-field__input${q?' comp-field__input--'+q:''}">`;
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
  out[W+'/'+size+'/'+st]={L:res.L,B:res.B,diffs};
  rows.push({W,size,st,n:diffs.length,diffs});
 }
 await ctx.close(); }

 // 原因確認: ① 375/sm でモバイル @media を除いた CSS、② 1280/md で L の親 .comp-field を display:block
 const ff=rd('components/FormField.css');
 const mediaRe=/@media \(max-width: 767px\) \{\s*\.comp-field__input,\s*\.comp-field__select,\s*\.comp-select__control \{\s*min-height: var\(--comp-input-height-mobile\);\s*\}\s*\}/;
 const mediaFound=mediaRe.test(ff);
 const cssNoMedia=[idx,ff.replace(mediaRe,'')].map(c=>`<style>${c}</style>`).join('\n');
 const measure=async(W,html,cssx,extra)=>{const cx=await b.newContext({viewport:{width:W,height:800}});const pg=await cx.newPage();
  await pg.setContent(`<!doctype html><html><head><meta charset="utf-8">${cssx}${extra||''}</head><body>${html}</body></html>`);
  const r=await pg.locator('#t').evaluate((e,ps)=>{const c=getComputedStyle(e);const o={};for(const x of ps)o[x]=c.getPropertyValue(x);return o},props);await cx.close();return r;};
 const Lh=q=>`<div class="comp-field${q?' comp-field--'+q:''}"><input id="t" class="comp-field__input"></div>`;
 const Bh=q=>`<input id="t" class="comp-field__input${q?' comp-field__input--'+q:''}">`;
 const dif=(x,y)=>props.filter(k=>x[k]!==y[k]).map(k=>`${k}: ${x[k]} / ${y[k]}`);
 const c1L=await measure(375,Lh('sm'),cssNoMedia), c1B=await measure(375,Bh('sm'),cssNoMedia);
 const c2L0=await measure(1280,Lh(''),css), c2L1=await measure(1280,Lh(''),css,'<style>.comp-field{display:block}</style>'), c2B=await measure(1280,Bh(''),css);
 const d1=dif(c1L,c1B), d2=dif(c2L1,c2B);
 const ok1=mediaFound&&d1.length===0, ok2=c2L0['min-height']==='auto'&&c2L1['min-height']==='0px'&&d2.length===0;
 const cause=`\n## 原因確認\n\n① 幅375/sm/通常: FormField.css からモバイル @media (max-width:767px) ブロックを除去（除去対象を検出: ${mediaFound}）して L と B を再測定。L: min-height ${c1L['min-height']} height ${c1L.height} / B: min-height ${c1B['min-height']} height ${c1B.height}。差分項目: ${d1.length?d1.join('; '):'0件'} → ${ok1?'B が L と一致（想定どおり）':'想定と不一致'}\n\n② 幅1280/md/通常: L の親 .comp-field が flex（既定）のとき L min-height=${c2L0['min-height']}。親を display:block にすると L min-height=${c2L1['min-height']}（B は ${c2B['min-height']}）。display:block 後の L と B の差分項目: ${d2.length?d2.join('; '):'0件'} → ${ok2?'想定どおり（flex 子の computed 値の差）':'想定と不一致'}\n`;
 const exc=`\n## 既知の例外（設計 §AY 受入の①②）\n\n- ① 幅375px（767px以下）の sm: 裸の本体はモバイル用タップ領域の規則（FormField.css の @media (max-width:767px)）が後勝ちで min-height 44px（height 44px）。L は 28px（height 30.3906px）。\n- ② 幅1280px の md: L の min-height は親 .comp-field が flex のため computed で auto、裸の本体は 0px。height は両者 39.6094px で同じ。\n`;
 const causeOk=ok1&&ok2;
 const ver=b.version();
 const total=rows.reduce((a,r)=>a+r.n,0);
 let md=`# AY-1 外観一致（TextFieldControl 裸 B ＝ ラベル付き TextField 内 L）\n\nchromium ${ver}／幅1280と375／light／比較項目 ${props.length}（+focus 状態）／console 警告: ${warns.length?warns.join('; '):'なし'}\n\n| 幅 | size | 状態 | 差分件数 | height(L/B) | min-height(L/B) |\n|---|---|---|---|---|---|\n`;
 for(const r of rows){const o=out[r.W+'/'+r.size+'/'+r.st];md+=`| ${r.W} | ${r.size} | ${r.st} | ${r.n} | ${o.L.height}/${o.B.height} | ${o['L']['min-height']}/${o['B']['min-height']} |\n`;}
 md+=`\n合計差分: ${total}\n`;
 if(total){md+='\n## 差分の値\n\n| 幅/size/状態 | 項目 | L | B |\n|---|---|---|---|\n';for(const r of rows)for(const d of r.diffs)md+=`| ${r.W}/${r.size}/${r.st} | ${d.prop} | ${d.L} | ${d.B} |\n`;}
 md+=cause+(causeOk&&total===9?exc:'\n（原因確認が想定と不一致のため例外記録なし）\n');
 fs.writeFileSync(path.join(__dirname,'ay1-visual.json'),JSON.stringify({chromium:ver,warnings:warns,total,causeOk,out},null,1));
 fs.writeFileSync(path.join(__dirname,'ay1-visual.md'),md);
 console.log(md);
 await b.close();
})();
