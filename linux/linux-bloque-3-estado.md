# Linux/VPS · Bloque 3 · Estado para continuar en un chat nuevo

> **Para Claude:** pega esto como contexto. `progreso.md` **no** está actualizado con el Bloque 3 por decisión propia: se actualiza al cerrar el bloque con los datos de este fichero. El plan de sesiones está en `linux-bloque-3-plan.md` y los apuntes de lo hecho, en `linux-bloque-3.md`.

## Dónde estoy

- **Bloque 3 · Odoo 18 desplegado a mano:** 🟡 en curso. Sesiones 1 a 9 completadas (la 9, el 11/10/2026; sus tres comprobaciones de navegador pasan a la 10). **Siguiente: Sesión 10 · HTTPS con certbot.**
- Decisión de solape con Redes: nginx y TLS se instalan funcionales en este bloque; el fondo queda para Redes · Bloques 4 y 5.

| Sesión | Estado | Ritual de cierre |
|---|---|---|
| 1 · La red del VPS | ✅ | Hecho, con correcciones en local/peer y `0.0.0.0` |
| 2 · Paquetes | ✅ | Hecho; preguntas 3, 4 y 5 con ayuda. Leído TLCL cap. 14 |
| 3 · PostgreSQL listo para Odoo | ✅ | Hecho |
| 4 · Código y entorno Python | ✅ | Hecho. Leído HLW cap. 15 (bibliotecas y cabeceras) |
| 5 · Primer arranque y `odoo.conf` | ✅ | Hecho, línea a línea. Correcciones: valor por defecto de `data_dir` (`$HOME/.local/share/Odoo`), `addons/18.0` depende de `data_dir`, `admin_passwd` no tiene opción de CLI y su defecto es `admin` |
| 6 · `odoo.service` | ✅ | Hecho, una pregunta cada vez. Correcciones: motivo de `Wants=` (se reconecta solo; `Restart=` no rescata una parada por dependencia), consecuencia de `postgresql.service` (activo al instante), cadena `rwxr-x---` (9 caracteres). `verify` no lo recordó: se le dio |
| 7 · Los PDF: wkhtmltopdf | ✅ | Hecho. Odoo genera PDF con logo, cabecera, estilos y pie. Repetido en la Sesión 8, una pregunta cada vez. Correcciones: `apt` **sí** trae `wkhtmltopdf` (el motivo es que su build no lleva Qt parcheado y no pone cabecera ni pie); `report.url` lleva el esquema (`http://127.0.0.1:8069`); lo que descarga `wkhtmltopdf` de esa dirección son los recursos del informe (estilos, logo, fuentes), no «el programa» |
| 8 · nginx delante de `labweb` | ✅ | Hecho, pero con las cuatro preguntas juntas (incumple el método). Correcciones: hay **dos** conexiones (portátil → nginx y nginx → `labweb`), no se «recoge un fichero»; `location /` es prefijo y atrapa todas las rutas; el 80 lo pone curl por `http://`; `listen :80;` no es válido (`listen 80;`); `ln -S` ≠ `ln -s`; faltaba `sudo` en `ln`, `nginx -t` y `systemctl reload`. Diagnóstico del `502` completado con ayuda: fragmento `upstream:`, `systemctl status` y `ss` |
| 9 · `odoo.mlozano.dev` y Odoo detrás de nginx | ✅ (parcial) | Hecho, una pregunta cada vez. DNS, gestor cerrado, sitio de nginx, cabeceras y `proxy_mode` comprobados con `curl` y el journal. **No hechas** (precarga HSTS de `.dev`): `web.base.url`, PDF y websocket desde el navegador. Desvío largo para leer `dig +trace` con nomenclatura fija (bloques, línea Received, columnas 1–5). Correcciones del ritual: TTL lo guarda el **resolutor** y lo fija el dueño; DNS only porque con Proxied Cloudflare publica sus IPs y hace de proxy; partes de `dig` = a quién / por quién / qué dato (`dig` es el programa); `NS` da nombres, la `@` hace contestar al autoritativo; en `+trace` faltaba la raíz y **no** hay bloque final del resolutor; `list_db` también bloquea operaciones y sigue dando `200`; `dbfilter` limita, no «muestra»; se pierden nombre, IP y esquema (dos son de la conexión), y faltaba `proxy_mode`; `.dev` está en la precarga HSTS y nginx no escucha en el 443 |

## Estado real del VPS

- **Red:** `eth0`, IPv4 `89.58.45.111/22`, IPv6 `2a03:4000:67:5e2:c456:77ff:fe3a:fc4c/64`, puerta de enlace `89.58.44.1` (virtual VRRP) y `fe80::1`. Configuración estática en `/etc/netplan/50-cloud-init.yaml`, aplicada por systemd-networkd.
- **Escuchando:** SSH en `0.0.0.0:22` y `[::]:22`; **nginx en `0.0.0.0:80` y `[::]:80`** (maestro + 2 *workers*); `labweb` en `127.0.0.1:8080` (accesible desde fuera **solo** a través de nginx); Odoo en `127.0.0.1:8069` (servicio `odoo.service`, permanente); PostgreSQL en `127.0.0.1:5432`, `[::1]:5432` y socket `/var/run/postgresql/.s.PGSQL.5432`. No hay firewall.
- **Kernel:** `6.8.0-146-generic`. Último reinicio de la máquina: 10/10/2026, 16:38; `labweb`, `postgresql@16-main` y `odoo` volvieron solos.
- **Paquetes instalados en el bloque:** `nginx`, `apt-file`, `iputils-tracepath`, `gcc-x86-64-linux-gnu` (+25 dependencias), `libpython3.12-dev`, `libldap-dev`, `libpq-dev`, `binutils`. `bind9-dnsutils` ya estaba instalado.
- **nginx 1.24.0 (Ubuntu)**, instalado con `sudo apt install nginx` el 10/10/2026. Al instalarse arrancó y se habilitó solo, con el sitio `default` (página «Welcome to nginx!» desde `/var/www/html`). Proceso maestro de root (PID 5914, se mantiene en los reload) y *workers* de `www-data`. Logs: `/var/log/nginx/error.log` y `/var/log/nginx/access.log`.
- **DNS (Cloudflare, zona `mlozano.dev`, autoritativos `autumn` y `gannon.ns.cloudflare.com`):** `odoo` `A` `89.58.45.111` y `odoo` `AAAA` `2a03:4000:67:5e2:c456:77ff:fe3a:fc4c`, ambos **DNS only**, TTL Auto (300 s). Ya existía `actual` (Tunnel `finances`, Proxied) hacia un servicio del portátil. La raíz `mlozano.dev` no tiene `A`. Comprobado: autoritativo con `aa`, `1.1.1.1` y `dig -4 +trace` (TLD `.dev` = `ns-tld*.charlestonroadregistry.com`).
- **Sitio `odoo` de nginx:** `/etc/nginx/sites-available/odoo`, enlazado en `sites-enabled/odoo`. `server_name odoo.mlozano.dev;`, `listen 80;`, `listen [::]:80;`, `location /` con `proxy_pass http://127.0.0.1:8069;` y `proxy_set_header` de `X-Forwarded-Host $http_host`, `X-Forwarded-For $proxy_add_x_forwarded_for` y `X-Forwarded-Proto $scheme`. Sin bloque de websocket. `labweb` sigue siendo el sitio por defecto (sin `server_name`, carga antes por orden alfabético). Comprobado: `curl -4 -sI http://odoo.mlozano.dev/web` → `303` con `Location` relativa; el journal de Odoo registra `80.29.79.154`.
- **Sitios de nginx (antes de la Sesión 9):** `sites-enabled/` contenía solo el enlace `labweb -> /etc/nginx/sites-available/labweb`. El enlace `default` se borró con `rm`; el fichero `sites-available/default` sigue intacto. `modules-enabled/` y `conf.d/` vacíos. Contenido de `/etc/nginx/sites-available/labweb`:
  ```
  server {
          listen 80;
          listen [::]:80;
          location / {
                  proxy_pass http://127.0.0.1:8080;
          }
  }
  ```
  Sin `server_name`. Comprobado desde el portátil: `200 OK` con `Server: nginx/1.24.0 (Ubuntu)` y cuerpo de `labweb`; con `labweb` parado, `502 Bad Gateway` y en `error.log` `connect() failed (111: Connection refused) while connecting to upstream`, `upstream: "http://127.0.0.1:8080/"`, `client: 80.29.79.154`. El journal de `labweb` registra `127.0.0.1` y `GET / HTTP/1.0`.
- **wkhtmltox 0.12.6.1-3** (`wkhtmltox_0.12.6.1-3.jammy_amd64.deb`), instalado con `sudo apt install ./…`. Binario en `/usr/local/bin/wkhtmltopdf`. `wkhtmltopdf -V` → `0.12.6.1 (with patched qt)`. Origen para `apt`: `/var/lib/dpkg/status` (instalado desde fichero, sin actualizaciones).
- **6 actualizaciones pendientes** (sin aplicar): `libarchive13t64`, `libopeniscsiusr`, `libpng16-16t64`, `libxml2`, `open-iscsi`, `sudo`.
- **Usuario de sistema `odoo`:** `nologin`, grupo propio, directorio `/var/lib/odoo` (propiedad de `odoo`, para los datos).
- **Rol `odoo` en PostgreSQL:** solo `CREATEDB`. Entra por socket con `peer`; por TCP pide contraseña (no tiene).
- **Código:** `/opt/odoo/src` (renombrado desde `/opt/odoo/odoo`), rama `18.0`, commit `6b45949f`, clon superficial, propiedad de root.
- **`uv 0.12.24`** en `/usr/local/bin`, instalado con `UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1`.
- **Configuración:** `/etc/odoo/odoo.conf`, `root:odoo`, `640` (directorio `/etc/odoo` `root:root 755`). Contiene `[options]`, `http_interface=127.0.0.1`, `addons_path=/opt/odoo/src/addons,/opt/odoo/src/odoo/addons`, `data_dir=/var/lib/odoo` y `admin_passwd` en texto plano (generada con `openssl rand -base64 24`, guardada en el gestor de contraseñas). Desde la Sesión 9, además: `list_db = False` (línea 6), `dbfilter = ^test-db$` (línea 7) y `proxy_mode = True`. Sin `db_*`. Comprobado: el gestor muestra «disabled by the administrator» y `/web/login` da `200` sin selector. Comprobado: `miguel` → `Permission denied`; `odoo` lee.
- **Primera base:** `test-db`, creada desde el gestor por el túnel, sin datos de demostración. Aplicación de Ventas instalada: su instalación arrastró `account_peppol`, que declara la biblioteca `phonenumbers`. Presupuesto `S00021` impreso en PDF con cabecera, logo, estilos y pie. `/var/lib/odoo` contiene `addons/`, `filestore/test-db/` y `sessions/`, todo de `odoo`. Tras `sudo chmod -R g-w,o-rwx /var/lib/odoo`, todo el árbol queda sin escritura para el grupo ni acceso para otros (`filestore` y `test-db`: `rwxr-x---`). Usuario de Odoo: `test-db@correo.es`.
- **Parámetros del sistema de Odoo (en `test-db`):** `report.url` = `http://127.0.0.1:8069` (dirección que usa el VPS para generar los PDF); `web.base.url` = `http://localhost:10000` (valor de la URL del túnel en el portátil; consultado el 11/10/2026, sigue así porque el administrador no ha entrado por nginx).
- **Directorio de datos por defecto** (`/var/lib/odoo/.local`) revisado (vacío, sin `filestore`) y **borrado**.
- **Arranque actual:** servicio `/etc/systemd/system/odoo.service` (`root:root 644`), **activo y habilitado**, reiniciado tras instalar wkhtmltopdf. `[Unit]`: `Description=Odoo service`, `After=` y `Wants=postgresql@16-main.service`. `[Service]`: `User=odoo` (grupo implícito), `ExecStart=/opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin -c /etc/odoo/odoo.conf`, `Type=exec`, `UMask=0027`, `Restart=on-failure`. `[Install]`: `WantedBy=multi-user.target`. `systemd-analyze verify` limpio. Log solo en el journal (sin `--logfile`).
- **Comprobado tras reiniciar la máquina:** PostgreSQL `Starting` 16:38:05 → `Started` 16:38:08 → Odoo `Starting` 16:38:08; Odoo responde por el túnel.
- **Experimento:** con `Wants=`, parar `postgresql@16-main` deja Odoo `active (running)` con errores de conexión; al arrancar PostgreSQL, Odoo funciona solo (la sesión del navegador se cerró).
- **Túnel desde el portátil:** `ssh -N -L 10000:127.0.0.1:8069 vps` (el `8069` del portátil lo ocupa un contenedor). Navegador: `http://localhost:10000`.
- **Entorno:** `/opt/odoo/venv`, creado con `sudo uv venv --python /usr/bin/python3`; propiedad de root. 65 librerías instaladas (`psycopg2` y `python-ldap` compiladas), más `phonenumbers` instalada con `sudo uv pip install --python /opt/odoo/venv/bin/python phonenumbers`. `odoo-bin --version` → `Odoo Server 18.0`. `odoo` no puede escribir en código ni entorno (comprobado).

## Para actualizar `progreso.md` al cerrar el bloque

- Consola VNC de Netcup **probada y funcionando** (pendiente del Bloque 0 y del Bloque 2).
- `miguel` tiene contraseña (`P`, puesta el 11/09).
- Las 28 actualizaciones de «Temas aplazados» **ya se aplicaron**: `apt upgrade` de `miguel` el 07/10/2026 y `unattended-upgrade` diario. Quitar ese pendiente del Bloque 4.
- `unattended-upgrade` ya está activo por defecto: el Bloque 4 debe entenderlo y configurarlo, no activarlo.
- Pendiente de `bind9-dnsutils` resuelto: ya estaba instalado.
- `squashfs-tools` huérfano (probable resto de `snapd`); sin tocar.
- Decisiones: `uv` en lugar de `venv`+`pip`; Python del sistema (no uno gestionado por `uv`); `psycopg2` compilado, **no** `psycopg2-binary`; código y entorno de root, datos de `odoo`.
- Para el Bloque 4: `uv` no se actualiza con `apt` (`sudo uv self update`).
- Decisiones de la Sesión 5: configuración en `/etc/odoo/odoo.conf` con `root:odoo 640`; `data_dir` explícito en `/var/lib/odoo`; `addons_path` explícito; contraseña maestra en texto plano hasta la Sesión 9.
- Shell de `miguel` en el VPS: `fish`; `ls` es un alias de un sustituto con iconos (probablemente `eza`); para la salida estándar, `command ls`. Con `sudo`, `ls` a secas (`sudo command ls` falla). Umask de la shell: `0002`.
- Decisiones de la Sesión 6: `Wants=` (no `Requires=`) sobre `postgresql@16-main`; `Type=exec`; `UMask=0027` y `chmod` de lo existente; sin `--logfile`; `KillMode=mixed` aplazado.
- `odoo.service` es el servicio que se matará en el Bloque 5 y vigilará el healthcheck (Artefacto 2).
- Decisiones de la Sesión 7: build oficial `wkhtmltox 0.12.6.1-3` (jammy amd64) instalado desde fichero, fuera de `apt`. Razón: el wiki oficial de Odoo recomienda esa versión desde Odoo 16; el build de Ubuntu no lleva Qt parcheado y no pone cabecera ni pie. `report.url` = `http://127.0.0.1:8069` para que los PDF se generen con recursos alcanzables desde el VPS.
- Dependencia de `account_peppol` (Ventas): `phonenumbers` instalada a mano en el entorno de Odoo. Anotar en la guía de reinstalación.
- Decisiones de la Sesión 8: ensayo del proxy con `labweb` y no con Odoo (el gestor de bases quedaría expuesto antes de cerrar la seguridad, y se mezclarían fallos de nginx y de Odoo); `proxy_pass` a `127.0.0.1` y no a `localhost` (`localhost` resuelve también a `::1`, donde no escucha nadie); sitio `default` desactivado, no borrado.
- **Pregunta aparcada para Redes · Bloque 5:** ¿cómo recibe el servicio de detrás la IP real del visitante? `labweb` ve `127.0.0.1`, aunque nginx sí conoce la IP real (aparece como `client:` en `error.log`). Contexto relacionado: nginx habla HTTP/1.0 con el servicio de detrás y responde al cliente en HTTP/1.1 con `Transfer-Encoding: chunked`.
- IP pública de casa vista por el VPS el 11/10/2026: `80.29.79.154` (puede cambiar).
- Decisiones de la Sesión 9: Odoo en **`odoo.mlozano.dev`**, no en la raíz (la raíz queda para la web o el portfolio); registros en DNS only; sitio nuevo con `server_name` y `labweb` intacto como sitio por defecto; `list_db = False` y `dbfilter = ^test-db$` (una sola base); cabeceras `X-Forwarded-*` más `proxy_mode = True`. Del ejemplo de *Deploying Odoo* quedan fuera, hasta HTTPS, `add_header Strict-Transport-Security` y `proxy_cookie_flags … secure`; `proxy_pass http://odoo` no aplica (no hay `upstream`).
- La pregunta aparcada sobre la IP real tiene respuesta práctica (cabeceras + `proxy_mode`); el fondo de `X-Forwarded-*` sigue en Redes · Bloque 5.
- Hallazgo: Odoo 18 redirige con `Location` relativa; la redirección a `127.0.0.1:8069` que preveía el plan no se reproduce. El problema real está en `web.base.url`.

## Pendientes abiertos

- **Sesión 10:** comprobar desde el navegador lo que la 9 no pudo: `web.base.url` = `https://odoo.mlozano.dev` tras entrar como administrador (consulta con `psql`), PDF con estilos (`report.url` sigue en `http://127.0.0.1:8069`) y notificaciones en vivo.
- **Sesión 10:** bloque `location /websocket` en el sitio de Odoo (con `workers = 0` va al mismo 8069; cabeceras `Upgrade`/`Connection`, fondo en Redes · Bloque 5).
- **Sesión 10:** cambiar la contraseña del administrador de `test-db` (se usó por `http` en una prueba previa al certificado) y pasar `admin_passwd` a hash.
- **Sesión 10:** añadir, ya con HTTPS, `Strict-Transport-Security` y `proxy_cookie_flags session_id samesite=lax secure` si certbot no lo hace.
- **Para los apuntes:** las cabeceras de la respuesta del gestor y el `303` del selector sin `dbfilter` no se reprodujeron; constan como descripción.
- **Sesión 11 (guía de reinstalación):** anotar que `wkhtmltox` viene de un fichero y no de `apt`; que `phonenumbers` es dependencia de `account_peppol`; y el parámetro `report.url`.
- **Bloque 4:** `wkhtmltox` fuera de las actualizaciones automáticas, y anotar que el proyecto está archivado. Existen alternativas de terceros (Fast PDF Reports, OrbitPDF, TemplateTo) que no se han evaluado; TemplateTo envía el HTML de los informes a un servicio externo.
- **Bloque 5:** el flujo interno de impresión de PDF y cómo diagnosticar sus fallos. El log no separa el tráfico de wkhtmltopdf del tráfico del túnel, así que `grep 127.0.0.1` no sirve para probarlo. En la Sesión 7 el aviso de «no encontrar wkhtmltopdf» persistió con el estado en `ok`; la causa no quedó confirmada.
- **Cuando se configuren workers:** añadir `KillMode=mixed` (tomado de la unit Debian de Odoo).
- Opcional: con una sesión iniciada en Odoo, ver con `sudo ss -tnp` el par `sshd` ↔ `python` en `127.0.0.1:8069`.
- Para los apuntes: el nombre exacto del error de conexión durante el corte (`journalctl -u odoo -S ... | grep -i error`) no se anotó.

## Método acordado (además de las instrucciones del proyecto)

- **Ritmo lento:** un paso cada vez; no anticipar herramientas o paquetes antes de que el problema los pida. En las correcciones, también una a una.
- Cuando no sepa elegir entre opciones por falta de experiencia, dar una recomendación justificada en lugar de insistir con la pregunta. Si pide un comando que no recuerda tras un intento, darlo.
- Comandos básicos de herramientas nuevas: darlos directamente con la explicación de cada parte. Dejar que formule cuando haya una decisión (opciones, directivas, filtros).
- Enseñar **qué mirar y cómo interpretar** cada salida antes de dar la conclusión.
- Marcar en una línea lo que sea contexto no necesario; no convertirlo en ejercicio.
- Ritual de cierre: una pregunta cada vez, no todas juntas.
- Si cito documentación, dar la URL exacta y el apartado.
- **Precisión al señalar:** cuando en un fichero haya varias líneas candidatas (por ejemplo, cuatro `include`), decir exactamente cuál y por qué las demás no; no «mira la línea `include`».
- **Antes de pedir una acción, decir qué estamos mirando y para qué.** No encadenar el paso siguiente sin cerrar el actual.
- **Referencias en el ritual:** el usuario no usa `man` (dice que no encuentra lo que busca). Pedirle la referencia como apartado de la documentación oficial o capítulo del libro, no como página de `man`.
- **Nomenclatura fija:** al leer una salida larga, definir antes los términos (bloque 0, 1…; línea Received; columnas 1–5) y usarlos siempre igual. Las preguntas cortas encadenadas funcionan solo con esa base.
- **Re-anclar:** si el usuario dice que no sabe qué estamos haciendo, parar y dar la tabla de dónde estamos y para qué sirve el paso. Explicar qué sucede y por qué **antes** de pedir comandos de una parte nueva.
- **No predecir sin verificar:** en la Sesión 9 fallaron dos predicciones (redirección a `127.0.0.1`, código del gestor con `list_db = False`). Decir «debería» solo con la fuente delante, o plantearlo como hipótesis.
- **Desvíos fuera de los apuntes de sesión:** lo que resuelve dudas de otra rama va a esa rama, en su sitio, no al final.

## Siguiente: Sesión 10 · HTTPS con certbot

Dónde: VPS (terminal SSH); portátil (navegador y terminal).

Problema: el navegador no abre `odoo.mlozano.dev`. `.dev` está en la precarga HSTS, así que fuerza `https://` y en el 443 no escucha nadie. Las tres comprobaciones de la Sesión 9 que necesitan navegador están bloqueadas por esto. La herramienta habitual, certbot, recomienda instalarse con snap, y **`snapd` está purgado** desde el Bloque 1: hay que elegir otra vía. Y certbot va a modificar el sitio de nginx: quieres saber exactamente qué ha cambiado.

Bibliografía:
- Documentación de certbot → obtener certificados con el plugin de nginx y renovación.
- *The Linux Command Line* cap. 14 → instalar certbot y su plugin desde los repositorios de Ubuntu.
- Apuntes del Bloque 2 de Linux, sección de timers → cómo se renueva solo.
- Odoo 18, *Deploying Odoo* → «HTTPS» (comparar con lo que deje certbot; las líneas de HSTS y cookie `secure` entran ahora) y «Builtin server» (websocket).
- *Grigorik* cap. 4 y documentación de Let's Encrypt sobre el reto HTTP-01 → **no ahora**: Redes · Bloque 4.

Objetivos para darla por superada:
- `https://odoo.mlozano.dev` muestra el candado y `curl -I` a `http://` devuelve un `301` a `https://`.
- Copia del sitio `odoo` antes de certbot y `diff` con el de después, cada línea marcada como «la entiendo» o «aparcada para Redes 4/5».
- El timer de renovación aparece en `systemctl list-timers` y una renovación de prueba termina bien.
- Sabes dónde están el certificado y la clave privada, y `miguel` no puede leer la clave.
- Tras entrar como administrador, `web.base.url` = `https://odoo.mlozano.dev` (consulta con `psql`).
- Un PDF sale con estilos (`report.url` sigue en `http://127.0.0.1:8069`).
- Bloque `location /websocket` añadido y notificaciones en vivo funcionando.
- Contraseña del administrador de `test-db` cambiada; `admin_passwd` en hash.

Al empezar el chat: mapa corto de piezas (certificado y clave, certbot y su plugin de nginx, bloque `listen 443 ssl`, redirección 80 → 443, timer de renovación, `X-Forwarded-Proto` = `https`, websocket), una línea cada una, según el método.
