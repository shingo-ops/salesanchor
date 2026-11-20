import os,re,sys
root=sys.argv[1]
adr=os.path.join(root,'docs/adr')
ids=set()
for f in os.listdir(adr):
    m=re.match(r'ADR-(\d+)-',f)
    if m: ids.add(int(m.group(1)))
fi=open(os.path.join(adr,'FEATURE-INDEX.md')).read()
ref=set(int(x) for x in re.findall(r'ADR-(\d+)',fi))
miss=sorted(ids-ref)
specs=os.path.join(root,'docs/specs')
dirs=sorted(d for d in os.listdir(specs) if os.path.isdir(os.path.join(specs,d)))
sr=open(os.path.join(specs,'README.md')).read()
smiss=[d for d in dirs if f'{d}/' not in sr and f'({d})' not in sr]
fi_spec=[d for d in dirs if f'specs/{d}' in fi]
print('adr_ids',len(ids),'referenced',len(ids&ref),'missing',len(miss))
print('spec_dirs',len(dirs),'missing_in_specs_readme',len(smiss),smiss)
print('spec_dirs_referenced_from_feature_index',len(fi_spec))
print('fi_rows',sum(1 for l in fi.splitlines() if l.startswith('| ') and not l.startswith('| 機能') and not l.startswith('|---')))
print('MISSING',' '.join(f'{i:03d}' for i in miss))
