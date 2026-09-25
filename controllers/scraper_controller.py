import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from models.item import Produit
from models.repository import ProduitRepository
from views.console_view import ConsoleView


class ScraperController:
    """
    Orchestre le scraping d'une page de résultats de recherche Amazon.

    ATTENTION : Amazon change fréquemment sa structure HTML et bloque
    activement les bots (CAPTCHA, blocage IP). Les sélecteurs CSS ci-dessous
    sont un point de départ : ouvre la page dans ton navigateur, clic droit
    -> Inspecter sur un produit, et ajuste les sélecteurs si besoin.
    """

    def __init__(self, base_url: str, headless: bool = True):
        self.base_url = base_url
        self.repository = ProduitRepository()
        self.view = ConsoleView()
        self.driver = self._init_driver(headless)

    def _init_driver(self, headless: bool):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def _wait_for(self, by, selector, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_all_elements_located((by, selector))
        )

    def _parse_price(self, text: str) -> float:
        """Transforme '19,99€' ou '$19.99' en 19.99 (float)."""
        cleaned = re.sub(r"[^\d,.]", "", text)
        cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _parse_rating(self, text: str) -> float:
        """Transforme '4,5 sur 5 étoiles' en 4.5 (float)."""
        match = re.search(r"(\d[.,]?\d?)", text)
        if match:
            return float(match.group(1).replace(",", "."))
        return 0.0

    def _scrape_page(self):
        """
        Sélecteurs validés le 24/09/2026 sur la page Bestsellers Amazon.fr
        via l'inspecteur du navigateur (structure .a-carousel-card).
        """
        CARD_SELECTOR = ".a-carousel-card"
        cards = self._wait_for(By.CSS_SELECTOR, CARD_SELECTOR)
        items = []
        for card in cards:
            # Certaines cartes du carousel sont des publicités de marque
            # ("Brand Story"), pas des produits : on les ignore.
            card_class = card.get_attribute("class") or ""
            if "brand-story" in card_class:
                continue
            try:
                # Titre : dans l'attribut "title" du div dédié (cartes normales),
                # ou dans l'attribut "title" d'un lien (cartes sponsorisées)
                try:
                    nom = card.find_element(
                        By.CSS_SELECTOR, "div.p13n-sc-truncate-desktop-type2"
                    ).get_attribute("title")
                except NoSuchElementException:
                    try:
                        nom = card.find_element(By.CSS_SELECTOR, "a[title]").get_attribute("title")
                    except NoSuchElementException:
                        nom = ""

                # Lien : href relatif -> on complète avec le domaine
                try:
                    href = card.find_element(
                        By.CSS_SELECTOR, "a.a-link-normal.aok-block"
                    ).get_attribute("href")
                    url = href  # Selenium retourne déjà l'URL absolue résolue par le navigateur
                except NoSuchElementException:
                    url = ""

                # Prix : structure "normale" d'abord, structure sponsorisée en secours
                try:
                    prix_text = card.find_element(By.CSS_SELECTOR, "span.p13n-sc-price").text
                    prix = self._parse_price(prix_text)
                except NoSuchElementException:
                    try:
                        prix_text = card.find_element(By.CSS_SELECTOR, "span.a-price .a-offscreen").text
                        prix = self._parse_price(prix_text)
                    except NoSuchElementException:
                        prix = 0.0

                # Note : texte explicite d'abord, sinon on lit la classe CSS
                # de l'étoile (ex. "a-star-4-5" -> 4.5) sur les cartes sponsorisées
                try:
                    note_text = card.find_element(By.CSS_SELECTOR, "span.a-icon-alt").get_attribute("innerText")
                    note = self._parse_rating(note_text)
                except NoSuchElementException:
                    try:
                        classes = card.find_element(By.CSS_SELECTOR, "i.a-icon-star").get_attribute("class")
                        # ex. "a-icon a-icon-star a-star-4-5" -> on extrait "4-5" -> 4.5
                        match = re.search(r"a-star-(\d)-(\d)", classes)
                        note = float(f"{match.group(1)}.{match.group(2)}") if match else 0.0
                    except NoSuchElementException:
                        note = 0.0

                disponibilite = True  # les produits bestsellers sont presque toujours en stock

                if nom and url:
                    items.append(Produit(nom=nom.strip(), prix=prix, note=note,
                                          disponibilite=disponibilite, url=url))
            except NoSuchElementException:
                continue
        return items

    def run(self):
        self.view.show_start(self.base_url)
        try:
            self.driver.get(self.base_url)
            time.sleep(2)  # laisser la page se stabiliser

            items = self._scrape_page()
            for item in items:
                self.repository.add(item)
            self.view.show_progress(1, len(items))

            self.view.show_results(self.repository.all())
            json_path = self.repository.save_json()
            csv_path = self.repository.save_csv()
            self.view.show_saved(json_path, csv_path)

        except TimeoutException:
            self.view.show_error(
                "Timeout : la page n'a pas chargé, ou Amazon a affiché un CAPTCHA / bloqué la requête."
            )
        finally:
            self.driver.quit()