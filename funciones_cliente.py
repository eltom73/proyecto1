"""
Funciones del menú
"""
import json
from servidor import FILEPATH, mutex  # usamos el mismo archivo JSON
from datetime import datetime

def menu_cliente(sock, email, nombre):
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
            historial_de_operaciones(sock, email, nombre)
        elif opcion == "3":
            comprar_cartas(sock, email, nombre)
        elif opcion == "4":
            devolver_cartas(sock, email, nombre)
        elif opcion == "5":
            confirmar_envio(sock, email, nombre)
        elif opcion == "6":
            contactar_ejecutivo(sock, email, nombre)
        elif opcion == "7":
            sock.send("Sesión finalizada. ¡Hasta luego!\n".encode())
            break
        else:
            sock.send("Opción inválida. Intenta nuevamente.\n".encode())


def cambiar_contrasena(sock, email):
    """Permite al cliente cambiar su contraseña y la guarda en el historial."""
    try:
        sock.send("Ingrese su nueva contraseña: ".encode())
        nueva = sock.recv(1024).decode().strip()

        sock.send("Confirme la nueva contraseña: ".encode())
        confirmacion = sock.recv(1024).decode().strip()

        if nueva != confirmacion:
            sock.send("Las contraseñas no coinciden. Inténtelo nuevamente.\n".encode())
            return

        # Actualizar el archivo JSON
        with mutex:
            with open(FILEPATH, "r+") as f:
                data = json.load(f)
                data["CLIENTES"][email]["contrasena"] = nueva
                data["CLIENTES"][email]["cambios de contrasena"].append({
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "nueva": nueva
                })
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()

        sock.send("¡Contraseña cambiada exitosamente!\n".encode())

    except Exception as e:
        print(f"[SERVIDOR] Error al cambiar contraseña: {e}")
        sock.send("Ocurrió un error al cambiar la contraseña.\n".encode())


def historial_de_operaciones(sock, email, nombre):
    try:
        with mutex:
            with open(FILEPATH, "r") as f:
                data = json.load(f)

        cliente = data["CLIENTES"].get(email)

        if not cliente:
            sock.send("Error: cliente no encontrado.\n".encode())
            return

        historial = cliente.get("transacciones", [])

        if not historial:
            sock.send("No tienes transacciones registradas.\n".encode())
            return

        mensaje = "\n--- Historial de operaciones ---\n"
        for i, operacion in enumerate(historial, 1):
            linea = (
                f"{i}. {operacion['tipo'].capitalize()} - "
                f"{operacion['producto']} - "
                f"{operacion['fecha']} - "
                f"Estado: {operacion['estado']}\n"
            )
            mensaje += linea

        sock.send(mensaje.encode())

    except Exception as e:
        print(f"[ERROR] historial_de_operaciones: {e}")
        sock.send("Ocurrió un error al cargar el historial.\n".encode())


def comprar_cartas(sock, email, nombre): #carga catalogo.json, muestra cartas disponibles, permite elegir, actualiza stock y guarda en historial.
    # Mostrar productos del catálogo, restar stock, etc.
    pass

def devolver_cartas(sock, email, nombre): #cambia el estado de una operación a “devuelto” y suma el stock.
    # Buscar la carta, cambiar estado de operación, sumar stock
    pass

def confirmar_envio(sock, email, nombre): #marca una operación pendiente como “recibido” o “finalizado”.
    # Confirmar que cliente recibió el pedido
    pass

def contactar_ejecutivo(sock, email, nombre): #envía el cliente a una cola (puede ser una lista compartida o archivo queue.json), esperar match con ejecutivo
    # Meterlo a la cola, esperar match con ejecutivo
    pass