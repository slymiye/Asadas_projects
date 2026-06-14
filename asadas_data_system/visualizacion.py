"""
visualizacion.py
----------------
Módulo de visualización geográfica de ASADAS

Funciones principales:
  - convertir_crtm05_a_wgs84()  : Transforma coordenadas CRTM05 → WGS84.
  - generar_mapa_todas()         : Mapa con TODAS las ASADAS del sistema.
  - generar_mapa_por_ubicacion() : Mapa filtrado por provincia/cantón/distrito.
  - generar_mapa_una_asada()     : Mapa de una ASADA individual por id_Asada.
  - abrir_mapa()                 : Abre el HTML generado en el navegador.

Uso típico desde sistema.py o el cliente:
    from visualizacion import VisualizadorAsadas
    vis = VisualizadorAsadas(sistema)
    vis.mostrar_todas()
    vis.mostrar_por_ubicacion("ALAJUELA", "SAN CARLOS", "FLORENCIA")
    vis.mostrar_una("1790")
"""

import os
import tempfile
import webbrowser
from pathlib import Path

import folium
from folium.plugins import MarkerCluster
from pyproj import Transformer

# ─────────────────────────────────────────────────────────────
# Transformador de coordenadas CRTM05 (EPSG:5367) → WGS84 (EPSG:4326)
# Se instancia una sola vez para evitar overhead repetido.
# ─────────────────────────────────────────────────────────────
_TRANSFORMADOR = Transformer.from_crs(
    "EPSG:5367",   # CRTM05 — sistema oficial de Costa Rica
    "EPSG:4326",   # WGS84  — latitud / longitud
    always_xy=True
)

# Centro geográfico aproximado de Costa Rica (fallback cuando no hay datos)
_CENTRO_COSTA_RICA = (9.7489, -83.7534)

# Colores por provincia para diferenciar marcadores en el mapa general
_COLORES_PROVINCIA = {
    "SAN JOSÉ":    "red",
    "ALAJUELA":    "blue",
    "CARTAGO":     "green",
    "HEREDIA":     "purple",
    "GUANACASTE":  "orange",
    "PUNTARENAS":  "pink",
    "LIMÓN":       "darkblue",
}
_COLOR_DEFAULT = "gray"


# ══════════════════════════════════════════════════════════════
# Funciones utilitarias de coordenadas
# ══════════════════════════════════════════════════════════════

def convertir_crtm05_a_wgs84(x: str | float, y: str | float) -> tuple[float, float] | None:
    """
    Convierte coordenadas CRTM05 (X, Y) a WGS84 (latitud, longitud).

    Args:
        x: Coordenada X en CRTM05 (puede ser str o float).
        y: Coordenada Y en CRTM05 (puede ser str o float).

    Returns:
        Tupla (latitud, longitud) en WGS84, o None si la conversión falla.
    """
    try:
        x_f = float(str(x).strip())
        y_f = float(str(y).strip())

        # Validar que las coordenadas no sean cero (dato vacío/inválido)
        if x_f == 0.0 or y_f == 0.0:
            return None

        # CRTM05 usa always_xy=True → primer arg = X (longitud plana), segundo = Y (latitud plana)
        lon, lat = _TRANSFORMADOR.transform(x_f, y_f)

        # Validar que el resultado caiga dentro de Costa Rica (bounding box aproximado)
        if not (8.0 <= lat <= 11.3 and -86.0 <= lon <= -82.5):
            return None

        return (lat, lon)

    except (ValueError, TypeError, Exception):
        return None


def _color_provincia(provincia: str) -> str:
    """Retorna el color Folium asignado a la provincia dada."""
    return _COLORES_PROVINCIA.get(provincia.strip().upper(), _COLOR_DEFAULT)


def _popup_html(reg) -> str:
    """
    Genera el HTML del popup de un marcador a partir de un Registro_asada.

    Args:
        reg: Instancia de Registro_asada.

    Returns:
        String HTML con los datos formateados del registro.
    """
    def fila(etiqueta: str, valor: str) -> str:
        valor = valor.strip() if valor else "—"
        return f"<tr><td><b>{etiqueta}</b></td><td>{valor}</td></tr>"

    html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 13px; min-width: 250px;">
        <h4 style="margin:0 0 6px 0; color:#1a5276;">ASADA #{reg.id_Asada}</h4>
        <table style="border-collapse: collapse; width:100%;">
            {fila("Operador",    reg.operador)}
            {fila("Provincia",   reg.provincia)}
            {fila("Cantón",      reg.canton)}
            {fila("Distrito",    reg.distrito)}
            {fila("Tipo",        reg.tipoSistema)}
            {fila("Teléfono",    reg.telefono)}
            {fila("Correo",      reg.correo)}
        </table>
    </div>
    """
    return html


def _tooltip_texto(reg) -> str:
    """Genera el texto del tooltip (hover) para un marcador."""
    operador = (reg.operador[:40] + "…") if len(reg.operador) > 40 else reg.operador
    return f"[{reg.id_Asada}] {operador}"


# ══════════════════════════════════════════════════════════════
# Funciones principales de generación de mapas
# ══════════════════════════════════════════════════════════════

def generar_mapa_todas(registros: list, titulo: str = "ASADAS de Costa Rica") -> folium.Map:
    """
    Genera un mapa Folium con TODAS las ASADAS del sistema agrupadas
    por clusters interactivos. Los marcadores se colorean por provincia.

    Args:
        registros : Lista de Registro_asada con todos los datos.
        titulo    : Título que aparece en el panel lateral del mapa.

    Returns:
        Objeto folium.Map listo para guardar o mostrar.
    """
    # Calcular centro del mapa con el promedio de coordenadas válidas
    coords_validas = []
    for reg in registros:
        punto = convertir_crtm05_a_wgs84(reg.coordenadaX, reg.coordenadaY)
        if punto:
            coords_validas.append(punto)

    if coords_validas:
        lat_c = sum(c[0] for c in coords_validas) / len(coords_validas)
        lon_c = sum(c[1] for c in coords_validas) / len(coords_validas)
        centro = (lat_c, lon_c)
        zoom   = 8
    else:
        centro = _CENTRO_COSTA_RICA
        zoom   = 8

    mapa = folium.Map(location=centro, zoom_start=zoom,
                      tiles="OpenStreetMap")

    # Agregar título al mapa
    titulo_html = f"""
    <div style="position:fixed; top:10px; left:50%; transform:translateX(-50%);
                z-index:1000; background:white; padding:8px 18px;
                border-radius:8px; box-shadow:2px 2px 6px rgba(0,0,0,0.3);
                font-family:Arial; font-size:16px; font-weight:bold; color:#1a5276;">
        🗺️ {titulo}
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(titulo_html))

    # Panel de leyenda de colores por provincia
    leyenda_filas = "".join(
        f'<div><span style="background:{color};display:inline-block;'
        f'width:14px;height:14px;border-radius:50%;margin-right:6px;"></span>'
        f'{prov.title()}</div>'
        for prov, color in _COLORES_PROVINCIA.items()
    )
    leyenda_html = f"""
    <div style="position:fixed; bottom:30px; left:15px; z-index:1000;
                background:white; padding:10px 14px; border-radius:8px;
                box-shadow:2px 2px 6px rgba(0,0,0,0.3);
                font-family:Arial; font-size:12px; line-height:1.8;">
        <b>Provincias</b><br>{leyenda_filas}
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(leyenda_html))

    # Cluster de marcadores para rendimiento con muchos puntos
    cluster = MarkerCluster(name="ASADAS").add_to(mapa)

    sin_coords = 0
    con_coords = 0
    for reg in registros:
        punto = convertir_crtm05_a_wgs84(reg.coordenadaX, reg.coordenadaY)
        if punto is None:
            sin_coords += 1
            continue

        color = _color_provincia(reg.provincia)
        folium.Marker(
            location=punto,
            popup=folium.Popup(
                folium.IFrame(_popup_html(reg), width=300, height=200),
                max_width=320
            ),
            tooltip=_tooltip_texto(reg),
            icon=folium.Icon(color=color, icon="tint", prefix="fa")
        ).add_to(cluster)
        con_coords += 1

    # Contador de ASADAS en mapa
    contador_html = f"""
    <div style="position:fixed; top:60px; right:15px; z-index:1000;
                background:#1a5276; color:white; padding:8px 14px;
                border-radius:8px; font-family:Arial; font-size:12px; line-height:1.6;">
        <b>Total ASADAS:</b> {len(registros)}<br>
        <b>En mapa:</b> {con_coords}<br>
        <b>Sin coordenadas:</b> {sin_coords}
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(contador_html))

    return mapa


def generar_mapa_por_ubicacion(
    registros: list,
    provincia: str,
    canton: str   = "",
    distrito: str = "",
) -> folium.Map:
    """
    Genera un mapa Folium con las ASADAS filtradas por división política.

    Args:
        registros : Lista de Registro_asada ya filtrada (resultante de
                    sistema.listar_asadas_por_ubicacion o listar_todos).
        provincia : Nombre de la provincia (para el título).
        canton    : Nombre del cantón (opcional, para el título).
        distrito  : Nombre del distrito (opcional, para el título).

    Returns:
        Objeto folium.Map.
    """
    # Construir título dinámico
    partes = [p for p in [provincia, canton, distrito] if p.strip()]
    titulo = " › ".join(p.title() for p in partes)

    # Calcular centro a partir de los registros filtrados
    coords_validas = []
    for reg in registros:
        punto = convertir_crtm05_a_wgs84(reg.coordenadaX, reg.coordenadaY)
        if punto:
            coords_validas.append(punto)

    if coords_validas:
        lat_c = sum(c[0] for c in coords_validas) / len(coords_validas)
        lon_c = sum(c[1] for c in coords_validas) / len(coords_validas)
        centro = (lat_c, lon_c)
        zoom   = 12 if distrito else (10 if canton else 9)
    else:
        centro = _CENTRO_COSTA_RICA
        zoom   = 9

    mapa = folium.Map(location=centro, zoom_start=zoom,
                      tiles="OpenStreetMap")

    # Título del mapa
    titulo_html = f"""
    <div style="position:fixed; top:10px; left:50%; transform:translateX(-50%);
                z-index:1000; background:white; padding:8px 18px;
                border-radius:8px; box-shadow:2px 2px 6px rgba(0,0,0,0.3);
                font-family:Arial; font-size:15px; font-weight:bold; color:#1a5276;">
        📍 {titulo}
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(titulo_html))

    sin_coords = 0
    for reg in registros:
        punto = convertir_crtm05_a_wgs84(reg.coordenadaX, reg.coordenadaY)
        if punto is None:
            sin_coords += 1
            continue

        folium.Marker(
            location=punto,
            popup=folium.Popup(
                folium.IFrame(_popup_html(reg), width=300, height=200),
                max_width=320
            ),
            tooltip=_tooltip_texto(reg),
            icon=folium.Icon(color="blue", icon="tint", prefix="fa")
        ).add_to(mapa)

    # Info de resultados
    con_coords = len(registros) - sin_coords
    info_html = f"""
    <div style="position:fixed; top:60px; right:15px; z-index:1000;
                background:#1a5276; color:white; padding:8px 14px;
                border-radius:8px; font-family:Arial; font-size:12px; line-height:1.6;">
        <b>ASADAS encontradas:</b> {len(registros)}<br>
        <b>Ubicadas en mapa:</b> {con_coords}<br>
        <b>Sin coordenadas:</b> {sin_coords}
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(info_html))

    return mapa


def generar_mapa_una_asada(reg) -> folium.Map:
    """
    Genera un mapa Folium centrado en una única ASADA con zoom detallado.

    Args:
        reg: Instancia de Registro_asada de la ASADA a visualizar.

    Returns:
        Objeto folium.Map, o None si la ASADA no tiene coordenadas válidas.
    """
    punto = convertir_crtm05_a_wgs84(reg.coordenadaX, reg.coordenadaY)

    if punto is None:
        return None

    mapa = folium.Map(location=punto, zoom_start=15,
                      tiles="OpenStreetMap")

    # Marcador principal
    folium.Marker(
        location=punto,
        popup=folium.Popup(
            folium.IFrame(_popup_html(reg), width=300, height=220),
            max_width=320
        ),
        tooltip=_tooltip_texto(reg),
        icon=folium.Icon(color="red", icon="tint", prefix="fa")
    ).add_to(mapa)

    # Círculo de área aproximada
    folium.Circle(
        location=punto,
        radius=500,
        color="#1a5276",
        fill=True,
        fill_opacity=0.08,
        tooltip=f"Área de influencia aprox. ASADA #{reg.id_Asada}"
    ).add_to(mapa)

    # Tarjeta de información
    info_html = f"""
    <div style="position:fixed; top:10px; left:50%; transform:translateX(-50%);
                z-index:1000; background:white; padding:10px 20px;
                border-radius:8px; box-shadow:2px 2px 8px rgba(0,0,0,0.3);
                font-family:Arial; font-size:14px; color:#1a5276; text-align:center;">
        <b>ASADA #{reg.id_Asada}</b><br>
        <span style="font-size:12px; color:#555;">{reg.operador[:50]}</span>
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(info_html))

    return mapa


# ══════════════════════════════════════════════════════════════
# Apertura automática del mapa en el navegador
# ══════════════════════════════════════════════════════════════

def abrir_mapa(mapa: folium.Map, nombre_archivo: str = "mapa_asadas.html"):
    """
    Guarda el mapa como HTML en el directorio del proyecto y lo abre
    automáticamente en el navegador predeterminado del sistema.
    """
    # Guardar junto a los archivos del proyecto (accesible por el navegador)
    ruta = Path(os.path.dirname(os.path.abspath(__file__))) / nombre_archivo
    mapa.save(str(ruta))
    webbrowser.open(ruta.as_uri())
    print(f"  ✓ Mapa guardado en: {ruta}")
    print(f"  ✓ Abriendo en el navegador...")
    """
    Guarda el mapa como HTML en un directorio temporal y lo abre
    automáticamente en el navegador predeterminado del sistema.

    Args:
        mapa          : Objeto folium.Map a renderizar.
        nombre_archivo: Nombre del archivo HTML generado.
    """
    ruta = Path(tempfile.gettempdir()) / nombre_archivo
    mapa.save(str(ruta))
    webbrowser.open(ruta.as_uri())
    print(f"  ✓ Mapa guardado en: {ruta}")
    print(f"  ✓ Abriendo en el navegador...")


# ══════════════════════════════════════════════════════════════
# Clase fachada: VisualizadorAsadas
# ══════════════════════════════════════════════════════════════

class VisualizadorAsadas:
    """
    Fachada de visualización geográfica integrada con Sistema_Datos_Asadas.

    Ejemplo de uso:
        from sistema import Sistema_Datos_Asadas
        from visualizacion import VisualizadorAsadas

        sistema = Sistema_Datos_Asadas()
        sistema.inicializar()

        vis = VisualizadorAsadas(sistema)
        vis.mostrar_todas()
        vis.mostrar_por_ubicacion("ALAJUELA", "SAN CARLOS", "FLORENCIA")
        vis.mostrar_una("1790")
    """

    def __init__(self, sistema):
        """
        Args:
            sistema: Instancia de Sistema_Datos_Asadas ya inicializada.
        """
        self._sistema = sistema

    # ── mostrar todos ─────────────────────────────────────────

    def mostrar_todas(self):
        """
        Genera y abre un mapa con TODAS las ASADAS registradas en el sistema,
        agrupadas en clusters interactivos.
        """
        print("Generando mapa con todas las ASADAS...")
        registros = self._sistema.listar_todos()

        if not registros:
            print("  ✗ No hay registros disponibles. Ejecute sistema.inicializar() primero.")
            return

        mapa = generar_mapa_todas(registros)
        abrir_mapa(mapa, "mapa_todas_asadas.html")

    # ── mostrar por ubicación ────────────────────────────────

    def mostrar_por_ubicacion(
        self,
        provincia: str,
        canton:    str = "",
        distrito:  str = "",
    ):
        """
        Genera y abre un mapa con las ASADAS del área geográfica indicada.

        Si se provee solo provincia → muestra TODAS las ASADAS de esa provincia.
        Si se provee provincia + cantón → muestra las del cantón.
        Si se provee provincia + cantón + distrito → muestra las del distrito.

        Args:
            provincia: Nombre de la provincia (obligatorio).
            canton   : Nombre del cantón (opcional).
            distrito : Nombre del distrito (opcional).
        """
        provincia = provincia.strip().upper()
        canton    = canton.strip().upper()
        distrito  = distrito.strip().upper()

        print(f"Generando mapa para: {provincia}"
              + (f" › {canton.title()}" if canton else "")
              + (f" › {distrito.title()}" if distrito else "") + "...")

        # Selección del conjunto de registros según el nivel de filtro
        if distrito and canton:
            registros = self._sistema.listar_asadas_por_ubicacion(
                provincia, canton, distrito
            )
        elif canton:
            # Iterar todos los distritos del cantón
            registros = []
            for dist in self._sistema.listar_distritos(provincia, canton):
                registros.extend(
                    self._sistema.listar_asadas_por_ubicacion(
                        provincia, canton, dist
                    )
                )
        else:
            # Iterar todos los cantones de la provincia
            registros = []
            for cant in self._sistema.listar_cantones(provincia):
                for dist in self._sistema.listar_distritos(provincia, cant):
                    registros.extend(
                        self._sistema.listar_asadas_por_ubicacion(
                            provincia, cant, dist
                        )
                    )

        if not registros:
            print(f"  ✗ No se encontraron ASADAS para la ubicación indicada.")
            return

        print(f"  → {len(registros)} ASADA(s) encontrada(s).")
        mapa = generar_mapa_por_ubicacion(registros, provincia, canton, distrito)
        nombre = f"mapa_{provincia.lower().replace(' ','_')}"
        if canton:
            nombre += f"_{canton.lower().replace(' ','_')}"
        if distrito:
            nombre += f"_{distrito.lower().replace(' ','_')}"
        nombre += ".html"
        abrir_mapa(mapa, nombre)

    # ── mostrar una ASADA ─────────────────────────────────────

    def mostrar_una(self, id_asada: str):
        """
        Genera y abre un mapa centrado en la ASADA con el id indicado.

        Args:
            id_asada: Identificador numérico de la ASADA (string o int).
        """
        id_asada = str(id_asada).strip()
        print(f"Buscando ASADA con id {id_asada}...")

        reg = self._sistema.buscar_por_id(id_asada)
        if reg is None:
            print(f"  ✗ ASADA con id {id_asada} no encontrada.")
            return

        print(f"  → Encontrada: {reg.operador[:50]}")
        mapa = generar_mapa_una_asada(reg)

        if mapa is None:
            print(f"  ✗ La ASADA #{id_asada} no tiene coordenadas geográficas válidas.")
            return

        abrir_mapa(mapa, f"mapa_asada_{id_asada}.html")


def main_prueba():
    """
    Función de prueba para generar mapas de ejemplo usando datos del sistema.

    Asegúrese de ejecutar sistema.inicializar() antes de llamar a esta función.
    """
    import sistema

    sistem = sistema.Sistema_Datos_Asadas()
    sistem.inicializar()

    vis = VisualizadorAsadas(sistem)
    vis.mostrar_todas()
    vis.mostrar_por_ubicacion("ALAJUELA", "SAN CARLOS", "FLORENCIA")
    vis.mostrar_una("1790")

main_prueba()