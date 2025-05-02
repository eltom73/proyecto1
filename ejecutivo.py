import socket
import threading
import sys


def mostrar_menu():
    print("""
--- Comandos disponibles ---
:status       -> Ver clientes conectados y solicitudes
:details      -> Ver detalles de clientes conectados
:history [email]     -> Ver historial de acciones del cliente
:operations [email]  -> Ver historial de operaciones del cliente
:catalogue    -> Ver catálogo de productos
:buy [carta] [precio]     -> Comprar carta al cliente
:publish [carta] [precio] -> Publicar carta a la venta
:connect      -> Conectarse con cliente en espera
:disconnect   -> Finalizar conexión con cliente
:exit         -> Cerrar sesión
-----------------------------
""")



#------------------------------------------------------------------------------------
#EJECUTIVO
def recibir_mensajes(sock):
    """
    Lee todo lo que el servidor envía al ejecutivo y lo imprime
    inmediatamente.  Si el servidor cierra la conexión, termina
    el programa con un aviso elegante.
    """
    while True:
        try:
            datos = sock.recv(4096).decode()
            if not datos:                       # conexión cerrada
                print("\n[Conexión cerrada por el servidor]")
                sock.close()
                sys.exit(0)

            # Imprimimos el bloque recibido tal cual llegó
            # (podría ser “Cliente …”, una respuesta a :status,
            #  un historial, etc.)
            print(f"\n{datos}", end="", flush=True)

            # Volvemos a mostrar el prompt del ejecutivo
            # para que pueda seguir escribiendo comandos.
            print("> ", end="", flush=True)

        except OSError:
            # El socket se cerró desde otro hilo (:exit) → salimos.
            break
        except Exception as e:
            print(f"\n[Error receptor: {e}]")
            break

def terminal_ejecutivo():
    HOST = '127.0.0.1'
    PORT = 8889
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.send("EJECUTIVO".encode())

    print("¡Bienvenido a la plataforma de servicio al cliente de la tienda TC5G!")
    print("Para autenticarse ingrese su mail y contraseña:")

    # Paso 1: Enviar correo
    usuario = input("usuario: ")
    s.send(usuario.encode())

    # Paso 2: esperar solicitudes de contraseña e intentar hasta 3 veces
    while True:
        respuesta = s.recv(1024).decode()
        print("Asistente:", respuesta.strip())

        if "Contraseña:" in respuesta:
            clave = input("")
            s.send(clave.encode())
        elif "Bienvenido/a" in respuesta or "Hola " in respuesta:
            # ✅ Lanzar hilo para escuchar mensajes del cliente
            threading.Thread(target=recibir_mensajes, args=(s,), daemon=True).start()
            break

        elif "Demasiados intentos" in respuesta or "Correo no encontrado" in respuesta or "Formato inválido" in respuesta:
            s.close()
            return

    mostrar_menu()

    while True:
        comando = input("\n> ").strip()
        if not comando:
            continue

        s.send(comando.encode())

        # 🔽 NO hacemos ningún recv aquí.
        # La respuesta (si hay) la mostrará recibir_mensajes()

        if comando == ":exit":
            print("Sesión cerrada.")
            break

            # Esperamos UNA respuesta del servidor (lista, catálogo, historial, …)
            respuesta = s.recv(4096).decode()
            print("Asistente:\n" + respuesta)

        # ▸ Si NO empieza con ":", es texto de chat ↦ no bloqueamos con recv()
        #   ──» El hilo `recibir_mensajes()` mostrará lo que llegue.

    s.close()

if __name__ == "__main__":
    terminal_ejecutivo()