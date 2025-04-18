"""
Servidor TC5G - Tienda de Cartas
"""

# Importamos librerias
import socket
import threading
import json
from datetime import datetime
import funciones_cliente as fc
import time 


# Variables globales
FILEPATH = "database_clientes.json" #Ruta al archivo JSON principal (database.json). Todo se guarda ahí.
CLIENTS_LIST = [] #Lista de sockets (conexiones) de los clientes que están conectados.
EXECUTIVE_LIST = [] #Lista de sockets de los ejecutivos conectados.
WAITING_QUEVE = [] #Lista de Clientes en espera de algún ejecutivo.
mutex = threading.Lock() # Lock para evitar que dos hilos escriban el JSON al mismo tiempo.



# -------------------- función auxiliar --------------------
def atender_cliente_login(sock):
    """Autentica a un cliente y entrega el control al menú de fc."""
    logueado = False  # Bandera para saber si el cliente pasó el login completo

    try:
        sock.send((
            "¡Bienvenido a la plataforma de servicio al cliente de la tienda TC5G!\n"
            "Para autenticarse ingrese su mail y contraseña.\n"
        ).encode())

        while True:
            sock.send("Email: ".encode())
            email = sock.recv(1024).decode().strip()
            print(f"[LOGIN] Cliente ingresó email: {email}")

            if not email:
                sock.send("No se ingresó un correo. Intente nuevamente.\n".encode())
                continue  # vuelve a pedir email

            # Abrir base de datos
            with mutex:
                with open(FILEPATH, "r") as f:
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

        # Pide contraseña si el correo fue válido
        sock.send("Contraseña: ".encode())
        password = sock.recv(1024).decode().strip()
        print(f"[LOGIN] Cliente ingresó contraseña: {password}")
        print(f"[DEBUG] usuario: {usuario}")
        print(f"[DEBUG] type(usuario): {type(usuario)}")

        if usuario["contrasena"] != password:
            sock.send("Error: clave incorrecta. Conexión cerrada.\n".encode())
            time.sleep(0.1)
            sock.close()
            return

        nombre = usuario["nombre"]
        sock.send(f"¡Bienvenido/a {nombre}!\n".encode())

        # Registrar acción
        with mutex:
            with open(FILEPATH, "r+") as f:
                data = json.load(f)
                data["Ingresados"].append({
                    "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "acción": f"Cliente {nombre} conectado"
                })
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()

        with mutex:
            CLIENTS_LIST.append((sock, email))

        logueado = True  # ← El cliente pasó el login

        # Entrar al menú del cliente
        fc.menu_cliente(sock, email, nombre)

    except Exception as e:
        print("Error en login:", e)
        sock.close()
    finally:
        # Solo cerrar si el login fue exitoso o si no entró al menú
        if not logueado:
            sock.close()
        else:
            with mutex:
                if (sock, email) in CLIENTS_LIST:
                    CLIENTS_LIST.remove((sock, email))
            sock.close()







    
if __name__ == "__main__":
    # Configurar servidor
    HOST, PORT = "127.0.0.1", 8889
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Servidor TC5G escuchando en {HOST}:{PORT}")

    # Bucle principal: aceptar clientes
    while True:
        conn, addr = s.accept()
        print(f"[SERVIDOR] Conexión desde {addr}")

        # Lanza un hilo que hace login y luego menú de cliente
        threading.Thread(
            target=atender_cliente_login,  # <- función que autentica
            args=(conn,),                  # pasa el socket
            daemon=True
        ).start()
