import socket
import threading
import json
from datetime import datetime

# Carga de base de datos
FILEPATH = 'databaseclientes.json'
with open(FILEPATH, encoding='utf-8') as f:
    DB = json.load(f)

HOST = '127.0.0.1'
PORT = 5000

# Estructuras globales
STATE = {"clientes_linea": {},
         "ejecutivos_linea":{}}   # email -> socket
clientes_espera = []
parejas = {}   # ejecutivo_socket -> cliente_socket
mutex = threading.Lock()

def autenticar(sock, seccion):
    """
    Autentica un usuario en la sección CLIENTES o EJECUTIVOS.
    Devuelve (email, nombre) o (None, None) si falla.
    """
    with mutex:
        data = json.load(open(FILEPATH, encoding='utf-8'))
    usuarios = data.get(seccion, {})

    # Bucle email
    while True:
        sock.send("Email: ".encode())
        email = sock.recv(1024).decode().strip()
        if not email:
            sock.send("No se ingresó un correo. Intente nuevamente.\n".encode())
            continue
        if email not in usuarios:
            sock.send("Correo no registrado. Intente nuevamente.\n".encode())
            continue
        usuario = usuarios[email]
        break

    # Bucle contraseña (3 intentos)
    intentos = 0
    while intentos < 3:
        sock.send("Contraseña: ".encode())
        pwd = sock.recv(1024).decode().strip()
        # manejar clave mal codificada
        real_pwd = usuario.get('clave') 
        if pwd == real_pwd:
            nombre = usuario.get('nombre', email)
            # registrar en línea
            key = "clientes_linea" if seccion=="CLIENTES" else "ejecutivos_linea"
            with mutex:
                STATE[key][email] = sock
            # registrar ingreso
            with mutex:
                data.setdefault("Ingresados", []).append({
                    "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "acción": f"{seccion[:-1].capitalize()} {nombre} conectado"
                })
                with open(FILEPATH, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
            return email, nombre
        else:
            intentos += 1
            sock.send(f"Contraseña incorrecta. Intento {intentos}/3\n".encode())

    sock.send("Demasiados intentos fallidos. Conexión cerrada.\n".encode())
    return None, None

#============================================================================================================
#============================================================================================================
# 2. FUNCIÓN HISTORIAL DE OPERACIONES
#============================================================================================================
#============================================================================================================
from datetime import datetime, timedelta

def historial_de_operaciones(sock, email):
    """
    • Muestra las transacciones de los últimos 12 meses.
    • Envía un resumen numerado.
    • Si el usuario lo desea, muestra el detalle de alguna.
    """
    try:
        with mutex:
            with open(FILEPATH, "r", encoding="utf-8") as f:
                data = json.load(f)

        cliente = data["CLIENTES"].get(email)
        if not cliente:
            sock.send("Error: cliente no encontrado.\n".encode())
            return

        transacciones = cliente.get("transacciones", [])
        if not transacciones:
            sock.send("No tienes transacciones registradas.\n".encode())
            return

        ahora = datetime.now()
        hace_un_ano = ahora - timedelta(days=365)

        recientes = [
            t for t in transacciones
            if datetime.strptime(t["fecha"], "%Y-%m-%d %H:%M:%S") >= hace_un_ano
        ]

        if not recientes:
            sock.send("No tienes transacciones en el último año.\n".encode())
            return

        mensaje = "\n--- Historial último año ---\n"
        for i, op in enumerate(recientes, 1):
            fecha = op["fecha"]
            mensaje += f"[{i}] ({fecha})\n"
        mensaje += "¿Desea ver más detalles de alguno? (0 = No): "
        sock.send(mensaje.encode())

        try:
            eleccion = int(sock.recv(1024).decode().strip())
        except ValueError:
            sock.send("Entrada inválida.\n".encode())
            return

        if eleccion == 0:
            return
        if not (1 <= eleccion <= len(recientes)):
            sock.send("Número fuera de rango.\n".encode())
            return

        op = recientes[eleccion - 1]

        detalle = (
            f"[{eleccion}] {op['tipo']} ({op['fecha']})\n"
            f"* {op['producto']} [x{op.get('cantidad', 1)}]\n"
            f"Estado: {op['estado']}\n"
        )
        sock.send(detalle.encode())

    except Exception as e:
        print(f"[ERROR] historial_de_operaciones: {e}")
        sock.send("Ocurrió un error al cargar el historial.\n".encode())






def handle_cliente(conn, addr):
    # saludo y login…
    conn.send(
        "¡Bienvenido a la plataforma de servicio al cliente de la tienda TC5G!\n"
        " Para autenticarse ingrese su mail y contraseña.\n".encode()
    )
    email, nombre = autenticar(conn, 'CLIENTES')
    if not email:
        conn.close()
        return

    # menú y lógica principal
    while True:
        # mostramos el menú
        menu = (
            f"Asistente: ¡Bienvenido {nombre}! ¿En qué te podemos ayudar?\n"
            "[1] Cambio de contraseña.\n"
            "[2] Historial de operaciones.\n"
            "[3] Catálogo de productos / Comprar productos.\n"
            "[4] Solicitar devolución.\n"
            "[5] Confirmar envío.\n"
            "[6] Contactarse con un ejecutivo.\n"
            "[7] Salir\n"
            "Ingrese un número: "
        )
        conn.send(menu.encode())

        raw = conn.recv(1024)
        if not raw:
            break
        opt = raw.decode().strip()

        # Opción 1: Cambio de contraseña
        if opt == '1':
            conn.send("Ingrese nueva contraseña: ".encode())
            new1 = conn.recv(1024).decode().strip()
            conn.send("Confirme nueva contraseña: ".encode())
            new2 = conn.recv(1024).decode().strip()
            if new1 == new2:
                # actualizar JSON como antes…
                with mutex:
                    data = json.load(open(FILEPATH, encoding='utf-8'))
                    data['CLIENTES'][email]['clave'] = new1
                    with open(FILEPATH, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                conn.send("Contraseña cambiada con éxito.\n".encode())
            else:
                conn.send("No coinciden, operación cancelada.\n".encode())

         # Opción 2: Historial de operaciones
        elif opt == '2':
            historial_de_operaciones(conn, email)


        # Opción 6: Contactarse con ejecutivo
        elif opt == '6':
            with mutex:
                clientes_espera.append((conn, email))
            conn.send("Quedaste en cola, espera a un ejecutivo...\n".encode())
            # espera emparejamiento
            while True:
                with mutex:
                    current = list(parejas.values())
                if any(conn is c for c, _ in current):
                    conn.send("Conectado a ejecutivo. Empieza a chatear.\n".encode())
                    break
            # chat con ejecutivo
            while True:
                msg = conn.recv(1024)
                if not msg:
                    break
                txt = msg.decode().strip()
                if txt.lower() in ('7', 'salir'):
                    conn.send("Desconectando chat...\n".encode())
                    break
                for ej, (cli, _) in parejas.items():
                    if cli is conn:
                        ej.send(f"Cliente: {txt}\n".encode())

        # Opción 7: Salir
        elif opt == '7':
            conn.send("Hasta pronto.\n".encode())
            break

        # Opción no implementada
        else:
            conn.send(f"Opción {opt} no implementada.\n".encode())

        # Pregunta después de cada operación
        conn.send("Asistente: ¿Desea realizar otra operación? (0=no) ".encode())
        again = conn.recv(1024)
        if not again or again.decode().strip() == '0':
            conn.send("Sesión finalizada. ¡Hasta luego!\n".encode())
            break
        # si no es '0', el bucle vuelve a mostrar el menú

    conn.close()



def handle_ejecutivo(conn, addr):
    conn.send(
        "¡Bienvenido a la plataforma de servicio al cliente de la tienda TC5G!\n"
        " Para autenticarse ingrese su mail y contraseña.\n".encode()
    )
    email, nombre = autenticar(conn, "EJECUTIVOS")
    if not email:
        conn.close()
        return

    conn.send(f"Hola {nombre}, hay {len(clientes_espera)} clientes en espera.\n".encode())

    while True:
        raw = conn.recv(1024)
        if not raw:
            continue
        line = raw.decode().strip()
        lower = line.lower()

        # --- comando :connect inicia chat ---
        if lower == ':connect':
            with mutex:
                if not clientes_espera:
                    conn.send("No hay clientes en espera.\n".encode())
                    continue
                cli_conn, cli_email = clientes_espera.pop(0)
                parejas[conn] = (cli_conn, cli_email)
            conn.send(f"Conectado a cliente {cli_email}\n".encode())

            # bucle de chat hasta :disconnect
            while True:
                chat_raw = conn.recv(1024)
                if not chat_raw:
                    break
                msg = chat_raw.decode().strip()
                if msg.lower() == ':disconnect':
                    with mutex:
                        parejas.pop(conn, None)
                    conn.send("Chat terminado.\n".encode())
                    cli_conn.send("El ejecutivo se desconectó.\n".encode())
                    break
                # reenviar al cliente
                cli_conn.send(f"Ejecutivo: {msg}\n".encode())
            continue

        # --- resto de comandos “colon” ---
        if lower == ':status':
            conn.send(f"Clientes en espera: {len(clientes_espera)}\n".encode())

        elif lower == ':details':
            conn.send("Clientes en espera:\n".encode())
            for _, e in clientes_espera:
                conn.send(f" - {e}\n".encode())

        elif lower == ':catalogue':
            conn.send("Catálogo de productos:\n".encode())
            for prod, info in DB.get('PRODUCTOS', {}).items():
                conn.send(f" * {prod}: stock={info['stock']} precio={info['precio']}\n".encode())

        elif lower == ':disconnect':
            # en caso de llamarlo fuera de chat
            conn.send("No estabas conectado a ningún cliente.\n".encode())

        elif lower == ':exit':
            conn.send("Hasta luego, Ejecutivo.\n".encode())
            break

        else:
            conn.send(f"Comando '{line}' no implementado.\n".encode())

    conn.close()


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(10)
    print(f"[SERVIDOR] Escuchando en {HOST}:{PORT}")

    while True:
        conn, addr = s.accept()
        # primera línea recibida para distinguir rol
        role = conn.recv(1024).decode().strip().lower()
        if role == 'cliente':
            threading.Thread(target=handle_cliente, args=(conn, addr), daemon=True).start()
        else:
            threading.Thread(target=handle_ejecutivo, args=(conn, addr), daemon=True).start()

if __name__ == '__main__':
    main()