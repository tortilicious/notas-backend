# Linux/VPS · Bloque 3 — Odoo 18 desplegado a mano · Plan de sesiones

Carril de Linux y VPS, en alternancia por sesión con Redes. Doce sesiones: las 1 a 10 se planificaron a ~1 h; desde la 11, **~2 h por sesión** con objetivos numerados como puntos de control.

**Criterio de cierre:** reinstalar Odoo 18 entero en una máquina nueva siguiendo solo tus propias notas. Sin Docker, deliberadamente.

**Entorno de partida:**

| Pieza | Estado |
|---|---|
| VPS | `backend-lab`, Netcup VPS 500 G12, Ubuntu 24.04 LTS minimal, acceso solo por clave con el alias `vps` |
| PostgreSQL | Paquete 16 instalado en el VPS, clúster `16/main`, unit `postgresql@16-main.service` |
| `labweb` | Servicio de prueba en `127.0.0.1:8080`, se usa para ensayar nginx antes que con Odoo |
| Portátil | CachyOS, con PostgreSQL 18 y Pagila (carril de PostgreSQL) |
| Dominio | `mlozano.dev` en Cloudflare, sin registros que apunten al VPS al empezar el bloque |

**Decisión de solape con Redes:** nginx y TLS se instalan **funcionales** en este bloque. Se entiende cada línea a nivel de «qué hace», y todo lo que pida más fondo se apunta en los pendientes de `progreso.md` para Redes · Bloque 4 (TLS) y Bloque 5 (reverse proxy).

**Ritual de cada sesión:** según las instrucciones del proyecto (§7).

---

## Índice

| # | Sesión | Dónde se trabaja |
|---|---|---|
| 1 | La red del VPS | VPS (+ panel de Netcup) |
| 2 | Paquetes: qué hay y de dónde viene | VPS |
| 3 | PostgreSQL listo para Odoo | VPS |
| 4 | Código de Odoo y entorno Python | VPS |
| 5 | Primer arranque a mano y `odoo.conf` | VPS (2 terminales) + portátil |
| 6 | `odoo.service` | VPS |
| 7 | Los PDF: wkhtmltopdf | VPS + portátil (navegador) |
| 8 | nginx delante de `labweb` | VPS + portátil |
| 9 | `mlozano.dev` y Odoo detrás de nginx | Cloudflare + VPS + portátil |
| 10 | HTTPS con certbot | VPS + portátil |
| 11 | Notas de reinstalación y `vps-setup` | Portátil + VPS |
| 12 | Reinstalación (criterio de cierre) | Máquina nueva |

## Bibliografía del bloque y dónde se usa

| Fuente | Sesiones |
|---|---|
| *How Linux Works*, cap. 9 (la red y su configuración) | 1, 5, 9 |
| *How Linux Works*, cap. 10 (servicios de red) | 3, 5, 8 |
| *The Linux Command Line*, cap. 14 (gestión de paquetes) | 2, 4, 7, 10 |
| *The Linux Command Line*, cap. 16 (herramientas de red) | 1, 5, 8 |
| Documentación de Odoo 18: *Source install*, *Deploying Odoo* y referencia de la CLI | 3 a 7, 9, 10 |
| Tus apuntes del Bloque 2 y `systemd.unit`, `systemd.service`, `systemd.exec` (manpages.ubuntu.com, *noble*) | 6 |
| Guía de principiante de nginx (nginx.org) | 8, 9 |
| Documentación de certbot | 10 |

La documentación de Odoo se usa **como referencia, no como receta**: primero formulas la necesidad, después confirmas allí el nombre exacto.

---

## Sesión 1 · La red del VPS

**1. El problema** (VPS, terminal SSH; antes, panel de Netcup en el navegador del portátil)

Para apuntar `mlozano.dev` al VPS necesitas sus direcciones IPv4 e IPv6 públicas, y hoy no sabes de dónde salen ni quién las configura al arrancar. Hay una segunda pregunta sin responder: si Odoo escucha en `0.0.0.0`, ¿desde dónde se le puede llegar? ¿Y si escucha en `127.0.0.1`?

Antes de tocar nada: prueba la **consola VNC** del panel de Netcup (pendiente desde el Bloque 0). Esta sesión solo **lee** la configuración de red, pero en este bloque vas a abrir puertos y el día que algo corte SSH esa consola es la única puerta.

**2. Bibliografía**

- *How Linux Works* cap. 9:
  - «Network Interfaces» e «Introduction to Network Interface Configuration» → qué direcciones tiene el VPS y en qué interfaz.
  - «Routes and the Kernel Routing Table» y «The Default Gateway» → por dónde sale el tráfico.
  - «Boot-Activated Network Configuration» y «Network Configuration Managers» → quién configura la red al arrancar (en Ubuntu, netplan).
  - «Resolving Hostnames» → `/etc/hosts`, `resolv.conf`, `systemd-resolved` (enlaza con Redes · Bloque 2).
  - «localhost» → por qué `127.0.0.1` no se ve desde fuera.
  - «The Transport Layer: TCP, UDP, and Services» → qué es un socket escuchando.
  - *Lectura de contexto opcional:* DHCP, NAT, ARP, Linux como router y wireless. Ya lo viste en Redes · Bloque 1 y no se aplica hoy.
- *The Linux Command Line* cap. 16, «Examining and Monitoring a Network» → `ping`, `tracepath`/`traceroute`, `ip`. `netstat` aparece en el libro, pero en Ubuntu 24.04 se usa `ss`.

**3. Objetivos para darla por superada**

- Has iniciado sesión con `miguel` en la consola VNC de Netcup.
- Tienes anotados la IPv4 y la IPv6 públicas del VPS, el nombre de la interfaz y la puerta de enlace por defecto, sacados con `ip` en el VPS.
- Has localizado el fichero de netplan y sabes decir, comprobándolo en el fichero y en el estado del servicio, qué renderer usa (`systemd-networkd` o NetworkManager) y si la dirección es estática o por DHCP.
- Con `ss` has listado lo que escucha hoy en el VPS (SSH, `labweb`, PostgreSQL) y has clasificado cada socket en «accesible desde fuera» o «solo local».

**4. Lo más importante**

- `127.0.0.1` frente a `0.0.0.0` es exactamente la diferencia entre un Odoo protegido detrás de nginx y un Odoo expuesto a internet. Es la base de las sesiones 5, 8 y 9.
- La IPv4 y la IPv6 que anotes hoy son el contenido de los registros `A` y `AAAA` de la Sesión 9.
- Platform engineering: en la nube, el fichero de netplan suele generarlo cloud-init al crear la máquina. Saber leerlo es saber qué ha hecho el proveedor por ti.

---

## Sesión 2 · Paquetes: qué hay instalado y de dónde viene

**1. El problema** (VPS, terminal SSH)

Necesitas `dig` en el VPS (pendiente de Redes · Bloque 2) y no sabes qué paquete lo trae. PostgreSQL 16 está instalado, pero no sabes de qué repositorio vino, qué ficheros puso ni qué otros paquetes arrastró. Y el VPS avisa de actualizaciones pendientes: ¿cuáles son? (**Se listan, no se aplican**: eso es el Bloque 4.)

**2. Bibliografía**

- *The Linux Command Line* cap. 14:
  - «Packaging Systems» y «How a Package System Works» (ficheros de paquete, repositorios, dependencias, herramientas de alto y bajo nivel) → la diferencia entre `apt` y `dpkg`.
  - «Common Package Management Tasks» → cada subpregunta del problema: buscar un paquete en el repositorio, instalar, listar los instalados, saber si uno está instalado, ver su información y averiguar qué paquete instaló un fichero.
  - «Upgrading Packages from a Repository» → solo lectura hoy.
- `man apt` y `man dpkg` en el VPS, para confirmar las opciones en tu versión.
- Ubuntu 24.04 guarda los repositorios en `/etc/apt/sources.list.d/` con el formato *deb822*; el libro muestra el formato antiguo de una línea. Contrástalo en el VPS.

**3. Objetivos para darla por superada**

- `dig` funciona en el VPS, y sabes nombrar el paquete que lo aporta y cómo lo averiguaste **antes** de instalarlo.
- Con la salida de `apt policy` dices de qué repositorio viene `postgresql-16`.
- Dado el binario `psql` del VPS, sabes qué paquete lo instaló.
- La lista de actualizaciones pendientes está guardada en una nota, sin aplicar.
- Señalas en el VPS un par «biblioteca / paquete `-dev`» (por ejemplo, `libpq5` y `libpq-dev`) y dices cuál está instalado y por qué.

**4. Lo más importante**

- La diferencia entre la biblioteca y su paquete `-dev` (cabeceras para compilar) es lo que va a romper el `pip install` de la Sesión 4.
- «Qué paquete instaló este fichero» es la pregunta de diagnóstico más útil del Bloque 5.
- Platform engineering: un `Dockerfile` es, en buena parte, una lista de `apt install`. Saber qué aporta cada paquete es lo que separa una imagen limpia de una de 2 GB.

---

## Sesión 3 · PostgreSQL listo para Odoo

**1. El problema** (VPS, terminal SSH)

Odoo va a correr como un usuario de sistema propio y tiene que conectarse a PostgreSQL **sin contraseña**. En el portátil ya resolviste por qué `psql -d` entra sin contraseña y `psql -h localhost` no (PostgreSQL · Bloque 0), pero en Ubuntu el clúster lo creó el paquete y los ficheros están en otro sitio.

Reprodúcelo: crea el usuario de sistema `odoo` (como hiciste con `labweb`) e intenta listar las bases como ese usuario. Falla. ¿Por qué, y qué es lo mínimo que hay que crear para que funcione?

**2. Bibliografía**

- *How Linux Works* cap. 10, «Unix Domain Sockets» → por qué una conexión sin host va por un fichero de socket y por qué eso permite autenticación `peer`. «Network Sockets» como contexto.
- `man pg_lsclusters` (herramientas de Debian/Ubuntu para clústeres) → dónde vive la configuración de `16/main`.
- Documentación de PostgreSQL 16, capítulo «Client Authentication» (`pg_hba.conf`) → repaso; ya lo trabajaste en PostgreSQL · Bloque 0.
- Odoo 18, *Source install* → apartado de PostgreSQL (qué rol necesita).
- Odoo 18, referencia de la CLI → opciones de base de datos (`db_host`, `db_user`): qué significa dejar `db_host` vacío.

**3. Objetivos para darla por superada**

- Usuario de sistema `odoo` creado, con shell `nologin` y con el directorio personal que decidas. Anota por qué ese directorio (Odoo escribirá allí sus ficheros si no le dices otra cosa).
- Como `odoo`, `psql` devuelve `odoo` en `current_user` sin pedir contraseña.
- `\du` muestra el rol `odoo` con `Create DB` y **sin** `Superuser`.
- Señalas la línea de `pg_hba.conf` que permite esa conexión, y el socket de PostgreSQL en la salida de `ss`.
- La misma conexión con `-h 127.0.0.1` falla, y sabes explicar por qué.

**4. Lo más importante**

- Esta sesión decide las líneas de base de datos de `odoo.conf` (Sesión 5).
- Conexión por socket + `peer` = ninguna contraseña de base de datos guardada en un fichero. Menos secretos que proteger en el Bloque 4.
- `CREATEDB` sí y `SUPERUSER` no: el mismo razonamiento de mínimo privilegio que con `labweb` y con `root` en el VPS.
- PostgreSQL · Bloque 5 (activar el log de consultas del ORM) se hace sobre este clúster.

---

## Sesión 4 · Código de Odoo y entorno Python

**1. El problema** (VPS, terminal SSH)

Descargas el código de la rama `18.0`, creas un entorno virtual de Python y le pides que instale `requirements.txt`. Lo esperable es que falle al menos tres veces: al crear el entorno virtual y al compilar alguna de las dependencias (por ejemplo, el conector de PostgreSQL o el de LDAP). Cada error dice qué le falta; tu trabajo es pasar del mensaje de error al nombre del paquete `apt`.

Decisión de diseño antes de empezar: qué carpetas debe poder **escribir** el usuario `odoo` y cuáles no. Criterio: el código y el entorno, solo lectura para `odoo` (como `/opt/labweb`); sus datos, escritura.

**2. Bibliografía**

- Odoo 18, *Source install* → «Fetch the sources» (git) y «Prepare» (versión de Python, dependencias, mención a `debinstall.sh`). Úsalo para **confirmar** la lista a la que llegues desde los errores, no para copiarla.
- *The Linux Command Line* cap. 14, «Finding a Package in a Repository» → del nombre de un fichero que falta al paquete que lo contiene.
- Documentación de Python 3.12, módulo `venv` → qué es un entorno virtual y por qué no se instala nada con `pip` en el Python del sistema.
- *Lectura de contexto opcional:* `rtlcss`/Node.js, solo necesario para idiomas que se escriben de derecha a izquierda.

**3. Objetivos para darla por superada**

- El repositorio está en la rama `18.0` y tienes anotado el commit concreto que has desplegado.
- Tienes una lista de los paquetes `apt` añadidos en la sesión, cada uno con el error que lo pidió.
- `pip install` termina sin errores y `pip check` no informa de conflictos.
- El `odoo-bin` lanzado con el Python del entorno virtual imprime la versión 18.0.
- Como `odoo`, intentar crear un fichero dentro del código o del entorno virtual da `Permission denied`.

**4. Lo más importante**

- Dependencias de compilación (`-dev`, `build-essential`) frente a dependencias de ejecución: en contenedores es la base de los *builds* multietapa.
- El commit anotado es la diferencia entre «reinstalar Odoo» y «reinstalar **tu** Odoo» en la Sesión 12.
- Actualizar Odoo en este esquema será traer cambios con git y reiniciar el servicio: lo entenderás porque has montado cada pieza.

---

## Sesión 5 · Primer arranque a mano y `odoo.conf`

**1. El problema** (VPS: terminal 1 para lanzar Odoo, terminal 2 para observar; portátil: terminal y navegador)

Lanzas Odoo a mano como `odoo` con las opciones por defecto y, desde la terminal 2, miras con `ss` dónde escucha. Párelo en cuanto lo veas (menos de un minuto, sin abrir el navegador): todavía no hay firewall y el gestor de bases quedaría abierto a internet.

Después: quieres usar Odoo desde el navegador del portátil **sin** exponerlo. Y todas las opciones que hayas puesto en la línea de comandos tienen que pasar a un fichero de configuración que contiene un secreto (la contraseña maestra).

**2. Bibliografía**

- Odoo 18, referencia de la CLI → el nombre exacto de cada opción (dirección y puerto HTTP, `addons_path`, `data_dir`, base de datos, contraseña maestra) y cómo se escribe en el fichero. Es la «referencia delante» de esta sesión.
- *How Linux Works* cap. 10, «The Secure Shell» (cliente SSH) y *The Linux Command Line* cap. 16, «Tunneling with SSH» → reenvío de puertos con `ssh`.
- *How Linux Works* cap. 9, «localhost» → repaso.
- Odoo 18, *Deploying Odoo* → «Configuration» y «Builtin server». La parte de seguridad se completa en las sesiones 9 y 10.

**3. Objetivos para darla por superada**

- Con el fichero de configuración, `ss` muestra Odoo **solo** en `127.0.0.1:8069`.
- Desde el navegador del portátil, a través del túnel SSH, ves Odoo y has creado la primera base de datos (nombre a tu elección, anotado).
- El directorio de datos contiene el *filestore* de esa base, propiedad de `odoo`.
- `odoo` puede leer `odoo.conf` y `miguel` no puede sin `sudo`.
- Explicas cada línea de `odoo.conf` señalando la opción de la referencia de la CLI.

**4. Lo más importante**

- Base de datos + *filestore* = lo que el backup tiene que copiar (Artefacto 1 y Bloque 4). Una sin la otra no restaura nada.
- El túnel SSH es cómo los administradores llegan a servicios internos sin abrir puertos: lo usarás con PostgreSQL, paneles de monitorización y cualquier cosa que no deba estar en internet.
- Contraseña maestra y gestor de bases: la decisión de seguridad se cierra en la Sesión 9, antes de exponer nada.

---

## Sesión 6 · `odoo.service`

**1. El problema** (VPS, terminal SSH)

Cierras la terminal 1 de la sesión anterior y Odoo muere. Es el problema con el que empezó el Bloque 2, ahora con un servicio de verdad que además depende de otro. Pendiente aplazado: dependencia sobre `postgresql@16-main.service` (no sobre `postgresql.service`) y decidir entre `Wants=` y `Requires=`.

**2. Bibliografía**

- Tus apuntes del Bloque 2 como referencia principal; después, `man systemd.unit` (`After=`, `Wants=`, `Requires=`), `man systemd.service` (`Type=`, `ExecStart=`, `Restart=`) y `man systemd.exec` (`User=`, `Group=`).
- El código de Odoo incluye un unit file en su empaquetado Debian (búscalo dentro del repositorio). Léelo **después** de escribir el tuyo, para comparar, no antes.

**3. Objetivos para darla por superada**

- `odoo.service` activo y habilitado; `systemd-analyze verify` no da avisos.
- Tras reiniciar el VPS, el journal de ese arranque muestra PostgreSQL iniciado antes que Odoo, y Odoo responde por el túnel.
- Experimento documentado: paras `postgresql@16-main`, observas qué hace Odoo; lo vuelves a arrancar y observas de nuevo. Con ese resultado eliges `Wants=` o `Requires=` y lo justificas.
- Encuentras en `journalctl -u odoo` la línea de un inicio de sesión tuyo en Odoo.
- Anotas las diferencias entre tu unit y la de Odoo, y si alguna merece adoptarse.

**4. Lo más importante**

- Este servicio es el que vas a matar en el Bloque 5 y el que vigilará el healthcheck (Artefacto 2).
- Sin fichero de log propio, todo el log de Odoo va al journal: un solo sitio donde mirar.
- Platform engineering: `Restart=` y las dependencias son el antecedente directo de las políticas de reinicio y las *probes* de Kubernetes.

---

## Sesión 7 · Los PDF: wkhtmltopdf

**1. El problema** (VPS, terminal SSH; navegador del portátil por el túnel)

Instalas una aplicación con documentos imprimibles (Ventas o Facturación) e imprimes un presupuesto. Primero falla porque falta el motor de PDF. Si instalas el que trae Ubuntu, el PDF sale **sin cabecera ni pie**. Odoo pide una versión concreta con Qt parcheado, que no está en los repositorios.

**2. Bibliografía**

- Odoo 18, *Source install* → nota sobre wkhtmltopdf (qué versión y de dónde descargarla).
- *The Linux Command Line* cap. 14, «Installing a Package from a Package File» → instalar un `.deb` descargado y en qué se diferencia `dpkg` de `apt` cuando faltan dependencias.
- *Lectura de contexto opcional:* por qué el Qt parcheado (historia del proyecto wkhtmltopdf).

**3. Objetivos para darla por superada**

- `wkhtmltopdf --version` indica «with patched qt».
- Enseñas un PDF de presupuesto con cabecera y pie.
- `apt policy` muestra que ese paquete no viene de ningún repositorio, y sabes explicar qué implica para las actualizaciones.

**4. Lo más importante**

- Un paquete instalado desde fichero no recibe actualizaciones de seguridad: queda apuntado para el Bloque 4.
- Odoo genera el PDF pidiéndose a sí mismo los estilos a través de su URL base. Cuando pongas nginx delante (Sesión 9), vuelve a comprobar que los PDF salen con estilos.

---

## Sesión 8 · nginx delante de `labweb`

**1. El problema** (VPS, terminal SSH; portátil, terminal)

`labweb` solo escucha en `127.0.0.1:8080`. Desde el portátil, una petición al puerto 80 del VPS da conexión rechazada. Quieres que se pueda llegar desde fuera **sin** cambiar `labweb`. Se ensaya aquí, con algo que no importa romper, antes de hacerlo con Odoo.

**2. Bibliografía**

- *How Linux Works* cap. 10, «The Basics of Services», «A Closer Look» y «Network Servers» → qué hace un servidor que escucha y atiende conexiones. «Diagnostic Tools» → `ss`/`lsof` y `nc` para comprobar puertos.
- Guía de principiante de nginx (nginx.org): estructura del fichero de configuración, «Setting Up a Simple Proxy Server» y cómo arrancar, parar y recargar.
- En el VPS: `/etc/nginx/nginx.conf` → cómo incluye `sites-enabled` (organización propia de Debian/Ubuntu).
- *Grigorik* cap. 13 → **no ahora**: es Redes · Bloque 5.

**3. Objetivos para darla por superada**

- Desde el portátil, `curl -v` a la IPv4 del VPS en el puerto 80 devuelve la respuesta de `labweb`.
- `ss` muestra nginx en el puerto 80 (IPv4 e IPv6) y `labweb` sigue solo en `127.0.0.1`.
- El sitio por defecto de nginx está desactivado, y sabes explicar cómo funcionan los enlaces de `sites-enabled`.
- Has parado `labweb`, has visto el `502` en `curl` y la línea correspondiente en el log de errores de nginx; después lo has vuelto a arrancar.
- Siempre has validado la configuración de nginx antes de recargar.
- El journal de `labweb` muestra que las peticiones llegan desde `127.0.0.1`, no desde tu IP. Apuntado en las preguntas aparcadas.

**4. Lo más importante**

- El mismo patrón, con Odoo, en la Sesión 9.
- «Corrompe la config de nginx» es uno de los incidentes del Bloque 5: hoy has visto cómo es el `502` sano.
- Platform engineering: un *ingress controller* de Kubernetes es, en muchos casos, un nginx generado a partir de reglas.

---

## Sesión 9 · `mlozano.dev` y Odoo detrás de nginx

**1. El problema** (Cloudflare en el navegador; VPS, terminal SSH; portátil, terminal y navegador)

`http://mlozano.dev` no lleva a ningún sitio: no hay registros. Una vez creados y con nginx apuntando a Odoo, aparece un fallo típico: al iniciar sesión, el navegador salta a `127.0.0.1:8069` y la página no carga. Además, en el momento en que Odoo es alcanzable desde internet, el gestor de bases de datos también lo es.

**2. Bibliografía**

- Documentación de Cloudflare sobre registros DNS → crear `A` y `AAAA` en modo «DNS only» (nube gris).
- `man dig` y tus apuntes de Redes · Bloque 2 → comprobar contra el autoritativo y contra un resolutor; `dig -4 +trace` para la delegación (pendiente aplazado).
- Odoo 18, *Deploying Odoo* → «HTTPS» (configuración de ejemplo de nginx: úsala hoy sin las líneas de certificado), «Builtin server» (websocket y `proxy_mode`) y «Security» (contraseña maestra, `list_db`, `dbfilter`).
- *Lectura de contexto opcional:* *Deploying Odoo*, cálculo de *workers* y memoria. Hoy basta con `workers = 0`.
- *Grigorik* caps. 13 y 17 → **no ahora**: Redes · Bloque 5.

**3. Objetivos para darla por superada**

- `dig` contra el autoritativo de Cloudflare y contra `1.1.1.1` devuelve la IP del VPS para `A` (y `AAAA` si el VPS tiene IPv6), y la traza muestra la delegación de `.dev` a Cloudflare.
- Has reproducido una vez la redirección a `127.0.0.1` y sabes qué línea (de nginx y de `odoo.conf`) la corrige.
- Desde el navegador del portátil, `http://mlozano.dev` muestra Odoo y la URL sigue siendo `mlozano.dev` después de iniciar sesión.
- El journal de Odoo registra tu IP pública real, no `127.0.0.1`.
- El gestor de bases de datos ya no es accesible desde fuera.
- Los PDF siguen saliendo con estilos.
- Cada línea de la configuración de nginx que no sepas explicar está en las preguntas aparcadas.

**4. Lo más importante**

- `proxy_mode` y las cabeceras que lo acompañan son el puente con Redes · Bloque 5: aquí funcionan, allí entenderás por qué.
- Esta sesión es la primera mitad del hito final de Redes: dominio → DNS → TCP → nginx → Odoo → Postgres.
- La seguridad se cierra **antes** de exponer, no después: es el hábito del Bloque 4.

---

## Sesión 10 · HTTPS con certbot

**1. El problema** (VPS, terminal SSH; portátil, navegador y terminal)

El navegador marca `mlozano.dev` como «No seguro» y tu contraseña de Odoo viaja en claro. La herramienta habitual, certbot, recomienda instalarse con snap, y **purgaste `snapd`** en el Bloque 1. Hay que elegir otra vía. Y certbot va a modificar tu configuración de nginx: quieres saber exactamente qué ha cambiado.

**2. Bibliografía**

- Documentación de certbot → obtener certificados con el plugin de nginx y renovación.
- *The Linux Command Line* cap. 14 → instalar certbot y su plugin desde los repositorios de Ubuntu.
- Tus apuntes del Bloque 2, sección de timers → cómo se renueva solo.
- Odoo 18, *Deploying Odoo* → «HTTPS», para comparar con lo que haya dejado certbot.
- *Grigorik* cap. 4 y documentación de Let's Encrypt sobre el reto HTTP-01 → **no ahora**: Redes · Bloque 4.

**3. Objetivos para darla por superada**

- `https://mlozano.dev` muestra el candado y `curl -I` a `http://` devuelve una redirección `301` a `https://`.
- Tienes una copia de tu fichero de sitio antes de certbot y un `diff` con el de después, con cada línea añadida marcada como «la entiendo» o «aparcada para Redes 4/5».
- El timer de renovación aparece en `systemctl list-timers` y una renovación de prueba termina bien.
- Sabes dónde están el certificado y la clave privada, y compruebas que `miguel` no puede leer la clave.
- La URL base de Odoo empieza por `https://` y los PDF siguen saliendo bien.

**4. Lo más importante**

- El `diff` de hoy es el material para cerrar Redes · Bloque 4 («entender exactamente qué hace certbot por debajo»).
- Un certificado que no se renueva caduca en 90 días: es un incidente de Bloque 5 esperando a ocurrir si el timer falla.
- Con esta sesión, el entregable del trimestre «VPS con Odoo desplegado a mano y HTTPS» está cumplido (faltan los backups, Bloque 4).

### Resto de la Sesión 10 · Endurecimiento (urgente)

**1. El problema** (VPS, terminal SSH; portátil, navegador)

El certificado funciona, pero hay tres huecos: la contraseña del administrador de `test-db` viajó por `http` en una prueba previa al certificado; la contraseña maestra quedó escrita en un chat y está en texto plano en `odoo.conf`; y certbot no añadió ni HSTS ni la marca `secure` en la cookie de sesión.

**2. Bibliografía**

- Odoo 18, *Deploying Odoo* → «Security»: contraseña maestra y `admin_passwd` en hash.
- Odoo 18, *Deploying Odoo* → «HTTPS»: el ejemplo con `Strict-Transport-Security` y `proxy_cookie_flags`.
- Documentación de nginx, módulo `ngx_http_headers_module` → `add_header` y cuándo se hereda en un `location` (por eso `location /websocket` necesita revisión aparte).

**3. Objetivos para darla por superada**

1. Contraseña del administrador de `test-db` cambiada desde la interfaz de Odoo y anotada en el gestor de contraseñas.
2. Contraseña maestra nueva guardada en el gestor, `admin_passwd` en hash (copia previa de `odoo.conf`), `odoo` reiniciado y arrancando bien.
3. `curl -I https://odoo.mlozano.dev/web/login` muestra `Strict-Transport-Security` (copia previa del sitio, `sudo nginx -t`, `reload`) y un inicio de sesión funciona con la cookie `secure`.

**4. Lo más importante**

- Una contraseña que ha pasado por un sitio no controlado se considera comprometida: se cambia, no se vigila.
- HSTS y la cookie `secure` cierran el paso a que el navegador vuelva a usar `http`. El fondo, en Redes · Bloques 4 y 5.
- Al terminar, completar «Pendiente de completar» en `vps-setup/odoo.md` y actualizar `vps-inventario.md`.

---

## Sesión 11 · Notas de reinstalación y `vps-setup`

**1. El problema** (portátil; VPS para contrastar)

Sin estas conversaciones, ¿podrías repetirlo todo? `vps-setup/odoo.md` existe, pero es un borrador largo. Contrástalo con lo que de verdad ejecutaste: el journal de `sudo` del VPS guarda cada comando con privilegios (Bloque 2). Cada paso que esté en el journal y no en la receta es un hueco. Además, `vps-setup` es público y parte del portfolio: tiene que servir a cualquiera, no solo a tu máquina.

Decisión de la máquina nueva para la Sesión 12:

| Opción | A favor | En contra |
|---|---|---|
| Máquina virtual Ubuntu 24.04 en el portátil | Gratis, se destruye y repite | Sin IP pública: no se puede probar Let's Encrypt |
| VPS temporal con facturación por horas | Prueba real completa con un subdominio (`prueba.mlozano.dev`) | Coste pequeño; hay que acordarse de destruirlo |

**2. Bibliografía**

- Ninguna nueva. Tus apuntes del bloque, `linux/vps-inventario.md` y el journal de `sudo` del VPS.

**3. Objetivos para darla por superada**

1. Huecos localizados: comandos del journal de `sudo` que no están en `vps-setup`, incluidos los ⚠️ de `odoo.md` (comando de instalación de PostgreSQL, si hubo que instalar `git`) y los comandos de creación de usuario y copia de clave del `README.md` (`adduser`, `usermod -aG sudo`, `ssh-copy-id`).
2. `odoo.md` recortado a receta por capas + comprobación + decisiones de una línea, con la teoría enlazada a `notas-backend`. Incluye que `wkhtmltox` viene de un fichero y no de `apt`, que `phonenumbers` es dependencia de `account_peppol` y el parámetro `report.url`.
3. `README.md` como portada (qué es, arquitectura navegador → nginx → Odoo → PostgreSQL, estado) e índice. Corregidas la frase de `reload` (§3.9) y la de terminfo (§6); quitada la §7 (el seguimiento vive en `progreso.md`).
4. `sistema.md` creado con los ajustes de los Bloques 1 y 2 (`multi-user.target`, `snapd` purgado, `miguel` en `systemd-journal`, terminfo de Ghostty). `labweb` no entra: es de laboratorio.
5. Datos del entorno (IP, dominio, usuario, nombre de la base) como valores a sustituir, con el mismo criterio en todos los ficheros. Revisión de secretos antes del push.
6. Máquina nueva elegida y accesible por SSH con clave.

Si no cabe en 2 h, los objetivos que queden pasan a la siguiente sesión de Linux.

**4. Lo más importante**

- La receta es el entregable real del bloque y la base del procedimiento de restauración del Bloque 4.
- Platform engineering: esta receta es lo que después se convierte en un script, en Ansible o en un `Dockerfile`. Primero tiene que existir a mano.

---

## Sesión 12 · Reinstalación (criterio de cierre)

**1. El problema** (máquina nueva, desde el portátil)

Una máquina vacía. Solo tienes `vps-setup`. Cada vez que tengas que buscar algo fuera de él, lo apuntas como hueco y lo corriges al terminar. Puede necesitar dos sesiones.

**2. Bibliografía**

- `vps-setup`. Nada más.

**3. Objetivos para darla por superada**

1. Odoo 18 responde a través de nginx (con HTTPS si la máquina es pública), en la versión y el commit anotados.
2. El servicio sobrevive a un reinicio y arranca después de PostgreSQL.
3. Un PDF sale con cabecera y pie.
4. Lista de huecos encontrados, y `vps-setup` corregido y subido.
5. Máquina temporal destruida (si se usó un VPS por horas).

**4. Lo más importante**

- Si lo reinstalas desde tus notas, lo puedes restaurar en el Bloque 4 y diagnosticar en el Bloque 5.
- `labweb` **no** se borra al cerrar: se mantiene para el Bloque 5 y el Artefacto 2 (ver pendientes en `progreso.md`).
- Al cerrar el bloque se cumple el hito H1: jueves y viernes pasan al Artefacto 2.

---
