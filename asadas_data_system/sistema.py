"""
sistema.py
----------
Orquesta todo el sistema:
  1. Descarga datos del endpoint ARESEP.
  2. Detecta si hubo cambios.
  3. Si cambió: reconstruye el archivo principal, el índice BSB
     y la lista jerárquica.
  4. Permite consultar por id_Asada y por división política.
"""

from api_asada import AsadaApi
from file_manager import (ArbolBSB, ArchivoIndice, ArchivoListaJerarquica,
                           ArchivoRegistros, ListaJerarquica)
from models import Registro_asada


class Sistema_Datos_Asadas:

    def __init__(
        self,
        main_file:  str = "archivo_principal.bin",
        index_file: str = "indice_bsb.bin",
        list_file:  str = "lista_jerarquica.bin",
        hash_file:  str = "data_hash.txt",
    ):
        self.api      = AsadaApi(hash_file=hash_file)
        self.archivo  = ArchivoRegistros(main_file)
        self.indice_f = ArchivoIndice(index_file)
        self.arbol    = ArbolBSB(self.indice_f)
        self.lista_f  = ArchivoListaJerarquica(list_file)
        self.lista    = ListaJerarquica(self.lista_f)

    # ── inicialización ────────────────────────────────────────

    def inicializar(self, forzar: bool = False) -> str:
        """
        Descarga los datos. Si detecta cambios (o forzar=True),
        reconstruye los tres archivos binarios.
        """
        print("Descargando datos desde ARESEP...")
        records = self.api.get_records()

        if not forzar and self.archivo.existe() and not self.api.has_changed(records):
            print("Sin cambios detectados. Cargando estructuras existentes...")
            self.arbol.cargar()
            self.lista.cargar()
            return f"Sin cambios. {self.archivo.total_registros()} registros en memoria."

        print(f"Cambios detectados. Procesando {len(records)} registros...")
        self._reconstruir(records)
        self.api.confirm_update(records)
        return f"Sistema reconstruido con {len(records)} registros."

    def _reconstruir(self, records: list[dict]):
        """Reconstruye el archivo principal, el índice BSB y la lista jerárquica."""
        registros = [Registro_asada.from_dict(r) for r in records]

        # 1. Escribir archivo principal
        self.archivo.guardar_todos(registros)

        # 2. Reconstruir árbol BSB
        self.arbol = ArbolBSB(self.indice_f)
        open(self.indice_f.path, "wb").close()
        from models import RECORD_SIZE
        for i, reg in enumerate(registros):
            position = i * RECORD_SIZE
            self.arbol.insertar(reg.id_Asada, position)

        # 3. Reconstruir lista jerárquica
        self.lista = ListaJerarquica(self.lista_f)
        self.lista.construir(registros)

        print(f"  ✓ {len(registros)} registros en archivo principal.")
        print(f"  ✓ {len(self.arbol.nodos)} nodos en índice BSB.")

    # ── consulta por id ───────────────────────────────────────

    def buscar_por_id(self, id_Asada: str) -> Registro_asada | None:
        """Busca una ASADA por id_Asada usando el árbol BSB en memoria."""
        nodo = self.arbol.buscar(str(id_Asada))
        if nodo is None:
            return None
        return self.archivo.leer_en_posicion(nodo.position)

    # ── consultas jerárquicas ────────────────────────────────

    def listar_provincias(self) -> list[str]:
        """Retorna todos los nombres de provincia disponibles."""
        return self.lista.listar_provincias()

    def listar_cantones(self, provincia: str) -> list[str]:
        """Retorna los cantones de una provincia."""
        return self.lista.listar_cantones(provincia)

    def listar_distritos(self, provincia: str, canton: str) -> list[str]:
        """Retorna los distritos de un cantón."""
        return self.lista.listar_distritos(provincia, canton)

    def listar_asadas_por_ubicacion(self, provincia: str, canton: str,
                                     distrito: str) -> list[Registro_asada]:
        """
        Retorna los registros completos de todas las ASADAS de un distrito,
        accediendo directamente al archivo principal por posición.
        """
        nodos = self.lista.listar_asadas(provincia, canton, distrito)
        registros = []
        for nodo in nodos:
            if nodo.position >= 0:
                try:
                    reg = self.archivo.leer_en_posicion(nodo.position)
                    registros.append(reg)
                except ValueError:
                    pass
        return registros

    # ── lectura completa ──────────────────────────────────────

    def listar_todos(self) -> list[Registro_asada]:
        """Lee todos los registros secuencialmente del archivo principal."""
        return self.archivo.leer_todos()

    def total_registros(self) -> int:
        return self.archivo.total_registros()