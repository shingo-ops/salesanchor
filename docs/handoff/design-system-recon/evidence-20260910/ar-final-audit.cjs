// Read-only verifier: run from repository root after CARD-AR-NATIVE-BUTTONS-01.
const fs = require('fs'), cp = require('child_process'), crypto = require('crypto');
const ts = require(process.cwd() + '/frontend/node_modules/typescript');
const audit = JSON.parse(fs.readFileSync(__dirname + '/ar-button-audit.json', 'utf8'));
const sha = text => crypto.createHash('sha256').update(text).digest('hex');
const result = { base: audit.base, files: [], shared: [], counts: {} };
for (const entry of audit.files) {
  const baseline = cp.execFileSync('git', ['show', audit.base + ':' + entry.file], { encoding: 'utf8' });
  const current = fs.readFileSync(entry.file, 'utf8');
  let inverse = current;
  const targets = entry.targets.map(target => {
    const variant = target.raw.includes('className="btn-primary"') ? 'primary' : 'secondary';
    const migrated = target.raw.replace(/^<button\b/, '<Button').replace(/<\/button>$/, '</Button>')
      .replace(/className="btn-(?:primary|secondary)(?: field-h-md)?"/, 'variant="' + variant + '" size="md"');
    const present = inverse.includes(migrated);
    if (present) inverse = inverse.replace(migrated, target.raw);
    return { line: target.line, present };
  });
  if (!/import\s*\{[^}]*\bButton\b[^}]*\}[^;]*;/.test(baseline)) {
    inverse = inverse.replace(/^import \{ Button \} from [^;]+;\r?\n/m, '');
  }
  const outsidePreserved = entry.outsideLegacy.every(x => current.includes(x.raw));
  result.files.push({ file: entry.file, sha256: sha(current), baselineMatches: sha(baseline) === entry.sha256,
    targets, inverseByteEqual: inverse === baseline, outsidePreserved });
}
result.shared = audit.shared.map(x => ({ file: x.file, unchanged: sha(fs.readFileSync(x.file)) === x.sha256 }));
let common = 0, legacy = 0;
for (const p of cp.execFileSync('git', ['ls-files', 'frontend/src'], { encoding: 'utf8' }).trim().split('\n').filter(p => p.endsWith('.tsx') && !/(stories|test|spec)\.|\/design-preview\//.test(p))) {
 const source = ts.createSourceFile(p, fs.readFileSync(p, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
 function walk(n) {
  if (ts.isJsxOpeningElement(n) || ts.isJsxSelfClosingElement(n)) {
   const tag = n.tagName.getText(source); if (tag === 'Button') common++;
   if (['button', 'Link', 'a'].includes(tag)) {
    const attr = n.attributes.properties.find(x => x.name?.getText(source) === 'className');
    if (attr?.initializer && /(^|[^\w-])btn-/.test(attr.initializer.getText(source))) legacy++;
   }
  }
  ts.forEachChild(n, walk);
 }
 walk(source);
}
result.counts = { common, legacy };
result.pass = result.files.every(x => x.baselineMatches && x.inverseByteEqual && x.outsidePreserved && x.targets.every(t => t.present)) && result.shared.every(x => x.unchanged) && common === 231 && legacy === 266;
console.log(JSON.stringify(result, null, 2));
process.exitCode = result.pass ? 0 : 1;
