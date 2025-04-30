import socket


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

def terminal_ejecutivo():
    HOST = '127.0.0.1'
    PORT = 8889
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.send("EJECUTIVO".encode())

    # Mensaje de bienvenida antes de autenticación
    print("¡Bienvenido a la plataforma de servicio al cliente de la tienda TC5G!")
    print("Para autenticarse ingrese su mail y contraseña:")
    usuario = input("usuario: ")
    clave = input("contraseña: ")
    s.send(f"EJECUTIVO|{usuario}|{clave}".encode())

    # Mensaje del servidor después de autenticación
    respuesta = s.recv(1024).decode()
    print("Asistente:", respuesta)
    if "Correo no encontrado" in respuesta or "Contraseña incorrecta" in respuesta or "Formato inválido" in respuesta:
        s.close()
        return

    mostrar_menu()

    while True:
        comando = input("\n> ").strip()
        if not comando:
            continue

        s.send(comando.encode())

        if comando == ":exit":
            print("Sesión cerrada.")
            break

        else:
            respuesta = s.recv(4096).decode()
            print("Asistente:\n" + respuesta)

    s.close()

if __name__ == "__main__":
    terminal_ejecutivo()