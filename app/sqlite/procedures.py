"""Procédures de gestion de la base de données SQLite pour Amazon Scraper Pro.

Toutes les opérations SQL sont paramétrées avec '?' pour garantir la sécurité
contre les injections SQL et gérées sous forme de transactions fiables.
"""
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from app.models.item import Produit
from app.sqlite.connection import db_session, get_connection

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# Colonnes autorisées pour le tri dynamique sécurisé
ALLOWED_SORT_COLUMNS = {
    "id": "id",
    "prix": "prix",
    "note": "note",
    "nom": "nom",
    "date_scrape": "date_scrape",
    "categorie": "categorie",
}


# ==============================================================================
# 1. INITIALISATION DU SCHÉMA
# ==============================================================================
def proc_init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """Procédure : crée la table 'produits' et ses index si non existants."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with db_session(db_path) as conn:
        conn.executescript(schema_sql)


# ==============================================================================
# 2. INSERTION ET MISE À JOUR (UPSERT)
# ==============================================================================
def proc_insert_product(
    produit: Produit,
    db_path: Optional[Union[str, Path]] = None,
    on_conflict: str = "update",
) -> Optional[int]:
    """Procédure : insère un produit unique.

    - on_conflict="update" : met à jour le prix, note, disponibilité et date en cas de doublon sur l'URL.
    - on_conflict="ignore" : ignore silencieusement les doublons d'URL.
    Retourne l'ID du produit inséré/mis à jour.
    """
    dispo_int = 1 if produit.disponibilite else 0

    if on_conflict == "update":
        sql = """
        INSERT INTO produits (nom, prix, note, disponibilite, url, image, categorie, date_scrape)
        VALUES (?, ?, ?, ?, ?, ?, ?, DATETIME('now', 'localtime'))
        ON CONFLICT(url) DO UPDATE SET
            nom = excluded.nom,
            prix = excluded.prix,
            note = excluded.note,
            disponibilite = excluded.disponibilite,
            image = excluded.image,
            categorie = excluded.categorie,
            date_scrape = DATETIME('now', 'localtime')
        RETURNING id;
        """
        with db_session(db_path) as conn:
            cursor = conn.execute(
                sql,
                (
                    produit.nom,
                    produit.prix,
                    produit.note,
                    dispo_int,
                    produit.url,
                    produit.image,
                    produit.categorie,
                ),
            )
            row = cursor.fetchone()
            return row["id"] if row else None
    else:
        sql = """
        INSERT OR IGNORE INTO produits (nom, prix, note, disponibilite, url, image, categorie, date_scrape)
        VALUES (?, ?, ?, ?, ?, ?, ?, DATETIME('now', 'localtime'));
        """
        with db_session(db_path) as conn:
            cursor = conn.execute(
                sql,
                (
                    produit.nom,
                    produit.prix,
                    produit.note,
                    dispo_int,
                    produit.url,
                    produit.image,
                    produit.categorie,
                ),
            )
            return cursor.lastrowid if cursor.rowcount > 0 else None


def proc_insert_many(
    produits: Iterable[Produit],
    db_path: Optional[Union[str, Path]] = None,
    on_conflict: str = "update",
) -> int:
    """Procédure : insère un lot de produits dans une seule transaction optimisée.

    Retourne le nombre total de produits traités.
    """
    records = [
        (
            p.nom,
            p.prix,
            p.note,
            1 if p.disponibilite else 0,
            p.url,
            p.image,
            p.categorie,
        )
        for p in produits
    ]
    if not records:
        return 0

    if on_conflict == "update":
        sql = """
        INSERT INTO produits (nom, prix, note, disponibilite, url, image, categorie, date_scrape)
        VALUES (?, ?, ?, ?, ?, ?, ?, DATETIME('now', 'localtime'))
        ON CONFLICT(url) DO UPDATE SET
            nom = excluded.nom,
            prix = excluded.prix,
            note = excluded.note,
            disponibilite = excluded.disponibilite,
            image = excluded.image,
            categorie = excluded.categorie,
            date_scrape = DATETIME('now', 'localtime');
        """
    else:
        sql = """
        INSERT OR IGNORE INTO produits (nom, prix, note, disponibilite, url, image, categorie, date_scrape)
        VALUES (?, ?, ?, ?, ?, ?, ?, DATETIME('now', 'localtime'));
        """

    with db_session(db_path) as conn:
        conn.executemany(sql, records)

    return len(records)


# ==============================================================================
# 3. LECTURE ET SÉLECTION
# ==============================================================================
def proc_get_all(
    db_path: Optional[Union[str, Path]] = None,
    order_by: str = "id DESC",
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Produit]:
    """Procédure : récupère la liste complète des produits avec tri sécurisé et pagination."""
    # Nettoyage et validation sécurisée du ORDER BY
    order_parts = order_by.strip().split()
    col = order_parts[0].lower() if order_parts else "id"
    direction = "DESC" if len(order_parts) > 1 and order_parts[1].upper() == "DESC" else "ASC"
    safe_col = ALLOWED_SORT_COLUMNS.get(col, "id")
    safe_order = f"{safe_col} {direction}"

    sql = f"SELECT * FROM produits ORDER BY {safe_order}"
    params: List[Any] = []

    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])

    conn = get_connection(db_path)
    try:
        cursor = conn.execute(sql, params)
        return [Produit.from_row(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def proc_get_by_id(
    product_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Produit]:
    """Procédure : recherche un produit par son identifiant unique ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM produits WHERE id = ?;", (product_id,))
        row = cursor.fetchone()
        return Produit.from_row(row) if row else None
    finally:
        conn.close()


def proc_get_by_url(
    url: str,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Produit]:
    """Procédure : recherche un produit par son URL Amazon unique."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM produits WHERE url = ?;", (url,))
        row = cursor.fetchone()
        return Produit.from_row(row) if row else None
    finally:
        conn.close()


def proc_get_by_category(
    categorie: str,
    db_path: Optional[Union[str, Path]] = None,
    limit: Optional[int] = None,
) -> List[Produit]:
    """Procédure : retourne tous les produits associés à une catégorie."""
    sql = "SELECT * FROM produits WHERE categorie = ? ORDER BY id DESC"
    params: List[Any] = [categorie]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))

    conn = get_connection(db_path)
    try:
        cursor = conn.execute(sql, params)
        return [Produit.from_row(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def proc_search(
    keyword: str,
    db_path: Optional[Union[str, Path]] = None,
    limit: Optional[int] = None,
) -> List[Produit]:
    """Procédure : recherche textuelle par mot-clé dans le nom du produit."""
    sql = "SELECT * FROM produits WHERE nom LIKE ? ORDER BY id DESC"
    params: List[Any] = [f"%{keyword}%"]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))

    conn = get_connection(db_path)
    try:
        cursor = conn.execute(sql, params)
        return [Produit.from_row(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# ==============================================================================
# 4. MODIFICATION ET SUPPRESSION
# ==============================================================================
def proc_update_price(
    product_id: int,
    new_price: float,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Procédure : met à jour le prix et la date de scrape d'un produit."""
    sql = """
    UPDATE produits
    SET prix = ?, date_scrape = DATETIME('now', 'localtime')
    WHERE id = ?;
    """
    with db_session(db_path) as conn:
        cursor = conn.execute(sql, (float(new_price), product_id))
        return cursor.rowcount > 0


def proc_delete(
    product_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Procédure : supprime un produit par son identifiant unique ID."""
    with db_session(db_path) as conn:
        cursor = conn.execute("DELETE FROM produits WHERE id = ?;", (product_id,))
        return cursor.rowcount > 0


def proc_clear_all(db_path: Optional[Union[str, Path]] = None) -> int:
    """Procédure : vide la table 'produits' et réinitialise l'auto-incrément."""
    with db_session(db_path) as conn:
        cursor = conn.execute("DELETE FROM produits;")
        deleted_count = cursor.rowcount
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'produits';")
        return deleted_count


# ==============================================================================
# 5. AGRÉGATIONS ET STATISTIQUES
# ==============================================================================
def proc_count(
    categorie: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Procédure : compte le nombre total de produits (optionnellement par catégorie)."""
    conn = get_connection(db_path)
    try:
        if categorie:
            cursor = conn.execute(
                "SELECT COUNT(*) AS total FROM produits WHERE categorie = ?;",
                (categorie,),
            )
        else:
            cursor = conn.execute("SELECT COUNT(*) AS total FROM produits;")
        row = cursor.fetchone()
        return row["total"] if row else 0
    finally:
        conn.close()


def proc_get_stats(db_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Procédure : calcule les statistiques globales sur la base de données."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("""
            SELECT
                COUNT(*) AS total_produits,
                COALESCE(AVG(prix), 0.0) AS prix_moyen,
                COALESCE(MIN(prix), 0.0) AS prix_min,
                COALESCE(MAX(prix), 0.0) AS prix_max,
                COALESCE(AVG(note), 0.0) AS note_moyenne,
                COALESCE(SUM(disponibilite), 0) AS en_stock,
                COUNT(DISTINCT categorie) AS total_categories
            FROM produits;
        """)
        row = cursor.fetchone()
        stats = dict(row) if row else {}

        # Répartition par catégorie
        cat_cursor = conn.execute("""
            SELECT
                categorie,
                COUNT(*) AS nombre,
                COALESCE(AVG(prix), 0.0) AS prix_moyen
            FROM produits
            WHERE categorie IS NOT NULL AND categorie != ''
            GROUP BY categorie
            ORDER BY nombre DESC;
        """)
        stats["categories"] = [dict(r) for r in cat_cursor.fetchall()]
        return stats
    finally:
        conn.close()
