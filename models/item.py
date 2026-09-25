from dataclasses import dataclass, asdict

@dataclass
class Produit:
    nom: str
    prix: float
    note: float
    disponibilite: bool
    url: str

    def to_dict(self) -> dict:
        return asdict(self)