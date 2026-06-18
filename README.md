# hdfs-log-anomaly-detection

Anomaly detection in HDFS logs using tabular ML, LSTM sequence models, and LogBERT-style scoring.

Проект посвящён поиску аномалий в логах распределённой файловой системы HDFS. Цель - построить и сравнить несколько подходов, которые по событиям внутри `block_id` определяют, является ли блок нормальным или аномальным.

Основной акцент сделан на sequence-based постановке: на инференсе события считаются поступающими последовательно, поэтому модель не должна полагаться только на признаки всего блока целиком. Табличные модели используются как baseline и sanity check, а LSTM-модели - как более близкий к production-like сценарию подход.

## Что сделано

- EDA предобработанных HDFS logs.
- Табличные baseline-модели: Logistic Regression, Isolation Forest, Random Forest.
- Drain3: парсинг raw HDFS logs в event templates.
- One-step LSTM: предсказание следующего события после окна.
- Many-to-many LSTM: предсказание следующего события для каждой позиции внутри окна.
- Сравнение anomaly scoring strategies: `topk_last`, `topk_all`, `topk_last3`, `nll_mean`, `nll_p95`, `nll_max`.
- Эксперименты с архитектурой LSTM.
- Подготовлена структура для расширения в сторону LogBERT-style scoring.

## Стек

- Python, NumPy, pandas;
- scikit-learn для табличных baseline;
- PyTorch для LSTM-моделей;
- Drain3 для парсинга raw HDFS logs в event templates;
- Matplotlib / seaborn для визуализации;
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
