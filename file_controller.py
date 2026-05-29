import models
import Api_asada
import pickle


def _dict_a_registro(item):
    """Convierte un dict del API en un objeto Registro_asada."""
    return models.Registro_asada(
        codigoDTA=item.get("codigoDTA"),
        id_Asada=item.get("id_Asada"),
        id_objeto=item.get("id_Objecto"),
        cordY=item.get("coordenadaY"),
        cordX=item.get("coordenadaX"),
        provincia=item.get("provincia"),
        canton=item.get("canton"),
        distrito=item.get("distrito"),
        telefono=item.get("telefono"),
        correo=item.get("correo"),
        fax=item.get("fax"),
        tipoSistema=item.get("tipoSistema"),
        operador=item.get("operador"),
    )


class file_controller:
    def __init__(self):
        self.api = Api_asada.AsadaApi()
        self.file_model = None

    def load_data(self):
        data = self.api.get_asadas_values()
        return data

    def save_data_to_binary_file(self, save_path, data):
        pass


class main_file_bin_controller(file_controller):
    def __init__(self):
        super().__init__()

    def save_data_to_binary_file(self, save_path, data):
        with open(save_path, 'wb') as file:
            pickle.dump(data, file)

    def load_data_from_binary_file(self, file_path):
        with open(file_path, 'rb') as file:
            data = pickle.load(file)
        return data


class liked_list_bin_controller(file_controller):
    def __init__(self):
        super().__init__()
        self.file_model = models.Lista_enlazada_asada()

    # Fix #5: agregado self que faltaba
    def save_data_to_binary_file(self, save_path, data):
        with open(save_path, 'wb') as file:
            pickle.dump(data, file)

    def load_data_from_binary_file_to_linked_list(self, file_path):
        with open(file_path, 'rb') as file:
            data = pickle.load(file)
        # Fix #6: convertir dicts a objetos Registro_asada antes de insertar
        for item in data:
            asada = _dict_a_registro(item)
            self.file_model.agregar_asada(asada)
        return self.file_model


class binary_tree_bin_controller(file_controller):
    def __init__(self):
        super().__init__()
        self.file_model = models.Arbol_asada()

    def save_data_to_binary_file(self, save_path, data):
        with open(save_path, 'wb') as file:
            pickle.dump(data, file)

    def load_data_from_binary_file_to_binary_tree(self, file_path):
        with open(file_path, 'rb') as file:
            data = pickle.load(file)
        # Fix #6: convertir dicts a objetos Registro_asada antes de insertar
        for item in data:
            asada = _dict_a_registro(item)
            self.file_model.agregar_asada(asada)
        return self.file_model
