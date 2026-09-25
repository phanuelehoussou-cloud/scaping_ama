from controllers.scraper_controller import ScraperController

BASE_URL = "https://www.amazon.fr/gp/bestsellers/?ref_=nav_em_cs_bestsellers_0_1_1_2"

if __name__ == "__main__":
    controller = ScraperController(base_url=BASE_URL, headless=True)
    controller.run()