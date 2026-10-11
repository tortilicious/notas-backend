# Linux/VPS · Bloque 3 · Estado para continuar en un chat nuevo

> **Para Claude:** pega esto como contexto. `progreso.md` **no** está actualizado con el Bloque 3 por decisión propia: se actualiza al cerrar el bloque con los datos de este fichero. El plan de sesiones está en `linux-bloque-3-plan.md` y los apuntes de lo hecho, en `linux-bloque-3.md`.

## Dónde estoy

- **Bloque 3 · Odoo 18 desplegado a mano:** 🟡 en curso. Sesiones 1 a 8 completadas (la 8, el 11/10/2026). **Siguiente: Sesión 9 · `mlozano.dev` y Odoo detrás de nginx.**
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

## Estado real del VPS

- **Red:** `eth0`, IPv4 `89.58.45.111/22`, IPv6 `2a03:4000:67:5e2:c456:77ff:fe3a:fc4c/64`, puerta de enlace `89.58.44.1` (virtual VRRP) y `fe80::1`. Configuración estática en `/etc/netplan/50-cloud-init.yaml`, aplicada por systemd-networkd.
- **Escuchando:** SSH en `0.0.0.0:22` y `[::]:22`; **nginx en `0.0.0.0:80` y `[::]:80`** (maestro + 2 *workers*); `labweb` en `127.0.0.1:8080` (accesible desde fuera **solo** a través de nginx); Odoo en `127.0.0.1:8069` (servicio `odoo.service`, permanente); PostgreSQL en `127.0.0.1:5432`, `[::1]:5432` y socket `/var/run/postgresql/.s.PGSQL.5432`. No hay firewall.
- **Kernel:** `6.8.0-146-generic`. Último reinicio de la máquina: 10/10/2026, 16:38; `labweb`, `postgresql@16-main` y `odoo` volvieron solos.
- **Paquetes instalados en el bloque:** `nginx`, `apt-file`, `iputils-tracepath`, `gcc-x86-64-linux-gnu` (+25 dependencias), `libpython3.12-dev`, `libldap-dev`, `libpq-dev`, `binutils`. `bind9-dnsutils` ya estaba instalado.
- **nginx 1.24.0 (Ubuntu)**, instalado con `sudo apt install nginx` el 10/10/2026. Al instalarse arrancó y se habilitó solo, con el sitio `default` (página «Welcome to nginx!» desde `/var/www/html`). Proceso maestro de root (PID 5914, se mantiene en los reload) y *workers* de `www-data`. Logs: `/var/log/nginx/error.log` y `/var/log/nginx/access.log`.
- **Sitios de nginx:** `sites-enabled/` contiene solo el enlace `labweb -> /etc/nginx/sites-available/labweb`. El enlace `default` se borró con `rm`; el fichero `sites-available/default` sigue intacto. `modules-enabled/` y `conf.d/` vacíos. Contenido de `/etc/nginx/sites-available/labweb`:
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
- **Configuración:** `/etc/odoo/odoo.conf`, `root:odoo`, `640` (directorio `/etc/odoo` `root:root 755`). Contiene `[options]`, `http_interface=127.0.0.1`, `addons_path=/opt/odoo/src/addons,/opt/odoo/src/odoo/addons`, `data_dir=/var/lib/odoo` y `admin_passwd` en texto plano (generada con `openssl rand -base64 24`, guardada en el gestor de contraseñas). Sin `db_*`. Comprobado: `miguel` → `Permission denied`; `odoo` lee.
- **Primera base:** `test-db`, creada desde el gestor por el túnel, sin datos de demostración. Aplicación de Ventas instalada: su instalación arrastró `account_peppol`, que declara la biblioteca `phonenumbers`. Presupuesto `S00021` impreso en PDF con cabecera, logo, estilos y pie. `/var/lib/odoo` contiene `addons/`, `filestore/test-db/` y `sessions/`, todo de `odoo`. Tras `sudo chmod -R g-w,o-rwx /var/lib/odoo`, todo el árbol queda sin escritura para el grupo ni acceso para otros (`filestore` y `test-db`: `rwxr-x---`). Usuario de Odoo: `test-db@correo.es`.
- **Parámetros del sistema de Odoo (en `test-db`):** `report.url` = `http://127.0.0.1:8069` (dirección que usa el VPS para generar los PDF); `web.base.url` = `http://localhost:10000` (valor de la URL del túnel en el portátil).
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

## Pendientes abiertos

- **Sesión 9:** contraseña maestra cifrada o en texto plano; gestor de bases activo o desactivado; `dbfilter`/`db_name`.
- **Sesión 9:** con nginx delante, `web.base.url` pasará a ser `https://mlozano.dev`. Revisar `report.url`: debe seguir en `http://127.0.0.1:8069` mientras el PDF se genere en el VPS.
- **Sesión 9:** con nginx delante, Odoo verá las peticiones `from 127.0.0.1` igual que con el túnel.
- **Sesión 9:** el sitio `labweb` ocupa hoy el puerto 80 y atiende cualquier nombre (no tiene `server_name`). Decidir si Odoo va en un sitio nuevo con `server_name mlozano.dev` (y qué se hace con `labweb`) o sustituyendo el `proxy_pass`.
- **Sesión 9:** `labweb` es accesible desde Internet por el puerto 80 hasta entonces. No tiene riesgo, pero recordarlo.
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

## Siguiente: Sesión 9 · `mlozano.dev` y Odoo detrás de nginx

Dónde: Cloudflare en el navegador; VPS (terminal SSH); portátil (terminal y navegador).

Problema: `http://mlozano.dev` no lleva a ningún sitio porque no hay registros. Una vez creados y con nginx apuntando a Odoo, aparece un fallo típico: al iniciar sesión, el navegador salta a `127.0.0.1:8069` y la página no carga. Además, en cuanto Odoo es alcanzable desde Internet, el gestor de bases de datos también lo es: **la seguridad se cierra antes de exponer**.

Bibliografía:
- Documentación de Cloudflare sobre registros DNS → `A` y `AAAA` en modo «DNS only» (nube gris).
- Apuntes de Redes · Bloque 2 → comprobar con `dig` contra el autoritativo y contra un resolutor; `dig -4 +trace` para la delegación. (No usa `man`: dar apartados de los apuntes o de la documentación.)
- Odoo 18, *Deploying Odoo* → «HTTPS» (ejemplo de nginx, hoy sin las líneas de certificado), «Builtin server» (websocket y `proxy_mode`) y «Security» (contraseña maestra, `list_db`, `dbfilter`).
- *Lectura de contexto opcional:* *Deploying Odoo*, cálculo de *workers*. Hoy basta con `workers = 0`.
- *Grigorik* caps. 13 y 17 → **no ahora**: Redes · Bloque 5.

Objetivos para darla por superada:
- `dig` contra el autoritativo de Cloudflare y contra `1.1.1.1` devuelve `89.58.45.111` para `A` y la IPv6 del VPS para `AAAA`, y la traza muestra la delegación de `.dev` a Cloudflare.
- Has reproducido una vez la redirección a `127.0.0.1` y sabes qué línea (de nginx y de `odoo.conf`) la corrige.
- Desde el navegador del portátil, `http://mlozano.dev` muestra Odoo y la URL sigue siendo `mlozano.dev` después de iniciar sesión.
- El journal de Odoo registra tu IP pública real, no `127.0.0.1`.
- El gestor de bases de datos ya no es accesible desde fuera.
- Los PDF siguen saliendo con estilos (`report.url` en `http://127.0.0.1:8069`).
- Cada línea de la configuración de nginx que no sepas explicar está en las preguntas aparcadas.

Al empezar el chat: dar primero el mapa corto de piezas (registros `A`/`AAAA`, `server_name`, `proxy_mode`, cabeceras de proxy, `location` del websocket, `list_db`/`dbfilter`, `web.base.url`), una línea cada una, según el método.
