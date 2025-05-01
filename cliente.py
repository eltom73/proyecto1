import socket
import threading
import sys

def recibir_respuestas(sock):
    """
    Función que corre en un hilo aparte. 
    Lee y muestra todos los mensajes que el servidor envía.
    """
    while True:
        try:
            mensaje = sock.recv(4096).decode('utf-8')
            if not mensaje:
                print("\n[Conexión cerrada por el servidor]")
                sock.close()
                sys.exit(0)
                
            print(mensaje, end="", flush=True)
            
            # Condiciones para terminar la conexión
            if "Hasta luego" in mensaje or "Conexión cerrada" in mensaje:
                sock.close()
                sys.exit(0)
                
        except ConnectionResetError:
            print("\n[Error: El servidor cerró la conexión abruptamente]")
            sock.close()
            sys.exit(1)
        except Exception as e:
            print(f"\n[Error inesperado: {str(e)}]")
            sock.close()
            sys.exit(1)

def main():
    HOST = '127.0.0.1'
    PORT = 8889
    
    try:
        # Crear socket y conectar al servidor
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        sock.send("CLIENTE".encode())

        
        # Iniciar hilo para recibir respuestas
        threading.Thread(target=recibir_respuestas, args=(sock,), daemon=True).start()
        
        # Bucle principal para enviar mensajes
        while True:
            mensaje = input()
            
            # Comandos especiales del cliente
            if mensaje.lower() == '/salir':
                sock.send(mensaje.encode('utf-8'))
                sock.close()
                break
                
            # Enviar mensaje normal al servidor
            try:
                sock.send(mensaje.encode('utf-8'))
            except BrokenPipeError:
                print("[Error: No se pudo enviar el mensaje - conexión cerrada]")
                sock.close()
                break
                
    except ConnectionRefusedError:
        print("[Error: No se pudo conectar al servidor]")
    except KeyboardInterrupt:
        print("\n[Cliente terminado por el usuario]")
        sock.close()
    except Exception as e:
        print(f"[Error inesperado: {str(e)}]")
        sock.close()

if __name__ == "__main__":
    main()