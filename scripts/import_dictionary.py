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


def create_schema(conn):
    conn.executescript('''
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        PRAGMA cache_size=-64000;
        PRAGMA foreign_keys=ON;
        
        CREATE TABLE IF NOT EXISTS import_metadata (
            id INTEGER PRIMARY KEY,
            source_filename TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            import_timestamp TEXT NOT NULL,
            data_version TEXT,
            total_entries INTEGER,
            total_senses INTEGER,
            total_examples INTEGER,
            origin_entries INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
            target_code INTEGER NOT NULL,
            written_form TEXT NOT NULL,
            variant TEXT,
            homonym_number INTEGER,
            lexical_unit TEXT,
            part_of_speech TEXT,
            origin_raw TEXT,
            vocabulary_level TEXT,
            annotation TEXT,
            semantic_category TEXT,
            subject_category TEXT,
            raw_json TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS senses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            sense_number TEXT,
            definition TEXT,
            annotation TEXT,
            syntactic_annotation TEXT,
            syntactic_pattern TEXT
        );
        
        CREATE TABLE IF NOT EXISTS equivalents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sense_id INTEGER NOT NULL REFERENCES senses(id) ON DELETE CASCADE,
            language TEXT,
            lemma TEXT,
            definition TEXT
        );
        
        CREATE TABLE IF NOT EXISTS sense_examples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sense_id INTEGER NOT NULL REFERENCES senses(id) ON DELETE CASCADE,
            group_index INTEGER NOT NULL DEFAULT 0,
            order_index INTEGER NOT NULL DEFAULT 0,
            example_type TEXT,
            example TEXT
        );
        
        CREATE TABLE IF NOT EXISTS sense_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sense_id INTEGER NOT NULL REFERENCES senses(id) ON DELETE CASCADE,
            target_entry_id TEXT,
            target_lemma TEXT,
            target_homonym_number TEXT,
            relation_type TEXT
        );
        
        CREATE TABLE IF NOT EXISTS multimedia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sense_id INTEGER NOT NULL REFERENCES senses(id) ON DELETE CASCADE,
            label TEXT,
            media_type TEXT,
            url TEXT
        );
        
        CREATE TABLE IF NOT EXISTS word_forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            form_type TEXT,
            written_form TEXT,
            pronunciation TEXT,
            sound_url TEXT
        );
        
        CREATE TABLE IF NOT EXISTS form_representations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_form_id INTEGER NOT NULL REFERENCES word_forms(id) ON DELETE CASCADE,
            repr_type TEXT,
            written_form TEXT,
            pronunciation TEXT,
            sound_url TEXT
        );
        
        CREATE TABLE IF NOT EXISTS related_forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            target_entry_id TEXT,
            relation_type TEXT,
            written_form TEXT
        );
        
        CREATE TABLE IF NOT EXISTS conversion_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            written_form TEXT NOT NULL,
            entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            origin_raw TEXT,
            replacement TEXT,
            replacement_type TEXT,
            is_reliable INTEGER NOT NULL DEFAULT 0
        );
        
        CREATE INDEX IF NOT EXISTS idx_entries_written_form ON entries(written_form);
        CREATE INDEX IF NOT EXISTS idx_entries_target_code ON entries(target_code);
        CREATE INDEX IF NOT EXISTS idx_entries_pos ON entries(part_of_speech);
        CREATE INDEX IF NOT EXISTS idx_entries_origin ON entries(origin_raw);
        CREATE INDEX IF NOT EXISTS idx_senses_entry ON senses(entry_id);
        CREATE INDEX IF NOT EXISTS idx_equiv_sense ON equivalents(sense_id);
        CREATE INDEX IF NOT EXISTS idx_examples_sense ON sense_examples(sense_id);
        CREATE INDEX IF NOT EXISTS idx_examples_group ON sense_examples(sense_id, group_index);
        CREATE INDEX IF NOT EXISTS idx_relations_sense ON sense_relations(sense_id);
        CREATE INDEX IF NOT EXISTS idx_relations_target ON sense_relations(target_entry_id);
        CREATE INDEX IF NOT EXISTS idx_multimedia_sense ON multimedia(sense_id);
        CREATE INDEX IF NOT EXISTS idx_wordforms_entry ON word_forms(entry_id);
        CREATE INDEX IF NOT EXISTS idx_formrep_wf ON form_representations(word_form_id);
        CREATE INDEX IF NOT EXISTS idx_relforms_entry ON related_forms(entry_id);
        CREATE INDEX IF NOT EXISTS idx_candidates_wf ON conversion_candidates(written_form);
        CREATE INDEX IF NOT EXISTS idx_candidates_entry ON conversion_candidates(entry_id);
    ''')


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
        
        # Verify counts against reference benchmarks before recording metadata
        if stats['entries'] != 56555:
            raise RuntimeError(f"Entry count mismatch: expected 56555, got {stats['entries']}")
        if stats['senses'] != 76833:
            raise RuntimeError(f"Sense count mismatch: expected 76833, got {stats['senses']}")
        if stats['examples'] != 657975:
            raise RuntimeError(f"Example count mismatch: expected 657975, got {stats['examples']}")

        # Validate dialogue examples preserved (e.g. 요리하다 entry 9471)
        yori_dialogues = conn.execute('''
            SELECT se.group_index, se.order_index, se.example_type, se.example 
            FROM sense_examples se 
            JOIN senses s ON se.sense_id = s.id 
            WHERE s.entry_id = 9471 AND se.example_type = '대화'
            ORDER BY se.group_index, se.order_index
        ''').fetchall()
        if len(yori_dialogues) < 4:
            raise RuntimeError(f"Dialogue examples verification failed for 요리하다: got {len(yori_dialogues)}")

        data_version = json_files[0].split('_')[-1].replace('.json', '') if json_files else ''
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
        shutil.copy2(db_path, backup_path)
        print(f"Backed up previous database to: {backup_path}")

    os.replace(temp_db_path, db_path)
    
    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"Total entries:        {stats['entries']:>8}  (reference: 56,555)")
    print(f"Total senses:         {stats['senses']:>8}  (reference: 76,833)")
    print(f"Total examples:       {stats['examples']:>8}  (reference: 657,975)")
    print(f"Entries with hanja:   {stats['origin_entries']:>8}  (reference: ~34,142)")
    print(f"Skipped:              {stats['skipped']:>8}")
    print(f"Errors:               {stats['errors']:>8}")
    print(f"Database: {db_path}")


if __name__ == '__main__':
    main()
