"""Package SQLite pour Amazon Scraper Pro.

Expose l'ensemble des procédures d'accès aux données et de gestion de connexion.
"""
from app.sqlite.connection import DEFAULT_DB_PATH, db_session, get_connection
from app.sqlite.procedures import (
    proc_clear_all,
    proc_count,
    proc_delete,
    proc_get_all,
    proc_get_by_id,
    proc_get_by_category,
    proc_get_by_url,
    proc_get_stats,
    proc_init_db,
    proc_insert_many,
    proc_insert_product,
    proc_search,
    proc_update_price,
)

__all__ = [
    "DEFAULT_DB_PATH",
    "get_connection",
    "db_session",
    "proc_init_db",
    "proc_insert_product",
    "proc_insert_many",
    "proc_get_all",
    "proc_get_by_id",
    "proc_get_by_url",
    "proc_get_by_category",
    "proc_search",
    "proc_update_price",
    "proc_delete",
    "proc_count",
    "proc_get_stats",
    "proc_clear_all",
]
