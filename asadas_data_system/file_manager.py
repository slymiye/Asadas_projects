"""
file_manager.py
---------------
Gestiona dos archivos binarios:

1. archivo_principal.bin  — registros de tamaño fijo (RECORD_SIZE bytes c/u)
2. indice_bsb.bin         — nodos del árbol BSB     (NODE_SIZE  bytes c/u)

El índice almacena, por cada nodo, la posición exacta en bytes
donde vive el registro en el archivo principal, lo que permite
acceso directo sin escanear todo el archivo.
"""

import os
import struct

from models import (
    NODE_SIZE,
    RECORD_SIZE,
    NodoArbol,
    Registro_asada,
)

MAIN_FILE  = "archivo_principal.bin"
INDEX_FILE = "indice_bsb.bin"


# ══════════════════════════════════════════════════════════════
# Archivo principal (registros de tamaño fijo)
# ══════════════════════════════════════════════════════════════

class ArchivoRegistros:
    """
    Almacena registros con tamaño fijo (RECORD_SIZE bytes).
    Posición de registro N = N * RECORD_SIZE.
    """

    def __init__(self, path: str = MAIN_FILE):
        self.path = path

    # ── escritura ─────────────────────────────────────────────

    def guardar_todos(self, registros: list[Registro_asada]):
        """Reescribe el archivo completo con todos los registros."""
        with open(self.path, "wb") as f:
            for reg in registros:
                data = reg.to_bytes()
                assert len(data) == RECORD_SIZE, (
                    f"Registro de tamaño incorrecto: {len(data)} != {RECORD_SIZE}"
                )
                f.write(data)

    def agregar(self, registro: Registro_asada) -> int:
        """
        Agrega un registro al final del archivo.
        Retorna la posición en bytes donde fue escrito.
        """
        posicion = os.path.getsize(self.path) if os.path.exists(self.path) else 0
        with open(self.path, "ab") as f:
            f.write(registro.to_bytes())
        return posicion
    # ── lectura ───────────────────────────────────────────────

    def leer_en_posicion(self, position: int) -> Registro_asada:
        """Acceso directo: lee el registro en la posición (bytes) indicada."""
        with open(self.path, "rb") as f:
            f.seek(position)
            data = f.read(RECORD_SIZE)
        if len(data) != RECORD_SIZE:
            raise ValueError(
                f"No se pudo leer un registro completo en posición {position}."
            )
        return Registro_asada.from_bytes(data)

    def leer_todos(self) -> list[Registro_asada]:
        """Lee secuencialmente todos los registros del archivo."""
        registros = []
        with open(self.path, "rb") as f:
            while True:
                data = f.read(RECORD_SIZE)
                if len(data) == 0:
                    break
                if len(data) != RECORD_SIZE:
                    raise ValueError("Archivo principal corrupto: bloque incompleto.")
                registros.append(Registro_asada.from_bytes(data))
        return registros

    def total_registros(self) -> int:
        if not os.path.exists(self.path):
            return 0
        return os.path.getsize(self.path) // RECORD_SIZE

    def existe(self) -> bool:
        return os.path.exists(self.path)


# ══════════════════════════════════════════════════════════════
# Archivo de índice BSB (nodos de tamaño fijo)
# ══════════════════════════════════════════════════════════════

class ArchivoIndice:
    """
    Almacena los nodos del árbol BSB como registros de tamaño fijo
    (NODE_SIZE bytes). El índice de un nodo es su posición ordinal
    dentro del archivo (0, 1, 2, …).

    El primer nodo escrito (índice 0) es la raíz del árbol.
    """

    def __init__(self, path: str = INDEX_FILE):
        self.path = path

    # ── escritura ─────────────────────────────────────────────

    def escribir_nodo(self, nodo: NodoArbol) -> int:
        """
        Escribe (o sobreescribe) el nodo en su posición lógica.
        Si el nodo aún no existe (index == -1) se agrega al final.
        Retorna el índice asignado.
        """
        if nodo.index == -1:
            # Nuevo nodo: agregar al final
            with open(self.path, "ab") as f:
                nodo.index = self._total_nodos_en_archivo()
                f.write(nodo.to_bytes())
        else:
            # Actualizar nodo existente (para guardar sus hijos)
            mode = "r+b" if os.path.exists(self.path) else "wb"
            with open(self.path, mode) as f:
                f.seek(nodo.index * NODE_SIZE)
                f.write(nodo.to_bytes())
        return nodo.index

    def reescribir_todos(self, nodos: list[NodoArbol]):
        """Reescribe el archivo de índice completo."""
        with open(self.path, "wb") as f:
            for i, nodo in enumerate(nodos):
                nodo.index = i
                f.write(nodo.to_bytes())

    # ── lectura ───────────────────────────────────────────────

    def leer_nodo(self, index: int) -> NodoArbol:
        """Lee el nodo en la posición lógica dada."""
        with open(self.path, "rb") as f:
            f.seek(index * NODE_SIZE)
            data = f.read(NODE_SIZE)
        if len(data) != NODE_SIZE:
            raise ValueError(f"Nodo en índice {index} incompleto o no existe.")
        return NodoArbol.from_bytes(data, index)

    def leer_todos(self) -> list[NodoArbol]:
        nodos = []
        with open(self.path, "rb") as f:
            idx = 0
            while True:
                data = f.read(NODE_SIZE)
                if len(data) == 0:
                    break
                nodos.append(NodoArbol.from_bytes(data, idx))
                idx += 1
        return nodos

    def _total_nodos_en_archivo(self) -> int:
        if not os.path.exists(self.path):
            return 0
        return os.path.getsize(self.path) // NODE_SIZE

    def existe(self) -> bool:
        return os.path.exists(self.path)


# ══════════════════════════════════════════════════════════════
# Árbol BSB en memoria + persistencia
# ══════════════════════════════════════════════════════════════

class ArbolBSB:
    """
    Árbol Binario de Búsqueda cargado en memoria.
    Los nodos se persisten en ArchivoIndice.
    La raíz siempre tiene index = 0.
    """

    def __init__(self, archivo_indice: ArchivoIndice):
        self.archivo = archivo_indice
        self.nodos: list[NodoArbol] = []   # todos los nodos en memoria
        self.raiz_idx: int = -1            # índice lógico de la raíz

    # ── carga ────────────────────────────────────────────────

    def cargar(self):
        """Carga todos los nodos del archivo de índice en memoria."""
        self.nodos = self.archivo.leer_todos()
        self.raiz_idx = 0 if self.nodos else -1

    # ── inserción ────────────────────────────────────────────

    def insertar(self, id_Asada: str, position: int):
        """
        Inserta un nodo en el árbol con la llave id_Asada y
        la posición en bytes dentro del archivo principal.
        """
        nuevo = NodoArbol(id_Asada, position)

        if self.raiz_idx == -1:
            # Árbol vacío: el nuevo nodo es la raíz
            nuevo.index = 0
            self.nodos.append(nuevo)
            self.raiz_idx = 0
            self.archivo.escribir_nodo(nuevo)
        else:
            self._insertar_recursivo(self.raiz_idx, nuevo)

    def _insertar_recursivo(self, idx_actual: int, nuevo: NodoArbol):
        actual = self.nodos[idx_actual]

        if int(nuevo.id_Asada) < int(actual.id_Asada):
            if actual.left_idx == -1:
                nuevo.index = len(self.nodos)
                self.nodos.append(nuevo)
                actual.left_idx = nuevo.index
                self.archivo.escribir_nodo(nuevo)
                self.archivo.escribir_nodo(actual)   # actualiza puntero
            else:
                self._insertar_recursivo(actual.left_idx, nuevo)
        else:
            if actual.right_idx == -1:
                nuevo.index = len(self.nodos)
                self.nodos.append(nuevo)
                actual.right_idx = nuevo.index
                self.archivo.escribir_nodo(nuevo)
                self.archivo.escribir_nodo(actual)
            else:
                self._insertar_recursivo(actual.right_idx, nuevo)

    # ── búsqueda ─────────────────────────────────────────────

    def buscar(self, id_Asada: str) -> NodoArbol | None:
        """
        Busca el nodo con id_Asada en el árbol cargado en memoria.
        Retorna el NodoArbol o None si no existe.
        """
        if self.raiz_idx == -1:
            return None
        return self._buscar_recursivo(self.raiz_idx, id_Asada)

    def _buscar_recursivo(self, idx: int, id_Asada: str) -> NodoArbol | None:
        if idx == -1:
            return None
        nodo = self.nodos[idx]
        if id_Asada == nodo.id_Asada:
            return nodo
        if int(id_Asada) < int(nodo.id_Asada):
            return self._buscar_recursivo(nodo.left_idx, id_Asada)
        return self._buscar_recursivo(nodo.right_idx, id_Asada)

    def total_nodos(self) -> int:
        return len(self.nodos)
    


