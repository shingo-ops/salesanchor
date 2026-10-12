// AY-2b 追加: 非テキスト input を現状のまま保つ案。`.form-group input` / `:focus` を type 限定に絞り、宣言は変えない。
// before = 現行 CSS。after = components.css:19/30 の selector だけを絞った CSS（宣言・位置は不変）、pages-layout.css:246/255（login）は撤去。要素は変えない。
const fs=require("fs"),path=require("path"),os=require("os");
const W="/Users/tanizawashingo/worktrees/salesanchor/release-frontend-textfield-ay2b";
const {chromium}=require(path.join(W,"frontend/node_modules/playwright"));
const postcss=require(path.join(W,"frontend/node_modules/postcss"));
const rdRaw=f=>fs.readFileSync(path.join(W,f),"utf8");
const applied=require("./ay2-applied-css.json"),members=require("./ay2b-members.json");
const norm=s=>s.replace(/\s+/g," ").trim();
const TYPES=["checkbox","radio","range","file"];
const narrow=base=>TYPES.map(t=>base.replace(/ input(:focus)?$/,(m,f)=>` input[type="${t}"]${f||""}`));
const log=[];
function transform(file,text){
  if(file!=="frontend/src/components.css"&&file!=="frontend/src/pages-layout.css")return text;
  const root=postcss.parse(text);
  root.walkRules(r=>{const sels=r.selectors.map(norm);
    if(file.endsWith("components.css")&&sels.length===1&&(sels[0]===".form-group input"||sels[0]===".form-group input:focus")){r.selectors=narrow(sels[0]);log.push({file,line:r.source.start.line,from:sels[0],to:r.selectors.join(", "),decls:r.nodes.map(n=>n.prop+": "+n.value).join("; ")});}
    else if(file.endsWith("pages-layout.css")&&sels.length===1&&/^\.login-card \.form-group input(:focus)?$/.test(sels[0])){log.push({file,line:r.source.start.line,from:sels[0],to:"(削除)"});r.remove();}
  });return root.toString();}
const cache={};
function loadCss(file,mode){
  const raw=file.endsWith("/index.css")?rdRaw("frontend/src/index.css").replace(/@import\s+"\.\/tokens\.css";/,()=>rdRaw("frontend/src/tokens.css")).replace(/@import\s+"\.\/components\/field-size\.css";/,()=>rdRaw("frontend/src/components/field-size.css")):rdRaw(file);
  if(mode==="before")return raw;if(!(file in cache))cache[file]=transform(file,raw);return cache[file];}
const FORM_FIELD="frontend/src/components/FormField.css";
const cssFor=(order,mode)=>order.map(f=>`<style>${loadCss(f,mode)}</style>`).join("\n");
const orderFor=row=>{const o=["frontend/src/index.css",...applied.globalCss.filter(f=>!/index\.css$|tokens\.css$|field-size\.css$/.test(f)),...row.cssImports.forwardClosure,...row.cssImports.reverseImportersCss].filter((v,i,a)=>a.indexOf(v)===i&&v!==FORM_FIELD);o.push(FORM_FIELD);return o;};
const PROPS=["padding-top","padding-right","padding-bottom","padding-left","border-top-width","border-right-width","border-bottom-width","border-left-width","border-top-style","border-right-style","border-bottom-style","border-left-style","border-top-color","border-right-color","border-bottom-color","border-left-color","border-top-left-radius","border-top-right-radius","border-bottom-right-radius","border-bottom-left-radius","font-size","font-family","font-weight","line-height","color","background-color","height","min-height","max-height","width","min-width","max-width","outline-style","outline-width","outline-color","outline-offset","box-shadow","box-sizing","cursor","opacity","transition-property","transition-duration","appearance"];
const kebab=s=>s.replace(/[A-Z]/g,m=>"-"+m.toLowerCase());
async function measure(page,css,spec){
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8">${css}</head><body></body></html>`);
  await page.evaluate(spec=>{let p=document.body;for(const a of [...spec.anc].reverse()){const e=document.createElement(a.tag);if(a.classes.length)e.className=a.classes.join(" ");p.appendChild(e);p=e;}
    const t=document.createElement("input");t.id="t";if(spec.cls)t.className=spec.cls;if(spec.type)t.setAttribute("type",spec.type);if(spec.style)t.setAttribute("style",spec.style);p.appendChild(t);},spec);
  const g=()=>page.locator("#t").evaluate((e,props)=>{const c=getComputedStyle(e),o={};for(const k of props)o[k]=c.getPropertyValue(k);o.offsetHeight=e.offsetHeight;o.offsetWidth=e.offsetWidth;return o;},PROPS);
  await page.mouse.move(1,1);const out={normal:await g()};const h=page.locator("#t");await h.focus();await page.waitForTimeout(200);out.focus=await g();await h.evaluate(e=>e.blur());
  if(spec.disabledAttr){await h.evaluate(e=>{e.disabled=true;});await page.waitForTimeout(200);out.disabled=await g();}
  return out;}
const diff=(b,a)=>{const d={};for(const s of Object.keys(b)){const x={};for(const k of Object.keys(b[s]))if(b[s][k]!==a[s][k])x[k]=[b[s][k],a[s][k]];if(Object.keys(x).length)d[s]=x;}return d;};
(async()=>{
  const exe=path.join(os.homedir(),"Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell");
  const b=await chromium.launch({executablePath:exe});const page=await(await b.newContext({viewport:{width:1280,height:800}})).newPage();
  const nt=members.all.filter(m=>m.category==="non-text");const res={chromium:b.version(),items:[],log:null};
  for(const vw of [1280,375]){await page.setViewportSize({width:vw,height:800});
    for(const m of nt){const row=applied.rows.find(r=>r.file===m.file&&r.line===m.line);const order=orderFor(row);
      const inline=(row.inlineStyle.props||[]).filter(p=>p.prop[0]!=="(").map(p=>`${p.prop}:${String(p.value).replace(/^['"]|['"]$/g,"")}`).join(";");
      const sigs=row.chains.distinctSignatures.slice(0,5);
      for(const [i,sg] of sigs.entries()){const anc=sg.ancestorsInnermostFirst.map(e=>({tag:e.tag,classes:e.classes}));
        const spec={anc,cls:row.className.staticTokens.join(" "),type:row.type==="omitted"?null:row.type,style:inline,disabledAttr:!!row.attrs.disabled};
        const before=await measure(page,cssFor(order,"before"),spec),after=await measure(page,cssFor(order,"after"),spec);
        const hasFG=anc.some(e=>e.classes.includes("form-group"));
        res.items.push({vw,file:row.file,line:row.line,type:row.type,sig:i,hasFormGroupInChain:hasFG,matchedBy:m.hitDefinite.length?"確定":"祖先未確定のみ",diff:diff(before,after),states:Object.keys(before)});}}
    process.stderr.write(" @"+vw);}
  res.log=log;await b.close();fs.writeFileSync("ay2b-nontext-keep.json",JSON.stringify(res));
  const rule=log.filter(l=>l.to!=="(削除)");
  const nz=res.items.filter(i=>Object.keys(i.diff).length);
  const conf=res.items.filter(i=>i.matchedBy==="確定"),unc=res.items.filter(i=>i.matchedBy!=="確定");
  const cnt=(a)=>`${a.length} 測定（要素×祖先連鎖×幅2）`;
  let md=`## 6. 非テキスト input を現状のまま保つ案（\`.form-group input\` を type 限定に絞る）\n\n方法: ay2b-nontext-keep.cjs。before = 現行 CSS。after = components.css:19/30 の selector だけを下記に絞り（宣言と位置は不変）、pages-layout.css:246/255（login 規則）は撤去。要素・class・inline style・type は一切変えない。幅 1280/375、normal・focus（disabled 属性のある要素は disabled も）、${PROPS.length} プロパティ + offsetHeight/Width。\n\n絞った規則（postcss が書き換えた結果。宣言は元の \`.form-group input\` / \`:focus\` と同一）:\n\n\`\`\`css\n`;
  for(const l of rule)md+=`/* components.css:${l.line} 旧 ${l.from} */\n${l.to.replace(/, /g,",\n")} {\n  ${l.decls.split("; ").join(";\n  ")};\n}\n\n`;
  md+=`\`\`\`\n\n宣言の中身は取り除く案と同じ（§1 表の規則 1・2）。type を足すので特異度は (0,1,1) → (0,2,1)（\`:focus\` は (0,2,1) → (0,3,1)）に上がる。型セレクタなしだった旧規則が当たっていた type のうち、確定で当たっていたのは checkbox・radio・range・file の 4 種（color・hidden・submit 等は \`.form-group\` 配下に無いため含めていない。これは TSX の静的 type 属性による。\`dynamic\` type は §1 で text/url/email の 2 件のみ）。\n\n結果:\n\n| 区分 | 測定数 | 差のあった数 |\n|---|---|---|\n| 確定で当たる 9 要素 | ${cnt(conf)} | ${conf.filter(i=>Object.keys(i.diff).length).length} |\n| 祖先未確定だった 10 要素（§ ay2b-unresolved-trace.md で \`.form-group\` 祖先無しと確定） | ${cnt(unc)} | ${unc.filter(i=>Object.keys(i.diff).length).length} |\n\n`;
  if(nz.length){md+=`差のあった測定:\n\n`+nz.map(i=>`- ${i.vw} ${i.file.replace("frontend/src/","")}:${i.line} [${i.type}] sig${i.sig}: `+Object.entries(i.diff).map(([s,d])=>s+" "+Object.entries(d).map(([k,v])=>k+" "+v[0]+"→"+v[1]).join("; ")).join(" || ")).join("\n")+"\n\n";}
  else md+=`差分 0: 全 ${res.items.length} 測定で normal・focus（disabled 属性があるものは disabled も）とも差なし。\n\n`;
  md+=`確定 9 の内訳: ${[...new Set(conf.map(i=>i.file.replace("frontend/src/","")+":"+i.line+"["+i.type+"]"))].join(", ")}。確定のうち祖先連鎖に \`.form-group\` を持つ測定: ${conf.filter(i=>i.hasFormGroupInChain).length}/${conf.length}。\n`;
  const base=fs.readFileSync("ay2b-visual.md","utf8").split("\n## 6.")[0];
  fs.writeFileSync("ay2b-visual.md",base.replace(/\n+$/,"\n")+"\n"+md);
  console.log("\n"+md.slice(0,3000));
})();
