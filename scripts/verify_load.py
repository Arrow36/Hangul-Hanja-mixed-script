"""
Generate comprehensive category_i18n.js covering all 232 category parts and fixed enums
for all 12 supported languages: zh, ko, en, ja, fr, es, ru, vi, mn, ar, th, id.
"""

import json
import re

# Load all 232 parts
with open('all_232_parts.json', 'r', encoding='utf-8') as f:
    ALL_PARTS = json.load(f)

print(f"Loaded {len(ALL_PARTS)} parts.")
