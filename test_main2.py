"""
Testy integracyjne i jednostkowe dla modułu main2.py (GUI).

Skupiają się na weryfikacji poprawności działania bazy danych SQLite,
do której zapisywana jest historia estymacji.

Autor: Zuzanna Bosak
Licencja: MIT
"""

import pytest
import os
from main2 import DatabaseManager


@pytest.fixture
def test_db(tmp_path):
    """
    Fixture PyTest tworzący tymczasową bazę danych na potrzeby testów.
    Dzięki tmp_path baza jest izolowana i usuwana po teście.
    """
    db_path = tmp_path / "test_history.db"
    db = DatabaseManager(db_name=str(db_path))
    yield db



@pytest.mark.parametrize(
    "typ, metraz, prowincja, cena_rf",
    [
        ("mieszkania", 50.5, "MI", 150000.0),
        ("domy", 120.0, "Sardegna", 350000.0),
        ("mieszkania", 30.0, "Lazio", 80000.50),
        ("domy", 250.0, "RM", 1000000.0),
    ],
    ids=[
        "standardowe_mieszkanie_milan",
        "duzy_dom_sardynia",
        "kawalerka_lazio",
        "luksusowy_dom_rzym"
    ]
)
def test_add_and_get_history(test_db, typ, metraz, prowincja, cena_rf):
    """
    Test weryfikujący poprawny zapis parametrów wyceny do bazy danych 
    oraz ich późniejsze poprawne odczytanie.
    """
    # Act
    test_db.add_history(typ, metraz, prowincja, cena_rf)
    historia = test_db.get_history()

    # Assert
    assert len(historia) == 1, "Baza powinna zawierać dokładnie jeden rekord"
    rekord = historia[0]
    
    # Krotka z bazy: (timestamp, typ, metraz, prowincja, cena_rf)
    assert rekord[1] == typ
    assert rekord[2] == metraz
    assert rekord[3] == prowincja
    assert rekord[4] == cena_rf



def test_clear_history(test_db):
    """
    Test weryfikujący czy metoda clear_history prawidłowo usuwa
    wszystkie rekordy, by użytkownik mógł zresetować panel GUI.
    """
    # Zapychamy bazę testowymi danymi
    test_db.add_history("domy", 100, "MI", 200000)
    test_db.add_history("mieszkania", 50, "RM", 100000)
    test_db.add_history("mieszkania", 75, "VE", 120000)
    
    # Sprawdzamy czy na pewno weszły 3 wpisy
    assert len(test_db.get_history()) == 3
    
    # Czyścimy bazę (Symulacja kliknięcia przycisku "Wyczyść historię")
    test_db.clear_history()
    
    # Sprawdzamy, czy baza jest całkowicie pusta
    assert len(test_db.get_history()) == 0