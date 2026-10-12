// Read-only AU migration verification. Run from repository root.
const fs = require('fs');
const cp = require('child_process');
const crypto = require('crypto');
const ts = require(process.cwd() + '/frontend/node_modules/typescript');
const base = '303c3cfe756b1d82c042cba342c3a3150fc5ab8c';
const inventory = JSON.parse(fs.readFileSync(__dirname + '/au-inventory.json', 'utf8'));
const plan = JSON.parse(fs.readFileSync(__dirname + '/au-transform-plan.json', 'utf8'));
const planByKey = new Map(plan.nodes.map(n => [n.file+':'+n.line,n.expected]));
const sha = v => crypto.createHash('sha256').update(v).digest('hex');
const show = file => cp.execFileSync('git', ['show', base + ':' + file], {encoding:'utf8'});
const parse = (file,s) => ts.createSourceFile(file,s,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
function nodes(file,s) {
 const root = parse(file,s), all=[];
 function visit(n) {
  if(ts.isJsxElement(n)) all.push(n);
  ts.forEachChild(n,visit);
 } visit(root);return {root,all};
}
function normalizedImports(s) {
 // Only permit new common-component import bindings and the Link binding rendered redundant.
 return s.replace(/^import[^;]+;\r?\n/gm, line => {
  if(/from ["'][^"']*\/(Button|ButtonLink)["']/.test(line)) return '';
  if(/from ["']react-router-dom["']/.test(line)) {
   return line.replace(/\bLink\s*,\s*/,'').replace(/,\s*Link\b/,'').replace(/\{\s*Link\s*\}/,'{}').replace(/import\s*\{\s*\}\s*from[^;]+;\r?\n/,'');
  } return line;
 });
}
const report={base,counts:{before:inventory.legacy.length,afterLegacy:0,common:0,links:0},files:[],errors:[]};
const appearanceBefore=new Set(['className','style']);
const appearanceAfter=new Set(['variant','size','fullWidth','layoutClassName']);
for(const [file,entries] of Object.entries(inventory.groupedFiles)) {
 const before=show(file), after=fs.readFileSync(file,'utf8');
 const b=nodes(file,before),a=nodes(file,after);
 let inverse=after;
 const results=[];
 for(const e of entries) {
  const old=b.all.find(n=>n.getText(b.root)===e.raw);
  if(!old){ report.errors.push({file,line:e.line,reason:'baseline node absent'});continue; }
  const attrs=(n,s,ignore)=>n.openingElement.attributes.properties.filter(p=>!ignore.has(p.name?.getText(s))).map(p=>p.getText(s));
  const oldAttrs=JSON.stringify(attrs(old,b.root,appearanceBefore));
  const children=old.children.map(n=>n.getText(b.root)).join('\n');
  const expectedTag=e.tag==='button'?'Button':'ButtonLink';
  const candidates=a.all.filter(n=>n.openingElement.tagName.getText(a.root)===expectedTag && JSON.stringify(attrs(n,a.root,appearanceAfter))===oldAttrs && n.children.map(v=>v.getText(a.root)).join('\n')===children);
  // Duplicate identical source nodes are tracked through replacement multiplicity below.
  const found=candidates.find(n=>inverse.includes(n.getText(a.root)));
  if(!found){ report.errors.push({file,line:e.line,reason:'nonappearance attribute/children changed or missing migration'});continue; }
  const expected=planByKey.get(file+':'+e.line);
  const actualAppearance=found.openingElement.attributes.properties.filter(p=>appearanceAfter.has(p.name?.getText(a.root)));
  const observed=Object.fromEntries(actualAppearance.map(p=>[p.name.getText(a.root),p.initializer?.getText(a.root) ?? true]));
  const format=v=>typeof v==='object'&&v?.expression ? '{'+v.expression+'}' : JSON.stringify(v);
  const wanted={variant:format(expected.variant),size:format(expected.size)};
  if(expected.fullWidth)wanted.fullWidth=true;
  if(expected.layoutClassName?.length)wanted.layoutClassName=JSON.stringify(expected.layoutClassName.join(' '));
  if(JSON.stringify(Object.entries(observed).sort())!==JSON.stringify(Object.entries(wanted).sort())) report.errors.push({file,line:e.line,reason:'appearance differs from reviewed plan',observed,wanted});
  const migrated=found.getText(a.root);
  inverse=inverse.replace(migrated,e.raw);
  results.push({line:e.line,semanticAttributesEqual:true,childrenEqual:true,migratedSha256:sha(migrated)});
 }
 if(file==='frontend/src/pages/goal-setting/GoalSettingPage.tsx') {
  const signature='function AdvisorMetricRow({ label, value, onChange, recommended, testId }: AdvisorMetricRowProps) {\n';
  const added=signature+'  const { t } = useTranslation();\n';
  const translated='t("goals.advisorRecommended", { value: formatAdviceNumber(recommended) })';
  if(inverse.split(added).length!==2||inverse.split(translated).length!==2)report.errors.push({file,reason:'i18n approved delta missing/duplicated'});
  inverse=inverse.replace(added,signature).replace(translated,'`おすすめ ${formatAdviceNumber(recommended)}`');
 }
 const equal=normalizedImports(inverse)===normalizedImports(before);
 if(!equal)report.errors.push({file,reason:'nonappearance file content differs after inverse'});
 report.files.push({file,beforeSha256:sha(before),afterSha256:sha(after),targets:results.length,expected:entries.length,inverseEqual:equal,results});
}
for(const file of cp.execFileSync('git',['ls-files','frontend/src'],{encoding:'utf8'}).trim().split('\n').filter(p=>p.endsWith('.tsx')&&!/(stories|test|spec)\.|\/design-preview\//.test(p))) {
 const source=fs.readFileSync(file,'utf8'),s=parse(file,source);
 for(const err of s.parseDiagnostics)report.errors.push({file,reason:ts.flattenDiagnosticMessageText(err.messageText,' ')});
 function visit(n){
  if(ts.isJsxOpeningElement(n)||ts.isJsxSelfClosingElement(n)){
   const tag=n.tagName.getText(s);if(tag==='Button')report.counts.common++;if(tag==='ButtonLink')report.counts.links++;
   const c=n.attributes.properties.find(p=>p.name?.getText(s)==='className');
   if(['button','Link','a'].includes(tag)&&c?.initializer&&/(^|[^\w-])btn(?:-|(?=[^\w-]|$))/.test(c.initializer.getText(s)))report.counts.afterLegacy++;
  }ts.forEachChild(n,visit);
 }visit(s);
}
report.outsideNative=inventory.nativeButtonsOutsideBtnPrefix.filter(e=>e.file!=='frontend/src/components/HeaderButton.tsx').map(e=>({file:e.file,line:e.line,unchanged:fs.readFileSync(e.file,'utf8').includes(e.raw)}));
for(const e of report.outsideNative)if(!e.unchanged)report.errors.push({file:e.file,line:e.line,reason:'outside native changed'});
report.locales=[];
for(const [lang,value] of [['ja','おすすめ {{value}}'],['en','Recommended {{value}}']]) {
 const file='frontend/src/locales/'+lang+'.json';
 const old=JSON.parse(show(file)),now=JSON.parse(fs.readFileSync(file,'utf8'));
 const valueMatches=now.goals.advisorRecommended===value;
 delete now.goals.advisorRecommended;
 const otherKeysUnchanged=JSON.stringify(old)===JSON.stringify(now);
 report.locales.push({file,valueMatches,otherKeysUnchanged});
 if(!valueMatches||!otherKeysUnchanged)report.errors.push({file,reason:'locale delta beyond reviewed single key'});
}
report.pass=report.errors.length===0&&report.counts.afterLegacy===0&&report.files.reduce((sum,f)=>sum+f.targets,0)===221;
console.log(JSON.stringify(report,null,2));process.exitCode=report.pass?0:1;
