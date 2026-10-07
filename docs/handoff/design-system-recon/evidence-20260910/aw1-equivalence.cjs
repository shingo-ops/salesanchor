// AW-1 外観同等性: 旧ページ class の select と新 variant の select を同じページに置き computed style を比較する。
// 実行: node docs/handoff/design-system-recon/evidence-20260910/aw1-equivalence.cjs（作業台のルートから）
const fs=require('fs'),path=require('path'),os=require('os');
const {chromium}=require('/Users/tanizawashingo/salesanchor/frontend/node_modules/playwright');
const ROOT=path.resolve(__dirname,'..','..','..','..');
const SRC=path.join(ROOT,'frontend','src');
const rd=f=>fs.readFileSync(path.join(SRC,f),'utf8');
const idx=rd('index.css').replace(/@import\s+"\.\/tokens\.css";/,()=>rd('tokens.css')).replace(/@import\s+"\.\/components\/field-size\.css";/,()=>rd('components/field-size.css'));
const order=['index.css (+@import tokens.css, components/field-size.css inlined)','components.css','company-forms.css','pages/inbox/InboxPage.css','components/FormField.css'];
const css=[idx,rd('components.css'),rd('company-forms.css'),rd('pages/inbox/InboxPage.css'),rd('components/FormField.css')].map(c=>`<style>${c}</style>`).join('\n');
const opt='<option>A</option><option>B</option>';
const pairs={
 karte:['right-panel-field','comp-select__control comp-select--karte'],
 header:['page-header-select','comp-select__control comp-select--header'],
 tabbar:['inbox-platform-select','comp-select__control comp-select--tabbar'],
};
const props=['padding-top','padding-right','padding-bottom','padding-left','border-top-width','border-right-width','border-bottom-width','border-left-width','border-top-style','border-right-style','border-bottom-style','border-left-style','border-top-color','border-right-color','border-bottom-color','border-left-color','border-top-left-radius','border-top-right-radius','border-bottom-right-radius','border-bottom-left-radius','font-size','font-family','font-weight','line-height','color','background-color','background-image','background-position','background-repeat','height','min-height','box-shadow','outline-style','outline-width','outline-color','appearance','cursor','transition-property','transition-duration','white-space'];
const extra=['opacity'];
const all=[...props,...extra,'offsetHeight'];
(async()=>{
 const base=os.homedir()+'/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell';
 const b=await chromium.launch({executablePath:base});
 const warns=[];
 const out={};const diffs=[];const expectedDisabled=[];let conds=0;
 const baseline=JSON.parse(fs.readFileSync(path.join(__dirname,'aw1-baseline.json'),'utf8')).out;
 const baseDiffs=[];
 for(const w of [1280,390]) for(const theme of ['light','dark']){
  const ctx=await b.newContext({viewport:{width:w,height:800}});
  const p=await ctx.newPage();
  p.on('console',m=>warns.push(m.type()+': '+m.text()));p.on('pageerror',e=>warns.push('pageerror '+e));
  for(const [name,[oldC,newC]] of Object.entries(pairs)) for(const st of ['normal','focus','hover','disabled']){
   const html=`<select id="old" class="${oldC}">${opt}</select><br><select id="new" class="${newC}">${opt}</select>`;
   await p.setContent(`<!doctype html><html${theme==='dark'?' class="force-dark"':''}><head><meta charset="utf-8">${css}</head><body style="margin:20px">${html}</body></html>`);
   const res={};
   for(const id of ['old','new']){
    const h=p.locator('#'+id); await p.mouse.move(1,1);
    await h.evaluate(e=>{e.disabled=false;e.blur()});
    if(st==='focus')await h.focus(); if(st==='hover')await h.hover(); if(st==='disabled')await h.evaluate(e=>e.disabled=true);
    await p.waitForTimeout(400);
    res[id]=await h.evaluate((e,all)=>{const c=getComputedStyle(e);const o={};for(const k of all){if(k!=='offsetHeight')o[k]=c.getPropertyValue(k)}o.offsetHeight=e.offsetHeight;o._active=document.activeElement===e;o._hover=e.matches(':hover');return o},[...props,...extra,'offsetHeight']);
    await h.evaluate(e=>{e.disabled=false;e.blur()});
   }
   conds++;
   const d=all.filter(k=>res.old[k]!==res.new[k]).map(k=>({prop:k,old:res.old[k],new:res.new[k]}));
   const stateMismatch=res.old._active!==res.new._active||res.old._hover!==res.new._hover;
   const bo=baseline[name]?.[st]?.[w]?.[theme];
   const bd=bo?all.filter(k=>k!=='opacity'&&String(bo[k])!==String(res.old[k])).map(k=>({prop:k,baseline:bo[k],old:res.old[k]})):[{prop:'(baseline missing)'}];
   if(bd.length)baseDiffs.push({name,st,w,theme,diffs:bd});
   (out[name]??={})[st]??={};(out[name][st][w]??={})[theme]={old:res.old,new:res.new,match:d.length===0&&!stateMismatch,diffs:d,stateMismatch};
   if(d.length||stateMismatch)(st==='disabled'?expectedDisabled:diffs).push({name,st,w,theme,diffs:d,stateMismatch});
  }
  await ctx.close();
 }

 // DPR2 ピクセル比較: 旧・新を別ページに同じ位置・同じ幅で描き、要素の clip スクリーンショットを in-page canvas で比較する
 const pixel=[];
 for(const theme of ['light','dark']){
  const ctx=await b.newContext({viewport:{width:1280,height:800},deviceScaleFactor:2});
  const p=await ctx.newPage();
  for(const [name,[oldC,newC]] of Object.entries(pairs)) for(const st of ['normal','focus','hover']){
   const shots={};
   for(const [id,cls] of [['old',oldC],['new',newC]]){
    await p.setContent(`<!doctype html><html${theme==='dark'?' class="force-dark"':''}><head><meta charset="utf-8">${css}</head><body style="margin:20px"><select id="t" class="${cls}" style="width:200px">${opt}</select></body></html>`);
    const h=p.locator('#t'); await p.mouse.move(1,1);
    if(st==='focus')await h.focus(); if(st==='hover')await h.hover();
    await p.waitForTimeout(400);
    const box=await h.boundingBox();
    const clip={x:box.x-6,y:box.y-6,width:box.width+12,height:box.height+12};
    shots[id]=(await p.screenshot({clip})).toString('base64');
   }
   const cmp=await p.evaluate(async(s)=>{
    const load=b64=>new Promise((res,rej)=>{const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src='data:image/png;base64,'+b64});
    const [a,c]=await Promise.all([load(s.old),load(s.new)]);
    if(a.width!==c.width||a.height!==c.height)return {sizeMismatch:[a.width,a.height,c.width,c.height]};
    const px=i=>{const cv=document.createElement('canvas');cv.width=i.width;cv.height=i.height;const g=cv.getContext('2d');g.drawImage(i,0,0);return g.getImageData(0,0,i.width,i.height).data};
    const da=px(a),dc=px(c);let n=0;for(let k=0;k<da.length;k+=4){if(da[k]!==dc[k]||da[k+1]!==dc[k+1]||da[k+2]!==dc[k+2]||da[k+3]!==dc[k+3])n++}
    return {width:a.width,height:a.height,diffPixels:n};
   },shots);
   pixel.push({name,st,theme,...cmp});
  }
  await ctx.close();
 }
 const pixelBad=pixel.filter(r=>r.sizeMismatch||r.diffPixels!==0);
 const ver=b.version();
 fs.writeFileSync(path.join(__dirname,'aw1-equivalence.json'),JSON.stringify({chromium:ver,cssOrder:order,conditions:conds,warnings:warns,baselineMismatchVsOld:baseDiffs,expectedDisabledDiffs:expectedDisabled,pixelDpr2:pixel,out},null,1));
 let md=`# AW-1 外観同等性\n\nchromium ${ver}／条件数 ${conds}（3種類×4状態×2幅×2テーマ。各条件で旧・新の ${all.length} 項目を比較）／console 警告: ${warns.length?warns.join('; '):'なし'}\n\n旧要素と aw1-baseline.json の差（opacity 以外）: ${baseDiffs.length?JSON.stringify(baseDiffs):'0件'}\n\n`;
 md+=`判定対象: normal/focus/hover（disabled は判定から除外）\n\n`;
 if(!diffs.length)md+='差分0\n';
 else{md+=`差分あり: ${diffs.length} 条件\n\n`;for(const d of diffs){md+=`- ${d.name}/${d.st}/${d.w}/${d.theme}${d.stateMismatch?' [hover/focus 状態不一致]':''}: `+d.diffs.map(x=>`${x.prop}: 旧=${String(x.old).slice(0,70)} 新=${String(x.new).slice(0,70)}`).join('; ')+'\n';}}
 md+=`\n## 想定差分（disabled 状態。13 利用先は disabled を使わず、使う場合は金型の disabled に従う）\n\n`;
 if(!expectedDisabled.length)md+='なし\n';
 else{md+=`${expectedDisabled.length} 条件\n\n`;for(const d of expectedDisabled){md+=`- ${d.name}/${d.st}/${d.w}/${d.theme}: `+d.diffs.map(x=>`${x.prop}: 旧=${String(x.old).slice(0,40)} 新=${String(x.new).slice(0,40)}`).join('; ')+'\n';}}
 md+=`\n## DPR2 ピクセル比較（幅1280・normal/focus/hover・light/dark、旧新とも幅200px固定の clip スクリーンショット）\n\n| 種類 | 状態 | テーマ | サイズ(px) | 差分ピクセル数 |\n|---|---|---|---|---|\n`;
 for(const r of pixel)md+=`| ${r.name} | ${r.st} | ${r.theme} | ${r.sizeMismatch?'サイズ不一致 '+r.sizeMismatch.join(','):r.width+'x'+r.height} | ${r.sizeMismatch?'-':r.diffPixels} |\n`;
 md+=`\nピクセル判定: ${pixelBad.length?'差分あり '+pixelBad.length+' 件':'差分0（'+pixel.length+' 件）'}\n`;
 fs.writeFileSync(path.join(__dirname,'aw1-equivalence.md'),md);
 console.log(md);
 await b.close();
})();
