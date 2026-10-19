import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.prompt import IntPrompt, Prompt

from controllers.categories import ALL_CATEGORIES_KEY, CATEGORIES, Categorie
from controllers.scraper_controller import ScraperController
from models.repository import ProduitRepository


BASE_DIR = Path(__file__).resolve().parent
console = Console()


def choose_categories() -> List[Categorie]:
    console.print("\n[bold cyan]Catégories disponibles[/bold cyan]")
    console.print("[bold]0[/bold]. Toutes les catégories")
    for category in CATEGORIES:
        console.print(f"[bold]{category.cle}[/bold]. {category.nom}")

    choice = Prompt.ask("\nChoisis une catégorie", default="0").strip().lower()
    if choice in {"0", ALL_CATEGORIES_KEY, "toutes", "all"}:
        return CATEGORIES

    selected = next((category for category in CATEGORIES if category.cle == choice), None)
    if selected:
        return [selected]
    console.print("[yellow]Choix invalide : toutes les catégories seront utilisées.[/yellow]")
    return CATEGORIES


def ask_limit(categories: List[Categorie]) -> int:
    label = (
        "Produits à scraper par catégorie"
        if len(categories) > 1
        else f"Produits à scraper dans {categories[0].nom}"
    )
    return IntPrompt.ask(label, default=10, show_default=True)


def save_results(repository: ProduitRepository) -> bool:
    choice = Prompt.ask(
        "\nFormat de sauvegarde",
        choices=["csv", "json", "both", "aucun"],
        default="both",
    )
    saved = []
    if choice in {"json", "both"}:
        saved.append(repository.save_json())
    if choice in {"csv", "both"}:
        saved.append(repository.save_csv())
    if saved:
        console.print("\n[bold green]Exports terminés[/bold green]")
        for path in saved:
            console.print(f"  • {path}")
    else:
        console.print("[yellow]Aucun fichier sauvegardé.[/yellow]")
    return choice in {"json", "both"}


def offer_web_viewer() -> None:
    choice = Prompt.ask(
        "\nOuvrir la galerie web des produits scrapés ?",
        choices=["o", "n"],
        default="o",
    )
    if choice != "o":
        return

    python_executable = sys.executable
    process = subprocess.Popen(
        [python_executable, str(BASE_DIR / "web.py")],
        cwd=BASE_DIR,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    console.print(
        f"[green]Galerie disponible sur http://127.0.0.1:5000[/green] (PID {process.pid})"
    )
    webbrowser.open("http://127.0.0.1:5000")


def main() -> None:
    console.print(Panel.fit(
        "[bold white]Amazon Scraper by PH-KING[/bold white]\n"
        "Scraping multi-catégories avec exports et galerie web",
        border_style="cyan",
    ))
    categories = choose_categories()
    limit = ask_limit(categories)
    total = len(categories) * limit
    headless = os.getenv("SCRAPER_HEADLESS", "1") != "0"

    repository = ProduitRepository(output_dir=str(BASE_DIR / "output"))
    controller = None
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    )

    try:
        controller = ScraperController(headless=headless)
        with progress:
            task = progress.add_task("Préparation...", total=total)
            for category in categories:
                progress.update(task, description=f"Scraping [cyan]{category.nom}[/cyan]")

                def on_product(_product, task_id=task):
                    progress.advance(task_id)

                try:
                    products = controller.scrape_category(category, limit, on_product)
                    repository.add_many(products)
                except Exception as exc:
                    progress.console.print(
                        f"[yellow]Catégorie {category.nom} ignorée : {exc}[/yellow]"
                    )
            progress.update(task, description="Scraping terminé")
    except Exception as exc:
        console.print(f"[bold red]Impossible de démarrer le scraper : {exc}[/bold red]")
        return
    finally:
        if controller:
            controller.close()

    console.print(f"\n[bold green]{repository.count()} produit(s) récupéré(s).[/bold green]")
    if repository.count() == 0:
        console.print("[yellow]Aucun produit trouvé. Vérifie le réseau ou un éventuel CAPTCHA Amazon.[/yellow]")
        return
    json_saved = save_results(repository)
    if json_saved:
        offer_web_viewer()
    else:
        console.print("[dim]La galerie web nécessite l'export JSON.[/dim]")


if __name__ == "__main__":
    main()
