# Scripting · Bloque 1 · Plan

**Carril:** Linux y VPS (Q1). **Franja:** 30 min diarios con temporizador propio, independiente del carril de 2 h.
**Lenguaje:** bash. Python entra más adelante, cuando la lógica de un script se haga difícil de leer en bash (JSON, peticiones HTTP, procesamiento de datos).
**Entorno:** `backend-lab` (Ubuntu 24.04, bash 5.2) y portátil (CachyOS). Los scripts llevan `#!/usr/bin/env bash`: aunque tu shell de uso sea `fish`, los scripts se ejecutan con bash.

**Límite de la franja:** a los 25 min no se empieza nada nuevo; a los 30 se cierra en el punto limpio más cercano.

---

## Fase 1 · Bases (sesiones 1 a 7)

Cada sesión sigue el método del plan: problema real, bibliografía, objetivos comprobables y los conceptos conectados con el problema.

### Sesión 1 · Del comando al script

**El problema.** Cada vez que algo parece raro en `backend-lab` escribes a mano `systemctl status odoo`, `df -h /` y `ss -tlnp`. Quieres un fichero que lo haga por ti.

**Bibliografía.** *The Linux Command Line* (Shotts), 3.ª ed., Parte IV, cap. 24 «Writing Your First Script».

**Objetivos.**
1. Crear `estado.sh` con esos tres comandos, con shebang `#!/usr/bin/env bash`.
2. Hacerlo ejecutable (`chmod +x`) y lanzarlo como `./estado.sh`.
3. Comprobar con `file estado.sh` que el sistema lo reconoce como script ejecutable.

**Lo importante.** Un script es un fichero de texto con comandos que la shell ejecuta en orden. El shebang dice qué programa lo interpreta. Sin `chmod +x` el sistema no lo considera ejecutable. Sin `./` la shell busca el nombre en el `PATH` y no en la carpeta actual.

### Sesión 2 · Variables, comillas y argumentos

**El problema.** Quieres `./estado.sh odoo` para consultar un servicio concreto, sin editar el script cada vez.

**Bibliografía.** Shotts, 3.ª ed., Parte IV, apartado de variables y parámetros posicionales (consultar el índice detallado de la edición instalada; el capítulo 32 de la 2.ª ed. es el equivalente).

**Objetivos.**
1. Leer el primer argumento con `$1` y guardarlo en una variable.
2. Mostrar un mensaje de uso por la salida de error (`>&2`) si no se pasa argumento, y salir con código distinto de 0.
3. Usar `"$1"` entrecomillado y comprobar qué pasa con un argumento que contenga espacios.

**Lo importante.** `$1` es el primer argumento, `$#` cuántos hay, `$?` el código de salida del último comando. Las comillas evitan que la shell parta un valor en varios.

### Sesión 3 · Decidir: códigos de salida e `if`

**El problema.** Quieres saber si Odoo responde, no solo ver su salida. Un script que avisa necesita una respuesta sí o no.

**Bibliografía.** Shotts, 3.ª ed., Parte IV, apartado de condicionales (`if`); en la 2.ª ed., cap. 27. Conecta con lo visto en Redes · Bloque 3 (`curl` y su código de salida).

**Objetivos.**
1. Crear `odoo-ok.sh` que consulte `http://localhost:8069` con `curl -s -o /dev/null -w '%{http_code}'`.
2. Salir con `0` si la respuesta es `200` y con `1` en cualquier otro caso.
3. Comprobar los dos caminos: con Odoo arrancado y con Odoo parado (`sudo systemctl stop odoo`, y luego volver a arrancarlo).

**Lo importante.** Cada comando devuelve un código: `0` es éxito, cualquier otro valor es fallo. Un script se comunica con quien lo llama a través de ese código. `if` decide según el resultado.

### Sesión 4 · Repetir: `for` y `while`

**El problema.** Tienes una lista de servicios o dominios y quieres revisarlos todos con un solo comando.

**Bibliografía.** Shotts, 3.ª ed., Parte IV, apartados de bucles `for` y `while`; en la 2.ª ed., caps. 29 y 33.

**Objetivos.**
1. Crear `servicios.txt` con tres nombres de servicio, uno por línea.
2. Recorrerlo con `while read -r linea; do ... done < servicios.txt` y mostrar el estado de cada uno.
3. Hacer lo mismo con `for` sobre una lista escrita en el propio script y explicar la diferencia con tu compañero de sesión (o con tus notas).

**Lo importante.** `while read` lee un fichero línea a línea. `for` recorre una lista de palabras. Usar `-r` en `read` evita que las barras invertidas se interpreten.

### Sesión 5 · Modo estricto y fallos

**El problema.** Un script de backup falla a mitad, pero sigue y deja un fichero vacío con nombre correcto. Nadie se entera hasta que lo necesitas.

**Bibliografía.** Shotts, 3.ª ed., Parte IV, apartado de depuración (*troubleshooting*); en la 2.ª ed., cap. 30. Manual de bash, apartado «The Set Builtin» (gnu.org/software/bash/manual, sección 4.3.1).

**Objetivos.**
1. Escribir un script con un `false` en medio y comprobar que sin modo estricto sigue ejecutándose.
2. Añadir `set -euo pipefail` y comprobar que se detiene en el `false`.
3. Ejecutar un script con `bash -x` y leer la salida: cada línea marcada con `+` es lo que se ejecutó de verdad.

**Lo importante.** `-e` detiene el script al primer fallo. `-u` trata las variables sin valor como error. `pipefail` hace que una tubería falle si falla cualquiera de sus comandos. `set -e` tiene excepciones (un comando dentro de un `if` no lo dispara); las veremos al llegar a ellas en los ejercicios diarios.

### Sesión 6 · Funciones, mensajes y limpieza

**El problema.** Los mensajes salen sin fecha ni origen, y el script deja ficheros temporales si falla a mitad.

**Bibliografía.** Shotts, 3.ª ed., Parte IV, apartado de funciones (consultar el índice detallado). Página de `logger`: manpages.ubuntu.com, sección *noble*.

**Objetivos.**
1. Escribir una función `log()` que muestre fecha y mensaje por la salida de error.
2. Usar `local` para variables dentro de una función.
3. Crear un fichero temporal con `mktemp` y borrarlo con `trap 'rm -f "$tmp"' EXIT`. Comprobar que se borra aunque el script falle.

**Lo importante.** Una función agrupa comandos con nombre. `local` evita que una variable se filtre al resto del script. `trap` ejecuta código al salir, con éxito o con fallo: es la red de seguridad de cualquier script que toca ficheros.

### Sesión 7 · Integrador: mini-backup con rotación

**El problema.** Quieres copiar un directorio cada día, conservar solo las últimas tres copias y no dejar nunca una copia incompleta.

**Bibliografía.** Repaso de las sesiones 1 a 6. Shotts, 3.ª ed., Parte IV, ejemplos del final de la parte (escribir scripts útiles).

**Objetivos.**
1. Script que reciba un directorio de origen, cree un `tar.gz` con fecha en el nombre y lo guarde en un directorio de destino.
2. Borrar copias antiguas dejando solo las tres últimas.
3. Escribir primero en un fichero temporal y renombrar al final: si falla, no queda ninguna copia con nombre válido.

**Lo importante.** Esta sesión es la versión pequeña del Artefacto 1 de `progreso.md`. Cierra la Fase 1 y deja la base del backup automatizado de Linux · Bloque 4.

---

## Fase 2 · Ejercicio diario (sesiones 8 en adelante)

Desde la sesión 8, cada día es un ejercicio de 10 a 20 minutos sobre un escenario de tu entorno, con un criterio de éxito escrito antes de empezar. Los últimos 10 minutos de la franja son para repasar el ejercicio y, a partir de la sesión 8, para pasar el script por `shellcheck` (instalación y uso se verán en esa sesión).

Escenarios de partida, por orden aproximado (se generan uno a uno, no todos de golpe):

1. Avisar si el disco supera un porcentaje de uso (`df`).
2. Conservar solo las N copias más recientes de un directorio.
3. Comprobar que un fichero de dump existe y no está vacío antes de darlo por bueno.
4. Leer `db_name` de `odoo.conf` sin tocar el fichero.
5. Esperar a que un servicio responda, con reintentos y tiempo máximo.
6. Buscar errores de las últimas horas en el journal de Odoo (`journalctl`, filtro por tiempo).
7. Validar que un dominio resuelve y responde (`dig` y `curl`, enlazando con Redes · Bloques 2 y 3).
8. Sumar columnas de un CSV con `awk`.

**Criterio de cierre del bloque:** escribir un script con argumentos, comprobación de errores, función y limpieza, sin que `shellcheck` dé avisos, y explicar en voz alta por qué se usa `set -euo pipefail`.

**Relación con el roadmap:** el Artefacto 1 (backup de base y *filestore*) se hace después de Linux · Bloque 4, con H2. Este bloque lo prepara.

---

## Referencias

| Dónde | Referencia |
|---|---|
| Manual de bash (versión instalada: 5.2) | gnu.org/software/bash/manual, sección *The Set Builtin* (4.3.1) para `set -euo pipefail` |
| Páginas de `man` del VPS | manpages.ubuntu.com, sección *noble*: `man bash`, `man logger`, `man mktemp` |
| Herramienta de revisión | Wiki de ShellCheck (github.com/koalaman/shellcheck/wiki), entrada del código de aviso que salga |
| Libro | Shotts, *The Linux Command Line*, 3.ª ed., Parte IV, «Writing Shell Scripts» (cap. 24 «Writing Your First Script», confirmado en la edición 3) |

Los números de capítulo de la 2.ª edición citados arriba corresponden a la numeración del roadmap. Antes de cada sesión se comprueban en el índice detallado de la edición que tengas.
