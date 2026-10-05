# Entorno del servidor

Infraestructura del equipo SWEETCODE para el proyecto del hackIAthon.

## Aplicación (Dokku)

| Recurso | Detalle |
|---|---|
| **Host** | CT112 `dokku-hackathon` (LXC Debian 13, unprivileged) |
| **IP interna** | `192.168.40.104` |
| **Dokku** | 0.38.27 · app `hackathon-sandbox` |
| **URL** | https://sandbox.sweetcode.studio (Cloudflare Tunnel → CT101 → CT112:80) |
| **Git** | deploy key (solo lectura) para clonar el repo privado |

### Flujo de despliegue (DevSecOps)

```
git push (GitHub main)
   → cron en CT112 (cada 3 min) detecta el commit nuevo
   → dokku git:sync --build hackathon-sandbox ...
   → build + deploy automático
```

### Comandos útiles (dentro de CT112, como root)

```bash
dokku apps:list
dokku ps:report hackathon-sandbox
dokku logs hackathon-sandbox --tail
bash /root/auto-deploy.sh          # forzar un deploy ahora
tail -f /var/log/auto-deploy.log   # historial de despliegues
```

## Otros contenedores

- **CT111 `hackathon`** (`192.168.40.103`): Docker plano, preparado al inicio;
  quedó en desuso al adoptar Dokku (CT112).
