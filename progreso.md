# Progreso · Roadmap Backend + Infra · Año 1

**Última actualización:** 12/10/2026

> **Para Claude:** este fichero es la única fuente de verdad sobre dónde estoy. Cómo se lee y cómo se actualiza está en las instrucciones del proyecto.

Leyenda: ✅ cerrado · 🟡 en curso · ⏸ en pausa · ⬜ sin empezar · ❓ por confirmar

---

## Ahora

| | |
|---|---|
| Última sesión de carril | Linux y VPS · Bloque 3, Sesión 10 (11–12/10/2026) |
| Siguiente carril | Redes · Bloque 4 (sin plan todavía: se genera al empezar) |
| Rotación | Linux y VPS ↔ Redes. PostgreSQL entra al terminar Learn SQL de Boot.dev |
| Boot.dev | Ruta backend (Python), capítulo 9: Learn Data Structures and Algorithms (86/127). Siguiente: capítulo 16, Learn SQL (95 lecciones), adelantado; después se retoma el orden en el capítulo 10 |
| Viernes | Código fuente de Odoo (H3 cumplido) |

## Hitos para jueves y viernes

Hasta que se cumpla H1, el jueves es día de carril. Desde H3, el viernes es para el código de Odoo.

| Hito | Se activa con | Jueves y viernes pasan a | Estado |
|---|---|---|---|
| H1 | Cierre de Linux · Bloque 3 | Artefacto 2: healthcheck de Odoo con aviso por Telegram, con Git en serio desde el primer commit | ⬜ |
| H2 | Inicio de Linux · Bloque 4 | Artefacto 1: script de backup de la base y el *filestore* (es el backup automatizado del Bloque 4) | ⬜ |
| H3 | Closures y decoradores terminados en Boot.dev | El viernes, lectura del código de Odoo: `odoo/api.py` y después `odoo/models.py` | ✅ 12/10/2026 |
| H4 | Inicio del Q2 (01/12/2026) | Proyecto propio: mes 1, diseño | ⬜ |

El Artefacto 3 (algo del trabajo que dé rabia hacer a mano) queda libre desde H1, cuando surja una tarea concreta.

---

## Linux y VPS

| Bloque | Estado | Cierre | Apuntes |
|---|---|---|---|
| 0 · El servidor existe | ✅ | 11/09/2026 | `linux-bloque-0.md` |
| 1 · El sistema por dentro | ✅ | 24/09/2026 | `linux-bloque-1.md` |
| 2 · systemd de verdad | ✅ | 03/10/2026 | `linux-bloque-2.md` |
| 3 · Odoo 18 desplegado a mano | 🟡 | | `linux-bloque-3.md` (en curso) |
| 4 · Que no se lo lleve nadie | ⬜ | | |
| 5 · Romperlo | ⬜ | | |

**Bloque en curso: 3 · Odoo 18 desplegado a mano.** Plan en `linux/linux-bloque-3-plan.md`; estado de la máquina en `linux/vps-inventario.md`.

| Sesión | Estado |
|---|---|
| 1 a 9 | ✅ |
| 10 · HTTPS con certbot | 🟡 Certificado, redirección, renovación y websocket hechos. Falta el endurecimiento (ver «Urgente») |
| 11 · Notas de reinstalación y `vps-setup` | ⬜ |
| 12 · Reinstalación (criterio de cierre) | ⬜ |

Entregable del trimestre «VPS con Odoo desplegado a mano y HTTPS»: cumplido. Faltan los backups (Bloque 4).

---

## Redes

| Bloque | Estado | Cierre | Apuntes |
|---|---|---|---|
| 1 · El modelo y las capas | ✅ | | `redes-bloque-1.md` |
| 2 · DNS | ✅ | 28/09/2026 | `redes-bloque-2.md` |
| 3 · HTTP | ✅ | 08/10/2026 | `redes-bloque-3.md` |
| 4 · TLS | ⬜ | | |
| 5 · El reverse proxy | ⬜ | | |

---

## PostgreSQL

| Bloque | Estado | Cierre | Apuntes |
|---|---|---|---|
| 0 · Que la base de datos exista | ✅ | 13/09/2026 | `postgresql-bloque-0.md` |
| 1 · SQL sólido | ⏸ | | `postgresql-bloque-1.md` |
| 2 · El modelo relacional | ⏸ Lo cubre Boot.dev (Learn SQL) | | |
| 3 · Índices | ⏸ Lo cubre Boot.dev; repaso en PostgreSQL al volver | | |
| 4 · Leer planes de ejecución | ⬜ Primer bloque al volver a la rotación | | |
| 5 · El ORM de Odoo bajo el capó | ⬜ | | |

En pausa hasta terminar Learn SQL de Boot.dev (capítulo 16, adelantado para hacerlo justo después de algoritmos).

---

## Código de Odoo · viernes

| Bloque | Estado | Cierre | Apuntes |
|---|---|---|---|
| 1 · `odoo/api.py` y `odoo/models.py` | ⬜ Sin plan todavía: se genera el primer viernes | | |

Del roadmap: en `api.py`, cómo están implementados `@api.depends` y `@api.model` (closures reales); en `models.py`, `search` y `browse`.

---

## Pendientes

Lista única. Cada pendiente lleva su destino; se borra al resolverse.

### Urgente (antes de seguir con cualquier carril)

- **Resto de la Sesión 10 de Linux** (detalle en el plan del Bloque 3): contraseña del administrador de `test-db` (viajó por `http`), contraseña maestra nueva (la actual quedó escrita en un chat) con `admin_passwd` en hash, y HSTS más cookie `secure` en nginx. Al terminar, completar «Pendiente de completar» en `vps-setup/odoo.md`.

### Linux · Bloque 3

- Para los apuntes: el nombre exacto del error de conexión durante el corte de PostgreSQL no se anotó (`journalctl -u odoo` con filtro de tiempo y `grep -i error`). Las cabeceras del gestor y el `303` del selector sin `dbfilter` constan como descripción, sin reproducir.
- Opcional: notificaciones en vivo con dos usuarios en dos navegadores (el `101` ya prueba el websocket).
- Opcional: con una sesión iniciada en Odoo, ver con `sudo ss -tnp` el par `sshd` ↔ `python` en `127.0.0.1:8069`.

### Linux · Bloque 4

- Cortafuegos: solo 22, 80 y 443 abiertos; PostgreSQL y Odoo, solo locales. El puerto de SSH lo fija `ssh.socket`, no `sshd_config`.
- `fail2ban`: bots probando usuarios por SSH a diario (rechazados por autenticación solo con clave).
- `unattended-upgrade` ya está activo por defecto: entenderlo y configurarlo, no activarlo. **No ejecutar `do-release-upgrade`** a 26.04: el roadmap está planteado sobre 24.04.
- `uv` no se actualiza con `apt` (`sudo uv self update`).
- `wkhtmltox` está fuera de las actualizaciones automáticas (instalado desde fichero) y el proyecto está archivado. Hay alternativas de terceros sin evaluar (Fast PDF Reports, OrbitPDF, TemplateTo); TemplateTo envía el HTML de los informes a un servicio externo.
- Backup (Artefacto 1): base de datos + *filestore* + `odoo.conf`; decidir qué hacer con `/etc/letsencrypt`.
- Rotar la contraseña de root del VPS: sigue siendo la original de Netcup (no alcanzable por SSH, pero válida por la consola VNC).
- Candidato: endurecimiento de units de systemd (`ProtectSystem=`, `NoNewPrivileges=`, `PrivateTmp=`, `DynamicUser=`).
- `squashfs-tools` huérfano (probable resto de `snapd`).

### Linux · Bloque 5

- Flujo interno de impresión de PDF y cómo diagnosticar sus fallos. El log no separa el tráfico de `wkhtmltopdf` del del túnel, así que `grep 127.0.0.1` no sirve para probarlo. En la Sesión 7 el aviso de «no encontrar wkhtmltopdf» persistió con el estado en `ok`; causa sin confirmar.
- Eliminar `labweb` al cerrar el Bloque 5 (hasta entonces sirve para el Bloque 5 y para probar el healthcheck): `disable --now`, borrar `labweb.service`, `labweb-health.service` y `labweb-health.timer`, `daemon-reload`, `rm -r /opt/labweb`, `userdel labweb`.

### Linux · sin bloque asignado

- Cuando se configuren *workers* en Odoo: `KillMode=mixed` en `odoo.service` y el `proxy_pass` de `location /websocket` al 8072.
- Experimentos opcionales del Bloque 2: ver la activación por socket con `ssh.service` parado; comprobar un `reload` con un `Banner` en `/etc/ssh/sshd_config.d/99-lab.conf` y retirarlo.
- Borrar `~/labweb.service.bak` en el VPS.

### Redes · Bloque 4

- Antes de empezar: terminar Grigorik cap. 12 (*Binary Framing Layer*, *Streams, Messages, and Frames*, *Request and Response Multiplexing*, *Header Compression*), pendiente del Bloque 3.
- Preguntas del `diff` de certbot: qué pasa al abrir una conexión TLS (`ssl`); qué hay en `fullchain.pem` frente a `cert.pem` y `chain.pem`; qué elige `options-ssl-nginx.conf`; para qué sirve `ssl_dhparam`; qué comprueba Let's Encrypt (reto HTTP-01); qué significan los campos de TLS que muestra el navegador (`TLS_AES_128_GCM_SHA256`, TLS 1.3, Certificate Transparency).
- Caso pixeldrain por HTTPS: la conexión TCP se abre y el corte (`Connection reset by peer`, código 35 de `curl`) llega justo después del `Client hello`. Apunta a inspección del SNI y corrige la conclusión del Bloque 2.

### Redes · Bloque 5

- Fondo de las cabeceras `X-Forwarded-*` (la parte práctica quedó resuelta con `proxy_mode`).
- Por qué `Upgrade` y `Connection` son *hop-by-hop*.
- El *buffering* de nginx y cuándo estorba.
- `ipv6only=on`; el `if` redundante y el `return 404` del bloque del puerto 80 que dejó certbot.
- nginx habla HTTP/1.0 con el servicio de detrás y responde al cliente en HTTP/1.1 con `Transfer-Encoding: chunked`.

### Redes · opcionales

- `labweb` en HTTP/1.1 (`protocol_version`), primero sin `Content-Length` y después con ella, con copia previa de `labweb.py` y revirtiendo al acabar.
- Experimento de TTL con `prueba.mlozano.dev` → `192.0.2.1`, TTL 300, y cambio posterior, observando al autoritativo, `1.1.1.1` y `8.8.8.8`. No consultar el nombre antes de crearlo (caché negativa).
- Dos IP locales distintas en casa (`192.168.1.74` y `192.168.17.250`): revisar con `ip a` e `ip r` si hay dos redes (principal e invitados) o un repetidor.

### PostgreSQL · al volver a la rotación

- Repaso de índices en PostgreSQL (Boot.dev los ve sobre SQLite).
- Rehacer `postgresql-bloque-0.md` y `postgresql-bloque-1.md` al formato de tres partes, integrando lo de Boot.dev y `00-sql-sintaxis-y-comportamiento.md`.
- Criterio de cierre del Bloque 1: repaso en voz alta de `WHERE` frente a `HAVING`, `GROUP BY` frente a `PARTITION BY` y por qué `HAVING` no ve los alias del `SELECT`. Practicar `LAG()` y `LEAD()`.

### Casa y cuentas

- Mejoras del router propuestas y no aplicadas: contraseña de administración, desactivar WPS, revisar la redirección de puertos, valorar desactivar UPnP, comprobar WPA2/WPA3 y red de invitados. De una en una, apuntando el valor anterior.
- Tras el próximo reinicio del router, comprobar que conserva los DNS de Quad9.
- Comprobar que Gmail tiene 2FA: es el último eslabón de la cadena Gmail → GitHub → Cloudflare → `mlozano.dev`.

### Ideas de proyecto

- VPN propia con WireGuard, después de Linux · Bloque 4. Detalle en `ideas-proyectos.md`.
- Personal Project 1 de Boot.dev (capítulo 12): se decide juntos al llegar. Requisito: relacionado con lo estudiado y, si encaja, usando el VPS. Candidatos: uno de los artefactos o una primera versión del proyecto propio del Q2. No sustituye al proyecto propio del roadmap (H4).
