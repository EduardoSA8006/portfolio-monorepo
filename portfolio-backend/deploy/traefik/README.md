# Traefik edge stack — templates

These files are the source of truth for the Traefik reverse proxy that sits
in front of `api.eduardoalves.online` in production. They are **templates** —
copy this directory to `/srv/traefik/` on the VPS and operate it from there.

## Files

- `docker-compose.yml` — the Traefik service, bound to ports 80/443 on the host.
- `traefik.yml` — static config: entrypoints, providers, ACME resolver.
- `.env.example` — template for `.env` (set `ACME_EMAIL` before starting).
- `acme.json` — created manually on the VPS with `chmod 600`. Not in this
  repo because it will contain issued certificates after the first run.

## Setup (on the VPS)

See `docs/runbook-deploy.md` in the backend repo for the full step-by-step.
Short version:

```bash
# 1. Create the shared `edge` network (idempotent)
sudo bash /srv/portfolio-backend/scripts/create-edge-network.sh

# 2. Copy the templates
sudo mkdir -p /srv/traefik
sudo cp -r /srv/portfolio-backend/deploy/traefik/. /srv/traefik/
cd /srv/traefik

# 3. Provision .env and acme.json
sudo cp .env.example .env
sudo $EDITOR .env               # set ACME_EMAIL=you@yourdomain
sudo touch acme.json
sudo chmod 600 acme.json

# 4. Start Traefik
sudo docker compose up -d
sudo docker compose logs -f traefik
```

## Enabling the dashboard (optional, later)

The dashboard is off by default. To turn it on:

1. Create a strong basic-auth hash:
   ```bash
   docker run --rm httpd:2.4-alpine htpasswd -nbB admin 'chosen-password'
   ```
2. Add to `traefik.yml` under `api:`:
   ```yaml
   api:
     dashboard: true
     insecure: false
   ```
3. Add a dynamic config file `/srv/traefik/dynamic/dashboard.yml` and mount
   it via `providers.file`. Define a Host router for
   `traefik.eduardoalves.online` with the basic-auth middleware and send it
   to the `api@internal` service.

Not included in this template on purpose — add it when you actually need it.
