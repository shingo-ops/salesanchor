// usage: node av2-inventory.cjs <exportRoot containing frontend/src> <out.json>
const ts = require('/Users/tanizawashingo/salesanchor/frontend/node_modules/typescript');
const fs = require('fs'), path = require('path');
const root = process.argv[2], out = process.argv[3];
const src = path.join(root, 'frontend/src');
const files = [];
(function walk(d){ for (const e of fs.readdirSync(d,{withFileTypes:true})) { const p=path.join(d,e.name);
  if (e.isDirectory()) { if (e.name==='__tests__') continue; walk(p); }
  else if (/\.tsx$/.test(e.name) && !/\.(stories|test)\.tsx$/.test(e.name)) files.push(p); } })(src);
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
    // same line, and the previous non-empty line (also checks the JSX multi-line opening tag lines)
    const startL = l, endL = sf.getLineAndCharacterOfPosition(n.getEnd()).line + 1;
    for (let i=startL-1;i<=Math.min(endL,lines.length)-1;i++) if (/ui-allow/.test(lines[i])) hits.push({line:i+1,text:lines[i].trim()});
    let j = startL-2; while (j>=0 && lines[j].trim()==='') j--;
    if (j>=0 && /ui-allow/.test(lines[j])) hits.push({line:j+1,text:lines[j].trim()});
    return hits; };
  const inMold = /^frontend\/src\/components\/Textarea\.tsx$/.test(rel);
  (function visit(n){
    if (ts.isJsxOpeningElement(n) || ts.isJsxSelfClosingElement(n)) {
      const tag = n.tagName.getText(sf);
      if (tag === 'textarea') rows.push({file:rel,line:line(n),attrs:attrsOf(n),uiAllow:uiAllow(n),ancestors:ancClass(n),insideMold:inMold});
      if (tag === 'Textarea') molds.push({file:rel,line:line(n),attrs:attrsOf(n)});
    }
    ts.forEachChild(n, visit); })(sf);
}
const res = { tsVersion: ts.version, tsxFilesScanned: files.length, syntaxErrorFiles: syntaxErrors,
  rawTextareaTotal: rows.length, rawInsideMold: rows.filter(r=>r.insideMold).length,
  rawWithUiAllow: rows.filter(r=>r.uiAllow.length).length,
  pageSideRaw: rows.filter(r=>!r.insideMold).length, moldUsages: molds.length, rows, molds };
fs.writeFileSync(out, JSON.stringify(res,null,1));
console.log(JSON.stringify({tsVersion:res.tsVersion,files:res.tsxFilesScanned,syntaxErrors:syntaxErrors.length,total:res.rawTextareaTotal,inMold:res.rawInsideMold,uiAllow:res.rawWithUiAllow,pageSide:res.pageSideRaw,moldUsages:res.moldUsages}));
