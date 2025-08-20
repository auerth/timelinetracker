import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import sqlite3
import pygetwindow as gw
import threading
import time
from datetime import datetime, timedelta, date
from tkcalendar import DateEntry
import settings_manager 
import restapi_controller 
import os
# HINZUGEFÜGT: Imports für das Tray-Icon
import threading
from PIL import Image, ImageDraw
import pystray
from search_dialog import SearchDialog 
import json
# Importiere die Pfade aus deiner Konfigurationsdatei
from app_config import APP_DIR, CONFIG_PATH, DB_PATH, initialize_config


# --- (Alle globalen Konstanten und Variablen bleiben gleich) ---
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

# --- UI Layout Konstanten ---
WINDOW_WIDTH = 1000
TIME_AXIS_WIDTH = 60
GAP_WIDTH = 10 
Y_PADDING = 10

# --- Globale Variablen ---
displayed_date = date.today()
drag_data = {"start_y": None, "temp_rect": None}
resize_timer = None


def create_icon_image():
    """Erstellt programmatisch ein einfaches Icon-Bild."""
    width = 64
    height = 64
    # Erstellt ein blaues Bild mit einem weißen "T" in der Mitte
    image = Image.new('RGBA', (width, height), (58, 134, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=(255, 255, 255, 255))
    dc.rectangle((width // 3, height // 3, width * 2 // 3, height * 2 // 3), fill=(58, 134, 255, 255))
    return image

def on_closing():
    """Wird aufgerufen, wenn auf das 'X' geklickt wird. Versteckt das Fenster."""
    root.withdraw()

def show_window(icon, item):
    """Zeigt das Hauptfenster wieder an."""
    root.deiconify()
    root.lift()
    root.focus_force()

def exit_app(icon, item):
    """Beendet die Anwendung komplett."""
    global tray_icon
    if tray_icon:
        tray_icon.stop()
    root.destroy()
    
def setup_tray_icon():
    """Erstellt und startet das System-Tray-Icon in einem separaten Thread."""
    global tray_icon
    
    # Menü für das Rechtsklick-Kontextmenü definieren
    menu = pystray.Menu(
        pystray.MenuItem('Anzeigen', show_window, default=True),
        pystray.MenuItem('Beenden', exit_app)
    )
    
    # Icon-Bild erstellen
    image = create_icon_image()
    
    # Das pystray-Icon-Objekt erstellen
    tray_icon = pystray.Icon(
        "TimelineTracker", 
        image, 
        "Timeline Tracker", 
        menu
    )

    # Das Icon in einem separaten Thread ausführen, um die GUI nicht zu blockieren
    # daemon=True sorgt dafür, dass der Thread beendet wird, wenn das Hauptprogramm endet
    thread = threading.Thread(target=tray_icon.run, daemon=True)
    thread.start()

# Ersetze deine alte 'create_icon_image' Funktion hiermit:
def create_icon_image():
    """Lädt das Icon-Bild aus der Datei 'icon.png'."""
    try:
        # Pillow kann .png direkt für pystray verwenden
        return Image.open("icon.png")
    except FileNotFoundError:
        print("WARNUNG: 'icon.png' nicht gefunden. Ein Standard-Icon wird erstellt.")
        # Fallback, falls die Datei nicht gefunden wird, um einen Absturz zu verhindern
        width = 64
        height = 64
        image = Image.new('RGBA', (width, height), (58, 134, 255, 255))
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=(255, 255, 255, 255))
        dc.rectangle((width // 3, height // 3, width * 2 // 3, height * 2 // 3), fill=(58, 134, 255, 255))
        return image

def track_activity_in_blocks():
    conn = sqlite3.connect(DB_PATH)
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

# --- (Zeichenfunktionen _draw_time_axis_and_grid etc. unverändert) ---
def _draw_time_axis_and_grid(canvas, width):
    canvas.delete("all")
    for hour in range(24):
        y_pos_hour = (hour * 60) * PIXELS_PER_MINUTE + Y_PADDING
        canvas.create_line(TIME_AXIS_WIDTH, y_pos_hour, width, y_pos_hour, fill=COLOR_HOUR_LINE, width=1)
        canvas.create_text(TIME_AXIS_WIDTH - 5, y_pos_hour, text=f"{hour:02d}:00", anchor="e", font=FONT_BOLD, fill=COLOR_FG)
        for minute in range(5, 60, 5):
            y_pos = y_pos_hour + (minute * PIXELS_PER_MINUTE)
            canvas.create_line(TIME_AXIS_WIDTH + 5, y_pos, width, y_pos, fill=COLOR_GRID_LINE, dash=(2, 4))
            canvas.create_text(
                TIME_AXIS_WIDTH - 5, y_pos, text=f"{hour:02d}:{minute:02d}", 
                anchor="e", font=("Segoe UI", 7), fill="gray"
            )

# --- Funktion draw_timeline GEÄNDERT ---
def draw_timeline(target_date):
    auto_width = canvas_auto.winfo_width()
    manual_width = canvas_manual.winfo_width()
    if auto_width < 2 or manual_width < 2: return
    _draw_time_axis_and_grid(canvas_auto, auto_width)
    _draw_time_axis_and_grid(canvas_manual, manual_width)
    
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
        if block["app"] not in app_colors: app_colors[block["app"]] = colors[len(app_colors) % len(colors)]
        color = app_colors[block["app"]]
        canvas_auto.create_rectangle(TIME_AXIS_WIDTH + 10, y_start, auto_width - 10, y_start + height, fill=color, outline=COLOR_GRID_LINE, width=1)
        if height > 15:
            display_text = f"{block['title'][:40]}"
            display_time = f"{duration_decimal:.2f}h"
            canvas_auto.create_text(TIME_AXIS_WIDTH + 20, y_start + 5, text=display_text, anchor="nw", font=("Segoe UI", 8, "bold"), fill="white")
            canvas_auto.create_text(auto_width - 20, y_start + 5, text=display_time, anchor="ne", font=FONT_BOLD, fill="white")

    # GEÄNDERT: 'id' wird jetzt auch aus der Datenbank geholt
    cursor.execute("SELECT id, start_time, end_time, description, comment, externalId FROM manual_events WHERE start_time >= ? AND start_time < ? ORDER BY start_time", (day_start, day_end))
    manual_events = cursor.fetchall()
    conn.close()
    text_font = font.Font(font=FONT_BOLD)

    for event in manual_events:
        # GEÄNDERT: event_id wird aus dem Tupel extrahiert
        event_id, start_time_str, end_time_str, description,comment,externalId = event
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
        
        minutes_from_midnight = (start_time.hour * 60) + start_time.minute
        duration_min = (end_time - start_time).total_seconds() / 60
        y_start = minutes_from_midnight * PIXELS_PER_MINUTE + Y_PADDING
        height = duration_min * PIXELS_PER_MINUTE
        duration_decimal = duration_min / 60.0

        # GEÄNDERT: Dem Rechteck wird ein Tag mit der ID hinzugefügt
        tag_id = f"manual_event_{event_id}"
        canvas_manual.create_rectangle(
            TIME_AXIS_WIDTH + 10, y_start, manual_width - 10, y_start + height, 
            fill=COLOR_MANUAL_BLOCK, outline=COLOR_GRID_LINE, width=1, 
            activefill="#5a9bff", tags=(tag_id,)
        )
        if height > 30: # Evtl. den Mindestwert etwas erhöhen, damit Text Platz hat
            # 1. Zeichne die obere Zeile (Beschreibung und Zeit)
            y_top_line = y_start + 5
            display_text = f"{description}"
            display_time = f"{duration_decimal:.2f}h"
            
            canvas_manual.create_text(
                TIME_AXIS_WIDTH + 20, y_top_line, 
                text=display_text, anchor="nw", font=FONT_BOLD, fill="white", tags=(tag_id,)
            )
            canvas_manual.create_text(
                manual_width - 20, y_top_line, 
                text=display_time, anchor="ne", font=FONT_BOLD, fill="white", tags=(tag_id,)
            )

            # 2. Berechne die Position für den Kommentar dynamisch
            line_height = text_font.metrics('linespace') # Höhe einer Textzeile
            # Startposition ist unter der ersten Zeile plus ein kleiner Abstand
            y_comment_start = y_top_line + line_height + 5 
            
            # Die x-Position soll die Mitte des Blocks sein
            x_comment_left = TIME_AXIS_WIDTH + 20 # GEÄNDERT
            
            max_text_width = manual_width - 100 # Etwas mehr Rand lassen
            max_y_coordinate = y_start + height - 5 # Sicherstellen, dass Text nicht am Rand klebt

            # 3. Zeichne den Kommentar mit der neuen Position und den Korrekturen
            # Nur wenn ein Kommentar vorhanden ist
            if comment and comment.strip():
                draw_wrapped_and_truncated_text(
                    canvas=canvas_manual,
                    x=x_comment_left,
                    y=y_comment_start,
                    text=comment,
                    max_width=max_text_width,
                    max_bottom_y=max_y_coordinate,
                    anchor="nw",                  # GEÄNDERT: Anker auf "nw" (oben-links)
                    justify="left",               # GEÄNDERT: Textzeilen linksbündig
                    font=FONT_BOLD,
                    fill="white",
                    tags=(tag_id,)
                )

    
    if target_date == date.today():
        now = datetime.now()
        minutes_now = now.hour * 60 + now.minute
        y_pos_now = minutes_now * PIXELS_PER_MINUTE + Y_PADDING
        canvas_auto.create_line(0, y_pos_now, auto_width, y_pos_now, fill="red", width=2, tags="now_line")
        canvas_manual.create_line(0, y_pos_now, manual_width, y_pos_now, fill="red", width=2, tags="now_line")
    
    full_height = 24 * 60 * PIXELS_PER_MINUTE + Y_PADDING * 2
    canvas_auto.config(scrollregion=(0, 0, auto_width, full_height))
    canvas_manual.config(scrollregion=(0, 0, manual_width, full_height))
    
    if target_date == date.today():
        root.after(60000, lambda: draw_timeline(displayed_date))
        
import tkinter as tk
from tkinter import font

def draw_wrapped_and_truncated_text(canvas, x, y, text, max_width, max_bottom_y, **kwargs):
    """
    Zeichnet Text auf einen Canvas, der automatisch umgebrochen und bei
    Bedarf mit '...' gekürzt wird, um eine maximale Höhe nicht zu überschreiten.

    Args:
        canvas: Das tkinter.Canvas-Objekt.
        x (int): Die x-Koordinate für den Textanker.
        y (int): Die y-Koordinate für den Textanker.
        text (str): Der zu zeichnende Text.
        max_width (int): Die maximale Breite, die der Text haben darf, bevor er umbricht.
        max_bottom_y (int): Die absolute y-Koordinate, die der untere Rand des Textes nicht überschreiten darf.
        **kwargs: Weitere Argumente für canvas.create_text (z.B. font, fill, anchor, tags).
    """
    temp_text = text

    while True:
        # Erstelle das Textobjekt mit der aktuellen Textversion und der maximalen Breite
        item_id = canvas.create_text(x, y, text=temp_text, width=max_width, **kwargs)
        
        # Hol dir die Bounding Box des erstellten Textobjekts
        bbox = canvas.bbox(item_id)
        
        # Wenn keine Bounding Box vorhanden ist (z.B. leerer Text), abbrechen
        if not bbox:
            canvas.delete(item_id)
            return None # Gibt nichts zurück, wenn nichts gezeichnet werden kann

        # Prüfe, ob der untere Rand des Textes (y2) innerhalb der erlaubten Höhe liegt
        bottom_y = bbox[3]
        if bottom_y <= max_bottom_y:
            # Der Text passt, wir sind fertig und geben die ID des Objekts zurück
            return item_id

        # Der Text ist zu hoch, also löschen wir ihn und versuchen es mit einer kürzeren Version
        canvas.delete(item_id)

        # Wenn der Text schon gekürzt wurde, entfernen wir die letzten 4 Zeichen ("...")
        # und versuchen es erneut.
        if temp_text.endswith("..."):
            temp_text = temp_text[:-4]

        # Finde das letzte Leerzeichen, um sauber am Wortende zu kürzen
        last_space = temp_text.rfind(' ')
        if last_space != -1:
            # Kürze den Text bis zum letzten Wort
            temp_text = temp_text[:last_space]
        else:
            # Kein Leerzeichen gefunden, kürze den Text einfach um ein paar Zeichen
            temp_text = temp_text[:-5]

        # Wenn der Text leer wird, können wir nichts mehr kürzen. Schleife beenden.
        if not temp_text:
            # Optional: Zeichne nur die Auslassungspunkte, wenn gar nichts passt
            return canvas.create_text(x, y, text="...", width=max_width, **kwargs)

        # Hänge die Auslassungspunkte an den gekürzten Text an
        temp_text += "..."

# --- (Navigations- und Drag&Drop-Funktionen unverändert) ---
def show_previous_day():
    global displayed_date
    displayed_date -= timedelta(days=1)
    date_entry.set_date(displayed_date)
    draw_timeline(displayed_date)
    scroll_to_now()

def show_next_day():
    global displayed_date
    if displayed_date < date.today():
        displayed_date += timedelta(days=1)
        date_entry.set_date(displayed_date)
        draw_timeline(displayed_date)
        scroll_to_now()
        
def show_today():
    """Springt direkt zur heutigen Tagesansicht."""
    global displayed_date
    today = date.today()
    
    # Nur aktualisieren, wenn nicht bereits der heutige Tag angezeigt wird
    if displayed_date != today:
        displayed_date = today
        date_entry.set_date(displayed_date)  # Das Kalender-Widget aktualisieren
        draw_timeline(displayed_date)       # Die Zeitleiste für heute neu zeichnen
        scroll_to_now()                     # Zur aktuellen Uhrzeit scrollen

def snap_y_to_block(y):
    pixels_per_block = PIXELS_PER_MINUTE * BLOCK_DURATION_MINUTES
    relative_y = y - Y_PADDING
    snapped_relative_y = (max(0, relative_y) // pixels_per_block) * pixels_per_block
    return snapped_relative_y + Y_PADDING

def y_to_datetime(y, target_date):
    total_minutes = (y - Y_PADDING) / PIXELS_PER_MINUTE
    total_minutes = max(0, total_minutes)
    hours, minutes = int(total_minutes // 60), int(total_minutes % 60)
    return datetime.combine(target_date, datetime.min.time()).replace(hour=hours, minute=minutes)

def start_drag(event):
    y = canvas_manual.canvasy(event.y)
    drag_data["start_y"] = snap_y_to_block(y)
    manual_width = canvas_manual.winfo_width()
    drag_data["temp_rect"] = canvas_manual.create_rectangle(
        TIME_AXIS_WIDTH, drag_data["start_y"], manual_width, drag_data["start_y"],
        outline="white", width=2, dash=(4, 4)
    )

def drag_motion(event):
    if drag_data["start_y"] is None: return
    manual_width = canvas_manual.winfo_width()
    pixels_per_block = PIXELS_PER_MINUTE * BLOCK_DURATION_MINUTES
    y = canvas_manual.canvasy(event.y)
    snapped_y = snap_y_to_block(y)
    y_anchor = drag_data["start_y"]
    y_top = min(y_anchor, snapped_y)
    y_bottom = max(y_anchor, snapped_y)
    canvas_manual.coords(drag_data["temp_rect"], TIME_AXIS_WIDTH, y_top, manual_width, y_bottom + pixels_per_block)

# Ersetze die komplette 'end_drag' Funktion in deiner Hauptdatei
def end_drag(event):
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
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM manual_events WHERE (start_time < ?) AND (end_time > ?)', (end_time, start_time))
    
    if cursor.fetchone():
        messagebox.showerror("Error", "The new block overlaps with an existing entry.")
        conn.close()
    else:
        conn.close()
        
        # CORRECTION: Correctly call the SearchDialog with all required arguments
        color_config = {
            'canvas_bg': COLOR_CANVAS_BG,
            'fg': COLOR_FG,
            'manual_block': COLOR_MANUAL_BLOCK
        }
        dialog = SearchDialog(root, title="Aufgabe zuweisen", colors=color_config)
        selected_task = dialog.result['task']
        comment = dialog.result['comment']
        if selected_task and selected_task.get("id"):
            description = f"[#{selected_task['id']}] {selected_task['display']}"
           
            # ----------------- ANFANG: API-AUFRUF -----------------
            try:
                # 1. API-Controller initialisieren
                api_controller = restapi_controller.ApiController()

                # 2. Dauer in Dezimalstunden umrechnen
                duration = end_time - start_time
                time_in_hours = duration.total_seconds() / 3600.0

                # 3. API-Aufruf durchführen
                response = api_controller.log_time(
                    issue_id=selected_task['id'],
                    time_decimal=time_in_hours,
                    comment=comment
                )


                if response and 'id' in response:
                    # Erfolgreich! Speichere die externe ID in der lokalen DB
                    remote_time_entry_id = response['id']
                    
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO manual_events (start_time, end_time, description,externalId,comment,time_entry_id ) VALUES (?, ?, ?, ?, ?,?)',
                                (start_time, end_time, description,selected_task['id'],comment,remote_time_entry_id))
                    conn.commit()
                    conn.close()
                    
                elif response and 'error' in response:
                    # API hat einen Fehler gemeldet
                    messagebox.showerror(
                        "API Fehler",
                        f"Der lokale Eintrag wurde erstellt, aber die Zeit konnte nicht im externen System erfasst werden:\n\n{response['error']}"
                    )
            except (FileNotFoundError, json.JSONDecodeError) as e:
                messagebox.showerror("Konfigurationsfehler", f"API-Konfiguration konnte nicht geladen werden: {e}")
            except Exception as e:
                # Fängt andere unerwartete Fehler ab (z.B. Netzwerkprobleme)
                messagebox.showerror("Unerwarteter Fehler", f"Ein Fehler bei der API-Kommunikation ist aufgetreten: {e}")
            draw_timeline(displayed_date)
        
    drag_data["start_y"], drag_data["temp_rect"] = None, None
    
def delete_manual_event(event_db_id):
    """
    Löscht einen manuellen Zeiteintrag. Behandelt 404-Fehler von der API als "bereits gelöscht".
    """
    if not messagebox.askyesno("Löschen bestätigen", 
                               "Möchten Sie diesen Zeiteintrag wirklich endgültig löschen?"):
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT time_entry_id FROM manual_events WHERE id = ?", (event_db_id,))
        result = cursor.fetchone()

        if not result:
            messagebox.showerror("Fehler", "Der zu löschende Eintrag wurde nicht in der Datenbank gefunden.")
            return

        time_entry_id = result[0]

        if time_entry_id:
            try:
                api_controller = restapi_controller.ApiController()
                response = api_controller.delete_time_entry(time_entry_id=time_entry_id)
                
                if response and 'error' in response:
                    # NEU: Spezielle Behandlung für 404-Fehler
                    if "404" in response['error']:
                        messagebox.showinfo(
                            "Hinweis",
                            "Dieser Eintrag existiert im externen System nicht mehr.\n\n"
                            "Der lokale Eintrag wird jetzt entfernt."
                        )
                        # Wichtig: KEIN "return" hier, damit der lokale Eintrag gelöscht wird.
                    else:
                        # Für alle ANDEREN Fehler wird der Vorgang abgebrochen
                        messagebox.showerror(
                            "API Fehler",
                            f"Der Eintrag konnte im externen System nicht gelöscht werden:\n\n{response['error']}"
                        )
                        return # Lokalen Eintrag bei schwerwiegenden Fehlern NICHT löschen
            except Exception as e:
                messagebox.showerror("API Kommunikationsfehler", f"Fehler beim Löschen des externen Eintrags: {e}")
                return

        # Dieser Teil wird jetzt auch nach einem 404-Fehler erreicht
        cursor.execute("DELETE FROM manual_events WHERE id = ?", (event_db_id,))
        conn.commit()
        
    except sqlite3.Error as e:
        messagebox.showerror("Datenbankfehler", f"Ein Fehler ist aufgetreten: {e}")
    finally:
        if conn:
            conn.close()

    draw_timeline(displayed_date)

def show_context_menu(event):
    """Findet das Element direkt unter dem Mauszeiger und zeigt ein Kontextmenü an."""
    # Verwende find_withtag("current"), um das Element direkt unter dem Cursor zu finden.
    # Dies ist zuverlässiger als find_closest.
    canvas_item_tuple = canvas_manual.find_withtag("current")
    
    # "current" gibt ein Tupel zurück. Wenn es leer ist, war der Klick im leeren Raum.
    if not canvas_item_tuple:
        return

    # Hole die Tags des ersten gefundenen Elements
    item_id = canvas_item_tuple[0]
    item_tags = canvas_manual.gettags(item_id)
    
    event_db_id = None
    for tag in item_tags:
        # Suche nach unserem benutzerdefinierten Tag-Format
        if tag.startswith("manual_event_"):
            try:
                # Extrahiere die ID aus dem Tag-String 'manual_event_ID'
                event_db_id = int(tag.split('_')[2])
                break # Wir haben die ID gefunden, Schleife abbrechen
            except (ValueError, IndexError):
                # Falls der Tag unerwartet formatiert ist, fahre fort
                continue
    
    # Wenn eine gültige ID aus den Tags extrahiert wurde, zeige das Menü an
    if event_db_id is not None:
        context_menu = tk.Menu(root, tearoff=0, bg=COLOR_BG, fg=COLOR_FG, 
                               activebackground=COLOR_MANUAL_BLOCK, activeforeground="white")
        context_menu.add_command(
            label="Löschen", 
            command=lambda: delete_manual_event(event_db_id)
        )
        # Zeige das Menü an der globalen Bildschirmposition des Mauszeigers
        context_menu.tk_popup(event.x_root, event.y_root)

def on_resize(event):
    global resize_timer
    if resize_timer:
        root.after_cancel(resize_timer)
    resize_timer = root.after(100, lambda: draw_timeline(displayed_date))

def on_date_selected(event):
    global displayed_date
    new_date = event.widget.get_date()
    if new_date != displayed_date:
        displayed_date = new_date
        draw_timeline(displayed_date)
        scroll_to_now()

def open_settings_dialog():
    # --- INNERE FUNKTIONEN FÜR DIE BUTTONS ---
    def save_and_close():
        try:
            settings_manager.set_autostart(autostart_var.get())
        except Exception as e:
            messagebox.showerror("Fehler", f"Autostart konnte nicht geändert werden:\n{e}", parent=settings_window)

        messagebox.showinfo("Gespeichert", "Einstellungen wurden erfolgreich gespeichert.", parent=settings_window)
        settings_window.destroy()

    def open_app_directory():
        """Öffnet den Roaming-Ordner der Anwendung im Explorer."""
        try:
            # os.startfile() ist der direkteste Weg unter Windows
            os.startfile(APP_DIR)
        except Exception as e:
            messagebox.showerror("Fehler", f"Verzeichnis konnte nicht geöffnet werden:\n{e}", parent=settings_window)

    def open_config_file():
        """Öffnet die Konfigurationsdatei mit dem Standard-Editor."""
        try:
            os.startfile(CONFIG_PATH)
        except Exception as e:
            messagebox.showerror("Fehler", f"Konfigurationsdatei konnte nicht geöffnet werden:\n{e}", parent=settings_window)

    def delete_database():
        """Löscht die lokale Datenbank nach einer Bestätigungsabfrage."""
        if messagebox.askyesno("Datenbank wirklich löschen?",
                               "Sind Sie sicher? Alle lokal gespeicherten Zeiteinträge werden unwiderruflich gelöscht. "
                               "Die Anwendung muss danach neu gestartet werden.",
                               parent=settings_window):
            try:
                # Wichtig: Hier sollte idealerweise die DB-Verbindung geschlossen werden.
                # Die einfachste und sicherste Methode ist, die App danach zu beenden.
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                    messagebox.showinfo("Erfolg", "Die Datenbank wurde gelöscht. Die Anwendung wird jetzt beendet.", parent=settings_window)
                    root.destroy() # Beendet die Hauptanwendung
                else:
                    messagebox.showinfo("Hinweis", "Die Datenbank existiert bereits nicht mehr.", parent=settings_window)
            except Exception as e:
                messagebox.showerror("Fehler", f"Datenbank konnte nicht gelöscht werden:\n{e}", parent=settings_window)

    # --- FENSTER-SETUP ---
    settings_window = tk.Toplevel(root)
    settings_window.title("Einstellungen")
    settings_window.resizable(False, False)
    settings_window.transient(root)
    settings_window.grab_set()
    
    # Fensterhöhe anpassen für die neuen Buttons
    win_width = 400
    win_height = 350 # Erhöht für den neuen Bereich

    # (Code zum Zentrieren des Fensters bleibt unverändert)
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_width = root.winfo_width()
    root_height = root.winfo_height()
    pos_x = root_x + (root_width // 2) - (win_width // 2)
    pos_y = root_y + (root_height // 2) - (win_height // 2)
    settings_window.geometry(f'{win_width}x{win_height}+{pos_x}+{pos_y}')
    settings_window.configure(bg=COLOR_BG)
    
    frame = ttk.Frame(settings_window, padding=20)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)

    # --- VARIABLEN ---
    autostart_var = tk.BooleanVar(value=settings_manager.is_autostart_enabled())

    # --- WIDGETS ---
    autostart_check = ttk.Checkbutton(frame, text="Automatisch mit Windows starten", variable=autostart_var)
    autostart_check.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))
    
    # --- NEU: WARTUNGS-BEREICH ---
    maintenance_frame = ttk.LabelFrame(frame, text="Wartung & Fehlerbehebung", padding=10)
    maintenance_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
    maintenance_frame.columnconfigure(0, weight=1) # Buttons zentrieren

    btn_open_dir = ttk.Button(maintenance_frame, text="Daten-Ordner öffnen", command=open_app_directory)
    btn_open_dir.pack(fill='x', pady=2)
    
    btn_open_config = ttk.Button(maintenance_frame, text="Konfigurationsdatei bearbeiten", command=open_config_file)
    btn_open_config.pack(fill='x', pady=2)

    btn_delete_db = ttk.Button(maintenance_frame, text="Lokale Datenbank löschen...", command=delete_database)
    btn_delete_db.pack(fill='x', pady=(2, 0))
    
    # --- SPEICHERN/ABBRECHEN BUTTONS ---
    button_frame = ttk.Frame(frame)
    button_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0))
    
    ttk.Button(button_frame, text="Speichern", command=save_and_close).pack(side="left", padx=10)
    ttk.Button(button_frame, text="Abbrechen", command=settings_window.destroy).pack(side="left")


# --- Haupt-UI-Setup ---
if __name__ == "__main__":
    initialize_config()
    settings_manager.setup_database() 
    tracking_thread = threading.Thread(target=track_activity_in_blocks, daemon=True)
    tracking_thread.start()
    root = tk.Tk()
    root.title("Timeline Tracker")
    root.geometry(f"{WINDOW_WIDTH}x700")
    root.configure(bg=COLOR_BG)
    root.bind("<Configure>", on_resize)
    root.protocol("WM_DELETE_WINDOW", on_closing)
    # HINZUGEFÜGT: Setzt das Icon für die Titelleiste und die Taskleiste
    try:
        root.iconbitmap("icon.ico")
    except tk.TclError:
        print("WARNUNG: 'icon.ico' nicht gefunden oder ungültig.")
    style = ttk.Style(root)
    style.theme_use("clam") 
    style.configure(".", background=COLOR_BG, foreground=COLOR_FG, font=FONT_NORMAL)
    style.configure("TFrame", background=COLOR_BG)
    style.configure("TLabel", background=COLOR_BG, foreground=COLOR_FG)
    style.configure("TButton", background="#4a4a4a", foreground=COLOR_FG, borderwidth=0)
    style.map("TButton", background=[("active", "#5a5a5a")])
    style.configure('my.DateEntry',
                      fieldbackground=COLOR_BG,
                      background=COLOR_BG,
                      foreground=COLOR_FG,
                      arrowcolor=COLOR_FG,
                      bordercolor=COLOR_GRID_LINE)

    nav_frame = ttk.Frame(root, padding=(10, 5))
    nav_frame.pack(fill="x", side="top")
    
    ttk.Button(nav_frame, text="<", command=show_previous_day).pack(side="left", padx=5)
    
    date_entry = DateEntry(nav_frame,
                           width=16,
                           font=FONT_HEADER,
                           date_pattern='dd.mm.yyyy',
                           style='my.DateEntry',
                           borderwidth=0)
    date_entry.pack(side="left", expand=True, fill="x", padx=10)
    date_entry.bind("<<DateEntrySelected>>", on_date_selected)
    
    ttk.Button(nav_frame, text=">", command=show_next_day).pack(side="left", padx=5)
    ttk.Button(nav_frame, text="Heute", command=show_today).pack(side="left", padx=5)

    settings_button = ttk.Button(nav_frame, text="⚙️", command=open_settings_dialog, width=3)
    settings_button.pack(side="right", padx=10)
    
    main_frame = ttk.Frame(root, padding=(10, 5, 10, 10))
    main_frame.pack(fill="both", expand=True)
    main_frame.columnconfigure(0, weight=1) 
    main_frame.columnconfigure(2, weight=1)
    main_frame.rowconfigure(1, weight=1)

    auto_header_label = ttk.Label(main_frame, text="Automatisch erfasst", font=FONT_TITLE, anchor="w")
    auto_header_label.grid(row=0, column=0, sticky="w", padx=(TIME_AXIS_WIDTH, 0), pady=(5,0))
    manual_header_label = ttk.Label(main_frame, text="Manuelle Zuweisung", font=FONT_TITLE, anchor="w")
    manual_header_label.grid(row=0, column=2, sticky="w", padx=(TIME_AXIS_WIDTH, 0), pady=(5,0))

    canvas_auto = tk.Canvas(main_frame, bg=COLOR_CANVAS_BG, highlightthickness=0)
    canvas_auto.grid(row=1, column=0, sticky="nsew", padx=(0, GAP_WIDTH // 2))
    canvas_manual = tk.Canvas(main_frame, bg=COLOR_CANVAS_BG, highlightthickness=0)
    canvas_manual.grid(row=1, column=2, sticky="nsew", padx=(GAP_WIDTH // 2, 0))

    scrollbar = ttk.Scrollbar(main_frame, orient="vertical")
    scrollbar.grid(row=1, column=3, sticky="ns")

    def on_scrollbar_move(*args):
        canvas_auto.yview(*args)
        canvas_manual.yview(*args)
    def on_mousewheel(event):
        scroll_val = -1 if event.num == 4 or event.delta > 0 else 1
        canvas_auto.yview_scroll(scroll_val, "units")
        canvas_manual.yview_scroll(scroll_val, "units")
        return "break" 
    
    scrollbar.config(command=on_scrollbar_move)
    canvas_auto.config(yscrollcommand=scrollbar.set)
    canvas_manual.config(yscrollcommand=scrollbar.set)
    root.bind_all("<MouseWheel>", on_mousewheel)
    root.bind_all("<Button-4>", on_mousewheel)
    root.bind_all("<Button-5>", on_mousewheel)

    # Event-Bindings für Drag & Drop (Linksklick)
    canvas_manual.bind("<ButtonPress-1>", start_drag)
    canvas_manual.bind("<B1-Motion>", drag_motion)
    canvas_manual.bind("<ButtonRelease-1>", end_drag)

    # HINZUGEFÜGT: Event-Binding für das Kontextmenü (Rechtsklick)
    canvas_manual.bind("<Button-3>", show_context_menu)

    def scroll_to_now():
        if displayed_date == date.today() and canvas_auto.find_withtag("now_line"):
            bbox = canvas_auto.bbox("now_line")
            if bbox:
                canvas_height = canvas_auto.winfo_height()
                scrollregion_height = float(canvas_auto.cget("scrollregion").split(' ')[3])
                if scrollregion_height > 0:
                    scroll_pos = (bbox[1] - canvas_height / 3) / scrollregion_height
                    canvas_auto.yview_moveto(max(0, scroll_pos))
                    canvas_manual.yview_moveto(max(0, scroll_pos))
    # HINZUGEFÜGT: Das Tray-Icon wird vor dem Start der mainloop eingerichtet
    setup_tray_icon()
    root.after(100, lambda: draw_timeline(displayed_date))
    root.after(500, scroll_to_now)

    root.mainloop()
    
    
    
    