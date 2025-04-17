import socket
import sys
import threading

def leer(sock):
    while True:
        try: #
            res = sock.recv(1024).decode()   #I ntenta recibir un mensaje del servidor.
        except: # en except se coloca lo que se hace si es que el try falla
            sock.close()
            break
        print(res)
        if res == 'No te cacho :/': break
    return None

# Se asume que el servidor esta corriendo localmente en el puerto 8889.
HOST = '127.0.0.1'
PORT = 8889

# Se crea el socket y se conecta al servidor.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
print("Conectado al servidor")

reading_thread = threading.Thread(target=leer, args=(s,))
reading_thread.start()

# Se revisa la entrada estandar y se envia lo que ingrese le usuarie.
for line in sys.stdin: #lee línea por línea lo que se escribe en consola
    msg = line.rstrip() #quita el salto de línea final (\n), dejando solo el texto.
    s.send(msg.encode()) #codifica el mensaje como bytes y lo envía al servidor.
    if msg == "::exit": #si el mensaje es ::exit
        res = s.recv(1024).decode() #Espera una última respuesta del servidor con recv().
        break #Luego rompe el bucle.
s.close() #finalmente se cierra el socket