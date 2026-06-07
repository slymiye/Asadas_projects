# Este script genera un mapa HTML utilizando la biblioteca Folium, a partir de coordenadas en el sistema de referencia CRTM05, que se convierten a WGS84 para su visualización en el mapa.
# Al final abre desde el navegador predeterminado el archivo HTML generado.
import json
import webbrowser
from pathlib import Path
import folium
from pyproj import Transformer

#leer del archivo JSON
with open("asadas.json", "r", encoding="utf-8") as archivo:
    datos = json.load(archivo)

# Coordenadas CRTM05
x_crtm05 = 0
y_crtm05 = 0

#Busca la asada 1790 correspondiente a la asada de cuestillas y extrae sus coordenadas CRTM05
for asada in datos['value']:
    if asada['id_Asada']   == "1790":
        x_crtm05 = asada['coordenadaX']
        y_crtm05 = asada['coordenadaY']

# Convertir CRTM05 -> WGS84
transformador = Transformer.from_crs(
    "EPSG:5367",   # CRTM05
    "EPSG:4326",   # WGS84
    always_xy=True
)

# Transformar coordenadas
longitud, latitud = transformador.transform(x_crtm05, y_crtm05)

print(latitud, longitud)

# Crear mapa
mapa = folium.Map(
    location=[latitud, longitud],
    zoom_start=15
)

# Agregar marcador
folium.Marker(
    [latitud, longitud],
    popup="Ubicación CRTM05",
    tooltip="ASADA"
).add_to(mapa)

# Guardar HTML
mapa.save("mapa.html")

# Obtener ruta absoluta del archivo HTML
ruta = Path("mapa.html").resolve()

# Abrir navegador predeterminado
webbrowser.open(f"file://{ruta}")

print("Mapa generado")