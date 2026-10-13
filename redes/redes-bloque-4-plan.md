# Redes · Bloque 4 — TLS · Plan de sesiones

Carril de Redes, en alternancia por sesión con Linux y VPS. Seis sesiones de **~2 h** con objetivos numerados como puntos de control.

**Enfoque (acordado el 13/10/2026):** nivel de quien configura, diagnostica y explica incidencias en sus servidores (platform engineering / DevOps), no de quien diseña protocolos. Lo interno del protocolo (formato de los mensajes, orden exacto del *handshake*, diferencias finas entre versiones) se ve solo a nivel de idea. Lo que pesa: la cadena de certificados, SNI, ACME y medir el coste de TLS.

**Criterio de cierre:** explicar, sin notas, qué hace certbot por debajo: cómo demuestra a Let's Encrypt que controlas `odoo.mlozano.dev`, qué recibe, dónde lo deja, qué cambia en nginx y qué ocurre en cada conexión de un navegador con ese certificado.

**Entorno de partida:**

| Pieza | Estado |
|---|---|
| VPS | `backend-lab`, Ubuntu 24.04, shell `fish`, alias `vps` |
| nginx | Delante de Odoo (`127.0.0.1:8069`) y de `labweb` (`127.0.0.1:8080`), en 80 y 443; HTTP/2 activo en el 443 |
| Certificado | Let's Encrypt para `odoo.mlozano.dev`, obtenido con el plugin de nginx de certbot; renovación por `certbot.timer` |
| Endurecimiento | HSTS y cookie `secure` activos (Linux · Bloque 3, Sesión 10) |
| Portátil | CachyOS, `curl` 8.22.0 |
| Material previo | El `diff` del sitio de nginx antes y después de certbot, con las líneas aparcadas para este bloque |

**Ritual de cada sesión:** según las instrucciones del proyecto (§7).

---

## Índice

| # | Sesión | Dónde se trabaja |
|---|---|---|
| 1 | Cierre de HTTP/2 y la puerta de TLS (ALPN) ✅ | Portátil + VPS |
| 2 | Qué protege TLS y cuánto cuesta | Portátil |
| 3 | La cadena de certificados | VPS + portátil |
| 4 | SNI: varios dominios en una IP | Portátil |
| 5 | Qué hace certbot por debajo: ACME y el reto HTTP-01 | VPS |
| 6 | HSTS, Certificate Transparency y criterio de cierre | Portátil (navegador) + VPS |

## Bibliografía del bloque y dónde se usa

| Fuente | Sesiones |
|---|---|
| Kurose y Ross, 8.ª ed., 2.2.6 (HTTP/2) | 1 |
| Kurose y Ross, 8.ª ed., 8.1, 8.2 y 8.6 a nivel de idea (qué garantiza TLS y cómo arranca) | 2 |
| Kurose y Ross, 8.ª ed., 8.3.3 (firmas y certificados) | 3 |
| `man curl` → `--write-out` (`time_connect`, `time_appconnect`) y `--resolve` | 2, 4 |
| Cloudflare Learning Center, *What is SNI?* | 4 |
| Documentación de Let's Encrypt (*How It Works*, *Challenge Types*, *Chain of Trust*) | 3, 5 |
| Documentación de certbot y de nginx (`ngx_http_ssl_module`, `ngx_http_v2_module`) en la versión instalada | 1, 5 |
| `man openssl-s_client`, `man openssl-x509`, `man openssl-verify` (man.archlinux.org en el portátil; manpages.ubuntu.com, *noble*, en el VPS) | 3, 4 |
| MDN, cabecera `Strict-Transport-Security`; certificate.transparency.dev | 6 |

**Lectura principal: Kurose.** Grigorik (*High Performance Browser Networking*, caps. 4 y 12) y el RFC 8446 quedan como **consulta opcional** para un detalle concreto.

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

## Sesión 2 · Qué protege TLS y cuánto cuesta

**1. El problema** (portátil, terminal y navegador)

`curl -v` contra `odoo.mlozano.dev` muestra `TLSv1.3` y `TLS_AES_128_GCM_SHA256`, y varias líneas `TLS handshake, …` antes de la primera petición. Dos preguntas de administrador: ¿qué ve alguien conectado a tu misma wifi?, y si un usuario dice «Odoo va lento», ¿cuánto de ese tiempo es TLS y no Odoo?

**2. Bibliografía**

- Kurose 8.1 → las tres garantías: confidencialidad, integridad y autenticación.
- Kurose 8.2, a nivel de idea → por qué TLS usa clave pública al empezar y clave simétrica para los datos.
- Kurose 8.6, solo la visión general del *handshake* → qué se negocia antes del primer byte de HTTP.
- `man curl` → `--write-out` con `time_connect` y `time_appconnect`.
- Formato de cada mensaje del *handshake* y diferencias finas entre TLS 1.2 y 1.3: consulta opcional (RFC 8446 §2, Grigorik cap. 4).

**3. Objetivos para darla por superada**

1. Dices qué garantía cubre cada parte de `TLS_AES_128_GCM_SHA256` (una línea por parte, a nivel de idea).
2. Sabes qué partes de una conexión a `odoo.mlozano.dev` son visibles para un tercero en la red (IP, puerto, nombre) y cuáles no (ruta, cabeceras, cookies, cuerpo).
3. Mides con `curl` el tiempo de la conexión TCP y el de TLS por separado, y los comparas con el RTT de `ping` al VPS: cuántos viajes de ida y vuelta añade TLS 1.3.

**4. Lo más importante**

- Cifrar sin autenticar no sirve: estarías hablando en secreto con quien no es. Esa autenticación es el certificado (Sesión 3).
- Separar el tiempo de TCP, TLS y la respuesta del servidor es diagnóstico real; es la misma medida que usará el healthcheck (Artefacto 2).
- Lo visible del objetivo 2 (el nombre) es la base de SNI (Sesión 4).

---

## Sesión 3 · La cadena de certificados

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

## Sesión 4 · SNI: varios dominios en una IP

**1. El problema** (portátil, terminal)

Si un día tu VPS sirve dos dominios en la misma IP, ¿cómo sabe nginx qué certificado enviar antes de ver ninguna cabecera `Host`? Es la misma pregunta que resuelve cualquier *ingress* de Kubernetes. (Caso aparte y opcional: el corte de pixeldrain del Bloque 2 justo después del *Client hello*.)

**2. Bibliografía**

- Cloudflare Learning Center, *What is SNI?* → qué es y por qué viaja sin cifrar.
- Kurose 8.6 → en qué punto del *handshake* va el *ClientHello*.
- `man openssl-s_client` → opciones para elegir o suprimir el nombre enviado.
- `man curl` → `--resolve`: hablar con una IP concreta usando un nombre concreto.
- ECH (*Encrypted Client Hello*): lectura de contexto opcional.

**3. Objetivos para darla por superada**

1. Conectas al VPS con y sin SNI, y con un nombre que no es tuyo, y explicas qué certificado devuelve nginx en cada caso.
2. Confirmas que el nombre viaja sin cifrar en el *ClientHello*.
3. *(Opcional, solo si sobra tiempo)* Pruebas la hipótesis del corte por SNI en pixeldrain: misma IP con el nombre real y con otro nombre. Anotas la conclusión corregida del Bloque 2.

**4. Lo más importante**

- SNI es lo que permite muchos sitios con HTTPS en una IP, y también lo que ve una operadora aunque todo lo demás vaya cifrado.
- Cuando tu VPS sirva más de un dominio, el `server_name` y el certificado de cada bloque `server` dependen de esto (Bloque 5).

---

## Sesión 5 · Qué hace certbot por debajo: ACME y el reto HTTP-01

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
- Con esta sesión está casi todo el criterio de cierre; la Sesión 6 lo une.

---

## Sesión 6 · HSTS, Certificate Transparency y criterio de cierre

**1. El problema** (portátil, navegador con F12; VPS)

Con HSTS activo, cargar `http://odoo.mlozano.dev` produce un `307 Internal Redirect` que no sale de tu servidor. Cualquiera puede ver todos los certificados emitidos para `mlozano.dev`. Y para cerrar el bloque: explicar, sin notas, todo lo que ocurre desde que `certbot.timer` lanza una renovación hasta que un navegador abre `https://odoo.mlozano.dev` con el certificado nuevo.

**2. Bibliografía**

- MDN, cabecera `Strict-Transport-Security` → `max-age`, `includeSubDomains` y precarga.
- hstspreload.org → por qué `.dev` entero está en la lista de precarga.
- certificate.transparency.dev → qué son los logs públicos.
- Tus notas de las Sesiones 1 a 5, solo para repasar antes del recorrido; el recorrido, sin ellas.

**3. Objetivos para darla por superada**

1. Capturas el `307 Internal Redirect` (F12 → *Network*, con *Preserve log*) y explicas por qué no llega al VPS y por qué en `.dev` no existe la primera visita sin HSTS.
2. Buscas `mlozano.dev` en un buscador de logs de CT y explicas qué subdominios aparecen y por qué.
3. Recorrido en voz alta de la renovación (timer, ACME, HTTP-01, ficheros en `/etc/letsencrypt`, recarga de nginx) y de una conexión (TCP, *ClientHello* con SNI y ALPN, cadena, primera petición HTTP/2), con una salida real que demuestre cada paso.

**4. Lo más importante**

- Con HSTS, un certificado caducado tumba el acceso por completo: no se puede saltar el aviso.
- CT hace públicos todos tus nombres con certificado: no publiques un subdominio pensando que nadie lo encontrará.
- Si los objetivos 1 y 2 se comen la sesión, el objetivo 3 pasa a una sesión corta propia.
- Es la mitad del hito final de Redes («qué ocurre entre teclear tu dominio y ver Odoo»). Al cerrar: apuntes `redes-bloque-4.md`, línea en `progreso.md` y borrar este plan del repo.
