"""
Suite de tests completa para el proyecto Asadas.
Cubre: Api_asada, models, file_controller (todas las clases).

Dependencias:
    pip install pytest requests pytest-mock
"""

import os
import pickle
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import models
import file_controller as fc
from Api_asada import AsadaApi

# ─────────────────────────────────────────────
# FIXTURES REUTILIZABLES
# ─────────────────────────────────────────────

ITEM_VALIDO = {
    "canton": "UPALA",
    "codigoDTA": 21303,
    "coordenadaX": "364776",
    "coordenadaY": "1215603",
    "correo": "SIN INFORMACIÓN",
    "distrito": "SAN JOSÉ O PIZOTE",
    "fax": "SIN INFORMACIÓN",
    "id_Asada": "1537",
    "id_Objecto": 3,
    "operador": "00023-2014_EL PROGRESO DE SAN JOSE DE UPALA, ALAJUELA",
    "provincia": "ALAJUELA",
    "telefono": "87186088",
    "tipoSistema": "GRAVEDAD",
}

ITEMS_MULTIPLES = [
    {**ITEM_VALIDO, "id_Asada": "500",  "operador": "ASADA BETA",  "provincia": "CARTAGO"},
    {**ITEM_VALIDO, "id_Asada": "200",  "operador": "ASADA ALFA",  "provincia": "SAN JOSE"},
    {**ITEM_VALIDO, "id_Asada": "1000", "operador": "ASADA GAMMA", "provincia": "HEREDIA"},
]


@pytest.fixture
def registro_simple():
    """Un Registro_asada construido con el item válido."""
    return fc._dict_a_registro(ITEM_VALIDO)


@pytest.fixture
def tres_registros():
    """Lista de tres Registro_asada."""
    return [fc._dict_a_registro(i) for i in ITEMS_MULTIPLES]


@pytest.fixture
def archivo_temp_con_datos():
    """Archivo binario temporal que ya tiene los ITEMS_MULTIPLES serializados."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
        pickle.dump(ITEMS_MULTIPLES, tmp)
        path = tmp.name
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def archivo_temp_vacio():
    """Archivo temporal vacío (solo el path)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
        path = tmp.name
    yield path
    if os.path.exists(path):
        os.remove(path)


# ─────────────────────────────────────────────
# 1. TESTS: Registro_asada (models.py)
# ─────────────────────────────────────────────

class TestRegistroAsada:
    """Verifica que el modelo de datos se construye correctamente."""

    def test_atributos_se_asignan(self, registro_simple):
        r = registro_simple
        assert r.id_Asada   == "1537"
        assert r.provincia  == "ALAJUELA"
        assert r.canton     == "UPALA"
        assert r.distrito   == "SAN JOSÉ O PIZOTE"
        assert r.telefono   == "87186088"
        assert r.correo     == "SIN INFORMACIÓN"
        assert r.fax        == "SIN INFORMACIÓN"
        assert r.tipoSistema == "GRAVEDAD"
        assert r.operador   == "00023-2014_EL PROGRESO DE SAN JOSE DE UPALA, ALAJUELA"
        assert r.codigoDTA  == 21303
        assert r.id_objeto  == 3
        assert r.cordX      == "364776"
        assert r.cordY      == "1215603"

    def test_campos_pueden_ser_none(self):
        """Acepta None sin lanzar excepción."""
        r = models.Registro_asada(
            codigoDTA=None, id_Asada=None, id_objeto=None,
            cordY=None, cordX=None, provincia=None,
            canton=None, distrito=None, telefono=None,
            correo=None, fax=None, tipoSistema=None, operador=None
        )
        assert r.id_Asada is None


# ─────────────────────────────────────────────
# 2. TESTS: Lista_enlazada_asada (models.py)
# ─────────────────────────────────────────────

class TestListaEnlazada:
    """Cubre inserción, recorrido y orden de la lista enlazada."""

    def test_lista_inicia_vacia(self):
        lista = models.Lista_enlazada_asada()
        assert lista.cabeza is None

    def test_agregar_primer_nodo(self, registro_simple):
        lista = models.Lista_enlazada_asada()
        lista.agregar_asada(registro_simple)
        assert lista.cabeza is not None
        assert lista.cabeza.asada is registro_simple

    def test_agregar_multiples_nodos(self, tres_registros):
        lista = models.Lista_enlazada_asada()
        for r in tres_registros:
            lista.agregar_asada(r)

        # Recorrer y contar
        count = 0
        actual = lista.cabeza
        while actual:
            count += 1
            actual = actual.siguiente
        assert count == 3

    def test_orden_de_insercion_fifo(self, tres_registros):
        """El primero en entrar debe ser la cabeza."""
        lista = models.Lista_enlazada_asada()
        for r in tres_registros:
            lista.agregar_asada(r)
        assert lista.cabeza.asada.id_Asada == "500"

    def test_ultimo_nodo_apunta_a_none(self, tres_registros):
        lista = models.Lista_enlazada_asada()
        for r in tres_registros:
            lista.agregar_asada(r)
        actual = lista.cabeza
        while actual.siguiente:
            actual = actual.siguiente
        assert actual.siguiente is None

    def test_mostrar_asadas_no_lanza_excepcion(self, tres_registros, capsys):
        lista = models.Lista_enlazada_asada()
        for r in tres_registros:
            lista.agregar_asada(r)
        lista.mostrar_asadas()          # No debe lanzar AttributeError
        out = capsys.readouterr().out
        assert "500" in out
        assert "200" in out


# ─────────────────────────────────────────────
# 3. TESTS: Arbol_asada / BSB (models.py)
# ─────────────────────────────────────────────

class TestArbolBSB:
    """Verifica inserción y propiedad BSB del árbol binario."""

    def test_arbol_inicia_sin_raiz(self):
        arbol = models.Arbol_asada()
        assert arbol.raiz is None

    def test_primer_elemento_es_raiz(self, registro_simple):
        arbol = models.Arbol_asada()
        arbol.agregar_asada(registro_simple)
        assert arbol.raiz is not None
        assert arbol.raiz.asada.id_Asada == "1537"

    def test_propiedad_bsb_izquierda_menor(self, tres_registros):
        """
        Insertamos: 500 (raíz), 200 (izquierda), 1000 (derecha).
        El nodo izquierdo debe tener id < raíz y el derecho id > raíz.
        """
        arbol = models.Arbol_asada()
        for r in tres_registros:
            arbol.agregar_asada(r)

        raiz = arbol.raiz
        assert int(raiz.izquierda.asada.id_Asada) < int(raiz.asada.id_Asada)
        assert int(raiz.derecha.asada.id_Asada)   > int(raiz.asada.id_Asada)

    def test_insercion_multiples_elementos(self, tres_registros):
        arbol = models.Arbol_asada()
        for r in tres_registros:
            arbol.agregar_asada(r)
        assert arbol.raiz is not None
        assert arbol.raiz.izquierda is not None
        assert arbol.raiz.derecha   is not None

    def test_comparacion_numerica_no_lexicografica(self):
        """
        '9' > '1537' en orden lexicográfico pero 9 < 1537 en numérico.
        El árbol debe colocar id=9 a la IZQUIERDA de id=1537.
        """
        r_grande = models.Registro_asada("X","1537",0,"","","","","","","","","","")
        r_chico  = models.Registro_asada("Y","9",   0,"","","","","","","","","","")

        arbol = models.Arbol_asada()
        arbol.agregar_asada(r_grande)
        arbol.agregar_asada(r_chico)

        assert arbol.raiz.izquierda is not None
        assert arbol.raiz.izquierda.asada.id_Asada == "9"

    def test_elemento_duplicado_va_a_derecha(self):
        """IDs iguales deben ir a la derecha (condición else del árbol)."""
        r1 = models.Registro_asada("A","100",0,"","","","","","","","","","")
        r2 = models.Registro_asada("B","100",0,"","","","","","","","","","")
        arbol = models.Arbol_asada()
        arbol.agregar_asada(r1)
        arbol.agregar_asada(r2)
        assert arbol.raiz.derecha is not None


# ─────────────────────────────────────────────
# 4. TESTS: _dict_a_registro (file_controller.py)
# ─────────────────────────────────────────────

class TestDictARegistro:
    """Verifica la conversión de dict → Registro_asada."""

    def test_conversion_correcta(self):
        r = fc._dict_a_registro(ITEM_VALIDO)
        assert isinstance(r, models.Registro_asada)
        assert r.id_Asada  == "1537"
        assert r.provincia == "ALAJUELA"
        assert r.id_objeto == 3

    def test_campo_faltante_retorna_none(self):
        item_incompleto = {"id_Asada": "999"}
        r = fc._dict_a_registro(item_incompleto)
        assert r.id_Asada  == "999"
        assert r.provincia is None
        assert r.canton    is None

    def test_dict_vacio_retorna_registro_con_nones(self):
        r = fc._dict_a_registro({})
        assert r.id_Asada is None


# ─────────────────────────────────────────────
# 5. TESTS: main_file_bin_controller
# ─────────────────────────────────────────────

class TestMainFileBinController:
    """Cubre guardar y cargar datos crudos (lista de dicts)."""

    def test_guardar_crea_archivo(self, archivo_temp_vacio):
        ctrl = fc.main_file_bin_controller()
        ctrl.save_data_to_binary_file(archivo_temp_vacio, ITEMS_MULTIPLES)
        assert os.path.exists(archivo_temp_vacio)
        assert os.path.getsize(archivo_temp_vacio) > 0

    def test_cargar_retorna_lista_original(self, archivo_temp_vacio):
        ctrl = fc.main_file_bin_controller()
        ctrl.save_data_to_binary_file(archivo_temp_vacio, ITEMS_MULTIPLES)
        cargado = ctrl.load_data_from_binary_file(archivo_temp_vacio)
        assert isinstance(cargado, list)
        assert len(cargado) == len(ITEMS_MULTIPLES)

    def test_integridad_datos_tras_ciclo_guardar_cargar(self, archivo_temp_vacio):
        ctrl = fc.main_file_bin_controller()
        ctrl.save_data_to_binary_file(archivo_temp_vacio, ITEMS_MULTIPLES)
        cargado = ctrl.load_data_from_binary_file(archivo_temp_vacio)
        assert cargado[0]["id_Asada"] == ITEMS_MULTIPLES[0]["id_Asada"]
        assert cargado[1]["provincia"] == ITEMS_MULTIPLES[1]["provincia"]

    def test_guardar_lista_vacia(self, archivo_temp_vacio):
        ctrl = fc.main_file_bin_controller()
        ctrl.save_data_to_binary_file(archivo_temp_vacio, [])
        cargado = ctrl.load_data_from_binary_file(archivo_temp_vacio)
        assert cargado == []

    def test_cargar_archivo_inexistente_lanza_error(self):
        ctrl = fc.main_file_bin_controller()
        with pytest.raises(FileNotFoundError):
            ctrl.load_data_from_binary_file("/ruta/que/no/existe.bin")


# ─────────────────────────────────────────────
# 6. TESTS: liked_list_bin_controller
# ─────────────────────────────────────────────

class TestLikedListBinController:
    """Cubre guardar y cargar hacia lista enlazada."""

    def test_guardar_crea_archivo(self, archivo_temp_vacio):
        ctrl = fc.liked_list_bin_controller()
        ctrl.save_data_to_binary_file(archivo_temp_vacio, ITEMS_MULTIPLES)
        assert os.path.getsize(archivo_temp_vacio) > 0

    def test_cargar_retorna_lista_enlazada(self, archivo_temp_con_datos):
        ctrl = fc.liked_list_bin_controller()
        lista = ctrl.load_data_from_binary_file_to_linked_list(archivo_temp_con_datos)
        assert isinstance(lista, models.Lista_enlazada_asada)
        assert lista.cabeza is not None

    def test_cantidad_nodos_correcta(self, archivo_temp_con_datos):
        ctrl = fc.liked_list_bin_controller()
        lista = ctrl.load_data_from_binary_file_to_linked_list(archivo_temp_con_datos)
        count = 0
        actual = lista.cabeza
        while actual:
            count += 1
            actual = actual.siguiente
        assert count == len(ITEMS_MULTIPLES)

    def test_nodos_son_registro_asada(self, archivo_temp_con_datos):
        ctrl = fc.liked_list_bin_controller()
        lista = ctrl.load_data_from_binary_file_to_linked_list(archivo_temp_con_datos)
        assert isinstance(lista.cabeza.asada, models.Registro_asada)

    def test_file_model_actualizado(self, archivo_temp_con_datos):
        ctrl = fc.liked_list_bin_controller()
        ctrl.load_data_from_binary_file_to_linked_list(archivo_temp_con_datos)
        assert ctrl.file_model is not None
        assert ctrl.file_model.cabeza is not None


# ─────────────────────────────────────────────
# 7. TESTS: binary_tree_bin_controller
# ─────────────────────────────────────────────

class TestBinaryTreeBinController:
    """Cubre guardar y cargar hacia árbol BSB."""

    def test_guardar_crea_archivo(self, archivo_temp_vacio):
        ctrl = fc.binary_tree_bin_controller()
        ctrl.save_data_to_binary_file(archivo_temp_vacio, ITEMS_MULTIPLES)
        assert os.path.getsize(archivo_temp_vacio) > 0

    def test_cargar_retorna_arbol(self, archivo_temp_con_datos):
        ctrl = fc.binary_tree_bin_controller()
        arbol = ctrl.load_data_from_binary_file_to_binary_tree(archivo_temp_con_datos)
        assert isinstance(arbol, models.Arbol_asada)

    def test_raiz_no_es_none(self, archivo_temp_con_datos):
        ctrl = fc.binary_tree_bin_controller()
        arbol = ctrl.load_data_from_binary_file_to_binary_tree(archivo_temp_con_datos)
        assert arbol.raiz is not None

    def test_raiz_es_primer_elemento_insertado(self, archivo_temp_con_datos):
        """El primero en la lista (id=500) debe ser la raíz."""
        ctrl = fc.binary_tree_bin_controller()
        arbol = ctrl.load_data_from_binary_file_to_binary_tree(archivo_temp_con_datos)
        assert arbol.raiz.asada.id_Asada == "500"

    def test_bsb_correcto_en_arbol_cargado(self, archivo_temp_con_datos):
        ctrl = fc.binary_tree_bin_controller()
        arbol = ctrl.load_data_from_binary_file_to_binary_tree(archivo_temp_con_datos)
        raiz = arbol.raiz
        assert int(raiz.izquierda.asada.id_Asada) < int(raiz.asada.id_Asada)
        assert int(raiz.derecha.asada.id_Asada)   > int(raiz.asada.id_Asada)

    def test_file_model_actualizado(self, archivo_temp_con_datos):
        ctrl = fc.binary_tree_bin_controller()
        ctrl.load_data_from_binary_file_to_binary_tree(archivo_temp_con_datos)
        assert ctrl.file_model is not None
        assert ctrl.file_model.raiz is not None


# ─────────────────────────────────────────────
# 8. TESTS: AsadaApi (con mock — sin llamada real)
# ─────────────────────────────────────────────

class TestAsadaApi:
    """
    Usa unittest.mock para simular el endpoint real.
    Así los tests corren sin internet y de forma determinista.
    """

    RESPUESTA_VALIDA = {
        "value": [ITEM_VALIDO, {**ITEM_VALIDO, "id_Asada": "999"}]
    }

    def _mock_get(self, json_data, status=200):
        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.json.return_value = json_data
        return mock_resp

    def test_get_data_retorna_dict(self):
        api = AsadaApi()
        with patch("requests.get", return_value=self._mock_get(self.RESPUESTA_VALIDA)):
            data = api.get_data()
        assert isinstance(data, dict)
        assert "value" in data

    def test_get_asadas_values_retorna_lista(self):
        api = AsadaApi()
        with patch("requests.get", return_value=self._mock_get(self.RESPUESTA_VALIDA)):
            valores = api.get_asadas_values()
        assert isinstance(valores, list)
        assert len(valores) == 2

    def test_get_asadas_values_contiene_campos_requeridos(self):
        api = AsadaApi()
        with patch("requests.get", return_value=self._mock_get(self.RESPUESTA_VALIDA)):
            valores = api.get_asadas_values()
        for campo in ["id_Asada", "operador", "provincia", "canton", "distrito"]:
            assert campo in valores[0]

    def test_error_http_lanza_excepcion(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("500 Server Error")
        api = AsadaApi()
        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(Exception, match="500 Server Error"):
                api.get_data()

    def test_respuesta_sin_clave_value_lanza_value_error(self):
        api = AsadaApi()
        with patch("requests.get", return_value=self._mock_get({"oops": []})):
            with pytest.raises(ValueError, match="Respuesta inesperada"):
                api.get_asadas_values()

    def test_url_no_tiene_espacio_final(self):
        api = AsadaApi()
        assert not api.base_url.endswith(" "), "La URL no debe terminar con espacio"

    def test_url_es_https(self):
        api = AsadaApi()
        assert api.base_url.startswith("https://")
