# hdfs-log-anomaly-detection

Anomaly detection in HDFS logs using tabular ML, LSTM sequence models, and LogBERT-style scoring.

Проект посвящён поиску аномалий в логах распределённой файловой системы HDFS. Основная задача - определить, является ли `block_id` нормальным или аномальным по последовательности событий, связанных с этим блоком.

Данные основаны на HDFS logs из LogHub. Логи предварительно распарсены в `EventId` / `EventTemplate`, а ключевой объект анализа - `block_id`.

## Идея проекта

В проекте сравниваются два типа подходов:

- Табличные baseline-модели, которые видят весь блок целиком.
- Последовательные LSTM-модели, которые работают с окнами событий и ближе к production-like сценарию, где события приходят последовательно.

Табличные модели нужны как sanity check: они показывают, что в данных есть сильный сигнал. Но основной фокус проекта - sequence-модели и способы агрегировать их предсказания в anomaly score на уровне блока.

## Структура

```text
.
├── configs/                 # YAML-конфиги экспериментов
├── data/                    # локальные данные, не коммитятся
├── artifacts/               # модели, подготовленные датасеты, Drain state
├── notebooks/               # EDA и анализ результатов
├── reports/                 # таблицы метрик и графики
├── scripts/                 # entrypoint-скрипты обучения/evaluation
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
└── utils/       # служебные функции для экспериментов
```

## Данные

Данные не входят в репозиторий. Ожидаемая локальная структура описана в [data/README.md](data/README.md).

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

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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
python scripts/train_tabular_baseline.py --config configs/tabular_baselines.yaml
python scripts/evaluate_tabular_baselines.py --config configs/tabular_baselines.yaml
```

### Подготовка LSTM datasets

One-step:

```bash
python scripts/prepare_lstm_data.py --config configs/lstm_one_step_data.yaml
```

Many-to-many:

```bash
python scripts/prepare_lstm_data.py --config configs/lstm_many_to_many_data.yaml
```

### One-step LSTM

```bash
python scripts/train_lstm_one_step.py --config configs/lstm_one_step_e32_h64_l1_d00.yaml
python scripts/evaluate_lstm_one_step.py --config configs/lstm_one_step_e32_h64_l1_d00.yaml
```

### Many-to-many LSTM: сравнение scoring strategies

```bash
python scripts/train_lstm_many_to_many.py --config configs/lstm_many_to_many.yaml
python scripts/evaluate_lstm_many_to_many.py --config configs/lstm_many_to_many.yaml
```

### Many-to-many LSTM: архитектурные эксперименты

Пример:

```bash
python scripts/train_lstm_many_to_many.py --config configs/lstm_many_to_many_nllmax_e64_h128_l1_d00.yaml
python scripts/evaluate_lstm_many_to_many.py --config configs/lstm_many_to_many_nllmax_e64_h128_l1_d00.yaml
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
