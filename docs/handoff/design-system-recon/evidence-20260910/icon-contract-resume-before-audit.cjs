const cp = require('child_process');
const path = require('path');
const fs = require('fs');
const root = process.env.SALESANCHOR_AUDIT_REPO || '/Users/tanizawashingo/salesanchor';
const ts = require(path.join(root, 'frontend/node_modules/typescript'));
const sha = '5de8afa1f97b67ebaebe186fed3d9751bbf2fcd7';
const out = __dirname;
const git = (...args) => cp.execFileSync('git', args, { cwd: root, encoding: 'utf8' });
const files = git('ls-tree', '-r', '--name-only', sha, 'frontend/src').trim().split('\n').filter(p => /\.(tsx?|json)$/.test(p));
const cache = new Map(files.map(p => [path.join(root, p), git('show', sha + ':' + p)]));
const options = { jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext, moduleResolution: ts.ModuleResolutionKind.Bundler, allowSyntheticDefaultImports: true, skipLibCheck: true };
const host = ts.createCompilerHost(options);
const read = host.readFile;
host.readFile = p => cache.get(p) ?? read(p);
const program = ts.createProgram(files.filter(p => /\.tsx?$/.test(p)).map(p => path.join(root, p)), options, host);
const checker = program.getTypeChecker();
const rows = [];
for (const sf of program.getSourceFiles()) {
  if (!cache.has(sf.fileName) || !sf.fileName.endsWith('.tsx')) continue;
  function visit(n) {
    if (ts.isJsxOpeningElement(n) || ts.isJsxSelfClosingElement(n)) {
      const type = checker.getTypeAtLocation(n.tagName);
      const sigs = checker.getSignaturesOfType(type, ts.SignatureKind.Call);
      const match = sigs.some(s => s.parameters.some(p => checker.getTypeOfSymbolAtLocation(p, n).getProperty('weight')?.declarations?.some(d => d.getSourceFile().fileName === path.join(root, 'frontend/src/constants/icons.tsx'))));
      if (match) {
        const attrs = {};
        for (const a of n.attributes.properties) {
          attrs[ts.isJsxSpreadAttribute(a) ? 'spread' : a.name.getText(sf)] = ts.isJsxSpreadAttribute(a) ? a.expression.getText(sf) : a.initializer?.getText(sf) || true;
        }
        rows.push({ file: path.relative(root, sf.fileName), line: sf.getLineAndCharacterOfPosition(n.getStart()).line + 1, tag: n.tagName.getText(sf), attrs });
      }
    }
    ts.forEachChild(n, visit);
  }
  visit(sf);
}
const production = rows.filter(r => !/(stories|test|spec)\.|\/design-preview\//.test(r.file));
const keys = ['style', 'color', 'ref', 'spread', 'aria-hidden', 'aria-label', 'aria-labelledby', 'aria-describedby', 'role', 'focusable', 'weight'];
const summary = { sha, typescriptVersion: ts.version, method: 'JSX call signature props.weight declaration originates from constants/icons.tsx; tracked source loaded from fixed SHA; dependencies read from installed node_modules', exclusion: '(stories|test|spec)\\.|/design-preview/', total: rows.length, production: production.length, productionFiles: new Set(production.map(r => r.file)).size, counts: Object.fromEntries(keys.map(k => [k, production.filter(r => k in r.attrs).length])) };
fs.writeFileSync(path.join(out, 'icon-all-targets.json'), JSON.stringify({ summary, rows }, null, 2) + '\n');
fs.writeFileSync(path.join(out, 'icon-summary.json'), JSON.stringify(summary, null, 2) + '\n');
console.log(JSON.stringify(summary, null, 2));
