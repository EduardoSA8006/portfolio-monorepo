# Runbook — recuperação de admin

Quando seguir este runbook: o admin **perdeu o TOTP e a senha** ao
mesmo tempo (ex.: troca de telefone sem export do authenticator +
gerenciador de senhas comprometido). Cobre apenas o caso "quem está
recuperando tem acesso root ao VPS de produção" — não há (e não deve
haver) caminho remoto para isto.

> **Antes de começar:** confirme por canal lateral (telefone,
> presencial) que a pessoa pedindo a recuperação é mesmo o owner do
> projeto. Este procedimento concede acesso administrativo total à
> aplicação.

## Caminhos disponíveis

1. **Script de reset** (`create_admin.py --reset`) — preferido. Re-set
   a senha e zera TOTP de uma vez.
2. **SQL direto** — fallback se o container API não estiver rodando.

Os dois exigem acesso ao container/instância de Postgres.

## Caminho 1 — script `--reset`

```bash
ssh root@<vps>
cd /srv/portfolio-backend

# Pré-condição: container API está rodando OU sobe um one-shot.
# Para rodar como one-shot, sem afetar tráfego:
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm api \
    python scripts/create_admin.py --reset --email admin@example.com
```

O script vai:

1. Pedir uma nova senha (interativo, sem eco — `getpass`).
2. Validar contra `is_strong_password` (mínimo 8 chars, upper, lower, digit, special).
3. Re-hashar com Argon2 e gravar em `admin_users.password_hash`.
4. **Zerar `totp_enabled` e `totp_secret_enc`** — força re-enrollment
   no próximo login (impede que um TOTP secret antigo permaneça
   ativo após a recuperação).

Após o sucesso, o admin faz login com a nova senha e o sistema vai
direcioná-lo pra cadastrar um novo TOTP (caminho `/api/v1/auth/totp/enroll`).

> Se quiser fazer no-prompt (CI/automação interna):
> ```bash
> ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='<senha-temp>' \
>     docker compose ... run --rm api python scripts/create_admin.py --reset
> ```
> A senha temp deve ser comunicada ao admin por canal seguro e
> trocada no primeiro login.

## Caminho 2 — SQL direto (fallback)

Use quando:
- O container API não está saudável (pode estar bloqueado em migration).
- Você precisa zerar TOTP **sem** trocar senha (raro).

```bash
docker exec -it portfolio_postgres psql \
    -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"
```

Dentro do `psql`:

```sql
-- Zerar TOTP de um admin específico.
UPDATE admin_users
   SET totp_enabled = false,
       totp_secret_enc = NULL,
       updated_at = NOW()
 WHERE email_hash = encode(
       hmac(lower('admin@example.com')::bytea,
            current_setting('app.email_pepper')::bytea,
            'sha256'),
       'hex'
   );
```

> O cálculo de `email_hash` aqui depende de `EMAIL_PEPPER` estar
> exposto via `current_setting('app.email_pepper')`. Como isso não
> está configurado no DB, o caminho mais simples é executar o
> Python:
> ```bash
> docker compose ... exec api python -c \
>     "from app.shared.security import hash_email; \
>      print(hash_email('admin@example.com'))"
> ```
> e usar o hash literal:
> ```sql
> UPDATE admin_users SET totp_enabled = false, totp_secret_enc = NULL
>  WHERE email_hash = '<hash-impresso-acima>';
> ```

## Pós-recuperação — checklist obrigatório

- [ ] Confirmar que o admin consegue logar com a nova credencial.
- [ ] Confirmar que o cadastro de TOTP no primeiro login funcionou
      (cookies `__Host-portfolio_session` aparecem; `/api/v1/auth/config`
      retorna `mfa_required` esperado).
- [ ] **Revogar todas as sessões existentes** desse usuário —
      qualquer cookie pré-recuperação ainda é válido até o TTL natural.
      Use o endpoint `/api/v1/auth/sessions/clear` (autenticado) ou
      via Redis: `redis-cli -a "${REDIS_PASSWORD}" --scan --pattern \
      'auth:session:*' | xargs redis-cli -a "${REDIS_PASSWORD}" DEL`.
- [ ] Inserir entrada no `auth_events` documentando a recuperação
      (gravada manualmente — esse caminho **não** passa pelo audit log
      automático). Exemplo:
      ```sql
      INSERT INTO auth_events
          (id, user_id, event_type, reason, ip, user_agent, created_at)
      VALUES (
          gen_random_uuid(),
          (SELECT id FROM admin_users WHERE email_hash = '<hash>'),
          'admin_recovery',
          'manual_reset_via_runbook',
          '<sua origem>',
          'create_admin.py --reset',
          NOW()
      );
      ```
- [ ] Postar no canal interno (Slack/email) o que aconteceu, quem
      executou, e quando.

## Por que não há caminho via API

A recuperação **não pode** ter caminho remoto, mesmo com email/SMS:

- Email do admin pode estar comprometido (essa é, frequentemente,
  a forma como ele perde o TOTP — provedor de email atacado).
- Telefone para SMS é vulnerável a SIM-swap.
- Qualquer endpoint de "recuperação" remota precisa ser perfeitamente
  seguro contra força bruta, o que efetivamente recria o problema do
  login original.

A escolha consciente é: para recuperar precisa estar fisicamente (ou
via SSH) na máquina de produção, e a posse do SSH **é** a credencial
de recuperação.
