@echo off
REM --- Build EXE ---
python -m PyInstaller --onefile --noconsole --icon=icon.ico tracker_app.py

REM --- Warten bis PyInstaller fertig ist ---
echo Warten auf PyInstaller...
timeout /t 2 > nul

REM --- Dateien kopieren ---
echo Kopiere zusätzliche Dateien ins dist-Verzeichnis...
copy /Y "api_config.json.example" "dist\api_config.json.example"
copy /Y "icon.ico" "dist\icon.ico"
copy /Y "icon.png" "dist\icon.png"

echo Fertig! Prüfe den dist-Ordner.
pause
