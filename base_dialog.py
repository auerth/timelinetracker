import tkinter as tk
from tkinter import ttk, simpledialog
import ctypes

class BaseDialog(simpledialog.Dialog):
    """Eine Basis-Klasse für alle Dialoge in der App, die das dunkle Design übernehmen soll."""
    def __init__(self, parent, title, colors):
        self.colors = colors
        # HINWEIS: simpledialog.Dialog.__init__ ist blockierend.
        # Wir rufen es erst ganz am Ende auf.
        
        # --- Generelles Styling für alle Dialoge ---
        # 1. ttk-Stile definieren (z.B. für das dunkle Entry-Feld)
        style = ttk.Style()
        style.configure(
            'Dark.TEntry', 
            fieldbackground=self.colors['canvas_bg'],
            foreground=self.colors['fg'],
            insertcolor=self.colors['fg'],
            bordercolor=self.colors['canvas_bg'], # Rahmenfarbe im Normalzustand
            borderwidth=1
        )
        style.map('Dark.TEntry',
            # Rahmenfarbe, wenn das Widget den Fokus hat
            bordercolor=[('focus', self.colors['manual_block'])]
        )
        
        # Der Aufruf an die Elternklasse startet den Dialog
        super().__init__(parent, title=title)

    def _initialize_window_style(self):
        """Wird aufgerufen, nachdem das Fenster erstellt wurde."""
        # 2. Icon für die Titelleiste setzen
        try:
            # Wichtig: 'self' ist das Dialogfenster (Toplevel)
            self.iconbitmap("icon.ico") 
        except tk.TclError:
            print("Dialog-Icon 'icon.ico' nicht gefunden.")
            
        # 3. Titelleiste auf Dark Mode setzen (mit Verzögerung für mehr Zuverlässigkeit)
        self.after(50, self._set_dark_title_bar)

    def _set_dark_title_bar(self):
        """Setzt die Titelleiste auf Dark Mode via ctypes."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            value = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass
            
    def body(self, master):
        # Diese Methode wird von der Kind-Klasse (z.B. SearchDialog) überschrieben.
        # Aber wir rufen hier die Initialisierung auf, da hier das Fenster sicher existiert.
        self._initialize_window_style()
        return None # Muss von der Kind-Klasse implementiert werden

    def buttonbox(self):
        # 4. Generische, gestylte Buttons für alle Dialoge
        box = ttk.Frame(self)
        ok_button = ttk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        ok_button.pack(side=tk.LEFT, padx=5, pady=5)
        cancel_button = ttk.Button(box, text="Abbrechen", width=10, command=self.cancel)
        cancel_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", lambda event: self.ok())
        self.bind("<Escape>", lambda event: self.cancel())
        box.pack()