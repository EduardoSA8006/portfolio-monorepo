# Design: Deploy cross-origin com Traefik na borda

**Data:** 2026-04-23
**Status:** Aprovado (pendente implementação)
**Escopo:** Adaptar o backend FastAPI para rodar em `api.eduardoalves.online`, servindo o frontend hospedado em `eduardoalves.online` (em outro VPS), eliminando os cinco problemas de segurança identificados no review (C1–C5).

---

## 1. Contexto e problema

O backend hoje está configurado para desenvolvimento local: `uvicorn` exposto direto em `:8000` no host, cookie com `SameSite=Strict`, sem TLS, sem reverse proxy, sem confiança em headers de proxy, e CORS/hosts liberados apenas para `localhost`. Isso bloqueia o deploy e quebra o login cross-origin.

### Problemas a resolver

| Id | Problema | Correção |
|---|---|---|
| C1 | `ports: "8000:8000"` expõe uvicorn direto na internet | Traefik na borda termina TLS; API passa a `expose: 8000` em rede Docker interna |
| C2 | `SameSite=Strict` quebraria login cross-site | Frontend e API compartilham eTLD+1 (`eduardoalves.online`) → same-site, cross-origin. `SameSite=Lax` cobre o caso com folga, mantém `__Host-` prefix |
| C3 | Sem TLS → `Secure=true` impossível | Traefik emite certificado via Let's Encrypt (HTTP-01) automaticamente |
| C4 | `TRUST_PROXY_HEADERS=False` atrás de proxy → IP do rate limit é o IP do Traefik | `TRUST_PROXY_HEADERS=True` + `ProxyHeadersMiddleware(trusted_hosts=<subnet edge>)` em vez de `"*"` |
| C5 | `ALLOWED_ORIGINS`/`ALLOWED_HOSTS` de produção não configurados | `.env.example` e runbook referenciando `eduardoalves.online` e `api.eduardoalves.online` |

### Requisitos

1. Nenhuma porta de aplicação exposta no host — só `:80` e `:443` via Traefik.
2. TLS automático com Let's Encrypt, renovação transparente.
3. Login do admin funcional de `https://eduardoalves.online` para `https://api.eduardoalves.online`.
4. Rate limit/lockout usando IP real do cliente, não da rede Docker.
5. Dev local continua funcionando em `http://localhost:8000` sem Traefik.
6. API preparada para receber rotas públicas no futuro sem replanejamento.

### Não-objetivos

- Configurar o VPS do frontend (está fora da stack).
- Automação de CI/CD (próxima fase).
- Multi-tenancy ou high-availability (uma instância de Traefik + uma API em um VPS).
- Observabilidade (logs centralizados, métricas, tracing) — deixado para etapa separada.

---

## 2. Arquitetura

### 2.1 Topologia física

```
Internet
    │
    │ TCP :443 (e :80 para ACME + redirect)
    ▼
┌────────────────────────┐
│  VPS (backend)         │
│                        │
│  ┌───────────────────┐ │       docker network "edge"  (external)
│  │ Traefik v3        │◄┼───────┐  subnet: 172.28.0.0/16
│  │ :80, :443         │ │       │
│  │ Let's Encrypt     │ │       │
│  │ Docker provider   │ │       │
│  └────────┬──────────┘ │       │
│           │            │       │
│           ▼ HTTP 8000  │       │
│  ┌───────────────────┐ │       │
│  │ portfolio_api     │─┼───────┘
│  │ expose: 8000      │ │
│  │ uvicorn --workers │ │
│  └───┬───────────┬───┘ │       docker network "portfolio_net"  (internal)
│      │           │     │       (Traefik não alcança)
│      ▼           ▼     │
│  ┌──────┐    ┌──────┐  │
│  │  DB  │    │Redis │  │
│  └──────┘    └──────┘  │
│       ▲                │
│       │                │
│  ┌──────────┐          │
│  │ celery   │          │
│  └──────────┘          │
└────────────────────────┘
```

### 2.2 DNS

- `eduardoalves.online` → VPS do front (fora do escopo desta stack, referenciado só em CORS).
- `api.eduardoalves.online` → A record apontando para o IP público do VPS do backend.

### 2.3 Redes Docker

- **`edge`** — external, criada manualmente com subnet fixa `172.28.0.0/16`. Traefik + container `api` conectados a ela. Permite Traefik descobrir e rotear para a API.
- **`portfolio_net`** — interna da stack do backend. API, Postgres, Redis e Celery. Traefik **não** participa.
- API é o único serviço multi-homed (em `edge` e `portfolio_net`).

**Por que subnet fixa na `edge`?** Porque `TRUST_PROXY_HEADERS=True` vai validar origem dos headers `X-Forwarded-*` via `trusted_hosts=["172.28.0.0/16"]`. Se a subnet for dinâmica, Docker pode atribuir outra faixa após recreação e o `ProxyHeadersMiddleware` passa a descartar os headers — quebrando rate limit e logging de IP real.

### 2.4 Stacks docker-compose separados no VPS

```
/srv/traefik/              ← stack da borda, criada/mantida manualmente
  docker-compose.yml
  traefik.yml              (config estática Traefik)
  acme.json                (storage Let's Encrypt, chmod 600)
  .env                     (ACME_EMAIL)

/srv/portfolio-backend/    ← clone do repositório
  docker-compose.prod.yml  (ajustado)
  .env                     (valores de produção)
  deploy/traefik/          (templates de referência versionados)
  ...
```

Duas stacks distintas para que, ao adicionar um segundo app no mesmo VPS, ele apenas se conecte à rede `edge` com suas próprias labels Traefik — sem precisar mexer na stack do backend.

---

## 3. Componentes

### 3.1 Stack Traefik

**Arquivos (templates versionados em `deploy/traefik/`, cópia operacional em `/srv/traefik/`):**

- **`docker-compose.yml`**
  - Serviço `traefik` na imagem `traefik:v3.1`.
  - Expõe `80:80` e `443:443` no host.
  - Volumes: `/var/run/docker.sock:/var/run/docker.sock:ro`, `./traefik.yml:/etc/traefik/traefik.yml:ro`, `./acme.json:/acme.json`.
  - Conectado na network externa `edge`.
  - `restart: unless-stopped`, `security_opt: ["no-new-privileges:true"]`, resource limits (cpu 0.5, mem 256M).

- **`traefik.yml`** (config estática)
  - `entryPoints.web` em `:80` com middleware global de redirect permanente para `:443`.
  - `entryPoints.websecure` em `:443`.
  - `certificatesResolvers.letsencrypt.acme`: storage `/acme.json`, `httpChallenge.entryPoint: web`, email `${ACME_EMAIL}`.
  - `providers.docker`: `exposedByDefault: false`, `network: edge`.
  - `api.dashboard: false` (desligado por padrão; habilitação documentada separadamente no runbook).
  - `log.level: INFO`, `accessLog` em stdout JSON.

- **`acme.json`** — arquivo vazio inicial com `chmod 600`. Traefik popula automaticamente.

- **`.env`** — `ACME_EMAIL=<email_operacional>`.

### 3.2 Backend — arquivos alterados

| Arquivo | Mudança |
|---|---|
| `docker-compose.prod.yml` | `api`: remover `ports: "8000:8000"`, adicionar `expose: ["8000"]`, adicionar labels Traefik (Host=api.eduardoalves.online, entrypoint=websecure, certresolver=letsencrypt, service port=8000), conectar nas duas redes (`edge` + `portfolio_net`). |
| `docker-compose.prod.yml` | Declarar `networks.edge.external: true`. |
| `docker-compose.prod.yml` | Postgres/Redis/Celery inalterados — permanecem só em `portfolio_net`. |
| `docker-compose.override.yml` | Adicionar `COOKIE_SAMESITE: "lax"`, `TRUST_PROXY_HEADERS: "false"` explícitos para dev. |
| `app/core/config.py` | Default `COOKIE_SAMESITE` muda de `"strict"` para `"lax"`. |
| `app/core/config.py` | Nova setting `TRUSTED_PROXY_CIDRS: list[str] = ["127.0.0.1/32"]`. Validator que exige lista não-vazia quando `TRUST_PROXY_HEADERS=True` e rejeita `"*"` como valor. |
| `app/main.py` | `ProxyHeadersMiddleware(trusted_hosts=settings.TRUSTED_PROXY_CIDRS)` em vez de `"*"`. A API converte a lista de CIDRs no formato que o middleware do uvicorn espera. |
| `.env.example` | Adicionar defaults de produção: `COOKIE_SECURE=true`, `COOKIE_SAMESITE=lax`, `TRUST_PROXY_HEADERS=true`, `TRUSTED_PROXY_CIDRS=["172.28.0.0/16"]`, `ALLOWED_ORIGINS=["https://eduardoalves.online"]`, `ALLOWED_HOSTS=["api.eduardoalves.online"]`. |
| `.env` (dev local) | `TRUST_PROXY_HEADERS=false`, `TRUSTED_PROXY_CIDRS=["127.0.0.1/32"]`, `ALLOWED_ORIGINS=["http://localhost:3000"]`, `ALLOWED_HOSTS=["localhost","127.0.0.1"]`. |

### 3.3 Backend — arquivos novos

| Arquivo | Propósito |
|---|---|
| `deploy/traefik/docker-compose.yml` | Template de referência da stack Traefik (versionado no repo, copiado para `/srv/traefik/` no VPS). |
| `deploy/traefik/traefik.yml` | Template de config estática Traefik. |
| `deploy/traefik/.env.example` | Exemplo de `ACME_EMAIL`. |
| `deploy/traefik/acme.json` | Arquivo vazio com nota para `chmod 600` — ou gerado pelo script de setup. |
| `scripts/create-edge-network.sh` | Idempotente: `docker network inspect edge >/dev/null 2>&1 \|\| docker network create --driver bridge --subnet 172.28.0.0/16 edge`. |
| `docs/runbook-deploy.md` | Passo-a-passo operacional: instalar Docker, rodar `create-edge-network.sh`, subir Traefik, subir backend, validar TLS, validar cookie, troubleshooting. |

### 3.4 Arquivos intencionalmente não alterados

- **`app/features/auth/cookies.py`** — lógica de `__Host-` prefix, HMAC e `domain: None` já correta. Com `COOKIE_SECURE=true` e `COOKIE_SAMESITE=lax`, funciona sem mudança.
- **`app/features/auth/rate_limit.py`** — correta; bug de IP era sintoma de `TRUST_PROXY_HEADERS=false`. Corrigido no middleware.
- **`app/core/middleware.py`** — HSTS já condicionado a `COOKIE_SECURE`.
- **Lógica de auth/sessão/MFA/CSRF** — intocada.

---

## 4. Fluxos de dados

### 4.1 Login (cross-origin, same-site)

```
Browser @ eduardoalves.online
  │
  │ 1. CORS preflight OPTIONS
  │ 2. fetch(POST https://api.eduardoalves.online/api/v1/auth/login,
  │    {credentials:'include', body:{email,password}})
  ▼
Traefik (:443)
  │ - termina TLS (cert Let's Encrypt)
  │ - injeta X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Host
  ▼
API container (:8000, via edge network)
  │ ProxyHeadersMiddleware (trusted_hosts=172.28.0.0/16)
  │    → reescreve request.client.host = IP real do cliente
  │ TrustedHostMiddleware
  │    → valida Host == api.eduardoalves.online
  │ CORSMiddleware
  │    → valida Origin == https://eduardoalves.online
  │    → adiciona Access-Control-Allow-Credentials: true
  │ SecurityHeadersMiddleware
  │    → injeta HSTS, X-Content-Type-Options, Referrer-Policy, etc.
  │ Router /api/v1/auth/login
  │    → rate_limit (chave = IP real + email_hash)
  │    → valida credenciais, cria sessão em Redis
  │    → Set-Cookie: __Host-portfolio_session=<raw>.<sig>;
  │                  HttpOnly; Secure; SameSite=Lax; Path=/
  │    → body: { status: "ok", csrf_token: "..." }
  ▼
Response via Traefik → Browser
  │ - Cookie fixado em api.eduardoalves.online (host-only via __Host-)
  │ - JS guarda csrf_token em memória (não em localStorage)
```

### 4.2 Request autenticado subsequente

```
fetch(POST https://api.eduardoalves.online/api/v1/auth/logout, {
  credentials: 'include',
  headers: { 'X-CSRF-Token': csrfToken, 'Content-Type': 'application/json' }
})
```

- Cookie enviado: eTLD+1 compartilhado (`eduardoalves.online`) → same-site → `SameSite=Lax` permite.
- Servidor valida, na ordem: (1) assinatura HMAC do cookie, (2) sessão ativa no Redis, (3) CSRF token bate com o salvo na sessão, (4) Origin header = `https://eduardoalves.online`.

### 4.3 Dev local (inalterado)

```
Browser @ localhost:3000
  │
  │ fetch(POST http://localhost:8000/api/v1/auth/login, ...)
  ▼
uvicorn :8000 (direto, via docker-compose.override)
  │ sem ProxyHeadersMiddleware (TRUST_PROXY_HEADERS=false)
  │ request.client.host = 127.0.0.1
  │ Cookie: portfolio_session (sem __Host- porque COOKIE_SECURE=false)
  │         HttpOnly; SameSite=Lax; Path=/
```

---

## 5. Segurança

### 5.1 Matriz de defesa — área admin

| Vetor | Camada defensiva |
|---|---|
| Session hijack via XSS | `HttpOnly` no cookie + CSRF token em memória JS (não em storage) |
| CSRF cross-site | `SameSite=Lax` + header obrigatório `X-CSRF-Token` + validação de Origin |
| Subdomain cookie injection | `__Host-` prefix (host-only, sem Domain) |
| Downgrade HTTP | HSTS (max-age 2 anos, includeSubDomains, preload) + redirect http→https no Traefik |
| Redis write comprometido | Cookie HMAC-signed com `SECRET_KEY` — atacante não forja cookie válido mesmo escrevendo no Redis |
| Brute force login | Rate limit per (IP real, email_hash) + lockout global per email |
| Slowloris / headers gigantes | Traefik na borda aplica timeouts e buffering padrão; uvicorn não fica mais exposto |
| Cert expirado | Let's Encrypt auto-renova; `ACME_EMAIL` recebe aviso 20 dias antes |
| Host header poisoning | `TrustedHostMiddleware` rejeita hosts fora de `ALLOWED_HOSTS` |
| CORS bypass | `ALLOWED_ORIGINS` restrito; nunca `["*"]` com `allow_credentials=true` |

### 5.2 Rotas públicas futuras

Quando forem adicionadas:

- Novo router sem `require_auth`, registrado em `app/main.py` com outro prefixo.
- CORS permanece restrito a `https://eduardoalves.online` (consumo pelo próprio front). Clientes server-to-server não precisam de CORS.
- Cookie admin **não vaza** para rotas públicas porque:
  - Rotas públicas GET não leem o cookie.
  - Rotas públicas que mudem estado (improvável) validariam sessão, equivalente a estar autenticado — requererem CSRF token como o admin.
- `__Host-` + `Path=/` é ok mesmo com múltiplos routers — a restrição é no envio (browser só envia para `api.eduardoalves.online`), não no consumo.

### 5.3 Princípio de isolamento

- DB e Redis **não estão** na rede `edge`. Se Traefik for comprometido, atacante não alcança DB/Redis via rede Docker.
- Socket do Docker montado **read-only** no Traefik.
- `security_opt: no-new-privileges:true` em todos os containers.
- `read_only: true` no container da API em prod.
- Secrets (`.env`) não são versionados; `.env.example` documenta formato sem valores.

---

## 6. Estratégia de testes

### 6.1 Testes automatizados

**Unit/integration (backend):**

- Teste de `config.py`: validar que `TRUSTED_PROXY_CIDRS=[]` + `TRUST_PROXY_HEADERS=True` falha no startup.
- Teste de `config.py`: validar que `TRUSTED_PROXY_CIDRS=["*"]` é rejeitado.
- Teste do middleware: com `TRUST_PROXY_HEADERS=True` e request vindo de CIDR confiável, `request.client.host` é reescrito de `X-Forwarded-For`.
- Teste do middleware: request vindo de fora do CIDR confiável **não** tem `request.client.host` alterado.
- Teste de cookie: `COOKIE_SECURE=True` + `COOKIE_SAMESITE=lax` produz Set-Cookie com prefixo `__Host-` e flags corretos.
- Teste de CORS: preflight de `https://eduardoalves.online` passa; preflight de `https://evil.com` é bloqueado.

### 6.2 Verificações manuais de deploy (runbook)

1. `dig +short A api.eduardoalves.online` retorna o IP do VPS antes de subir Traefik.
2. `docker network inspect edge` mostra subnet `172.28.0.0/16`.
3. `docker logs traefik 2>&1 | grep -i "certificate obtained"` aparece em < 60s após primeiro hit.
4. `curl -I https://api.eduardoalves.online/health` → `200 OK`, header `Strict-Transport-Security` presente.
5. `curl -I http://api.eduardoalves.online/health` → `308` para `https://`.
6. Dev tools do browser no front: cookie `__Host-portfolio_session` com flags `Secure`, `HttpOnly`, `SameSite=Lax`.
7. 6 logins errados consecutivos: 6ª request retorna 429; logs mostram `request.client.host = <IP público do browser>`, não `172.28.x.x`.
8. `curl -H 'Host: evil.com' https://api.eduardoalves.online/health` → `400` (bloqueado por `TrustedHostMiddleware`).
9. `ss -tlnp | grep -E ':(80|443|8000|5432|6379)\s'` no host: só `:80` e `:443`.

### 6.3 Rollback

- `docker compose -f docker-compose.prod.yml down` no backend.
- Traefik continua rodando sem rotas → responde 404 para `api.eduardoalves.online`.
- Frontend (outro VPS) continua acessível.
- Subir versão anterior via `git checkout <tag-anterior>` e `docker compose up -d`.

---

## 7. Sequência de build

Implementação recomendada em 5 fases, cada uma verificável isoladamente:

1. **Config e código da API** — `config.py` (novo `TRUSTED_PROXY_CIDRS`, default `COOKIE_SAMESITE=lax`), `main.py` (middleware com CIDR), testes unitários. Sem deploy; roda local.
2. **docker-compose.prod.yml** — remover ports, adicionar expose + labels Traefik + rede edge. Validar com `docker compose config`.
3. **Templates Traefik em `deploy/traefik/`** — docker-compose + traefik.yml + script de rede + `.env.example`.
4. **Runbook `docs/runbook-deploy.md`** — passo-a-passo para aplicar no VPS.
5. **Ambiente de exemplo atualizado** — `.env.example` com defaults de produção; `.env` local com os dev explícitos.

Cada fase pode ser commitada e revisada separadamente.

---

## 8. Riscos e perguntas abertas

- **ACME_EMAIL não é definido.** A implementação vai deixar o valor em `.env.example` como placeholder explícito; o usuário preenche no `.env` do Traefik antes de subir. Runbook alerta.
- **Primeiro `docker compose up` do Traefik sem DNS propagado** gera falhas de ACME e pode consumir rate limit do Let's Encrypt (5 falhas/hora/domínio). Runbook obriga checar `dig` antes.
- **Subnet `172.28.0.0/16` pode colidir** se o VPS já tiver redes Docker custom com essa faixa. Runbook instrui a verificar com `docker network ls` + `docker network inspect` antes; se colidir, escolher outra faixa coerente com `TRUSTED_PROXY_CIDRS`.
- **Dashboard do Traefik desligado.** Se o usuário quiser habilitar depois, adicionar um segundo Host em `traefik.eduardoalves.online` com basic-auth middleware e roteamento só para o entry `api@internal` — fora do escopo desta iteração.
