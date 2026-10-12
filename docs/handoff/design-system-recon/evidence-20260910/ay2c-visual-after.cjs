const fs=require("fs"),path=require("path");
const SNAP="/tmp/CC報告ファイル/ssot-ay2c/snap/frontend/src/";
const WT=require("path").resolve(__dirname,"../../../..")+"/frontend/src/";
const FE=require("path").resolve(__dirname,"../../../..")+"/frontend/node_modules/";
const {chromium}=require(FE+"playwright");const postcss=require(FE+"postcss");
const rdAt=B=>f=>fs.readFileSync(B+f,"utf8");
const rd=rdAt(SNAP),rdW=rdAt(WT);
let idx=rd("index.css").replace(/@import\s+["']\.\/tokens\.css["'];?/,()=>rd("tokens.css")).replace(/@import\s+["']\.\/components\/field-size\.css["'];?/,()=>rd("components/field-size.css"));
const globals=["loading-animations.css","sidebar.css","topbar.css","components.css","pages-layout.css","hub-shell.css","company-forms.css","responsive.css"];
const extra=fs.existsSync(SNAP+"components/Modal.css")?["components/Modal.css"]:[];
const mk=(r,B)=>{const idx=r("index.css").replace(/@import\s+["']\.\/tokens\.css["'];?/,()=>r("tokens.css")).replace(/@import\s+["']\.\/components\/field-size\.css["'];?/,()=>r("components/field-size.css"));const ex=fs.existsSync(B+"components/Modal.css")?["components/Modal.css"]:[];return[idx,...globals.map(r),...ex.map(r),r("components/FormField.css")].map(c=>`<style>${c}</style>`).join("\n");};
const BEFORE=mk(rd,SNAP),AFTER=mk(rdW,WT),dropped=0;
const PROPS=["padding-top","padding-right","padding-bottom","padding-left","border-top-width","border-right-width","border-bottom-width","border-left-width","border-top-style","border-top-color","border-right-color","border-bottom-color","border-left-color","border-top-left-radius","border-top-right-radius","border-bottom-right-radius","border-bottom-left-radius","font-size","font-family","font-weight","line-height","color","background-color","height","min-height","width","max-width","outline-style","outline-width","outline-color","outline-offset","box-shadow","box-sizing","cursor","opacity","transition-property","transition-duration","appearance"];
const reps=[ // id, host ancestors (root->parent of input), type, disabled, mold, kind
 {id:"T1 text  modal-content-wide<form-row (MergeLeadModal:146)",anc:["div.modal-content-wide","div.form-row"],type:"text",dis:false},
 {id:"T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452)",anc:["div.modal-content-wide","form.form-grid","div.form-row"],type:null,dis:false},
 {id:"T3 number modal-wide<form-grid<form-row (CompaniesPage:480)",anc:["div.modal-content-wide","form.form-grid","div.form-row"],type:"number",dis:false},
 {id:"T4 email modal-wide<form-grid<form-row (CompaniesPage:536)",anc:["div.modal-content-wide","form.form-grid","div.form-row"],type:"email",dis:false},
 {id:"T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38)",anc:["form.form-grid","div.form-row"],type:null,dis:true},
 {id:"T6 number+disabled form-grid<form-row (CompanyBasicTab:62)",anc:["form.form-grid","div.form-row"],type:"number",dis:true},
 {id:"T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53)",anc:["div","form","div.form-grid","div.form-row"],type:null,dis:true},
 {id:"C1 checkbox form-grid<form-row<label (ContactChannelForm:227)",anc:["div.form-grid","div.form-row","label"],type:"checkbox",dis:false,plain:true},
 {id:"C2 checkbox+disabled modal-wide<form-grid<form-row<label (CompanyAddressModal:147)",anc:["div.modal-content-wide","form.form-grid","div.form-row","label"],type:"checkbox",dis:true,plain:true},
 {id:"C3 checkbox+disabled div<form-grid<form-row<label (CompanyDiscordTab:42)",anc:["div","form","div.form-grid","div.form-row","label"],type:"checkbox",dis:true,plain:true},
 {id:"C4 checkbox div<form.form-grid<form-row<label (CompanyContactsTab:206)",anc:["div","form.form-grid","div.form-row","label"],type:"checkbox",dis:false,plain:true},
 {id:"C5 checkbox modal-wide<form-grid<form-row<label (ContactsPage:332)",anc:["div.modal-content-wide","form.form-grid","div.form-row","label"],type:"checkbox",dis:false,plain:true},
 {id:"M1 existing TextField modal-wide<form-row (MergeCompanyModal:158)",anc:["div.modal-content-wide","div.form-row"],type:"text",dis:false,mold:true},
 {id:"M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96)",anc:["div.modal-content-wide","form.form-grid","div.form-row"],type:null,dis:true,mold:true},
];
async function setup(page,css,rep,after){
 await page.setContent(`<!doctype html><html><head><meta charset="utf-8">${css}</head><body></body></html>`);
 await page.evaluate(([rep,after])=>{let p=document.body;for(const a of rep.anc){const[t,...c]=a.split(".");const e=document.createElement(t);if(c.length)e.className=c.join(" ");if(t==="div"&&!c.length){}p.appendChild(e);p=e;}
  if(rep.mold){const w=document.createElement("div");w.className="comp-field";p.appendChild(w);p=w;}
  const i=document.createElement("input");i.id="t";if(rep.type)i.setAttribute("type",rep.type);i.setAttribute("placeholder","ph");
  if(!rep.plain&&(rep.mold||after))i.className="comp-field__input";
  else if(rep.mold)i.className="comp-field__input";
  p.appendChild(i);},[rep,after]);}
const grab=page=>page.locator("#t").evaluate((e,props)=>{const c=getComputedStyle(e),o={};for(const k of props)o[k]=c.getPropertyValue(k);o["::placeholder color"]=getComputedStyle(e,"::placeholder").color;o.offsetHeight=e.offsetHeight;o.offsetWidth=e.offsetWidth;return o;},PROPS);
async function measure(page,css,rep,after){await setup(page,css,rep,after);const out={};await page.mouse.move(1,1);out.normal=await grab(page);const h=page.locator("#t");await h.focus();await page.waitForTimeout(250);out.focus=await grab(page);await h.evaluate(e=>e.blur());if(rep.dis){await h.evaluate(e=>{e.disabled=true;});await page.waitForTimeout(250);out.disabled=await grab(page);}return out;}
(async()=>{const b=await chromium.launch({executablePath:'/Users/tanizawashingo/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell'});const res={dropped,chromium:b.version(),rows:[]};
 for(const w of [1280,375]){const ctx=await b.newContext({viewport:{width:w,height:900}});const page=await ctx.newPage();
  for(const rep of reps){const bef=await measure(page,BEFORE,rep,false);const aft=await measure(page,AFTER,rep,true);
   const diffs={};for(const st of Object.keys(bef)){for(const k of Object.keys(bef[st]))if(bef[st][k]!==aft[st][k])(diffs[st]=diffs[st]||{})[k]=[bef[st][k],aft[st][k]];}
   res.rows.push({w,id:rep.id,diffs,before:bef,after:aft});}
  await ctx.close();}
 await b.close();fs.writeFileSync("/tmp/CC報告ファイル/ssot-ay2c/impl/ay2c-visual-after.json",JSON.stringify(res,null,1));
 let md=`# AY-2c 外観実測（Chromium ${res.chromium}、幅1280/375、light）\n\n手法: before=snap(origin/main c6c4fdc51)の CSS、after=実装後 worktree の実 CSS 実ファイル（postcss 除去の模擬ではない）。祖先連鎖を同じクラスで再構成した fixture に input を置き computed style を取得。旧記述: snap の CSS を読み込み、祖先連鎖を同じクラスで再構成した fixture に input を置き computed style を取得。before=現行 CSS（text系は class 無し、既存金型は comp-field__input）。after=company-forms.css の4規則群（:100 / :113 / :147-148 / :163-164、計 ${dropped} セレクタ）を postcss で除去、text系は class=comp-field__input のみ（type/disabled 保持）、checkbox は規則除去のみ。ファイルは書き換えていない。disabled は属性を持つ代表のみ disabled 状態を測定。\n\n`;
 for(const w of [1280,375]){md+=`## 幅 ${w}\n\n| 代表 | 状態 | プロパティ | before | after |\n|---|---|---|---|---|\n`;
  for(const r of res.rows.filter(x=>x.w===w)){let any=false;for(const st of Object.keys(r.before)){const d=r.diffs[st]||{};const ks=Object.keys(d);if(!ks.length){md+=`| ${r.id} | ${st} | (差なし) | | |\n`;continue;}for(const k of ks)md+=`| ${r.id} | ${st} | ${k} | ${d[k][0]} | ${d[k][1]} |\n`;}}
  md+="\n";}
 fs.writeFileSync("/tmp/CC報告ファイル/ssot-ay2c/impl/ay2c-visual-after.md",md);console.log("dropped",dropped);})();
