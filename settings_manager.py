import sqlite3
import os
import sys
import winshell
from app_config import DB_PATH, initialize_config

# --- Konstanten ---
# Der Name, den die Verknüpfung im Autostart haben soll
SHORTCUT_NAME = "Timeline Tracker.lnk" 
# Der Name deines Hauptskripts
# WICHTIG: Passe diesen Namen an, falls deine Hauptdatei anders heißt!
MAIN_SCRIPT_NAME = "main.py" 


def setup_database():
    """Initialisiert die Datenbanktabellen, falls sie nicht existieren."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, app_name TEXT, window_title TEXT,
            start_time DATETIME UNIQUE, end_time DATETIME
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manual_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL, description TEXT NOT NULL, externalId TEXT NOT NULL, time_entry_id TEXT NOT NULL, comment TEXT NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_manual_start_time ON manual_events (start_time)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)
    ''')
    conn.commit()
    conn.close()

def save_setting(key, value):
    """Speichert eine Einstellung in der Datenbank."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def load_setting(key):
    """Lädt eine Einstellung aus der Datenbank."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else ""

# --- Autostart-Funktionen ---

def _get_shortcut_path():
    """Gibt den vollständigen Pfad zur Autostart-Verknüpfung zurück."""
    return os.path.join(winshell.startup(), SHORTCUT_NAME)

def is_autostart_enabled():
    """Prüft, ob die Autostart-Verknüpfung existiert."""
    return os.path.exists(_get_shortcut_path())

def set_autostart(enable: bool):
    """Aktiviert oder deaktiviert den Autostart durch Erstellen/Löschen der Verknüpfung."""
    shortcut_path = _get_shortcut_path()
    
    if enable:
        if is_autostart_enabled():
            return # Ist bereits aktiviert

        # Pfad zum pythonw.exe Interpreter (vermeidet Konsolenfenster)
        python_executable = sys.executable.replace("python.exe", "pythonw.exe")
        # Pfad zum Hauptskript
        script_path = os.path.abspath(MAIN_SCRIPT_NAME)

        # Erstelle die Verknüpfung
        with winshell.shortcut(shortcut_path) as shortcut:
            shortcut.path = python_executable
            shortcut.arguments = f'"{script_path}"'
            shortcut.working_directory = os.path.dirname(script_path)
            shortcut.description = "Startet den Timeline Tracker automatisch."
        print("Autostart aktiviert.")
    else:
        if not is_autostart_enabled():
            return # Ist bereits deaktiviert

        try:
            os.remove(shortcut_path)
            print("Autostart deaktiviert.")
        except OSError as e:
            print(f"Fehler beim Deaktivieren des Autostarts: {e}")
            
            
            
