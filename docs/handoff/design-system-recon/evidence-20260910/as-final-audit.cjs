// Read-only: run from repository root. Baseline JSON preserves exact JSX bytes.
const fs=require('fs'),cp=require('child_process'),crypto=require('crypto'),path=require('path');
const ts=require(process.cwd()+'/frontend/node_modules/typescript');
const a=JSON.parse(fs.readFileSync(__dirname+'/as-button-audit.json','utf8'));
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const r={base:a.base,files:[],shared:[],counts:{common:0,legacy:0},syntaxErrors:[]};
for(const e of a.files){
 const before=cp.execFileSync('git',['show',a.base+':'+e.file],{encoding:'utf8'}),now=fs.readFileSync(e.file,'utf8');let inverse=now;
 const targets=e.targets.map(t=>{const count=inverse.split(t.migrated).length-1;if(count===1)inverse=inverse.replace(t.migrated,t.raw);return {line:t.line,count};});
 if(!/import\s*\{[^}]*\bButton\b[^}]*\}[^;]*;/.test(before)){
 let rel=path.posix.relative(path.posix.dirname(e.file),'frontend/src/components/Button');if(!rel.startsWith('.'))rel='./'+rel;
 inverse=inverse.replace('import { Button } from '+JSON.stringify(rel)+';\n','');
 }
 r.files.push({file:e.file,sha256:sha(now),baselineMatches:sha(before)===e.sha256,inverseByteEqual:before===inverse,targets});
}
r.shared=a.shared.map(x=>({file:x.file,unchanged:sha(fs.readFileSync(x.file))===x.sha256}));
const remaining=[];
for(const file of cp.execFileSync('git',['ls-files','frontend/src'],{encoding:'utf8'}).trim().split('\n').filter(p=>p.endsWith('.tsx')&&!/(stories|test|spec)\.|\/design-preview\//.test(p))){
 const s=ts.createSourceFile(file,fs.readFileSync(file,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 for(const d of s.parseDiagnostics)r.syntaxErrors.push({file,start:d.start,message:ts.flattenDiagnosticMessageText(d.messageText,' ')});
 function visit(n){if(ts.isJsxOpeningElement(n)||ts.isJsxSelfClosingElement(n)){
 const tag=n.tagName.getText(s);if(tag==='Button')r.counts.common++;
 const at=n.attributes.properties.find(x=>x.name?.getText(s)==='className');
 if(['button','Link','a'].includes(tag)&&at?.initializer&&/(^|[^\w-])btn-/.test(at.initializer.getText(s))){r.counts.legacy++;remaining.push({file,raw:(ts.isJsxOpeningElement(n)?n.parent:n).getText(s)});}}
 ts.forEachChild(n,visit);}visit(s);
}
const canonical=xs=>JSON.stringify(xs.map(x=>x.file+'\n'+x.raw).sort());
r.outsideLegacyByteEqual=canonical(remaining)===canonical(a.outsideLegacy);
r.pass=r.syntaxErrors.length===0&&r.files.every(x=>x.baselineMatches&&x.inverseByteEqual&&x.targets.every(t=>t.count===1))&&r.shared.every(x=>x.unchanged)&&r.outsideLegacyByteEqual&&r.counts.common===265&&r.counts.legacy===232;
console.log(JSON.stringify(r,null,2));process.exitCode=r.pass?0:1;
