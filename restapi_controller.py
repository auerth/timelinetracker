import json
import requests
import os

# Wir gehen davon aus, dass die JSON-Datei im selben Ordner liegt
CONFIG_FILE = 'api_config.json'

class ApiController:
    def __init__(self, config_path=CONFIG_FILE):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.base_url = self.config.get('api_base_url', '')

    def _prepare_request(self, endpoint_name, **kwargs):
        """Bereitet die URL, Header, Body und Parameter für einen Request vor."""
        endpoint = self.config['endpoints'].get(endpoint_name)
        if not endpoint:
            raise ValueError(f"Endpunkt '{endpoint_name}' nicht in der Konfiguration gefunden.")

        # 1. URL zusammenbauen und Platzhalter ersetzen
        path = endpoint['path']
        for key, value in kwargs.items():
            path = path.replace(f'{{{key}}}', str(value))
        full_url = self.base_url + path

        # 2. Header vorbereiten und Platzhalter ersetzen
        headers = self.config.get('api_headers', {}).copy()
        for key, value in headers.items():
            headers[key] = value.format(**kwargs)

        # 3. Body vorbereiten und Platzhalter ersetzen
        body = endpoint.get('body')
        if body:
            # json.dumps and loads, um eine tiefe Kopie zu erstellen
            body = json.loads(json.dumps(body)) 
            for key, value in body.items():
                if isinstance(value, str):
                    body[key] = value.format(**kwargs)

        # 4. Query-Parameter vorbereiten und Platzhalter ersetzen
        params = endpoint.get('params')
        if params:
            params = params.copy()
            for key, value in params.items():
                params[key] = value.format(**kwargs)

        return endpoint['method'], full_url, headers, body, params

    def _execute_request(self, method, url, headers, body, params):
        """Führt den eigentlichen HTTP-Request aus und gibt die Antwort zurück."""
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                params=params,
                timeout=10 # Guter Standardwert
            )
            response.raise_for_status()  # Wirft einen Fehler bei HTTP-Status 4xx oder 5xx
            
            # Bei DELETE-Requests gibt es oft keinen JSON-Body in der Antwort
            if response.status_code == 204: # No Content
                return None
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"API-Fehler: {e}")
            # Hier könntest du eine spezifischere Fehlermeldung an die UI zurückgeben
            return {"error": str(e)}

    # --- Öffentliche Methoden für deine Anwendung ---

    def create_issue(self, api_token: str, title: str, description: str):
        method, url, headers, body, params = self._prepare_request(
            'create_issue', api_token=api_token, title=title, description=description
        )
        return self._execute_request(method, url, headers, body, params)

    def log_time(self, api_token: str, issue_id: int, time_decimal: float, comment: str):
        method, url, headers, body, params = self._prepare_request(
            'log_time', api_token=api_token, issue_id=issue_id, time_decimal=time_decimal, comment=comment
        )
        return self._execute_request(method, url, headers, body, params)

    def search_issue(self, api_token: str, query: str):
        method, url, headers, body, params = self._prepare_request(
            'search_issue', api_token=api_token, query=query
        )
        return self._execute_request(method, url, headers, body, params)
        
    def delete_time_entry(self, api_token: str, time_entry_id: int):
        method, url, headers, body, params = self._prepare_request(
            'delete_time_entry', api_token=api_token, time_entry_id=time_entry_id
        )
        return self._execute_request(method, url, headers, body, params)