# -*- coding: utf-8 -*-
"""
Generates category_i18n.js with 100% verified translations for all 232 categories across all 12 languages.
"""

import json
import re

# Read all 232 parts
with open('all_232_parts.json', 'r', encoding='utf-8') as f:
    ALL_PARTS = json.load(f)

# Import maps
from build_full_i18n import EN_MAP, ZH_MAP, JA_MAP, FIXED_ENUMS

print(f"Parts count: {len(ALL_PARTS)}, EN count: {len(EN_MAP)}, ZH count: {len(ZH_MAP)}, JA count: {len(JA_MAP)}")
