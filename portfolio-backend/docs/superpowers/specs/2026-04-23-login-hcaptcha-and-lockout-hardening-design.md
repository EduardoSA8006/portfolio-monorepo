# Login hCaptcha + lockout hardening — design

**Data:** 2026-04-23
**Escopo:** `portfolio-backend` (service, rate_limit, novo módulo captcha) + `portfolio-frontend` (nova rota `/admin/login`)
**Problema:** o lockout global por `email_hash` no `rate_limit.py` permite DoS direcionado contra o único admin; não existe tela de admin login nem segunda linha de defesa contra brute-force automatizado.
**Meta:** (a) eliminar o DoS via lockout, (b) adicionar hCaptcha condicional como defesa em profundidade, (c) entregar tela `/admin/login` consumindo o fluxo novo.

## Decisões de design

Tomadas via brainstorm, cada uma fecha um eixo independente:

| Eixo | Escolha | Motivo |
|---|---|---|
| Onde vive a tela de login | Dentro do `portfolio-frontend` existente, route group `(admin)` em `/admin/login` | Mais rápido que novo app; isolamento por route group + dynamic import do widget evita impacto no LCP das páginas públicas |
| Quando o captcha é exigido | Condicional, **após a 1ª falha** no par IP+email | Caminho feliz sem UX-tax; bot já é barrado na 2ª tentativa, muito antes do lockout |
| Critério do lockout global | **Multi-IP signal**: só dispara quando ≥3 IPs distintos trippam o per-IP limit na janela | Ataque de um único IP nunca tranca o admin → mata o DoS direcionado |
| Política em outage do hCaptcha | Fail-open + endurecimento temporário (`MAX_ATTEMPTS 5→2`, flag `degraded` no audit) | Preserva disponibilidade do admin durante outage de terceiro sem abrir janela larga para atacante |
| Payload 401 | `INVALID_CREDENTIALS` ganha campo `captcha_required: boolean` | Front já renderiza widget no mesmo erro da senha errada — 1 roundtrip a menos na 2ª tentativa |

## Arquitetura e fronteiras

### Backend (portfolio-backend)

- **`app/features/auth/captcha.py`** (novo) — cliente hCaptcha. Função única `verify(token, remote_ip) -> VerifyResult`. Timeout 3s. Não conhece rate-limit. Marca flag global `auth:rl:degraded` em Redis quando o provider cai. Testável com mock de `httpx.AsyncClient`.
- **`app/features/auth/rate_limit.py`** (alterado) — ganha: (a) flag `auth:rl:captcha:{ip}:{email_hash}` por par; (b) set `auth:rl:lockout_ips:{email_hash}` acumulando IPs que tripparam; (c) lockout global só é setado quando `SCARD ≥ LOGIN_LOCKOUT_DISTINCT_IPS`. Script Lua existente é estendido; a chave `auth:rl:lockout:{email_hash}` continua existindo, mas com semântica "lockout ativo", não "contador pré-lockout".
- **`app/features/auth/service.py`** (alterado) — `login()` orquestra: lê estado (`captcha_required`, `degraded`), decide se chama `captcha.verify`, só conta falha real após autenticação de senha errada (não em falhas de widget/token).

### Frontend (portfolio-frontend)

- **`src/app/admin/login/page.tsx`** (novo) — route group `(admin)` com layout próprio (sem nav/footer do site público).
- **`src/features/admin/auth/`** (novo) — client para `/auth/login`, hook `useLogin`, componente wrapper do widget hCaptcha com dynamic import. Isolado de `src/features/*` públicas.

### Fronteiras e acoplamento

- `captcha.py` depende só de `httpx` + Redis (para flag `degraded`). Não conhece login.
- `rate_limit.py` expõe `captcha_required` e `degraded` como flags; não sabe que existe hCaptcha.
- `service.py` é o único módulo que conhece a semântica "falhou senha → marca captcha_required".
- Script do hCaptcha (`js.hcaptcha.com/1/api.js`) carrega via `next/script` apenas no componente do widget, que só monta em `/admin/login`. Páginas públicas não pagam o custo.

## Estruturas de dados

### Redis — chaves usadas

| Key | Tipo | TTL | Quando muda |
|---|---|---|---|
| `auth:rl:login:{ip}:{email_hash}` | INT | `LOGIN_WINDOW_SECONDS` (900s) | `INCR` em falha real; `DEL` em sucesso |
| `auth:rl:captcha:{ip}:{email_hash}` | STRING "1" | `LOGIN_WINDOW_SECONDS` (900s) | `SETEX` junto com o 1º `INCR`; `DEL` em sucesso |
| `auth:rl:lockout_ips:{email_hash}` | SET de IPs | `LOGIN_LOCKOUT_WINDOW_SECONDS` (1800s) | `SADD` quando counter excede max; não é limpo por sucesso de um IP isolado |
| `auth:rl:lockout:{email_hash}` | STRING "1" | `LOGIN_LOCKOUT_SECONDS` (1800s) | `SETEX` quando `SCARD(lockout_ips) ≥ LOCKOUT_DISTINCT_IPS`; expira sozinho |
| `auth:rl:degraded` | STRING "1" | 60s (auto-renovado por `captcha.verify` enquanto siteverify falha) | `SETEX` em timeout/5xx do hCaptcha |

### Config novos (`app/core/config.py`)

```python
HCAPTCHA_SITE_KEY: str = ""
HCAPTCHA_SECRET_KEY: SecretStr = ""
HCAPTCHA_VERIFY_URL: str = "https://api.hcaptcha.com/siteverify"
HCAPTCHA_TIMEOUT_SECONDS: float = 3.0

LOGIN_LOCKOUT_DISTINCT_IPS: int = 3
LOGIN_LOCKOUT_WINDOW_SECONDS: int = 1800

LOGIN_MAX_ATTEMPTS_DEGRADED: int = 2
```

**Validador produção:** `APP_ENV=production` obriga `HCAPTCHA_SITE_KEY` e `HCAPTCHA_SECRET_KEY` não-vazios. Dev: opcionais; se vazios, `captcha.verify` retorna `ok=True` silenciosamente para permitir desenvolvimento sem integração com hCaptcha.

### Python dataclasses

```python
# captcha.py
@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    provider_available: bool
    reason: str | None = None

# rate_limit.py
@dataclass(frozen=True)
class RateCheckResult:
    captcha_required: bool
    degraded: bool
```

### Exceções novas (`app/features/auth/exceptions.py`)

```python
class CaptchaRequiredError(Exception): ...  # → 401 {"error": "CAPTCHA_REQUIRED"}
class CaptchaInvalidError(Exception): ...   # → 401 {"error": "CAPTCHA_INVALID"}
```

## Contratos HTTP

### `POST /auth/login`

**Request:**
```json
{
  "email": "...",
  "password": "...",
  "captcha_token": "P0_eyJ..."   // opcional, null ou ausente no 1º submit
}
```

**Responses:**
```json
// 200 — sucesso (ou 200 com challenge MFA, fluxo existente)
{ "session_token": "...", "csrf_token": "..." }

// 401 — senha errada
{ "error": "INVALID_CREDENTIALS", "captcha_required": true }

// 401 — request sem token quando era obrigatório
{ "error": "CAPTCHA_REQUIRED" }

// 401 — token presente, hCaptcha rejeitou
{ "error": "CAPTCHA_INVALID" }

// 429 — lockout global
{ "error": "TOO_MANY_ATTEMPTS" }
```

O campo `captcha_required` é **sempre** presente no 401 `INVALID_CREDENTIALS` (bool), para simplificar tipagem no front.

### Novo endpoint `GET /auth/config`

```json
{ "hcaptcha_site_key": "10000000-ffff-ffff-ffff-000000000001" }
```

Serve o site_key do hCaptcha para o front montar o widget. Sem autenticação (a site_key é pública). Se vazia no config, retorna `{"hcaptcha_site_key": ""}` e o front renderiza formulário sem widget (modo dev).

## Fluxos de dados

### Cenário 1 — Login limpo
```
POST /auth/login {email, password}
  check_login_rate      → captcha_required=False, degraded=False
  (skip captcha)
  verify_password       → True
  reset_login_rate      → DEL counter + captcha flag
  create_session
200 {session_token, csrf_token}
```
Nenhuma chamada a hCaptcha.

### Cenário 2 — Primeira senha errada
```
POST /auth/login {email, password_errada}
  check_login_rate      → captcha_required=False
  verify_password       → False
  register_login_failure:
    INCR counter → 1
    SETEX captcha flag 900
    (counter ≤ max, não toca lockout_ips)
401 {error: INVALID_CREDENTIALS, captcha_required: true}
```
Front já mostra erro de senha + renderiza widget na mesma resposta.

### Cenário 3 — Segunda tentativa (usuário corrigiu a senha)
```
POST /auth/login {email, password_correta, captcha_token: "P0_..."}
  check_login_rate      → captcha_required=True
  captcha.verify        → ok=True
  verify_password       → True
  reset_login_rate
200
```
Se a senha ainda estivesse errada: `register_login_failure` roda, counter vai a 2, continua abaixo de `LOGIN_MAX_ATTEMPTS` (5), captcha permanece required, nada é adicionado a `lockout_ips`.

**Regra:** `CaptchaRequiredError` e `CaptchaInvalidError` **não** incrementam o counter. Sinal de abuso é senha errada após autenticação de máquina, não latência do widget.

### Cenário 4 — Lockout multi-IP
```
IP A → 6 falhas (com captcha resolvido) → SADD lockout_ips "A" → SCARD=1 < 3
IP B → idem → SCARD=2 < 3
IP C → idem → SCARD=3 ≥ LOCKOUT_DISTINCT_IPS → SETEX lockout 1800
Próximo request (qualquer IP):
  check_login_rate → raises TooManyAttemptsError
429 {error: TOO_MANY_ATTEMPTS}
```
Atacante de um único IP nunca tranca o admin.

### Cenário 5 — hCaptcha em outage
```
captcha.verify:
  httpx POST siteverify → timeout / 5xx
  SETEX auth:rl:degraded "1" 60
  return VerifyResult(ok=False, provider_available=False)

check_login_rate → lê degraded=True
login():
  se captcha_required=True e degraded=True → pula verify (fail-open)
  register_login_failure usa LOGIN_MAX_ATTEMPTS_DEGRADED=2
  audit event reason="captcha_degraded"
```
Durante outage, sua margem cai de 5 para 2 falhas antes do counter rodar. Auditoria pós-incidente distingue operação degradada.

## Error handling — tabela de decisão

| Situação | Ação em service.py | Counter sobe? | Response |
|---|---|---|---|
| Senha errada, captcha não required | `register_login_failure` | Sim | 401 INVALID_CREDENTIALS, `captcha_required: true` |
| Senha errada, captcha ok | `register_login_failure` | Sim (pode disparar SADD) | 401 INVALID_CREDENTIALS, `captcha_required: true` |
| Senha certa, captcha ok | `reset_login_rate` | Reset | 200 |
| Captcha required, token ausente | Não chama register | Não | 401 CAPTCHA_REQUIRED |
| Captcha required, token rejeitado | Não chama register | Não | 401 CAPTCHA_INVALID |
| hCaptcha timeout/5xx | Marca degraded, pula verify | Próximas falhas usam threshold degraded | Segue fluxo com max reduzido |
| Lockout global ativo | `check_login_rate` levanta | N/A | 429 TOO_MANY_ATTEMPTS |
| Redis indisponível | `RedisError` propaga | N/A | 503 SERVICE_UNAVAILABLE (fail-closed em Redis) |

**Fail-closed em Redis** é intencional e diferente de fail-open em hCaptcha: sem Redis não temos rate-limit, então login tem que parar; sem hCaptcha temos rate-limit + Argon2, então podemos degradar.

## Auditoria

Novos `AuthEvent.reason` em falhas:
- `captcha_required` — 401 CAPTCHA_REQUIRED
- `captcha_invalid` — 401 CAPTCHA_INVALID
- `captcha_degraded` — login_failed ou login_success em modo degradado

Novo `AuthEvent.event_type`:
- `login_lockout_triggered` — emitido uma vez quando `SCARD` cruza o threshold e o lockout é setado. Payload inclui `ip` do IP que disparou.

Objetivo: permitir pós-mortem rápido distinguindo "pegou captcha na 1ª falha" vs "acessou durante outage do hCaptcha" vs "lockout disparou por quais IPs".

## Testing

### `tests/features/auth/test_captcha.py` (novo)
- `verify(token=None)` → `ok=False, provider_available=True`
- Siteverify 200 + success=True → `ok=True`
- Siteverify 200 + success=False → `ok=False, reason` preenchido
- Timeout → `ok=False, provider_available=False`, set `auth:rl:degraded`
- 5xx → idem
- Mock `httpx.AsyncClient` via fixture, sem rede

### `tests/features/auth/test_rate_limit.py` (novo)
- Fluxo básico: 0 falhas → captcha_required=False; 1 falha → setado; counter sobe
- SADD só quando counter excede max
- Multi-IP: 3 IPs excedendo cada um → lockout; 1 IP excedendo 10x → não dispara
- `reset_login_rate` limpa counter + captcha flag, preserva lockout_ips set
- Degraded: thresholds reduzidos aplicam
- `fakeredis.aioredis` como backend

### `tests/features/test_auth_service.py` (alterado)
- Happy path existente continua passando (mocks do `check_login_rate`/`reset_login_rate` cobrem)
- Novos casos:
  - `captcha_required=True, token=None` → `CaptchaRequiredError` levantada antes de `verify_password`
  - `captcha_required=True, token="bad"` → `CaptchaInvalidError`
  - `degraded=True` → `captcha.verify` não é chamado
  - Order inclui `captcha.verify` entre `rate.check` e `verify_password` quando aplicável

### `tests/features/auth/test_login_e2e.py` (novo)
- Cenários 1–5 como testes de integração: `fakeredis` + `sqlite+aiosqlite` + mock de `captcha.verify` (não mocka rate_limit)
- Verifica também: emit de `AuthEvent` com `reason` correto em cada cenário

### Frontend — `src/features/admin/auth/__tests__/use-login.test.ts`
- Transições de estado `idle → submitting → captcha_required → submitting → success`
- Erro 401 INVALID_CREDENTIALS com `captcha_required: true` → estado `captcha_required`
- Mock do `fetch`

E2E Playwright explicitamente **out of scope** nesta iteração (admin único, não justifica a infra).

## No escopo desta iteração mas fora do núcleo do spec

- **Stub `/admin/page.tsx`** — página de destino após login bem-sucedido. Conteúdo mínimo ("Welcome, admin" + botão logout); serve só para haver um target de redirect válido. Protegida pelo mesmo middleware de sessão do backend (verifica cookie `__Host-session`).

## Out of scope (adiado para iterações futuras)

- Dashboard admin real, gestão de conteúdo, qualquer UI além do stub.
- Recuperação de senha por email / "forgot password" — não existe hoje, permanece não existindo.
- CAPTCHA para outras rotas (ex: formulário de contato público) — decisão separada.
- Integração real com hCaptcha em testes (todos os testes mockam).
- Observabilidade/métricas Prometheus no rate_limit — logs + AuthEvent já cobrem auditoria.

## Follow-ups (não bloqueantes)

- Considerar migrar `auth:rl:lockout_ips` set para HyperLogLog (`PFADD`/`PFCOUNT`) se um dia o cardinality importar mais que o espaço (improvável no perfil atual).
- Revisar se `LOGIN_LOCKOUT_DISTINCT_IPS=3` ainda faz sentido após 3 meses de dados de auditoria.
- Avaliar CAPTCHA_BYPASS_UNTIL break-glass se a política fail-open + degraded se mostrar insuficiente na prática (improvável).

## Referências

- Issue original: 3 falhas de segurança identificadas durante revisão (lockout DoS, .env no zip, alembic/scripts no .dockerignore) — .env e .dockerignore já corrigidos em commits anteriores; este spec cobre item 3.
- Código atual de rate-limit: `app/features/auth/rate_limit.py` (Lua script `_CHECK_AND_INCREMENT`)
- Código atual de login: `app/features/auth/service.py:102-155`
- Frontend atual: `portfolio-frontend/src/app/` — nenhuma rota admin existe
