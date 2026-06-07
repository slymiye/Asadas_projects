"""
sistema.py
----------
Orquesta todo el sistema:
  1. Descarga datos del endpoint ARESEP.
  2. Detecta si hubo cambios.
  3. Si cambió: reconstruye el archivo principal y el índice BSB.
  4. Permite consultar una ASADA por id_Asada usando el índice.
"""

from api_asada import AsadaApi
from file_manager import ArbolBSB, ArchivoIndice, ArchivoRegistros
from models import Registro_asada


class Sistema_Datos_Asadas:

    def __init__(
        self,
        main_file:  str = "archivo_principal.bin",
        index_file: str = "indice_bsb.bin",
        hash_file:  str = "data_hash.txt",
    ):
        self.api      = AsadaApi(hash_file=hash_file)
        self.archivo  = ArchivoRegistros(main_file)
        self.indice_f = ArchivoIndice(index_file)
        self.arbol    = ArbolBSB(self.indice_f)

    # ── inicialización ────────────────────────────────────────

    def inicializar(self, forzar: bool = False) -> str:
        """
        Descarga los datos. Si detecta cambios (o forzar=True),
        reconstruye ambos archivos y el árbol BSB.
        Retorna un mensaje con el resultado.
        """
        print("Descargando datos desde ARESEP...")
        records = self.api.get_records()

        if not forzar and self.archivo.existe() and not self.api.has_changed(records):
            print("Sin cambios detectados. Cargando índice existente...")
            self.arbol.cargar()
            return f"Sin cambios. {self.archivo.total_registros()} registros en memoria."

        print(f"Cambios detectados. Procesando {len(records)} registros...")
        self._reconstruir(records)
        self.api.confirm_update(records)
        return f"Sistema reconstruido con {len(records)} registros."

    def _reconstruir(self, records: list[dict]):
        """Reconstruye el archivo principal y el índice BSB desde cero."""
        registros = [Registro_asada.from_dict(r) for r in records]

        # 1. Escribir archivo principal (todos los registros secuenciales)
        self.archivo.guardar_todos(registros)

        # 2. Resetear árbol y archivo de índice
        self.arbol = ArbolBSB(self.indice_f)
        open(self.indice_f.path, "wb").close()  # limpiar archivo de índice

        # 3. Insertar cada registro en el árbol (position = byte en archivo principal)
        from models import RECORD_SIZE
        for i, reg in enumerate(registros):
            position = i * RECORD_SIZE
            self.arbol.insertar(reg.id_Asada, position)

        print(f"  ✓ {len(registros)} registros en archivo principal.")
        print(f"  ✓ {self.arbol.total_nodos()} nodos en índice BSB.")

    # ── consulta ──────────────────────────────────────────────

    def buscar_por_id(self, id_Asada: str) -> Registro_asada | None:
        """
        Busca una ASADA por id_Asada:
          1. Busca en el árbol BSB (en memoria) → obtiene posición en archivo.
          2. Accede directamente al archivo principal en esa posición.
        Retorna el Registro_asada o None si no existe.
        """
        nodo = self.arbol.buscar(str(id_Asada))
        if nodo is None:
            return None
        return self.archivo.leer_en_posicion(nodo.position)

    def listar_todos(self) -> list[Registro_asada]:
        """Lee todos los registros secuencialmente del archivo principal."""
        return self.archivo.leer_todos()

    def total_registros(self) -> int:
        return self.archivo.total_registros()
