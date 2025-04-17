"""
Servidor cookie clicker
"""

# Importamos librerias
import socket
import threading
import json

# Variables globales
FILEPATH = "database.json"
CLIENTS_LIST = [] #La lista CLIENTS_LIST guarda los sockets (conn) de los clientes conectados, no sus nombres. Los sockets son lo que el servidor necesita para poder enviar mensajes de vuelta a los clientes.
mutex = threading.Lock() # Este impone el mutex


# Funcion de cliente
def cliente(sock):    # sock es el socket hijo devuelto por accept(), exclusivo para hablar con este cliente.
    global CLIENTS_LIST, FILEPATH
    while True:
        # Revisamos que usuarios disponibles tenemos
        with mutex:
            with open(FILEPATH, "r") as file:
                data = json.load(file)
                names = list(data.keys())
                print(names)
                file.close()

        # Revisamos el mensaje recibido
        nombre = sock.recv(1024).decode()
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
                    with mutex: #evita que dos clientes puedan modificar el archivo simultáneamente
                        with open(FILEPATH) as file: #Abre el archivo en modo lectura ("r" por defecto).
                            database = json.load(file) #Lee el JSON y lo transforma en un diccionario Python llamado database. Queda en RAM para poder modificarlo
                            database[data] +=1 #Incrementa en 1 el contador de galletas del usuario cuyo nombre llegó en data. "data" es el destinatario que el cliente tipeó
                            amount = database[data] #Guarda el nuevo total para usarlo en el mensaje de confirmación.
                            file.close()
                        with open(FILEPATH, "w") as file: #Abre el archivo en modo escritura.
                            json.dump(database, file) #Traduce el dict database a texto JSON. Deja el archivo actualizado, garantizando persistencia.
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
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #→ socket TCP sobre IPv4. Este socket solo se usa para aceptar clientes, no para enviar/recibir mensajes de ellos.
    s.bind((HOST, PORT)) #→ lo vincula a la IP/puerto donde escuchará.
    s.listen() #→ lo pone en modo de espera de conexiones entrantes.

    # Se buscan clientes que quieran conectarse.
    while True:

        # Se acepta la conexion de un cliente
        conn, addr = s.accept() #conn es un socket nuevo exclusivo para ese cliente. addr es una tupla (ip_cliente, puerto_cliente) (se puede usar para logs).
        CLIENTS_LIST.append(conn) #Se guarda el conn en CLIENTS_LIST para poder llevar registro de los conectados.

        # Se manda el mensaje de bienvenida
        conn.send("Bienvenid@ a mi clicker :D \n Te conozco? (dime tu nombre)".encode())

        # Se inicia el thread del cliente
        client_thread = threading.Thread(target=cliente, args=(conn,))
        client_thread.start()