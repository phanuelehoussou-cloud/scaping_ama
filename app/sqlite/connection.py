"""Module de connexion SQLite pour Amazon Scraper Pro."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Generator, Optional, Union

import config

DEFAULT_DB_PATH: Path = config.SQLITE_DB_PATH


def get_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Crée et configure une connexion SQLite avec row_factory et mode WAL."""
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(path),
        check_same_thread=False,
        timeout=20.0,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextmanager
def db_session(
    db_path: Optional[Union[str, Path]] = None,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager gérant automatiquement le commit, rollback et la fermeture."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
