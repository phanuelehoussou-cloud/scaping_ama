import random
import re
import time
from typing import Callable, List, Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

import config
from app.models.categories import Categorie
from app.models.item import Produit


ProgressCallback = Callable[[Produit], None]

# Sélecteurs de SECOURS, essayés APRÈS ceux de config.py (qui gardent la priorité).
# Utiles sur les pages de résultats de recherche (/s?k=...), où le titre est dans <h2>.
_EXTRA_TITLE_SELECTORS = ("h2 span", "h2", "img[alt]")
_EXTRA_LINK_SELECTORS = ("h2 a", "a[href*='/dp/']", "a[href*='/gp/product/']")
_EXTRA_PRICE_SELECTORS = (".a-price .a-offscreen", "[class*='price']")


class AmazonScraper:
    """Scraper Amazon multi-pages avec défilement et déduplication."""

    CARD_SELECTOR = config.CARD_SELECTOR
    NEXT_PAGE_SELECTORS = config.NEXT_PAGE_SELECTORS

    def __init__(
        self,
        headless: Optional[bool] = None,
        wait_seconds: Optional[int] = None,
        base_url: Optional[str] = None,
    ):
        self.headless = config.HEADLESS if headless is None else headless
        self.wait_seconds = config.WAIT_SECONDS if wait_seconds is None else wait_seconds
        self.base_url = base_url or config.AMAZON_BASE_URL
        self.driver = self._init_driver(self.headless)

    @staticmethod
    def _pause(delay_range) -> None:
        """Attend une durée aléatoire dans la fourchette (min, max), en secondes."""
        time.sleep(random.uniform(*delay_range))

    def _init_driver(self, headless: bool):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        for arg in config.CHROME_ARGUMENTS:
            options.add_argument(arg)
        options.add_argument(f"user-agent={config.DEFAULT_USER_AGENT}")

        # Réduit les traces visibles de Selenium
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )

    def _is_blocked(self) -> bool:
        """Détecte si Amazon affiche une page de blocage / CAPTCHA."""
        page = self.driver.page_source
        src = page.lower()
        return (
            "validatecaptcha" in src
            or "continuer les achats" in src
            or "robot" in self.driver.title.lower()
            or len(page) < 5_000
        )

    def _bypass_soft_block(self) -> bool:
        """Tente de passer la page de validation douce (bouton 'Continuer')."""
        try:
            buttons = self.driver.find_elements(By.CSS_SELECTOR, ".a-button-text, button[type='submit']")
            for btn in buttons:
                text = (btn.text or "").lower()
                if "continuer" in text or "achats" in text or "continue" in text:
                    self.driver.execute_script("arguments[0].click();", btn)
                    self._pause(config.PAGE_TRANSITION_DELAY_RANGE)
                    return not self._is_blocked()
        except Exception:
            pass
        return False

    def _navigate(self, url: str, attempts: int = config.NAVIGATE_ATTEMPTS) -> bool:
        """Navigue avec quelques tentatives et gestion du blocage Amazon."""
        for attempt in range(attempts):
            try:
                self.driver.get(url)
                self._pause(config.NAVIGATE_INITIAL_DELAY_RANGE)
                if self._is_blocked():
                    if not self._bypass_soft_block():
                        time.sleep(config.NAVIGATE_BACKOFF_FACTOR * (attempt + 2) * 3)
                        self.driver.get(url)
                        self._pause(config.NAVIGATE_INITIAL_DELAY_RANGE)
                        if self._is_blocked():
                            print("[INFO] Page bloquée par Amazon (CAPTCHA).")
                            return False
                return True
            except WebDriverException:
                if attempt == attempts - 1:
                    return False
                time.sleep(config.NAVIGATE_BACKOFF_FACTOR * (attempt + 1))
        return False

    @staticmethod
    def _link_text(link) -> str:
        """Texte + aria-label d'un lien, normalisé pour la comparaison."""
        return " ".join(
            ((link.text or "") + " " + (link.get_attribute("aria-label") or "")).split()
        ).casefold()

    def _open_category_from_home(self, category: Categorie) -> bool:
        """Ouvre une catégorie via les liens de l'accueil, sinon via la recherche."""
        if not self._navigate(self.base_url):
            return False
        self._dismiss_overlays()

        links = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
        category_link = None
        best_sellers_link = None
        labels = tuple(label.casefold() for label in category.labels)

        for link in links:
            text = self._link_text(link)
            href = (link.get_attribute("href") or "").casefold()
            if any(label in text for label in labels):
                category_link = link
                break
            if "gp/bestsellers" in href and "best" in text:
                best_sellers_link = link

        try:
            if category_link is not None:
                self.driver.execute_script("arguments[0].click();", category_link)
            elif best_sellers_link is not None:
                self.driver.execute_script("arguments[0].click();", best_sellers_link)
                WebDriverWait(self.driver, self.wait_seconds).until(
                    lambda driver: any(
                        any(label in self._link_text(link) for label in labels)
                        for link in driver.find_elements(By.CSS_SELECTOR, "a[href]")
                    )
                )
                for link in self.driver.find_elements(By.CSS_SELECTOR, "a[href]"):
                    if any(label in self._link_text(link) for label in labels):
                        self.driver.execute_script("arguments[0].click();", link)
                        break
            else:
                # Dernier recours : recherche de la catégorie dans la barre de recherche
                search_box = WebDriverWait(self.driver, self.wait_seconds).until(
                    lambda driver: driver.find_element(By.ID, config.SEARCH_INPUT_ID)
                )
                search_box.clear()
                search_box.send_keys(category.nom)
                search_box.send_keys(Keys.ENTER)
            self._dismiss_overlays()
            return True
        except (NoSuchElementException, TimeoutException, WebDriverException):
            return False

    @staticmethod
    def parse_price(text: str) -> float:
        """Extrait le premier nombre du texte (gère espaces de milliers et virgule)."""
        match = re.search(r"\d[\d\s\u00a0]*(?:[.,]\d{1,2}(?!\d))?", text)
        if not match:
            return 0.0
        number = re.sub(r"[\s\u00a0]", "", match.group()).replace(",", ".")
        try:
            return float(number)
        except ValueError:
            return 0.0

    @staticmethod
    def parse_rating(text: str) -> float:
        star_class = re.search(r"a-star-(\d)-(\d)", text)
        if star_class:
            return float(f"{star_class.group(1)}.{star_class.group(2)}")
        rating = re.search(r"(\d[.,]?\d?)", text)
        return float(rating.group(1).replace(",", ".")) if rating else 0.0

    @staticmethod
    def _find_first(container, selectors):
        for selector in selectors:
            try:
                return container.find_element(By.CSS_SELECTOR, selector)
            except NoSuchElementException:
                continue
        return None

    @staticmethod
    def _read_text(element) -> str:
        """Lit le texte, même caché (textContent), avec repli sur innerText puis .text."""
        return (
            element.get_attribute("textContent")
            or element.get_attribute("innerText")
            or element.text
            or ""
        ).strip()

    def _find_product_link(self, card):
        """Premier lien de la carte dont l'URL pointe vraiment vers un produit (/dp/ ou /gp/product/)."""
        for selector in tuple(config.LINK_SELECTORS) + _EXTRA_LINK_SELECTORS:
            for element in card.find_elements(By.CSS_SELECTOR, selector):
                href = element.get_attribute("href") or ""
                if "/dp/" in href or "/gp/product/" in href:
                    return element
        return None

    def _find_all_cards(self):
        return self.driver.find_elements(By.CSS_SELECTOR, self.CARD_SELECTOR)

    def _dismiss_overlays(self) -> None:
        """Ferme les écrans de consentement qui peuvent masquer la page."""
        for selector in config.OVERLAY_CONSENT_SELECTORS:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if buttons and buttons[0].is_displayed():
                    self.driver.execute_script("arguments[0].click();", buttons[0])
                    self._pause(config.CONSENT_DISMISS_PAUSE_RANGE)
                    return
            except Exception:
                continue

    def _get_image(self, card) -> str:
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", card
        )
        self._pause(config.IMAGE_SCROLL_PAUSE_RANGE)
        image = self._find_first(card, config.IMAGE_SELECTORS)
        if image is None:
            return ""
        for attribute in config.IMAGE_ATTRIBUTES:
            value = image.get_attribute(attribute) or ""
            if value.startswith("http"):
                return value
        return ""

    def _wait_for_cards(self):
        return WebDriverWait(self.driver, self.wait_seconds).until(
            lambda driver: self._find_all_cards() or self._find_product_links()
        )

    def _find_product_links(self):
        """Retourne les liens produits, même si le conteneur change."""
        links = self.driver.find_elements(
            By.CSS_SELECTOR, config.PRODUCT_LINK_SELECTOR
        )
        return [link for link in links if link.is_displayed()]

    def _product_container_from_link(self, link):
        return self.driver.execute_script(
            """
            let node = arguments[0];
            for (let i = 0; i < 8 && node; i++, node = node.parentElement) {
                const text = (node.innerText || '').trim();
                if (text.length > 20 && node.querySelector('img, .a-price, [class*="price"]')) {
                    return node;
                }
            }
            return arguments[0].parentElement;
            """,
            link,
        )

    def _scroll_until_stable(self) -> None:
        """Force le chargement des cartes lazy-loaded (défilement progressif)."""
        previous_count = 0
        stable_rounds = 0
        for _ in range(config.SCROLL_MAX_ROUNDS):
            current_count = len(self._find_all_cards())
            if current_count == previous_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
            if stable_rounds >= config.SCROLL_STABLE_THRESHOLD:
                break
            previous_count = current_count
            self.driver.execute_script(
                "window.scrollBy(0, arguments[0]);", random.randint(600, 1200)
            )
            self._pause(config.SCROLL_PAUSE_RANGE)

    def _parse_card(self, card, category: Categorie) -> Optional[Produit]:
        link = self._find_product_link(card)
        if link is None:
            return None
        url = urljoin(self.driver.current_url, link.get_attribute("href") or "")

        # Titre : sélecteurs de config.py d'abord, puis secours
        title = self._find_first(card, tuple(config.TITLE_SELECTORS) + _EXTRA_TITLE_SELECTORS)
        name = ""
        if title is not None:
            name = " ".join(
                (
                    title.get_attribute("title")
                    or title.get_attribute("alt")
                    or title.text
                    or title.get_attribute("textContent")
                    or ""
                ).split()
            )
        if not name:
            return None

        # Prix : sélecteurs de config.py d'abord, puis secours
        price = self._find_first(card, tuple(config.PRICE_SELECTORS) + _EXTRA_PRICE_SELECTORS)
        price_text = self._read_text(price) if price else ""

        rating = self._find_first(card, config.RATING_SELECTORS)
        rating_text = ""
        if rating:
            rating_text = (
                rating.get_attribute("innerText")
                or rating.get_attribute("class")
                or rating.text
                or ""
            )
        card_text = (card.text or "").lower()
        unavailable = any(marker in card_text for marker in config.UNAVAILABLE_MARKERS)
        return Produit(
            nom=name,
            prix=self.parse_price(price_text),
            note=self.parse_rating(rating_text),
            disponibilite=not unavailable,
            url=url,
            image=self._get_image(card),
            categorie=category.nom,
        )

    def _next_page_url(self) -> Optional[str]:
        next_link = self._find_first(self.driver, self.NEXT_PAGE_SELECTORS)
        if next_link is None:
            return None
        classes = next_link.get_attribute("class") or ""
        if "a-disabled" in classes:
            return None
        href = next_link.get_attribute("href") or ""
        return urljoin(self.driver.current_url, href) if href else None

    def scrape_category(
        self,
        category: Categorie,
        limit: int,
        on_product: Optional[ProgressCallback] = None,
    ) -> List[Produit]:
        """Scrape jusqu'à `limit` produits, en parcourant plusieurs pages."""
        if limit <= 0:
            return []

        if not self._open_category_from_home(category):
            print(f"[INFO] {category.nom} : impossible d'ouvrir la catégorie (blocage ou réseau).")
            return []

        products: List[Produit] = []
        seen_urls = set()
        visited_pages = set()
        estimated_pages = (
            (limit + config.ITEMS_PER_PAGE_ESTIMATE - 1) // config.ITEMS_PER_PAGE_ESTIMATE
            + config.PAGE_BUFFER
        )
        max_pages = max(1, min(config.MAX_PAGES_LIMIT, estimated_pages))

        for _ in range(max_pages):
            current_url = self.driver.current_url
            if current_url in visited_pages:
                break
            visited_pages.add(current_url)
            try:
                self._wait_for_cards()
            except TimeoutException:
                print(f"[INFO] {category.nom} : aucune carte trouvée sur {current_url}")
                break

            self._scroll_until_stable()
            cards = self._find_all_cards()
            if not cards:
                cards = [
                    self._product_container_from_link(link)
                    for link in self._find_product_links()
                ]
                cards = [card for card in cards if card is not None]

            before_page = len(products)
            rejected = 0
            for card in cards:
                if len(products) >= limit:
                    break
                try:
                    card_class = card.get_attribute("class") or ""
                    if any(ignored in card_class for ignored in config.IGNORED_CARD_CLASSES):
                        continue
                    product = self._parse_card(card, category)
                except StaleElementReferenceException:
                    continue
                if product is None:
                    rejected += 1
                    continue
                if product.url in seen_urls:
                    continue
                seen_urls.add(product.url)
                products.append(product)
                if on_product:
                    on_product(product)

            print(
                f"[INFO] {category.nom} : {len(cards)} cartes, "
                f"{len(products) - before_page} retenues, {rejected} rejetées"
            )

            if len(products) >= limit:
                break
            next_url = self._next_page_url()
            if not next_url or len(products) == before_page:
                break
            if not self._navigate(next_url):
                break
            self._dismiss_overlays()
            self._pause(config.PAGE_TRANSITION_DELAY_RANGE)

        return products[:limit]

    def close(self) -> None:
        if self.driver:
            self.driver.quit()


# Aliases pour rétrocompatibilité
ScraperController = AmazonScraper
Amazon_Scraper = AmazonScraper