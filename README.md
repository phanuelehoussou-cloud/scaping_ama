# Amazon Scraper Pro

## Prérequis

- Python installé
- Google Chrome installé (le pilote est téléchargé automatiquement au premier lancement)

## Lancer le projet

1. Ouvrir PowerShell dans le dossier du projet :

```powershell
cd " C:\Users\AHIBO\Documents\IIT_school\PYTHON\projet_scrapping\scaping_ama "
```

2. Activer l'environnement virtuel (le dossier `.venv`) :

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Installer les dépendances (à faire une seule fois) :

```powershell
python -m pip install -r requirements.txt
```

4. Lancer le scraping :

```powershell
python main.py
```

5. Répondre aux questions du programme :
   1. la catégorie à scraper ;
   2. le nombre de produits par catégorie ;
   3. le format d'export (CSV, JSON, les deux, ou aucun) ;
   4. ouvrir ou non la galerie web.

Les fichiers sont créés dans `output/produits.json` et `output/produits.csv`.

## Configuration (`config.py`)

Tous les paramètres du scraper et de l'application sont centralisés dans le fichier `config.py` :
- **Chemins et répertoires** : dossier d'export `output/`, templates Flask, noms des fichiers CSV/JSON.
- **Selenium / Navigateur** : mode headless (`HEADLESS`), délais d'attente (`WAIT_SECONDS`), taille de fenêtre, langue.
- **User-Agents** : liste de User-Agents et User-Agent par défaut.
- **Délais et retries** : nombre de tentatives de navigation, backoff, pause de défilement lazy-loading.
- **Sélecteurs CSS Amazon** : cartes produits, pagination, images, prix, notes, bandeaux de consentement.
- **Serveur Web** : hôte (`127.0.0.1`), port (`5000`) et mode debug.

Les options peuvent être modifiées directement dans `config.py` ou surchargées via des variables d'environnement (`SCRAPER_HEADLESS`, `SCRAPER_USER_AGENT`, `SCRAPER_WAIT_SECONDS`, etc.).

## Ouvrir la galerie sans relancer le scraping

```powershell
python web.py
```

Puis ouvrir <http://127.0.0.1:5000> dans le navigateur.

## Option : voir Chrome travailler

```powershell
$env:SCRAPER_HEADLESS = "0"
python main.py
```
