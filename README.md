# Sistema de subastas distribuido con Pyro4

Subasta por consola en la que varios clientes pujan en tiempo real por los productos de un catálogo. Un servidor Pyro4 guarda el estado de la subasta y cada cliente lo consulta y le envía sus ofertas mediante llamadas a métodos remotos.

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python&logoColor=white)
![Pyro4](https://img.shields.io/badge/Pyro4-objetos%20remotos-informational?style=for-the-badge)
![Name Server](https://img.shields.io/badge/Pyro4-Name%20Server%20integrado-informational?style=for-the-badge)
![Instancia](https://img.shields.io/badge/instancia-%C3%BAnica%20(single)-informational?style=for-the-badge)
![Hilos](https://img.shields.io/badge/concurrencia-hilos%20con%20Lock-orange?style=for-the-badge)
![Terminal](https://img.shields.io/badge/terminal-Linux%20y%20macOS-orange?style=for-the-badge&logo=linux&logoColor=white)
![Arquitectura](https://img.shields.io/badge/arquitectura-cliente--servidor-green?style=for-the-badge)
![RPC](https://img.shields.io/badge/comunicaci%C3%B3n-llamadas%20remotas-green?style=for-the-badge)
![Interfaz](https://img.shields.io/badge/interfaz-consola-lightgrey?style=for-the-badge)


## Tabla de contenido

- [Descripción general](#descripción-general)
- [Características](#características)
- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Cómo funciona](#cómo-funciona)
- [Referencia de clases y funciones](#referencia-de-clases-y-funciones)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Capturas de pantalla](#capturas-de-pantalla)

## Descripción general

Este proyecto es una práctica de sistemas distribuidos que muestra cómo varios clientes comparten un mismo objeto remoto. El servidor define la clase `SistemaSubasta`, que lleva un catálogo de tres productos y subasta uno a la vez. Cada cliente se identifica con un nombre de usuario, ve el producto actual con su precio y el tiempo que queda, y escribe en la terminal el monto que quiere ofrecer.

Una subasta termina cuando se agotan los 5 minutos o cuando pasa 1 minuto sin nuevas ofertas y ya hay un líder. Al terminar, el cliente muestra al ganador y pregunta si se quiere pasar al siguiente producto. El servidor tiene una sola instancia de la subasta, compartida por todos los clientes, y protege su estado con un `Lock` porque Pyro4 atiende cada llamada en un hilo distinto.

El servidor también inicia su propio Name Server de Pyro4 en un hilo aparte y publica ahí el servicio como `subastas.central`. Por eso no hace falta abrir una terminal extra con `python -m Pyro4.naming`.

## Características

- Catálogo de tres productos con su precio base: Laptop Gaming RTX 4080 (500.0), Smartphone 5G Pro (300.0) y Consola de Videojuegos NextGen (400.0).
- Una sola instancia de la subasta en el servidor, compartida por todos los clientes conectados.
- Cada oferta debe superar el precio actual. El servidor la rechaza si no lo hace o si la subasta ya terminó.
- Cierre automático a los 300 segundos, o a los 60 segundos sin pujas cuando ya existe un líder.
- El cliente consulta el estado al servidor cada segundo y avisa cuando otro usuario sube la oferta máxima.
- El prompt del cliente se redibuja en la misma línea y muestra el tiempo restante y el precio actual, mientras la persona escribe.
- El cliente acepta montos escritos con coma o punto decimal y toma el último número de la entrada, así que `150,50`, `$ 150.50` o `ofrezco 150.50` se interpretan igual.
- Un `threading.Lock` en el servidor evita que dos ofertas simultáneas se pisen al modificar el estado.
- Al terminar cada producto, el cliente pregunta si se quiere continuar con el siguiente.

## Requisitos previos

- Python 3
- pip
- Pyro4
- Una terminal de Linux o macOS para el cliente. Usa los módulos `termios`, `tty` y `select`, que no existen en Windows. En Windows puede usarse WSL.

Solo Pyro4 se instala con pip. El resto de los módulos (`threading`, `time`, `re`, `termios`, `tty`, `select`, `sys`) vienen con Python.

## Instalación

Guarda `servidor.py` y `cliente.py` en una misma carpeta y abre una terminal dentro de ella.

Instala Pyro4:

```bash
pip install Pyro4
```

Si prefieres aislar las dependencias en un entorno virtual:

```bash
python -m venv venv
source venv/bin/activate
pip install Pyro4
```

## Configuración

Antes de ejecutar, revisa estos valores en el código.

| Archivo | Variable | Valor en el código | Para qué sirve |
|---|---|---|---|
| `servidor.py` | `IP_SERVIDOR` | `"172.17.39.6"` | IP del equipo donde corre el servidor. Cámbiala por la tuya, por ejemplo con el resultado de `hostname -I` en Linux |
| `servidor.py` | `PUERTO_NAMESERVER` | `9090` | Puerto del Name Server integrado |
| `servidor.py` | `catalogo` | Tres productos con su precio base | Lista de tuplas `(nombre, precio base)` dentro de `SistemaSubasta.__init__` |
| `servidor.py` | `300` | Duración máxima en segundos | Aparece dos veces en `cargar_producto_actual`, en `duracion_segundos` y en `tiempo_fin`. Si lo cambias, cámbialo en ambos |
| `servidor.py` | `60` | Segundos sin pujas para cerrar | Está dentro de `obtener_estado`, en el cálculo de `inactivo` |
| `cliente.py` | `IP_SERVIDOR` | `"127.0.0.1"` | IP del servidor. Solo sirve tal cual si cliente y servidor están en el mismo equipo. Si no, pon la misma IP que usa el servidor |

Si el cliente corre en otro equipo, ese equipo debe poder llegar al servidor por la red. Revisa que el cortafuegos no bloquee el puerto 9090 ni el puerto que Pyro4 asigne al servidor de objetos.

## Uso

Se necesitan al menos dos terminales abiertas. El orden importa: primero el servidor y después los clientes.

### 1. Iniciar el servidor

```bash
python servidor.py
```

Salida esperada:

```text
Iniciando Name Server en hilo independiente...
=== SERVIDOR DE SUBASTAS ACTIVO EN 172.17.39.6 ===
```

Pyro4 puede imprimir sus propias líneas del Name Server entre esos dos mensajes. El servidor queda esperando peticiones y no debes cerrar esta terminal.

### 2. Ejecutar un cliente

```bash
python cliente.py
```

El cliente pide un nombre de usuario y empieza la subasta del primer producto:

```text
Ingrese su nombre de usuario: Ana

==================================================
 NUEVA SUBASTA INICIADA
 Producto: Laptop Gaming RTX 4080
 Precio Base: $500.00
 Duracion maxima: 5 minutos (Cierre automatico si pasan 1 min sin pujas)
==================================================
Escriba el monto de su oferta (ej: 100.02) y presione Enter (o 'q' para salir):

[Tiempo Restante: 04:41 | Actual: $500.00] Pujar > 520
-> Felicidades Ana! Tu oferta de $520.00 ha sido aceptada.
```

La línea del prompt se actualiza sola cada segundo, así que en pantalla solo se ve la última versión.

Para probar con varios usuarios, abre otra terminal y ejecuta `python cliente.py` con otro nombre. El segundo cliente ve un aviso cada vez que alguien sube la oferta:

```text
[AVISO] Nueva oferta maxima: $520.00 (Lider: Ana)
[Tiempo Restante: 04:12 | Actual: $520.00] Pujar > 
```

### 3. Final de una subasta

Cuando se cumple el tiempo o la inactividad, el cliente muestra el resultado y pregunta por el siguiente producto:

```text
==================================================
 LA SUBASTA HA FINALIZADO 
 Producto: Laptop Gaming RTX 4080
 Ganador: Ana con $520.00
==================================================

Desea ingresar a la subasta del siguiente producto (Smartphone 5G Pro)? (s/n): s

Cargando nuevo producto...
```

Si nadie hizo ofertas, el cliente muestra `No hubo ofertas para este producto.` en lugar del ganador.

Con `n` el cliente se despide y termina. Después del último producto, aunque se responda `s`, aparece `Se han completado todos los productos del catalogo. Gracias por participar!` y el programa termina.

Lo que se ve al mismo tiempo en la terminal del servidor:

```text
[NUEVA OFERTA MAXIMA] Ana ofreció $520.00
[SUBASTA FINALIZADA] 'Laptop Gaming RTX 4080' por inactividad (1 min sin pujas). Adjudicado a: Ana por $520.00
```

Si la subasta se cierra por el tiempo máximo, el mensaje dice `por tiempo limite` en lugar de `por inactividad (1 min sin pujas)`.

### Ejemplo de oferta rechazada

```text
[Tiempo Restante: 03:20 | Actual: $520.00] Pujar > 400
Aviso: Formato no reconocido. Ingrese un numero valido con decimales (ej: 100.02).
```

El servidor rechaza la oferta porque no supera $520.00, pero el cliente atrapa ese error con el mismo `except ValueError` que usa para los formatos inválidos, y por eso muestra este mensaje. Más detalles en [Limitaciones conocidas](#limitaciones-conocidas).

### Salir

Se sale escribiendo `q` y Enter, o con Ctrl+C. El cliente restaura la configuración de la terminal antes de cerrar.

### Errores comunes

| Mensaje | Causa probable | Solución |
|---|---|---|
| `Error: No se pudo conectar al Name Server en '127.0.0.1'.` | El servidor no está corriendo, o `IP_SERVIDOR` del cliente no es la IP del servidor | Inicia `servidor.py` y pon la IP correcta en `cliente.py` |
| `Error al iniciar el servidor de objetos: ...` | La IP de `IP_SERVIDOR` en `servidor.py` no pertenece a este equipo | Cambia la IP por la de tu equipo |
| `ModuleNotFoundError: No module named 'termios'` | El cliente se ejecutó en Windows | Usa Linux, macOS o WSL |
| `ModuleNotFoundError: No module named 'Pyro4'` | Pyro4 no está instalado | Ejecuta `pip install Pyro4` |
| El prompt no se actualiza o se ve desordenado | La terminal no es una terminal real, por ejemplo la consola de algunos editores | Ejecuta el cliente desde una terminal normal |


## Cómo funciona

El proyecto usa Pyro4 (Python Remote Objects), una biblioteca que permite llamar métodos de un objeto que vive en otro proceso, o incluso en otro equipo, como si fuera local. Hay tres piezas:

1. Name Server. Es un directorio que relaciona nombres con direcciones de objetos remotos. Aquí lo inicia el propio `servidor.py` en un hilo con `Pyro4.naming.startNSLoop`, en la IP y el puerto configurados. Si el arranque falla, por ejemplo porque ya hay un Name Server en ese puerto, el error se ignora y el servidor intenta usar el que esté disponible.
2. Servidor (`servidor.py`). Define la clase `SistemaSubasta`, marcada con `@Pyro4.expose` para que sus métodos se puedan llamar desde fuera y con `@Pyro4.behavior(instance_mode="single")` para que Pyro4 cree una única instancia compartida por todos los clientes. Después de la clase, el script lanza el Name Server, espera un segundo, crea un `Pyro4.Daemon` en la IP configurada, registra la clase, publica la URI con el nombre `subastas.central` y deja el proceso atendiendo llamadas con `daemon.requestLoop()`.
3. Cliente (`cliente.py`). Fija `Pyro4.config.NS_HOST` con la IP del servidor y crea un `Pyro4.Proxy("PYRONAME:subastas.central")`. Pide el nombre de usuario, arranca un hilo que consulta el estado cada segundo y entra en un ciclo que lee las ofertas de la persona y las envía al servidor.

Reglas de la subasta:

| Regla | Valor |
|---|---|
| Duración máxima por producto | 300 segundos (5 minutos) |
| Cierre por inactividad | 60 segundos sin pujas, solo si ya hay un líder |
| Oferta válida | Mayor al precio actual y con la subasta todavía activa |
| Líder inicial | `"Nadie"`, hasta que llega la primera oferta |
| Productos | Se subastan en el orden del catálogo, uno a la vez |

La subasta no termina sola en el servidor, sino cuando alguien consulta su estado. `obtener_estado` calcula el tiempo restante y la inactividad cada vez que se llama, y si se cumple alguna condición marca la subasta como finalizada y guarda el resultado. Como cada cliente la consulta una vez por segundo, el cierre ocurre prácticamente a tiempo mientras haya algún cliente conectado.

Flujo de una oferta:

```text
cliente.py  ->  Name Server: "¿dónde está subastas.central?"
Name Server ->  cliente.py:  URI del objeto en el servidor
cliente.py  ->  servidor.py: obtener_estado()          (cada segundo, en un hilo)
servidor.py ->  cliente.py:  diccionario con el estado actual
cliente.py  ->  servidor.py: realizar_oferta("Ana", 520.0)
servidor.py ->  cliente.py:  "Felicidades Ana! Tu oferta de $520.00 ha sido aceptada."
```

Hilos en el cliente: el hilo principal lee el teclado y el hilo `escuchar_servidor` consulta el estado. Los dos comparten la variable `estado_actual`, que se protege con `lock_pantalla`, y se avisan del fin de la subasta con el evento `evento_fin_subasta`. Entre consultas, el cliente descuenta un segundo por su cuenta al tiempo restante para que el contador se mueva con fluidez, y lo corrige con el valor real del servidor en cada consulta.

## Referencia de clases y funciones

### Servidor: clase `SistemaSubasta`

Es la única clase del proyecto. Su constructor crea el `Lock`, el catálogo y el índice del producto actual, y carga el primer producto.

| Método | Qué hace | Devuelve | Errores |
|---|---|---|---|
| `__init__()` | Crea el `Lock`, el catálogo de productos y el índice en 0, y llama a `cargar_producto_actual` | Nada | Ninguno |
| `cargar_producto_actual()` | Toma del catálogo el producto del índice actual. Fija su nombre y precio base, la duración en 300 segundos, el líder en `"Nadie"`, borra el ganador anterior, marca la subasta como activa y calcula la hora de cierre | Nada | Ninguno |
| `obtener_estado()` | Calcula el tiempo restante y la inactividad. Si se cumple alguna condición de cierre y la subasta sigue activa, la finaliza, guarda el resultado en `ganador_anterior` e imprime el aviso en el servidor | Diccionario con el estado | Ninguno |
| `obtener_nombre_siguiente()` | Consulta el nombre del próximo producto del catálogo | Texto con el nombre, o `""` si no quedan más | Ninguno |
| `avanzar_siguiente_producto()` | Sube el índice del catálogo y carga el nuevo producto | `True` si avanzó, `False` si ya era el último | Ninguno |
| `realizar_oferta(postor, monto)` | Valida la oferta y, si es correcta, actualiza precio, líder y hora de la última actividad. Imprime el aviso en el servidor | Texto de confirmación | `ValueError` si la subasta terminó o si el monto no supera el precio actual |

Todos los métodos, salvo `__init__` y `cargar_producto_actual`, toman el `Lock` antes de leer o cambiar el estado. `cargar_producto_actual` no lo toma por sí mismo, pero solo se llama desde `__init__` y desde `avanzar_siguiente_producto`, que ya lo tienen.

Diccionario que devuelve `obtener_estado`:

| Clave | Contenido |
|---|---|
| `item` | Nombre del producto en subasta |
| `precio_actual` | Precio base o la mejor oferta hasta el momento |
| `lider` | Nombre de quien lleva la mejor oferta, o `"Nadie"` |
| `tiempo_restante` | Segundos que quedan, nunca menor a 0 |
| `duracion_total` | Duración máxima del producto en segundos |
| `activa` | `True` mientras se acepten ofertas |
| `ganador_anterior` | Diccionario con `item`, `ganador` y `precio` cuando la subasta ya terminó, o `None` |

### Servidor: función `iniciar_name_server(ip, puerto)`

Arranca el Name Server de Pyro4 con `Pyro4.naming.startNSLoop`. Se ejecuta en un hilo `daemon`, que se cierra solo cuando termina el programa. Si falla, la excepción se descarta sin mostrar nada.

### Cliente: funciones

| Función | Qué hace | Devuelve |
|---|---|---|
| `escuchar_servidor(subasta)` | Corre en un hilo. Cada segundo llama a `obtener_estado`, actualiza `estado_actual`, avisa con `[AVISO]` si el precio subió y activa `evento_fin_subasta` cuando la subasta pasa de activa a terminada. Si una consulta falla, la ignora y sigue | Nada |
| `limpiar_monto_seguro(texto)` | Quita espacios, cambia las comas por puntos y busca números con una expresión regular. Toma el último que encuentre | `float` con el monto. Lanza `ValueError` si no encuentra ningún número |
| `input_con_temporizador_linux()` | Pone la terminal en modo `cbreak` y lee el teclado carácter por carácter. Mientras tanto redibuja el prompt con el tiempo restante y el precio actual. Admite Enter, retroceso y Ctrl+C, y restaura la terminal al terminar | Texto que escribió la persona |

### Cliente: variables globales

| Variable | Para qué sirve |
|---|---|
| `IP_SERVIDOR` | IP del servidor, usada para localizar el Name Server |
| `activo` | Indica que el programa debe seguir funcionando. Pasa a `False` al salir |
| `estado_actual` | Última copia del estado de la subasta que recibió el cliente |
| `lock_pantalla` | Candado que protege `estado_actual` y la escritura en pantalla |
| `evento_fin_subasta` | Evento que avisa al ciclo principal que la subasta actual terminó |

### Cliente: ciclo principal

El resto de `cliente.py` es un script sin funciones. Primero crea el proxy y pide el nombre de usuario. Después, en un ciclo externo, muestra el encabezado de cada subasta y, en un ciclo interno, lee ofertas hasta que la subasta termina o la persona escribe `q`. Al salir del ciclo interno muestra el ganador y pregunta si se pasa al siguiente producto, llamando a `obtener_nombre_siguiente` y `avanzar_siguiente_producto`.


## Capturas de pantalla



Servidor en ejecución:

<img width="886" height="226" alt="imagen" src="https://github.com/user-attachments/assets/22d3c6db-6d5a-4518-a36f-64e3db236ea4" />



Cliente con el prompt de tiempo y precio:

<img width="567" height="273" alt="imagen" src="https://github.com/user-attachments/assets/70491793-7ce8-4f45-bf71-7faaece533d5" />



Pantalla de fin de subasta y pregunta por el siguiente producto:

<img width="567" height="91" alt="imagen" src="https://github.com/user-attachments/assets/9ee7d90e-5d3c-4c38-9ced-fb7523c8e2e3" />
