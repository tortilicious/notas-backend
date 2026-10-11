# Redes · Bloque 1 — El modelo y las capas

El modelo de capas de internet, direccionamiento IPv4 y subredes, puertos y sockets, NAT, y TCP frente a UDP con el handshake. Todo observado en el VPS y en el portátil con `ip`, `ss`, `ping`, `traceroute` y `tcpdump`.

**Entorno de referencia:** VPS `backend-lab` (Ubuntu 24.04 en Netcup, Núremberg; interfaz `eth0`, IP `89.58.45.111/22`, gateway `89.58.44.1`; shell fish) y portátil con CachyOS (Arch; interfaz de cable `enp5s0` en la red de casa `192.168.1.0/24`, detrás del router de O2). Las opciones de `ip`, `ss` y `tcpdump` pueden variar entre versiones: confírmalas con `man` en la máquina donde vayas a ejecutarlas.

---

# Parte 1 · Teoría

## 1. El modelo de capas

Para dar estructura al diseño de los protocolos de red, se organizan **por capas**: cada una resuelve un problema y se apoya en la de debajo sin saber cómo funciona por dentro. En internet la pila tiene **cinco**.

| Capa | Qué hace | Unidad | Dirección | Alcance | Ejemplos |
|---|---|---|---|---|---|
| **Aplicación** | Produce y consume los datos | mensaje | nombres (URL) | extremo a extremo | HTTP, SSH, DNS, SMTP |
| **Transporte** | Lleva datos entre **procesos**; opcionalmente añade fiabilidad | segmento (TCP) / datagrama (UDP) | **puerto** | extremo a extremo | TCP, UDP |
| **Red** | Lleva paquetes entre **máquinas**, decidiendo el siguiente salto | datagrama | **IP** | extremo a extremo | IP |
| **Enlace** | Mueve la trama al **siguiente salto** | trama | **MAC** | **un salto** | Ethernet, wifi |
| **Física** | Mueve **bits** por el medio | bit | — | un salto | cobre, fibra, radio |

«Datagrama» aparece en dos capas: el de red (IP) y el de usuario (UDP). UDP se llama así porque apenas añade nada a la filosofía de IP: es casi IP con puertos. TCP habla de **segmentos** porque trocea un flujo continuo de bytes. En la práctica casi todo el mundo dice «paquete» para todo.

### Las ideas que sostienen el modelo

**Encapsulación.** Al bajar, cada capa envuelve lo que le da la de arriba con su propia cabecera. Al subir, se desenvuelve en orden inverso. Muñecas rusas.

**Cada capa solo abre su propio sobre.** Red entiende IPs y nunca toca MACs; enlace entiende MACs y nunca lee IPs. Esa ignorancia deliberada es lo que permite cambiar wifi por fibra sin tocar SSH.

**Cada capa habla con su homóloga del otro lado.** Transporte con transporte, red con red, enlace con enlace. Lo que cambia es el alcance de esa conversación: las tres de arriba, de punta a punta; enlace y física, solo hasta el vecino.

**No todos suben las cinco capas.** Los extremos sí. Los **routers intermedios suben solo hasta red** y vuelven a bajar: nunca ven la conexión TCP, que es un acuerdo privado entre los dos extremos.

**El reloj de arena.** En aplicación hay cientos de protocolos; en transporte, dos; en red, **uno solo**: IP. Debajo vuelve la variedad. Todo el mundo se pone de acuerdo en una sola cosa, y por encima y por debajo cada uno hace lo que quiere.

## 2. El recorrido de un paquete

**En el origen**

1. La aplicación quiere enviar algo a una IP.
2. Transporte prepara el segmento y lo entrega a red con esa IP. No le pasa el puerto: red no lo mira.
3. Red escribe la IP de destino, consulta la **tabla de rutas** y decide el vecino al que dárselo.
4. Enlace averigua la MAC de ese vecino y construye la trama.
5. Sale por el medio físico.

**En cada router**

1. Enlace compara la MAC de destino con la suya, verifica el *checksum* y quita la envoltura. La trama muere aquí.
2. Red compara la IP de destino: no es suya. Decrementa el **TTL**, consulta su tabla y decide su siguiente vecino.
3. Enlace construye una **trama nueva**, con MACs distintas, para el siguiente tramo.

**En el destino**

1. Enlace compara la MAC y sube el datagrama.
2. Red compara la IP: **es suya**. Sube a transporte.
3. Transporte lee el puerto, reordena si hace falta y entrega al proceso.

Con diez routers en medio, red actúa once veces con el mismo dato; enlace, diez veces con datos nuevos cada vez.

### Lo que cambia y lo que no

- **La IP viaja intacta de punta a punta.** De la cabecera IP solo cambia el TTL, que baja de uno en uno (y la IP de origen si hay NAT, §7).
- **La trama se destruye y se rehace en cada salto.**
- **Nadie conoce el camino completo.** Ni el origen ni ningún router. Cada nodo decide solo el siguiente salto, cuando el paquete ya está en sus manos. La ruta emerge de muchas decisiones locales encadenadas.

### Dos tablas, dos preguntas

| Tabla | Comando | Pregunta que responde | Responde con | Capa |
|---|---|---|---|---|
| Tabla de rutas | `ip r` | ¿A quién le paso el paquete? | Una **IP** (la del siguiente salto) | Red |
| Tabla de vecinos (ARP) | `ip neigh` | ¿Qué MAC tiene ese vecino? | Una **MAC** | Enlace |

En la tabla de rutas **no hay MACs ni caminos completos**: solo «si el destino está en mi subred, directo; si no, al gateway». Enlace no decide nada: entrega a la MAC que le indica red. Es un ejecutor.

**Forwarding frente a routing.** *Forwarding* es consultar la tabla y sacar el paquete por la interfaz que toca: microsegundos, por cada paquete. *Routing* es el proceso de fondo que **construye** esa tabla mediante protocolos de enrutado: lento, continuo, ocurre aunque no circule nada.

## 3. MAC, IP y ARP

**La MAC va con la máquina; la IP va con el sitio donde está.**

- **MAC:** 48 bits grabados de fábrica en la tarjeta. Los primeros 24 identifican al fabricante (registro del IEEE); los otros 24 los asigna él.
- **IP:** la da la red donde te conectas, y cambia si te mueves.

**La MAC no es enrutable.** Es un número de serie, no una dirección postal: no hay forma de deducir un camino a partir de ella. La IP sí lo es porque está agrupada en bloques (`89.58.44.0/22` son mil direcciones en una sola línea de tabla). Si internet funcionara por MAC, cada router necesitaría una tabla con todos los dispositivos del planeta. **MAC para el último metro, IP para todo lo demás.**

### ARP: de IP a MAC

Se resuelve **después** de que red decida el siguiente salto y **antes** de construir la trama.

1. ¿Está la MAC en la caché de vecinos? → se usa al instante.
2. ¿No está? → se emite una petición ARP a `ff:ff:ff:ff:ff:ff` (broadcast de enlace) preguntando quién tiene esa IP. Todos la reciben; solo el interesado contesta con su MAC. El paquete **espera** mientras tanto.

Solo se resuelve la MAC del **siguiente salto**, nunca la del destino final.

| Estado en `ip neigh` | Significado |
|---|---|
| `REACHABLE` | Confirmado hace poco (unos 30 s). Se usa sin preguntar |
| `STALE` | Caducó el plazo pero sigue en caché. Se revalida al usarlo |
| `FAILED` | Se preguntó y nadie respondió |

La caché caduca a propósito: si cambia una tarjeta o se reasigna una IP, el sistema tiene que enterarse.

## 4. Direccionamiento IPv4 y subredes

### Dirección, prefijo y máscara

Una IPv4 son 32 bits, escritos como cuatro números de 0 a 255 (octetos). El **prefijo** (`/24`, `/22`) dice cuántos bits, contando desde la izquierda, identifican **la red**; el resto identifican **la máquina** dentro de ella. La **máscara** es lo mismo escrito como dirección: `/24` = `255.255.255.0`. Esta notación con barra es **CIDR**.

La máscara es una **frontera**: la máquina la usa para decidir en un instante «este destino es vecino, se lo doy directo» o «es de fuera, al gateway».

### Calcular una subred

Cuatro valores, siempre en este orden:

1. **Bits de host** = 32 − prefijo.
2. **Dirección de red:** bits de host todos a **cero**. No asignable.
3. **Broadcast:** bits de host todos a **uno**. No asignable.
4. **Hosts** = 2^(bits de host) − 2, por los dos extremos reservados.

El rango utilizable va de red + 1 a broadcast − 1. Cuando el prefijo no es múltiplo de 8, el corte cae **dentro** de un octeto y hay que pasar ese octeto a binario (caso del `/22` del VPS, en Ejemplos). El gateway suele ser la primera o la última dirección utilizable.

### La máscara no dice si tu IP cambia

- **La máscara** describe el tamaño del rango.
- **`dynamic`** en la salida de `ip a` indica que la dirección vino por DHCP y puede cambiar.

El VPS está en un `/22` y su IP es fija; el portátil está en un `/24` y la suya es dinámica. Lo que sí dice la máscara es **dentro de qué margen** puede cambiar.

### Quién reparte las direcciones

| Nivel | Quién | Qué hace |
|---|---|---|
| Cima | **IANA** | Administra todo el espacio IPv4 y entrega bloques enormes a los RIR |
| Regional | **RIR** (cinco; en Europa, **RIPE NCC**) | Trocea sus bloques y los asigna a operadores |
| Operador | ISP, proveedores como Netcup | Divide su bloque en segmentos para sus clientes |
| Cliente | Tú | Recibe una dirección del bloque de su proveedor |

Cada nivel trocea **alargando el prefijo**: **cada bit que se añade parte el bloque en dos**. Un `/16` (65.536 direcciones) da 4 bloques `/18`, o 64 `/22`, o 256 `/24`.

### Direcciones privadas

Rangos reservados para redes internas (RFC 1918): `10.0.0.0/8`, `172.16.0.0/12` y `192.168.0.0/16`. **No son enrutables en internet**: ningún router público tiene ruta hacia ellas, porque el mismo rango existe repetido en millones de casas. No son secretas: son inalcanzables desde fuera. La red de casa (`192.168.1.0/24`) y las redes de Docker (`172.17.0.0/16`) usan estos rangos. Para salir a internet necesitan **NAT** (§7).

## 5. Broadcast, red local y DHCP

### Broadcast

La dirección «para todos los de esta subred». Se usa **cuando no sabes con quién hablar**; si lo supieras, te dirigirías a él. Sus dos usos reales son problemas de arranque:

- **ARP:** «¿quién tiene esta IP?».
- **DHCP:** la máquina no tiene IP ni sabe quién es el router.

**El coste:** un broadcast lo procesan **todas** las máquinas de la subred. Con 254 es despreciable; con los 65.534 de un `/16` se convierte en problema (*broadcast storm*). Los routers **no reenvían broadcasts nunca**, así que **cada subred es una frontera que los acota**: es una razón práctica para dividir en subredes. Casi todos los servidores modernos ignoran el ping a broadcast, como protección contra ataques de amplificación.

### Red local no significa red privada

**Red local = las máquinas a las que llegas directamente, sin pasar por un router.** No dice nada de IPs privadas ni de NAT.

| | Casa | VPS |
|---|---|---|
| Red local | `192.168.1.0/24` | `89.58.44.0/22` |
| IPs | Privadas | **Públicas** |
| NAT | Sí | No |

En casa las tres cosas vienen juntas, y de ahí sale la idea equivocada de que «local» implica «privado y detrás de NAT». Lo raro es la casa: todo centro de datos está hecho de segmentos locales con IPs públicas.

### Switch y router

| | Switch | Router |
|---|---|---|
| Conecta | Dentro de la subred | Entre subredes |
| Mira | **MAC** | **IP** |
| Capa | Enlace | Red |

Cuando el VPS habla con un vecino de su `/22`, el tráfico pasa por los switches y **nunca toca el router**. En un centro de datos hay un switch por rack, interconectados en un segmento plano. Y el gateway puede no ser un solo aparato: con **VRRP**, dos routers físicos comparten una IP y una MAC virtuales (prefijo `00:00:5e`) por redundancia.

### DHCP

Entrega automáticamente **cuatro cosas** a una máquina que se conecta: **IP, máscara, gateway y servidores DNS**, con un tiempo de préstamo (*lease*) que la máquina renueva.

**La paradoja de arranque:** el cliente no tiene IP, no sabe la máscara ni quién es el router, y aun así tiene que pedir. Se resuelve con dos direcciones especiales: **origen `0.0.0.0`** («todavía no tengo dirección») y **destino `255.255.255.255`** (broadcast total).

| Paso | Qué ocurre |
|---|---|
| **Discover** | El cliente pregunta por broadcast si hay algún servidor DHCP. UDP, del puerto 68 al 67 |
| **Offer** | Un servidor ofrece una IP con su máscara, gateway, DNS y tiempo de préstamo |
| **Request** | El cliente pide la oferta elegida, también por broadcast, para que otros servidores sepan que no se quedó con la suya |
| **ACK** | El servidor confirma. Desde ahí la máquina usa esa configuración |

**DHCP necesita enlace primero.** Viaja dentro de una trama: antes hace falta conexión física (el cable, o asociarse a la wifi, que es radio y no tiene nada de IP). Cambia el medio, cambia cómo se conecta, y DHCP sigue siendo idéntico: las capas son independientes.

## 6. Puertos y sockets

### Multiplexación y demultiplexación

- **Multiplexar** (emisor): recoger los datos de **varios sockets**, ponerles su cabecera con el puerto de origen y meterlos todos por el mismo canal hacia la capa de red.
- **Demultiplexar** (receptor): usar esa información para entregar cada segmento al **socket correcto**.

Multiplexar **obliga** a etiquetar: sin el remitente en el sobre, al llegar no habría forma de repartir.

### Puerto no es socket

| | Puerto | Socket |
|---|---|---|
| Qué es | Un número de 16 bits en la cabecera | Una estructura del sistema operativo |
| Tiene | Nada: es un dato | Estado, buffers, descriptor de fichero |

El puerto es la **etiqueta**; el socket, **la cosa**. Un proceso puede tener varios sockets en el mismo puerto (`systemd-resolved` tenía cuatro en el 53), y cien clientes en el 22 son cien sockets y un solo puerto.

### Cómo se identifica cada socket

| Protocolo | Datos necesarios para repartir |
|---|---|
| **UDP** | **Dos:** IP y puerto de destino |
| **TCP** | **Cuatro:** IP y puerto de origen, IP y puerto de destino |

**Por qué.** TCP mantiene estado **por interlocutor** (números de secuencia, qué se ha confirmado, qué falta), y ese estado solo tiene sentido dentro de una conversación concreta. Necesita un socket por conversación y, para repartir, mirar de dónde viene cada segmento. UDP no guarda nada: cada datagrama se basta a sí mismo, así que mil clientes escribiendo al mismo puerto UDP caen en **el mismo socket**; si la aplicación quiere distinguirlos, mira ella la IP de origen.

### Servidor y cliente no son simétricos

- **Servidor:** puerto fijo y conocido de antemano (22 SSH, 80 HTTP, 443 HTTPS, 5432 PostgreSQL, 8069 Odoo).
- **Cliente:** puerto **efímero**, asignado al vuelo y liberado al cerrar.

| Rango | Qué son |
|---|---|
| 0–1023 | **Bien conocidos**, reservados por IANA. En Linux, **solo root puede escuchar en ellos** |
| 1024–65535 | Libres: puertos efímeros y servicios propios |

Por eso nginx arranca como root para coger el 80 y luego baja de privilegios, y Odoo usa el 8069. Mover el PostgreSQL de Docker al 5433 fue elegir un puerto libre por encima de 1023.

### `LISTEN` y `ESTAB`

El socket que escucha **no se convierte en la conexión**: por cada cliente el kernel crea uno nuevo en estado `ESTAB`, y el original sigue en `LISTEN`. Con tres sesiones SSH hay cuatro sockets en el 22. Por eso caben cien clientes en un puerto, y por eso reiniciar `sshd` no corta las sesiones abiertas.

Reparto de lo que llega:

1. Se busca coincidencia exacta de los cuatro datos → socket `ESTAB`.
2. Si no hay, se mira si algún socket en `LISTEN` encaja → ahí caen las conexiones nuevas.

Que el socket en `LISTEN` acepte de cualquier IP es decisión del servicio (`sshd`), no del kernel. Es lo que permite que los bots prueben el 22 desde el primer día.

Un servicio solo necesita puerto si habla por TCP o UDP: `cron` o `systemd-logind` no tienen. La comunicación local también puede ir por **sockets Unix**, ficheros en disco sin puerto ni red.

## 7. NAT

**Qué resuelve:** varios dispositivos con IP privada compartiendo **una sola IP pública**, la del router.

| Sentido | Campos que reescribe el router |
|---|---|
| **Al salir** | IP de origen (privada → pública) y **puerto de origen** (→ uno elegido por el router) |
| **Al entrar** | IP y puerto de **destino**, deshaciendo el cambio |

**Por qué también el puerto.** Dos dispositivos pueden elegir el mismo puerto efímero. Si el router solo cambiara la IP, dos filas de su tabla serían idénticas y no sabría a quién devolver cada respuesta. Reescribir el puerto garantiza que cada fila es única. Al volver, el router mira el **puerto de destino**, busca la fila y restaura IP y puerto originales.

No es solo memoria: es **traducción**. El paquete que sale del router ya no es el que entró. Un router normal mira la IP y decide por dónde sale sin tocar nada salvo el TTL.

**Sobre el nombre:** lo que hace un router doméstico es, en rigor, **PAT** (*Port Address Translation*). El NAT original traducía direcciones una a una; «NAT» se quedó como nombre genérico.

### Por qué el NAT rompe el modelo de capas

Un nodo intermedio debería subir solo hasta red. El NAT:

- **Lee y modifica puertos**, que son de transporte.
- **Modifica la IP de origen**, que se supone intacta de punta a punta.
- **Sigue los flags TCP** para saber cuándo crear una fila (ve un `SYN`) y cuándo borrarla (ve un `FIN` o se agota el tiempo): sigue el estado de una conexión que en teoría solo es asunto de los extremos.

### Port forwarding

Con NAT normal la tabla se llena sola, pero **solo hacia fuera**: cada fila nace de una petición interna. Un paquete entrante sin fila no tiene destinatario y se descarta. El *port forwarding* añade una fila **permanente, escrita a mano**, en sentido contrario: «lo que llegue al puerto X, dáselo a este dispositivo». Es la única forma de recibir conexiones no solicitadas detrás de un NAT.

### Por qué el VPS recibe conexiones y el portátil no

El VPS tiene IP pública directa, sin NAT delante: es alcanzable desde el primer segundo. El portátil tiene una IP privada no enrutable; desde fuera solo se alcanza la IP pública del router, que sin una fila en su tabla no sabe a quién entregar lo que llega.

## 8. TCP y UDP

### Qué ofrece cada uno

| | UDP | TCP |
|---|---|---|
| Conexión | No: cada datagrama va suelto | Sí: se establece con el handshake |
| Garantías | Ninguna: puede perderse, duplicarse o llegar desordenado | Todo llega, una vez y en orden |
| Estado | Ninguno | Por interlocutor: secuencia, confirmaciones, retransmisiones |
| Coste | Rápido: no espera nada | Más lento **porque** garantiza: espera confirmaciones y retransmite |
| Uso típico | Pregunta y respuesta cortas (DNS), tiempo real | SSH, HTTP, PostgreSQL |

IP, por debajo de ambos, es *best effort*: sin conexión ni promesas. Toda la fiabilidad de TCP la construyen los extremos encima de una red que no garantiza nada.

### Por qué existe el handshake

**No es cortesía: es acordar los números de secuencia** con los que cada lado va a contar los bytes que envía. Sin ese punto de partida común no hay forma de detectar qué falta ni de reordenar lo que llega desordenado.

| Paso | Flag en `tcpdump` | Qué hace |
|---|---|---|
| 1 | `[S]` SYN | El cliente propone su número inicial |
| 2 | `[S.]` SYN-ACK | El servidor confirma el del cliente (+1) y propone el suyo |
| 3 | `[.]` ACK | El cliente confirma el del servidor (+1) |

El ACK significa «he recibido hasta aquí; el siguiente byte que espero es este». Los números iniciales son **aleatorios a propósito**: si fueran predecibles, alguien podría inyectar paquetes falsos en una conexión ajena.

### Los flags que se ven en una captura

| Flag | Significa |
|---|---|
| `[S]` | SYN: abrir |
| `[S.]` | SYN-ACK (el punto es el ACK) |
| `[.]` | Solo ACK |
| `[P.]` | PUSH + ACK: datos reales |
| `[F.]` | FIN: cierre ordenado |
| `[R]` | RST: cierre abrupto |

El cierre son **cuatro pasos**, no tres: una conexión TCP son dos flujos independientes y cada lado cierra el suyo por separado.

Quedan fuera del bloque la fiabilidad por dentro (retransmisiones, control de flujo) y el control de congestión: importan al diseñar protocolos, no al operar un servidor.

## 9. Retardos y `ping`

Cada nodo añade cuatro retardos: **procesamiento, cola, transmisión y propagación**. El de cola es el más **variable** (no siempre el mayor) y el único que depende de lo que hagan los demás.

`ping` mide el **RTT** (ida y vuelta) y da el total, no la descomposición. La vuelta puede ir por otra ruta: RTT ÷ 2 es una aproximación.

| Valor de `ping` | Lectura |
|---|---|
| **min** | El suelo irreducible: propagación y transmisión. Física |
| **avg − min** | Retardo de cola medio. Pocos ms → ruta descargada |
| **max** | Un pico. Puede ser la wifi propia, no internet |
| **mdev** | Variación (*jitter*). Bajo con un max alto = pico aislado, no patrón |

Los routers contestan a ICMP con prioridad baja: un salto lento en `traceroute` puede estar perfectamente sano si los siguientes van bien.

## 10. Conmutación de circuitos y de paquetes

| | Circuitos | Paquetes |
|---|---|---|
| Reserva | Capacidad fija antes de transmitir | Ninguna |
| Fases | Establecimiento (puede **bloquearse**), transferencia, liberación | Se envía sin más |
| Reparto del enlace | FDM (bandas de frecuencia) o TDM (turnos de tiempo) | Bajo demanda |
| Si no hay tráfico | La capacidad reservada se desperdicia | Otros la usan |
| Cuando hay saturación | No admite nuevas llamadas | Admite todo y empeora la calidad (colas) |

**Circuitos cambia eficiencia por garantía; paquetes cambia garantía por eficiencia.** Internet eligió paquetes porque el tráfico de datos va a ráfagas y reservar para el pico desperdicia casi todo el tiempo. Quedan circuitos en la telefonía clásica (facturación por minutos, tono de marcado, señal de ocupado) y en líneas dedicadas.

## 11. Estructura de internet

- Los ISP de acceso son clientes de ISP regionales, que son clientes de los **tier-1**. **El de abajo paga al de arriba por el tránsito.** Los tier-1 no pagan a nadie: hacen *peering* entre iguales.
- Los **IXP** son puntos físicos donde muchas redes se interconectan directamente.
- Los grandes proveedores de contenido tienen **redes privadas globales**, colocan servidores dentro de los IXP y hacen *peering* gratuito con ISP pequeños, saltándose escalones. Les interesa por coste y, sobre todo, por **control sobre la entrega** (ruta, latencia, cercanía al usuario). La pirámide se ha aplanado.

## 12. Ataques y colas

Un DDoS lleva al extremo el retardo de cola, pero la cola es el síntoma, no siempre el mecanismo.

| Tipo | Qué agota | ¿Llena la cola de red? |
|---|---|---|
| **Volumétrico** | El ancho de banda. Suele usar amplificación: consulta pequeña con IP de origen falsificada, respuesta enorme hacia la víctima | Sí |
| **De protocolo** | Una tabla en memoria. El *SYN flood* envía miles de SYN sin completar el handshake | No |
| **De aplicación** | CPU o base de datos, con peticiones legítimas pero caras | No |

Un resolutor DNS abierto a internet es munición para amplificación; Ubuntu trae el suyo escuchando solo en loopback.

## 13. Analogías de referencia

| Concepto | Analogía |
|---|---|
| Encapsulación | Muñecas rusas: cada capa envuelve el sobre anterior |
| Router intermedio | El cartero de cada oficina: abre el sobre exterior, lee la dirección y lo vuelve a cerrar en otro sobre |
| Red frente a enlace | Planificar Madrid → Núremberg en el mapa de Europa frente a conducir el tramo de la M-30 a la A-2 |
| IP | La dirección del edificio |
| MAC | El número de serie del buzón: identifica, pero no dice dónde está |
| Máscara | Qué parte de la dirección es el barrio y qué parte el portal |
| Puerto | La extensión telefónica |
| Socket | La llamada en curso: muchas llamadas por la misma extensión |
| Multiplexar | Una oficina con una sola saca de correo saliente; cada carta lleva su remitente |
| NAT | El conserje de un bloque con una sola dirección: apunta en una libreta qué vecino pidió qué paquete |
| Port forwarding | Una nota fija en la libreta: «lo que llegue para el buzón 8069, al 2.º B» |
| UDP | Una postal: va suelta y sin acuse |
| TCP | Correo certificado con acuse de recibo |
| Handshake | La llamada previa para confirmar que hay alguien y acordar cómo numerar las cartas |
| Conmutación de circuitos | Una llamada telefónica clásica: la línea es tuya aunque calles |

---

# Parte 2 · Ejemplos

## Las tablas del VPS, anotadas

En el VPS:

```
$ ip r
default via 89.58.44.1 dev eth0 proto static
89.58.44.0/22 dev eth0 proto kernel scope link src 89.58.45.111
```

| Fragmento | Lectura |
|---|---|
| `default via 89.58.44.1` | Todo lo que no encaje en otra línea va al gateway de Netcup |
| `proto static` | Configurada a mano (netplan), no aprendida |
| `89.58.44.0/22 … scope link` | A los vecinos de la subred se llega **directamente**, sin gateway |
| `proto kernel` | La dedujo el kernel al configurar la interfaz |
| `src 89.58.45.111` | La IP propia que se pone como origen |

```
$ ip neigh
89.58.44.2 dev eth0 lladdr bc:0f:fe:37:fb:a2 STALE
89.58.44.3 dev eth0 lladdr bc:0f:fe:33:fc:e2 STALE
89.58.44.1 dev eth0 lladdr 00:00:5e:00:01:01 REACHABLE
2a03:4000:67::3 dev eth0 FAILED
fe80::be0f:fe00:c437:fba2 dev eth0 lladdr bc:0f:fe:37:fb:a2 router STALE
```

- El gateway está `REACHABLE`: se usa constantemente. Su MAC `00:00:5e:00:01:01` es la virtual de **VRRP**: dos routers físicos detrás de una sola dirección.
- `.2` y `.3` son vecinos de la subred; sus MACs coinciden con las entradas IPv6 marcadas `router`: son routers de Netcup.
- Las entradas IPv6 `FAILED` encajan con que `ip -6 r` no tenga ruta por defecto: IPv6 está sin configurar en el VPS.
- La tabla solo conoce un puñado de máquinas: enlace no sabe nada más allá del vecino.

## Portátil frente a VPS

| | Portátil | VPS |
|---|---|---|
| Interfaz | `enp5s0` (cable) | `eth0` |
| Dirección | `192.168.1.74/24`, privada, `dynamic` | `89.58.45.111/22`, pública, fija |
| Ruta por defecto | Al router de casa | A `89.58.44.1` |
| Alcanzable desde internet | No (NAT) | Sí |

## Dos subredes calculadas

**`192.168.1.74/24` (portátil):** 8 bits de host, 2⁸ = 256 direcciones.

```
192.168.1.0     ← red, no asignable
192.168.1.1     ← primera utilizable
   ...             254 hosts
192.168.1.254   ← última utilizable
192.168.1.255   ← broadcast, no asignable
```

**`89.58.45.111/22` (VPS):** el corte cae dentro del tercer octeto. `45` en binario es `00101101`; los 6 primeros bits (22 − 16) son de red: `001011`, que con los dos últimos a cero da `44` y a uno da `47`.

| | |
|---|---|
| Bits de host | 32 − 22 = **10** |
| Red | `89.58.44.0` |
| Broadcast | `89.58.47.255` |
| Rango utilizable | `89.58.44.1` – `89.58.47.254` |
| Hosts | 2¹⁰ − 2 = **1022** |
| ¿`89.58.48.1` está dentro? | No: el tercer octeto solo abarca 44–47 |

**La decisión que toma el VPS:** `89.58.44.2` está dentro de `89.58.44.0/22` → entrega directa por enlace, sin router. `8.8.8.8` no lo está → al gateway.

## Ping a broadcast en el VPS

```
$ ping -c 3 -b 89.58.47.255
64 bytes from 89.58.44.2: icmp_seq=1 ttl=64 time=0.506 ms
64 bytes from 89.58.44.3: icmp_seq=1 ttl=64 time=0.530 ms
3 packets transmitted, 3 received, +2 duplicates, 0% packet loss
```

- **`+2 duplicates`:** `ping` espera un interlocutor y recibe varios. Es la prueba de que el broadcast llegó a toda la subred.
- **Solo contestan dos de 1022:** los routers de Netcup. Los servidores modernos ignoran el ping a broadcast.
- **`ttl=64` sin decrementar y 0,5 ms:** cero saltos, entrega directa por enlace. Compárese con los casi 40 ms hasta el portátil.

## `ping` del portátil al VPS

```
rtt min/avg/max/mdev = 37.979/40.409/64.933/5.128 ms
```

El suelo es de 38 ms (Madrid → Núremberg, física). La media solo está 2,4 ms por encima: ruta descargada. El máximo de 65 ms con `mdev` bajo es un pico aislado. Antes de culpar a la red, repetir por cable.

## Dos sesiones SSH en el mismo puerto

En el VPS, con dos sesiones abiertas desde el portátil:

```
$ sudo ss -tnp | grep :22
ESTAB 0 0    89.58.45.111:22  83.56.140.163:54364  users:(("sshd",pid=75419,fd=4),...)
ESTAB 0 304  89.58.45.111:22  83.56.140.163:54842  users:(("sshd",pid=75327,fd=4),...)
```

Comparten tres de los cuatro datos. Solo los distingue el **puerto de origen** (54364 y 54842): ahí está, medida, la razón de que TCP necesite los cuatro. Los 304 bytes de `Send-Q` son datos en vuelo pendientes de confirmar. La IP de origen es la **pública del router de casa**, no la del portátil: el NAT ya actuó.

## La salida de `ss`, columna a columna

| Lo que ves | Qué significa |
|---|---|
| `0.0.0.0` en *Local* | Escucha por **todas** las interfaces: expuesto a internet |
| `127.0.0.x` en *Local* | Solo loopback: inalcanzable desde fuera |
| `[::]` en *Local* | Lo mismo que `0.0.0.0`, en IPv6 |
| `0.0.0.0:*` en *Peer* | Acepta de cualquier IP y puerto |
| `LISTEN` | Esperando conexiones |
| `UNCONN` | Normal en UDP: no hay conexión |
| `Send-Q` en `LISTEN` | El **backlog** máximo de conexiones pendientes, no una cola de envío. Es lo que agota un *SYN flood* |
| `Send-Q` en `ESTAB` | Bytes enviados aún sin confirmar |
| Mismo PID, `fd` distintos | Un proceso con varios sockets (`systemd-resolved` con cuatro en el 53) |

*Local* siempre es la máquina donde ejecutas el comando: en el portátil, *Local* y *Peer* salen al revés. Cuando se despliegue Odoo, la misma salida debe mostrar `127.0.0.1:8069` (solo nginx habla con él) y `0.0.0.0:80` y `:443` para nginx.

## La tabla del NAT de casa

Dos dispositivos que eligen por casualidad el mismo puerto efímero:

| Puerto público | Dispositivo interno | Su puerto |
|---|---|---|
| 40001 | `192.168.1.74` | 51234 |
| 40002 | `192.168.1.30` | 51234 |

Sin reescribir el puerto, las dos filas serían idénticas. La respuesta que llega al 40002 vuelve al `.30`.

## El handshake capturado en el VPS

Terminal 1, en el VPS, deja la captura corriendo. Terminal 2, en el portátil, abre una sesión nueva con `ssh vps`.

```
In   80.29.31.121.60352 > 89.58.45.111.22: Flags [S],  seq 2648884223
Out  89.58.45.111.22 > 80.29.31.121.60352: Flags [S.], seq 2481111623, ack 2648884224
In   80.29.31.121.60352 > 89.58.45.111.22: Flags [.],  ack 1
```

- El ACK del servidor (`2648884224`) es el SYN del cliente **más uno**.
- El tercer paquete dice `ack 1` porque, tras el primero, `tcpdump` muestra números **relativos** al inicio de la conexión.
- El origen `80.29.31.121` es la IP pública del router de casa (otra conexión, otra IP pública distinta a la de `ss` arriba: la que asigna la operadora no es fija).

Justo después, TCP ha terminado y empieza SSH:

```
length 22: SSH: SSH-2.0-OpenSSH_10.5
length 43: SSH: SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.19
```

Ambos extremos anuncian su versión **en claro, antes de cifrar nada**. Es lo que un atacante usa para buscar vulnerabilidades conocidas.

## El camino de un paquete del portátil al VPS

| Parada | IP origen | IP destino | Puerto origen | MAC destino |
|---|---|---|---|---|
| **Portátil** | Privada del portátil | VPS | Efímero del portátil | Router de casa |
| **Router de casa** | **Pública del router** | VPS | **Del router (NAT)** | Siguiente router |
| **Router intermedio** | Pública del router | VPS | Del router | Siguiente salto |
| **VPS** | Pública del router | VPS | Del router | — (ya llegó) |

- **La IP de destino no cambia nunca:** es la dirección final.
- **La MAC de destino cambia en cada fila:** es la del dispositivo del siguiente salto; la trama se rehace en cada tramo.
- **La IP y el puerto de origen cambian una sola vez, en el router de casa, y a la vez:** el VPS tiene que poder contestar, y no puede contestar a una dirección no enrutable.

## Errores vistos

| Lo que se ve | Causa | Arreglo |
|---|---|---|
| `sudo: tcpdump: command not found` con el prompt sin `@backend-lab` | Se estaba en el portátil, no en el VPS | Mirar el prompt antes de ejecutar; entrar con `ssh vps` |
| `sudo: tcpdump: command not found` ya en el VPS | La imagen de Netcup es mínima y no lo trae | `sudo apt install tcpdump`; comprobar con `which tcpdump` |
| `ping vps` no encuentra el nombre | El alias de `~/.ssh/config` solo lo leen `ssh`, `scp`, `rsync` y `git` | Usar la IP |
| Columna *Process* vacía en `ss -tulpn` | Sin `sudo` no se ven procesos de otros usuarios | `sudo ss -tulpn` |
| La captura se llena de líneas sin parar | El filtro incluye los ACK de la propia sesión SSH | Filtrar solo SYN (ver Comandos) |

## Confusiones vistas

| Confusión | Corrección |
|---|---|
| Enlace decide a qué nodo mandar el paquete | Lo decide red con la tabla de rutas; enlace entrega a la MAC que le dicen |
| La tabla de rutas guarda las MACs hasta el destino | No hay MACs ni caminos: solo el siguiente salto, como IP |
| ARP averigua la MAC del destino final | Solo la del siguiente salto |
| Red local implica IPs privadas y NAT | Red local es lo alcanzable sin router; el VPS tiene red local pública y sin NAT |
| Una máscara amplia significa que la IP cambia | Que cambie lo indica `dynamic` (DHCP); la máscara solo da el margen |
| TCP se distingue de UDP en que trocea | Los dos se trocean; TCP es más lento porque **garantiza** |
| El socket en `LISTEN` pasa a ser la conexión | El kernel crea uno nuevo por conexión; el original sigue escuchando |
| El NAT solo cambia la IP | Cambia también el puerto de origen, para que cada fila sea única |
| El handshake es cortesía | Es acordar los números de secuencia |
| RTT ÷ 2 es el tiempo de ida | Aproximación: la vuelta puede ir por otra ruta |

## Preguntas frecuentes y cómo responderlas

| Pregunta | Comando (dónde) |
|---|---|
| ¿Qué IP tiene esta máquina y es fija? | `ip a`: línea `inet` de la interfaz de salida; `dynamic` = DHCP (portátil o VPS) |
| ¿Por dónde sale lo que no es para mi subred? | `ip r`, línea `default` |
| ¿Este destino está en mi subred o va al gateway? | `ip r` y calcular la subred; para confirmar, `traceroute -n IP`: un solo salto = vecino |
| ¿Qué MAC tiene el gateway y está respondiendo? | `ip neigh`: `REACHABLE` |
| ¿Qué está expuesto a internet en el VPS? | `sudo ss -tulpn`: lo que escucha en `0.0.0.0` o `[::]` |
| ¿Cuántas sesiones SSH hay abiertas? | `sudo ss -tnp \| grep :22` (VPS) |
| ¿La conexión llega a abrirse? | `sudo tcpdump -n -i any 'tcp port PUERTO and tcp[tcpflags] & tcp-syn != 0'` (VPS) y provocar la conexión desde otra terminal |
| ¿Hay bots probando el puerto 22? | La misma captura de SYN, dejada unos minutos sin conectarse uno mismo |
| ¿La lentitud es de la red o de mi wifi? | `ping -c 50 IP` y comparar min, avg y max; repetir por cable |
| ¿Odoo quedará expuesto al desplegarlo? | `sudo ss -tlnp`: debe verse `127.0.0.1:8069`, no `0.0.0.0:8069` |

---

# Parte 3 · Comandos útiles del bloque

## Interfaces, rutas y vecinos

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ip a` | `a` (*address*): interfaces y sus direcciones. `inet` = IPv4, `inet6` = IPv6, `link/ether` = MAC propia | Saber la IP de una máquina: interfaz de salida (`eth0`, `enp5s0`), `scope global`. `lo` es loopback; las `fe80::` (`scope link`) se ignoran. Las `veth…`, `br-…` y `docker0` son de Docker |
| `ip r` | `r` (*route*): tabla de rutas | Primer paso si una máquina no llega a algo: ¿hay ruta `default`? Sin ella, solo se llega a la subred |
| `ip -6 r` | `-6`: solo la tabla IPv6 | En el VPS no hay ruta por defecto IPv6: IPv6 sin configurar (revisar al tocar netplan) |
| `ip neigh` | Caché ARP: IP → MAC de los vecinos, con su estado | Ver si el gateway responde (`REACHABLE`); un vecino en `FAILED` no contesta a nivel de enlace |
| `sudo ip neigh flush all` | Vacía la caché ARP | Forzar que se vuelvan a preguntar las MACs y ver cómo se repuebla. No rompe nada: se rellena sola al siguiente paquete |
| `ip link show eth0` | Datos de enlace de una interfaz, incluida la MAC | Cuando solo interesa la capa de enlace |

## Puertos y sockets

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo ss -tulpn` | Quién escucha y dónde: `-t` TCP, `-u` UDP, `-l` solo los que escuchan, `-p` proceso, `-n` números en vez de nombres | Inventario de lo expuesto en el VPS; foto del «antes» de desplegar Odoo. Sin `sudo`, la columna *Process* sale vacía |
| `sudo ss -tnp \| grep :22` | Conexiones TCP **establecidas** (sin `-l`) en el puerto 22; `grep` filtra las líneas | Ver sesiones SSH abiertas y desde qué IP. `Send-Q` aquí son bytes en vuelo, no el backlog |

## Conectividad

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ping -c N IP` | Paquetes ICMP de ida y vuelta; `-c` limita el número | Medir RTT y pérdidas. Sin `-c` no para: `Ctrl-C`. No usar el alias `vps`: no lo entiende |
| `ping -c 3 -b BROADCAST` | `-b` permite hacer ping a una dirección de broadcast | Comprobar quién responde en la subred. La mayoría de servidores lo ignoran: que contesten pocos es normal |
| `traceroute -n IP` | Lista de routers hasta un destino; `-n` sin resolver nombres | Ver dónde se pierde o se frena el tráfico. Un salto lento puede estar sano (ICMP con baja prioridad); una línea con varias IPs es balanceo de carga. No viene instalado en el VPS |

## Captura de tráfico

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo tcpdump -n -i any 'tcp port 22 and tcp[tcpflags] & (tcp-syn\|tcp-ack) != 0'` | Captura TCP del puerto 22 con SYN o ACK. `sudo`: leer tráfico crudo es privilegiado; `-n` sin resolver nombres ni puertos; `-i any` todas las interfaces; el filtro, entre comillas simples para que la shell no interprete `( ) & \|` | Ver el handshake. Incluye los ACK de la propia sesión: mucho ruido |
| `sudo tcpdump -n -i any 'tcp port 22 and tcp[tcpflags] & tcp-syn != 0'` | Solo paquetes con SYN: los intentos de conexión nuevos | Ver handshakes sin ruido; dejarlo unos minutos muestra los bots que prueban el 22 (lo que bloqueará `fail2ban` en Linux · Bloque 4). Parar con `Ctrl-C` |

## Instalación y comprobación

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo apt install tcpdump traceroute` | Instalar en el VPS (Ubuntu); `apt` gestor de paquetes, `install` la acción | La imagen de Netcup es mínima: casi ninguna herramienta de red viene de serie. Pide confirmación (`y`) |
| `sudo pacman -S tcpdump` | Instalar en el portátil (Arch); `-S` (*sync*) instala desde los repositorios | Solo si se quiere capturar desde el lado del cliente. El NAT no se ve desde ninguna de las dos máquinas: ocurre en el router |
| `which PROGRAMA` | Ruta del ejecutable que se usaría | Comprobar si algo está instalado antes de dar por hecho que existe |

## SSH

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ssh -G vps \| grep hostname` | `-G` imprime la configuración efectiva para un alias sin conectar | Saber a qué IP apunta el alias `vps` para usarla con `ping` o `traceroute` |

## Documentación

| Referencia | Para qué | Cuándo |
|---|---|---|
| Kurose y Ross, *Computer Networking: A Top-Down Approach*: 1.3–1.5 (conmutación, estructura de internet, retardos, capas) | El modelo de capas y el contexto | Repasar el porqué de las capas |
| Kurose y Ross, 4.3.1–4.3.3 | Datagrama IPv4, direccionamiento, subredes, DHCP y NAT | Cálculo de subredes y NAT |
| Kurose y Ross, 3.1, 3.2, 3.3, 3.5.1 y 3.5.6 | Transporte, multiplexación, UDP, segmento TCP y handshake | Puertos, sockets y la captura |
| `man ip`, `man ss`, `man tcpdump`, `man pcap-filter` | Opciones y sintaxis de filtros en la versión instalada | `pcap-filter` documenta la sintaxis de lo que va entre comillas en `tcpdump` |
