import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import sqlite3
import pygetwindow as gw
import threading
import time
from datetime import datetime, timedelta, date

# --- Globale Konstanten ---
BLOCK_DURATION_MINUTES = 5
PIXELS_PER_MINUTE = 5

# --- Globale Design-Konstanten ---
COLOR_BG = "#2e2e2e"
COLOR_CANVAS_BG = "#3a3a3a"
COLOR_FG = "#d0d0d0"
COLOR_GRID_LINE = "#4a4a4a"
COLOR_HOUR_LINE = "#888888"
COLOR_MANUAL_BLOCK = "#3a86ff"
FONT_NORMAL = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_HEADER = ("Segoe UI", 14, "bold")

# --- UI Layout Konstanten (werden für die initiale Fenstergröße verwendet) ---
WINDOW_WIDTH = 1000
TIME_AXIS_WIDTH = 60
GAP_WIDTH = 10 
Y_PADDING = 10

# --- Globale Variable für das Datum ---
displayed_date = date.today()

# --- Globale Variablen für Drag & Drop ---
drag_data = {"start_y": None, "temp_rect": None}

# --- Globale Variable für den Resize-Timer ---
resize_timer = None

# --- 1. Datenbank-Setup (unverändert) ---
def setup_database():
    conn = sqlite3.connect('timeline_tracker_5min.db')
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
            end_time DATETIME NOT NULL, description TEXT NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_manual_start_time ON manual_events (start_time)')
    conn.commit()
    conn.close()

# --- 2. 5-Minuten-Tracking-Logik (unverändert) ---
def track_activity_in_blocks():
    conn = sqlite3.connect('timeline_tracker_5min.db')
    cursor = conn.cursor()
    while True:
        now = datetime.now()
        minutes_into_hour = now.minute
        start_minute = minutes_into_hour - (minutes_into_hour % BLOCK_DURATION_MINUTES)
        block_start_time = now.replace(minute=start_minute, second=0, microsecond=0)
        block_end_time = block_start_time + timedelta(minutes=BLOCK_DURATION_MINUTES)
        
        active_window = gw.getActiveWindow()
        if active_window and active_window.title:
            title_parts = active_window.title.split('-')
            app_name = title_parts[-1].strip() if len(title_parts) > 1 else title_parts[0].strip()
            window_title = active_window.title
        else:
            app_name, window_title = "System", "Inaktiv / Kein Fenster"

        cursor.execute(
            'INSERT OR IGNORE INTO activity_events (app_name, window_title, start_time, end_time) VALUES (?, ?, ?, ?)',
            (app_name, window_title, block_start_time, block_end_time)
        )
        conn.commit()
        
        sleep_duration_seconds = (block_end_time - datetime.now()).total_seconds()
        if sleep_duration_seconds > 0:
            time.sleep(sleep_duration_seconds + 1)

# --- 3. Logik zum Zusammenfassen von Blöcken (unverändert) ---
def _merge_blocks(events):
    if not events: return []
    merged = []
    current_app, current_title, current_start, _ = events[0]
    duration = BLOCK_DURATION_MINUTES
    for i in range(1, len(events)):
        next_app, next_title, _, _ = events[i]
        if next_app == current_app and next_title == current_title:
            duration += BLOCK_DURATION_MINUTES
        else:
            merged.append({"app": current_app, "title": current_title, "start_time": datetime.fromisoformat(current_start), "duration": duration})
            current_app, current_title, current_start, _ = events[i]
            duration = BLOCK_DURATION_MINUTES
    merged.append({"app": current_app, "title": current_title, "start_time": datetime.fromisoformat(current_start), "duration": duration})
    return merged

# --- 4. UI-Zeichenfunktionen (angepasst für Responsivität) ---
def _draw_time_axis_and_grid(canvas, width):
    """Hilfsfunktion zum Zeichnen der Zeitachse und der Gitterlinien auf einem Canvas."""
    canvas.delete("all")
    for hour in range(24):
        y_pos_hour = (hour * 60) * PIXELS_PER_MINUTE + Y_PADDING
        
        # Stündliche Linie und Beschriftung
        canvas.create_line(TIME_AXIS_WIDTH, y_pos_hour, width, y_pos_hour, fill=COLOR_HOUR_LINE, width=1)
        canvas.create_text(TIME_AXIS_WIDTH - 5, y_pos_hour, text=f"{hour:02d}:00", anchor="e", font=FONT_BOLD, fill=COLOR_FG)
        
        # 5-Minuten Gitterlinien
        for minute in range(5, 60, 5):
            y_pos = y_pos_hour + (minute * PIXELS_PER_MINUTE)
            canvas.create_line(TIME_AXIS_WIDTH + 5, y_pos, width, y_pos, fill=COLOR_GRID_LINE, dash=(2, 4))
            canvas.create_text(
                TIME_AXIS_WIDTH - 5, y_pos, 
                text=f"{hour:02d}:{minute:02d}", 
                anchor="e", 
                font=("Segoe UI", 7), 
                fill="gray"
            )

def draw_timeline(target_date):
    """Zeichnet die komplette Timeline auf den getrennten Canvases."""
    # NEU: Aktuelle Breite der Canvases abfragen
    auto_width = canvas_auto.winfo_width()
    manual_width = canvas_manual.winfo_width()

    # Wenn die Breite 0 ist (z.B. beim allerersten Start), breche ab.
    # Das Configure-Event wird dies kurz darauf korrekt auslösen.
    if auto_width < 2 or manual_width < 2:
        return
        
    # 1. Beide Canvases leeren und die Zeitachsen neu zeichnen
    # Der manuelle Canvas erhält eine "unsichtbare" Zeitachse, um das Gitter zu zeichnen
    _draw_time_axis_and_grid(canvas_auto, auto_width)
    _draw_time_axis_and_grid(canvas_manual, manual_width)
    
    weekdays_german = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    weekday_name = weekdays_german[target_date.weekday()]
    date_label_var.set(f"{weekday_name}, {target_date.strftime('%d.%m.%Y')}")

    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    
    conn = sqlite3.connect('timeline_tracker_5min.db')
    cursor = conn.cursor()

    # --- 2. Automatische Events zeichnen (linker Canvas) ---
    cursor.execute("SELECT app_name, window_title, start_time, end_time FROM activity_events WHERE start_time >= ? AND start_time < ? ORDER BY start_time", (day_start, day_end))
    raw_events = cursor.fetchall()
    merged_events = _merge_blocks(raw_events)
    
    app_colors = {}
    colors = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]
    
    for block in merged_events:
        minutes_from_midnight = (block["start_time"].hour * 60) + block["start_time"].minute
        y_start = minutes_from_midnight * PIXELS_PER_MINUTE + Y_PADDING
        height = block["duration"] * PIXELS_PER_MINUTE
        
        duration_decimal = block["duration"] / 60.0
        if block["app"] not in app_colors:
            app_colors[block["app"]] = colors[len(app_colors) % len(colors)]
        color = app_colors[block["app"]]
        
        canvas_auto.create_rectangle(TIME_AXIS_WIDTH + 10, y_start, auto_width - 10, y_start + height, fill=color, outline=COLOR_GRID_LINE, width=1)
        
        if height > 15:
            display_text = f"{block['title'][:40]}"
            display_time = f"{duration_decimal:.2f}h"
            canvas_auto.create_text(TIME_AXIS_WIDTH + 20, y_start + 5, text=display_text, anchor="nw", font=("Segoe UI", 8, "bold"), fill="white")
            canvas_auto.create_text(auto_width - 20, y_start + 5, text=display_time, anchor="ne", font=FONT_BOLD, fill="white")

    # --- 3. Manuelle Events zeichnen (rechter Canvas) ---
    cursor.execute("SELECT start_time, end_time, description FROM manual_events WHERE start_time >= ? AND start_time < ? ORDER BY start_time", (day_start, day_end))
    manual_events = cursor.fetchall()
    conn.close()

    for event in manual_events:
        start_time, end_time, description = datetime.fromisoformat(event[0]), datetime.fromisoformat(event[1]), event[2]
        minutes_from_midnight = (start_time.hour * 60) + start_time.minute
        duration_min = (end_time - start_time).total_seconds() / 60
        y_start = minutes_from_midnight * PIXELS_PER_MINUTE + Y_PADDING
        height = duration_min * PIXELS_PER_MINUTE
        duration_decimal = duration_min / 60.0
        
        # Der manuelle Canvas hat keine Zeitachse, also startet das Rechteck bei 0
        canvas_manual.create_rectangle(TIME_AXIS_WIDTH + 10, y_start, manual_width - 10, y_start + height, fill=COLOR_MANUAL_BLOCK, outline=COLOR_GRID_LINE, width=1, activefill="#5a9bff")
        
        if height > 15:
            display_text = f"{description}"
            display_time = f"{duration_decimal:.2f}h"
            canvas_manual.create_text(TIME_AXIS_WIDTH + 20, y_start + 5, text=display_text, anchor="nw", font=FONT_BOLD, fill="white")
            canvas_manual.create_text(manual_width - 20, y_start + 5, text=display_time, anchor="ne", font=FONT_BOLD, fill="white")


    # --- 4. "Jetzt"-Linie auf beiden Canvases zeichnen ---
    if target_date == date.today():
        now = datetime.now()
        minutes_now = now.hour * 60 + now.minute
        y_pos_now = minutes_now * PIXELS_PER_MINUTE + Y_PADDING
        canvas_auto.create_line(0, y_pos_now, auto_width, y_pos_now, fill="red", width=2, tags="now_line")
        canvas_manual.create_line(0, y_pos_now, manual_width, y_pos_now, fill="red", width=2, tags="now_line")

    # --- 5. Scrollregion für beide Canvases setzen ---
    full_height = 24 * 60 * PIXELS_PER_MINUTE + Y_PADDING * 2
    canvas_auto.config(scrollregion=(0, 0, auto_width, full_height))
    canvas_manual.config(scrollregion=(0, 0, manual_width, full_height))
    
    if target_date == date.today():
        root.after(60000, lambda: draw_timeline(displayed_date))

def show_previous_day():
    global displayed_date
    displayed_date -= timedelta(days=1)
    draw_timeline(displayed_date)
    scroll_to_now()

def show_next_day():
    global displayed_date
    if displayed_date < date.today():
        displayed_date += timedelta(days=1)
        draw_timeline(displayed_date)
        scroll_to_now()

# --- 5. Drag & Drop Funktionen (angepasst für Responsivität) ---
def snap_y_to_block(y):
    """Rastet eine Y-Koordinate am Anfang des Blocks ein."""
    pixels_per_block = PIXELS_PER_MINUTE * BLOCK_DURATION_MINUTES
    relative_y = y - Y_PADDING
    snapped_relative_y = (max(0, relative_y) // pixels_per_block) * pixels_per_block
    return snapped_relative_y + Y_PADDING

def y_to_datetime(y, target_date):
    """Wandelt eine Y-Koordinate in ein datetime-Objekt um."""
    total_minutes = (y - Y_PADDING) / PIXELS_PER_MINUTE
    total_minutes = max(0, total_minutes)
    hours, minutes = int(total_minutes // 60), int(total_minutes % 60)
    return datetime.combine(target_date, datetime.min.time()).replace(hour=hours, minute=minutes)

def start_drag(event):
    """Beginnt den Drag-Vorgang."""
    y = canvas_manual.canvasy(event.y)
    drag_data["start_y"] = snap_y_to_block(y)
    
    manual_width = canvas_manual.winfo_width()
    drag_data["temp_rect"] = canvas_manual.create_rectangle(
        TIME_AXIS_WIDTH, drag_data["start_y"], manual_width, drag_data["start_y"],
        outline="white", width=2, dash=(4, 4)
    )

def drag_motion(event):
    """Aktualisiert das temporäre Rechteck während des Ziehens."""
    if drag_data["start_y"] is None: return
    
    manual_width = canvas_manual.winfo_width()
    pixels_per_block = PIXELS_PER_MINUTE * BLOCK_DURATION_MINUTES
    y = canvas_manual.canvasy(event.y)
    snapped_y = snap_y_to_block(y)
    
    y_anchor = drag_data["start_y"]
    y_top = min(y_anchor, snapped_y)
    y_bottom = max(y_anchor, snapped_y)
    
    canvas_manual.coords(drag_data["temp_rect"], TIME_AXIS_WIDTH, y_top, manual_width, y_bottom + pixels_per_block)

def end_drag(event):
    """Beendet den Drag-Vorgang und speichert den neuen Block."""
    if drag_data["start_y"] is None: return
        
    canvas_manual.delete(drag_data["temp_rect"])
    pixels_per_block = PIXELS_PER_MINUTE * BLOCK_DURATION_MINUTES
    
    y_start_raw = drag_data["start_y"]
    y_end_raw = snap_y_to_block(canvas_manual.canvasy(event.y))
    
    y_start = min(y_start_raw, y_end_raw)
    y_end = max(y_start_raw, y_end_raw) + pixels_per_block

    if y_start >= y_end - pixels_per_block:
        drag_data["start_y"] = None
        return

    start_time = y_to_datetime(y_start, displayed_date)
    end_time = y_to_datetime(y_end, displayed_date)
    
    conn = sqlite3.connect('timeline_tracker_5min.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM manual_events WHERE (start_time < ?) AND (end_time > ?)', (end_time, start_time))
    
    if cursor.fetchone():
        messagebox.showerror("Fehler", "Der neue Block überschneidet sich mit einem bestehenden Eintrag.")
    else:
        description = simpledialog.askstring("Neuer Eintrag", "Beschreibung für den Zeitblock:")
        if description and description.strip():
            cursor.execute('INSERT INTO manual_events (start_time, end_time, description) VALUES (?, ?, ?)',
                           (start_time, end_time, description.strip()))
            conn.commit()
            draw_timeline(displayed_date)
            
    conn.close()
    drag_data["start_y"], drag_data["temp_rect"] = None, None

# --- 6. Neue Funktion für responsives Verhalten ---
def on_resize(event):
    """Wird aufgerufen, wenn das Fenster in der Größe geändert wird."""
    global resize_timer
    if resize_timer:
        root.after_cancel(resize_timer)
    resize_timer = root.after(100, lambda: draw_timeline(displayed_date))

# --- 7. Haupt-UI-Setup mit Grid-Layout ---
if __name__ == "__main__":
    setup_database()
    tracking_thread = threading.Thread(target=track_activity_in_blocks, daemon=True)
    tracking_thread.start()

    root = tk.Tk()
    root.title("Timeline Tracker")
    root.geometry(f"{WINDOW_WIDTH}x700")
    root.configure(bg=COLOR_BG)
    root.bind("<Configure>", on_resize) # Event für Größenänderung binden

    style = ttk.Style(root)
    style.theme_use("clam") 
    style.configure(".", background=COLOR_BG, foreground=COLOR_FG, font=FONT_NORMAL)
    style.configure("TFrame", background=COLOR_BG)
    style.configure("TLabel", background=COLOR_BG, foreground=COLOR_FG)
    style.configure("TButton", background="#4a4a4a", foreground=COLOR_FG, borderwidth=0)
    style.map("TButton", background=[("active", "#5a5a5a")])

    # --- Obere Navigationsleiste (Datum) ---
    nav_frame = ttk.Frame(root, padding=(10, 5))
    nav_frame.pack(fill="x", side="top")
    ttk.Button(nav_frame, text="<", command=show_previous_day).pack(side="left", padx=10)
    date_label_var = tk.StringVar()
    ttk.Label(nav_frame, textvariable=date_label_var, font=FONT_HEADER, anchor="center").pack(side="left", expand=True, fill="x")
    ttk.Button(nav_frame, text=">", command=show_next_day).pack(side="right", padx=10)
    
    # --- Hauptcontainer, der das Grid-Layout steuert ---
    main_frame = ttk.Frame(root, padding=(10, 5, 10, 10))
    main_frame.pack(fill="both", expand=True)

    # --- Grid-Konfiguration für proportionale Spalten ---
    main_frame.columnconfigure(0, weight=1) 
    main_frame.columnconfigure(2, weight=1)
    # Die Zeile mit den Canvas soll den vertikalen Platz füllen
    main_frame.rowconfigure(1, weight=1)

    # --- Spaltenüberschriften ---
    auto_header_label = ttk.Label(main_frame, text="Automatisch erfasst", font=FONT_TITLE, anchor="w")
    auto_header_label.grid(row=0, column=0, sticky="w", padx=(TIME_AXIS_WIDTH, 0), pady=(5,0))
    manual_header_label = ttk.Label(main_frame, text="Manuelle Zuweisung", font=FONT_TITLE, anchor="w")
    manual_header_label.grid(row=0, column=2, sticky="w", padx=(TIME_AXIS_WIDTH, 0), pady=(5,0))

    # --- Linker Canvas für automatische Events (mit Zeitachse) ---
    canvas_auto = tk.Canvas(main_frame, bg=COLOR_CANVAS_BG, highlightthickness=0)
    canvas_auto.grid(row=1, column=0, sticky="nsew", padx=(0, GAP_WIDTH // 2))

    # --- Rechter Canvas für manuelle Events ---
    canvas_manual = tk.Canvas(main_frame, bg=COLOR_CANVAS_BG, highlightthickness=0)
    canvas_manual.grid(row=1, column=2, sticky="nsew", padx=(GAP_WIDTH // 2, 0))
    
    # --- Scrollbar, die beide Canvases steuert ---
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical")
    scrollbar.grid(row=1, column=3, sticky="ns")

    # --- Logik für synchrones Scrollen ---
    def on_scrollbar_move(*args):
        canvas_auto.yview(*args)
        canvas_manual.yview(*args)

    def on_mousewheel(event):
        if event.num == 4 or event.delta > 0:
            scroll_val = -1
        else:
            scroll_val = 1
        canvas_auto.yview_scroll(scroll_val, "units")
        canvas_manual.yview_scroll(scroll_val, "units")
        return "break" 

    scrollbar.config(command=on_scrollbar_move)
    canvas_auto.config(yscrollcommand=scrollbar.set)
    canvas_manual.config(yscrollcommand=scrollbar.set)
    
    root.bind_all("<MouseWheel>", on_mousewheel)
    root.bind_all("<Button-4>", on_mousewheel)
    root.bind_all("<Button-5>", on_mousewheel)

    # Drag & Drop Events NUR an den manuellen Canvas binden
    canvas_manual.bind("<ButtonPress-1>", start_drag)
    canvas_manual.bind("<B1-Motion>", drag_motion)
    canvas_manual.bind("<ButtonRelease-1>", end_drag)

    def scroll_to_now():
        if displayed_date == date.today():
            if canvas_auto.find_withtag("now_line"):
                bbox = canvas_auto.bbox("now_line")
                if bbox:
                    canvas_height = canvas_auto.winfo_height()
                    scrollregion_height = float(canvas_auto.cget("scrollregion").split(' ')[3])
                    if scrollregion_height > 0:
                        scroll_pos = (bbox[1] - canvas_height / 3) / scrollregion_height
                        canvas_auto.yview_moveto(max(0, scroll_pos))
                        canvas_manual.yview_moveto(max(0, scroll_pos))

    # Initiales Zeichnen und Scrollen
    root.after(100, lambda: draw_timeline(displayed_date))
    root.after(500, scroll_to_now)

    root.mainloop()