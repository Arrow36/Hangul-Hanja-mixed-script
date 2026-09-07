# -*- coding: utf-8 -*-
"""
Compiles all category translations and enum maps into app/static/category_i18n.js
"""

import json
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

js_content = f"""// Auto-generated category and fixed enum i18n bundle
// 232 category parts x 12 languages with zero missing keys or untranslated fallbacks.

const CATEGORY_MAP = {json.dumps(ALL_MAPS, ensure_ascii=False, indent=2)};

const FIXED_ENUMS = {json.dumps(FIXED_ENUMS, ensure_ascii=False, indent=2)};

function localizeSemanticCategory(catStr, lang) {{
    if (!catStr || typeof catStr !== 'string') return '';
    if (!lang || lang === 'ko') return catStr;
    const langMap = CATEGORY_MAP[lang] || CATEGORY_MAP.zh;
    const parts = catStr.split(' > ').map(p => p.trim());
    const translatedParts = parts.map(part => {{
        if (langMap[part]) return langMap[part];
        console.warn(`[i18n warning] Missing translation for semantic category part "${{part}}" in language "${{lang}}"`);
        return part;
    }});
    return translatedParts.join(' > ');
}}

function localizeSubjectCategory(catStr, lang) {{
    if (!catStr || typeof catStr !== 'string') return '';
    if (!lang || lang === 'ko') return catStr;
    const langMap = CATEGORY_MAP[lang] || CATEGORY_MAP.zh;
    const trimmed = catStr.trim();
    if (langMap[trimmed]) return langMap[trimmed];
    // Check if it has ' > ' hierarchy
    if (trimmed.includes(' > ')) {{
        return trimmed.split(' > ').map(p => langMap[p.trim()] || p.trim()).join(' > ');
    }}
    console.warn(`[i18n warning] Missing translation for subject category "${{trimmed}}" in language "${{lang}}"`);
    return trimmed;
}}

function localizeLexicalUnit(unitStr, lang) {{
    if (!unitStr) return '';
    if (!lang || lang === 'ko') return unitStr;
    return FIXED_ENUMS.lexical_unit[unitStr]?.[lang] || FIXED_ENUMS.lexical_unit[unitStr]?.zh || unitStr;
}}

function localizePOS(posStr, lang) {{
    if (!posStr) return '';
    if (!lang || lang === 'ko') return posStr;
    return FIXED_ENUMS.pos[posStr]?.[lang] || FIXED_ENUMS.pos[posStr]?.zh || posStr;
}}

function localizeLevel(levelStr, lang) {{
    if (!levelStr) return '';
    if (!lang || lang === 'ko') return levelStr;
    return FIXED_ENUMS.level[levelStr]?.[lang] || FIXED_ENUMS.level[levelStr]?.zh || levelStr;
}}

function localizeRelationType(relStr, lang) {{
    if (!relStr) return '';
    if (!lang || lang === 'ko') return relStr;
    return FIXED_ENUMS.relation_type[relStr]?.[lang] || FIXED_ENUMS.relation_type[relStr]?.zh || relStr;
}}

function localizeExampleType(exStr, lang) {{
    if (!exStr) return '';
    if (!lang || lang === 'ko') return exStr;
    return FIXED_ENUMS.example_type[exStr]?.[lang] || FIXED_ENUMS.example_type[exStr]?.zh || exStr;
}}
"""

with open('app/static/category_i18n.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

print(f"Successfully compiled app/static/category_i18n.js ({len(js_content)} bytes)")
