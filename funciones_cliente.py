"""
Funciones del menú
"""

import json
import socket
import threading    
from shared_state import FILEPATH, mutex, STATE
from datetime import datetime, timedelta   


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
            cambiar_contrasena(sock, email,nombre)

        elif opcion == "2":
            historial_de_operaciones(sock, email)

        elif opcion == "3":
            comprar_cartas(sock, email,nombre)

        elif opcion == "4":
            devolver_cartas(sock, email,nombre)

        elif opcion == "5":
            confirmar_envio(sock, email, nombre)

        elif opcion == "6":
            contactar_ejecutivo(sock, email, nombre)
            chat_con_ejecutivo(sock)
            return  # Salimos del menú porque ya está en el chat

        
        elif opcion == "7":
            sock.send("Sesión finalizada. ¡Hasta luego!\n".encode())
            break
        else:
            sock.send("Opción inválida. Intenta nuevamente.\n".encode())


def cambiar_contrasena(sock, email,nombre):
    """Permite al cliente cambiar su contraseña y la guarda en el historial."""
    try:
        sock.send("Ingrese su nueva contraseña: ".encode())  #Solicitar nueva contraseña al cliente en su terminal
        nueva = sock.recv(1024).decode().strip()

        sock.send("Confirme la nueva contraseña: ".encode()) #Solicitar confirmación de contraseña al cliente en su terminal
        confirmacion = sock.recv(1024).decode().strip()

        if nueva != confirmacion: #Verificar que las contraseñas coincidan
            sock.send("Las contraseñas no coinciden. Inténtelo nuevamente.\n".encode())
            return

        # Actualizar el archivo JSON, es decir, reescribir la contraseña y agregar el cambio al historial
        with mutex:
            with open(FILEPATH, "r+") as f:
                data = json.load(f)
                data["CLIENTES"][email]["contraseña"] = nueva #Actualizar la contraseña en el archivo JSON
                data["CLIENTES"][email]["cambios de contraseña"].append({ #Agregar el cambio de contraseñal al historial del cliente
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "nueva": nueva
                })
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()

        sock.send("¡Contraseña cambiada exitosamente!\n".encode())
        print(f"[SERVIDOR] Contraseña cambiada para el cliente {nombre}.") #mensaje para el servidor con tal de detectar estado de la operación

    except Exception as e:
        print(f"[SERVIDOR] Error al cambiar contraseña: {e}")
        sock.send("Ocurrió un error al cambiar la contraseña.\n".encode())


def historial_de_operaciones(sock, email):
    """
    • Muestra las transacciones de los últimos 12 meses.
    • Primero envía un listado resumido [n] (fecha).
    • Luego pregunta qué entrada quiere detallar.
    """
    try:
        # ---------- CARGAR DATOS ----------
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

        # ---------- FILTRAR ÚLTIMO AÑO ----------
        ahora = datetime.now()
        hace_un_ano = ahora - timedelta(days=365)
        recientes = [
            t for t in transacciones
            if datetime.strptime(t["fecha"], "%Y-%m-%d %H:%M:%S") >= hace_un_ano
        ]

        if not recientes:
            sock.send("No tienes transacciones en el último año.\n".encode())
            return

        # ---------- LISTADO RESUMEN ----------
        mensaje = "\n--- Historial último año ---\n"
        for i, op in enumerate(recientes, 1):
            fecha = op["fecha"]
            mensaje += f"[{i}] ({fecha})\n"
        mensaje += "¿Desea ver más detalles de alguno? (0 = No): "
        sock.send(mensaje.encode())

        # ---------- PREGUNTAR NÚMERO ----------
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

        op = recientes[eleccion - 1]  # transacción elegida

        # ---------- DETALLE COMPLETO ----------
        detalle = (
            f"[{eleccion}] {op['tipo']} ({op['fecha']})\n"
            f"* {op['producto']} [x{op.get('cantidad',1)}]\n"
            f"Estado: {op['estado']}\n"
        )
        sock.send(detalle.encode())

    except Exception as e:
        print(f"[ERROR] historial_de_operaciones: {e}")
        sock.send("Ocurrió un error al cargar el historial.\n".encode())



def comprar_cartas(sock, email,nombre): #carga catalogo.json, muestra cartas disponibles, permite elegir, actualiza stock y guarda en historial.
    # Mostrar productos del catálogo, restar stock, etc.
    try:
        with mutex:
            print("[DEBUG] Cargando catálogo de cartas...")
            with open(FILEPATH, "r+") as f: #abrimos el archivo en modo lectura y escritura con "r+"
                data = json.load(f)
                print("[DEBUG] Archivo JSON cargado correctamente.")

                #catálogo de cartas
                catalogo = data.get("PRODUCTOS") #extraemos la lista "PRODUCTOS" del catálogo de cartas de la data
                if not catalogo:
                    sock.send("No hay cartas disponibles en el catálogo.\n".encode())
                    print("[DEBUG] No hay cartas disponibles en el catálogo.")  
                    return
                if not isinstance(catalogo, dict): 
                    print("[DEBUG] Catálogo de cartas no es un diccionario: {type(catalogo)}") #mensaje para el servidor con tal de detectar errores
                    sock.send("Error: Catálogo de cartas formato no válido.\n".encode())
                    return
                print(f"[DEBUG] Catálogo de cartas cargado correctamente-.{catalogo}")  #Si no existen errores, el catálogo se carga correctamente y se muestra al cliente

                #Catalogo de cartas disponibles. (nombre, precio, stock)
                mensaje = "\n--- Catálogo de cartas ---\n"
                for i, (nombre_carta, detalles) in enumerate(catalogo.items(), 1):
                    mensaje += f"{i}. {nombre_carta} - Precio: {detalles['precio']} - Stock: {detalles['stock']}\n" #Hacemo un barrido de todo el listado de cartas y lo mostramos al cliente
                sock.send(mensaje.encode())

                #Cliente elige carta
                sock.send("Elige el número de la carta que deseas comprar (0 si no desea ninguna): ".encode())     
                try:
                    seleccion = int(sock.recv(1024).decode().strip())   
                except ValueError:
                    sock.send("Error: Ingrese un número válido.\n".encode())
                    print(f"[DEBUG] Selección inválida (no es un número): {seleccion}")
                    return 
                print(f"[SERVDOR] Cliente {nombre} eligió la carta número: {seleccion}") #mensaje para el servidor con tal de detectar errores

                #Validar selección
                if seleccion == 0: #Si elige 0, no compra nada
                    sock.send("Compra cancelada.\n".encode())
                    return
                if seleccion < 1 or seleccion > len(catalogo): #Verifica que la selección esté dentro del rango de cartas disponibles
                    sock.send("Error: Selección inválida.\n".encode())
                    print(f"[DEBUG] Selección inválida (fuera de rango): {seleccion}") #mensaje para el servidor con tal de detectar errores
                    return
                
                carta = list(catalogo.keys())[seleccion - 1] #Selecciona la carta según el índice que ingresó el cliente. La selección se hace en base a la lista de cartas definida como la lista
                                                            # de los valores principales, es decir, el nombre de la carta.
                                                            # Se resta 1 porque las lista en Python empiezan en 0.
                print(f"[SERVIDOR] Cliente {nombre} eligió la carta: {carta}") #mensaje para el servidor con tal de detectar errores
                # Verificar stock
                if catalogo[carta]["stock"] <= 0:
                    sock.send("No hay stock disponible para esta carta.\n".encode())
                    print(f"[DEBUG] No hay stock disponible para la carta: {carta}") #mensaje para el servidor con tal de detectar el tipo de error
                    return
                #Confirmar compra => restar stock y agregar a historial
                sock.send(f"¿Confirmar compra de {carta} por {catalogo[carta]['precio']}? (si/no): ".encode()) #se espera que escriba "si" o "no". No que escriba SI, Si, Sí,....
                confirmacion = sock.recv(1024).decode().strip().lower()
                print(f"[SERVIDOR] Cliente confirmó la compra: {confirmacion}") #mensaje para el servidor con tal de detectar errores

                if confirmacion == "si": #Si confirma la compra=>actualizar stock y agregar a historial
                    #Actualizar stock
                    sock.send("¿Cuantas cartas desea comprar?: ".encode())
                    cantidad = int(sock.recv(1024).decode().strip())
                    print(f"[SERVIDOR] Cliente {nombre} eligió la cantidad: {cantidad}")
                    if cantidad > catalogo[carta]["stock"]:
                        sock.send("No hay suficiente stock disponible.\n".encode())
                        print(f"[DEBUG] No hay suficiente stock disponible para la carta: {carta}")
                        return
                    catalogo[carta]["stock"] -= cantidad #restar la cantidad de cartas compradas al stock de la carta

                    print(f"[SERVIDOR] Stock actualizado para la carta: {carta}. Nuevo stock: {catalogo[carta]['stock']}")

                    #Agregar a historial la transacción
                    nueva_transaccion = {
                        "tipo": "compra",
                        "producto": carta,
                        "cantidad": cantidad,
                        "precio": catalogo[carta]["precio"],
                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "estado": "envío pendiente" #estado inicial de la compra
                    }
                    if "transacciones" not in data["CLIENTES"][email]:
                        data["CLIENTES"][email]["transacciones"] = [] #crear lista de transacciones si no existe
                    data["CLIENTES"][email]["transacciones"].append(nueva_transaccion) #agregar la transacción al historial del cliente

                    #Guardar cambios en el archivo JSON
                    f.seek(0)
                    json.dump(data, f, indent=4)
                    f.truncate()
                    sock.send(f"Compra exitosa!. Ha adquirido {cantidad} {carta}.\n".encode())
                else:
                    sock.send("Compra cancelada.\n".encode()) #no confirmó la compra => no se hace nada
                    print(f"[DEBUG] Compra cancelada por el cliente: {carta}")


    except ValueError:
        sock.send("⚠️ Error: Ingrese un número válido.\n".encode())
    except IndexError:
        sock.send("⚠️ Error: Selección inválida.\n".encode())
    except Exception as e:
        print(f"[ERROR] comprar_cartas: {e}")
        sock.send("⚠️ Error al procesar la compra.\n".encode())

def devolver_cartas(sock, email,nombre): #cambia el estado de una operación a “devuelto” y suma el stock.
    # Buscar la carta, cambiar estado de operación, sumar stock
    try:
        with mutex:
            with open(FILEPATH, "r+") as f:
                data = json.load(f)
                print("[DEBUG] Archivo JSON cargado correctamente.")

                #Obtenemos el historial de transacciones del cliente
                transacciones = data["CLIENTES"].get(email, {}).get("transacciones", []) #extraemos la lista "transacciones" del cliente de la data
                compras = [t for t in transacciones if t["tipo"] == "compra" and (t["estado"] == "envío pendiente" or t["estado"] == "envío confirmado")] #filtramos las compras completadas (las pendientes y confirmadas), ya que la queremos devolver

                if not compras: #Verificamos si hay compras registradas, si no hay, no tiene sentido devolver 
                    sock.send("No tienes compras registradas.\n".encode())
                    print("[DEBUG] No hay compras registradas.")
                    return
                
                #Mostrar compras al cliente
                mensaje = "\n--- Compras registradas ---\n"
                for i, compra in enumerate(compras, 1):
                    mensaje += f"{i}. Producto: {compra['producto']}, Fecha: {compra['fecha']}, Estado: {compra['estado']}\n" #Hacemo un barrido de todo el listado de compras y lo mostramos al cliente
                sock.send(mensaje.encode())

                #Cliente selecciona carta a devolver
                sock.send("Elige el número de la carta que deseas devolver (0 si no desea ninguna): ".encode()) #Cliente elige la carta a devolver según el indice de la lista de compras presentada
                seleccion = int(sock.recv(1024).decode().strip()) #Esperamos que el cliente ingrese un número sobre su selección
                print(f"[SERVIDOR] Cliente {nombre} eligió la carta número: {seleccion}")

                #Validar selección (existen varios casos: 0 = cancelar, fuera de rango = error, válida etc.)
                if seleccion == 0:
                    sock.send("Devolución cancelada.\n".encode())
                    return
                if seleccion < 1 or seleccion > len(compras):
                    sock.send("⚠️ Error: Selección inválida.\n".encode())
                    print(f"[DEBUG] Selección inválida (fuera de rango): {seleccion}")
                    return
                compra = compras[seleccion - 1] #Selecciona la compra según el índice que ingresó el cliente. La selección se hace en base a la lista "compras". El -1 es porque las lista en Python empiezan en 0.
                carta = compra["producto"] #nombre de la carta a devolver

                #Confirmar devolución
                sock.send(f"¿Confirmar devolución de {carta}? (si/no): ".encode()) #se espera que escriba "si" o "no". No que escriba variaciones como SI, Si, Sí,....
                confirmacion = sock.recv(1024).decode().strip().lower()
                print(f"[SERVIDOR] Cliente {nombre} confirmó la devolución: {confirmacion}")

                #Casos: si o no 
                if confirmacion == "si": # => actualizamos el stock => le sumamos 1 unidad al stock de la carta
                    #Actualizar stock
                    sock.send("¿Cuantas cartas desea devolver?: ".encode())
                    cantidad = int(sock.recv(1024).decode().strip()) #Esperamos que el cliente ingrese un número entero sobre su selección, sino se genera un error
                    data["PRODUCTOS"][carta]["stock"] += cantidad
                    print(f"[SERVIDOR] Stock actualizado para la carta: {carta}. Nuevo stock: {data['PRODUCTOS'][carta]['stock']}")
                     #Agregar a historial la transacción
                    nueva_transaccion = {
                        "tipo": "devolución",
                        "producto": carta,
                        "cantidad": cantidad,
                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "estado": "devuelto"
                    }
                    if "transacciones" not in data["CLIENTES"][email]:
                        data["CLIENTES"][email]["transacciones"] = [] #crear lista de transacciones si no existe
                    data["CLIENTES"][email]["transacciones"].append(nueva_transaccion) #agregar la transacción al historial del cliente

                    #Guardar cambios en el archivo JSON
                    f.seek(0)
                    json.dump(data, f, indent=4)
                    f.truncate()
                    sock.send(f"Devolución exitosa!. Has devuelto {carta}.\n".encode())

                else: 
                    sock.send("Devolución cancelada.\n".encode())
                    print(f"[DEBUG] Devolución cancelada por el cliente: {carta}")
    except ValueError:
        sock.send("⚠️ Error: Ingrese un número válido.\n".encode())
    except IndexError:
        sock.send("⚠️ Error: Selección inválida.\n".encode())
    except Exception as e:
        print(f"[ERROR] devolver_cartas: {e}")
        sock.send("⚠️ Error al procesar la devolución.\n".encode())

    

def confirmar_envio(sock, email, nombre): #marca una operación pendiente como “recibido” o “finalizado”.
    # Confirmar que cliente recibió el pedido
    try:
        with mutex:
            with open(FILEPATH, "r+") as f:
                data = json.load(f)
                print("[DEBUG] Archivo JSON cargado correctamente.")

                #Obtenemos el historial de transacciones del cliente
                transacciones = data["CLIENTES"][email].get("transacciones", []) #extraemos la lista "transacciones" del cliente de la data 
                pendientes = [t for t in transacciones if t["tipo"]== "compra" and t["estado"] == "envío pendiente"]

                if not pendientes: #Verificamos si hay compras pendientes, si no hay, no tiene sentido confirmar el envío
                    sock.send("No tienes compras pendientes.\n".encode())
                    print("[DEBUG] No hay compras pendientes.")
                    return
                
                #Mostrar compras pendientes al cliente
                mensaje = "\n--- Compras pendientes de confirmación---\n"
                for i, compra in enumerate(pendientes, 1):
                    mensaje += f"{i}. Producto: {compra['producto']}, Fecha: {compra['fecha']}, Estado: {compra['estado']}\n" #Hacemo un barrido de todo el listado de compras y lo mostramos al cliente
                sock.send(mensaje.encode()) #enviamos el mensaje al cliente

                #Selección de compra a confirmar
                sock.send("Elige el número de la compra que deseas confirmar (0 si no desea ninguna): ".encode())
                seleccion = int(sock.recv(1024).decode().strip()) #Esperamos que el cliente ingrese un número sobre su selección
                print(f"[SERVIDOR] Cliente {nombre} eligió la compra número: {seleccion}")

                if seleccion == 0: #Si elige 0, no confirma nada
                    sock.send("Confirmación cancelada.\n".encode())
                    return
                compra= pendientes[seleccion - 1] #Selecciona la compra según el índice que ingresó el cliente. La selección se hace en base a la lista "pendientes". El -1 es porque las lista en Python empiezan en 0.
                carta = compra["producto"] #nombre de la carta a confirmar

                #Confirmar recepción
                sock.send(f"¿Confirmar recepción de {carta}? (si/no): ".encode()) #se espera que escriba "si" o "no". No que escriba variaciones como SI, Si, Sí,....
                confirmacion = sock.recv(1024).decode().strip().lower()

                if confirmacion == "si": # => actualizamos el estado de la compra a "recibido"
                    #Actualizar estado de la compra
                    compra["estado"] = "envío confirmado" #cambiamos el estado de la compra a "envío confirmado"
                    compra["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") #actualizamos la fecha de la compra a la fecha actual

                    #Guardar cambios en el archivo JSON
                    f.seek(0)
                    json.dump(data, f, indent=4)
                    f.truncate()
                    sock.send(f"Confirmación exitosa!. Has confirmado la recepción de {carta}.\n".encode())

                else:
                    sock.send("Confirmación cancelada.\n".encode())
                    print(f"[DEBUG] Confirmación cancelada por el cliente: {carta}")
        
    except ValueError:
        sock.send("Error: Ingrese un número válido.\n".encode())
    except IndexError:
        sock.send("Error: Selección inválida.\n".encode())
    except Exception as e:
        print(f"[ERROR] confirmar_envio: {e}")
        sock.send("Error al procesar la confirmación.\n".encode())

def contactar_ejecutivo(sock, email, nombre):
    """
    El cliente se pone en la cola de espera para un ejecutivo.
    """
    print(f"[INFO] Cliente {nombre} solicitó hablar con un ejecutivo")

    with mutex:
        # Verificar si ya estaba en espera
        for _, e in STATE["clientes_espera"]:
            if e == email:
                sock.send("Ya estabas en la cola de espera. Por favor aguarda.\n".encode())
                print(f"[INFO] Cliente {nombre} ya estaba en la cola de espera")
                return

        # Agregar cliente a la lista de espera
        STATE["clientes_espera"].append((sock, email))
        print(f"[INFO] Cliente {nombre} añadido a la cola de espera")

        # ─── NUEVO: Avisar a todos los ejecutivos conectados ───
        for s_ejec in STATE["ejecutivos_linea"].values():
            try:
                s_ejec.send(f"El cliente {nombre} ({email}) se quiere conectar\n".encode())
            except (BrokenPipeError, OSError):
                pass

    # Confirmación al cliente
    sock.send(
        "Has sido añadido a la cola de espera. "
        "Un ejecutivo te contactará pronto…\n".encode()
    )

def chat_con_ejecutivo(sock):
    """
    Función que maneja el chat en vivo con el ejecutivo.
    """
    try:
        while True:
            mensaje = sock.recv(1024).decode()
            if not mensaje:
                break
            print(mensaje, end="")  # Mostrar mensaje recibido sin doble salto
    except Exception as e:
        print(f"[ERROR] chat_con_ejecutivo: {e}")
    finally:
        print("[Conexión finalizada con el ejecutivo]")


    



