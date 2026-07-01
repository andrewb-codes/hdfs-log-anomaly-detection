# hdfs-log-anomaly-detection

Anomaly detection in HDFS logs using tabular ML, LSTM sequence models, and a FastAPI inference service.

Проект посвящён поиску аномалий в логах распределённой файловой системы HDFS. Цель - построить и сравнить несколько подходов, которые по событиям внутри `block_id` определяют, является ли блок нормальным или аномальным.

Основной акцент сделан на sequence-based постановке: на инференсе события считаются поступающими последовательно, поэтому модель не должна полагаться только на признаки всего блока целиком. Табличные модели используются как baseline и sanity check, а LSTM-модели - как более близкий к production-like сценарию подход.

## Ключевой результат

Лучший sequence-based подход - many-to-many LSTM с `nll_max` scoring:

| F1 | Precision | Recall | FPR | Average Precision |
|---:|---:|---:|---:|---:|
| 0.911 | 0.966 | 0.863 | 0.0041 | 0.975 |

Главный вывод: для HDFS logs сильнее всего работает не средняя ошибка по блоку, а самый неожиданный переход внутри последовательности. Это соответствует интуиции задачи: аномальный `block_id` часто отличается одним или несколькими резкими нарушениями нормального порядка событий.

Репозиторий демонстрирует полный ML workflow: EDA, feature engineering, baseline-модели, sequence-модели, подбор anomaly scoring, воспроизводимые YAML-конфиги, сохранение reports/artifacts и FastAPI-сервис для inference по raw log lines.

## Что сделано

- EDA предобработанных HDFS logs.
- Табличные baseline-модели: Logistic Regression, Isolation Forest, Random Forest.
- Drain3: парсинг raw HDFS logs в event templates.
- One-step LSTM: предсказание следующего события после окна.
- Many-to-many LSTM: предсказание следующего события для каждой позиции внутри окна.
- Сравнение anomaly scoring strategies: `topk_last`, `topk_all`, `topk_last3`, `nll_mean`, `nll_p95`, `nll_max`.
- Эксперименты с архитектурой LSTM.
- FastAPI-сервис для inference по raw HDFS log lines с сохранением истории запросов в SQLite.
- Streamlit-фронтенд для запуска inference и просмотра служебных endpoints.

## Стек

- Python, NumPy, pandas;
- scikit-learn для табличных baseline;
- PyTorch для LSTM-моделей;
- Drain3 для парсинга raw HDFS logs в event templates;
- FastAPI, SQLAlchemy, SQLite, Alembic для ML-сервиса;
- Streamlit для frontend-интерфейса;
- Docker / Docker Compose для контейнерного запуска API и frontend;
- uv, Ruff, mypy для управления зависимостями, форматирования и type checking;
- Matplotlib для визуализации;
- Jupyter notebooks для EDA и анализа результатов;
- YAML-конфиги для воспроизводимых запусков.

## Идея проекта

Логи представлены через `EventId` / `EventTemplate`, а ключевой объект анализа - `block_id`.

В проекте сравниваются два типа моделей:

- Табличные baseline-модели, которые видят весь блок целиком.
- Последовательные LSTM-модели, которые работают с окнами событий и ближе к production-like сценарию, где события приходят последовательно.

Табличные модели показывают, что в данных есть сильный сигнал, но они используют полную информацию о блоке сразу. Основной фокус проекта - sequence-модели и способы агрегировать их предсказания в anomaly score на уровне блока.

Общий pipeline:

```text
raw/preprocessed HDFS logs
        ↓
event sequences per block_id
        ↓
sliding windows
        ↓
next-event prediction model
        ↓
window-level surprise / miss score
        ↓
block-level anomaly score
        ↓
threshold selected on validation by max F1
```

## Структура

```text
.
├── configs/                 # YAML-конфиги экспериментов
├── data/                    # локальные данные, не коммитятся
├── artifacts/               # модели, подготовленные датасеты, Drain state
├── notebooks/               # EDA и анализ результатов
├── reports/                 # таблицы метрик и графики
├── examples/                # готовые raw logs и JSON payloads для API/frontend
├── scripts/                 # entrypoint-скрипты обучения/evaluation
├── pyproject.toml           # зависимости, package metadata, Ruff/mypy config
├── uv.lock                  # lock-файл для воспроизводимой установки
├── Dockerfile               # общий контейнер API/frontend
├── docker-compose.yml       # запуск API и frontend с mounted artifacts/reports/configs
└── src/hdfs_anomaly/        # основной Python-код проекта
```

Основные модули:

```text
src/hdfs_anomaly/
├── data/        # загрузка предобработанных HDFS файлов
├── features/    # табличные признаки
├── metrics/     # метрики, thresholding, LSTM scoring
├── models/      # tabular, one-step LSTM, many-to-many LSTM
├── parsing/     # Drain parser для raw HDFS logs
├── sequences/   # split, windowing, сохранение LSTM datasets
├── api/         # FastAPI inference service
├── frontend/    # Streamlit frontend
└── utils/       # служебные функции для экспериментов
```

## Данные

Используется набор `HDFS_v1` из [LogPai LogHub](https://github.com/logpai/loghub). Данные не входят в репозиторий; ожидаемая локальная структура описана в [data/README.md](data/README.md).

`HDFS_v1` содержит системные логи Hadoop Distributed File System. В этом датасете события группируются по `block_id`, а разметка задаётся на уровне блока: каждый блок считается нормальным или аномальным. В проекте используются как raw logs для повторного парсинга через Drain3, так и предобработанные файлы с `EventId`, `EventTemplate` и block-level labels.

Краткая статистика используемой версии данных:

| Характеристика | Значение |
|---|---:|
| Raw log lines | 11,175,629 |
| Block-level samples | 575,061 |
| Normal blocks | 558,223 |
| Anomaly blocks | 16,838 |
| Anomaly ratio | 2.93% |
| Event templates | 29 |
| Median sequence length | 19 events |
| Mean sequence length | 19.43 events |
| Max sequence length | 298 events |

Основные файлы:

```text
data/HDFS.log
data/preprocessed/anomaly_label.csv
data/preprocessed/Event_occurrence_matrix.csv
data/preprocessed/Event_traces.csv
data/preprocessed/HDFS.log_templates.csv
data/preprocessed/HDFS.npz
```

## Установка

Проект использует `uv`, `pyproject.toml` и `uv.lock` вместо `requirements.txt`.

Полное окружение для разработки, ноутбуков и экспериментов:

```bash
uv sync --all-groups
```

Runtime-окружение без notebook/dev-зависимостей:

```bash
uv sync --no-dev --no-group notebooks
```

Быстрые проверки кода:

```bash
uv run ruff check src scripts
uv run ruff format src scripts --check
uv run mypy
```

## Notebooks

```text
01_preprocessed_logs_eda.ipynb
```

EDA по предобработанным HDFS логам: распределения событий, длины последовательностей, различия normal/anomaly блоков.

```text
02_tabular_baselines_eval.ipynb
```

Анализ Logistic Regression, Isolation Forest и Random Forest.

```text
03_lstm_one_step_eval.ipynb
```

Подробная оценка базовой one-step LSTM.

```text
04_lstm_one_step_architecture_experiments.ipynb
```

Сравнение архитектур one-step LSTM.

```text
05_lstm_many_to_many_scoring_eval.ipynb
```

Сравнение scoring strategies для базовой many-to-many LSTM.

```text
06_lstm_many_to_many_architecture_experiments.ipynb
```

Сравнение архитектур many-to-many LSTM при фиксированном `nll_max` scoring.

## Запуск экспериментов

### Табличные baseline

```bash
uv run python scripts/train_tabular_baseline.py --config configs/tabular_baselines.yaml
uv run python scripts/evaluate_tabular_baselines.py --config configs/tabular_baselines.yaml
```

### Подготовка LSTM datasets

One-step:

```bash
uv run python scripts/prepare_lstm_data.py --config configs/lstm_one_step_data.yaml
```

Many-to-many:

```bash
uv run python scripts/prepare_lstm_data.py --config configs/lstm_many_to_many_data.yaml
```

### One-step LSTM

```bash
uv run python scripts/train_lstm_one_step.py --config configs/lstm_one_step_e32_h64_l1_d00.yaml
uv run python scripts/evaluate_lstm_one_step.py --config configs/lstm_one_step_e32_h64_l1_d00.yaml
```

### Many-to-many LSTM: сравнение scoring strategies

```bash
uv run python scripts/train_lstm_many_to_many.py --config configs/lstm_many_to_many.yaml
uv run python scripts/evaluate_lstm_many_to_many.py --config configs/lstm_many_to_many.yaml
```

### Many-to-many LSTM: архитектурные эксперименты

Пример:

```bash
uv run python scripts/train_lstm_many_to_many.py --config configs/lstm_many_to_many_nllmax_e64_h128_l1_d00.yaml
uv run python scripts/evaluate_lstm_many_to_many.py --config configs/lstm_many_to_many_nllmax_e64_h128_l1_d00.yaml
```

## FastAPI inference service

В проект добавлен ML-сервис, который выполняет inference обученной many-to-many LSTM по сырым строкам HDFS logs.

Сервис использует:

- checkpoint модели: `artifacts/lstm/many_to_many/<run_name>/model.pt`;
- сохранённый Drain transformer: `artifacts/lstm/many_to_many/drain_event_sequence_transformer.joblib`;
- threshold, подобранный на validation: `reports/lstm_many_to_many/<run_name>/tables/lstm_many_to_many_thresholds.csv`;
- настройки из [configs/api.yaml](configs/api.yaml);
- SQLite-историю запросов: `artifacts/api/history.sqlite3`.

Перед запуском должны быть доступны файлы модели, Drain transformer и таблица threshold, указанные в `configs/api.yaml`.

Локальные переменные окружения можно положить в `.env`:

```bash
cp .env.example .env
```

`.env` автоматически читается API и Streamlit при локальном запуске, а также используется `docker-compose.yml`. Файл `.env.example` содержит безопасный шаблон для коммита, а реальный `.env` игнорируется git.

Для Docker Compose внешний порт frontend задаётся в `.env`:

```text
FRONTEND_PORT=8501
```

Локальный запуск:

```bash
uv run alembic upgrade head
uv run uvicorn hdfs_anomaly.api.app:app --reload
```

В отдельном терминале можно запустить Streamlit-фронтенд:

```bash
uv run streamlit run src/hdfs_anomaly/frontend/app.py
```

По умолчанию frontend обращается к `HDFS_API_URL`, а если переменная не задана - к `http://127.0.0.1:8000`. Адрес API можно переопределить явно:

```bash
uv run uvicorn hdfs_anomaly.api.app:app --reload --port 9000
HDFS_API_URL=http://127.0.0.1:9000 uv run streamlit run src/hdfs_anomaly/frontend/app.py
```

Docker-запуск:

```bash
docker compose up --build
```

Docker image собирается через `uv sync --frozen --no-dev --no-group notebooks`, поэтому в контейнер попадают только runtime-зависимости API и frontend. Данные, модели и reports не вшиваются в image: `docker-compose.yml` монтирует локальные папки `./artifacts`, `./reports` и `./configs` внутрь API-контейнера. При старте API-контейнер автоматически выполняет `alembic upgrade head`, а затем запускает `uvicorn`. API не публикуется на host и доступен только внутри Docker-сети по адресу `http://api:8000`; frontend-контейнер обращается к этому внутреннему адресу.

Streamlit UI после запуска доступен по адресу:

```text
http://127.0.0.1:8501
```

Примеры raw logs для быстрой проверки лежат в `examples/`:

```text
examples/normal_block_logs.txt
examples/anomaly_block_logs.txt
```

Их можно вставить в поле `Log lines` в Streamlit. Для локального запуска API без Docker также доступны готовые payloads:

```bash
curl -X POST http://127.0.0.1:8000/forward \
  -H "Content-Type: application/json" \
  -d @examples/api_forward_normal.json

curl -X POST http://127.0.0.1:8000/forward \
  -H "Content-Type: application/json" \
  -d @examples/api_forward_anomaly.json
```

JWT-авторизация требует переменные окружения:

```text
API_SECRET_KEY=change-me
API_ADMIN_USERNAME=admin
API_ADMIN_PASSWORD=admin
API_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Для локального запуска скопируйте `.env.example` в `.env` и задайте свои значения.

Основные endpoints:

| Method | Route | Назначение |
|---|---|---|
| `GET` | `/health` | Проверка состояния сервиса и загрузки модели |
| `POST` | `/auth/login` | Получение JWT для admin endpoints |
| `GET` | `/model-info` | Информация о загруженной модели, threshold и scoring |
| `POST` | `/forward` | Inference по raw HDFS log lines |
| `GET` | `/history` | История успешных и неуспешных model calls |
| `DELETE` | `/history` | Очистка истории |
| `GET` | `/stats` | Статистика запросов и времени обработки |

`/forward` и `/health` доступны без авторизации. `/model-info`, `/history`, `DELETE /history` и `/stats` требуют JWT в header:

```text
Authorization: Bearer <access_token>
```

Получение токена:

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

Формат запроса `/forward`:

```bash
curl -X POST http://127.0.0.1:8000/forward \
  -H "Content-Type: application/json" \
  -d '{
    "block_id": "blk_7503483334202473044",
    "log_lines": [
      "081109 203615 148 INFO dfs.DataNode$DataXceiver: Receiving block blk_7503483334202473044 src: /10.0.0.1:1 dest: /10.0.0.2:2",
      "..."
    ],
    "return_event_ids": true,
    "return_window_scores": true
  }'
```

Для many-to-many LSTM нужно больше `window_size` событий в одном блоке, иначе сервис вернёт ошибку inference. Для проверки удобно отправлять несколько десятков реальных строк одного `block_id` из `data/HDFS.log`.

Пример успешного ответа:

```json
{
  "block_id": "blk_7503483334202473044",
  "score": 4.8507,
  "threshold": 8.6785,
  "is_anomaly": false,
  "scoring_strategy": "nll_max",
  "num_log_lines": 22,
  "num_events": 22,
  "num_windows": 12,
  "event_ids": [0, 0, 1, 0, 2],
  "window_scores": [1.1899, 1.3688, 1.1948]
}
```

Очистка истории:

```bash
curl -X DELETE http://127.0.0.1:8000/history \
  -H "Authorization: Bearer <access_token>"
```

## Scoring

### Top-k miss

Модель предсказывает следующий `EventId`. Если истинный следующий event не входит в top-k предсказаний, это считается miss.

Для блока:

```text
score(block) = num_misses / num_windows
```

### Many-to-many top-k variants

```text
topk_last   # только последний переход окна
topk_all    # все позиции окна
topk_last3  # последние 3 позиции окна
```

### NLL scoring

```text
NLL = -log P(true_event)
```

Агрегации:

```text
nll_mean  # средняя неожиданность по блоку
nll_p95   # 95-й перцентиль неожиданности
nll_max   # самый неожиданный переход в блоке
```

`nll_max` оказался лучшей стратегией: аномальный HDFS block часто содержит хотя бы один резко непривычный переход.

## Результаты

Актуальные test-метрики из сохранённых reports:

| Подход | Модель / scoring | F1 | Precision | Recall | FPR | AP |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | full-block tabular | 0.991 | 0.984 | 0.999 | 0.0005 | 0.993 |
| Isolation Forest | full-block tabular | 0.328 | 0.247 | 0.486 | 0.0446 | 0.155 |
| Random Forest | full-block tabular | 0.999 | 0.999 | 0.999 | 0.0000 | 1.000 |
| One-step LSTM | top-k miss | 0.706 | 0.746 | 0.670 | 0.0305 | 0.671 |
| Many-to-many LSTM | baseline + `nll_max` | 0.887 | 0.963 | 0.823 | 0.0043 | 0.951 |
| Many-to-many LSTM | best architecture + `nll_max` | 0.911 | 0.966 | 0.863 | 0.0041 | 0.975 |

Табличные supervised-модели дают очень высокое качество, но это не полностью production-like сценарий: модель видит весь блок целиком. Последовательные модели важнее для сценария, где события поступают по порядку.

Ключевой итог проекта: many-to-many LSTM с `nll_max` scoring даёт сильный sequence-based результат и существенно снижает FPR относительно one-step baseline.

Подробнее про структуру результатов см. [reports/README.md](reports/README.md).

## References

- **LogHub / HDFS dataset**: He et al., *LogHub: A Large Collection of System Log Datasets for AI-driven Log Analytics*.  
  https://github.com/logpai/loghub

- **DeepLog**: Du et al., *DeepLog: Anomaly Detection and Diagnosis from System Logs through Deep Learning*, CCS 2017.  
  https://dl.acm.org/doi/10.1145/3133956.3134015

- **LogBERT**: Guo et al., *LogBERT: Log Anomaly Detection via BERT*, 2021.  
  https://arxiv.org/abs/2103.04475

- **LogGPT**: Han et al., *LogGPT: Log Anomaly Detection via GPT*, 2023.  
  https://arxiv.org/abs/2309.14482

- **Critical evaluation of DL log anomaly detection**: Le and Zhang, *Log-based Anomaly Detection with Deep Learning: How Far Are We?*, 2022.  
  https://arxiv.org/abs/2202.04301
