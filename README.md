# Amazon Scraper Pro

Application Python de scraping Amazon par catégories, basée sur `https://www.amazon.fr/`, avec progression dans le terminal, exports CSV/JSON et galerie web.

## Fonctionnalités

- choix interactif d'une catégorie ou de toutes les catégories proposées ;
- nombre de produits configurable par catégorie ;
- extraction du nom, prix, note, disponibilité, image, URL et catégorie ;
- barre de progression riche dans le terminal ;
- export CSV, JSON, ou les deux ;
- galerie Flask responsive avec filtres par catégorie ;
- réutilisation du même navigateur Selenium pour toutes les catégories.
- sélecteurs CSS orientés classes Amazon (`a-cardui`, `a-carousel-card`, `s-result-item`, etc.).

## Installation

Le dossier `.env` du projet est l'environnement virtuel Python. Sous PowerShell :

```powershell
cd "C:\Users\ELIE EHOUSSOU\Documents\PERSONNEL\scaping_ama"
.\.env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Chrome doit être installé. `webdriver-manager` téléchargera automatiquement le pilote compatible au premier lancement.

## Lancer le scraping

```powershell
.\.env\Scripts\python.exe main.py
```

Le programme demande successivement :

1. la catégorie à scraper ;
2. le nombre de produits par catégorie ;
3. le format d'export (`csv`, `json`, `both` ou `aucun`) ;
4. s'il faut ouvrir la galerie web.

Les fichiers sont générés dans `output/produits.json` et `output/produits.csv`.

## Lancer uniquement la galerie web

```powershell
.\.env\Scripts\python.exe web.py
```

Puis ouvrir <http://127.0.0.1:5000>.

## Configuration

Le dossier `.env` est volontairement utilisé comme environnement virtuel Python. Les options d'exécution peuvent être configurées par variables d'environnement :

```powershell
$env:SCRAPER_HEADLESS = "1"  # 0 pour afficher Chrome
$env:FLASK_DEBUG = "0"       # 1 uniquement en développement
```

## Sessions multiples

Après chaque scraping, le programme demande si l'utilisateur veut `continuer` ou `sortir`. Le choix `continuer` réaffiche le menu des catégories pour démarrer une nouvelle session. Le serveur web déjà ouvert est réutilisé au lieu d'être lancé une seconde fois.

## Notes importantes

Amazon peut afficher un CAPTCHA, modifier ses sélecteurs HTML ou limiter les requêtes automatisées. Le scraper traite alors la catégorie concernée et continue avec les suivantes. Utilisez ce projet dans le respect des conditions d'utilisation et de la réglementation applicables.
