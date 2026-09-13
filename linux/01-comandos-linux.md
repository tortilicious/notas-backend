Servicios

systemctl status <servicio>        # estado detallado + últimas líneas de log
systemctl is-active <servicio>     # ¿corre ahora? responde active / inactive
systemctl is-enabled <servicio>    # ¿arranca al reiniciar? enabled / disabled
sudo systemctl enable <servicio>   # que arranque al reiniciar (no lo arranca ahora)
sudo systemctl start <servicio>    # arrancarlo ahora (no afecta al reinicio)
sudo systemctl enable --now <ser>  # las dos cosas de golpe


Usuarios / Grupos

whoami                    # mi nombre de usuario
id                        # identidad completa: UID, grupo principal, suplementarios
id <usuario>              # lo mismo, de otro usuario
groups                    # solo mis grupos
cat /etc/passwd           # todos los usuarios del sistema
cat /etc/group            # todos los grupos y sus miembros
sudo cat /etc/shadow      # contraseñas cifradas; necesita sudo a propósito
getent passwd <usuario>   # consultar un usuario concreto
