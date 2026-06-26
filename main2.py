"""
Estymator Cen Nieruchomości - Włochy.

Główny plik aplikacji graficznej stworzonej w bibliotece Flet.
Aplikacja wykorzystuje wytrenowane modele Machine Learning (Regresja Liniowa 
oraz Las Losowy) do przewidywania cen włoskich nieruchomości na podstawie 
podanych parametrów, takich jak metraż, lokalizacja czy udogodnienia.
Ocenia również, czy podana przez nas cena jest zgodna z rynkową, czy jest za wysoka bądź za niska.

Autor: Zuzanna Bosak
Licencja: MIT
"""

import os
import sqlite3
from datetime import datetime

import flet as ft
import joblib
import numpy as np
import pandas as pd


class DatabaseManager:
    """
    Klasa obsługująca lokalną bazę danych SQLite dla historii wyszukiwań.
    
    Odpowiada za tworzenie tabeli, dodawanie nowych zapytań użytkownika
    oraz odczytywanie i czyszczenie historii.
    """

    def __init__(self, db_name="history.db"):
        """
        Inicjalizuje menedżera bazy danych.

        Args:
            db_name (str): Nazwa (lub ścieżka) pliku bazy danych. Domyślnie 'history.db'.
        """
        self.db_name = db_name
        self._create_table()

    def _create_table(self):
        """Tworzy tabelę 'history' w bazie danych, jeśli jeszcze nie istnieje."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    typ TEXT,
                    metraz REAL,
                    prowincja TEXT,
                    cena_rf REAL
                )
            """)
            conn.commit()

    def add_history(self, typ, metraz, prowincja, cena_rf):
        """
        Dodaje nowy wpis do historii wycen.

        Args:
            typ (str): Typ nieruchomości (np. 'mieszkania', 'domy').
            metraz (float): Powierzchnia nieruchomości.
            prowincja (str): Kod prowincji lub nazwa regionu.
            cena_rf (float): Przewidywana cena z modelu Random Forest.
        """
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO history (timestamp, typ, metraz, prowincja, cena_rf) VALUES (?, ?, ?, ?, ?)",
                (now, typ, metraz, prowincja, cena_rf)
            )
            conn.commit()

    def get_history(self):
        """
        Pobiera 20 ostatnich wpisów z historii wyszukiwań.

        Zwraca:
            list: Lista krotek reprezentujących wiersze z bazy danych.
        """
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, typ, metraz, prowincja, cena_rf FROM history ORDER BY id DESC LIMIT 20")
            return cursor.fetchall()

    def clear_history(self):
        """Czyści całkowicie tabelę historii w bazie danych."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history")
            conn.commit()


class PropertyApp:
    """
    Główna klasa interfejsu graficznego Flet i silnika sztucznej inteligencji.
    
    Zarządza logiką ładowania modeli predykcyjnych, przetwarzaniem danych 
    wejściowych od użytkownika oraz budowaniem widoku aplikacji (UI).
    """

    PROVINCE_TO_REGION = {
        'MI': 'Lombardia', 'RM': 'Lazio', 'TO': 'Piemonte', 'NA': 'Campania',
        'VE': 'Veneto', 'FI': 'Toscana', 'BO': 'Emilia-Romagna', 'BA': 'Puglia',
        'PA': 'Sicilia', 'GE': 'Liguria', 'CA': 'Sardegna'
    }

    FEATURE_ORDER = [
        'Metraz', 'Liczba_Pokoi', 'Blisko_Morza', 'Po_Remoncie', 'Winda', 'Klimatyzacja', 'Dlugosc_Opisu',
        'Prowincja_Encoded', 'Region_Basilicata', 'Region_Calabria', 'Region_Campania', 'Region_Emilia-Romagna',
        'Region_Friuli-Venezia Giulia', 'Region_Lazio', 'Region_Liguria', 'Region_Lombardia', 'Region_Marche',
        'Region_Molise', 'Region_Piemonte', 'Region_Puglia', 'Region_Sardegna', 'Region_Sicilia', 'Region_Toscana',
        'Region_Trentino-Alto Adige', 'Region_Umbria', "Region_Valle d'Aosta", 'Region_Veneto'
    ]

    def __init__(self):
        """Inicjalizuje bazę danych, słowniki konfiguracyjne i próbuje załadować pliki modeli ML."""
        self.db = DatabaseManager()
        self.models_loaded = False
        self.assets = {'mieszkania': {}, 'domy': {}}

        try:
            self.assets['mieszkania']['lr'] = joblib.load(os.path.join("models", "lr_model_mieszkania.pkl"))
            self.assets['mieszkania']['rf'] = joblib.load(os.path.join("models", "rf_model_mieszkania.pkl"))
            self.assets['mieszkania']['encoder'] = joblib.load(os.path.join("models", "encoder_mieszkania.pkl"))
            
            self.assets['domy']['lr'] = joblib.load(os.path.join("models", "lr_model_domy.pkl"))
            self.assets['domy']['rf'] = joblib.load(os.path.join("models", "rf_model_domy.pkl"))
            self.assets['domy']['encoder'] = joblib.load(os.path.join("models", "encoder_domy.pkl"))
            
            self.models_loaded = True
            print("Wszystkie modele wczytane poprawnie!")
        except Exception as e:
            print(f"Błąd ładowania modeli: {e}")

    def main(self, page: ft.Page):
        """
        Główna funkcja budująca interfejs użytkownika w oknie aplikacji.

        Args:
            page (ft.Page): Obiekt reprezentujący główne okno aplikacji Flet.
        """
        page.title = "Estymator Cen Nieruchomości - Włochy"
        page.theme_mode = ft.ThemeMode.DARK 
        page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(primary=ft.Colors.INDIGO_400),
            font_family="Georgia"  
        )
        page.padding = 20
        page.scroll = "adaptive"

        
        type_dropdown = ft.Dropdown(
            label="Typ nieruchomości",
            options=[ft.dropdown.Option("mieszkania", "Mieszkanie"), ft.dropdown.Option("domy", "Dom")],
            value="mieszkania"
        )
        area_input = ft.TextField(label="Metraż (m²)", keyboard_type=ft.KeyboardType.NUMBER)
        rooms_input = ft.TextField(label="Liczba pokoi", keyboard_type=ft.KeyboardType.NUMBER, value="3")
        location_input = ft.TextField(label="Kod prowincji (np. MI) lub Region (np. Lazio)", value="MI")
        desc_len_input = ft.TextField(label="Długość opisu (znaki)", value="500", keyboard_type=ft.KeyboardType.NUMBER)
        user_price_input = ft.TextField(label="Twoja cena (€) - opcjonalnie", keyboard_type=ft.KeyboardType.NUMBER)

        chk_renovated = ft.Checkbox(label="Po remoncie")
        chk_sea = ft.Checkbox(label="Blisko morza")
        chk_elevator = ft.Checkbox(label="Winda")
        chk_ac = ft.Checkbox(label="Klimatyzacja")

     
        result_lr = ft.Text("Regresja Liniowa", size=16, weight=ft.FontWeight.W_500)
        result_rf = ft.Text("Las Losowy", size=16, weight=ft.FontWeight.BOLD)
        market_eval = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
        history_list = ft.ListView(expand=True, spacing=5)

        def update_history():
            """Odświeża widok listy historii na podstawie bazy danych."""
            history_list.controls.clear()
            for r in self.db.get_history():
                history_list.controls.append(
                    ft.Text(f"[{r[0]}] {r[1].capitalize()} | {r[3].upper()} | {r[2]}m² -> {r[4]:,.2f} €")
                )
            page.update()

        def clear_history_click(e):
            """Czyści widok oraz wpisy historii w bazie po kliknięciu przycisku."""
            self.db.clear_history()
            update_history()

        def predict_click(e):
            """
            Główna logika aplikacji po kliknięciu 'Szacuj Cenę'.
            Pobiera dane z formularza, przygotowuje wektor cech i wykonuje predykcję.
            """
            if not self.models_loaded:
                result_rf.value = "BŁĄD: Brak plików modeli w folderze 'models'!"
                result_rf.color = ft.Colors.RED
                page.update()
                return

            area_input.error_text = None
            try:
                area = float(area_input.value)
                if area <= 0: raise ValueError
            except ValueError:
                area_input.error_text = "Podaj poprawny metraż"
                page.update()
                return

            rooms = float(rooms_input.value) if rooms_input.value else 3.0
            desc_len = float(desc_len_input.value) if desc_len_input.value else 500.0
            loc_val = str(location_input.value).strip()

            if len(loc_val) == 2:
                prov = loc_val.upper()
                region = self.PROVINCE_TO_REGION.get(prov, "Inne")
            else:
                prov = "BRAK"
                loc_lower = loc_val.lower()
                if loc_lower in ["emilia romagna", "emilia-romagna"]: region = "Emilia-Romagna"
                elif loc_lower in ["friuli venezia giulia", "friuli-venezia giulia"]: region = "Friuli-Venezia Giulia"
                elif loc_lower in ["valle d'aosta", "valle daosta", "valle d aosta"]: region = "Valle d'Aosta"
                elif loc_lower in ["trentino alto adige", "trentino-alto adige"]: region = "Trentino-Alto Adige"
                else: region = loc_val.title()

            typ = type_dropdown.value
            models = self.assets[typ]
            encoded_val = models['encoder'].get(prov, np.mean(list(models['encoder'].values())))

            features = {col: 0.0 for col in self.FEATURE_ORDER}
            features['Metraz'] = area
            features['Liczba_Pokoi'] = rooms
            features['Blisko_Morza'] = 1.0 if chk_sea.value else 0.0
            features['Po_Remoncie'] = 1.0 if chk_renovated.value else 0.0
            features['Winda'] = 1.0 if chk_elevator.value else 0.0
            features['Klimatyzacja'] = 1.0 if chk_ac.value else 0.0
            features['Dlugosc_Opisu'] = desc_len
            features['Prowincja_Encoded'] = encoded_val

            if f"Region_{region}" in features:
                features[f"Region_{region}"] = 1.0

            display_loc = prov if prov != "BRAK" else region
            input_df = pd.DataFrame([features])[self.FEATURE_ORDER]

            try:
                pred_log_lr = models['lr'].predict(input_df)[0]
                pred_log_rf = models['rf'].predict(input_df)[0]
                
                cena_lr = max(0.0, float(np.expm1(pred_log_lr)))
                cena_rf = max(0.0, float(np.expm1(pred_log_rf)))
            except Exception as ex:
                result_rf.value = f"Błąd obliczeń: {ex}"
                page.update()
                return

            lower = cena_rf * 0.85
            upper = cena_rf * 1.15

            result_lr.value = f"Regresja Liniowa: {cena_lr:,.2f} €"
            result_rf.value = f"Las Losowy: {cena_rf:,.2f} €\nWidełki (85-115%): {lower:,.2f} - {upper:,.2f} €"

            market_eval.value = ""
            if user_price_input.value:
                try:
                    user_price = float(user_price_input.value)
                    if user_price < lower:
                        market_eval.value = "Cena znacznie poniżej wartości rynkowej."
                        market_eval.color = ft.Colors.GREEN_700
                    elif user_price > upper:
                        market_eval.value = "Cena jest za wysoka. Nieruchomość przeszacowana."
                        market_eval.color = ft.Colors.RED_700
                    else:
                        market_eval.value = "Cena adekwatna do rynku."
                        market_eval.color = ft.Colors.BLUE_700
                except ValueError:
                    pass

            self.db.add_history(typ, area, display_loc, cena_rf)
            update_history()

        btn_predict = ft.ElevatedButton("Szacuj Cenę", on_click=predict_click)
        btn_clear = ft.ElevatedButton("Wyczyść historię", on_click=clear_history_click, color=ft.Colors.RED)

        
        page.add(
            ft.Text("Estymator Cen Nieruchomości - Włochy", size=26, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.ResponsiveRow([
                ft.Column([
                    ft.Text("Dane nieruchomości:", size=18, weight=ft.FontWeight.BOLD),
                    type_dropdown, location_input, area_input, rooms_input, desc_len_input,
                    ft.Row([chk_sea, chk_renovated]),
                    ft.Row([chk_elevator, chk_ac]),
                    user_price_input,
                    btn_predict
                ], col={"sm": 12, "md": 5}),
                ft.Column([
                    ft.Text("Wyniki estymacji:", size=18, weight=ft.FontWeight.BOLD),
                    ft.Card(content=ft.Container(content=ft.Column([result_lr, ft.Divider(), result_rf, market_eval]), padding=15)),
                    ft.Divider(),
                    ft.Row([ft.Text("Historia Oszacowań", size=16, weight=ft.FontWeight.BOLD), btn_clear], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(history_list, height=250, bgcolor=ft.Colors.GREY_900, border_radius=8, padding=10)
                ], col={"sm": 12, "md": 7})
            ])
        )
        update_history()


if __name__ == "__main__":
    app = PropertyApp()
    ft.app(target=app.main)