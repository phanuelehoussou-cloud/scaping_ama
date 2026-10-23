from dataclasses import dataclass
from typing import List, Tuple

from config import AMAZON_BASE_URL


@dataclass(frozen=True)
class Categorie:
    cle: str
    nom: str
    labels: Tuple[str, ...]


CATEGORIES: List[Categorie] = [
    Categorie("1", "Livres", ("Livres", "Books")),
    Categorie("2", "Informatique", ("Informatique", "Computers")),
    Categorie("3", "High-Tech", ("High-Tech", "Electronics")),
    Categorie("4", "Mode", ("Mode", "Fashion")),
    Categorie("5", "Maison et cuisine", ("Maison et cuisine", "Home and Kitchen", "Kitchen")),
    Categorie("6", "Beauté", ("Beauté", "Beauty")),
    Categorie("7", "Sports et loisirs", ("Sports et loisirs", "Sports & Outdoors", "Sporting Goods")),
    Categorie("8", "Jeux et jouets", ("Jeux et jouets", "Toys & Games", "Toys")),
    Categorie("9", "Jeux vidéo", ("Jeux vidéo", "Video Games")),
    Categorie("10", "Jardin", ("Jardin", "Garden")),
]


ALL_CATEGORIES_KEY = "all"
