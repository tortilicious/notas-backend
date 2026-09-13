# SQL · Guía de sintaxis y comportamiento

Referencia de consulta, no material de estudio. Se amplía según avanzan los bloques.

**Cobertura actual:** hasta donde empieza el Bloque 1 del roadmap. No incluye joins, `GROUP BY`, subconsultas, CTEs ni window functions.

**Ejemplos:** ejecutables tal cual contra la base de laboratorio `pagila`.

**Documentación de referencia:** capítulo 7 (*Queries*), capítulo 9 (*Functions and Operators*), capítulo 8 (*Data Types*).

---

## 1. SELECT

```sql
SELECT title FROM film;
SELECT title, length FROM film;
SELECT * FROM film;                   -- todas las columnas
```

`*` es cómodo para explorar y mala idea en código: si mañana alguien añade una columna, la consulta empieza a devolver algo distinto sin que nadie la haya tocado.

### Alias

```sql
SELECT title AS pelicula, length AS minutos FROM film;
SELECT title pelicula FROM film;      -- AS es opcional, pero escríbelo
```

Si el alias lleva espacios o mayúsculas que quieres conservar, comillas **dobles**:

```sql
SELECT title AS "Título de la película" FROM film;
```

> Comillas **simples** para valores de texto, comillas **dobles** para identificadores (nombres de columna, tabla o alias). Confundirlas da errores difíciles de leer: `WHERE rating = "PG-13"` busca una *columna* llamada PG-13.

### Expresiones calculadas

Cualquier operación vale como columna:

```sql
SELECT title,
       rental_rate * rental_duration AS coste_total,
       ROUND(length / 60.0, 2)       AS duracion_horas
FROM film;
```

### DISTINCT

Elimina filas duplicadas del resultado:

```sql
SELECT DISTINCT rating FROM film;
SELECT DISTINCT rating, rental_rate FROM film;    -- combinaciones únicas de las dos
```

`DISTINCT` aplica a **todas** las columnas seleccionadas, no solo a la primera.

---

## 2. WHERE

Filtra filas **antes** de que se construya el resultado.

```sql
SELECT title FROM film WHERE length > 180;
```

### Comparadores

| Operador | Significado |
|---|---|
| `=` | igual. **No** `==` |
| `<>` o `!=` | distinto. Los dos valen; `<>` es el estándar |
| `<` `>` `<=` `>=` | comparaciones |

### Combinar condiciones

```sql
SELECT title FROM film
WHERE length > 150 AND rental_rate < 3;

SELECT title FROM film
WHERE rating = 'PG-13' OR rating = 'NC-17';

SELECT title FROM film
WHERE NOT rating = 'R';
```

`AND` tiene más precedencia que `OR`. Con las dos mezcladas, usa paréntesis aunque creas que no hacen falta:

```sql
-- distintas cosas:
WHERE a AND b OR c
WHERE a AND (b OR c)
```

### BETWEEN

```sql
SELECT title FROM film WHERE rental_rate BETWEEN 2 AND 4;
```

Los dos extremos están **incluidos**. Equivale a `rental_rate >= 2 AND rental_rate <= 4`.

Con fechas cuidado: `BETWEEN '2024-01-01' AND '2024-01-31'` sobre un `timestamp` deja fuera casi todo el día 31, porque `'2024-01-31'` se interpreta como las 00:00 de ese día. Para rangos de fechas sobre timestamps, mejor `>= inicio AND < día_siguiente`.

### IN

```sql
SELECT title FROM film WHERE rating IN ('PG-13', 'NC-17');
SELECT title FROM film WHERE rating NOT IN ('G', 'PG');
```

Más legible que encadenar `OR`.

> `NOT IN` con `NULL` en la lista devuelve cero filas siempre. Ver sección 6.

### LIKE

Comparación con patrón. Dos comodines:

| | |
|---|---|
| `%` | cualquier secuencia de caracteres, incluida ninguna |
| `_` | exactamente un carácter |

```sql
SELECT first_name, last_name FROM actor WHERE last_name LIKE 'W%';     -- empieza por W
SELECT title FROM film WHERE title LIKE '%LOVE%';                      -- contiene LOVE
SELECT title FROM film WHERE title LIKE '_ODA%';                       -- 2ª a 4ª letra = ODA
```

`LIKE` distingue mayúsculas; **`ILIKE`** no (es extensión de Postgres, no estándar).

> **No confundir con los comodines de la shell.** En SQL el comodín es `%`, no `*`. Y `^` no significa nada: es sintaxis de expresiones regulares. Postgres sí tiene regex, con el operador `~`, pero es otro mundo.

### NULL

```sql
SELECT title FROM film WHERE original_language_id IS NULL;
SELECT title FROM film WHERE original_language_id IS NOT NULL;
```

**Nunca `= NULL`.** Ver sección 6, que es la importante.

---

## 3. ORDER BY

```sql
SELECT title, length FROM film ORDER BY length DESC;
SELECT title FROM film ORDER BY title;                    -- ASC es el default
SELECT title, length FROM film ORDER BY rating, length DESC;
```

Con varios criterios, se aplican en orden: primero `rating`, y dentro de cada rating, por `length` descendente. Cada uno lleva su propio `ASC`/`DESC`.

### NULL en la ordenación

Por defecto en Postgres los `NULL` van **al final** en `ASC` y al principio en `DESC`. Se puede forzar:

```sql
SELECT title, original_language_id FROM film
ORDER BY original_language_id NULLS FIRST;
```

### Ordenar por alias o por posición

```sql
SELECT title, rental_rate * rental_duration AS coste FROM film ORDER BY coste DESC;
SELECT title, length FROM film ORDER BY 2 DESC;      -- por la 2ª columna. Frágil, evítalo
```

El alias funciona aquí pero **no** en el `WHERE`. Ver sección 6.

---

## 4. LIMIT y OFFSET

```sql
SELECT title, length FROM film ORDER BY length DESC LIMIT 10;
SELECT title FROM film ORDER BY title LIMIT 10 OFFSET 20;   -- filas 21 a 30
```

**`LIMIT` sin `ORDER BY` no tiene sentido.** Sin orden explícito, «las 10 primeras» son diez filas cualesquiera, y pueden cambiar entre ejecuciones. Ver sección 6.

---

## 5. INSERT, UPDATE, DELETE

### INSERT

```sql
INSERT INTO notas (concepto, valor) VALUES ('test1', 100);

INSERT INTO notas (concepto, valor) VALUES
    ('test1', 100),
    ('test2', 200),
    ('test3', NULL);                   -- NULL explícito
```

Las columnas omitidas toman su `DEFAULT`, o `NULL` si no tienen. Nombrar las columnas siempre: sin la lista, el orden posicional se rompe el día que alguien añade una columna.

Devolver lo insertado, útil para conocer el `id` generado:

```sql
INSERT INTO notas (concepto) VALUES ('x') RETURNING id, creado;
```

`RETURNING` es extensión de Postgres y funciona también con `UPDATE` y `DELETE`.

### UPDATE

```sql
UPDATE notas SET valor = 500 WHERE id = 1;
UPDATE notas SET valor = valor * 1.1 WHERE valor IS NOT NULL;
```

### DELETE

```sql
DELETE FROM notas WHERE id = 2;
DELETE FROM notas;                     -- TODAS las filas
```

> **`UPDATE` y `DELETE` sin `WHERE` afectan a la tabla entera** y no piden confirmación. Costumbre: escribir primero la sentencia como `SELECT` con el mismo `WHERE`, ver qué filas salen, y solo entonces cambiar el verbo.

Diferencia con `TRUNCATE`: `DELETE FROM tabla` borra fila a fila, respeta triggers y se puede deshacer dentro de una transacción. `TRUNCATE` vacía la tabla de golpe, mucho más rápido, pero es otra operación con otras implicaciones.

---

## 6. Comportamiento que sorprende

Esta es la sección importante. Todo lo de arriba se busca en cinco segundos; esto es lo que hace que una consulta devuelva algo que no esperabas **sin dar ningún error**.

### NULL no es un valor, es la ausencia de valor

No es cero. No es cadena vacía. Es «aquí no hay dato».

Consecuencia: **cualquier comparación con `NULL` devuelve `NULL`**, que no es verdadero. Por eso:

```sql
WHERE valor = NULL      -- nunca encuentra nada, ni siquiera los NULL
WHERE valor IS NULL     -- correcto
```

Y no da error: la consulta es válida, simplemente devuelve cero filas.

La analogía: `NULL` es una casilla del formulario que nadie rellenó. Preguntar «¿es igual a 5 lo que no está escrito?» no tiene respuesta verdadera ni falsa.

Se propaga a la aritmética y a la concatenación:

```sql
SELECT 100 + NULL;              -- NULL
SELECT 'texto' || NULL;         -- NULL
```

Herramientas para manejarlo:

```sql
COALESCE(valor, 0)              -- primer argumento no nulo. Sustituye NULL por 0
NULLIF(valor, 0)                -- devuelve NULL si valor = 0. El inverso
```

Y la trampa de `NOT IN`:

```sql
WHERE x NOT IN (1, 2, NULL)     -- devuelve CERO filas, siempre
```

Porque internamente es `x <> 1 AND x <> 2 AND x <> NULL`, y ese último factor nunca es verdadero. Con `IN` normal no pasa, solo con `NOT IN`.

### La división entre enteros da un entero

```sql
SELECT 171 / 60;                -- 2, no 2.85
SELECT 171 / 60.0;              -- 2.85
SELECT 171::numeric / 60;       -- 2.85
```

Postgres mira los tipos de los operandos, no lo que tú esperabas. Si los dos son `integer`, el resultado es `integer` y trunca. Dos formas de evitarlo: escribir un literal decimal (`60.0`) o convertir con `::`.

Viene de C y está en casi todos los lenguajes. En SQL duele más porque el resultado se guarda o se muestra sin que nadie avise.

### El orden de las filas no está garantizado

Sin `ORDER BY`, el orden de salida es el que resulte del acceso físico a la tabla, y **cambia solo**.

Ejemplo observado: tras un `UPDATE`, la fila modificada salta al final del resultado. No es un capricho — Postgres no actualiza en el sitio, escribe una **versión nueva** de la fila al final y marca la vieja como muerta. Esas filas muertas son las que luego limpia `autovacuum`.

Regla: si el orden importa, pídelo. Nunca dependas del orden «natural».

### WHERE no ve los alias del SELECT

```sql
SELECT title, rental_rate * rental_duration AS coste
FROM film
ORDER BY coste DESC;            -- funciona

SELECT title, rental_rate * rental_duration AS coste
FROM film
WHERE coste > 30;               -- ERROR: column "coste" does not exist
```

El motivo es el orden en que se procesan las cláusulas, que **no** es el orden en que se escriben:

```
FROM → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT
```

Cuando `WHERE` se evalúa, `SELECT` todavía no ha ocurrido y el alias no existe. `ORDER BY` va después, y por eso sí lo ve.

Para filtrar por una expresión calculada hay que repetirla entera:

```sql
WHERE rental_rate * rental_duration > 30
```

Ese orden de evaluación explica también por qué `WHERE` no puede usar agregados y `HAVING` sí. Material del Bloque 1.

### Las secuencias no devuelven los números fallidos

```sql
INSERT INTO notas (concepto) VALUES (NULL);
-- ERROR: null value in column "concepto" violates not-null constraint
-- DETAIL: Failing row contains (4, null, ...)
```

El `id` 4 se consumió aunque la fila no llegara a existir. La secuencia avanza **antes** de que se comprueben las restricciones, y no retrocede. Por eso en producción hay huecos en los ID que no corresponden a filas borradas.

Es deliberado: si las secuencias se pudieran deshacer, dos transacciones concurrentes tendrían que esperarse mutuamente.

### COUNT(columna) no cuenta los NULL

```sql
SELECT COUNT(*) FROM film;                       -- 1000, cuenta filas
SELECT COUNT(original_language_id) FROM film;    -- 0, ignora los NULL
```

`COUNT(*)` cuenta filas sin mirar columnas. `COUNT(columna)` cuenta **valores no nulos** de esa columna. Con un `WHERE ... IS NULL` delante da igual, pero en cuanto lleguen los `GROUP BY` la diferencia importa.

### Una consulta válida sobre la columna equivocada no avisa

```sql
SELECT title FROM film WHERE title = 'PG-13';    -- 0 filas, ningún error
```

SQL comprueba que la columna existe y que los tipos son compatibles. Que hayas preguntado por la columna equivocada es un problema semántico, y de eso no avisa nadie. **Cero filas es la única señal.**

Ante un resultado vacío inesperado, lo primero es releer el `WHERE`, no dudar de los datos.

### El texto va entre comillas simples

```sql
WHERE rating = 'PG-13'          -- valor
WHERE "mi columna" > 3          -- identificador
```

`WHERE rating = "PG-13"` no es un error de sintaxis: Postgres busca una **columna** llamada `PG-13` y falla con `column "PG-13" does not exist`, que despista bastante.

Para una comilla simple dentro de una cadena, se duplica: `'D''Angelo'`.

---

## 7. Tipos y conversiones

Los que aparecen en Pagila y en Odoo:

| Tipo | Qué es |
|---|---|
| `integer` / `smallint` / `bigint` | enteros de distinto tamaño |
| `numeric(p,s)` | decimal exacto: `p` dígitos totales, `s` decimales. **Para dinero, siempre este** |
| `real` / `double precision` | coma flotante. Rápidos e **inexactos**: nunca para dinero |
| `text` / `varchar(n)` | texto. En Postgres `text` no es más lento |
| `boolean` | `true` / `false` / `NULL` |
| `date` | solo fecha |
| `timestamp` | fecha y hora, **sin** zona horaria |
| `timestamptz` | fecha y hora con zona horaria. El que se debe usar |
| `text[]` | array de texto (`special_features` en `film`) |

### Conversión

```sql
SELECT length::numeric / 60 FROM film;
SELECT CAST(length AS numeric) / 60 FROM film;     -- idéntico, sintaxis estándar
SELECT '2024-01-15'::date;
```

`::` es sintaxis de Postgres, más corta. `CAST` es estándar SQL.

### Fechas

```sql
SELECT now();                                  -- fecha y hora actuales con zona
SELECT current_date;
SELECT now() - interval '7 days';
SELECT EXTRACT(year FROM payment_date) FROM payment;
SELECT date_trunc('month', payment_date) FROM payment;
```

`date_trunc` redondea hacia abajo a la unidad indicada: todos los pagos de enero pasan a ser `2024-01-01 00:00`. Es la pieza básica para agrupar por periodos, que llega en el Bloque 1.

---

## 8. Funciones de uso frecuente

### Texto

```sql
LOWER(title)        UPPER(title)
LENGTH(title)                          -- número de caracteres
TRIM(' hola ')                         -- quita espacios de los extremos
SUBSTRING(title FROM 1 FOR 10)
REPLACE(title, 'A', 'B')
first_name || ' ' || last_name         -- concatenación
CONCAT(first_name, ' ', last_name)     -- ignora los NULL, a diferencia de ||
```

### Números

```sql
ROUND(length / 60.0, 2)                -- redondea a 2 decimales
CEIL(2.1)      FLOOR(2.9)              -- arriba, abajo
ABS(-5)
```

### Condicionales

```sql
SELECT title,
       CASE
           WHEN length > 150 THEN 'larga'
           WHEN length > 90  THEN 'media'
           ELSE 'corta'
       END AS duracion
FROM film;
```

`CASE` se evalúa de arriba abajo y se queda con la primera condición verdadera. Sin `ELSE`, lo que no encaje devuelve `NULL`.

---

## 9. Comentarios y formato

```sql
-- comentario de una línea

/* comentario
   de varias líneas */
```

Convención de formato que paga sola en cuanto una consulta pasa de tres líneas:

```sql
SELECT title,
       length,
       rental_rate
FROM   film
WHERE  length > 150
  AND  rental_rate < 3
ORDER  BY length DESC
LIMIT  10;
```

Palabras clave en mayúsculas, una cláusula por línea, condiciones del `AND` alineadas. SQL es indiferente al formato y a los saltos de línea; quien los lee, no.

---

## Pendiente de añadir

Según avance el Bloque 1: `JOIN` (todos los tipos), `GROUP BY` y agregados, `HAVING`, subconsultas, CTEs (`WITH`), window functions.
