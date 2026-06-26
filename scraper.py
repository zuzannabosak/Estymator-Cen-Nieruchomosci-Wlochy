"""
Subito Real Estate Pipeline Scraper.

Skrypt służący do pobierania i parsowania ogłoszeń nieruchomości z włoskiego serwisu Subito.it.
Umożliwia ekstrakcję takich danych jak cena, metraż, liczba pokoi oraz udogodnienia (bliskość morza, klimatyzacja, winda itp.).

Autor: Zuzanna Bosak
Licencja: MIT
"""

import json
import os
import random
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup


class SubitoPropertyScraper:
    """
    Główna klasa odpowiadająca za pobieranie danych o nieruchomościach.

    Zarządza sesją HTTP, pobiera listę linków z głównych stron wyszukiwania,
    a następnie ekstrahuje szczegółowe parametry z pojedynczych ofert.

    """

    def __init__(self, rooms_file: str, offers_file: str):
        """
        Inicjalizuje obiekt scrapera i ustawia nagłówki przeglądarki.

        Args:
            rooms_file (str): Nazwa pliku z głównymi linkami wyszukiwania.
            offers_file (str): Nazwa pliku do zapisu linków ofert.
        """
        self.rooms_file = rooms_file
        self.offers_file = offers_file
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pl-PL,pl;q=0.9,en;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15',
            'Referer': 'https://www.subito.it/'
        })

    def extract_features_from_desc(self, description: str) -> dict:
        """
        Analizuje opis oferty i szuka w nim słów kluczowych dotyczących udogodnień.

        Args:
            description (str): Treść opisu ogłoszenia pobrana ze strony.

        Returns:
            dict: Słownik zawierający binarne flagi (1/0) dla udogodnień oraz długość opisu.
        """
        desc_lower = description.lower() if description else ""
        return {
            "Blisko_Morza": 1 if any(w in desc_lower for w in ["mare", "spiaggia", "litorale"]) else 0,
            "Po_Remoncie": 1 if any(w in desc_lower for w in ["ristrutturato", "rinnovato", "nuovo"]) else 0,
            "Winda": 1 if "ascensore" in desc_lower else 0,
            "Klimatyzacja": 1 if any(w in desc_lower for w in ["aria condizionata", "climatizzato"]) else 0,
            "Dlugosc_Opisu": len(desc_lower)
        }

    def scrape_single_offer(self, offer_url: str) -> dict | None:
        """
        Pobiera i przetwarza pojedynczą stronę z ofertą nieruchomości.

        Funkcja wyciąga podstawowe metadane (cena, metraż, lokalizacja) używając
        BeautifulSoup oraz wyrażeń regularnych. Symuluje również zachowanie
        człowieka poprzez losowe opóźnienia zapytań (time.sleep).

        Args:
            offer_url (str): Bezpośredni link do ogłoszenia na Subito.it.

        Returns:
            dict: Słownik z pobranymi danymi nieruchomości, jeśli zawierały cenę i metraż.
            None: Jeśli wystąpił błąd pobierania lub brakowało krytycznych danych.
        """
        try:
            time.sleep(random.uniform(2.0, 4.0))
            r = self.session.get(offer_url, timeout=15)
            if r.status_code != 200:
                return None

            html_content = r.text
            soup = BeautifulSoup(html_content, "html.parser")

            title_tag = soup.select_one('h1[class*="title"]')
            subject = title_tag.get_text().strip() if title_tag else ""

            price_tag = soup.select_one('p[class*="price"]')
            price_text = price_tag.get_text() if price_tag else ""
            price_digits = re.sub(r"[^\d]", "", price_text)
            price = int(price_digits) if price_digits else None

            loc_tag = soup.select_one('p[class*="locationText"]')
            location = loc_tag.get_text().strip() if loc_tag else "Unknown"

            desc_tag = soup.select_one('p[class*="description"]')
            body_desc = desc_tag.get_text().strip() if desc_tag else ""

            # Pobieranie metrażu
            size = None
            for span in soup.find_all('span'):
                if span.get_text().strip().lower() == 'superficie':
                    parent = span.parent
                    value_span = parent.find_all('span')[-1]
                    if value_span:
                        digits = re.sub(r"[^\d]", "", value_span.get_text())
                        if digits:
                            size = int(digits)
                            break

            
            if not size:
                for p in soup.find_all('p'):
                    text = p.get_text().strip().lower()
                    match = re.match(r"^(\d+)\s*(?:mq|m²|m2)$", text)
                    if match:
                        size = int(match.group(1))
                        break

            # Pobieranie liczby pokoi
            rooms = None
            for span in soup.find_all('span'):
                if span.get_text().strip().lower() == 'locali':
                    parent = span.parent
                    value_span = parent.find_all('span')[-1]
                    if value_span:
                        digits = re.sub(r"[^\d]", "", value_span.get_text())
                        if digits:
                            rooms = int(digits)
                            break

            # Pobieranie klasy energetycznej
            energy = "Brak"
            for span in soup.find_all('span'):
                if span.get_text().strip().lower() == 'classe energetica':
                    parent = span.parent
                    value_span = parent.find_all('span')[-1]
                    if value_span:
                        energy = value_span.get_text().strip()
                        break

            if energy == "Brak":
                energy_match = re.search(r"Classe\s+energetica[^\d<]*([A-G]\d*)", html_content, re.IGNORECASE)
                if energy_match:
                    energy = energy_match.group(1)

            if not price or not size:
                return None

            house_pattern = re.compile(r"/(ville|case|rustici|villa)[-/]", re.IGNORECASE)
            is_house = 1 if house_pattern.search(offer_url) else 0

            data = {
                "Tytul": subject,
                "Prowincja": location,
                "Cena": price,
                "Metraz": size,
                "Liczba_Pokoi": rooms if rooms else 0,
                "Typ_Dom": is_house,
                "Klasa_Energetyczna": energy,
                "URL": offer_url
            }

            data.update(self.extract_features_from_desc(body_desc))
            return data

        except Exception:
            return None


def main():
    """
    Główna funkcja sterująca procesem scrapowania (ETAP 1 i ETAP 2).

    Działanie:
    1. Odczytuje plik 'links_to_pages.txt' zawierający strony z listami wyników.
    2. Pobiera każdą stronę, analizuje ukryte dane JSON (__NEXT_DATA__) i wyciąga unikalne linki do ofert.
    3. Zapisuje zebrane linki w pliku 'offers_urls.txt'.
    4. Odczytuje zebrane linki i dla każdego z nich uruchamia szczegółowe parsowanie.
    5. Zapisuje poprawne oferty (posiadające cenę i metraż) na bieżąco do pliku 'data_real_assets.csv'.

    Przez cały czas działania program informuje o progresie.
    """
    scraper = SubitoPropertyScraper("links_to_pages.txt", "offers_urls.txt")


    try:
        with open("links_to_pages.txt", "r", encoding="utf-8") as f:
            pages_to_scrape = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Nie znaleziono pliku links_to_pages.txt. Uruchom najpierw generator!")
        pages_to_scrape = []

    all_unique_links = set()

    if pages_to_scrape:
        print(f"Zbieranie ogłoszeń z {len(pages_to_scrape)} stron ---")

        for p_idx, page_url in enumerate(pages_to_scrape, 1):
            print(f"Przeszukuję stronę [{p_idx}/{len(pages_to_scrape)}]...")
            try:
                r = scraper.session.get(page_url, timeout=10)
                if r.status_code != 200:
                    print(f"Błąd {r.status_code}. Przechodzę dalej.")
                    continue

                soup = BeautifulSoup(r.text, "html.parser")
                links_on_page = 0


                next_data_script = soup.find('script', id='__NEXT_DATA__')
                if next_data_script:
                    try:
                        json_data = json.loads(next_data_script.string)
                        items = json_data.get('props', {}).get('pageProps', {}).get(
                            'initialState', {}).get('items', {}).get('originalList', [])

                        for item in items:
                            href = item.get('urls', {}).get('default', '')
                            if href:
                                clean_link = href.split('?')[0]
                                if clean_link not in all_unique_links:
                                    all_unique_links.add(clean_link)
                                    links_on_page += 1
                    except Exception as e:
                        print(f"Błąd parsowania ukrytych danych: {e}")

                print(f"Złapano {links_on_page} nowych ogłoszeń.")

                if links_on_page == 0:
                    print("Brak ogłoszeń na stronie. Może to być koniec wyników dla tego filtra.")

                time.sleep(random.uniform(2.0, 4.0))

            except Exception as e:
                print(f"Błąd połączenia: {e}")
                continue

        # Zapis do pliku offers_urls.txt
        with open("offers_urls.txt", "w", encoding="utf-8") as f:
            for link in all_unique_links:
                f.write(link + "\n")
        print(f"Zapisano łącznie {len(all_unique_links)} linków do pliku offers_urls.txt.")


    # Parsowanie z offers_urls.txt do pliku CSV

    try:
        with open("offers_urls.txt", "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        links = []

    unique_links = list(set(links))

    if unique_links:
        print(f"\nRozpoczynam parsowanie {len(unique_links)} unikalnych ogłoszeń ---")

        for idx, link in enumerate(unique_links, start=1):
            details = scraper.scrape_single_offer(link)
            if details:
                pd.DataFrame([details]).to_csv(
                    "data_real_assets.csv",
                    mode='a',
                    header=not os.path.exists("data_real_assets.csv"),
                    index=False
                )
                print(f"  [{idx}/{len(unique_links)}] Zapisano: {details['Cena']} € | "
                      f"{details['Metraz']} mq | Pokoi: {details['Liczba_Pokoi']}")
            else:
                print(f"  [{idx}/{len(unique_links)}] Pominięto (brak ceny lub metrażu)")
    else:
        print("\nLista linków do ofert jest pusta! Skrypt kończy działanie.")


if __name__ == "__main__":
    main()