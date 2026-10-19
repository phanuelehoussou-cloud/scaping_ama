from dataclasses import dataclass
from typing import List


AMAZON_BASE_URL = "https://www.amazon.fr/"


@dataclass(frozen=True)
class Categorie:
    cle: str
    nom: str
    slug: str

    @property
    def url(self) -> str:
        return f"{AMAZON_BASE_URL}gp/bestsellers/{self.slug}"


CATEGORIES: List[Categorie] = [
    Categorie("1", "Livres", "books"),
    Categorie("2", "Informatique", "computers"),
    Categorie("3", "High-Tech", "electronics"),
    Categorie("4", "Mode", "fashion"),
    Categorie("5", "Maison et cuisine", "kitchen"),
    Categorie("6", "Beauté", "beauty"),
    Categorie("7", "Sports et loisirs", "sporting-goods"),
    Categorie("8", "Jeux et jouets", "toys"),
    Categorie("9", "Jeux vidéo", "videogames"),
    Categorie("10", "Jardin", "garden"),
]


ALL_CATEGORIES_KEY = "all"
