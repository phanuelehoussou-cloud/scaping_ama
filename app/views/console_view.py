from typing import List
from app.models.item import Produit


class ConsoleView:
    def show_start(self, url: str) -> None:
        print(f"[+] Démarrage du scraping sur : {url}")

    def show_progress(self, page: int, found: int) -> None:
        print(f"    Page {page} -> {found} produits trouvés")

    def show_results(self, items: List[Produit]) -> None:
        print(f"\n[+] {len(items)} produits récupérés :\n")
        for i, item in enumerate(items, start=1):
            print(f"{i}. {item.nom} — {item.prix}€ — note {item.note}/5"
                f" — {'en stock' if item.disponibilite else 'rupture'}")

    def show_saved(self, json_path, csv_path) -> None:
        print(f"\n[+] Résultats enregistrés :")
        print(f"    JSON -> {json_path}")
        print(f"    CSV  -> {csv_path}")

    def show_error(self, message: str) -> None:
        print(f"[!] Erreur : {message}")