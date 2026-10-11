# Redes · Bloque 2 — DNS

Jerarquía y delegación, resolución recursiva e iterativa, cachés, tipos de registro, TTL y propagación. Practicado con `dig` contra dominios reales, y aplicado a elegir resolutor y a entender los bloqueos de la operadora.

**Entorno de referencia:** portátil con CachyOS (`dig` del paquete `bind`, NetworkManager, `systemd-resolved` en modo *foreign*) y VPS `backend-lab` (Ubuntu 24.04, `systemd-resolved` en modo *stub*, `dig` del paquete `bind9-dnsutils`). Las opciones de `dig` y la salida de `resolvectl` cambian entre versiones: confírmalas con `dig -v`, `man dig` y `man resolvectl` en la máquina donde vayas a ejecutarlos.

---

# Parte 1 · Teoría

## 1. Qué es DNS y por qué está repartido

### Qué hace

Traduce nombres a IPs: las personas recuerdan nombres, los routers solo entienden números. Kurose le atribuye cuatro servicios:

| Servicio | Registro que lo implementa |
|---|---|
| Traducir nombre a IP | `A`, `AAAA` |
| Alias de nombres | `CNAME` |
| Alias de correo | `MX` |
| Reparto de carga | Varios `A` para un mismo nombre, que se van rotando |

Es un protocolo de **aplicación** al servicio de otras aplicaciones: el navegador, `ssh` o `apt` le preguntan **antes** de abrir su propia conexión. Viaja normalmente por **UDP, puerto 53**: una pregunta corta y una respuesta corta no justifican el handshake de TCP.

### Por qué no hay una base de datos central

1. **Punto único de fallo.** Si cae, internet entero se queda sin DNS.
2. **Volumen de tráfico.** Ningún centro de datos aguanta las **lecturas** del planeta entero.
3. **Distancia.** Una consulta desde el otro lado del mundo pagaría esa latencia antes de cada conexión.
4. **Mantenimiento.** Una sola organización tendría que aplicar millones de **escrituras** al día y sincronizarlas en todas sus copias. No es un problema de rendimiento sino de organización, y es el que justifica la jerarquía.

### La jerarquía y la delegación

Tres niveles. **Ninguno sabe la respuesta completa, solo a quién preguntar después.**

| Nivel | Qué sabe | Qué no sabe |
|---|---|---|
| **Raíz** | Dónde están los servidores de cada TLD | Nada sobre dominios concretos |
| **TLD** (`.com`, `.es`, `.dev`…) | Qué autoritativos lleva cada dominio bajo él | La IP de ningún dominio |
| **Autoritativo** | Los registros reales del dominio | — |

**Raíz y TLD guardan el *dónde*; el autoritativo guarda el *qué*.** Cuando un dominio cambia de IP solo se toca su autoritativo, y cada dueño cambia lo suyo sin pedir permiso a nadie de arriba: la delegación resuelve el problema de mantenimiento.

### Los nombres se leen de derecha a izquierda

De lo más general a lo más concreto: `odoo.com` se resuelve empezando por `.com`. El nombre completo es `odoo.com.`, con un **punto final que representa la raíz**. `dig` lo muestra siempre; en los paneles de DNS no suele hacer falta escribirlo.

## 2. Resolutores frente a jerarquía

### Dos grupos con papeles opuestos

```
          RESOLUTORES                               JERARQUÍA
      (los que preguntan)                   (los que contestan)

navegador                                   raíz         → «pregunta al TLD»
  → systemd-resolved (127.0.0.53)           TLD .com     → «pregunta al autoritativo»
      → resolutor de la operadora  ───────▶ autoritativo → «la IP es esta»
        (hace el recorrido y GUARDA
         en caché lo que le contestan)
```

- **Resolutores:** los recaderos. No son dueños de ningún dato; lo van a buscar y **guardan una copia**. Es el «servidor DNS local» de Kurose, y **no forma parte de la jerarquía**. Lo pone la operadora, la empresa o el proveedor del servidor.
- **Jerarquía:** las ventanillas. Contestan lo suyo y **no guardan nada** de quién les preguntó. Tienen los datos originales, no copias.

### El resolutor de la propia máquina: `systemd-resolved`

En el portátil y en el VPS los programas preguntan a `127.0.0.53`, que es la **dirección** donde escucha `systemd-resolved`, un programa de la propia máquina.

- Es ***stub***: tiene caché, pero **no recorre la jerarquía**. Si no sabe algo, reenvía la pregunta entera al resolutor de fuera (en el VPS, el de Netcup).
- `/etc/resolv.conf` solo contiene `nameserver 127.0.0.53`. **Nunca dice a qué resolutor de fuera se reenvía**; eso aparece en `resolvectl status`.

| `resolv.conf mode` | Quién gestiona `/etc/resolv.conf` | Dónde se vio |
|---|---|---|
| `stub` | `systemd-resolved`: es un enlace simbólico a `/run/systemd/resolve/stub-resolv.conf`, regenerado en cada arranque. **No se edita a mano** | VPS (Ubuntu) |
| `foreign` | Otro programa (NetworkManager). Las consultas siguen pasando por `127.0.0.53` | Portátil (CachyOS) |

### Consulta recursiva frente a iterativa

- **Recursiva:** «resuélvemelo y tráeme la respuesta final».
- **Iterativa:** «si no lo sabes, dime a quién preguntar».

**Por qué se llama recursiva:** en el modelo completamente recursivo cada servidor delega en el siguiente y **espera**, y la respuesta vuelve desapilándose por el mismo camino, como una función recursiva cuyo **caso base es el autoritativo**.

**Por qué no se usa recursión contra la jerarquía:** la raíz tendría que esperar y recordar cada consulta pendiente del planeta. Con la iterativa contesta en una frase y se olvida.

| Tramo | Tipo | Por qué |
|---|---|---|
| Programa → `systemd-resolved` → resolutor de fuera | **Recursiva** | El cliente quiere la respuesta final |
| Resolutor de fuera → raíz, TLD, autoritativo | **Iterativa** | Cada ventanilla solo dice a quién preguntar; el trabajo lo hace el resolutor, que solo atiende a sus clientes |

### La caché

El resolutor guarda **todas** las respuestas del recorrido, no solo la IP final: dónde están los TLD, dónde los autoritativos de cada dominio y la IP. Al resolver después otro dominio `.com` que nunca vio, se salta la raíz y va directo al TLD. Por eso la raíz recibe muchas menos consultas de lo que parecería.

### El recorrido completo

Resolución de `odoo.com` sin nada en caché:

1. **El navegador** pregunta a **`systemd-resolved`**. **Recursiva.**
2. **`systemd-resolved`** no la tiene y, como es *stub*, la reenvía al **resolutor de fuera**. **Recursiva.**
3. **El resolutor** pregunta a la **raíz**. **Iterativa.** Respuesta: «para `.com`, pregunta a estos» (`NS`). La raíz no guarda nada.
4. **El resolutor** guarda en caché los TLD de `.com` y les pregunta. **Iterativa.** Respuesta: «para `odoo.com`, pregunta a estos autoritativos» (`NS`).
5. **El resolutor** guarda en caché los autoritativos y les pregunta. **Iterativa.** Respuesta: el `A` de `odoo.com`, con `aa` y el TTL completo.
6. **El resolutor** guarda la IP en caché y la devuelve a `systemd-resolved`.
7. **`systemd-resolved`** la guarda también y la devuelve al navegador.

```
navegador ─rec─▶ systemd-resolved ─rec─▶ resolutor de fuera ─iter─▶ raíz / TLD / autoritativo
                   [caché]                  [caché]                   [sin caché: fuente]
```

Hay **dos cachés** en el camino, y ambas son de resolutores.

## 3. Direcciones especiales: loopback y rangos privados

| Rango | Alcance |
|---|---|
| `127.0.0.0/8` | La propia máquina, en cualquier ordenador (loopback) |
| `192.168.x.x`, `10.x.x.x`, `172.16–31.x.x` | Red privada, del router hacia dentro. Se repiten en cada casa sin conflicto porque nunca salen a internet |
| IP pública | Internet, única |

- **`127.x.x.x` es loopback por norma**, no por configuración: se sabe sin ver la máscara. `127.0.0.53` es tan local como `127.0.0.1`.
- **`0.0.0.0` es lo contrario** cuando un servicio escucha: **todas** las interfaces.
- **La máscara vive en la interfaz**, no en la dirección: `ip a` muestra `127.0.0.1/8` en `lo`; `dig` solo muestra la dirección.

## 4. Registros de recursos

### Los cuatro campos

```
mediavida.com.   35   IN   A   84.17.59.120
   nombre        TTL  clase tipo  valor
```

- **Clase** (`IN`, *Internet*) es siempre la misma.
- **El tipo cambia el significado de los demás campos.**
- **Nombre:** de quién habla la ficha. **Valor:** a dónde apunta.

### Los tipos

| Tipo | Siglas | Qué responde | Valor |
|---|---|---|---|
| `A` | *Address* | ¿En qué IPv4 está este nombre? | Una IPv4 |
| `AAAA` | IPv4 × 4 en bits | ¿Y en qué IPv6? | Una IPv6 |
| `NS` | *Name Server* | ¿Quiénes son los servidores de este nombre? | Un nombre |
| `CNAME` | *Canonical Name* | ¿De qué nombre es alias este? | Un nombre, nunca una IP |
| `MX` | *Mail eXchanger* | ¿Dónde se entrega el correo de este dominio? | Prioridad + nombre |
| `TXT` | *Text* | Texto libre que leen otros sistemas | Texto |
| `SOA` | *Start of Authority* | Ficha técnica de la zona | Siete valores |
| `PTR` | *Pointer* | ¿Qué nombre tiene esta IP? | Un nombre |

`RRSIG`, `DS` y `NSEC3` son de **DNSSEC** (firmas que prueban que una respuesta no está falsificada). Fuera del bloque.

### `CNAME`

Con varios nombres apuntando a la misma máquina (`www.`, `tienda.`, `blog.`), un `A` en cada uno escribe la IP varias veces: al cambiar de servidor hay que tocarlas todas y la que se olvide queda apuntando a la máquina vieja. Con un `A` en el canónico y `CNAME` en los demás, la IP está escrita **una sola vez**: es la idea de la clave ajena de PostgreSQL. El resolutor **sigue el alias él solo** y devuelve el `CNAME` y el `A` del canónico.

### `MX` y SPF

Sobre un mismo nombre caben dos preguntas, cada una con su ficha: «¿dónde está la web?» → `A`; «¿dónde dejo el correo?» → `MX`. Así la web y el correo pueden vivir en máquinas distintas con el mismo nombre. Con un dominio propio se contrata un proveedor de correo, y **el `MX` es lo que permite usarlo con tu nombre**. Si la web se muda, el `MX` no se toca.

La **prioridad** del `MX`: se prueba primero el número más bajo; con dos iguales, el correo se reparte entre ambos.

**SPF** es el uso más común de `TXT`: lista quién puede **enviar** correo en nombre del dominio.

| | Qué controla |
|---|---|
| `MX` | Dónde se **recibe** el correo del dominio |
| SPF (`TXT`) | Quién puede **enviar** en su nombre |

`TXT` también sirve para **demostrar que un dominio es tuyo** (Let's Encrypt puede usarlo; vuelve en el Bloque 4).

### `SOA`

Siete valores: autoritativo principal, email del responsable (con punto en vez de `@`), número de serie (normalmente `AAAAMMDDnn`, sube con cada cambio), tres tiempos de sincronización entre autoritativos (se ignoran) y, el último, la duración de la **caché negativa** (§6).

### `PTR`: la resolución inversa

- **El nombre es la IP al revés** más `.in-addr.arpa`. DNS va de lo general a lo concreto de derecha a izquierda; una IP, de izquierda a derecha. Al darle la vuelta, la jerarquía puede delegar por bloques de IP igual que por dominios.
- **Lo controla quien tiene el bloque de IPs** (Netcup para el VPS), no quien tiene el dominio.
- **Sirve** sobre todo para el correo: muchos servidores rechazan correo de una IP cuyo `PTR` no encaje con el dominio emisor. También para que los logs muestren nombres.

### Quién escribe cada ficha al tener dominio propio

| Ficha | Dónde vive | Quién la escribe |
|---|---|---|
| `NS` del dominio | En el TLD | El **registrador**, al comprar el dominio e indicarle los autoritativos |
| `A`, `AAAA`, `CNAME`, `MX`, `TXT` | En el autoritativo | Tú, en el panel del **proveedor de DNS** |
| `PTR` de la IP del servidor | En la zona inversa del bloque de IPs | El proveedor del servidor (Netcup), desde su panel |

### Raíz del dominio o subdominio

Cada nombre tiene **sus propias fichas**: un `A` en `odoo.mlozano.dev` no crea nada en `mlozano.dev`, y al revés. En el panel de Cloudflare, el campo *Name* se rellena con `@` para la raíz (el *apex*) o con la etiqueta del subdominio (`odoo`), y Cloudflare añade el dominio detrás.

| Opción | A favor | En contra |
|---|---|---|
| Raíz (`mlozano.dev`) | Nombre corto | El servicio ocupa la raíz; si después se quiere otra cosa ahí, hay que moverlo |
| Subdominio (`odoo.mlozano.dev`) | La raíz queda libre; cada servicio, con su nombre | Nombre algo más largo |

### DNS only frente a Proxied (Cloudflare)

El interruptor de la nube de cada registro decide qué IP se publica:

| Modo | Nube | Qué IP publica el autoritativo | Camino del visitante |
|---|---|---|---|
| **DNS only** | Gris | La que escribiste (la del VPS) | Directo al servidor |
| **Proxied** | Naranja | IPs de Cloudflare | A Cloudflare, que hace de proxy hasta el servidor |

- Con **Proxied**, `dig` no devuelve la IP del VPS, el servidor deja de ver al visitante directamente y el TLS lo gestiona Cloudflare. Con nginx y certbot en el VPS, el modo es **DNS only**.
- El **TTL** solo se puede elegir en DNS only; con Proxied lo gestiona Cloudflare. **Auto** equivale a 300 s.
- Los registros de tipo **Tunnel** (Cloudflare Tunnel) van siempre en Proxied: por debajo son un `CNAME` hacia la infraestructura de Cloudflare.

## 5. El mensaje DNS y cómo lo muestra `dig`

### Cómo se construye una consulta

Toda consulta tiene tres partes: **a quién** se pregunta, **por quién** y **qué dato** se quiere.

```
dig  @SERVIDOR   NOMBRE   TIPO
     a quién    por quién  qué dato
```

| Parte | Ejemplo | Si no se pone |
|---|---|---|
| A quién (`@SERVIDOR`) | `@autumn.ns.cloudflare.com`, `@1.1.1.1` | Pregunta al resolutor del sistema (`127.0.0.53`), con su caché |
| Por quién (`NOMBRE`) | `odoo.mlozano.dev` | Obligatorio. Tiene que ser el nombre exacto de la ficha: la raíz y un subdominio son nombres distintos |
| Qué dato (`TIPO`) | `A`, `AAAA`, `NS`, `MX` | Pide `A` |

- **`dig` es el programa**, no una de las partes.
- **Lo que empieza por `+` o `-` no cambia la pregunta.** Las opciones `+` cambian la consulta o cómo se muestra (`+short`, `+trace`); las `-`, el programa (`-4`: enviar la pregunta por IPv4). `-4` no es un tipo: `dig -4 mlozano.dev` sigue pidiendo `A`.
- **El tipo va detrás del nombre**, sin guion.
- En estos apuntes, las palabras en MAYÚSCULAS (`DOMINIO`, `NOMBRE`, `AUTORITATIVO`) son huecos que se sustituyen por un valor real.

**Preguntar a un autoritativo** son dos pasos:

| Paso | Comando | Qué hace |
|---|---|---|
| 1. Saber cómo se llama | `dig +noall +answer DOMINIO NS` | `NS` como *qué dato*: devuelve los nombres de los autoritativos. La pregunta la sigue contestando el resolutor. Se pregunta por el **dominio** (`mlozano.dev`), no por el subdominio: los autoritativos lo son de la zona entera |
| 2. Preguntarle | `dig @AUTORITATIVO NOMBRE TIPO` | Lo que hace que conteste el autoritativo es la **`@`**. La prueba es el flag `aa` |

Hay dos o más autoritativos por redundancia, con los mismos datos: vale cualquiera. La sección `ADDITIONAL` de la respuesta a `NS` trae sus IPs; no hacen falta, porque `dig` resuelve el nombre que va detrás de `@`.

### Cómo se lee la respuesta

Las secciones de la salida de `dig` (`HEADER`, `QUESTION`, `ANSWER`, `AUTHORITY`, `ADDITIONAL`) son las del formato del mensaje DNS. Solo cuatro líneas importan; `OPT PSEUDOSECTION`, `id`, `global options` y `MSG SIZE` se ignoran.

| Línea | Qué dice |
|---|---|
| `status:` | `NOERROR` (existe) o `NXDOMAIN` (*Non-Existent Domain*) |
| `flags:` | `qr` es respuesta · `rd` pediste recursión · `ra` el servidor la ofrece · **`aa`** respuesta autoritativa |
| `ANSWER SECTION` | Las fichas de la respuesta |
| `SERVER:` | Quién contestó: IP, puerto `#53` y protocolo |

**Con `NXDOMAIN`:** `ANSWER: 0`, sin sección de respuesta, y una `AUTHORITY SECTION` con el `SOA` de quien afirma que el nombre no existe.

**Con `NOERROR` y `ANSWER: 0`** (*NODATA*): el nombre **existe**, pero no tiene fichas del tipo pedido. También trae el `SOA` en la `AUTHORITY SECTION`. El primer campo del `SOA` es el autoritativo principal de la zona.

**Preguntando directamente a un autoritativo:** aparece `aa`, falta `ra` y sale `WARNING: recursion requested but not available`. `dig` pide recursión por defecto y el autoritativo no la ofrece.

### Cómo se lee `dig +trace`

`dig +trace` no pregunta al resolutor: recorre la jerarquía él mismo, de forma iterativa, y muestra la respuesta de cada salto. Es pedir indicaciones sin GPS: cada oficina solo sabe a cuál mandarte después.

**Nomenclatura.**

| Término | Qué es |
|---|---|
| **Bloque** | Cada grupo de líneas separado por una línea en blanco. Se numeran por orden de aparición, empezando por el **bloque 0** |
| **Línea Received** | La última línea de cada bloque, la que empieza por `;; Received` |
| **Servidor que contesta** | El nombre entre paréntesis en la línea Received. Lo anterior es su IP y el puerto (`216.239.34.105#53`) |
| **Columnas de un registro** | Las cinco de cada línea de registro (abajo). Solo se cuentan en las líneas de registro, nunca en la línea Received |
| **Líneas que se ignoran** | Las que tienen `DS`, `RRSIG` o `NSEC3` en la columna 4: firmas DNSSEC |

```
mlozano.dev.   10800   IN   NS   gannon.ns.cloudflare.com.
 columna 1    col. 2  col.3 col.4      columna 5
 (nombre)     (TTL)  (clase)(tipo)     (valor)
```

**Método para leer un bloque**, siempre en este orden:

1. **Servidor que contesta**: en la línea Received, al final del bloque.
2. **Columna 1**: de qué nombre habla.
3. **Columna 4**: el tipo. `NS` significa «pregunta a estos servidores»; `A` o `AAAA`, «esta es la dirección».
4. **Columna 5**: el valor.

**Reglas de la cadena.**

| Regla | Consecuencia |
|---|---|
| El servidor que contesta un bloque es uno de los que aparecen en la columna 5 del bloque anterior | Así se encadenan. `dig` elige **uno cualquiera** de la lista, porque todos tienen los mismos datos; en otra ejecución puede tocar otro |
| La columna 1 va de lo general a lo concreto | `.` → `dev.` → `mlozano.dev.` → `odoo.mlozano.dev.` |
| El bloque 0 lo contesta el resolutor local | Habla **de** la raíz (columna 1 = `.`), pero no lo dice la raíz: es la única pregunta que `dig` hace al resolutor, para saber dónde empezar. No hay ningún bloque final del resolutor |
| El paso de `NS` a `A` en la columna 4 marca el final | Mientras sea `NS`, cada servidor remite al siguiente; con `A`, ya está la respuesta, que da el autoritativo |

Los cuatro bloques típicos: 0 resolutor local (lista de raíces) → 1 raíz (servidores del TLD) → 2 TLD (servidores autoritativos: **la delegación**) → 3 autoritativo (la dirección).

## 6. TTL y propagación

### Quién fija el TTL y qué hace el resolutor

- Lo decide **el dueño del dominio**, en su proveedor de DNS.
- El resolutor **guarda la ficha y va descontando**: contesta con lo que **le queda**, no con el valor original.

| | Autoritativo | Resolutor |
|---|---|---|
| Flag `aa` | Sí | No |
| TTL | Siempre completo | Lo que queda |

### Por qué un cambio «tarda»

- **Nadie avisa a las cachés.** El autoritativo no guarda quién le preguntó, así que **no sabe quién tiene copia**; y aunque lo supiera, serían millones.
- **Cada resolutor empieza su cuenta atrás cuando alguien le pregunta**, así que cada uno caduca en un momento distinto: parte de la gente ve la IP nueva y parte no.
- **El tiempo máximo es el TTL**: el peor caso es un resolutor que guardó la ficha un instante antes del cambio.

La «propagación» no es un cambio que viaje por internet: son cachés que caducan cada una a su ritmo. El TTL es la fecha de caducidad que el dueño pone **por adelantado**, porque después no puede hablar con las copias.

### El equilibrio del TTL

| TTL | Se gana | Se pierde |
|---|---|---|
| Largo | Menos consultas, respuestas más rápidas, menos carga | Los cambios tardan en verse |
| Corto | Los cambios se ven enseguida | Más consultas y más latencia |

### Cómo migrar un servidor sin esperas largas

1. **Bajar el TTL al menos un TTL antiguo antes** del cambio.
2. **Cambiar la IP** cuando toque. Nadie tardará más que el TTL nuevo en verla.
3. **Días después, volver a subir el TTL.**
4. Si se puede, hacerlo a una hora de poco tráfico.

Bajar el TTL el mismo día no sirve: el valor nuevo solo afecta a las copias que se hagan desde ese momento.

### La caché negativa

Un `NXDOMAIN` también se guarda, y un *NODATA* (`NOERROR` con `ANSWER: 0`) también. Su duración es **la menor entre el último número del `SOA` y el TTL del propio `SOA`** (RFC 2308, sección 5).

**La trampa:** preguntar por un nombre antes de crearlo. El resolutor guarda «no existe» y lo sigue contestando aunque el registro ya esté creado.

- No preguntar por un nombre antes de crearlo.
- Si ya se hizo, preguntar **directamente al autoritativo**, que no tiene caché: si ahí sale `NOERROR` con `aa`, el registro está bien y solo hay que esperar.

## 7. Elegir y configurar el resolutor

### Qué significa «cambiar el DNS»

Configurar `1.1.1.1` u `8.8.8.8` **sustituye al resolutor de la operadora** por uno público. No es el que está justo delante (ese sigue siendo `systemd-resolved`), sino el **siguiente**: el que hace el recorrido iterativo.

```
Por defecto:
navegador ─rec─▶ systemd-resolved ─rec─▶ resolutor de la operadora ─iter─▶ jerarquía

Con 1.1.1.1:
navegador ─rec─▶ systemd-resolved ─rec─▶ resolutor de Cloudflare ─iter─▶ jerarquía
```

La jerarquía es la misma para todo el mundo. **Solo se cambia de recadero.** Se hace por velocidad, por esquivar bloqueos del resolutor de la operadora o para que esta deje de ver los nombres consultados. **La contrapartida:** el resolutor nuevo ve **todos los dominios que consultas**. La lista cambia de manos; es una decisión sobre en quién confías.

### Criterios para elegir

| Criterio | Qué preguntarse |
|---|---|
| **Privacidad** | ¿Guarda las consultas? ¿Cuánto tiempo? ¿Las asocia a mi IP? ¿Las usa para publicidad? |
| **Filtrado** | ¿Bloquea dominios de malware y *phishing*? ¿Aplica listas judiciales? |
| **Velocidad** | ¿Cuánto tarda **desde mi conexión**? Depende de lo cerca que tenga un servidor, no de su fama |
| **Cifrado** | ¿Admite DNS sobre TLS o HTTPS? |
| **Validación DNSSEC** | ¿Comprueba las firmas y descarta respuestas falsificadas? |

En casa la velocidad no decide (las diferencias son de pocos milisegundos y solo en la primera consulta de cada dominio): deciden privacidad y filtrado. En un servidor, lo razonable es el resolutor del propio proveedor: está en el mismo centro de datos y un servidor no tiene historial de navegación que proteger.

### Dónde informarse sin caer en un resolutor falso

- **Privacy Guides** (`privacyguides.org/en/dns/`): proyecto sin ánimo de lucro ni afiliados, con criterios explícitos.
- **La web oficial de cada resolutor**, para copiar sus IPs y leer su política. **Nunca** de un blog, un foro o una lista masiva de «servidores DNS públicos»: muchas son equipos mal configurados y algunas están montadas para falsificar respuestas.
- Señales de fiabilidad: organización conocida con sede, política de privacidad pública, DNS cifrado y auditorías externas.

| Columna de Privacy Guides | Qué significa |
|---|---|
| **Protocols** | *Cleartext* es DNS clásico (UDP 53, sin cifrar). DoH, DoT, DoQ y DNSCrypt son variantes cifradas |
| **Logging** | *No*: no guarda nada. *Anonymized*: guarda sin asociar a la IP |
| **ECS** | *EDNS Client Subnet*: pasa un trozo de tu IP al autoritativo para que elija servidor cercano. Mejora la puntería de los CDN pero revela tu zona |
| **Filtering** | *Based on server choice*: cada proveedor tiene varias IPs, unas filtran y otras no |
| **Signed Apple Profile** | Configuración para iPhone y Mac. Irrelevante en Linux |

El DNS cifrado **no oculta la navegación**: la operadora sigue viendo a qué IP te conectas y el nombre del sitio en el SNI de TLS.

### De dónde saca el DNS el portátil

`systemd-resolved` reenvía a los servidores que NetworkManager le asigna en la interfaz de salida, tomados de una de estas fuentes, por orden:

```
1. DNS puesto a mano en la conexión del portátil      ← si existe, manda este
2. Lo que reparte el router por DHCP al conectarse     ← si no hay manual
3. Fallback DNS Servers de systemd-resolved             ← solo si no hay ninguno
(+) Una VPN activa puede imponer los suyos mientras está conectada
```

Por DHCP, el router entrega a cada dispositivo su IP privada, la puerta de enlace y **el DNS**. Por eso configurar el DNS en el router lo aplica a todos los dispositivos de casa que lo acepten. Matices: muchos routers de operadora no dejan cambiarlo; otros se ponen a sí mismos como DNS y reenvían; y esa configuración solo vale **en casa**.

## 8. Cómo bloquea la operadora

**Bloqueo por DNS.** La operadora carga una lista de dominios en **su resolutor** y, para esos dominios, **contesta con una mentira**: `NXDOMAIN`, un `A` hacia su página de «bloqueado» o una IP que no lleva a ningún sitio. El cliente se lo cree porque DNS clásico no lleva prueba de autenticidad (DNSSEC la daría, pero la máquina no la comprueba). **Cambiar de resolutor lo esquiva.**

| Mecanismo | Cómo funciona | ¿Lo esquiva cambiar de resolutor? |
|---|---|---|
| Bloqueo por DNS | El resolutor de la operadora miente | Sí |
| **Bloqueo por IP** | Corta el tráfico hacia la IP del servidor, da igual quién la resolviera. Tumba todo lo que comparta esa IP | No |
| Interceptar el puerto 53 | Como DNS clásico va sin cifrar, captura la consulta a `8.8.8.8` y contesta ella | No; hace falta DNS cifrado |
| Mirar el SNI | Al abrir HTTPS, el nombre del sitio viaja visible al inicio del handshake de TLS (Bloque 4) | No |

**Un código HTTP nunca viene de DNS.** Para recibirlo, DNS tuvo que dar una IP, abrirse una conexión TCP y **alguien contestar**. Un bloqueo por DNS daría «no se encuentra el sitio».

### Por qué una VPN esquiva el bloqueo por IP

Es **encapsulación**: el portátil cifra el paquete original entero, incluida la IP de destino, y lo mete dentro de otro paquete dirigido al servidor de la VPN, que lo saca y lo envía desde su IP.

```
Lo que ve la operadora:
[ destino: servidor VPN ][ ▓▓▓▓▓▓ cifrado ▓▓▓▓▓▓ ]
```

Con VPN, la operadora no ve **la IP de destino, ni las consultas DNS, ni el SNI**. Límites: puede bloquear la propia VPN; el proveedor de la VPN pasa a verlo todo; y para el destino se viene del país de la VPN.

## 9. Analogías de referencia

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

# Parte 2 · Ejemplos

## El recorrido de `mediavida.com` con `dig +trace`

En el portátil: `dig -4 +trace mediavida.com`.

| Bloque | Contesta | Tipo | Dice |
|---|---|---|---|
| 0 | `systemd-resolved` (`127.0.0.53`) | `NS` | «Los 13 servidores raíz son `a`–`m`.root-servers.net» |
| 1 | Raíz (`a.root-servers.net`) | `NS` | «Para `.com`, pregunta a estos» |
| 2 | TLD (`b.gtld-servers.net`) | `NS` | «Para `mediavida.com`, pregunta a `christina` o `damian` (Cloudflare)» |
| 3 | Autoritativo (`christina.ns.cloudflare.com`) | **`A`** | «La IP es `84.17.59.120`» |

- El bloque 0 tardó 5 ms: caché y loopback, sin salir de la máquina.
- Dos autoritativos, 13 raíces y 13 TLD de `.com`: redundancia, sin punto único de fallo.
- Mediavida no gestiona su propio DNS: lo contrata a Cloudflare.
- Consultas seguidas a `mediavida.com` devolvían IPs distintas (`.115`, `.117`, `.119`, `.120`): reparto de carga con varios `A`.
- La primera resolución tardó 55 ms; la segunda, 8 ms: la caché.

## La delegación de `odoo.mlozano.dev` con `dig +trace`

En el portátil: `dig -4 +trace odoo.mlozano.dev`. Sin las líneas `DS`, `RRSIG` y `NSEC3`:

```
.                 NS   a.root-servers.net.                  (y 12 más)
;; Received 1097 bytes from 127.0.0.53#53(127.0.0.53) in 12 ms

dev.              NS   ns-tld5.charlestonroadregistry.com.  (y 4 más)
;; Received 764 bytes from 192.5.5.241#53(f.root-servers.net) in 4 ms

mlozano.dev.      NS   gannon.ns.cloudflare.com.
mlozano.dev.      NS   autumn.ns.cloudflare.com.
;; Received 382 bytes from 216.239.34.105#53(ns-tld2.charlestonroadregistry.com) in 30 ms

odoo.mlozano.dev. A    89.58.45.111
;; Received 61 bytes from 162.159.44.59#53(gannon.ns.cloudflare.com) in 5 ms
```

| Bloque | Servidor que contesta | Columna 1 | Columna 4 | Columna 5 |
|---|---|---|---|---|
| 0 | `127.0.0.53` (resolutor local) | `.` | `NS` | 13 raíces |
| 1 | `f.root-servers.net` (raíz) | `dev.` | `NS` | 5 servidores del TLD `.dev` |
| 2 | `ns-tld2.charlestonroadregistry.com` (TLD) | `mlozano.dev.` | `NS` | `gannon`, `autumn` |
| 3 | `gannon.ns.cloudflare.com` (autoritativo) | `odoo.mlozano.dev.` | **`A`** | `89.58.45.111` |

- *Charleston Road Registry* es la empresa de Google que gestiona el TLD `.dev`.
- El bloque 2 es la prueba de que el registrador (Cloudflare) dio de alta los autoritativos en el TLD al comprar el dominio.
- `ns-tld2` es uno de los cinco que nombró la raíz en el bloque 1, y `gannon`, uno de los dos que nombró el TLD en el bloque 2.

## Respuesta del autoritativo frente a la de un resolutor

| Consulta | `aa` | TTL de `mediavida.com` |
|---|---|---|
| `dig @christina.ns.cloudflare.com mediavida.com` | Sí | `35`, siempre |
| `dig @1.1.1.1 mediavida.com`, varias veces | No | `33`, `35`, `35`, `22` |

Los TTL de `1.1.1.1` saltan porque detrás de esa IP hay cientos de servidores, cada uno con su caché. Un `35` significa que esa máquina acababa de ir al autoritativo.

## Un nombre que no existe

`dig estedominionoexiste12345.com` devuelve `status: NXDOMAIN`, `ANSWER: 0` y una `AUTHORITY SECTION` con el `SOA` de `com.`: quien afirma que no existe es el TLD, que sabe qué dominios `.com` están delegados.

## Un nombre que existe sin fichas de ese tipo

`dig mlozano.dev` (sin tipo, así que pide `A`) devuelve `status: NOERROR`, `ANSWER: 0` y una `AUTHORITY SECTION` con el `SOA` de `mlozano.dev.`, cuyo primer campo es `autumn.ns.cloudflare.com.`. El dominio existe, pero en la raíz no hay ningún `A`: las fichas están en `odoo.mlozano.dev`. Repetida 90 s después, el TTL del `SOA` había bajado de `600` a `510` y `Query time` era `0 msec`: la respuesta negativa salía de la caché de `systemd-resolved`.

## Un alias: `www.wikipedia.org`

`dig www.wikipedia.org` devuelve dos fichas: el `CNAME` de `www.wikipedia.org` hacia `dyna.wikimedia.org`, con TTL `11930`, y la IP de `dyna.wikimedia.org`, con TTL `107`. El resolutor siguió el alias él solo.

El alias casi nunca cambia (TTL de más de tres horas); la IP cambia a menudo porque Wikipedia manda a cada usuario a su centro de datos más cercano (`dyna`, dinámico): TTL de menos de dos minutos.

## El correo de `kogniatech.es`

```
kogniatech.es.  IN  MX   10 mx00.ionos.es.
kogniatech.es.  IN  TXT  "v=spf1 include:_spf-eu.ionos.com ~all"
kogniatech.es.  21600 IN SOA ns1051.ui-dns.com. hostmaster.1und1.com. 2017060123 28800 7200 604800 600
```

(Hay un segundo `MX` de IONOS con la misma prioridad.)

| Parte | Lectura |
|---|---|
| Dos `MX` con prioridad `10` | El correo se reparte entre los dos servidores de IONOS; ninguno es de reserva |
| `v=spf1` | Política SPF, versión 1 |
| `include:_spf-eu.ionos.com` | Pueden enviar los servidores que lista IONOS |
| `~all` | Cualquier otro es sospechoso |
| `ns1051.ui-dns.com.` | Autoritativo principal, infraestructura de IONOS |
| `hostmaster.1und1.com.` | Email del responsable; 1&1 es el nombre antiguo de IONOS |
| `600` | Caché negativa: `min(600, 21600) = 600` s |

## El `PTR` del VPS

```
$ dig +noall +answer -x 89.58.45.111
111.45.58.89.in-addr.arpa.  21600  IN  PTR  v2202609416983518596.powersrv.de.
```

El nombre genérico de Netcup. Si el VPS llega a enviar correo (alertas, Odoo), habrá que cambiar el `PTR` desde el panel de Netcup para que encaje con el dominio.

## Registros de `mlozano.dev` para el VPS

Zona de `mlozano.dev` en Cloudflare:

| Name | Type | Content | Proxy status | TTL |
|---|---|---|---|---|
| `actual` | Tunnel | `finances` (servicio en el portátil) | Proxied | Auto |
| `odoo` | `A` | `89.58.45.111` | DNS only | Auto (300 s) |
| `odoo` | `AAAA` | `2a03:4000:67:5e2:c456:77ff:fe3a:fc4c` | DNS only | Auto (300 s) |

```
raíz ──NS──▶ TLD .dev ──NS──▶ Cloudflare ──A/AAAA──▶ VPS
```

- Odoo va en el subdominio `odoo`; la raíz queda libre. El registro `Tunnel` de `actual` no interfiere: es otro nombre.
- Las IPs salen del VPS: `ip -4 address show dev eth0` y `ip -6 address show dev eth0 scope global` (sin la máscara).
- Al crear el `A`, el formulario traía el proxy activado y la frase *«has its traffic proxied through Cloudflare»*: había que apagarlo. Sin proxy, el TTL pasa a ser editable.

Comprobación, en el portátil:

| Consulta | Resultado |
|---|---|
| `dig @autumn.ns.cloudflare.com odoo.mlozano.dev A` | `odoo.mlozano.dev. 300 IN A 89.58.45.111`, con `aa` |
| `dig @autumn.ns.cloudflare.com odoo.mlozano.dev AAAA` | `… 300 IN AAAA 2a03:4000:67:5e2:c456:77ff:fe3a:fc4c` |
| `dig @1.1.1.1 odoo.mlozano.dev A` | `… 300 IN A 89.58.45.111`, sin `aa`: esa máquina de `1.1.1.1` acababa de ir a la fuente |

## Migración con un TTL de un día

Un `A` con TTL de 86400 s y migración el sábado a las 10:00:

1. Bajar el TTL a 300 **el viernes a las 10:00 o antes**.
2. El sábado, cambiar la IP: nadie tarda más de 5 minutos en verla.
3. Días después, volver a subir el TTL.

Si se baja el TTL el sábado a las 10:00, un resolutor que guardó la ficha a las 9:59 con 86400 s sigue con la IP vieja hasta el domingo a las 9:59.

## La trampa de la caché negativa

Se consulta `erp.cliente.es` antes de crearlo: `NXDOMAIN`. Se crea el registro y se vuelve a consultar: sigue `NXDOMAIN` durante el mínimo del `SOA` (10 minutos con un `SOA` como el de `kogniatech.es`). Diagnóstico: `dig NS cliente.es` para saber el autoritativo y `dig @AUTORITATIVO erp.cliente.es`: si da `NOERROR` con `aa`, está bien; solo hay que esperar.

## Medir resolutores desde casa

Siete rondas de `dig @RESOLUTOR example.org | grep "Query time"` en el portátil:

| Resolutor | Media |
|---|---|
| Quad9 `9.9.9.9` | 3,0 ms |
| Cloudflare `1.1.1.1` | 4,0 ms |
| Google `8.8.8.8` | 5,9 ms |

Los tres tienen servidores muy cerca. `example.org` estaba en la caché de los tres, así que se midió la **distancia**, que es lo que interesa al comparar. Diferencia irrelevante; Quad9 encaja además por filtrado de malware por defecto y ECS opcional.

## De dónde venía el DNS del portátil

| Dato | Valor | Lectura |
|---|---|---|
| `resolvectl status`, interfaz `enp5s0` | `8.8.8.8` y `8.8.4.4` | Usaba Google |
| `ipv4.dns` de `Wired connection 1` | `--` | Sin DNS puesto a mano |
| `ipv4.ignore-auto-dns` | `no` | Acepta el DNS del router |
| Conclusión | | **El `8.8.8.8` venía del router**, que lo repartía por DHCP |

Otras líneas de `resolvectl status` en el portátil: `resolv.conf mode: foreign` (NetworkManager), `Fallback DNS Servers` con Quad9, Cloudflare y Google (los de emergencia que trae `systemd-resolved` en Arch), interfaces `veth…`, `br-…` y `docker0` de Docker sin DNS, `LLMNR` y `mDNS` (nombres locales tipo `impresora.local` sin servidor DNS), `DNSOverTLS` desactivado y `DNSSEC=no/unsupported`. La conexión VPN `kognia` impone sus propios DNS cuando está activa.

**El cambio a Quad9:**

1. En el router (HGU Mitrastar de O2), apartado del servidor DHCP: `9.9.9.9` y `149.112.112.112`, copiadas de `quad9.net`. Valores anteriores: `8.8.8.8` y `8.8.4.4`.
2. En el portátil: `nmcli connection up "Wired connection 1"` para pedir de nuevo la configuración.
3. `resolvectl status` muestra Quad9 en `enp5s0`. En `dig`, `SERVER` sigue siendo `127.0.0.53`: la secretaria no cambia, solo a quién llama.

## El resolutor del VPS

`resolvectl status` en el VPS: `resolv.conf mode: stub` y `Current DNS Server: 46.38.252.230`, el resolutor de Netcup (cuatro en la lista, dos IPv4 y dos IPv6). `ls -l /etc/resolv.conf` muestra el enlace a `/run/systemd/resolve/stub-resolv.conf`. Se deja así.

## pixeldrain.com, capa por capa

En el navegador, `http://pixeldrain.com` mostraba un `451` y `https://pixeldrain.com` daba *Unable to connect*.

| Capa | Prueba | Resultado | Conclusión |
|---|---|---|---|
| **DNS** | `dig @8.8.8.8` y `dig @1.1.1.1` | Mismas IPs (`203.23.179.11` y `.12`), en distinto orden y con distinto TTL | **No hay bloqueo DNS** |
| **HTTP, puerto 80** | Navegador | Página genérica, sin cifrar | Alguien responde en nombre de pixeldrain |
| **HTTPS, puerto 443** | Navegador | No conecta | Se estudia con `curl -v` en el Bloque 3: TCP sí se abre y el corte llega tras el `Client hello` de TLS |

Cambiar de resolutor no sirvió porque el bloqueo no está en DNS: es sobre el tráfico (por IP o mirando el SNI, Bloque 4), con una respuesta inyectada en lo que va sin cifrar.

## Confusiones vistas

| Confusión | Corrección |
|---|---|
| `127.0.0.53` está en mi subred | Es loopback: la propia máquina. Todo `127.0.0.0/8` lo es |
| `127.0.0.1` escucha en toda la red local | Eso es `0.0.0.0`. `127.0.0.1` es solo la propia máquina |
| El TLD devuelve la IP del dominio | Devuelve los `NS` de los autoritativos: el *dónde* |
| El TLD que contesta es el autoritativo | El TLD **dice quiénes son** los autoritativos; estos todavía no han hablado |
| Tras resolver `odoo.com`, para otro `.com` hay que volver a la raíz | El resolutor ya tiene en caché los TLD de `.com` |
| `systemd-resolved` recorre la jerarquía | Es *stub*: reenvía de forma recursiva al resolutor de fuera |
| Raíz, TLD y autoritativo guardan caché | Solo los resolutores guardan copias |
| El `MX` apunta a la web del dominio | Su valor es el servidor de correo; web y correo son fichas independientes |
| Bajar el TTL el mismo día de la migración | Hay que bajarlo un TTL antiguo antes |
| Tras un `NXDOMAIN`, al crear el registro ya sale `NOERROR` | El `NXDOMAIN` está en caché durante el mínimo del `SOA` |
| `/etc/resolv.conf` dice qué resolutor de fuera se usa | Solo apunta a `127.0.0.53`. El de fuera está en `resolvectl status` |
| Cambiar el DNS en el router lo cambia en todos los dispositivos | Solo en los que aceptan el del router (sin DNS manual e `ignore-auto-dns: no`) |
| El `451` de pixeldrain es un bloqueo por DNS | DNS daba las IPs correctas en dos resolutores; un código HTTP no viene de DNS |
| Cambiar de resolutor esquiva cualquier bloqueo | Solo el de DNS |
| `dig` es una de las tres partes de la consulta | Es el programa. Las partes son a quién (`@`), por quién (nombre) y qué dato (tipo) |
| `dig -4 NOMBRE` pide la IPv4 | `-4` es una opción del programa (enviar por IPv4). Sin tipo, `dig` pide `A` igualmente |
| Preguntar por `mlozano.dev` para ver las fichas de `odoo.mlozano.dev` | Cada nombre tiene sus fichas. En la raíz no hay `A`: `NOERROR` con `ANSWER: 0` |
| Añadir `NS` al final hace que conteste el autoritativo | `NS` solo da los nombres de los autoritativos. Lo que hace que conteste uno es la `@` |
| El bloque 0 de `+trace` lo contesta la raíz | Lo contesta el resolutor local; habla **de** la raíz |
| El último bloque de `+trace` es el resolutor devolviendo la dirección | El resolutor solo interviene en el bloque 0. La dirección la da el autoritativo |
| El servidor que contesta el bloque de los `NS` de `mlozano.dev` es `gannon` | Es el TLD (`ns-tld2…`). `gannon` contesta el bloque siguiente. La línea Received va **debajo** de los registros de su bloque |
| Contar las columnas en la línea Received (`59#53`) | Las columnas solo existen en las líneas de registro |

## Preguntas frecuentes y cómo responderlas

| Pregunta | Comando (dónde) |
|---|---|
| ¿A qué IP apunta un nombre? | `dig +short NOMBRE` (portátil) |
| ¿Quién lleva el correo de un dominio? | `dig +noall +answer DOMINIO MX` |
| ¿Quiénes son los autoritativos de un dominio? | `dig +noall +answer DOMINIO NS` |
| ¿El dato está bien en la fuente, aunque las cachés no se hayan enterado? | `dig @AUTORITATIVO NOMBRE` y buscar `aa` |
| ¿Cómo va la propagación de un cambio? | `dig @1.1.1.1 NOMBRE`, `dig @8.8.8.8 NOMBRE` y `dig @9.9.9.9 NOMBRE`, comparando valor y TTL |
| ¿Dónde se rompe una resolución? | `dig -4 +trace NOMBRE`: el último bloque que responde bien |
| ¿Cuánto tardará en verse un cambio? | El TTL de la ficha en el autoritativo |
| ¿De quién es una IP que aparece en un log? | `dig +noall +answer -x IP` |
| ¿A qué resolutor reenvía esta máquina? | `resolvectl status`: interfaz con `Default Route: yes`, línea `DNS Servers` |
| ¿Por qué el portátil usa este DNS? | `nmcli -f ipv4.dns,ipv4.ignore-auto-dns connection show "Wired connection 1"` |
| ¿Qué resolutor es más rápido desde aquí? | `dig @RESOLUTOR example.org \| grep "Query time"`, varias rondas |
| ¿Un sitio bloqueado lo está por DNS? | `dig` contra dos resolutores públicos: si dan las mismas IPs, el bloqueo está en otra capa |
| Antes del certificado TLS del VPS, ¿el dominio apunta a él? | `dig +short odoo.mlozano.dev` debe dar `89.58.45.111` |
| ¿El nombre existe aunque no tenga ese tipo de ficha? | `dig NOMBRE TIPO`: `NOERROR` con `ANSWER: 0` (existe) frente a `NXDOMAIN` (no existe) |
| ¿Está bien hecha la delegación de un dominio recién comprado? | `dig -4 +trace NOMBRE`: el bloque del TLD debe listar los autoritativos del proveedor de DNS |

---

# Parte 3 · Comandos útiles del bloque

## Instalación

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `sudo pacman -S bind` | Instalar `dig` en el portátil; `-S` (*sync*) instala desde los repositorios | En Arch, `dig` viene dentro del paquete `bind` |
| `sudo apt install bind9-dnsutils` | Instalar `dig` en el VPS | La imagen mínima de Ubuntu no lo trae. Hará falta en Linux · Bloque 3 para comprobar el dominio antes de pedir el certificado |
| `dig -v` | Versión instalada | Antes de consultar `man dig`, saber de qué versión es |

## `dig`: consultas

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `dig NOMBRE` | Registro `A` preguntando al resolutor del sistema (`127.0.0.53`), con la respuesta completa | Ver `status`, `flags`, respuesta y quién contestó |
| `dig NOMBRE TIPO` | Pedir otro registro: `MX`, `AAAA`, `NS`, `TXT`, `SOA`, `CNAME` | El tipo va detrás del nombre |
| `dig +short NOMBRE` | `+short`: solo el valor | Scripts, o sacar la IP para `curl -H "Host: …"` |
| `dig +noall +answer NOMBRE` | `+noall` apaga todas las secciones; `+answer` enciende solo la respuesta | La combinación del día a día. Las opciones `+` son de consulta; las `-`, del programa |

**Trampas comunes:** un `NXDOMAIN` puede venir de la caché negativa aunque el registro ya exista; lo que devuelve un resolutor es su copia, con el TTL restante. Sin tipo, `dig` pide `A`; `-4` no es un tipo. Preguntar por la raíz cuando la ficha es de un subdominio da `ANSWER: 0`.

## `dig`: elegir a quién preguntar

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `dig @SERVIDOR NOMBRE` | `@`: pregunta a un servidor concreto (IP o nombre) en vez de al resolutor del sistema | Contra un autoritativo (sacarlo con `dig NOMBRE NS`): el dato real sin caché, con `aa`; sale `WARNING: recursion requested but not available`, que es normal. Contra `1.1.1.1`, `8.8.8.8` o `9.9.9.9`: ver la propagación. Los TTL de `1.1.1.1` saltan entre consultas |
| `dig @SERVIDOR example.org \| grep "Query time"` | Solo la línea del tiempo de respuesta; `\|` pasa la salida a `grep`, comillas por el espacio | Comparar resolutores con varias rondas. Un dominio popular mide la distancia; uno raro, también el recorrido completo |

## `dig`: recorrido e inversa

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `dig -4 +trace NOMBRE` | `+trace`: recorre la jerarquía desde la raíz, salto a salto; `-4`: solo IPv4 | Diagnosticar dónde se rompe una resolución; tras comprar un dominio, ver que el TLD apunta a tus autoritativos. Leer cada bloque con el método de §5: servidor que contesta (línea Received), columnas 1, 4 y 5. Sin `-4`, en una red sin IPv6 salen errores `network unreachable` inofensivos. Ignorar `RRSIG`, `DS`, `NSEC3` |
| `dig +noall +answer -x IP` | `-x`: consulta inversa (`PTR`), construye sola el nombre `.in-addr.arpa` | Identificar IPs de `/var/log/auth.log` o de los logs de nginx; comprobar el `PTR` antes de enviar correo desde el VPS. Lo controla el dueño del bloque de IPs |

## El resolutor del sistema

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `cat /etc/resolv.conf` | Ver a qué servidor DNS preguntan los programas | Siempre dirá `127.0.0.53`: no enseña el resolutor de fuera |
| `ls -l /etc/resolv.conf` | `-l` formato largo: si es un enlace simbólico (`l` inicial) y a dónde apunta (`->`) | En Ubuntu apunta a `/run/...`: no editar a mano, se sobrescribe. El DNS del VPS se cambiaría por netplan (Linux · Bloque 3) |
| `resolvectl status` | Modo de `systemd-resolved` y a qué servidores reenvía en cada interfaz | Primer paso cuando una máquina no resuelve. Líneas clave: `resolv.conf mode`, `Current DNS Server`, `DNS Servers` de la interfaz con `Default Route: yes`. No necesita `sudo`. Ignorar `veth…`, `br-…`, `docker0`, `LLMNR`, `mDNS` |

## Interfaces y sockets

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `ip a` | Interfaces y direcciones | IP pública del VPS: `eth0`, `inet`, `scope global`. `lo` es loopback (`127.0.0.1/8`) |
| `ip -4 address show dev eth0` / `ip -6 address show dev eth0 scope global` | Solo la IPv4 / solo la IPv6 pública de `eth0`; `scope global` descarta la `fe80::` de enlace local | Copiar la dirección para un registro `A` o `AAAA`, sin lo que va detrás de la `/` |
| `sudo ss -tulpn \| grep 127.0.0.53` | Quién escucha en esa dirección: `-t` TCP, `-u` UDP, `-l` escuchando, `-p` proceso, `-n` números | Confirmar que en el 53 está `systemd-resolved`. Sin `sudo`, no sale el proceso |

## NetworkManager (portátil)

| Sintaxis | Para qué | Cuándo / trampas |
|---|---|---|
| `nmcli connection show` | Conexiones guardadas; `DEVICE` dice cuál va por qué interfaz (`--` = inactiva) | Saber el nombre exacto de la conexión activa |
| `nmcli -f ipv4.dns,ipv4.ignore-auto-dns connection show "Wired connection 1"` | `-f` (*fields*): solo esos campos. `ipv4.dns` = DNS a mano (`--` ninguno); `ipv4.ignore-auto-dns` = `yes` ignora el del router | Antes de cambiar el DNS en el router, comprobar que el portátil le hará caso. El nombre lleva espacios: **entre comillas** |
| `nmcli connection up "Wired connection 1"` | Reactiva la conexión y pide de nuevo la configuración por DHCP | Aplicar un cambio del router sin reiniciar; verificar después con `resolvectl status`. Corta la red un instante |

## Documentación

| Referencia | Para qué | Cuándo |
|---|---|---|
| Kurose y Ross, 8.ª ed., 2.4 (2.4.1 servicios, 2.4.2 funcionamiento y caché, 2.4.3 registros y mensajes) | La base del bloque | Repasar jerarquía, recorrido y formato del mensaje |
| Grigorik, *High Performance Browser Networking*, cap. 1 (hpbn.co) | Latencia y su coste | Contexto del porqué de la caché |
| RFC 2308, sección 5 | Caché negativa | Duda exacta sobre cuánto se guarda un `NXDOMAIN` |
| RFC 1034 y 1035 | Definición original de DNS | Dudas concretas, no lectura entera |
| `privacyguides.org/en/dns/` | Evaluación independiente de resolutores | Elegir resolutor |
| `quad9.net`, `developers.google.com/speed/public-dns`, la página de `1.1.1.1` de Cloudflare | IPs y políticas oficiales | Copiar IPs de resolutores: solo de aquí |
| `man dig`, `man resolvectl`, `man systemd-resolved`, `man nmcli` | Opciones en la versión instalada | Antes de usar una opción nueva |
