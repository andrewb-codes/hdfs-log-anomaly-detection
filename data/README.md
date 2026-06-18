# Данные

В этой папке должны лежать локальные HDFS данные из LogHub.

Ожидаемая структура:

```text
data/
├── HDFS.log
└── preprocessed/
    ├── anomaly_label.csv
    ├── Event_occurrence_matrix.csv
    ├── Event_traces.csv
    ├── HDFS.log_templates.csv
    └── HDFS.npz
```

## Назначение файлов

```text
HDFS.log
```

Raw HDFS log file. Используется для подготовки sequence datasets через Drain parser.

```text
anomaly_label.csv
```

Block-level labels. Основная целевая переменная: нормальный или аномальный `block_id`.

```text
Event_occurrence_matrix.csv
```

Табличное представление блоков через частоты/наличие событий. Используется в tabular baselines.

```text
Event_traces.csv
```

Последовательности `EventId` по блокам.

```text
HDFS.log_templates.csv
```

Распарсенные шаблоны логов.

```text
HDFS.npz
```

Дополнительный предобработанный формат LogHub.

## Важные предположения

- Основная сущность анализа - `block_id`.
- Метка аномалии задаётся на уровне блока, а не отдельной строки лога.
- Sequence-модели используют порядок событий внутри блока.

## Подготовка LSTM datasets

One-step:

```bash
python scripts/prepare_lstm_data.py --config configs/lstm_one_step_data.yaml
```

Many-to-many:

```bash
python scripts/prepare_lstm_data.py --config configs/lstm_many_to_many_data.yaml
```

Результаты подготовки сохраняются в `artifacts/lstm/...`.

