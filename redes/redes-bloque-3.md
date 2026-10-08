# Redes · Bloque 3 — HTTP

Métodos, códigos de estado, cabeceras, cookies, conexiones persistentes y HTTP/1.1 frente a HTTP/2. Todo observado con `curl -v`.

**Entorno de referencia:** VPS `backend-lab` (Ubuntu 24.04, `curl` 8.5.0, Python 3.12.3, shell fish) y portátil con CachyOS (`curl` 8.22.0). Las opciones y los mensajes de `curl` cambian entre versiones: confírmalos con `man curl` en la máquina donde vayas a ejecutar el comando.

---

# Parte 1 · Teoría

## 1. Dónde está HTTP: la llamada y la conversación

HTTP es un protocolo de **aplicación**. No transporta nada por sí mismo: viaja por una conexión **TCP** que tiene que estar abierta antes de enviar la primera línea.

| | TCP | HTTP |
|---|---|---|
| Papel | La llamada: conectar, que todo llegue completo y en orden, colgar | La conversación: qué se pide y qué se responde |
| Qué sabe | IPs, puertos, orden de los bytes, qué paquete se perdió | Método, ruta, `Host`, códigos, cabeceras, cookies, *streams* |
| Qué no sabe | Qué significan los bytes que transporta | Cómo llegan los bytes; da por hecho que la conexión funciona |

**Regla práctica con `curl -v`:** lo que aparece en una línea `>` o `<` es HTTP. Las líneas `*` de conexión (`Trying`, `Connected to`, `Established connection`, `Closing connection`) son TCP.

**Encapsulación completa** de una petición HTTPS con HTTP/2 desde el portátil:

```
trama Wi-Fi: «del portátil al router»                       ← enlace
 └─ datagrama IP: «de 192.168.17.250 a 84.17.59.115»         ← red
     └─ segmento TCP: «del puerto 42678 al 443»              ← transporte
         └─ TLS: cifrado                                     ← (Bloque 4)
             └─ trama HTTP/2 [stream 3]: HEAD /foro, Host…   ← aplicación
```

Cada aparato abre solo los sobres que necesita: el router doméstico llega hasta IP y los puertos (NAT); los routers de internet, hasta IP; el servidor los abre todos. Con HTTPS, la operadora ve IPs y puertos, pero no la petición; con HTTP sin cifrar lo ve todo y puede modificarlo.

**Mismo nombre, dos cosas:** la *trama* de la capa de enlace (Ethernet, Wi-Fi) y la *trama* de HTTP/2 (§9) son unidades distintas de capas distintas.

| Capa | Nombre de su unidad |
|---|---|
| Aplicación | Mensaje (y, en HTTP/2, tramas) |
| Transporte | Segmento |
| Red | Datagrama |
| Enlace | Trama |

**Sin estado (*stateless*).** El servidor no recuerda nada entre una petición y la siguiente. Las sesiones existen gracias a las cookies (§6).

## 2. Servidor web

«Servidor» significa dos cosas:

| Sentido | Qué es | Ejemplo |
|---|---|---|
| Máquina | El ordenador que aloja programas | El VPS `backend-lab` |
| Programa | Un proceso que escucha en un puerto y responde | `sshd`, `labweb`, PostgreSQL |

Un **servidor web** es un programa que habla HTTP: escucha en un puerto, recibe peticiones y devuelve respuestas. `labweb` (hecho con `http.server` de Python) ya lo es. **nginx** y **Apache** son servidores web de propósito general: sirven ficheros y, sobre todo, se ponen delante de otras aplicaciones como *reverse proxy*. Odoo trae su propio servidor web, pero en producción se le pone nginx delante.

## 3. El mensaje HTTP

Petición y respuesta tienen la misma estructura:

| Parte | Petición | Respuesta |
|---|---|---|
| Primera línea | **Línea de petición:** método, ruta y versión (`GET /health HTTP/1.1`) | **Línea de estado:** versión, código y frase (`HTTP/1.0 200 OK`) |
| Cabeceras | Una por línea, `Nombre: valor` | Igual |
| Línea vacía | Marca el fin de las cabeceras | Igual |
| Cuerpo | Opcional; un `GET` normalmente no lleva | El contenido (HTML, `ok`…); puede no existir |

La línea vacía es un salto de línea solo (`\r\n`). `curl -v` le pone el prefijo `>` o `<`, pero está vacía.

**Partes de una URL:**

```
https://www.odoo.com/web/login
└─┬──┘  └────┬─────┘└───┬────┘
protocolo  nombre     ruta
             │          └─ va en la línea de petición (GET /web/login)
             └─ va en la cabecera Host
```

Sin ruta en la URL, `curl` pide `/`. Sin protocolo, usa `http://`.

**Versiones en la primera línea.** Cada lado anuncia la suya: `curl` pide con `HTTP/1.1` y `labweb` contesta con `HTTP/1.0`. El servidor responde con la versión que habla, aunque el cliente pida otra más nueva.

**HTTP/0.9** (1991) no tenía línea de estado ni cabeceras: la respuesta era directamente el cuerpo. `curl` rechaza hoy esas respuestas (`Received HTTP/0.9 when not allowed`) salvo con `--http0.9`. Recibir una es señal de que algo en medio manipula la respuesta.

## 4. Métodos

| Método | Qué pide | Cuerpo en la petición |
|---|---|---|
| `GET` | Obtener un recurso, sin cambiar nada | No |
| `HEAD` | Igual que `GET`, pero la respuesta no trae cuerpo | No |
| `POST` | Enviar datos para que el servidor haga algo (formulario, login) | Sí |
| `PUT` | Sustituir un recurso | Sí |
| `DELETE` | Borrar un recurso | Normalmente no |

Un servidor solo atiende los métodos para los que tiene código. En `http.server` de Python, cada método necesita un método `do_GET`, `do_HEAD`, `do_POST`…; si falta, responde `501 Unsupported method`.

**Métodos frente a opciones de `curl`.** El método viaja al servidor (es la primera palabra de la línea `>`). Las opciones (`-v`, `-f`, `-I`, `-X`) son instrucciones para el programa `curl` y nunca salen de tu máquina. Algunas opciones deciden el método: `-I` envía `HEAD` y `-X POST` envía `POST`.

## 5. Códigos de estado

| Familia | Significado | ¿De quién es el problema? | Vistos en el bloque |
|---|---|---|---|
| `1xx` | Información provisional | — | — |
| `2xx` | Éxito | De nadie | `200` |
| `3xx` | Redirección: «está en otro sitio» (cabecera `Location`) | De nadie | `301`, `302` |
| `4xx` | Error del cliente | Del que pide | `403`, `451` |
| `5xx` | Error del servidor | Del que responde | `501` |

| Código | Significado |
|---|---|
| `200 OK` | Petición atendida |
| `301 Moved Permanently` | El recurso está definitivamente en la URL de `Location` |
| `302 Found` | Redirección temporal |
| `403 Forbidden` | El servidor entiende la petición pero se niega a atenderla |
| `451 Unavailable For Legal Reasons` | Bloqueado por motivos legales (RFC 7725) |
| `501 Not Implemented` | El servidor no sabe atender ese método |

**El código lo decide el programa.** HTTP no genera un `404` solo: hace falta que el código del servidor compruebe la ruta y decida que no existe. `labweb` responde `200` a cualquier ruta que no sea `/health`.

**Un código HTTP prueba que alguien contestó.** Para recibirlo hubo DNS, conexión TCP y un programa respondiendo. Otra cosa es que ese programa sea el servidor real (§ ejemplos, pixeldrain).

## 6. Cabeceras

| Cabecera | Va en | Para qué |
|---|---|---|
| `Host` | Petición | Nombre del sitio que se pide; obligatoria en HTTP/1.1 |
| `User-Agent` | Petición | Programa que pide (`curl/8.22.0`, un navegador…) |
| `Accept` | Petición | Tipos de contenido aceptados (`*/*` = cualquiera) |
| `Cookie` | Petición | Cookies guardadas, de vuelta al servidor |
| `Server` | Respuesta | Programa que responde (`BaseHTTP/0.6 Python/3.12.3`, `nginx`…) |
| `Date` | Respuesta | Momento de la respuesta |
| `Content-Type` | Respuesta (o petición con cuerpo) | Tipo del cuerpo (`text/html`) |
| `Content-Length` | Respuesta (o petición con cuerpo) | Tamaño del cuerpo en bytes |
| `Connection` | Ambas | `keep-alive` o `close` tras la respuesta (§7) |
| `Location` | Respuesta `3xx` | Adónde redirigir |
| `Set-Cookie` | Respuesta | «Guarda este dato y devuélvemelo» |

### `Host` y el *virtual hosting*

Varios sitios pueden compartir IP y puerto (`80` o `443`). DNS ya terminó su trabajo (todos los nombres dan la misma IP) y TCP solo conoce IPs y puertos, así que el nombre tiene que viajar **dentro** de la petición: en `Host`. El programa que escucha la lee y decide qué sitio servir. En nginx lo hace la directiva `server_name` (Redes · Bloque 5).

| Alternativa | Por qué no sirve |
|---|---|
| NAT | Trabaja con IPs y puertos en el router doméstico, para conexiones salientes. El nombre no existe en esas capas, y el VPS no tiene NAT delante |
| Un puerto distinto por sitio | Obliga a escribirlo en la URL, los cortafuegos de empresa suelen permitir solo `80` y `443`, y no escala |

Con HTTPS, el nombre viaja además antes, en el *handshake* de TLS (SNI, Bloque 4); por eso, para probar un dominio contra una IP concreta por HTTPS, `-H "Host: …"` no basta y se usa `--resolve`.

## 7. Cookies y sesiones

Recorrido, con el `session_id` de Odoo:

| Paso | Mensaje | Qué pasa |
|---|---|---|
| 1 | Petición `GET /web/login` | Sin cookies |
| 2 | Respuesta con `Set-Cookie: session_id=…` | El **servidor** inventa el identificador, lo guarda y pide al cliente que lo guarde |
| 3 | — | El navegador lo guarda |
| 4 | Peticiones siguientes con `Cookie: session_id=…` | El navegador lo devuelve solo, a cada petición del sitio |
| 5 | Respuesta | El servidor busca el identificador y sabe de qué sesión se trata |

`Set-Cookie` va en la respuesta (servidor → cliente); `Cookie`, en las peticiones (cliente → servidor). El identificador lo crea siempre el servidor: solo él sabe qué significa.

**Atributos.** Lo que va detrás del `nombre=valor`, separado por `;`. Son instrucciones para el navegador y no se devuelven al servidor.

| Atributo | Qué indica al navegador |
|---|---|
| `Expires` | Fecha de caducidad |
| `Max-Age` | Segundos de vida; si aparece junto a `Expires`, manda `Max-Age` |
| `Path` | En qué rutas del sitio enviarla (`/` = en todas) |
| `Domain` | A qué dominios enviarla |
| `Secure` | Enviarla solo por HTTPS: nunca viaja sin cifrar |
| `HttpOnly` | No dejar que el JavaScript de la página la lea |

**Secuestro de sesión.** Quien presenta un `session_id` válido entra en la sesión sin contraseña: la cookie demuestra quién tiene el tique, no quién eres. La defensa es impedir el robo: `Secure` y TLS (que no viaje en claro), `HttpOnly` (que no la lea un script inyectado), caducidad corta y cerrar sesión (el servidor invalida el identificador).

## 8. Conexiones persistentes (keep-alive)

| | No persistente | Persistente |
|---|---|---|
| Conexiones | Una por petición | Una para varias peticiones |
| Coste | Un *handshake* de TCP (y de TLS con HTTPS) por petición | Solo el primero |
| Por defecto en | HTTP/1.0 | HTTP/1.1 y HTTP/2 |

Cada conexión nueva paga al menos un RTT de *handshake* antes de enviar la primera línea. Contra `127.0.0.1` no se nota; contra un servidor lejano, sí.

**Para mantener la conexión, el cliente tiene que saber dónde acaba cada cuerpo sin que se cierre:**

| Mecanismo | Cómo marca el final |
|---|---|
| Cerrar la conexión | El final del cuerpo es el cierre. Impide reutilizar |
| `Content-Length` | Indica cuántos bytes mide el cuerpo |
| `Transfer-Encoding: chunked` (HTTP/1.1) | El cuerpo va en trozos con su tamaño y un trozo vacío al final; para cuando no se sabe el tamaño de antemano |
| Tramas (HTTP/2) | Cada trama marca su longitud y el final de su *stream* |

**`Connection: keep-alive` es HTTP**, porque es una cabecera. HTTP **pide** que no se cierre; TCP **mantiene** la conexión abierta.

## 9. Los límites de HTTP/1.1

**Bloqueo en cabeza de cola** (*head-of-line blocking*). Por una conexión HTTP/1.1 las respuestas viajan enteras, sin ninguna etiqueta que diga a qué petición pertenecen, así que tienen que salir en el mismo orden que las peticiones. Si la primera tarda, las demás esperan aunque estén listas.

| Petición enviada | Tarda en prepararse | Llega con HTTP/1.1 | Llega con HTTP/2 |
|---|---|---|---|
| 1ª | 5 s | 5 s | 5 s |
| 2ª | 0,1 s | 5 s | 0,1 s |
| 3ª | 0,1 s | 5 s | 0,1 s |

**Parches de HTTP/1.1:**

- *Pipelining*: enviar varias peticiones sin esperar respuesta. No elimina el bloqueo (las respuestas siguen en orden) y en la práctica casi nadie lo usa.
- **Varias conexiones en paralelo**, unas seis por origen. Funciona, pero cada una paga su *handshake*.
- Trucos de rendimiento (*domain sharding*, concatenar ficheros, *sprites*, incrustar recursos) que HTTP/2 vuelve innecesarios.

## 10. HTTP/2

No cambia métodos, códigos ni cabeceras: cambia cómo viajan.

| Pieza | Qué es |
|---|---|
| Capa de tramas binarias | Los mensajes se trocean en tramas binarias, ya no en texto |
| Trama (*frame*) | Un trozo de un mensaje: `HEADERS` (cabeceras, incluido lo que era la primera línea) o `DATA` (cuerpo) |
| Cabecera de la trama | 9 bytes delante de cada trama: longitud, tipo, *flags* e **identificador de *stream*** |
| *Stream* | Una petición con su respuesta. En una conexión hay muchos; los abiertos por el cliente llevan números impares (`1`, `3`, `5`…) |
| Multiplexado | Tramas de varios *streams* intercaladas en la misma conexión; el receptor las separa por el identificador |
| Una conexión por origen | Ya no hacen falta seis |
| Compresión de cabeceras (HPACK) | Las cabeceras repetidas no se reenvían enteras |
| Pseudocabeceras | `:method`, `:scheme`, `:authority` (equivale a `Host`), `:path` |
| ALPN | Acuerdo dentro del *handshake* de TLS para hablar `h2` (detalle en el Bloque 4) |
| *Server push* | El servidor envía recursos sin que se pidan; los navegadores principales lo han retirado |

Señales en la salida de `curl`: cabeceras de respuesta en minúsculas, línea de estado sin frase (`HTTP/2 301`) y líneas `[HTTP/2] [1] …`, donde el número es el *stream*. Las líneas `>` de HTTP/2 son una traducción de `curl`: lo que viaja es binario.

```
1 conexión TCP
 ├─ stream 1 → HEAD /
 └─ stream 3 → HEAD /foro
```

**Lo que HTTP/2 no resuelve.** Todos los *streams* viajan por una sola conexión TCP, y TCP no sabe que existen: solo ve una fila de bytes que debe entregar completa y en orden. Si se pierde un paquete, TCP retiene todo lo que viene detrás, sea del *stream* que sea.

| Bloqueo en cabeza de cola | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| En HTTP (una respuesta lenta) | Sí | Resuelto | Resuelto |
| En TCP (un paquete perdido) | Sí | Sí | Resuelto |

**HTTP/3** sustituye TCP por **QUIC** (sobre UDP), que conoce los *streams* y solo retiene el afectado. El servidor anuncia que lo habla con la cabecera `alt-svc`, y el navegador cambia a partir de ahí. Fuera del roadmap de este año.

## 11. Código HTTP frente a código de salida

```
labweb ──(código HTTP: 501)──▶ curl ──(código de salida: 0 o 22)──▶ shell / systemd
```

| Número | Entre quiénes | Valores |
|---|---|---|
| Código HTTP | Servidor → `curl` | `200`, `501`… |
| Código de salida | `curl` → quien lo lanzó | `0` = terminó bien; otro número = fallo |

systemd no entiende HTTP: decide si un servicio ha fallado por el código de salida. Sin `-f`, `curl` sale con `0` ante cualquier respuesta HTTP, aunque sea un error. Con `-f`, ante un código `400` o superior sale con `22`. La regla de `-f` es fija; lo que depende del servidor es qué código envía. `-f` solo mira el número: un `200` con cuerpo `roto` lo da por bueno.

En bash el código de salida está en `$?`; en fish, en `$status`.

## 12. Analogías de referencia

| Concepto | Analogía |
|---|---|
| TCP y HTTP | La llamada de teléfono y la conversación: la línea transporta el sonido sin entender el idioma |
| Mensaje HTTP | Un sobre: cabeceras escritas por fuera, cuerpo dentro |
| Servidor (máquina y programa) | El local del restaurante y los camareros; cada uno atiende su mesa (puerto) |
| Código de estado | El sello del funcionario: aprobado, ve a otra ventanilla, el formulario está mal, se nos ha caído el sistema |
| `501` | Una ventanilla que recoge el formulario y lo devuelve sellado: «aquí no hacemos este trámite» |
| `-f` | Conectar el pitido del detector de humo |
| `Host` | El nombre del inquilino en un edificio con una sola dirección; el conserje (nginx) reparte por nombre |
| NAT frente a `Host` | El NAT sabe a qué edificio va el paquete, no a qué inquilino |
| Cookie | El tique del guardarropa: lo imprime la discoteca, tú solo lo guardas y lo enseñas |
| `Content-Length` | Un paquete etiquetado «contiene 166 páginas»: al llegar a 166, has terminado |
| Conexión no persistente | Colgar y volver a marcar para cada frase |
| Bloqueo en cabeza de cola | La caja del supermercado: si el primero paga con monedas, esperan todos |
| Seis conexiones | Abrir más cajas |
| Multiplexado | Una cinta compartida donde cada producto lleva el número de cliente |
| Bloqueo de TCP en HTTP/2 | Si la cinta se para, nadie avanza, lleve la etiqueta que lleve |
| Los *streams* dentro de TCP | Cajas etiquetadas en un camión: el conductor no lee las etiquetas |
| TLS | Meter la carta en una caja fuerte en lugar de en un sobre transparente |

---

# Parte 2 · Ejemplos

## Una petición completa a `labweb`, anotada

```
*   Trying 127.0.0.1:8080...                         ← TCP: conectando
* Connected to 127.0.0.1 (127.0.0.1) port 8080       ← TCP: conexión abierta
> GET /health HTTP/1.1                               ← línea de petición: método, ruta, versión
> Host: 127.0.0.1:8080                               ← cabeceras de la petición
> User-Agent: curl/8.5.0
> Accept: */*
>                                                    ← línea vacía: fin de la petición (sin cuerpo)
* HTTP 1.0, assume close after body                  ← curl: verá el cierre como final
< HTTP/1.0 200 OK                                    ← línea de estado
< Server: BaseHTTP/0.6 Python/3.12.3                 ← cabeceras de la respuesta (sin Content-Length)
< Date: Wed, 07 Oct 2026 08:27:41 GMT
<                                                    ← línea vacía
ok                                                   ← cuerpo
* Closing connection                                 ← TCP: se cierra
```

## Cómo responde `labweb` y por qué

| Petición | Respuesta | Por qué |
|---|---|---|
| `GET /health` | `200`, cuerpo `ok` | Su código reconoce la ruta |
| `GET /` o `GET /fake-url` | `200`, cuerpo `labweb en backend-lab, pid 656, usuario 999` | Solo distingue `/health`; a todo lo demás responde esa línea |
| `HEAD /health` | `501 Unsupported method ('HEAD')`, con `Connection: close` y `Content-Length: 357` (de la página de error que no se envía) | No define `do_HEAD` |
| `POST /health` | `501 Unsupported method ('POST')` y página HTML de error | No define `do_POST` |
| Dos peticiones seguidas | Dos conexiones, `Closing connection` tras cada una | `http.server` usa `protocol_version = 'HTTP/1.0'` por defecto y `labweb` no envía `Content-Length` |

Según la documentación de `http.server` (Python 3.12), si `protocol_version` pasa a `'HTTP/1.1'` el servidor admite conexiones persistentes, pero entonces debe enviar `Content-Length` en todas sus respuestas. `request_version` es otra cosa: la versión que pidió el cliente.

## El healthcheck y `-f`

`labweb-health.service` ejecuta `curl -fsS --max-time 5 http://127.0.0.1:8080/health`. Probado con el `501` del `POST` como error:

| Comando | Código HTTP | Código de salida | Qué concluye systemd |
|---|---|---|---|
| `curl -X POST http://127.0.0.1:8080/health` | `501` | `0` | Todo bien: el error pasa desapercibido |
| `curl -f -X POST http://127.0.0.1:8080/health` | `501` | `22` (`The requested URL returned error: 501`) | `failed`, con el error en el journal |

Con `-f` desaparece además la página HTML de error de la salida.

## Una IP, varios sitios: Cloudflare

`dig +short cloudflare.com` devuelve, entre otras, `104.16.132.229`.

| Petición (portátil) | `Host` enviado | Respuesta |
|---|---|---|
| `curl -v http://104.16.132.229` | `104.16.132.229` | `403 Forbidden`, cuerpo `error code: 1003` (acceso directo por IP no permitido) |
| `curl -v -H "Host: cloudflare.com" http://104.16.132.229` | `cloudflare.com` | `301`, `Location: https://www.cloudflare.com/` |

Misma IP, mismo puerto, misma petición: solo cambia `Host`. Es lo que hará nginx en el VPS con `server_name`.

## La cookie de sesión de Odoo

`curl -I https://www.odoo.com/web/login` devuelve `HTTP/2 200`, `server: nginx` (odoo.com tiene nginx delante de Odoo) y dos cookies:

```
set-cookie: frontend_lang=en_US; Expires=Thu, 07 Oct 2027 16:08:03 GMT; Path=/
set-cookie: session_id=BjCS6s...; Expires=Thu, 07 Oct 2027 ...; Max-Age=604800; Secure; HttpOnly; Path=/
```

| Cookie | Uso | Atributos que importan |
|---|---|---|
| `frontend_lang` | Idioma de la web | — |
| `session_id` | La sesión del usuario | `Secure` (solo HTTPS), `HttpOnly` (sin acceso desde JavaScript), `Max-Age=604800` (7 días; manda sobre el `Expires` de un año) |

Si Odoo se sirviera por HTTP sin TLS, el `session_id` de los usuarios viajaría en claro: uno de los motivos por los que el certificado no es opcional en el VPS.

## Keep-alive: `labweb` frente a mediavida

Dos URLs en un mismo `curl -v`:

| | `labweb` (VPS) | `http://mediavida.com` (portátil) |
|---|---|---|
| Versión de la respuesta | `HTTP/1.0` | `HTTP/1.1` |
| `Content-Length` | No | `166` |
| `Connection` | — | `keep-alive` |
| Conexiones | 2 (`Trying` dos veces) | 1 |
| Tras cada respuesta | `Closing connection` | `left intact` |
| Segunda petición | `Trying` de nuevo | `Reusing existing http: connection with host mediavida.com` |

## HTTP/1.1 frente a HTTP/2, en paralelo

Dos URLs de `https://www.mediavida.com` a la vez (`-Z`):

| | `--http1.1` (VPS, `curl` 8.5.0) | `--http2` (portátil, `curl` 8.22.0) |
|---|---|---|
| Versión negociada | `ALPN: server accepted http/1.1` | `ALPN: server accepted h2` → `using HTTP/2` |
| Conexiones | 2 (`Connected to` dos veces; `Connection #0` y `#1`) | 1 (`Established connection` una vez) |
| *Handshakes* TCP y TLS | 2, casi intercalados | 1 |
| Segunda petición | Por su propia conexión | `Multiplexed connection found`, *stream* `[3]` |
| Orden | — | Las dos peticiones salen antes de que llegue ninguna respuesta |

Antes de abrir nada, `curl` espera a saber si puede multiplexar: `Waiting on connection to negotiate possible multiplexing`.

Ambas pruebas recibieron `403` del CDN de mediavida (Bunny), con `CDN-Challenge: true`: protección contra bots ante peticiones que no vienen de un navegador. No afecta a lo que se mide, que es la conexión.

## Una página real en el navegador

Herramientas de desarrollador (`F12` → *Network*, recargar, clic derecho en los títulos de columna → *Protocol*) sobre `https://www.odoo.com/web/login`: **27 peticiones** para una página; la mayoría `h3`, muchas `h2` y una `http/1.1`. Con HTTP/1.1 y seis conexiones, 27 peticiones serían varias rondas de cola.

## Inyección de la operadora: pixeldrain

**Por HTTP**, desde el portátil en la red de casa:

```
> GET / HTTP/1.1
> Host: pixeldrain.com
> 
* Received HTTP/0.9 when not allowed
< <!DOCTYPE html>
curl: (1) Received HTTP/0.9 when not allowed
```

Con `--http0.9`, el cuerpo es una página en español: *«Contenido bloqueado por requerimiento de la Autoridad Competente comunicado a esta Operadora»*.

| Dato | Qué indica |
|---|---|
| Sin línea de estado ni cabeceras | No responde un servidor HTTP real: es una página inyectada |
| `lang="es"` y texto en español | Pixeldrain es un servicio en inglés |
| El propio mensaje | La operadora bloquea por requerimiento de una autoridad |

El `451` que se vio en el navegador en el Bloque 2 no aparece hoy: o la operadora ha cambiado la página, o aquel código venía de otro sitio.

**Por HTTPS** (`curl -v https://pixeldrain.com`): la conexión TCP se abre, `curl` envía el `Client hello` de TLS y llega `Recv failure: Connection reset by peer` (código `35`). El corte llega después de abrir TCP, no antes como se supuso en el Bloque 2. Qué lee quien intercepta en ese mensaje (el SNI) es del Bloque 4.

## Errores de `curl` y de la shell vistos

| Lo que se ve | Causa | Arreglo |
|---|---|---|
| `curl: (2) no URL specified` tras `curl -X http://…` | `-X` tomó la URL como nombre del método | El método justo detrás: `-X POST URL` |
| `Warning: The provided HTTP header 'cloudflare.com' does not look like a header?` | A `-H` se le pasó solo el valor | La línea completa entre comillas: `-H "Host: cloudflare.com"` |
| `curl: (22) The requested URL returned error: 501` | `-f` ante un código `400` o superior | Es lo esperado en un healthcheck |
| `curl: (1) Received HTTP/0.9 when not allowed` | Respuesta sin línea de estado | `--http0.9` para verla; sospechar de algo en medio |
| `curl: (35) Recv failure: Connection reset by peer` | Corte durante el *handshake* de TLS | Diagnóstico en el Bloque 4 |
| `Immediate connect fail for 2400:…: Network is unreachable` | El portátil no tiene salida IPv6; `curl` pasa a IPv4 | Nada que hacer; el VPS sí tiene IPv6 |
| Cada cabecera aparece dos veces | `-I` las escribe en la salida normal y `-v` otra vez con `<` | Usar solo una de las dos opciones si molesta |
| `fish: $? is not the exit status` | En fish la variable es `$status` | `echo $status` |
| `grep` no filtra la salida de `curl -v` | Orden de la tubería invertido, y `-v` escribe en *stderr* | `curl … 2>&1 \| grep …` |
| No aparece `set-cookie` de sesión en odoo.com | Se pidió `http://odoo.com/`: solo un `302` a HTTPS | URL completa: `https://www.odoo.com/web/login` |

## Confusiones vistas

| Confusión | Corrección |
|---|---|
| Una ruta inexistente da `404` | Solo si el código del servidor lo programa; `labweb` da `200` |
| Las partes del mensaje son cabecera y cuerpo | Primera línea, cabeceras, línea vacía y cuerpo (opcional) |
| `-I` muestra las cabeceras de la petición | Las de la **respuesta**; lo consigue enviando `HEAD` |
| `-I` envía `GET` | Envía `HEAD` (por eso `labweb` dio `501`) |
| El código HTTP es el de la conexión | Es la respuesta del servidor, dentro de HTTP; la conexión (TCP) no tiene códigos |
| `-f` es un método | Es una opción de `curl`; no cambia nada de lo que se envía |
| `-f` depende de cómo esté configurado `curl` | Su regla es fija (`≥ 400` → `22`); lo que varía es el código que elige el servidor |
| Las líneas `*` son mensajes del servidor | Son avisos de `curl` para ti; no viajan |
| `Host` es la URL | Es solo el nombre; la ruta va en la línea de petición |
| El NAT reparte los sitios de un servidor | El NAT traduce IPs y puertos en el router doméstico; el reparto por nombre lo hace `Host` |
| La cookie la inventa el navegador | La crea el servidor y la envía en `Set-Cookie` |
| `Secure` impide que JavaScript lea la cookie | Eso es `HttpOnly`; `Secure` limita el envío a HTTPS |
| HTTP/1.1 abre una conexión por petición | Reutiliza la conexión; el bloqueo está dentro de ella |
| `Connection: keep-alive` es TCP | Es una cabecera HTTP; TCP solo ejecuta lo que pide |
| `left intact` se debe a HTTP/2 | HTTP/1.1 también mantiene la conexión si el servidor marca el final de cada respuesta |
| Una trama de HTTP/2 es un segmento TCP | Es un trozo de un mensaje HTTP/2 que viaja dentro de los segmentos TCP |
| Un *stream* es una conexión cliente-servidor | Es una petición con su respuesta; una conexión lleva muchos |
| Con HTTP/2 un paquete perdido solo frena su *stream* | Frena todos: TCP no sabe qué bytes son de cada *stream* |
| Las tramas de HTTP/2 son las de la capa de enlace | Mismo nombre, capas distintas |

## Preguntas frecuentes y cómo responderlas

| Pregunta | Comando o consulta |
|---|---|
| ¿Responde `labweb` y con qué código? | `curl -v http://127.0.0.1:8080/health` (VPS) |
| ¿Qué cabeceras devuelve un sitio, sin descargar la página? | `curl -I URL` |
| ¿Fallaría un healthcheck con esta respuesta? | `curl -f URL`, y después `echo $status` (fish) |
| ¿Qué versión de HTTP habla un servidor? | Primera línea `<` de `curl -v`; con HTTPS, `ALPN: server accepted …` |
| ¿Reutiliza la conexión? | `curl -v URL1 URL2`: buscar `Reusing existing` frente a `Closing connection` |
| ¿Multiplexa? | `curl -v -I -Z --http2 URL1 URL2 2>&1 \| grep -ic established` → `1` |
| ¿Qué sitio sirve una IP si le pido un nombre concreto? | `curl -v -H "Host: NOMBRE" http://IP` |
| ¿Qué cookie de sesión pone una aplicación? | `curl -I URL_DE_LOGIN` y buscar `set-cookie` |
| ¿Responde el servidor real o algo en medio? | `curl -v http://…`: una respuesta sin línea de estado o con `Server` inesperado es sospechosa; `--http0.9` para ver el cuerpo |
| ¿Cuántas peticiones y con qué protocolo carga una página? | Navegador, `F12` → *Network* → columna *Protocol* |
| Odoo detrás de nginx no carga: ¿de qué lado está el fallo? | `curl -v` en el VPS contra el puerto de Odoo, saltándose nginx. Un `502` de nginx: no pudo hablar con Odoo; un `500`: Odoo respondió con error |

---

# Parte 3 · Comandos útiles del bloque

## `curl`: peticiones y lectura de la respuesta

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `curl URL` | Petición `GET`; escribe el cuerpo de la respuesta | Sin `http://` usa HTTP; sin ruta pide `/` |
| `curl -v URL` | `-v` (*verbose*): toda la conversación. `*` = avisos de `curl` (conexión), `>` = lo enviado, `<` = lo recibido | Primer paso de cualquier diagnóstico HTTP. Con HTTPS añade muchas líneas de TLS |
| `curl -I URL` | `-I` (`--head`): envía `HEAD` y muestra solo línea de estado y cabeceras | Ver código, `Server`, cookies o redirecciones sin descargar la página. Si el servidor no implementa `HEAD` da `501` (`labweb`). Con `-v` las cabeceras salen dos veces |
| `curl -X MÉTODO URL` | `-X` (`--request`): cambia el método (`-X POST`) | El valor va justo detrás; sin él, `curl` toma la URL como método: `(2) no URL specified` |
| `curl -d DATOS URL` | `-d` (`--data`): envía datos en el cuerpo y cambia el método a `POST` | Alternativa a `-X POST` cuando de verdad hay datos |
| `curl -H "Nombre: valor" URL` | `-H` (`--header`): añade o sustituye una cabecera | La línea completa, entre comillas por el espacio. Solo el valor da `does not look like a header` |
| `curl -H "Host: NOMBRE" http://IP` | Pedir a una IP presentándose como un dominio | *Virtual hosting* (Cloudflare `403`/`1003` frente a `301`). Con HTTPS no basta: el nombre también viaja en TLS |
| `curl --resolve NOMBRE:PUERTO:IP URL` | Fijar a qué IP resuelve un nombre solo para esta petición | Probar `mlozano.dev` contra el VPS antes de cambiar el DNS (Linux · Bloque 3). Funciona también con HTTPS |
| `curl --http0.9 URL` | Aceptar respuestas sin línea de estado | Diagnóstico de inyecciones (pixeldrain). Desactivado por defecto desde la 7.66 |

## `curl`: códigos de salida y scripts

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `curl -f URL` | `-f` (`--fail`): con código HTTP `≥ 400`, sale con `22` y no escribe el cuerpo | Imprescindible en healthchecks. Solo mira el código, no el contenido |
| `curl -fsS --max-time 5 URL` | `-s` silencio, `-S` pero muestra errores, `--max-time` límite en segundos | La línea de `labweb-health.service` |
| `echo $status` (fish) / `echo $?` (bash) | Código de salida del último comando | Justo después, sin nada en medio. `0` = bien |
| Códigos vistos | `1` protocolo no soportado (HTTP/0.9), `2` error de uso, `7` nadie escucha, `22` error HTTP con `-f`, `35` fallo en TLS, `52` el servidor no respondió | Lista completa en `man curl`, sección *EXIT CODES* |

## `curl`: conexiones y versiones

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `curl -v URL1 URL2` | Varias URLs, una detrás de otra; reutiliza la conexión si puede | Comprobar keep-alive: `Reusing existing` frente a `Closing connection` |
| `curl -Z URL1 URL2` | `-Z` (`--parallel`): lanza las peticiones a la vez | Ver cuántas conexiones abre cada versión |
| `curl --http1.1 URL` | Forzar HTTP/1.1 | Comparar con HTTP/2; en paralelo abre una conexión por petición |
| `curl --http2 URL` | Intentar HTTP/2 (por HTTPS se acuerda con ALPN) | La línea `ALPN: server accepted h2` y después `using HTTP/2` lo confirman |

## Shell: filtrar salidas

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `COMANDO 2>&1 \| grep -i TEXTO` | `2>&1` une *stderr* a la salida normal; `\|` pasa la salida al siguiente; `grep -i` filtra sin distinguir mayúsculas | `curl -v` escribe en *stderr*: sin `2>&1`, `grep` no ve nada. El productor va a la izquierda de `\|`. Funciona en bash y fish |
| `grep -ic TEXTO` | `-c`: cuenta las líneas en lugar de mostrarlas | Contar conexiones (`established`) |

## DNS

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `dig +short NOMBRE` | Solo las IPs de la respuesta | Encontrar la IP a la que pedir con `-H "Host: …"` |

## Documentación y navegador

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `man curl`, y dentro `/--opción` + `Enter`, `n`, `q` | Buscar una opción por su nombre largo; `n` siguiente coincidencia; `q` salir | Buscar `--request`, `--header`, `--fail`, `/EXIT CODES`. Mejor el nombre largo que palabras sueltas. Usar el `man` de la máquina donde se ejecuta |
| `https://docs.python.org/3.12/library/http.server.html` | Documentación de `http.server` para la versión del VPS | `protocol_version` decide la versión que habla `labweb`; `request_version` es la del cliente |
| Navegador: `F12` → *Network* → recargar → columna *Protocol* | Peticiones de una página y su protocolo (`http/1.1`, `h2`, `h3`) | Solo registra lo pedido con la pestaña abierta |
| RFC 9110 (secc. 7.2 `Host`, 9 métodos, 15 códigos), RFC 9112 (secc. 9 conexiones), RFC 7725 (`451`) | Consulta del significado exacto | Buscar el código o la cabecera concretos, no leer entero |
