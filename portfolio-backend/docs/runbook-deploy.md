# Runbook — Deploy em produção (api.eduardoalves.online)

Passo-a-passo para subir o backend em um VPS Linux (Debian/Ubuntu) com
Traefik na borda e TLS via Let's Encrypt. Não contempla CI/CD automatizado.

## Pré-requisitos

- VPS com Linux (Debian 12+, Ubuntu 22.04+).
- IP público estático.
- Acesso root (ou sudo).
- Domínio `eduardoalves.online` sob seu controle, com possibilidade de criar
  um registro A para `api.eduardoalves.online`.
- Portas `80` e `443` abertas no firewall (ufw/iptables/cloud provider).

## 0. Configurar DNS

No painel DNS do seu provedor, criar um registro A:

```
api.eduardoalves.online.  300  IN  A  <IP público do VPS>
```

**Aguarde a propagação** antes de prosseguir. Validar no próprio VPS:

```bash
dig +short A api.eduardoalves.online
```

O IP retornado tem que ser o do próprio VPS. Sem isso, Let's Encrypt
(HTTP-01) vai falhar — e cada falha conta contra o rate limit de 5/hora/domínio.

## 1. Instalar Docker + Compose plugin

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

docker --version
docker compose version
```

## 2. Clonar o backend e provisionar .env

```bash
sudo mkdir -p /srv
sudo chown $USER:$USER /srv
cd /srv
git clone <URL-do-repositorio> portfolio-backend
cd portfolio-backend

# Gerar segredos (64 chars, urlsafe)
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # -> SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # -> EMAIL_PEPPER

cp .env.example .env
$EDITOR .env
```

Preencher no `.env` (gerar **senhas distintas** para cada serviço):

- `SECRET_KEY` e `EMAIL_PEPPER` (saída dos comandos acima)
- `POSTGRES_PASSWORD`, `DATABASE_URL`, `DATABASE_URL_SYNC` com a senha real
- `REDIS_PASSWORD`, `REDIS_URL` — instância de sessões (apontando para host `redis`)
- `CELERY_REDIS_PASSWORD`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` — instância **dedicada** do Celery (apontando para host `redis_celery`)
- `APP_ENV=production`
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=lax`
- `TRUST_PROXY_HEADERS=true`
- `TRUSTED_PROXY_CIDRS=["172.28.0.10/32"]` — Traefik's pinned IP on `edge`. Do **not** widen to the whole subnet; any other container on `edge` could otherwise spoof `X-Forwarded-For`.
- `READINESS_ALLOWED_CIDRS=["127.0.0.1/32","::1/128","172.28.0.0/16"]`
- `ALLOWED_ORIGINS=["https://eduardoalves.online"]`
- `ALLOWED_HOSTS=["api.eduardoalves.online"]`
- `NEXT_PUBLIC_API_BASE_URL=https://api.eduardoalves.online` — inlined into the Next.js bundle at build time. Compose's base file is fail-closed (`:?`) on this var, so omitting it aborts the build.

**Importante:** `REDIS_PASSWORD` e `CELERY_REDIS_PASSWORD` devem ser **diferentes**. Cada senha protege uma instância Redis distinta em redes Docker separadas (sessions_net vs celery_net), de modo que um comprometimento do worker Celery não alcance chaves `auth:session:*`.

## 3. Criar a rede Docker `edge`

```bash
bash /srv/portfolio-backend/scripts/create-edge-network.sh
docker network inspect edge --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
# Expected: 172.28.0.0/16
```

Se aparecer **outra** subnet, ou você alterou `EDGE_SUBNET` propositalmente
(e ajustou `TRUSTED_PROXY_CIDRS` no `.env`), ou há colisão com outra rede
existente — resolver antes de continuar.

## 4. Preparar a stack Traefik em /srv/traefik

```bash
sudo mkdir -p /srv/traefik
sudo cp -r /srv/portfolio-backend/deploy/traefik/. /srv/traefik/
cd /srv/traefik

# Configurar o email do ACME
sudo cp .env.example .env
sudo $EDITOR .env                 # Definir ACME_EMAIL=<seu-email>

# Criar o storage do Let's Encrypt
sudo touch acme.json
sudo chmod 600 acme.json
ls -l acme.json
# Expected: -rw------- ... acme.json
```

## 5. Subir o Traefik

```bash
cd /srv/traefik
docker compose up -d
docker compose logs -f traefik
# Procurar linha "Starting provider"
```

Neste ponto o Traefik está rodando mas sem rotas (o backend ainda não
subiu). Um `curl -I https://api.eduardoalves.online` deve falhar com
TLS handshake error (esperado — sem cert ainda).

## 6. Rodar migrações do banco

> **AVISO — sempre passe `-f docker-compose.yml -f docker-compose.prod.yml`.**
> O repositório contém um `docker-compose.override.yml` (dev) que o Compose
> aplica **automaticamente** se você rodar `docker compose <cmd>` puro nesse
> diretório. Em produção isso silenciosamente publica portas em 127.0.0.1,
> desativa `read_only`, troca para `APP_ENV=development`, `COOKIE_SECURE=false`
> e remove a rede `edge` (Traefik perde a rota para o backend). Use sempre os
> dois `-f` em qualquer comando — `up`, `down`, `ps`, `logs`, `run`, `exec`.

```bash
cd /srv/portfolio-backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm api alembic upgrade head
```

Expected: tabelas criadas e revisão atual = `d5a1e3f0` (cabeça atual).
Migrações que sobem nesse passo:
- `69e9b063` cria `admin_users`.
- `3a7f21bc` cria `auth_events`.
- `b2c14e80` adiciona `totp_secret_enc` + `totp_enabled`.
- `c4d918ef` relaxa `totp_secret_enc → TEXT` + cria índice `(event_type, created_at)`.
- `d5a1e3f0` adiciona `email` + `email_2fa_enabled` em `admin_users`.

Se falhar, verificar `DATABASE_URL_SYNC` no `.env`.

## 7. Subir o backend

```bash
cd /srv/portfolio-backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

Todos os serviços devem aparecer `running (healthy)` em até 60s — incluindo
o `api` (o healthcheck dele bate em `http://127.0.0.1:8000/health` interno
ao container, então `frontend` espera o backend estar saudável antes de
subir, evitando 502 transitório no boot).

## 8. Validar o certificado

```bash
docker logs traefik 2>&1 | grep -i "certificate obtained"
# Expected: mensagem com "api.eduardoalves.online"

curl -I https://api.eduardoalves.online/health
# Expected: HTTP/2 200
#           strict-transport-security: max-age=63072000; includeSubDomains; preload

curl -I http://api.eduardoalves.online/health
# Expected: HTTP/1.1 308 Permanent Redirect -> https://...
```

Se o certificado não emitir em ~60s, checar `docker logs traefik` por
erros de rate limit ou DNS.

## 9. Validação funcional

1. **Health readiness:**
   ```bash
   curl -s https://api.eduardoalves.online/health/ready
   # Expected: {"error":"FORBIDDEN","detail":"Forbidden"}

   docker compose -f docker-compose.yml -f docker-compose.prod.yml exec api python - <<'PY'
   import json
   from urllib.request import urlopen

   with urlopen("http://127.0.0.1:8000/health/ready") as response:
       print(json.load(response))
   PY
   # Expected: {'status': 'ok'}
   ```

2. **Host inválido rejeitado:**
   ```bash
   curl -sI -H 'Host: evil.com' https://api.eduardoalves.online/health
   # Expected: HTTP/... 400 Bad Request
   ```

3. **Login do front:** do browser em `https://eduardoalves.online`, fazer
   login. Dev tools -> Application -> Cookies de `api.eduardoalves.online`:
   cookie deve aparecer com nome começando em `__Host-`, flags
   `Secure`, `HttpOnly`, `SameSite=Lax`.

4. **IP real no rate limit:** forçar 6 logins errados. 6ª request retorna
   429. Nos logs (`docker logs portfolio_api`), o campo de IP mostra seu
   IP público — **nunca** `172.28.x.x`.

5. **Portas do host:**
   ```bash
   ss -tlnp | grep -E ':(80|443|8000|5432|6379)\s'
   # Expected: apenas :80 e :443 aparecem
   ```

## 10. Criar o usuário admin inicial

```bash
cd /srv/portfolio-backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm api python scripts/create_admin.py
```

Seguir os prompts do script.

## Rollback

Se algo quebrar em produção:

```bash
cd /srv/portfolio-backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
# Traefik continua rodando, mas sem rota -> responde 404 para api.eduardoalves.online
# Frontend em eduardoalves.online continua acessível (outro VPS).

git fetch --tags
git checkout <tag-anterior-estavel>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Operação contínua

- **Renovação TLS:** automática via Traefik; nada a fazer.
- **Atualizar o backend:** `git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`.
- **Atualizar o Traefik:** `cd /srv/traefik && docker compose pull && docker compose up -d`.
- **Backup do DB:** `docker exec portfolio_postgres pg_dump -U portfolio portfolio > backup-$(date +%F).sql` (rodar em cron; fora do escopo deste runbook).
- **Logs:** `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api`.
- **Isolamento Redis:** há duas instâncias — `portfolio_redis` (sessões) e `portfolio_redis_celery` (broker/resultado). Ficam em redes Docker separadas (`sessions_net` e `celery_net`); cada uma tem uma senha. Nunca apontar `CELERY_BROKER_URL` para `redis:6379` — isso recoloca o risco de task poisoning atingir sessões.

## Troubleshooting

| Sintoma | Causa provável |
|---|---|
| Cert não emite, log menciona "challenge failed" | DNS não propagado, ou firewall bloqueando :80 inbound |
| Browser mostra `NET::ERR_CERT_AUTHORITY_INVALID` | Traefik ainda usando self-signed; aguardar ACME ou conferir `.env` do Traefik |
| `400 Bad Request` em tudo | `ALLOWED_HOSTS` no `.env` não contém `api.eduardoalves.online` |
| Login ok mas próxima request 401 | Cookie não voltando. Checar no browser: `SameSite=Lax`, `Secure=true`, domínio = `api.eduardoalves.online` |
| Rate limit não dispara / dispara pra todo mundo | `TRUST_PROXY_HEADERS` ou `TRUSTED_PROXY_CIDRS` errados. Confirmar que logs mostram IP real do browser |
| `docker compose up` trava em "network edge not found" | Rodar `scripts/create-edge-network.sh` antes |
