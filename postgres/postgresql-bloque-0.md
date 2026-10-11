# PostgreSQL · Bloque 0 — Que la base de datos exista y sea tuya

Carril de PostgreSQL: **miércoles, 1 h**. Tres sesiones. Cerrado el 13/09/2026.

Este bloque no venía en el roadmap. El Bloque 1 arranca con «joins, agregaciones, subconsultas, CTEs y window functions… escríbelo contra una base con datos», y da por hecho que hay un servidor corriendo, un rol propio y datos dentro. No había nada de eso. Esto construye el laboratorio.

**Criterio de cierre:** explicar sin notas por qué `psql -d pagila` entra sin contraseña mientras `psql -h localhost -d pagila` la pide, siendo la misma máquina, el mismo servidor y el mismo rol.

**Entorno:** CachyOS (Arch) · PostgreSQL 18.6 · base de laboratorio Pagila.

---

## 1. Cuatro cosas con nombres parecidos

La confusión de base es que en el habla diaria todo se llama «Postgres». Son cuatro capas distintas, y cada una se instala, se arranca y se borra por separado.

| Capa | Qué es | Dónde vive |
|---|---|---|
| **Paquete** | Los binarios: `postgres`, `psql`, `initdb`, `pg_dump` | `/usr/bin/` |
| **Cluster** | Los ficheros de datos que creó `initdb` | `/var/lib/postgres/data` |
| **Servidor** | El proceso en ejecución sobre esos ficheros | un PID, gestionado por systemd |
| **Base de datos** | Cada base dentro del cluster | dentro del cluster |

La analogía: `initdb` levanta un **edificio** (el cluster). Cada base de datos es un **piso**. Cada esquema, una **habitación**. Los roles son los **inquilinos con llave**.

De ahí salen cuatro consecuencias que conviene tener claras:

- Borrar el paquete no borra datos. Borrar `/var/lib/postgres/data` los borra todos.
- Un servidor abre **un puerto** y atiende **todas** las bases de su cluster.
- Las bases están aisladas entre sí. Desde `pagila` no se consulta una tabla de otra base: no hay joins entre pisos. Esto sorprende viniendo de MySQL, donde sí se cruza con `basedatos.tabla`.
- Lo que **sí** comparten todas las bases del cluster: los roles, el puerto, `postgresql.conf` y `pg_hba.conf`. Por eso un rol existe en todas a la vez: los inquilinos están dados de alta en el edificio, no en un piso.

«Cluster» aquí **no** significa varias máquinas, como en Kubernetes. Es terminología histórica desafortunada.

Un mismo equipo puede tener **varios clusters**, cada uno en su puerto. Los contenedores Docker de Odoo son exactamente eso: clusters completos e independientes, con su propio `initdb`, su directorio de datos y su proceso. Dos edificios en la misma calle; el número de portal es el puerto.

### Por qué en Arch se ve y en Debian no

El paquete de Arch **no** inicializa el cluster: hay que ejecutar `initdb` a mano. Debian y Ubuntu lo hacen por ti al instalar, y por eso mucha gente que lleva años usando Postgres no distingue el cluster del servidor. Tener que construirlo es una ventaja pedagógica.

### El servidor no es un proceso, es una cuadrilla

```
├─ postgres -D /var/lib/postgres/data     ← el padre (postmaster)
├─ postgres: io worker 0..2
├─ postgres: checkpointer                 ← vuelca páginas a disco
├─ postgres: background writer
├─ postgres: walwriter                    ← escribe el registro de transacciones
├─ postgres: autovacuum launcher          ← limpia filas muertas
└─ postgres: logical replication launcher
```

El padre no atiende consultas: escucha el puerto y engendra **un hijo por cada conexión**. El resto es personal de mantenimiento permanente.

---

## 2. Autenticación y autorización son dos filtros distintos

Este es el nudo conceptual del bloque, y casi todos los «no me conecta» nacen de confundirlos.

- **Autenticación** — decide si te dejan **entrar** por la puerta. La gobierna `pg_hba.conf`.
- **Autorización** — decide qué puedes **tocar** una vez dentro. La gobiernan la propiedad de los objetos y los `GRANT`.

Son filtros encadenados e independientes. Se puede entrar sin acreditarse con nada y aun así tener prohibido crear una base — pasó literalmente.

### pg_hba.conf: una tabla de reglas en orden

Cada línea responde a cinco preguntas, y **gana la primera que encaja**, igual que `sshd_config`.

| Columna | Pregunta |
|---|---|
| TYPE | Por qué puerta llega: `local` (socket Unix) o `host` (TCP) |
| DATABASE | A qué bases aplica |
| USER | Qué roles puede pedir |
| ADDRESS | Desde qué direcciones (solo en `host`) |
| METHOD | Cómo se comprueba la identidad |

### Los tres métodos que importan aquí

**`trust`** — no se comprueba nada. El portero no está: pasa cualquiera pidiendo el rol que quiera, superusuario incluido. **Es el default de `initdb`** cuando no se le pasa `--auth-local`; avisa al terminar, pero el aviso se pierde entre cincuenta líneas de salida.

**`peer`** — el servidor le pregunta al kernel qué UID tiene el proceso al otro lado del socket, lo traduce a nombre y comprueba que coincide con el rol solicitado.

La clave: **la contraseña no existe en ningún punto del proceso**. No es que se la salte, es que no hay nada que comprobar. El dato no lo envía el cliente, lo consulta el servidor a una fuente que el cliente no controla. Por eso `peer` es *más* seguro que una contraseña en local, no menos.

La analogía: el portero no te reconoce por la cara, **llama al registro del edificio**. Tú no aportas información; él la obtiene de donde no puedes mentir.

**`scram-sha-256`** — la contraseña **nunca viaja**. El servidor manda un desafío aleatorio, el cliente responde con un cálculo que solo sale bien si conoce la contraseña, el servidor lo verifica. Misma idea que la autenticación por clave SSH: un reto irrepetible en lugar de un secreto por el cable. El `md5` de servidores antiguos es su predecesor, ya roto.

### Por qué hacen falta dos métodos en la misma máquina

En el **socket Unix** el kernel sabe qué proceso hay al otro lado, porque es local y fue él quien lo creó. Ese testigo existe, y `peer` lo aprovecha.

En **TCP** ese testigo no existe: una conexión TCP es una conexión TCP aunque dé la vuelta y vuelva a la misma máquina. Sin testigo, la identidad hay que demostrarla con contraseña.

De ahí la configuración que quedó:

```
local   all   all                    peer
host    all   all   127.0.0.1/32     scram-sha-256
host    all   all   ::1/128          scram-sha-256
```

`127.0.0.1/32` y `::1/128` son lo mismo en IPv4 e IPv6: la propia máquina y nadie más. El número tras la barra es la máscara — `/32` fija los 32 bits, así que el rango contiene una sola dirección. Aritmética del Bloque 1 de Redes.

### Las tres pruebas que lo demuestran

Mismo servidor, misma máquina, mismo rol. Lo único que cambia es **la puerta y el rol pedido**:

| Comando | Puerta | Regla | Método | Resultado |
|---|---|---|---|---|
| `psql -d pagila` | socket | `local` | `peer` | entra sin contraseña |
| `psql -U postgres -d postgres` | socket | `local` | `peer` | **rechazado** |
| `psql -h localhost -d pagila` | TCP | `host` | `scram-sha-256` | pide contraseña |

Ese es el contenido del criterio de cierre.

### Cómo decide psql qué rol pedir

Cascada de tres fuentes, gana la primera:

1. El flag `-U`
2. La variable de entorno `PGUSER`
3. **El nombre del usuario del sistema operativo**

Lo mismo con la base: sin `-d`, busca una base con el mismo nombre que el rol. De ahí el error confuso al ejecutar `psql` a secas.

**Punto que cuesta ver:** ese default y el mecanismo `peer` son **dos cosas distintas** que miran el mismo dato.

- `psql` mira tu usuario de Linux para decidir **qué rol pedir**. Conveniencia del cliente, sin seguridad detrás.
- `peer` mira tu usuario de Linux para decidir **si te deja entrar**. Lo hace el servidor preguntando al kernel, y no se puede falsear.

Que ambos coincidan es lo que permite escribir `psql -d pagila` a secas. Por eso conviene que el rol se llame igual que el usuario de Linux.

### sudo y Postgres no comparten contraseña

`sudo -u postgres psql` puede pedir una contraseña, y **no es de Postgres**: el mensaje dice `[sudo] password for miguel`. Son dos puertas seguidas y solo una tiene cerradura.

1. `sudo` pide **tu** contraseña de Linux para confirmar que eres tú quien está al teclado.
2. Ya convertido en `postgres`, `psql` conecta por socket y `peer` lo confirma sin pedir nada.

La analogía: la contraseña es la del **taxi** que te lleva al portal, no la del portal.

Y `sudo` cachea esa autenticación **15 minutos por terminal**, lo que explica que unas veces pregunte y otras no. `sudo -k` invalida el caché al instante; `sudo -v` lo renueva.

---

## 3. Roles: una sola entidad, tres mecanismos de poder

### Un rol no es un usuario; un usuario es un rol

En Postgres existe **una sola entidad**: el rol. Lo único que separa un «usuario» de un «grupo» es el atributo `LOGIN`:

```
miguel       rolcanlogin = t     → lo llamamos "usuario"
pg_monitor   rolcanlogin = f     → lo llamamos "grupo"
```

Están en la misma tabla del catálogo. «Usuario» y «grupo» no son tipos: son **maneras de hablar** según cómo uses el rol. Por eso la sentencia se llama `ALTER ROLE`.

Hasta la versión 8.1 sí eran cosas distintas, con `CREATE USER` y `CREATE GROUP` separados. Se unificaron porque no se podía hacer que un usuario heredara permisos de otro. `CREATE USER` sobrevive como alias de `CREATE ROLE ... LOGIN`.

Lo que se ganó con la unificación:

```sql
GRANT miguel TO otro;   -- otro hereda todo lo de miguel
```

La analogía: en una empresa no hay «personas» y «departamentos» como categorías biológicas distintas. Hay **miembros de una estructura**; algunos tienen tarjeta para entrar y otros son solo una casilla del organigrama. Están en la misma tabla.

### Tres mecanismos que conceden poderes

| Mecanismo | Qué es | Cómo se concede | Dónde se ve en `\du` |
|---|---|---|---|
| **Atributo** | Columna booleana en la fila del rol | `ALTER ROLE x CREATEDB` | columna *Attributes* |
| **Privilegio** | Permiso sobre un objeto concreto | `GRANT SELECT ON film TO x` | no aparece |
| **Pertenencia** | Ser miembro de otro rol y heredar lo suyo | `GRANT pg_monitor TO x` | columna *Member of* |

La preposición distingue los dos últimos: `GRANT algo ON objeto TO rol` es privilegio; `GRANT rol TO rol` es pertenencia.

`CREATEDB` es un **atributo**, no un rol. Un privilegio en Postgres no es más que una columna booleana en una tabla.

La analogía: en el gimnasio, la ficha tiene **casillas marcadas** (puede usar la piscina) y **grupos a los que perteneces** (equipo de natación). Casillas = atributos; grupos = pertenencia.

Que convivan dos sistemas para cosas parecidas es deuda histórica: los roles predefinidos son un mecanismo posterior, pensado para trocear poderes que antes solo existían dentro del superusuario.

### Los roles predefinidos y la escalada

Un cluster recién creado trae 17 roles: `postgres` y 16 predefinidos `pg_*`, todos con `rolcanlogin = false`. No son cuentas: son **llaves maestras parciales** colgadas de un tablero, esperando a que alguien las coja con un `GRANT`.

Antes, para que monitorización leyera estadísticas del servidor había que hacerla superusuario — darle las llaves del edificio entero para mirar el contador de la luz. Ahora se le da `pg_monitor` y nada más.

Tres que explican por qué el rol propio no debe ser superusuario:

- `pg_read_server_files` / `pg_write_server_files` — leer y escribir ficheros **del disco del servidor**, no de la base.
- `pg_execute_server_program` — ejecutar comandos del sistema operativo con los permisos del usuario `postgres`.

Ahí está la escalada, explícita: **rol de base de datos → comandos en la máquina → dueño de todos los ficheros del cluster**. Un superusuario los tiene los tres por definición. Es el mismo razonamiento que llevó a no trabajar como root en el VPS.

Dos rarezas del catálogo:

- `pg_database_owner` no tiene miembros fijos: dentro de cada base, el miembro es quien sea el propietario de **esa** base. Contenido variable según el piso.
- `pg_signal_backend` permite cancelar consultas y cerrar conexiones ajenas — el `kill` de Postgres. El día que una query de Odoo se quede colgada bloqueando una tabla, es el privilegio que se quiere tener sin ser superusuario.

> El prefijo `pg_` está reservado: no se pueden crear roles, esquemas ni tablas que empiecen así.

### El CRUD no hay que concederlo

Cadena completa, sin un solo `GRANT`:

1. Crear una base te hace **dueño de la base**.
2. Como dueño, puedes crear tablas dentro.
3. Quien crea una tabla es **su dueño**.
4. El dueño tiene todo sobre ella: `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `DROP`, índices.

Ser titular del contrato del piso ya permite mover los muebles y tirar un tabique. Lo que no permite es entrar en el piso del vecino ni dar de alta inquilinos.

Lo que se renuncia al no ser superusuario: crear roles, crear bases sin `CREATEDB`, instalar ciertas extensiones, tocar bases ajenas. Nada de eso aparece en el Bloque 1, y `sudo -u postgres psql` está a un comando. El privilegio se pide, no se lleva puesto.

### Criterio para repartir atributos

**`CREATEDB` es para quien administra, no para quien usa.** La pregunta: ¿este rol va a escribir `CREATE DATABASE` alguna vez? Si no, no se lo pongas.

- Persona que administra su entorno → `LOGIN CREATEDB`
- Rol de aplicación → `LOGIN` y nada más
- Excepción conocida: el rol `odoo` **sí** necesita `CREATEDB`, porque su gestor de bases crea y duplica desde la interfaz web. Por eso conviene desactivar ese gestor en producción: es un `CREATEDB` expuesto en un formulario público.

Los dos que nunca se conceden sin razón escrita:

- `SUPERUSER` — salta todas las comprobaciones y, vía `pg_execute_server_program`, llega al sistema operativo.
- `CREATEROLE` — parece inocente y no lo es: quien puede crear roles puede crearse uno con más permisos y usarlo.

La analogía: `CREATEDB` es la llave del cuarto de contadores; `SUPERUSER` es la llave maestra del edificio. La primera se le puede dar al inquilino que lleva la comunidad; la segunda se queda en conserjería.

### Borrar un rol

Un rol no se borra si posee objetos o tiene privilegios concedidos: Postgres frena con `role "x" cannot be dropped because some objects depend on it`. No se da de baja a un inquilino con el contrato todavía a su nombre.

Antes hay que traspasar (`REASSIGN OWNED BY viejo TO nuevo`) y limpiar el resto (`DROP OWNED BY viejo`).

En un servidor con datos reales, `ALTER ROLE` es siempre la vía: borrar y recrear arrastra dependencias.

---

## 4. Leer un log: el incidente del puerto

El primer arranque del servicio falló. El log, tal cual:

```
LOG:      could not bind IPv6 address "::1"
HINT:     Is another postmaster already running on port 5432?
LOG:      could not bind IPv4 address "127.0.0.1"
WARNING:  could not create listen socket
FATAL:    could not create any TCP/IP sockets
LOG:      database system is shut down
```

**Se lee de abajo arriba.** El último mensaje es la consecuencia; el primero, la causa. Quedarse en el `FATAL` es saber que el paciente murió, no de qué. Y los `HINT` merecen leerse: Postgres sugiere la causa más probable.

`bind` es la llamada al sistema con la que un proceso reclama un puerto al kernel. El kernel solo lo concede a uno: es reservar una mesa, no se puede reservar dos veces. Que falle `bind` **solo admite una lectura** — el puerto ya está cogido.

Dos señales de que no era problema del cluster:

- `ExecStartPre=/usr/bin/postgresql-check-db-dir ... status=0/SUCCESS` — la comprobación del directorio de datos pasó. Un `initdb` mal hecho o unos permisos rotos habrían petado ahí, sin llegar a ejecutar `postgres`.
- `database system is shut down` sin errores previos de recuperación. Arrancó, no pudo abrir la puerta, se apagó limpiamente.

**La división del trabajo:** el log dice **qué** falló; las herramientas de observación dicen **quién** lo causó. `ss -tulpn` señaló a `docker-proxy` — un contenedor de desarrollo publicando el 5432.

**Decisión:** mover el puerto publicado del contenedor, no el del cluster. Tener dos Postgres y no saber a cuál te conectas es peor que el problema original.

Lo que hace esto seguro: si Odoo habla con su Postgres, lo hace por la **red interna de Docker** (`db:5432`). El `ports:` del Compose solo existe para llegar desde fuera. Cambiarlo no toca nada de lo que Odoo necesita, y los volúmenes no se tocan.

```yaml
ports:
  - "127.0.0.1:5433:5432"
```

Tres partes: dirección del host, puerto del host, puerto del contenedor. El `127.0.0.1` delante no es cosmético: sin él, el `0.0.0.0` que mostraba `ss` significa que el contenedor escucha en **todas** las interfaces, y en una wifi pública cualquiera de esa red alcanza el puerto.

Resultado: cluster local en 5432, contenedor en 5433.

### Reload frente a restart

`reload` manda `SIGHUP`: el proceso sigue vivo, con el mismo PID, y relee su configuración. Las conexiones abiertas no se cortan.

**Para `pg_hba.conf` basta `reload`**, a diferencia de lo que ocurrió con SSH en el VPS, donde hizo falta `restart`. Está diseñado para releerse en caliente: cambiar reglas de acceso en producción no puede implicar tirar a todos los usuarios. La analogía: el portero recibe una lista nueva sin que nadie tenga que salir del edificio.

Cómo distinguir que fue recarga y no reinicio: mismo `Main PID`, `Active: since` sin resetear, y en el log `received SIGHUP, reloading configuration files`.

Matiz: las reglas nuevas afectan a conexiones **futuras**. Una sesión ya abierta no se vuelve a autenticar.

### Validar antes de aplicar

No existe un equivalente a `sshd -t`, pero hay algo mejor: la vista `pg_hba_file_rules` lee el fichero **del disco** y lo devuelve interpretado, con una columna `error`. No es la configuración activa: es una simulación de lo que pasaría al recargar, ejecutable mientras la configuración vieja sigue funcionando.

Copia de seguridad siempre antes de tocar un fichero que controla el acceso. Mismo reflejo que con `sshd_config`.

---

## 5. El modelo relacional, visto en Pagila

Lo que devuelve `\d film`:

```
Foreign-key constraints:
    film_language_id_fkey FOREIGN KEY (language_id) REFERENCES language(language_id)
Referenced by:
    TABLE film_actor ...
    TABLE film_category ...
    TABLE inventory ...
```

`film` apunta a `language`: cada película tiene un idioma, y ese dato no se repite dentro de `film` — se guarda una vez en `language` y aquí solo hay un número que la señala. Y tres tablas apuntan a `film`.

La información está **troceada y conectada por números**, no amontonada. La analogía: en vez de escribir la dirección completa del almacén en cada albarán, se escribe el código del almacén; si el almacén se muda, cambia una fila y no diez mil.

**De ahí sale la pregunta que abre el Bloque 1:** si el título está en `film`, el nombre del actor en `actor`, y lo único que las une es `film_actor` con dos números, ¿cómo se obtiene una lista de películas con sus actores? Esa operación de volver a juntar lo que el modelo separó es el `JOIN`.

### Lo que trae Pagila

1.000 películas, 200 actores, 51.061 pagos. Volumen suficiente para que se note la diferencia entre una consulta buena y una mala.

`payment` aparece como `partitioned table`, con 54 tablas `payment_pAAAA_MM` debajo. Es **una sola tabla** dividida físicamente por meses: se consulta `payment` y Postgres decide a qué trozos bajar según las fechas del `WHERE`. La analogía: preguntas cuántos libros hay en la biblioteca y el bibliotecario suma las salas sin que tú sepas que hay salas. Material del Bloque 4.

Dos columnas curiosas de `film`, que no son Bloque 1 pero conviene que no parezcan magia:

- `fulltext` no guarda el texto, sino sus palabras reducidas a raíz con su posición (`'amaz':4`). Un índice de búsqueda guardado como dato.
- `length_hours` no está almacenada: es una columna generada, calculada a partir de `length` cada vez que se consulta.

### Los dos errores esperados al cargar

**`must be able to SET ROLE "postgres"`**, decenas de veces, cada una seguida de un `CREATE TABLE` que sí funciona. El fichero fue generado con `pg_dump` desde un servidor donde todo pertenecía a `postgres`, así que intercala sentencias que fijan ese propietario. Un rol normal no puede convertirse en `postgres` y esas líneas fallan — pero **las tablas se crean igual y quedan a nombre del rol propio**, que es lo que se quiere.

La analogía: el fichero dice «pon la etiqueta con el nombre del dueño anterior». Sin esa etiqueta, el mueble se monta igual y se queda a tu nombre.

**`extension "vector" is not available`** — este sí pierde algo. Pagila 4.1 incluye una tabla `film_embedding` que necesita `pgvector`, y de ahí una cascada de cuatro o cinco errores. Es búsqueda vectorial, sin relación con el Bloque 1.

> **`psql -f` no para en el primer error.** Sigue ejecutando, y lo siguiente falla en cascada por dependencias. Cuando haya fallos, el primero es el que importa; el resto suele ser ruido derivado.

### COPY frente a INSERT

`pagila-data.sql` usa 70 bloques `COPY`; `pagila-insert-data.sql` tiene los mismos datos como decenas de miles de `INSERT`. `COPY` carga en bloque, en una pasada; cada `INSERT` es una sentencia independiente con su propio coste. La analogía: una cinta transportadora frente a bajar las cajas de una en una.

---

## Referencia de comandos

### Instalación y cluster

```bash
sudo pacman -S postgresql          # -S = sync, instala desde repos. Crea el usuario de sistema postgres
postgres --version

sudo -iu postgres initdb -D /var/lib/postgres/data \
     --locale=C.UTF-8 --encoding=UTF8 --data-checksums
```

- `sudo -iu postgres` — ejecuta como el usuario `postgres`. `-u` elige usuario, `-i` simula login completo (su entorno, su home). El cluster debe pertenecer a `postgres`; creado como root, el servicio no podría leerlo.
- `-D` — directorio de datos. Es la ruta que espera la unidad de systemd de Arch.
- `--locale=C.UTF-8` — orden byte a byte, rápido y predecible. Otro locale ordena acentos distinto y cambia el resultado de un `ORDER BY`.
- `--encoding=UTF8` — innegociable si va a entrar un dump de Odoo.
- `--data-checksums` — detecta corrupción silenciosa de disco. Añadirlo después obliga a parar y reconvertir el cluster.
- `--auth-local=peer --auth-host=scram-sha-256` — evita el `trust` por defecto. **No se usó y hubo que arreglarlo después.**

> En Btrfs, `/var/lib/postgres/data` lleva el atributo `C` (No_COW), que desactiva el checksumming del sistema de ficheros. Razón de más para `--data-checksums`.

### Servicio

```bash
sudo systemctl enable --now postgresql.service   # enable = en cada boot; --now = además ahora
systemctl status postgresql
sudo systemctl reload postgresql                 # SIGHUP: relee config sin cortar conexiones
journalctl -u postgresql -n 30                   # -u = unidad; -n = últimas N líneas
```

### Diagnóstico de red

```bash
sudo ss -tulpn | grep 5432       # quién escucha en ese puerto
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
```

`ss` lista sockets (sustituto de `netstat`): `-t` TCP, `-u` UDP, `-l` solo los que escuchan, `-p` el proceso dueño (necesita `sudo`), `-n` puertos numéricos.

### Roles y bases

```bash
sudo -u postgres createuser -d -P miguel   # -d = --createdb; -P = --pwprompt
sudo -u postgres dropuser miguel           # sin confirmación; -i para que pregunte
createdb pagila                            # el creador es el propietario
dropdb pagila
psql -l                                    # listar bases y salir
```

- `-d` (`--createdb`) — enciende el atributo `CREATEDB`. **Sin este flag el rol nace sin él**: `createdb` devuelve `permission denied to create database`.
- `-P` (`--pwprompt`) — pide la contraseña por teclado, dos veces. Por teclado y no por flag a propósito: en la línea de comandos quedaría en el historial de la shell y sería visible en `ps`.
- `--echo` (`-e`) — imprime el SQL que envía antes de ejecutarlo. Útil para ver que el wrapper no hace magia.

> **Cuidado con `-c` en `createuser`:** no es «create», es `--connection-limit` y espera un número. `-c -P` interpretaría `-P` como ese valor.

Equivalentes en SQL:

| Shell | SQL |
|---|---|
| `createdb pagila` | `CREATE DATABASE pagila;` |
| `dropdb pagila` | `DROP DATABASE pagila;` |
| `createuser x` | `CREATE ROLE x LOGIN;` |
| `dropuser x` | `DROP ROLE x;` |
| `psql -l` | `\l` |

Los wrappers son clientes: abren conexión, mandan la sentencia y salen. **No son SQL** — escribir `createuser` dentro de `psql` da `syntax error at or near "createuser"`.

Trampa: `createuser` pone `LOGIN` por defecto; `CREATE ROLE` **no**. `CREATE USER` sí, porque es su alias.

```sql
CREATE ROLE miguel LOGIN CREATEDB PASSWORD 'xxx';
ALTER ROLE miguel CREATEDB;
GRANT pg_read_all_data TO miguel;
REASSIGN OWNED BY viejo TO nuevo;
DROP OWNED BY viejo;
```

### Inspeccionar el catálogo

```sql
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin
FROM pg_roles ORDER BY rolname;          -- en un servidor heredado, suele dar sorpresas

SELECT current_user, current_database();
```

### Configuración del servidor

```bash
psql -d pagila -c "SHOW hba_file;"          # preguntar la ruta al servidor, no adivinarla
psql -d pagila -c "SHOW config_file;"
psql -d pagila -c "SHOW data_directory;"

sudo grep -vE '^\s*#|^\s*$' /var/lib/postgres/data/pg_hba.conf   # solo reglas activas
```

`grep -v` invierte la selección (muestra lo que **no** encaja); `-E` activa regex extendidas, que es lo que hace funcionar el `|` como «o».

```bash
sudo -u postgres psql -c "SELECT line_number, type, database, user_name, address, auth_method, error
                          FROM pg_hba_file_rules;"
```

La columna `error` debe estar vacía en todas las filas.

> **Comodines en fish:** `sudo ls /var/lib/postgres/data/pg_hba.conf*` falla con `No matches for wildcard`. El `*` lo expande la **shell**, antes de que `sudo` exista, y fish no puede leer un directorio cerrado, así que aborta la línea entera (bash pasaría el asterisco literal). Solución: `sudo sh -c 'ls -l ...conf*'`, donde la expansión ocurre ya como root. Volverá a aparecer con `/var/log` y con los directorios de Odoo.

### Conexión

```bash
psql -d pagila                     # socket Unix → regla local → peer
psql -h localhost -d pagila        # TCP → regla host → scram-sha-256
psql -U postgres -d postgres       # pedir otro rol explícitamente
sudo -u postgres psql              # la vía correcta al superusuario
psql -d pagila -c "SELECT 1;"      # -c: una sentencia y salir. La pieza para scripts
psql -d pagila -f fichero.sql      # -f: ejecutar un fichero
```

### Cargar datos

```bash
psql -d pagila -f pagila-schema.sql     # primero la estructura
psql -d pagila -f pagila-data.sql       # después las filas. El orden no es opcional

psql -d pagila -f pagila-schema.sql 2>&1 | grep -i error
```

`2>&1` redirige la salida de errores (descriptor 2) a la estándar (descriptor 1) para que ambas pasen por el filtro. `|` entrega la salida de la izquierda como entrada de la derecha. `grep -i` ignora mayúsculas.

```bash
pg_dump -Fc -d origen -f cliente.dump   # -Fc = formato custom: comprimido y restaurable selectivamente
createdb cliente
pg_restore -d cliente cliente.dump      # la base destino debe existir antes
```

### Meta-comandos de psql

Empiezan por barra y **no son SQL**: los interpreta `psql`, no el servidor.

| | |
|---|---|
| `\l` | listar bases |
| `\c pagila` | conectar a otra base sin salir |
| `\dt` | listar tablas |
| `\d film` | describir tabla: columnas, tipos, índices, claves ajenas, triggers |
| `\du` | listar roles |
| `\x` | salida expandida (vertical). **No afecta a `\d`**, solo a resultados de consultas |
| `\timing` | cuánto tarda cada consulta |
| `\i fichero.sql` | ejecutar un fichero |
| `\e` | abrir la última consulta en `$EDITOR` |
| `\r` | descartar el búfer de consulta |
| `\?` · `\h SELECT` | ayuda de meta-comandos · de sintaxis SQL |
| `\q` | salir |

> **El prompt informa.** `=>` rol normal · `=#` superusuario · `->` sentencia a medias esperando el punto y coma. Cuando aparece `->` por un paréntesis o una comilla sin cerrar, `\r` limpia; es más limpio que aporrear intro.

### ~/.psqlrc

`psql` lo lee al arrancar, como la shell su `.bashrc`:

```bash
printf '%s\n' '\x auto' '\timing on' '\set HISTSIZE 5000' > ~/.psqlrc
```

`printf '%s\n'` imprime cada argumento en su línea, más predecible que `echo` con varias. `>` sobrescribe; `>>` añadiría al final.

- `\x auto` — mide el ancho de la salida: si cabe, horizontal; si no, vertical. Horizontal para explorar conjuntos, vertical para inspeccionar un registro. Evita pulsar `\x` cada dos comandos.
- `\timing on` — primera señal de que algo va mal. Instrumento principal a partir del Bloque 4.
- `\set HISTSIZE 5000` — más historial entre sesiones.

---

## Analogías de referencia

| Concepto | Analogía |
|---|---|
| Cluster | El edificio que levanta `initdb`: existe aunque no haya nadie dentro |
| Base de datos | Un piso. Aislado: desde uno no se ve lo que hay en otro |
| Esquema | Una habitación dentro del piso |
| Servidor | El edificio con las luces encendidas y el portero en su sitio |
| Rol | El inquilino con llave. Puede ser una persona o un grupo |
| Propietario | Titular del contrato del piso, frente al administrador del edificio (superusuario) |
| Usuario / grupo | No son especies distintas: son miembros de la misma estructura, unos con tarjeta y otros sin ella |
| Atributo / pertenencia | Casillas marcadas en tu ficha del gimnasio / grupos a los que perteneces |
| `pg_hba.conf` | El portero con su lista, mirando las reglas en orden |
| `trust` | El portero no está. Pasa cualquiera pidiendo el rol que quiera |
| `peer` | El portero llama al registro del edificio: el dato no lo aportas tú |
| `scram-sha-256` | Un reto irrepetible, como la autenticación por clave SSH |
| Contraseña de `sudo` | La del taxi que te lleva al portal, no la del portal |
| `bind` | Reservar una mesa: no se puede reservar dos veces |
| `reload` | El portero recibe una lista nueva sin que nadie salga del edificio |
| Tabla particionada | Preguntas cuántos libros hay y el bibliotecario suma las salas sin que sepas que hay salas |
| `COPY` frente a `INSERT` | Cinta transportadora frente a bajar cajas de una en una |
| Clave ajena | El código del almacén en el albarán, en vez de la dirección entera |

---

## Material

- **Documentación oficial** (postgresql.org/docs/current) — capítulos 19 (servidor), 21.1 (`pg_hba.conf`), 22 (roles), 1 (tutorial) y la referencia de `psql`.
- **ArchWiki, artículo PostgreSQL** — lo específico de Arch y CachyOS: rutas, unidad de systemd, actualización de versión mayor.
- **Pagila** (github.com/devrimgunduz/pagila).
- `man initdb`, `man psql`.

---

## Pendiente

- Criterio de cierre: explicación en voz alta, en frío y sin notas.
- Cuando haya una réplica anonimizada de un cliente, restaurarla junto a `pagila` con `pg_dump -Fc` y `pg_restore`. No bloquea el Bloque 1, pero es lo que convierte el carril en «casos reales de clientes» como dice el roadmap.
