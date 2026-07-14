# Деплой через Ansible

Playbook деплоит приложение на один Ubuntu/Debian VPS. Сервер загружает готовые 
API/frontend images из GHCR и запускает четыре сервиса через Docker Compose:

- `redis` — Redis для счетчиков rate limiting во внутренней сети;
- `postgres` — PostgreSQL 17 с volume `hdfs_anomaly_data` во внутренней сети;
- `api` — FastAPI во внутренней сети;
- `frontend` — Streamlit во внутренней сети и общей external-сети `web`.

Streamlit обращается к API по адресу `http://api:8000`. 
Reverse proxy обращается к frontend по alias `hdfs-anomaly-frontend:8501`. 
API, PostgreSQL и Redis снаружи не публикуются.

## Конфигурация

- `inventory.ini.example` — пример inventory;
- `group_vars/portfolio/main.yml` — несекретные переменные;
- `group_vars/portfolio/vault.yml.example` — шаблон секретов;
- `templates/env.j2` — production `.env`;
- `templates/docker-compose.prod.yml.j2` — production Compose;
- `playbook.yml` — установка Docker, очистка неиспользуемых Docker-объектов
  без удаления volumes, миграции, seed и запуск сервисов.

Production images:

```yaml
api_image: ghcr.io/andrewb-codes/hdfs-log-anomaly-detection-api
frontend_image: ghcr.io/andrewb-codes/hdfs-log-anomaly-detection-frontend
app_image_tag: main
```

Seed-скрипт создает включенные в `app_env` сущности:

- bootstrap admin из `BOOTSTRAP_ADMIN_*`;
- demo-профиль из `DEMO_*`.

Пароли задаются через Ansible Vault или GitHub Secrets. Повторный seed не
создает профили с уже существующими email. Если email bootstrap admin занят
профилем без роли `ADMIN`, deploy завершается с ошибкой.

## Что делает playbook

1. Устанавливает Docker Engine и Compose plugin.
2. Очищает неиспользуемые Docker-объекты без удаления volumes, чтобы
   освободить место перед pull.
3. Создаёт external-сеть `web` и каталог `/opt/apps/hdfs-anomaly`.
4. Рендерит production `.env` и `docker-compose.prod.yml`.
5. Синхронизирует `artifacts/`, `reports/` и `configs/` из Selectel S3.
6. Загружает images, запускает PostgreSQL/Redis, Alembic-миграции и seed admin/demo-профилей.
7. Поднимает API и frontend.
8. Повторно очищает неиспользуемые Docker-объекты после замены контейнеров.

Основные настройки находятся в `group_vars/portfolio/main.yml`, 
секреты — в зашифрованном `group_vars/portfolio/vault.yml`.

## Runtime-файлы

В S3 ожидается следующая структура:

```text
s3://hdfs-anomaly-artifacts-prod/prod/artifacts/...
s3://hdfs-anomaly-artifacts-prod/prod/reports/...
s3://hdfs-anomaly-artifacts-prod/prod/configs/...
```

В ней должны присутствовать checkpoint, Drain transformer и threshold, указанные в
`configs/api.yaml`. На VPS файлы синхронизируются в
`/opt/apps/hdfs-anomaly/{artifacts,reports,configs}`.

## Автоматический деплой

Workflow `.github/workflows/ci-cd.yml` запускает deploy после успешных проверок 
при push в `main`. Images публикуются с тегами `main` и commit SHA.

GitHub Variables:

```text
VPS_HOST
VPS_USER
```

GitHub Secrets:

```text
VPS_SSH_KEY
POSTGRES_PASSWORD
JWT_SECRET
S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY
BOOTSTRAP_ADMIN_PASSWORD
DEMO_PASSWORD
RATE_LIMIT_KEY_SECRET
```

Публичная часть `VPS_SSH_KEY` должна находиться в `~/.ssh/authorized_keys` 
пользователя `VPS_USER`.

## Ручной запуск

```bash
cd deploy/ansible
cp inventory.ini.example inventory.ini
cp group_vars/portfolio/vault.yml.example group_vars/portfolio/vault.yml

# Заполнить inventory и vault.yml, затем:
ansible-vault encrypt group_vars/portfolio/vault.yml
ansible-playbook playbook.yml --ask-vault-pass
```

Для запуска без интерактивного ввода создайте файл с паролем Vault вне
репозитория:

```bash
mkdir -p ~/.ansible
nano ~/.ansible/hdfs-anomaly-vault-pass
chmod 600 ~/.ansible/hdfs-anomaly-vault-pass
ansible-playbook playbook.yml \
  --vault-password-file ~/.ansible/hdfs-anomaly-vault-pass
```

Ожидаемые поля Vault перечислены в `vault.yml.example`. Application images
должны быть заранее опубликованы в GHCR.

## Диагностика

```bash
cd /opt/apps/hdfs-anomaly
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f postgres
docker compose -f docker-compose.prod.yml logs -f redis
docker compose -f docker-compose.prod.yml run --rm api alembic current
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml run --rm api python -m hdfs_anomaly.app.scripts.seed_data
```

## Ротация пароля PostgreSQL

`POSTGRES_PASSWORD` применяется только при первичной инициализации пустого volume.
Для существующей БД сначала измените пароль роли:

```bash
cd /opt/apps/hdfs-anomaly
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U anomaly_user -d anomaly
```

В `psql`:

```text
\password anomaly_user
\q
```

Затем обновите `postgres_password` в Ansible Vault или `POSTGRES_PASSWORD` в GitHub
Secrets и повторите deploy. Удаление `hdfs_anomaly_data` приводит к потере данных. 

## Caddy

Пример конфигурации для reverse proxy, подключённого к сети `web`:

```caddyfile
hdfs-anomaly.example.com {
  reverse_proxy hdfs-anomaly-frontend:8501
}
```
