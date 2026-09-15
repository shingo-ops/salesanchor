const fs=require('fs'),path=require('path'),cp=require('child_process');
const repo='/Users/tanizawashingo/worktrees/salesanchor/release-frontend-button-appearance',base='e81dd3ece217c6ea3d43fa9c9943440055e13adf',out=__dirname,input=path.join(out,'fixture');
const ts=require(path.join(repo,'frontend/node_modules/typescript'));
fs.mkdirSync(input,{recursive:true});
const get=(file,before)=>before?cp.execFileSync('git',['show',`${base}:${file}`],{cwd:repo,encoding:'utf8'}):fs.readFileSync(path.join(repo,file),'utf8');
const exist=(file)=>fs.existsSync(path.join(repo,file))&&fs.statSync(path.join(repo,file)).isFile();
function cssGraph(before,rootfiles){const seen=new Set(),order=[];function visit(f){if(seen.has(f))return;seen.add(f);const src=get(f,before);if(f.endsWith('.css')){order.push(f);return}const sf=ts.createSourceFile(f,src,ts.ScriptTarget.Latest,true);for(const s of sf.statements){if(!ts.isImportDeclaration(s)&&!ts.isExportDeclaration(s))continue;const spec=s.moduleSpecifier?.text;if(!spec?.startsWith('.'))continue;const p=path.posix.normalize(path.posix.join(path.posix.dirname(f),spec));const resolved=[p,p+'.tsx',p+'.ts',p+'/index.tsx',p+'/index.ts'].find(exist);if(resolved)visit(resolved)}}rootfiles.forEach(visit);return order}
function cssText(file,before){return get(file,before).replace(/@import\s+["']([^"']+)["'];/g,(s,spec)=>spec.startsWith('.')?cssText(path.posix.normalize(path.posix.join(path.posix.dirname(file),spec)),before):s)}
const manifest={};
for(const before of [true,false]){const stage=before?'before':'after';const dir=path.join(input,stage);fs.mkdirSync(dir,{recursive:true});let s=get('frontend/src/components/Button.tsx',before);s=s.replace('from "./loading"',`from "${repo}/frontend/src/components/loading"`);fs.writeFileSync(path.join(dir,'Button.tsx'),s);fs.writeFileSync(path.join(dir,'Button.css'),get('frontend/src/components/Button.css',before));
 for(const mode of ['app','storybook']){const roots=mode==='app'?['frontend/src/main.tsx']:['frontend/.storybook/preview.tsx','frontend/src/components/Button.stories.tsx'];const order=cssGraph(before,roots);manifest[stage+'-'+mode]={roots,order};fs.writeFileSync(path.join(dir,mode+'.css'),order.map(f=>'/* SOURCE '+f+' */\n'+cssText(f,before)).join('\n'));}
}
fs.writeFileSync(path.join(out,'css-import-order.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(Object.fromEntries(Object.entries(manifest).map(([k,v])=>[k,v.order.length])));
