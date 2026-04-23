# Deploy cross-origin com Traefik — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adaptar o backend FastAPI para rodar em `api.eduardoalves.online` servindo o frontend em `eduardoalves.online` (outro VPS), com Traefik na borda terminando TLS via Let's Encrypt, eliminando os 5 problemas de segurança C1–C5.

**Architecture:** Duas stacks docker-compose separadas no VPS do backend — Traefik em `/srv/traefik/` e o backend em `/srv/portfolio-backend/` — conectadas via rede Docker externa `edge` com subnet fixa `172.28.0.0/16`. A API passa a `expose: 8000` (sem publicar no host), Traefik descobre via labels. Cookie usa `SameSite=Lax` (mesmo eTLD+1 = same-site), `__Host-` prefix mantido, `TRUST_PROXY_HEADERS=True` com `TRUSTED_PROXY_CIDRS` restrito à subnet `edge`.

**Tech Stack:** FastAPI, uvicorn 0.45, Traefik v3.1, Let's Encrypt (HTTP-01), Docker Compose v2, pydantic-settings 2.x, pytest + pytest-asyncio + httpx.

**Spec:** `docs/superpowers/specs/2026-04-23-deploy-cross-origin-traefik-design.md`

---

## Estrutura de arquivos

**Modificar:**
- `app/core/config.py` — nova setting `TRUSTED_PROXY_CIDRS` + validator; default `COOKIE_SAMESITE="lax"`
- `app/main.py` — middleware recebe CIDR em vez de `"*"`
- `docker-compose.prod.yml` — expose em vez de ports, labels Traefik, rede edge
- `docker-compose.override.yml` — explicitar `COOKIE_SAMESITE=lax` e `TRUST_PROXY_HEADERS=false` em dev
- `.env.example` — defaults alinhados com produção
- `.env` — defaults explícitos de dev
- `.gitignore` — ignorar `acme.json` e `deploy/traefik/.env`

**Criar:**
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/core/__init__.py`
- `tests/core/test_config_validators.py`
- `deploy/traefik/docker-compose.yml`
- `deploy/traefik/traefik.yml`
- `deploy/traefik/.env.example`
- `deploy/traefik/README.md`
- `scripts/create-edge-network.sh`
- `docs/runbook-deploy.md`

---

## Fase 1 — Config da API com TDD

### Task 1: Criar estrutura de testes

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/core/__init__.py`

- [ ] **Step 1: Criar os pacotes de testes**

Arquivo `tests/__init__.py`: vazio.

Arquivo `tests/core/__init__.py`: vazio.

Arquivo `tests/conftest.py`:

```python
"""
Pytest configuration shared across the suite.

Sets minimally valid env vars for modules that import `settings` at load time.
Individual tests that exercise Settings validation create their own Settings
instance with explicit values.
"""
import os

# Populate env before `app.core.config` is imported anywhere.
os.environ.setdefault(
    "SECRET_KEY",
    "test-secret-key-0123456789abcdef0123456789abcdef0123456789abcdef",
)
os.environ.setdefault(
    "EMAIL_PEPPER",
    "test-email-pepper-0123456789abcdef0123456789abcdef0123456789abcdef",
)
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test",
)
os.environ.setdefault(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://test:test@localhost:5432/test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("REDIS_PASSWORD", "")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
```

- [ ] **Step 2: Validar que pytest carrega sem erros**

Run:
```
cd portfolio-backend && poetry run pytest --collect-only -q
```
Expected: `no tests ran in 0.0Xs` (nenhum teste ainda, mas zero erros de coleta).

- [ ] **Step 3: Commit**

```bash
git add tests/__init__.py tests/conftest.py tests/core/__init__.py
git commit -m "test: bootstrap de estrutura de testes com conftest"
```

---

### Task 2: Teste falho — TRUSTED_PROXY_CIDRS obrigatório quando TRUST_PROXY_HEADERS=True

**Files:**
- Create: `tests/core/test_config_validators.py`

- [ ] **Step 1: Escrever o primeiro teste falhando**

Arquivo `tests/core/test_config_validators.py`:

```python
"""
Tests for Settings validators in app.core.config.

We instantiate Settings with explicit values rather than relying on .env,
so we can assert the validator behavior precisely.
"""
import pytest
from pydantic import ValidationError

from app.core.config import Settings

_COMMON_KWARGS = {
    "SECRET_KEY": "x" * 64,
    "EMAIL_PEPPER": "y" * 64,
    "DATABASE_URL": "postgresql+asyncpg://u:p@h:5432/d",
    "DATABASE_URL_SYNC": "postgresql+psycopg2://u:p@h:5432/d",
    "REDIS_URL": "redis://h:6379/0",
    "CELERY_BROKER_URL": "redis://h:6379/1",
    "CELERY_RESULT_BACKEND": "redis://h:6379/2",
}


def test_trusted_proxy_cidrs_required_when_trust_proxy_headers_true():
    """TRUST_PROXY_HEADERS=True with empty TRUSTED_PROXY_CIDRS must fail."""
    with pytest.raises(ValidationError, match="TRUSTED_PROXY_CIDRS"):
        Settings(
            **_COMMON_KWARGS,
            TRUST_PROXY_HEADERS=True,
            TRUSTED_PROXY_CIDRS=[],
        )
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run:
```
cd portfolio-backend && poetry run pytest tests/core/test_config_validators.py -v
```
Expected: `FAILED` — ou por `AttributeError: TRUSTED_PROXY_CIDRS` (setting ainda não existe) ou por ausência do validator.

- [ ] **Step 3: Não commitar ainda** — vamos implementar na próxima task.

---

### Task 3: Implementar TRUSTED_PROXY_CIDRS + validator em config.py

**Files:**
- Modify: `app/core/config.py`

- [ ] **Step 1: Adicionar setting e validator**

Localizar o bloco do `TRUST_PROXY_HEADERS` (linha ~72–76). Substituir por:

```python
    # Set True only when the app runs behind a trusted reverse proxy
    # that injects a reliable X-Forwarded-For header.
    # When True, ProxyHeadersMiddleware is added and request.client.host
    # is automatically set to the real client IP.
    TRUST_PROXY_HEADERS: bool = False

    # CIDRs (or single IPs) that the proxy headers middleware trusts.
    # X-Forwarded-For is only honored when the direct peer falls inside one
    # of these ranges. Never use ["*"] in production — any client could then
    # spoof the header and defeat rate limiting.
    TRUSTED_PROXY_CIDRS: list[str] = ["127.0.0.1/32"]
```

- [ ] **Step 2: Adicionar validator de TRUSTED_PROXY_CIDRS**

No final da classe `Settings`, antes do último `@field_validator` de `EMAIL_PEPPER`, adicionar:

```python
    @field_validator("TRUSTED_PROXY_CIDRS")
    @classmethod
    def _validate_trusted_proxy_cidrs(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError(
                'TRUSTED_PROXY_CIDRS must not contain "*" — '
                "specify concrete CIDRs or IPs"
            )
        import ipaddress
        for entry in v:
            try:
                ipaddress.ip_network(entry, strict=False)
            except ValueError as exc:
                raise ValueError(
                    f"TRUSTED_PROXY_CIDRS entry {entry!r} is not a valid IP or CIDR"
                ) from exc
        return v
```

- [ ] **Step 3: Adicionar model_validator para dependência TRUST_PROXY_HEADERS × TRUSTED_PROXY_CIDRS**

Adicionar import no topo:

```python
from pydantic import field_validator, model_validator
```

Adicionar antes do `settings = Settings()` final, ainda dentro da classe `Settings`:

```python
    @model_validator(mode="after")
    def _validate_proxy_header_dependency(self) -> "Settings":
        if self.TRUST_PROXY_HEADERS and not self.TRUSTED_PROXY_CIDRS:
            raise ValueError(
                "TRUSTED_PROXY_CIDRS must be non-empty when TRUST_PROXY_HEADERS=True"
            )
        return self
```

- [ ] **Step 4: Rodar teste do Task 2 e confirmar PASS**

Run:
```
cd portfolio-backend && poetry run pytest tests/core/test_config_validators.py::test_trusted_proxy_cidrs_required_when_trust_proxy_headers_true -v
```
Expected: `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add app/core/config.py tests/core/test_config_validators.py
git commit -m "feat(config): exigir TRUSTED_PROXY_CIDRS quando TRUST_PROXY_HEADERS=True"
```

---

### Task 4: Teste — TRUSTED_PROXY_CIDRS rejeita "*" e valores inválidos

**Files:**
- Modify: `tests/core/test_config_validators.py`

- [ ] **Step 1: Adicionar testes**

Anexar ao final de `tests/core/test_config_validators.py`:

```python
def test_trusted_proxy_cidrs_rejects_wildcard():
    """Literal '*' must be rejected — it would defeat IP-based rate limiting."""
    with pytest.raises(ValidationError, match='must not contain "\\*"'):
        Settings(
            **_COMMON_KWARGS,
            TRUST_PROXY_HEADERS=True,
            TRUSTED_PROXY_CIDRS=["*"],
        )


def test_trusted_proxy_cidrs_rejects_invalid_entry():
    """Garbage input must fail loudly at startup, not silently."""
    with pytest.raises(ValidationError, match="not a valid IP or CIDR"):
        Settings(
            **_COMMON_KWARGS,
            TRUST_PROXY_HEADERS=True,
            TRUSTED_PROXY_CIDRS=["not-an-ip"],
        )


def test_trusted_proxy_cidrs_accepts_valid_cidr_and_ip():
    """Happy path: CIDR ranges and single IPs both work."""
    s = Settings(
        **_COMMON_KWARGS,
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_CIDRS=["172.28.0.0/16", "10.0.0.1"],
    )
    assert s.TRUSTED_PROXY_CIDRS == ["172.28.0.0/16", "10.0.0.1"]


def test_trusted_proxy_headers_false_allows_empty_cidrs():
    """When proxy headers are disabled, empty CIDR list is fine."""
    s = Settings(
        **_COMMON_KWARGS,
        TRUST_PROXY_HEADERS=False,
        TRUSTED_PROXY_CIDRS=[],
    )
    assert s.TRUST_PROXY_HEADERS is False
    assert s.TRUSTED_PROXY_CIDRS == []
```

- [ ] **Step 2: Rodar todos os testes de config**

Run:
```
cd portfolio-backend && poetry run pytest tests/core/test_config_validators.py -v
```
Expected: `5 passed`.

- [ ] **Step 3: Commit**

```bash
git add tests/core/test_config_validators.py
git commit -m "test(config): cobrir casos de borda de TRUSTED_PROXY_CIDRS"
```

---

### Task 5: Teste — COOKIE_SAMESITE default passa a ser "lax"

**Files:**
- Modify: `tests/core/test_config_validators.py`

- [ ] **Step 1: Adicionar teste falhando**

Anexar ao final de `tests/core/test_config_validators.py`:

```python
def test_cookie_samesite_default_is_lax():
    """
    Default is 'lax' — works for the common case where frontend and API
    share the same registrable domain. 'strict' and 'none' require
    explicit opt-in.
    """
    s = Settings(**_COMMON_KWARGS)
    assert s.COOKIE_SAMESITE == "lax"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run:
```
cd portfolio-backend && poetry run pytest tests/core/test_config_validators.py::test_cookie_samesite_default_is_lax -v
```
Expected: `FAILED` — valor atual ainda é `"strict"`.

- [ ] **Step 3: Alterar default em `app/core/config.py`**

Localizar a linha (~58):

```python
    COOKIE_SAMESITE: str = "strict"
```

Substituir por:

```python
    # 'lax' is the sweet spot for cross-origin requests between subdomains
    # of the same registrable domain (our case: eduardoalves.online ↔
    # api.eduardoalves.online). Use 'strict' only if there is no cross-origin
    # interaction; use 'none' (with Secure=True) only for truly cross-site
    # topologies with different eTLD+1.
    COOKIE_SAMESITE: str = "lax"
```

- [ ] **Step 4: Rodar teste e confirmar PASS**

Run:
```
cd portfolio-backend && poetry run pytest tests/core/test_config_validators.py -v
```
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add app/core/config.py tests/core/test_config_validators.py
git commit -m "feat(config): default de COOKIE_SAMESITE passa a lax"
```

---

### Task 6: Substituir trusted_hosts="*" por TRUSTED_PROXY_CIDRS em main.py

**Files:**
- Modify: `app/main.py:47-50`

- [ ] **Step 1: Aplicar mudança**

Localizar o bloco:

```python
if settings.TRUST_PROXY_HEADERS:
    # trusted_hosts restricts which proxy IPs to trust.
    # "*" accepts any upstream — tighten to your proxy CIDR in production.
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
```

Substituir por:

```python
if settings.TRUST_PROXY_HEADERS:
    # trusted_hosts restricts which proxy IPs to trust. uvicorn's
    # ProxyHeadersMiddleware accepts a list of IPs or CIDRs (natively since
    # 0.32). Reading from TRUSTED_PROXY_CIDRS guarantees we never deploy
    # with "*" — the validator in Settings rejects that value.
    app.add_middleware(
        ProxyHeadersMiddleware,
        trusted_hosts=settings.TRUSTED_PROXY_CIDRS,
    )
```

- [ ] **Step 2: Validar que a aplicação ainda importa sem erro**

Run:
```
cd portfolio-backend && poetry run python -c "from app.main import app; print(app.title)"
```
Expected: `Portfolio Backend`.

- [ ] **Step 3: Rodar todos os testes**

Run:
```
cd portfolio-backend && poetry run pytest -v
```
Expected: `6 passed`.

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat(middleware): ProxyHeadersMiddleware usa TRUSTED_PROXY_CIDRS"
```

---

## Fase 2 — docker-compose de produção

### Task 7: Ajustar docker-compose.prod.yml — expose + labels Traefik + rede edge

**Files:**
- Modify: `docker-compose.prod.yml`

- [ ] **Step 1: Substituir o arquivo inteiro pelo conteúdo abaixo**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: portfolio_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-portfolio}
      POSTGRES_USER: ${POSTGRES_USER:-portfolio}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-portfolio_secret}
    expose:
      - "5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-portfolio} -d ${POSTGRES_DB:-portfolio}"]
      interval: 10s
      timeout: 5s
      retries: 5
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "512M"
    networks:
      - portfolio_net

  redis:
    image: redis:7-alpine
    container_name: portfolio_redis
    restart: unless-stopped
    # Session, Celery broker, and result backend share this instance via separate
    # logical DBs (0 / 1 / 2). For production, point CELERY_BROKER_URL and
    # CELERY_RESULT_BACKEND at a dedicated Redis instance with its own requirepass
    # so that a Celery compromise cannot reach auth:session:* keys.
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-redis_secret}
    expose:
      - "6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-redis_secret}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "512M"
    networks:
      - portfolio_net

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: portfolio_api
    restart: unless-stopped
    # No `ports:` — the host never exposes 8000. Traefik (on the `edge`
    # network) is the only path from the internet to this container.
    expose:
      - "8000"
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "512M"
    networks:
      - portfolio_net
      - edge
    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=edge"
      - "traefik.http.routers.portfolio-api.rule=Host(`api.eduardoalves.online`)"
      - "traefik.http.routers.portfolio-api.entrypoints=websecure"
      - "traefik.http.routers.portfolio-api.tls=true"
      - "traefik.http.routers.portfolio-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.portfolio-api.loadbalancer.server.port=8000"

  celery:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: portfolio_celery
    restart: unless-stopped
    command: ["celery", "-A", "app.worker", "worker", "--loglevel=info", "--concurrency=4"]
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "512M"
    networks:
      - portfolio_net

volumes:
  postgres_data:
  redis_data:

networks:
  portfolio_net:
    driver: bridge
  # `edge` is created externally (see scripts/create-edge-network.sh) so the
  # Traefik stack in /srv/traefik/ can share it. Subnet is pinned to
  # 172.28.0.0/16 — if you change it, update TRUSTED_PROXY_CIDRS in .env.
  edge:
    external: true
```

- [ ] **Step 2: Validar sintaxe com docker compose config**

Run:
```
cd portfolio-backend && docker compose -f docker-compose.prod.yml config --quiet
```
Expected: sem output (configuração válida). Pode aparecer aviso sobre rede externa inexistente — **ignorar** (vamos criá-la no VPS).

- [ ] **Step 3: Commit**

```bash
git add docker-compose.prod.yml
git commit -m "feat(compose): API expõe 8000 só na rede edge; labels Traefik"
```

---

### Task 8: Ajustar docker-compose.override.yml — dev explícito, sem Traefik

**Files:**
- Modify: `docker-compose.override.yml`

- [ ] **Step 1: Substituir o arquivo inteiro**

```yaml
# Development overrides — applied automatically by Docker Compose.
# Never commit secrets here. Add to .gitignore if this file contains env values.
services:
  postgres:
    ports:
      - "5432:5432"

  redis:
    ports:
      - "6379:6379"

  api:
    # In dev we publish 8000 on the host so the local frontend can hit it
    # directly — no Traefik, no TLS. Production never goes through this file.
    ports:
      - "8000:8000"
    # read_only + bind mount for hot-reload: dev needs to write bytecode caches,
    # so we disable read_only here. Production keeps read_only=true from the base file.
    read_only: false
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    volumes:
      - .:/app
    environment:
      APP_ENV: development
      COOKIE_SECURE: "false"
      COOKIE_SAMESITE: "lax"
      TRUST_PROXY_HEADERS: "false"
      TRUSTED_PROXY_CIDRS: '["127.0.0.1/32"]'
    # No `edge` network in dev — override removes what prod adds.
    networks:
      - portfolio_net

  celery:
    read_only: false
    command: ["celery", "-A", "app.worker", "worker", "--loglevel=debug", "--concurrency=2"]
    volumes:
      - .:/app
    environment:
      APP_ENV: development
```

- [ ] **Step 2: Validar merged config**

Run:
```
cd portfolio-backend && docker compose config --quiet
```
Expected: sem erros. Como `edge` é `external: true` mas override coloca api só em `portfolio_net`, **pode aparecer** aviso sobre edge. Rodar também:
```
cd portfolio-backend && docker compose config | grep -A5 "api:" | head -30
```
Conferir que em dev a `api` só tem `portfolio_net` nos networks e `ports: 8000:8000` está presente.

**Nota importante:** Docker Compose faz merge aditivo de `networks` por padrão. Se o merge estiver anexando `edge` em dev, ajustar o override para usar `!reset` ou declarar explicitamente. Se aparecer erro sobre rede `edge` não existir, executar:
```
docker network create --driver bridge --subnet 172.28.0.0/16 edge
```
Ou seguir Task 16 (script dedicado).

- [ ] **Step 3: Commit**

```bash
git add docker-compose.override.yml
git commit -m "feat(compose): override de dev explicita env e publica 8000 no host"
```

---

## Fase 3 — Templates Traefik versionados

### Task 9: Criar deploy/traefik/docker-compose.yml

**Files:**
- Create: `deploy/traefik/docker-compose.yml`

- [ ] **Step 1: Criar o arquivo**

```yaml
# Traefik edge stack — copy this directory to /srv/traefik/ on the VPS.
# See deploy/traefik/README.md and docs/runbook-deploy.md for setup steps.
services:
  traefik:
    image: traefik:v3.1
    container_name: traefik
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      # Read-only socket — Traefik only reads container labels, never creates.
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./acme.json:/acme.json
    env_file:
      - .env
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: "256M"
    networks:
      - edge

networks:
  edge:
    external: true
```

- [ ] **Step 2: Commit (ainda sem os outros templates)**

```bash
git add deploy/traefik/docker-compose.yml
git commit -m "feat(deploy): template docker-compose da stack Traefik"
```

---

### Task 10: Criar deploy/traefik/traefik.yml (config estática)

**Files:**
- Create: `deploy/traefik/traefik.yml`

- [ ] **Step 1: Criar o arquivo**

```yaml
# Traefik static configuration.
# Runtime routing (hosts, services, middlewares) is discovered via Docker
# provider from container labels in each app's docker-compose.

global:
  checkNewVersion: false
  sendAnonymousUsage: false

log:
  level: INFO
  format: json

accessLog:
  format: json
  fields:
    defaultMode: keep
    headers:
      defaultMode: drop
      names:
        User-Agent: keep
        X-Forwarded-For: keep

entryPoints:
  web:
    address: ":80"
    # Every http:// request is redirected to https:// — permanent (301).
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
          permanent: true
  websecure:
    address: ":443"

providers:
  docker:
    # Traefik listens on the Docker socket and discovers containers that
    # carry `traefik.enable=true`. `exposedByDefault: false` is critical —
    # otherwise any container with a default label gets exposed.
    exposedByDefault: false
    network: edge
    watch: true

certificatesResolvers:
  letsencrypt:
    acme:
      email: ${ACME_EMAIL}
      storage: /acme.json
      # HTTP-01 challenge: Let's Encrypt hits http://<domain>/.well-known/...
      # Requires port 80 reachable from the internet and DNS pointing here.
      httpChallenge:
        entryPoint: web

# Dashboard disabled by default. To enable, add a separate Host router
# with basicauth middleware (see deploy/traefik/README.md).
api:
  dashboard: false
  insecure: false
```

- [ ] **Step 2: Commit**

```bash
git add deploy/traefik/traefik.yml
git commit -m "feat(deploy): config estática Traefik com Let's Encrypt"
```

---

### Task 11: Criar deploy/traefik/.env.example

**Files:**
- Create: `deploy/traefik/.env.example`

- [ ] **Step 1: Criar o arquivo**

```
# Email used by Let's Encrypt to:
#   - send expiration warnings (~20 days before cert expiry)
#   - contact you for compliance/abuse issues
# Use a mailbox you actually read — otherwise certs will renew fine but
# you'll miss notifications when something goes wrong.
ACME_EMAIL=replace-with-real-email@example.com
```

- [ ] **Step 2: Commit**

```bash
git add deploy/traefik/.env.example
git commit -m "feat(deploy): .env.example para stack Traefik"
```

---

### Task 12: Criar deploy/traefik/README.md

**Files:**
- Create: `deploy/traefik/README.md`

- [ ] **Step 1: Criar o arquivo**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add deploy/traefik/README.md
git commit -m "docs(deploy): README dos templates Traefik"
```

---

### Task 13: Atualizar .gitignore (acme.json + deploy/traefik/.env)

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Ler o .gitignore atual**

Run:
```
cd portfolio-backend && cat .gitignore
```

- [ ] **Step 2: Acrescentar entradas no final**

Adicionar ao final do `.gitignore`:

```
# Traefik runtime files — generated on the VPS, never committed.
deploy/traefik/acme.json
deploy/traefik/.env
```

- [ ] **Step 3: Confirmar que `.env.example` continua versionado**

Run:
```
cd portfolio-backend && git check-ignore deploy/traefik/.env.example && echo "ERROR: .env.example is ignored" || echo "OK: .env.example tracked"
```
Expected: `OK: .env.example tracked`.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore(gitignore): ignorar acme.json e .env da stack Traefik"
```

---

## Fase 4 — Scripts e runbook

### Task 14: Criar scripts/create-edge-network.sh

**Files:**
- Create: `scripts/create-edge-network.sh`

- [ ] **Step 1: Criar o arquivo**

```bash
#!/usr/bin/env bash
# Creates the shared `edge` Docker network used by the Traefik stack and
# the backend. Idempotent: safe to rerun.
#
# The subnet 172.28.0.0/16 is fixed so TRUSTED_PROXY_CIDRS in the API's .env
# can pin validation to it. If you must change the subnet, also update
# TRUSTED_PROXY_CIDRS in /srv/portfolio-backend/.env.

set -euo pipefail

SUBNET="${EDGE_SUBNET:-172.28.0.0/16}"
NAME="edge"

if docker network inspect "$NAME" >/dev/null 2>&1; then
    actual_subnet=$(
        docker network inspect "$NAME" \
            --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
    )
    if [ "$actual_subnet" != "$SUBNET" ]; then
        echo "WARN: network '$NAME' exists with subnet $actual_subnet (expected $SUBNET)." >&2
        echo "      Update TRUSTED_PROXY_CIDRS to match, or recreate the network." >&2
    else
        echo "OK: network '$NAME' already exists with subnet $SUBNET."
    fi
    exit 0
fi

echo "Creating Docker network '$NAME' with subnet $SUBNET..."
docker network create \
    --driver bridge \
    --subnet "$SUBNET" \
    "$NAME"
echo "Done."
```

- [ ] **Step 2: Tornar executável**

Run:
```
cd portfolio-backend && chmod +x scripts/create-edge-network.sh
```

- [ ] **Step 3: Teste rápido**

Run:
```
cd portfolio-backend && bash -n scripts/create-edge-network.sh
```
Expected: sem output (sintaxe válida).

- [ ] **Step 4: Commit**

```bash
git add scripts/create-edge-network.sh
git commit -m "feat(scripts): criar rede docker edge idempotente"
```

---

### Task 15: Criar docs/runbook-deploy.md

**Files:**
- Create: `docs/runbook-deploy.md`

- [ ] **Step 1: Criar o arquivo**

```markdown
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
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # → SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # → EMAIL_PEPPER

cp .env.example .env
$EDITOR .env
```

Preencher no `.env`:

- `SECRET_KEY` e `EMAIL_PEPPER` (saída dos comandos acima)
- `POSTGRES_PASSWORD`, `DATABASE_URL`, `DATABASE_URL_SYNC` com a senha real
- `REDIS_PASSWORD`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` idem
- `APP_ENV=production`
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=lax`
- `TRUST_PROXY_HEADERS=true`
- `TRUSTED_PROXY_CIDRS=["172.28.0.0/16"]`
- `ALLOWED_ORIGINS=["https://eduardoalves.online"]`
- `ALLOWED_HOSTS=["api.eduardoalves.online"]`

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

```bash
cd /srv/portfolio-backend
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
```

Expected: tabelas criadas. Se falhar, verificar `DATABASE_URL_SYNC` no `.env`.

## 7. Subir o backend

```bash
cd /srv/portfolio-backend
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

Todos os serviços devem aparecer `running (healthy)` em até 60s.

## 8. Validar o certificado

```bash
docker logs traefik 2>&1 | grep -i "certificate obtained"
# Expected: mensagem com "api.eduardoalves.online"

curl -I https://api.eduardoalves.online/health
# Expected: HTTP/2 200
#           strict-transport-security: max-age=63072000; includeSubDomains; preload

curl -I http://api.eduardoalves.online/health
# Expected: HTTP/1.1 308 Permanent Redirect → https://...
```

Se o certificado não emitir em ~60s, checar `docker logs traefik` por
erros de rate limit ou DNS.

## 9. Validação funcional

1. **Health readiness:**
   ```bash
   curl -s https://api.eduardoalves.online/health/ready
   # Expected: {"status":"ok"}
   ```

2. **Host inválido rejeitado:**
   ```bash
   curl -sI -H 'Host: evil.com' https://api.eduardoalves.online/health
   # Expected: HTTP/... 400 Bad Request
   ```

3. **Login do front:** do browser em `https://eduardoalves.online`, fazer
   login. Dev tools → Application → Cookies de `api.eduardoalves.online`:
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
docker compose -f docker-compose.prod.yml run --rm api python scripts/create_admin.py
```

Seguir os prompts do script.

## Rollback

Se algo quebrar em produção:

```bash
cd /srv/portfolio-backend
docker compose -f docker-compose.prod.yml down
# Traefik continua rodando, mas sem rota → responde 404 para api.eduardoalves.online
# Frontend em eduardoalves.online continua acessível (outro VPS).

git fetch --tags
git checkout <tag-anterior-estavel>
docker compose -f docker-compose.prod.yml up -d --build
```

## Operação contínua

- **Renovação TLS:** automática via Traefik; nada a fazer.
- **Atualizar o backend:** `git pull && docker compose -f docker-compose.prod.yml up -d --build`.
- **Atualizar o Traefik:** `cd /srv/traefik && docker compose pull && docker compose up -d`.
- **Backup do DB:** `docker exec portfolio_postgres pg_dump -U portfolio portfolio > backup-$(date +%F).sql` (rodar em cron; fora do escopo deste runbook).
- **Logs:** `docker compose -f docker-compose.prod.yml logs -f api`.

## Troubleshooting

| Sintoma | Causa provável |
|---|---|
| Cert não emite, log menciona "challenge failed" | DNS não propagado, ou firewall bloqueando :80 inbound |
| Browser mostra `NET::ERR_CERT_AUTHORITY_INVALID` | Traefik ainda usando self-signed; aguardar ACME ou conferir `.env` do Traefik |
| `400 Bad Request` em tudo | `ALLOWED_HOSTS` no `.env` não contém `api.eduardoalves.online` |
| Login ok mas próxima request 401 | Cookie não voltando. Checar no browser: `SameSite=Lax`, `Secure=true`, domínio = `api.eduardoalves.online` |
| Rate limit não dispara / dispara pra todo mundo | `TRUST_PROXY_HEADERS` ou `TRUSTED_PROXY_CIDRS` errados. Confirmar que logs mostram IP real do browser |
| `docker compose up` trava em "network edge not found" | Rodar `scripts/create-edge-network.sh` antes |
```

- [ ] **Step 2: Commit**

```bash
git add docs/runbook-deploy.md
git commit -m "docs: runbook de deploy em produção com Traefik"
```

---

## Fase 5 — Arquivos de env

### Task 16: Atualizar .env.example com defaults de produção

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Substituir o arquivo inteiro pelo conteúdo abaixo**

```
# ── Secrets ──────────────────────────────────────────────────────────────────
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
# Minimum 32 chars. Placeholder values are rejected at startup.
#
# SECRET_KEY  → general app secret (signing, future use).
#               Rotating this does NOT affect stored email hashes.
#
# EMAIL_PEPPER → dedicated HMAC key for email hashing (shared/security.py).
#                Rotating this requires re-hashing every email_hash in the DB.
SECRET_KEY=REPLACE_WITH_OUTPUT_OF_secrets_token_urlsafe_64
EMAIL_PEPPER=REPLACE_WITH_OUTPUT_OF_secrets_token_urlsafe_64

# ── PostgreSQL ────────────────────────────────────────────────────────────────
POSTGRES_DB=portfolio
POSTGRES_USER=portfolio
POSTGRES_PASSWORD=REPLACE_ME
DATABASE_URL=postgresql+asyncpg://portfolio:REPLACE_ME@postgres:5432/portfolio
DATABASE_URL_SYNC=postgresql+psycopg2://portfolio:REPLACE_ME@postgres:5432/portfolio

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_PASSWORD=REPLACE_ME
REDIS_URL=redis://:REPLACE_ME@redis:6379/0

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL=redis://:REPLACE_ME@redis:6379/1
CELERY_RESULT_BACKEND=redis://:REPLACE_ME@redis:6379/2

# ── App ───────────────────────────────────────────────────────────────────────
APP_ENV=production

# ── Session / Auth ────────────────────────────────────────────────────────────
SESSION_TOKEN_LENGTH=48
SESSION_ROTATE_SECONDS=3600
SESSION_MAX_AGE_SECONDS=86400
CSRF_TOKEN_LENGTH=48

# ── Cookies ───────────────────────────────────────────────────────────────────
# Production (behind Traefik + HTTPS): secure=true, samesite=lax.
# Dev (no TLS): override to secure=false in docker-compose.override.yml.
COOKIE_SECURE=true
COOKIE_SAMESITE=lax

# ── Proxy headers ─────────────────────────────────────────────────────────────
# TRUE in production behind Traefik; the CIDR must match the `edge` Docker
# network subnet so only the real Traefik container can set X-Forwarded-For.
# Never use ["*"] — the validator rejects it.
TRUST_PROXY_HEADERS=true
TRUSTED_PROXY_CIDRS=["172.28.0.0/16"]

# ── CORS / Hosts ──────────────────────────────────────────────────────────────
# JSON arrays. Never use ["*"] with allow_credentials=True.
ALLOWED_ORIGINS=["https://eduardoalves.online"]
ALLOWED_HOSTS=["api.eduardoalves.online"]
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "chore(env): .env.example com defaults de produção"
```

---

### Task 17: Atualizar .env (dev local) com variáveis novas

**Files:**
- Modify: `.env`

- [ ] **Step 1: Ler .env atual**

Run:
```
cd portfolio-backend && cat .env
```

- [ ] **Step 2: Acrescentar (ou ajustar) as linhas abaixo ao final do `.env`**

```
# ── Cookies (dev) ─────────────────────────────────────────────────────────────
# COOKIE_SECURE vem de docker-compose.override.yml em dev; aqui é só fallback.
COOKIE_SAMESITE=lax

# ── Proxy headers (dev) ───────────────────────────────────────────────────────
TRUST_PROXY_HEADERS=false
TRUSTED_PROXY_CIDRS=["127.0.0.1/32"]
```

Verificar que já existem no `.env`:

```
ALLOWED_ORIGINS=["http://localhost:3000"]
ALLOWED_HOSTS=["localhost","127.0.0.1"]
COOKIE_SECURE=false
```

Se não existirem, adicionar.

- [ ] **Step 3: Commit**

Apenas se o `.env` estiver versionado. `.env` provavelmente está em `.gitignore`
— se `git status` não listar `.env`, **pular o commit**.

```bash
git status .env
# Se aparecer "nothing to commit" ou ".env is ignored" → pular
# Senão:
git add .env
git commit -m "chore(env): dev env com COOKIE_SAMESITE, TRUST_PROXY_HEADERS, CIDRs"
```

---

## Fase 6 — Validação final

### Task 18: Suite completa de testes + lint

- [ ] **Step 1: Rodar toda a suite**

Run:
```
cd portfolio-backend && poetry run pytest -v
```
Expected: todos os testes PASS (mínimo 6 do `test_config_validators.py`).

- [ ] **Step 2: Rodar ruff**

Run:
```
cd portfolio-backend && poetry run ruff check .
```
Expected: zero warnings (ou só regras já ignoradas em `pyproject.toml`).

Se aparecer erro em `app/core/config.py` por `import ipaddress` dentro da
função, mover para o topo do arquivo.

- [ ] **Step 3: Validar docker compose de prod**

Run:
```
cd portfolio-backend && docker compose -f docker-compose.prod.yml config --quiet
```
Expected: sem output. Aviso sobre rede externa é OK.

- [ ] **Step 4: Validar docker compose merged (prod + override)**

Run:
```
cd portfolio-backend && docker compose config --quiet
```
Expected: sem erros.

- [ ] **Step 5: Subir stack em dev e fazer smoke test**

Run:
```
cd portfolio-backend && docker compose up -d
sleep 10
curl -sI http://localhost:8000/health
```
Expected: `HTTP/1.1 200 OK`.

Derrubar:
```
docker compose down
```

- [ ] **Step 6: Commit (se necessário)**

Se `ruff check` exigiu mover imports ou alguma correção estética:
```bash
git add -A
git commit -m "chore: ajustes de lint pós-implementação"
```

Senão, tudo já está commitado.

---

### Task 19: Tag de release

- [ ] **Step 1: Criar tag anotada**

```bash
cd portfolio-backend
git tag -a v0.2.0-deploy-ready -m "Deploy-ready: Traefik edge + cookie cross-origin + CIDR-restricted proxy headers"
git log --oneline -20
```

- [ ] **Step 2 (opcional): Push**

Só se o usuário confirmar:
```
git push origin main
git push origin v0.2.0-deploy-ready
```

---

## Self-review do plano

**Cobertura da spec:**
- C1 (ports → expose + Traefik): Task 7 (compose prod) + Tasks 9–12 (Traefik templates). ✓
- C2 (SameSite): Task 5 (default lax) + Task 8 (override explícito). ✓
- C3 (TLS): Tasks 10, 15 (Traefik config + runbook). ✓
- C4 (TRUST_PROXY_HEADERS + CIDR): Tasks 2–4 (testes + validator), Task 6 (middleware). ✓
- C5 (ALLOWED_ORIGINS/HOSTS): Tasks 16, 17 (env files). ✓
- Rede edge externa + subnet fixa: Task 14 (script) + Task 7 (prod compose) + Task 15 (runbook). ✓
- Runbook completo: Task 15. ✓
- Rotas públicas futuras (não-bloqueador): abordado na Seção 5.2 do spec, sem task — nada a fazer agora. ✓
- Testes de cookie/CORS na Seção 6.1 do spec: **gap** — Seção 6.1 lista 2 testes extras (cookie com __Host- prefix, CORS preflight). Adicionados como Task 19 a seguir.

**Placeholder scan:** nenhum TBD/TODO. Códigos completos em cada step.

**Consistência de tipos:**
- `TRUSTED_PROXY_CIDRS: list[str]` usado de forma consistente em config, main, env e compose.
- `COOKIE_SAMESITE="lax"` uniforme.
- Subnet `172.28.0.0/16` uniforme em script, compose prod, env e runbook.

---

### Task 19: Testes adicionais de cookie e CORS (fechando gap do spec §6.1)

**Files:**
- Create: `tests/features/__init__.py`
- Create: `tests/features/test_cookie_and_cors.py`

- [ ] **Step 1: Criar diretório e arquivo**

`tests/features/__init__.py`: vazio.

`tests/features/test_cookie_and_cors.py`:

```python
"""
Integration-ish tests for cookie emission and CORS preflight behavior.

These run without a real proxy — they verify the FastAPI middleware stack
responds correctly given the current settings.
"""
from fastapi.testclient import TestClient

from app.core.config import settings
from app.features.auth.cookies import get_cookie_key


def _client():
    # Import lazily so conftest env vars are in place.
    from app.main import app
    return TestClient(app)


def test_cookie_key_uses_host_prefix_when_secure(monkeypatch):
    """With COOKIE_SECURE=True, cookie name must start with __Host-."""
    monkeypatch.setattr(settings, "COOKIE_SECURE", True)
    assert get_cookie_key().startswith("__Host-")


def test_cookie_key_plain_when_not_secure(monkeypatch):
    """In dev (HTTP), the __Host- prefix is dropped so the cookie is usable."""
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    assert not get_cookie_key().startswith("__Host-")


def test_cors_preflight_from_allowed_origin_accepted(monkeypatch):
    """Preflight from an allowed origin returns 200 with credentials header."""
    monkeypatch.setattr(
        settings, "ALLOWED_ORIGINS", ["https://eduardoalves.online"]
    )
    client = _client()
    resp = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://eduardoalves.online",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "https://eduardoalves.online"
    assert resp.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_from_disallowed_origin_blocked(monkeypatch):
    """Preflight from an unknown origin does NOT get the allow-origin header."""
    monkeypatch.setattr(
        settings, "ALLOWED_ORIGINS", ["https://eduardoalves.online"]
    )
    client = _client()
    resp = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    # CORSMiddleware returns 400 for disallowed origins in FastAPI's default config
    # OR returns 200 without the allow-origin header — both are acceptable.
    assert "access-control-allow-origin" not in {
        k.lower(): v for k, v in resp.headers.items()
    } or resp.headers.get("access-control-allow-origin") != "https://evil.com"
```

- [ ] **Step 2: Rodar**

Run:
```
cd portfolio-backend && poetry run pytest tests/features/test_cookie_and_cors.py -v
```
Expected: `4 passed`.

Se o 4º teste falhar porque `TrustedHostMiddleware` rejeita o OPTIONS antes
de o CORS middleware rodar (devido a `ALLOWED_HOSTS=[localhost,127.0.0.1]`),
ajustar a chamada do TestClient passando `headers={"Host": "localhost"}`.

- [ ] **Step 3: Commit**

```bash
git add tests/features/__init__.py tests/features/test_cookie_and_cors.py
git commit -m "test(cookie,cors): cobrir __Host- prefix e preflight allow/deny"
```
