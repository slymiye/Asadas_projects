"""
models.py
---------
Define la estructura de datos de un registro ASADA y el nodo del árbol BSB.
"""

import struct

# ─────────────────────────────────────────────────────────────
# Tamaños fijos de cada campo en el archivo binario principal.
# Todos los strings se almacenan con padding de espacios.
# ─────────────────────────────────────────────────────────────
FIELD_SIZES = {
    "canton":      50,
    "codigoDTA":    4,   # int de 4 bytes (struct int)
    "coordenadaX": 20,
    "coordenadaY": 20,
    "correo":      80,
    "distrito":    60,
    "fax":         20,
    "id_Asada":    10,
    "id_Objecto":   4,   # int de 4 bytes
    "operador":   120,
    "provincia":   40,
    "telefono":    20,
    "tipoSistema": 30,
}

# Tamaño total de un registro en bytes
RECORD_SIZE = (
    FIELD_SIZES["canton"] +
    FIELD_SIZES["codigoDTA"] +
    FIELD_SIZES["coordenadaX"] +
    FIELD_SIZES["coordenadaY"] +
    FIELD_SIZES["correo"] +
    FIELD_SIZES["distrito"] +
    FIELD_SIZES["fax"] +
    FIELD_SIZES["id_Asada"] +
    FIELD_SIZES["id_Objecto"] +
    FIELD_SIZES["operador"] +
    FIELD_SIZES["provincia"] +
    FIELD_SIZES["telefono"] +
    FIELD_SIZES["tipoSistema"]
)

TIPOS_NODO_LISTA = (
    {1:"provincia"},
    {2:"canton"},
    {3:"distrito"}, 
    {4:"asada"}
    )

def _encode_str(value, size):
    """Codifica un string a bytes con padding, truncando si es necesario."""
    s = str(value) if value is not None else ""
    return s.encode("utf-8")[:size].ljust(size)


def _decode_str(data):
    """Decodifica bytes a string eliminando padding."""
    return data.decode("utf-8", errors="replace").strip()


def _encode_int(value):
    """Codifica un entero en 4 bytes."""
    try:
        return struct.pack(">i", int(value))
    except (ValueError, TypeError):
        return struct.pack(">i", 0)


def _decode_int(data):
    """Decodifica 4 bytes a entero."""
    return struct.unpack(">i", data)[0]


class Registro_asada:
    """Representa un registro completo de una ASADA."""

    def __init__(self, canton, codigoDTA, coordenadaX, coordenadaY,
                 correo, distrito, fax, id_Asada, id_Objecto,
                 operador, provincia, telefono, tipoSistema):
        self.canton      = str(canton)      if canton      is not None else ""
        self.codigoDTA   = int(codigoDTA)   if codigoDTA   is not None else 0
        self.coordenadaX = str(coordenadaX) if coordenadaX is not None else ""
        self.coordenadaY = str(coordenadaY) if coordenadaY is not None else ""
        self.correo      = str(correo)      if correo      is not None else ""
        self.distrito    = str(distrito)    if distrito    is not None else ""
        self.fax         = str(fax)         if fax         is not None else ""
        self.id_Asada    = str(id_Asada)    if id_Asada    is not None else ""
        self.id_Objecto  = int(id_Objecto)  if id_Objecto  is not None else 0
        self.operador    = str(operador)    if operador    is not None else ""
        self.provincia   = str(provincia)   if provincia   is not None else ""
        self.telefono    = str(telefono)    if telefono    is not None else ""
        self.tipoSistema = str(tipoSistema) if tipoSistema is not None else ""

    @staticmethod
    def from_dict(d: dict) -> "Registro_asada":
        """Construye un Registro_asada desde un dict del API."""
        return Registro_asada(
            canton      = d.get("canton"),
            codigoDTA   = d.get("codigoDTA"),
            coordenadaX = d.get("coordenadaX"),
            coordenadaY = d.get("coordenadaY"),
            correo      = d.get("correo"),
            distrito    = d.get("distrito"),
            fax         = d.get("fax"),
            id_Asada    = d.get("id_Asada"),
            id_Objecto  = d.get("id_Objecto"),
            operador    = d.get("operador"),
            provincia   = d.get("provincia"),
            telefono    = d.get("telefono"),
            tipoSistema = d.get("tipoSistema"),
        )

    def to_bytes(self) -> bytes:
        """Serializa el registro a RECORD_SIZE bytes (tamaño fijo)."""
        return (
            _encode_str(self.canton,      FIELD_SIZES["canton"])      +
            _encode_int(self.codigoDTA)                               +
            _encode_str(self.coordenadaX, FIELD_SIZES["coordenadaX"]) +
            _encode_str(self.coordenadaY, FIELD_SIZES["coordenadaY"]) +
            _encode_str(self.correo,      FIELD_SIZES["correo"])      +
            _encode_str(self.distrito,    FIELD_SIZES["distrito"])    +
            _encode_str(self.fax,         FIELD_SIZES["fax"])         +
            _encode_str(self.id_Asada,    FIELD_SIZES["id_Asada"])    +
            _encode_int(self.id_Objecto)                              +
            _encode_str(self.operador,    FIELD_SIZES["operador"])    +
            _encode_str(self.provincia,   FIELD_SIZES["provincia"])   +
            _encode_str(self.telefono,    FIELD_SIZES["telefono"])    +
            _encode_str(self.tipoSistema, FIELD_SIZES["tipoSistema"])
        )

    @staticmethod
    def from_bytes(data: bytes) -> "Registro_asada":
        """Deserializa RECORD_SIZE bytes a un Registro_asada."""
        offset = 0

        def read_str(size):
            nonlocal offset
            val = _decode_str(data[offset:offset + size])
            offset += size
            return val

        def read_int():
            nonlocal offset
            val = _decode_int(data[offset:offset + 4])
            offset += 4
            return val

        canton      = read_str(FIELD_SIZES["canton"])
        codigoDTA   = read_int()
        coordenadaX = read_str(FIELD_SIZES["coordenadaX"])
        coordenadaY = read_str(FIELD_SIZES["coordenadaY"])
        correo      = read_str(FIELD_SIZES["correo"])
        distrito    = read_str(FIELD_SIZES["distrito"])
        fax         = read_str(FIELD_SIZES["fax"])
        id_Asada    = read_str(FIELD_SIZES["id_Asada"])
        id_Objecto  = read_int()
        operador    = read_str(FIELD_SIZES["operador"])
        provincia   = read_str(FIELD_SIZES["provincia"])
        telefono    = read_str(FIELD_SIZES["telefono"])
        tipoSistema = read_str(FIELD_SIZES["tipoSistema"])

        return Registro_asada(canton, codigoDTA, coordenadaX, coordenadaY,
                              correo, distrito, fax, id_Asada, id_Objecto,
                              operador, provincia, telefono, tipoSistema)

    def __repr__(self):
        return (f"Registro_asada(id={self.id_Asada}, "
                f"operador={self.operador[:30]}, "
                f"provincia={self.provincia})")


# ─────────────────────────────────────────────────────────────
# Nodo del árbol BSB (índice)
# Cada nodo guarda: id_Asada, posición en el archivo principal,
# índice lógico del hijo izquierdo y del derecho (-1 = vacío).
# ─────────────────────────────────────────────────────────────

# Formato del nodo en el archivo de índice:
#   id_Asada  : 10 bytes (string con padding)
#   position  :  8 bytes (long long — posición en bytes en el archivo principal)
#   left_idx  :  4 bytes (int — índice del nodo izquierdo, -1 si no hay)
#   right_idx :  4 bytes (int — índice del nodo derecho,  -1 si no hay)
NODE_SIZE = 10 + 8 + 4 + 4   # = 26 bytes por nodo


class NodoArbol:
    """Nodo del árbol BSB en memoria."""

    def __init__(self, id_Asada: str, position: int, index: int = -1):
        self.id_Asada  = id_Asada   # llave de búsqueda
        self.position  = position   # posición en bytes dentro del archivo principal
        self.index     = index      # posición de ESTE nodo en el archivo de índice
        self.left_idx  = -1         # índice del hijo izquierdo (-1 = ninguno)
        self.right_idx = -1         # índice del hijo derecho  (-1 = ninguno)

    def to_bytes(self) -> bytes:
        return (
            _encode_str(self.id_Asada, 10) +
            struct.pack(">q", self.position) +
            struct.pack(">i", self.left_idx) +
            struct.pack(">i", self.right_idx)
        )

    @staticmethod
    def from_bytes(data: bytes, index: int) -> "NodoArbol":
        id_Asada  = _decode_str(data[0:10])
        position  = struct.unpack(">q", data[10:18])[0]
        left_idx  = struct.unpack(">i", data[18:22])[0]
        right_idx = struct.unpack(">i", data[22:26])[0]
        nodo = NodoArbol(id_Asada, position, index)
        nodo.left_idx  = left_idx
        nodo.right_idx = right_idx
        return nodo

    def __repr__(self):
        return (f"Nodo(id={self.id_Asada}, pos={self.position}, "
                f"L={self.left_idx}, R={self.right_idx})")

class NodoListaJerarquica:
    """Nodo para la lista jerárquica de ASADAS por provincia."""

    def __init__(self,tipo):
        self.tipo  = TIPOS_NODO_LISTA[tipo-1]  # tipo es un entero del 1 al 4
        self.nombre = ""  # nombre de la provincia/cantón/distrito/asada
        self.siguiente  = None  # puntero al siguiente nodo en la lista