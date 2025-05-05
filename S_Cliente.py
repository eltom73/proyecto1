import socket
import threading
import sys

HOST = '127.0.0.1'
PORT = 5000

def recibir(sock):
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            print(data.decode(), end='', flush=True)
        except:
            break

def main():
    s = socket.socket()
    s.connect((HOST, PORT))
    # rol
    s.send("cliente\n".encode())

    # manejo de mensajes del servidor
    threading.Thread(target=recibir, args=(s,), daemon=True).start()

    # interacción usuario
    while True:
        linea = sys.stdin.readline()
        if not linea: break
        s.send(linea.encode())
        if linea.strip().lower() == 'salir':
            break

    s.close()

if __name__ == '__main__':
    main()