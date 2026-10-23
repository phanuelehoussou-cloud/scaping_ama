import subprocess
import sys
import webbrowser
from typing import List, Optional

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
from rich.prompt import IntPrompt

import config
from app.controllers.scraper_controller import ScraperController
from app.models.categories import CATEGORIES, Categorie
from app.models.repository import ProduitRepository


console = Console()


def ask_menu_number(prompt: str, minimum: int, maximum: int, default: Optional[int] = None) -> int:
    """Demande un entier dans une plage et recommence tant que la saisie est invalide."""
    while True:
        # Aucun défaut : une saisie vide ne doit pas être acceptée.
        value = IntPrompt.ask(prompt)
        if minimum <= value <= maximum:
            return value
        console.print(f"[yellow]Choisis un nombre entre {minimum} et {maximum}.[/yellow]")


def ask_positive_number(prompt: str, default: int = config.DEFAULT_PRODUCTS_PER_CATEGORY) -> int:
    """Demande un nombre strictement positif."""
    while True:
        value = IntPrompt.ask(prompt, default=default)
        if value > 0:
            return value
        console.print("[yellow]Le nombre doit être supérieur à zéro.[/yellow]")


def choose_categories() -> List[Categorie]:
    console.print("\n[bold cyan]Catégories disponibles[/bold cyan]")
    console.print("[bold]0[/bold]. Toutes les catégories")
    for category in CATEGORIES:
        console.print(f"[bold]{category.cle}[/bold]. {category.nom}")

    choice = ask_menu_number("Choisis une catégorie", 0, len(CATEGORIES), default=0)
    if choice == 0:
        return CATEGORIES
    return [CATEGORIES[choice - 1]]


def ask_limit(categories: List[Categorie]) -> int:
    label = (
        "Produits à scraper par catégorie"
        if len(categories) > 1
        else f"Produits à scraper dans {categories[0].nom}"
    )
    return ask_positive_number(label, default=config.DEFAULT_PRODUCTS_PER_CATEGORY)


def save_results(repository: ProduitRepository) -> bool:
    console.print("\n[bold cyan]Format de sauvegarde[/bold cyan]")
    console.print("[bold]1[/bold]. CSV uniquement")
    console.print("[bold]2[/bold]. JSON uniquement")
    console.print("[bold]3[/bold]. CSV et JSON")
    console.print("[bold]4[/bold]. Ne pas sauvegarder")
    choice = ask_menu_number("Choisis une option", 1, 4, default=3)

    saved = []
    if choice in {2, 3}:
        saved.append(repository.save_json())
    if choice in {1, 3}:
        saved.append(repository.save_csv())
    if saved:
        console.print("\n[bold green]Exports terminés[/bold green]")
        for path in saved:
            console.print(f"  • {path}")
    else:
        console.print("[yellow]Aucun fichier sauvegardé.[/yellow]")
    return choice in {2, 3}


def offer_web_viewer(
    existing_process: Optional[subprocess.Popen] = None,
    json_available: bool = True,
):
    console.print("\n[bold cyan]Galerie web[/bold cyan]")
    console.print("[bold]1[/bold]. Ouvrir la galerie")
    console.print("[bold]2[/bold]. Ne pas ouvrir")
    choice = ask_menu_number("Choisis une option", 1, 2, default=1)
    if choice != 1:
        return existing_process
    if not json_available:
        console.print("[yellow]La galerie nécessite une sauvegarde JSON.[/yellow]")
        return existing_process

    if existing_process and existing_process.poll() is None:
        console.print(f"[green]Galerie déjà ouverte sur {config.WEB_URL}[/green]")
        webbrowser.open(config.WEB_URL)
        return existing_process

    process = subprocess.Popen(
        [sys.executable, str(config.BASE_DIR / "web.py")],
        cwd=config.BASE_DIR,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    console.print(
        f"[green]Galerie disponible sur {config.WEB_URL}[/green] (PID {process.pid})"
    )
    webbrowser.open(config.WEB_URL)
    return process


def run_scraping_session(web_process=None):
    categories = choose_categories()
    limit = ask_limit(categories)
    total = len(categories) * limit
    controller = ScraperController(headless=config.HEADLESS)
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    )

    try:
        with progress:
            task = progress.add_task("Préparation...", total=total)

            def on_start(cat: Categorie):
                progress.update(task, description=f"Scraping [cyan]{cat.nom}[/cyan]")

            def on_product(_product):
                progress.advance(task)

            def on_error(cat: Categorie, exc: Exception):
                progress.console.print(
                    f"[yellow]Catégorie {cat.nom} ignorée : {exc}[/yellow]"
                )

            controller.scrape_categories(
                categories=categories,
                limit_per_category=limit,
                on_product=on_product,
                on_category_start=on_start,
                on_category_error=on_error,
            )
            progress.update(task, completed=total, description="Scraping terminé")
    except Exception as exc:
        console.print(f"[bold red]Impossible de démarrer le scraper : {exc}[/bold red]")
        return web_process

    product_count = controller.repository.count()
    console.print(f"\n[bold green]{product_count} produit(s) récupéré(s).[/bold green]")
    if product_count == 0:
        console.print("[yellow]Aucun produit trouvé. Vérifie le réseau ou un éventuel CAPTCHA Amazon.[/yellow]")
        return web_process

    json_available = save_results(controller.repository)
    return offer_web_viewer(web_process, json_available)


def main() -> None:
    console.print(Panel.fit(
        "[bold white]Amazon Scraper Pro[/bold white]\n"
        "Scraping multi-catégories avec exports et galerie web",
        border_style="cyan",
    ))
    web_process = None
    while True:
        web_process = run_scraping_session(web_process)
        console.print("\n[bold cyan]Action suivante[/bold cyan]")
        console.print("[bold]1[/bold]. Continuer le scraping")
        console.print("[bold]2[/bold]. Sortir du programme")
        choice = ask_menu_number("Choisis une option", 1, 2, default=2)
        if choice == 2:
            console.print("[bold cyan]Programme terminé. À bientôt.[/bold cyan]")
            break
        console.print("\n[bold cyan]Nouvelle session de scraping[/bold cyan]")


if __name__ == "__main__":
    main()
