# Linux/VPS · Bloque 1 — El sistema por dentro

Terminal, ficheros y sistemas de ficheros, permisos, usuarios y privilegios, procesos y señales, y cómo arranca un Linux moderno.

**Entorno de referencia:** VPS `backend-lab` (Ubuntu 24.04, systemd) y portátil (CachyOS, derivada de Arch, con Btrfs). La shell de ambos es **fish**. Los nombres de ficheros, rutas y valores de este documento existen en esas versiones; con otra distribución, confírmalos en su documentación.

---

# Parte 1 · Teoría

## 1. La terminal: edición de línea y Vim

### Atajos de la línea de comandos

Funcionan en la shell y en la mayoría de programas Unix. Sirven para no depender de las flechas.

| Atajo | Acción |
|---|---|
| `Ctrl-A` / `Ctrl-E` | Cursor al principio / al final de la línea |
| `Ctrl-B` / `Ctrl-F` | Cursor una letra a la izquierda / a la derecha |
| `Ctrl-P` / `Ctrl-N` | Comando anterior / siguiente del historial |
| `Ctrl-W` | Borrar la palabra anterior al cursor |
| `Ctrl-U` / `Ctrl-K` | Borrar hasta el principio / hasta el final de la línea |
| `Ctrl-Y` | Pegar lo último borrado |

### Vim

Dentro de una sesión SSH no hay entorno gráfico: el editor tiene que funcionar en la terminal. Vim está instalado en casi cualquier servidor; `nano` no siempre.

Vim tiene **dos modos**, y casi toda la confusión inicial viene de no saber en cuál estás:

| Modo | Qué hacen las teclas | Cómo se entra |
|---|---|---|
| Normal | Son comandos (moverse, borrar, guardar) | Al abrir Vim, y con `Esc` desde cualquier otro modo |
| Inserción | Escriben texto | `i` (insertar en el cursor), `o` (abre línea nueva debajo y entra) |

| Comando (en modo normal) | Qué hace |
|---|---|
| `:wq` | Guardar y salir |
| `:q` | Salir; falla si hay cambios sin guardar |
| `:q!` | Salir descartando los cambios |
| `G` | Ir a la última línea |

## 2. Leer ficheros: `cat`, `less`, `grep`

Los tres «leen» ficheros, pero resuelven problemas distintos.

| Herramienta | Qué hace | Cuándo |
|---|---|---|
| `cat` | Vuelca el fichero entero | Ficheros pequeños, o para pasarlo a otro comando por tubería |
| `less` | Muestra el fichero por páginas, sin cargarlo entero en memoria | Ficheros largos que quieres recorrer. `Espacio` avanza, `b` retrocede, `/TEXTO` busca, `n` siguiente coincidencia, `q` sale |
| `grep` | **Filtra**: solo muestra las líneas que contienen un patrón | Sabes qué buscas y no quieres leer el resto |

`grep` no necesita `cat` delante: `grep "error" fichero` basta. `cat FICHERO \| grep` solo tiene sentido cuando la entrada viene de otro comando (`ps aux \| grep ssh`).

## 3. Redirección y tuberías

Todo proceso tiene **dos canales de salida independientes**, aunque ambos acaben en tu pantalla:

| Canal | Número | Qué lleva |
|---|---|---|
| `stdout` | 1 | La salida normal |
| `stderr` | 2 | Errores y diagnósticos |

| Operador | Qué hace |
|---|---|
| `> FICHERO` | Manda **solo stdout** al fichero (lo sobrescribe). stderr sigue yendo a la pantalla |
| `2> FICHERO` | Manda **solo stderr** al fichero |
| `> FICHERO 2>&1` | stderr va al mismo sitio al que apunta stdout **en ese momento**; ambos acaban en el fichero |
| `\|` | Tubería: la stdout de un comando es la entrada del siguiente |
| `&` (al final) | Lanza el comando en segundo plano y devuelve la terminal |

- **El orden importa.** `2>&1 > FICHERO` no hace lo mismo que `> FICHERO 2>&1`: en el primer caso stderr se apunta a la pantalla (donde stdout estaba todavía) y luego stdout cambia al fichero. Escribe siempre `> FICHERO 2>&1`.
- El `&` de `2>&1` significa «el destino del canal», no «el fichero llamado 1». Sin él, `2>1` crearía un fichero llamado `1`.
- **`/dev/null`** es un fichero especial que destruye lo que recibe. No es ocultar la salida: el contenido deja de existir. Se usa cuando un comando es muy verboso y solo te importa si falla; con `> /dev/null`, los errores (stderr) siguen apareciendo.
- **El globbing lo hace la shell, no el comando.** Antes de ejecutar `rm -rf ./*`, la shell sustituye `./*` por los nombres de lo que hay dentro. `rm` recibe una lista de ficheros sueltos, no el asterisco. `echo ./*` enseña exactamente lo que recibiría. El `*` no incluye los ficheros ocultos (los que empiezan por `.`).

## 4. Jerarquía de ficheros

Todo cuelga de una única raíz, `/`. Cada directorio principal tiene un uso fijo:

| Ruta | Contenido |
|---|---|
| `/etc` | Configuración del sistema |
| `/var` | Datos que cambian: logs (`/var/log`), bases de datos, cachés |
| `/home` | Directorios personales de los usuarios |
| `/root` | Directorio personal de root |
| `/usr` | Programas y librerías |
| `/boot` | Kernel, `initramfs` y, en máquinas UEFI, el bootloader |
| `/dev` | Dispositivos, representados como ficheros (`/dev/nvme0n1`, `/dev/vda`) |
| `/proc`, `/sys` | Información del kernel y del hardware, generada al leerla (no hay datos en disco) |
| `/tmp`, `/run` | Temporales y estado en ejecución; normalmente en RAM, desaparecen al reiniciar |

**En Linux todo se representa como fichero**: dispositivos, procesos (`/proc/PID/`), información del kernel. Por eso las mismas herramientas (`cat`, `grep`, `ls`) sirven para todo.

## 5. Discos, particiones y sistemas de ficheros

Son **tres capas distintas**:

| Capa | Qué es | Ejemplo |
|---|---|---|
| Disco | El dispositivo (físico, o virtual en un VPS) | `/dev/nvme1n1` en el portátil; `/dev/vda` en el VPS |
| Partición | Una división lógica del disco, descrita en la tabla de particiones (hoy, normalmente GPT) | `/dev/nvme1n1p2` |
| Sistema de ficheros | La estructura que organiza ficheros y directorios dentro de una partición | `btrfs`, `ext4` |

**Montar** es enganchar un sistema de ficheros a un directorio del árbol (el **punto de montaje**). Hasta que no se monta, existe pero no se puede navegar. Un mismo sistema de ficheros puede estar montado en varios sitios.

| Tipo | Qué es |
|---|---|
| `ext4` | El sistema de ficheros clásico de Linux, con *journaling* (se recupera tras un corte de luz). El del VPS |
| `btrfs` | Moderno: compresión transparente, *snapshots* y **subvolúmenes**. El del portátil |
| `ntfs` | El de Windows |
| `fat32` / `vfat` | Sencillo y legible por cualquier firmware. Lo usan la **ESP** y `/boot` |
| `tmpfs` | Vive en RAM; muy rápido; desaparece al reiniciar (`/tmp`, `/run`) |
| `proc`, `sysfs` | Virtuales: el kernel genera su contenido al leerlos |
| `overlay` | Lo usa Docker: capas de solo lectura (`lowerdir`) bajo una única capa de escritura (`upperdir`); varios contenedores comparten las capas base |
| `linux-swap` | Espacio de intercambio. `zram` crea un dispositivo en RAM, comprimido, y lo usa como swap (más rápido que uno en disco) |

**Subvolúmenes de Btrfs.** Una misma partición puede aparecer montada varias veces (`/`, `/home`, `/var/log`…), cada una con su `subvolid` y su `subvol=/@nombre`. Son divisiones lógicas de la misma partición que se pueden recuperar (*rollback*) por separado: se puede volver `/` a una versión anterior sin tocar `/home`.

**Opciones de montaje** (la parte entre paréntesis de la salida de `mount`):

| Opción | Significado |
|---|---|
| `rw` | Lectura y escritura |
| `noatime` | No escribe la fecha de último acceso en cada lectura (menos escrituras) |
| `compress=zstd:1` | Compresión transparente de los datos (Btrfs) |
| `ssd`, `discard=async` | Ajustes para discos de estado sólido |
| `nosuid`, `noexec`, `nodev` | No permite setuid, ejecutar programas ni dispositivos en ese montaje |

**ESP** (*EFI System Partition*): partición `fat32` con las banderas `boot, esp`, donde el firmware UEFI busca el bootloader.

## 6. Permisos de ficheros

`ls -l` muestra, para cada fichero:

```
-rw-r-----  1  miguel  miguel  ...  fichero
│└┬┘└┬┘└┬┘     └─ dueño └─ grupo
│ │  │  └─ resto
│ │  └─ grupo
│ └─ dueño
└─ tipo
```

- **Tipo** (primer carácter): `-` fichero, `d` directorio, `l` enlace simbólico.
- **Tres tríos**: dueño, grupo, resto. Se aplica **el primero que corresponde**: si eres el dueño, cuenta el trío del dueño aunque el del grupo diera más.

| Permiso | En un fichero | En un directorio |
|---|---|---|
| `r` | Leerlo | Listar su contenido |
| `w` | Modificarlo | Crear, renombrar y borrar ficheros dentro |
| `x` | Ejecutarlo | Entrar en él (`cd`) y acceder a lo de dentro |

### Notación octal

Cada trío es un número: `r`=4, `w`=2, `x`=1, sumados.

| Dígito | Permisos | | Modo | Permisos | Uso típico |
|---|---|---|---|---|---|
| 0 | `---` | | `644` | `rw-r--r--` | Fichero normal |
| 1 | `--x` | | `755` | `rwxr-xr-x` | Programa o directorio |
| 2 | `-w-` | | `600` | `rw-------` | Solo el dueño (claves privadas) |
| 4 | `r--` | | `640` | `rw-r-----` | Dueño escribe, grupo lee |
| 5 | `r-x` | | `750` | `rwxr-x---` | Directorio del grupo |
| 6 | `rw-` | | `700` | `rwx------` | Directorio privado |
| 7 | `rwx` | | | | |

### Notación simbólica

`chmod QUIÉN OPERACIÓN PERMISO`:

| Quién | Operación | Permiso |
|---|---|---|
| `u` dueño, `g` grupo, `o` resto, `a` todos | `+` añade, `-` quita, `=` fija exactamente | `r`, `w`, `x` |

`chmod go+r f` añade lectura a grupo y resto; `chmod u=rw,g=r,o= f` fija `rw-r-----` borrando lo que hubiera antes.

### `umask`

Resta permisos a lo que se **crea a partir de ese momento**; no toca lo que ya existe. Los máximos de partida son 666 para ficheros (no nacen ejecutables) y 777 para directorios.

| `umask` | Ficheros nuevos | Directorios nuevos |
|---|---|---|
| `022` | `644` | `755` |
| `077` | `600` | `700` |

### `chown` frente a `chmod`

`chown` cambia **de quién es** el fichero (dueño y grupo); `chmod` cambia **qué se puede hacer** con él. Cambiar el dueño requiere root.

### Permisos especiales

Resuelven el caso de un programa que necesita más permisos de los que tiene quien lo ejecuta.

| Bit | Octal | Se ve en `ls -l` como | Efecto |
|---|---|---|---|
| `setuid` | 4 | `s` donde iría la `x` del dueño | El proceso corre con los permisos del **dueño del fichero**, no de quien lo lanza. `passwd` lo usa para escribir en `/etc/shadow` |
| `setgid` | 2 | `s` donde iría la `x` del grupo | En un fichero, igual con el grupo. En un **directorio**, lo creado dentro hereda el grupo del directorio |
| sticky | 1 | `t` donde iría la `x` del resto | En un directorio compartido, solo el dueño de un fichero (o root) puede borrarlo. `/tmp` es `drwxrwxrwt` |

Se escriben como un cuarto dígito delante: `chmod 4755`, `chmod 2755`, `chmod 1777`.

## 7. Usuarios y grupos

| UID | Tipo de cuenta |
|---|---|
| 0 | `root`, el superusuario |
| 1–999 | Cuentas de **sistema** y de servicio (`bin`, `daemon`, `postgres`…) |
| 1000 en adelante | Usuarios normales (el primero, `miguel`, tiene el 1000) |

### `/etc/passwd`

Legible por cualquiera. Una línea por cuenta, siete campos separados por `:`:

```
usuario : x : UID : GID : comentario : directorio_home : shell
```

| Campo | Significado |
|---|---|
| `x` | La contraseña no está aquí, sino en `/etc/shadow` |
| `GID` | Grupo **primario** |
| `shell` | Programa que se lanza al iniciar sesión. `/usr/bin/nologin` = cuenta que no permite sesión interactiva |

### `/etc/shadow`

Solo legible por root. Contiene las contraseñas cifradas:

```
usuario : hash : último_cambio : mín : máx : aviso : inactividad : expiración : reservado
```

| Valor del campo `hash` | Significado |
|---|---|
| `$6$…` | Hash real, algoritmo sha512crypt |
| `$y$…` | Hash real, algoritmo yescrypt (más moderno) |
| `!` o `*` (o `!*`) | No hay contraseña utilizable: no se puede entrar con contraseña |

`último_cambio` son **días desde el 1 de enero de 1970**.

Las cuentas de servicio combinan los dos cerrojos: shell `nologin` y sin contraseña. Cada demonio corre con su propia cuenta limitada para que, si lo comprometen, el atacante herede solo esos permisos y no los de root.

### Grupos

Cada usuario tiene un **grupo primario** (campo GID de `/etc/passwd`, normalmente con su mismo nombre) y puede estar en varios **suplementarios** (`/etc/group`). Sirven para dar permisos a un conjunto de usuarios sin repetir la regla persona a persona.

| Grupo | Para qué |
|---|---|
| `sudo` (Ubuntu) / `wheel` (Arch) | Derecho a usar `sudo` |
| `docker` | Usar Docker sin `sudo` |
| `video`, `audio`, `kvm`, `storage` | Acceso a dispositivos concretos |
| `adm`, `systemd-journal` | Leer los logs del sistema sin `sudo` |

## 8. Elevación de privilegios: `su`, `sudo` y `sudoers`

| | `su` | `sudo` |
|---|---|---|
| Qué hace | Abre una sesión **completa** como otro usuario (root por defecto) | Ejecuta **un comando** con privilegios y vuelve a tu usuario |
| Contraseña que pide | La del usuario de destino | La tuya |
| Duración | Hasta `exit` | Un comando; la autenticación se **cachea** (por terminal) unos minutos |
| Registro | No distingue quién eras | Anota usuario, terminal y comando |
| Requisito | Conocer la contraseña de destino | Estar en el grupo `sudo`/`wheel` |

- **`sudo su`**: `sudo` (con tu contraseña) ejecuta `su`; como ya es root, `su` no pide contraseña de destino. Es la forma de abrir una sesión de root cuando la cuenta root no tiene contraseña utilizable.
- **El prompt avisa:** `$` usuario normal, `#` root (en psql, `=>` frente a `=#`). Si ves `#` y no recuerdas cómo llegaste, estás en una sesión de root.
- En una sesión de root **ningún comando pide confirmación**: es el riesgo de `su` frente a `sudo`.

### `/etc/sudoers`

Se edita **siempre con `visudo`**, que valida la sintaxis antes de guardar; un error escrito a mano puede dejar sin `sudo` al sistema. Anatomía de una línea:

```
root    ALL=(ALL)   ALL
│       │    │      └─ qué comandos
│       │    └─ como qué usuarios puede ejecutarlos
│       └─ en qué máquinas
└─ quién
```

| Directiva | Efecto |
|---|---|
| `NOPASSWD:` delante de los comandos | No pide contraseña |
| `Defaults timestamp_timeout=N` | Minutos que dura la autenticación en caché (por defecto, 15) |

`NOPASSWD: ALL` quita la última comprobación de que quien actúa eres tú: cualquier proceso que corra con tu usuario podría hacerse root sin barrera. En una máquina con IP pública es lo que hay que evitar. Alargar `timestamp_timeout` mantiene la barrera y reduce las veces que se pide.

## 9. Procesos

**Proceso.** Un programa en ejecución, con un número único, el **PID**. Todo proceso nace de otro, su **padre** (**PPID**). El **PID 1** es el primero que lanza el kernel.

**Zombie.** Proceso que ya terminó pero cuyo padre no ha recogido su estado de salida; sigue en la tabla de procesos, sin consumir recursos. Muchos zombies indican un padre defectuoso.

**Hilos del kernel.** Los procesos `[kworker/…]`, `kthreadd`, `ksoftirqd`… no son programas instalados: son trabajo interno del kernel. Se reconocen porque `VIRT`, `RES` y `SHR` valen 0. En un diagnóstico se ignoran.

**Cadena de procesos de una conexión SSH.** `sshd` principal (root, escucha el puerto; nunca atiende conexiones directamente) → un hijo de root que verifica quién eres (`sshd: usuario [priv]`) → un hijo ya con tu usuario que gestiona la sesión (`sshd: usuario@pts/0`) → tu shell. Es el patrón de «usar privilegios solo el tiempo necesario». El proceso principal sigue escuchando para la siguiente conexión.

### Estado de un proceso (columna `S` en `top`, `STAT` en `ps`)

| Estado | Significado |
|---|---|
| `R` | Ejecutándose o listo para ejecutarse |
| `S` | Dormido, esperando algo (la mayoría de procesos, y es normal) |
| `D` | Dormido esperando disco o red, sin poder interrumpirse |
| `I` | Hilo del kernel inactivo |
| `Z` | Zombie |
| Sufijos de `ps` | `s` líder de sesión · `+` en primer plano de su terminal · `l` con varios hilos |

### Señales

Avisos cortos que el kernel entrega a un proceso.

| Señal | Número | Efecto |
|---|---|---|
| `SIGTERM` | 15 | Pide que termine. El proceso puede capturarla y limpiar antes (guardar datos, cerrar conexiones) |
| `SIGKILL` | 9 | El kernel lo mata sin aviso. No se puede capturar ni ignorar |

**Primero `-15`; `-9` solo si el proceso sigue vivo pasados unos segundos.** Matar con `-9` una base de datos a mitad de escritura puede corromper datos.

### Lectura de `ps aux`

| Columna | Significado |
|---|---|
| `USER` | Con qué usuario corre |
| `PID` | Identificador |
| `%CPU`, `%MEM` | Uso de CPU y de memoria |
| `VSZ` | Memoria virtual reservada (inflada; poco útil) |
| `RSS` | Memoria física realmente en uso. La que importa |
| `TTY` | Terminal asociada; `?` = ninguna (servicio de fondo); `pts/N` = sesión remota |
| `STAT` | Estado |
| `START`, `TIME` | Cuándo arrancó · CPU **acumulada** (no tiempo transcurrido) |
| `COMMAND` | El programa |

Para una primera lectura basta con **`COMMAND`, `USER` y `PID`**. El resto se consulta cuando hay una pregunta concreta.

### Lectura de `top`

Cabecera:

| Línea | Qué mirar |
|---|---|
| `up ... load average: A, B, C` | Tiempo encendido; carga media en 1, 5 y 15 minutos. **Compárala con el número de núcleos**: con 2 núcleos, 2.00 es ocupación completa; por encima, hay procesos esperando CPU |
| `Tasks: ... zombie` | Procesos totales y por estado. `0 zombie` es lo sano |
| `%Cpu(s)` | `us` programas, `sy` kernel, `id` ocioso, **`wa` esperando al disco** (si sube, el cuello de botella es el disco, no la CPU) |
| `MiB Mem` | `used` en uso, `buff/cache` caché de disco, **`avail Mem`** memoria realmente disponible |
| `MiB Swap` | Intercambio en uso |

`buff/cache` no es memoria ocupada de forma preocupante: el kernel la libera al instante si un proceso la necesita. El dato realista es `avail Mem`.

Columnas de la tabla:

| Columna | Significado |
|---|---|
| `PR`, `NI` | Prioridad real y valor *nice* (−20 a 19; **más bajo = más prioridad**; `PR` = `NI` + 20 en procesos normales) |
| `VIRT`, `RES`, `SHR` | Memoria virtual · física en uso · parte de la física compartida con otros procesos |
| `S` | Estado |
| `TIME+` | CPU acumulada |

## 10. Cómo arranca un Linux moderno

| Fase | Quién | Qué hace |
|---|---|---|
| 1. Firmware | UEFI (antes, BIOS) | Comprueba el hardware y busca el bootloader en la ESP |
| 2. Bootloader | GRUB, systemd-boot… | Muestra el menú si hay varias opciones y **carga en RAM el kernel y el `initramfs`**; cede el control al kernel |
| 3. Kernel | Linux | Toma el control del hardware real |
| 4. `initramfs` | El kernel | Monta el disco real usando los drivers mínimos que trae este sistema de ficheros temporal |
| 5. Espacio de usuario | El kernel lanza **systemd como PID 1** | systemd arranca el resto |
| 6. Targets y units | systemd | Arranca los servicios agrupados por fases hasta el target por defecto |

**Bootloader.** Su único trabajo es cargar y entregar el control. No instala ni actualiza kernels: eso lo hace el gestor de paquetes, que además regenera la lista de opciones del menú. Si una opción es otro sistema operativo (Windows), el bootloader hace **chainload**: le cede el control al bootloader de ese sistema, que arranca su propio kernel.

**`initramfs`.** Resuelve un problema de huevo y gallina: el kernel necesita drivers para leer el disco real, pero esos drivers viven normalmente dentro de la partición que aún no puede montar. Se guarda como **fichero en `/boot`** y se vuelve a cargar en RAM **en cada arranque**; no persiste entre arranques, se descarta cuando el disco real está montado. Los gestores de paquetes lo regeneran al actualizar el kernel.

**Son dos pasos distintos del kernel, uno detrás de otro:** primero usa el `initramfs` para montar el disco real; después, y sin relación causal con aquel, lanza systemd.

**Targets.** Un **target** no ejecuta nada: es un punto de sincronización que agrupa units. Cada uno depende de que otros se hayan alcanzado antes.

| Target | Qué significa alcanzarlo |
|---|---|
| `sysinit.target` | Inicialización básica |
| `local-fs.target` | Sistemas de ficheros locales montados |
| `network.target` / `network-online.target` | Red configurada / **con conectividad confirmada** |
| `nss-lookup.target` | Resolución de nombres funcionando |
| `basic.target` | Lo esencial listo: pueden arrancar los servicios normales |
| `multi-user.target` | Sistema completo en modo texto, listo para login. **El normal de un servidor** |
| `graphical.target` | Lo anterior más el entorno gráfico. Innecesario en un servidor sin pantalla |
| `getty.target` | Prompts de login en las terminales |

`graphical.target` depende de `multi-user.target`: lo extiende, no lo sustituye. `systemctl set-default` cambia el target que se persigue al arrancar (crea el enlace `/etc/systemd/system/default.target`); el cambio se aplica en el siguiente arranque.

**SSH no es parte del arranque.** `sshd` es un servicio más: se arranca durante la fase de `multi-user.target` y se queda escuchando el puerto. Conectarse es un evento posterior e independiente, que puede ocurrir mil veces sin que el sistema vuelva a arrancar.

### Medir el arranque

`systemd-analyze` desglosa el tiempo por fase:

| Fase en la salida | Qué mide |
|---|---|
| `firmware` | El UEFI comprobando el hardware físico |
| `loader` | El bootloader, hasta cargar el kernel |
| `kernel` | La inicialización del kernel |
| `initrd` | El `initramfs`, hasta montar el disco real |
| `userspace` | systemd arrancando servicios hasta el target por defecto |

**Una VM no tiene todas las fases.** En un VPS no aparecen `firmware`, `loader` ni `initrd`: el hipervisor entrega al kernel un entorno ya preparado, sin hardware físico que comprobar. Por eso un VPS arranca bastante más rápido que un portátil.

`systemd-analyze blame` lista las units por tiempo de activación. **No mide cuánto retrasó cada una el arranque**: systemd arranca en paralelo, y una unit lenta puede estar terminando de fondo mientras el sistema ya es utilizable. Las unidades `.device` que aparecen en un portátil son esperas a que el kernel registre un dispositivo (TPM, puertos serie, particiones del disco con varias rutas alternativas: `by-id`, `by-partuuid`, `by-path`).

### El journal y los permisos

`journalctl` lee el registro de systemd. **Sin privilegios solo muestra los mensajes de tu propio usuario**, no los del sistema ni los de servicios de otros usuarios; el aviso `You are currently not seeing messages from other users and the system` lo indica. Se resuelve con `sudo` o perteneciendo a los grupos `adm` o `systemd-journal`. `-b` limita a un arranque; `-u UNIT` limita a una unit. Un arranque que lleva días activo acumula todos esos días en `-b`.

---

# Parte 2 · Ejemplos

## Identidad y grupos en el portátil

```
❯ id
uid=1000(miguel) gid=1000(miguel) groups=1000(miguel),3(sys),90(network),955(docker),956(nopasswdlogin),979(rfkill),982(users),983(video),985(storage),989(lp),990(kvm),995(audio),998(wheel)
```

| Parte | Lectura |
|---|---|
| `uid=1000(miguel)` | Primer UID de usuario normal |
| `gid=1000(miguel)` | Grupo primario con el mismo nombre que el usuario (grupo privado) |
| `docker` | Permite usar `docker` sin `sudo` |
| `wheel` | El equivalente en Arch al grupo `sudo` de Ubuntu |
| `video`, `audio`, `kvm`, `storage` | Acceso directo a esos dispositivos sin pasar por root |

## Cuentas: `/etc/passwd` y `/etc/shadow`

Los hashes reales no se copian aquí.

| Cuenta | Shell (`/etc/passwd`) | Campo de contraseña (`/etc/shadow`) | ¿Entrada con contraseña? |
|---|---|---|---|
| `root` (portátil) | `/usr/bin/bash` | `$y$j9T$…` (yescrypt) | Sí |
| `bin`, `daemon` (portátil) | `/usr/bin/nologin` | `!*` | No: ni shell ni contraseña |
| `root` (VPS) | — | `$6$…` (sha512crypt) | Con contraseña solo por la consola de recuperación (VNC): `PermitRootLogin no` lo bloquea por SSH |
| `miguel` (VPS) | — | `$y$j9T$…` | Sí |

Otras cuentas de servicio del portátil: `mail`, `ftp`, `http` (UID 33), `nobody` (65534), `dbus`, `systemd-network`… todas con `nologin`. Cada demonio corre con la suya.

En el VPS, `root` **sí tiene contraseña**: la entregada por el proveedor al crear la máquina. Que no pueda usarse por SSH no significa que no exista.

## `sudoers`: alargar la caché de contraseña

Línea añadida al final de `/etc/sudoers` (con `visudo`) en el portátil:

```
Defaults timestamp_timeout=60
```

Primer intento, sin editor definido:

```
❯ sudo visudo
visudo: no editor found (editor path = /usr/bin/vi)
```

`/usr/bin/vi` no existe en esa instalación (hay `vim`, pero no el enlace `vi`). Se soluciona indicando el editor solo para esa ejecución:

```
sudo EDITOR=vim visudo
```

Dentro de Vim: `G` (última línea), `o` (línea nueva e inserción), escribir la línea, `Esc`, `:wq`. Si `visudo` detecta un error de sintaxis pregunta `What now?`: `e` vuelve a editar, `x` sale sin guardar.

Verificación:

```
sudo -k          # invalida la caché
sudo whoami      # pide contraseña, responde root
sudo ls /root    # ya no la pide durante los 60 minutos siguientes, en esa terminal
```

## Discos del portátil

`sudo parted -l`:

| Disco | Partición | Sistema de ficheros | Para qué |
|---|---|---|---|
| `/dev/nvme0n1` (Windows) | 1 · 16,8 MB | — | Reservada de Windows (`msftres`) |
| | 2 · 999 GB | `ntfs` | Datos de Windows |
| | 3 · 900 MB | `ntfs` | Recuperación (`hidden`, `diag`) |
| `/dev/nvme1n1` (Linux) | 1 · 2,1 GB | `fat32`, banderas `boot, esp` | La ESP |
| | 2 · 998 GB | `btrfs` | Todo el sistema Linux |
| `/dev/zram0` | 1 · 32,6 GB | `linux-swap` | Swap en RAM comprimida; tabla de particiones `loop` (no es un disco real) |

Los dos discos con tabla `gpt` confirman el arranque dual: cada sistema tiene su disco y su bootloader.

`mount` sobre esa máquina, resumido:

```
/dev/nvme1n1p2 on /         type btrfs (rw,noatime,compress=zstd:1,ssd,discard=async,subvolid=256,subvol=/@)
/dev/nvme1n1p2 on /home     type btrfs (rw,noatime,compress=zstd:1,ssd,discard=async,subvolid=257,subvol=/@home)
/dev/nvme1n1p2 on /var/log  type btrfs (rw,noatime,compress=zstd:1,ssd,discard=async,subvolid=262,subvol=/@log)
/dev/nvme1n1p1 on /boot     type vfat  (rw,relatime,fmask=0077,dmask=0077,...)
tmpfs          on /tmp      type tmpfs (rw,noatime,...)
proc           on /proc     type proc  (rw,nosuid,nodev,noexec,relatime)
overlay        on /var/lib/docker/rootfs/overlayfs/... type overlay (rw,relatime,lowerdir=...,upperdir=...,workdir=...)
```

| Línea | Lectura |
|---|---|
| `nvme1n1p2` repetida | Una sola partición física, montada varias veces: subvolúmenes `@`, `@home`, `@log`… |
| `nvme1n1p1` en `/boot` | La ESP, en `vfat` (`fat32`) |
| `tmpfs`, `proc` | Virtuales; no ocupan disco |
| `overlay` | Un contenedor Docker en marcha, con sus capas |

La salida completa es larga porque hay un `overlay` por contenedor y un `nsfs` por cada red aislada de Docker.

## Salud del VPS en `top`

```
top - 17:09:11 up 12 days, 12:09,  1 user,  load average: 0.00, 0.00, 0.00
Tasks: 118 total,   1 running, 117 sleeping,   0 stopped,   0 zombie
%Cpu(s):  0.0 us,  0.2 sy,  0.0 ni, 99.8 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :   3910.4 total,   1931.0 free,    563.3 used,   1752.5 buff/cache
MiB Swap:      0.0 total,      0.0 free,      0.0 used.   3347.1 avail Mem
```

| Dato | Lectura |
|---|---|
| `up 12 days` | Lleva 12 días sin reiniciar |
| `load average: 0.00` | El VPS tiene 2 núcleos; carga nula, sin cola de espera |
| `1 running, 117 sleeping, 0 zombie` | El único proceso activo es el propio `top`; no hay zombies |
| `99.8 id`, `0.0 wa` | CPU ociosa, sin esperas de disco |
| `3910.4 total` | Los 4 GB del plan |
| `buff/cache 1752.5` | Caché de disco, liberable; el dato real es `avail Mem` 3347.1 |
| `Swap 0.0` | No hay swap en el VPS |

Dos filas de la tabla de procesos:

```
 PID USER  PR  NI    VIRT   RES   SHR S  %CPU %MEM    TIME+ COMMAND
   1 root  20   0   22528 13812  9560 S   0.0  0.3  0:26.18 systemd
   4 root   0 -20       0     0     0 I   0.0  0.0  0:00.00 kworker/R-rcu_g
```

La primera es un proceso normal: PID 1, prioridad 20 (nice 0), dormido, con memoria real asignada, y 26 s de CPU acumulada en 12 días. La segunda es un hilo del kernel: nice −20 (máxima prioridad), memoria 0, estado `I`.

## La cadena SSH en `ps aux`

```
miguel@backend-lab ~> ps aux | grep -E "USER|ssh"
USER   PID   %CPU %MEM  VSZ    RSS    TTY    STAT START  TIME COMMAND
root   800   0.0  0.2   12024  8300   ?      Ss   Sep12  0:22 sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups
root   117406 0.0 0.2   14740  10616  ?      Ss   17:07   0:00 sshd: miguel [priv]
miguel 117523 0.0 0.1   14996  7260   ?      S    17:07   0:00 sshd: miguel@pts/0
miguel 117655 0.0 0.0   6904   2436   pts/0  S+   17:13   0:00 grep --color=auto ssh
```

| Línea | Lectura |
|---|---|
| 1 | El `sshd` principal, root, sin terminal, líder de sesión, activo desde el 12 de septiembre. Solo escucha |
| 2 | Hijo de root creado para esta conexión: verifica la identidad (`[priv]`) |
| 3 | Ya con el usuario `miguel`: gestiona la sesión |
| 4 | El propio `grep`, que se captura a sí mismo; en `pts/0`, en primer plano (`+`) |

Cada conexión nueva añade su pareja `[priv]` + `usuario@pts/N`; la primera línea sigue ahí.

## Qué cuenta el journal de PostgreSQL en el VPS

`sudo journalctl -b -u postgresql --no-pager`, combinado con la búsqueda de `postgresql` en todo el journal:

```
Sep 13 13:47:19 backend-lab sudo[9792]: miguel : TTY=pts/0 ; PWD=/home/miguel ; USER=root ; COMMAND=/usr/bin/apt install postgresql
Sep 13 13:47:27 backend-lab useradd[11256]: new user: name=postgres, UID=105, GID=110, home=/var/lib/postgresql, shell=/bin/bash, from=none
Sep 13 13:47:28 backend-lab systemd[1]: Starting postgresql.service - PostgreSQL RDBMS...
Sep 13 13:47:28 backend-lab systemd[1]: Finished postgresql.service - PostgreSQL RDBMS.
Sep 13 13:47:30 backend-lab systemd[1]: Starting postgresql@16-main.service - PostgreSQL Cluster 16-main...
Sep 13 13:47:32 backend-lab systemd[1]: Started postgresql@16-main.service - PostgreSQL Cluster 16-main.
Sep 22 06:27:20 backend-lab systemd[1]: Stopping postgresql@16-main.service - PostgreSQL Cluster 16-main...
Sep 22 06:27:20 backend-lab systemd[1]: postgresql@16-main.service: Deactivated successfully.
Sep 22 06:27:20 backend-lab systemd[1]: postgresql@16-main.service: Consumed 1min 28.980s CPU time, 27.3M memory peak, 0B memory swap peak.
Sep 22 06:27:22 backend-lab systemd[1]: Started postgresql@16-main.service - PostgreSQL Cluster 16-main.
```

| Línea | Lectura |
|---|---|
| `sudo[9792]` | `sudo` anota quién instaló el paquete, desde qué terminal y con qué comando |
| `useradd … UID=105` | El paquete crea la cuenta de servicio `postgres` (UID bajo 1000) |
| `postgresql.service` → `Finished` al instante | La unit «paraguas»: no hace trabajo por sí sola |
| `postgresql@16-main.service` | La unit que ejecuta el clúster. `@16-main` es la instancia de una plantilla |
| `Stopping` + `Deactivated successfully` + `Started` | Una parada y un arranque **limpios**, dos segundos de diferencia: no es un fallo (un fallo diría `Failed`) |
| `Consumed 1min 28.980s CPU time, 27.3M memory peak` | Resumen del consumo de esa vida del servicio, del 13 al 22 de septiembre |

## Arranque: VPS frente a portátil

`systemd-analyze` en los dos:

| Fase | VPS | Portátil |
|---|---|---|
| firmware | — | 12,621 s |
| loader | — | 1,583 s |
| kernel | 1,952 s | 1,638 s |
| initrd | — | 2,676 s |
| userspace | 4,902 s | 5,346 s |
| **Total** | **6,854 s** | **23,866 s** |

En el portátil, la mayor parte la consume el firmware comprobando hardware físico. `blame` en el portátil lista sobre todo `.device`: `tpm0`, `ttyS0`–`ttyS3` y el disco con sus rutas `by-id`, `by-partuuid`, `by-path`, `by-diskseq`.

`systemd-analyze blame` en el VPS (primeras líneas):

```
35.447s apt-daily-upgrade.service
 2.201s postgresql@16-main.service
 1.638s systemd-networkd-wait-online.service
 1.243s dev-vda3.device
 1.092s apparmor.service
 1.004s snapd.seeded.service
  912ms snapd.service
  614ms systemd-networkd.service
```

| Línea | Lectura |
|---|---|
| `apt-daily-upgrade.service`, 35 s | Más que el arranque entero (6,8 s): corre de fondo, en paralelo; no retrasa el login |
| `postgresql@16-main` | El clúster de la base de datos |
| `systemd-networkd-wait-online` | Espera a que la red tenga conectividad (`network-online.target`) |
| `dev-vda3.device` | El disco virtual `vda` del VPS |
| `snapd.*` | Servicios de `snap`, que en un servidor sin aplicaciones de escritorio no se usan |

`systemctl list-units --type=target` en el VPS mostró 25 targets activos, todos `loaded active active`, incluidos `graphical.target` y `snapd.mounts.target`: señal de un sistema sano, pero con un target gráfico que un servidor no necesita.

## Quitar el target gráfico y `snapd` del VPS

```
sudo systemctl set-default multi-user.target
systemctl get-default                         # multi-user.target

snap list                                      # sin paquetes instalados
sudo systemctl stop snapd
sudo systemctl disable snapd
sudo apt purge snapd -y
sudo rm -rf /var/cache/snapd/
rm -rf ~/snap
snap list                                      # fish: Unknown command: snap
```

Tras la purga quedó un resto:

```
systemctl list-units --type=target | grep -i snap
● snapd.mounts-pre.target not-found active active snapd.mounts-pre.target
```

`not-found` con el punto `●`: el fichero de la unit ya no existe, pero systemd la sigue teniendo cargada en memoria. `daemon-reload` **no** la quitó, porque la unit seguía **activa**; hubo que pararla:

```
sudo systemctl stop snapd.mounts-pre.target snapd.mounts.target
# Failed to stop snapd.mounts.target: Unit snapd.mounts.target not loaded.
sudo systemctl daemon-reload
systemctl list-units --type=target | grep -i snap     # sin salida
```

El error del segundo target es correcto: ya no estaba cargado. Tras `sudo reboot`:

```
systemctl get-default
multi-user.target
systemd-analyze
Startup finished in 2.195s (kernel) + 6.335s (userspace) = 8.531s
multi-user.target reached after 6.199s in userspace.
```

La diferencia de tiempo con la medición anterior (6,854 s) está dentro de la variación normal entre arranques de una VM; para comparar con rigor habría que repetir la medición varias veces.

## Fallos típicos y cómo se ven

| Situación | Qué se ve | Causa y salida |
|---|---|---|
| `ls /noexiste > f` | El error sigue en pantalla; `f` queda vacío | `>` solo redirige stdout; el error va por stderr. Usar `2>` o `2>&1` |
| `rm -rf ./` | `rm: refusing to remove '.' or '..' directory: skipping './'` | `rm` protege `.` y `..`. Para vaciar la carpeta sin borrarla: `rm -rf ./*` (sin red de seguridad: comprobar antes con `ls -la ./*`) |
| `sudo visudo` sin editor | `visudo: no editor found (editor path = /usr/bin/vi)` | Indicar el editor: `sudo EDITOR=vim visudo` |
| `journalctl -b` sin `sudo` | `Hint: You are currently not seeing messages from other users and the system` | Solo ves tus mensajes. Usar `sudo` o el grupo `systemd-journal` |
| `ps aux \| grep sleep` | Aparecen dos filas: el proceso y el propio `grep` | El `grep` se captura a sí mismo. El PID a usar es el de la fila cuyo `COMMAND` es el programa real |
| `ps aux \| grep ssh` | Se pierde la fila de cabecera con los nombres de columna | `ps aux \| grep -E "USER\|ssh"` la conserva |
| `purge` de un paquete con units activas | `●` y `not-found` en `list-units` | La unit sigue cargada: `systemctl stop` y después `daemon-reload` |
| Comando cuyo paquete se purgó | `fish: Unknown command: snap` | Confirma que ya no está |
| `chmod` sobre un directorio sin `x` | `Permission denied` al entrar | Un directorio sin `x` no se puede atravesar aunque se pueda listar |
| `sudo` deja de pedir contraseña | No es un fallo | Está en la caché (`timestamp_timeout`); `sudo -k` la invalida |

## Preguntas frecuentes

| Pregunta | Comando |
|---|---|
| ¿Está sano el servidor ahora mismo? | `top` y leer la cabecera: `load average`, `id`, `wa`, `avail Mem`, `zombie` |
| ¿Quién ejecuta este programa y cuál es su PID? | `ps aux \| grep -E "USER\|NOMBRE"` |
| ¿Quién puede leer o escribir este fichero? | `ls -l FICHERO` |
| ¿A qué grupos pertenezco? | `id` |
| ¿Una cuenta puede entrar con contraseña? | `sudo cat /etc/shadow \| grep -E "^root:\|^$(whoami):"` — `!` o `*` = no |
| ¿Qué disco, partición y sistema de ficheros tengo? | `sudo parted -l` |
| ¿Dónde está montado esto y con qué opciones? | `findmnt` o `mount` |
| ¿Cuánto espacio queda en disco? | `df -h` |
| ¿Qué target alcanza el arranque? | `systemctl get-default` |
| ¿Qué servicio es el más lento al arrancar? | `systemd-analyze blame \| head -15` |
| ¿Cuánto tardó el último arranque, y en qué fase? | `systemd-analyze` |
| ¿Qué ha hecho un servicio desde el arranque? | `sudo journalctl -b -u SERVICIO --no-pager` |
| ¿Quién ejecutó un comando con `sudo`? | `sudo journalctl -b \| grep "COMMAND="` |
| ¿Qué recibirá `rm` si uso un asterisco? | `echo ./*` |

---

# Parte 3 · Comandos útiles del bloque

## Leer y buscar en ficheros

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `cat FICHERO` | Volcar un fichero entero | Ficheros pequeños. En uno largo, se te escapa por arriba de la pantalla |
| `less FICHERO` | Recorrer un fichero largo. `Espacio` avanza, `b` retrocede, `/TEXTO` busca, `n` siguiente, `q` sale | Logs y configuraciones largas |
| `grep "PATRÓN" FICHERO` | Mostrar solo las líneas que contienen el patrón. `-i` ignora mayúsculas, `-n` numera líneas, `-v` invierte (las que **no** coinciden), `-r` recursivo en un directorio, `-E` permite `\|` como «o» | Sin fichero, lee la entrada estándar y se queda esperando: `Ctrl-C`. `grep -E "USER\|ssh"` conserva la cabecera de `ps` |
| `head -N` | Las primeras N líneas de la entrada | Limitar salidas largas: `systemd-analyze blame \| head -15`. Sin número, son 10 |
| `column -t` | Alinear en columnas la entrada | `mount \| column -t` |
| `vim FICHERO` | Editar. `i` inserta, `Esc` vuelve al modo normal, `:wq` guarda y sale, `:q!` sale sin guardar | Con `sudo` para ficheros de sistema. Si no sabes salir: `Esc`, luego `:q!` |

## Redirección y tuberías

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `COMANDO > FICHERO` | stdout al fichero (lo sobrescribe) | Los errores no se redirigen |
| `COMANDO 2> FICHERO` | Solo stderr al fichero | Separar errores de la salida normal |
| `COMANDO > FICHERO 2>&1` | stdout y stderr al mismo fichero | El orden importa; el `&` es necesario |
| `COMANDO > /dev/null` | Descartar la salida normal | `apt update > /dev/null`: los errores siguen visibles |
| `COMANDO1 \| COMANDO2` | Pasar la salida de uno como entrada del otro | `ps aux \| grep ssh`, `journalctl ... \| head` |
| `COMANDO &` | Lanzar en segundo plano | Muere con la shell que lo lanzó (ver Bloque 2: no sustituye a un servicio) |
| `echo ./*` | Ver en qué se expande un asterisco antes de usarlo | Antes de cualquier `rm` con comodín |

## Discos y sistemas de ficheros

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo parted -l` | Discos, tablas de particiones, particiones, tipos y banderas. `-l` lista todos | Averiguar la estructura de una máquina. Requiere `sudo` |
| `mount` | Todo lo montado, con tipo y opciones | Salida enorme con Docker (un `overlay` por contenedor) |
| `mount \| column -t` | Lo mismo, alineado | Más legible |
| `findmnt` | Lo montado, en forma de árbol | Ver qué cuelga de qué |
| `df -h` | Espacio usado y libre por sistema de ficheros. `-h` en unidades legibles (G, M) | Primera comprobación cuando algo falla por falta de espacio |
| `ls -la /` | Contenido de la raíz. `-l` formato largo, `-a` incluye ocultos | Ver la jerarquía y los permisos de los directorios principales |

## Empaquetar y comprimir

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `tar -cf PAQUETE.tar CARPETA/` | Juntar varios ficheros en uno solo, **sin comprimir**. `-c` crear, `-f` nombre del fichero (siempre seguido del nombre) | `tar` agrupa; no reduce tamaño |
| `tar -czf PAQUETE.tar.gz CARPETA/` | Agrupar y comprimir a la vez. `-z` pasa el resultado por `gzip` | Copias de seguridad |
| `tar -xzf PAQUETE.tar.gz` | Extraer. `-x` extraer, `-z` descomprimir gzip, `-f` fichero de entrada | Extrae en el directorio actual |
| `gzip FICHERO` | Comprimir **un** fichero; crea `FICHERO.gz` y **borra el original** | No sabe comprimir carpetas: por eso se usa dentro de `tar` |

## Permisos y propietarios

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ls -l FICHERO` | Tipo, permisos, dueño, grupo, tamaño y fecha | Primer paso ante un `Permission denied` |
| `ls -ld DIRECTORIO` | Lo mismo, del propio directorio. `-d` no entra en él | Sin `-d` lista su contenido |
| `touch FICHERO` | Crear un fichero vacío (o actualizar su fecha) | Para practicar permisos |
| `chmod u+x FICHERO` | Cambiar permisos en notación simbólica. `u` dueño, `g` grupo, `o` resto, `a` todos; `+` añade, `-` quita, `=` fija | `u=rw,g=r,o=` fija exactamente `rw-r-----`; `=` borra lo que hubiera |
| `chmod 640 FICHERO` | Cambiar permisos en octal | `666` deja escribir a todos |
| `chmod 4755 FICHERO` | Con un cuarto dígito: 4 setuid, 2 setgid, 1 sticky | Raro de necesitar |
| `sudo chown USUARIO:GRUPO FICHERO` | Cambiar dueño y grupo | Requiere root. Con `-R` actúa recursivamente |
| `umask` | Ver los permisos que se restan a lo que se cree | Solo afecta a lo creado después |

## Usuarios, grupos y privilegios

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `id` | Tu UID, GID primario y todos tus grupos | Comprobar si estás en `sudo`, `docker`… |
| `groups` | Solo la lista de grupos | |
| `cat /etc/passwd \| head` | Cuentas del sistema: 7 campos por `:` | Legible por todos |
| `sudo cat /etc/shadow \| head -3` | Contraseñas cifradas. `head -3` limita a 3 líneas | Solo root. Nunca copiar los hashes a documentos o repositorios |
| `sudo COMANDO` | Ejecutar un comando con privilegios | Pide **tu** contraseña; cacheada unos minutos por terminal |
| `sudo -k` | Invalidar la caché de `sudo` | Probar de cero si te pide contraseña |
| `su` / `su USUARIO` | Sesión completa como root / como otro usuario | Pide la contraseña del **destino**. En Ubuntu, root suele no tener contraseña utilizable |
| `sudo su` | Sesión de root usando tu contraseña | El prompt pasa a `#`. Se sale con `exit` |
| `sudo visudo` | Editar `/etc/sudoers` con validación | Nunca con un editor directo. Sin editor: `sudo EDITOR=vim visudo` |
| `whoami` | Con qué usuario estás | Dentro de `$(whoami)` para usarlo en otro comando |

## Procesos y señales

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ps aux` | Foto fija de todos los procesos. `a` de todos los usuarios, `u` formato con usuario y memoria, `x` incluye los que no tienen terminal | Lista larga: filtrar con `grep`. `ps` sin flags solo muestra los de tu terminal |
| `ps aux \| head -1` | Solo la cabecera de columnas | Recordar qué es cada columna |
| `ps aux \| grep -E "USER\|NOMBRE"` | Buscar un proceso conservando la cabecera | El propio `grep` aparece en el resultado; el PID correcto es el de la fila del programa real |
| `top` | Procesos y recursos en vivo. `q` sale | Mirar primero la cabecera; ignorar los `kworker` con memoria 0 |
| `kill -15 PID` | Pedir que termine (`SIGTERM`) | Siempre primero. Solo acepta PID. Con procesos de otro usuario hace falta `sudo` |
| `kill -9 PID` | Matar sin aviso (`SIGKILL`) | Solo si `-15` no funcionó; puede dejar datos corruptos |
| `kill -l` | Lista de señales y sus números | Consulta |
| `sleep 300 &` | Proceso de prueba que no hace nada durante 300 s, en segundo plano | Para practicar `ps` y `kill`; muestra su PID al lanzarlo |
| `rm -rf RUTA` | Borrar. `-r` recursivo, `-f` sin preguntar ni avisar si no existe | **Irreversible, sin papelera.** `rm -rf ./` es rechazado; `rm -rf ./*` no. Comprobar antes con `ls -la ./*` |

## Arranque, systemd y journal

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `systemd-analyze` | Tiempo total de arranque, por fase | En una VM no aparecen `firmware`, `loader` ni `initrd` |
| `systemd-analyze blame` | Units ordenadas por tiempo de activación | No mide el retraso real: arrancan en paralelo. `\| head -15` |
| `systemctl get-default` | Target que alcanza el arranque | Comprobar si un servidor arranca en `graphical.target` |
| `sudo systemctl set-default multi-user.target` | Cambiar el target por defecto | Se aplica en el próximo arranque |
| `systemctl list-units --type=target` | Targets activos. `--type=` filtra por tipo | Columnas `LOAD`, `ACTIVE`, `SUB`; `not-found` = la unit ya no existe |
| `sudo journalctl -b` | Log del arranque actual. `-b` limita a ese arranque | Sin `sudo`, solo ves tus mensajes. Con muchos días encendido es enorme: filtrar |
| `sudo journalctl -b -u UNIT --no-pager` | Solo el log de una unit (`-u`). `--no-pager` imprime todo sin abrir `less` | `UNIT` puede ser un nombre parcial (`postgresql`) |
| `sudo systemctl stop UNIT` / `disable UNIT` | Parar ahora / evitar que arranque en el próximo arranque | Una unit activa con el fichero borrado sigue cargada hasta pararla |
| `sudo systemctl daemon-reload` | Hacer que systemd relea las fichas de disco | Tras editar o borrar units. No para las que ya están activas |
| `sudo apt purge PAQUETE -y` | Desinstalar el paquete **y su configuración**. `-y` confirma sin preguntar | `remove` dejaría la configuración. `purge` no limpia directorios de datos fuera de `apt` (`/var/cache/snapd`, `~/snap`) |
| `sudo reboot` | Reiniciar | Corta tu sesión SSH; reconectar con `ssh vps` tras unos segundos |
