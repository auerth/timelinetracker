import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import threading
import queue
import restapi_controller

class SearchDialog(simpledialog.Dialog):
    def __init__(self, parent, title, colors):
        self.search_timer = None
        self.search_id = 0
        self.result_queue = queue.Queue()
        self.results_data = []
        self.colors = colors
        
        try:
            self.api_controller = restapi_controller.ApiController()
        except FileNotFoundError:
            messagebox.showerror("Fehler", "api_config.json nicht gefunden!", parent=parent)
            self.api_controller = None
        except json.JSONDecodeError:
            messagebox.showerror("Fehler", "api_config.json enthält ungültiges JSON.", parent=parent)
            self.api_controller = None

        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="Aufgabe suchen:").pack(anchor="w")
   
        self.config(bg=self.colors['canvas_bg']) # Hintergrund für das Dialogfenster selbst
        master.config(bg=self.colors['canvas_bg']) # Hintergrund für den Haupt-Frame im Body
        self.entry = ttk.Entry(master, width=50)
        self.entry.pack(fill="x", expand=True, pady=(0, 5))
        self.entry.bind("<KeyRelease>", self.on_key_release)

        list_frame = ttk.Frame(master)
        list_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(list_frame, height=10, 
                                 bg=self.colors['canvas_bg'], 
                                 fg=self.colors['fg'], 
                                 selectbackground=self.colors['manual_block'])
        self.scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.config(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda e: self.ok())
    
        ttk.Label(master, text="Kommentar:").pack(anchor="w", pady=(10, 0))

        self.comment_text = tk.Text(master, height=4, width=50,
                                    bg=self.colors['canvas_bg'],
                                    fg=self.colors['fg'],
                                    insertbackground=self.colors['fg'], # Farbe für den Cursor
                                    highlightthickness=0, # Optional
                                    borderwidth=0)        # Optional
        self.comment_text.pack(fill="x", expand=True, pady=(0, 5))
        self.process_queue()
        return self.entry

    def on_key_release(self, event):
        if self.search_timer:
            self.after_cancel(self.search_timer)
        self.search_timer = self.after(500, self.start_search)

    def start_search(self):
        self.search_id += 1
        query = self.entry.get()

        if not self.api_controller: return
        if len(query) < 3:
            self.listbox.delete(0, tk.END)
            self.listbox.insert(tk.END, " (Bitte mindestens 3 Zeichen eingeben)")
            return
        
        self.listbox.delete(0, tk.END)
        self.listbox.insert(tk.END, f" Suche nach '{query}'...")
        threading.Thread(target=self._search_worker, args=(query, self.search_id), daemon=True).start()

    def _search_worker(self, query, search_id):
        """Worker-Thread, der den API-Aufruf durchführt."""
        results = self.api_controller.search_issue(query)
        if search_id == self.search_id:
            self.result_queue.put(results)

    def process_queue(self):
        try:
            results = self.result_queue.get_nowait()
            self.update_listbox(results)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)

    def update_listbox(self, results):
        self.listbox.delete(0, tk.END)
        self.results_data.clear()

        if isinstance(results, dict) and "error" in results:
            self.listbox.insert(tk.END, f" Fehler: {results['error']}")
            return
            
        if not results:
            self.listbox.insert(tk.END, " Keine Ergebnisse gefunden.")
            return

        self.results_data = results
        for item in self.results_data:
             # *** GEÄNDERTE LOGIK FÜR DIE ANZEIGE ***
            item_id = item.get('id', '?')
            item_display = item.get('display', 'Unbekannter Eintrag')
            display_text = f"#{item_id} {item_display}"
            self.listbox.insert(tk.END, display_text)

    def apply(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            self.result = None
            return

        selected_index = selected_indices[0]
        
        # Kommentar aus dem Textfeld auslesen
        comment = self.comment_text.get("1.0", tk.END).strip()

        if 0 <= selected_index < len(self.results_data):
            selected_task = self.results_data[selected_index]
            self.result = {
                "task": selected_task,
                "comment": comment
            }
        else:
            self.result = None