"""
Generator Linków dla Subito.it.

Skrypt omija limity paginacji (maksymalnie 300 stron wyników na jedno zapytanie) 
poprzez dynamiczne generowanie linków z nałożonymi wąskimi widełkami cenowymi.

Autor: Zuzanna Bosak
Licencja: MIT
"""

class PageLinkGenerator:
    """Klasa generująca listę stron do przeszukania dla wielu filtrów naraz."""

    def __init__(self, base_url):
        self.base_url = base_url

    def save_all_links(self, filename, max_pages):
        """
        Generuje i zapisuje linki do pliku .txt na podstawie widełek cenowych.
        """

        price_ranges = [
            (20000, 50000), (50000, 100000), (100000, 130000),
            (130000, 150000), (150000, 170000), (170000, 190000),
            (190000, 220000), (220000, 250000), (250000, 290000),
            (290000, 350000), (350000, 450000), (450000, 700000),
            (700000, 1000000), (1000000, 2000000), (2000000, 3000000),
            (3000000, 4000000)
        ]

        with open(filename, "w", encoding="utf-8") as f:
            for price_from, price_to in price_ranges:
                for i in range(1, max_pages + 1):
                   
                    link = f"{self.base_url}?o={i}&ps={price_from}&pe={price_to}"
                    f.write(link + "\n")

        print(f"Zapisano linki dla {len(price_ranges)} filtrów (po {max_pages} stron) w pliku {filename}")


if __name__ == "__main__":
    BASE = "https://www.subito.it/annunci-italia/vendita/immobili/"
    generator = PageLinkGenerator(BASE)
    generator.save_all_links("links_to_pages.txt", 300)