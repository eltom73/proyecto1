import threading

FILEPATH = "database_clientes.json"
mutex = threading.Lock()

STATE = {
    "clientes_linea":   {},
    "ejecutivos_linea": {},
    "clientes_espera":  [],
    "conexiones":       {}
}
