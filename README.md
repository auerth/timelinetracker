# TimelineTracker

![TimelineTracker Logo](https://github.com/auerth/timelinetracker/blob/main/icon.png)

**Ein Open-Source-Tool zur automatischen Erfassung deiner PC-Aktivitäten und zur nahtlosen Zuweisung von Zeit auf deine Projekte.**

TimelineTracker ist eine Windows-Desktop-Anwendung, die im Hintergrund läuft und alle 5 Minuten das aktive Fenster aufzeichnet. Die gesammelten Daten werden in einer visuellen Timeline dargestellt, die es dir ermöglicht, deine Zeit einfach und effizient auf Aufgaben in deinem Projektmanagement-Tool (z.B. Redmine, Jira) zu buchen.

---

## ✨ Funktionen

* **Automatische Zeiterfassung**: Erfasst kontinuierlich die Nutzung von Anwendungen und Fenstertiteln in 5-Minuten-Intervallen.
* **Visuelle Timeline**: Zwei parallele Timelines zur übersichtlichen Darstellung von automatisch erfassten Aktivitäten und manuell zugewiesenen Zeitblöcken.
* **Manuelle Zuweisung per Drag & Drop**: Erstelle und buche Zeitblöcke einfach durch Aufziehen mit der Maus.
* **Flexible API-Anbindung**: Verbinde den Tracker über eine simple JSON-Konfiguration mit praktisch jedem Projektmanagement-Tool, das eine REST-API anbietet.
* **Intelligente Task-Suche**: Suche direkt in der App nach Aufgaben aus deinem System, um Zeit korrekt zu verbuchen.
* **Open Source**: Der gesamte Quellcode ist frei verfügbar. Passe den Tracker an deine Bedürfnisse an oder hilf mit, ihn zu verbessern!

---

## 🚀 Getting Started

Folge diesen Schritten, um TimelineTracker zu installieren und zu verwenden.

### 1. Installation

1.  Lade den neuesten Installer (`TimelineTracker.exe`) aus dem [Releases-Bereich](https://github.com/softwelop/timelinetracker/releases) herunter.
2.  Führe die heruntergeladene `.exe`-Datei aus und folge den Anweisungen des Installationsassistenten.
3.  Nach der Installation startet die Anwendung automatisch. Du findest sie als Icon in deiner Taskleiste.

### 2. Konfiguration

Beim ersten Start wird automatisch eine Konfigurationsdatei `api_config.json` in deinem Benutzerverzeichnis erstellt.

* **Pfad**: `C:\Benutzer\DEIN_BENUTZERNAME\TimelineTracker\api_config.json`
* Du kannst diesen Ordner auch direkt über das Einstellungsmenü (⚙️) in der App öffnen.

Passe diese Datei an, um TimelineTracker mit deinem Projektmanagement-Tool zu verbinden. Eine detaillierte Erklärung der Konfiguration findest du unten.

---

## ⚙️ Die `api_config.json` Konfiguration

Diese Datei ist das Herzstück der Anbindung an externe Systeme. Hier definierst du, wie der Tracker mit der API deines Projektmanagement-Tools kommuniziert.

### Beispiel (`api_config.json`)

```json
{
  "api_base_url": "[https://dein-system.com/]",
  "api_headers": {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": "DEIN_API_SCHLÜSSEL"
  },
  "endpoints": {
    "log_time": {
      "method": "POST",
      "path": "time_entries.json",
      "body": {
        "time_entry": {
          "issue_id": "{issue_id}",
          "hours": "{time_decimal}",
          "comments": "{comment}"
        }
      },
      "response_mapping": {
        "results_path": "time_entry",
        "id_field": "id"
      }
    },
    "search_issue": {
      "method": "GET",
      "path": "issues.json",
      "params": {
        "subject": "~{query}"
      },
      "response_mapping": {
        "results_path": "issues",
        "display_field": "subject",
        "id_field": "id"
      }
    },
    "delete_time_entry": {
      "method": "DELETE",
      "path": "time_entries/{time_entry_id}.json"
    }
  }
}
```

### Erklärung der Felder

* `api_base_url`: Die Basis-URL deiner API (z.B. `https://redmine.softwelop.com/`).
* `api_headers`: Ein Objekt für HTTP-Header. Hier kommt typischerweise dein API-Schlüssel oder ein Authentifizierungs-Token hinein.
* `endpoints`: Definiert die drei Aktionen, die der Tracker ausführen kann:
    * `log_time`: Zeit buchen.
    * `search_issue`: Nach einer Aufgabe suchen.
    * `delete_time_entry`: Eine Zeitbuchung löschen.
* **Parameter innerhalb eines Endpoints**:
    * `method`: Die HTTP-Methode (`GET`, `POST`, `DELETE`).
    * `path`: Der API-Pfad, der an die `api_base_url` angehängt wird. Platzhalter wie `{time_entry_id}` werden automatisch ersetzt.
    * `body`: Die JSON-Struktur für `POST`-Requests. Die Platzhalter `{issue_id}`, `{time_decimal}` und `{comment}` werden vom Tracker gefüllt.
    * `params`: URL-Parameter für `GET`-Requests. `{query}` wird durch die Sucheingabe ersetzt.
    * `response_mapping`: Definiert, wie die API-Antwort interpretiert wird.
        * `results_path`: Der Pfad zum Array der Ergebnisse (z.B. `issues`).
        * `display_field`: Das Feld, das in der Suchliste angezeigt wird (z.B. `subject`).
        * `id_field`: Das Feld, das die eindeutige ID eines Eintrags enthält.

---

## 🛠️ Build-Prozess (für Entwickler)

Um die Anwendung aus dem Quellcode selbst zu bauen, benötigst du Python und die in `requirements.txt` (falls vorhanden) gelisteten Pakete.

1.  **Abhängigkeiten installieren**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Executable erstellen**:
    Führe die `build.bat`-Datei aus. Diese verwendet `PyInstaller`, um eine einzelne `.exe`-Datei im `dist`-Ordner zu erstellen und kopiert alle notwendigen Zusatzdateien (Icons, Beispiel-Konfig).
3.  **Installer erstellen**:
    * Installiere [Inno Setup](https://jrsoftware.org/isinfo.php).
    * Öffne die Datei `installer/installer_project.iss` mit Inno Setup.
    * Passe die Pfade in der `[Files]`-Sektion an, sodass sie auf die Dateien in deinem `dist`-Ordner zeigen.
    * Kompiliere das Skript in Inno Setup, um die `TimelineTracker.exe`-Installationsdatei zu erzeugen.

---

## 🤝 Contributing

Beiträge sind herzlich willkommen! Wenn du einen Fehler findest oder eine neue Funktion vorschlagen möchtest, erstelle bitte ein [Issue](https://github.com/softwelop/timelinetracker/issues). Wenn du Code beisteuern möchtest, erstelle einen Fork des Repositories und sende einen Pull Request.

---

## 📄 Lizenz & Nutzung

TimelineTracker ist kostenlos und darf frei verwendet, modifiziert und weitergegeben werden.

Die einzige Bedingung ist die **Nennung des ursprünglichen Autors** (softwelop - Thorben Auer) in abgeleiteten Werken oder bei einer Weiterverbreitung.

**Was bedeutet "Nennung"?** Wenn du den Code in deinem eigenen Projekt verwendest, erwähne bitte den Ursprung – zum Beispiel in deiner README, in den Credits deiner Anwendung oder in den Kommentaren deines Codes.
