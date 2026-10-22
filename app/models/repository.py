import csv
import json
from pathlib import Path
from typing import Iterable, List, Optional, Union

import config
from app.models.item import Produit


class ProduitRepository:
    """Stockage mémoire et export des produits scrapés."""

    FIELDNAMES = config.PRODUCT_FIELDNAMES

    def __init__(self, output_dir: Optional[Union[str, Path]] = None):
        self._output_dir = Path(output_dir) if output_dir is not None else config.OUTPUT_DIR
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._items: List[Produit] = []

    def add(self, item: Produit) -> None:
        self._items.append(item)

    def add_many(self, items: Iterable[Produit]) -> None:
        self._items.extend(items)

    def all(self) -> List[Produit]:
        return list(self._items)

    def get_all(self) -> List[Produit]:
        return list(self._items)

    def count(self) -> int:
        return len(self._items)

    def save_json(self, filename: str = config.DEFAULT_JSON_FILENAME) -> Path:
        path = self._output_dir / filename
        with path.open("w", encoding="utf-8") as file:
            json.dump([item.to_dict() for item in self._items], file, ensure_ascii=False, indent=2)
        return path

    def save_csv(self, filename: str = config.DEFAULT_CSV_FILENAME) -> Path:
        path = self._output_dir / filename
        with path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            writer.writerows(item.to_dict() for item in self._items)
        return path

    def load_json(self, filename: str = config.DEFAULT_JSON_FILENAME) -> List[Produit]:
        path = self._output_dir / filename
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as file:
            return [Produit(**data) for data in json.load(file)]
