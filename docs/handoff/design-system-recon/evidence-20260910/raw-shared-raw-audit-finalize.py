import json,collections,re
p='/tmp/frontend-raw-buttons-20260911/raw-audit.json';j=json.load(open(p))
for r in j['rows']:
 if r['classification']=='unclassified-current':
  if '/design-system/' in r['file']:c='CatalogDemo'
  elif 'navigate(' in r['attrs'].get('onClick',''):c='NavigationAction(native button)'
  elif '/Distribution' in r['file'] or '/TcgDistribution' in r['file']:c='Button'
  elif '/InventoryPage.' in r['file']:c='FilterDisclosureButton'
  elif '/ProductsPage.' in r['file']:c='ReorderModeButton'
  elif '/QuotesPage.' in r['file']:c='StatusFilterButton'
  elif '/ProductMastersTab.' in r['file']:c='ExistingRoleTab'
  else:c='unclassified-current'
  r['classification']=c;r['classificationEvidence']='current exact JSX: '+r['file']+':'+str(r['line'])+'; classification of UI trigger, not exhaustive callback behavior verification'
 r['id']='RAW-'+str(j['rows'].index(r)+1).zfill(3)
j['summary']['classifications']=dict(collections.Counter(r['classification'] for r in j['rows']))
j['summary']['buttonOnlyTypes']=dict(collections.Counter(r['attrs'].get('type','omitted') for r in j['rows'] if r['tag']=='button'))
j['summary']['autoFocus']=sum('autoFocus' in r['attrs'] for r in j['rows'])
j['summary']['limitations']=['352 preserves previous broad regex cohort; 332 btn-prefix versus 20 dedicated btn-substring, not 352 global CSS consumers','JSX call-site/static counts, not rendered instances','inline stopPropagation19 excludes uninspected named-handler internals','Existing BSA matches require same file and whitespace-normalized entire JSX; not an assumption based on old line number','Classification describes UI trigger; business function internal exhaustive tests and browser CSS precedence not performed','design-system catalog6 is included to match prior scope; stories/test/spec/design-preview excluded']
candidates=['ConfirmModal','CommissionPanel','PriorityScoreOverride','OrderFinancialPanel','PurchaseDetailPanel','ShippingDetailPanel']
j['firstBatch']=[]
for n in candidates:
 rows=[r for r in j['rows'] if r['file']=='frontend/src/components/'+n+'.tsx'];j['firstBatch'].append({'file':rows[0]['file'],'count':len(rows),'rows':[{'id':r['id'],'line':r['line'],'BSA':r.get('existingBSA',{}).get('id'),'props':r.get('existingBSA',{}).get('proposed_button_props'),'originalAttrs':r['attrs']} for r in rows]})
json.dump(j,open(p,'w'),ensure_ascii=False,indent=2)
with open('/tmp/frontend-raw-buttons-20260911/raw-audit.md','w') as f:
 f.write('# 旧rawボタン最新監査\n\n固定SHA: '+j['summary']['sha']+'。git show追跡原文のみ、製品/正式文書変更なし。raw-audit.cjs → raw-audit-enrich.py → raw-audit-finalize.pyで再現。\n\n')
 f.write('## 件数と分類\n\n'+json.dumps(j['summary'],ensure_ascii=False,indent=2)+'\n\n')
 f.write('## 最初の小口候補\n\n推奨: ConfirmModalの2個で機能/autoFocus/危険分岐を検証、または同じ条件で以下6部品16個を一便に束ねる。既存BSAの全JSX一致、追加class/style/ref/spread0なので新しい装飾判断を増やさずに移行できる。単独btn-sm2個は既存設計どおりsecondary/sm。危険分岐、submit、form、disabled、type省略、callback本文、翻訳文言は保持する。\n\n')
 for g in j['firstBatch']:
  f.write('### '+g['file']+' ('+str(g['count'])+')\n\n')
  for r in g['rows']:f.write('- :'+str(r['line'])+' '+str(r['BSA'])+' '+json.dumps(r['props'],ensure_ascii=False)+'; '+json.dumps(r['originalAttrs'],ensure_ascii=False)+'\n')
 f.write('\nConfirmModal:34のautoFocusを保持。PriorityScoreOverride:66のtype省略をbuttonへ変えない。PurchaseDetailPanel:286とShippingDetailPanel:359は外部form ID保持必須。callback処理は移管しない。\n\n## 今回分離する操作\n\nリンク8はa7/Link1のhref/to/target/relを保持するButtonLink便へ。DataTable:197はソート専用、:286/:298はページ操作だが英語aria-label直書きあり次便候補から分離。InventoryPage:400のfilterEnabledとshowFilterPanelは異なる状態で、pressed/expandedを統合しない。ProductsPage:234のreorder、QuotesPage:100のstatusFilter、ProductMastersTab:332の既存role=tab/aria-selected、InvoiceCreatePage:233/240の2モード、TcgSeriesTab:197の開閉は通常単発操作と別契約。send-guard3は翻訳/そのまま送信/取消の順序を保持。専用dist15、modal-icon1、table-sort1もグローバルbtnクラス使用と区別する。\n\n## 検証条件\n\n6部品16個のクリック1回/無効0、submitに既存formが1回応答、外部form関連付け、ConfirmModalのautoFocusとdanger分岐、旧type省略、title/data属性・翻訳済みchildren保持。CSSは共通Button外観へ意図した統一。旧未移行rawと専用部品の表示差分0を対照する。業務APIを実行する実データ試験はここでは行っていない。\n')
print(j['summary']['classifications']);print(j['summary']['buttonOnlyTypes']);print(j['summary']['allAriaAttributes']);print('firstBatch',sum(g['count'] for g in j['firstBatch']))
