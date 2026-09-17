# Redes · Bloque 1 — El modelo y las capas

> Carril de Redes: martes, 1 h. Notas acumulativas del bloque.
> **Material:** Kurose y Ross, *Computer Networking: A Top-Down Approach*.

**Contenido del bloque (roadmap):** TCP/IP, direccionamiento, subredes, puertos, NAT. TCP frente a UDP y por qué existe el handshake.

**Criterio de cierre del bloque:** dibujar a mano el camino de un paquete desde el portátil hasta el VPS, atravesando el NAT del router doméstico, y explicarlo en voz alta sin notas aguantando tres «¿y por qué?» seguidos.

**Estado:** sesiones 1 y 2 hechas. Pendientes las sesiones 3 (puertos y NAT) y 4 (TCP y handshake).

---

## Sesión 1 · Capas y direccionamiento

> Kurose y Ross, cap. 1.5



Para dar estructura al diseño de protocolos de red, los ingenieros los organizan por capas, separando la funcionalidad de cada protocolo que compone el comportamiento de la red.

En internet el stack es de **cinco capas**.

---

### 1. Aplicación

Donde se producen y se consumen los datos. Protocolos como HTTP, SMTP o DNS.

### 2. Transporte

Transmite la información **entre procesos**. Su dirección es el **puerto**.

- **TCP** — garantiza que todo llega y en orden. Es más lento precisamente por eso: espera confirmaciones y retransmite lo que se pierde.
- **UDP** — transmite sin comprobar si llega. Más rápido porque no espera nada.

### 3. Red

Su dirección es la **IP**.

- **En el origen:** escribe la IP de destino final. No cambia en todo el viaje.
- **En cada nodo:** compara esa IP con las suyas.
  - Coincide → sube a transporte. **Fin del viaje.**
  - No coincide → hace *forwarding*: consulta la tabla de rutas y pasa a enlace la IP del siguiente vecino.

### 4. Enlace

Su dirección es la **MAC**.

- **Al recibir:** compara la MAC de la trama con la suya. Si coincide, quita la envoltura y sube el datagrama a red.
- **Al enviar:** traduce a MAC la IP de vecino que le dio red, y construye una **trama nueva** para ese tramo.

### 5. Física

El medio por el que viajan los bits.

---

### Las ideas que lo sostienen

**Encapsulación.** Al bajar, cada capa envuelve lo de arriba con su propia cabecera. Al subir, se desenvuelve en orden inverso.

**Cada capa entiende solo su propia dirección.** Red entiende IPs y nunca toca MACs. Enlace entiende MACs y nunca lee IPs.

**Cada capa habla con su homóloga del otro lado.** Transporte con transporte de extremo a extremo, red con red, enlace con enlace. La diferencia es el alcance de esa conversación.

**Los routers intermedios suben solo hasta red** y vuelven a bajar. Nunca ven la conexión TCP: es un acuerdo privado entre los dos extremos.

**La IP viaja intacta de punta a punta; la trama se destruye y se rehace en cada salto.** De la cabecera IP solo cambia el TTL, que baja de uno en uno.

**Nadie conoce el camino completo.** Ni el origen, ni ningún router. Cada nodo decide solo el siguiente salto, cuando el paquete ya está en sus manos. La ruta emerge de muchas decisiones locales encadenadas.

**Forwarding ≠ routing.** *Forwarding* es consultar la tabla y sacar el paquete por la interfaz que toca: microsegundos, por paquete. *Routing* es el proceso de fondo que **construye** esa tabla mediante los protocolos de enrutado: lento, continuo, ocurre aunque no circule nada.

---

### Unidades y direcciones

| Capa | Unidad | Dirección | Alcance |
|---|---|---|---|
| Aplicación | mensaje | nombres (URL) | extremo a extremo |
| Transporte | segmento (TCP) / datagrama (UDP) | **puerto** | extremo a extremo |
| Red | datagrama | **IP** | extremo a extremo |
| Enlace | trama | **MAC** | **un salto** |
| Física | bit | — | un salto |

> «Datagrama» aparece en dos capas: el de red y el de usuario (UDP). En la práctica casi todo el mundo dice «paquete» para todo.

---

### El recorrido, paso a paso

**En el origen**

1. La aplicación quiere enviar algo a una IP.
2. Transporte prepara el segmento y lo entrega a red con esa IP. No le pasa el puerto: red no lo quiere ni lo mira.
3. Red escribe la IP de destino, consulta la tabla y decide el vecino.
4. Enlace resuelve la MAC de ese vecino y construye la trama.
5. Sale por el medio físico.

**En cada router**

1. Enlace compara la MAC, verifica el checksum, quita la envoltura. La trama muere aquí.
2. Red compara la IP: no es suya. Decrementa el TTL, consulta su tabla, decide su siguiente vecino.
3. Enlace construye una **trama nueva**, con MACs distintas, para el siguiente tramo.

**En el destino**

1. Enlace compara la MAC y sube el datagrama.
2. Red compara la IP: **es suya**. Sube a transporte.
3. Transporte lee el puerto, reordena si hace falta, y entrega al proceso.

Con diez routers, el patrón se repite diez veces: red actúa once veces con el mismo dato; enlace, diez veces con datos nuevos cada vez.

---

### MAC e IP

**La MAC va con la máquina; la IP va con el sitio donde está.**

La MAC viene grabada de fábrica en la tarjeta: 48 bits, los primeros 24 identifican al fabricante (registro del IEEE), los otros 24 los asigna él. La IP la da la red donde te conectas y cambia si te mueves.

**La MAC no es enrutable.** No hay forma de deducir un camino a partir de ella: es un número de serie, no una dirección postal. La IP sí lo es, porque está agrupada por bloques — `89.58.44.0/22` son mil direcciones en una sola línea de tabla. Si internet funcionara por MAC, cada router necesitaría una tabla con todos los dispositivos del planeta.

**MAC para el último metro, IP para todo lo demás.**

### ARP: de IP a MAC

Se resuelve **después** de que red decida el siguiente salto y **antes** de construir la trama.

1. ¿Está la MAC en la caché de vecinos? → instantáneo.
2. ¿No está? → se emite un ARP a `ff:ff:ff:ff:ff:ff` (broadcast) preguntando quién tiene esa IP. Todos lo reciben, solo el interesado contesta con su MAC. El paquete **espera** mientras tanto.

Solo se resuelve la MAC del **siguiente salto**, nunca la del destino final.

Estados de la caché (`ip neigh`):

| Estado | Significado |
|---|---|
| `REACHABLE` | Confirmado hace poco (~30 s). Se usa sin preguntar. |
| `STALE` | Caducó el plazo pero sigue en caché. Se revalida al usarla. |
| `FAILED` | Se preguntó y nadie respondió. |

La caché caduca a propósito: si cambia una tarjeta o se reasigna una IP, el sistema tiene que enterarse.

---

### Puertos

Número de 16 bits cuyo único propósito es que el sistema operativo sepa **a qué proceso** entregar los datos. IP lleva al edificio; el puerto dice a qué extensión.

Los dos lados **no son simétricos**:

- **Servidor** — puerto fijo y conocido de antemano. 22 SSH, 80 HTTP, 443 HTTPS, 5432 PostgreSQL, 8069 Odoo.
- **Cliente** — puerto efímero, asignado al vuelo y liberado al cerrar.

Una conexión se identifica por **cuatro datos**: IP origen, puerto origen, IP destino, puerto destino. Por eso caben tres `ssh vps` simultáneos sin confundirse — solo cambia el puerto de origen.

**El socket `LISTEN` no se convierte en la conexión.** El kernel crea uno nuevo por sesión; el original sigue escuchando. Por eso cien clientes caben en el puerto 22, y por eso reiniciar sshd no corta las sesiones abiertas.

Un servicio solo necesita puerto si habla por TCP o UDP. `cron` o `systemd-logind` no tienen. Y hay comunicación local por **sockets Unix** —ficheros en disco— sin puerto ni red.

---

### Comandos

```bash
ip a                          # interfaces y sus IPs (y la MAC propia)
ip r                          # tabla de rutas — capa de red
ip neigh                      # caché de vecinos: IP → MAC — capa de enlace
ip link show eth0             # MAC de la interfaz
```

```bash
ss -tulpn                     # t=TCP u=UDP l=listening p=proceso n=sin resolver nombres
sudo ss -tulpn                # sin sudo, la columna Process viene vacía
sudo ss -tnp | grep :22       # conexiones establecidas, no las que escuchan
```

```bash
ping -c 50 <IP>               # -c limita el número de paquetes
ssh -G vps | grep hostname    # volcar config efectiva del cliente sin conectar
traceroute -n <IP>            # la cadena de routers: ninguno estaba en `ip r`
```

> El alias `vps` de `~/.ssh/config` **solo lo leen** ssh, scp, rsync y git. `ping vps` falla: usa la IP.

### Cómo se lee `ss`

| Lo que ves | Qué significa |
|---|---|
| `0.0.0.0` en Local | Escucho por **todas** las interfaces. Expuesto a internet. |
| `127.0.0.x` en Local | Solo loopback. Inalcanzable desde fuera. |
| `[::]` en Local | Lo mismo que `0.0.0.0`, en IPv6. |
| `0.0.0.0:*` en Peer | Acepto de cualquier IP y cualquier puerto. |
| `LISTEN` | Esperando conexiones. |
| `UNCONN` | Normal en UDP: no hay conexión que mantener. |
| `Send-Q` en LISTEN | **Backlog máximo**, no cola de envío. Es lo que agota un SYN flood. |
| Mismo PID, `fd` distintos | Un proceso con varios sockets abiertos. |

**Local y Peer se invierten según dónde ejecutes el comando.** «Local» siempre significa «la máquina donde estoy».

---

### Retardos

Cuatro componentes en cada nodo: procesamiento, **cola**, transmisión y propagación. El de cola es el más **variable** —no siempre el mayor— y el único que depende de lo que hagan los demás.

`ping` mide **RTT**, ida y vuelta, y da un número agregado. El libro enseña a descomponer; ping da el total. Y la vuelta puede tomar otra ruta, así que RTT ÷ 2 es una aproximación, no una identidad.

```
rtt min/avg/max/mdev = 37.979/40.409/64.933/5.128 ms
```

| Valor | Lectura |
|---|---|
| **min** | El suelo irreducible: propagación + transmisión. Física. |
| **avg − min** | Retardo de cola medio. Aquí 2,4 ms → ruta descargada. |
| **max** | Un pico. Puede ser el wifi propio, no internet. |
| **mdev** | Jitter. Baja con un max alto = pico aislado, no patrón. |

Primer reflejo de diagnóstico: repetir por cable antes de acusar a la red. Y recordar que los routers responden a ICMP con prioridad baja — un salto lento en `traceroute` puede estar perfectamente sano.

---

### Circuit switching vs packet switching

**Circuit switching** reserva capacidad antes de transmitir, en tres fases: establecimiento (puede **bloquearse** si no hay recursos), transferencia a velocidad garantizada, y liberación. Se reparte el enlace por **FDM** (bandas de frecuencia, como la radio) o **TDM** (ranuras de tiempo, como turnos de palabra). Si no tienes nada que decir, tu banda o tu ranura se desperdicia.

**Packet switching** no reserva nada. Admite siempre, y lo que se degrada es la calidad.

> Circuit switching cambia eficiencia por garantía. Packet switching cambia garantía por eficiencia.

Internet eligió lo segundo porque el tráfico de datos va **a ráfagas**, y reservar para el pico significa tirar la mayor parte del tiempo.

Hoy queda circuit switching en la telefonía clásica (RTC, voz 2G/3G — de ahí la facturación por minutos, el tono de marcado como establecimiento y la señal de ocupado como bloqueo) y en líneas dedicadas. Todo lo demás, incluidas WhatsApp y VoLTE, es packet switching.

---

### Estructura de internet

La jerarquía comercial: los ISP de acceso son clientes de ISPs regionales, que son clientes de los **tier-1**. Los tier-1 no le pagan a nadie: hacen *peering* entre iguales. **El de abajo paga al de arriba por el tránsito.**

Los grandes proveedores de contenido construyen su **red privada global**, separada de internet público, que solo lleva su propio tráfico. Colocan centros de datos pequeños **dentro de los IXP** —puntos físicos donde muchos ISPs se interconectan directamente— y hacen peering *settlement free* con ISPs de nivel bajo, saltándose los escalones intermedios.

El peering gratuito funciona porque el interés es mutuo: recibir el contenido directo le sale más barato al ISP que comprar tránsito a un tier-1 para lo mismo.

**El bypass es parcial:** muchos ISPs de acceso solo son alcanzables atravesando un tier-1, así que también se conectan a ellos y les pagan.

Dos motivos, y el segundo es el fuerte: menos pagos, y **control sobre la entrega** (ruta, latencia, proximidad al usuario). En 2020, Amazon, Google, IBM y Microsoft alcanzaban el 76% de internet sin pasar por un tier-1: **la pirámide se ha aplanado**.

---

### Ataques y colas

Un DDoS es el fenómeno del retardo de cola llevado al extremo, pero **la cola es el síntoma, no el mecanismo**. Tres familias:

| Tipo | Qué agota | Llena la cola de red |
|---|---|---|
| **Volumétrico** | El ancho de banda del enlace. Suele usar amplificación: consulta pequeña con IP falsificada, respuesta enorme hacia la víctima. | Sí |
| **De protocolo** | Una tabla en memoria. El SYN flood manda miles de SYN sin completar el handshake. | **No** |
| **De aplicación** | CPU o base de datos. Peticiones legítimas pero caras. | No |

Un resolver DNS accesible desde internet es munición para amplificación. Ubuntu lo trae escuchando solo en loopback.

---


---

## Sesión 2 · Direccionamiento IPv4 y subredes

> Kurose y Ross, 4.3.1 y 4.3.2



---

### La máscara

### El problema que resuelve

Tu portátil tiene `192.168.1.74` y quiere enviar algo a `192.168.1.30`. Antes de nada debe decidir: **¿este destino está en mi red y se lo doy directo, o está fuera y se lo doy al router?**

Sin ayuda, `192.168.1.30` es solo un número. La máscara es lo que permite decidir.

### Qué hace

Divide los 32 bits de la dirección en dos partes: los del principio identifican **la red**, los del final identifican **al host dentro de ella**.

```
192.168.1 . 74
└── red ──┘  └host┘
```

El emisor compara su parte de red con la del destino. Si coinciden, es un vecino: entrega directa. Si no, al gateway.

> **La analogía:** la máscara es la línea que separa el nombre de la calle del número de portal. *Calle Mayor 74* y *Calle Mayor 30* → vas andando. *Calle Mayor 74* y *Gran Vía 12* → necesitas que alguien te lleve.

### Son bits, no dígitos

`/24` significa **24 bits**, no tres números. Coincide con tres octetos porque cada octeto son 8 bits, pero es una coincidencia afortunada de esa máscara concreta.

```
223.1.1.0/24
11011111.00000001.00000001.00000000
└──────── 24 bits de red ───────┘└─ 8 de host ─┘

89.58.44.0/22
01011001.00111010.001011 00.00000000
└─────── 22 bits de red ──┘└── 10 de host ──┘
```

En el `/22` el tercer octeto está **partido**: 6 bits de red, 2 de host. Por eso esa subred no es «todo lo que empiece por 89.58.44», sino que va del `.44` al `.47`. **El tercer número varía dentro de la misma subred.**

### Nombres

| Término | Nota |
|---|---|
| **Notación CIDR** | El formato con barra. *Classless Inter-Domain Routing*. |
| **Prefijo** / longitud de prefijo | El término más preciso. |
| **Máscara de subred** | El clásico, el que usa el libro. |

Formato largo equivalente, que verás en Windows y routers domésticos:

```
/24  =  255.255.255.0
/22  =  255.255.252.0
/16  =  255.255.0.0
```

Bits de red a unos, bits de host a ceros. De ahí el nombre **máscara**: una plantilla que se superpone a la dirección. Donde hay unos, eso es red.

### Tres cosas distintas que se confunden

| Concepto | Ejemplo | Qué es |
|---|---|---|
| **IP** | `192.168.1.74` | La dirección de una máquina |
| **Máscara** | `/24` | Dónde está la frontera |
| **Red** | `192.168.1.0` | La subred entera |

La máscara **no es** la red: es lo que permite **calcularla**. Se pone a cero la parte de host y lo que queda es la dirección de red.

Cómo distinguir al leer: si la parte de host está toda a ceros, es la red. Si tiene algo, es una máquina concreta.

### La máscara no dice si tu IP cambia

Son cosas independientes:

- **La máscara** describe el rango.
- **`dynamic`** en la salida de `ip a` indica que la dirección vino de DHCP y puede cambiar.

El VPS está en un `/22` de mil direcciones y su IP es **fija**. El portátil está en un `/24` y la suya es **dinámica**. Máscara amplia no implica dirección cambiante.

Lo que sí dice la máscara es **dentro de qué margen** puede cambiar.

---

### Calcular una subred

Cuatro valores, siempre en este orden:

1. **Bits de host** = 32 − prefijo
2. **Dirección de red** — bits de host todos a **cero**. No asignable.
3. **Broadcast** — bits de host todos a **uno**. No asignable.
4. **Hosts** = 2^(bits de host) **− 2**, por los dos extremos reservados

El rango utilizable va de red+1 a broadcast−1.

### Ejercicio resuelto: `192.168.1.74/24`

```
192.168.1.0     ← red, no asignable
192.168.1.1     ← primera utilizable
   ...             254 direcciones
192.168.1.254   ← última utilizable
192.168.1.255   ← broadcast, no asignable
```

2⁸ = 256 direcciones, **254 hosts**.

### Ejercicio resuelto: `89.58.45.111/22` (el VPS)

| | |
|---|---|
| Bits de host | 32 − 22 = **10** |
| Red | `89.58.44.0` |
| Broadcast | `89.58.47.255` |
| Rango utilizable | `89.58.44.1` – `89.58.47.254` |
| Hosts | 2¹⁰ − 2 = **1022** |
| ¿`89.58.48.1` dentro? | **No.** El tercer octeto solo abarca 44–47. |

El gateway es `89.58.44.1`, la **primera utilizable**. Convención habitual: al router se le da la primera o la última del rango.

> Escribe los números hechos, no como potencia. En producción quieres la magnitud de un vistazo.

---

### Broadcast

La dirección «para todos los de esta subred». Se usa **cuando no sabes con quién hablar** — si lo supieras, te dirigirías a él directamente.

Dos usos reales, ambos problemas de arranque:

- **ARP** — «¿quién tiene esta IP?». No sabes qué máquina es: eso es lo que preguntas.
- **DHCP** — no tienes IP ni sabes quién es el router.

### El coste

Un broadcast **lo procesan todas las máquinas** de la subred: sube a la capa de red de cada una, se examina y se descarta. Con 254 es despreciable; con los 65.534 de un `/16` se convierte en problema (*broadcast storm*).

**Ahí hay una razón práctica para dividir en subredes:** cada subred es una frontera que los broadcasts no cruzan. Los routers no los reenvían nunca, así que el daño queda acotado.

En un proveedor serio hay defensas: limitación de tasa por puerto en los switches, aislamiento entre clientes y filtrado de tráfico anómalo.

### Comprobado en el VPS

```bash
ping -c 3 -b 89.58.47.255
```

`-b` habilita el ping a broadcast, desactivado por defecto por ruidoso.

```
64 bytes from 89.58.44.2: icmp_seq=1 ttl=64 time=0.506 ms
64 bytes from 89.58.44.3: icmp_seq=1 ttl=64 time=0.530 ms
3 packets transmitted, 3 received, +2 duplicates, 0% packet loss
```

Tres lecturas:

- **`+2 duplicates`** — ping espera un interlocutor y recibe varios. Los cuenta como duplicados: es la prueba de que el broadcast funcionó.
- **Solo dos responden de 1022.** Casi todo servidor moderno ignora el ping a broadcast, por protección contra amplificación. Las dos que contestan son routers de Netcup, no VPS de clientes: sus MACs coinciden con las entradas marcadas `router` en `ip neigh`.
- **`ttl=64` sin decrementar y 0,5 ms.** Cero saltos: entrega directa por capa de enlace. Compárese con los 39 ms hasta el portátil.

---

### Red local no significa red privada

**Red local = el conjunto de máquinas a las que llegas directamente, sin pasar por un router.** Nada más. No dice nada sobre IPs privadas ni sobre NAT.

| | Casa | VPS |
|---|---|---|
| Red local | `192.168.1.0/24` | `89.58.44.0/22` |
| IPs | **Privadas** | **Públicas** |
| NAT | Sí | No |

En casa esas tres cosas vienen empaquetadas juntas, y de ahí sale la idea equivocada de que «local» implica «privado y detrás de NAT». El VPS tiene red local con IPs públicas y sin NAT — por eso es alcanzable desde fuera directamente.

**Lo raro es la casa, no el VPS.** Todo centro de datos está hecho de segmentos locales con IPs públicas.

### Router y switch

| | Switch | Router |
|---|---|---|
| Conecta | Dentro de la subred | Entre subredes |
| Mira | **MAC** | **IP** |
| Capa | Enlace | Red |

Cuando el VPS habla con `89.58.44.2`, el tráfico pasa por el switch y **nunca toca el router**. Es la distinción red/enlace en forma de cajas físicas.

Mil máquinas no caben en un switch: en un datacenter hay uno por rack y se interconectan formando un segmento plano. Y el gateway tampoco es un aparato: su MAC `00:00:5e:00:01:01` lleva el prefijo **VRRP**, dos routers físicos compartiendo una dirección virtual por redundancia.

---

### DHCP

Entrega automáticamente **cuatro cosas** a una máquina que se conecta: IP, máscara, gateway y servidores DNS.

### La paradoja de arranque

El cliente no tiene IP, no sabe la máscara, no sabe quién es el router ni si existe un servidor DHCP. Y aun así tiene que pedir algo.

Se resuelve con dos direcciones especiales:

- **Origen `0.0.0.0`** — «todavía no tengo dirección».
- **Destino `255.255.255.255`** — broadcast total, todos los bits a uno.

Ese par es la firma de una máquina arrancando desde cero.

### Los cuatro pasos

| Paso | Qué ocurre |
|---|---|
| **Discover** | El cliente grita por broadcast buscando servidor. UDP, puerto 67. |
| **Offer** | Uno o varios servidores ofrecen IP, máscara y tiempo de concesión. |
| **Request** | El cliente elige una oferta y la solicita formalmente. |
| **ACK** | El servidor confirma. |

**Por qué el Offer también va por broadcast** (ejercicio del libro): el servidor conoce la IP que va a dar, pero el cliente **aún no la tiene configurada** — si se la mandara ahí, no la recogería nadie. El cliente identifica su respuesta por el **ID de transacción**.

**Por qué UDP y no TCP:** un handshake TCP necesita los cuatro datos de la conexión, y el cliente no tiene IP propia. UDP no establece nada.

### La concesión

La IP es prestada. En el portátil:

```
valid_lft 32363sec
```

Nueve horas. A mitad de plazo se pide renovación, y el router suele devolver la misma dirección porque tiene apuntada la MAC.

### Limitación de movilidad

Al cambiar de subred recibes otra IP, y como una conexión TCP se identifica por sus cuatro datos, **cambiar de IP la rompe**. Por eso se cortan las descargas al cambiar de wifi. Las redes móviles lo resuelven de otra forma (cap. 7).

### Qué no es DHCP

Buscar redes wifi ocurre **antes** y en la capa de enlace: escaneo de canales, *beacons*, asociación. Ahí no hay IPs todavía. DHCP solo arranca cuando ya hay conexión de enlace — y funciona igual por wifi que por cable.

### Dónde vive

- **En casa:** dentro del router (`192.168.1.1`), que hace de router, switch, punto wifi y servidor DHCP a la vez.
- **En el VPS:** no hay. Netcup configura la IP de forma fija; por eso `ip -br a` no dice `dynamic`.

El router de casa es **cliente DHCP hacia arriba** (recibe su IP pública del operador) y **servidor hacia abajo**. Por eso la IP pública de casa también cambia.

---

### Asignación de bloques

Cadena de reparto jerárquica:

**IANA** → **RIR** (cinco regionales; Europa es RIPE NCC) → **ISP y operadores** → **cliente final**

Cada nivel trocea su bloque **alargando el prefijo**. Cada bit añadido parte el bloque en dos:

| Un `/16` se parte en | Cantidad | Direcciones cada uno |
|---|---|---|
| `/18` | 4 | 16.384 |
| `/22` | 64 | 1.024 |
| `/24` | 256 | 256 |

Netcup decidió que sus segmentos fueran `/22`: mil máquinas por dominio de broadcast.

### Por qué «classless»

Antes los bloques solo podían ser `/8`, `/16` o `/24`. Una empresa que necesitaba 300 direcciones no cabía en un `/24` y se llevaba un `/16` entero, desperdiciando 65.000. Así se agotó IPv4 antes de tiempo.

**CIDR eliminó las clases:** cualquier longitud de prefijo es válida.

### Agregación

Un router de tránsito no guarda `89.58.44.0/22`: guarda el bloque grande de Netcup, o el de RIPE. **Prefijos más cortos = menos entradas.**

Eso es lo que permite que la tabla global de rutas tenga cientos de miles de líneas y no miles de millones. Y es la razón de que la IP sea enrutable y la MAC no: **la jerarquía de reparto es la que crea el orden.**

```bash
whois 89.58.45.111     # de qué bloque y qué organización es una IP
```

---

### Leer un traceroute

```
 1  192.168.1.1  0.292 ms  0.425 ms  0.624 ms
 2  * * *
 5  * * 213.140.36.190  5.755 ms
 9  62.115.137.252  47.239 ms 62.115.46.183  35.151 ms 62.115.137.252  47.168 ms
11  89.58.45.111  39.020 ms 213.248.86.71  43.582 ms 89.58.45.111  39.229 ms
```

### Estructura

```
9    62.115.137.252   47.239 ms    62.115.46.183   35.151 ms
│    └─ IP sonda 1 ┘  └tiempo 1┘   └─ IP sonda 2 ┘ └tiempo 2┘
└─ nº de salto
```

**Tres sondas por salto**, cada una con su IP y su tiempo. La IP **solo se escribe cuando cambia** respecto a la sonda anterior: una IP y tres tiempos = siempre el mismo camino.

### Cómo funciona

Aprovecha el TTL. Manda un paquete con TTL=1: el primer router lo decrementa a 0, lo descarta y **avisa** al origen; ese aviso revela su IP. Luego TTL=2, y así. No hay ninguna consulta de ruta: es un mecanismo de seguridad reutilizado para dibujar el camino.

### Reglas de lectura

**Un asterisco significa «no hubo respuesta», nunca «el paquete no llegó».** El paquete puede haber llegado y la máquina haber decidido callarse. Confundir silencio con caída es el error clásico. En la salida de arriba los saltos 2–4 callan y el 5 responde: el tráfico pasaba perfectamente.

**Los tiempos de saltos intermedios no son fiables y no deben compararse entre sí.** Responder a una sonda obliga al router a generar un mensaje nuevo con su CPU, tarea de **baja prioridad**. Además cada fila mide una ruta de vuelta distinta. Un salto intermedio de 200 ms con destino a 40 ms está perfectamente sano.

**El tiempo total es el del último salto, no la suma de las filas.** Todos los tiempos se miden desde el origen.

**Cada tiempo pertenece a la IP que tiene delante.** En el salto 11, los 43,582 ms son de `213.248.86.71`, que no es el destino: esa sonda tomó otra ruta y murió antes de llegar. El dato bueno son los ~39 ms que acompañan a `89.58.45.111`.

### Lo que revela esta salida concreta

- **Once saltos** de Madrid a Núremberg, ~39 ms. La tabla de rutas del portátil tiene **dos líneas**: ninguno de los nueve routers intermedios estaba ahí.
- **Balanceo de carga** en los saltos 7, 9 y 11: sondas de la misma tanda tomando caminos distintos. Es la confirmación medida de que dos paquetes de la misma comunicación pueden ir por rutas diferentes — y de por qué TCP tiene que reordenar.
- **El salto de 5 ms a 47 ms** entre los saltos 5 y 7 es la distancia física: ahí el paquete sale de España.
- Los ~39 ms coinciden con el mínimo medido por `ping` en la sesión 1. Dos herramientas distintas, mismo número.

---

### Comandos

### Ver direcciones

```bash
ip a                        # todas las interfaces, todas sus direcciones
ip -br a                    # -br = brief: una línea por interfaz
ip -4 -br a                 # -4 = solo IPv4
ip -br a | grep UP          # solo interfaces activas
ip a show enp5s0            # una interfaz concreta
```

`ip` es la herramienta de red de Linux (sustituta de `ifconfig`). `a` abrevia `address`.

**Cuándo usar cada forma:** `ip a` en una máquina desconocida, para ver qué hay. `ip -br a` cuando sobra ruido — con Docker instalado salen dieciséis interfaces. `ip a show <iface>` cuando ya sabes el nombre y quieres el detalle.

> **Sintaxis de `ip`:** `ip [opciones] OBJETO [acción]`. El objeto va después de las opciones y **nunca al final**. `ip -a` falla porque `-a` es una opción sin objeto al que aplicarse. Objetos abreviables: `a`=address, `r`=route, `neigh`=neighbour, `link`.

> **No adivines nombres de interfaz.** En el VPS es `eth0`; en el portátil, `enp5s0`. Linux moderno los genera desde la posición física de la tarjeta (`enp5s0` = ethernet, bus PCI 5, slot 0) para que sean estables entre reinicios. Primero `ip -br a`, luego usas el nombre que salga.

### Recorrido y latencia

```bash
traceroute -n <IP>          # por dónde va. -n = no resolver nombres DNS
tracepath -n <IP>           # equivalente, viene de serie en Ubuntu, sin root
ping -c 20 <IP>             # cuánto tarda. -c = número de paquetes
ping -c 3 -b <broadcast>    # -b = permitir destino broadcast
```

**Cuál usar:** `ping` para **cuánto** tarda; `traceroute` para **por dónde** va. Traceroute mide peor, porque los routers responden a sus sondas con prioridad baja.

### Instalar lo que falta

```bash
sudo apt update                        # refresca la LISTA de paquetes, no instala nada
sudo apt install traceroute tcpdump    # varios paquetes en una línea
```

`apt update` antes de instalar: si la lista está vieja, `apt` puede pedir una versión que ya no existe en el servidor. En Arch el equivalente es `sudo pacman -S <paquete>` (`-S` = sync).

### DNS del sistema

```bash
resolvectl status           # configuración completa por interfaz
resolvectl dns enp5s0       # solo los DNS de una interfaz — mucho más legible
```

Para leer `resolvectl status` con muchas interfaces: **busca la que tiene `Default Route: yes`** e ignora el resto. Las de Docker solo tienen LLMNR y mDNS, protocolos de descubrimiento local.

### Encadenar comandos

```bash
ping -c 1 89.58.44.2; ip neigh | grep 44.2
```

`;` ejecuta el segundo comando termine como termine el primero. `&&` solo lo ejecutaría si el primero tuvo éxito. `|` pasa la salida del primero como entrada del segundo.

---

### Observaciones del entorno

**El portátil** tiene `192.168.1.74/24 dynamic` en `enp5s0` — por cable, no wifi. Y trece interfaces más de Docker: cada `br-*` es la red de un proyecto Compose, cada `veth*` el cable virtual de un contenedor. Todas en `172.x.0.1/16`, o sea **65.534 direcciones cada una**.

**El VPS** tiene `89.58.45.111/22` fija, y también una IPv6 global. Su `ip neigh` solo contiene routers de Netcup.

**Rangos privados vistos:** `192.168.x.x` en casa, `172.16–31.x.x` en Docker. No son enrutables en internet — de ahí la necesidad del NAT, que es la sesión 3.

**La IP pública de casa** aparece en el banner de login del VPS (`Last login ... from 80.29.58.105`). Ese par —`192.168.1.74` dentro, `80.29.58.105` fuera— es exactamente lo que traduce el NAT.

---


---

## Pendientes del bloque

### Hechos

- [x] Comparar `ip a` / `ip r` entre portátil y VPS
- [x] Calcular subredes a mano (`/24` y `/22`)
- [x] Instalar `traceroute` y `tcpdump` en el VPS

### Abiertos

- [ ] Ejercicio con `/26`, donde el corte cae en el **último** octeto y la subred ya no empieza en `.0`
- [ ] Verificar con `ipcalc` algún cálculo hecho a mano
- [ ] Los 10 minutos en voz alta de la sesión 2: por qué la máscara es una frontera
- [ ] Capturar el handshake con `tcpdump` (sesión 4)
- [ ] Guardar la salida de `sudo ss -tulpn` como foto del «antes», para comparar tras desplegar Odoo

### Para bloques posteriores

- [ ] **Bloque 2 (DNS):** `DNSOverTLS` está desactivado, y el portátil usa `8.8.8.8` en vez de lo que daría el router — averiguar quién lo configuró
- [ ] **Bloque 3 de Linux:** Odoo debe escuchar en `127.0.0.1:8069` y nginx en `0.0.0.0` — la decisión se entiende con la sesión 1
- [ ] **Bloque 4 de Linux:** las reglas de `ufw` usan notación CIDR. Un `/16` donde querías un `/32` es un agujero invisible

---

## Criterios de cierre por sesión

| Sesión | Criterio | Estado |
|---|---|---|
| 1 · Capas | Explicar qué hace cada capa con el sobre, sin notas | Hecho |
| 2 · Subredes | Explicar por qué el VPS llega directo a `89.58.44.2` pero necesita el gateway para `8.8.8.8` | Pendiente |
| 3 · Puertos y NAT | Por qué el VPS recibe conexiones entrantes y el portátil no | — |
| 4 · TCP y handshake | Por qué existe el handshake: acordar números de secuencia | — |
| **Bloque** | **El recorrido completo a mano, atravesando el NAT** | — |
