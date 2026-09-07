import sqlite3
import json

conn = sqlite3.connect('hanja_dict.db')
sem = sorted([r[0] for r in conn.execute("select distinct semantic_category from entries where semantic_category is not null and semantic_category != ''").fetchall()])
sub = sorted([r[0] for r in conn.execute("select distinct subject_category from entries where subject_category is not null and subject_category != ''").fetchall()])

# Also extract all unique components separated by ' > '
sem_components = set()
for s in sem:
    for part in s.split(' > '):
        sem_components.add(part.strip())

sub_components = set()
for s in sub:
    for part in s.split(' > '):
        sub_components.add(part.strip())

data = {
    'semantic_full': sem,
    'semantic_components': sorted(list(sem_components)),
    'subject_full': sub,
    'subject_components': sorted(list(sub_components))
}

with open('categories_extracted.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Extracted {len(sem)} full semantic categories ({len(sem_components)} components)")
print(f"Extracted {len(sub)} full subject categories ({len(sub_components)} components)")
conn.close()
