import csv
import json
from pathlib import Path
from typing import List
from models.item import Produit


class ProduitRepository:
    def __init__(self, output_dir: str = "output"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._items = []

    def add(self, item: Produit) -> None:
        self._items.append(item)
        

    def all(self) -> List[Produit]:
        return self._items

    def count(self) -> int:
        return len(self._items)
    
    def save_json(self, filename: str = "produits.json") -> Path:
        path = self._output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump([item.to_dict() for item in self._items], f, ensure_ascii=False, indent=2)
        return path

    def save_csv(self, filename: str = "produits.csv") -> Path:
        path = self._output_dir / filename
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["nom", "prix", "note", "disponibilite", "url", "image"])
            writer.writeheader()
            for item in self._items:
                writer.writerow(item.to_dict())
        return path
    
    def load_json(self, filename: str = "produits.json") -> List[Produit]:
        path = self._output_dir / filename
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            return [Produit(**data) for data in json.load(f)]