import tkinter as tk
from tkinter import ttk
import sqlite3
import pygetwindow as gw
import threading
import time
from datetime import datetime, timedelta, date

# --- Globale Konstanten ---
BLOCK_DURATION_MINUTES = 5
PIXELS_PER_MINUTE = 15

# --- Globale Variable für das Datum ---
displayed_date = date.today()

# --- 1. Datenbank-Setup ---
def setup_database():
    conn = sqlite3.connect('timeline_tracker_5min.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT,
            window_title TEXT,
            start_time DATETIME UNIQUE,
            end_time DATETIME
        )
    ''')
    conn.commit()
    conn.close()

# --- 2. 5-Minuten-Tracking-Logik ---
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
            app_name = active_window.title.split('-')[-1].strip()
            window_title = active_window.title
        else:
            app_name = "System"
            window_title = "Inaktiv / Kein Fenster"

        cursor.execute('''
            INSERT OR IGNORE INTO activity_events (app_name, window_title, start_time, end_time) 
            VALUES (?, ?, ?, ?)
        ''', (app_name, window_title, block_start_time, block_end_time))
        conn.commit()
        
        next_block_start_time = block_end_time
        sleep_duration_seconds = (next_block_start_time - datetime.now()).total_seconds()
        if sleep_duration_seconds > 0:
            time.sleep(sleep_duration_seconds + 1)

# --- 3. Logik zum Zusammenfassen von Blöcken ---
def _merge_blocks(events):
    if not events:
        return []
    merged = []
    current_app, current_title, current_start, _ = events[0]
    duration = BLOCK_DURATION_MINUTES
    for i in range(1, len(events)):
        next_app, next_title, _, _ = events[i]
        if next_app == current_app and next_title == current_title:
            duration += BLOCK_DURATION_MINUTES
        else:
            merged.append({
                "app": current_app, "title": current_title,
                "start_time": datetime.fromisoformat(current_start), "duration": duration
            })
            current_app, current_title, current_start, _ = events[i]
            duration = BLOCK_DURATION_MINUTES
    merged.append({
        "app": current_app, "title": current_title,
        "start_time": datetime.fromisoformat(current_start), "duration": duration
    })
    return merged

# --- 4. Angepasste UI-Funktionen ---
def draw_timeline(target_date):
    """Zeichnet die Timeline für ein bestimmtes Datum."""
    canvas.delete("all")
    
    weekdays_german = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    weekday_name = weekdays_german[target_date.weekday()]
    date_label_var.set(f"{weekday_name}, {target_date.strftime('%d.%m.%Y')}")

    for hour in range(24):
        for minute in range(0, 60, 5):
            y_pos = (hour * 60 + minute) * PIXELS_PER_MINUTE
            if minute == 0:
                canvas.create_line(60, y_pos, 70, y_pos, fill="black")
                canvas.create_text(55, y_pos, text=f"{hour:02d}:00", anchor="e", font=("Segoe UI", 9, "bold"))
            else:
                canvas.create_line(60, y_pos, 65, y_pos, fill="gray")
                canvas.create_text(55, y_pos, text=f"{hour:02d}:{minute:02d}", anchor="e", font=("Segoe UI", 7), fill="gray")

    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    
    conn = sqlite3.connect('timeline_tracker_5min.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT app_name, window_title, start_time, end_time FROM activity_events WHERE start_time >= ? AND start_time < ? ORDER BY start_time",
        (day_start, day_end)
    )
    raw_events = cursor.fetchall()
    conn.close()
    
    merged_events = _merge_blocks(raw_events)
    
    app_colors = {}
    colors = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]
    
    for block in merged_events:
        minutes_from_midnight = (block["start_time"].hour * 60) + block["start_time"].minute
        y_start = minutes_from_midnight * PIXELS_PER_MINUTE
        height = block["duration"] * PIXELS_PER_MINUTE

        if block["app"] not in app_colors:
            app_colors[block["app"]] = colors[len(app_colors) % len(colors)]
        color = app_colors[block["app"]]
        
        canvas.create_rectangle(75, y_start, 780, y_start + height, fill=color, outline="white", width=0.5)
        
        if height > 15:
            # Text für App und Titel (links oben)
            display_text = f"{block['app']} - {block['title'][:60]}"
            canvas.create_text(85, y_start + 5, text=display_text, anchor="nw", font=("Segoe UI", 8, "bold"), fill="white")

            # NEU: Text für die Dauer (rechts oben)
            duration_text = f"{block['duration']} min"
            canvas.create_text(775, y_start + 5, text=duration_text, anchor="ne", font=("Segoe UI", 8, "bold"), fill="white")

    canvas.config(scrollregion=canvas.bbox("all"))
    
    if target_date == date.today():
        root.after(60000, lambda: draw_timeline(displayed_date))

def show_previous_day():
    global displayed_date
    displayed_date -= timedelta(days=1)
    draw_timeline(displayed_date)

def show_next_day():
    global displayed_date
    if displayed_date < date.today():
        displayed_date += timedelta(days=1)
        draw_timeline(displayed_date)

# --- 5. Haupt-UI-Setup ---
if __name__ == "__main__":
    setup_database()
    tracking_thread = threading.Thread(target=track_activity_in_blocks, daemon=True)
    tracking_thread.start()

    root = tk.Tk()
    root.title("Timeline Tracker")
    root.geometry("850x700")

    nav_frame = tk.Frame(root, pady=5)
    nav_frame.pack(fill="x")

    prev_button = tk.Button(nav_frame, text="<", command=show_previous_day)
    prev_button.pack(side="left", padx=10)

    date_label_var = tk.StringVar()
    date_label = tk.Label(nav_frame, textvariable=date_label_var, font=("Segoe UI", 12, "bold"))
    date_label.pack(side="left", expand=True)

    next_button = tk.Button(nav_frame, text=">", command=show_next_day)
    next_button.pack(side="right", padx=10)
    
    main_frame = tk.Frame(root)
    main_frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(main_frame, bg="#f0f0f0")
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    def scroll_to_now():
        if displayed_date == date.today():
            now = datetime.now()
            minutes_today = now.hour * 60 + now.minute
            total_height = 24 * 60 * PIXELS_PER_MINUTE
            scroll_position = (minutes_today * PIXELS_PER_MINUTE - 100) / total_height
            canvas.yview_moveto(max(0, scroll_position))

    draw_timeline(displayed_date)
    root.after(500, scroll_to_now)

    root.mainloop()