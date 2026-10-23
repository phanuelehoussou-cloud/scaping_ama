from pathlib import Path
from typing import Callable, Iterable, List, Optional, Union

import config
from app.models.categories import CATEGORIES, Categorie
from app.models.item import Produit
from app.models.repository import ProduitRepository
from app.scrapers.amazon_scraper import AmazonScraper, ProgressCallback


class ScraperController:
    """Contrôleur orchestrant la logique de scraping et la persistance des données.

    Indépendant de toute interface (Flask ou CLI console).
    """

    def __init__(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        headless: Optional[bool] = None,
    ):
        self.output_dir = Path(output_dir) if output_dir else config.OUTPUT_DIR
        self.headless = config.HEADLESS if headless is None else headless
        self.repository = ProduitRepository(output_dir=self.output_dir)

    def scrape_categories(
        self,
        categories: Iterable[Categorie],
        limit_per_category: int = config.DEFAULT_PRODUCTS_PER_CATEGORY,
        on_product: Optional[ProgressCallback] = None,
        on_category_start: Optional[Callable[[Categorie], None]] = None,
        on_category_error: Optional[Callable[[Categorie, Exception], None]] = None,
    ) -> List[Produit]:
        """Scrape les produits pour chaque catégorie fournie et les stocke dans le repository."""
        scraped_products: List[Produit] = []
        scraper = AmazonScraper(headless=self.headless)
        try:
            for category in categories:
                if on_category_start:
                    on_category_start(category)
                try:
                    products = scraper.scrape_category(
                        category=category,
                        limit=limit_per_category,
                        on_product=on_product,
                    )
                    self.repository.add_many(products)
                    scraped_products.extend(products)
                except Exception as exc:
                    if on_category_error:
                        on_category_error(category, exc)
                    else:
                        raise
        finally:
            scraper.close()

        return scraped_products

    def scrape_category(
        self,
        category: Categorie,
        limit: int = config.DEFAULT_PRODUCTS_PER_CATEGORY,
        on_product: Optional[ProgressCallback] = None,
    ) -> List[Produit]:
        """Raccourci pour scraper une seule catégorie."""
        return self.scrape_categories(
            categories=[category],
            limit_per_category=limit,
            on_product=on_product,
        )

    def save_results(
        self,
        save_json: bool = True,
        save_csv: bool = True,
        json_filename: str = config.DEFAULT_JSON_FILENAME,
        csv_filename: str = config.DEFAULT_CSV_FILENAME,
    ) -> dict:
        """Exporte les données accumulées dans le repository au format JSON et/ou CSV."""
        paths = {}
        if save_json:
            paths["json"] = self.repository.save_json(filename=json_filename)
        if save_csv:
            paths["csv"] = self.repository.save_csv(filename=csv_filename)
        return paths

    def get_all_products(self) -> List[Produit]:
        """Retourne la liste des produits actuellement en mémoire."""
        return self.repository.all()

    @staticmethod
    def get_categories() -> List[Categorie]:
        """Retourne la liste des catégories disponibles."""
        return CATEGORIES
