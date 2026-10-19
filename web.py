from flask import Flask, render_template
from models.repository import Repository   # adapte le nom de la classe

app = Flask(__name__, template_folder="views/templates")
repo = Repository()

@app.route("/")
def index():
    items = repo.get_all()   # adapte : la méthode qui retourne tes Item
    return render_template("items.html", items=items)

if __name__ == "__main__":
    app.run(debug=True)