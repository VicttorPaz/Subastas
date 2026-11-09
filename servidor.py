import threading
import time
import Pyro4

# @Pyro4.expose expone esta clase para que los clientes remotos puedan invocar sus métodos.
@Pyro4.expose
# @Pyro4.behavior(instance_mode="single") asegura que exista una única instancia compartida del servidor para todos los clientes conectados.
@Pyro4.behavior(instance_mode="single")
class SistemaSubasta:
    """Clase remota que guarda el estado de la subasta y lo comparte con todos los clientes.

    Maneja el catálogo de productos, el precio actual, el líder de la puja y los
    tiempos de cierre. Como varios clientes la usan a la vez, todo acceso al estado
    pasa por un Lock.
    """

    def __init__(self):
        """Prepara el Lock, el catálogo de productos y carga el primer producto."""
        # Se inicializa un Lock de hilos para garantizar exclusión mutua al modificar el estado compartido.
        self.lock = threading.Lock()
        # Catálogo estático de productos (Nombre, Precio Base)
        self.catalogo = [("Laptop Gaming RTX 4080", 500.0), ("Smartphone 5G Pro", 300.0), ("Consola de Videojuegos NextGen", 400.0)]
        self.indice = 0
        self.cargar_producto_actual()

    def cargar_producto_actual(self):
        """Carga los datos del producto actual según el índice en el catálogo."""
        # Toma el nombre y el precio base del producto que marca el índice
        self.item, self.precio_actual = self.catalogo[self.indice]
        self.duracion_segundos = 300
        # Reinicia el líder, el ganador anterior y la bandera de subasta finalizada
        self.lider_actual, self.ganador_anterior, self.subasta_finalizada = "Nadie", None, False
        self.ultima_actividad = time.time()
        # La subasta dura 5 minutos desde que se carga el producto
        self.tiempo_fin = self.ultima_actividad + 300

    def obtener_estado(self) -> dict:
        """Devuelve el estado actual de la subasta para que los clientes se sincronicen."""
        with self.lock:
            t = time.time()
            restante = int(self.tiempo_fin - t)
            # Evalúa si pasó 1 minuto sin pujas y ya hay un líder
            inactivo = t - self.ultima_actividad >= 60 and self.lider_actual != "Nadie"
            
            # Si el tiempo se agotó o hubo inactividad y la subasta sigue activa, se finaliza.
            if (restante <= 0 or inactivo) and not self.subasta_finalizada:
                self.subasta_finalizada, restante = True, 0
                # Guarda los datos del ganador para mostrarlos a los clientes
                self.ganador_anterior = {"item": self.item, "ganador": self.lider_actual, "precio": self.precio_actual}
                print(f"\n[SUBASTA FINALIZADA] '{self.item}' {'por inactividad (1 min sin pujas)' if inactivo else 'por tiempo limite'}. Adjudicado a: {self.lider_actual} por ${self.precio_actual:.2f}")
            
            # Diccionario con todo lo que el cliente necesita para dibujar la pantalla
            return {
                "item": self.item, 
                "precio_actual": self.precio_actual, 
                "lider": self.lider_actual, 
                "tiempo_restante": max(0, restante),
                "duracion_total": self.duracion_segundos, 
                "activa": not self.subasta_finalizada, 
                "ganador_anterior": self.ganador_anterior
            }

    def obtener_nombre_siguiente(self) -> str:
        """Retorna el nombre del próximo producto en el catálogo (si existe)."""
        with self.lock:
            # Si ya no quedan productos devuelve una cadena vacía
            return self.catalogo[self.indice + 1][0] if self.indice + 1 < len(self.catalogo) else ""

    def avanzar_siguiente_producto(self) -> bool:
        """Avanza al siguiente índice del catálogo y carga sus propiedades."""
        with self.lock:
            # Devuelve False si ya se subastó el último producto
            if self.indice + 1 >= len(self.catalogo): return False
            self.indice += 1
            self.cargar_producto_actual()
            return True

    def realizar_oferta(self, postor: str, monto: float) -> str:
        """Valida e inscribe una nueva oferta realizada por un cliente."""
        with self.lock:
            # No se acepta ninguna oferta si la subasta ya terminó
            if time.time() > self.tiempo_fin or self.subasta_finalizada:
                raise ValueError("La subasta de este producto ya ha finalizado.")
            # La oferta tiene que superar el precio actual
            if monto <= self.precio_actual:
                raise ValueError(f"Oferta rechazada (${monto:.2f}). Debe superar el precio actual de ${self.precio_actual:.2f}")
            
            # Actualiza el precio, el líder y reinicia el contador de inactividad
            self.precio_actual, self.lider_actual, self.ultima_actividad = monto, postor, time.time()
            print(f"\n[NUEVA OFERTA MAXIMA] {postor} ofreció ${monto:.2f}")
            return f"Felicidades {postor}! Tu oferta de ${monto:.2f} ha sido aceptada."

def iniciar_name_server(ip, puerto):
    """Inicia el servidor de nombres (Name Server) de Pyro4 en un hilo separado."""
    # Si el Name Server ya está corriendo en ese puerto, el error se ignora
    try: Pyro4.naming.startNSLoop(host=ip, port=puerto)
    except Exception: pass

# Dirección y puerto donde se publican el servidor y el Name Server
IP_SERVIDOR, PUERTO_NAMESERVER = "172.17.39.6", 9090
print("Iniciando Name Server en hilo independiente...")
# El hilo es daemon para que se cierre junto con el programa principal
threading.Thread(target=iniciar_name_server, args=(IP_SERVIDOR, PUERTO_NAMESERVER), daemon=True).start()
# Pausa de un segundo para darle tiempo al Name Server de arrancar
time.sleep(1)

try:
    # Se inicia el daemon de Pyro4 para escuchar solicitudes remotas
    daemon = Pyro4.Daemon(host=IP_SERVIDOR)
    # Se registra el objeto SistemaSubasta en el Name Server bajo el nombre lógico "subastas.central"
    Pyro4.locateNS(host=IP_SERVIDOR, port=PUERTO_NAMESERVER).register("subastas.central", daemon.register(SistemaSubasta))
    print(f"=== SERVIDOR DE SUBASTAS ACTIVO EN {IP_SERVIDOR} ===")
    # Deja el servidor atendiendo peticiones hasta que se detenga el programa
    daemon.requestLoop()
except Exception as e:
    print(f"Error al iniciar el servidor de objetos: {e}")