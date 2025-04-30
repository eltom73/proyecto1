"""
Servidor TC5G - Tienda de Cartas
"""

# Importamos librerias
import socket
import threading
import json
import funciones_cliente as fc
from datetime import datetime
import time

# Variables globales
FILEPATH = "database_clientes.json"
CLIENTS_LIST = [] #Lista de Clientes en línea
EXECUTIVE_LIST = [] #Lista de Ejecutivos en línea
LISTA_ESPERA = [] #Lista de Clientes en espera de algún ejecutivo
CONEXIONES_ACTIVAS = {} #Lista de conexiones activas entre ejecutivos y clientes
mutex = threading.Lock() # Este impone el mutex



#def AutentificarUsuarios(email, contraseña, tipo):
#    with mutex:
#        with open(FILEPATH, "r") as file:
#            data = json.load(file)
#            usuarios = data.get(tipo, {})
#            if email in usuarios: #busca el email ingresado por el cliente en la base de datos
#                if usuarios[email]["contraseña"] == contraseña: #verifica que la contraseña ingresada por el 
#                    return True, usuarios[email]["nombre"]
#                else:
#                    return False, "Contraseña incorrecta"
#            return False, "Usuario No Encontrado"

#------------------------------------------------------------------------------------
#CLIENTE

# Funcion de cliente
def Identificación(sock):
    global CLIENTS_LIST, EXECUTIVE_LIST, LISTA_ESPERA, mutex 
    
    email = None # Inicializamos la variable para evitar errores
    nombre = None # Inicializamos la variable para evitar errores
    #es_ejecutivo = False  # Inicializamos la variable para evitar errores
    logueado = False  # Bandera para saber si el cliente pasó el login completo
    try:

        # Proceso de Identificación del cliente o ejecutivo
        sock.send("¡Bienvenido a la plataforma de servicio al cliente de la tienda TC5G!\n"
                  " Para autenticarse ingrese su mail y contraseña.\n ".encode())
        #Bucle para pedir email y contraseña
        while True:
            sock.send("Email: ".encode())
            email = sock.recv(1024).decode().strip()
            print(f"[LOGIN] Cliente ingresó email: {email}")
            if not email:
                sock.send("No se ingresó un correo. Intente nuevamente.\n".encode())
                continue # vuelve a pedir email
            # Abrir base de datos
            with mutex:
                with open(FILEPATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            clientes = data.get("CLIENTES", {})
            print(f"[DEBUG] clientes: {clientes}")
            # Verifica si el correo está registrado
            if email not in clientes:
                sock.send("Correo no registrado. Intente nuevamente.\n".encode())
                continue  # vuelve a pedir email
            # El correo es válido, se obtiene el usuario asociado
            usuario = clientes[email]
            break # sale del bucle
        # Pide contraseña si el correo fue válido
        while True:
            sock.send("Contraseña: ".encode())
            contraseña = sock.recv(1024).decode().strip()

            print(f"[SERVIDOR] Cliente ingresó contraseña: {contraseña}")
            print(f"[SERVIDOR] usuario: {usuario}")
            print(f"[SERVIDOR] type(usuario): {type(usuario)}")

            if usuario["contraseña"] == contraseña: # Verifica si la contraseña es correcta
                nombre = usuario["nombre"]
                sock.send(f"¡Bienvenido/a {nombre}!\n".encode())
                logueado = True # El cliente ha pasado el login completo

                break
            else:
                sock.send("Error: clave incorrecta. Conexión cerrada.\n".encode())
            
       
        if logueado:
            # Registrar acción
            with mutex:
                with open(FILEPATH, "r+",encoding="utf-8") as f:
                    data = json.load(f)
                    data["Ingresados"].append({
                        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "acción": f"Cliente {nombre} conectado"
                    })
                    f.seek(0)
                    json.dump(data, f, indent=4)
                    f.truncate()
            print(f"[SERVIDOR] Cliente {nombre} autenticado correctamente.")
            with mutex:
                CLIENTS_LIST.append((sock, email)) # Añadimos el socket y el email a la lista de clientes en línea
            fc.menu_cliente(sock, email, nombre) #Lo redirigimos al menú del cliente
            

    except Exception as e:
        print(f"[SERVIDOR] Error al autenticar cliente: {e}")
        sock.send("Ocurrió un error durante la autenticación. Conexión cerrada.\n".encode())
        
    finally:
        sock.close()
        with mutex:
            CLIENTS_LIST = [(s, e) for (s, e) in CLIENTS_LIST if s != sock] # Elimina el socket del cliente de la lista de clientes en línea

#-----------------------------------------------------------------------------------
# EJECUTIVO
def cargar_db(path):
    with open(path, "r", encoding="utf-8") as f:
        contenido = f.read().strip()
        if not contenido:
            raise ValueError(f"[ERROR] El archivo '{path}' está vacío.")
        try:
            return json.loads(contenido)
        except json.JSONDecodeError as e:
            raise ValueError(f"[ERROR] Error de formato JSON en '{path}': {e}")

def guardar_db(path, db):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


def manejar_ejecutivo(sock):
    datos = cargar_db(FILEPATH) #leemos la base de datos json

    try:
        login_data = sock.recv(1024).decode().split("|") #
        if len(login_data) != 3:
            sock.send("Formato inválido.".encode())
            sock.close()
            return

        _, correo, clave_ingresada = login_data #separar el mensaje recibido del ejecutivo en partes: email y contraseña
        print(f"[SERVIDOR] Ejecutivo ingresó email: {correo} y contraseña: {clave_ingresada}")


        #Validar ejecutivo en database
        ejecutivos = datos.get("EJECUTIVOS", {}) #extraemos la lista de ejecutivos de la base de datos
        if correo not in ejecutivos:
            sock.send("Correo no encontrado.".encode()) #si el correo no está en la base de datos, enviamos un mensaje de error
            sock.close() #cerramos la conexión
            return
        
        credenciales = ejecutivos[correo] #extraemos los correos de los ejecutivos de la base de datos
        clave_almacenada = credenciales.get("contraseña") #extraemos la contraseña del ejecutivo de la base de datos

        if clave_almacenada != clave_ingresada: #si la contraseña ingresada no coincide con la almacenada en la base, enviamos un mensaje de error
            sock.send("Contraseña incorrecta.".encode()) #Error de contraseña
            sock.close() #cerramos la conexión
            return
        
        #Numero de clientes conectados
        cantidad_clientes = len(CLIENTS_LIST) #lista de clientes EN LÍNEA ≠ EN ESPERA
        nombre = credenciales.get("nombre", "Ejecutivo") #extraemos el nombre del ejecutivo de la base de datos según el correo ingresado
        mensaje_bienvenida = f"Hola {nombre}, en este momento hay {cantidad_clientes} clientes conectados" #MENSAJE: el numero de clientes en línea al ejecutivo
        sock.send(mensaje_bienvenida.encode()) # enviamos el mensaje

        while True: #bucle infinito para recibir comandos de parte del ejecutivo, según lo estipulado en el menú
            msg = sock.recv(4096).decode() #mensaje recibido del ejecutivo
            if not msg: #si el mensaje está vacío, cerramos la conexión
                break

            if msg == ":status":
                with mutex:
                    cantidad_conectados = len(CLIENTS_LIST)
                    cantidad_en_espera = len(LISTA_ESPERA)
                response = f"Clientes conectados: {cantidad_conectados}\nClientes en espera: {cantidad_en_espera}" #Mensaje: clientes conectados y en espera según las listas CLIENTS_LIST y LISTA_ESPERA (su largo: len() )
                sock.send(response.encode()) #enviamos el mensaje al ejecutivo

            elif msg == ":details":
                with mutex:
                    if CLIENTS_LIST:
                        detalles = ""
                        for (_, email) in CLIENTS_LIST:
                            cliente_info = datos.get("CLIENTES", {}).get(email, {})
                            nombre = cliente_info.get("nombre", "Nombre no encontrado")
                            detalles += f"{email}: {nombre}\n"
                    else:
                        detalles = "No hay clientes conectados."
                sock.send(detalles.encode())

            elif msg == ":catalogue":
                productos = datos.get("PRODUCTOS", {})
                lista = "\n".join([f"{k}: ${int(v['precio']) if v['precio'] == int(v['precio']) else v['precio']}" for k, v in productos.items()])
                sock.send(lista.encode())

            elif msg.startswith(":publish"):
                partes = msg.split()
                if len(partes) == 3:
                    _, carta, precio = partes
                    datos.setdefault("PRODUCTOS", {})[carta] = {
                        "stock": 10,
                        "precio": float(precio)
                    }
                    guardar_db(FILEPATH, datos)
                    sock.send("Carta publicada.".encode())
                else:
                    sock.send("Uso incorrecto de :publish [carta] [precio]".encode())




            elif msg.startswith(":history"): #si el ejecutivo pide el historial de un cliente, el mensaje debe empezar con :history. Luego, va el email del cliente
                partes = msg.split() #Separamos el mensaje en partes, es decir, el comando y el email del cliente. Ejemplo: :history [email] Ejecutivo1@tc5g.com
                if len(partes) == 2: #Si el mensaje tiene 2 partes, es decir, el comando y el email del cliente, es correcto. Lo definimos como algo, email cliente
                    _, email_cliente = partes

                    #Verifica si el ejecutivo está atendiendo al cliente que pidió el historial
                    if email_cliente not in [email for (_, email) in CLIENTS_LIST]: #Verificamos si el email del cliente está en la lista de clientes conectados
                        sock.send("Debes estar conectado con el cliente\n".encode())
                        continue
                    with mutex:  #cargamos la base de datos
                        with open(FILEPATH, "r") as f:
                            data = json.load(f)

                            cliente = data["CLIENTES"].get(email_cliente, {}) #Definimos el cliente como el email del cliente que pidió el historial. Si no existe, devuelve un diccionario vacío
                            if not cliente:
                                sock.send(f"No se encontró el cliente {email_cliente}".encode())
                                continue

                            historial = cliente.get("transacciones", []) #Extraemos sus trasacciones mediante la variable cliente definida anteriormente. Si no existe, devuelve una lista vacía
                            if not historial:
                                sock.send(f"No hay historial para {email_cliente}".encode()) #Si no hay historial, enviamos un mensaje al ejecutivo diciendo que no hay historial
                                continue

                            # Formatear el historial    
                            mensaje = f"Historial completo de {cliente.get("nombre", email_cliente)}:\n"
                            for op in historial:
                                mensaje += (
                                    f" {op["tipo"].upper()} - {op["producto"]} "
                                f"(X{op.get("cantidad", 1)})- " 
                                f"{op["fecha"]} - "  
                                f"Estado: {op["estado"]}\n"
                                )
                            sock.send(mensaje.encode())
                else:
                    sock.send("Uso incorrecto de :history [email]".encode())

            elif msg == ":connect":
                with mutex:
                    if not LISTA_ESPERA: #si la lista de espera está vacía, enviamos un mensaje al ejecutivo diciendo que no hay clientes en espera
                        sock.send("No hay clientes en espera.\n".encode())
                        continue
                    #El ejecutivo se conecta al primer cliente de la lista de espera
                    cliente_sock, email_cliente = LISTA_ESPERA.pop(0) #saca el primer cliente de la lista de espera. La lista de espera contiene email de los clientes. En la función contactar_ejecutivo, se agrega el email del cliente a la lista de espera
                                                        #A la vez, se elimina de la lista de clientes en línea
                    try:
                    #Obtener nombre del cliente
                        with mutex:
                            with open(FILEPATH, "r") as f:
                                data = json.load(f)
                                cliente = data.get["CLIENTES",{}].get(email_cliente, {}).get("nombre", email_cliente)

                         #Establecer conexión con el cliente
                        CONEXIONES_ACTIVAS[sock] = cliente_sock #Agregamos el socket del ejecutivo a la lista de conexiones activas
                        #Notificaciones
                        cliente_sock.send(f"Conectado con el ejecutivo {nombre} ({correo})\n".encode()) #enviamos un mensaje AL CLIENTE diciendo que se ha conectado con el ejecutivo a traves de su socket
                        sock.send(f"Conectado con {cliente} ({email_cliente})\n".encode()) #enviamos un mensaje AL EJECUTIVO diciendo que se ha conectado con el cliente
                        print(f"[SERVIDOR] Ejecutivo {nombre} conectado con cliente {cliente} ({email_cliente})") #registramos la conexión en la consola del servidor


                    except (ConnectionError, OSError):
                        sock.send("El cliente no se encuentra disponible".encode())
                        continue

                  

                    ##Notificar conexión al cliente
                    #info_cliente = datos["CLIENTES"].get(email_cliente, {})
                    #nombre_cliente = info_cliente.get("nombre", email_cliente)
                    #sock.send(f"Conectado con {nombre_cliente} ({email_cliente})\n".encode()) #enviamos un mensaje al ejecutivo diciendo que se ha conectado con el cliente
                    #cliente_sock.send(f"Conectado con el ejecutivo {nombre} ({correo})\n".encode()) #enviamos un mensaje al cliente diciendo que se ha conectado con el ejecutivo a traves de su socket

                    ##Registrar la conexión
                    #print(f"[SERVIDOR] Ejecutivo {nombre} conectado con cliente {nombre_cliente} ({email_cliente})")  
                                            
        

            elif msg == ":exit":
                break
            else:
                sock.send("Comando recibido (no implementado completamente).".encode())

    except Exception as e:
        print(f"[ERROR] Ejecutivo error: {e}")
    finally:
        sock.close()




    #    print(f"Conexión exitosa como {'ejecutivo' if es_ejecutivo else 'cliente'}: {nombre} ")
    #    with mutex:
    #        if es_ejecutivo: 
    #            EXECUTIVE_LIST.append((sock, email)) #Añadimos el socket y el email a la lista de ejecutivos
    #            Log_in(f"Ejecutivo {nombre} conectado") #Ingresamos el tiempo de conexión del ejecutivo a la database
    #        else:
    #            CLIENTS_LIST.append((sock, email)) #Añadimos el socket y el email a la lista de clientes
    #            Log_in(f"Cliente {nombre} conectado") #Ingresamos el tiempo de conexión del cliente a la database
    #    sock.send(f"Asistente: ¡Bienvenido {nombre}! ¿En qué te podemos ayudar?\n".encode()) #Ya ingresado, le damos la bienvenida al cliente
#
    #    if es_ejecutivo:
    #        Ejecutivo(sock, email, nombre) #Si es ejecutivo, llamamos a la función Ejecutivo
    #    else:
    #        Cliente(sock, email) #Si es cliente, llamamos a la función Cliente
    #except Exception as e:
    #    print(f"Error en Cliente: {e}")
#
    #finally: 
    #    with mutex:
    #        if es_ejecutivo and (sock, email) in EXECUTIVE_LIST:  #Cerramos la conexión del ejecutivo y eliminamos de la lista de " en línea" 
    #            EXECUTIVE_LIST.remove((sock, email))
    #            Log_in(f"Ejecutivo {nombre} desconectado")
    #        elif (sock, email) in CLIENTS_LIST:  #Cerramos la conexión del cliente y eliminamos de la lista de " en línea" 
    #            CLIENTS_LIST.remove((sock, email))
    #            Log_in(f"Cliente {nombre} desconectado") 
    #   sock.close()

#def Ejecutivo (sock, nombre): #Función que maneja la interacción con el ejecutivo
#        EstadoDeClientes = None #Caso base. Al inicio no atiende a nadie
#        
#        while True:
#            if EstadoDeClientes:
#                prompt = f"[Ejecutivo {nombre} atendiendo a {EstadoDeClientes[1]}] Ingrese comando:"
#            else:
#                prompt=f"[Ejecutivo {nombre}] Ingrese comando: "
#            sock.send(prompt.encode())
#            comando = sock.recv(1024).decode().strip().lower()
#
#            if comando == ":status":
#                with mutex:
#                    status = f"Clientes conectados: {len(CLIENTS_LIST)}\n En cola de espera: {len(LISTA_ESPERA)}"
#                    sock.send(status.encode())
#            elif comando == ":details":
#                details = "Clientes conectados:\n"
#                with mutex:
#                    for cliente in CLIENTS_LIST:
#                        details += f"- {cliente[1]}\n"
#                    sock.send(details.encode())
#            elif comando.startswith(":history") and EstadoDeClientes:
#                pass #aca va la funcion 
#
#            elif comando == ":disconnect" and EstadoDeClientes:
#                sock.send(f"Desconectando de {EstadoDeClientes[1]}\n".encode())
#                EstadoDeClientes[0].send("El ejecutivo terminó al sesión. ¿Desea usted realizar alguna otra operación?\n".encode())
#                EstadoDeClientes = None
#            elif comando == ":exit":
#                sock.send("Desconectando...\n".encode())
#                break
#            elif not EstadoDeClientes and LISTA_ESPERA:
#                with mutex:
#                    EstadoDeClientes = LISTA_ESPERA.pop(0)
#                sock.send(f"Conectado con {EstadoDeClientes[1]}\n".encode())
#                EstadoDeClientes[0].send("Conectado con el ejecutivo....Espere.... \n".encode())
#                Log_in(f"Ejecutivo {nombre} atendiendo a {EstadoDeClientes[1]}")
#            
#            else:
#                sock.send("Comando no reconocido. Intente nuevamente.\n".encode())

      
    
if __name__ == "__main__":
    # Se configura el servidor para que corra localmente y en el puerto 8889.
    HOST = '127.0.0.1'
    PORT = 8889

    # Se crea el socket y se instancia en las variables anteriores.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(10) # Se permite hasta 10 conexiones simultáneas.
    print(f"Servidor TC5G escuchando en {HOST}:{PORT}")

    # Se inicia el thread del cliente
    while True:
            # Se acepta la conexion de un cliente
            conn, addr = s.accept()
            try:
                # Primero recibe el primer mensaje de identificación
                tipo = conn.recv(1024).decode().strip()

                if tipo == "EJECUTIVO":
                    print(f"[SERVIDOR] Conexión de un Ejecutivo desde {addr}")
                    threading.Thread(target=manejar_ejecutivo, args=(conn,), daemon=True).start()
                elif tipo == "CLIENTE":
                    print(f"[SERVIDOR] Conexión de un Cliente desde {addr}")
                    threading.Thread(target=Identificación, args=(conn,), daemon=True).start()
            except Exception as e:
                print(f"[SERVIDOR] Error en el handshake inicial: {e}")
                conn.close()
            