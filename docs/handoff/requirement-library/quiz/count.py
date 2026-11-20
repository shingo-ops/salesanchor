"""要件の練習問題の数え方（quiz.md に測定前に固定）。

usage: python3 count.py OUT_DIR [ROUNDS]
開いた(R2) = Read/Bash/Grep/Glob の入力に正解のパスの文字列が1つでもある回（K12 の read と同じ数え方）。
読まずに不具合(R4 補助) = 正解の書類を開く前の文に「不具合・バグ・bug」がある回、
  または最後の答えにその語があり正解の書類を一度も開いていない回。
"""
import json
import sys

D = sys.argv[1]
R = int(sys.argv[2]) if len(sys.argv) > 2 else 2
GOLD = {
    'Q1': ['ADR-097-', 'deal-removal/design.md'],
    'Q2': ['ADR-1076-', 'status-ssot-contact-company/design.md'],
    'Q3': ['ADR-1083-', 'auth-expired-token-lockout/design.md'],
    'Q4': ['ADR-1027-', 'specs/bundle-sale/'],
    'Q5': ['ADR-1022-', 'py312-guard/design.md'],
    'Q6': ['ADR-1037-', 'migration-lock-timeout/design.md'],
    'Q7': ['ADR-1032-', 'revival-guard/design.md'],
    'Q8': ['ADR-1062-', 'gemini-auto-failover/design.md'],
    'Q9': ['ADR-1056-', 'ADR-1078-', 'secretary-chat/design.md', 'secretary-event-karte/'],
    'Q10': ['ADR-1071-', 'error-message-plain-language/design.md'],
}
BUG = ('不具合', 'バグ', 'bug', 'Bug', 'BUG')
READ_TOOLS = ('Read', 'Bash', 'Grep', 'Glob')

rows = []
for q, gold in GOLD.items():
    for k in range(1, R + 1):
        f = f'{D}/{q}-{k}.jsonl'
        try:
            lines = open(f, errors='replace').read().splitlines()
        except FileNotFoundError:
            rows.append((q, k, 'MISSING', '', '', '', '', ''))
            continue
        opened = 0
        first_open = ''
        n = 0
        cost = ''
        text = ''
        idx = 0
        bug_before = 0
        for line in lines:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get('type') == 'result':
                cost = d.get('total_cost_usd', '')
                text = d.get('result', '') or ''
            if d.get('type') != 'assistant':
                continue
            for c in d.get('message', {}).get('content', []):
                if c.get('type') == 'text' and not opened and any(b in c.get('text', '') for b in BUG):
                    bug_before = 1
                if c.get('type') == 'tool_use':
                    n += 1
                    s = json.dumps(c.get('input'), ensure_ascii=False)
                    if 'FEATURE-INDEX' in s:
                        idx = 1
                    if c.get('name') in READ_TOOLS and any(g in s for g in gold):
                        if not opened:
                            first_open = n
                        opened = 1
        bug_final = int(any(b in text for b in BUG))
        r4 = int((bug_final and not opened) or bug_before)
        rows.append((q, k, opened, first_open, idx, n, r4, cost))
        with open(f'{D}/{q}-{k}.answer.txt', 'w') as o:
            o.write(text)

with open(D + '/result.tsv', 'w') as o:
    o.write('題\t回\t開いた(R2)\t何回目の道具で開いたか\t索引を開いた\t道具の数\t読まずに不具合(R4補助)\t費用usd\n')
    for r in rows:
        o.write('\t'.join(map(str, r)) + '\n')
print(open(D + '/result.tsv').read())
ok = [r for r in rows if r[2] != 'MISSING']
print('R2', sum(r[2] for r in ok), '/', len(ok),
      'R4aux', sum(r[6] for r in ok),
      'cost', round(sum(float(r[7] or 0) for r in ok), 2))
