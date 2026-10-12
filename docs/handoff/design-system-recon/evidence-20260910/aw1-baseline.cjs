const fs=require('fs'),path=require('path'),os=require('os');
const {chromium}=require('/Users/tanizawashingo/salesanchor/frontend/node_modules/playwright');
const SRC=path.join(__dirname,'..','frontend','src');
const rd=f=>fs.readFileSync(path.join(SRC,f),'utf8');
const idx=rd('index.css').replace(/@import\s+"\.\/tokens\.css";/,()=>rd('tokens.css')).replace(/@import\s+"\.\/components\/field-size\.css";/,()=>rd('components/field-size.css'));
const order=['index.css (+@import tokens.css, components/field-size.css inlined at index.css:1-2)','components.css','company-forms.css','pages/inbox/InboxPage.css','components/FormField.css'];
const css=[idx,rd('components.css'),rd('company-forms.css'),rd('pages/inbox/InboxPage.css'),rd('components/FormField.css')].map(c=>`<style>${c}</style>`).join('\n');
const opt='<option>A</option><option>B</option>';
const els={
 karte:'<select id="t" class="right-panel-field">'+opt+'</select>',
 header:'<select id="t" class="page-header-select">'+opt+'</select>',
 tabbar:'<select id="t" class="inbox-platform-select">'+opt+'</select>',
 mold_md:'<select id="t" class="comp-select__control">'+opt+'</select>',
 mold_sm:'<select id="t" class="comp-select__control comp-select__control--sm">'+opt+'</select>',
};
const props=['padding-top','padding-right','padding-bottom','padding-left','border-top-width','border-right-width','border-bottom-width','border-left-width','border-top-style','border-right-style','border-bottom-style','border-left-style','border-top-color','border-right-color','border-bottom-color','border-left-color','border-top-left-radius','border-top-right-radius','border-bottom-right-radius','border-bottom-left-radius','font-size','font-family','font-weight','line-height','color','background-color','background-image','background-position','background-repeat','height','min-height','box-shadow','outline-style','outline-width','outline-color','appearance','cursor','transition-property','transition-duration','white-space'];
(async()=>{
 const base=os.homedir()+'/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell';
 const b=await chromium.launch({executablePath:base});
 console.log('chromium version:',b.version());
 const warns=[];
 const out={};
 for(const w of [1280,390]) for(const theme of ['light','dark']){
  const ctx=await b.newContext({viewport:{width:w,height:800}});
  const p=await ctx.newPage();
  p.on('console',m=>warns.push(m.type()+': '+m.text()));p.on('pageerror',e=>warns.push('pageerror '+e));
  for(const [name,html] of Object.entries(els)) for(const st of ['normal','focus','hover','disabled']){
   await p.setContent(`<!doctype html><html${theme==='dark'?' class="force-dark"':''}><head><meta charset="utf-8">${css}</head><body style="margin:20px">${html}</body></html>`);
   const h=p.locator('#t'); await p.mouse.move(1,1);
   if(st==='focus')await h.focus(); if(st==='hover')await h.hover(); if(st==='disabled')await h.evaluate(e=>e.disabled=true);
   await p.waitForTimeout(400);
   const r=await h.evaluate((e,props)=>{const c=getComputedStyle(e);const o={};for(const k of props)o[k]=c.getPropertyValue(k);o.offsetHeight=e.offsetHeight;o._active=document.activeElement===e;o._hover=e.matches(':hover');return o},props);
   (out[name]??={})[st]??={};(out[name][st][w]??={})[theme]=r;
  }
  await ctx.close();
 }
 const dark=await (async()=>{const p=await b.newPage();await p.setContent(`<html class="force-dark"><head>${css}</head><body><select id=t class="comp-select__control"></select></body></html>`);return p.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--bg-surface')+' | bg='+getComputedStyle(document.getElementById('t')).backgroundColor)})();
 fs.writeFileSync(path.join(__dirname,'aw1-baseline.json'),JSON.stringify({chromium:b.version(),cssOrder:order,warnings:warns,out},null,1));
 // md
 let md=`# AW-1 baseline\n\nchromium: ${b.version()}\n\nCSS order:\n${order.map((o,i)=>(i+1)+'. '+o).join('\n')}\n\nDark selector: \`:root.force-dark\` (index.css:220, tokens.css:577); html class force-dark. Probe: ${dark}\n\nWarnings/console: ${warns.length?warns.join('; '):'none'}\n\n## light / 1280 / normal\n\n`;
 const names=Object.keys(els);
 md+='| property | '+names.join(' | ')+' |\n|---|'+names.map(()=>'---|').join('')+'\n';
 for(const k of [...props,'offsetHeight']) md+=`| ${k} | `+names.map(n=>String(out[n].normal[1280].light[k]).replace(/\|/g,'\\|')).join(' | ')+' |\n';
 md+='\n## Properties that change (vs light/1280/normal baseline)\n';
 for(const n of names){
  md+=`\n### ${n}\n`;
  const b0=out[n].normal[1280].light;
  for(const st of Object.keys(out[n])) for(const w of [1280,390]) for(const th of ['light','dark']){
   if(st==='normal'&&w===1280&&th==='light')continue;
   const r=out[n][st][w][th];
   const d=[...props,'offsetHeight'].filter(k=>r[k]!==b0[k]).map(k=>`${k}: ${String(b0[k]).slice(0,60)} -> ${String(r[k]).slice(0,60)}`);
   md+=`- ${st}/${w}/${th}: ${d.length?d.join('; '):'(no change)'}\n`;
  }
 }
 fs.writeFileSync(path.join(__dirname,'aw1-baseline.md'),md);
 await b.close();
})();
