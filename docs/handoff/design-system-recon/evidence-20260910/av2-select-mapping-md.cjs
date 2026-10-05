// AV-2 recon: render markdown from av2-select-mapping.json. Read-only.
const fs = require('fs'), path = require('path');
const OUT = path.join(__dirname);
const d = JSON.parse(fs.readFileSync(path.join(OUT, 'av2-select-mapping.json'), 'utf8'));
const short = p => p.replace(/^frontend\/src\//, '');
const abbr = v => String(v).replace(/url\("data:image\/svg\+xml[^)]*\)/g, 'url(<chevron-svg>)');
const esc = v => abbr(v).replace(/\|/g, '\\|');
const loc = r => '`' + short(r.file) + ':' + r.line + '`';
const L = [];
const P = s => L.push(s);
const NAMES = { i: '(i) no matched rule / no inline style', ii: '(ii) only layout declarations', iii: '(iii) decoration equals one mold size (declared-subset equality)', iv: '(iv) decoration differs', v: '(v) unconfirmed (ancestor unknown etc.)' };

P('# AV-2 select -> SelectControl mapping recon (read-only)');
P('');
P(`- origin/main SHA: \`${d.baseSha}\``);
P(`- method: TypeScript ${d.typescriptVersion} AST + postcss/postcss-selector-parser over \`frontend/src/**/*.css\` (snapshot via git archive; scripts in this directory: av2-project.cjs / av2-css.cjs / av2-select-mapping.cjs / av2-select-mapping-md.cjs)`);
P(`- scope: ${d.definitions.inventory}`);
P('');
P('## Definitions used');
P('');
P('- applied CSS: ' + d.definitions.applied);
P('- LAYOUT: ' + d.definitions.layout);
for (const k of ['i', 'ii', 'iii', 'iv', 'v']) P(`- class ${k}: ${d.definitions.classes[k]}`);
P('- universal baseline: ' + d.universalBaselineAppliedToEverySelect.join(' ; ') + ' (applies to every select; used for "before" values, not counted as a matched rule for classification)');
P('- ' + d.definitions.universalRulesNote);
P('- ' + d.definitions.nestedCssNote + ': ' + d.nestedRulesSkipped.length + ' rule(s)');
P('- all stylesheets are assumed loaded; cross-file cascade ties (same specificity, different files) are flagged `ambiguousAcrossFiles` in the JSON');
P('');
P('## Summary counts');
P('');
P('|class|count|');
P('|---|---:|');
for (const k of ['i', 'ii', 'iii', 'iv', 'v']) P(`|${NAMES[k]}|${d.counts[k] || 0}|`);
P(`|total|${d.rows.length}|`);
P('');
const iiiWeak = d.rows.filter(r => r.classification === 'iii' && /^weak/.test(r.iiiStrength)).length;
P(`- class (iii) rows whose equality is only on weak properties (no font-size/padding declared): ${iiiWeak} of ${d.counts.iii || 0}`);
const ownClsNoRule = d.rows.filter(r => r.classification === 'i' && r.className.staticTokens.length);
P(`- class (i) rows that carry an own className with no matching CSS rule anywhere: ${ownClsNoRule.length} (${ownClsNoRule.map(r => short(r.file) + ':' + r.line + ' .' + r.className.staticTokens.join('.')).join(', ') || '-'})`);
const ownDim = d.rows.filter(r => r.ownedDimensionDeclared.length);
P(`- selects whose applied CSS declares height/min-height/max-height (dimension owned by Select size props per contract): ${ownDim.length}`);
P('');
P('## A. Inventory vs av1-select-detail.json (80 rows, previous base)');
P('');
P(`- av1 count: ${d.inventory.av1Count}; now: ${d.inventory.newCount}`);
P(`- removed (key = file + openingTag text): ${d.inventory.removedByKey.length}`);
d.inventory.removedByKey.forEach(x => P(`  - \`${short(x)}\``));
P(`- added: ${d.inventory.addedByKey.length}${d.inventory.addedByKey.length ? '' : ' (none)'}`);
d.inventory.addedByKey.forEach(x => P(`  - \`${short(x)}\``));
P(`- same select, line moved: ${d.inventory.lineMoved.length}${d.inventory.lineMoved.length ? '' : ' (none)'}`);
d.inventory.lineMoved.forEach(x => P(`  - \`${short(x)}\``));
P(`- file:line-only diff: removed ${d.inventory.fileLineOnlyRemoved.length}, added ${d.inventory.fileLineOnlyAdded.length}`);
const vs = {}; d.rows.forEach(r => { vs[r.vsAv1] = (vs[r.vsAv1] || 0) + 1; });
P('- option/onChange facts vs av1 (labelsRaw/labelsT/numericConverted/readsPattern/childPattern): ' + Object.entries(vs).map(([k, v]) => `${k}: ${v}`).join('; '));
P('');
P('## Mold reference: SelectControl appearance="bare" (from FormField.css, base state, effective longhands)');
P('');
const props = ['padding-top', 'padding-right', 'padding-bottom', 'padding-left', 'border', 'border-radius', 'font-size', 'color', 'background-color', 'background-image', 'min-height', 'line-height', 'cursor', 'appearance', 'width', 'max-width'];
P('|property|sm|md|lg|');
P('|---|---|---|---|');
for (const pr of props) P(`|${pr}|${['sm', 'md', 'lg'].map(s => { const e = d.mold[s].eff.base[pr]; return e ? esc(e.value) : '(none)'; }).join('|')}|`);
for (const s of ['sm', 'md', 'lg']) { const buckets = Object.keys(d.mold[s].eff).filter(b => b !== 'base'); P(''); P(`- ${s} non-base buckets: ` + buckets.map(b => b + ' {' + Object.entries(d.mold[s].eff[b]).map(([k, v]) => k + ': ' + abbr(v.value)).join('; ') + '}').join(' / ')); }
P('');
P('## Per-class tables');
const tableRows = r => {
  const t = r.perSize[r.nearestSize];
  const decl = Object.entries(r.effectiveBaseDecoration).map(([k, v]) => `${k}: ${v}`).join('; ');
  const st = r.stateDecorations.map(s => s.state + '@' + s.selector).join(', ');
  const diffs = t ? t.table.filter(x => !x.equal && x.before !== '(unset: browser default)' && !(r.effectiveBaseAll[x.property.startsWith('border') ? x.property : x.property] === undefined && false)).map(x => `${x.property}: ${x.before} -> ${x.after}`) : [];
  const adds = t ? t.table.filter(x => x.before === '(unset: browser default)' && x.after !== '(none)').map(x => x.property) : [];
  const extra = t ? t.declaredDecorationDiffers.filter(x => !t.table.some(g => g.property === x.property || (g.property === 'border' && x.property.startsWith('border') && !x.property.startsWith('border-radius')) || (x.property === 'background-color' && g.property === 'background-color'))).map(x => `${x.property}: ${x.before} -> ${x.after}`) : [];
  const stDiff = t ? t.stateDecorationDiffers.map(x => `[${x.state}] ${x.property}: ${x.before} -> ${x.after}`) : [];
  return { decl, st, diffs, adds, extra, stDiff, t };
};
for (const k of ['i', 'ii', 'iii', 'iv', 'v']) {
  const rs = d.rows.filter(r => r.classification === k);
  P('');
  P(`### ${NAMES[k]} - ${rs.length}`);
  P('');
  if (!rs.length) { P('none'); continue; }
  if (k === 'i') {
    P('|file:line|own className|inline style|note|');
    P('|---|---|---|---|');
    rs.forEach(r => P(`|${loc(r)}|${r.className.expression ? esc(r.className.expression) : '(none)'}|${r.inlineStyle.present ? 'yes' : 'no'}|before = browser default + universal baseline (padding 0, margin 0); mold would add every property in the table above|`));
    continue;
  }
  if (k === 'ii') { P('|file:line|layout props|'); P('|---|---|'); rs.forEach(r => P(`|${loc(r)}|${r.layoutProperties.join(', ')}|`)); continue; }
  P('|file:line|current decoration (effective base)|state-bucket decoration rules|nearest size (score)|differing properties before -> after (declared in current)|mold adds (unset in current)|extra declared props not in mold / differing|state differences vs mold|' + (k === 'iii' ? 'strength|' : (k === 'v' ? 'unconfirmed reason|' : '')));
  P('|---|---|---|---|---|---|---|---|' + (k === 'iii' || k === 'v' ? '---|' : ''));
  rs.forEach(r => {
    const x = tableRows(r);
    const near = r.nearestSize + (r.nearestIsExact ? ' (exact on declared props; exact for sizes: ' + r.exactSizes.join(',') + ')' : ' (nearest, differences)') + ' score=' + x.t.score + ' [font-size exact: ' + x.t.fontSizeExact + '; padding sides exact: ' + x.t.paddingSidesExact + '/4]';
    const tail = k === 'iii' ? `${r.iiiStrength}|` : (k === 'v' ? `${[...new Set(r.unconfirmedRules.flatMap(u => u.whys))].map(esc).join('; ')}|` : '');
    P(`|${loc(r)}|${esc(x.decl) || '-'}|${esc(x.st) || '-'}|${near}|${esc(x.diffs.join('; ')) || '-'}|${x.adds.join(', ') || '-'}|${esc(x.extra.join('; ')) || '-'}|${esc(x.stDiff.join('; ')) || '-'}|${tail}`);
  });
}
P('');
P('## Distinct applied-CSS signatures (class iii/iv/v rows grouped)');
P('');
const sig = {};
d.rows.filter(r => ['iii', 'iv', 'v'].includes(r.classification)).forEach(r => {
  const key = JSON.stringify([r.appliedRules.map(a => a.file + ':' + a.line + ' ' + a.selector).sort(), r.inlineStyle.props.map(p => p.prop + ':' + p.value)]);
  (sig[key] = sig[key] || []).push(r);
});
Object.values(sig).sort((a, b) => b.length - a.length).forEach((rs, i) => {
  const r = rs[0];
  P(`**S${i + 1}** (${rs.length} select(s); classes: ${[...new Set(rs.map(x => x.classification))].join('/')}; nearest: ${[...new Set(rs.map(x => x.nearestSize))].join('/')})`);
  P('');
  r.appliedRules.forEach(a => P(`- \`${a.file}:${a.line}\` \`${a.selector}\` [${a.state}] ${a.layout.length ? 'LAYOUT{' + a.layout.map(x => x.prop + ': ' + x.value).join('; ') + '} ' : ''}${a.decoration.length ? 'DECORATION{' + a.decoration.map(x => x.prop + ': ' + abbr(x.value)).join('; ') + '}' : ''}`));
  if (r.inlineStyle.props.length) P(`- inline style: ${r.inlineStyle.props.map(p => p.prop + ': ' + p.value + (p.dynamic ? ' (dynamic)' : '')).join('; ')}`);
  P(`- members: ${rs.map(x => '`' + short(x.file) + ':' + x.line + '`').join(', ')}`);
  P('');
});
P('## Ancestor-unknown list (class v)');
P('');
const vs5 = d.rows.filter(r => r.classification === 'v');
P(`${vs5.length} select(s). Unknown means no JSX usage of the enclosing component exists in non-test sources (only comment/CSS-import mentions), so ancestors cannot be established; test files were excluded from the usage search.`);
P('');
vs5.forEach(r => P(`- ${loc(r)} (component ${r.component}): ${[...new Set(r.unconfirmedRules.flatMap(u => u.whys))].join(' ; ')}; rules in question: ${r.unconfirmedRules.map(u => '`' + u.selector + '`').join(', ')}`));
P('');
P('## Selects with an unresolved/forwarded own className or spread (informational)');
P('');
const un = d.rows.filter(r => r.className.unresolved || r.className.spreadAttributes);
P(un.length ? un.map(r => `- ${loc(r)}: unresolved=${r.className.unresolved} spread=${r.className.spreadAttributes}`).join('\n') : 'none');
P('');
P('## E. Option labels / i18n / onChange');
P('');
P('### Raw literal option labels (verbatim; JSX text or string literals inside `<option>`)');
P('');
const rawRows = d.rows.filter(r => r.options.labelsRaw.length);
P(rawRows.length ? '|file:line|raw literals|' : 'none');
if (rawRows.length) { P('|---|---|'); rawRows.forEach(r => P(`|${loc(r)}|${r.options.labelsRaw.map(x => '`' + x.replace(/\|/g, '\\|') + '`').join(', ')}|`)); }
P('');
P('### Raw label literals reachable through `.map` source arrays declared in the same file (array-literal resolution)');
P('');
const mapRaw = d.rows.filter(r => r.options.mapSources.some(m => m.arrayLiteral && m.rawLiteralLabels && m.rawLiteralLabels.length));
P(mapRaw.length ? '|file:line|receiver|raw literals|' : 'none');
if (mapRaw.length) { P('|---|---|---|'); mapRaw.forEach(r => r.options.mapSources.filter(m => m.arrayLiteral && m.rawLiteralLabels && m.rawLiteralLabels.length).forEach(m => P(`|${loc(r)}|\`${m.receiver}\`|${m.rawLiteralLabels.map(x => '`' + x.replace(/\|/g, '\\|') + '`').join(', ')}|`))); }
P('');
P('### Per-select option / onChange facts');
P('');
P('|file:line|child pattern|t() option labels|unresolved expr labels|raw literals|disabled option|onChange reads|Number()/parse*|vs av1|');
P('|---|---|---:|---:|---:|---|---|---|---|');
d.rows.forEach(r => P(`|${loc(r)}|${r.options.childPattern}|${r.options.labelsT}|${r.options.labelsExprUnresolved}|${r.options.labelsRaw.length}|${r.options.hasDisabledOption}|${r.options.readsPattern.join('+') || '(none)'}|${r.options.numericConverted}|${r.vsAv1}|`));
P('');
P('## F. ui-allow comments attached to these selects (verbatim)');
P('');
const ua = d.rows.filter(r => r.uiAllow.length);
P(ua.length ? ua.map(r => r.uiAllow.map(u => `- ${loc(r)} (${u.position}, line ${u.line}): \`${u.text}\``).join('\n')).join('\n') : 'none');
P('');
P('## Limits of this analysis (facts about the method)');
P('');
P('- Ancestor chains follow JSX nesting, expand same-codebase components through their `{children}` / named-prop placements, resolve `Route element` layouts through `Outlet`, and walk JSX usage sites up to depth 10. External library components not in the codebase are treated as unknown. Runtime-only conditions (data-dependent rendering, portals) are not modelled.');
P('- Cascade between different files with equal specificity depends on bundle order, which was not measured; such cases are flagged in the JSON (`ambiguousAcrossFiles`).');
P('- Computed values were not measured in a browser; this is a static computation from stylesheet text.');
fs.writeFileSync(path.join(OUT, 'av2-select-mapping.md'), L.join('\n'));
console.log('md lines', L.length);
