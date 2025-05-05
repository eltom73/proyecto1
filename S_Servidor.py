import socket
import threading
import json
from datetime import datetime, timedelta

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
# 1. FUNCIÓN CAMBIAR CLAVE
#============================================================================================================

def cambiar_clave(sock, email):
    try:
        sock.send("Ingrese nueva contraseña: ".encode())
        new1 = sock.recv(1024).decode().strip()
        sock.send("Confirme nueva contraseña: ".encode())
        new2 = sock.recv(1024).decode().strip()

        if new1 != new2:
            sock.send("No coinciden, operación cancelada.\n".encode())
            return

        with mutex:
            with open(FILEPATH, "r+", encoding="utf-8") as f:
                data = json.load(f)
                data["CLIENTES"][email]["clave"] = new1
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()

        sock.send("✅ Contraseña cambiada con éxito.\n".encode())

    except Exception as e:
        print(f"[ERROR] cambiar_clave: {e}")
        sock.send("⚠️ Error al cambiar la contraseña.\n".encode())

#============================================================================================================
# 2. FUNCIÓN HISTORIAL DE OPERACIONES
#============================================================================================================

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

#============================================================================================================
# 3. FUNCIÓN COMPRAR CARTAS
#============================================================================================================

def comprar_cartas(sock, email, nombre):
    try:
        with mutex:
            with open(FILEPATH, "r+", encoding="utf-8") as f:
                data = json.load(f)
                catalogo = data.get("PRODUCTOS")
                if not catalogo or not isinstance(catalogo, dict):
                    sock.send("Catálogo no disponible o malformado.\n".encode())
                    return

                mensaje = "\n--- Catálogo de cartas ---\n"
                for i, (nombre_carta, detalles) in enumerate(catalogo.items(), 1):
                    mensaje += f"{i}. {nombre_carta} - Precio: {detalles['precio']} - Stock: {detalles['stock']}\n"
                sock.send(mensaje.encode())

                sock.send("Elige el número de la carta que deseas comprar (0 = cancelar): ".encode())
                try:
                    seleccion = int(sock.recv(1024).decode().strip())
                except ValueError:
                    sock.send("Error: Ingrese un número válido.\n".encode())
                    return

                if seleccion == 0:
                    sock.send("Compra cancelada.\n".encode())
                    return

                if seleccion < 1 or seleccion > len(catalogo):
                    sock.send("Selección inválida.\n".encode())
                    return

                carta = list(catalogo.keys())[seleccion - 1]
                detalles = catalogo[carta]

                if detalles["stock"] <= 0:
                    sock.send("No hay stock disponible para esta carta.\n".encode())
                    return

                sock.send(f"¿Confirmar compra de {carta} por {detalles['precio']}? (si/no): ".encode())
                confirmacion = sock.recv(1024).decode().strip().lower()
                if confirmacion != "si":
                    sock.send("Compra cancelada.\n".encode())
                    return

                sock.send("¿Cuántas cartas desea comprar?: ".encode())
                try:
                    cantidad = int(sock.recv(1024).decode().strip())
                except ValueError:
                    sock.send("Cantidad inválida.\n".encode())
                    return

                if cantidad > detalles["stock"]:
                    sock.send("No hay suficiente stock disponible.\n".encode())
                    return

                # Actualizar stock
                detalles["stock"] -= cantidad

                # Registrar transacción
                transaccion = {
                    "tipo": "compra",
                    "producto": carta,
                    "cantidad": cantidad,
                    "precio": detalles["precio"],
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "estado": "envío pendiente"
                }

                cliente = data["CLIENTES"][email]
                cliente.setdefault("transacciones", []).append(transaccion)

                # Guardar
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()

                sock.send(f"✅ Compra exitosa: {cantidad}x {carta}.\n".encode())

    except Exception as e:
        print(f"[ERROR] comprar_cartas: {e}")
        sock.send("⚠️ Error al procesar la compra.\n".encode())

#============================================================================================================
# 4. FUNCIÓN DEVOLVER CARTAS
#============================================================================================================

def devolver_cartas(sock, email, nombre):
    try:
        with mutex:
            with open(FILEPATH, "r+", encoding="utf-8") as f:
                data = json.load(f)

                transacciones = data["CLIENTES"].get(email, {}).get("transacciones", [])
                compras = [
                    t for t in transacciones
                    if t["tipo"] == "compra" and t["estado"] in ("envío pendiente", "envío confirmado")
                ]

                if not compras:
                    sock.send("No tienes compras devolvibles registradas.\n".encode())
                    return

                mensaje = "\n--- Compras disponibles para devolución ---\n"
                for i, compra in enumerate(compras, 1):
                    mensaje += f"{i}. Producto: {compra['producto']}, Fecha: {compra['fecha']}, Estado: {compra['estado']}\n"
                sock.send(mensaje.encode())

                sock.send("Elige el número de la carta que deseas devolver (0 = cancelar): ".encode())
                try:
                    seleccion = int(sock.recv(1024).decode().strip())
                except ValueError:
                    sock.send("⚠️ Error: Ingrese un número válido.\n".encode())
                    return

                if seleccion == 0:
                    sock.send("Devolución cancelada.\n".encode())
                    return
                if seleccion < 1 or seleccion > len(compras):
                    sock.send("⚠️ Error: Selección fuera de rango.\n".encode())
                    return

                compra = compras[seleccion - 1]
                carta = compra["producto"]

                sock.send(f"¿Confirmar devolución de {carta}? (si/no): ".encode())
                confirmacion = sock.recv(1024).decode().strip().lower()
                if confirmacion != "si":
                    sock.send("Devolución cancelada.\n".encode())
                    return

                sock.send("¿Cuántas cartas desea devolver?: ".encode())
                try:
                    cantidad = int(sock.recv(1024).decode().strip())
                except ValueError:
                    sock.send("⚠️ Cantidad inválida.\n".encode())
                    return

                data["PRODUCTOS"][carta]["stock"] += cantidad

                nueva_transaccion = {
                    "tipo": "devolución",
                    "producto": carta,
                    "cantidad": cantidad,
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "estado": "devuelto"
                }

                data["CLIENTES"][email].setdefault("transacciones", []).append(nueva_transaccion)

                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()

                sock.send(f"✅ Devolución exitosa: {cantidad}x {carta}.\n".encode())

    except Exception as e:
        print(f"[ERROR] devolver_cartas: {e}")
        sock.send("⚠️ Error al procesar la devolución.\n".encode())

#============================================================================================================
# 5. FUNCIÓN CONFIRMAR ENVÍO
#============================================================================================================

def confirmar_envio(sock, email, nombre):
    try:
        with mutex:
            with open(FILEPATH, "r+", encoding="utf-8") as f:
                data = json.load(f)
                transacciones = data["CLIENTES"][email].get("transacciones", [])
                pendientes = [
                    t for t in transacciones
                    if t["tipo"] == "compra" and t["estado"] == "envío pendiente"
                ]

                if not pendientes:
                    sock.send("No tienes compras pendientes de confirmación.\n".encode())
                    return

                mensaje = "\n--- Compras pendientes de confirmación ---\n"
                for i, compra in enumerate(pendientes, 1):
                    mensaje += f"{i}. Producto: {compra['producto']}, Fecha: {compra['fecha']}, Estado: {compra['estado']}\n"
                sock.send(mensaje.encode())

                sock.send("Elige el número de la compra que deseas confirmar (0 = cancelar): ".encode())
                try:
                    seleccion = int(sock.recv(1024).decode().strip())
                except ValueError:
                    sock.send("⚠️ Error: Ingrese un número válido.\n".encode())
                    return

                if seleccion == 0:
                    sock.send("Confirmación cancelada.\n".encode())
                    return

                if seleccion < 1 or seleccion > len(pendientes):
                    sock.send("⚠️ Selección fuera de rango.\n".encode())
                    return

                compra = pendientes[seleccion - 1]
                carta = compra["producto"]

                sock.send(f"¿Confirmar recepción de {carta}? (si/no): ".encode())
                confirmacion = sock.recv(1024).decode().strip().lower()
                if confirmacion != "si":
                    sock.send("Confirmación cancelada.\n".encode())
                    return

                compra["estado"] = "envío confirmado"
                compra["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()

                sock.send(f"✅ Confirmación exitosa: recepción de {carta}.\n".encode())

    except Exception as e:
        print(f"[ERROR] confirmar_envio: {e}")
        sock.send("⚠️ Error al procesar la confirmación.\n".encode())




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
            cambiar_clave(conn, email)
        
         # Opción 2: Historial de operaciones
        elif opt == '2':
            historial_de_operaciones(conn, email)

        # Opción 3: Catálogo de productos / Comprar productos
        elif opt == '3':
            comprar_cartas(conn, email, nombre)

        # Opción 4: Solicitar devolución
        elif opt == '4':
            devolver_cartas(conn, email, nombre)

        # Opción 5: Confirmar envío
        elif opt == '5':
            confirmar_envio(conn, email, nombre)

        # Opción 6: Contactarse con ejecutivo
        elif opt == '6':
            with mutex:
                clientes_espera.append((conn, email))

                # Cargar nombre del cliente
                with open(FILEPATH, encoding='utf-8') as f:
                    data = json.load(f)
                nombre_cli = data["CLIENTES"].get(email, {}).get("nombre", email)

                # Avisar a todos los ejecutivos conectados
                alerta = f"\n⚠️ Nuevo cliente en espera: {nombre_cli} (correo: {email})\n"
                for sock_ej in STATE["ejecutivos_linea"].values():
                    try:
                        sock_ej.send(alerta.encode())
                    except:
                        pass  # en caso de que el socket se haya cerrado o esté caído

            conn.send("Quedaste en cola, espera a un ejecutivo...\n".encode())

            # espera emparejamiento
            while True:
                with mutex:
                    current = list(parejas.values())
                for ej, (cli, _) in parejas.items():
                    if cli is conn:
                        # Obtener nombre del ejecutivo
                        with open(FILEPATH, encoding='utf-8') as f:
                            data = json.load(f)
                        for correo_ej, datos in data["EJECUTIVOS"].items():
                            if STATE["ejecutivos_linea"].get(correo_ej) is ej:
                                nombre_ej = datos.get("nombre", correo_ej)
                                break
                        else:
                            nombre_ej = "desconocido"
                        conn.send(f"Conectado a ejecutivo {nombre_ej}. Empieza a chatear.\n".encode())
                        break  # <- rompe el for
                else:
                    continue  # si no encontró pareja, sigue esperando
                break  # <- rompe el while si encontró pareja

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


#============================================================================================================
# FUNCIÓN PARA :history
#============================================================================================================

def reunir_historial_cliente(cli_email):
    """
    Devuelve (texto_historial, nombre_cliente) listos para enviar.
    Reúne:
      • Cambios de contraseña
      • Transacciones (compras y devoluciones)
      • Actividades registradas en data["Ingresados"]
    """
    with open(FILEPATH, encoding='utf-8') as f:
        data = json.load(f)

    cli_data  = data["CLIENTES"].get(cli_email, {})
    nombre_cli = cli_data.get("nombre", cli_email)

    # 1. Cambios de contraseña
    cambios = cli_data.get("cambios de contraseña", [])
    txt_cambios = "\n--- Cambios de contraseña ---\n"
    if cambios:
        for c in cambios:
            txt_cambios += f"* {c['fecha']}  →  nueva clave: {c['nueva']}\n"
    else:
        txt_cambios += "Sin cambios registrados.\n"

    # 2. Transacciones (compras / devoluciones)
    trans = cli_data.get("transacciones", [])
    txt_trans = "\n--- Transacciones ---\n"
    if trans:
        for t in trans:
            txt_trans += (f"* {t['fecha']}  [{t['tipo']}] {t['producto']}  "
                          f"x{t.get('cantidad',1)}  estado: {t['estado']}\n")
    else:
        txt_trans += "Sin transacciones registradas.\n"

    # 3. Actividad en “Ingresados”
    logs = [log for log in data.get("Ingresados", [])
            if nombre_cli in log.get("acción", "")]
    txt_logs = "\n--- Actividad general ---\n"
    if logs:
        for l in logs:
            txt_logs += f"* {l.get('timestamp','?')}  – {l.get('acción','')}\n"
    else:
        txt_logs += "Sin registros de actividad.\n"

    historial = (f"\n========== Historial de {nombre_cli} ==========\n"
                 f"{txt_cambios}{txt_trans}{txt_logs}"
                 "==============================================\n")
    return historial, nombre_cli



# =========================================================================================================
# FUNCIÓN PRINCIPAL DEL EJECUTIVO
# =========================================================================================================
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
        line   = raw.decode().strip()
        lower  = line.lower()

        # ------------------------------------------------------------------ #
        # :connect  →   empieza un chat uno-a-uno con el cliente en espera
        # ------------------------------------------------------------------ #
        if lower == ':connect':
            with mutex:
                if not clientes_espera:
                    conn.send("No hay clientes en espera.\n".encode())
                    continue
                cli_conn, cli_email = clientes_espera.pop(0)
                parejas[conn] = (cli_conn, cli_email)

                # obtener nombre del cliente
                with open(FILEPATH, encoding='utf-8') as f:
                    data = json.load(f)
                cli_nombre = data["CLIENTES"].get(cli_email, {}).get("nombre", cli_email)

            conn.send(f"Conectado a cliente {cli_nombre} (correo: {cli_email})\n".encode())

        # -------------- BUCLE DE CHAT ACTIVO --------------
        while True:
            chat_raw = conn.recv(1024)
            if not chat_raw:
                break

            msg_original = chat_raw.decode()
            cmd = msg_original.lower().strip()        # ← normalizamos una vez

            # ---- 1. Desconexión explícita ----
            if cmd == ':disconnect':
                with mutex:
                    parejas.pop(conn, None)
                conn.send("Chat terminado.\n".encode())
                cli_conn.send("El ejecutivo se desconectó.\n".encode())
                break

            # ---- 2. HISTORIAL DEL CLIENTE ----
            elif cmd == ':history':
                try:
                    historial, _ = reunir_historial_cliente(cli_email)
                    conn.send(historial.encode())
                    conn.send("¿Enviar historial al cliente? (1 = sí / 0 = no): ".encode())
                    resp = conn.recv(1024).decode().strip()
                    if resp == '1':
                        cli_conn.send(historial.encode())
                        conn.send("Historial enviado al cliente.\n".encode())
                    else:
                        conn.send("Historial NO enviado al cliente.\n".encode())
                except Exception as e:
                    conn.send(f"⚠️ Error al obtener historial: {e}\n".encode())
                continue  # no reenvía el comando al cliente

            # ---- 3. Cualquier otro mensaje se reenvía ----
            cli_conn.send(f"Ejecutivo: {msg_original}\n".encode())


        # ------------------------------------------------------------------ #
        # RESTO DE COMANDOS “COLON” (fuera de chat)
        # ------------------------------------------------------------------ #
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
            # llamado fuera de un chat activo
            conn.send("No estabas conectado a ningún cliente.\n".encode())

        elif lower == ':exit':
            conn.send("Hasta luego, Ejecutivo.\n".encode())
            break

        else:
            conn.send(f"Comando '{line}' no implementado.\n".encode())

    conn.close()
# =========================================================================================================


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