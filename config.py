"""Configuration globale du projet Amazon Scraper Pro.

Ce module centralise l'ensemble des paramètres configurables du scraper :
- Chemins et répertoires d'export
- Paramètres de connexion Selenium & Chrome
- User-Agents
- Délais d'attente et stratégies de retry
- Sélecteurs CSS pour le DOM Amazon
- Configuration du serveur web Flask
"""

import os
from pathlib import Path
from typing import List, Tuple

# ==============================================================================
# 1. CHEMINS ET RÉPERTOIRES
# ==============================================================================
BASE_DIR: Path = Path(__file__).resolve().parent

# Dossier où sont enregistrés les fichiers exportés (CSV / JSON)
OUTPUT_DIR: Path = Path(os.getenv("SCRAPER_OUTPUT_DIR", str(BASE_DIR / "output")))

# Noms et chemins des fichiers de sortie par défaut
DEFAULT_JSON_FILENAME: str = "produits.json"
DEFAULT_CSV_FILENAME: str = "produits.csv"
DEFAULT_DB_FILENAME: str = "produits.db"
DEFAULT_JSON_PATH: Path = OUTPUT_DIR / DEFAULT_JSON_FILENAME
DEFAULT_CSV_PATH: Path = OUTPUT_DIR / DEFAULT_CSV_FILENAME
SQLITE_DB_PATH: Path = OUTPUT_DIR / DEFAULT_DB_FILENAME

# Répertoire des templates Flask pour la galerie web
TEMPLATES_DIR: Path = BASE_DIR / "app" / "views" / "templates"


# ==============================================================================
# 2. CIBLES WEB & URLS
# ==============================================================================
AMAZON_BASE_URL: str = os.getenv("AMAZON_BASE_URL", "https://www.amazon.fr/")


# ==============================================================================
# 3. CONFIGURATION SELENIUM / NAVIGATEUR
# ==============================================================================
# Mode sans tête (headless) par défaut (désactivable via $env:SCRAPER_HEADLESS = "0")
HEADLESS: bool = os.getenv("SCRAPER_HEADLESS", "1") != "0"

# Temps d'attente explicite maximal (en secondes) pour WebDriverWait
WAIT_SECONDS: int = int(os.getenv("SCRAPER_WAIT_SECONDS", "12"))

# Taille de la fenêtre virtuelle du navigateur
WINDOW_SIZE: str = os.getenv("SCRAPER_WINDOW_SIZE", "1920,1080")

# Langue par défaut transmise au navigateur
BROWSER_LANG: str = os.getenv("SCRAPER_BROWSER_LANG", "fr-FR")

# Arguments passés au pilote Chrome
CHROME_ARGUMENTS: List[str] = [
    "--disable-gpu",
    "--no-sandbox",
    f"--window-size={WINDOW_SIZE}",
    f"--lang={BROWSER_LANG}",
]


# ==============================================================================
# 4. USER-AGENTS
# ==============================================================================
USER_AGENT_CANDIDATES: Tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.170 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.62 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.88 Safari/537.36 Edg/117.0.2045.43",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
)

# User-Agent par défaut (configurable via variable d'environnement)
DEFAULT_USER_AGENT: str = os.getenv("SCRAPER_USER_AGENT", USER_AGENT_CANDIDATES[0])


# ==============================================================================
# 5. STRATÉGIE DE NAVIGATION, DÉLAIS ET RETRIES
# ==============================================================================
# Nombre de tentatives de chargement d'une URL avant d'abandonner
NAVIGATE_ATTEMPTS: int = int(os.getenv("SCRAPER_NAVIGATE_ATTEMPTS", "3"))

# Facteur multiplicateur pour le backoff exponentiel lors des réessais de navigation
# (attente de plus en plus longue après chaque échec)
NAVIGATE_BACKOFF_FACTOR: float = float(os.getenv("SCRAPER_BACKOFF_FACTOR", "1.5"))

# ------------------------------------------------------------------------------
# Pauses aléatoires (min, max) en secondes
# Un rythme variable imite un humain, une pause fixe trahit un robot.
# Si Amazon te bloque : augmente les fourchettes. Si tout passe : tu peux les baisser.
# ------------------------------------------------------------------------------

# Pause après un changement de page, pour laisser le DOM se stabiliser
PAGE_TRANSITION_DELAY_RANGE: Tuple[float, float] = (3.0, 6.0)

# Pause juste après le chargement d'une URL (driver.get), avant de lire la page
NAVIGATE_INITIAL_DELAY_RANGE: Tuple[float, float] = (1.0, 2.5)

# Pause après avoir fermé un popup de consentement / cookies
CONSENT_DISMISS_PAUSE_RANGE: Tuple[float, float] = (1.0, 2.0)

# Pause après avoir fait défiler une carte produit dans la vue
# (déclenche le lazy-loading de l'image). Exécutée pour CHAQUE carte.
IMAGE_SCROLL_PAUSE_RANGE: Tuple[float, float] = (0.6, 1.4)

# Pause entre deux défilements de page (chargement des cartes lazy-loaded)
SCROLL_PAUSE_RANGE: Tuple[float, float] = (1.5, 3.0)

# ------------------------------------------------------------------------------
# Paramètres de défilement (lazy loading infini / dynamique)
# ------------------------------------------------------------------------------
# Nombre maximal de défilements avant d'arrêter
SCROLL_MAX_ROUNDS: int = int(os.getenv("SCRAPER_SCROLL_MAX_ROUNDS", "12"))  

# Nombre de défilements consécutifs sans nouvelle carte avant de considérer la page stable
SCROLL_STABLE_THRESHOLD: int = int(os.getenv("SCRAPER_SCROLL_STABLE_THRESHOLD", "2"))

# ==============================================================================
# 6. ESTIMATION ET LIMITES DE PAGINATION
# ==============================================================================
# Valeur par défaut pour la limite de produits à scraper si non spécifiée
DEFAULT_PRODUCTS_PER_CATEGORY: int = 10

# Estimation du nombre de produits par page Amazon pour calculer max_pages
ITEMS_PER_PAGE_ESTIMATE: int = 20
PAGE_BUFFER: int = 5
MAX_PAGES_LIMIT: int = 10


# ==============================================================================
# 7. SÉLECTEURS CSS / DOM AMAZON
# ==============================================================================
# Cartes produits dans les grilles, carrousels et listes de recherche
CARD_SELECTOR: str = ".zg-grid-general-faceout, .a-carousel-card, .s-result-item, .a-cardui"

# Liens vers la page suivante
NEXT_PAGE_SELECTORS: Tuple[str, ...] = (
    ".a-pagination .a-last a",
    ".a-last a",
    ".s-pagination-next",
)

# Sélecteur pour identifier les liens produits
PRODUCT_LINK_SELECTOR: str = "a[href*='/dp/'], a[href*='/gp/product/']"

# Champ de recherche principal Amazon
SEARCH_INPUT_ID: str = "twotabsearchtextbox"

# Boutons d'acceptation ou de rejet des cookies / overlays
OVERLAY_CONSENT_SELECTORS: Tuple[str, ...] = (
    "#sp-cc-accept",
    "#sp-cc-rejectall-link",
    "input[name='accept']",
    "button[name='accept']",
    ".a-button-primary[name='accept']",
)

# Sélecteurs de l'image du produit (par ordre de priorité)
IMAGE_SELECTORS: Tuple[str, ...] = (
    ".s-image",
    ".a-dynamic-image",
    ".product-image",
    "img",
)

# Attributs explorés pour extraire l'URL de l'image
IMAGE_ATTRIBUTES: Tuple[str, ...] = ("src", "data-src", "data-old-hires")

# Sélecteurs du titre du produit
TITLE_SELECTORS: Tuple[str, ...] = (
    ".p13n-sc-truncate-desktop-type2",
    ".p13n-sc-truncate",
    "[class*='p13n-sc-css-line-clamp']",
    ".a-size-medium",
    ".a-size-base-plus",
)

# Sélecteurs du lien cliquable du produit
LINK_SELECTORS: Tuple[str, ...] = (
    ".a-link-normal.aok-block",
    ".a-link-normal",
)

# Sélecteurs du prix
PRICE_SELECTORS: Tuple[str, ...] = (
    ".a-price-whole .a-price-fraction",
    ".p13n-sc-price",
    ".a-price",
    ".a-price-whole",
    ".a-color-price",
)

# Sélecteurs de la note / notation étoiles
RATING_SELECTORS: Tuple[str, ...] = (
    ".a-icon-alt",
    ".a-icon-star",
)

# Mots-clés déclenchant la détection d'indisponibilité
UNAVAILABLE_MARKERS: Tuple[str, ...] = (
    "indisponible",
    "rupture de stock",
    "épuisé",
)

# Classes d'éléments à ignorer (ex: cartes promotionnelles ou sponsorisées non pertinentes)
IGNORED_CARD_CLASSES: Tuple[str, ...] = ("brand-story",)


# ==============================================================================
# 8. STRUCTURE DES DONNÉES ET EXPORTS
# ==============================================================================
PRODUCT_FIELDNAMES: List[str] = [
    "nom",
    "prix",
    "note",
    "disponibilite",
    "url",
    "image",
    "categorie",
]


# ==============================================================================
# 9. SERVEUR WEB FLASK (GALERIE)
# ==============================================================================
WEB_HOST: str = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT: int = int(os.getenv("WEB_PORT", "5000"))
WEB_URL: str = f"http://{WEB_HOST}:{WEB_PORT}"
FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "0") == "1"
