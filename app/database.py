"""Locate and validate an imported dictionary without modifying it at startup."""
import os
import sqlite3
import asyncio
from contextlib import closing
from pathlib import Path
from app.schema import SCHEMA_SQL, SCHEMA_VERSION

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def get_db_path() -> Path:
    path = Path(os.environ.get("HANJA_DB_PATH", "hanja_dict.db"))
    return (path if path.is_absolute() else PROJECT_ROOT / path).resolve()

def validate_database(path: Path) -> None:
    help_text = "Run python scripts/import_dictionary.py <dictionary.zip> first."
    if not path.is_file():
        raise RuntimeError(f"Dictionary database not found: {path}. {help_text}")
    try:
        with closing(sqlite3.connect(":memory:")) as expected, closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as actual:
            expected.executescript(SCHEMA_SQL)
            version = actual.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError("Dictionary schema is newer than this application.")
            tables = expected.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            for (table,) in tables:
                required = {r[1] for r in expected.execute(f'PRAGMA table_info({table})')}
                present = {r[1] for r in actual.execute(f'PRAGMA table_info({table})')}
                if required - present:
                    raise RuntimeError(f"Incompatible dictionary schema: {table} missing {sorted(required-present)}. {help_text}")
            if not actual.execute("SELECT 1 FROM entries LIMIT 1").fetchone():
                raise RuntimeError(f"Dictionary database is empty. {help_text}")
    except sqlite3.DatabaseError as exc:
        raise RuntimeError(f"Cannot read dictionary database: {path}. {help_text}") from exc

async def init_db() -> None:
    await asyncio.to_thread(validate_database, get_db_path())
