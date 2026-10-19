import os

from flask import Flask, render_template

from models.repository import ProduitRepository


app = Flask(__name__, template_folder="views/templates")
repo = ProduitRepository()


@app.route("/")
def index():
    produits = repo.load_json()
    return render_template("items.html", produits=produits)


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)
