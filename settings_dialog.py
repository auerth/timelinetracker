# Du musst deine BaseDialog-Klasse importieren
from base_dialog import BaseDialog 
import os # sicherstellen, dass os importiert ist
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
class SettingsDialog(BaseDialog):
    def __init__(self, parent, title, colors, settings_manager, app_dir, config_path, db_path):
        # Wir übergeben die benötigten Manager und Pfade
        self.settings_manager = settings_manager
        self.app_dir = app_dir
        self.config_path = config_path
        self.db_path = db_path
        self.root_window = parent # Referenz zum Hauptfenster speichern

        # Tkinter-Variable für die Checkbox initialisieren
        self.autostart_var = tk.BooleanVar(value=self.settings_manager.is_autostart_enabled())

        # Ruft die __init__ von BaseDialog auf, die das Fenster erstellt und stylt
        super().__init__(parent, title=title, colors=colors)

    def body(self, master):
        # Ruft die Styling-Initialisierung der BaseDialog auf
        super().body(master)

        # Hintergrundfarben für den Inhaltsbereich setzen
        self.config(bg=self.colors['bg'])
        master.config(bg=self.colors['bg'])
        
        frame = ttk.Frame(master, padding=20)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        # --- WIDGETS ---
        autostart_check = ttk.Checkbutton(frame, text="Automatisch mit Windows starten", variable=self.autostart_var)
        autostart_check.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))
        
        maintenance_frame = ttk.LabelFrame(frame, text="Wartung & Fehlerbehebung", padding=10)
        maintenance_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        btn_open_dir = ttk.Button(maintenance_frame, text="Daten-Ordner öffnen", command=self.open_app_directory)
        btn_open_dir.pack(fill='x', pady=2)
        
        btn_open_config = ttk.Button(maintenance_frame, text="Konfigurationsdatei bearbeiten", command=self.open_config_file)
        btn_open_config.pack(fill='x', pady=2)

        btn_delete_db = ttk.Button(maintenance_frame, text="Lokale Datenbank löschen...", command=self.delete_database)
        btn_delete_db.pack(fill='x', pady=(2, 0))

        return autostart_check # Widget, das den initialen Fokus erhält

    def apply(self):
        """Wird aufgerufen, wenn der OK-Button geklickt wird."""
        try:
            self.settings_manager.set_autostart(self.autostart_var.get())
            messagebox.showinfo("Gespeichert", "Einstellungen wurden erfolgreich gespeichert.", parent=self)
        except Exception as e:
            messagebox.showerror("Fehler", f"Autostart konnte nicht geändert werden:\n{e}", parent=self)

    # --- Hilfsmethoden (vorher innere Funktionen) ---
    def open_app_directory(self):
        try:
            os.startfile(self.app_dir)
        except Exception as e:
            messagebox.showerror("Fehler", f"Verzeichnis konnte nicht geöffnet werden:\n{e}", parent=self)

    def open_config_file(self):
        try:
            os.startfile(self.config_path)
        except Exception as e:
            messagebox.showerror("Fehler", f"Konfigurationsdatei konnte nicht geöffnet werden:\n{e}", parent=self)

    def delete_database(self):
        if messagebox.askyesno("Datenbank wirklich löschen?",
                               "Sind Sie sicher? Alle lokal gespeicherten Zeiteinträge werden unwiderruflich gelöscht. "
                               "Die Anwendung muss danach neu gestartet werden.",
                               parent=self):
            try:
                if os.path.exists(self.db_path):
                    os.remove(self.db_path)
                    messagebox.showinfo("Erfolg", "Die Datenbank wurde gelöscht. Die Anwendung wird jetzt beendet.", parent=self)
                    self.root_window.destroy() # Hauptanwendung beenden
                else:
                    messagebox.showinfo("Hinweis", "Die Datenbank existiert bereits nicht mehr.", parent=self)
            except Exception as e:
                messagebox.showerror("Fehler", f"Datenbank konnte nicht gelöscht werden:\n{e}", parent=self)