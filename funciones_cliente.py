"""
Funciones del menú
"""
def cambiar_contrasena(sock, email): #pide la contraseña actual, luego la nueva, y actualiza base_clientes.json.
    sock.send("Ingresa nueva contraseña:\n".encode())
    nueva = sock.recv(1024).decode().strip()
    # Guardar en JSON, confirmar, etc.

def historial_de_operaciones(sock, email): #busca las operaciones del cliente (por correo, por ejemplo) en operaciones.json
    # Leer operaciones.json o base_clientes.json
    sock.send("Tu historial es:\n...".encode())

def comprar_cartas(sock, email): #carga catalogo.json, muestra cartas disponibles, permite elegir, actualiza stock y guarda en historial.
    # Mostrar productos del catálogo, restar stock, etc.
    pass

def devolver_cartas(sock, email): #cambia el estado de una operación a “devuelto” y suma el stock.
    # Buscar la carta, cambiar estado de operación, sumar stock
    pass

def confirmar_envio(sock, email): #marca una operación pendiente como “recibido” o “finalizado”.
    # Confirmar que cliente recibió el pedido
    pass

def contactar_ejecutivo(sock, email): #envía el cliente a una cola (puede ser una lista compartida o archivo queue.json), esperar match con ejecutivo
    # Meterlo a la cola, esperar match con ejecutivo
    pass