import re
import time
from typing import Callable, List, Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from controllers.categories import AMAZON_BASE_URL, Categorie
from models.item import Produit


ProgressCallback = Callable[[Produit], None]


class ScraperController:
    """Scraper Amazon multi-pages avec défilement et déduplication."""

    # Classes de cartes produit Amazon. On évite les identifiants instables.
    CARD_SELECTOR = ".zg-grid-general-faceout, .a-carousel-card, .s-result-item, .a-cardui"
    NEXT_PAGE_SELECTORS = (
        ".a-pagination .a-last a",
        ".a-last a",
        ".s-pagination-next",
    )

    def __init__(self, headless: bool = True, wait_seconds: int = 12):
        self.wait_seconds = wait_seconds
        self.base_url = AMAZON_BASE_URL
        self.driver = self._init_driver(headless)

    def _init_driver(self, headless: bool):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=fr-FR")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )

    def _navigate(self, url: str, attempts: int = 3) -> bool:
        """Navigue avec quelques tentatives pour absorber les erreurs réseau temporaires."""
        for attempt in range(attempts):
            try:
                self.driver.get(url)
                return True
            except WebDriverException:
                if attempt == attempts - 1:
                    return False
                time.sleep(1.5 * (attempt + 1))
        return False

    @staticmethod
    def parse_price(text: str) -> float:
        cleaned = re.sub(r"[^\d,.]", "", text)
        if not cleaned:
            return 0.0
        comma = cleaned.rfind(",")
        dot = cleaned.rfind(".")
        decimal = "," if comma > dot else "."
        if comma >= 0 and dot >= 0:
            cleaned = cleaned.replace("." if decimal == "," else ",", "")
        try:
            return float(cleaned.replace(decimal, "."))
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

    def _find_all_cards(self):
        return self.driver.find_elements(By.CSS_SELECTOR, self.CARD_SELECTOR)

    def _dismiss_overlays(self) -> None:
        """Ferme les écrans de consentement qui peuvent masquer la page."""
        selectors = (
            "#sp-cc-accept",
            "#sp-cc-rejectall-link",
            "input[name='accept']",
            "button[name='accept']",
            ".a-button-primary[name='accept']",
        )
        for selector in selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if buttons and buttons[0].is_displayed():
                    self.driver.execute_script("arguments[0].click();", buttons[0])
                    time.sleep(0.5)
                    return
            except Exception:
                continue

    def _get_image(self, card) -> str:
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", card
        )
        time.sleep(0.1)
        image = self._find_first(card, [
            ".s-image",
            ".a-dynamic-image",
            ".product-image",
            "img",
        ])
        if image is None:
            return ""
        for attribute in ("src", "data-src", "data-old-hires"):
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
            By.CSS_SELECTOR, "a[href*='/dp/'], a[href*='/gp/product/']"
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
        """Force le chargement des cartes lazy-loaded avant l'extraction."""
        previous_count = 0
        stable_rounds = 0
        for _ in range(8):
            current_count = len(self._find_all_cards())
            if current_count == previous_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
            if stable_rounds >= 2:
                break
            previous_count = current_count
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.7)

    def _parse_card(self, card, category: Categorie) -> Optional[Produit]:
        title = self._find_first(card, [
            ".p13n-sc-truncate-desktop-type2",
            ".p13n-sc-truncate",
            "[class*='p13n-sc-css-line-clamp']",
            ".a-size-medium",
            ".a-size-base-plus",
        ])
        link = self._find_first(card, [
            ".a-link-normal.aok-block",
            ".a-link-normal",
        ])
        if link is None:
            return None

        url = urljoin(self.driver.current_url, link.get_attribute("href") or "")
        if not url or "/dp/" not in url and "/gp/product/" not in url:
            return None

        if title is None:
            title = self._find_first(card, ["img[alt]"])
        name = " ".join(
            ((title.get_attribute("title") if title else "")
             or (title.get_attribute("alt") if title else "")
             or (title.text if title else "")).split()
        )
        if not name:
            return None

        price = self._find_first(card, [
            ".p13n-sc-price",
            ".a-price .a-offscreen",
            ".a-price-whole",
        ])
        rating = self._find_first(card, [".a-icon-alt", ".a-icon-star"])
        rating_text = ""
        if rating:
            rating_text = (
                rating.get_attribute("innerText")
                or rating.get_attribute("class")
                or rating.text
            )
        card_text = (card.text or "").lower()
        unavailable = any(
            marker in card_text
            for marker in ("indisponible", "rupture de stock", "épuisé")
        )
        return Produit(
            nom=name,
            prix=self.parse_price(price.text) if price else 0.0,
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

        if not self._navigate(self.base_url):
            return []
        self._dismiss_overlays()
        if not self._navigate(category.url):
            return []
        self._dismiss_overlays()
        products: List[Produit] = []
        seen_urls = set()
        visited_pages = set()
        max_pages = max(1, min(50, (limit + 19) // 20 + 5))

        for _ in range(max_pages):
            current_url = self.driver.current_url
            if current_url in visited_pages:
                break
            visited_pages.add(current_url)
            try:
                self._wait_for_cards()
            except TimeoutException:
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
            for card in cards:
                if len(products) >= limit:
                    break
                if "brand-story" in (card.get_attribute("class") or ""):
                    continue
                product = self._parse_card(card, category)
                if product is None or product.url in seen_urls:
                    continue
                seen_urls.add(product.url)
                products.append(product)
                if on_product:
                    on_product(product)

            if len(products) >= limit:
                break
            next_url = self._next_page_url()
            if not next_url or len(products) == before_page:
                break
            if not self._navigate(next_url):
                break
            self._dismiss_overlays()
            time.sleep(1.2)

        return products[:limit]

    def close(self) -> None:
        if self.driver:
            self.driver.quit()
