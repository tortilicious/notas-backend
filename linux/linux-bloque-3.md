# Linux/VPS · Bloque 3 — Odoo 18 desplegado a mano

La red del VPS, paquetes del sistema, bibliotecas y compilación, PostgreSQL preparado para un servicio, el entorno Python de Odoo, su primer arranque con `odoo.conf` y Odoo como servicio de systemd, con sus informes PDF, y nginx como proxy inverso. Sin Docker.

**Entorno de referencia:** Ubuntu 24.04 · kernel 6.8 · PostgreSQL 16.15 (repositorios de Ubuntu) · Python 3.12.3 · git 2.43 · uv 0.12.24 · Odoo 18.0 · nginx 1.24.0 (repositorios de Ubuntu). Con otras versiones, confirma opciones y rutas en la documentación de la versión instalada.

---

# Parte 1 · Teoría

## 1. Interfaces y direcciones

Una **interfaz** es un punto por el que la máquina envía y recibe tráfico. Un VPS típico tiene dos:

| Interfaz | Qué es | Direcciones | Quién puede llegar |
|---|---|---|---|
| `lo` (*loopback*) | Interfaz virtual: la máquina hablando consigo misma | `127.0.0.1/8`, `::1/128` | Solo la propia máquina |
| `eth0` | La interfaz conectada a la red del proveedor | IPv4 e IPv6 públicas | Cualquiera en internet |

Una máquina tiene **varias direcciones a la vez**, una o más por interfaz. Un paquete dirigido a `127.0.0.1` nunca sale de la máquina que lo envía: cada equipo usa esa dirección solo para sí mismo, y no existe camino por internet hasta la `127.0.0.1` de otro.

**Para qué sirve `lo`.** Para que los programas de una misma máquina se comuniquen por red sin exponerse: Odoo con PostgreSQL, nginx con Odoo, cualquier programa con el *stub* de DNS. Tres ventajas: lo interno no es alcanzable desde fuera; un programa que habla TCP con `127.0.0.1` habla igual con otra máquina cambiando solo la dirección; y funciona aunque `eth0` esté caída.

**TCP no significa «desde fuera».** TCP es un protocolo de conexión y funciona igual entre dos máquinas que dentro de una sola, usando `127.0.0.1`.

**Máscara y red.** `89.58.45.111/22` significa 22 bits de red y 10 de host (1024 direcciones). Aplicando la máscara (`255.255.252.0`) se obtiene la red `89.58.44.0/22`, que va de `89.58.44.0` a `89.58.47.255` (*broadcast*, el `brd` de la salida). Las demás máquinas de ese rango son vecinas: se alcanzan directamente.

**Ámbito de una dirección IPv6:**

| `scope` | Significado |
|---|---|
| `global` | Pública, alcanzable desde internet. Es la que va en un registro `AAAA` |
| `link` | De enlace local (`fe80::...`): solo vale dentro del segmento físico. Toda interfaz IPv6 tiene una |
| `host` | Solo dentro de la máquina (`::1`) |

**Estado de una interfaz:** `UP` = activada por software; `LOWER_UP` = enlace físico presente («cable conectado»). Una interfaz puede tener varios nombres (`altname`): `eth0`, `ens3` y `enp0s3` pueden ser la misma.

## 2. Rutas

Una **ruta** es una regla: «para tal destino, entrégalo de tal manera». El kernel elige la ruta según **el destino** de cada paquete; si varias encajan, gana la más concreta.

| Elemento | Significado |
|---|---|
| `via IP` | Se entrega a un **intermediario** (el siguiente salto o puerta de enlace), que lo reenvía. Sin `via`, entrega directa al destino |
| `dev eth0` | Por qué interfaz sale |
| `default` | Equivale a `0.0.0.0/0` (IPv4) o `::/0` (IPv6): una máscara de cero bits abarca todas las direcciones. Es la ruta de «todo lo demás» |
| `scope link` | El destino está en el mismo enlace: entrega directa |
| `proto kernel` | La creó el kernel al asignar una dirección a la interfaz (por ejemplo, la ruta a la propia red `/22`) |
| `proto static` | Viene de una configuración estática escrita en un fichero |
| `proto dhcp` | La entregó un servidor DHCP |
| `src IP` | Dirección que se usa como remitente |

Con una sola interfaz real, todo sale por `eth0`: lo único que decide la tabla es el siguiente salto (el vecino directamente o el router). La elección de interfaz importa cuando hay varias (`docker0` con Docker, `wg0` con WireGuard).

La puerta de enlace tiene que estar dentro de la red de la interfaz; si no, el VPS no sabría llegar a ella. En IPv6 es habitual que sea una dirección de enlace local (`fe80::1`); como no pertenece a la red `/64`, la ruta necesita marcarla como alcanzable en el mismo enlace (`on-link: true` en netplan, `GatewayOnLink=true` en systemd-networkd).

**Puerta de enlace virtual (VRRP).** En los centros de datos, la puerta de enlace suele ser una IP **virtual** compartida por dos o más routers físicos: contesta uno y, si cae, otro asume la dirección sin que los clientes noten nada. El VPS envía a la IP virtual, pero `traceroute` muestra la IP propia del router físico que responde. Se reconoce en la tabla de vecinos por la MAC: `00:00:5e:00:01:XX` (IPv4) y `00:00:5e:00:02:XX` (IPv6) están reservadas para VRRP. `keepalived`, la herramienta estándar de alta disponibilidad en Linux, usa el mismo protocolo.

**Tabla de vecinos.** Asocia cada IP de la red local con la MAC que respondió por ella.

| Estado | Significado |
|---|---|
| `REACHABLE` | Confirmado hace poco |
| `STALE` | La MAC se conoce, pero hace tiempo que no se confirma; se volverá a comprobar al usarla |
| `FAILED` | Se preguntó por esa IP y nadie respondió |

**Lectura de `traceroute`.** Varias IP en un mismo salto: las sondas fueron por caminos paralelos (reparto de carga). `*`: esa sonda no obtuvo respuesta (los routers limitan las respuestas; no implica pérdida). Un salto que «tarda» más que el siguiente no indica distancia: generar respuestas a `traceroute` es tarea de baja prioridad para un router.

## 3. Configuración de red en Ubuntu: netplan y systemd-networkd

Tres piezas, cada una con un papel:

| Pieza | Papel | Dónde |
|---|---|---|
| YAML de netplan | **Describe** cómo debe quedar la red: direcciones, rutas | `/etc/netplan/*.yaml` |
| netplan | **Traduce** el YAML, al arrancar, al formato del servicio que aplica la red | — |
| `systemd-networkd` (o NetworkManager) | **Aplica**: pone las direcciones en la interfaz y crea las rutas | Lee `/run/systemd/network/*.network` |

El servicio que aplica la red lo indica la clave `renderer:`; sin ella, en Ubuntu Server es `systemd-networkd`.

**Por qué existe netplan** si `systemd-networkd` ya tiene su formato (`.network`, con secciones como los unit files, documentado en `man systemd.network`): un solo formato vale para servidores (systemd-networkd) y escritorios (NetworkManager); es lo que generan las herramientas de la nube (cloud-init); y `netplan try` aplica un cambio y lo deshace solo si no se confirma, lo que evita perder SSH por un error. El coste es una capa más.

**cloud-init** configura la máquina la primera vez que arranca, con los datos que le pasa el proveedor. Por eso el fichero de netplan de un VPS suele llamarse `50-cloud-init.yaml`. El número inicial fija el orden de lectura.

**Reglas prácticas:**
- Se edita el YAML, nunca los `.network` de `/run/systemd/network/`, que se regeneran en cada arranque.
- Los ficheros de netplan deben ser legibles solo por root (`600`), porque pueden contener secretos (contraseñas wifi, claves de VPN).
- Configuración estática: el YAML lista `addresses`. Por DHCP: `dhcp4: true` y sin lista de direcciones.

**Columna `SETUP` de `networkctl`** (lo que dice systemd-networkd de cada interfaz):

| Valor | Significado |
|---|---|
| `configured` | La gestiona y la ha configurado bien |
| `configuring` | La gestiona y está en ello |
| `failed` | La gestiona y algo falló |
| `unmanaged` | No es suya: no hay `.network` para ella, o la gestiona otro |

La columna `OPERATIONAL` dice si la interfaz puede llegar más allá de la máquina: `routable` (tiene dirección y ruta) o `carrier` (activa, sin direcciones que lleven fuera; es lo normal en `lo`).

## 4. Sockets: quién escucha y desde dónde se llega

**Socket que escucha.** Un programa que espera conexiones reserva una dirección y un puerto de la propia máquina.

| Columna de `ss` | Significado |
|---|---|
| `Local Address:Port` | El extremo de **esta máquina**: en qué dirección y puerto escucha el programa |
| `Peer Address:Port` | El **otro extremo**: quién está conectado. En un socket que escucha sale `*` porque todavía no hay nadie |
| `State` | `LISTEN` (TCP esperando), `UNCONN` (UDP: no tiene conexiones, es su equivalente), `ESTAB` (conexión establecida) |

**La dirección local decide desde dónde se puede llegar:**

| Dirección local | Atiende en | Alcanzable desde fuera |
|---|---|---|
| `127.0.0.1`, `[::1]`, o lleva `%lo` | Solo la interfaz loopback | No |
| Una IP pública concreta | Solo esa dirección | Sí |
| `0.0.0.0` (IPv4) / `[::]` (IPv6) | **Todas** las direcciones de la máquina | Sí |

`0.0.0.0` se refiere a las direcciones de la propia máquina, no a quién se conecta. El peer no es una regla de admisión: solo registra quién está al otro lado. El filtrado por cliente se hace en el **firewall** o en la **propia aplicación** (`pg_hba.conf` en PostgreSQL).

**Cómo entrega el kernel una conexión entrante:**
1. Llega un paquete dirigido a `IP:puerto`. El puerto lo elige el cliente (22 para SSH, 80/443 para un navegador).
2. El kernel busca un socket que escuche con ese puerto y con esa IP (o con `0.0.0.0`).
3. Si lo encuentra, entrega la conexión a ese programa. Si no, la rechaza (`Connection refused`).

Un programa en `127.0.0.1:8080` no recibe lo que llega a `IP_pública:8080`: coincide el puerto, pero no la dirección.

**Cada conexión se identifica con cuatro datos:** IP y puerto locales, IP y puerto del peer. Así se distinguen dos clientes conectados al mismo puerto. El cliente usa un puerto alto aleatorio en su lado. Desde una red doméstica, el peer que ve el servidor es la IP pública del router, no la del equipo (NAT).

**Socket Unix.** Una puerta de conexión en forma de **fichero** (por ejemplo, `/var/run/postgresql/.s.PGSQL.5432`), solo usable desde la misma máquina. Como la conexión ocurre dentro del sistema, el sistema operativo sabe qué usuario está al otro lado; por TCP, el servidor solo ve una IP y un puerto. En `ss`, la dirección local de un socket Unix es una ruta; el número que aparece después es un identificador interno, no un puerto.

## 5. Paquetes del sistema

| Pieza | Qué es |
|---|---|
| Paquete `.deb` | Archivo con programas, sus manuales y una ficha: nombre, versión y dependencias |
| Repositorio | Servidor con paquetes. En Ubuntu 24.04, configurado en `/etc/apt/sources.list.d/` (formato *deb822*) |
| Índice local | Copia del catálogo de cada repositorio en la máquina |
| Dependencias | Lo que un paquete necesita; se instala con él y se marca como `automatic` |
| Metapaquete | Paquete sin ficheros propios, solo con dependencias (`build-essential`) |
| `dpkg` | Herramienta de bajo nivel: **instala** de verdad los paquetes y lleva el **registro** de lo instalado |
| `apt` | Herramienta de alto nivel: busca en los repositorios, resuelve dependencias, descarga y pasa los paquetes a `dpkg` |

Las líneas `Unpacking ...` y `Setting up ...` de una instalación las escribe `dpkg`, llamado por `apt`.

**Se instalan paquetes, no programas.** El nombre del paquete muchas veces no coincide con el del programa: `ip` y `ss` vienen en `iproute2`; `dig`, en `bind9-dnsutils`; `tracepath`, en `iputils-tracepath`.

**`apt update` frente a `apt upgrade`:** `update` solo descarga el catálogo actualizado; `upgrade` instala las versiones nuevas.

**Repositorios de Ubuntu 24.04 (*noble*):**

| Origen | Contenido |
|---|---|
| `noble` | Lo que había el día de la publicación. No cambia |
| `noble-security` | Paquetes con correcciones de seguridad |
| `noble-updates` | Correcciones de errores en general (incluye también las de seguridad) |
| Componente `main` | Paquetes con soporte oficial de Canonical, que reciben parches de seguridad |

**Versiones.** En `1.9.15p5-3ubuntu5.24.04.4`, lo anterior al primer guion es la versión del proyecto original; lo posterior, la revisión de Debian/Ubuntu. En una LTS, la versión original se congela durante toda su vida (git sigue en 2.43 aunque el proyecto vaya por la 2.56) y solo sube la revisión con cada parche: estabilidad antes que novedades. `0ubuntu` en la versión indica empaquetado por Ubuntu; el repositorio del proyecto PostgreSQL usaría `pgdg`.

**Herramientas de consulta:**

| Le das | Quieres saber | Herramienta |
|---|---|---|
| Un fichero que **no** tienes | Qué paquete lo trae | `apt-file search` |
| Un fichero que **sí** tienes | Qué paquete lo puso | `dpkg -S` |
| Un paquete | Qué ficheros instaló | `dpkg -L` |
| Un paquete | Si está instalado | `dpkg -l` |
| Un paquete | De dónde viene y en qué versión | `apt policy` |
| Nada | Qué se puede actualizar | `apt list --upgradable` |
| Nada | Qué se instaló, cuándo y quién | `/var/log/apt/history.log` |

`apt-file` busca en su propio índice (los ficheros `Contents` de cada repositorio, descargados con `apt-file update`), que lista todos los ficheros de todos los paquetes. Busca trozos de texto dentro de la ruta; con `--regexp` acepta patrones (`/` delante fija el inicio del nombre; `$` al final, que la ruta termina ahí).

**Dónde van los ficheros instalados:**

| Directorio | Contenido |
|---|---|
| `/usr/bin` | Programas para cualquier usuario |
| `/usr/sbin` | Programas de administración |
| `/usr/include` | Cabeceras para compilar |
| `/usr/lib` | Bibliotecas |
| `/usr/local/bin` | Programas instalados por el administrador **fuera de `apt`** |

En Ubuntu moderno, `/lib` es un enlace a `/usr/lib` (*usrmerge*). `dpkg` registra la ruta de `/usr/lib`; si `dpkg -S` no encuentra algo en `/lib`, se prueba con `/usr/lib`.

**Actualizaciones automáticas.** `unattended-upgrade` está activo por defecto en Ubuntu: cada madrugada instala los parches de seguridad. Lo que se instala fuera de los repositorios (un `.deb` descargado, `uv`) no lo actualiza.

**Kernel pendiente y `needrestart`.** Tras una instalación, `needrestart` revisa qué servicios siguen usando versiones viejas de bibliotecas y si el kernel en ejecución es anterior al instalado. Un kernel nuevo solo se carga al reiniciar.

**Paquetes huérfanos.** Un paquete instalado como dependencia que ya nadie necesita aparece como `no longer required`; `apt autoremove` lo quitaría.

## 6. Bibliotecas, cabeceras y compilación

**Compilar** es traducir un programa escrito en un lenguaje como C al código que entiende el procesador. Python no se compila, pero algunas librerías Python tienen partes en C por velocidad.

**Biblioteca:** código ya escrito que reutilizan muchos programas (`libpq`: cómo hablar con PostgreSQL).

| | Estática (`.a`) | Compartida (`.so`) |
|---|---|---|
| Cuándo se une al programa | Al compilar: se copia dentro | Al ejecutar: se busca en el sistema |
| El programa resultante | Más grande, autosuficiente | Más pequeño; depende de que la biblioteca esté instalada |
| Parche de seguridad | Hay que recompilar cada programa | Se actualiza un fichero y todos lo usan al reiniciarse |

Los programas piden un nombre con la versión de su interfaz (`libpq.so.5`), que es un enlace a la biblioteca real (`libpq.so.5.16`). Así se puede actualizar la biblioteca sin que los programas se enteren. Go compila por defecto en estático: un binario de Go funciona en un contenedor casi vacío.

**Cabecera (`.h`):** el índice de lo que ofrece una biblioteca: nombres de funciones, qué datos reciben y qué devuelven. No contiene el código. El compilador la necesita para traducir una llamada a esa biblioteca sin tener su código fuente; una vez compilado el programa, deja de hacer falta. C las usa porque resuelve todo antes de ejecutar; Python, que resuelve los `import` al ejecutar, no las necesita; Go y Rust leen la información directamente del paquete que importan.

**Paquetes `-dev`:** traen las cabeceras (y herramientas como `pg_config`) para **compilar** contra una biblioteca. El paquete sin `-dev` trae la biblioteca para **ejecutar**.

| Paquete | Contiene | Hace falta |
|---|---|---|
| `libpq5` | `libpq.so.5` | Siempre que un programa use PostgreSQL (`psql`, Odoo funcionando) |
| `libpq-dev` | `libpq-fe.h`, `pg_config` | Solo al compilar algo que use `libpq` (`psycopg2`) |
| `libpython3.12-dev` | `Python.h` | Al compilar extensiones en C de Python |
| `libldap-dev` | `lber.h` y demás cabeceras de LDAP | Al compilar `python-ldap` |

**Cadena de herramientas.** Un compilador es una cadena: `gcc` traduce C a ensamblador, `as` (ensamblador) lo convierte en código del procesador y `ld` (enlazador) lo une con las bibliotecas. `gcc` viene en `gcc-x86-64-linux-gnu` (y sus dependencias); `as` y `ld`, en `binutils`. El metapaquete `build-essential` trae la cadena completa (`gcc`, `g++`, `make`, `libc6-dev`). En el nombre `x86_64-linux-gnu-gcc`, la primera parte indica para qué sistema genera programas; los nombres con versión (`-13`) o con otro prefijo (`aarch64-...`) son otras versiones u otros procesadores.

## 7. Librerías Python: pip, PyPI y entornos virtuales

| | `apt` | `pip` / `uv pip` |
|---|---|---|
| Qué instala | Programas y bibliotecas del sistema | Librerías Python |
| De dónde | Repositorios de Ubuntu | PyPI (*Python Package Index*) |
| Dónde | Todo el sistema | Un entorno Python concreto |
| Lista de lo necesario | Dependencias del paquete | `requirements.txt` |

**Formatos en PyPI:** *wheel* (ya compilado: se copia) o código fuente (se compila en la máquina: hace falta compilador y paquetes `-dev`). Por eso, de las 65 librerías de Odoo 18, solo `psycopg2` y `python-ldap` necesitaron compilación.

`requirements.txt` solo puede listar librerías Python; no puede instalar un compilador ni cabeceras del sistema, que dependen del sistema operativo. Odoo documenta su parte de `apt` en `debian/control` y en `setup/debinstall.sh`, dentro de su código.

**Entorno virtual:** una carpeta con un enlace al Python del sistema y una carpeta propia para las librerías. No copia Python: cuando `apt` parchea el intérprete, el entorno lo usa sin tocar nada. Permite que un proyecto tenga sus versiones de librerías sin afectar al resto de la máquina.

**`uv`:** crea entornos (`uv venv`) e instala librerías (`uv pip install`, misma interfaz que `pip`), más rápido. No necesita el paquete `python3-venv` de Ubuntu. En un servidor:
- Debe usar el **Python del sistema**, no uno descargado por `uv`: una copia propia no recibiría los parches de `apt`.
- Se instala en `/usr/local/bin` para todos los usuarios, no en `~/.local/bin` de quien lo ejecuta.
- No viene de los repositorios: se actualiza a mano (`sudo uv self update`).

**Variables del instalador de `uv`** (docs.astral.sh/uv/reference/installer/):

| Variable | Efecto |
|---|---|
| `UV_INSTALL_DIR` | Dónde se instala el binario |
| `UV_NO_MODIFY_PATH` | No edita los ficheros de configuración de la shell (ni al instalar ni con `uv self update`) |
| `UV_UNMANAGED_INSTALL` | Instala en una ruta, no toca la shell y desactiva `uv self update`. Pensada para entornos efímeros (CI) |

**Clientes de PostgreSQL para Python:**

| Librería | Cómo habla con PostgreSQL | Compilación |
|---|---|---|
| `psycopg2` | Usa `libpq` del sistema | Sí (`libpq-dev`). La que exige Odoo 18 |
| `psycopg2-binary` | Lleva dentro su propia copia de `libpq` y OpenSSL | No. Desaconsejada en producción: los parches del sistema no le llegan |
| `psycopg` (v3) | Usa `libpq`; tiene variante precompilada | Opcional |
| `asyncpg` | Implementa el protocolo ella misma | No (FastAPI, código asíncrono) |
| `pg8000` | Python puro | No |

Python carga C de forma nativa porque el intérprete está escrito en C. Una biblioteca en Go solo podría usarse desde Python exponiéndose como C, con su cabecera. Cada lenguaje usa su propio cliente: en Go, `pgx`, que no usa `libpq`.

## 8. PostgreSQL preparado para un servicio

**Rol:** el usuario dentro de PostgreSQL. Para entrar sin contraseña por el socket, el rol debe llamarse igual que el usuario de Linux.

**Privilegios mínimos del rol `odoo`:** `CREATEDB` (Odoo crea y duplica bases desde su interfaz). Ni `SUPERUSER` (podría leer y borrar cualquier base y ejecutar comandos como `postgres`) ni `CREATEROLE`. Ser propietario de una base no es un privilegio que se otorgue: es la consecuencia de haberla creado.

**`pg_hba.conf`:** en Ubuntu, `/etc/postgresql/16/main/pg_hba.conf`. Cada fila es una regla; se leen de arriba abajo y se aplica **la primera que encaje** en las cuatro primeras columnas. Las líneas con `#` son comentarios.

| Columna | Significado | Valores habituales |
|---|---|---|
| `TYPE` | Por dónde llega la conexión | `local` (socket Unix), `host` (TCP) |
| `DATABASE` | A qué base | `all`, una concreta, `replication` |
| `USER` | Qué rol | `all` o uno concreto |
| `ADDRESS` | Desde qué IP (solo en `host`; vacía en `local`) | `127.0.0.1/32`, `::1/128` |
| `METHOD` | Cómo se comprueba la identidad | `peer`, `scram-sha-256` |

| Método | Funcionamiento |
|---|---|
| `peer` | Pregunta al sistema qué usuario de Linux hay al otro lado del socket y deja entrar como el rol del mismo nombre. Sin contraseña. Solo con `local` |
| `scram-sha-256` | Contraseña comprobada sin enviarla en claro |

Una fila se lee como: «si la conexión llega por TYPE, a la base DATABASE, como el rol USER, desde ADDRESS, compruébalo con METHOD».

Sin host, los programas que usan `libpq` se conectan por el socket Unix. Por eso Odoo no llevará host de base de datos en su configuración: entra por `peer` y no hay ninguna contraseña de base de datos guardada en un fichero. La fila `host ... 127.0.0.1/32` existe para programas que solo hablan TCP, como un túnel SSH desde otro equipo.

**PostgreSQL en Debian/Ubuntu va por versiones:** cada versión tiene su paquete (`postgresql-client-16`), sus programas en `/usr/lib/postgresql/16/bin/` y su configuración en `/etc/postgresql/16/main/`. `/usr/bin/psql` es un enlace a `pg_wrapper` (paquete `postgresql-client-common`), que lanza el `psql` de la versión adecuada.

## 9. Disposición de una instalación a mano

**Regla general: el código es de root; los datos, del usuario del servicio.**

| Pieza | Ruta | Dueño | Por qué |
|---|---|---|---|
| Código de Odoo | `/opt/odoo/src` | root | Solo modificable con `sudo`, de forma deliberada. Si alguien aprovecha un fallo de Odoo, no puede reescribir Odoo |
| Entorno virtual | `/opt/odoo/venv` | root | Igual que el código. Se puede borrar y recrear sin tocar el código |
| Datos (adjuntos, sesiones) | `/var/lib/odoo` | `odoo` | Odoo necesita escribir ahí. `/var/lib` es el sitio estándar para los datos que genera un programa |
| Configuración | `/etc/odoo/odoo.conf` | `root:odoo`, `640` | Contiene la contraseña maestra. `odoo` la lee; no puede modificarla. `/etc` es el sitio estándar de la configuración, un directorio por programa |
| `uv` | `/usr/local/bin/uv` | root | Instalado por el administrador fuera de `apt` |

Separar código, entorno y módulos propios evita que git vea el entorno como ficheros extraños y que una actualización de Odoo pise módulos propios.

**Usuario de sistema:** UID bajo, shell `nologin`, sin sesión. `sudo -u odoo comando` ejecuta un comando como ese usuario aunque tenga `nologin`, porque no abre una sesión.

**Clon superficial.** `--depth 1` descarga solo la última versión de cada fichero; el historial aparece como `grafted`. El commit desplegado se anota para poder reproducir la instalación exacta.

**`dubious ownership`.** Git se niega a trabajar en un repositorio que pertenece a otro usuario, porque podría llevar configuración que ejecute programas. Se ejecuta con `sudo` (como el dueño) o se declara de confianza con `safe.directory`.

## 10. Permisos de un fichero con secretos

Linux decide qué puede hacer un usuario con un fichero mirando tres categorías, en este orden, y aplica **la primera que encaja**:

| Categoría | Letra en `chmod` | Quién entra |
|---|---|---|
| Propietario | `u` (*user*) | Un único usuario |
| Grupo | `g` (*group*) | Los miembros del grupo del fichero |
| Otros | `o` (*others*) | Todos los demás |
| Las tres | `a` (*all*) | — |

Cada categoría tiene tres permisos. En `ls -l` aparecen como nueve caracteres, tres por categoría; en forma numérica, cada cifra es la suma de los permisos concedidos:

| Permiso | Letra | Valor | En un fichero | En un directorio |
|---|---|---|---|---|
| Leer | `r` | 4 | Ver el contenido | Listar lo que contiene |
| Escribir | `w` | 2 | Modificarlo | Crear y borrar dentro |
| Ejecutar | `x` | 1 | Ejecutarlo como programa | **Atravesarlo** para llegar a lo que hay dentro |
| Nada | `-` | 0 | | |

`chmod` admite dos formas:

| Forma | Ejemplo | Efecto |
|---|---|---|
| Numérica | `chmod 640` | **Fija** los nueve permisos: `rw-r-----` |
| Simbólica | `chmod o-r` | **Modifica** solo lo indicado (`+` añade, `-` quita, `=` fija esa categoría) y deja el resto como estaba |

Con la forma simbólica hay que saber de qué permisos se parte: `g+r` sobre un fichero que ya es `rw-r--r--` no cambia nada. `touch` crea los ficheros con `rw-r--r--`, legibles por todos.

**Patrón para un fichero de configuración con secretos:** propietario `root` (lectura y escritura), grupo el del servicio (solo lectura), otros nada → `root:servicio` con `640`. El servicio lee su configuración pero no la cambia; un usuario sin `sudo` no la ve. Los permisos se fijan **antes** de escribir el secreto.

**Atravesar directorios.** Para llegar a un fichero hay que tener `x` en **todos** los directorios de su ruta. Un directorio con `rwxr-x---` deja fuera a otros aunque lo que haya dentro tenga permisos más abiertos.

**Editar ficheros protegidos.** `sudoedit` copia el fichero a un temporal, lo abre con el editor del usuario normal y, al salir, lo copia encima del original **conservando propietario, grupo y permisos**. El editor no se ejecuta como root, a diferencia de `sudo vim`.

**Alias de la shell.** Si `ls` es un alias de un sustituto (como `eza`), su salida no es la estándar: puede ocultar el grupo o marcar los ficheros con `.` en lugar de `-`. `command ls` ejecuta el programa real. Con `sudo` delante también se ejecuta el real, porque los alias son de la shell y `sudo` no los conoce.

## 11. Opciones de Odoo: línea de comandos y `odoo.conf`

Odoo se ajusta con opciones de `odoo-bin`. Todas, menos unas pocas, pueden escribirse también en un fichero de configuración, que es la línea de comandos guardada de forma permanente.

**Cómo leer una opción en la referencia o en `--help`:**

| Trozo | Ejemplo | Significado |
|---|---|---|
| Forma corta | `-c` | Se escribe `-c valor` |
| Forma larga | `--config` | Se escribe `--config=valor` o `--config valor` |
| Hueco del valor | `<config>`, `CONFIG` | Lo que hay que poner; los `< >` no se escriben |

Las opciones van **detrás del programa al que pertenecen**. En `sudo -u odoo /opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin -c /etc/odoo/odoo.conf` hay tres programas encadenados: `-u odoo` es de `sudo`, Python no lleva opciones y `-c` es de Odoo. Una opción que espera valor no funciona sola.

**Formato del fichero:**

```ini
[options]
nombre = valor
```

- La sección `[options]` es obligatoria y va **en minúsculas**. Con `[Options]`, Odoo no encuentra la sección e ignora el fichero entero **sin dar error**.
- Los espacios alrededor de `=` son opcionales.

**Del nombre de la CLI al nombre del fichero:** se quita el `--` y los `-` pasan a `_` (`--http-interface` → `http_interface`). La referencia lista las excepciones; la que más aparece es `--database` → `db_name`. La fuente definitiva es `odoo/tools/config.py`: el valor de `dest=` de cada opción es su nombre en el fichero. Algunas opciones **solo existen en el fichero**, como `admin_passwd`.

**Qué fichero lee Odoo:** sin `-c`, `$HOME/.odoorc` del usuario que lo ejecuta. Con `-c RUTA`, ese. El log lo confirma con la línea `Using configuration file at RUTA`; si no aparece, Odoo está usando los valores por defecto. `--save` hace que Odoo escriba su configuración en el fichero: con `root:odoo 640`, no puede.

**Opciones de un despliegue básico:**

| En el fichero | Opción de la CLI | Valor por defecto | Para qué |
|---|---|---|---|
| `http_interface` | `--http-interface` | vacío = `0.0.0.0`, todas las interfaces | Dirección en la que escucha el servidor HTTP |
| `http_port` | `--http-port` (`-p`) | `8069` | Puerto HTTP |
| `addons_path` | `--addons-path` | Las dos carpetas de módulos del código, detectadas solas | Carpetas con módulos, separadas por comas. Si un módulo está en dos, gana la primera |
| `data_dir` | `--data-dir` | `$HOME/.local/share/Odoo` | Directorio de datos (§12) |
| `admin_passwd` | no existe | `admin` | Contraseña maestra del gestor de bases |
| `db_host`, `db_user`, `db_password` | `--db_host`, `--db_user`, `--db_password` | vacíos | Sin ellos: socket Unix y `peer` con el usuario que ejecuta Odoo |

Odoo añade siempre `DATA_DIR/addons/18.0` a las rutas de módulos, para los que se descargan desde la propia interfaz, y siempre incluye `odoo/addons`, los módulos base.

**Contraseña maestra.** Protege el gestor de bases (`/web/database/manager`): crear, duplicar, descargar copia, restaurar y borrar bases. **No** sirve para entrar en Odoo: para eso está el usuario de cada base. Con el valor por defecto, `admin`, el gestor avisa de que no está protegido. En el fichero puede ir en texto plano, protegida por los permisos, o cifrada.

## 12. Directorio de datos y *filestore*

Odoo guarda la información en dos sitios:

| Sitio | Qué guarda |
|---|---|
| PostgreSQL | Los registros: clientes, facturas, usuarios... y, para cada adjunto, una referencia a su fichero |
| Directorio de datos | Los ficheros: adjuntos, imágenes, PDF, recursos de la interfaz, y las sesiones |

Dentro del directorio de datos:

| Carpeta | Contenido |
|---|---|
| `filestore/NOMBRE_BASE/` | Adjuntos de esa base, uno por huella (*hash*), repartidos en subcarpetas con los dos primeros caracteres de la huella. Ficheros idénticos se guardan una sola vez |
| `sessions/` | Sesiones de los usuarios conectados |
| `addons/18.0/` | Módulos descargados desde la interfaz |

El *filestore* no se entiende sin la base: los ficheros no tienen su nombre original. **Base y *filestore* van juntos al backup**; uno sin el otro no restaura nada.

Es el único sitio donde el usuario del servicio necesita escribir. Si no se fija `data_dir`, Odoo crea el directorio por defecto la primera vez que arranca, aunque no se haya creado ninguna base.

## 13. Túnel SSH: reenvío de puertos

Un servicio que escucha en `127.0.0.1` del servidor no es accesible desde fuera. Para usarlo desde otro equipo sin abrir ningún puerto, se reenvía un puerto local a través de la conexión SSH:

```
ssh -N -L PUERTO_LOCAL:DESTINO:PUERTO_DESTINO SERVIDOR
```

| Parte | Significado |
|---|---|
| `-L` | Reenvío de puerto local: se abre `PUERTO_LOCAL` en el equipo desde el que se lanza |
| `PUERTO_LOCAL` | Cualquiera libre por encima de 1023. Si el habitual está ocupado, se elige otro; solo cambia la dirección del navegador |
| `DESTINO:PUERTO_DESTINO` | A dónde se conecta **el servidor** al recibir algo por el túnel. Se interpreta desde el servidor: `127.0.0.1` es el propio servidor |
| `-N` | Sin shell remota, solo el túnel. La terminal queda sin prompt; `Ctrl+C` lo cierra |

Camino de una petición:

| Tramo | Origen → destino | Lo que ve el servidor |
|---|---|---|
| Equipo local → servidor | IP pública de casa → `IP_servidor:22` | Una conexión SSH más |
| Dentro del servidor | `sshd` → `127.0.0.1:PUERTO_DESTINO` | Una conexión local |

Para el servicio, la petición llega desde `127.0.0.1`, enviada por `sshd`. Por eso el túnel funciona con servicios que solo aceptan conexiones locales, y la IP del cliente solo aparece en las conexiones del puerto 22.

Un servicio interno se queda en `127.0.0.1` de forma permanente: hoy se accede por túnel; más adelante, un proxy inverso en la misma máquina será la única puerta hacia fuera.

## 14. Odoo como servicio de systemd

**Por qué muere al cerrar la terminal.** Un programa lanzado a mano cuelga de la sesión SSH (en `status` aparecería bajo `user.slice/.../session-N.scope`). Al cerrarse la sesión, sus procesos reciben `SIGHUP` y mueren. Lanzado por systemd, cuelga de `system.slice/odoo.service` y no depende de ninguna sesión: es la línea `CGroup:` de `systemctl status`.

**Dónde va la unit.** systemd busca units en varias carpetas; la de más prioridad gana si hay dos con el mismo nombre:

| Carpeta | Quién escribe | Prioridad |
|---|---|---|
| `/etc/systemd/system/` | El administrador | La más alta |
| `/run/systemd/system/` | Units temporales; se borran al reiniciar | Media |
| `/usr/lib/systemd/system/` | Los paquetes de `apt` | La más baja |

Un servicio instalado a mano lleva su unit en `/etc/systemd/system/`; en `/usr/lib` podría pisarla una actualización. La carpeta es de root, así que la unit se crea con `sudo` y queda `root:root 644`: puede leerla cualquiera porque no contiene secretos (están en `odoo.conf`, `640`). La ruta desde la que systemd cargó una unit es la propiedad `FragmentPath`. Referencia: `man systemd.unit`, apartado `UNIT FILE LOAD PATH`.

**Del comando manual a la unit.** Cada parte del arranque manual tiene su directiva:

| Comando manual | Directiva | Sección |
|---|---|---|
| `sudo -u odoo` | `User=odoo` | `[Service]` |
| `/opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin -c /etc/odoo/odoo.conf` | `ExecStart=` con la línea completa: ejecutable y, detrás, sus argumentos | `[Service]` |

- `ExecStart=` admite argumentos separados por espacios, pero no es una shell: rutas completas y nada de `|`, `>` o `&` (`man systemd.service`, apartado `COMMAND LINES`).
- Los nombres de directiva y de sección distinguen mayúsculas: `Execstart=` o `[Instal]` se ignoran con un aviso y la unit queda incompleta.
- Sin `Group=`, se usa el grupo por defecto del usuario: `User=odoo` da `odoo:odoo`, igual que `sudo -u odoo`. Los grupos suplementarios salen de la base de usuarios (`man systemd.exec`, `User=, Group=`).

**`Type=`: cuándo se considera arrancado.** Odoo lanzado a mano no devuelve el prompt: se queda en primer plano. Corresponde a `simple` o `exec`, no a `forking` (programas que se van a segundo plano).

| Valor | Arrancado cuando | Ejecutable inexistente en `ExecStart=` |
|---|---|---|
| `simple` (por defecto) | En cuanto systemd crea el proceso | `start` dice que todo va bien; el fallo aparece después en `status` |
| `exec` | Cuando el ejecutable se ha lanzado de verdad | `start` falla en el acto |
| `forking` | Cuando el proceso inicial termina, dejando un hijo en segundo plano | — |

`exec` vigila el primer ejecutable de la línea (`python`). Si la ruta mal escrita es la de `odoo-bin`, Python sí arranca y el fallo se ve en el journal.

**Dependencia de PostgreSQL.** En Ubuntu hay dos units de PostgreSQL:

| Unit | Qué hace | Activa cuando |
|---|---|---|
| `postgresql.service` | Meta unit: interruptor para todos los clústeres. `Type=oneshot`, `ExecStart=/bin/true`, `RemainAfterExit=on` | Al instante, sin esperar a ningún servidor |
| `postgresql@16-main.service` | Instancia de la plantilla `postgresql@.service` para el clúster `16-main`: el servidor real | Cuando el servidor está arrancado y ha abierto el socket |

`After=postgresql.service` solo esperaría a `/bin/true`. La dependencia va sobre el clúster.

**Orden y relación son independientes.** Van las dos en `[Unit]`:

| En la unit de Odoo | `systemctl start odoo` con PostgreSQL parado |
|---|---|
| Solo `Wants=` | Arranca los dos a la vez; Odoo puede intentar conectar antes de que exista el socket |
| Solo `After=` | Arranca solo Odoo; `After=` no arrastra a nadie |
| `Wants=` + `After=` | Arranca PostgreSQL, espera a que esté activo y luego arranca Odoo |

`After=` hacia una unit que no existe (por una errata) no da error ni aviso: simplemente no hay orden.

**`Wants=` o `Requires=` para Odoo.** Lo decide cómo se comporta Odoo cuando PostgreSQL desaparece y vuelve:

| Corte de PostgreSQL | `Wants=` | `Requires=` |
|---|---|---|
| Durante el corte | Odoo sigue vivo; cada petición que necesita la base falla con error de conexión | Odoo se para |
| Cuando PostgreSQL vuelve | Odoo funciona solo: pide una conexión nueva en cada petición | Odoo sigue parado hasta un `start` manual |

Con `Requires=`, `Restart=on-failure` no rescata a Odoo, porque una parada por dependencia es limpia (`SIGTERM`). Como Odoo se reconecta solo, la elección es `Wants=`: cualquier reinicio de PostgreSQL (por ejemplo, el de una actualización automática de madrugada) dejaría Odoo parado con `Requires=`. Efecto secundario de un corte: las sesiones abiertas pueden cerrarse.

**`[Install]` y el target.** El target dice en qué etapa del arranque tiene que estar funcionando el servicio:

| Target | Representa | Para |
|---|---|---|
| `multi-user.target` | Sistema completo en modo texto: red, usuarios, servicios | Servicios de servidor |
| `graphical.target` | Lo anterior más el entorno gráfico | Escritorio |

Se averigua copiando de un servicio parecido (`systemctl cat postgresql.service` lleva `WantedBy=multi-user.target`), comprobando la etapa que alcanza la máquina (`systemctl get-default`) o en `man systemd.special`. Un target mal escrito habilita la unit contra algo que nunca se alcanza: no arranca sola.

**`systemd-analyze verify`.** Carga la unit como lo haría systemd y avisa de directivas o secciones desconocidas y de ejecutables inexistentes; sin avisos, no imprime nada. No comprueba que los argumentos tengan sentido: `-c /etc/odoo/odoo.` pasaría limpio. Esa comprobación la da el log de Odoo con `Using configuration file at`.

**Crear o modificar una unit a mano** exige `daemon-reload`: systemd trabaja con la copia que tiene en memoria hasta que vuelve a leer el disco. `systemctl edit --force --full` crea el fichero en `/etc/systemd/system/` y hace la recarga al guardar. Un cambio en `[Service]` solo lo recibe un proceso nuevo: `restart`.

**Log en el journal.** Sin `--logfile`, todo lo que escribe Odoo va al journal: un único sitio. Cada línea lleva dos horas: la del journal, en hora local, y la de Odoo, en UTC. Las peticiones pasadas por el túnel figuran `from 127.0.0.1`, porque quien conecta es `sshd`.

**`preset:` en `Loaded:`** es la política por defecto de la distribución para units nuevas, no el estado actual (`enabled`/`disabled`).

**Comparación con la unit del empaquetado Debian de Odoo** (`/opt/odoo/src/debian/odoo.service`):

| Directiva | Unit de Odoo | La propia | Motivo |
|---|---|---|---|
| `After=` / `Wants=` | `After=network.target` | `postgresql@16-main.service` | El paquete no sabe dónde estará la base; aquí está en la misma máquina |
| `Type=` | `simple` | `exec` | Detecta antes un ejecutable inexistente |
| `Group=` | Explícito | Implícito | Mismo resultado |
| `ExecStart=` | `/usr/bin/odoo --config ... --logfile /var/log/odoo/odoo-server.log` | Python del entorno, sin `--logfile` | Instalación a mano; log en el journal |
| `Restart=` | No tiene | `on-failure` | El paquete no reinicia Odoo si se cae |
| `UMask=` | No tiene (`0022`) | `0027` | §15 |
| `KillMode=` | `mixed` | No tiene (`control-group`) | Ver abajo |

`KillMode=` decide a quién envía `SIGTERM` systemd al parar: `control-group` (por defecto), a todos los procesos del servicio a la vez; `mixed`, solo al principal, que cierra a sus hijos de forma ordenada, y `SIGKILL` a todos si quedan procesos tras el tiempo de espera. Con Odoo en un solo proceso no hay diferencia; la hay con *workers*. Referencia: `man systemd.kill`.

## 15. Umask: los permisos de lo que se crea

Un programa que crea una carpeta pide normalmente `777` (`666` si es un fichero). Antes de crearla, el kernel le quita los permisos que indica la **umask** del proceso. La umask no concede nada: solo quita.

```
0  0  2  7
│  │  │  └─ otros
│  │  └──── grupo
│  └─────── propietario
└────────── cifra especial (casi siempre 0)
```

Cada cifra usa los valores de los permisos (`r` = 4, `w` = 2, `x` = 1) con el sentido contrario: lo que aparece se quita. `0` no quita nada, `2` quita escribir, `7` quita todo.

| umask | Carpeta nueva | Fichero nuevo | Grupo | Otros |
|---|---|---|---|---|
| `0002` | `775` `rwxrwxr-x` | `664` | Escribe | Lee |
| `0022` | `755` `rwxr-xr-x` | `644` | Lee | Lee |
| `0027` | `750` `rwxr-x---` | `640` | Lee | Nada |
| `0077` | `700` `rwx------` | `600` | Nada | Nada |

**De dónde la saca un proceso.** La hereda de quien lo lanza. La shell de un usuario de Ubuntu suele tener `0002`; un servicio de systemd recibe `0022` si la unit no dice otra cosa (`UMask=` en `man systemd.exec`). El mismo programa crea carpetas con permisos distintos según cómo se arranque. Odoo lanzado desde la shell creó `filestore` con `775`.

**Solo afecta a lo nuevo.** Cambiar la umask no toca lo que ya existe; para igualarlo se usa `chmod`.

**Por qué los demás pueden leer por defecto.** Es la tradición de Unix: casi todo es legible y solo se protege la escritura. Para datos privados hay que cerrarlos con algo: el directorio de arriba (sin `x` para otros, nadie lo atraviesa), la umask, o las dos cosas.

**Criterio para los datos de un servicio:** `0027`. Propietario escribe, grupo lee, otros nada: el mismo criterio que `/var/lib/odoo` (`750`) y `odoo.conf` (`640`). Los datos siguen cerrados aunque un día cambien los permisos del directorio de arriba, y el grupo del servicio queda como vía de solo lectura (por ejemplo, para un usuario de copias de seguridad) sin recurrir a root. Root no cuenta en este cálculo: lee y escribe cualquier cosa.

## 16. Dependencias externas de un módulo

Odoo se divide en el **núcleo** (el código de `/opt/odoo/src/odoo`) y en **módulos** (carpetas como `addons/account_peppol`). Un módulo puede necesitar bibliotecas de Python que el núcleo no trae. Las declara en su ficha, el fichero `__manifest__.py` de su carpeta:

```python
'external_dependencies': {
    'python': ['phonenumbers'],
},
```

Odoo lee esa clave al instalar el módulo. Si la biblioteca no está en el entorno de Odoo, la instalación se detiene con un error. Ese entorno es `/opt/odoo/venv`, no el Python del sistema.

| Concepto | Qué es | Dónde vive | Ejemplo |
|---|---|---|---|
| Módulo | Una funcionalidad de Odoo, con su código y su ficha | Carpeta con `__manifest__.py` | `account_peppol` |
| Biblioteca de Python | Código de terceros que el módulo importa | Paquete instalado en el entorno de Odoo | `phonenumbers` |
| Declaración | Lista de bibliotecas que el módulo exige | Clave `external_dependencies` del manifest | `'python': ['phonenumbers']` |

Que una biblioteca aparezca en `requirements.txt` del núcleo significa que Odoo la necesita para arrancar. Que aparezca solo en el manifest de un módulo significa que hace falta únicamente para ese módulo. Son dos listas distintas, y el error de instalación habla de la segunda.

## 17. Informes PDF: wkhtmltopdf

Odoo no genera los PDF por sí mismo. Monta cada informe como HTML y se lo entrega a un programa externo, **wkhtmltopdf**, que lo convierte en PDF. Si el programa no está, Odoo muestra el informe en HTML.

**El programa.** wkhtmltopdf funciona como un navegador sin ventana: carga la página y la dibuja en PDF. Su motor de dibujo es Qt WebKit, un componente antiguo. El proyecto está archivado desde 2023: no publica versiones nuevas ni corrige fallos. Odoo 18 lo sigue necesitando. No encontramos un sustituto incluido en el núcleo; las alternativas que existen son módulos de terceros, algunos de pago, y no se han evaluado.

**Dos builds.** El build de Ubuntu no lleva el parche de Qt y no pone cabecera ni pie en los PDF. El build oficial sí.

| | Build de Ubuntu | Build oficial |
|---|---|---|
| Nombre del paquete | `wkhtmltopdf` | `wkhtmltox` |
| Origen | Repositorio `universe` | Fichero `.deb` descargado de GitHub |
| Cabecera y pie | No | Sí |
| Actualizaciones con `apt` | Sí | No: está instalado desde un fichero |

**Qué versión.** El wiki oficial de Odoo recomienda la `0.12.6.1-3` para Odoo 16 y posteriores. Sus builds oficiales son para Debian y para Ubuntu desde la 16.04. La página de release no incluye un build para Ubuntu 24.04 (noble). El de Ubuntu 22.04 (jammy) funciona en noble, y así se comprobó generando un PDF en un VPS con noble.

**Cómo se ve la versión.** `wkhtmltopdf -V` muestra la versión y la leyenda `with patched qt` cuando es el build que Odoo necesita. En `apt policy` aparece `1:0.12.6.1-3.jammy`: el `1:` es el *epoch* de dpkg, un número que forma parte de la versión. No es un error.

**Estado de la integración.** Al arrancar, Odoo ejecuta `wkhtmltopdf --version` y guarda el resultado en una variable del módulo `base`. Los estados posibles, según la documentación interna de la clase:

| Estado | Significado |
|---|---|
| `install` | Estado inicial: no se encontró el programa |
| `upgrade` | El binario es anterior a la 0.12.0 |
| `ok` | Binario encontrado y con versión válida |
| `workers` | Odoo tiene exactamente un worker configurado; para PDF se piden al menos dos |
| `broken` | Hay un binario, pero no responde a `--version` |

Con el estado `install`, el informe se muestra en HTML y el navegador avisa. Con `ok`, se genera el PDF.

**Dónde se decide la dirección de los recursos.** wkhtmltopdf pide por HTTP los estilos, el logo y las fuentes que la página enlaza, igual que un navegador. Odoo escribe esas direcciones con `report.url` si tiene valor; si no, usa `web.base.url`. El proceso que genera el PDF corre en el servidor, así que la dirección tiene que ser alcanzable desde allí. Una dirección que solo existe en tu portátil, como la del túnel, no lo es.

**Permisos.** Odoo ejecuta wkhtmltopdf con el usuario de su servicio (`odoo`). Ese usuario tiene que poder ejecutar el binario, y se comprueba con `sudo -u odoo`.

**Nombres exactos.** Odoo lee solo `report.url`. Un parámetro llamado `web.report.url` no tiene efecto, aunque el nombre parezca correcto.

## 18. nginx como proxy inverso

**Servidor web.** Un programa que escucha en un puerto (80 para HTTP, 443 para HTTPS) y atiende peticiones HTTP. Puede servir ficheros del disco o reenviar las peticiones a otro programa.

**Proxy.** Un intermediario: recibe una petición, la hace en nombre de otro y devuelve la respuesta. Los dos extremos no hablan directamente.

| | Proxy directo (*forward*) | Proxy inverso (*reverse*) |
|---|---|---|
| Trabaja para | Los clientes | Los servidores |
| Dónde está | Cerca de los clientes (la red de una empresa) | Cerca de los servidores (el VPS) |
| Quién sabe que existe | El cliente lo configura a propósito | El cliente no lo sabe: cree que habla con el servidor |
| Qué oculta | Al cliente: el servidor ve la IP del proxy | Al servidor: el cliente solo ve el proxy |
| Ejemplo | Proxy de oficina que filtra webs | nginx delante de `labweb` u Odoo |

**Por qué un proxy delante de Odoo** en lugar de hacer que Odoo escuche en `0.0.0.0:80`:

- Los puertos por debajo de 1024 requieren privilegios de root, y Odoo corre como `odoo`, sin privilegios.
- nginx se encarga de HTTPS con el certificado; Odoo sigue hablando HTTP en local.
- Una IP y un puerto 80 pueden llevar a programas distintos según el nombre pedido (`server_name`).
- La documentación de Odoo (*Deploying Odoo*) asume un proxy delante.

### Estructura de la configuración

El fichero principal es `/etc/nginx/nginx.conf`. Tiene **directivas simples** (`nombre valor;`, siempre terminadas en `;`) y **bloques** (`nombre { … }`). Un bloque es un **contexto**, y cada directiva solo vale en ciertos contextos.

| Contexto | Qué contiene |
|---|---|
| Principal (fuera de todo bloque) | Ajustes globales: `user www-data`, `error_log`, `include` de módulos |
| `events { }` | Cómo atiende conexiones (`worker_connections`) |
| `http { }` | Todo lo de HTTP: logs de acceso, tipos de fichero y los sitios |
| `server { }` (dentro de `http`) | Un sitio: en qué puerto escucha y para qué nombre |
| `location { }` (dentro de `server`) | Qué hacer con las peticiones de una ruta |

`include` inserta el contenido de otros ficheros en ese punto. `nginx.conf` de Ubuntu tiene cuatro:

| Línea | Contexto | Qué carga |
|---|---|---|
| `include /etc/nginx/modules-enabled/*.conf;` | Principal | Módulos: extensiones de nginx. Vacío en una instalación básica |
| `include /etc/nginx/mime.types;` | `http` | Tabla de tipos de contenido por extensión (`.html`, `.png`…) |
| `include /etc/nginx/conf.d/*.conf;` | `http` | Ajustes HTTP comunes. Vacío por defecto |
| `include /etc/nginx/sites-enabled/*;` | `http` | **Los sitios**, un fichero cada uno |

### Sitios disponibles y sitios activos

Organización propia de Debian y Ubuntu; para nginx solo existe la línea `include /etc/nginx/sites-enabled/*;`.

| Directorio | Contiene | Significado |
|---|---|---|
| `sites-available/` | Los ficheros de configuración reales | Sitios escritos, activos o no |
| `sites-enabled/` | Enlaces simbólicos a ficheros de `sites-available/` | Sitios activos: los únicos que carga nginx |

- **Activar** un sitio = crear en `sites-enabled/` un enlace simbólico a su fichero de `sites-available/`.
- **Desactivar** = borrar el enlace (`rm` o `unlink`). El fichero original queda intacto.

Un **enlace simbólico** es un fichero que apunta a otra ruta, como un acceso directo. En `ls -l` empieza por `l` y muestra `nombre -> destino`. Borrarlo no borra el destino. Con `ln -s`, el primer argumento es el destino y el segundo el enlace; con ruta absoluta en el destino, el enlace no depende del directorio desde el que se cree.

**El paquete deja un sitio activo.** Al instalarse, nginx arranca, queda habilitado y activa `default`: escucha en el 80 con `default_server` y sirve ficheros de `/var/www/html`, la página «Welcome to nginx!». Los puertos los abre cada sitio con su `listen`: sin ningún sitio activo, nginx sigue en marcha pero no escucha en ningún puerto.

### Las directivas de un sitio proxy

| Directiva | Contexto | Qué hace |
|---|---|---|
| `listen 80;` | `server` | Escucha en el puerto 80 de todas las direcciones IPv4 |
| `listen [::]:80;` | `server` | Lo mismo en IPv6. `[::]` = todas las direcciones IPv6; los corchetes separan la dirección (que lleva `:`) del puerto |
| `server_name NOMBRE;` | `server` | Para qué nombre de dominio es el sitio. Sin él, o con `_`, no corresponde a ninguno concreto |
| `location / { }` | `server` | Agrupa lo que se hace con las rutas que empiezan por `/` |
| `proxy_pass http://127.0.0.1:8080;` | `location` | Reenvía la petición a esa dirección |

`listen` acepta un puerto (`80`) o una dirección con puerto (`0.0.0.0:80`, `[::]:80`). `listen :80;` no es válido. Con un solo sitio, `default_server` no hace falta: ese sitio atiende todas las peticiones.

**`location` compara por prefijo.** La ruta viaja en la primera línea de la petición (`GET /health HTTP/1.1`). `location /` encaja con cualquier ruta que empiece por `/`, es decir, con todas. Con varias `location`, nginx elige el prefijo más largo que encaje.

**`127.0.0.1` y no `localhost` en `proxy_pass`.** `localhost` es un nombre y en Ubuntu resuelve a `127.0.0.1` y a `::1` (`/etc/hosts`). Si el servicio solo escucha en `127.0.0.1`, nginx puede probar antes `::1`, fallar y dejar errores en el log. Regla: en `proxy_pass`, la misma dirección en la que escucha el servicio según `ss`.

### El recorrido de una petición

1. El cliente pide `http://89.58.45.111`. Sin puerto en la URL, `http://` implica el 80; lo decide el cliente.
2. El kernel del VPS recibe el SYN para el 80 y entrega la conexión a nginx, que escucha allí.
3. nginx lee la ruta, la encaja en una `location` y abre **una segunda conexión TCP**, desde el propio VPS, hacia la dirección de `proxy_pass`.
4. El servicio de detrás responde a nginx, y nginx reenvía la respuesta al cliente.

Consecuencias de que haya dos conexiones:

- El servicio de detrás ve como origen `127.0.0.1`, no la IP del visitante. nginx sí la conoce.
- La cabecera `Server:` de la respuesta la pone nginx, aunque el cuerpo sea del servicio.
- Las versiones de HTTP pueden diferir a cada lado: por defecto nginx habla HTTP/1.0 con el servicio de detrás y HTTP/1.1 con el cliente.

### Aplicar cambios

nginx lee la configuración al arrancar y la guarda en memoria. Cambiar ficheros, crear enlaces o borrarlos no tiene efecto hasta que se le pide releerla.

| Acción | Qué hace | Cuándo |
|---|---|---|
| `nginx -t` | Lee toda la configuración, incluidos los `include`, y comprueba la sintaxis sin tocar el nginx en marcha | Siempre, antes de recargar |
| `reload` | El maestro relee la configuración y sustituye a los *workers* sin cortar conexiones. Si la configuración nueva tiene errores, la rechaza y sigue con la anterior | Tras cualquier cambio |
| `restart` | Para nginx por completo y lo arranca | Casi nunca. Corta conexiones, y con un error en la configuración nginx no vuelve a arrancar |

`nginx -t` comprueba la sintaxis, pero no abre puertos: un `listen` en un puerto ocupado pasa la prueba y falla al recargar.

**Procesos.** Un **maestro**, de root, que lee la configuración y abre los puertos, y varios ***workers***, del usuario de `user` (`www-data`), que atienden las conexiones. En un reload, el PID del maestro se mantiene y cambian los de los *workers*; en un restart cambian todos.

### Errores: dónde está el fallo

| Lo que ve el cliente | Dónde está el problema |
|---|---|
| `Connection refused` | Nadie escucha en el puerto de entrada: nginx parado o ningún sitio con ese `listen` |
| `502 Bad Gateway` | nginx funciona; el servicio de detrás no responde. *Gateway* es nginx haciendo de pasarela |

El 502 dice *dónde* mirar; la causa está en `/var/log/nginx/error.log`. Las peticiones atendidas se registran en `/var/log/nginx/access.log`.

| Fragmento de una línea de `error.log` | Significado |
|---|---|
| `[error]` | Nivel de gravedad (`[notice]` es informativo) |
| `connect() failed (111: Connection refused)` | La causa: el kernel rechazó la conexión de nginx con el servicio |
| `while connecting to upstream` | *Upstream* = el servicio de detrás |
| `upstream: "http://127.0.0.1:8080/"` | A qué dirección intentaba conectar: identifica qué servicio falla |
| `client: IP` | La IP pública del visitante |
| `server: ` | El `server_name` del sitio; vacío si no tiene |

Orden de diagnóstico de un 502: `curl` (confirma el 502) → `error.log` (causa y `upstream`) → `systemctl status` del servicio (parado o caído) → `ss` (si alguien escucha en su puerto) → `journalctl -u` del servicio (por qué se cayó).

---

# Parte 2 · Ejemplos

## La red del VPS

| Dato | Valor |
|---|---|
| Interfaz | `eth0` (también `ens3`, `enp0s3`), MAC `c6:56:77:3a:fc:4c` |
| IPv4 pública | `89.58.45.111/22` → registro `A` |
| IPv6 pública | `2a03:4000:67:5e2:c456:77ff:fe3a:fc4c/64` → registro `AAAA` |
| Puerta de enlace IPv4 | `89.58.44.1` (virtual, VRRP); routers físicos `89.58.44.2` y `89.58.44.3` |
| Puerta de enlace IPv6 | `fe80::1` (virtual) |
| Configuración | Estática, generada por cloud-init, aplicada por systemd-networkd |

El final de la IPv6 (`c456:77ff:fe3a:fc4c`) está construido a partir de la MAC, con `ff:fe` insertado en medio.

```yaml
# /etc/netplan/50-cloud-init.yaml (permisos 600, root)
network:
  version: 2
  ethernets:
    eth0:
      match:
        macaddress: "c6:56:77:3a:fc:4c"
      addresses:
      - "89.58.45.111/22"
      - "2a03:4000:67:5e2:c456:77ff:fe3a:fc4c/64"
      routes:
      - to: "default"
        via: "89.58.44.1"
      - on-link: true
        to: "default"
        via: "fe80::1"
```

```ini
# /run/systemd/network/10-netplan-eth0.network (generado por netplan; no editar)
[Match]
PermanentMACAddress=c6:56:77:3a:fc:4c

[Network]
LinkLocalAddressing=ipv6
Address=89.58.45.111/22
Address=2a03:4000:67:5e2:c456:77ff:fe3a:fc4c/64

[Route]
Destination=0.0.0.0/0
Gateway=89.58.44.1

[Route]
Destination=::/0
Gateway=fe80::1
GatewayOnLink=true
```

`LinkLocalAddressing=ipv6` lo añade netplan: crea la dirección `fe80::` pero no la de enlace local IPv4 (`169.254.x.x`).

```
# ip route show
default via 89.58.44.1 dev eth0 proto static
89.58.44.0/22 dev eth0 proto kernel scope link src 89.58.45.111
```

```
# ip neighbour show (fragmento)
89.58.44.1 dev eth0 lladdr 00:00:5e:00:01:01 REACHABLE      ← IP virtual (VRRP)
89.58.44.2 dev eth0 lladdr bc:0f:fe:37:fb:a2 STALE          ← router físico A
89.58.44.3 dev eth0 lladdr bc:0f:fe:33:fc:e2 STALE          ← router físico B
fe80::1    dev eth0 lladdr 00:00:5e:00:02:02 router STALE   ← IP virtual IPv6
```

Camino desde el VPS hasta `1.1.1.1`: red de Netcup (saltos 1–2), Arelion/`twelve99.net` como tránsito (Núremberg → Fráncfort), interconexión con Cloudflare y red de Cloudflare.

## Qué escucha en el VPS

| Puerto | Programa | Dirección local | Desde fuera |
|---|---|---|---|
| 22/TCP | `sshd` (y `systemd`, PID 1, por `ssh.socket`) | `0.0.0.0`, `[::]` | Sí |
| 80/TCP | `nginx` (maestro y dos *workers*) | `0.0.0.0`, `[::]` | Sí |
| 8080/TCP | `labweb` | `127.0.0.1` | No; a través de nginx por el 80 |
| 8069/TCP | Odoo (`python`, como `odoo`) | `127.0.0.1` | No; por túnel SSH |
| 5432/TCP | `postgres` | `127.0.0.1`, `[::1]` | No |
| 53/TCP y UDP | `systemd-resolve` | `127.0.0.53`, `127.0.0.54` | No |
| Socket Unix | `postgres` | `/var/run/postgresql/.s.PGSQL.5432` | No |

Prueba de la dirección local: `curl http://127.0.0.1:8080` en el VPS responde; `curl http://89.58.45.111:8080` desde el portátil falla. Mismo programa y puerto, distinta dirección de llegada.

## Reglas de `pg_hba.conf` en Ubuntu 24.04

```
local   all          postgres                 peer
local   all          all                      peer
host    all          all       127.0.0.1/32   scram-sha-256
host    all          all       ::1/128        scram-sha-256
local   replication  all                      peer
host    replication  all       127.0.0.1/32   scram-sha-256
host    replication  all       ::1/128        scram-sha-256
```

No hay ninguna fila `host` con direcciones externas: aunque PostgreSQL escuchara en `0.0.0.0`, rechazaría a quien llegara de fuera.

| Conexión | Regla que encaja | Resultado |
|---|---|---|
| `sudo -u odoo psql -l` (socket) | `local all all peer` | Entra sin contraseña |
| `sudo -u odoo psql -h 127.0.0.1 -l` (TCP) | `host all all 127.0.0.1/32 scram-sha-256` | Pide contraseña; `odoo` no tiene |

## Origen de PostgreSQL 16

```
postgresql-16:
  Installed: 16.15-0ubuntu0.24.04.1
  Candidate: 16.15-0ubuntu0.24.04.1
  Version table:
 *** 16.15-0ubuntu0.24.04.1 500
        500 http://at.archive.ubuntu.com/ubuntu noble-updates/main amd64 Packages
        500 http://security.ubuntu.com/ubuntu noble-security/main amd64 Packages
        100 /var/lib/dpkg/status
     16.2-1ubuntu4 500
        500 http://at.archive.ubuntu.com/ubuntu noble/main amd64 Packages
```

Repositorios oficiales de Ubuntu, componente `main`, al día. `100 /var/lib/dpkg/status` es el registro local de lo instalado. Los números `500`/`100` son prioridades entre repositorios.

Cadena de `psql`:

```
psql → /usr/bin/psql                           (enlace; postgresql-client-common)
     → /usr/share/postgresql-common/pg_wrapper (elige la versión)
     → /usr/lib/postgresql/16/bin/psql         (programa real; postgresql-client-16)
     → necesita libpq.so.5                     (ldd)
     → /usr/lib/x86_64-linux-gnu/libpq.so.5    (enlace a libpq.so.5.16; paquete libpq5)
```

Un enlace relativo (`../share/...`) se resuelve desde el directorio donde está el enlace (`/usr/bin`), no desde el propio enlace.

## Historial de `apt`

```
# grep -E 'Start-Date|Commandline|Requested-By' /var/log/apt/history.log (fragmento)
Start-Date: 2026-10-07  06:40:38
Commandline: /usr/bin/unattended-upgrade
Start-Date: 2026-10-07  13:19:45
Commandline: apt upgrade
Requested-By: miguel (1000)
```

Las operaciones sin `Requested-By` las lanza el sistema. El historial se rota: los meses anteriores están en `history.log.1.gz` y siguientes.

## Instalación de las librerías de Odoo: fallos en orden

| Error en la salida | Fichero que falta | Paquete (`apt-file`) |
|---|---|---|
| `No such file or directory: 'x86_64-linux-gnu-gcc'` | El compilador | `gcc-x86-64-linux-gnu` (arrastró 25 paquetes) |
| `fatal error: Python.h: No such file or directory` | Cabecera de Python | `libpython3.12-dev` |
| `fatal error: lber.h: No such file or directory` | Cabecera de LDAP | `libldap-dev` |
| `libpq-fe.h` no encontrado | Cabecera de `libpq` | `libpq-dev` |
| `cannot execute 'as': execvp: No such file or directory` | El ensamblador | `binutils` |

Resultado final: `Built psycopg2==2.9.9`, `Built python-ldap==3.4.4`, `Installed 65 packages`.

En la salida de `psycopg2` aparece la sugerencia de instalar `psycopg2-binary` para evitar la compilación. En producción no se sigue (ver §7).

**Método para pasar de un error de compilación al paquete:**
1. Buscar el último `error:`. Si solo dice que un comando terminó con fallo, subir hasta el `fatal error`.
2. Quedarse con el nombre del fichero que falta.
3. `apt-file search --regexp '/NOMBRE$'` (o `'/bin/NOMBRE$'` si es un programa).
4. Elegir la línea que encaja con el sistema: ruta en `/usr/bin`, versión `python3.12`, sin sufijo de otra versión ni prefijo de otra arquitectura.

Atajos válidos: leer el `hint:` del final (`uv` suele indicar qué cabecera falta) o buscar el `fatal error` literal en internet. Los `UserWarning` y `SetuptoolsDeprecationWarning` de la salida son avisos para los autores de la librería: ruido.

## `odoo.conf` del VPS

```ini
# /etc/odoo/odoo.conf (root:odoo, 640)
[options]
http_interface=127.0.0.1
addons_path=/opt/odoo/src/addons,/opt/odoo/src/odoo/addons
data_dir=/var/lib/odoo
admin_passwd=CONTRASEÑA_MAESTRA
```

| Línea | Opción de la CLI | Sin ella |
|---|---|---|
| `http_interface=127.0.0.1` | `--http-interface` | `0.0.0.0`: el gestor de bases, abierto a internet |
| `addons_path=...` | `--addons-path` | Las mismas dos rutas, detectadas solas |
| `data_dir=/var/lib/odoo` | `--data-dir` | `/var/lib/odoo/.local/share/Odoo` |
| `admin_passwd=...` | no existe | `admin` |

No lleva `db_host`, `db_user` ni `db_password`: Odoo entra en PostgreSQL por el socket como `odoo`, con `peer`. La contraseña maestra se generó con `openssl rand -base64 24` y está guardada en el gestor de contraseñas.

```
# command ls -l /etc/odoo/odoo.conf (tras chown y chmod, antes de escribirlo)
-rw-r----- 1 root odoo 0 Oct  9 18:28 /etc/odoo/odoo.conf
```

| Usuario | Categoría | `cat /etc/odoo/odoo.conf` |
|---|---|---|
| `miguel` | otros | `Permission denied` |
| `odoo` (`sudo -u odoo cat ...`) | grupo | Muestra el contenido |
| `miguel` con `sudo` | root, propietario | Muestra el contenido |

## Arranque sin fichero y con fichero

```
# sudo -u odoo /opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin   (fragmento, sin fecha ni PID)
INFO ? odoo: Odoo version 18.0
INFO ? odoo: addons paths: ['/opt/odoo/src/odoo/addons', '/var/lib/odoo/.local/share/Odoo/addons/18.0', '/opt/odoo/src/addons']
INFO ? odoo: database: default@default:default
INFO ? odoo.addons.base.models.ir_actions_report: You need Wkhtmltopdf to print a pdf version of the reports.
INFO ? odoo.service.server: HTTP service (werkzeug) running on backend-lab:8069
```

```
# sudo -u odoo /opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin -c /etc/odoo/odoo.conf   (fragmento)
INFO ? odoo: Odoo version 18.0
INFO ? odoo: Using configuration file at /etc/odoo/odoo.conf
INFO ? odoo: addons paths: ['/opt/odoo/src/odoo/addons', '/var/lib/odoo/addons/18.0', '/opt/odoo/src/addons']
INFO ? odoo: database: default@default:default
INFO ? odoo.addons.base.models.ir_actions_report: You need Wkhtmltopdf to print a pdf version of the reports.
INFO ? odoo.service.server: HTTP service (werkzeug) running on localhost:8069
```

| Línea del log | Qué comprobar |
|---|---|
| `Using configuration file at` | Que Odoo ha leído el fichero. Si falta, usa los valores por defecto |
| `addons paths` | La ruta `.../addons/18.0` revela el `data_dir` en uso |
| `database: usuario@host:puerto` | `default@default:default` = socket Unix y `peer` con el usuario del sistema |
| `running on` | Nombre de la máquina = todas las interfaces; `localhost` = solo `127.0.0.1` |
| `You need Wkhtmltopdf` | Falta el generador de PDF. No impide arrancar |

Comprobación desde fuera de Odoo, con `ss`:

```
LISTEN 0 128 0.0.0.0:8069   0.0.0.0:*                                    ← sin opciones (ss -tl)
LISTEN 0 128 127.0.0.1:8069 0.0.0.0:* users:(("python",pid=13166,fd=3)) ← con fichero
```

El proceso es `python`, no `odoo`: el programa es el intérprete y `odoo-bin` es el fichero que lee. El PID coincide con el que aparece en cada línea del log.

## Túnel al Odoo del VPS

```
# Portátil, terminal propia (no dentro del VPS)
ssh -N -L 10000:127.0.0.1:8069 vps
# Navegador del portátil: http://localhost:10000
```

El puerto local es `10000` porque el `8069` del portátil lo ocupa un contenedor. Con `sudo ss -tnp` en el VPS se ven tres conexiones `ESTAB` en `:22` desde la IP de casa: dos terminales y el túnel. Las conexiones a `:8069` solo existen mientras hay una petición en curso, y tienen `sshd` en un extremo y `python` en el otro, ambos en `127.0.0.1`.

## Directorio de datos tras crear la primera base

Base creada desde el gestor: `test-db`, sin datos de demostración.

```
# sudo ls -l /var/lib/odoo
drwx------ 3 odoo odoo 4096 Oct  9 19:16 addons
drwxrwxr-x 3 odoo odoo 4096 Oct  9 19:23 filestore
drwx------ 5 odoo odoo 4096 Oct  9 19:26 sessions

# sudo ls -l /var/lib/odoo/filestore
drwxrwxr-x 59 odoo odoo 4096 Oct  9 19:26 test-db
```

El `59` son los enlaces del directorio: subcarpetas + 2, es decir, 57 carpetas de huellas con los recursos de la interfaz que se guardan al crear la base. `filestore` es `rwxrwxr-x`, pero `/var/lib/odoo` es `rwxr-x---`, así que otros no pueden llegar a él.

El directorio por defecto del primer arranque, `/var/lib/odoo/.local/share/Odoo`, solo tenía `addons/18.0` y `sessions` vacíos, sin `filestore`; se revisó con `sudo ls -laR` y se borró.

## `odoo.service` del VPS

```ini
# /etc/systemd/system/odoo.service (root:root, 644)
[Unit]
Description=Odoo service
After=postgresql@16-main.service
Wants=postgresql@16-main.service

[Service]
User=odoo
ExecStart=/opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin -c /etc/odoo/odoo.conf
Type=exec
UMask=0027
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Borrador con cuatro fallos antes de crearlo, ninguno de los cuales señalaría systemd con claridad: `-c /etc/odoo/odoo.` (Odoo arrancaría con valores por defecto: todas las interfaces, contraseña maestra `admin`), falta de `Type=exec` (se usaría `simple`), `[Instal]` (sección ignorada; `enable` diría que no hay `[Install]`) y `multi-user.targ` (habilitada contra un target inexistente).

## Estado del servicio recién arrancado

```
# systemctl status odoo
● odoo.service - Odoo service
     Loaded: loaded (/etc/systemd/system/odoo.service; disabled; preset: enabled)
     Active: active (running) since Sat 2026-10-10 16:04:46 CEST; 6s ago
   Main PID: 27284 (python)
     CGroup: /system.slice/odoo.service
             └─27284 /opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin -c /etc/odoo/odoo.conf

... systemd[1]: Started odoo.service - Odoo service.
... python[27284]: 2026-10-10 14:04:48,862 27284 INFO ? odoo: Using configuration file at /etc/odoo/odoo.conf
... python[27284]: 2026-10-10 14:04:49,560 27284 INFO ? odoo.service.server: HTTP service (werkzeug) running on localhost:8069
```

| Qué mirar | Qué dice |
|---|---|
| `disabled` | Arrancada, pero no volvería sola tras reiniciar (antes del `enable`) |
| `preset: enabled` | Política por defecto de Ubuntu, no el estado actual |
| `CGroup: /system.slice/odoo.service` | Cuelga de systemd, no de la sesión SSH |
| `Using configuration file at` | El `-c` de `ExecStart=` llega |
| `running on localhost:8069` | Respeta `http_interface=127.0.0.1` |
| `16:04:48` / `14:04:48` | Mismo instante: hora local del journal y UTC de Odoo |

## Corte de PostgreSQL con `Wants=`

Con Odoo en marcha, `journalctl -u odoo -f` en una terminal y en otra:

```
sudo systemctl stop postgresql@16-main
systemctl status odoo                      # active (running)
```

Al recargar Odoo en el navegador, el journal muestra errores de conexión con la base. Después:

```
sudo systemctl start postgresql@16-main
```

Sin tocar Odoo, la página vuelve a funcionar; la sesión del usuario se había cerrado durante el corte.

## Orden de arranque tras reiniciar

```
# journalctl -b -u postgresql@16-main -u odoo | grep -E 'Starting|Started'
Oct 10 16:38:05 backend-lab systemd[1]: Starting postgresql@16-main.service - PostgreSQL Cluster 16-main...
Oct 10 16:38:08 backend-lab systemd[1]: Started postgresql@16-main.service - PostgreSQL Cluster 16-main.
Oct 10 16:38:08 backend-lab systemd[1]: Starting odoo.service - Odoo service...
Oct 10 16:38:08 backend-lab systemd[1]: Started odoo.service - Odoo service.
```

PostgreSQL tarda tres segundos en arrancar y Odoo no empieza hasta que termina: es `After=`. Sin ella, los dos `Starting` saldrían a la vez.

## Inicio de sesión en el journal

```
# journalctl -u odoo -S '15 min ago' | grep -i login
... INFO test-db werkzeug: 127.0.0.1 - - [10/Oct/2026 14:10:44] "GET /web/login?redirect=/odoo? HTTP/1.1" 200 - ...
... INFO test-db odoo.addons.base.models.res_users: Login successful for db:test-db login:test-db@correo.es from 127.0.0.1
... INFO test-db werkzeug: 127.0.0.1 - - [10/Oct/2026 14:10:49] "POST /web/login HTTP/1.1" 303 - ...
```

La línea del inicio de sesión es la de `res_users`. Las de `werkzeug`, el servidor web interno, son las peticiones HTTP: `GET` de la página de login (`200`, servida) y `POST` con las credenciales (`303`, redirección tras entrar).

## Permisos del directorio de datos tras `UMask=0027`

```
# systemctl show -p UMask odoo
UMask=0022                                  # sin UMask= en la unit
UMask=0027                                  # con UMask=0027, tras daemon-reload y restart

# sudo ls -ld /var/lib/odoo/filestore /var/lib/odoo/filestore/test-db   (tras el restart)
drwxrwxr-x  3 odoo odoo 4096 Oct  9 19:23 /var/lib/odoo/filestore
drwxrwxr-x 59 odoo odoo 4096 Oct  9 19:26 /var/lib/odoo/filestore/test-db

# sudo chmod -R g-w,o-rwx /var/lib/odoo
# sudo ls -ld /var/lib/odoo/filestore /var/lib/odoo/filestore/test-db
drwxr-x---  3 odoo odoo 4096 Oct  9 19:23 /var/lib/odoo/filestore
drwxr-x--- 59 odoo odoo 4096 Oct  9 19:26 /var/lib/odoo/filestore/test-db
```

La umask nueva no cambió las carpetas que ya existían; el `chmod` las igualó al criterio `0027`.

## Dependencia de un módulo sin su biblioteca

Al instalar la aplicación de Ventas, Odoo intenta instalar `account_peppol` y falla con este mensaje:

```
No es posible instalar el módulo "account_peppol".
External dependency phonenumbers not installed: No package metadata was found for phonenumbers
```

Diagnóstico, en la terminal SSH del VPS. Primero, si el núcleo la pide:

```
grep -i phonenumbers /opt/odoo/src/requirements.txt
```

No devuelve nada. Después, la declaración del módulo:

```
grep -n -A 3 'external_dependencies' /opt/odoo/src/addons/account_peppol/__manifest__.py
```

```
'external_dependencies': {
    'python': ['phonenumbers']
},
```

Solución, en el mismo VPS:

```
sudo uv pip install --python /opt/odoo/venv/bin/python phonenumbers
```

Tras la instalación, la aplicación de Ventas se instaló sin reiniciar `odoo.service`.

## Informe en HTML y en PDF

Arranque con el programa encontrado (fragmento, sin fecha ni PID):

```
INFO odoo.addons.base.models.ir_actions_report: Will use the Wkhtmltopdf binary at /usr/local/bin/wkhtmltopdf
INFO odoo.addons.base.models.ir_actions_report: Will use the Wkhtmltoimage binary at /usr/local/bin/wkhtmltoimage
```

Arranque sin el programa:

```
INFO odoo.addons.base.models.ir_actions_report: You need Wkhtmltopdf to print a pdf version of the reports.
```

Al imprimir sin el programa, el navegador muestra:

> No se ha podido encontrar Wkhtmltopdf en este sistema. El informe será mostrado en HTML.

y el log registra una petición que termina en `/report/html/`:

```
"GET /report/html/sale.report_saleorder/21?context=... HTTP/1.1" 200
```

## PDF sin logo ni cabecera

El PDF se genera, pero sin logo, sin cabecera y sin líneas de tabla. El pie «Página 1 / 1» sí aparece. La causa estaba en `web.base.url`, con el valor `http://localhost:10000`: esa dirección solo existe en el portátil, mientras el túnel está abierto. El PDF lo genera el VPS, que no puede llegar a ella.

El parámetro `web.report.url`, creado por error, no lo lee el código: Odoo busca solo `report.url`. Con la clave `report.url` y el valor `http://127.0.0.1:8069`, el PDF salió completo, con logo, cabecera, estilos y pie.

## Aviso que persiste tras instalar el programa

Tras instalar el build oficial y reiniciar `odoo.service`, el aviso «No se ha podido encontrar Wkhtmltopdf» siguió apareciendo en la página del presupuesto. Desde la consola de Odoo, el estado devolvía `'ok'`. Al recargar la página y repetir la impresión, el PDF se generó. La causa no quedó establecida; lo más probable es que la página ya cargada conservara el aviso de antes.

## Estado de la integración desde la consola de Odoo

En la terminal SSH del VPS:

```
sudo -u odoo /opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin shell -c /etc/odoo/odoo.conf -d test-db --no-http
```

Dentro de la consola:

```
env['ir.actions.report'].get_wkhtmltopdf_state()
```

Respuesta: `'ok'`. Para salir, `Ctrl+D`.

## Paquete instalado desde un fichero

Antes de instalar el build oficial, `apt` tenía como candidato el de Ubuntu:

```
apt policy wkhtmltopdf
wkhtmltopdf:
  Installed: (none)
  Candidate: 0.12.6-2build2
  Version table:
     0.12.6-2build2 500
        500 http://at.archive.ubuntu.com/ubuntu noble/universe amd64 Packages
```

El build oficial se instala con otro nombre de paquete, `wkhtmltox`, así que la consulta correcta es esta:

```
apt policy wkhtmltox
wkhtmltox:
  Installed: 1:0.12.6.1-3.jammy
  Candidate: 1:0.12.6.1-3.jammy
  Version table:
 *** 1:0.12.6.1-3.jammy 100
        100 /var/lib/dpkg/status
```

El origen `/var/lib/dpkg/status` indica que el paquete se instaló desde un fichero y no desde un repositorio. `apt upgrade` no lo actualizará, y tampoco le llegarán parches de seguridad, porque el proyecto está archivado.

## nginx delante de `labweb`

```
# /etc/nginx/sites-available/labweb (enlazado desde sites-enabled/labweb)
server {
        listen 80;
        listen [::]:80;
        location / {
                proxy_pass http://127.0.0.1:8080;
        }
}
```

```
# command ls -l /etc/nginx/sites-enabled/
lrwxrwxrwx 1 root root ... labweb -> /etc/nginx/sites-available/labweb
```

Sitio por defecto que trae el paquete (fragmento de `/etc/nginx/sites-available/default`, sin comentarios):

```
server {
        listen 80 default_server;
        listen [::]:80 default_server;
        root /var/www/html;
        index index.html index.htm index.nginx-debian.html;
        server_name _;
        ...
}
```

Sirve ficheros: la petición de `/` encuentra `/var/www/html/index.nginx-debian.html`.

## La misma petición en cada estado

`curl -v http://89.58.45.111` desde el portátil:

| Estado del VPS | Líneas clave | Lectura |
|---|---|---|
| Sin nginx | `connect to 89.58.45.111 port 80 ... failed: Connection refused` | Nadie escucha en el 80; el kernel responde con RST |
| nginx recién instalado | `HTTP/1.1 200 OK`, `<title>Welcome to nginx!</title>` | Responde el sitio `default` |
| Enlace `default` borrado, sin recargar | La misma página de bienvenida | nginx trabaja con la configuración en memoria |
| `default` desactivado y recargado | `Connection refused` | Sin ningún sitio, nginx no abre el 80 |
| Sitio `labweb` activo | `HTTP/1.1 200 OK`, `Server: nginx/1.24.0 (Ubuntu)`, cuerpo `labweb en backend-lab, pid 654, usuario 999` | Cabecera de nginx, contenido de `labweb` |
| `labweb` parado | `HTTP/1.1 502 Bad Gateway` | nginx funciona; detrás no hay nadie |

La misma petición hecha en el VPS directamente a `labweb` (`curl -v http://127.0.0.1:8080`) responde `HTTP/1.0 200 OK` con `Server: BaseHTTP/0.6 Python/3.12.3`: sin intermediario, la cabecera es la del propio servicio.

## Qué ve cada lado

```
# journalctl -u labweb -S '5 min ago'
... python3[654]: 127.0.0.1 - - [11/Oct/2026 10:54:51] "GET / HTTP/1.0" 200 -
```

`labweb` registra `127.0.0.1` y HTTP/1.0: quien le habla es nginx. El cliente envió HTTP/1.1.

```
# sudo tail -n 15 /var/log/nginx/error.log   (con labweb parado)
2026/10/11 11:03:11 [error] 15506#15506: *15 connect() failed (111: Connection refused) while connecting to upstream, client: 80.29.79.154, server: , request: "GET / HTTP/1.1", upstream: "http://127.0.0.1:8080/", host: "89.58.45.111"
```

nginx sí conoce la IP pública del visitante (`client:`).

## nginx en `ss` tras un reload

```
# sudo ss -tlnp 'sport = :80 or sport = :8080'
LISTEN 0 511   0.0.0.0:80   0.0.0.0:*  users:(("nginx",pid=15506,...),("nginx",pid=15505,...),("nginx",pid=5914,...))
LISTEN 0 5   127.0.0.1:8080 0.0.0.0:*  users:(("python3",pid=16066,fd=3))
LISTEN 0 511      [::]:80      [::]:*  users:(("nginx",pid=15506,...),("nginx",pid=15505,...),("nginx",pid=5914,...))
```

El PID 5914 (maestro) es el mismo que tras la instalación; los *workers* son nuevos. `labweb` tiene otro PID porque se rearrancó.

## Otros fallos y cómo se ven

| Situación | Lo que aparece | Causa |
|---|---|---|
| `apt policy wkhtmltopdf` antes de instalar el `.deb` oficial | `Candidate: 0.12.6-2build2` desde `noble/universe` | Es el build de Ubuntu, sin Qt parcheado. No es el que necesita Odoo |
| `apt policy wkhtmltopdf` después de instalar el `.deb` oficial | Consulta por el nombre equivocado | El paquete instalado se llama `wkhtmltox`: `apt policy wkhtmltox` |
| Aviso «No se ha podido encontrar Wkhtmltopdf» con el estado en `'ok'` | El aviso sigue en una página cargada antes de instalar | Recargar la página y repetir la impresión. Causa no confirmada |
| `grep -i phonenumbers /opt/odoo/src/requirements.txt` sin salida | Nada: el núcleo no la pide | La declara el manifest de un módulo, no el núcleo |
| Instalar un módulo con una biblioteca ausente | `External dependency phonenumbers not installed` | La biblioteca falta en `/opt/odoo/venv`: instalarla con `uv --python` |
| PDF sin logo ni cabecera | Texto plano y tablas sin líneas | `web.base.url` apunta a una dirección que el VPS no alcanza: `report.url` |
| Parámetro `web.report.url` | Sin efecto | Odoo lee solo `report.url` |
| `find ... -name '__manifest__.py'` sin `-path` | Un manifest por cada módulo | Filtrar por la ruta del módulo con `-path` |
| `ip-neighbour` como comando | `fish: Unknown command: ip-neighbour` | El guion solo está en el nombre del manual; el comando es `ip neighbour` |
| `ip neighbour 89.58.44.1` | `Command "89.58.44.1" is unknown` | Tras el subcomando, `ip` espera un verbo (`show`) |
| Prompt con `[127]` | Código de salida 127 | Comando no encontrado (`tracepath` sin instalar) |
| Prompt con `[255]` o `[1]` | Código distinto de 0 | El comando anterior falló |
| `cat` de un fichero de netplan sin `sudo` | Error de permisos | Solo root puede leerlos |
| `sudo ss -tulpn` sin la sesión SSH propia | Solo sockets en escucha | `-l` excluye las conexiones establecidas; usar `ss -tn` |
| `dpkg -S /lib/x86_64-linux-gnu/libpq.so.5` | `no path found matching pattern` | `dpkg` registra la ruta de `/usr/lib` |
| `sudo -u odoo psql -l` sin rol | `FATAL: role "odoo" does not exist` | Autenticación correcta por `peer`; falta crear el rol |
| `git log` en `/opt/odoo/src` como `miguel` | `fatal: detected dubious ownership` | El repositorio es de root |
| `apt install` de un paquete ya presente | `is already the newest version` | Ya estaba instalado |
| Escribir en código o entorno como `odoo` | `Permission denied` | Esperado: son de root |
| `ss` sin opciones | Cientos de líneas `u_str` / `u_dgr` y solo conexiones `ESTAB` | Por defecto no muestra sockets en escucha; los `u_*` son sockets Unix |
| `ss -tl` | Puertos con nombre (`http-alt`, `postgresql`) y columna `Process` vacía | Falta `-n` (números) y `-p` con `sudo` |
| Buscar `odoo` en la columna `Process` | No aparece | El proceso es `python`; se identifica por el puerto |
| `sudo -u odoo --http-interface=... python odoo-bin` | `sudo: unrecognized option` | La opción de Odoo va detrás de `odoo-bin` |
| `odoo-bin -c` sin ruta | Error: la opción necesita un argumento | Toda opción con hueco de valor necesita su valor |
| Lanzar Odoo sin `-c` | Sin `Using configuration file`; `running on backend-lab:8069` | No lee `/etc/odoo/odoo.conf`; usa `$HOME/.odoorc` o los valores por defecto |
| Sección `[Options]` | Ningún error; Odoo arranca con valores por defecto | La sección debe ser `[options]` en minúsculas |
| `ssh -L 8069:...` con el puerto local ocupado | El túnel no puede abrir el puerto | Elegir otro puerto local (`10000`) |
| `chmod g+r` para proteger un fichero `rw-r--r--` | Nada cambia | La forma simbólica solo añade o quita; el problema estaba en `o` |
| `chmod u-r` para quitar permisos a los demás | Quita la lectura al propietario | `u` es el propietario; otros es `o` |
| `ls -l` con alias de `eza` | Tipo `.`, sin columna de grupo | Usar `command ls -l` |
| `cat /etc/odoo/odoo.conf` como `miguel` | `Permission denied` | Esperado: permisos `640` |
| Cerrar la terminal donde corre Odoo | El `:8069` desaparece de `ss` | El proceso cuelga de la sesión SSH y recibe `SIGHUP`; hace falta una unit |
| `Execstart=` en la unit | `Unknown key name 'Execstart' in section 'Service', ignoring` | Las directivas distinguen mayúsculas: `ExecStart=` |
| `After=` con una errata en el nombre | Nada: ni error ni aviso | systemd acepta dependencias hacia units inexistentes; no hay orden |
| Unit creada con un editor y sin recargar | systemd usa la versión anterior o avisa `changed on disk` | Falta `sudo systemctl daemon-reload` |
| `systemctl list-units postgresql*` en fish | `No matches for wildcard` | fish expande el `*`; poner el patrón entre comillas simples |
| `grep LOGIN` en el log de Odoo | Salida vacía | `grep` distingue mayúsculas; Odoo escribe `Login`. Usar `grep -i` |
| `UMask=` cambiada y carpetas antiguas igual | Siguen `rwxrwxr-x` | La umask solo afecta a lo que se crea; `chmod` para lo existente |
| `sudo command ls ...` | `sudo: command: command not found` | `command` es una orden de la shell, no un programa; con `sudo`, `ls` a secas |
| `listen 8080;` en el sitio de nginx, con `labweb` en `127.0.0.1:8080` | `nginx -t` correcto; el reload falla por dirección en uso | `listen` es el puerto de entrada (80); el 8080 va en `proxy_pass`. `-t` no abre puertos |
| `listen :80;` | `nginx -t` lo rechaza | Puerto solo (`80`) o dirección con puerto (`[::]:80`) |
| `ln -S` en lugar de `ln -s` | El enlace no se crea como se esperaba | Las opciones distinguen mayúsculas: `-S` es el sufijo de copias de seguridad |
| `ln -s` sin `sudo` en `sites-enabled/` | `Permission denied` | El directorio es de root |
| `proxy_pass http://localhost:8080` | Funciona, con errores de conexión en el log | `localhost` resuelve también a `::1`; usar `127.0.0.1` |
| Borrar el enlace `default` y probar | Sigue la página de bienvenida | Falta `sudo nginx -t` y `sudo systemctl reload nginx` |
| Recargar sin ningún sitio activo | `Connection refused` en el 80 con nginx en marcha | Los puertos los abre el `listen` de cada sitio |
| Buscar los sitios en `modules-enabled/` | Directorio vacío | Ese `include` carga módulos; los sitios están en `sites-enabled/` |
| `curl` al 8080 desde el portátil con nginx activo | `Connection refused` | `labweb` escucha solo en `127.0.0.1`; desde fuera solo se llega por el 80 |
| `sudo cat error.log \| tail` | Funciona, con un programa de más | `tail` lee el fichero directamente |

## Preguntas frecuentes

| Pregunta | Comando |
|---|---|
| Qué versión de wkhtmltopdf tiene el sistema | `wkhtmltopdf -V` |
| Puede el usuario de Odoo ejecutarlo | `sudo -u odoo /usr/local/bin/wkhtmltopdf -V` |
| De dónde viene el build oficial instalado | `apt policy wkhtmltox` |
| Qué estado tiene la integración de PDF | En la consola de Odoo: `env['ir.actions.report'].get_wkhtmltopdf_state()` |
| Qué dirección usan los informes | Ajustes → Técnico → Parámetros del sistema, clave `report.url` |
| Qué dijo Odoo sobre wkhtmltopdf desde el último arranque | `journalctl -u odoo -S "$(systemctl show -p ActiveEnterTimestamp --value odoo)" \| grep -i wkhtmltopdf` |
| Qué bibliotecas declara un módulo | `grep -n -A 3 'external_dependencies' /opt/odoo/src/addons/account_peppol/__manifest__.py` |
| Qué direcciones tiene la máquina | `ip address show` |
| Por dónde sale el tráfico | `ip route show` (IPv6: `ip -6 route show`) |
| Qué MAC tiene la puerta de enlace | `ip neighbour show` |
| Qué servicio gestiona una interfaz | `networkctl` (columna `SETUP`) |
| Qué escucha y desde dónde se llega | `sudo ss -tulpn` |
| Quién está conectado ahora | `ss -tn` |
| Por dónde pasa el tráfico hasta un destino | `traceroute 1.1.1.1` / `tracepath -n 1.1.1.1` |
| Qué paquete trae un programa que no tengo | `apt-file search --regexp '/bin/dig$'` |
| Qué paquete puso un fichero | `dpkg -S /usr/bin/psql` |
| De dónde viene un paquete | `apt policy postgresql-16` |
| Qué hay pendiente de actualizar | `sudo apt update` y `apt list --upgradable` |
| Quién instaló algo y cuándo | `grep -E 'Start-Date\|Commandline\|Requested-By' /var/log/apt/history.log` |
| Qué kernel está funcionando | `uname -r` |
| Qué bibliotecas compartidas usa un programa | `ldd /usr/lib/postgresql/16/bin/psql` |
| Qué atributos tiene un rol | `sudo -u postgres psql -c '\du odoo'` |
| Qué reglas de acceso tiene PostgreSQL | `sudo grep -Ev '^#\|^$' /etc/postgresql/16/main/pg_hba.conf` |
| Qué commit de Odoo está desplegado | `sudo git -C /opt/odoo/src log -1 --oneline` |
| Con qué Python funciona el entorno | `ls -l /opt/odoo/venv/bin/python` |
| Qué opciones admite mi versión de Odoo | `/opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin --help \| less` |
| Cómo se llama una opción en `odoo.conf` | `grep -n '"--data-dir"' /opt/odoo/src/odoo/tools/config.py` (valor de `dest=`) |
| Qué contraseñas admite el fichero | `grep -n "passwd" /opt/odoo/src/odoo/tools/config.py` |
| Está Odoo leyendo mi fichero | Línea `Using configuration file at` del log |
| En qué dirección escucha Odoo | `sudo ss -tlnp` (línea `:8069`) |
| Qué permisos y grupo tiene la configuración | `command ls -l /etc/odoo/odoo.conf` |
| Qué bases tienen *filestore* | `sudo ls -l /var/lib/odoo/filestore` |
| Qué hay en un directorio antes de borrarlo | `sudo ls -laR RUTA` |
| Desde qué fichero cargó systemd una unit | `systemctl show -p FragmentPath odoo` |
| Qué hace una unit de un paquete | `systemctl cat postgresql.service` |
| Cómo se llama exactamente un servicio | `systemctl list-units 'postgresql*'` (`--all` para incluir los parados) |
| Qué target alcanza la máquina al arrancar | `systemctl get-default` |
| Tiene mi unit errores de sintaxis | `sudo systemd-analyze verify /etc/systemd/system/odoo.service` |
| Está Odoo activo y habilitado | `systemctl status odoo` (líneas `Loaded:` y `Active:`) |
| Arrancó PostgreSQL antes que Odoo | `journalctl -b -u postgresql@16-main -u odoo \| grep -E 'Starting\|Started'` |
| Quién ha entrado en Odoo últimamente | `journalctl -u odoo -S '15 min ago' \| grep -i login` |
| Qué está registrando Odoo ahora mismo | `journalctl -u odoo -f` |
| Con qué umask corre un servicio | `systemctl show -p UMask odoo` |
| Qué umask tiene mi shell | `umask` |
| Dónde está la unit que trae Odoo | `find /opt/odoo/src -name '*.service'` |
| Qué versión de nginx hay | Cabecera `Server:` de `curl -v`, o `nginx -v` |
| Tiene errores la configuración de nginx | `sudo nginx -t` |
| Qué sitios están activos | `command ls -l /etc/nginx/sites-enabled/` |
| De qué directorios carga nginx configuración | `grep include /etc/nginx/nginx.conf` |
| Por qué da 502 | `sudo tail -n 15 /var/log/nginx/error.log` (fragmentos de causa y `upstream:`) |
| Llego al servicio sin pasar por nginx | En el VPS, `curl -v http://127.0.0.1:8080` |
| Escuchan nginx y `labweb` donde deben | `sudo ss -tlnp 'sport = :80 or sport = :8080'` |
| Desde qué IP le llegan las peticiones a `labweb` | `journalctl -u labweb -S '5 min ago'` |
| A qué direcciones resuelve `localhost` | `cat /etc/hosts` |

---

# Parte 3 · Comandos útiles del bloque

## Red

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ip address show` | Interfaces y sus direcciones. Abreviable: `ip addr`, `ip a` | Saber qué IP poner en un registro DNS. Manual: `man ip-address` |
| `ip route show` | Tabla de rutas IPv4; `ip -6 route show` para IPv6 | Con `via` hay intermediario; sin `via`, entrega directa. Manual: `man ip-route` |
| `ip neighbour show` | Tabla de vecinos: IP, MAC (`lladdr`) y estado | Identificar una puerta de enlace virtual. El comando lleva espacio; el manual, guion (`man ip-neighbour`). Tras el subcomando va un verbo, no una IP |
| `networkctl` | Interfaces y si las gestiona systemd-networkd | `SETUP` = `configured` / `unmanaged` |
| `sudo ss -tulpn` | Sockets que escuchan: `-t` TCP, `-u` UDP, `-l` escuchando, `-p` proceso, `-n` números | Clasificar qué es accesible desde fuera. Sin `sudo`, `-p` no ve procesos ajenos |
| `ss -tn` | Conexiones TCP establecidas | Ver quién está conectado (columna `Peer`) |
| `sudo ss -tlnp` | Puertos TCP en escucha con número y proceso | Confirmar dónde escucha Odoo. Sin opciones, `ss` muestra solo conexiones establecidas, incluidas las Unix |
| `sudo ss -tnp` | Conexiones TCP establecidas con su proceso | Ver el túnel: tres `ESTAB` en `:22`. Las de `:8069` solo existen durante una petición |
| `ss -lx` | Sockets Unix que escuchan; `-x` = Unix | Localizar el socket de PostgreSQL |
| `traceroute IP` / `tracepath -n IP` | Saltos hasta un destino; `-n` sin resolver nombres | `tracepath` está en `iputils-tracepath`, que no viene en Ubuntu minimal |
| `curl http://127.0.0.1:8080` | Petición HTTP | Comparar el mismo puerto desde dentro y desde fuera |

## Configuración de red

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ls -l /etc/netplan/` | Ver los ficheros de netplan y sus permisos | `-a` muestra ocultos pero no permisos |
| `sudo cat /etc/netplan/50-cloud-init.yaml` | Leer la descripción de la red | Sin `sudo`, error de permisos (son `600`) |
| `ls /run/systemd/network/` | Ver los `.network` generados por netplan | No editarlos: se regeneran al arrancar |
| Consola VNC del panel del proveedor | Entrar sin red ni SSH | Puerta de recuperación. Al escribir la contraseña no se ve nada; el teclado puede estar en distribución estadounidense |

## Paquetes

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo apt update` | Descargar el catálogo actualizado | No instala nada. Siempre antes de buscar o listar |
| `apt list --upgradable` | Paquetes con versión nueva disponible | No aplica nada. El origen (`noble-security`, `noble-updates`) indica el tipo de corrección |
| `sudo apt install PAQ1 PAQ2` | Instalar paquetes y sus dependencias | Leer el resumen antes de confirmar (`newly installed`, paquetes huérfanos, kernel pendiente) |
| `sudo apt-file update` | Descargar el índice de ficheros de los paquetes | Necesario una vez antes de `apt-file search` |
| `apt-file search --regexp '/bin/NOMBRE$'` | Qué paquete trae un fichero que no tienes | Sin `--regexp` busca el texto en cualquier parte de la ruta y trae ruido |
| `dpkg -S RUTA` | Qué paquete instalado puso un fichero | Usar la ruta de `/usr/lib`, no `/lib`. Si el fichero es un enlace, devuelve el paquete del enlace |
| `dpkg -L PAQUETE` | Ficheros que instaló un paquete | Combinado con `grep` para localizar un fichero |
| `dpkg -l PAQ1 PAQ2` | Estado de paquetes (`ii` = instalado) | `-l`, `-L` y `-S` son opciones distintas |
| `apt policy PAQUETE` | Versión instalada, candidata y repositorio de cada una | Saber si algo viene de Ubuntu o de un tercero |
| `grep -E 'Start-Date\|Commandline\|Requested-By' /var/log/apt/history.log` | Línea de tiempo de instalaciones | Saber quién actualizó algo. `-E` permite `\|` como «o» |
| `tail -n 20 /var/log/apt/history.log` | Últimas operaciones de `apt`, completas | Ver qué entró como `automatic` |
| `apt autoremove` | Quitar dependencias que nadie usa | Revisar la lista antes |
| `sudo systemctl reboot` | Reiniciar para cargar un kernel nuevo | Comprobar después con `uname -r` y `systemctl is-active` |

## Bibliotecas y compilación

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ldd PROGRAMA` | Bibliotecas compartidas que usa un programa y dónde las encuentra | La dirección entre paréntesis cambia en cada ejecución |
| `ls -l RUTA` | Ver si un fichero es un enlace (`->`) y a dónde apunta | Un comando que se comporta raro puede ser un intermediario |
| `sudo apt install gcc-x86-64-linux-gnu binutils` | Compilador y ensamblador/enlazador | Alternativa de una línea: `build-essential` |
| `sudo apt install libpython3.12-dev libldap-dev libpq-dev` | Cabeceras para compilar `python-ldap` y `psycopg2` | Solo hacen falta al instalar las librerías, no con Odoo funcionando |

## PostgreSQL

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo -u postgres createuser --createdb odoo` | Crear un rol con `CREATEDB`, con login, sin superusuario ni creación de roles | El nombre debe coincidir con el usuario de Linux para `peer` |
| `sudo -u odoo psql -l` | Listar bases como `odoo`, por el socket | `could not change directory` es un aviso inofensivo |
| `sudo -u odoo psql -h 127.0.0.1 -l` | La misma conexión por TCP | Pide contraseña: comprueba la regla `scram-sha-256` |
| `sudo -u postgres psql -c '\du odoo'` | Atributos de un rol; `-c` ejecuta una orden | Lo importante es lo que **no** aparece (`Superuser`, `Create role`) |
| `sudo grep -Ev '^#\|^$' /etc/postgresql/16/main/pg_hba.conf` | Reglas sin comentarios ni líneas vacías; `-v` invierte | En Ubuntu la ruta lleva versión y clúster |

## Usuarios y permisos

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo useradd --system --user-group --create-home --home-dir /var/lib/odoo --shell /usr/sbin/nologin odoo` | Usuario de servicio con grupo propio y directorio de datos | Con `--system` el directorio no se crea si falta `--create-home` |
| `sudo passwd -S USUARIO` | Estado de la contraseña: `P` (tiene), `L` (bloqueada), `NP` (sin contraseña) | `-Sa` muestra todos los usuarios |
| `sudo -u USUARIO COMANDO` | Ejecutar un comando como otro usuario | Funciona con `nologin`: no abre sesión |
| `sudo -u odoo touch /opt/odoo/src/prueba` | Comprobar que un servicio no puede escribir en una ruta | Lo esperado es `Permission denied` |

## Código y entorno de Odoo

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `git --version` | Comprobar que git está instalado | La versión de Ubuntu LTS es más antigua que la del proyecto; es normal |
| `sudo git clone --depth 1 --branch 18.0 https://github.com/odoo/odoo.git /opt/odoo/src` | Descargar Odoo 18 sin historial | `sudo` para que el código sea de root |
| `sudo git -C /opt/odoo/src log -1 --oneline` | Commit desplegado; `-C` ejecuta git en esa carpeta | Sin `sudo`: `dubious ownership` |
| `curl -LsSf https://astral.sh/uv/install.sh \| less` | Leer el instalador antes de ejecutarlo | `-L` sigue redirecciones, `-s` silencioso, `-S` con errores, `-f` falla con errores HTTP |
| `curl -LsSf https://astral.sh/uv/install.sh \| sudo env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh` | Instalar `uv` para todo el sistema | Sin la variable, con `sudo`, acabaría en `/root/.local/bin` |
| `uv --version` | Versión instalada | Anotarla en la guía de reinstalación |
| `sudo uv venv --python /usr/bin/python3 /opt/odoo/venv` | Entorno virtual con el Python del sistema | Dar la ruta exacta evita que `uv` use o descargue otro Python |
| `sudo uv pip install --python /opt/odoo/venv/bin/python -r /opt/odoo/src/requirements.txt` | Instalar las librerías de Odoo en su entorno | Los fallos de compilación se resuelven con el método de la Parte 2 |
| `/opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin --version` | Comprobar que Odoo arranca con su entorno | Debe responder `Odoo Server 18.0` |
| `sudo mv /opt/odoo/odoo /opt/odoo/src` | Renombrar una carpeta | Hacerlo antes de que algo dependa de la ruta |

## Permisos y ficheros con secretos

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo mkdir /etc/odoo` | Directorio de configuración de un programa | Queda `root:root 755`: basta con proteger el fichero |
| `sudo touch FICHERO` | Crear un fichero vacío | Para fijar permisos antes de escribir un secreto. Nace `rw-r--r--` |
| `sudo chown root:odoo FICHERO` | Cambiar propietario y grupo (`usuario:grupo`) | `root` escribe; el grupo del servicio lee |
| `sudo chmod 640 FICHERO` | Fijar `rw-r-----` | Patrón de configuración con secretos |
| `sudo chmod o-r FICHERO` | Quitar la lectura a otros, sin tocar el resto | `u` es el propietario, no «usuarios». Las simbólicas parten de los permisos actuales |
| `command ls -l RUTA` | `ls` real, saltando el alias | Ver el grupo cuando `ls` es `eza`. Con `sudo` delante ya se usa el real |
| `sudoedit FICHERO` | Editar un fichero de root con tu editor, sin ejecutarlo como root | Conserva propietario, grupo y permisos. Editor elegido por `SUDO_EDITOR`, `VISUAL` o `EDITOR` |
| `sudo cat FICHERO` | Ver el contenido real en disco | Comprobar lo guardado, no lo recordado. Cuidado con secretos en pantalla |
| `sudo -u odoo cat FICHERO` | Comprobar que el servicio puede leer | Objetivo: contenido como `odoo`, `Permission denied` como `miguel` |
| `openssl rand -base64 24` | Contraseña aleatoria de 32 caracteres; `24` bytes, `-base64` los pasa a texto | Contraseña maestra. Guardarla en el gestor de contraseñas antes de seguir |
| `sudo ls -laR RUTA` | Listado recursivo con ocultos; `-R` entra en cada subcarpeta | Revisar antes de borrar |
| `sudo rm -r RUTA` | Borrar una carpeta y su contenido | Sin papelera. Un espacio de más en la ruta la convierte en dos |

## Arranque y configuración de Odoo

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `/opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin --help \| less` | Opciones de la versión instalada; `\| less` permite desplazarse, buscar con `/` y salir con `q` | Referencia delante para escribir `odoo.conf` |
| `sudo -u odoo /opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin` | Arrancar con valores por defecto | Escucha en `0.0.0.0:8069`. Sin firewall, pararlo enseguida con `Ctrl+C` |
| `sudo -u odoo ... odoo-bin --http-interface=127.0.0.1` | Probar una opción antes de llevarla al fichero | Las opciones de Odoo van detrás de `odoo-bin` |
| `sudo -u odoo /opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin -c /etc/odoo/odoo.conf` | Arrancar con el fichero; `-c` = `--config` | Buscar `Using configuration file at` en el log. Muere al cerrar la terminal |
| `grep -n '"--OPCION"' /opt/odoo/src/odoo/tools/config.py` | Nombre de una opción en el fichero (`dest=`); `-n` numera las líneas | Cuando la regla `--` → `_` no cuadra |
| `grep -n "passwd" /opt/odoo/src/odoo/tools/config.py` | Localizar opciones que solo existen en el fichero | `admin_passwd`, por defecto `admin` |

## Servicio de Odoo (systemd)

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo nano /etc/systemd/system/odoo.service` | Crear o editar la unit como root | Después, siempre `daemon-reload` |
| `sudo systemctl edit --force --full odoo.service` | Crear la unit en `/etc/systemd/system/` y editarla; `--force` permite que no exista, `--full` edita el fichero entero y no un override | Recarga systemd al guardar. Si el fichero ya existe, basta con editarlo |
| `sudo systemctl daemon-reload` | Que systemd vuelva a leer las units del disco | Tras crear o modificar una unit a mano. Sin él: `changed on disk` |
| `systemctl cat UNIT` | Contenido de una unit y de sus overrides, con la ruta encima | Ver que lo guardado es lo que se quería; leer units de paquetes (`postgresql.service` ejecuta `/bin/true`) |
| `systemctl show -p FragmentPath UNIT1 UNIT2` | Fichero desde el que se cargó cada unit; `-p` limita a una propiedad | Distinguir units del administrador (`/etc`) y de paquetes (`/usr/lib`) |
| `systemctl list-units 'PATRÓN*'` | Units cargadas que coinciden con un patrón | En fish, el patrón entre comillas simples. `--all` incluye las paradas; `list-unit-files` lista lo instalado en disco, plantillas incluidas |
| `systemctl get-default` | Target que alcanza la máquina al arrancar | Elegir `WantedBy=`. En el VPS: `multi-user.target` |
| `systemd-analyze --help` | Subcomandos de `systemd-analyze`, una línea cada uno | Encontrar un nombre sin abrir el `man` |
| `sudo systemd-analyze verify /etc/systemd/system/odoo.service` | Revisar la sintaxis de la unit; sin avisos no imprime nada | Recibe la **ruta**, no el nombre. No detecta argumentos absurdos (`-c /etc/odoo/odoo.`) ni erratas en `After=` |
| `sudo systemctl start odoo` | Arrancar ahora; `.service` se puede omitir | Con `Type=exec`, falla aquí mismo si la ruta de Python está mal |
| `systemctl status odoo` | Estado, PID, cgroup y últimas líneas del log | `Loaded:` (`enabled`/`disabled`; `preset:` no es el estado), `Active:`, `CGroup:` |
| `sudo systemctl enable odoo` | Crear el enlace de `[Install]` para que arranque al iniciar | No arranca nada en ese momento. Si `[Install]` está mal escrita, avisa de que no la tiene |
| `sudo systemctl restart odoo` | Parar y arrancar | Necesario para que un cambio en `[Service]` (como `UMask=`) llegue al proceso |
| `sudo systemctl stop postgresql@16-main` / `start` | Simular un corte de la base | Experimento `Wants=`/`Requires=`. Volver a arrancarla al terminar |
| `sudo reboot` | Reiniciar el VPS | Corta SSH y túnel. Comprobar después el orden en el journal |
| `journalctl -u odoo -f` | Log de Odoo en directo; `-f` espera líneas nuevas | Dejarlo abierto en otra terminal durante un experimento. `Ctrl+C` sale |
| `journalctl -u odoo -S '15 min ago' \| grep -i login` | Inicios de sesión recientes; `-S` = `--since`, `-i` ignora mayúsculas | `grep LOGIN` no encuentra nada. Alternativa: `-g login` dentro de `journalctl` |
| `journalctl -b -u postgresql@16-main -u odoo \| grep -E 'Starting\|Started'` | Orden de arranque de las dos units en el arranque actual; `-b` = este arranque, `-u` repetible | Comprobar que `After=` funciona tras reiniciar |
| `find /opt/odoo/src -name '*.service'` | Buscar ficheros por nombre dentro de una carpeta | Patrón entre comillas en fish. Encuentra `debian/odoo.service`, legible sin `sudo` |

## Umask

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `umask` | Umask de la shell actual | En el VPS, `0002`: lo lanzado a mano crea carpetas `775` |
| `systemctl show -p UMask odoo` | Umask con la que systemd lanza el servicio | Sin `UMask=` en la unit, `0022` |
| `UMask=0027` en `[Service]` | Que lo que cree Odoo nazca `750`/`640` | Solo afecta a lo nuevo y tras `restart` |
| `sudo chmod -R g-w,o-rwx /var/lib/odoo` | Igualar lo existente: quita escritura al grupo y todo a otros; `-R` recursivo, `,` separa órdenes | Solo quita, nunca añade: no rompe el acceso del propietario |
| `sudo ls -ld RUTA1 RUTA2` | Permisos de las carpetas en sí; `-d` no entra en ellas | Con `sudo`, `ls` a secas: `sudo command ls` falla |

## Túnel SSH

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ssh -N -L 10000:127.0.0.1:8069 vps` | Llevar el `10000` del portátil al `127.0.0.1:8069` del VPS; `-L` reenvío local, `-N` sin shell | Se lanza en el portátil, no dentro del VPS. Navegador: `http://localhost:10000`. La terminal queda sin prompt; `Ctrl+C` cierra el túnel. Si el puerto local está ocupado, se cambia solo el primero |

## Informes PDF y dependencias de módulos

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.jammy_amd64.deb` | Descargar un fichero desde una dirección y guardarlo en el directorio actual | Antes, `cd ~`, para saber dónde queda. Sin opciones en este caso |
| `ls -lh wkhtmltox*` | Comprobar la descarga; `-l` muestra tamaño y fecha, `-h` los pone en MB en vez de bytes | El `*` vale por cualquier texto. El `.deb` de jammy ocupa unos 16,5 MB |
| `sudo apt install ./wkhtmltox_0.12.6.1-3.jammy_amd64.deb` | Instalar un `.deb` local con sus dependencias | El `./` indica un fichero de la carpeta actual; sin él, `apt` busca un paquete en los repositorios. `dpkg -i` no resuelve las dependencias que falten |
| `wkhtmltopdf -V` | Versión del programa y si lleva Qt parcheado | Debe aparecer `with patched qt`. Sin esa leyenda, el programa no sirve para Odoo |
| `sudo -u odoo /usr/local/bin/wkhtmltopdf -V` | Comprobar que el usuario del servicio puede ejecutarlo | La ruta es la del log de arranque. Un `Permission denied` apuntaría a permisos |
| `apt policy wkhtmltopdf` | Versión candidata y origen del build de Ubuntu | Antes de instalar, `Installed: (none)` y origen de un repositorio |
| `apt policy wkhtmltox` | Versión instalada y origen del build oficial | El nombre es `wkhtmltox`, no `wkhtmltopdf`. `/var/lib/dpkg/status` indica instalación desde fichero |
| `systemctl is-active odoo` | Responder solo `active` o `inactive` | Sin el resto del estado que muestra `systemctl status` |
| `journalctl -u odoo -S "$(systemctl show -p ActiveEnterTimestamp --value odoo)" \| grep -i wkhtmltopdf` | Mensajes de wkhtmltopdf desde el último arranque de Odoo | `$( … )` ejecuta `systemctl show` y pasa su resultado a `-S`. Con `--since "2 min ago"` se pierde el arranque si fue hace más de dos minutos |
| `journalctl -u odoo --since "5 min ago" \| grep -iE "report\|pdf\|wkhtml"` | Actividad de informes en los últimos cinco minutos | `-E` permite varios patrones separados por `\|`. La hora del journal y la de los mensajes de Odoo difieren dos horas |
| `sudo -u odoo /opt/odoo/venv/bin/python /opt/odoo/src/odoo-bin shell -c /etc/odoo/odoo.conf -d test-db --no-http` | Consola de Python con Odoo cargado, como el usuario del servicio | `--no-http` evita levantar el servidor web, que chocaría con el puerto 8069 del servicio. `Ctrl+D` sale |
| `env['ir.actions.report'].get_wkhtmltopdf_state()` | Estado de la integración de PDF, dentro de la consola de Odoo | Puede devolver `'install'`, `'ok'`, `'upgrade'`, `'workers'` o `'broken'` |
| `grep -n "report.url" /opt/odoo/src/odoo/addons/base/models/ir_actions_report.py` | Líneas donde Odoo lee el parámetro `report.url` | El `.` vale por cualquier carácter, así que `report_url` también coincide |
| `sed -n '85,125p;258,275p;843,858p' /opt/odoo/src/odoo/addons/base/models/ir_actions_report.py` | Imprimir solo esos rangos de líneas de un fichero | `-n` evita imprimir el fichero entero; `;` separa los rangos |
| `find /opt/odoo/src -path '*account_peppol*' -name '__manifest__.py'` | Localizar la ficha de un módulo | `-path` compara la ruta completa y `-name` solo el nombre del fichero. Sin `-path` salen todos los manifests. Los `*` van entre comillas para que fish no los expanda |
| `grep -n -A 3 'external_dependencies' /opt/odoo/src/addons/account_peppol/__manifest__.py` | Ver las bibliotecas que declara un módulo | `-A 3` muestra las tres líneas siguientes a la coincidencia |
| `sudo uv pip install --python /opt/odoo/venv/bin/python phonenumbers` | Instalar una biblioteca en el entorno de Odoo | Sin `--python`, `uv` instala en el Python del sistema. Con `sudo`, porque el entorno es de root |

## nginx

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `curl -v http://89.58.45.111` | Petición HTTP mostrando la conexión (`*`), lo enviado (`>`) y lo recibido (`<`); `-v` = *verbose* | Desde el portátil. Sin puerto, `http://` usa el 80. `Connection refused` = nadie escucha; `502` = nginx responde pero detrás falla |
| `curl -v http://127.0.0.1:8080` | Hablar con el servicio sin pasar por nginx | En el VPS. Separa un fallo de nginx de uno del servicio |
| `sudo apt install nginx` | Instalar nginx | Arranca y queda habilitado al momento, con el sitio `default` en el 80 |
| `grep include /etc/nginx/nginx.conf` | Ver solo las líneas que cargan otros ficheros | Sin `sudo`: el fichero es legible por todos. De los cuatro `include`, el de los sitios es `sites-enabled/` |
| `command ls -l /etc/nginx/sites-enabled/` | Sitios activos; `-l` muestra el tipo (`l` = enlace) y el destino (`->`) | En fish, `command` salta el alias de `ls` |
| `sudo rm /etc/nginx/sites-enabled/default` | Desactivar un sitio borrando su enlace | Borra el enlace, no el fichero de `sites-available/`. Con un enlace a un directorio, nunca `rm -r` con `/` final: borraría el contenido real |
| `sudo unlink /etc/nginx/sites-enabled/default` | Lo mismo con `unlink`: un solo nombre, sin opciones | Alternativa a `rm` para enlaces |
| `sudo ln -s /etc/nginx/sites-available/labweb /etc/nginx/sites-enabled/labweb` | Activar un sitio; `-s` = enlace simbólico | Primero el destino, después el enlace. Destino con ruta absoluta. `-S` (mayúscula) es otra opción |
| `sudo nginx -t` | Validar toda la configuración; `-t` = *test* | Siempre antes de recargar. No detecta puertos ocupados |
| `sudo systemctl reload nginx` | Aplicar la configuración nueva sin cortar conexiones | Solo si `nginx -t` es correcto. El PID del maestro se mantiene |
| `sudo systemctl stop labweb` / `start` | Parar y arrancar el servicio de detrás | Reproducir un 502. Volver a arrancarlo al terminar |
| `sudo tail -n 15 /var/log/nginx/error.log` | Últimas líneas del log de errores; `-n` = número de líneas (10 por defecto) | La causa de un 502. `cat \| tail` sobra |
| `journalctl -u labweb -S '5 min ago'` | Peticiones que ha recibido `labweb`; `-u` unit, `-S` desde | Muestra `127.0.0.1` como origen cuando hay proxy delante |
| `sudo ss -tlnp 'sport = :80 or sport = :8080'` | Sockets en escucha de esos puertos, con cabecera; `sport` = puerto local | El filtro de `ss` conserva la cabecera, que `grep` elimina. Comillas simples para fish. Sin `sudo`, la columna `Process` sale vacía |
| `cat /etc/hosts` | Nombres locales y sus direcciones | Comprobar que `localhost` resuelve a `127.0.0.1` y a `::1` |
