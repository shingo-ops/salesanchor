// usage: node ay-inventory.cjs <worktree root containing frontend/src> <out.json>
const ts = require(process.argv[2] + '/frontend/node_modules/typescript');
const fs = require('fs'), path = require('path');
const root = process.argv[2], out = process.argv[3];
const src = path.join(root, 'frontend/src');
const files = [];
(function walk(d){ for (const e of fs.readdirSync(d,{withFileTypes:true})) { const p=path.join(d,e.name);
  if (e.isDirectory()) { if (e.name==='__tests__') continue; walk(p); }
  else if (/\.tsx$/.test(e.name) && !/\.(stories|test)\.tsx$/.test(e.name)) files.push(p); } })(src);
const NONTEXT = new Set(['checkbox','radio','file','color','range','hidden']);
const MOLD_FILES = /^frontend\/src\/components\/(TextField|Textarea|Select|Checkbox|Radio)\.tsx$/;
const rows = [], molds = [], syntaxErrors = [];
for (const f of files.sort()) {
  const text = fs.readFileSync(f,'utf8');
  const sf = ts.createSourceFile(f, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  if (sf.parseDiagnostics && sf.parseDiagnostics.length) syntaxErrors.push(path.relative(root,f));
  const lines = text.split('\n');
  const rel = path.relative(root, f);
  const line = n => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  const attrsOf = (el) => el.attributes.properties.map(p => ts.isJsxSpreadAttribute(p)
      ? {name:'...spread', raw:p.getText(sf)}
      : {name:p.name.getText(sf), raw: p.initializer ? p.initializer.getText(sf) : '(true)'});
  const ancClass = (n) => { const res=[]; let p=n.parent;
    while (p && res.length<3) { if (ts.isJsxElement(p) || ts.isJsxSelfClosingElement(p)) {
        const el = ts.isJsxElement(p)?p.openingElement:p;
        const a = el.attributes.properties.find(x=>ts.isJsxAttribute(x)&&x.name.getText(sf)==='className');
        res.push({tag: el.tagName.getText(sf), line: line(el), className: a&&a.initializer?a.initializer.getText(sf):null}); }
      p = p.parent; } return res; };
  const uiAllow = (n) => { const l = line(n); const hits=[];
    const endL = sf.getLineAndCharacterOfPosition(n.getEnd()).line + 1;
    for (let i=l-1;i<=Math.min(endL,lines.length)-1;i++) if (/ui-allow/.test(lines[i])) hits.push({line:i+1,text:lines[i].trim()});
    let j = l-2; while (j>=0 && lines[j].trim()==='') j--;
    if (j>=0 && /ui-allow/.test(lines[j])) hits.push({line:j+1,text:lines[j].trim()});
    return hits; };
  const inMold = rel === 'frontend/src/components/TextField.tsx';
  (function visit(n){
    if (ts.isJsxOpeningElement(n) || ts.isJsxSelfClosingElement(n)) {
      const tag = n.tagName.getText(sf);
      if (tag === 'input') {
        const attrs = attrsOf(n);
        const t = attrs.find(a=>a.name==='type');
        let type;
        if (!t) type='omitted';
        else { const m = /^["'](.*)["']$/.exec(t.raw) || /^\{\s*["'`]([^"'`$]*)["'`]\s*\}$/.exec(t.raw); type = m ? m[1] : 'dynamic'; }
        const names = attrs.map(a=>a.name);
        rows.push({file:rel,line:line(n),type,textLike:!NONTEXT.has(type),attrs,
          has:{ref:names.includes('ref'),onKeyDown:names.includes('onKeyDown'),autoFocus:names.includes('autoFocus'),spread:names.includes('...spread'),style:names.includes('style'),className:names.includes('className')},
          uiAllow:uiAllow(n),ancestors:ancClass(n),insideMold:inMold});
      }
      if (tag === 'TextField' || tag === 'TextFieldControl') molds.push({tag,file:rel,line:line(n),attrs:attrsOf(n)});
    }
    ts.forEachChild(n, visit); })(sf);
}
const cnt = (arr,k)=>arr.reduce((a,r)=>(a[k(r)]=(a[k(r)]||0)+1,a),{});
const page = rows.filter(r=>!r.insideMold), tl = page.filter(r=>r.textLike);
const res = { tsVersion: ts.version, tsxFilesScanned: files.length, syntaxErrorFiles: syntaxErrors,
  rawInputTotal: rows.length, rawInsideMold: rows.length-page.length, pageSide: page.length,
  byTypePageSide: cnt(page,r=>r.type), byTypeAll: cnt(rows,r=>r.type),
  textLikePageSide: tl.length,
  textLikeCounts: {ref:tl.filter(r=>r.has.ref).length,onKeyDown:tl.filter(r=>r.has.onKeyDown).length,autoFocus:tl.filter(r=>r.has.autoFocus).length,spread:tl.filter(r=>r.has.spread).length,style:tl.filter(r=>r.has.style).length,className:tl.filter(r=>r.has.className).length},
  uiAllowPageSide: page.filter(r=>r.uiAllow.length).length,
  moldUsages: molds.length, moldTagCounts: cnt(molds,m=>m.tag),
  moldAttrCounts: molds.reduce((a,m)=>{m.attrs.forEach(x=>a[x.name]=(a[x.name]||0)+1);return a;},{}),
  rows, molds };
fs.writeFileSync(out, JSON.stringify(res,null,1));
const {rows:_r,molds:_m,...sum}=res; console.log(JSON.stringify(sum,null,1));
