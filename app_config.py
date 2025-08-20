import os
import sys
import shutil

# Direkt den Benutzer-Ordner als Basis verwenden (z.B. C:\Users\thorr)
base_path = os.path.expanduser('~')


# Name für das Verzeichnis deiner Anwendung
APP_NAME = "TimelineTracker"
APP_DIR = os.path.join(base_path, APP_NAME)

# Sicherstellen, dass dieses Verzeichnis existiert
os.makedirs(APP_DIR, exist_ok=True)


# Definiere die finalen Pfade für deine Dateien
DB_PATH = os.path.join(APP_DIR, 'timeline_tracker_5min.db')
# ... restlicher Code ...
# Definiere die finalen Pfade für deine Dateien
DB_PATH = os.path.join(APP_DIR, 'timeline_tracker_5min.db')
CONFIG_PATH = os.path.join(APP_DIR, 'api_config.json')

def get_script_dir():
    """Gibt das Verzeichnis des laufenden Skripts zurück."""
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist (z.B. mit PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Im normalen Entwicklungsmodus
        return os.path.dirname(os.path.abspath(__file__))

def initialize_config():
    """
    Prüft, ob die api_config.json im Roaming-Ordner existiert.
    Wenn nicht, wird 'api_config.json.example' vom Skript-Verzeichnis 
    als 'api_config.json' dorthin kopiert.
    """
    # Prüft, ob die Zieldatei bereits existiert.
    if not os.path.exists(CONFIG_PATH):
        # Pfad zur Beispieldatei, die mit der App ausgeliefert wird.
        example_path = os.path.join(get_script_dir(), 'api_config.json.example')
        
        # Prüft, ob die Beispieldatei vorhanden ist.
        if os.path.exists(example_path):
            # Kopiert die Beispieldatei zum Zielpfad. 
            # shutil.copy2 benennt die Datei automatisch um, da der Zieldateiname anders ist.
            shutil.copy2(example_path, CONFIG_PATH)
            print(f"'{CONFIG_PATH}' wurde aus der Vorlage erstellt. Bitte mit API-Daten füllen.")
        else:
            # Fallback: Erstellt eine leere Datei, falls keine Vorlage gefunden wird.
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write('{}')
            print(f"Leere '{CONFIG_PATH}' wurde erstellt, da keine Vorlage gefunden wurde. Bitte mit API-Daten füllen.")