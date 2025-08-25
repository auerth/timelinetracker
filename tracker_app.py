import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, font
import sqlite3
import pygetwindow as gw
import threading
import time
from datetime import datetime, timedelta, date
from tkcalendar import DateEntry
import settings_manager
import restapi_controller
import os
import threading
from PIL import Image, ImageDraw, ImageTk
import pystray
from search_dialog import SearchDialog
import json
import socket
import sys

# Geänderte/Neue Imports
import psutil
import win32gui
import win32process
import win32con
import win32api
import win32ui # NEU

# Importiere die Pfade aus deiner Konfigurationsdatei
from app_config import APP_DIR, CONFIG_PATH, DB_PATH, initialize_config
from settings_dialog import SettingsDialog

# --- Globale Konstanten ---
SINGLE_INSTANCE_PORT = 38765
FOCUS_MESSAGE = b"focus"
BLOCK_DURATION_MINUTES = 5
PIXELS_PER_MINUTE = 5
COLOR_BG = "#2e2e2e"
COLOR_CANVAS_BG = "#3a3a3a"
COLOR_FG = "#d0d0d0"
COLOR_GRID_LINE = "#4a4a4a"
COLOR_HOUR_LINE = "#888888"
COLOR_MANUAL_BLOCK = "#f18557"
COLOR_MANUAL_BLOCK_ACTIVE = "#f7ae67"
FONT_NORMAL = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_HEADER = ("Segoe UI", 14, "bold")
WINDOW_WIDTH = 1000
TIME_AXIS_WIDTH = 60
GAP_WIDTH = 10
Y_PADDING = 10
ICON_CACHE_DIR = os.path.join(APP_DIR, 'icons')


# --- Globale Hilfsfunktionen ---
def create_icon_image():
    """Lädt das Icon-Bild aus der Datei 'icon.png' oder erstellt ein Fallback."""
    try:
        return Image.open("icon.png")
    except FileNotFoundError:
        print("WARNUNG: 'icon.png' nicht gefunden. Ein Standard-Icon wird erstellt.")
        width, height = 64, 64
        image = Image.new('RGBA', (width, height), (58, 134, 255, 255))
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=(255, 255, 255, 255))
        dc.rectangle((width // 3, height // 3, width * 2 // 3, height * 2 // 3), fill=(58, 134, 255, 255))
        return image

# ### KORRIGIERTE ICON-EXTRAKTION ###
def track_activity_in_blocks():
    """Hintergrund-Thread, der die Fensteraktivität aufzeichnet und Icons extrahiert."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    while True:
        now = datetime.now()
        minutes_into_hour = now.minute
        start_minute = minutes_into_hour - (minutes_into_hour % BLOCK_DURATION_MINUTES)
        block_start_time = now.replace(minute=start_minute, second=0, microsecond=0)
        block_end_time = block_start_time + timedelta(minutes=BLOCK_DURATION_MINUTES)
        
        app_name, window_title, exe_path = "System", "Inaktiv / Kein Fenster", None
        
        try:
            active_window = gw.getActiveWindow()
            if active_window and active_window.title:
                hwnd = active_window._hWnd
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(pid)
                exe_path = process.exe()
                app_name = os.path.basename(exe_path)
                window_title = active_window.title

                icon_path = os.path.join(ICON_CACHE_DIR, f"{app_name}.png")
                if not os.path.exists(icon_path):
                    try:
                        large, small = win32gui.ExtractIconEx(exe_path, 0)
                        if large:
                            h_icon = large[0]
                            
                            # --- START DER KORREKTUR ---
                            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                            hbmp = win32ui.CreateBitmap()
                            hbmp.CreateCompatibleBitmap(hdc, 32, 32)
                            hdc_dest = hdc.CreateCompatibleDC()
                            hdc_dest.SelectObject(hbmp)
                            
                            hdc_dest.DrawIcon((0, 0), h_icon)
                            
                            bmp_str = hbmp.GetBitmapBits(True)
                            
                            img = Image.frombuffer('RGBA', (32, 32), bmp_str, 'raw', 'BGRA', 0, 1)
                            img.save(icon_path)

                            # Resourcen freigeben
                            win32gui.DestroyIcon(h_icon)
                            hdc.DeleteDC()
                            hdc_dest.DeleteDC()
                            win32gui.ReleaseDC(0, win32gui.GetDC(0))
                            # --- ENDE DER KORREKTUR ---

                    except Exception as e:
                        print(f"Icon für {app_name} konnte nicht extrahiert werden: {e}")

        except (psutil.NoSuchProcess, psutil.AccessDenied, gw.PyGetWindowException):
            active_window = gw.getActiveWindow()
            if active_window and active_window.title:
                 title_parts = active_window.title.split('-')
                 app_name = title_parts[-1].strip() if len(title_parts) > 1 else title_parts[0].strip()
                 window_title = active_window.title
            else:
                app_name, window_title = "System", "Inaktiv / Kein Fenster"
            exe_path = None
        except Exception as e:
            print(f"Ein unerwarteter Fehler beim Tracking ist aufgetreten: {e}")

        cursor.execute(
            'INSERT OR IGNORE INTO activity_events (app_name, window_title, start_time, end_time, exe_path) VALUES (?, ?, ?, ?, ?)',
            (app_name, window_title, block_start_time, block_end_time, exe_path)
        )
        conn.commit()
        
        sleep_duration_seconds = (block_end_time - datetime.now()).total_seconds()
        if sleep_duration_seconds > 0:
            time.sleep(sleep_duration_seconds + 1)


def draw_wrapped_and_truncated_text(canvas, x, y, text, max_width, max_bottom_y, **kwargs):
    """Zeichnet Text mit automatischem Umbruch und Kürzung."""
    temp_text = text
    while True:
        item_id = canvas.create_text(x, y, text=temp_text, width=max_width, **kwargs)
        bbox = canvas.bbox(item_id)
        if not bbox:
            canvas.delete(item_id)
            return None
        if bbox[3] <= max_bottom_y:
            return item_id
        canvas.delete(item_id)
        if temp_text.endswith("..."):
            temp_text = temp_text[:-4]
        last_space = temp_text.rfind(' ')
        if last_space != -1:
            temp_text = temp_text[:last_space]
        else:
            temp_text = temp_text[:-5]
        if not temp_text:
            return canvas.create_text(x, y, text="...", width=max_width, **kwargs)
        temp_text += "..."

class TimelineTrackerApp:
    def __init__(self):
        self.root = None
        self.canvas_auto = None
        self.canvas_manual = None
        self.date_entry = None
        self.tray_icon = None
        self.resize_timer = None
        self.server_socket = None
        self.server_thread = None
        self.displayed_date = date.today()
        self.drag_data = {"start_y": None, "temp_rect": None}
        self.is_first_instance = False
        self.icon_cache = {} 
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(("localhost", SINGLE_INSTANCE_PORT))
            self.server_socket.listen(1)
            self.is_first_instance = True
        except OSError:
            self.is_first_instance = False

    def on_closing(self):
        self.root.withdraw()

    def show_window(self, icon, item):
        self._focus_window()

    def exit_app(self, icon, item):
        if self.tray_icon:
            self.tray_icon.stop()
        if self.server_socket:
            self.server_socket.close()
        self.root.destroy()
        sys.exit(0)

    def setup_tray_icon(self):
        menu = pystray.Menu(
            pystray.MenuItem('Anzeigen', self.show_window, default=True),
            pystray.MenuItem('Beenden', self.exit_app)
        )
        image = create_icon_image()
        self.tray_icon = pystray.Icon("TimelineTracker", image, "Timeline Tracker", menu)
        thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        thread.start()

    def _focus_window(self):
        if self.root:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

    def _run_server(self):
        while True:
            try:
                conn, addr = self.server_socket.accept()
                with conn:
                    if conn.recv(1024) == FOCUS_MESSAGE:
                        self.root.after(0, self._focus_window)
            except OSError:
                break

    def _draw_time_axis_and_grid(self, canvas, width):
        canvas.delete("all")
        for hour in range(24):
            y_pos_hour = (hour * 60) * PIXELS_PER_MINUTE + Y_PADDING
            canvas.create_line(TIME_AXIS_WIDTH, y_pos_hour, width, y_pos_hour, fill=COLOR_HOUR_LINE, width=1)
            canvas.create_text(TIME_AXIS_WIDTH - 5, y_pos_hour, text=f"{hour:02d}:00", anchor="e", font=FONT_BOLD, fill=COLOR_FG)
            for minute in range(5, 60, 5):
                y_pos = y_pos_hour + (minute * PIXELS_PER_MINUTE)
                canvas.create_line(TIME_AXIS_WIDTH + 5, y_pos, width, y_pos, fill=COLOR_GRID_LINE, dash=(2, 4))
                canvas.create_text(TIME_AXIS_WIDTH - 5, y_pos, text=f"{hour:02d}:{minute:02d}", anchor="e", font=("Segoe UI", 7), fill="gray")

    def _merge_blocks(self, events):
        if not events: return []
        merged = []
        duration = BLOCK_DURATION_MINUTES
        current_app, current_title, current_start, _, current_exe = events[0]
        for i in range(1, len(events)):
            next_app, next_title, _, _, next_exe = events[i]
            if next_app == current_app and next_title == current_title:
                duration += BLOCK_DURATION_MINUTES
            else:
                merged.append({"app": current_app, "title": current_title, "start_time": datetime.fromisoformat(current_start), "duration": duration, "exe_path": current_exe})
                current_app, current_title, current_start, _, current_exe = events[i]
                duration = BLOCK_DURATION_MINUTES
        merged.append({"app": current_app, "title": current_title, "start_time": datetime.fromisoformat(current_start), "duration": duration, "exe_path": current_exe})
        return merged

    def draw_timeline(self, target_date):
        auto_width, manual_width = self.canvas_auto.winfo_width(), self.canvas_manual.winfo_width()
        if auto_width < 2 or manual_width < 2: return
        self._draw_time_axis_and_grid(self.canvas_auto, auto_width)
        self._draw_time_axis_and_grid(self.canvas_manual, manual_width)
        
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT app_name, window_title, start_time, end_time, exe_path FROM activity_events WHERE start_time >= ? AND start_time < ? ORDER BY start_time", (day_start, day_end))
        all_events = cursor.fetchall()

        if not all_events:
            conn.close()
            return
            
        merged_events = self._merge_blocks(all_events)
        app_colors = {}
        colors = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]
        
        for block in merged_events:
            minutes_from_midnight = (block["start_time"].hour * 60) + block["start_time"].minute
            y_start = minutes_from_midnight * PIXELS_PER_MINUTE + Y_PADDING
            height = block["duration"] * PIXELS_PER_MINUTE
            
            if block["app"] not in app_colors:
                app_colors[block["app"]] = colors[len(app_colors) % len(colors)]
                
            self.canvas_auto.create_rectangle(TIME_AXIS_WIDTH + 10, y_start, auto_width - 10, y_start + height, fill=app_colors[block["app"]], outline=COLOR_GRID_LINE, width=1)
            
            if height > 15:
                icon_x_offset = 0
                icon_path = os.path.join(ICON_CACHE_DIR, f"{block['app']}.png")
                
                if block['app'] in self.icon_cache:
                    icon_image = self.icon_cache[block['app']]
                elif os.path.exists(icon_path):
                    try:
                        pil_img = Image.open(icon_path).resize((16, 16), Image.Resampling.LANCZOS)
                        self.icon_cache[block['app']] = ImageTk.PhotoImage(pil_img)
                        icon_image = self.icon_cache[block['app']]
                    except Exception as e:
                        print(f"Konnte Icon nicht laden: {e}")
                        icon_image = None
                else:
                    icon_image = None

                if icon_image:
                    self.canvas_auto.create_image(TIME_AXIS_WIDTH + 20, y_start + height / 2, image=icon_image, anchor="w")
                    icon_x_offset = 22
                    
                self.canvas_auto.create_text(TIME_AXIS_WIDTH + 20 + icon_x_offset, y_start + 5, text=f"{block['title'][:40]}", anchor="nw", font=("Segoe UI", 8, "bold"), fill="white")
                self.canvas_auto.create_text(auto_width - 20, y_start + 5, text=f"{block['duration'] / 60.0:.2f}h", anchor="ne", font=FONT_BOLD, fill="white")

        cursor.execute("SELECT id, start_time, end_time, description, comment, externalId FROM manual_events WHERE start_time >= ? AND start_time < ? ORDER BY start_time", (day_start, day_end))
        text_font = font.Font(font=FONT_BOLD)
        for event_id, start_time_str, end_time_str, description, comment, externalId in cursor.fetchall():
            start_time, end_time = datetime.fromisoformat(start_time_str), datetime.fromisoformat(end_time_str)
            minutes_from_midnight = (start_time.hour * 60) + start_time.minute
            duration_min = (end_time - start_time).total_seconds() / 60
            y_start = minutes_from_midnight * PIXELS_PER_MINUTE + Y_PADDING
            height = duration_min * PIXELS_PER_MINUTE
            tag_id = f"manual_event_{event_id}"
            self.canvas_manual.create_rectangle(TIME_AXIS_WIDTH + 10, y_start, manual_width - 10, y_start + height, fill=COLOR_MANUAL_BLOCK, outline=COLOR_GRID_LINE, width=1, activefill=COLOR_MANUAL_BLOCK_ACTIVE, tags=(tag_id,))
            if height > 30:
                y_top_line = y_start + 5
                self.canvas_manual.create_text(TIME_AXIS_WIDTH + 20, y_top_line, text=f"{description}", anchor="nw", font=FONT_BOLD, fill="white", tags=(tag_id,))
                self.canvas_manual.create_text(manual_width - 20, y_top_line, text=f"{duration_min / 60.0:.2f}h", anchor="ne", font=FONT_BOLD, fill="white", tags=(tag_id,))
                if comment and comment.strip():
                    y_comment_start = y_top_line + text_font.metrics('linespace') + 5
                    draw_wrapped_and_truncated_text(canvas=self.canvas_manual, x=TIME_AXIS_WIDTH + 20, y=y_comment_start, text=comment, max_width=manual_width - 100, max_bottom_y=y_start + height - 5, anchor="nw", justify="left", font=FONT_BOLD, fill="white", tags=(tag_id,))
        
        conn.close()

        if target_date == date.today():
            now = datetime.now()
            y_pos_now = (now.hour * 60 + now.minute) * PIXELS_PER_MINUTE + Y_PADDING
            self.canvas_auto.create_line(0, y_pos_now, auto_width, y_pos_now, fill="red", width=2, tags="now_line")
            self.canvas_manual.create_line(0, y_pos_now, manual_width, y_pos_now, fill="red", width=2, tags="now_line")
        
        full_height = 24 * 60 * PIXELS_PER_MINUTE + Y_PADDING * 2
        self.canvas_auto.config(scrollregion=(0, 0, auto_width, full_height))
        self.canvas_manual.config(scrollregion=(0, 0, manual_width, full_height))
        
        if target_date == date.today():
            self.root.after(60000, lambda: self.draw_timeline(self.displayed_date))

    def show_previous_day(self):
        self.displayed_date -= timedelta(days=1)
        self.date_entry.set_date(self.displayed_date)
        self.draw_timeline(self.displayed_date)
        self.scroll_to_now()

    def show_next_day(self):
        if self.displayed_date < date.today():
            self.displayed_date += timedelta(days=1)
            self.date_entry.set_date(self.displayed_date)
            self.draw_timeline(self.displayed_date)
            self.scroll_to_now()

    def show_today(self):
        if self.displayed_date != date.today():
            self.displayed_date = date.today()
            self.date_entry.set_date(self.displayed_date)
            self.draw_timeline(self.displayed_date)
            self.scroll_to_now()

    def on_date_selected(self, event):
        new_date = event.widget.get_date()
        if new_date != self.displayed_date:
            self.displayed_date = new_date
            self.draw_timeline(self.displayed_date)
            self.scroll_to_now()

    def on_resize(self, event):
        if self.resize_timer:
            self.root.after_cancel(self.resize_timer)
        self.resize_timer = self.root.after(100, lambda: self.draw_timeline(self.displayed_date))

    def scroll_to_now(self):
        if self.displayed_date == date.today() and self.canvas_auto.find_withtag("now_line"):
            bbox = self.canvas_auto.bbox("now_line")
            if bbox:
                canvas_height = self.canvas_auto.winfo_height()
                scrollregion_height = float(self.canvas_auto.cget("scrollregion").split(' ')[3])
                if scrollregion_height > 0:
                    scroll_pos = (bbox[1] - canvas_height / 3) / scrollregion_height
                    self.canvas_auto.yview_moveto(max(0, scroll_pos))
                    self.canvas_manual.yview_moveto(max(0, scroll_pos))

    def snap_y_to_block(self, y):
        pixels_per_block = PIXELS_PER_MINUTE * BLOCK_DURATION_MINUTES
        relative_y = y - Y_PADDING
        snapped_relative_y = (max(0, relative_y) // pixels_per_block) * pixels_per_block
        return snapped_relative_y + Y_PADDING

    def y_to_datetime(self, y, target_date):
        total_minutes = max(0, (y - Y_PADDING) / PIXELS_PER_MINUTE)
        hours, minutes = int(total_minutes // 60), int(total_minutes % 60)
        return datetime.combine(target_date, datetime.min.time()).replace(hour=hours, minute=minutes)

    def start_drag(self, event):
        y = self.canvas_manual.canvasy(event.y)
        self.drag_data["raw_start_y"] = y
        self.drag_data["start_y"] = self.snap_y_to_block(y)
        manual_width = self.canvas_manual.winfo_width()
        self.drag_data["temp_rect"] = self.canvas_manual.create_rectangle(
            TIME_AXIS_WIDTH, self.drag_data["start_y"], manual_width, self.drag_data["start_y"],
            outline="white", width=2, dash=(4, 4)
        )
    def drag_motion(self, event):
        if self.drag_data["start_y"] is None: return
        manual_width, pixels_per_block = self.canvas_manual.winfo_width(), PIXELS_PER_MINUTE * BLOCK_DURATION_MINUTES
        snapped_y = self.snap_y_to_block(self.canvas_manual.canvasy(event.y))
        y_top = min(self.drag_data["start_y"], snapped_y)
        y_bottom = max(self.drag_data["start_y"], snapped_y)
        self.canvas_manual.coords(self.drag_data["temp_rect"], TIME_AXIS_WIDTH, y_top, manual_width, y_bottom + pixels_per_block)

    def end_drag(self, event):
        if self.drag_data["start_y"] is None: return
        self.canvas_manual.delete(self.drag_data["temp_rect"])
        raw_end_y = self.canvas_manual.canvasy(event.y)
        raw_start_y = self.drag_data.get("raw_start_y", raw_end_y)
        distance_moved = abs(raw_end_y - raw_start_y)
        min_drag_pixels = 5
        if distance_moved < min_drag_pixels:
            self.drag_data["start_y"], self.drag_data["temp_rect"] = None, None
            return

        y_start_raw = self.drag_data["start_y"]
        y_end_raw = self.snap_y_to_block(raw_end_y)
        y_start = min(y_start_raw, y_end_raw)
        y_end = max(y_start_raw, y_end_raw) + (PIXELS_PER_MINUTE * BLOCK_DURATION_MINUTES)
        start_time = self.y_to_datetime(y_start, self.displayed_date)
        end_time = self.y_to_datetime(y_end, self.displayed_date)
        
        conn = sqlite3.connect(DB_PATH)
        if conn.cursor().execute('SELECT 1 FROM manual_events WHERE (start_time < ?) AND (end_time > ?)', (end_time, start_time)).fetchone():
            messagebox.showerror("Error", "The new block overlaps with an existing entry.")
            conn.close()
        else:
            conn.close()
            color_config = {'canvas_bg': COLOR_CANVAS_BG, 'bg': COLOR_BG, 'fg': COLOR_FG, 'manual_block': COLOR_MANUAL_BLOCK}
            dialog = SearchDialog(self.root, title="Aufgabe zuweisen", colors=color_config)
            if dialog.result:
                selected_task, comment = dialog.result.get('task'), dialog.result.get('comment')
                custom_fields = dialog.result.get('custom_fields', {})

                if selected_task and selected_task.get("id"):
                    try:
                        api_controller = restapi_controller.ApiController()
                        duration = (end_time - start_time).total_seconds() / 3600.0
                        log_time_kwargs = {f"custom_field_{field_id}": value for field_id, value in custom_fields.items()}
                        response = api_controller.log_time(
                            issue_id=selected_task['id'], time_decimal=duration, comment=comment, **log_time_kwargs
                        )
                        if response and 'id' in response:
                            with sqlite3.connect(DB_PATH) as conn:
                                description = f"[#{selected_task['id']}] {selected_task['display']}"
                                conn.execute('INSERT INTO manual_events (start_time, end_time, description,externalId,comment,time_entry_id) VALUES (?, ?, ?, ?, ?,?)', 
                                             (start_time, end_time, description,selected_task['id'],comment,response['id']))
                        elif response and 'error' in response:
                            messagebox.showerror("API Fehler", f"Zeit konnte nicht erfasst werden:\n\n{response['error']}")
                    except Exception as e:
                        messagebox.showerror("Unerwarteter Fehler", f"API-Kommunikation fehlgeschlagen: {e}")
                    self.draw_timeline(self.displayed_date)
        
        self.drag_data["start_y"], self.drag_data["temp_rect"] = None, None

    def delete_manual_event(self, event_db_id):
        if not messagebox.askyesno("Löschen", "Diesen Zeiteintrag wirklich endgültig löschen?"): return
        with sqlite3.connect(DB_PATH) as conn:
            result = conn.execute("SELECT time_entry_id FROM manual_events WHERE id = ?", (event_db_id,)).fetchone()
        if not result:
            messagebox.showerror("Fehler", "Eintrag nicht in der DB gefunden.")
            return
        if result[0]:
            try:
                response = restapi_controller.ApiController().delete_time_entry(time_entry_id=result[0])
                if response and 'error' in response and "404" not in response['error']:
                    messagebox.showerror("API Fehler", f"Externer Eintrag konnte nicht gelöscht werden:\n\n{response['error']}")
                    return
            except Exception as e:
                messagebox.showerror("API Kommunikationsfehler", f"Fehler beim Löschen: {e}")
                return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM manual_events WHERE id = ?", (event_db_id,))
        self.draw_timeline(self.displayed_date)

    def show_context_menu(self, event):
        item_tuple = self.canvas_manual.find_withtag("current")
        if not item_tuple: return
        for tag in self.canvas_manual.gettags(item_tuple[0]):
            if tag.startswith("manual_event_"):
                try:
                    event_db_id = int(tag.split('_')[2])
                    context_menu = tk.Menu(self.root, tearoff=0, bg=COLOR_BG, fg=COLOR_FG, activebackground=COLOR_MANUAL_BLOCK, activeforeground="white")
                    context_menu.add_command(label="Löschen", command=lambda: self.delete_manual_event(event_db_id))
                    context_menu.tk_popup(event.x_root, event.y_root)
                    break
                except (ValueError, IndexError): continue

    def open_settings_dialog(self):
        colors = {'bg': COLOR_BG, 'canvas_bg': COLOR_CANVAS_BG, 'fg': COLOR_FG, 'manual_block': COLOR_MANUAL_BLOCK, 'grid_line': COLOR_GRID_LINE}
        SettingsDialog(self.root, "Einstellungen", colors, settings_manager, APP_DIR, CONFIG_PATH, DB_PATH)

    def start(self):
        if not self.is_first_instance:
            print("Anwendung läuft bereits. Sende Fokus-Signal und beende mich.")
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                    client_socket.connect(("localhost", SINGLE_INSTANCE_PORT))
                    client_socket.sendall(FOCUS_MESSAGE)
            except Exception as e:
                print(f"Fehler bei der Kommunikation mit der Hauptinstanz: {e}")
            sys.exit(0)

        initialize_config()
        settings_manager.setup_database()
        os.makedirs(ICON_CACHE_DIR, exist_ok=True)
        
        threading.Thread(target=track_activity_in_blocks, daemon=True).start()
        threading.Thread(target=self._run_server, daemon=True).start()

        self.root = tk.Tk()
        self.root.title("Timeline Tracker")
        self.root.geometry(f"{WINDOW_WIDTH}x700")
        self.root.configure(bg=COLOR_BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        try:
            self.root.iconbitmap("icon.ico")
        except tk.TclError:
            print("WARNUNG: 'icon.ico' nicht gefunden.")
            
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            value = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception: pass

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=COLOR_BG, foreground=COLOR_FG, font=FONT_NORMAL)
        style.configure("TFrame", background=COLOR_BG)
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_FG)
        style.configure("TButton", background="#4a4a4a", foreground=COLOR_FG, borderwidth=0)
        style.map("TButton", background=[("active", "#5a5a5a")])
        style.configure('my.DateEntry', fieldbackground=COLOR_BG, background=COLOR_BG, foreground=COLOR_FG, arrowcolor=COLOR_FG, bordercolor=COLOR_BG)

        nav_frame = ttk.Frame(self.root, padding=(10, 20, 10, 10))
        nav_frame.pack(fill="x", side="top")
        
        ttk.Button(nav_frame, text="<", command=self.show_previous_day).pack(side="left", padx=5)
        self.date_entry = DateEntry(nav_frame, width=16, font=FONT_HEADER, date_pattern='dd.mm.yyyy', style='my.DateEntry', borderwidth=0)
        self.date_entry.pack(side="left", expand=False, fill="x", padx=10)
        ttk.Button(nav_frame, text=">", command=self.show_next_day).pack(side="left", padx=5)
        ttk.Button(nav_frame, text="Heute", command=self.show_today).pack(side="left", padx=5)
        ttk.Button(nav_frame, text="⚙️", command=self.open_settings_dialog, width=3).pack(side="right", padx=10)
        
        main_frame = ttk.Frame(self.root, padding=(10, 5, 10, 10))
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1); main_frame.columnconfigure(2, weight=1); main_frame.rowconfigure(1, weight=1)

        ttk.Label(main_frame, text="Automatisch erfasst", font=FONT_TITLE, anchor="w").grid(row=0, column=0, sticky="w", padx=(TIME_AXIS_WIDTH, 0), pady=5)
        ttk.Label(main_frame, text="Manuelle Zuweisung", font=FONT_TITLE, anchor="w").grid(row=0, column=2, sticky="w", padx=(TIME_AXIS_WIDTH, 0), pady=5)

        self.canvas_auto = tk.Canvas(main_frame, bg=COLOR_CANVAS_BG, highlightthickness=0)
        self.canvas_auto.grid(row=1, column=0, sticky="nsew", padx=(0, GAP_WIDTH // 2))
        self.canvas_manual = tk.Canvas(main_frame, bg=COLOR_CANVAS_BG, highlightthickness=0)
        self.canvas_manual.grid(row=1, column=2, sticky="nsew", padx=(GAP_WIDTH // 2, 0))

        scrollbar = ttk.Scrollbar(main_frame, orient="vertical")
        scrollbar.grid(row=1, column=3, sticky="ns")

        def on_scrollbar_move(*args):
            self.canvas_auto.yview(*args)
            self.canvas_manual.yview(*args)
        
        def on_mousewheel(event):
            scroll_val = -1 if event.num == 4 or event.delta > 0 else 1
            self.canvas_auto.yview_scroll(scroll_val, "units")
            self.canvas_manual.yview_scroll(scroll_val, "units")
            return "break"
        
        scrollbar.config(command=on_scrollbar_move)
        self.canvas_auto.config(yscrollcommand=scrollbar.set)
        self.canvas_manual.config(yscrollcommand=scrollbar.set)
        
        self.root.bind("<Configure>", self.on_resize)
        self.root.bind_all("<MouseWheel>", on_mousewheel)
        self.root.bind_all("<Button-4>", on_mousewheel)
        self.root.bind_all("<Button-5>", on_mousewheel)
        self.date_entry.bind("<<DateEntrySelected>>", self.on_date_selected)
        self.canvas_manual.bind("<ButtonPress-1>", self.start_drag)
        self.canvas_manual.bind("<B1-Motion>", self.drag_motion)
        self.canvas_manual.bind("<ButtonRelease-1>", self.end_drag)
        self.canvas_manual.bind("<Button-3>", self.show_context_menu)

        self.setup_tray_icon()
        self.root.after(100, lambda: self.draw_timeline(self.displayed_date))
        self.root.after(500, self.scroll_to_now)

        self.root.mainloop()

if __name__ == "__main__":
    app = TimelineTrackerApp()
    app.start()