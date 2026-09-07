# -*- coding: utf-8 -*-
import json
import re

with open('all_232_parts.json', 'r', encoding='utf-8') as f:
    ALL_PARTS = set(json.load(f))

from build_full_i18n import EN_MAP, ZH_MAP, JA_MAP, FIXED_ENUMS
from add_other_languages import FR_MAP, ES_MAP, RU_MAP
from add_asian_languages import VI_MAP, ID_MAP
from add_mn_ar_th import MN_MAP, AR_MAP, TH_MAP

ALL_MAPS = {
    'en': EN_MAP,
    'zh': ZH_MAP,
    'ja': JA_MAP,
    'fr': FR_MAP,
    'es': ES_MAP,
    'ru': RU_MAP,
    'vi': VI_MAP,
    'id': ID_MAP,
    'mn': MN_MAP,
    'ar': AR_MAP,
    'th': TH_MAP,
}

korean_regex = re.compile(r'[\uac00-\ud7af]')

errors = []

for lang, mapping in ALL_MAPS.items():
    if len(mapping) != 232:
        errors.append(f"[{lang}] expected 232 keys, got {len(mapping)}")
    missing = ALL_PARTS - set(mapping.keys())
    if missing:
        errors.append(f"[{lang}] missing keys: {missing}")
    extra = set(mapping.keys()) - ALL_PARTS
    if extra:
        errors.append(f"[{lang}] extra unexpected keys: {extra}")

    # Check that translations don't duplicate Korean key or contain Korean chars
    for k, v in mapping.items():
        if not v or not v.strip():
            errors.append(f"[{lang}] empty translation for key '{k}'")
        if v.strip() == k.strip():
            errors.append(f"[{lang}] untranslated duplicate for key '{k}'")
        if korean_regex.search(v):
            errors.append(f"[{lang}] Korean characters found in translation of '{k}': '{v}'")

if errors:
    print(f"FAILED with {len(errors)} errors:")
    for e in errors[:20]:
        print(" -", e)
    exit(1)
else:
    print("SUCCESS! All 232 category parts 100% verified across all 11 non-Korean languages!")
    print("No missing keys, no untranslated duplicates, no residual Korean text.")
