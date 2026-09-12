# Capas de protocolos

> Redes · Bloque 1 · Sesión 1 — Kurose y Ross, cap. 1.5

Para dar estructura al diseño de protocolos de red, los ingenieros los organizan por capas, separando la funcionalidad de cada protocolo que compone el comportamiento de la red.

En internet el stack es de **cinco capas**.

---

## 1. Aplicación

Donde se producen y se consumen los datos. Protocolos como HTTP, SMTP o DNS.

## 2. Transporte

Transmite la información **entre procesos**. Su dirección es el **puerto**.

- **TCP** — garantiza que todo llega y en orden. Es más lento precisamente por eso: espera confirmaciones y retransmite lo que se pierde.
- **UDP** — transmite sin comprobar si llega. Más rápido porque no espera nada.

## 3. Red

Su dirección es la **IP**.

- **En el origen:** escribe la IP de destino final. No cambia en todo el viaje.
- **En cada nodo:** compara esa IP con las suyas.
  - Coincide → sube a transporte. **Fin del viaje.**
  - No coincide → hace *forwarding*: consulta la tabla de rutas y pasa a enlace la IP del siguiente vecino.

## 4. Enlace

Su dirección es la **MAC**.

- **Al recibir:** compara la MAC de la trama con la suya. Si coincide, quita la envoltura y sube el datagrama a red.
- **Al enviar:** traduce a MAC la IP de vecino que le dio red, y construye una **trama nueva** para ese tramo.

## 5. Física

El medio por el que viajan los bits.

---

## Las ideas que lo sostienen

**Encapsulación.** Al bajar, cada capa envuelve lo de arriba con su propia cabecera. Al subir, se desenvuelve en orden inverso.

**Cada capa entiende solo su propia dirección.** Red entiende IPs y nunca toca MACs. Enlace entiende MACs y nunca lee IPs.

**Cada capa habla con su homóloga del otro lado.** Transporte con transporte de extremo a extremo, red con red, enlace con enlace. La diferencia es el alcance de esa conversación.

**Los routers intermedios suben solo hasta red** y vuelven a bajar. Nunca ven la conexión TCP: es un acuerdo privado entre los dos extremos.

**La IP viaja intacta de punta a punta; la trama se destruye y se rehace en cada salto.** De la cabecera IP solo cambia el TTL, que baja de uno en uno.

**Nadie conoce el camino completo.** Ni el origen, ni ningún router. Cada nodo decide solo el siguiente salto, cuando el paquete ya está en sus manos. La ruta emerge de muchas decisiones locales encadenadas.

**Forwarding ≠ routing.** *Forwarding* es consultar la tabla y sacar el paquete por la interfaz que toca: microsegundos, por paquete. *Routing* es el proceso de fondo que **construye** esa tabla mediante los protocolos de enrutado: lento, continuo, ocurre aunque no circule nada.

---

## Unidades y direcciones

| Capa | Unidad | Dirección | Alcance |
|---|---|---|---|
| Aplicación | mensaje | nombres (URL) | extremo a extremo |
| Transporte | segmento (TCP) / datagrama (UDP) | **puerto** | extremo a extremo |
| Red | datagrama | **IP** | extremo a extremo |
| Enlace | trama | **MAC** | **un salto** |
| Física | bit | — | un salto |

> «Datagrama» aparece en dos capas: el de red y el de usuario (UDP). En la práctica casi todo el mundo dice «paquete» para todo.

---

## El recorrido, paso a paso

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

## MAC e IP

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

## Puertos

Número de 16 bits cuyo único propósito es que el sistema operativo sepa **a qué proceso** entregar los datos. IP lleva al edificio; el puerto dice a qué extensión.

Los dos lados **no son simétricos**:

- **Servidor** — puerto fijo y conocido de antemano. 22 SSH, 80 HTTP, 443 HTTPS, 5432 PostgreSQL, 8069 Odoo.
- **Cliente** — puerto efímero, asignado al vuelo y liberado al cerrar.

Una conexión se identifica por **cuatro datos**: IP origen, puerto origen, IP destino, puerto destino. Por eso caben tres `ssh vps` simultáneos sin confundirse — solo cambia el puerto de origen.

**El socket `LISTEN` no se convierte en la conexión.** El kernel crea uno nuevo por sesión; el original sigue escuchando. Por eso cien clientes caben en el puerto 22, y por eso reiniciar sshd no corta las sesiones abiertas.

Un servicio solo necesita puerto si habla por TCP o UDP. `cron` o `systemd-logind` no tienen. Y hay comunicación local por **sockets Unix** —ficheros en disco— sin puerto ni red.

---

## Comandos

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

## Retardos

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

## Circuit switching vs packet switching

**Circuit switching** reserva capacidad antes de transmitir, en tres fases: establecimiento (puede **bloquearse** si no hay recursos), transferencia a velocidad garantizada, y liberación. Se reparte el enlace por **FDM** (bandas de frecuencia, como la radio) o **TDM** (ranuras de tiempo, como turnos de palabra). Si no tienes nada que decir, tu banda o tu ranura se desperdicia.

**Packet switching** no reserva nada. Admite siempre, y lo que se degrada es la calidad.

> Circuit switching cambia eficiencia por garantía. Packet switching cambia garantía por eficiencia.

Internet eligió lo segundo porque el tráfico de datos va **a ráfagas**, y reservar para el pico significa tirar la mayor parte del tiempo.

Hoy queda circuit switching en la telefonía clásica (RTC, voz 2G/3G — de ahí la facturación por minutos, el tono de marcado como establecimiento y la señal de ocupado como bloqueo) y en líneas dedicadas. Todo lo demás, incluidas WhatsApp y VoLTE, es packet switching.

---

## Estructura de internet

La jerarquía comercial: los ISP de acceso son clientes de ISPs regionales, que son clientes de los **tier-1**. Los tier-1 no le pagan a nadie: hacen *peering* entre iguales. **El de abajo paga al de arriba por el tránsito.**

Los grandes proveedores de contenido construyen su **red privada global**, separada de internet público, que solo lleva su propio tráfico. Colocan centros de datos pequeños **dentro de los IXP** —puntos físicos donde muchos ISPs se interconectan directamente— y hacen peering *settlement free* con ISPs de nivel bajo, saltándose los escalones intermedios.

El peering gratuito funciona porque el interés es mutuo: recibir el contenido directo le sale más barato al ISP que comprar tránsito a un tier-1 para lo mismo.

**El bypass es parcial:** muchos ISPs de acceso solo son alcanzables atravesando un tier-1, así que también se conectan a ellos y les pagan.

Dos motivos, y el segundo es el fuerte: menos pagos, y **control sobre la entrega** (ruta, latencia, proximidad al usuario). En 2020, Amazon, Google, IBM y Microsoft alcanzaban el 76% de internet sin pasar por un tier-1: **la pirámide se ha aplanado**.

---

## Ataques y colas

Un DDoS es el fenómeno del retardo de cola llevado al extremo, pero **la cola es el síntoma, no el mecanismo**. Tres familias:

| Tipo | Qué agota | Llena la cola de red |
|---|---|---|
| **Volumétrico** | El ancho de banda del enlace. Suele usar amplificación: consulta pequeña con IP falsificada, respuesta enorme hacia la víctima. | Sí |
| **De protocolo** | Una tabla en memoria. El SYN flood manda miles de SYN sin completar el handshake. | **No** |
| **De aplicación** | CPU o base de datos. Peticiones legítimas pero caras. | No |

Un resolver DNS accesible desde internet es munición para amplificación. Ubuntu lo trae escuchando solo en loopback.

---

## Pendientes anotados

- [ ] Comparar `ip a` / `ip r` entre portátil y VPS (los dos lados del NAT)
- [ ] Calcular subredes a mano antes de verificar con `ipcalc`
- [ ] Capturar el handshake con `tcpdump` (instalar antes: la imagen de Netcup es minimal)
- [ ] `ip -6 r` sin ruta por defecto → IPv6 sin configurar en el VPS. No urgente; revisar al tocar netplan.
- [ ] Guardar la salida de `sudo ss -tulpn` como foto del «antes», para comparar tras desplegar Odoo

---

## Criterio de cierre del bloque

Dibujar a mano el camino de un paquete desde el portátil hasta el VPS, atravesando el NAT del router doméstico, y explicarlo en voz alta sin notas aguantando tres «¿y por qué?» seguidos.
