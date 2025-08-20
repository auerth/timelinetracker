python -m PyInstaller --onefile --noconsole --icon=icon.ico `
  --add-data "api_config.json.example;." `
  --add-data "icon.ico;." `
  --add-data "icon.png;." `
  tracker_app.py
pause