# PostgreSQL · Bloque 1 — Joins, agregaciones, subconsultas, CTEs y window functions

Carril de PostgreSQL: **miércoles, 1 h**. Continúa sobre el laboratorio montado en el Bloque 0 (Pagila).

**Contenido del bloque (roadmap):** joins, agregaciones, subconsultas, CTEs y window functions. Escrito contra una base con datos reales, no solo leyendo documentación.

**Criterio de cierre:** poder explicar en voz alta, sin notas, la diferencia entre `WHERE` y `HAVING`, entre `GROUP BY` y `PARTITION BY`, y por qué `HAVING` no puede usar un alias del `SELECT` pero `ORDER BY` sí.

**Entorno:** Pagila (versión 4.1, con categorías muchos-a-muchos — ver nota en la sección de joins).

---

## 1. JOIN — juntar lo que el modelo separó

Recordando el Bloque 0: los datos viven troceados a propósito (normalización). El título en `film`, el actor en `actor`, y solo un número los une. `JOIN` es el acto de volver a juntarlos.

### Sintaxis general

```sql
SELECT tabla_a.columna, tabla_b.columna
FROM tabla_a
JOIN tabla_b ON tabla_a.columna_comun = tabla_b.columna_comun;
```

- `JOIN` a secas es sinónimo de `INNER JOIN` — el más usado.
- `ON` dice cómo se corresponden las filas de una tabla con las de otra.
- `tabla.columna` siempre lleva **un punto**, nunca `tabla.columna.algo` — ese es el error clásico de escribir `fc.category.id` en vez de `fc.category_id`.

### Alias

```sql
FROM film f
JOIN language l ON f.language_id = l.language_id
```

`film f` le pone el apodo `f` a la tabla para el resto de la consulta. Es obligatorio usar alias distintos cuando la misma tabla aparece dos veces en una consulta (típico en subconsultas anidadas, ver más abajo).

### INNER JOIN — relación directa

```sql
SELECT f.title, l.name
FROM film f
JOIN language l ON f.language_id = l.language_id;
```

Trae solo las filas que tienen coincidencia en ambos lados.

### INNER JOIN encadenado — relación muchos-a-muchos vía tabla intermedia

```sql
SELECT f.title, a.first_name, a.last_name
FROM film f
JOIN film_actor fa ON f.film_id = fa.film_id
JOIN actor a ON fa.actor_id = a.actor_id
WHERE f.title = 'ACADEMY DINOSAUR';
```

`film_actor` guarda dos referencias, una a cada lado (`film_id`, `actor_id`). `film` nunca conoce `actor_id` directamente — solo la tabla intermedia sabe emparejar ambos lados.

**Qué implica encadenar joins:** cada `JOIN` nuevo se engancha al resultado combinado que ya se lleva, no a la tabla original. Si el primer `JOIN` ya multiplicó filas (una película con 15 actores da 15 filas), el segundo `JOIN` actúa sobre esas 15 filas ya multiplicadas.

**Nota sobre Pagila 4.1:** en esta versión, `film_category` es *también* una relación muchos-a-muchos (una película puede tener varias categorías), a diferencia del Sakila/Pagila "clásico" de una categoría por película. Por eso un `JOIN` de `film` + `film_category` + `category` puede devolver más de 1000 filas y el mismo título repetido bajo categorías distintas — no es un error de sintaxis, es un dato real del modelo.

### LEFT JOIN — conservar todo lo de la izquierda

```sql
SELECT c.name, f.title
FROM category c
LEFT JOIN film_category fc ON c.category_id = fc.category_id
LEFT JOIN film f ON fc.film_id = f.film_id;
```

Trae **todos** los de la tabla de la izquierda (`FROM`), tengan o no coincidencia. Si no la tienen, las columnas del lado derecho quedan en `NULL`.

**Uso más importante — encontrar lo que falta**, combinando `LEFT JOIN` con `WHERE ... IS NULL`:

```sql
SELECT a.first_name, a.last_name
FROM actor a
LEFT JOIN film_actor fa ON a.actor_id = fa.actor_id
WHERE fa.actor_id IS NULL;
```

Se lee: "actores para los que, al intentar emparejar con `film_actor`, no hubo nada que enganchar".

**Importante — nunca `= NULL`, siempre `IS NULL`.** `NULL` representa "desconocido", no un valor comparable. `WHERE columna = NULL` no da error, pero **siempre** devuelve 0 filas silenciosamente, porque comparar contra "lo desconocido" nunca es verdadero. La forma correcta es `IS NULL` / `IS NOT NULL`.

### Mezclar INNER y LEFT JOIN en la misma cadena

Cada `JOIN` de la cadena es independiente — se puede decidir salto a salto:

```sql
SELECT a.first_name, f.title, l.name
FROM actor a
LEFT JOIN film_actor fa ON a.actor_id = fa.actor_id
LEFT JOIN film f ON fa.film_id = f.film_id
JOIN language l ON f.language_id = l.language_id
```

**Cuidado:** un `INNER JOIN` después de un `LEFT JOIN` puede **cancelar** el efecto del `LEFT JOIN` anterior. Si un actor sin películas produce `fa.film_id = NULL`, y el siguiente `JOIN` (inner) exige `fa.film_id = f.film_id`, esa fila se descarta — el actor sin películas desaparece igual que si el `LEFT JOIN` no hubiera existido. Regla práctica: decidir `INNER` vs `LEFT` pensando en si ese lado puede no tener coincidencia y si se quiere conservar la fila igualmente, y vigilar que un `INNER JOIN` posterior no destruya lo que un `LEFT JOIN` anterior quiso preservar.

### Utilidad de JOIN, en resumen

1. Mostrar datos legibles en vez de números de referencia (nombre del cliente en vez de `cliente_id = 42`).
2. Combinar entidades relacionadas para un informe.
3. Relaciones muchos-a-muchos: sin `JOIN` no hay forma de responder "¿qué actores salen en esta película?".
4. Filtrar usando condiciones de otra tabla, aunque el resultado final solo muestre columnas de la primera.

### Consultar columnas de varias tablas sin el "churro" de `\d`

```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name IN ('film', 'film_actor', 'actor')
ORDER BY table_name, ordinal_position;
```

Más ligero que `\d` completo cuando la tabla tiene muchos índices/triggers (como `film`). Para tablas pequeñas, `\d tabla` sigue siendo rápido.

---

## 2. Agregaciones — GROUP BY, COUNT, HAVING

### La mecánica de GROUP BY, explicada con datos de mentira

Tabla `film_actor` reducida:

```
actor_id | film_id
---------+--------
   1     |   10
   1     |   11
   1     |   12
   2     |   10
   2     |   13
   3     |   10
```

**`GROUP BY actor_id`** reorganiza las filas en montones — uno por cada valor distinto de `actor_id` — sin contar nada todavía:

```
Montón actor_id=1: [(1,10), (1,11), (1,12)]   ← 3 filas
Montón actor_id=2: [(2,10), (2,13)]           ← 2 filas
Montón actor_id=3: [(3,10)]                   ← 1 fila
```

**`COUNT(*)`** actúa dentro de cada montón, por separado, y da una fila de salida por montón:

```
actor_id | count
---------+------
   1     |   3
   2     |   2
   3     |   1
```

### La regla de oro de GROUP BY

En el `SELECT`, solo se puede pedir:
1. La(s) columna(s) por la(s) que se agrupa.
2. Funciones de agregación (`COUNT`, `SUM`, `AVG`, `MAX`, `MIN`) sobre el resto.

Pedir una columna suelta que no está en el `GROUP BY` da: `column "x" must appear in the GROUP BY clause or be used in an aggregate function`.

**Por qué conviene agrupar por el id, no solo por el nombre:** `first_name`/`last_name` no garantizan unicidad (dos personas podrían compartir nombre). Agrupar por `actor_id` (o `customer_id`, `language_id`...) asegura que cada montón es realmente una entidad distinta, aunque esa columna no aparezca en el `SELECT`.

```sql
SELECT a.first_name, a.last_name, COUNT(*) AS num_peliculas
FROM actor a
LEFT JOIN film_actor fa ON a.actor_id = fa.actor_id
GROUP BY a.actor_id, a.first_name, a.last_name
ORDER BY num_peliculas DESC;
```

### WHERE filtra antes de agrupar, HAVING filtra después

**Orden real de ejecución de una consulta** (no el orden en que se escribe):

1. `FROM` / `JOIN`
2. `WHERE` — filtra filas sueltas, antes de agrupar
3. `GROUP BY` — agrupa lo que sobrevivió al `WHERE`
4. Agregaciones (`COUNT`, `AVG`...) — calculan dentro de cada montón
5. `HAVING` — filtra montones enteros, usando el resultado de las agregaciones
6. `SELECT` — decide qué columnas mostrar (aquí nacen los alias)
7. `ORDER BY` — ordena el resultado final, siempre al final de la consulta escrita

**Orden obligatorio al escribir la consulta:**

```sql
SELECT ...
FROM ...
JOIN ...
WHERE ...
GROUP BY ...
HAVING ...
ORDER BY ...
```

`ORDER BY` antes de `HAVING` (por ejemplo) da un error de sintaxis directo — ambas cláusulas tienen una posición fija.

**Por qué `HAVING` no puede usar un alias del `SELECT` pero `ORDER BY` sí:** `HAVING` se ejecuta *antes* que el `SELECT` (paso 5 antes que paso 6 en la lista de arriba), así que el alias todavía no existe cuando `HAVING` se evalúa. Hay que repetir la función de agregación completa:

```sql
SELECT a.first_name, a.last_name, COUNT(*) AS num_peliculas
FROM actor a
LEFT JOIN film_actor fa ON a.actor_id = fa.actor_id
GROUP BY a.actor_id
HAVING COUNT(*) > 30          -- no: HAVING num_peliculas > 30
ORDER BY num_peliculas DESC;  -- ORDER BY sí puede usar el alias
```

`WHERE` y `GROUP BY` sí se pueden combinar: `WHERE` recorta filas por un criterio (por ejemplo, `f.length > 120`) *antes* de que se formen los montones por otro criterio distinto (por ejemplo, `a.actor_id`).

---

## 3. Subconsultas — una consulta dentro de otra

**Idea central:** a veces hace falta resolver una pregunta previa (la "de dentro") antes de poder responder la pregunta real (la "de fuera"). Postgres resuelve primero lo que está entre paréntesis, y lo trata como un valor fijo en la consulta exterior.

### Subconsulta escalar simple (sin GROUP BY dentro)

Cuando la subconsulta da un único número directamente, sin necesidad de agrupar antes:

```sql
SELECT title, rental_rate
FROM film
WHERE rental_rate > (SELECT AVG(rental_rate) FROM film);
```

Aquí no hace falta envolver la subconsulta en un `FROM (...)` adicional — `AVG` se aplica directamente sobre la tabla.

Esto también funciona con un `JOIN` dentro de la subconsulta, siempre que no haya `GROUP BY`:

```sql
SELECT f.title, f.length
FROM film f
WHERE f.length > (
    SELECT AVG(f2.length)
    FROM film f2
    JOIN film_category fc ON fc.film_id = f2.film_id
    JOIN category c ON c.category_id = fc.category_id
    WHERE c.name = 'Action'
);
```

### Subconsulta con GROUP BY dentro — dos niveles de agregación

Cuando hace falta **contar por grupo primero** y **luego** promediar esos conteos, un único `AVG` no basta — `AVG(COUNT(*))` no es válido porque una función de agregación no puede operar sobre otra que todavía se está calculando en el mismo paso. Hacen falta dos consultas anidadas:

```sql
SELECT a.first_name, a.last_name, COUNT(*) AS num_appearences
FROM actor a
LEFT JOIN film_actor fa ON fa.actor_id = a.actor_id
GROUP BY a.actor_id
HAVING COUNT(*) > (
    SELECT AVG(num_appearences)
    FROM (
        SELECT a2.actor_id, COUNT(*) AS num_appearences
        FROM actor a2
        LEFT JOIN film_actor fa2 ON fa2.actor_id = a2.actor_id
        GROUP BY a2.actor_id
    ) AS conteos
);
```

**Por qué el alias `a2`/`fa2`:** la misma tabla se usa dos veces, una en la consulta de fuera y otra en la de dentro. Sin alias distintos, Postgres no sabría a cuál te refieres — es como tener dos amigos llamados "Juan" y necesitar apodos distintos para cada uno.

**Toda subconsulta usada como tabla en un `FROM` necesita un alias obligatorio** (`AS conteos` en el ejemplo) — Postgres lo exige aunque no se use ese nombre después.

**El paréntesis de una subconsulta usada como valor** (por ejemplo, en un `WHERE columna > (...)` o `HAVING COUNT(*) > (...)`) debe envolver **toda** la subconsulta, desde la palabra `SELECT` hasta el final de todo su bloque (incluyendo su propio `FROM`, `GROUP BY` y alias).

**Regla práctica para saber si hace falta el `FROM (...)` extra:** solo se necesita cuando hay que agregar **dos veces seguidas** (contar por grupo, y luego promediar esos conteos). Si la subconsulta interna solo tiene un `AVG`/`COUNT` directo, sin `GROUP BY` previo, no hace falta esa capa extra.

### Cómo construir una subconsulta compleja sin bloquearse

1. Escribir primero, y ejecutar por separado, la parte **más de dentro** (la que hace el `GROUP BY` + `COUNT`).
2. Envolverla en un `FROM (...) AS alias` y aplicarle la agregación exterior (`AVG`). Ejecutar y comprobar el número.
3. Unir todo dentro de la consulta final, en el `WHERE` o `HAVING` correspondiente.

Cuanto más compleja la subconsulta, más vale la pena aislar y probar cada capa por separado antes de unirlas — igual que montar piezas pequeñas de un mueble antes de ensamblarlo entero.

---

## 4. CTEs — subconsultas con nombre

**Qué resuelven:** evitar repetir el mismo bloque de `JOIN`/`GROUP BY` dos veces dentro de la misma consulta (el mismo problema que un `DRY` en programación).

**¿Se ejecutan?** Sí — no es una plantilla de texto que se pega sin más. El CTE se calcula (conceptualmente, para un principiante) una sola vez, y ese resultado ya calculado se reutiliza tantas veces como se mencione después. Es más parecido a guardar el resultado de una consulta pesada en una tabla temporal con nombre que a una "variable" de programación. El nombre solo existe dentro de esa consulta concreta.

### Sintaxis

```sql
WITH nombre_cte AS (
    SELECT ...
    FROM ...
    WHERE ...
)
SELECT ...
FROM nombre_cte
WHERE ...;
```

### Ejemplo — reescribiendo la subconsulta anidada de actores en categoría 'Action'

```sql
WITH action_counts AS (
    SELECT a.actor_id, a.first_name, a.last_name, COUNT(*) AS num_appearances
    FROM actor a
    JOIN film_actor fa ON a.actor_id = fa.actor_id
    JOIN film_category fc ON fc.film_id = fa.film_id
    JOIN category c ON c.category_id = fc.category_id
    WHERE c.name = 'Action'
    GROUP BY a.actor_id, a.first_name, a.last_name
)
SELECT first_name, last_name, num_appearances
FROM action_counts
WHERE num_appearances > (SELECT AVG(num_appearances) FROM action_counts);
```

El `JOIN` largo se calcula una sola vez, se nombra (`action_counts`), y se reutiliza dos veces (para listar y para calcular la media) sin repetirlo.

**Ventajas frente a la subconsulta anidada:**
1. No se repite el `JOIN`.
2. Se lee de arriba a abajo, como una receta, en vez de tener que leer "de dentro hacia fuera".
3. Se pueden encadenar varios CTEs, cada uno construyendo sobre el anterior — algo que con subconsultas anidadas se vuelve ilegible rápido.

---

## 5. Window functions — agregación sin colapsar filas

**El problema que resuelven:** `GROUP BY` fusiona filas — de 1000 películas agrupadas por `rating`, se pasa a 5 filas (una por rating), perdiendo el detalle individual. Las window functions calculan una agregación, pero **sin perder ni una fila** — a cada fila original se le añade el resultado como columna extra.

**Ejemplo mental (4 películas, sin código):**

```
title    | length
---------+-------
Movie A  |  90
Movie B  |  120
Movie C  |  100
Movie D  |  130
```

Con una window function que calcule la media general, el resultado sigue teniendo **4 filas**, cada una con la media (110) repetida al lado:

```
title    | length | media_general
---------+--------+--------------
Movie A  |   90   |     110
Movie B  |  120   |     110
Movie C  |  100   |     110
Movie D  |  130   |     110
```

### Sintaxis general

```sql
FUNCION(columna) OVER (
    PARTITION BY columna_de_grupo   -- opcional
    ORDER BY columna_de_orden       -- obligatorio para funciones de ranking
)
```

`OVER (...)` es lo que distingue una window function de una agregación normal: le dice a Postgres "no colapses, solo calcula y pega el resultado en cada fila".

### AVG(...) OVER () — media general, sin agrupar

```sql
SELECT title, length,
       AVG(length) OVER () AS avg_all
FROM film;
```

Equivalente, para este caso simple, a una subconsulta escalar `(SELECT AVG(length) FROM film)` pegada como columna — pero calculada de forma más directa una sola vez, sin el patrón de subconsulta repetida por fila.

### PARTITION BY — la media, pero por grupos, sin fusionar filas

```sql
SELECT title, length, rating,
       AVG(length) OVER (PARTITION BY rating) AS avg_by_rating
FROM film;
```

Cada película sigue siendo su propia fila, pero ve "la media de duración de todas las películas con su mismo rating" — calculada por separado para cada grupo. Es donde una subconsulta escalar simple deja de ser suficiente y la window function se vuelve la herramienta natural.

### RANK() — posición dentro de un grupo

```sql
SELECT f.title, f.length, c.name,
       RANK() OVER (PARTITION BY c.name ORDER BY f.length DESC) AS ranking
FROM film f
JOIN film_category fc ON f.film_id = fc.film_id
JOIN category c ON fc.category_id = c.category_id;
```

`RANK()` necesita sí o sí un `ORDER BY` dentro del `OVER` — una posición solo tiene sentido si hay un criterio de orden. `DESC` hace que la posición 1 sea el valor más alto (la película más larga); sin especificar dirección, el orden por defecto es ascendente.

**Empates:** si dos filas comparten el mismo valor en el `ORDER BY`, `RANK()` les da la misma posición y **salta** el número siguiente (dos empatadas en 1º, la siguiente es 3º, no 2º). No es un error — es una respuesta correcta cuando hay, honestamente, varias filas "empatadas en primer lugar". Para forzar un desempate arbitrario: añadir un segundo criterio en el `ORDER BY` (`ORDER BY f.length DESC, f.title ASC`), o usar `ROW_NUMBER()` en vez de `RANK()`.

### Filtrar por el resultado de una window function

Las window functions, igual que los alias del `SELECT`, no se pueden usar directamente en el `WHERE`/`HAVING` de la misma consulta donde se calculan. Hace falta envolver la consulta y filtrar por fuera:

```sql
SELECT title, length, name, ranking
FROM (
    SELECT f.title, f.length, c.name,
           RANK() OVER (PARTITION BY c.name ORDER BY f.length DESC) AS ranking
    FROM film f
    JOIN film_category fc ON f.film_id = fc.film_id
    JOIN category c ON fc.category_id = c.category_id
) AS ranked
WHERE ranking = 1;
```

### Por qué no basta con LIMIT

`ORDER BY ... LIMIT 1` da **un único resultado** de toda la tabla. Si se necesita "la más larga **de cada** categoría" (varios resultados, uno por grupo), `LIMIT` no sirve — hay que calcular la posición dentro de cada partición por separado con una window function, y filtrar después por esa posición.

### Casos de uso habituales

- Rankings y "top N por grupo" (el actor con más películas de cada categoría).
- Comparar cada fila contra el agregado de su grupo (¿esta película dura más que la media de su categoría?).
- Acumulados progresivos (`SUM(...) OVER (ORDER BY fecha)`).
- Comparar con la fila anterior/siguiente (`LAG()`, `LEAD()`) — imposible de resolver razonablemente con `JOIN`, `GROUP BY` o subconsultas normales.

---

## Errores vistos y su causa

| Error | Causa | Solución |
|---|---|---|
| `syntax error at or near "select"` | El prompt quedó en `->`, sentencia anterior sin `;` | `\r` para limpiar el búfer, reescribir con `;` |
| `column f.actor_id does not exist` | Se buscó una columna en la tabla equivocada del JOIN | Verificar con `\d tabla` o `information_schema.columns` qué tabla tiene cada columna |
| `missing FROM-clause entry for table "category"` | `fc.category.id` con doble punto — Postgres lo lee como una tabla `category` dentro de `fc` | Escribir `fc.category_id`, con guión bajo, sin punto intermedio |
| `WHERE x = NULL` da 0 filas sin error | `NULL` no es comparable con `=`; la comparación nunca es verdadera | Usar `IS NULL` / `IS NOT NULL` |
| `column "a.first_name" must appear in the GROUP BY clause...` | Se pidió una columna no agregada que no está en el `GROUP BY` | Añadir esa columna (o su id) al `GROUP BY` |
| `ORDER BY` antes de `HAVING` → error de sintaxis | Orden de cláusulas incorrecto | `HAVING` siempre antes de `ORDER BY` |
| `column "num_peliculas" does not exist` en `HAVING` | `HAVING` se ejecuta antes que el `SELECT`; el alias aún no existe en ese momento | Repetir la función de agregación completa en el `HAVING` |
| `AVG(SELECT ...)` inválido | `AVG` solo envuelve una columna ya existente, no una consulta completa | Envolver la subconsulta en `FROM (...) AS alias`, y aplicar `AVG` sobre la columna resultante |

---

## Analogías de referencia

| Concepto | Analogía |
|---|---|
| JOIN | Grapar fichas de dos cajones distintos según un número de referencia compartido |
| Relación muchos-a-muchos (`film_actor`) | Hoja de asignaciones: un empleado puede estar en varios proyectos, cada combinación es una fila |
| LEFT JOIN | Traer a todos los empleados, tengan o no proyecto asignado; hueco vacío si no lo tienen |
| `IS NULL` frente a `= NULL` | Preguntar "¿está vacío?" frente a preguntar "¿es igual a lo desconocido?" (pregunta mal formada) |
| GROUP BY | Repartir fichas mezcladas en montones según un criterio |
| COUNT(*) | Contar cuántas fichas hay dentro de cada montón, por separado |
| WHERE | El portero de la entrada: filtra antes de que se formen los montones |
| HAVING | El que revisa los montones ya formados y descarta los que no cumplen una condición |
| Subconsulta | Resolver una pregunta previa antes de poder responder la pregunta real |
| Alias duplicado en subconsulta anidada (`a` / `a2`) | Dos amigos que se llaman igual — hace falta un apodo distinto para cada uno |
| CTE (`WITH`) | Guardar el resultado de una consulta pesada en una tabla temporal con nombre, para no repetirla |
| Window function | Ponerle a cada empleado, en su propia ficha, "tu sueldo comparado con la media del departamento" — sin fusionar a nadie |
| PARTITION BY | Igual que GROUP BY forma montones, pero sin fusionar las filas de cada montón |
| RANK() | Dorsal de carrera: posición de cada corredor, en carrera general o por categorías |
| LIMIT frente a window function | LIMIT da un único resultado de toda la tabla; una window function con PARTITION BY da un resultado por cada grupo |

---

## Pendiente

- Repaso en voz alta del criterio de cierre: `WHERE` vs `HAVING`, `GROUP BY` vs `PARTITION BY`, por qué `HAVING` no ve los alias del `SELECT`.
- Practicar `LAG()`/`LEAD()` (mencionados pero no ejercitados en este bloque).
- Bloque 2 de PostgreSQL (roadmap): normalización, claves, integridad referencial, y cómo lo traduce el ORM de Odoo.
