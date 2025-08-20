import json
import requests
import os
from functools import reduce

from app_config import CONFIG_PATH

def _get_nested_value(d, key_path):
    """Holt einen verschachtelten Wert aus einem Dictionary mittels Punktnotation."""
    try:
        return reduce(lambda val, key: val.get(key) if val else None, key_path.split('.'), d)
    except (TypeError, AttributeError):
        return None

class ApiController:
    def __init__(self, config_path=CONFIG_PATH):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.base_url = self.config.get('api_base_url', '')

    def _execute(self, endpoint_name: str, **kwargs):
        """
        Bereitet einen Request vor und führt ihn aus. Kennt keine Logik für Tokens.
        """
        endpoint_config = self.config['endpoints'].get(endpoint_name)
        if not endpoint_config:
            raise ValueError(f"Endpunkt '{endpoint_name}' nicht in der Konfiguration gefunden.")

        def format_recursive(item):
            if isinstance(item, str):
                try:
                    return item.format(**kwargs)
                except KeyError:
                    return item
            if isinstance(item, dict):
                return {k: format_recursive(v) for k, v in item.items()}
            if isinstance(item, list):
                return [format_recursive(i) for i in item]
            return item

        path = format_recursive(endpoint_config.get('path', ''))
        full_url = self.base_url + path
        # Die Header werden jetzt direkt und ohne spezielle Behandlung aus der Config genommen
        headers = format_recursive(self.config.get('api_headers', {}).copy())
        body = format_recursive(endpoint_config.get('body'))
        params = format_recursive(endpoint_config.get('params'))
        
        try:
            response = requests.request(
                method=endpoint_config['method'], url=full_url, headers=headers, json=body, params=params, timeout=10
            )
            response.raise_for_status()
            return None if response.status_code == 204 else response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    # --- Öffentliche Methoden sind jetzt komplett token-agnostisch ---

# In der Klasse ApiController

    def log_time(self, issue_id: int, time_decimal: float, comment: str):
        """Erfasst Zeit für eine Aufgabe und gibt die ID des neuen Eintrags zurück."""
        # 1. API-Aufruf durchführen
        raw_response = self._execute('log_time', issue_id=issue_id, time_decimal=time_decimal, comment=comment)

        # 2. Prüfen, ob der Aufruf an sich fehlgeschlagen ist
        if not raw_response or (isinstance(raw_response, dict) and "error" in raw_response):
            return raw_response  # Fehler direkt zurückgeben

        # 3. Response-Mapping aus der Konfiguration holen
        endpoint_config = self.config['endpoints'].get('log_time', {})
        mapping = endpoint_config.get('response_mapping')
        
        if not mapping:
            # Fallback: Wenn kein Mapping da ist, komplette Antwort zurückgeben
            return raw_response

        # 4. Das Objekt extrahieren, das die ID enthält (z.B. das "time_entry" Objekt)
        result_object = _get_nested_value(raw_response, mapping['results_path'])
        if not result_object:
            return {"error": f"Ergebnisobjekt unter Pfad '{mapping['results_path']}' nicht gefunden."}

        # 5. Die ID aus dem Objekt extrahieren
        entry_id = _get_nested_value(result_object, mapping['id_field'])
        if entry_id is None:
            return {"error": f"ID-Feld '{mapping['id_field']}' im Ergebnisobjekt nicht gefunden."}

        # 6. Erfolgreich extrahierte ID in einem Dictionary zurückgeben
        return {"id": entry_id}

    def search_issue(self, query: str):
        """Sucht nach Aufgaben und formatiert die Antwort für die Anzeige."""
        raw_response = self._execute('search_issue', query=query)

        if not raw_response or (isinstance(raw_response, dict) and "error" in raw_response):
            return raw_response

        mapping = self.config['endpoints']['search_issue'].get('response_mapping')
        if not mapping:
            return raw_response
        results_list = _get_nested_value(raw_response, mapping['results_path'])
        
        if not isinstance(results_list, list):
            return {"error": f"Ergebnisliste unter Pfad '{mapping['results_path']}' nicht gefunden."}

        formatted_results = []
        for item in results_list:
            display_text = _get_nested_value(item, mapping['display_field'])
            item_id = _get_nested_value(item, mapping['id_field'])
            if display_text is not None and item_id is not None:
                formatted_results.append({"id": item_id, "display": display_text})
                
        return formatted_results

    def delete_time_entry(self, time_entry_id: int):
        """Löscht einen Zeiteintrag."""
        return self._execute('delete_time_entry', time_entry_id=time_entry_id)