# Redes · Bloque 2 — DNS

Carril de Redes: **martes, 1 h**. Sesiones 1 a 4 completadas el 28/09/2026. Cierre pendiente de una repetición.

**Contenido del bloque (roadmap):** tipos de registro, resolución recursiva, TTL y propagación. Practicado con `dig` contra dominios reales.

**Criterio de cierre:** explicar sin notas, aguantando tres «¿y por qué?», **por qué un cambio de DNS «tarda» y qué controla ese tiempo**. Y describir el recorrido completo de una consulta, del navegador al autoritativo, indicando en cada tramo quién pregunta a quién, qué tipo de consulta es y dónde hay caché.

**Qué NO es este bloque:** no se monta un servidor DNS, ni se estudia DNSSEC, ni DNS sobre HTTPS.

**Entorno:** portátil con CachyOS y el VPS `backend-lab` (Ubuntu 24.04), sin dominio propio todavía.

---

## Estado

- [x] Sesión 1 · Qué problema resuelve DNS y su jerarquía
- [x] Sesión 2 · Resolución recursiva, iterativa y caché
- [x] Sesión 3 · Tipos de registro
- [x] Sesión 4 · TTL y propagación
- [x] Cierre, parte 1: por qué un cambio «tarda» y qué lo controla (tres «¿y por qué?» superados)
- [ ] Cierre, parte 2: recorrido completo **sin mirar**. Falló en el primer intento (ver §2.5)

---

## 1. Qué es DNS y por qué está repartido

### Qué hace

Traduce nombres a IPs: las personas recuerdan nombres, los routers solo entienden números. Kurose le atribuye cuatro servicios:

| Servicio | Registro que lo implementa |
|---|---|
| Traducir nombre a IP | `A`, `AAAA` |
| Alias de nombres | `CNAME` |
| Alias de correo | `MX` |
| Reparto de carga | Varios `A` para un mismo nombre, que se van rotando |

El reparto de carga se vio en directo: consultas seguidas a `mediavida.com` devolvían IPs distintas (`.115`, `.117`, `.119`, `.120`).

Es un protocolo de **aplicación** al servicio de otras aplicaciones: el navegador, `ssh` o `apt` le preguntan a DNS **antes** de abrir su propia conexión. Viaja normalmente por **UDP, puerto 53**. Enlaza con el Bloque 1: una pregunta corta y una respuesta corta no justifican el handshake de TCP.

### Por qué no hay una base de datos central

Las cuatro razones de Kurose, que hay que poder decir sin mirar:

1. **Punto único de fallo.** Si cae, internet entero se queda sin DNS.
2. **Volumen de tráfico.** Ningún centro de datos aguanta las **lecturas** del planeta entero.
3. **Distancia.** Una consulta desde el otro lado del mundo pagaría esa latencia **antes** de cada conexión.
4. **Mantenimiento.** Una sola organización tendría que aplicar millones de **escrituras** al día y sincronizarlas en todas sus copias. Es la menos intuitiva: no es un problema de rendimiento sino de organización.

La cuarta es la que justifica la jerarquía.

### La jerarquía y la delegación

Tres niveles. **Ninguno sabe la respuesta completa, solo a quién preguntar después.**

| Nivel | Qué sabe | Qué no sabe |
|---|---|---|
| **Raíz** | Dónde están los servidores de cada TLD | Nada sobre dominios concretos |
| **TLD** (`.com`, `.es`…) | Qué autoritativos lleva cada dominio bajo él | La IP de ningún dominio |
| **Autoritativo** | Los registros reales del dominio | — |

La formulación que resume la sesión: **raíz y TLD guardan el *dónde*; el autoritativo guarda el *qué*.** Por eso, cuando un dominio cambia de IP, solo se toca su autoritativo, y cada dueño cambia lo suyo sin pedir permiso a nadie de arriba. La delegación resuelve el problema de mantenimiento.

### Los nombres se leen de derecha a izquierda

De lo más general a lo más concreto: `odoo.com` se resuelve empezando por `.com`. Hay un nivel oculto más a la derecha: el nombre completo es `odoo.com.`, con un **punto final que representa la raíz**. `dig` lo muestra siempre.

---

## 2. Resolutores frente a jerarquía

### Dos grupos con papeles opuestos

Es el nudo conceptual del bloque, y el origen de los errores del cierre.

```
          RESOLUTORES                               JERARQUÍA
      (los que preguntan)                   (los que contestan)

navegador                                   raíz         → «pregunta al TLD»
  → systemd-resolved (127.0.0.53)           TLD .com     → «pregunta al autoritativo»
      → resolutor de la operadora  ───────▶ autoritativo → «la IP es esta»
        (hace el recorrido y GUARDA
         en caché lo que le contestan)
```

- **Resolutores:** los recaderos. No son dueños de ningún dato; lo van a buscar y **guardan una copia**. Es el «servidor DNS local» de Kurose, y **no forma parte de la jerarquía**. Lo pone el proveedor de acceso, la empresa o la universidad.
- **Jerarquía:** las ventanillas. Contestan lo suyo y **no guardan nada** de quién les preguntó. Tienen los datos originales, no copias.

### El resolutor local de la máquina: `systemd-resolved`

Tanto el portátil como el VPS responden desde `127.0.0.53`. Es **`systemd-resolved`**, un programa dentro de la propia máquina. Todos los programas le preguntan a él.

En el VPS, `resolvectl status` mostró:

- `resolv.conf mode: stub` — *stub* significa resolutor a medias: tiene caché, pero **no recorre la jerarquía**. Si no sabe algo, lo reenvía entero.
- `Current DNS Server: 46.38.252.230` — el resolutor de **Netcup**, al que reenvía. Hay cuatro en la lista (dos IPv4 y dos IPv6) por redundancia.

`127.0.0.53` es su **dirección**; el programa es `systemd-resolved`. Igual que `5432` no era Postgres, sino el puerto donde escuchaba.

`/etc/resolv.conf` es un **enlace simbólico** a `/run/systemd/resolve/stub-resolv.conf`, un fichero que genera `systemd-resolved` y que vive en `/run`, que se regenera en cada arranque. **No se edita a mano**: se sobrescribe.

### Consulta recursiva frente a iterativa

- **Recursiva:** «resuélvemelo y tráeme la respuesta final».
- **Iterativa:** «si no lo sabes, dime a quién preguntar».

**Por qué se llama recursiva:** en el modelo completamente recursivo de Kurose, cada servidor delega en el siguiente y **espera**, y la respuesta vuelve desapilándose por el mismo camino. La estructura es la de una función recursiva: cada llamada delega un trozo más pequeño del problema (el resto del nombre) y el **autoritativo es el caso base**, el que no delega y responde.

**Por qué en la práctica no se usa recursión contra la jerarquía:** si la raíz aceptara consultas recursivas, tendría que quedarse esperando, y recordando, cada consulta pendiente del planeta. Vuelve el problema de volumen. Con la iterativa contesta en una frase y se olvida.

El reparto real:

- Programa → `systemd-resolved` → resolutor de la operadora: **recursiva**. El cliente quiere la respuesta final.
- Resolutor de la operadora → raíz, TLD, autoritativo: **iterativa**. Cada uno solo dice a quién preguntar, y el trabajo lo hace el resolutor, que solo atiende a sus clientes. La carga queda repartida.

### La caché

El resolutor guarda **todas** las respuestas del recorrido, no solo la IP final: dónde están los TLD, dónde los autoritativos de cada dominio y la IP.

**Consecuencia:** al resolver luego otro dominio `.com` que nunca vio, se salta la raíz y va directo al TLD de `.com`. Por eso los servidores raíz reciben muchas menos consultas de lo que parecería.

Pruebas de la caché vistas: `mediavida.com` tardó 55 ms la primera vez y 8 ms la segunda; el bloque 0 de `dig +trace` tardó 5 ms (caché más loopback, sin salir de la máquina).

### El recorrido completo

Resolución de `odoo.com` sin nada en caché:

1. **El navegador** pregunta a **`systemd-resolved`**. **Recursiva.**
2. **`systemd-resolved`** no la tiene y, como es *stub*, la reenvía al **resolutor de la operadora** (en el VPS, Netcup). **Recursiva.**
3. **El resolutor** pregunta a la **raíz**. **Iterativa.** Respuesta: «para `.com`, pregunta a estos» (`NS`). La raíz no guarda nada.
4. **El resolutor** guarda en caché los TLD de `.com` y les pregunta. **Iterativa.** Respuesta: «para `odoo.com`, pregunta a estos autoritativos» (`NS`).
5. **El resolutor** guarda en caché los autoritativos y les pregunta. **Iterativa.** Respuesta: el `A` de `odoo.com`, con `aa` y el TTL completo.
6. **El resolutor** guarda la IP en caché y la devuelve a `systemd-resolved`.
7. **`systemd-resolved`** la guarda también y la devuelve al navegador.

```
navegador ─rec─▶ systemd-resolved ─rec─▶ resolutor operadora ─iter─▶ raíz / TLD / autoritativo
                   [caché]                  [caché]                   [sin caché: fuente]
```

Hay **dos cachés** en el camino: la de la máquina y la del resolutor de la operadora.

### Los dos errores del primer intento de cierre

- Poner a `systemd-resolved` haciendo el recorrido iterativo. **No lo hace: es *stub* y reenvía.**
- Poner caché en raíz, TLD y autoritativo. **Solo los resolutores guardan copias.**

---

## 3. Direcciones especiales: loopback y rangos privados

| Rango | Alcance | Analogía |
|---|---|---|
| `127.0.0.0/8` | La propia máquina. Siempre, en cualquier ordenador | El pasillo de tu casa |
| `192.168.x.x`, `10.x.x.x`, `172.16–31.x.x` | Red privada, del router hacia dentro. El vecino usa las mismas, sin conflicto, porque nunca salen a internet | Los pisos de un edificio: otro edificio también tiene un «2.º B» |
| IP pública | Internet | La dirección postal del edificio, única |

- **`127.x.x.x` es loopback por norma**, no por configuración. Se sabe sin ver la máscara, como se sabe que el 112 es emergencias. `127.0.0.53` es tan local como `127.0.0.1`.
- **`0.0.0.0` es lo contrario**: escuchar en **todas** las interfaces. Es el peligro del incidente de Docker del Bloque 0 de PostgreSQL.
- **La máscara vive en la interfaz**, no en la dirección. Por eso `ip a` muestra `127.0.0.1/8` en `lo` y `dig` solo muestra la dirección.

---

## 4. Registros de recursos

### Los cuatro campos

Toda línea de `dig` es una ficha:

```
mediavida.com.   35   IN   A   84.17.59.120
   nombre        TTL  clase tipo  valor
```

- **Clase** (`IN`, *Internet*) es siempre la misma; Kurose ni la cuenta como campo.
- **El tipo cambia el significado de los demás campos.**

**Nombre frente a valor**, la confusión más común:

- **Nombre:** **de quién habla** la ficha.
- **Valor:** **a dónde apunta**.

Un `MX` de `kogniatech.es` con valor `mx00.ionos.es` habla del correo de Kognia y apunta a IONOS. Si la web de Kognia se muda, **ese `MX` no se toca**.

### Los tipos

| Tipo | Siglas | Qué responde | Valor | Ejemplo visto |
|---|---|---|---|---|
| `A` | *Address* | ¿En qué IPv4 está este nombre? | Una IPv4 | `mediavida.com → 84.17.59.120` |
| `AAAA` | IPv4 × 4 bits | ¿Y en qué IPv6? | Una IPv6 | `wikipedia.org → 2a02:ec80:600:ed1a::1` |
| `NS` | *Name Server* | ¿Quiénes son los servidores de este nombre? | Un nombre | `mediavida.com → christina.ns.cloudflare.com` |
| `CNAME` | *Canonical Name* | ¿De qué nombre es alias este? | Un nombre | `www.wikipedia.org → dyna.wikimedia.org` |
| `MX` | *Mail eXchanger* | ¿Dónde se entrega el correo de este dominio? | Prioridad + nombre | `kogniatech.es → 10 mx00.ionos.es` |
| `TXT` | *Text* | Texto libre que leen otros sistemas | Texto | SPF de `kogniatech.es` |
| `SOA` | *Start of Authority* | Ficha técnica de la zona | Siete valores | `kogniatech.es → ns1051.ui-dns.com …` |
| `PTR` | *Pointer* | ¿Qué nombre tiene esta IP? | Un nombre | IP del VPS → `…powersrv.de` |

`RRSIG`, `DS` y `NSEC3` son de **DNSSEC** (firmas que prueban que una respuesta no está falsificada). Fuera del bloque: se ignoran.

### `CNAME`: la clave ajena de DNS

Varios nombres que apuntan a la misma máquina (`www.`, `tienda.`, `blog.`…):

- Con un `A` cada uno, la IP está escrita varias veces. Al cambiar de servidor hay que tocarlas todas, y la que se olvide queda apuntando a la máquina vieja.
- Con un `A` en el canónico y `CNAME` en los demás, la IP está escrita **una sola vez**.

Es la misma idea que la clave ajena del Bloque 0 de PostgreSQL: el código del almacén en vez de su dirección entera.

El resolutor **sigue el alias él solo**: al pedir `www.wikipedia.org` devuelve el `CNAME` y el `A` del canónico. El `CNAME` lleva siempre un **nombre** como valor, nunca una IP.

TTL observados: el alias `11930` s y la IP `107` s. El alias casi nunca cambia; la IP sí, porque Wikipedia reparte a cada usuario al centro de datos más cercano (`dyna`, dinámico).

### `MX` y SPF: el correo con dominio propio

Sobre un mismo nombre caben **dos preguntas distintas**, y cada una tiene su ficha:

- «¿Dónde está la web de `miguel.dev`?» → **`A`**.
- «¿Dónde dejo las cartas para `miguel.dev`?» → **`MX`**.

Así la web y el correo pueden vivir en máquinas distintas con el mismo nombre.

- Con una dirección `@gmail.com`, el dominio es de Google y su `MX` lo gestiona Google.
- Con una dirección de dominio propio (`desarrollo3@kogniatech.es`), se contrata un proveedor de correo y **el `MX` es el mecanismo que permite usarlo con tu nombre**. El de Kognia apunta a IONOS.

La **prioridad** del `MX`: se prueba primero el número más bajo. Kognia tiene dos con `10`, así que el correo se reparte entre ambos y ninguno es de reserva.

**SPF** es el uso más común de `TXT`:

```
"v=spf1 include:_spf-eu.ionos.com ~all"
```

| Parte | Significado |
|---|---|
| `v=spf1` | Política SPF, versión 1 |
| `include:_spf-eu.ionos.com` | Autorizados: los servidores que lista IONOS |
| `~all` | Cualquier otro es sospechoso |

- **`MX`:** dónde se **recibe** el correo del dominio.
- **SPF:** quién puede **enviar** en su nombre.

`TXT` también sirve para **demostrar que un dominio es tuyo**. Let's Encrypt puede usarlo: vuelve a salir en el Bloque 4 (TLS).

### `SOA`

```
kogniatech.es. 21600 IN SOA ns1051.ui-dns.com. hostmaster.1und1.com. 2017060123 28800 7200 604800 600
```

| Valor | Qué es |
|---|---|
| `ns1051.ui-dns.com.` | Autoritativo principal (infraestructura DNS de IONOS) |
| `hostmaster.1und1.com.` | Email del responsable, con punto en vez de `@`. 1&1 es el nombre antiguo de IONOS |
| `2017060123` | Número de serie, normalmente `AAAAMMDDnn`. Sube con cada cambio de la zona |
| `28800 7200 604800` | Sincronización entre autoritativos. Ignorar |
| **`600`** | Duración de la caché **negativa** (ver §6) |

### `PTR`: la resolución inversa

```
111.45.58.89.in-addr.arpa.  21600  IN  PTR  v2202609416983518596.powersrv.de.
```

- **El nombre es la IP al revés** más `.in-addr.arpa`. DNS lee de lo general a lo concreto de derecha a izquierda, y una IP lo hace de izquierda a derecha. Al darle la vuelta, la jerarquía puede delegar por bloques de IP igual que por dominios.
- **Lo controla quien tiene el bloque de IPs** (Netcup), no quien tiene el dominio, porque cuelga de la jerarquía de las IPs.
- **Sirve** sobre todo para el correo: muchos servidores rechazan correo de una IP cuyo `PTR` no encaje con el dominio emisor. También para que los logs muestren nombres.

### Qué registros hacen falta para apuntar un dominio al VPS

```
miguel.dev.       3600   IN   NS      ns1.proveedordns.com.   ← en el TLD de .dev
miguel.dev.       3600   IN   A       <IP>                    ← en tu autoritativo
www.miguel.dev.   3600   IN   CNAME   miguel.dev.             ← en tu autoritativo
```

```
raíz ──NS──▶ TLD .dev ──NS──▶ ns1.proveedordns.com ──A──▶ IP del VPS
```

- La ficha `NS` del TLD no se escribe a mano: al comprar el dominio se le indican al **registrador** los autoritativos y él la da de alta.
- Las fichas `A` y `CNAME` se crean en el panel del **proveedor de DNS**.
- En los paneles no suele hacer falta el punto final; en `dig` aparece siempre.

---

## 5. Leer la salida de `dig`

### Una consulta normal

Solo cuatro líneas importan; `OPT PSEUDOSECTION`, `id`, `global options` y `MSG SIZE` se ignoran.

| Línea | Qué dice |
|---|---|
| `status:` | `NOERROR` (existe) o `NXDOMAIN` (*Non-Existent Domain*) |
| `flags:` | `qr` es respuesta · `rd` pediste recursión · `ra` el servidor la ofrece · **`aa`** respuesta autoritativa |
| `ANSWER SECTION` | Las fichas de la respuesta |
| `SERVER:` | Quién contestó: IP, puerto `#53` y protocolo |

Las secciones de la salida (`HEADER`, `QUESTION`, `ANSWER`, `AUTHORITY`, `ADDITIONAL`) son exactamente las del **formato del mensaje DNS** de Kurose 2.4.3.

**Con `NXDOMAIN`:** `ANSWER: 0`, no hay sección de respuesta, y aparece una `AUTHORITY SECTION` con el `SOA` de quien afirma que el nombre no existe. Para `estedominionoexiste12345.com`, fue `com.`: el TLD, que sabe qué dominios `.com` están delegados.

**Preguntando directamente a un autoritativo:** aparece `aa`, falta `ra` y sale `WARNING: recursion requested but not available`. `dig` pide recursión por defecto y el autoritativo no la ofrece: solo contesta de lo suyo.

### `dig +trace`

- Cada bloque va separado por una **línea en blanco** y **termina en `;; Received … from …`**, que dice quién contestó.
- Se lee cada bloque **de abajo arriba**: primero quién contesta, luego qué dijo.
- Los errores `UDP setup with 2001:… failed: network unreachable` son intentos por IPv6 en una red sin salida IPv6. `dig` reintenta por IPv4. Se evitan con `-4`.

La salida con `mediavida.com`:

| Bloque | Contesta | Tipo | Dice |
|---|---|---|---|
| 0 | `systemd-resolved` (`127.0.0.53`) | `NS` | «Los 13 servidores raíz son `a`–`m`.root-servers.net» |
| 1 | Raíz (`a.root-servers.net`) | `NS` | «Para `.com`, pregunta a estos» |
| 2 | TLD (`b.gtld-servers.net`) | `NS` | «Para `mediavida.com`, pregunta a `christina` o `damian` (Cloudflare)» |
| 3 | Autoritativo (`christina.ns.cloudflare.com`) | **`A`** | «La IP es `84.17.59.120`» |

- El bloque 0 es la **única** vez que `+trace` usa el resolutor local: solo para saber por dónde empezar.
- **El paso de `NS` a `A` indica el final del recorrido**: `NS` es el *dónde*, `A` el *qué*.
- Que haya dos autoritativos (y 13 raíces, y 13 TLD de `.com`) es redundancia: no hay punto único de fallo.
- Mediavida no gestiona su propio DNS: lo contrata a Cloudflare.

---

## 6. TTL y propagación

### Quién fija el TTL y qué hace el resolutor

- Lo decide **el dueño del dominio**, en su proveedor de DNS (a veces se queda el valor por defecto, pero la decisión es suya).
- El resolutor **guarda la ficha y va descontando**. Contesta con lo que **le queda**, no con el valor original.

Cómo distinguir en `dig` una respuesta de la fuente de una cacheada:

| | Autoritativo | Resolutor |
|---|---|---|
| Flag `aa` | Sí | No |
| TTL | Siempre completo (`35`) | Lo que queda (`33`, `22`…) |

`1.1.1.1` devolvió TTL que saltaban (`33`, `35`, `35`, `22`): no es un servidor sino cientos bajo la misma IP, cada uno con su caché. Un `35` significa que esa máquina acababa de ir al autoritativo.

### Por qué un cambio «tarda»

- **Nadie avisa a las cachés.** El autoritativo solo responde y no guarda quién le preguntó, así que **no sabe quién tiene copia**. Aunque lo supiera, serían millones: volvería el problema de volumen.
- **Cada resolutor empieza su cuenta atrás cuando alguien le pregunta**, así que cada uno caduca en un momento distinto. Por eso «la mitad de la gente» ve la IP nueva y la otra mitad no.
- **El tiempo máximo es el TTL**: el peor caso es un resolutor que guardó la ficha un instante antes del cambio.

La «propagación» no es un cambio que viaje por internet: son cachés que caducan cada una a su ritmo. El TTL es la fecha de caducidad que el dueño pone **por adelantado**, porque después no puede hablar con las copias.

### El equilibrio del TTL

| TTL | Se gana | Se pierde |
|---|---|---|
| Largo | Menos consultas, respuestas más rápidas, menos carga | Los cambios tardan en verse |
| Corto | Los cambios se ven enseguida | Más consultas y más latencia |

Valores vistos: delegaciones `NS` de `.com` a 172800 s (dos días, cambian poquísimo), el `CNAME` de Wikipedia a 11930 s, la IP de Wikipedia a 107 s y la de mediavida a 35 s.

### Procedimiento para migrar un servidor

Un `A` con TTL de 86400 s (un día) y migración el sábado a las 10:00:

1. **Bajar el TTL (p. ej. a 300) al menos un TTL antiguo antes**: el viernes a las 10:00 o antes.
2. **El sábado, cambiar la IP.** Nadie tardará más de 5 minutos en verla.
3. **Días después, volver a subir el TTL.**
4. Si se puede, hacerlo a una hora de poco tráfico, para reducir a quién afecta esa ventana.

**Por qué bajarlo a la vez no sirve:** el TTL nuevo solo afecta a las copias que se hagan a partir de ese momento. Un resolutor que guardó la ficha a las 9:59 con 86400 s seguirá con la IP vieja hasta el domingo a las 9:59.

### La caché negativa

Un `NXDOMAIN` también se guarda. Su duración es **la menor entre el último número del `SOA` y el TTL del propio `SOA`** (RFC 2308). En `kogniatech.es`: `min(600, 21600) = 600` s.

**La trampa:** preguntar por `erp.cliente.es` antes de crearlo. El resolutor guarda «no existe» y lo sigue contestando durante esos 10 minutos, aunque el registro ya esté creado. Se tocan cosas que estaban bien y a los diez minutos funciona solo.

**Cómo evitarla o diagnosticarla:**

- No preguntar por un nombre antes de crearlo.
- Si ya se hizo, preguntar **directamente al autoritativo** (`dig @<autoritativo> nombre`). No tiene caché: si ahí sale `NOERROR` con `aa`, el registro está bien y solo hay que esperar.

---

## 7. Ampliación: elegir resolutor, configurarlo y los bloqueos de la operadora

Todo esto surgió después de cerrar las cuatro sesiones, al preguntar qué significa «poner el DNS a `1.1.1.1`». Aplica lo del bloque a casos reales.

### Qué significa «cambiar el DNS»

Cuando alguien configura `1.1.1.1` u `8.8.8.8`, **sustituye al resolutor de su operadora** por uno público. No es el que está justo delante de la máquina (ese sigue siendo `systemd-resolved`), sino el **siguiente**: el que hace el recorrido iterativo.

```
Por defecto:
navegador ─rec─▶ systemd-resolved ─rec─▶ resolutor de la operadora ─iter─▶ jerarquía

Con 1.1.1.1:
navegador ─rec─▶ systemd-resolved ─rec─▶ resolutor de Cloudflare ─iter─▶ jerarquía
```

La jerarquía no cambia: raíz, TLD y autoritativos son los mismos para todo el mundo. **Solo se cambia de recadero.**

**Por qué se hace:** velocidad, evitar los bloqueos que aplica el resolutor de la operadora, y que la operadora deje de ver los nombres que consultas.

**La contrapartida:** el resolutor ve **todos los dominios que consultas**. Esa lista no desaparece, cambia de manos: pasa de la operadora a Cloudflare, Google o quien sea. Es una decisión sobre en quién confías.

### Criterios para elegir

| Criterio | Qué preguntarse |
|---|---|
| **Privacidad** | ¿Guarda las consultas? ¿Cuánto tiempo? ¿Las asocia a mi IP? ¿Las usa para publicidad? |
| **Filtrado** | ¿Quiero que bloquee dominios de malware y *phishing*? ¿Aplica listas de bloqueo judiciales? |
| **Velocidad** | ¿Cuánto tarda **desde mi conexión**? Depende de lo cerca que tenga un servidor, no de su fama |
| **Cifrado** | ¿Admite DNS sobre TLS o HTTPS, para que nadie en el camino lea o altere las consultas? |
| **Validación DNSSEC** | ¿Comprueba las firmas `RRSIG` y descarta respuestas falsificadas? |

**Medición real desde casa**, siete rondas de `dig @<resolutor> example.org | grep "Query time"`:

| Resolutor | Media |
|---|---|
| Quad9 `9.9.9.9` | 3,0 ms |
| Cloudflare `1.1.1.1` | 4,0 ms |
| Google `8.8.8.8` | 5,9 ms |

- Los tres tienen servidores muy cerca (casi seguro en Madrid): una misma IP con cientos de servidores, y contesta el más cercano.
- La diferencia es **irrelevante**: pocos milisegundos, y solo en la primera consulta de cada dominio; después contesta la caché de `systemd-resolved`.
- **En casa, la velocidad no decide**: deciden privacidad y filtrado.
- `example.org` estaba en la caché de los tres, así que se midió la **distancia** hasta ellos, que es lo que interesa al comparar.

**En el VPS: dejar el de Netcup.** Está en el mismo centro de datos y un servidor no tiene historial de navegación que proteger.

### Dónde informarse sin caer en un «DNS trucha»

- **Privacy Guides** (`privacyguides.org/en/dns/`): proyecto sin ánimo de lucro y sin afiliados, que evalúa cada resolutor con criterios explícitos. Google no está entre sus recomendados.
- **La web oficial de cada resolutor**, para copiar sus IPs y leer su política: `quad9.net`, `developers.google.com/speed/public-dns` y la de `1.1.1.1` de Cloudflare.
- **Evitar las listas masivas de «servidores DNS públicos»**: recopilan miles de IPs que responden en el puerto 53, muchas de equipos mal configurados y algunas montadas para falsificar respuestas.
- **Las IPs, siempre de la web oficial**, nunca de un blog o un foro. Una IP de resolutor mal copiada, o cambiada a propósito, es un recadero que puede traer lo que quiera.

Señales de un resolutor fiable: organización conocida con nombre y sede, política de privacidad pública, DNS cifrado y, si puede ser, auditorías externas publicadas.

**Cómo leer la tabla de Privacy Guides:**

| Columna | Qué significa |
|---|---|
| **Protocols** | *Cleartext* es el DNS clásico del bloque (UDP 53, sin cifrar). DoH, DoT, DoQ y DNSCrypt son variantes **cifradas** (tras el Bloque 4, TLS) |
| **Logging** | *No*: no guarda nada. *Anonymized*: guarda datos sin asociarlos a la IP |
| **ECS** | *EDNS Client Subnet*: el resolutor pasa **un trozo de tu IP** al autoritativo para que este elija el servidor más cercano. Mejora la puntería de los CDN pero revela tu zona. *No* es lo más privado |
| **Filtering** | *Based on server choice*: cada proveedor tiene varias IPs, unas filtran y otras no |
| **Signed Apple Profile** | Configuración para iPhone y Mac. Irrelevante en Linux |

Mullvad **no admite *Cleartext***: solo DNS cifrado, así que no se configura como un `8.8.8.8`. `systemd-resolved` sabe hablar DNS sobre TLS (`-DNSOverTLS` en `resolvectl status`, desactivado), pero eso es para después del Bloque 4.

Para el caso de casa, **Quad9** encaja con lo medido: el más rápido, con filtrado de malware por defecto y ECS opcional.

La propia página avisa de que el DNS cifrado **no oculta la navegación**: aunque nadie lea las consultas, la operadora sigue viendo a qué IP te conectas y el nombre del sitio en el SNI (ver más abajo).

### De dónde saca el DNS el portátil

Hay **dos cosas distintas** que se mezclan fácilmente:

1. **`/etc/resolv.conf` no contiene el resolutor de fuera.** Solo dice `nameserver 127.0.0.53`: indica a los programas que pregunten a `systemd-resolved`. Nunca pondrá Quad9 ni Google.
2. **A quién reenvía `systemd-resolved`** aparece en `resolvectl status`, en la interfaz de salida. Ese dato lo rellena **NetworkManager** a partir de una de estas fuentes, por orden:

```
1. DNS puesto a mano en la conexión del portátil      ← si existe, manda este
2. Lo que reparte el router por DHCP al conectarse     ← si no hay manual
3. Fallback DNS Servers de systemd-resolved             ← solo si no hay ninguno
(+) Una VPN activa puede imponer los suyos mientras está conectada
```

**DHCP**, lo justo para entenderlo (no es de este bloque): al conectarse a la red, el router entrega a cada dispositivo **su IP privada, la puerta de enlace** (el propio router, la ruta *default* de `ip r`) **y el DNS** que debe usar. Por eso configurar el DNS en el router lo aplica a todos los dispositivos de casa de una vez.

Matices del router: muchos de operadora no dejan cambiarlo; a veces se ponen a sí mismos como DNS (`192.168.1.1`) y reenvían ellos; y su configuración solo vale **en casa**. Fuera, el portátil usa lo que le dé esa otra red.

**Diagnóstico del portátil (28/09/2026):**

| Dato | Valor | Lectura |
|---|---|---|
| `resolvectl status`, en `enp5s0` | `8.8.8.8` y `8.8.4.4` | Usa Google |
| `ipv4.dns` de `Wired connection 1` | `--` | No hay DNS puesto a mano |
| `ipv4.ignore-auto-dns` | `no` | Acepta el DNS del router |
| Conclusión | | **El `8.8.8.8` viene del router**, que se lo da a todos los dispositivos |

Otras cosas que mostró `resolvectl status` en el portátil:

- **`resolv.conf mode: foreign`**: en el VPS era `stub`. Aquí `/etc/resolv.conf` lo gestiona **otro programa** (NetworkManager), aunque las consultas siguen pasando por `127.0.0.53`.
- **`Fallback DNS Servers`**: Quad9, Cloudflare y Google, los de emergencia que trae de fábrica `systemd-resolved` en Arch.
- **Las interfaces `veth…`, `br-…` y `docker0`** son virtuales de Docker, sin DNS ni ruta por defecto. Redes de Docker: Q2 y Q3.
- **`LLMNR` y `mDNS`**: protocolos para encontrar dispositivos locales por nombre (`impresora.local`) sin servidor DNS.
- La conexión **`kognia`**, de tipo VPN, suele imponer sus propios DNS cuando está activa, para resolver nombres internos de la empresa.

**Para pasar a Quad9 en casa:**

1. En el router, en el apartado de DHCP o LAN, poner `9.9.9.9` y `149.112.112.112` (copiadas de `quad9.net`).
2. En el portátil, pedir la configuración de nuevo: `nmcli connection up "Wired connection 1"`.
3. Comprobar con `resolvectl status` que `DNS Servers` muestra Quad9. En `dig`, `SERVER` seguirá siendo `127.0.0.53`: la secretaria no cambia, solo **a quién llama**.

### Cómo bloquea la operadora

**Bloqueo por DNS.** La operadora carga una lista de dominios (por orden judicial) en **su resolutor**. Para esos dominios no hace el recorrido y **contesta con una mentira**: `NXDOMAIN`, un `A` hacia su página de «bloqueado», o una IP que no lleva a ningún sitio (`0.0.0.0`).

- El cliente se lo cree porque DNS clásico no lleva prueba de autenticidad. DNSSEC la daría, pero la máquina no la comprueba (`DNSSEC=no/unsupported` en `resolvectl status`).
- **Cambiar de resolutor lo esquiva**, porque el bloqueo solo vive en ese recadero.

**Por qué no basta, y lo que se usa además:**

| Mecanismo | Cómo funciona | ¿Lo esquiva cambiar de resolutor? |
|---|---|---|
| Bloqueo por DNS | El resolutor de la operadora miente | Sí |
| **Bloqueo por IP** | Corta el tráfico hacia la IP del servidor, da igual quién la resolviera. Tumba todo lo que comparta esa IP | No |
| Interceptar el puerto 53 | Como DNS clásico va sin cifrar, captura la consulta a `8.8.8.8` y contesta ella | No. Hace falta DNS cifrado |
| Mirar el SNI | Al abrir HTTPS, el nombre del sitio viaja visible al inicio del handshake TLS (Bloque 4) | No |

### Caso real: pixeldrain.com

En el navegador, `http://pixeldrain.com` mostraba `HTTP 451 – File unavailable For Legal Reasons`, con el aviso *Not Secure*.

**Primera lección: un código HTTP no viene de DNS.** Para recibirlo, DNS tuvo que dar una IP, abrirse una conexión TCP y **un servidor contestar**. Un bloqueo por DNS tipo `NXDOMAIN` daría «no se encuentra el sitio».

Las pruebas, capa por capa:

| Capa | Prueba | Resultado | Conclusión |
|---|---|---|---|
| **DNS** | `dig` a Google y a `1.1.1.1` | Mismas IPs (`203.23.179.11` y `.12`), en distinto orden y con distinto TTL | Funciona. **No hay bloqueo DNS** |
| **HTTP, puerto 80** | `http://pixeldrain.com` | 451, página genérica y sin cifrar | Alguien responde en nombre de pixeldrain |
| **TCP, puerto 443** | `https://pixeldrain.com` | *Unable to connect* | La conexión se corta antes de llegar a TLS |

**Por qué apunta a la operadora y no a pixeldrain:** si fuera pixeldrain bloqueando por país, contestaría también por HTTPS con su certificado válido. Que el 443 no conecte y el 80 devuelva una página genérica encaja con alguien **en medio**: impide el tráfico cifrado, que no puede suplantar, e inyecta su respuesta en el que va sin cifrar. Es **bloqueo por IP**, y por eso cambiar de resolutor no sirvió.

Matiz honesto: no es una prueba absoluta; un fallo del servidor en el 443 daría lo mismo, aunque sería mucha casualidad. Se podría ver el corte con el `tcpdump` del Bloque 1 (los `SYN` que salen y lo que vuelve) y, en el Bloque 3 (HTTP), con `curl -v`.

### Por qué una VPN esquiva el bloqueo por IP

Es **encapsulación**, las muñecas rusas del Bloque 1:

1. El portátil coge el paquete original, dirigido a la IP bloqueada.
2. Lo **cifra entero**, incluida la IP de destino.
3. Lo mete dentro de **otro paquete** dirigido al servidor de la VPN.

```
Lo que ve la operadora:
[ destino: servidor VPN ][ ▓▓▓▓▓▓ cifrado ▓▓▓▓▓▓ ]
```

El servidor de la VPN saca el paquete original y lo envía desde su IP. Con VPN, la operadora no ve **la IP de destino, ni las consultas DNS, ni el SNI**: los tres mecanismos quedan ciegos.

**Límites:** la operadora puede bloquear la propia VPN (su IP, o reconocer el tráfico); el proveedor de la VPN pasa a verlo todo (la confianza cambia de manos, como con el resolutor); y para el destino se viene del país de la VPN.

Montar una VPN propia en el VPS con WireGuard quedó apuntado en `ideas-proyectos.md`, para después del Bloque 4 de Linux.

---

## Errores y confusiones vistos

| Confusión | Corrección |
|---|---|
| `127.0.0.53` está en mi subred | Es loopback: la propia máquina. Todo `127.0.0.0/8` lo es |
| `127.0.0.1` escucha en toda la red local | Eso es `0.0.0.0`. `127.0.0.1` es solo la propia máquina |
| El TLD devuelve la IP del dominio | Devuelve los `NS` de los autoritativos: el *dónde* |
| El TLD que contesta es el autoritativo | El TLD **dice quiénes son** los autoritativos; estos todavía no han hablado |
| Tras resolver `odoo.com`, para otro `.com` hay que volver a la raíz | El resolutor ya tiene en caché los TLD de `.com`: va directo a ellos |
| El `MX` apunta a la web del dominio | El nombre del `MX` es el dominio; el valor apunta al servidor de correo. Son fichas independientes |
| Bajar el TTL el mismo día de la migración | Hay que bajarlo un TTL antiguo antes |
| Tras un `NXDOMAIN`, al crear el registro ya sale `NOERROR` | El `NXDOMAIN` está en caché durante el mínimo del `SOA` |
| `systemd-resolved` recorre la jerarquía | Es *stub*: reenvía de forma recursiva al resolutor de la operadora |
| Raíz, TLD y autoritativo guardan caché | Solo los resolutores guardan copias |
| `/etc/resolv.conf` dice qué resolutor de fuera se usa | Solo apunta a `127.0.0.53`. El de fuera está en `resolvectl status` |
| Cambiar el DNS en el router cambia el de todos los dispositivos | Solo el de los que aceptan el DNS del router (`ignore-auto-dns: no` y sin DNS manual) |
| El HTTP 451 de pixeldrain es un bloqueo por DNS | DNS daba las IPs correctas en dos resolutores. Es bloqueo por IP e inyección en HTTP |
| Cambiar de resolutor esquiva cualquier bloqueo | Solo el de DNS. El de IP, la interceptación del 53 y el SNI siguen |

---

## Analogías de referencia

| Concepto | Analogía |
|---|---|
| DNS | La guía telefónica: sabes el nombre, necesitas el número |
| Jerarquía | Una biblioteca por plantas: la entrada te manda a la planta `.com`, la planta a la estantería del dominio |
| Delegación | El catastro: la oficina central solo tiene la lista de ayuntamientos; cada ayuntamiento lleva su registro |
| Resolutor | El recadero: le preguntas una vez y recorre las ventanillas por ti |
| `systemd-resolved` | La secretaria de casa: todos le piden a ella, y ella hace la gestión fuera |
| Consulta iterativa | El conserje dice «planta tercera» y atiende al siguiente |
| Consulta recursiva | Una pila de llamadas: cada nivel delega y espera; el autoritativo es el caso base |
| Caché de los TLD | La segunda vez subes directo a la tercera planta sin pasar por la entrada |
| Loopback | El pasillo de tu casa: no sale a la calle |
| Rangos privados | El «2.º B» de tu edificio: otro edificio también tiene uno |
| `127.x.x.x` sin máscara | El 112: se sabe qué es porque está reservado por norma |
| `CNAME` | La clave ajena: el código del almacén en vez de su dirección |
| `A` frente a `MX` | El local de la tienda frente al almacén donde se entregan los paquetes |
| SPF | La lista de mensajeros autorizados que publica una empresa |
| TTL | La fecha de caducidad del yogur |
| Propagación | Neveras distintas cuyos yogures caducan en días distintos |
| Cambiar de resolutor | Cambiar de recadero: la biblioteca es la misma |
| DHCP y el DNS del router | El conserje apunta a cada vecino qué recadero usar al entrar; si el vecino ya tiene uno en su agenda, hace caso a su agenda |
| Bloqueo por DNS | El recadero vuelve diciendo «ese libro no existe» sin haber subido a la biblioteca |
| VPN | Meter la carta en un sobre opaco dirigido a un amigo en el extranjero, que la reenvía desde allí |

---

## Referencia de comandos

### Instalación de `dig`

```bash
sudo pacman -S bind              # portátil (CachyOS)
sudo apt install bind9-dnsutils  # VPS (Ubuntu minimal)
dig -v                           # comprobar la versión instalada
```

- **Qué hace:** instala `dig`, que no viene de serie en ninguno de los dos sistemas.
- **Flags:** `pacman -S` (*sync*) instala desde los repositorios. En Arch, `dig` viene dentro del paquete `bind`; en Ubuntu, en `bind9-dnsutils`. `dig -v` imprime la versión.
- **Cuándo:** una vez por máquina. En el VPS **todavía no está instalado**; hará falta en el Bloque 3 de Linux para comprobar el dominio antes de pedir el certificado TLS.

### `dig`: consultas básicas

```bash
dig mediavida.com
dig +short mediavida.com
dig +noall +answer mediavida.com
dig +noall +answer kogniatech.es MX
```

- **Qué hace:** lanza una consulta DNS y muestra la respuesta completa, no solo la IP. Es a DNS lo que `ssh -v` a SSH.
- **Flags:**
  - Sin opciones pide el registro `A` al resolutor del sistema (`127.0.0.53`).
  - Un **tipo tras el nombre** (`MX`, `AAAA`, `NS`, `TXT`, `SOA`, `CNAME`) pide ese registro.
  - `+short` — solo el valor, sin nada más. Para scripts.
  - `+noall` — apaga todas las secciones de la salida.
  - `+answer` — vuelve a encender solo la respuesta.
  - Los flags `+` son opciones de consulta y los `-` del programa: convención propia de `dig`.
- **Cuándo y cómo sacarle partido:**
  - `+noall +answer` es la combinación del día a día: deja solo la ficha que importa.
  - Averiguar quién lleva el correo de un cliente: `dig +noall +answer dominio MX`.
  - Antes de pedir un certificado TLS para el Odoo del VPS, comprobar que el `A` del dominio apunta a su IP.
  - En un incidente «la web no carga»: primero ver si el nombre resuelve y a qué.
- **Trampas:**
  - `NXDOMAIN` puede venir de la caché negativa aunque el registro ya exista (§6).
  - Lo que devuelve es la copia del resolutor, con el TTL restante, no necesariamente el dato actual del autoritativo.

### `dig`: elegir a quién preguntar

```bash
dig @1.1.1.1 +noall +answer mediavida.com
dig @christina.ns.cloudflare.com mediavida.com
```

- **Qué hace:** pregunta a un servidor concreto en vez de al resolutor del sistema.
- **Flags:** `@servidor` — IP o nombre del servidor al que preguntar. `1.1.1.1` es el resolutor público de Cloudflare; `8.8.8.8`, el de Google.
- **Cuándo y cómo sacarle partido:**
  - **Contra un autoritativo:** para ver el dato real, sin caché. Comprobar que un cambio está bien hecho aunque las cachés aún no se hayan enterado. Buscar el flag `aa`.
  - **Contra varios resolutores públicos:** para ver cómo va la «propagación» de un cambio en distintos sitios.
  - Para saltarse la caché de la propia máquina.
- **Trampas:**
  - `1.1.1.1` son cientos de servidores bajo la misma IP: los TTL saltan entre consultas.
  - Contra un autoritativo sale `WARNING: recursion requested but not available`. Es normal: solo contesta de lo suyo.

### `dig`: medir la velocidad de un resolutor

```bash
dig @9.9.9.9 example.org | grep "Query time"
dig @1.1.1.1 example.org | grep "Query time"
dig @8.8.8.8 example.org | grep "Query time"
```

- **Qué hace:** pregunta a cada resolutor y deja solo la línea del tiempo de respuesta.
- **Flags:** `@servidor` elige el resolutor. `|` pasa la salida de `dig` a `grep`, que filtra las líneas que contienen `"Query time"` (entre comillas porque lleva un espacio).
- **Cuándo y cómo sacarle partido:**
  - Elegir resolutor con datos, no por fama: repetir varias rondas y comparar medias.
  - Diagnosticar navegación lenta: si el resolutor de la operadora tarda cientos de milisegundos, ahí está el problema.
  - Usar un dominio popular mide la **distancia** hasta el resolutor (estará en su caché); uno raro mide además el recorrido completo.
- **Trampas:** la primera consulta puede ser lenta si el dominio no estaba en caché. Medir varias veces.

### `dig +trace`: ver el recorrido

```bash
dig +trace mediavida.com
dig -4 +trace mediavida.com
```

- **Qué hace:** en vez de preguntar al resolutor, recorre `dig` mismo la jerarquía de forma iterativa, desde la raíz, y muestra la respuesta de cada salto.
- **Flags:** `+trace` — recorrido iterativo paso a paso. `-4` — usar solo IPv4.
- **Cuándo y cómo sacarle partido:**
  - Diagnosticar **dónde se rompe** una resolución: si falla la delegación en el TLD o el autoritativo.
  - Tras comprar un dominio, comprobar que el TLD ya apunta a tus autoritativos.
  - Ver el dato de la fuente sin saber de antemano cuál es el autoritativo.
- **Trampas:**
  - Leer cada bloque de abajo arriba: la última línea dice quién contestó.
  - Sin `-4`, en una red sin IPv6 salen errores `network unreachable`. Son inofensivos.
  - Las líneas `RRSIG`, `DS` y `NSEC3` son DNSSEC: ignorarlas.

### `dig -x`: resolución inversa

```bash
dig +noall +answer -x <IP>
```

- **Qué hace:** pregunta qué nombre tiene una IP (registro `PTR`).
- **Flags:** `-x` — construye la consulta inversa sola (IP al revés más `.in-addr.arpa`).
- **Cuándo y cómo sacarle partido:**
  - Identificar de quién es una IP que aparece en un log (`/var/log/auth.log`, logs de nginx).
  - Cuando el VPS envíe correo (alertas, Odoo), comprobar que su `PTR` encaja con el dominio, o el correo acabará en spam.
- **Trampas:** el `PTR` lo controla el dueño del bloque de IPs (Netcup), no quien tiene el dominio.

### El resolutor del sistema

```bash
cat /etc/resolv.conf
ls -l /etc/resolv.conf
resolvectl status
```

- **Qué hacen:**
  - `cat` muestra un fichero. `/etc/resolv.conf` es donde los programas miran a qué servidor DNS preguntar.
  - `ls -l` muestra si ese fichero es un enlace simbólico y a dónde apunta.
  - `resolvectl status` muestra a qué servidores reenvía `systemd-resolved` y en qué modo funciona.
- **Flags:** `ls -l` (*long*) — formato largo: permisos, dueño y destino del enlace (`->`). La `l` inicial de los permisos indica enlace. `resolvectl` no necesita `sudo` para `status`: solo lee.
- **Cuándo y cómo sacarle partido:**
  - Cuando una máquina no resuelve nombres: ver primero `resolv.conf` y después qué hay detrás con `resolvectl status`.
  - En un servidor de cliente, saber qué resolutor usa antes de diagnosticar nada más.
  - En `resolvectl status`, las líneas clave son `resolv.conf mode` (*stub*), `Current DNS Server` y `DNS Servers`.
- **Trampas:**
  - En Ubuntu, `/etc/resolv.conf` **no se edita**: es un enlace a un fichero generado en `/run` y se sobrescribe. La configuración DNS se cambia por otra vía (Bloque 3 de Linux: netplan).
  - Todo lo que muestra `resolvectl` bajo `Link` y los protocolos (`LLMNR`, `mDNS`, `DNSOverTLS`) puede ignorarse por ahora.
  - En el portátil, buscar la interfaz con `Default Route: yes` (`enp5s0`): esa es la salida real y sus `DNS Servers` son los que se usan. `Fallback DNS Servers` solo entran si ninguna interfaz tiene DNS. `resolv.conf mode: foreign` significa que el fichero lo gestiona NetworkManager, no `systemd-resolved`.
  - Las decenas de interfaces `veth…`, `br-…` y `docker0` son de Docker: ignorarlas.

### Interfaces y sockets

```bash
ip a
sudo ss -tulpn | grep 127.0.0.53
```

- **Qué hacen:**
  - `ip a` muestra las interfaces de red y sus direcciones.
  - `ss -tulpn` lista quién escucha en qué puerto; `grep` filtra las líneas de una dirección.
- **Flags:**
  - `ip a` — `a` es *address*.
  - `ss`: `-t` TCP, `-u` UDP, `-l` solo los que escuchan, `-p` proceso dueño (necesita `sudo`), `-n` números en vez de nombres.
- **Cuándo y cómo sacarle partido:**
  - `ip a` para saber la IP pública de un servidor: interfaz `eth0`, línea `inet` con `scope global`. `lo` es el loopback. Las `inet6` con `fe80::` (`scope link`) se ignoran.
  - `ss` para saber qué proceso ocupa un puerto: el `systemd-resolved` del 53, o el `docker-proxy` del 5432 en el Bloque 0 de PostgreSQL.
- **Trampas:** sin `sudo`, `ss -p` no muestra el proceso.

---

### NetworkManager: de dónde sale el DNS del portátil

```bash
nmcli connection show
nmcli -f ipv4.dns,ipv4.ignore-auto-dns connection show "Wired connection 1"
nmcli connection up "Wired connection 1"
```

- **Qué hacen:**
  - `nmcli` es la herramienta de línea de comandos de NetworkManager, el programa que gestiona la red en CachyOS.
  - `connection show` lista las conexiones guardadas. Con un nombre detrás, muestra la configuración de esa conexión.
  - `connection up` activa una conexión o, si ya estaba activa, la **reactiva**: vuelve a pedir la configuración al router por DHCP.
- **Flags:**
  - `-f` (*fields*) — muestra solo los campos indicados, separados por comas, en vez de cientos de líneas.
  - `ipv4.dns` — DNS puestos **a mano** en esa conexión. `--` significa ninguno.
  - `ipv4.ignore-auto-dns` — si vale `yes`, se ignora el DNS que da el router.
- **Cuándo y cómo sacarle partido:**
  - Antes de cambiar el DNS en el router, comprobar que el equipo le va a hacer caso.
  - Tras cambiar algo en el router, aplicarlo sin reiniciar con `connection up`, y verificar después con `resolvectl status`.
  - En `connection show`, la columna `DEVICE` dice qué conexión va por qué interfaz; `--` es que está inactiva (la VPN `kognia`).
- **Trampas:**
  - El nombre `Wired connection 1` tiene espacios: **va entre comillas**. Sin ellas, la shell lo parte en tres palabras y `nmcli` no encuentra la conexión.
  - Una VPN activa puede imponer sus propios DNS mientras está conectada.

## Material

- **Kurose y Ross**, *Computer Networking: A Top-Down Approach*, 8.ª ed., sección 2.4 (2.4.1 servicios, 2.4.2 funcionamiento y caché, 2.4.3 registros y mensajes).
- **Grigorik**, *High Performance Browser Networking*, cap. 1 (gratis en hpbn.co).
- **RFC 2308**, sección 5 — caché negativa.
- **RFC 1034 y 1035** — definición original de DNS, para dudas concretas.
- **Privacy Guides**, `privacyguides.org/en/dns/` — evaluación independiente de resolutores públicos.
- **Webs oficiales de los resolutores** — `quad9.net`, `developers.google.com/speed/public-dns` y la de `1.1.1.1` de Cloudflare. De aquí, y solo de aquí, se copian las IPs.
- `man dig`, `man resolvectl`, `man systemd-resolved`, `man nmcli`.

---

## Pendiente

- **Cierre, parte 2:** reproducir sin mirar el recorrido de §2.5. Si sale limpio, el bloque queda cerrado.
- **Comprar dominio** antes del Bloque 3 de Linux (TLS con Let's Encrypt). Al tenerlo: bajar el TTL de un `A`, cambiar la IP y observar con `dig` al autoritativo, a `1.1.1.1` y a `8.8.8.8` quién se entera antes.
- Instalar `bind9-dnsutils` en el VPS.
- Opcional: cambiar el DNS del router a Quad9 y verificarlo con `nmcli connection up` y `resolvectl status`.
- En el Bloque 3 (HTTP), retomar el caso pixeldrain con `curl -v`; en el Bloque 4 (TLS), explicar por qué el 443 no llega a mostrar certificado.
- Siguiente: Bloque 3 de Redes, **HTTP**.
