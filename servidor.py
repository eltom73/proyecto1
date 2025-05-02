"""
Servidor TC5G - Tienda de Cartas
"""

# Importamos librerias
import socket
import threading
import json
import funciones_cliente as fc
from shared_state import FILEPATH, mutex, STATE
from datetime import datetime
import time

# Variables globales
FILEPATH = "database_clientes.json"
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
    email = None  # Inicializamos la variable para evitar errores
    nombre = None  # Inicializamos la variable para evitar errores
    logueado = False  # Bandera para saber si el cliente pasó el login completo

    try:
        # Proceso de Identificación del cliente o ejecutivo
        sock.send("¡Bienvenido a la plataforma de servicio al cliente de la tienda TC5G!\n"
                  " Para autenticarse ingrese su mail y contraseña.\n ".encode())

        # Bucle para pedir email y contraseña
        while True:
            sock.send("Email: ".encode())  # Solicita email al cliente
            email = sock.recv(1024).decode().strip()  # Recibe el correo
            print(f"[LOGIN] Cliente ingresó email: {email}")

            if not email:
                sock.send("No se ingresó un correo. Intente nuevamente.\n".encode())
                continue  # vuelve a pedir email

            # Abrir base de datos para buscar el correo
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
            break  # sale del bucle

        # Bucle para validar contraseña (máximo 3 intentos)
        intentos = 0
        while intentos < 3:
            sock.send("Contraseña: ".encode())
            contraseña = sock.recv(1024).decode().strip()

            if usuario["contraseña"] == contraseña:  # Verifica si la contraseña es correcta
                nombre = usuario["nombre"]
                sock.send(f"¡Bienvenido/a {nombre}!\n".encode())
                logueado = True  # El cliente ha pasado el login completo

                # Añadir al diccionario de clientes en línea
                with mutex:
                    STATE["clientes_linea"][email] = sock
                break
            else:
                intentos += 1
                sock.send(f"Contraseña incorrecta. Intento {intentos}/3\n".encode())

        if not logueado:
            sock.send("Demasiados intentos fallidos. Conexión cerrada.\n".encode())
            return

        # Si pasó el login correctamente:
        if logueado:
            # Registrar acción en el historial de ingresos
            with mutex:
                with open(FILEPATH, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    data["Ingresados"].append({
                        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "acción": f"Cliente {nombre} conectado"
                    })
                    f.seek(0)
                    json.dump(data, f, indent=4)
                    f.truncate()

            print(f"[SERVIDOR] Cliente {nombre} autenticado correctamente.")
            # Redirigir al menú principal del cliente
            fc.menu_cliente(sock, email, nombre)

    except Exception as e:
        print(f"[SERVIDOR] Error al autenticar cliente: {e}")
        sock.send("Ocurrió un error durante la autenticación. Conexión cerrada.\n".encode())

    finally:
        with mutex:
            STATE["clientes_linea"].pop(email, None)
            STATE["clientes_espera"] = [
                (s, e) for (s, e) in STATE["clientes_espera"] if e != email
            ]

        # Cierra el socket *solo si no está conectado a un ejecutivo*
        with mutex:
            if sock not in STATE["conexiones"].values():
                sock.close()



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


def chat_ejecutivo(sock_ejec, sock_cliente):
    """
    Escucha mensajes del ejecutivo y reenvía al cliente.
    """
    try:
        while True:
            mensaje = sock_ejec.recv(1024).decode().strip()
            if not mensaje:
                break

            if mensaje.startswith(":history"):
                # Reenviamos el mensaje al propio socket del ejecutivo
                sock_ejec.send((mensaje + "\n").encode())
                continue

            # elif mensaje.startswith(":buy"):  ESTA PARTE ES PARA CUANDO EL CLIENTE QUIERA VENDER CARTAS
            #     sock_ejec.send((mensaje + "\n").encode())
            #     continue

            # Si es texto normal, lo mandamos al cliente
            sock_cliente.send(f"Ejecutivo: {mensaje}\n".encode())

    except Exception as e:
        print(f"[ERROR] chat_ejecutivo: {e}")




def chat_cliente_a_ejecutivo(sock_cliente, sock_ejecutivo, nombre_cli):
    """
    Escucha lo que escribe el cliente y lo reenvía al ejecutivo
    con un prefijo claro para mostrarlo en consola.
    """
    try:
        while True:
            # Espera datos del cliente
            mensaje = sock_cliente.recv(1024).decode()

            # Si se cerró la conexión del cliente
            if mensaje == "":
                print(f"[SERVIDOR] Cliente {nombre_cli} se desconectó del chat.")
                sock_ejecutivo.send(f"\n[INFO] Cliente {nombre_cli} se ha desconectado.\n".encode())
                break

            # Mostrar y reenviar mensaje
            print(f"[DEBUG] Mensaje de {nombre_cli}: {mensaje.strip()}")
            sock_ejecutivo.send(f"Cliente {nombre_cli}: {mensaje}".encode())

    except ConnectionResetError:
        print(f"[SERVIDOR] Conexión perdida con cliente {nombre_cli}")
        try:
            sock_ejecutivo.send(f"\n[ERROR] Conexión perdida con {nombre_cli}.\n".encode())
        except:
            pass

    except Exception as e:
        print(f"[ERROR] chat_cliente_a_ejecutivo: {e}")
        try:
            sock_ejecutivo.send(f"\n[ERROR] Error recibiendo mensajes de {nombre_cli}.\n".encode())
        except:
            pass




# ---------------------------------------------------------------
# FUNCIÓN QUE ATIENE A LOS EJECUTIVOS DESDE EL SERVIDOR
# ---------------------------------------------------------------
def manejar_ejecutivo(sock):
    """
    • Autentica al ejecutivo (correo + contraseña).
    • Registra al ejecutivo en STATE["ejecutivos_linea"].
    • Atiende un bucle de comandos (:status, :details, :catalogue, etc.).
    • Gestiona la conexión con clientes que están en espera (:connect).
    """
    datos = cargar_db(FILEPATH)  # Cargamos la BD una vez para info básica

    try:
        # ------------------------------------------------------------------
        # 1) *** HANDSHAKE DE LOGIN ***
        # ------------------------------------------------------------------

        # Primero recibimos el correo
        correo = sock.recv(1024).decode().strip()
        print(f"[SERVIDOR] Ejecutivo ingresó email: {correo}")

        # Validamos que el correo esté en la base de datos
        ejecutivos = datos.get("EJECUTIVOS", {})
        if correo not in ejecutivos:
            sock.send("Correo no encontrado. Conexión cerrada.\n".encode())
            sock.close()
            return

        credenciales = ejecutivos[correo]
        clave_correcta = credenciales.get("contraseña")

        # Bucle de intentos de contraseña
        intentos = 0
        while intentos < 3:
            sock.send("Contraseña: ".encode())
            clave_ingresada = sock.recv(1024).decode().strip()

            if clave_ingresada == clave_correcta:
                break
            else:
                intentos += 1
                if intentos < 3:
                    sock.send(f"Contraseña incorrecta. Intento {intentos}/3\n".encode())

        # Si falló 3 veces
        if clave_ingresada != clave_correcta:
            sock.send("Demasiados intentos fallidos. Conexión cerrada.\n".encode())
            sock.close()
            return


        # --- Login exitoso ------------------------------------------------
        nombre = credenciales.get("nombre", "Ejecutivo")
        with mutex:
            STATE["ejecutivos_linea"][correo] = sock    # Se registra como “en línea”
            cantidad_clientes = len(STATE["clientes_linea"])

        mensaje_bienvenida = f"Hola {nombre}, en este momento hay {cantidad_clientes} clientes conectados"
        sock.send(mensaje_bienvenida.encode())



        # ------------------------------------------------------------------
        # 2) *** BUCLE PRINCIPAL DE COMANDOS DEL EJECUTIVO ***
        # ------------------------------------------------------------------
        while True:
            msg = sock.recv(4096).decode().strip()
            if not msg:           # Fin de conexión TCP
                break

            # ⚠️ si el mensaje no empieza con ":", se asume que es mensaje de chat en vivo
            if not msg.startswith(":"):
                # Aquí no hacemos nada, porque `chat_ejecutivo` ya está enviando al cliente
                continue

            # -------------------- :status ---------------------------------
            if msg == ":status":
                with mutex:
                    conectados = len(STATE["clientes_linea"])
                    en_espera  = len(STATE["clientes_espera"])
                    print("[DEBUG] Ejecutando :status")
                    print(f"  -> Clientes conectados: {conectados}")
                    print(f"  -> Clientes en espera: {en_espera}")
                sock.send(f"Clientes conectados: {conectados}\n"
                        f"Clientes en espera: {en_espera}\n".encode())


            # -------------------- :details --------------------------------
            elif msg == ":details":
                detalles = []
                with mutex:
                    for email in STATE["clientes_linea"]:
                        nombre_c = datos.get("CLIENTES", {}).get(email, {}).get("nombre", "")
                        detalles.append(f"{email}: {nombre_c}")
                respuesta = "\n".join(detalles) if detalles else "No hay clientes conectados."
                sock.send((respuesta + "\n").encode())

            # -------------------- :catalogue ------------------------------
            elif msg == ":catalogue":
                # Recargamos la BD para tener precios/stock actualizados
                datos = cargar_db(FILEPATH)
                productos = datos.get("PRODUCTOS", {})
                lista = "\n".join(
                    f"{k}: ${int(v['precio']) if v['precio'] == int(v['precio']) else v['precio']}"
                    for k, v in productos.items()
                )
                sock.send((lista + "\n").encode())

            # -------------------- :publish carta precio -------------------
            elif msg.startswith(":publish"):
                partes = msg.split(maxsplit=2)
                if len(partes) == 3:
                    _, carta, precio = partes
                    try:
                        precio_float = float(precio)
                    except ValueError:
                        sock.send("Precio inválido.\n".encode())
                        continue

                    datos["PRODUCTOS"][carta] = {"stock": 10, "precio": precio_float}
                    guardar_db(FILEPATH, datos)
                    sock.send("Carta publicada.\n".encode())
                else:
                    sock.send("Uso: :publish [carta] [precio]\n".encode())

            # -------------------- :history --------------------------------
            elif msg.startswith(":history"):
                partes = msg.split(maxsplit=1)
                if len(partes) != 2:
                    sock.send("Uso: :history [email]\n".encode())
                    continue
                email_cliente = partes[1]

                # Verificar si el ejecutivo está conectado con ese cliente
                with mutex:
                    conexion = STATE["conexiones"].get(correo)
                    if not conexion:
                        sock.send("No estás conectado con ningún cliente.\n".encode())
                        continue

                    _, correo_cliente_conectado = conexion
                    if correo_cliente_conectado != email_cliente:
                        sock.send("Debes estar conectado con ese cliente para ver su historial.\n".encode())
                        continue

                # Mostrar historial completo
                datos_hist = cargar_db(FILEPATH)
                cliente = datos_hist["CLIENTES"].get(email_cliente, {})
                historial = cliente.get("transacciones", [])
                if not historial:
                    sock.send("No hay historial para ese cliente.\n".encode())
                    continue

                mensaje = f"Historial completo de {cliente.get('nombre', email_cliente)}:\n"
                for op in historial:
                    mensaje += (
                        f" {op['tipo'].upper()} - {op['producto']} "
                        f"(x{op.get('cantidad', 1)}) - "
                        f"{op['fecha']} - Estado: {op['estado']}\n"
                    )
                sock.send(mensaje.encode())
                try:
                    # También enviamos el historial al cliente
                    if conexion:
                        cli_sock, _ = conexion
                        cli_sock.send(mensaje.encode())
                except:
                    pass


            # -------------------- :connect --------------------------------
            elif msg == ":connect":
                with mutex:
                    if not STATE["clientes_espera"]:
                        sock.send("No hay clientes en espera.\n".encode())
                        continue
                    cli_sock, cli_email = STATE["clientes_espera"].pop(0)
                    STATE["conexiones"][correo] = (cli_sock, cli_email)

                nombre_cli = datos["CLIENTES"].get(cli_email, {}).get("nombre", cli_email)
                
                # Mensajes de bienvenida a ambas partes
                cli_sock.send(f"Conectado con el ejecutivo {nombre}.\n".encode())
                sock.send(f"Conectado con {nombre_cli} ({cli_email}).\n".encode())

                threading.Thread(target=chat_ejecutivo, args=(sock, cli_sock), daemon=True).start()
                threading.Thread(target=chat_cliente_a_ejecutivo, args=(cli_sock, sock, nombre_cli), daemon=True).start()




            # -------------------- :exit -----------------------------------
            elif msg == ":exit":
                with mutex:
                    # Ver si estaba atendiendo a un cliente
                    conexión = STATE["conexiones"].pop(correo, None)
                    if conexión:
                        cli_sock, _ = conexión
                        try:
                            cli_sock.send("El ejecutivo ha finalizado la sesión.\n".encode())
                            cli_sock.close()
                        except:
                            pass

                    # Remover al ejecutivo del estado
                    STATE["ejecutivos_linea"].pop(correo, None)
                break


            # -------------------- comando desconocido --------------------
            else:
                sock.send("Comando no implementado.\n".encode())

    # ------------------------------------------------------------------
    # *** MANEJO DE EXCEPCIONES ***
    # ------------------------------------------------------------------
    except Exception as e:
        print(f"[ERROR] Ejecutivo error: {e}")

    # ------------------------------------------------------------------
    # *** LIMPIEZA FINAL ***
    # ------------------------------------------------------------------
    finally:
        with mutex:
            # Quitamos al ejecutivo de la lista de “en línea”
            STATE["ejecutivos_linea"].pop(correo, None)
            # Si estaba en conversación, avisamos al cliente
            cli_sock = STATE["conexiones"].pop(sock, None)
            if cli_sock:
                try:
                    cli_sock.send("El ejecutivo se ha desconectado.\n".encode())
                except (BrokenPipeError, OSError):
                    pass





    
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
            


# CLIENTS_LIST, EXECUTIVE_LIST, LISTA_ESPERA, CONEXIONES_ACTIVAS            