# Progreso · Roadmap Backend + Infra · Año 1

**Última actualización:** 12/10/2026

> **Para Claude:** este archivo es la fuente de verdad sobre dónde estoy. Léelo al empezar cada conversación. Si pregunto algo que corresponde a un bloque posterior al que está «en curso» en su carril, avísame y recuérdame cuándo lo veremos. Al cerrar un bloque o una sesión relevante, ofréceme la versión actualizada de este archivo. La sección «Aplicación en el trabajo» solo registra el estado de cada revisión: los resultados van al diario privado, nunca aquí.

**Horario:** lunes Linux y VPS · martes Redes · miércoles PostgreSQL · jueves y viernes proyecto propio y código de Odoo.

Leyenda: ✅ cerrado · 🟡 en curso · ⬜ sin empezar · ❓ por confirmar

---

## Resumen

| Carril | Bloque actual | Estado |
|---|---|---|
| Linux y VPS (lunes) | Bloque 3 · Odoo 18 desplegado a mano | ⬜ Sin empezar (quedan 3 experimentos de SSH del Bloque 2) |
| Redes (martes) | Bloque 4 · TLS | ⬜ Sin empezar |
| PostgreSQL (miércoles) | Bloque 1 · SQL sólido | 🟡 Falta el repaso de cierre |

---

## Linux y VPS · lunes

| Bloque | Estado | Fecha de cierre | Apuntes |
|---|---|---|---|
| 0 · El servidor existe | ✅ | 11/09/2026 | `README.md` (vps-setup) |
| 1 · El sistema por dentro | ✅ | 24/09/2026 | `linux-bloque-1.md` |
| 2 · systemd de verdad | ✅ | 03/10/2026 | `linux-bloque-2.md` |
| 3 · Odoo 18 desplegado a mano | ⬜ | | |
| 4 · Que no se lo lleve nadie | ⬜ | | |
| 5 · Romperlo | ⬜ | | |

**Bloque cerrado: 2 · systemd de verdad** (29/09 – 03/10/2026)
- Sesiones 1 a 5, 7 y 8 completadas. Sesión 6 con la pregunta respondida y tres experimentos pendientes (ver abajo). Lectura: *How Linux Works* cap. 6.3 y 7.1; `systemd.unit`, `systemd.service`, `systemd.exec`, `systemd.timer`.
- Criterio de cierre superado el 03/10/2026: `labweb.service` reescrito desde cero con una referencia de directivas (seis requisitos comprobados, incluido el arranque tras reinicio) y `labweb-roto.service` depurado (4 fallos: usuario inexistente, dos directivas ignoradas por `verify`, puerto ocupado).
- Pregunta abierta del Bloque 0 resuelta: `ssh.socket` hace que systemd abra el puerto 22 y `ssh.service` lanza `sshd` con ese puerto. El `reload` del 11/09 **no se ejecutó**: no hay `Reloading` en el journal de `ssh.service` ni el comando en el de `sudo`.
- Estado real del VPS al cerrar:
  - Usuario de sistema `labweb` (UID 999, shell `nologin`) y script en `/opt/labweb/labweb.py` (root, `644`).
  - `labweb.service` habilitado y funcionando en `127.0.0.1:8080` (`Type=exec`, `Restart=on-failure`, `RestartSec=2`, `PYTHONUNBUFFERED=1`).
  - `labweb-health.service` y `labweb-health.timer` en `/etc/systemd/system`, con el timer **deshabilitado**.
  - Sin drop-ins en `labweb` (revertidos tras la Sesión 5). `labweb-roto.service` eliminado. Sin tareas en el crontab de `miguel`.
  - `miguel` añadido al grupo `systemd-journal` (lee el journal sin `sudo`).
  - Descripción de terminal de Ghostty instalada a nivel de sistema (`infocmp -x xterm-ghostty | sudo tic -x -`): `sudo less`, `sudo vim` y `sudo nano` ya no fallan.
- Cambio de método acordado: mapa de lo que existe al empezar cada tema, la necesidad se formula en palabras y la línea se escribe con referencia (sin dictado), preguntas concretas de un solo dato. Recogido en las instrucciones del proyecto.
- **Pendientes del bloque (no bloquean el Bloque 3):**
  - Probar la consola VNC del panel de Netcup (también pendiente del Bloque 0).
  - Después, los tres experimentos de la Sesión 6: ver la activación por socket con `ssh.service` parado; comprobar un `reload` con un `Banner` en `/etc/ssh/sshd_config.d/99-lab.conf` y retirarlo; corregir la frase sobre `reload`/`restart` del `README.md` de `vps-setup`.
  - Borrar `~/labweb.service.bak`.

**Bloque cerrado: 1 · El sistema por dentro**
- Sesiones 1 a 4 completadas: cap. 2, 4, 5, 6 (parcial) y 8 de *How Linux Works*; cap. 9 de *The Linux Command Line*.
- Criterio de cierre superado: explicación en voz alta, sin notas, del recorrido completo firmware → bootloader → kernel → initramfs → systemd → targets → login SSH.
- Cambios reales aplicados y verificados en el VPS tras reinicio: `multi-user.target` como target por defecto (antes `graphical.target`), `snapd` purgado por completo.
- **Pendiente suelto (no bloquea el bloque):** rotar la contraseña de root del VPS (sigue siendo la original de Netcup; no alcanzable por SSH, pero sí válida por consola VNC).

**Bloque cerrado: 0 · El servidor existe** (11/09/2026, confirmado el 28/09/2026)
- Netcup VPS 500 G12 con Ubuntu 24.04 LTS minimal (UEFI amd64), hostname `backend-lab`.
- Criterio de cierre superado y verificado con `ssh -v`: `Authentications that can continue: publickey` y `Authenticated ... using "publickey"`.
- Usuario propio en el grupo `sudo`; `PermitRootLogin no`, `PasswordAuthentication no` y `KbdInteractiveAuthentication no` en `sshd_config`.
- Par ed25519 generado en local, clave pública en `authorized_keys`, alias `vps` en `~/.ssh/config` con `IdentityFile` e `IdentitiesOnly`.
- Procedimiento completo documentado en `README.md` del repo `vps-setup`.
- Aprendizajes con coste: `sudo sshd -t` falla sin privilegios con un error engañoso sobre hostkeys. ~~`systemctl reload ssh` no bastó para aplicar el cambio de métodos de autenticación~~ **Corregido en el Bloque 2:** el `reload` nunca llegó a ejecutarse (el journal lo demuestra); el cambio se aplicó con el `restart` de las 20:43.
- **Pendientes sueltos del bloque (no bloquean):** verificar la consola VNC del SCP (vía de recuperación, documentada pero no probada); confirmar en el `README.md` que los comandos de creación de usuario y copia de clave (`adduser`, `usermod -aG sudo`, `ssh-copy-id`) son los realmente usados.

---

## Redes · martes

| Bloque | Estado | Fecha de cierre | Apuntes |
|---|---|---|---|
| 1 · El modelo y las capas | ✅ | | `redes-bloque-1.md` |
| 2 · DNS | ✅ | 28/09/2026 | `redes-bloque-2.md` |
| 3 · HTTP | ✅ | 08/10/2026 | `redes-bloque-3.md` |
| 4 · TLS | ⬜ | | |
| 5 · El reverse proxy | ⬜ | | |

**Bloque cerrado: 3 · HTTP** (07/10 – 08/10/2026)
- Sesiones 1 a 5 y cierre (Sesión 6) completados. Lectura: Kurose 2.2.1 a 2.2.4 y 2.2.6; Grigorik cap. 11 (keep-alive, *pipelining*) y cap. 12 (pendiente de terminar, ver abajo); documentación de `http.server` (Python 3.12); `man curl` en las dos versiones (8.5.0 en el VPS, 8.22.0 en el portátil).
- Repaso del recorrido DNS de §2.5 (Bloque 2) hecho antes de empezar.
- Criterio de cierre superado el 08/10/2026: `curl -v` explicado sin notas contra `labweb` y contra `https://www.odoo.com/web/login` (cuatro correcciones: la ruta `/`, `Content-Length` como segundo motivo del cierre, `HttpOnly` frente a `Secure` y que el keep-alive no se debe a HTTP/2), y el multiplexado con tres «¿y por qué?» (con ayuda en el segundo: falta de etiqueta en las respuestas de HTTP/1.1).
- Puntos que costaron y conviene repasar: separar TCP de HTTP (trama de HTTP/2 frente a segmento, *stream* frente a conexión, `Connection: keep-alive` como cabecera HTTP) y el papel de `-f` (código HTTP frente a código de salida). Están en «Confusiones vistas» de los apuntes.
- Descubierto sobre `labweb`: habla HTTP/1.0 (`protocol_version` por defecto), no envía `Content-Length`, responde `200` a cualquier ruta que no sea `/health` y `501` a `HEAD` y `POST`. Sin cambios aplicados.
- Shell del VPS: **fish** (el código de salida está en `$status`, no en `$?`).
- Sin cambios reales en el VPS ni en el router.
- **Pendientes del bloque (no bloquean el Bloque 4):**
  - Terminar Grigorik cap. 12 (*Binary Framing Layer*, *Streams, Messages, and Frames*, *Request and Response Multiplexing*, *Header Compression*).
  - Experimento opcional: `labweb` en HTTP/1.1 (`protocol_version`), primero sin `Content-Length` y después con ella, con copia previa de `labweb.py` y revirtiendo al acabar.
  - Dos IPs locales distintas en casa (`192.168.1.74` el 07/10 por la mañana y `192.168.17.250` después, con el router de O2): revisar con `ip a` e `ip r` si hay dos redes (principal e invitados) o un repetidor.

**Bloque cerrado: 2 · DNS**
- Sesiones 1 a 4 completadas el 28/09/2026: jerarquía y delegación, recursiva frente a iterativa y caché, tipos de registro, TTL y propagación. Kurose 2.4 completo.
- Cierre parte 1 superado el 28/09/2026: por qué un cambio de DNS «tarda» y qué lo controla, aguantando los tres «¿y por qué?».
- Cierre parte 2 dado por cerrado por decisión propia, **con ayuda**: en el primer intento puse a `systemd-resolved` haciendo el recorrido iterativo (es *stub*: reenvía) y caché en raíz, TLD y autoritativo (solo cachean los resolutores). La versión correcta se vio en el chat (§2.5 de los apuntes).
- Ampliación práctica del mismo día (§7 de los apuntes): cómo elegir resolutor, de dónde saca el DNS el portátil (manual > DHCP del router > *fallback*), cómo bloquea la operadora y caso real pixeldrain analizado capa por capa (DNS correcto; bloqueo por IP e inyección en HTTP).
- Cambios reales aplicados:
  - DNS del router (HGU Mitrastar de O2) cambiado de Google a **Quad9** (`9.9.9.9` y `149.112.112.112`) en el servidor DHCP. Verificado en el portátil con `resolvectl status`. Valores anteriores: `8.8.8.8` y `8.8.4.4`.
  - Dominio **`mlozano.dev`** comprado en Cloudflare Registrar (12,20 $/año, renovación al mismo precio). Cuenta de Cloudflare con acceso vía GitHub y 2FA activada.
- ~~**Repaso pendiente al empezar Redes · Bloque 3:** reproducir sin mirar el recorrido de §2.5.~~ Hecho antes de la Sesión 1 del Bloque 3.

---

## PostgreSQL · miércoles

| Bloque | Estado | Fecha de cierre | Apuntes |
|---|---|---|---|
| 0 · Que la base de datos exista (extra) | ✅ | 13/09/2026 | `postgresql-bloque-0.md` |
| 1 · SQL sólido | 🟡 | | `postgresql-bloque-1.md` |
| 2 · El modelo relacional | ⬜ | | |
| 3 · Índices | ⬜ | | |
| 4 · Leer planes de ejecución | ⬜ | | |
| 5 · El ORM de Odoo bajo el capó | ⬜ | | |

**Bloque en curso: 1 · SQL sólido**
- Contenido trabajado: joins, agregaciones, subconsultas, CTEs y window functions.
- **Siguiente paso:** repaso en voz alta del criterio de cierre (`WHERE` frente a `HAVING`, `GROUP BY` frente a `PARTITION BY`, por qué `HAVING` no ve los alias del `SELECT`).
- Practicar `LAG()` y `LEAD()`, mencionados pero no ejercitados.

---

## Aplicación en el trabajo

Revisión de cada bloque cerrado con la pregunta «¿qué de esto puedo aplicar en el trabajo?», clasificando cada tema en observar, proponer o no aplica. Un chat por bloque. **Aquí solo va el estado:** los resultados viven en el diario privado (fuera del repo). Cada bloque que se cierre en adelante se añade a esta tabla.

| Carril | Bloque | Revisión | Fecha |
|---|---|---|---|
| Linux | 0 · El servidor existe | ⬜ | |
| Linux | 1 · El sistema por dentro | ⬜ | |
| Linux | 2 · systemd de verdad | ⬜ | |
| Redes | 1 · El modelo y las capas | ⬜ | |
| Redes | 2 · DNS | ⬜ | |
| Redes | 3 · HTTP | ⬜ | |
| PostgreSQL | 0 · Que la base de datos exista | ⬜ | |

- **Orden:** primero la revisión retroactiva de los bloques ya cerrados, empezando por Linux 0. Después, cada bloque al cerrarse.
- **Antes de empezar las revisiones:**
  - Diario privado creado y subido al conocimiento del proyecto (plantilla en un chat aparte).
  - Avisar al jefe de que voy a mirar, en solo lectura, cómo se gestionan los backups.

---

## Temas aplazados

Cosas que surgieron antes de tiempo y tienen un bloque asignado.

- **`odoo.service` (Linux · Bloque 3)** — dependencia sobre `postgresql@16-main.service` con `After=` (no sobre `postgresql.service`, que queda `active (exited)` aunque el servidor caiga). Decidir entre `Wants=` y `Requires=`: con `Requires=`, un `stop` + `start` de PostgreSQL deja Odoo parado.
- **`labweb` (Linux · Bloques 3 y 5, Artefacto 2)** — se mantiene para practicar nginx antes que con Odoo, para el Bloque 5 y para probar el healthcheck. Eliminarlo cuando Odoo funcione: `disable --now`, borrar `labweb.service`, `labweb-health.service` y `labweb-health.timer`, `daemon-reload`, `rm -r /opt/labweb`, `userdel labweb`.
- **Linux · Bloque 4** — bots probando usuarios por SSH a diario (vistos en el journal; rechazados por autenticación solo con clave): motivo para `fail2ban`. El puerto de SSH lo fija `ssh.socket`, no `sshd_config`. Aplicar las 28 actualizaciones pendientes. **No ejecutar `do-release-upgrade`** a 26.04: el roadmap está planteado sobre 24.04.
- **Endurecimiento de servicios systemd** (`ProtectSystem=`, `NoNewPrivileges=`, `PrivateTmp=`, `DynamicUser=`) — fuera del Bloque 2; sin bloque asignado, candidato al Bloque 4.
- **VPN propia sobre el VPS con WireGuard** — después del Bloque 4 de Linux (`ufw`, `fail2ban`, SSH endurecido). Ver `ideas-proyectos.md`.
- **`mlozano.dev`: comprobar la delegación** con `dig -4 +trace mlozano.dev` (el TLD de `.dev` debe dar `NS` de Cloudflare). Se puede hacer ya.
- **Experimento de TTL** con `prueba.mlozano.dev` → `192.0.2.1`, TTL 300, y cambio posterior, observando al autoritativo, `1.1.1.1` y `8.8.8.8`. Opcional, remate práctico de Redes · Bloque 2 (ya cerrado); se puede hacer antes del Bloque 3 de Linux. No consultar el nombre antes de crearlo (caché negativa).
- **Apuntar `mlozano.dev` al VPS** — en el Bloque 3 de Linux, junto con nginx, Odoo y TLS. Registros en **«DNS only»** (nube gris), no con el proxy de Cloudflare.
- **Mejoras del router** propuestas y no aplicadas: cambiar la contraseña de administración, desactivar WPS, revisar la redirección de puertos, valorar desactivar UPnP, comprobar WPA2/WPA3 y red de invitados. De una en una, apuntando el valor anterior.
- **Revisar tras el próximo reinicio del router** que conserva los DNS de Quad9.
- **Comprobar que Gmail tiene 2FA**: es el último eslabón de la cadena Gmail → GitHub → Cloudflare → `mlozano.dev`.
- **Instalar `bind9-dnsutils`** en el VPS (de Redes · Bloque 2; hará falta en el Bloque 3 de Linux).
- **Caso pixeldrain (Redes · Bloque 4)** — la parte HTTP quedó resuelta en el Bloque 3: por el puerto 80 la operadora inyecta una página sin línea de estado (`Received HTTP/0.9`) con el texto «Contenido bloqueado por requerimiento de la Autoridad Competente». Queda la parte HTTPS: la conexión TCP **sí** se abre y el corte (`Connection reset by peer`, `curl` código 35) llega justo después del `Client hello`. Corrige la conclusión del Bloque 2 («se corta antes de llegar a TLS») y apunta a inspección del SNI. Explicarlo en el Bloque 4.
