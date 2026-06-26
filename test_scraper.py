"""
Testy jednostkowe i integracyjne dla modułu scraper.py.

Autor: Zuzanna Bosak
Licencja: MIT
"""

import pytest
from unittest.mock import patch, MagicMock
from scraper import SubitoPropertyScraper


@pytest.fixture
def scraper():
    """Współdzielona instancja scrapera dla wszystkich testów."""
    return SubitoPropertyScraper("dummy_rooms.txt", "dummy_offers.txt")


@pytest.mark.parametrize(
    "opis, oczekiwany_wynik",
    [
        (
            "Splendido appartamento vicino al mare, nuovo, con ascensore e aria condizionata",
            {"Blisko_Morza": 1, "Po_Remoncie": 1, "Winda": 1, "Klimatyzacja": 1, "Dlugosc_Opisu": 79}
        ),
        (
            "Casa in montagna. Nessun servizio extra.",
            {"Blisko_Morza": 0, "Po_Remoncie": 0, "Winda": 0, "Klimatyzacja": 0, "Dlugosc_Opisu": 40}
        ),
        (
            None,
            {"Blisko_Morza": 0, "Po_Remoncie": 0, "Winda": 0, "Klimatyzacja": 0, "Dlugosc_Opisu": 0}
        ),
        (
            "Ristrutturato ma senza ascensore, a due passi dalla SPIAGGIA",
            # Scraper działa "naiwnie" i szuka słowa 'ascensore'. Słowo tam jest, więc daje 1.
            # Długość tego zdania to dokładnie 60 znaków.
            {"Blisko_Morza": 1, "Po_Remoncie": 1, "Winda": 1, "Klimatyzacja": 0, "Dlugosc_Opisu": 60}
        ),
    ],
    ids=[
        "all_amenities_present",
        "no_amenities_present",
        "empty_description_handling",
        "mixed_features_and_case_insensitivity"
    ]
)
def test_extract_features(scraper, opis, oczekiwany_wynik):
    """
    Test weryfikujący czy ekstrakcja udogodnień z opisu działa poprawnie.
    Testuje różne scenariusze, w tym brak tekstu i wielkość liter.
    """
    wynik = scraper.extract_features_from_desc(opis)
    assert wynik == oczekiwany_wynik


@patch('scraper.requests.Session.get')
def test_scrape_single_offer_success(mock_get, scraper):
    """
    Test weryfikujący poprawne wyciągnięcie danych ze strony HTML.
    Mokujemy odpowiedź z requests, żeby nie obciążać serwera Subito.it.
    """
    # Budujemy "sztuczną" stronę internetową na potrzeby testu.
    # Musimy dodać kontenery <div>, aby skrypt poprawnie określił "rodzica" znacznika.
    fake_html = """
    <html>
        <h1 class="title-123">Casa da sogno</h1>
        <p class="price-abc">150.000 €</p>
        <p class="locationText">Milano</p>
        <p class="description">Appartamento ristrutturato con ascensore</p>
        <div>
            <span>Superficie</span><span><span>90</span></span>
        </div>
        <div>
            <span>Locali</span><span><span>3</span></span>
        </div>
    </html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = fake_html
    mock_get.return_value = mock_response

    wynik = scraper.scrape_single_offer("https://subito.it/appartamenti/fake-url")

    assert wynik is not None
    assert wynik["Tytul"] == "Casa da sogno"
    assert wynik["Cena"] == 150000
    assert wynik["Metraz"] == 90
    assert wynik["Liczba_Pokoi"] == 3
    assert wynik["Po_Remoncie"] == 1
    assert wynik["Winda"] == 1


@patch('scraper.requests.Session.get')
def test_scrape_single_offer_missing_critical_data(mock_get, scraper):
    """
    Test integracyjny sprawdzający reakcję skryptu na ofertę,
    która nie ma ceny ani metrażu (powinien zwrócić None).
    """
    fake_html = """<html><h1 class="title">Brak Ceny</h1></html>"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = fake_html
    mock_get.return_value = mock_response

    wynik = scraper.scrape_single_offer("https://subito.it/fake-url2")
    assert wynik is None