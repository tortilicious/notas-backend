# Redes · Bloque 4 — TLS · Plan de sesiones

Carril de Redes, en alternancia por sesión con Linux y VPS. Ocho sesiones de **~2 h** con objetivos numerados como puntos de control.

**Criterio de cierre:** explicar, sin notas, qué hace certbot por debajo: cómo demuestra a Let's Encrypt que controlas `odoo.mlozano.dev`, qué recibe, dónde lo deja, qué cambia en nginx y qué ocurre en cada conexión de un navegador con ese certificado.

**Entorno de partida:**

| Pieza | Estado |
|---|---|
| VPS | `backend-lab`, Ubuntu 24.04, shell `fish`, alias `vps` |
| nginx | Delante de Odoo (`127.0.0.1:8069`) y de `labweb` (`127.0.0.1:8080`), en 80 y 443 |
| Certificado | Let's Encrypt para `odoo.mlozano.dev`, obtenido con el plugin de nginx de certbot; renovación por `certbot.timer` |
| Endurecimiento | HSTS y cookie `secure` activos (Linux · Bloque 3, Sesión 10) |
| Portátil | CachyOS, `curl` 8.22.0 |
| Material previo | El `diff` del sitio de nginx antes y después de certbot, con las líneas aparcadas para este bloque |

**Ritual de cada sesión:** según las instrucciones del proyecto (§7).

---

## Índice

| # | Sesión | Dónde se trabaja |
|---|---|---|
| 1 | Cierre de HTTP/2 y la puerta de TLS (ALPN) | Portátil + VPS |
| 2 | Qué protege TLS: cifrado, autenticación e integridad | Portátil |
| 3 | El *handshake* paso a paso | Portátil |
| 4 | La cadena de certificados | VPS + portátil |
| 5 | SNI y el caso pixeldrain | Portátil |
| 6 | Qué hace certbot por debajo: ACME y el reto HTTP-01 | VPS |
| 7 | HSTS, precarga y Certificate Transparency | Portátil (navegador) |
| 8 | Criterio de cierre | Portátil + VPS |

## Bibliografía del bloque y dónde se usa

| Fuente | Sesiones |
|---|---|
| Kurose y Ross, 8.ª ed., 2.2.6 (HTTP/2) | 1 |
| Kurose y Ross, 8.ª ed., cap. 8: 8.1 a 8.3 (criptografía, integridad, firmas y certificados) y 8.6 (TLS) | 2 a 5 |
| Cloudflare Learning Center, *What is SNI?* | 5 |
| MDN, cabecera `Strict-Transport-Security` | 7 |
| Documentación de Let's Encrypt (*How It Works*, *Challenge Types*, *Chain of Trust*) | 4, 6 |
| Documentación de certbot y de nginx (`ngx_http_ssl_module`, `ngx_http_v2_module`) en la versión instalada | 1, 6 |
| `man openssl-s_client`, `man openssl-x509`, `man openssl-verify` (man.archlinux.org en el portátil; manpages.ubuntu.com, *noble*, en el VPS) | 3, 4, 5 |

**Lectura principal: Kurose.** El nivel que pide el bloque es el de quien administra su servidor, no el de quien diseña protocolos. Grigorik (*High Performance Browser Networking*, caps. 4 y 12) queda como **consulta opcional** cuando haga falta un detalle concreto; es más técnico. Kurose describe TLS 1.2 en parte: tus conexiones usan TLS 1.3, que ahorra un viaje de ida y vuelta en el *handshake*. Para el detalle exacto, el RFC 8446 (opcional).

---

## Sesión 1 · Cierre de HTTP/2 y la puerta de TLS (ALPN)

**1. El problema** (portátil, terminal; VPS, terminal SSH para el objetivo 4)

En el Bloque 3 viste que algunos sitios responden con `HTTP/2`. Pide la portada de `odoo.mlozano.dev` con `curl -v` y fíjate en la versión de la respuesta: ¿tu propio servidor habla HTTP/2? Si no, ¿quién decide la versión, y en qué momento, si la primera línea HTTP se envía ya cifrada?

**2. Bibliografía**

- Kurose 2.2.6 → qué problema resolvió HTTP/2: tramas, *streams* y multiplexado.
- Documentación de nginx, `ngx_http_core_module`, directiva `listen`, parámetro `http2` → cómo se activa en 1.24 (la directiva `http2 on;` de `ngx_http_v2_module` es de 1.25.1).
- Grigorik cap. 12 (*Binary Framing Layer*, *Header Compression*): consulta opcional.

**3. Objetivos para darla por superada**

1. Sabes explicar con la salida de `curl -v` de un sitio con HTTP/2 qué es una trama, un *stream* y qué número de *stream* lleva cada petición.
2. Señalas en la salida de `curl -v` contra `odoo.mlozano.dev` las dos líneas de ALPN (qué ofrece `curl` y qué acepta el servidor) y explicas por qué ese acuerdo ocurre dentro del *handshake* de TLS.
3. Sabes qué hace HPACK a nivel de idea: tabla estática, tabla dinámica y Huffman.
4. HTTP/2 activado en nginx para `odoo.mlozano.dev` con la sintaxis de tu versión (copia previa del sitio, `sudo nginx -t`, `reload`): `curl -v` muestra `HTTP/2 200` y el websocket de Odoo sigue respondiendo `101`.

**4. Lo más importante**

- ALPN es el punto donde HTTP y TLS se tocan: la versión de HTTP se decide antes de enviar la primera petición, y por eso el multiplexado de HTTP/2 solo se usa sobre TLS en los navegadores.
- El objetivo 4 cambia el VPS: cierre con `vps-setup` (capa nginx) e inventario actualizados.
- Si el objetivo 4 no cabe, pasa a la Sesión 2.

---

## Sesión 2 · Qué protege TLS: cifrado, autenticación e integridad

**1. El problema** (portátil, terminal y navegador)

Cuando inicias sesión en `https://odoo.mlozano.dev`, `curl -v` muestra una línea con `TLSv1.3` y `TLS_AES_128_GCM_SHA256`, y el navegador enseña algo parecido en la información del certificado. ¿Qué significa cada trozo de ese nombre, y qué ve alguien conectado a tu misma wifi?

**2. Bibliografía**

- Kurose 8.1 → qué significa comunicación segura: confidencialidad, integridad y autenticación.
- Kurose 8.2 → criptografía de clave simétrica y de clave pública: por qué TLS usa las dos.
- Kurose 8.3.1 y 8.3.2 → funciones *hash* y MAC: la integridad.
- Grigorik cap. 4, *Encryption, Authentication, and Integrity*: consulta opcional.

**3. Objetivos para darla por superada**

1. Descompones `TLS_AES_128_GCM_SHA256` en sus partes y dices qué garantía cubre cada una.
2. Explicas con tus palabras por qué el intercambio inicial usa clave pública y los datos, clave simétrica.
3. Sabes qué partes de una conexión a `odoo.mlozano.dev` son visibles para un tercero en la red (IP, puerto, nombre) y cuáles no (ruta, cabeceras, cookies, cuerpo).

**4. Lo más importante**

- Cifrar sin autenticar no sirve: estarías hablando en secreto con quien no es. Esa autenticación es el certificado (Sesión 4).
- Lo que queda visible en el objetivo 3 es la base del caso pixeldrain (Sesión 5).

---

## Sesión 3 · El *handshake* paso a paso

**1. El problema** (portátil, terminal)

`curl -v` contra `odoo.mlozano.dev` escribe varias líneas `TLS handshake, …` entre `Connected to` y la primera petición. Cada una cuesta tiempo antes de que Odoo reciba nada. ¿Qué mensaje es cada línea y cuántos viajes de ida y vuelta añade TLS a la carga?

**2. Bibliografía**

- Kurose 8.6 → TLS en su conjunto: *handshake*, intercambio de claves y registros.
- `man openssl-s_client` → conectarse a mano y ver el *handshake* sin HTTP encima.
- RFC 8446 §2 (TLS 1.3) y Grigorik cap. 4, *TLS Handshake*: consulta opcional para la diferencia entre 1.2 y 1.3.

**3. Objetivos para darla por superada**

1. Asocias cada línea `TLS handshake` de `curl -v` con su mensaje (*ClientHello*, *ServerHello*, certificado, *Finished*…).
2. Mides con `curl` el tiempo de la conexión TCP y el del *handshake* TLS por separado, y lo comparas con el RTT de `ping` al VPS.
3. Repites la medida forzando TLS 1.2 y explicas la diferencia en viajes de ida y vuelta.

**4. Lo más importante**

- El coste de TLS se paga en cada conexión nueva: por eso importan las conexiones persistentes del Bloque 3 y el multiplexado de HTTP/2.
- Saber aislar el tiempo de TLS es diagnóstico real: «Odoo va lento» puede no ser Odoo.

---

## Sesión 4 · La cadena de certificados

**1. El problema** (VPS, terminal SSH; portátil, terminal)

En `/etc/letsencrypt/live/odoo.mlozano.dev/` hay `cert.pem`, `chain.pem` y `fullchain.pem`, y nginx usa `fullchain.pem`. Tu navegador nunca ha oído hablar de tu servidor y aun así confía en él. ¿Qué hay en cada fichero, y qué pasaría si nginx sirviera `cert.pem`?

**2. Bibliografía**

- Kurose 8.3.3 → firmas digitales y certificación de clave pública: por qué una autoridad puede responder por tu clave.
- Documentación de Let's Encrypt → *Chain of Trust*: qué intermedio y qué raíz usa ahora.
- `man openssl-x509` y `man openssl-verify`.
- Revocación: lectura de contexto; comprueba en tu certificado si trae URL de revocación y contrástalo con la documentación actual de Let's Encrypt.

**3. Objetivos para darla por superada**

1. Para cada certificado de la cadena, sacas *Subject*, *Issuer* y fechas de validez, y dibujas la cadena hoja → intermedio → raíz.
2. Localizas la raíz en el almacén de confianza del portátil y dices quién la instaló ahí.
3. Reproduces sin tocar nginx el fallo de servir `cert.pem`: la verificación sin el intermedio falla y con él pasa.
4. Explicas por qué la clave privada nunca sale del VPS y dónde está (sin mostrar su contenido).

**4. Lo más importante**

- `fullchain.pem` frente a `cert.pem` es uno de los fallos clásicos: el navegador de escritorio a veces lo tapa y una app o un `curl` fallan. Material para el Bloque 5 de Linux.
- La fecha de caducidad que ves hoy es la que vigila `certbot.timer`; si falla, es un incidente de Linux · Bloque 5 esperando a ocurrir.

---

## Sesión 5 · SNI y el caso pixeldrain

**1. El problema** (portátil, terminal)

En el Bloque 2, la conexión HTTPS a pixeldrain se abría y se cortaba justo después del *Client hello* (`Connection reset by peer`, código 35 de `curl`). Ese bloque lo atribuyó a otra causa. Y en tu propio VPS: si un día sirve dos dominios en la misma IP, ¿cómo sabe nginx qué certificado enviar antes de ver ninguna cabecera `Host`?

**2. Bibliografía**

- Cloudflare Learning Center, *What is SNI?* → qué es y por qué viaja sin cifrar.
- Kurose 8.6 → en qué punto del *handshake* va el *ClientHello*.
- `man openssl-s_client` → opciones para elegir o suprimir el nombre enviado.
- `man curl` → `--resolve`: hablar con una IP concreta usando un nombre concreto.
- ECH (*Encrypted Client Hello*): lectura de contexto opcional.

**3. Objetivos para darla por superada**

1. Conectas al VPS con y sin SNI, y con un nombre que no es tuyo, y explicas qué certificado devuelve nginx en cada caso.
2. Confirmas que el nombre viaja sin cifrar en el *ClientHello*.
3. Pruebas la hipótesis del corte por SNI en pixeldrain: misma IP con el nombre real y con otro nombre. Anotas la conclusión corregida del Bloque 2.

**4. Lo más importante**

- SNI es lo que permite muchos sitios con HTTPS en una IP, y también lo que ve una operadora aunque todo lo demás vaya cifrado.
- Cuando tu VPS sirva más de un dominio, el `server_name` y el certificado de cada bloque `server` dependen de esto (Bloque 5).

---

## Sesión 6 · Qué hace certbot por debajo: ACME y el reto HTTP-01

**1. El problema** (VPS, terminal SSH)

Ejecutaste `certbot --nginx` y apareció un certificado válido. Let's Encrypt no te conoce: ¿cómo comprobó que controlas `odoo.mlozano.dev`? Y del `diff` de nginx quedan sin explicar `options-ssl-nginx.conf` y `ssl_dhparam`.

**2. Bibliografía**

- Documentación de Let's Encrypt → *How It Works* y *Challenge Types* (HTTP-01).
- Documentación de certbot → plugin de nginx y `renew --dry-run`.
- nginx, `ngx_http_ssl_module` → `ssl_protocols`, `ssl_ciphers`, `ssl_session_cache`, `ssl_dhparam`.
- Tu `diff` de certbot de Linux · Bloque 3, Sesión 10.

**3. Objetivos para darla por superada**

1. Durante una renovación de prueba, encuentras en el log de acceso de nginx la petición de Let's Encrypt a `/.well-known/acme-challenge/` y explicas cómo le respondió nginx sin que tú configuraras esa ruta.
2. En el log de certbot identificas los pasos de ACME: cuenta, pedido, reto, validación, emisión.
3. Explicas cada línea de `options-ssl-nginx.conf` y si `ssl_dhparam` se usa en tus conexiones TLS 1.3 (con la referencia delante).

**4. Lo más importante**

- HTTP-01 necesita el puerto 80 abierto y respondiendo: el cortafuegos de Linux · Bloque 4 no puede cerrarlo.
- Con esta sesión está casi todo el criterio de cierre; la Sesión 8 lo une.

---

## Sesión 7 · HSTS, precarga y Certificate Transparency

**1. El problema** (portátil, navegador con F12)

Con HSTS activo, cargar `http://odoo.mlozano.dev` en el navegador produce un `307 Internal Redirect` que no sale de tu servidor. Y cualquiera puede ver todos los certificados emitidos para `mlozano.dev`: ¿qué revela eso de tus subdominios?

**2. Bibliografía**

- MDN, cabecera `Strict-Transport-Security` → qué hace, `max-age`, `includeSubDomains` y la precarga.
- hstspreload.org → qué es la lista de precarga y por qué `.dev` entero está en ella.
- Documentación de Certificate Transparency (certificate.transparency.dev) → qué son los logs públicos.

**3. Objetivos para darla por superada**

1. Capturas el `307 Internal Redirect` (F12 → *Network*, con *Preserve log*) y explicas por qué no llega al VPS.
2. Explicas por qué la primera visita sin HSTS es el punto débil y por qué en `.dev` ese punto no existe.
3. Buscas `mlozano.dev` en un buscador de logs de CT y explicas qué subdominios aparecen y por qué.

**4. Lo más importante**

- CT hace públicos todos tus nombres con certificado: no publiques un subdominio pensando que nadie lo encontrará.
- Con HSTS, un error de certificado deja de poder saltarse en el navegador: un certificado caducado tumba el acceso por completo.

---

## Sesión 8 · Criterio de cierre

**1. El problema** (portátil + VPS)

Explicar, sin notas, todo lo que ocurre desde que `certbot.timer` lanza una renovación hasta que un navegador abre `https://odoo.mlozano.dev` con el certificado nuevo.

**2. Bibliografía**

- Tus notas de las Sesiones 1 a 7, solo para repasar antes; la explicación, sin ellas.

**3. Objetivos para darla por superada**

1. Recorrido en voz alta de la renovación: timer, ACME, HTTP-01, ficheros en `/etc/letsencrypt`, recarga de nginx.
2. Recorrido en voz alta de una conexión: TCP, *ClientHello* con SNI y ALPN, cadena de certificados, claves, primera petición HTTP/2.
3. Para cada paso, una salida real que lo demuestra (un comando o una línea de log).

**4. Lo más importante**

- Es la mitad del hito final de Redes («qué ocurre entre teclear tu dominio y ver Odoo»).
- Al cerrar: apuntes `redes-bloque-4.md`, línea en `progreso.md` y borrar este plan del repo.
