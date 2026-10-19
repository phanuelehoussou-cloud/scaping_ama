from dataclasses import asdict, dataclass


@dataclass
class Produit:
    nom: str
    prix: float
    note: float
    disponibilite: bool
    url: str
    image: str = ""
    categorie: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
