"""Canonical dictionary schema, shared by import and validation."""

SCHEMA_VERSION = 1
SCHEMA_SQL = """
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
    
PRAGMA user_version=1;
"""

def create_schema(conn):
    conn.executescript(SCHEMA_SQL)
