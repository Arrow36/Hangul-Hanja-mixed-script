import os
import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

def get_db_path() -> Path:
    # Use environment variable or default to a local file
    db_path_str = os.environ.get("HANJA_DB_PATH", "hanja_dict.db")
    return Path(db_path_str).resolve()

async def init_db() -> None:
    db_path = get_db_path()
    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA cache_size=-64000")
        await db.execute("PRAGMA foreign_keys=ON")
        
        # Tables
        await db.execute('''
        CREATE TABLE IF NOT EXISTS import_metadata (
            id INTEGER PRIMARY KEY,
            source_filename TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            import_timestamp TEXT NOT NULL,
            data_version TEXT,
            total_entries INTEGER,
            total_senses INTEGER,
            origin_entries INTEGER
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
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
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS senses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL REFERENCES entries(id),
            sense_number TEXT,
            definition TEXT,
            annotation TEXT,
            syntactic_annotation TEXT,
            syntactic_pattern TEXT
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS equivalents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sense_id INTEGER NOT NULL REFERENCES senses(id),
            language TEXT,
            lemma TEXT,
            definition TEXT
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS sense_examples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sense_id INTEGER NOT NULL REFERENCES senses(id),
            example_type TEXT,
            example TEXT
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS sense_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sense_id INTEGER NOT NULL REFERENCES senses(id),
            target_entry_id TEXT,
            target_lemma TEXT,
            target_homonym_number TEXT,
            relation_type TEXT
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS multimedia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sense_id INTEGER NOT NULL REFERENCES senses(id),
            label TEXT,
            media_type TEXT,
            url TEXT
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS word_forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL REFERENCES entries(id),
            form_type TEXT,
            written_form TEXT,
            pronunciation TEXT,
            sound_url TEXT
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS form_representations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_form_id INTEGER NOT NULL REFERENCES word_forms(id),
            repr_type TEXT,
            written_form TEXT,
            pronunciation TEXT,
            sound_url TEXT
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS related_forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL REFERENCES entries(id),
            target_entry_id TEXT,
            relation_type TEXT,
            written_form TEXT
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS conversion_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            written_form TEXT NOT NULL,
            entry_id INTEGER NOT NULL REFERENCES entries(id),
            origin_raw TEXT,
            replacement TEXT,
            replacement_type TEXT,
            is_reliable INTEGER NOT NULL DEFAULT 0
        )
        ''')
        
        # Indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_entries_written_form ON entries(written_form)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_entries_pos ON entries(part_of_speech)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_entries_origin_raw ON entries(origin_raw)")
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_senses_entry_id ON senses(entry_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_equivalents_sense_id ON equivalents(sense_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sense_examples_sense_id ON sense_examples(sense_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sense_relations_sense_id ON sense_relations(sense_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sense_relations_target ON sense_relations(target_entry_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_multimedia_sense_id ON multimedia(sense_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_word_forms_entry_id ON word_forms(entry_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_form_representations_word_form_id ON form_representations(word_form_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_related_forms_entry_id ON related_forms(entry_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_conversion_candidates_written_form ON conversion_candidates(written_form)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_conversion_candidates_entry_id ON conversion_candidates(entry_id)")

        # Full-text search on entries.written_form and entries.origin_raw
        await db.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
            written_form,
            origin_raw,
            content='entries',
            content_rowid='id'
        )
        ''')
        
        # Triggers for FTS updates
        await db.execute('''
        CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
            INSERT INTO entries_fts(rowid, written_form, origin_raw) VALUES (new.id, new.written_form, new.origin_raw);
        END;
        ''')
        await db.execute('''
        CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
            INSERT INTO entries_fts(entries_fts, rowid, written_form, origin_raw) VALUES('delete', old.id, old.written_form, old.origin_raw);
        END;
        ''')
        await db.execute('''
        CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
            INSERT INTO entries_fts(entries_fts, rowid, written_form, origin_raw) VALUES('delete', old.id, old.written_form, old.origin_raw);
            INSERT INTO entries_fts(rowid, written_form, origin_raw) VALUES (new.id, new.written_form, new.origin_raw);
        END;
        ''')
        
        await db.commit()

@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        yield db

async def execute_query(db: aiosqlite.Connection, query: str, params: tuple = ()) -> aiosqlite.Cursor:
    return await db.execute(query, params)
