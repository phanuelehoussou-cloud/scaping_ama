import re
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from models.item import Produit
from models.repository import ProduitRepository
from views.console_view import ConsoleView


class ScraperController:
    """Scrape les produits visibles sur une page Amazon."""

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
        """Convertit les formats 19,99 €, 1.234,56 € et $19.99."""
        cleaned = re.sub(r"[^\d,.]", "", text)
        if not cleaned:
            return 0.0
        last_comma = cleaned.rfind(",")
        last_dot = cleaned.rfind(".")
        decimal_separator = "," if last_comma > last_dot else "."
        if last_comma >= 0 and last_dot >= 0:
            thousands_separator = "." if decimal_separator == "," else ","
            cleaned = cleaned.replace(thousands_separator, "")
        cleaned = cleaned.replace(decimal_separator, ".")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _parse_rating(self, text: str) -> float:
        class_match = re.search(r"a-star-(\d)-(\d)", text)
        if class_match:
            return float(f"{class_match.group(1)}.{class_match.group(2)}")
        match = re.search(r"(\d[.,]?\d?)", text)
        return float(match.group(1).replace(",", ".")) if match else 0.0

    def _get_image(self, card) -> str:
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", card
        )
        time.sleep(0.2)
        try:
            image = card.find_element(By.CSS_SELECTOR, "img")
        except NoSuchElementException:
            return ""
        for attribute in ("src", "data-src", "data-old-hires"):
            value = image.get_attribute(attribute) or ""
            if value.startswith("http"):
                return value
        return ""

    def _find_first(self, card, selectors):
        for selector in selectors:
            try:
                return card.find_element(By.CSS_SELECTOR, selector)
            except NoSuchElementException:
                continue
        return None

    def _scrape_page(self):
        cards = self._wait_for(By.CSS_SELECTOR, ".a-carousel-card")
        items = []
        for card in cards:
            if "brand-story" in (card.get_attribute("class") or ""):
                continue
            title_element = self._find_first(card, [
                "div.p13n-sc-truncate-desktop-type2",
                "a[title]",
            ])
            link_element = self._find_first(card, [
                "a.a-link-normal.aok-block",
                "a[href*='/dp/']",
            ])
            if title_element is None or link_element is None:
                continue
            nom = (title_element.get_attribute("title") or title_element.text or "").strip()
            url = link_element.get_attribute("href") or ""

            price_element = self._find_first(card, [
                "span.p13n-sc-price",
                "span.a-price .a-offscreen",
            ])
            prix = self._parse_price(price_element.text) if price_element else 0.0

            rating_element = self._find_first(card, ["span.a-icon-alt", "i.a-icon-star"])
            note = 0.0
            if rating_element:
                rating_text = rating_element.get_attribute("innerText") or rating_element.get_attribute("class") or rating_element.text
                note = self._parse_rating(rating_text)

            card_text = (card.text or "").lower()
            disponibilite = not any(
                marker in card_text
                for marker in ("indisponible", "rupture de stock", "épuisé")
            )
            if nom and url:
                items.append(Produit(
                    nom=nom,
                    prix=prix,
                    note=note,
                    disponibilite=disponibilite,
                    url=url,
                    image=self._get_image(card),
                ))
        return items

    def run(self):
        self.view.show_start(self.base_url)
        try:
            self.driver.get(self.base_url)
            time.sleep(2)
            items = self._scrape_page()
            for item in items:
                self.repository.add(item)
            self.view.show_progress(1, len(items))
            self.view.show_results(self.repository.all())
            self.view.show_saved(self.repository.save_json(), self.repository.save_csv())
        except TimeoutException:
            self.view.show_error("Timeout ou CAPTCHA Amazon détecté.")
        except WebDriverException as exc:
            self.view.show_error(f"Erreur Selenium : {exc}")
        except OSError as exc:
            self.view.show_error(f"Erreur d'enregistrement : {exc}")
        finally:
            if self.driver is not None:
                self.driver.quit()
