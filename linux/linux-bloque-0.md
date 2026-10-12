# Linux/VPS · Bloque 0 — El servidor existe

Un VPS con Ubuntu en el que se entra por clave SSH, con un usuario propio sin privilegios permanentes, sin login por contraseña y sin acceso de root por SSH.

**Entorno de referencia:** Ubuntu 24.04 LTS (imagen minimal) · OpenSSH 9.6. Las directivas y opciones de este documento existen en esa versión; con otra, confírmalas en la documentación de la versión instalada (`ssh -V` en cada máquina, `man sshd_config` en el servidor).

---

# Parte 1 · Teoría

## 1. El VPS y sus vías de acceso

Un **VPS** (*Virtual Private Server*) es una máquina virtual alojada en el hardware de un proveedor. Tiene sus propios vCores, memoria y disco reservados, una IP pública y un sistema operativo completo que administras tú. El proveedor entrega la máquina con un usuario `root` y su contraseña; todo lo demás es trabajo propio.

El **panel del proveedor** (en Netcup, el SCP) es la vía de gestión que no depende del sistema operativo: desde ahí se instala la imagen, se consultan las huellas de las claves de host y se abre la consola de emergencia.

| Vía | Depende de la red y de `sshd` | Sujeta a `sshd_config` | Uso |
|---|---|---|---|
| SSH | Sí | Sí | Trabajo diario |
| Consola VNC del panel | No | No | Recuperación cuando SSH no funciona |

La consola VNC equivale a tener un monitor y un teclado enchufados a la máquina. Por eso cualquier usuario con contraseña (incluido `root`) puede entrar por ella aunque SSH lo prohíba. Es la red de seguridad de todo lo que se cambia en SSH, y se comprueba que funciona **antes** de necesitarla.

## 2. Versiones LTS

Ubuntu publica una versión **LTS** (*Long Term Support*) cada dos años, en abril de los años pares. Cada LTS recibe cinco años de soporte estándar (parches de seguridad y correcciones).

| Versión | Salida | Fin del soporte estándar | Situación |
|---|---|---|---|
| 22.04 | abril 2022 | abril 2027 | Muy rodada, pero el soporte se acaba pronto |
| 24.04 | abril 2024 | abril 2029 | Rodada y con margen de soporte |
| 26.04 | abril 2026 | abril 2031 | Demasiado reciente: poca documentación de incidencias y poca presencia en servidores de clientes |

Para un servidor se elige la LTS que combine **rodaje** (problemas ya documentados), **margen de soporte** y **adopción real** (lo que vas a encontrar en producción).

Una **imagen minimal** trae solo lo imprescindible para arrancar y conectarse. Herramientas habituales como `nano` no vienen instaladas y se añaden con `apt` según hacen falta.

## 3. Root frente a usuario propio con `sudo`

Trabajar como `root` de forma permanente tiene tres problemas, y un usuario propio en el grupo `sudo` resuelve los tres:

| Problema con root directo | Con usuario propio + `sudo` |
|---|---|
| **Exposición:** cualquier comando mal escrito tiene privilegios totales | Los privilegios se piden comando a comando, solo cuando hacen falta |
| **Anonimato:** todas las acciones aparecen como `root` | `sudo` registra qué usuario ejecutó qué (`journalctl -t sudo`) |
| **Contagio:** si se compromete un proceso, tiene permisos de root | Un proceso comprometido hereda los permisos del usuario |

Pertenecer al grupo `sudo` no da privilegios permanentes: da el derecho a pedirlos autenticándote con **tu** contraseña. El mecanismo completo (`/etc/sudoers`, caché de contraseña, `su` frente a `sudo`) está en el Bloque 1, §8.

## 4. SSH: cliente, servidor y sus ficheros

SSH es un protocolo para abrir una shell en otra máquina a través de un canal cifrado. Tiene dos programas:

| Pieza | Dónde vive | Qué hace | Su configuración |
|---|---|---|---|
| `ssh` (cliente) | Portátil | Inicia la conexión | `~/.ssh/config` (del usuario), `/etc/ssh/ssh_config` (de todo el sistema) |
| `sshd` (servidor o *daemon*) | VPS | Escucha en el puerto 22 y atiende las conexiones | `/etc/ssh/sshd_config` y `/etc/ssh/sshd_config.d/` |

`ssh_config` y `sshd_config` se diferencian en una sola letra y configuran programas distintos: la `d` es de *daemon*. Editar `ssh_config` en el servidor para cambiar quién puede entrar no tiene ningún efecto.

En Ubuntu 24.04 el puerto 22 lo abre `ssh.socket` y `ssh.service` lanza `sshd`; el servicio se gestiona como `ssh` (no `sshd`). El detalle de la activación por socket está en el Bloque 2, §7.

Ficheros que intervienen a cada lado:

| Fichero | Máquina | Contenido |
|---|---|---|
| `~/.ssh/id_ed25519` | Portátil | Clave privada del usuario. Nunca sale de la máquina |
| `~/.ssh/id_ed25519.pub` | Portátil | Clave pública del usuario. Es la que se copia al servidor |
| `~/.ssh/known_hosts` | Portátil | Huellas de los servidores ya aceptados |
| `~/.ssh/config` | Portátil | Alias de conexión y opciones por servidor |
| `/etc/ssh/ssh_host_*_key` y `.pub` | VPS | Claves de host: identifican al servidor ante los clientes. Las privadas solo las lee root |
| `~/.ssh/authorized_keys` | VPS (en el home de cada usuario) | Claves públicas autorizadas a entrar como ese usuario, una por línea |
| `/etc/ssh/sshd_config` | VPS | Configuración de `sshd` |

## 5. Autenticación en dos fases

Cada conexión SSH verifica las dos identidades, en este orden.

**Fase 1 · El cliente comprueba al servidor.** El servidor presenta su clave de host. En la primera conexión el cliente muestra su **huella** (*fingerprint*, un resumen corto de la clave) y pide confirmación. Esa huella se coteja con la que publica el panel del proveedor: así sabes que hablas con tu máquina y no con un intermediario. Al aceptarla se guarda en `known_hosts` y las conexiones siguientes la comprueban solas. Si cambia, SSH se niega a continuar y avisa de un posible ataque *man-in-the-middle*.

El servidor tiene varias claves de host, una por algoritmo; la huella que se muestra es la del algoritmo negociado, normalmente ED25519.

**Fase 2 · El servidor comprueba al usuario.** Con clave pública funciona como un reto:

1. El servidor envía un dato aleatorio, distinto en cada conexión.
2. El cliente lo firma con la clave privada.
3. El servidor verifica la firma con la clave pública guardada en `authorized_keys`. Si cuadra, concede acceso.

La clave privada nunca viaja por la red, ni cifrada. Y como el reto no se repite, capturar el tráfico de una conexión no sirve para suplantarte en otra.

**Tipo de clave:** `ed25519` es el algoritmo recomendado para claves nuevas: claves cortas, rápidas y seguras. **Passphrase:** cifra la clave privada en el disco del portátil; si alguien roba el fichero sin la frase, no puede usarlo.

## 6. Métodos de autenticación y las directivas que los controlan

`sshd` puede ofrecer varios métodos. El cliente prueba los que el servidor anuncia, en orden de preferencia.

| Método | Qué pide | Directiva que lo controla |
|---|---|---|
| `publickey` | Firmar el reto con la clave privada | `PubkeyAuthentication` (activo por defecto) |
| `password` | La contraseña del usuario | `PasswordAuthentication` |
| `keyboard-interactive` | Preguntas del sistema de autenticación (PAM), que pueden incluir la contraseña | `KbdInteractiveAuthentication` |

Para que solo quede la clave hay que cerrar **los dos** caminos a la contraseña. Con `PasswordAuthentication no` pero `KbdInteractiveAuthentication yes`, PAM puede seguir pidiendo la contraseña por la vía interactiva.

Directivas de endurecimiento del bloque:

| Directiva | Valor | Efecto |
|---|---|---|
| `PermitRootLogin` | `no` | Root no puede iniciar sesión por SSH con ningún método |
| `PasswordAuthentication` | `no` | Deja de ofrecerse el método `password` |
| `KbdInteractiveAuthentication` | `no` | Deja de ofrecerse `keyboard-interactive` |

**Por qué importa:** un servidor con IP pública recibe intentos automatizados de adivinar contraseñas desde el primer día. Sin métodos basados en contraseña, esos intentos no tienen dónde probar.

**Permisos exigidos.** `sshd` ignora `authorized_keys` en silencio si el directorio `~/.ssh` o el fichero tienen permisos más abiertos de lo debido (directiva `StrictModes`, activa por defecto): `~/.ssh` en `700` y `authorized_keys` en `600`, ambos del propio usuario. La notación octal está en el Bloque 1, §6.

## 7. Cómo lee `sshd` su configuración

Tres reglas explican casi todos los «he cambiado la directiva y no hace nada»:

| Regla | Consecuencia |
|---|---|
| **Gana el primer valor leído** | Si una directiva aparece dos veces, vale la primera. Al revés que en la mayoría de programas |
| **`Include` va al principio** | `sshd_config` incluye `/etc/ssh/sshd_config.d/*.conf` en sus primeras líneas, así que esos fragmentos se leen antes y mandan sobre lo que escribas debajo. Algunas imágenes traen ahí un fichero que activa `PasswordAuthentication` |
| **`Match` acota hasta el final** | Todo lo que va detrás de una línea `Match` se aplica solo a esa condición (un usuario, una IP...). Las directivas globales van antes de cualquier `Match` |

Dos comprobaciones distintas:

| Comando | Responde a |
|---|---|
| `sudo sshd -t` | ¿La sintaxis es válida? Silencio significa que sí. No dice qué valor queda |
| `sudo sshd -T` | ¿Qué valor usa `sshd` de verdad para cada directiva, después de aplicar `Include` y el orden? |

## 8. Aplicar cambios sin quedarse fuera

**Orden de los pasos.** Primero se instala la clave y se **comprueba** que entras con ella; solo después se desactiva la contraseña. Invertirlo deja la máquina sin acceso por SSH.

**La sesión abierta es el salvavidas.** Cada sesión SSH cuelga de su propio proceso hijo, independiente del proceso que escucha (la cadena completa está en el Bloque 1, §9). Reiniciar o recargar `ssh` no corta las sesiones abiertas: por eso se cambia la configuración en una terminal, se prueba desde una **segunda** terminal y la primera no se cierra hasta confirmar que la segunda entra.

**`reload` frente a `restart`:**

| Acción | Qué hace con `sshd` | Sesiones abiertas | Conexiones nuevas |
|---|---|---|---|
| `systemctl reload ssh` | Le pide releer la configuración sin parar | Siguen igual | Usan la configuración nueva |
| `systemctl restart ssh` | Lo para y lo vuelve a arrancar | Siguen igual | Usan la configuración nueva |

Para saber si un cambio se aplicó de verdad no basta con haber escrito el comando: hay que verlo en el sistema. La hora de arranque en `systemctl status ssh` confirma un `restart`; una línea `Reloading` en `journalctl -u ssh` confirma un `reload`.

## 9. La terminal remota: `TERM` y terminfo

Los programas de pantalla completa (`nano`, `vim`, `less`) necesitan saber qué sabe hacer tu emulador de terminal. Lo averiguan con la variable `TERM`, que SSH copia del portátil al servidor, y buscando ese nombre en la **base de datos terminfo** de la máquina donde se ejecutan.

Si el emulador es reciente (Ghostty usa `TERM=xterm-ghostty`), el servidor no lo conoce y los programas fallan con `Error opening terminal`. Se arregla copiando la descripción del portátil al servidor:

| Dónde se instala | Quién la ve | Resultado con `sudo nano` |
|---|---|---|
| `~/.terminfo` del usuario (`tic` sin `sudo`) | Solo ese usuario | Sigue fallando: `sudo` limpia el entorno y root no mira tu home |
| Base de datos del sistema (`sudo tic`) | Todos los usuarios, root incluido | Funciona |

---

# Parte 2 · Ejemplos

## La máquina: `backend-lab`

| | |
|---|---|
| Proveedor y plan | Netcup VPS 500 G12 |
| Hardware | 2 vCore · 4 GB DDR5 ECC · 128 GB NVMe |
| Sistema | Ubuntu 24.04 LTS, imagen minimal UEFI amd64 |
| Hostname | `backend-lab` |
| Usuario | `miguel`, en el grupo `sudo` |
| Panel | SCP de Netcup (imagen, huellas y consola VNC en *Screen*) |

Ubuntu frente a Debian: Debian es más limpio para aprender, pero Ubuntu es lo que aparece con más frecuencia en despliegues de Odoo. 24.04 frente a 22.04 y 26.04: ver la tabla de §2.

## Alias de conexión

```
# Portátil: ~/.ssh/config
Host vps
    HostName IP_DEL_VPS
    User miguel
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

`HostName` es la IP que muestra el SCP. `IdentitiesOnly yes` hace que el cliente ofrezca solo la clave de `IdentityFile`, y no todas las que tenga cargadas. A partir de aquí basta `ssh vps`, y el alias lo usan también `scp`, `rsync` y Git.

## Las tres directivas en `sshd_config`

```
# VPS: /etc/ssh/sshd_config (fragmento, sin # delante y antes de cualquier Match)
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
```

Comprobación de cómo quedaron:

```
miguel@backend-lab ~> grep -n "^PermitRootLogin\|^PasswordAuthentication\|^KbdInteractive" /etc/ssh/sshd_config
```

La salida debe mostrar cada directiva una sola vez, con su número de línea y el valor `no`. En `backend-lab`, `/etc/ssh/sshd_config.d/` estaba vacío, así que no había fragmentos que se adelantaran.

## Primera conexión: la huella

```
The authenticity of host 'IP_DEL_VPS' can't be established.
ED25519 key fingerprint is SHA256:...
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Antes de escribir `yes`, se compara el `SHA256:...` con la huella ED25519 del SCP. En vez de `yes` también se puede pegar la huella del panel: el cliente la compara él mismo.

## Verificación con `ssh -v`

Desde una segunda terminal del portátil, con la primera aún abierta en el VPS:

| Línea de `ssh -v vps` | Valor que confirma el cierre del bloque |
|---|---|
| `Server host key: ssh-ed25519 SHA256:...` | Coincide con la huella del SCP |
| `Host '...' is known and matches the ED25519 host key` | El servidor está en `known_hosts` |
| `Authentications that can continue: publickey` | El servidor solo ofrece clave pública |
| `Authenticated to ... using "publickey"` | La entrada ha sido por clave |

Prueba en negativo, forzando la contraseña:

```
$ ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no vps
miguel@IP_DEL_VPS: Permission denied (publickey).
```

Entre paréntesis aparecen los métodos que el servidor admite: solo `publickey`.

## El `reload` que nunca se ejecutó

Tras endurecer SSH parecía que `reload` no había bastado y que hizo falta `restart`. Al consultar el journal, no había ninguna línea `Reloading` en `ssh.service` ni el comando en el registro de `sudo`: el `reload` no llegó a ejecutarse, y el cambio lo aplicó el `restart`. La lección no es sobre `reload`, sino sobre el método: una conclusión sobre un servicio se confirma en el journal, no en el recuerdo.

```
journalctl -u ssh -S '2026-09-11' -U '2026-09-12' | grep -iE 'reload|stopp|start'
journalctl -t sudo -S '2026-09-11' -U '2026-09-12'
```

## Fallos típicos y cómo se ven

| Causa | Dónde se ve | Mensaje |
|---|---|---|
| `sshd -t` sin `sudo` | VPS | `no hostkeys available -- exiting.` Es de permisos (las claves de host solo las lee root), no de configuración |
| Se reinstaló la imagen y la huella cambió | Portátil | `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` Se borra la entrada vieja con `ssh-keygen -R` tras verificar la nueva en el SCP |
| Permisos abiertos en `~/.ssh` o `authorized_keys` | Portátil: `Permission denied (publickey)` o vuelve a pedir contraseña. VPS: `Authentication refused: bad ownership or modes` en el journal de `ssh` | `chmod 700` y `chmod 600` |
| Demasiadas claves en el cliente | Portátil | `Too many authentication failures`. Se evita con `IdentitiesOnly yes` |
| Directiva editada en `ssh_config` en vez de `sshd_config` | Ninguno | El cambio no tiene efecto. `sudo sshd -T` muestra el valor antiguo |
| Un fragmento de `sshd_config.d/` fija otro valor | Ninguno | `sudo sshd -T` muestra el valor del fragmento |
| Cambio guardado pero no aplicado | VPS | `systemctl status ssh` con hora de arranque anterior al cambio y sin `Reloading` en el journal |
| `usermod -G sudo` sin `-a` | VPS | El usuario pierde todos sus demás grupos. `groups` lo confirma |
| Terminal desconocida para el servidor | VPS | `Error opening terminal: xterm-ghostty.` con `nano`, `vim` o `less` |
| Consola VNC con símbolos cambiados | Panel | Teclado en distribución US; el pegado no funciona y hay que teclear |

## Preguntas frecuentes

| Pregunta | Comando (dónde) |
|---|---|
| ¿En qué máquina estoy? | `hostname` (cualquiera) |
| ¿Qué versión de Ubuntu tengo? | `lsb_release -a` o `cat /etc/os-release` (VPS) |
| ¿Qué versión de OpenSSH? | `ssh -V` (en cada máquina) |
| ¿Qué huella tiene mi servidor? | `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` (VPS) |
| ¿Qué valor usa `sshd` para una directiva? | `sudo sshd -T \| grep -i passwordauthentication` (VPS) |
| ¿Qué métodos ofrece el servidor? | `ssh -v vps 2>&1 \| grep "can continue"` (portátil) |
| ¿Pertenezco al grupo `sudo`? | `groups miguel` (VPS) |
| ¿Se aplicó el último cambio en SSH? | `systemctl status ssh` (hora de arranque) y `journalctl -u ssh -n 50` (VPS) |
| ¿Están intentando entrar con contraseña? | `journalctl -u ssh \| grep -i "invalid user"` (VPS) |

---

# Parte 3 · Comandos útiles del bloque

## Conexión y claves

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ssh root@IP` | Conectar como un usuario concreto a una IP | Primer acceso a una máquina recién instalada (portátil). Cotejar la huella antes de aceptar |
| `ssh vps` | Conectar usando un alias de `~/.ssh/config` | Uso diario (portátil) |
| `ssh -v vps` | Conectar mostrando la traza: `-v` *verbose*; `-vv` y `-vvv` dan más detalle | Diagnosticar qué métodos ofrece el servidor y con cuál entras. Desde una segunda terminal tras tocar `sshd_config` |
| `ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no vps` | Forzar la contraseña: `-o` fija una opción del cliente para esta conexión | Comprobar que el servidor la rechaza. Debe responder `Permission denied (publickey)` |
| `ssh-keygen -t ed25519 -C "comentario"` | Generar un par de claves: `-t` tipo, `-C` comentario que acaba al final de la clave pública | En el **portátil**, nunca en el servidor. El comentario sirve para saber de quién es cada línea de `authorized_keys`. Poner passphrase |
| `ssh-copy-id USUARIO@IP` | Añadir tu clave pública al `authorized_keys` remoto; `-i FICHERO` elige qué clave | Portátil, mientras el servidor aún acepta contraseña. Crea `~/.ssh` y el fichero si no existen |
| `ssh-keygen -lf FICHERO.pub` | Mostrar la huella de una clave: `-l` huella, `-f` fichero | VPS, para comparar la clave de host con lo que ve el cliente |
| `ssh-keygen -R HOST` | Borrar la entrada de un servidor en `known_hosts` | Portátil, tras reinstalar el VPS, **después** de verificar la huella nueva en el panel |
| `ssh -V` | Versión de OpenSSH | Antes de consultar la documentación de una directiva |
| `chmod 700 ~/.ssh` / `chmod 600 ~/.ssh/authorized_keys` | Solo el dueño accede al directorio / lee y escribe el fichero | VPS. Con permisos más abiertos, `sshd` ignora la clave sin avisar al cliente |

## Configuración de `sshd`

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo nano /etc/ssh/sshd_config` | Editar la configuración del servidor | VPS. Con `d`: `ssh_config` es la del cliente. Si `sudo nano` falla por la terminal, ver «Terminal» |
| `grep -n "^PermitRootLogin\|^PasswordAuthentication\|^KbdInteractive" /etc/ssh/sshd_config` | Ver las líneas activas: `-n` número de línea, `^` principio de línea, `\|` alternativa | Comprobar que no quedan con `#` ni duplicadas |
| `ls /etc/ssh/sshd_config.d/` | Ver los fragmentos que se leen antes | Si un cambio no surte efecto |
| `sudo sshd -t` | Validar la sintaxis sin aplicar; `-t` *test* | Siempre antes de recargar o reiniciar. Sin `sudo`: `no hostkeys available` |
| `sudo sshd -T` | Volcar la configuración efectiva; `-T` *extended test* | Saber qué valor manda de verdad. Filtrar con `\| grep -i DIRECTIVA` |

## Servicio SSH

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo systemctl restart ssh` | Parar y arrancar `sshd` | VPS, tras validar con `sshd -t`. No corta la sesión abierta: no la cierres hasta probar desde otra terminal. El servicio es `ssh`, no `sshd` |
| `sudo systemctl reload ssh` | Releer la configuración sin parar | Confirmar en el journal que se ejecutó (`Reloading`) |
| `systemctl status ssh ssh.socket` | Estado del servicio y del socket que abre el puerto | La hora de `Active: ... since` confirma un `restart` |
| `sudo journalctl -u ssh -n 50` | Últimos 50 eventos del servicio: `-u` unit, `-n` número de líneas | Intentos de acceso, recargas, errores de permisos en `authorized_keys` |
| `sudo grep sshd /var/log/auth.log` | Buscar eventos de SSH en el log de autenticación | Alternativa al journal si el sistema tiene ese fichero |

## Usuarios

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `adduser USUARIO` | Crear un usuario de forma interactiva: home, shell y contraseña | VPS, como root en el primer acceso. `useradd` es la versión de bajo nivel, sin preguntas |
| `usermod -aG sudo USUARIO` | Añadir a un grupo: `-a` añade, `-G` grupo suplementario | Sin `-a`, **sustituye** todos los grupos. Hay que volver a iniciar sesión para que surta efecto |
| `groups USUARIO` | Listar los grupos del usuario | Verificar el paso anterior |

## Sistema y paquetes

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `pwd` / `hostname` | Directorio actual / nombre de la máquina | Antes de ejecutar algo con varias terminales abiertas: confirma si estás en el portátil o en el VPS |
| `lsb_release -a` / `cat /etc/os-release` | Distribución y versión | Al llegar a una máquina nueva (también en solo lectura en un servidor ajeno) |
| `sudo apt update` | Actualizar la lista de paquetes disponibles | Antes de cualquier `apt install`. No instala nada |
| `sudo apt install nano` | Instalar un paquete | En imágenes minimal, que traen lo justo |

## Terminal

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `infocmp -x xterm-ghostty \| ssh vps -- tic -x -` | Copiar la descripción de la terminal al usuario remoto: `infocmp` la vuelca en el portátil, `tic` la instala; `-x` incluye extensiones, `-` lee de la entrada | Portátil. Queda en `~/.terminfo`: `sudo nano` sigue fallando |
| `infocmp -x xterm-ghostty \| sudo tic -x -` | Instalarla para todo el sistema | VPS (con el fichero disponible allí). Solución definitiva |
| `sudo TERM=xterm-256color nano FICHERO` | Abrir el editor con una terminal genérica que todo sistema conoce | Apaño puntual cuando no puedes instalar la descripción |
| `shell-integration-features = ssh-env,ssh-terminfo,sudo` | Opción de Ghostty que envía la descripción al conectar | En `~/.config/ghostty/config` del portátil |
