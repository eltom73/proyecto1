import socket
import threading
import sys
#asd
HOST, PORT = "127.0.0.1", 8889

# Crear el socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

# Función para escuchar mensajes del servidor
def recibir_respuestas(sock): #función que corre en un hilo aparte. Lee y muestra todos los mensajes que el servidor envía.
    while True:
        try:
            mensaje = sock.recv(4096).decode() #mensaje contiene el texto que el servidor acaba de enviar.
            if not mensaje: #Si mensaje está vacío… significa que el servidor cerró el socket, pues recv(...) devuelve una cadena vacía ("").
                print("\n[Conexión cerrada por el servidor]") #Entonces esto detecta que el servidor cerró la conexión y el cliente debe terminar su bucle.
                break
            print(mensaje, end="", flush=True) #Si el mensaje sí existe, se muestra en pantalla
            

            if "Hasta luego" in mensaje or "Conexión cerrada" in mensaje: # Si ve alguna de esas frases, también termina el bucle y deja de escuchar.
                break
        except: #Esto captura cualquier error inesperado (por ejemplo, si el socket explota) 
            break

# Iniciar el hilo que escucha
reading_thread = threading.Thread(target=recibir_respuestas, args=(s,))
reading_thread.start()

# Enviar mensajes escritos por el usuario
try:
    for linea in sys.stdin:
        mensaje = linea.strip()
        s.send(mensaje.encode())
        if mensaje == "::exit":
            break
except Exception as e:
    print("Error en cliente:", e)
finally:
    s.close()
