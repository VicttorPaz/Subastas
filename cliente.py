import sys, threading, time, re, termios, tty, select
import Pyro4

# Dirección del servidor donde corre el Name Server
IP_SERVIDOR = "127.0.0.1"
# Bandera que mantiene vivo el programa y el hilo que consulta al servidor
activo = True
# Copia local del estado de la subasta, se actualiza cada segundo
estado_actual = {}
# Lock para que los hilos no escriban en pantalla ni en estado_actual al mismo tiempo
lock_pantalla = threading.Lock()
# Evento que avisa al input que la subasta terminó
evento_fin_subasta = threading.Event()

def escuchar_servidor(subasta):
    """Hilo que consulta al servidor cada segundo y mantiene actualizado estado_actual.

    Avisa por pantalla cuando alguien más sube el precio y activa el evento de fin
    cuando la subasta pasa de activa a finalizada.
    """
    global estado_actual
    # anterior guarda si la subasta estaba activa; ultimo guarda el último precio visto
    anterior, ultimo = True, -1
    while activo:
        try:
            nuevo = subasta.obtener_estado()
            with lock_pantalla:
                estado_actual = nuevo
                # Si el precio subió desde la última consulta, se avisa al usuario
                if ultimo != -1 and nuevo['precio_actual'] > ultimo:
                    # Borra la línea del prompt antes de imprimir el aviso
                    sys.stdout.write("\r" + " " * 80 + "\r")
                    print(f"\n[AVISO] Nueva oferta maxima: ${nuevo['precio_actual']:.2f} (Lider: {nuevo['lider']})")
                ultimo = nuevo['precio_actual']
                # Si la subasta acaba de terminar, se despierta al input
                if anterior and not nuevo['activa']: evento_fin_subasta.set()
                anterior = nuevo['activa']
        except Exception: pass
        time.sleep(1)

def limpiar_monto_seguro(texto):
    """Extrae un número decimal del texto escrito por el usuario.

    Quita los espacios, cambia las comas por puntos y devuelve el último número
    encontrado. Lanza ValueError si no hay ninguno.
    """
    c = re.findall(r'\b\d+(?:\.\d+)?\b', texto.replace(" ", "").replace(',', '.'))
    if not c: raise ValueError("No se encontró un número válido")
    return float(c[-1])

def input_con_temporizador_linux():
    """Lee lo que escribe el usuario letra por letra mientras redibuja el temporizador.

    Usa el modo cbreak de la terminal de Linux para no esperar el Enter y así poder
    refrescar el tiempo restante y el precio sin bloquearse. Devuelve el texto
    escrito, o sale antes si la subasta termina.
    """
    buffer, fd = [], sys.stdin.fileno()
    # Guarda la configuración original de la terminal para restaurarla al final
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ultimo = time.time()
        while not evento_fin_subasta.is_set():
            ahora = time.time()
            # Cada segundo descuenta uno al tiempo restante local
            if ahora - ultimo >= 1.0:
                with lock_pantalla:
                    if estado_actual.get('tiempo_restante', 0) > 0: estado_actual['tiempo_restante'] -= 1
                ultimo = ahora
            with lock_pantalla:
                t, p = estado_actual.get('tiempo_restante', 0), estado_actual.get('precio_actual', 0.0)
            # Redibuja la línea con el tiempo, el precio y lo que lleva escrito el usuario
            sys.stdout.write(f"\r[Tiempo Restante: {max(0, t // 60):02d}:{max(0, t % 60):02d} | Actual: ${p:.2f}] Pujar > " + "".join(buffer))
            sys.stdout.flush()
            # Espera 50 ms por una tecla; si no hay, vuelve a refrescar la pantalla
            if select.select([sys.stdin], [], [], 0.05)[0]:
                c = sys.stdin.read(1)
                # Enter: termina la lectura
                if c in ('\n', '\r'):
                    print(flush=True)
                    break
                # Retroceso: borra el último carácter
                elif ord(c) in (127, 8):
                    if buffer:
                        buffer.pop()
                        sys.stdout.write("\b \b")
                # Ctrl+C: se relanza para que lo maneje el bucle principal
                elif c == '\x03': raise KeyboardInterrupt
                else: buffer.append(c)
    finally:
        # Siempre se restaura la terminal, aunque haya un error
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return "".join(buffer)

# Le indica a Pyro4 dónde está el Name Server
Pyro4.config.NS_HOST = IP_SERVIDOR
try:
    # Proxy remoto: busca "subastas.central" en el Name Server y se comporta como el objeto del servidor
    subasta = Pyro4.Proxy("PYRONAME:subastas.central")
    nombre = input("Ingrese su nombre de usuario: ").strip()
    # Arranca el hilo que sincroniza el estado con el servidor
    threading.Thread(target=escuchar_servidor, args=(subasta,), daemon=True).start()
    # Bucle externo: una vuelta por cada producto del catálogo
    while activo:
        inicial = subasta.obtener_estado()
        with lock_pantalla:
            estado_actual = inicial
            evento_fin_subasta.clear()
        # Pantalla de presentación del producto
        print(f"\n==================================================\n NUEVA SUBASTA INICIADA\n Producto: {inicial['item']}\n Precio Base: ${inicial['precio_actual']:.2f}\n Duracion maxima: {inicial['duracion_total'] // 60} minutos (Cierre automatico si pasan 1 min sin pujas)\n==================================================")
        print("Escriba el monto de su oferta (ej: 100.02) y presione Enter (o 'q' para salir):\n")
        # Bucle interno: el usuario puja mientras la subasta siga activa
        while activo and not evento_fin_subasta.is_set() and estado_actual.get('activa', True):
            try: entrada = input_con_temporizador_linux()
            except (KeyboardInterrupt, EOFError):
                activo = False
                break
            # Si la subasta terminó mientras escribía, se sale sin enviar la oferta
            if evento_fin_subasta.is_set() or not estado_actual.get('activa', True): break
            # 'q' cierra el programa
            if entrada.lower() == 'q':
                activo = False
                break
            # Una línea vacía se ignora
            if entrada.strip() == "": continue
            try:
                monto = limpiar_monto_seguro(entrada)
                # Envía la oferta al servidor e imprime su respuesta
                print(f"-> {subasta.realizar_oferta(nombre, monto)}")
                # Actualiza el estado local sin esperar la siguiente consulta
                with lock_pantalla:
                    estado_actual['precio_actual'], estado_actual['lider'] = monto, nombre
            except ValueError: print("Aviso: Formato no reconocido. Ingrese un numero valido con decimales (ej: 100.02).")
            except Exception as e: print(f"Error de comunicacion: {e}")
        if not activo: break
        # La subasta terminó: se pide al servidor quién ganó
        with lock_pantalla:
            try: ganador_info = subasta.obtener_estado().get('ganador_anterior')
            except: ganador_info = estado_actual.get('ganador_anterior')
            evento_fin_subasta.clear()
        print("\n" + "=" * 50 + "\n LA SUBASTA HA FINALIZADO ")
        # Muestra el ganador, o avisa que nadie pujó
        if ganador_info and ganador_info.get('ganador') and ganador_info.get('ganador') != "Nadie":
            print(f" Producto: {ganador_info['item']}\n Ganador: {ganador_info['ganador']} con ${ganador_info['precio']:.2f}")
        else: print(" No hubo ofertas para este producto.")
        print("=" * 50)
        # Consulta el nombre del siguiente producto para incluirlo en la pregunta
        try: siguiente = subasta.obtener_nombre_siguiente()
        except: siguiente = ""
        pregunta = f"\nDesea ingresar a la subasta del siguiente producto ({siguiente})? (s/n): " if siguiente else "\nDesea ingresar a la subasta del SIGUIENTE producto? (s/n): "
        if input(pregunta).strip().lower() == 's':
            try:
                # Si el servidor ya no tiene más productos, se termina el programa
                if not subasta.avanzar_siguiente_producto():
                    print("\nSe han completado todos los productos del catalogo. Gracias por participar!")
                    activo = False
                    break
                print("\nCargando nuevo producto...")
                time.sleep(1)
            except Exception as e: print(f"Error: {e}")
        else:
            print("\nSaliendo de la subasta. Gracias por participar!")
            activo = False
            break
# Si no se encuentra el Name Server, se avisa y se cierra
except Pyro4.errors.NamingError:
    print(f"Error: No se pudo conectar al Name Server en '{IP_SERVIDOR}'.")
# Ctrl+C fuera del input también cierra de forma ordenada
except KeyboardInterrupt:
    print("\nSaliendo de la subasta... Ruta interrumpida.")
    activo = False