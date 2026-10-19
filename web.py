import os
from pathlib import Path

from flask import Flask, render_template

from models.repository import ProduitRepository


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(BASE_DIR / "views" / "templates"))
repo = ProduitRepository(output_dir=str(BASE_DIR / "output"))


@app.route("/")
def index():
    produits = repo.load_json()
    categories = sorted({p.categorie for p in produits if p.categorie})
    return render_template("items.html", produits=produits, categories=categories)


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)
