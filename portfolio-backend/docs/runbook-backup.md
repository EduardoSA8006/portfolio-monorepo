# Runbook — Postgres backup & restore

Backup do banco de produção. Cobre: dump cifrado em cron, retenção,
upload pra storage externo, e teste de restore. O `runbook-deploy.md`
cita backup ad-hoc; este aqui é o procedimento real.

## Pré-requisitos

- Acesso root/sudo no VPS de produção.
- Conta em storage externo (Backblaze B2, AWS S3, Cloudflare R2 — qualquer
  provedor S3-compatible serve). Os exemplos abaixo usam B2 via
  `rclone` por simplicidade.
- GPG instalado (`apt install gnupg`).
- Uma chave GPG pública dedicada ao backup, gerada offline (não no VPS):
  ```bash
  gpg --batch --gen-key <<EOF
  Key-Type: RSA
  Key-Length: 4096
  Name-Real: portfolio-backup
  Name-Email: backup@eduardoalves.online
  Expire-Date: 0
  %no-protection
  %commit
  EOF
  gpg --export --armor backup@eduardoalves.online > backup-pub.asc
  ```
  Suba **só a pública** pro VPS (`/etc/portfolio-backup.pub.asc`).
  A privada fica no seu cofre — sem ela ninguém restaura, nem mesmo
  alguém com acesso ao bucket.

## 1. Script de backup

Salve em `/srv/portfolio-backend/scripts/backup-postgres.sh`
(o repositório já tem versionado, mas a cópia em produção é a que
o cron executa):

```bash
#!/usr/bin/env bash
set -euo pipefail

# Carrega DATABASE_URL_SYNC e companhia.
source /srv/portfolio-backend/.env

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="/var/backups/portfolio"
OUT_FILE="${OUT_DIR}/portfolio-${TS}.sql.gz.gpg"

mkdir -p "${OUT_DIR}"

# pg_dump pelo container — não precisamos de psql no host.
docker exec portfolio_postgres \
    pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner --no-acl \
| gzip -9 \
| gpg --batch --yes --trust-model always \
      --recipient backup@eduardoalves.online \
      --encrypt --output "${OUT_FILE}"

chmod 600 "${OUT_FILE}"

# Upload (rclone com bucket pré-configurado em ~root/.config/rclone/rclone.conf).
rclone copy "${OUT_FILE}" "b2:portfolio-backups/" --quiet

# Retenção local: 7 dumps; remoto: aplique lifecycle policy no bucket.
ls -1t "${OUT_DIR}"/portfolio-*.sql.gz.gpg \
    | tail -n +8 \
    | xargs -r rm -f
```

Permissões:

```bash
chmod 700 /srv/portfolio-backend/scripts/backup-postgres.sh
chown root:root /srv/portfolio-backend/scripts/backup-postgres.sh
```

## 2. Importar a chave pública GPG

```bash
gpg --import /etc/portfolio-backup.pub.asc
gpg --edit-key backup@eduardoalves.online trust quit
# Confiança 5 (ultimate) sob este uid no keyring do root.
```

## 3. Cron

`/etc/cron.d/portfolio-backup`:

```
# Postgres backup — 03:15 UTC = ~00:15 BRT, baixa carga.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

15 3 * * * root /srv/portfolio-backend/scripts/backup-postgres.sh \
    >> /var/log/portfolio-backup.log 2>&1
```

`logrotate` separado:

```
/var/log/portfolio-backup.log {
    weekly
    rotate 8
    compress
    notifempty
    missingok
}
```

## 4. Retenção remota (B2 lifecycle rule)

No painel do bucket:

- 30 dias diários
- 12 semanas (mantém 1 dump/semana)
- 12 meses (1 dump/mês)
- expirar versões antigas após 365 dias

Equivalente em outros providers (S3 Lifecycle, R2 Object Lifecycle).

## 5. Teste de restore — obrigatório a cada 30 dias

Backup que nunca foi restaurado é só um arquivo. Um restore mensal
para um Postgres throw-away valida que a chave GPG ainda decifra,
que o dump não está corrompido, e que o schema atual aceita o dump
(útil quando há migrations recentes).

```bash
# Em uma máquina de teste (NÃO no VPS de produção):
docker run --rm -d --name pg-restore-test \
    -e POSTGRES_PASSWORD=throwaway \
    -p 55432:5432 \
    postgres:16-alpine

LATEST=$(rclone lsf b2:portfolio-backups/ | sort | tail -1)
rclone cat "b2:portfolio-backups/${LATEST}" \
    | gpg --decrypt \
    | gunzip \
    | docker exec -i pg-restore-test \
        psql -U postgres -d postgres

# Smoke check:
docker exec pg-restore-test psql -U postgres -d postgres \
    -c 'select count(*) from admin_users;'

docker rm -f pg-restore-test
```

Sucesso ⇒ registre data + hash do arquivo testado em
`docs/backup-restore-log.md`. Falha ⇒ trate como incidente; o backup
seguinte tem que passar antes do próximo ciclo de cron correr.

## 6. Rotação da chave GPG

A cada 24 meses:

1. Gere uma nova chave offline (mesmo procedimento da seção
   "Pré-requisitos").
2. Importe a nova pública no VPS, confie-a.
3. Edite o script para `--recipient` da chave nova.
4. Mantenha a chave antiga ativa por mais 90 dias para conseguir
   decifrar dumps antigos durante a transição. Documente a
   sobreposição em `docs/backup-restore-log.md`.

## Troubleshooting

| Sintoma | Causa provável |
|---|---|
| `gpg: encryption failed: No public key` | Chave do recipient não foi importada/`trust`-ada como root. |
| `pg_dump: error: connection failed` | `.env` mudou e o script não recarregou; ou container `portfolio_postgres` parou. |
| Restore: `relation "auth_events" already exists` | Você está restaurando num DB não-vazio. Use um container limpo. |
| `rclone: AccessDenied` | API key do B2 expirou ou bucket renomeado — refaça `rclone config`. |
