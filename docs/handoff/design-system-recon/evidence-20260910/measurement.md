# 測定方法

親: [調査記録](../recon.md#2026-09-10-フロントエンド金型化の再測定)

基準SHA `6e1335725bb8dfdf390125c4caf5a93f705f4821`。専用worktreeで実行。
`pages/**/*.tsx`を再帰走査。stories/test/spec、design-preview/design-systemを除外。
件数は画面数や実行時DOM数ではなく、子部品を含むソースのJSX開始要素数。
構文木でコメント中のタグを除外。別の正規表現 `<tag(?=[\s>/])` でもselect/button/textarea/tableが67/395/43/31と一致。
共通タグ数は別名import・間接利用を含む利用率ではない。Buttonの9ファイルでは共通Buttonのimportも確認。

実行: `node /tmp/frontend-mold-recon-20260910/inventory.cjs`。以下が測定コード。
worktreeルートのrequireはMODULE_NOT_FOUNDだったため、既存のTypeScript実在パスを読み取り利用。インストールなし。

```js
const fs=require('fs'),path=require('path');
const ts=require('/Users/tanizawashingo/salesanchor/frontend/node_modules/typescript/lib/typescript.js');
const root=process.cwd(), base='frontend/src/pages';
const walk=d=>fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(d,e.name)):[path.join(d,e.name)]);
const files=walk(base).filter(f=>f.endsWith('.tsx')&&!/\.(stories|test|spec)\.tsx$/.test(f)&&!/(design-preview|design-system)\//.test(f));
let rows=[],imports=[];
for(const file of files){const src=fs.readFileSync(file,'utf8'),sf=ts.createSourceFile(file,src,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
function visit(n){
 if(ts.isImportDeclaration(n)&&ts.isStringLiteral(n.moduleSpecifier)&&n.moduleSpecifier.text.includes('components/')) imports.push({file,line:sf.getLineAndCharacterOfPosition(n.getStart(sf)).line+1,source:n.moduleSpecifier.text,clause:n.importClause?.getText(sf)});
 if(ts.isJsxOpeningElement(n)||ts.isJsxSelfClosingElement(n)){let tag=n.tagName.getText(sf),line=sf.getLineAndCharacterOfPosition(n.getStart(sf)).line+1; const attrs={};for(const a of n.attributes.properties){if(ts.isJsxAttribute(a))attrs[a.name.getText(sf)]=a.initializer?.getText(sf)||true;}rows.push({file,line,tag,attrs});}ts.forEachChild(n,visit);}visit(sf);}
const summary={files:files.length,tags:{}};for(const tag of ['button','Button','HeaderButton','input','TextField','textarea','Textarea','select','Select','SelectControl','table','DataTable','Card','Modal','ConfirmModal','Tabs','PageLayout','ContentToolbar']){const r=rows.filter(r=>r.tag===tag);summary.tags[tag]={occurrences:r.length,files:new Set(r.map(x=>x.file)).size};}
const out='/tmp/frontend-mold-recon-20260910/';fs.writeFileSync(out+'jsx-inventory.json',JSON.stringify({files,imports,rows,summary},null,2));console.log(JSON.stringify(summary,null,2));
const selects=rows.filter(r=>r.tag==='select');console.log('SELECT examples',JSON.stringify(selects.slice(0,8)));
const custom=rows.filter(r=>r.tag==='Button'&&r.attrs.style);console.log('Button style attributes',JSON.stringify(custom));

```

既存チェック: `cd frontend && node scripts/<checks.jsonのcheck名>.js`。終了コードはchecks.json、全文は各log。
`node scripts/tests/test-ui-governance.js` は22 passed / 0 failed。
gate-inventory.jsonは既存ゲートのcountSelect/countInput/countTab関数を117ファイルへ直接適用した結果。CLIのPR差分検査を全体検査と呼んでいない。
