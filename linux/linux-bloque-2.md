# Linux/VPS · Bloque 2 — systemd de verdad

Unit files escritos a mano, targets, dependencias, `journalctl` con filtros y timers frente a cron.

**Entorno de referencia:** Ubuntu 24.04 · systemd 255. Las directivas y valores de este documento existen en esa versión; con otra, confírmalos en la documentación de la versión instalada (`systemctl --version`).

---

# Parte 1 · Teoría

## 1. Procesos, sesiones y servicios

**Proceso.** Un programa en ejecución. El kernel le asigna un número, el **PID**. Todo proceso lo crea otro proceso, su **padre**; el número del padre es el **PPID**.

**Huérfano.** Si el padre muere antes que el hijo, el kernel asigna el hijo al **PID 1**. Que el PID 1 sea su padre no implica que nadie lo gestione: solo lo ha adoptado.

**PID 1.** El primer proceso del sistema. En Ubuntu es **systemd**; `/sbin/init` es un enlace simbólico a él.

**Sesión.** Al entrar por SSH se crea una cadena de procesos: `sshd` de la conexión → shell de login (aparece con guion: `-fish`, `-bash`) → los programas que lances. Todo lo lanzado a mano pertenece a esa sesión.

**Señales.** Avisos cortos que el kernel entrega a un proceso. Ante cada una, el proceso hace la acción por defecto, la captura para hacer otra cosa, o la ignora (salvo `SIGKILL`).

| Señal | Número | Quién la envía | Acción por defecto | Uso habitual |
|---|---|---|---|---|
| `SIGHUP` | 1 | La shell, al cerrarse la terminal | Terminar | Muchos servicios la capturan para releer su configuración (`sshd`) |
| `SIGINT` | 2 | `Ctrl-C` | Terminar | En Python provoca `KeyboardInterrupt` |
| `SIGTERM` | 15 | `kill`, `systemctl stop` | Terminar | La forma normal de pedir que un programa pare |
| `SIGKILL` | 9 | `kill -9`, el kernel sin memoria (*OOM killer*) | Terminar sin aviso | No se puede capturar ni ignorar |

**`&` y `nohup`.** `&` lanza un programa en segundo plano: libera la terminal, pero el proceso sigue siendo hijo de la shell y muere con ella. `nohup` hace que el programa ignore `SIGHUP` y sobreviva al cierre de la sesión, pero queda sin vigilancia: nadie lo reinicia si cae, no arranca tras un reinicio y su salida va a `nohup.out`.

**Servicio.** Un programa que gestiona systemd a partir de una **unit**: un fichero que dice cómo lanzarlo, con qué identidad, cuándo y qué hacer si falla. Un servicio no tiene PID; tiene nombre (`labweb.service`). Su proceso principal sí lo tiene (`Main PID:`), y cambia en cada reinicio. Un servicio no tiene terminal.

**Daemon.** Programa que funciona en segundo plano, sin terminal, esperando trabajo. Que algo sea un daemon no implica que esté gestionado.

## 2. systemd y las units

**systemd** arranca el sistema, lanza y vigila los servicios, recoge su salida en el journal y los para al apagar.

**Units.** Cada cosa que gestiona systemd es una unit. El tipo lo indica la extensión:

| Tipo | Qué representa |
|---|---|
| `.service` | Un programa que se lanza y se vigila |
| `.socket` | Un puerto o socket que systemd abre por adelantado para un servicio |
| `.timer` | Un momento en el que arrancar un servicio |
| `.target` | Un punto del arranque que agrupa otras units (`multi-user.target`) |
| `.scope` | Procesos que systemd no lanzó pero vigila (las sesiones de usuario: `session-N.scope`) |
| `.slice` | Una rama del árbol de grupos de procesos (`system.slice`, `user.slice`) |

**cgroups.** systemd coloca cada unit en un grupo de procesos del kernel. Así sabe qué procesos pertenecen a cada unit aunque cambien de padre. Los servicios cuelgan de `system.slice`; las sesiones, de `user.slice/user-UID.slice`.

**Dónde viven las fichas:**

| Ruta | De quién | Prioridad |
|---|---|---|
| `/etc/systemd/system/` | Del administrador | Gana |
| `/run/systemd/...` | Generadas en ejecución, temporales | Media |
| `/usr/lib/systemd/system/` | De los paquetes; se sobrescriben al actualizar | Pierde |

**Copia en memoria.** systemd lee las fichas una vez y trabaja con esa copia. Si editas una, no se entera hasta que ejecutes `daemon-reload`. Mientras tanto, `status` avisa con `changed on disk`.

**Estados habituales:**

| Estado | Significado |
|---|---|
| `active (running)` | El proceso principal está funcionando |
| `active (exited)` | El proceso terminó con éxito y la unit se considera activa (`RemainAfterExit=yes`) |
| `active (abandoned)` | Un scope cuya sesión se cerró pero conserva procesos |
| `inactive (dead)` | Parado. Normal tras un `stop` limpio o tras un `oneshot` |
| `failed` | Terminó con error, o systemd no pudo lanzarlo |

En la línea `Loaded:` aparece además si la unit está `enabled`, `disabled` o `static` (sin sección `[Install]`: no se puede habilitar; la arranca otra unit).

## 3. El unit file de un servicio

### Secciones

| Sección | Qué describe | Cuándo la lee systemd |
|---|---|---|
| `[Unit]` | Qué es y de qué depende | Siempre |
| `[Service]` | Cómo se ejecuta | Siempre |
| `[Install]` | En qué target se apunta | Solo `systemctl enable` y `disable` |

`[Unit]` e `[Install]` son comunes a todos los tipos de unit (servicio, timer, socket). La sección central cambia según el tipo: `[Service]`, `[Timer]`, `[Socket]`.

### Reglas de sintaxis

- Una directiva por línea, `Nombre=valor`, sin espacios alrededor del `=`.
- Los nombres **distinguen mayúsculas**. Una directiva desconocida o en la sección equivocada se **ignora** con un aviso en el journal, y la unit arranca igual. Es el tipo de error más peligroso, porque no se ve.
- Las rutas de `ExecStart=` van completas: systemd no usa el `PATH` de tu shell. `ExecStart=` no es una shell: `&`, `|`, `>` no funcionan.

`man systemd.directives` es el índice: dice en qué página se explica cada directiva.

### `[Unit]`: qué es y de qué depende

| Directiva | Qué hace | Documentación |
|---|---|---|
| `Description=` | Nombre legible en `status` y en el journal | `systemd.unit` |
| `Wants=`, `Requires=`, `BindsTo=`, `PartOf=` | Dependencia: si esta unit arrastra a otra (tabla más abajo) | `systemd.unit` |
| `After=`, `Before=` | Orden: cuál arranca antes | `systemd.unit` |
| `StartLimitBurst=`, `StartLimitIntervalSec=` | Límite de arranques seguidos | `systemd.unit` |

**Dependencias.** Hay dos ejes independientes: **dependencia** (si una unit arrastra a otra) y **orden** (cuál arranca antes).

| Directiva | Al arrancar esta unit | Si la otra se para explícitamente | Si la otra cae sola |
|---|---|---|---|
| `Wants=` | Arranca la otra | Nada | Nada |
| `Requires=` | Arranca la otra | Esta se para (y un `restart` se propaga) | Nada |
| `BindsTo=` | Arranca la otra | Esta se para | Esta se para |
| `PartOf=` | — | Esta se para o reinicia; solo en esa dirección | — |

- **`After=` / `Before=`** solo fijan el orden. Sin `After=`, systemd arranca las dos a la vez. Lo habitual es `Wants=` o `Requires=` junto con `After=`.
- Una parada por dependencia es una parada **limpia** (`SIGTERM`), así que `Restart=on-failure` no actúa. Y la unit de la que dependes no arranca a quien depende de ella cuando vuelve.
- **Dependencias por defecto.** Todo servicio normal depende de `sysinit.target`, `basic.target`, `system.slice` y `systemd-journald.socket`, sin escribirlas.
- **Plantillas.** Una unit con `@` (`postgresql@.service`) es una plantilla; lo que va entre `@` y la extensión (`16-main`) es la **instancia**, y dentro de la ficha se usa como `%i`.

**Límite de arranques.** Por defecto, si una unit arranca más de 5 veces en 10 segundos (`StartLimitBurst=`, `StartLimitIntervalSec=`), systemd deja de intentarlo: `Start request repeated too quickly`. Protege de los bucles de caídas. Se sale con `reset-failed`. Van en `[Unit]` aunque afecten a `Restart=`, que está en `[Service]`.

### `[Service]`: cómo se ejecuta

| Directiva | Qué hace | Documentación |
|---|---|---|
| `ExecStart=` | Comando que se ejecuta | `systemd.service` |
| `Type=` | Cuándo se considera arrancado | `systemd.service` |
| `Restart=` | Cuándo volver a arrancarlo | `systemd.service` |
| `RestartSec=` | Espera antes de cada reinicio (por defecto, 100 ms) | `systemd.service` |
| `ExecReload=` | Qué hacer al recibir `reload`; sin ella, `reload` no existe | `systemd.service` |
| `RemainAfterExit=` | Considerarlo activo aunque su proceso haya terminado | `systemd.service` |
| `User=`, `Group=` | Identidad del proceso; sin `User=`, corre como root | `systemd.exec` |
| `Environment=` | Variables de entorno, `NOMBRE=valor`; puede repetirse o llevar varias separadas por espacios | `systemd.exec` |
| `WorkingDirectory=` | Carpeta en la que arranca | `systemd.exec` |
| `KillMode=` | Qué procesos mata al parar; `process` solo mata el principal | `systemd.kill` |

**`Type=`**

| Valor | Se considera arrancado cuando… | Si el ejecutable no existe |
|---|---|---|
| `simple` (por defecto) | Se crea el proceso | `start` no avisa; el fallo aparece después |
| `exec` | El programa se ha ejecutado | `start` falla en el momento |
| `oneshot` | El proceso termina con éxito | `start` falla |
| `notify` | El programa avisa a systemd de que está listo | Requiere soporte en el propio programa |

`exec` es la opción recomendada para servicios que se quedan funcionando. No detecta fallos que ocurren después de ejecutarse el programa (un fichero que no puede leer, un puerto ocupado).

**`Restart=`**

| Cómo termina el proceso | `no` | `on-failure` | `always` |
|---|---|---|---|
| Código 0 o `SIGHUP`/`SIGINT`/`SIGTERM`/`SIGPIPE` | — | — | Reinicia |
| Código distinto de 0 | — | Reinicia | Reinicia |
| Otra señal (`SIGKILL`, falta de memoria) | — | Reinicia | Reinicia |
| `systemctl stop` | — | — | — |

`on-failure` es la recomendada para servicios de larga duración. El límite de arranques que la frena está en `[Unit]`.

**Usuario dedicado.** Cada servicio continuo debería correr con su propio usuario de sistema (mínimo privilegio): si alguien explota un fallo del programa, obtiene los permisos de ese usuario, no los de root. Las cuentas de servicio tienen UID por debajo de 1000, shell `nologin` y ninguna contraseña utilizable. El código del servicio conviene que sea de root y solo legible por el servicio, para que no pueda modificarse a sí mismo.

### `[Install]`: en qué target se apunta

| Directiva | Qué hace | Documentación |
|---|---|---|
| `WantedBy=` | Target en cuyo `.wants/` se crea el enlace al habilitar | `systemd.unit` |

**Targets.** Un **target** es una etapa del arranque que agrupa units. `multi-user.target` es el sistema funcionando en modo normal sin entorno gráfico; `graphical.target` lo incluye y añade el escritorio; `sockets.target` y `timers.target` son etapas donde se apuntan sockets y timers. `systemctl get-default` dice qué target alcanza la máquina.

`WantedBy=multi-user.target` no hace nada por sí sola. Al ejecutar `systemctl enable`, se crea un enlace simbólico en `/etc/systemd/system/multi-user.target.wants/`. Al arrancar, systemd lanza todo lo que hay en esa carpeta. Si el target nunca se alcanza, el servicio nunca arranca solo.

`start` arranca ahora; `enable` deja apuntado para los próximos arranques. Son independientes. Una unit sin `[Install]` es `static`: no se puede habilitar, solo arrancar a mano o como dependencia de otra.

## 4. Drop-ins

Un **drop-in** es un fichero `.conf` en `/etc/systemd/system/<unit>.d/` que se suma a la ficha sin modificarla. Sirve sobre todo para ajustar units de paquetes, cuyos cambios en `/usr/lib` se perderían al actualizar.

- Debe repetir la cabecera de sección; sin ella, sus líneas se ignoran.
- Las directivas de lista (`After=`, `Wants=`, `Environment=`) se acumulan. Las de valor único (`User=`, `Type=`) se sustituyen.
- `systemctl status` muestra la línea `Drop-In:` cuando existe alguno.

## 5. Diagnosticar un servicio que falla

**Orden:** `systemctl status` → `journalctl -u` → la ficha.

**Quien hace la acción que falla, escribe el error.** systemd lee la ficha, prepara el usuario y lanza el programa. La aplicación abre ficheros, reserva puertos, conecta a bases de datos.

| Quién falla | Etiqueta en el journal | Código de salida | Dónde buscar |
|---|---|---|---|
| systemd, al preparar o lanzar | `systemd[1]:` o `(programa)[PID]:` entre paréntesis | 200 en adelante | La ficha |
| La aplicación, ya lanzada | `programa[PID]:` | Bajo (1, 2…) | Lo que usa el programa |

Códigos propios de systemd (`man systemd.exec`, *PROCESS EXIT CODES*): `200/CHDIR` (no existe `WorkingDirectory=`), `203/EXEC` (no pudo ejecutar el programa), `217/USER` (no existe el usuario). Los códigos bajos los define cada programa: en `curl`, 7 es «no pude conectar»; en el estado del servicio, systemd les pone un nombre (`2/INVALIDARGUMENT`, `7/NOTRUNNING`) que no tiene por qué corresponder a su significado real.

En un **bucle de caídas**, la causa está en la primera caída de la serie, no en las últimas líneas.

**Errores que no hacen fallar el servicio** (solo los detectan `systemd-analyze verify`, el aviso del journal o `systemctl show`): directivas mal escritas, en la sección equivocada, o una ficha editada sin `daemon-reload`.

## 6. El journal

El **journal** es el registro de systemd. Guarda cada mensaje con campos (`_SYSTEMD_UNIT`, `_PID`, `_UID`, `_COMM`, `PRIORITY`, arranque…), que son los que permiten filtrar.

- **Todo lo que un servicio imprime** (salida normal y de errores) llega al journal sin que el programa sepa nada de logs.
- **Prioridad.** De más a menos grave: `emerg`, `alert`, `crit`, `err`, `warning`, `notice`, `info`, `debug`. Lo que imprime un programa llega como `info`, incluido un traceback: `-p err` encuentra qué servicio falló (lo marca systemd), no por qué.
- **Persistencia.** Si existe `/var/log/journal`, el journal conserva los arranques anteriores. En Ubuntu es persistente por defecto.
- **La hora es la de llegada.** Con el búfer de Python, un mensaje puede llegar mucho después de imprimirse. Python retiene su salida cuando no escribe en una terminal; `PYTHONUNBUFFERED=1` o `python3 -u` lo desactivan.
- **Un log dice lo que el programa cree que pasa.** Si un programa anuncia algo antes de hacerlo, el log puede afirmar lo que luego falla.
- **Permisos.** Para leer los mensajes del sistema sin `sudo`, el usuario tiene que estar en el grupo `systemd-journal`.

## 7. Activación por socket

Una unit `.socket` hace que systemd abra un puerto por adelantado y se lo pase al servicio con su mismo nombre. Con `Accept=no`, un único proceso recibe el puerto y atiende todas las conexiones; con `Accept=yes`, se lanza un proceso por conexión. Si el servicio está parado y llega una conexión, systemd lo arranca (`TriggeredBy:` en el `status` del servicio).

Consecuencias: en `ss`, el puerto aparece en manos de `systemd` (PID 1) y del servicio; y el puerto lo decide la unit `.socket`, no la configuración del programa.

## 8. Timers y cron

Un **timer** arranca el servicio con su mismo nombre en un momento dado. El timer dice cuándo; el servicio, qué. Para tareas que hacen algo y terminan, el servicio usa `Type=oneshot`, y no necesita `[Install]`: se habilita el timer.

| Directiva del timer | Qué hace |
|---|---|
| `OnCalendar=` | Fecha y hora, formato `año-mes-día hora:minuto:segundo` con `*` y `/`. `*:0/5` = cada 5 minutos; `*-*-* 6:00` = cada día a las 6:00 |
| `Persistent=true` | Si la máquina estaba apagada, ejecuta lo pendiente al arrancar |
| `RandomizedDelaySec=` | Retraso aleatorio, para repartir la carga |
| `WantedBy=timers.target` | En `[Install]`, para habilitar el timer |

**cron** lee una tabla de tareas por usuario (`crontab`), con cinco campos de tiempo: minuto, hora, día del mes, mes, día de la semana. Envía la salida de cada tarea **por correo**; sin servidor de correo (MTA), la descarta. No registra si la tarea falló.

| | cron | Timer |
|---|---|---|
| Salida de la tarea | Por correo, o descartada | En el journal |
| Fallo visible | No | Sí: `failed`, `systemctl --failed` |
| Máquina apagada a la hora prevista | Se pierde | Se recupera con `Persistent=true` |
| Usuario | El dueño de la tabla | El de `User=` |
| Dependencias, límites, entorno | No | Todo lo de un servicio |

---

# Parte 2 · Ejemplos

## Servicio de larga duración

```ini
# /etc/systemd/system/labweb.service
[Unit]
Description=Python local web server

[Service]
Type=exec
ExecStart=/usr/bin/python3 /opt/labweb/labweb.py
User=labweb
Restart=on-failure
RestartSec=2
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Usuario dedicado, fallo inmediato si el programa no se puede lanzar, reinicio a los 2 segundos tras un error, salida de Python sin retraso, arranque automático. El usuario se crea con `sudo useradd --system --no-create-home --shell /usr/sbin/nologin labweb`.

## Tarea periódica: servicio `oneshot` y timer

```ini
# /etc/systemd/system/labweb-health.service
[Unit]
Description=Healthcheck de labweb

[Service]
Type=oneshot
ExecStart=/usr/bin/curl -fsS --max-time 5 http://127.0.0.1:8080/health
User=labweb
```

```ini
# /etc/systemd/system/labweb-health.timer
[Unit]
Description=Healthcheck de labweb cada 5 minutos

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

Se activa con `sudo systemctl enable --now labweb-health.timer`. Si `curl` no conecta, el servicio queda `failed` y el error queda en el journal.

La misma tarea en cron (`crontab -e`), sin registro del resultado:

```
*/5 * * * * curl -fsS --max-time 5 http://127.0.0.1:8080/health
```

## Drop-in con dependencia

```ini
# sudo systemctl edit labweb → /etc/systemd/system/labweb.service.d/override.conf
[Unit]
Wants=postgresql@16-main.service
After=postgresql@16-main.service
```

## Dos units de PostgreSQL en Ubuntu

- `postgresql@16-main.service`, instancia de la plantilla `postgresql@.service`, ejecuta el servidor. Lleva `PartOf=postgresql.service` y `Before=postgresql.service`.
- `postgresql.service` ejecuta `/bin/true` con `RemainAfterExit=yes`: queda `active (exited)` y sirve para controlar todos los clústeres a la vez.
- Parar `postgresql.service` para el clúster. Parar el clúster no cambia `postgresql.service`.

Por tanto, un servicio que necesite la base de datos (Odoo) debe depender de `postgresql@16-main.service`. Si dependiera de `postgresql.service`, seguiría funcionando con el servidor caído.

## SSH en Ubuntu 24.04

```ini
# ssh.socket (fragmento)
[Socket]
ListenStream=22
Accept=no
[Install]
WantedBy=sockets.target
```

```ini
# ssh.service (fragmento)
ExecStartPre=/usr/sbin/sshd -t
ExecStart=/usr/sbin/sshd -D $SSHD_OPTS
ExecReload=/usr/sbin/sshd -t
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
Restart=on-failure
Type=notify
```

- `ssh.socket` abre el puerto 22; `ssh.service` lanza `sshd` y le pasa el puerto.
- `reload` valida la configuración y envía `SIGHUP` a `sshd`, que la relee.
- `KillMode=process`: un `restart` solo mata el `sshd` principal; las sesiones abiertas sobreviven (en el journal: `Unit process ... remains running after unit stopped`).
- Cambiar `Port` en `sshd_config` no basta: el puerto lo fija `ssh.socket`.

## Fallos típicos y cómo se ven

| Causa | `status` | Línea del journal |
|---|---|---|
| El ejecutable de `ExecStart=` no existe | `status=203/EXEC` | Solo el código; la ruta, en la línea `Process:` |
| El usuario de `User=` no existe | `status=217/USER` | `(python3)[PID]: Failed to determine user credentials` |
| El script no existe | `status=2` | `python3[PID]: can't open file ...: [Errno 2] No such file or directory` |
| El script no se puede leer | `status=2` | `[Errno 13] Permission denied` |
| Puerto ocupado | `status=1` | `OSError: [Errno 98] Address already in use` |
| Ficha editada sin `daemon-reload` | `active`, sin fallo | `Warning: The unit file ... changed on disk` |
| Directiva mal escrita (`user=`, `Restrat=`) | `active`, sin fallo | `Unknown key name 'user' in section 'Service', ignoring` |
| Bucle de caídas | `failed` | `Start request repeated too quickly` |
| `kill -9` con `Restart=on-failure` | Reiniciado | `code=killed, status=9/KILL` y `Scheduled restart job` |

## Preguntas al journal

| Pregunta | Comando |
|---|---|
| Qué ha dicho un servicio en los últimos 15 minutos | `journalctl -u labweb -S '15 min ago'` |
| Avisos y errores de todo el sistema en este arranque | `journalctl -b -p warning` |
| Qué dijo un servicio en el arranque anterior | `journalctl -u labweb -b -1` |
| Si un servicio se recargó o reinició un día concreto | `journalctl -u ssh -S '2026-09-11' -U '2026-09-12' \| grep -iE 'reload\|stopp\|start'` |
| Qué comandos se ejecutaron con `sudo` en un intervalo | `journalctl -t sudo -S '...' -U '...'` |
| Con qué usuario se ejecutó un programa | `journalctl -u labweb-health _COMM=curl -o verbose \| grep _UID` |

---

# Parte 3 · Comandos útiles del bloque

## Procesos

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ps -o pid,ppid,user,cmd -p PID` | Ficha de un proceso: `-o` elige columnas (`ppid` = padre), `-p` filtra por PID | Saber quién lanzó un proceso y con qué usuario corre. Con `-o unit` añade la unit. En fish no uses `<PID>`: los `<` `>` son redirección |
| `ps -eo user,cmd \| sort \| uniq -c \| sort -rn` | Cuántos procesos corre cada usuario; `-e` todos | Revisión general de qué hay en marcha |
| `kill -15 PID` / `kill -9 PID` | Enviar `SIGTERM` o `SIGKILL` | Solo acepta PID. Con procesos de otro usuario: `sudo` (si no, `Operation not permitted`) |
| `comando &` / `nohup comando &` | Segundo plano / ignorar `SIGHUP` | No sustituyen a un servicio |
| `jobs` | Trabajos en segundo plano de esta shell | Antes de cerrar una terminal |
| `echo $status` (fish) / `echo $?` (bash) | Código de salida del último comando | Scripts y diagnósticos |

## Servicios

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `systemctl status UNIT` | Estado, PID, cgroup y últimas líneas del log | Primer paso de cualquier diagnóstico. `--no-pager` imprime sin `less`; `-l` no corta líneas. Mira si arriba aparece `changed on disk` |
| `systemctl status PID` | A qué unit pertenece un proceso | Averiguar si algo es un servicio o se lanzó a mano |
| `sudo systemctl start \| stop \| restart UNIT` | Arrancar, parar, reiniciar | `restart` sin `daemon-reload` usa la ficha antigua |
| `sudo systemctl reload UNIT` | Releer la configuración sin parar | Solo si la ficha tiene `ExecReload=` |
| `sudo systemctl enable --now UNIT` | Habilitar y arrancar | Una unit `static` no se puede habilitar. En timers, se habilita el `.timer` |
| `sudo systemctl disable --now UNIT` | Deshabilitar y parar | — |
| `sudo systemctl daemon-reload` | Releer todas las fichas | Siempre tras editar una ficha a mano |
| `sudo systemctl reset-failed UNIT` | Borrar el estado `failed` y los contadores | Tras `Start request repeated too quickly` |
| `systemctl cat UNIT` | Ficha y drop-ins, con sus rutas | Para entender una unit; mejor que `cat` de la ruta. Enseña lo que hay en disco |
| `systemctl show -p Prop1,Prop2 UNIT` | Valor que systemd usa de verdad | Confirmar que un cambio se aplicó. Ej.: `NRestarts`, `RestartUSec`, `After`, `Requires`, `StartLimitBurst` |
| `systemctl list-dependencies UNIT` | Árbol de lo que necesita | `--reverse`: quién depende de ella; antes de parar algo |
| `systemctl --failed` | Todas las units en `failed` | Revisión general de salud |
| `systemctl list-units --type=TIPO --state=ESTADO` | Units cargadas en memoria y su estado. `--type` filtra por tipo (`service`, `timer`, `socket`); `--state` por estado (`running`, `failed`, `inactive`) | Inventario del VPS: `--type=service --state=running` dice qué servicios corren ahora. Solo enseña las cargadas: `--all` añade las inactivas. No indica si arranca con el sistema (`enable`) |
| `systemctl get-default` | Target que alcanza el arranque | Para elegir `WantedBy=` |

## Unit files

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `systemd-analyze verify FICHERO` | Revisar una ficha sin arrancarla | Siempre antes de arrancar. Detecta los errores que no hacen fallar el servicio |
| `sudo systemctl edit UNIT` | Crear un drop-in; hace `daemon-reload` al guardar | Escribir entre los dos comentarios y con cabecera de sección. Para usar vim: `sudo SYSTEMD_EDITOR=vim systemctl edit UNIT` |
| `sudo systemctl revert UNIT` | Borrar todos los drop-ins | Deshacer ajustes |
| `which PROGRAMA` | Ruta completa de un programa | Para `ExecStart=` |
| `sudo useradd --system --no-create-home --shell /usr/sbin/nologin NOMBRE` | Usuario de servicio | Cada servicio propio. Crea también el grupo |
| `grep -n TEXTO FICHERO` | Buscar en un fichero, con número de línea | Ver qué variables de entorno lee un programa. Sin fichero, se queda esperando: `Ctrl-C` |
| `man systemd.directives` | Índice de directivas y su página | Cuando no sabes dónde está documentada una directiva |

## Journal

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `journalctl -u UNIT` | Log de una unit | Sin `-u`, el nombre se interpreta como filtro: `Failed to add match` |
| `-n N` | Las N líneas más recientes | Sin comas (`-n 5`). Pueden ser todas ruido: filtra por fecha o con `grep` |
| `-b` / `-b -1` | Arranque actual / anterior | `-b -2` es el de antes del anterior |
| `-S '...'` / `-U '...'` | Desde / hasta: `'15 min ago'`, `today`, `'2026-09-11 20:30'` | Reconstruir un incidente pasado |
| `-p PRIORIDAD` | Esa prioridad o más grave | No ve los errores impresos por las aplicaciones |
| `-f` | En vivo | Mientras provocas un fallo en otra terminal. Salir con `Ctrl-C` |
| `-t IDENTIFICADOR` | Por quién escribe (`sudo`, `CRON`) | Para programas que no son servicios |
| `-o verbose` | Todos los campos de cada mensaje | Descubrir por qué campo filtrar (`_UID`, `_COMM`, `_PID`) |
| `CAMPO=valor` | Filtrar por un campo | `_COMM=curl`, `_UID=999` |
| `-x` / `-e` | Explicaciones del catálogo / saltar al final | `-xeu UNIT` con mensajes que no entiendes |
| `--list-boots` / `--disk-usage` | Arranques guardados / espacio ocupado | Saber hasta dónde llega el registro |
| `sudo usermod -aG systemd-journal USUARIO` | Leer el journal sin `sudo` | Sin `-a` se pierden los demás grupos, incluido `sudo`. Hay que volver a iniciar sesión |

## Red

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo ss -tlnp` | Puertos TCP escuchando y su proceso: `-t` TCP, `-l` escuchando, `-n` números, `-p` proceso | Puerto ocupado; revisar qué está abierto a internet (`0.0.0.0`, `[::]`) y qué solo en local (`127.0.0.1`, `[::1]`). `users:` son procesos, no usuarios |
| `sudo ss -tlnp 'sport = :PUERTO'` | Solo ese puerto | Las comillas son necesarias |
| `curl URL` | Petición HTTP | `(7)`: nadie escucha; `(52)`: el servidor murió sin responder |
| `curl -fsS --max-time 5 URL` | Petición para scripts: `-f` error con respuestas HTTP de error, `-s` silencio, `-S` pero con errores | Healthchecks |

## Timers y cron

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `systemctl list-timers` | Timers con próxima y última ejecución | Comprobar tareas programadas (backups, healthchecks) |
| `systemd-analyze calendar 'EXPR'` | Traducir una expresión de `OnCalendar=` | Antes de escribir un timer |
| `crontab -e` / `crontab -l` | Editar / listar la tabla de cron del usuario | `crontab -r` borra la tabla entera sin confirmar |

## Permisos y ficheros

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo chmod 644 FICHERO` | `rw-r--r--`: el dueño escribe, los demás leen | Código de un servicio. `666` deja escribir a todos |
| `sudo mkdir -p RUTA` | Crear carpetas, incluidas las intermedias | No da error si existen |
| `sudo mv ORIGEN DESTINO` | Mover o renombrar | Para retirar una ficha sin borrarla |

## SSH y sistema

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo sshd -t` | Validar la configuración de SSH | Siempre antes de aplicar un cambio |
| `systemctl cat ssh.service ssh.socket` | Ver cómo está montado SSH | Antes de cambiar el puerto o endurecer SSH |
| `sudo reboot` | Reiniciar | Es un enlace a `systemctl`; sin `sudo`, `Interactive authentication required` |
| `infocmp -x xterm-ghostty \| sudo tic -x -` | Instalar la descripción de la terminal para todo el sistema | Si `sudo less` o `sudo vim` avisan de que la terminal no funciona bien |
