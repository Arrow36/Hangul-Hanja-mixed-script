"""
Import Korean dictionary ZIP into SQLite database.

Usage:
    python scripts/import_dictionary.py "C:/path/to/dictionary.zip"
"""

import sys
import os
import json
import zipfile
import hashlib
import sqlite3
import re
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from contextlib import closing

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CJK_RE = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')


def get_db_path():
    db_name = os.environ.get('HANJA_DB_PATH', 'hanja_dict.db')
    if os.path.isabs(db_name):
        return db_name
    return str(PROJECT_ROOT / db_name)


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


def compute_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(block)
    return sha256_hash.hexdigest().upper()


def has_cjk(text):
    if not text:
        return False
    return bool(CJK_RE.search(text))


def classify_origin(origin, written_form):
    """Classify origin string and determine replacement.
    
    Returns: (replacement, replacement_type, is_reliable)
    """
    if not origin or not has_cjk(origin):
        return None, None, 0
    
    clean_wf = written_form.strip('-')
    
    # Slash variants
    if '/' in origin:
        parts = origin.split('/')
        first_part = parts[0].strip()
        if re.fullmatch(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+', first_part):
            if len(first_part) == len(clean_wf):
                return first_part, 'slash_variants', 1
        return origin, 'slash_variants', 0
    
    # Pure CJK characters
    if re.fullmatch(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+', origin):
        if len(clean_wf) == len(origin):
            return origin, 'pure_hanja', 1
        else:
            return origin, 'pure_hanja', 0
    
    # Mixed with Hangul (e.g., '不正하다')
    if re.search(r'[\uac00-\ud7a3]', origin):
        m = re.match(r'^([\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+)([\uac00-\ud7a3]+)$', origin)
        if m:
            hanja_part = m.group(1)
            hangul_suffix = m.group(2)
            if clean_wf.endswith(hangul_suffix):
                stem = clean_wf[:-len(hangul_suffix)]
                if len(stem) == len(hanja_part):
                    return hanja_part, 'mixed', 1
            return origin, 'mixed', 0
        return origin, 'mixed', 0
    
    # Foreign mixed (e.g., 'game機')
    if re.search(r'[A-Za-z0-9]', origin):
        return origin, 'foreign_mixed', 0
    
    return origin, 'unresolved', 0


from app.schema import create_schema


def import_entry(conn, entry, stats, id_tracker):
    """Import a single dictionary entry and all its children."""
    raw_val = int(entry['val'])
    
    # Handle duplicate val (headword vs idioms/proverbs)
    if raw_val not in id_tracker:
        id_tracker[raw_val] = 0
        entry_id = raw_val
    else:
        id_tracker[raw_val] += 1
        entry_id = raw_val * 10000 + id_tracker[raw_val]
    
    feats = get_feat_dict(entry.get('feat'))
    
    lemmas = ensure_list(entry.get('Lemma'))
    written_form = ''
    variant = ''
    for lem in lemmas:
        lem_feats = get_feat_dict(lem.get('feat'))
        if 'writtenForm' in lem_feats:
            written_form = first_val(lem_feats['writtenForm'])
        if 'variant' in lem_feats:
            variant = first_val(lem_feats['variant'])
    
    if not written_form:
        stats['skipped'] += 1
        return
    
    origin_raw = first_val(feats.get('origin', ''))
    homonym_num = feats.get('homonym_number', '')
    import_error = None
    try:
        homonym_num = int(homonym_num) if homonym_num else None
    except (ValueError, TypeError):
        homonym_num = None
    
    conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    
    raw_json = json.dumps(entry, ensure_ascii=False)
    conn.execute('''
        INSERT INTO entries (
            id, target_code, written_form, variant, homonym_number, lexical_unit,
            part_of_speech, origin_raw, vocabulary_level, annotation,
            semantic_category, subject_category, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        entry_id,
        raw_val,
        written_form,
        variant or None,
        homonym_num,
        first_val(feats.get('lexicalUnit', '')),
        first_val(feats.get('partOfSpeech', '')),
        origin_raw or None,
        first_val(feats.get('vocabularyLevel', '')),
        first_val(feats.get('annotation', '')),
        first_val(feats.get('semanticCategory', '')),
        first_val(feats.get('subjectCategiory', '')),
        raw_json,
    ))
    stats['entries'] += 1
    
    # Senses
    senses = ensure_list(entry.get('Sense'))
    for sense in senses:
        sense_number = sense.get('val', '')
        s_feats = get_feat_dict(sense.get('feat'))
        
        cursor = conn.execute('''
            INSERT INTO senses (
                entry_id, sense_number, definition, annotation,
                syntactic_annotation, syntactic_pattern
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            entry_id,
            str(sense_number),
            first_val(s_feats.get('definition', '')),
            first_val(s_feats.get('annotation', '')),
            first_val(s_feats.get('syntacticAnnotation', '')),
            first_val(s_feats.get('syntacticPattern', '')),
        ))
        sense_db_id = cursor.lastrowid
        stats['senses'] += 1
        
        # Equivalents
        for eq in ensure_list(sense.get('Equivalent')):
            eq_feats = get_feat_dict(eq.get('feat'))
            conn.execute('''
                INSERT INTO equivalents (sense_id, language, lemma, definition)
                VALUES (?, ?, ?, ?)
            ''', (
                sense_db_id,
                first_val(eq_feats.get('language', '')),
                first_val(eq_feats.get('lemma', '')),
                first_val(eq_feats.get('definition', '')),
            ))
        
        # Sense examples
        for group_idx, ex in enumerate(ensure_list(sense.get('SenseExample'))):
            ex_feats = get_feat_dict(ex.get('feat'))
            examples = ensure_list(ex_feats.get('example', ''))
            example_types = ensure_list(ex_feats.get('type', ''))
            for order_idx, example_text in enumerate(examples):
                example_text = example_text or ''
                example_type = example_types[min(order_idx, len(example_types) - 1)] if example_types else ''
                conn.execute('''
                    INSERT INTO sense_examples (sense_id, group_index, order_index, example_type, example)
                    VALUES (?, ?, ?, ?, ?)
                ''', (sense_db_id, group_idx, order_idx, example_type, example_text))
                stats['examples'] += 1
        
        # Sense relations
        for rel in ensure_list(sense.get('SenseRelation')):
            rel_feats = get_feat_dict(rel.get('feat'))
            conn.execute('''
                INSERT INTO sense_relations (
                    sense_id, target_entry_id, target_lemma,
                    target_homonym_number, relation_type
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                sense_db_id,
                first_val(rel_feats.get('id', '')),
                first_val(rel_feats.get('lemma', '')),
                first_val(rel_feats.get('homonymNumber', '')),
                first_val(rel_feats.get('type', '')),
            ))
        
        # Multimedia
        for mm in ensure_list(sense.get('Multimedia')):
            mm_feats = get_feat_dict(mm.get('feat'))
            conn.execute('''
                INSERT INTO multimedia (sense_id, label, media_type, url)
                VALUES (?, ?, ?, ?)
            ''', (
                sense_db_id,
                first_val(mm_feats.get('label', '')),
                first_val(mm_feats.get('type', '')),
                first_val(mm_feats.get('url', '')),
            ))
    
    # Word forms
    for wf in ensure_list(entry.get('WordForm')):
        wf_feats = get_feat_dict(wf.get('feat'))
        cursor = conn.execute('''
            INSERT INTO word_forms (
                entry_id, form_type, written_form, pronunciation, sound_url
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            entry_id,
            first_val(wf_feats.get('type', '')),
            first_val(wf_feats.get('writtenForm', '')),
            first_val(wf_feats.get('pronunciation', '')),
            first_val(wf_feats.get('sound', '')),
        ))
        wf_db_id = cursor.lastrowid
        
        for fr in ensure_list(wf.get('FormRepresentation')):
            fr_feats = get_feat_dict(fr.get('feat'))
            conn.execute('''
                INSERT INTO form_representations (
                    word_form_id, repr_type, written_form, pronunciation, sound_url
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                wf_db_id,
                first_val(fr_feats.get('type', '')),
                first_val(fr_feats.get('writtenForm', '')),
                first_val(fr_feats.get('pronunciation', '')),
                first_val(fr_feats.get('sound', '')),
            ))
    
    # Related forms
    for rf in ensure_list(entry.get('RelatedForm')):
        rf_feats = get_feat_dict(rf.get('feat'))
        conn.execute('''
            INSERT INTO related_forms (
                entry_id, target_entry_id, relation_type, written_form
            ) VALUES (?, ?, ?, ?)
        ''', (
            entry_id,
            first_val(rf_feats.get('id', '')),
            first_val(rf_feats.get('type', '')),
            first_val(rf_feats.get('writtenForm', '')),
        ))
    
    # Conversion candidates
    if origin_raw and has_cjk(origin_raw):
        replacement, rtype, reliable = classify_origin(origin_raw, written_form)
        if replacement:
            clean_wf = written_form.strip('-')
            conn.execute('''
                INSERT INTO conversion_candidates (
                    written_form, entry_id, origin_raw, replacement,
                    replacement_type, is_reliable
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                clean_wf,
                entry_id,
                origin_raw,
                replacement,
                rtype,
                reliable,
            ))
        stats['origin_entries'] += 1


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_dictionary.py <zip_path>")
        sys.exit(1)
    
    zip_path = sys.argv[1]
    if not os.path.exists(zip_path):
        print(f"Error: ZIP file not found: {zip_path}")
        sys.exit(1)
    
    db_path = get_db_path()
    print(f"ZIP file: {zip_path}")
    print(f"Database: {db_path}")
    
    print("Computing SHA-256...")
    sha256 = compute_sha256(zip_path)
    print(f"SHA-256: {sha256}")
    
    # Build the new dictionary beside the live file. The existing database is
    # replaced only after the full import and integrity checks succeed.
    temp_db_path = str(Path(db_path).with_suffix(Path(db_path).suffix + '.importing'))
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    
    # Clear existing data for clean import
    conn.executescript('''
        DROP TABLE IF EXISTS conversion_candidates;
        DROP TABLE IF EXISTS related_forms;
        DROP TABLE IF EXISTS form_representations;
        DROP TABLE IF EXISTS word_forms;
        DROP TABLE IF EXISTS multimedia;
        DROP TABLE IF EXISTS sense_relations;
        DROP TABLE IF EXISTS sense_examples;
        DROP TABLE IF EXISTS equivalents;
        DROP TABLE IF EXISTS senses;
        DROP TABLE IF EXISTS entries;
        DROP TABLE IF EXISTS import_metadata;
    ''')
    create_schema(conn)
    
    stats = {
        'entries': 0,
        'senses': 0,
        'examples': 0,
        'origin_entries': 0,
        'skipped': 0,
        'errors': 0,
    }
    
    source_counts = {'entries': 0, 'senses': 0, 'examples': 0}
    id_tracker = {}
    import_start = datetime.now(timezone.utc).isoformat()
    import_error = None
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            json_files = sorted([f for f in zf.namelist() if f.endswith('.json')])
            print(f"\nFound {len(json_files)} JSON files")
            if not json_files:
                raise RuntimeError("Empty or invalid dictionary zip: no JSON files found")
            
            for file_idx, filename in enumerate(json_files, 1):
                print(f"[{file_idx}/{len(json_files)}] Processing {filename}...")
                
                with zf.open(filename) as f:
                    data = json.loads(f.read())
                
                lexicon = data.get('LexicalResource', {}).get('Lexicon', {})
                entries = ensure_list(lexicon.get('LexicalEntry', []))
                if not entries:
                    raise RuntimeError(f'No lexical entries in {filename}')
                source_counts['entries'] += len(entries)
                for source_entry in entries:
                    source_senses = ensure_list(source_entry.get('Sense'))
                    source_counts['senses'] += len(source_senses)
                    for sense in source_senses:
                        for example in ensure_list(sense.get('SenseExample')):
                            source_counts['examples'] += sum(1 for feat in ensure_list(example.get('feat')) if feat.get('att') == 'example')
                
                conn.execute("BEGIN TRANSACTION")
                try:
                    for entry in entries:
                        entry_id = entry.get('val', '?')
                        try:
                            conn.execute('SAVEPOINT import_entry')
                            import_entry(conn, entry, stats, id_tracker)
                            conn.execute('RELEASE SAVEPOINT import_entry')
                        except Exception as e:
                            conn.execute('ROLLBACK TO SAVEPOINT import_entry')
                            conn.execute('RELEASE SAVEPOINT import_entry')
                            stats['errors'] += 1
                            raise RuntimeError(f"entry {entry_id}: {e}") from e
                    
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f"  FATAL error in {filename}: {e}")
                    raise
        
        # Validate against this archive, rather than requiring an old snapshot's totals.
        for key, table in [('entries', 'entries'), ('senses', 'senses'), ('examples', 'sense_examples')]:
            actual = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            if actual != source_counts[key] or actual != stats[key] or actual == 0:
                raise RuntimeError(f'{key} mismatch: source={source_counts[key]}, imported={stats[key]}, database={actual}')
        if stats['errors'] or stats['skipped']:
            raise RuntimeError('Dictionary import contains skipped or failed entries')
        if conn.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('Dictionary foreign key check failed')
        versions = {match.group(1) for name in json_files if (match := re.search(r'_(\d{8})\.json$', name))}
        if len(versions) != 1:
            raise RuntimeError('JSON files must identify one consistent snapshot date')
        data_version = versions.pop()
        conn.execute('''
            INSERT INTO import_metadata (
                source_filename, sha256, import_timestamp, data_version,
                total_entries, total_senses, total_examples, origin_entries
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            os.path.basename(zip_path),
            sha256,
            import_start,
            data_version,
            stats['entries'],
            stats['senses'],
            stats['examples'],
            stats['origin_entries'],
        ))
        conn.commit()

        integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity != 'ok':
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        
    except Exception as e:
        print(f"\nImport failed: {e}")
        import traceback
        traceback.print_exc()
        import_error = e
    finally:
        conn.close()

    if import_error is not None:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        sys.exit(1)

    # Safe atomic replacement with backup
    if os.path.exists(db_path):
        import shutil
        backup_path = str(Path(db_path).with_suffix('.db.bak'))
        with closing(sqlite3.connect(db_path)) as old, closing(sqlite3.connect(backup_path)) as backup:
            old.backup(backup)
        print(f"Backed up previous database to: {backup_path}")

    os.replace(temp_db_path, db_path)
    
    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"Total entries:        {stats['entries']:>8}")
    print(f"Total senses:         {stats['senses']:>8}")
    print(f"Total examples:       {stats['examples']:>8}")
    print(f"Entries with hanja:   {stats['origin_entries']:>8}")
    print(f"Skipped:              {stats['skipped']:>8}")
    print(f"Errors:               {stats['errors']:>8}")
    print(f"Database: {db_path}")


if __name__ == '__main__':
    main()
