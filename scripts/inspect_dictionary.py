"""
Inspect Korean dictionary ZIP without importing.

Usage:
    python scripts/inspect_dictionary.py "C:/path/to/dictionary.zip"
"""

import sys
import json
import zipfile
import hashlib
import re
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')


def get_feat_dict(feats):
    if feats is None:
        return {}
    if isinstance(feats, dict):
        return {feats.get('att', ''): feats.get('val', '')}
    result = {}
    for f in feats:
        att = f.get('att', '')
        val = f.get('val', '')
        if att in result:
            if isinstance(result[att], list):
                result[att].append(val)
            else:
                result[att] = [result[att], val]
        else:
            result[att] = val
    return result


def ensure_list(obj):
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    return [obj]


def first_val(v):
    if isinstance(v, list):
        return v[0] if v else ''
    return v or ''


def has_cjk(text):
    if not text:
        return False
    return bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))


def get_written_form(entry):
    lemmas = ensure_list(entry.get('Lemma'))
    for lem in lemmas:
        feats = get_feat_dict(lem.get('feat'))
        if 'writtenForm' in feats:
            return first_val(feats['writtenForm'])
    return ''


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/inspect_dictionary.py <zip_path>")
        sys.exit(1)

    zip_path = sys.argv[1]

    # SHA-256
    sha256_hash = hashlib.sha256()
    with open(zip_path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(block)
    sha256 = sha256_hash.hexdigest().upper()

    print(f"File: {zip_path}")
    print(f"SHA-256: {sha256}")
    print()

    zf = zipfile.ZipFile(zip_path)
    json_files = sorted([f for f in zf.namelist() if f.endswith('.json')])
    print(f"JSON files: {len(json_files)}")
    for fname in json_files:
        info = zf.getinfo(fname)
        print(f"  {fname}: {info.file_size:,} bytes")
    print()

    # Statistics
    total_entries = 0
    total_senses = 0
    origin_count = 0
    origin_hangul_set = set()
    origin_strings = defaultdict(set)
    feat_counter = Counter()
    lemma_list_count = 0
    sense_dict_count = 0
    kisa_entries = []

    for fname in json_files:
        with zf.open(fname) as f:
            data = json.loads(f.read())

        entries = ensure_list(
            data.get('LexicalResource', {}).get('Lexicon', {}).get('LexicalEntry', [])
        )
        total_entries += len(entries)

        for e in entries:
            wf = get_written_form(e)
            feats = get_feat_dict(e.get('feat'))

            # Count senses
            senses = e.get('Sense')
            if isinstance(senses, dict):
                total_senses += 1
                sense_dict_count += 1
            elif isinstance(senses, list):
                total_senses += len(senses)

            # Lemma structure
            if isinstance(e.get('Lemma'), list):
                lemma_list_count += 1

            # Entry feats
            if isinstance(e.get('feat'), dict):
                feat_counter[e['feat'].get('att', '')] += 1
            elif isinstance(e.get('feat'), list):
                for ft in e['feat']:
                    feat_counter[ft.get('att', '')] += 1

            # Origin
            origin = first_val(feats.get('origin', ''))
            if origin and has_cjk(origin):
                origin_count += 1
                clean_wf = wf.strip('-')
                if clean_wf:
                    origin_hangul_set.add(clean_wf)
                    origin_strings[clean_wf].add(origin)

            # Collect 기사
            if wf == '기사':
                entry_id = e.get('val', '?')
                hom = first_val(feats.get('homonym_number', ''))
                orig = first_val(feats.get('origin', ''))
                pos = first_val(feats.get('partOfSpeech', ''))
                kisa_entries.append((entry_id, hom, orig, pos))

    # Multi-origin
    multi_origin = {wf: origs for wf, origs in origin_strings.items() if len(origs) > 1}
    max_count = max((len(v) for v in origin_strings.values()), default=0)

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total entries:           {total_entries}")
    print(f"Total senses:            {total_senses}")
    print(f"Origin with hanja:       {origin_count}")
    print(f"Unique hangul forms:     {len(origin_hangul_set)}")
    print(f"Multi-origin forms:      {len(multi_origin)}")
    print(f"Max origins per form:    {max_count}")
    print()
    print(f"Lemma is list:           {lemma_list_count}")
    print(f"Sense is dict:           {sense_dict_count}")
    print()
    print("Entry feat attributes:")
    for att, cnt in feat_counter.most_common():
        print(f"  {att}: {cnt}")
    print()
    print("기사 entries:")
    for eid, hom, orig, pos in kisa_entries:
        print(f"  ID={eid}, homonym={hom}, origin={orig}, pos={pos}")


if __name__ == '__main__':
    main()
