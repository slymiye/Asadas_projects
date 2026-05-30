"""
tests/test_sistema.py
---------------------
Suite de tests completa.
Cubre: modelos, serialización, archivo principal, índice BSB,
árbol en memoria, detección de cambios y búsqueda integrada.

Ejecutar:
    cd asadas_system
    pytest tests/test_sistema.py -v
"""

import os
import pickle
import struct
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (
    NODE_SIZE,
    RECORD_SIZE,
    NodoArbol,
    Registro_asada,
    _decode_str,
    _encode_str,
)
from file_manager import ArbolBSB, ArchivoIndice, ArchivoRegistros
from api_asada import AsadaApi
from sistema import SistemaAsadas


# ─────────────────────────────────────────────
# DATOS DE PRUEBA
# ─────────────────────────────────────────────

DICT_VALIDO = {
    "canton": "UPALA",
    "codigoDTA": 21303,
    "coordenadaX": "364776",
    "coordenadaY": "1215603",
    "correo": "asada@test.cr",
    "distrito": "SAN JOSÉ",
    "fax": "SIN INFO",
    "id_Asada": "1000",
    "id_Objecto": 3,
    "operador": "ASADA UPALA",
    "provincia": "ALAJUELA",
    "telefono": "87186088",
    "tipoSistema": "GRAVEDAD",
}

DICTS_MULTIPLES = [
    {**DICT_VALIDO, "id_Asada": "500",  "operador": "ASADA BETA",  "canton": "CARTAGO"},
    {**DICT_VALIDO, "id_Asada": "200",  "operador": "ASADA ALFA",  "canton": "SAN JOSE"},
    {**DICT_VALIDO, "id_Asada": "900",  "operador": "ASADA GAMMA", "canton": "HEREDIA"},
    {**DICT_VALIDO, "id_Asada": "100",  "operador": "ASADA DELTA", "canton": "LIMON"},
    {**DICT_VALIDO, "id_Asada": "1500", "operador": "ASADA OMEGA", "canton": "GUANACASTE"},
]

RESPUESTA_API = {"value": DICTS_MULTIPLES}


@pytest.fixture
def registro():
    return Registro_asada.from_dict(DICT_VALIDO)


@pytest.fixture
def varios_registros():
    return [Registro_asada.from_dict(d) for d in DICTS_MULTIPLES]


@pytest.fixture
def tmpdir_path():
    with tempfile.TemporaryDirectory() as d:
        yield d


# ═══════════════════════════════════════════════════════════════
# 1. MODELO: Registro_asada
# ═══════════════════════════════════════════════════════════════

class TestRegistroAsada:

    def test_from_dict_asigna_atributos(self, registro):
        assert registro.id_Asada    == "1000"
        assert registro.provincia   == "ALAJUELA"
        assert registro.canton      == "UPALA"
        assert registro.codigoDTA   == 21303
        assert registro.id_Objecto  == 3
        assert registro.tipoSistema == "GRAVEDAD"

    def test_from_dict_campo_faltante_es_vacio(self):
        r = Registro_asada.from_dict({"id_Asada": "99"})
        assert r.id_Asada  == "99"
        assert r.canton    == ""
        assert r.codigoDTA == 0

    def test_to_bytes_tamano_exacto(self, registro):
        data = registro.to_bytes()
        assert len(data) == RECORD_SIZE

    def test_ciclo_bytes_ida_y_vuelta(self, registro):
        data  = registro.to_bytes()
        copia = Registro_asada.from_bytes(data)
        assert copia.id_Asada    == registro.id_Asada
        assert copia.canton      == registro.canton
        assert copia.provincia   == registro.provincia
        assert copia.codigoDTA   == registro.codigoDTA
        assert copia.operador    == registro.operador
        assert copia.tipoSistema == registro.tipoSistema

    def test_campos_largos_se_truncan(self):
        r = Registro_asada.from_dict({"canton": "X" * 200})
        data  = r.to_bytes()
        copia = Registro_asada.from_bytes(data)
        assert len(copia.canton) <= 50

    def test_varios_registros_ciclo(self, varios_registros):
        for reg in varios_registros:
            copia = Registro_asada.from_bytes(reg.to_bytes())
            assert copia.id_Asada == reg.id_Asada


# ═══════════════════════════════════════════════════════════════
# 2. MODELO: NodoArbol
# ═══════════════════════════════════════════════════════════════

class TestNodoArbol:

    def test_to_bytes_tamano_exacto(self):
        nodo = NodoArbol("1000", 0, 0)
        assert len(nodo.to_bytes()) == NODE_SIZE

    def test_ciclo_bytes_ida_y_vuelta(self):
        nodo = NodoArbol("1000", 512, 3)
        nodo.left_idx  = 1
        nodo.right_idx = 2
        copia = NodoArbol.from_bytes(nodo.to_bytes(), 3)
        assert copia.id_Asada  == "1000"
        assert copia.position  == 512
        assert copia.left_idx  == 1
        assert copia.right_idx == 2
        assert copia.index     == 3

    def test_sin_hijos_por_defecto(self):
        nodo = NodoArbol("500", 0, 0)
        assert nodo.left_idx  == -1
        assert nodo.right_idx == -1


# ═══════════════════════════════════════════════════════════════
# 3. ARCHIVO PRINCIPAL: ArchivoRegistros
# ═══════════════════════════════════════════════════════════════

class TestArchivoRegistros:

    def test_guardar_y_leer_todos(self, varios_registros, tmpdir_path):
        path = os.path.join(tmpdir_path, "main.bin")
        ar   = ArchivoRegistros(path)
        ar.guardar_todos(varios_registros)

        leidos = ar.leer_todos()
        assert len(leidos) == len(varios_registros)
        ids_orig  = {r.id_Asada for r in varios_registros}
        ids_leido = {r.id_Asada for r in leidos}
        assert ids_orig == ids_leido

    def test_total_registros(self, varios_registros, tmpdir_path):
        path = os.path.join(tmpdir_path, "main.bin")
        ar   = ArchivoRegistros(path)
        ar.guardar_todos(varios_registros)
        assert ar.total_registros() == len(varios_registros)

    def test_acceso_directo_por_posicion(self, varios_registros, tmpdir_path):
        path = os.path.join(tmpdir_path, "main.bin")
        ar   = ArchivoRegistros(path)
        ar.guardar_todos(varios_registros)

        # El registro en posición RECORD_SIZE*2 debe ser el tercero
        reg = ar.leer_en_posicion(RECORD_SIZE * 2)
        assert reg.id_Asada == varios_registros[2].id_Asada

    def test_acceso_directo_primer_registro(self, varios_registros, tmpdir_path):
        path = os.path.join(tmpdir_path, "main.bin")
        ar   = ArchivoRegistros(path)
        ar.guardar_todos(varios_registros)
        reg = ar.leer_en_posicion(0)
        assert reg.id_Asada == varios_registros[0].id_Asada

    def test_acceso_directo_ultimo_registro(self, varios_registros, tmpdir_path):
        path = os.path.join(tmpdir_path, "main.bin")
        ar   = ArchivoRegistros(path)
        ar.guardar_todos(varios_registros)
        last_pos = RECORD_SIZE * (len(varios_registros) - 1)
        reg = ar.leer_en_posicion(last_pos)
        assert reg.id_Asada == varios_registros[-1].id_Asada

    def test_integridad_datos_canton_y_correo(self, varios_registros, tmpdir_path):
        path = os.path.join(tmpdir_path, "main.bin")
        ar   = ArchivoRegistros(path)
        ar.guardar_todos(varios_registros)
        leidos = ar.leer_todos()
        for orig, leido in zip(varios_registros, leidos):
            assert orig.correo  == leido.correo
            assert orig.telefono == leido.telefono

    def test_existe_retorna_true_si_archivo_creado(self, varios_registros, tmpdir_path):
        path = os.path.join(tmpdir_path, "main.bin")
        ar   = ArchivoRegistros(path)
        assert not ar.existe()
        ar.guardar_todos(varios_registros)
        assert ar.existe()

    def test_archivo_vacio_leer_todos_retorna_lista_vacia(self, tmpdir_path):
        path = os.path.join(tmpdir_path, "main.bin")
        ar   = ArchivoRegistros(path)
        ar.guardar_todos([])
        assert ar.leer_todos() == []

    def test_posicion_invalida_lanza_error(self, varios_registros, tmpdir_path):
        path = os.path.join(tmpdir_path, "main.bin")
        ar   = ArchivoRegistros(path)
        ar.guardar_todos(varios_registros)
        with pytest.raises(ValueError):
            ar.leer_en_posicion(999_999_999)


# ═══════════════════════════════════════════════════════════════
# 4. ÍNDICE BSB: ArchivoIndice
# ═══════════════════════════════════════════════════════════════

class TestArchivoIndice:

    def test_escribir_y_leer_nodo(self, tmpdir_path):
        path = os.path.join(tmpdir_path, "indice.bin")
        ai   = ArchivoIndice(path)
        nodo = NodoArbol("1000", 0)
        idx  = ai.escribir_nodo(nodo)
        leido = ai.leer_nodo(idx)
        assert leido.id_Asada == "1000"
        assert leido.position == 0

    def test_actualizar_nodo_existente(self, tmpdir_path):
        path = os.path.join(tmpdir_path, "indice.bin")
        ai   = ArchivoIndice(path)
        nodo = NodoArbol("1000", 0)
        ai.escribir_nodo(nodo)
        nodo.left_idx = 5
        ai.escribir_nodo(nodo)
        leido = ai.leer_nodo(0)
        assert leido.left_idx == 5

    def test_leer_todos_retorna_lista(self, tmpdir_path):
        path = os.path.join(tmpdir_path, "indice.bin")
        ai   = ArchivoIndice(path)
        for i, d in enumerate(DICTS_MULTIPLES):
            nodo = NodoArbol(d["id_Asada"], i * RECORD_SIZE)
            ai.escribir_nodo(nodo)
        nodos = ai.leer_todos()
        assert len(nodos) == len(DICTS_MULTIPLES)

    def test_nodo_inexistente_lanza_error(self, tmpdir_path):
        path = os.path.join(tmpdir_path, "indice.bin")
        ai   = ArchivoIndice(path)
        with pytest.raises((ValueError, Exception)):
            ai.leer_nodo(99)


# ═══════════════════════════════════════════════════════════════
# 5. ÁRBOL BSB EN MEMORIA: ArbolBSB
# ═══════════════════════════════════════════════════════════════

class TestArbolBSB:

    def _crear_arbol(self, tmpdir_path):
        path  = os.path.join(tmpdir_path, "indice.bin")
        ai    = ArchivoIndice(path)
        arbol = ArbolBSB(ai)
        return arbol

    def test_arbol_inicia_sin_raiz(self, tmpdir_path):
        arbol = self._crear_arbol(tmpdir_path)
        assert arbol.raiz_idx == -1

    def test_insertar_primer_nodo_es_raiz(self, tmpdir_path):
        arbol = self._crear_arbol(tmpdir_path)
        arbol.insertar("500", 0)
        assert arbol.raiz_idx == 0
        assert arbol.nodos[0].id_Asada == "500"

    def test_insertar_menor_va_izquierda(self, tmpdir_path):
        arbol = self._crear_arbol(tmpdir_path)
        arbol.insertar("500", 0)
        arbol.insertar("200", RECORD_SIZE)
        raiz = arbol.nodos[0]
        assert raiz.left_idx != -1
        assert arbol.nodos[raiz.left_idx].id_Asada == "200"

    def test_insertar_mayor_va_derecha(self, tmpdir_path):
        arbol = self._crear_arbol(tmpdir_path)
        arbol.insertar("500", 0)
        arbol.insertar("900", RECORD_SIZE)
        raiz = arbol.nodos[0]
        assert raiz.right_idx != -1
        assert arbol.nodos[raiz.right_idx].id_Asada == "900"

    def test_propiedad_bsb_con_cinco_nodos(self, tmpdir_path):
        """Todos los nodos izquierdos < raíz y derechos > raíz."""
        arbol = self._crear_arbol(tmpdir_path)
        ids   = ["500", "200", "900", "100", "1500"]
        for i, id_ in enumerate(ids):
            arbol.insertar(id_, i * RECORD_SIZE)
        raiz = arbol.nodos[0]
        assert int(arbol.nodos[raiz.left_idx].id_Asada)  < int(raiz.id_Asada)
        assert int(arbol.nodos[raiz.right_idx].id_Asada) > int(raiz.id_Asada)

    def test_comparacion_numerica_no_lexicografica(self, tmpdir_path):
        """'9' < '1000' numéricamente; debe ir a la izquierda."""
        arbol = self._crear_arbol(tmpdir_path)
        arbol.insertar("1000", 0)
        arbol.insertar("9",    RECORD_SIZE)
        raiz = arbol.nodos[0]
        assert raiz.left_idx != -1
        assert arbol.nodos[raiz.left_idx].id_Asada == "9"

    def test_buscar_existente_retorna_nodo(self, tmpdir_path):
        arbol = self._crear_arbol(tmpdir_path)
        for i, d in enumerate(DICTS_MULTIPLES):
            arbol.insertar(d["id_Asada"], i * RECORD_SIZE)
        nodo = arbol.buscar("900")
        assert nodo is not None
        assert nodo.id_Asada == "900"

    def test_buscar_inexistente_retorna_none(self, tmpdir_path):
        arbol = self._crear_arbol(tmpdir_path)
        arbol.insertar("500", 0)
        assert arbol.buscar("9999") is None

    def test_buscar_en_arbol_vacio_retorna_none(self, tmpdir_path):
        arbol = self._crear_arbol(tmpdir_path)
        assert arbol.buscar("500") is None

    def test_posicion_en_nodo_es_correcta(self, tmpdir_path):
        arbol = self._crear_arbol(tmpdir_path)
        arbol.insertar("500", 0)
        arbol.insertar("200", RECORD_SIZE * 1)
        nodo = arbol.buscar("200")
        assert nodo.position == RECORD_SIZE * 1

    def test_cargar_desde_archivo(self, tmpdir_path):
        """Inserta, recarga desde archivo, y vuelve a buscar."""
        path  = os.path.join(tmpdir_path, "indice.bin")
        ai    = ArchivoIndice(path)
        arbol = ArbolBSB(ai)
        for i, d in enumerate(DICTS_MULTIPLES):
            arbol.insertar(d["id_Asada"], i * RECORD_SIZE)

        # Crear nuevo árbol y cargar desde el mismo archivo
        arbol2 = ArbolBSB(ArchivoIndice(path))
        arbol2.cargar()
        nodo = arbol2.buscar("900")
        assert nodo is not None

    def test_total_nodos(self, tmpdir_path):
        arbol = self._crear_arbol(tmpdir_path)
        for i, d in enumerate(DICTS_MULTIPLES):
            arbol.insertar(d["id_Asada"], i * RECORD_SIZE)
        assert arbol.total_nodos() == len(DICTS_MULTIPLES)


# ═══════════════════════════════════════════════════════════════
# 6. API: AsadaApi (con mock)
# ═══════════════════════════════════════════════════════════════

class TestAsadaApi:

    def _mock_response(self, json_data, status=200):
        mock = MagicMock()
        mock.status_code = status
        mock.json.return_value = json_data
        return mock

    def test_get_records_retorna_lista(self, tmpdir_path):
        api = AsadaApi(hash_file=os.path.join(tmpdir_path, "hash.txt"))
        with patch("requests.get", return_value=self._mock_response(RESPUESTA_API)):
            records = api.get_records()
        assert isinstance(records, list)
        assert len(records) == len(DICTS_MULTIPLES)

    def test_get_records_contiene_campos_requeridos(self, tmpdir_path):
        api = AsadaApi(hash_file=os.path.join(tmpdir_path, "hash.txt"))
        with patch("requests.get", return_value=self._mock_response(RESPUESTA_API)):
            records = api.get_records()
        for campo in ["id_Asada", "provincia", "canton", "operador"]:
            assert campo in records[0]

    def test_sin_clave_value_lanza_error(self, tmpdir_path):
        api = AsadaApi(hash_file=os.path.join(tmpdir_path, "hash.txt"))
        with patch("requests.get", return_value=self._mock_response({"oops": []})):
            with pytest.raises(ValueError, match="value"):
                api.get_records()

    def test_error_http_lanza_excepcion(self, tmpdir_path):
        mock = MagicMock()
        mock.status_code = 500
        mock.raise_for_status.side_effect = Exception("HTTP 500")
        api = AsadaApi(hash_file=os.path.join(tmpdir_path, "hash.txt"))
        with patch("requests.get", return_value=mock):
            with pytest.raises(Exception, match="500"):
                api.get_records()

    def test_has_changed_primera_vez_es_true(self, tmpdir_path):
        api = AsadaApi(hash_file=os.path.join(tmpdir_path, "hash.txt"))
        assert api.has_changed(DICTS_MULTIPLES) is True

    def test_has_changed_despues_de_confirm_es_false(self, tmpdir_path):
        api = AsadaApi(hash_file=os.path.join(tmpdir_path, "hash.txt"))
        api.confirm_update(DICTS_MULTIPLES)
        assert api.has_changed(DICTS_MULTIPLES) is False

    def test_has_changed_con_datos_distintos_es_true(self, tmpdir_path):
        api = AsadaApi(hash_file=os.path.join(tmpdir_path, "hash.txt"))
        api.confirm_update(DICTS_MULTIPLES)
        datos_nuevos = [{**DICTS_MULTIPLES[0], "canton": "NUEVO CANTON"}]
        assert api.has_changed(datos_nuevos) is True

    def test_url_sin_espacio_final(self):
        api = AsadaApi()
        assert not api.endpoint.endswith(" ")

    def test_url_es_https(self):
        api = AsadaApi()
        assert api.endpoint.startswith("https://")


# ═══════════════════════════════════════════════════════════════
# 7. INTEGRACIÓN: SistemaAsadas (búsqueda end-to-end)
# ═══════════════════════════════════════════════════════════════

class TestSistemaAsadas:

    def _crear_sistema(self, tmpdir_path):
        return SistemaAsadas(
            main_file  = os.path.join(tmpdir_path, "main.bin"),
            index_file = os.path.join(tmpdir_path, "indice.bin"),
            hash_file  = os.path.join(tmpdir_path, "hash.txt"),
        )

    def _inicializar(self, sistema):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = RESPUESTA_API
        with patch("requests.get", return_value=mock):
            sistema.inicializar(forzar=True)

    def test_inicializar_crea_archivos(self, tmpdir_path):
        sistema = self._crear_sistema(tmpdir_path)
        self._inicializar(sistema)
        assert os.path.exists(os.path.join(tmpdir_path, "main.bin"))
        assert os.path.exists(os.path.join(tmpdir_path, "indice.bin"))

    def test_total_registros_correcto(self, tmpdir_path):
        sistema = self._crear_sistema(tmpdir_path)
        self._inicializar(sistema)
        assert sistema.total_registros() == len(DICTS_MULTIPLES)

    def test_buscar_id_existente_retorna_registro(self, tmpdir_path):
        sistema = self._crear_sistema(tmpdir_path)
        self._inicializar(sistema)
        reg = sistema.buscar_por_id("500")
        assert reg is not None
        assert reg.id_Asada == "500"

    def test_buscar_id_inexistente_retorna_none(self, tmpdir_path):
        sistema = self._crear_sistema(tmpdir_path)
        self._inicializar(sistema)
        assert sistema.buscar_por_id("9999") is None

    def test_buscar_todos_los_ids(self, tmpdir_path):
        sistema = self._crear_sistema(tmpdir_path)
        self._inicializar(sistema)
        for d in DICTS_MULTIPLES:
            reg = sistema.buscar_por_id(d["id_Asada"])
            assert reg is not None
            assert reg.id_Asada == d["id_Asada"]

    def test_buscar_retorna_todos_los_campos(self, tmpdir_path):
        sistema = self._crear_sistema(tmpdir_path)
        self._inicializar(sistema)
        reg = sistema.buscar_por_id("200")
        assert reg.canton    == "SAN JOSE"
        assert reg.operador  == "ASADA ALFA"
        assert reg.provincia == "ALAJUELA"

    def test_listar_todos_retorna_cantidad_correcta(self, tmpdir_path):
        sistema = self._crear_sistema(tmpdir_path)
        self._inicializar(sistema)
        todos = sistema.listar_todos()
        assert len(todos) == len(DICTS_MULTIPLES)

    def test_sin_cambios_no_reconstruye(self, tmpdir_path):
        """Segunda llamada a inicializar sin cambios no debe reconstruir."""
        sistema = self._crear_sistema(tmpdir_path)
        self._inicializar(sistema)

        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = RESPUESTA_API
        with patch("requests.get", return_value=mock):
            resultado = sistema.inicializar()
        assert "Sin cambios" in resultado

    def test_con_cambios_reconstruye(self, tmpdir_path):
        sistema = self._crear_sistema(tmpdir_path)
        self._inicializar(sistema)

        datos_nuevos = [{**DICTS_MULTIPLES[0], "canton": "NUEVO"}]
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {"value": datos_nuevos}
        with patch("requests.get", return_value=mock):
            resultado = sistema.inicializar()
        assert "reconstruido" in resultado
        assert sistema.total_registros() == 1
