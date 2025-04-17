"""
Template para editar JSON
"""
# Importamos librerias
import json

# Definimos variables globales
FILEPATH = "database2.json"

# Definimos funciones
def create(filename):
    """
    Creamos y cerramos un archivo solo para crearlo
    """
    with open(FILEPATH, "w") as file:
        json.dump({}, file)
        file.close()
    pass

def save(data, filename):
    """
    Guarda un diccionario como json
    """
    with open(FILEPATH, "w") as file:
        json.dump(data, file)
        file.close()


def add(data, key_name, value):
    """
    Agrega un valor nuevo a nuestro archivo
    """
    data[key_name] = value
    # Guardamos los cambios
    save(data, FILEPATH)
    

def delete_obj(data, key_name):
    """
    Elimina una llave en el JSON
    """
    del data[key_name]
    # Guardamos los cambios
    save(data, FILEPATH)


def modify(data, dictionary):
    """
    Modifica/agrega mas de un valor
    """
    data.update(dictionary)
    # Guardamos los cambios
    save(data, FILEPATH)



if __name__ == "__main__":
    # Creamos el archivo
    create(FILEPATH)
    # Abrimos el archivo
    with open(FILEPATH, "r") as file:
        data = json.load(file)
        file.close()
    # Agregamos valores
    add(data, "a", 1)
    add(data, "b", 2)
    add(data, "c", 3)
    add(data, "d", 4)
    # Eliminamos uno
    delete_obj(data, "a")
    # Agregamos varios
    nuevos = {
        "ola":23,
        "como": 25,
        "estas": 34,
        "b": "jejeje",
        "otro": {
            "secreto": 300
        }
    }
    modify(data, nuevos)





