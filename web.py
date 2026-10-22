from flask import Flask, render_template

import config
from app.models.repository import ProduitRepository


app = Flask(__name__, template_folder=str(config.TEMPLATES_DIR))
repo = ProduitRepository(output_dir=config.OUTPUT_DIR)


@app.route("/")
def index():
    produits = repo.load_json(filename=config.DEFAULT_JSON_FILENAME)
    categories = sorted({p.categorie for p in produits if p.categorie})
    return render_template("items.html", produits=produits, categories=categories)


if __name__ == "__main__":
    app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=config.FLASK_DEBUG)
