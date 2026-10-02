const fs=require('fs'),path=require('path');
const [root,tsRoot,outDir]=process.argv.slice(2);
const ts=require(path.join(tsRoot,'node_modules/typescript'));
const rows=JSON.parse(fs.readFileSync(path.join(outDir,'av0-input-audit.json'),'utf8')).rows.filter(r=>r.tag==='select'&&r.scope==='page');
const byFile={};rows.forEach(r=>(byFile[r.file]=byFile[r.file]||[]).push(r));
const out=[];
const cap=(s,n)=>s.length>n?s.slice(0,n)+'…[cut]':s;
for(const [file,rs] of Object.entries(byFile)){
  const src=fs.readFileSync(path.join(root,file),'utf8');
  const sf=ts.createSourceFile(file,src,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
  const sels=[];
  const find=n=>{if(ts.isJsxElement(n)&&n.openingElement.tagName.getText(sf)==='select')sels.push(n);ts.forEachChild(n,find)};find(sf);
  const decl=name=>{let f=null;const v=n=>{if(f)return;if(ts.isVariableDeclaration(n)&&n.name.getText(sf)===name&&n.initializer)f=n.initializer.getText(sf);else if(ts.isFunctionDeclaration(n)&&n.name&&n.name.text===name)f=n.getText(sf);ts.forEachChild(n,v)};v(sf);return f};
  for(const r of rs){
    const el=sels.find(e=>sf.getLineAndCharacterOfPosition(e.openingElement.getStart(sf)).line+1===r.line);
    if(!el){out.push({file,line:r.line,error:'select element not found (self-closing?)'});continue;}
    const op=el.openingElement,attr=n=>op.attributes.properties.find(a=>ts.isJsxAttribute(a)&&a.name.getText(sf)===n);
    const at=n=>{const a=attr(n);return a?(a.initializer?a.initializer.getText(sf):'true'):null};
    const oc=at('onChange');let handler=oc;let resolved=null;
    if(oc){const m=oc.match(/^\{\s*([A-Za-z_$][\w$]*)\s*\}$/);if(m){resolved=decl(m[1]);}}
    const hText=resolved||oc||'';
    const reads=[];if(/e(vent)?\.target\.value|\.target\.value|\btarget\.value/.test(hText))reads.push('target.value');if(/selectedOptions|selectedIndex/.test(hText))reads.push('selectedOptions/Index');if(oc&&!reads.length)reads.push(oc&&/\bvalue\b/.test(hText)?'other(value-ish)':'other/unresolved');
    const numeric=/Number\(|parseInt\(|parseFloat\(|\+\s*e\.target|\+\s*\w+\.target/.test(hText);
    const kids=el.children.filter(c=>!(ts.isJsxText(c)&&!c.getText(sf).trim()));
    const kindOf=c=>{if(ts.isJsxElement(c)||ts.isJsxSelfClosingElement(c)){const t=ts.isJsxElement(c)?c.openingElement.tagName.getText(sf):c.tagName.getText(sf);return t||'fragment'}if(ts.isJsxFragment(c))return 'fragment';if(ts.isJsxExpression(c)){const e=c.expression;if(!e)return 'comment/empty';const tx=e.getText(sf);if(/\.map\(/.test(tx))return 'map';if(ts.isConditionalExpression(e)||(ts.isBinaryExpression(e)&&/&&|\|\|/.test(e.operatorToken.getText(sf))))return 'conditional';return 'expression'}return 'text'};
    const kinds=kids.map(kindOf);
    const optNodes=[];const fo=n=>{if(ts.isJsxElement(n)&&n.openingElement.tagName.getText(sf)==='option')optNodes.push(n);ts.forEachChild(n,fo)};fo(el);
    let disabled=false,rawLabels=[],tLabels=0,exprLabels=0;
    for(const o of optNodes){if(o.openingElement.attributes.properties.some(a=>ts.isJsxAttribute(a)&&a.name.getText(sf)==='disabled'))disabled=true;
      for(const c of o.children){if(ts.isJsxText(c)){const x=c.getText(sf).trim();if(x)rawLabels.push(x)}else if(ts.isJsxExpression(c)&&c.expression){const x=c.expression.getText(sf);if(/\bt\(/.test(x))tLabels++;else if(/^["'`]/.test(x))rawLabels.push(x);else exprLabels++}}}
    // options built from data in map (label field): note
    let parent=el.parent;while(parent&&!(ts.isJsxElement(parent)||ts.isJsxSelfClosingElement(parent)||ts.isJsxFragment(parent)))parent=parent.parent;
    let ptag=null,pcls=null;if(parent){const o=ts.isJsxElement(parent)?parent.openingElement:parent;ptag=ts.isJsxFragment(parent)?'<>':o.tagName.getText(sf);if(o.attributes){const c=o.attributes.properties.find(a=>ts.isJsxAttribute(a)&&a.name.getText(sf)==='className');pcls=c&&c.initializer?c.initializer.getText(sf):null}}
    let wrapLabel=false;for(let p=el.parent;p;p=p.parent){if(ts.isJsxElement(p)&&p.openingElement.tagName.getText(sf)==='label'){wrapLabel=true;break}if(ts.isFunctionLike(p))break}
    const id=at('id');let htmlFor=false;if(id){const idv=id.replace(/^\{|\}$/g,'').trim();const re=/htmlFor=(\{[^}]*\}|"[^"]*")/g;let m;while((m=re.exec(src)))if(m[1].replace(/^\{|\}$/g,'').trim()===idv)htmlFor=true}
    const full=el.getText(sf);
    out.push({file,line:r.line,component:r.component,openingTag:op.getText(sf),children:cap(el.children.map(c=>c.getText(sf)).join(''),1500),className:at('className'),value:at('value'),onChange:cap(oc||'',200),onChangeResolved:resolved?cap(resolved,200):null,readsPattern:reads,numericConverted:numeric,childKinds:kinds,childCount:kids.length,
      childPattern:kinds.includes('optgroup')?'optgroup':kinds.includes('map')?'map':kinds.every(k=>k==='option')?'static-option':kinds.includes('conditional')?'conditional':'mixed',
      nonOptionChildren:kids.map((c,i)=>[kinds[i],c]).filter(([k])=>k!=='option').map(([k,c])=>({kind:k,text:cap(c.getText(sf),300)})),
      hasDisabledOption:disabled,labelsT:tLabels,labelsExpr:exprLabels,labelsRaw:rawLabels,id,wrappedByLabel:wrapLabel,htmlForRef:htmlFor,parentTag:ptag,parentClassName:pcls,fullChars:full.length});
  }
}
fs.writeFileSync(path.join(outDir,'av1-select-detail.json'),JSON.stringify(out,null,2));
const cnt=(a,f)=>{const m={};a.forEach(x=>{const k=f(x);m[k]=(m[k]||0)+1});return Object.entries(m).sort((a,b)=>b[1]-a[1])};
const S={total:out.length,notFound:out.filter(o=>o.error).length,
className:cnt(out.filter(o=>!o.error),o=>o.className||'(none)').slice(0,20),
reads:cnt(out.filter(o=>!o.error),o=>o.readsPattern.join('+')||'(no onChange)'),
numeric:cnt(out.filter(o=>!o.error),o=>String(o.numericConverted)),
childPattern:cnt(out.filter(o=>!o.error),o=>o.childPattern),
childKinds:cnt(out.filter(o=>!o.error),o=>[...new Set(o.childKinds)].sort().join('+')),
hardcodedLabels:out.filter(o=>o.labelsRaw&&o.labelsRaw.length).length,
labelsT:out.filter(o=>o.labelsT>0).length,disabledOpt:out.filter(o=>o.hasDisabledOption).length,
withId:out.filter(o=>o.id).length,htmlFor:out.filter(o=>o.htmlForRef).length,wrapped:out.filter(o=>o.wrappedByLabel).length,
labelled:out.filter(o=>o.htmlForRef||o.wrappedByLabel).length};
fs.writeFileSync(path.join(outDir,'av1-summary.json'),JSON.stringify(S,null,2));
console.log(JSON.stringify(S,null,1));
