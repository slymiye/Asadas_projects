"""
api_asada.py
------------
Consume el endpoint oficial de ARESEP y detecta cambios en los datos.
"""

import hashlib
import json
import os

import requests

ENDPOINT = (
    "https://datos.aresep.go.cr/ws.datosabiertos/Services/IA/"
    "Asadas.svc/ObtenerInformacionUbicacionAsadas"
)
HASH_FILE = "data_hash.txt"


class AsadaApi:
    def __init__(self, endpoint: str = ENDPOINT, hash_file: str = HASH_FILE):
        self.endpoint  = endpoint
        self.hash_file = hash_file

    # ── descarga ──────────────────────────────────────────────

    def get_raw(self) -> dict:
        """Descarga el JSON completo desde el endpoint."""
        response = requests.get(self.endpoint, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_records(self) -> list[dict]:
        """Retorna la lista de registros (campo 'value')."""
        data = self.get_raw()
        if "value" not in data:
            raise ValueError(
                f"La respuesta no contiene 'value'. "
                f"Claves recibidas: {list(data.keys())}"
            )
        return data["value"]

    # ── detección de cambios ──────────────────────────────────

    def _compute_hash(self, records: list[dict]) -> str:
        """Calcula un hash MD5 de los datos para detectar cambios."""
        raw = json.dumps(records, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _load_saved_hash(self) -> str | None:
        if os.path.exists(self.hash_file):
            with open(self.hash_file, "r") as f:
                return f.read().strip()
        return None

    def _save_hash(self, hash_value: str):
        with open(self.hash_file, "w") as f:
            f.write(hash_value)

    def has_changed(self, records: list[dict]) -> bool:
        """Retorna True si los datos descargados difieren de los guardados."""
        current_hash = self._compute_hash(records)
        saved_hash   = self._load_saved_hash()
        return current_hash != saved_hash

    def confirm_update(self, records: list[dict]):
        """Guarda el hash actual para marcar los datos como procesados."""
        self._save_hash(self._compute_hash(records))
