import requests
import json

class AsadaApi:
    def __init__(self):
        self.base_url = "https://datos.aresep.go.cr/ws.datosabiertos/Services/IA/Asadas.svc/ObtenerInformacionUbicacionAsadas"

    def get_data(self):
        response = requests.get(self.base_url)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def get_asadas_values(self):
        data = self.get_data()
        if "value" not in data:
            raise ValueError(f"Respuesta inesperada del API. Claves recibidas: {list(data.keys())}")
        return data["value"]
