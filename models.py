'''
{
            "canton": "UPALA",
            "codigoDTA": 21303,
            "coordenadaX": "364776 ",
            "coordenadaY": " 1215603",
            "correo": "SIN INFORMACIÓN",
            "distrito": "SAN JOSÉ O PIZOTE",
            "fax": "SIN INFORMACIÓN",
            "id_Asada": "1537",
            "id_Objecto": 3,
            "operador": "00023-2014_EL PROGRESO DE SAN JOSE DE UPALA, ALAJUELA",
            "provincia": "ALAJUELA",
            "telefono": "87186088",
            "tipoSistema": "GRAVEDAD"
        },
'''


class Registro_asada:
    def __init__(
                self,
                codigoDTA,
                id_Asada, id_objeto, 
                cordY, cordX,
                provincia,canton,distrito,
                telefono,correo, fax,
                tipoSistema,
                operador
                ):
        
        self.id_Asada = id_Asada
        self.provincia = provincia
        self.canton = canton
        self.distrito = distrito
        self.telefono = telefono
        self.correo = correo
        self.fax = fax
        self.tipoSistema = tipoSistema
        self.operador = operador
        self.codigoDTA = codigoDTA
        self.id_objeto = id_objeto
        self.cordY = cordY
        self.cordX = cordX


class Nodo_asada:
    def __init__(self, asada):
        self.asada = asada
        self.siguiente = None


class Nodo_asada_arbol:
    def __init__(self, asada):
        self.asada = asada
        self.izquierda = None
        self.derecha = None


class Arbol_asada:
    def __init__(self):
        self.raiz = None

    def agregar_asada(self, asada):
        if self.raiz is None:
            self.raiz = Nodo_asada_arbol(asada)
        else:
            self._agregar_asada_recursivo(self.raiz, asada)

    def _agregar_asada_recursivo(self, nodo_actual, asada):
        if int(asada.id_Asada) < int(nodo_actual.asada.id_Asada):
            if nodo_actual.izquierda is None:
                nodo_actual.izquierda = Nodo_asada_arbol(asada)
            else:
                self._agregar_asada_recursivo(nodo_actual.izquierda, asada)
        else:
            if nodo_actual.derecha is None:
                nodo_actual.derecha = Nodo_asada_arbol(asada)
            else:
                self._agregar_asada_recursivo(nodo_actual.derecha, asada)


class Lista_enlazada_asada:
    def __init__(self):
        self.cabeza = None

    def agregar_asada(self, asada):
        nuevo_nodo = Nodo_asada(asada)
        if self.cabeza is None:
            self.cabeza = nuevo_nodo
        else:
            actual = self.cabeza
            while actual.siguiente is not None:
                actual = actual.siguiente
            actual.siguiente = nuevo_nodo

    def mostrar_asadas(self):
        actual = self.cabeza
        while actual is not None:
            print(
                f'ID: {actual.asada.id_Asada}, '
                f'Operador: {actual.asada.operador}, '
                f'Provincia: {actual.asada.provincia}, '
                f'Cantón: {actual.asada.canton}, '
                f'Distrito: {actual.asada.distrito}, '
                f'Teléfono: {actual.asada.telefono}, '
                f'Correo: {actual.asada.correo}, '
                f'Fax: {actual.asada.fax}, '
                f'Tipo de Sistema: {actual.asada.tipoSistema}'
            )
            actual = actual.siguiente
