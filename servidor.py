"""
Servidor TC5G - Tienda de Cartas
"""

# Importamos librerias
import socket
import threading
import json
from datetime import datetime

# Importamos las funciones del cliente
import funciones_cliente as fc


# Variables globales
FILEPATH = "database.json"
CLIENTS_LIST = [] #Lista de Clientes en línea
EXECUTIVE_LIST = [] #Lista de Ejecutivos en línea
WAITING_QUEVE = [] #Lista de Clientes en espera de algún ejecutivo
mutex = threading.Lock() # Este impone el mutex

def Log_in(accion): #Función que registra en la database columna "Ingresados" el tiempo cuando un cliente/ejecutivo se conecta al servidor
    with mutex:
        with open(FILEPATH, "r+") as file: #abrimos la database como file, tal que se pueda leer y escribir sobre este
            data = json.load(file)
            data["Ingresados"].append({"timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),"acción":accion})
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()
def AutentificarUsuarios(email, contraseña, tipo):
    with mutex:
        with open(FILEPATH, "r") as file:
            data = json.load(file)
            usuarios = data.get(tipo, {})
            if email in usuarios: #busca el email ingresado por el cliente en la base de datos
                if usuarios[email]["contraseña"] == contraseña: #verifica que la contraseña ingresada por el 
                    return True, usuarios[email]["nombre"]
                else:
                    return False, "Contraseña incorrecta"
            return False, "Usuario No Encontrado"

def menu_cliente(sock,email):
    while True:
        menu = (
            "\n--- MENÚ CLIENTE ---\n"
            "1. Cambiar contraseña\n"
            "2. Ver historial\n"
            "3. Comprar carta\n"
            "4. Devolver carta\n"
            "5. Confirmar envío\n"
            "6. Hablar con ejecutivo\n"
            "7. Salir\n"
            "Elige una opción: "
        )
        sock.send(menu.encode())
        opcion = sock.recv(1024).decode().strip()

        if opcion == "1":
            cambiar_contrasena(sock, email)
        elif opcion == "2":
            historial_de_operaciones(sock, email)
        elif opcion == "3":
            comprar_cartas(sock, email)
        elif opcion == "4":
            devolver_cartas(sock, email)
        elif opcion == "5":
            confirmar_envio(sock, email)
        elif opcion == "6":
            contactar_ejecutivo(sock, email)
        elif opcion == "7":
            sock.send("Sesión finalizada. ¡Hasta luego!\n".encode())
            break
        else:
            sock.send("Opción inválida. Intenta nuevamente.\n".encode())




# Funcion de cliente
def cliente(sock):
    global CLIENTS_LIST, WAITING_QUEVE
    try:

        # Proceso de Identificación del cliente o ejecutivo
        sock.send("¡Bienvenido a la plataforma de servicio al cliente de la tienda TC5G! Para autenticarse ingrese su mail y contraseña: ".encode())
        email = sock.recv(1024).decode().strip() #esperamos respuesta sobre email
        sock.send("Contraseña: ".encode())
        contraseña = sock.recv(1024).decode().strip()#esperamos respuesta sobre contraseña

        autenticacion, nombre = AutentificarUsuarios(email, contraseña, "CLIENTES") #llamamos a la función AutentificarUsuarios para ver si es un cliente (TRUE)
        es_ejecutivo = False #caso base = no es ejecutivo
        if not autenticacion: #Si al preguntar si es que es un cliente devuelve False, preguntamos si es ejecutivo
            autenticacion, nombre = AutentificarUsuarios(email, contraseña, "EJECUTIVOS")
            es_ejecutivo = True #Si es ejecutivo, se setea a True
        if not autenticacion: #No es ni cliente ni ejecutivo, damos error de inicio de sesión
            sock.send(f"Asistente: {"Error de inicio de sesión"}\n".encode())
            sock.close()
            return
        #Conexión exitosa como cliente o como ejecutivo
        with mutex:
            if es_ejecutivo: 
                EXECUTIVE_LIST.append((sock, email))
                Log_in(f"Ejecutivo {nombre} conectado")
            else:
                CLIENTS_LIST.append((sock, email)) 
                Log_in(f"Cliente {nombre} conectado")
        sock.send(f"Asistente: ¡Bienvenido {nombre}! ¿En qué te podemos ayudar?\n".encode())

        if es_ejecutivo:
            Ejecutivo(sock, email, nombre)
        else:
            Ejecutivo(sock, email, nombre)
    except Exception as e:
        print(f"Error en Cliente: {e}")

    finally: 
        with mutex:
            if es_ejecutivo and (sock, email) in EXECUTIVE_LIST:
                EXECUTIVE_LIST.remove((sock, email))
                Log_in(f"Ejecutivo {nombre} desconectado")
            elif (sock, email)



##########################################################################################################################
        if nombre in names: # Si esta en la lista de clientes
            sock.send('Asistente: Yo a ti te conozco...'.encode())
            sock.send('¿A quien le sumas 1 galleta? \n Escribe ::exit para salir'.encode())
            print(f'Cliente {nombre} se ha conectado.')

            while True:
                try:
                    data = sock.recv(1024).decode()
                except:
                    break

                if data == "::exit":
                    sock.send("Chao cuidate!".encode())
                    
                    # Se modifican las variables globales usando un mutex.
                    with mutex:
                        CLIENTS_LIST.remove(sock)
                    sock.close()
                    print(f'Cliente {nombre} se ha desconectado.')
                    break

                elif data in names:
                    #muestra los pedidos de los clientes
                    print(f'El cliente {nombre} le da una galleta a {data}')
                    with mutex:
                        with open(FILEPATH) as file:
                            database = json.load(file)
                            database[data] +=1
                            amount = database[data]
                            file.close()
                        with open(FILEPATH, "w") as file:
                            json.dump(database, file)
                            file.close()
                        
                    sock.send(f'Gracias a ti, {data} ahora tiene {amount} galleta(s)'.encode())
                    
                else:
                    sock.send('No conozco esa persona :c, intenta con otro nombre'.encode())
            return None

        elif nombre == '::exit':
            with mutex:
                CLIENTS_LIST.remove(sock)
            sock.close()
            return None

        else: 
            sock.send('No te conozco y no hablo con desconocidos :C \nVuelve a intentarlo o ::exit para salir.'.encode())

    
if __name__ == "__main__":
    # Se configura el servidor para que corra localmente y en el puerto 8889.
    HOST = '127.0.0.1'
    PORT = 8889

    # Se crea el socket y se instancia en las variables anteriores.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()

    # Se buscan clientes que quieran conectarse.
    while True:

        # Se acepta la conexion de un cliente
        conn, addr = s.accept()
        CLIENTS_LIST.append(conn)

        # Se manda el mensaje de bienvenida
        conn.send("Bienvenid@ a mi clicker :D \n Te conozco? (dime tu nombre)".encode())

        # Se inicia el thread del cliente
        client_thread = threading.Thread(target=cliente, args=(conn,))
        client_thread.start()