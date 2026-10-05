# Entorno del servidor

Infraestructura preparada por el equipo SWEETCODE para el proyecto del hackIAthon.

- **Contenedor:** CT111 `hackathon` (LXC Debian 13, unprivileged, planchado en Proxmox)
- **IP interna:** `192.168.40.103`
- **Docker:** Docker + Docker Compose instalados (overlayfs, cgroup v2)
- **Repo:** clonado en `/opt/hackathon-sandbox` (git vía **deploy key** de solo lectura)
- **Despliegue:** dentro de `/opt/hackathon-sandbox`, ejecutar `./deploy.sh`

## Pendiente

- Definir el stack real cuando se confirme el reto.
- Exponer el servicio por **Cloudflare Tunnel** (cuando exista una app; añadir el
  ingress en CT101 y apuntar al puerto del CT111).
