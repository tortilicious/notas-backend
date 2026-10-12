# notas-backend

Apuntes de aprendizaje del roadmap Backend + Infra (año 1): Linux y VPS, redes, PostgreSQL y código fuente de Odoo.

## Estructura

| Ruta | Qué es |
|---|---|
| `progreso.md` | Única fuente de verdad: dónde voy, alternancia de carriles, hitos y pendientes |
| `roadmap.html` | El plan del año |
| `ideas-proyectos.md` | Ideas de proyecto con su «cuándo» |
| `generar-apuntes.py` | Genera el HTML de apuntes de una rama |
| `linux/` | Apuntes `linux-bloque-N.md`, plan del bloque en curso, `vps-inventario.md` (estado actual del VPS) y `linux.html` |
| `redes/` | Apuntes `redes-bloque-N.md`, plan del bloque en curso y `redes.html` |
| `postgres/` | Apuntes `postgresql-bloque-N.md` y `00-sql-sintaxis-y-comportamiento.md` |
| `odoo/` | Lectura del código fuente de Odoo: plan del bloque en curso y apuntes `odoo-bloque-N.md` |

Cada fichero de apuntes tiene tres partes: teoría, ejemplos y comandos útiles del bloque. Los planes de bloque se borran al cerrar el bloque.

La receta para reconstruir el VPS vive en otro repo: [vps-setup](https://github.com/tortilicious/vps-setup).

## Generar el HTML de una rama

```
python3 generar-apuntes.py linux "Linux y VPS: apuntes" --origen linux --salida linux
```
