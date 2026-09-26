const fs=require('fs'),path=require('path');
const ts=require('/Users/tanizawashingo/salesanchor/frontend/node_modules/typescript/lib/typescript.js');
const walk=d=>fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(d,e.name)):[path.join(d,e.name)]);
const files=walk('frontend/src').filter(f=>f.endsWith('.tsx')&&!/\.(stories|test|spec)\.tsx$/.test(f)&&!/(design-preview|design-system)\//.test(f));
const rows=[];
for(const file of files){const src=fs.readFileSync(file,'utf8'),sf=ts.createSourceFile(file,src,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
function visit(n){if(ts.isJsxElement(n)&&n.openingElement.tagName.getText(sf)==='table'){
const r={file,line:sf.getLineAndCharacterOfPosition(n.getStart(sf)).line+1,spans:[],controls:[],events:[],footer:false};
function scan(x){if(x!==n&&ts.isJsxElement(x)&&x.openingElement.tagName.getText(sf)==='table')return;
if(ts.isJsxOpeningElement(x)||ts.isJsxSelfClosingElement(x)){const tag=x.tagName.getText(sf),line=sf.getLineAndCharacterOfPosition(x.getStart(sf)).line+1;if(tag==='tfoot')r.footer=true;if(['button','input','select','textarea'].includes(tag))r.controls.push({tag,line});for(const a of x.attributes.properties)if(ts.isJsxAttribute(a)){const name=a.name.getText(sf);if(['rowSpan','colSpan'].includes(name))r.spans.push({name,value:a.initializer?.getText(sf),line});if(/^on[A-Z]/.test(name))r.events.push({name,line,value:a.initializer?.getText(sf)});}}
ts.forEachChild(x,scan);}scan(n);rows.push(r);}ts.forEachChild(n,visit);}visit(sf);}
fs.writeFileSync('/tmp/frontend-mold-recon-20260910/table-behaviors.json',JSON.stringify(rows,null,2));console.log(JSON.stringify({tables:rows.length,spanTables:rows.filter(r=>r.spans.length).map(r=>({file:r.file,line:r.line})),footerTables:rows.filter(r=>r.footer).length,interactiveTables:rows.filter(r=>r.controls.length||r.events.length).length},null,2));
