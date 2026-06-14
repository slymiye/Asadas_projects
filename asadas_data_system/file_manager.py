"""
file_manager.py
---------------
Gestiona tres archivos binarios:

1. archivo_principal.bin   — registros de tamaño fijo (RECORD_SIZE bytes c/u)
2. indice_bsb.bin          — nodos del árbol BSB     (NODE_SIZE  bytes c/u)
3. lista_jerarquica.bin    — nodos de la lista jerárquica (LISTA_NODO_SIZE bytes c/u)
"""

import os
import struct

from models import (
    LISTA_NODO_SIZE,
    NODE_SIZE,
    RECORD_SIZE,
    TIPO_ASADA,
    TIPO_CANTON,
    TIPO_DISTRITO,
    TIPO_PROVINCIA,
    NodoArbol,
    NodoListaJerarquica,
    Registro_asada,
)

MAIN_FILE  = "archivo_principal.bin"
INDEX_FILE = "indice_bsb.bin"
LIST_FILE  = "lista_jerarquica.bin"


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
        position = os.path.getsize(self.path) if os.path.exists(self.path) else 0
        with open(self.path, "ab") as f:
            f.write(registro.to_bytes())
        return position

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
    """

    def __init__(self, path: str = INDEX_FILE):
        self.path = path

    def escribir_nodo(self, nodo: NodoArbol) -> int:
        """
        Escribe (o sobreescribe) el nodo en su posición lógica.
        Si el nodo aún no existe (index == -1) se agrega al final.
        Retorna el índice asignado.
        """
        if nodo.index == -1:
            with open(self.path, "ab") as f:
                nodo.index = self._total_nodos_en_archivo()
                f.write(nodo.to_bytes())
        else:
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
    """

    def __init__(self, archivo_indice: ArchivoIndice):
        self.archivo = archivo_indice
        self.nodos: list[NodoArbol] = []
        self.raiz_idx: int = -1

    def cargar(self):
        """Carga todos los nodos del archivo de índice en memoria."""
        self.nodos = self.archivo.leer_todos()
        self.raiz_idx = 0 if self.nodos else -1

    def insertar(self, id_Asada: str, position: int):
        """Inserta un nodo en el árbol de forma iterativa."""
        nuevo = NodoArbol(id_Asada, position)

        if self.raiz_idx == -1:
            nuevo.index = 0
            self.nodos.append(nuevo)
            self.raiz_idx = 0
            self.archivo.escribir_nodo(nuevo)
            return

        # Inserción iterativa — evita RecursionError con datasets grandes
        idx_actual = self.raiz_idx
        while True:
            actual = self.nodos[idx_actual]

            try:
                ir_izquierda = int(nuevo.id_Asada) < int(actual.id_Asada)
            except ValueError:
                ir_izquierda = nuevo.id_Asada < actual.id_Asada

            if ir_izquierda:
                if actual.left_idx == -1:
                    nuevo.index = len(self.nodos)
                    self.nodos.append(nuevo)
                    actual.left_idx = nuevo.index
                    self.archivo.escribir_nodo(nuevo)
                    self.archivo.escribir_nodo(actual)
                    break
                else:
                    idx_actual = actual.left_idx
            else:
                if actual.right_idx == -1:
                    nuevo.index = len(self.nodos)
                    self.nodos.append(nuevo)
                    actual.right_idx = nuevo.index
                    self.archivo.escribir_nodo(nuevo)
                    self.archivo.escribir_nodo(actual)
                    break
                else:
                    idx_actual = actual.right_idx

    def buscar(self, id_Asada: str) -> NodoArbol | None:
        """Busca el nodo con id_Asada de forma iterativa."""
        idx = self.raiz_idx
        while idx != -1:
            nodo = self.nodos[idx]
            if id_Asada == nodo.id_Asada:
                return nodo
            try:
                ir_izquierda = int(id_Asada) < int(nodo.id_Asada)
            except ValueError:
                ir_izquierda = id_Asada < nodo.id_Asada

            idx = nodo.left_idx if ir_izquierda else nodo.right_idx
        return None


# ══════════════════════════════════════════════════════════════
# Archivo de lista jerárquica (nodos de tamaño fijo)
# ══════════════════════════════════════════════════════════════

class ArchivoListaJerarquica:
    """
    Almacena los nodos de la lista enlazada jerárquica como registros
    de tamaño fijo (LISTA_NODO_SIZE = 107 bytes cada uno).
    """

    def __init__(self, path: str = LIST_FILE):
        self.path = path

    def escribir_nodo(self, nodo: NodoListaJerarquica) -> int:
        """
        Escribe (o sobreescribe) un nodo en su posición lógica.
        Si nodo.index == -1, se agrega al final.
        Retorna el índice asignado.
        """
        if nodo.index == -1:
            nodo.index = self._total_nodos_en_archivo()
            with open(self.path, "ab") as f:
                f.write(nodo.to_bytes())
        else:
            mode = "r+b" if os.path.exists(self.path) else "wb"
            with open(self.path, mode) as f:
                f.seek(nodo.index * LISTA_NODO_SIZE)
                f.write(nodo.to_bytes())
        return nodo.index

    def reescribir_todos(self, nodos: list):
        """Reescribe el archivo completo con la lista de nodos dada."""
        with open(self.path, "wb") as f:
            for i, nodo in enumerate(nodos):
                nodo.index = i
                f.write(nodo.to_bytes())

    def leer_nodo(self, index: int) -> NodoListaJerarquica:
        """Lee el nodo en la posición lógica dada."""
        with open(self.path, "rb") as f:
            f.seek(index * LISTA_NODO_SIZE)
            data = f.read(LISTA_NODO_SIZE)
        if len(data) != LISTA_NODO_SIZE:
            raise ValueError(f"Nodo de lista en índice {index} incompleto.")
        return NodoListaJerarquica.from_bytes(data, index)

    def leer_todos(self) -> list:
        """Lee todos los nodos del archivo secuencialmente."""
        nodos = []
        if not os.path.exists(self.path):
            return nodos
        with open(self.path, "rb") as f:
            idx = 0
            while True:
                data = f.read(LISTA_NODO_SIZE)
                if len(data) == 0:
                    break
                nodos.append(NodoListaJerarquica.from_bytes(data, idx))
                idx += 1
        return nodos

    def _total_nodos_en_archivo(self) -> int:
        if not os.path.exists(self.path):
            return 0
        return os.path.getsize(self.path) // LISTA_NODO_SIZE

    def existe(self) -> bool:
        return os.path.exists(self.path)


# ══════════════════════════════════════════════════════════════
# Constructor de la lista jerárquica en memoria + persistencia
# ══════════════════════════════════════════════════════════════

class ListaJerarquica:
    """
    Construye y persiste la jerarquía:
        Provincia → Cantón → Distrito → ASADA

    Todos los nodos se guardan en un único archivo binario plano.
    Las relaciones se expresan mediante punteros lógicos:
      sig_mismo_idx : siguiente nodo del mismo nivel (hermano)
      sig_hijo_idx  : primer nodo del nivel inferior (primer hijo)
    """

    def __init__(self, archivo: ArchivoListaJerarquica):
        self.archivo   = archivo
        self._nodos: list[NodoListaJerarquica] = []
        self._raiz_idx: int = -1

    def construir(self, registros: list):
        """
        Recibe la lista completa de Registro_asada y construye
        la jerarquía jerárquica ordenada alfabéticamente por nivel.
        """
        # ── paso 1: agrupar en estructura anidada ────────────
        jerarquia: dict[str, dict[str, dict[str, list]]] = {}

        for i, reg in enumerate(registros):
            prov = reg.provincia.strip()
            cant = reg.canton.strip()
            dist = reg.distrito.strip()
            ida  = reg.id_Asada.strip()
            pos  = i * RECORD_SIZE

            if not prov:
                continue
            jerarquia.setdefault(prov, {})
            jerarquia[prov].setdefault(cant, {})
            jerarquia[prov][cant].setdefault(dist, [])
            jerarquia[prov][cant][dist].append((ida, pos))

        # ── paso 2: construir nodos enlazados ────────────────
        self._nodos    = []
        self._raiz_idx = -1

        provincias_ord = sorted(jerarquia.keys())
        prev_prov_nodo = None

        for prov in provincias_ord:
            np = NodoListaJerarquica(TIPO_PROVINCIA, prov)
            np.index = len(self._nodos)
            self._nodos.append(np)

            if self._raiz_idx == -1:
                self._raiz_idx = np.index
            if prev_prov_nodo is not None:
                prev_prov_nodo.sig_mismo_idx = np.index

            cantones_ord    = sorted(jerarquia[prov].keys())
            prev_cant_nodo  = None
            primer_cant_idx = -1

            for cant in cantones_ord:
                nc = NodoListaJerarquica(TIPO_CANTON, cant)
                nc.index = len(self._nodos)
                self._nodos.append(nc)

                if primer_cant_idx == -1:
                    primer_cant_idx = nc.index
                if prev_cant_nodo is not None:
                    prev_cant_nodo.sig_mismo_idx = nc.index

                distritos_ord   = sorted(jerarquia[prov][cant].keys())
                prev_dist_nodo  = None
                primer_dist_idx = -1

                for dist in distritos_ord:
                    nd = NodoListaJerarquica(TIPO_DISTRITO, dist)
                    nd.index = len(self._nodos)
                    self._nodos.append(nd)

                    if primer_dist_idx == -1:
                        primer_dist_idx = nd.index
                    if prev_dist_nodo is not None:
                        prev_dist_nodo.sig_mismo_idx = nd.index

                    asadas_ord = sorted(
                        jerarquia[prov][cant][dist],
                        key=lambda t: int(t[0]) if t[0].isdigit() else t[0]
                    )
                    prev_asada_nodo  = None
                    primer_asada_idx = -1

                    for (ida, pos) in asadas_ord:
                        na = NodoListaJerarquica(TIPO_ASADA, ida,
                                                 id_Asada=ida, position=pos)
                        na.index = len(self._nodos)
                        self._nodos.append(na)

                        if primer_asada_idx == -1:
                            primer_asada_idx = na.index
                        if prev_asada_nodo is not None:
                            prev_asada_nodo.sig_mismo_idx = na.index
                        prev_asada_nodo = na

                    nd.sig_hijo_idx = primer_asada_idx
                    prev_dist_nodo  = nd

                nc.sig_hijo_idx = primer_dist_idx
                prev_cant_nodo  = nc

            np.sig_hijo_idx = primer_cant_idx
            prev_prov_nodo  = np

        # ── paso 3: persistir ─────────────────────────────────
        open(self.archivo.path, "wb").close()
        self.archivo.reescribir_todos(self._nodos)

        print(f"  ✓ Lista jerárquica: {len(self._nodos)} nodos "
              f"({len(provincias_ord)} provincias).")

    def cargar(self):
        """Carga todos los nodos del archivo en memoria."""
        self._nodos    = self.archivo.leer_todos()
        self._raiz_idx = 0 if self._nodos else -1

    # ── consultas ─────────────────────────────────────────────

    def listar_provincias(self) -> list:
        """Retorna lista de nombres de todas las provincias."""
        return self._recolectar_nombres_nivel(self._raiz_idx)

    def listar_cantones(self, provincia: str) -> list:
        """Retorna lista de nombres de cantones de la provincia dada."""
        idx_prov = self._buscar_por_nombre(self._raiz_idx, provincia)
        if idx_prov == -1:
            return []
        return self._recolectar_nombres_nivel(self._nodos[idx_prov].sig_hijo_idx)

    def listar_distritos(self, provincia: str, canton: str) -> list:
        """Retorna lista de nombres de distritos del cantón dado."""
        idx_prov = self._buscar_por_nombre(self._raiz_idx, provincia)
        if idx_prov == -1:
            return []
        idx_cant = self._buscar_por_nombre(
            self._nodos[idx_prov].sig_hijo_idx, canton
        )
        if idx_cant == -1:
            return []
        return self._recolectar_nombres_nivel(self._nodos[idx_cant].sig_hijo_idx)

    def listar_asadas(self, provincia: str, canton: str,
                      distrito: str) -> list:
        """
        Retorna lista de NodoListaJerarquica (tipo ASADA) del distrito dado,
        ordenadas por id_Asada.
        """
        idx_prov = self._buscar_por_nombre(self._raiz_idx, provincia)
        if idx_prov == -1:
            return []
        idx_cant = self._buscar_por_nombre(
            self._nodos[idx_prov].sig_hijo_idx, canton
        )
        if idx_cant == -1:
            return []
        idx_dist = self._buscar_por_nombre(
            self._nodos[idx_cant].sig_hijo_idx, distrito
        )
        if idx_dist == -1:
            return []
        return self._recolectar_nodos_nivel(self._nodos[idx_dist].sig_hijo_idx)

    # ── utilidades internas ───────────────────────────────────

    def _recolectar_nombres_nivel(self, inicio_idx: int) -> list:
        nombres = []
        idx = inicio_idx
        while idx != -1:
            nombres.append(self._nodos[idx].nombre)
            idx = self._nodos[idx].sig_mismo_idx
        return nombres

    def _recolectar_nodos_nivel(self, inicio_idx: int) -> list:
        nodos = []
        idx = inicio_idx
        while idx != -1:
            nodos.append(self._nodos[idx])
            idx = self._nodos[idx].sig_mismo_idx
        return nodos

    def _buscar_por_nombre(self, inicio_idx: int, nombre: str) -> int:
        idx = inicio_idx
        nombre_lower = nombre.strip().lower()
        while idx != -1:
            if self._nodos[idx].nombre.strip().lower() == nombre_lower:
                return idx
            idx = self._nodos[idx].sig_mismo_idx
        return -1

    def total_nodos(self) -> int:
        return len(self._nodos)