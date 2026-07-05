# Деплой через Ansible

Этот сценарий деплоит HDFS Log Anomaly Detection на один Ubuntu/Debian VPS через Docker Compose.
Сервер не билдит приложение из исходников: playbook подтягивает готовые Docker images из GHCR.

Production compose запускает два контейнера:

- `api` — FastAPI inference service из `Dockerfile.api`;
- `frontend` — Streamlit UI из `Dockerfile.frontend`.

FastAPI остается только во внутренней Docker-сети проекта. Streamlit обращается к нему по адресу
`http://api:8000`. Наружу через общую Docker-сеть `web` подключается только frontend.

## Файлы

- `inventory.ini.example` — пример inventory; скопировать в `inventory.ini` и указать адрес VPS.
- `group_vars/portfolio/main.yml` — несекретные настройки деплоя для общего portfolio VPS.
- `group_vars/portfolio/vault.yml.example` — пример секретов; скопировать в
  `group_vars/portfolio/vault.yml` и зашифровать через Ansible Vault.
- `templates/env.j2` — шаблон production `.env`.
- `templates/docker-compose.prod.yml.j2` — шаблон production compose-файла.
- `playbook.yml` — устанавливает Docker, создает общую Docker-сеть `web`, рендерит `.env` и
  compose-файл, подтягивает images, запускает Alembic миграции и поднимает сервисы.

## Docker Images

Production compose использует два image из `group_vars/portfolio/main.yml`:

```yaml
api_image: ghcr.io/andrewb-codes/hdfs-log-anomaly-detection-api
frontend_image: ghcr.io/andrewb-codes/hdfs-log-anomaly-detection-frontend
app_image_tag: main
```

При автоматическом деплое GitHub Actions собирает оба image, публикует их в GHCR с тегами
`main` и commit SHA, а затем запускает playbook с тегом текущего коммита. VPS получает готовые
images через `docker compose pull`.

## Данные И Артефакты

Images не содержат модели, reports и configs. На VPS должны существовать bind mount директории:

```text
/opt/apps/hdfs-anomaly/artifacts
/opt/apps/hdfs-anomaly/reports
/opt/apps/hdfs-anomaly/configs
```

Playbook создает эти директории, но содержимое нужно загрузить отдельно. В них должны быть файлы,
на которые ссылается `configs/api.yaml`: checkpoint модели, Drain transformer и таблица threshold.

## Автоматический Деплой Из GitHub Actions

Workflow `.github/workflows/ci.yml` запускает деплой после успешных проверок только при push в `main`.

Нужно добавить GitHub Variables:

```text
VPS_HOST
VPS_USER
```

И GitHub Secrets:

```text
VPS_SSH_KEY
ADMIN_USERNAME
ADMIN_PASSWORD
JWT_SECRET
```

`VPS_SSH_KEY` — приватный SSH-ключ, которым GitHub Actions подключается к VPS. Публичная часть
ключа должна быть добавлена на сервер в `~/.ssh/authorized_keys` для пользователя `VPS_USER`.

## Ручной Запуск Без GitHub Actions

Перед ручным запуском нужные images уже должны быть опубликованы в GHCR. Обычно это делает GitHub
Actions после push в `main`.

```bash
cd deploy/ansible
cp inventory.ini.example inventory.ini
cp group_vars/portfolio/vault.yml.example group_vars/portfolio/vault.yml
ansible-vault encrypt group_vars/portfolio/vault.yml
ansible-playbook playbook.yml --ask-vault-pass
```

Чтобы не вводить пароль Vault вручную при каждом запуске, можно хранить его вне репозитория:

```bash
mkdir -p ~/.ansible
nano ~/.ansible/hdfs-anomaly-vault-pass
chmod 600 ~/.ansible/hdfs-anomaly-vault-pass
```

В файле `~/.ansible/hdfs-anomaly-vault-pass` должна быть одна строка: пароль от Ansible Vault без
кавычек. Проверить расшифровку:

```bash
ansible-vault view group_vars/portfolio/vault.yml --vault-password-file ~/.ansible/hdfs-anomaly-vault-pass
```

Запуск playbook с файлом пароля:

```bash
ansible-playbook playbook.yml --vault-password-file ~/.ansible/hdfs-anomaly-vault-pass
```

## Полезные Команды На VPS

```bash
cd /opt/apps/hdfs-anomaly
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml run --rm api alembic current
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
```

## Caddy И Общая Docker-Сеть

Playbook создает external Docker network `web`. Это общая сеть для reverse proxy и всех публичных
приложений на VPS.

HDFS Anomaly Detection подключает к этой сети только публичный frontend:

- `hdfs-anomaly-frontend` — Streamlit на порту `8501`.

FastAPI к `web` не подключается и остается только во внутренней `default`-сети проекта.
Streamlit ходит в API внутри этой сети по адресу `http://api:8000`.

Пример Caddyfile для отдельного proxy compose-проекта:

```caddyfile
hdfs-anomaly.example.com {
  reverse_proxy hdfs-anomaly-frontend:8501
}
```

Когда на сервер добавятся другие приложения, они тоже должны подключать свои публичные сервисы к
сети `web` со своими alias-ами, например `rag-frontend` или `admin-frontend`.
