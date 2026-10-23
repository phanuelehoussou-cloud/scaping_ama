from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional


@dataclass
class Produit:
    nom: str
    prix: float
    note: float
    disponibilite: bool
    url: str
    image: str = ""
    categorie: str = ""
    id: Optional[int] = None
    date_scrape: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Produit":
        """Instancie un Produit à partir d'une ligne SQLite (sqlite3.Row ou dict)."""
        keys = row.keys() if hasattr(row, "keys") else row
        return cls(
            id=row["id"] if "id" in keys else None,
            nom=row["nom"],
            prix=float(row["prix"]),
            note=float(row["note"]),
            disponibilite=bool(row["disponibilite"]),
            url=row["url"],
            image=row["image"] or "",
            categorie=row["categorie"] or "",
            date_scrape=row["date_scrape"] if "date_scrape" in keys else None,
        )
