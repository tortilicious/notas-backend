# Inventario de `backend-lab`

**Estado a:** 13/10/2026

> Solo el estado actual de la máquina. Cuando algo cambia, se sobrescribe la línea; sin historial. Cómo se monta está en `vps-setup`; por qué, en los apuntes. Sin secretos: solo dónde viven.

## Máquina

| Pieza | Valor |
|---|---|
| Proveedor | Netcup VPS 500 G12 (2 vCore, 4 GB, 128 GB NVMe), Núremberg |
| Sistema | Ubuntu 24.04 LTS minimal, UEFI amd64 |
| Hostname | `backend-lab` |
| Kernel | `6.8.0-146-generic` |
| Último reinicio | 10/10/2026, 16:38. `labweb`, `postgresql@16-main` y `odoo` volvieron solos |
| Target por defecto | `multi-user.target` |
| Paquetes retirados | `snapd`, purgado por completo |
| Actualizaciones | `unattended-upgrade` activo por defecto. 6 pendientes a 12/10: `libarchive13t64`, `libopeniscsiusr`, `libpng16-16t64`, `libxml2`, `open-iscsi`, `sudo` |
| Vía de recuperación | Consola VNC del panel de Netcup, probada y funcionando |

## Acceso

| Pieza | Valor |
|---|---|
| Usuario | `miguel`, en los grupos `sudo` y `systemd-journal`. Tiene contraseña (para `sudo`), guardada en el gestor |
| Shell | `fish` (código de salida en `$status`). `ls` es un alias con iconos: para la salida estándar, `command ls`; con `sudo`, `ls` a secas. Umask `0002` |
| Root | Sin acceso por SSH. Contraseña original de Netcup, válida solo por VNC |
| SSH | `PermitRootLogin no`, `PasswordAuthentication no`, `KbdInteractiveAuthentication no`. Puerto 22 abierto por `ssh.socket` |
| Clave | ed25519, alias `vps` en `~/.ssh/config` del portátil (`IdentityFile` e `IdentitiesOnly`) |
| Terminal | Descripción de Ghostty instalada a nivel de sistema (`sudo less`, `sudo vim` y `sudo nano` funcionan) |

## Red

| Pieza | Valor |
|---|---|
| Interfaz | `eth0` |
| IPv4 | `89.58.45.111/22`, puerta de enlace `89.58.44.1` (virtual VRRP) |
| IPv6 | `2a03:4000:67:5e2:c456:77ff:fe3a:fc4c/64`, puerta de enlace `fe80::1` |
| Configuración | Estática en `/etc/netplan/50-cloud-init.yaml`, aplicada por systemd-networkd |
| Cortafuegos | Ninguno |

**Qué escucha:**

| Servicio | Dónde |
|---|---|
| SSH | `0.0.0.0:22`, `[::]:22` |
| nginx | `0.0.0.0:80`, `[::]:80`, `0.0.0.0:443`, `[::]:443` |
| `labweb` | `127.0.0.1:8080` (desde fuera, solo a través de nginx) |
| Odoo | `127.0.0.1:8069` |
| PostgreSQL | `127.0.0.1:5432`, `[::1]:5432` y socket `/var/run/postgresql/.s.PGSQL.5432` |

## DNS (Cloudflare, zona `mlozano.dev`)

| Registro | Valor | Modo |
|---|---|---|
| `odoo` `A` | `89.58.45.111` | DNS only, TTL Auto (300 s) |
| `odoo` `AAAA` | `2a03:4000:67:5e2:c456:77ff:fe3a:fc4c` | DNS only, TTL Auto (300 s) |
| `actual` | Tunnel `finances` hacia un servicio del portátil | Proxied (no es del VPS) |

La raíz `mlozano.dev` no tiene `A`. Autoritativos: `autumn` y `gannon.ns.cloudflare.com`.

## Servicios de systemd propios

| Unit | Fichero | Estado |
|---|---|---|
| `odoo.service` | `/etc/systemd/system/odoo.service` (`root:root 644`) | Activo y habilitado. `After=` y `Wants=postgresql@16-main.service`, `User=odoo`, `Type=exec`, `UMask=0027`, `Restart=on-failure`. Log solo en el journal |
| `labweb.service` | `/etc/systemd/system/labweb.service` | Activo y habilitado. `Type=exec`, `Restart=on-failure`, `RestartSec=2`, `PYTHONUNBUFFERED=1`. Script en `/opt/labweb/labweb.py` (root, `644`), usuario de sistema `labweb` |
| `labweb-health.service` y `.timer` | `/etc/systemd/system/` | Timer **deshabilitado** |
| `certbot.timer` | `/usr/lib/systemd/system/` (de paquete) | Activo. Dos veces al día con retraso aleatorio; lanza `certbot -q renew` |

Sin drop-ins. Sin tareas en el crontab de `miguel`.

## PostgreSQL

| Pieza | Valor |
|---|---|
| Versión | 16, clúster `16/main`, unit `postgresql@16-main.service` |
| Rol `odoo` | Solo `CREATEDB`. Entra por socket con `peer`; por TCP pide contraseña (no tiene) |
| Bases | `test-db` (Odoo, sin datos de demostración) |

## Odoo

| Pieza | Valor |
|---|---|
| Código | `/opt/odoo/src`, rama `18.0`, commit `6b45949f`, clon superficial, propiedad de root |
| Entorno | `/opt/odoo/venv`, creado con `uv` sobre el Python del sistema, propiedad de root. `psycopg2` y `python-ldap` compilados; `phonenumbers` añadida a mano (dependencia de `account_peppol`) |
| `uv` | `0.12.24` en `/usr/local/bin` (no se actualiza con `apt`) |
| Configuración | `/etc/odoo/odoo.conf`, `root:odoo 640` (directorio `root:root 755`). Claves: `http_interface=127.0.0.1`, `addons_path`, `data_dir=/var/lib/odoo`, `list_db = False`, `dbfilter = ^test-db$`, `proxy_mode = True`, `admin_passwd` (⚠️ en texto plano y comprometida: pendiente de cambio y hash) |
| Datos | `/var/lib/odoo` (`addons/`, `filestore/test-db/`, `sessions/`), todo de `odoo`, sin escritura para el grupo ni acceso para otros |
| Usuario de sistema | `odoo`, `nologin`, grupo propio, home `/var/lib/odoo` |
| Aplicaciones en `test-db` | Ventas (arrastró `account_peppol`) |
| Parámetros del sistema | `report.url` = `http://127.0.0.1:8069`; `web.base.url` = `https://odoo.mlozano.dev` |
| Secretos | Contraseña maestra y del administrador de `test-db`: en el gestor de contraseñas |
| Túnel desde el portátil | `ssh -N -L 10000:127.0.0.1:8069 vps` y `http://localhost:10000` (el 8069 del portátil lo ocupa un contenedor) |

## PDF

`wkhtmltox 0.12.6.1-3` (build jammy amd64 con Qt parcheado), instalado desde fichero con `apt install ./…`, fuera de las actualizaciones automáticas. Binario en `/usr/local/bin/wkhtmltopdf`.

## nginx

| Pieza | Valor |
|---|---|
| Versión | 1.24.0 (Ubuntu). Maestro de root y *workers* de `www-data` |
| Logs | `/var/log/nginx/error.log` y `/var/log/nginx/access.log` |
| Protocolo con el navegador | HTTP/2 en el 443 (ALPN `h2`); el websocket va por HTTP/1.1. Hacia Odoo, HTTP/1.0, salvo `/websocket` (1.1) |
| Sitios habilitados | `labweb` (por defecto, sin `server_name`, `proxy_pass http://127.0.0.1:8080`) y `odoo` |
| Sitio `default` | Desactivado (enlace borrado); `sites-available/default` intacto |
| Sitio `odoo` | `/etc/nginx/sites-available/odoo`. `map` para el websocket; bloque del 443 con certificado y `http2` en sus dos `listen`, `Strict-Transport-Security` (un año, `includeSubDomains`), `proxy_cookie_flags session_id samesite=lax secure`, `location /` y `location /websocket` (`proxy_http_version 1.1`); bloque del 80 con `301` a `https://` |

## Certificado

| Pieza | Valor |
|---|---|
| Dominio | `odoo.mlozano.dev`, Let's Encrypt, emitido el 11/10/2026 (caduca hacia el 09/01/2027) |
| Herramienta | certbot 2.9.0 con `python3-certbot-nginx`, desde `apt` |
| Ficheros | `/etc/letsencrypt/live/odoo.mlozano.dev/` (enlaces a `archive/`), solo root. Ficha en `renewal/odoo.mlozano.dev.conf` |
| Log | `/var/log/letsencrypt/letsencrypt.log` |
| Renovación | `certbot.timer`; `sudo certbot renew --dry-run` correcto |

## Paquetes instalados a mano (además de la base)

`nginx`, `certbot`, `python3-certbot-nginx`, `apt-file`, `iputils-tracepath`, `bind9-dnsutils`, `gcc-x86-64-linux-gnu`, `libpython3.12-dev`, `libldap-dev`, `libpq-dev`, `binutils`, PostgreSQL 16. Fuera de `apt`: `wkhtmltox` y `uv`.

## Copias previas en la home de `miguel`

| Fichero | Qué es |
|---|---|
| `~/odoo.nginx.antes-certbot` | Sitio `odoo` de nginx antes de certbot |
| `~/labweb.service.bak` | Copia antigua de `labweb.service` (pendiente de borrar) |
