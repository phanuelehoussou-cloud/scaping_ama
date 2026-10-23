import os
import threading
from pathlib import Path
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

import config
from app.controllers.scraper_controller import ScraperController
from app.models.categories import CATEGORIES, Categorie
from app.models.repository import ProduitRepository


app = Flask(__name__, template_folder=str(config.TEMPLATES_DIR))
app.secret_key = os.getenv("SECRET_KEY", "amazon-scraper-secret-key-2026")

repo = ProduitRepository(output_dir=config.OUTPUT_DIR)

# État de la tâche de scraping en arrière-plan
scraper_state = {
    "is_running": False,
    "progress_message": "",
    "error": None,
    "last_count": 0,
    "target_name": "",
}
state_lock = threading.Lock()


def background_scrape_task(target_categories, limit, cat_name):
    """Exécute le scraping Selenium en arrière-plan dans un thread indépendant."""
    global scraper_state
    try:
        controller = ScraperController(headless=config.HEADLESS)
        # On charge les produits existants pour cumuler
        existing = repo.load_json(filename=config.DEFAULT_JSON_FILENAME)
        controller.repository.add_many(existing)

        def on_cat_start(cat: Categorie):
            with state_lock:
                scraper_state["progress_message"] = f"Scraping de la catégorie « {cat.nom} » en cours..."

        def on_prod(_prod):
            with state_lock:
                current_total = controller.repository.count()
                scraper_state["progress_message"] = (
                    f"Extraction en cours ({current_total} produit(s) cumulé(s))..."
                )

        new_products = controller.scrape_categories(
            categories=target_categories,
            limit_per_category=limit,
            on_product=on_prod,
            on_category_start=on_cat_start,
        )
        controller.save_results(save_json=True, save_csv=True)

        with state_lock:
            scraper_state["is_running"] = False
            scraper_state["error"] = None
            scraper_state["last_count"] = len(new_products)
            scraper_state["progress_message"] = (
                f"Scraping terminé : {len(new_products)} nouveau(x) produit(s) ajouté(s) !"
            )
    except Exception as exc:
        with state_lock:
            scraper_state["is_running"] = False
            scraper_state["error"] = str(exc)
            scraper_state["progress_message"] = f"Erreur : {exc}"


@app.route("/")
def index():
    """Affiche la galerie des produits et l'état du scraper."""
    produits = repo.load_json(filename=config.DEFAULT_JSON_FILENAME)
    categories_presentes = sorted({p.categorie for p in produits if p.categorie})
    return render_template(
        "items.html",
        produits=produits,
        categories=categories_presentes,
        all_categories=CATEGORIES,
        total_count=len(produits),
        scraper_state=scraper_state,
    )


@app.route("/scrape", methods=["POST"])
def scrape():
    """Lance le scraping en tâche de fond pour ne pas bloquer l'interface."""
    with state_lock:
        if scraper_state["is_running"]:
            flash("Un scraping est déjà en cours d'exécution. Veuillez patienter.", "warning")
            return redirect(url_for("index"))

    category_id = request.form.get("category_id", "1")
    try:
        limit = int(request.form.get("limit", config.DEFAULT_PRODUCTS_PER_CATEGORY))
        limit = max(1, min(limit, 50))
    except ValueError:
        limit = config.DEFAULT_PRODUCTS_PER_CATEGORY

    if category_id == "0":
        target_categories = CATEGORIES
        cat_name = "Toutes les catégories"
    else:
        target_categories = [c for c in CATEGORIES if c.cle == category_id]
        if not target_categories:
            flash("Catégorie demandée introuvable.", "danger")
            return redirect(url_for("index"))
        cat_name = target_categories[0].nom

    with state_lock:
        scraper_state["is_running"] = True
        scraper_state["progress_message"] = f"Démarrage du scraper pour « {cat_name} »..."
        scraper_state["error"] = None
        scraper_state["last_count"] = 0
        scraper_state["target_name"] = cat_name

    thread = threading.Thread(
        target=background_scrape_task,
        args=(target_categories, limit, cat_name),
        daemon=True,
    )
    thread.start()

    flash(
        f"Scraping lancé en tâche de fond pour « {cat_name} » ({limit} produit(s) max).",
        "info",
    )
    return redirect(url_for("index"))


@app.route("/status")
def status():
    """Retourne l'état actuel de la tâche de fond au format JSON."""
    with state_lock:
        return jsonify(scraper_state)


@app.route("/clear", methods=["POST"])
def clear():
    """Réinitialise les fichiers de données si aucun scraping n'est actif."""
    with state_lock:
        if scraper_state["is_running"]:
            flash("Impossible de réinitialiser pendant qu'un scraping est en cours.", "warning")
            return redirect(url_for("index"))

    try:
        json_path = config.OUTPUT_DIR / config.DEFAULT_JSON_FILENAME
        csv_path = config.OUTPUT_DIR / config.DEFAULT_CSV_FILENAME
        if json_path.exists():
            json_path.unlink()
        if csv_path.exists():
            csv_path.unlink()
        flash("La base de produits a été réinitialisée.", "info")
    except Exception as exc:
        flash(f"Erreur lors de la réinitialisation : {exc}", "danger")

    return redirect(url_for("index"))


@app.route("/download/<file_type>")
def download(file_type):
    """Télécharge le fichier JSON ou CSV généré."""
    filename = (
        config.DEFAULT_JSON_FILENAME
        if file_type == "json"
        else config.DEFAULT_CSV_FILENAME
    )
    file_path = config.OUTPUT_DIR / filename
    if not file_path.exists():
        flash(f"Le fichier {filename} n'est pas encore généré.", "warning")
        return redirect(url_for("index"))

    return send_from_directory(
        directory=str(config.OUTPUT_DIR),
        path=filename,
        as_attachment=True,
    )


if __name__ == "__main__":
    app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=config.FLASK_DEBUG)
