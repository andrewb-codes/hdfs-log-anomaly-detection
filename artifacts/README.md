# Артефакты

Эта папка предназначена для локальных файлов, которые нужны для запуска экспериментов, но не должны коммититься в репозиторий.

Сюда относятся:

- обученные модели;
- подготовленные LSTM datasets;
- serialized Drain transformer;
- Drain state;
- бинарные intermediate-файлы.

## Ожидаемая структура

```text
artifacts/
├── tabular/
│   ├── logistic_regression.joblib
│   ├── isolation_forest.joblib
│   └── random_forest.joblib
├── drain/
│   ├── one_step_drain3_state.bin
│   └── many_to_many_drain3_state.bin
├── api/
│   └── history.sqlite3
└── lstm/
    ├── one_step/
    │   ├── dataset.npz
    │   ├── meta.json
    │   ├── drain_event_sequence_transformer.joblib
    │   └── <run_name>/
    │       └── model.pt
    └── many_to_many/
        ├── dataset.npz
        ├── meta.json
        ├── drain_event_sequence_transformer.joblib
        └── <run_name>/
            └── model.pt
```

## Что где лежит

```text
artifacts/lstm/one_step/dataset.npz
artifacts/lstm/many_to_many/dataset.npz
```

Подготовленные окна для LSTM. Эти файлы создаются `scripts/prepare_lstm_data.py`.

```text
meta.json
```

Метаданные подготовленного sequence dataset: window size, stride, vocab size, количество окон и блоков.

```text
drain_event_sequence_transformer.joblib
```

Сериализованный Drain transformer, который переводит raw log lines в последовательности event ids.

```text
artifacts/api/history.sqlite3
```

SQLite-база истории запросов FastAPI-сервиса.

```text
<run_name>/model.pt
```

PyTorch checkpoint конкретного запуска. Внутри сохраняются:

- `state_dict`;
- `vocab_size`;
- `model_config`;
- `scoring_config`;
- `early_stopping_config`;
- `best_epoch`;
- `best_val_loss`.
