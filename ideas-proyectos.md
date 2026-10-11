# Ideas de proyectos · Portfolio backend / devops

Ideas que surgen durante el roadmap y que merecen convertirse en proyecto propio. Cada una lleva cuándo tiene sentido abordarla, qué demuestra y qué criterio la cierra.

**Regla:** una idea no se empieza antes de su «cuándo». Apuntarla es para no perderla, no para desviarse del bloque en curso.

---

## 1. VPN propia sobre el VPS con WireGuard

**Origen:** Redes · Bloque 2 (DNS), al analizar un bloqueo por IP de la operadora y por qué una VPN lo evita. Apuntada el 28/09/2026.

**Cuándo:** después del **Bloque 4 de Linux** (`ufw`, `fail2ban`, SSH endurecido). Montarla implica abrir un puerto nuevo, y no se expone un servicio más en un servidor sin cortafuegos.

**Qué demuestra:**

- Redes aplicadas: túneles, encapsulación, reenvío de paquetes y NAT.
- Seguridad de un servicio expuesto a internet.
- Operación de infraestructura propia.

**Lo que lo convierte en proyecto de portfolio, y no en un tutorial seguido:**

- [ ] **README con las decisiones escritas:** por qué WireGuard y no OpenVPN, qué puerto y por qué, qué se gana y qué se pierde frente a una VPN comercial.
- [ ] **Modelo de amenazas breve:** de qué protege y de qué no. Incluir que la IP del VPS es solo mía (no hay anonimato) y que todo lo que salga de ella es responsabilidad mía ante Netcup.
- [ ] **Configuración reproducible:** primero a mano, con runbook como el del VPS; en Q4, con **Ansible**.
- [ ] **Verificación con evidencias:**
  - `tcpdump` en el portátil demostrando que hacia fuera solo sale tráfico cifrado al VPS.
  - `dig` y `resolvectl` demostrando que el DNS va por el túnel.
  - `curl` demostrando que la IP de salida es la del VPS.
- [ ] **Observabilidad** en Q4: métricas del túnel en Prometheus y Grafana.

**Antes de empezar:** revisar las condiciones de uso de Netcup sobre el uso del VPS como VPN.

**Criterio de cierre:** reinstalarla en una máquina limpia siguiendo las propias notas, y explicar sin notas el recorrido de un paquete por el túnel, capa por capa.

---

## 2. monetr autoalojado en el VPS

**Origen:** petición propia, fuera de bloque. Apuntada el 06/10/2026. Documentación: https://monetr.app/documentation/install

**Cuándo:** con tres cosas cerradas.

- **Linux · Bloque 3**: nginx como reverse proxy y TLS con Let's Encrypt, los mismos que irán delante de monetr.
- **Linux · Bloque 4**: cortafuegos y backups probados. Son datos financieros: no se exponen antes.
- **Primer contacto con Docker** del roadmap: monetr solo admite oficialmente instalación con contenedores, y lo recomendado es Docker Compose.

**Qué demuestra:**

- Operar una aplicación real de terceros con datos sensibles: actualizar, hacer backup y restaurar.
- Comparar despliegues: Odoo a mano frente a monetr con Docker Compose.

**Lo que lo convierte en proyecto de portfolio, y no en un tutorial seguido:**

- [ ] **README con las decisiones escritas:** subdominio, por qué nginx delante, dónde viven los volúmenes y qué fuente de datos bancarios se usa (Plaid tiene coste; la subida de ficheros, no).
- [ ] **Imagen verificada con `cosign`** antes de arrancarla (disponible desde la v1.14.0).
- [ ] **Backup del PostgreSQL de monetr** integrado en el script de backup del roadmap y restaurado en limpio.
- [ ] **Runbook de actualización de versión.**

**Requisitos según la documentación:** mínimo 512 MB de RAM y 1 GB de disco; PostgreSQL incluido en el Docker Compose. Encaja en el VPS 500 G12.

**Antes de empezar:** comprobar en la documentación de monetr la compatibilidad de Plaid y Lunch Flow con bancos españoles.

**Criterio de cierre:** monetr accesible por HTTPS en el dominio propio, y un backup suyo restaurado en una máquina limpia siguiendo las propias notas.

---

## Plantilla para nuevas ideas

```markdown
## N. Nombre del proyecto

**Origen:** bloque y conversación donde surgió. Fecha.

**Cuándo:** qué bloque tiene que estar cerrado antes, y por qué.

**Qué demuestra:**

- …

**Lo que lo convierte en proyecto de portfolio:**

- [ ] …

**Criterio de cierre:** …
```
