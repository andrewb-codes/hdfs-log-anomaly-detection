# Reports

В этой папке лежат результаты экспериментов: таблицы метрик, score-файлы и графики, которые используются в notebooks.

## Структура

```text
reports/
├── eda/
│   ├── figures/
│   └── tables/
├── tabular_baselines/
│   ├── figures/
│   └── tables/
├── lstm_one_step/
│   ├── <run_name>/
│   │   ├── figures/
│   │   └── tables/
│   └── architecture_experiments/
└── lstm_many_to_many/
    ├── <run_name>/
    │   ├── figures/
    │   └── tables/
    └── architecture_experiments/
```

## Что хранится в tables

Обычно здесь лежат:

- `*_validation_metrics.csv` - метрики на validation split;
- `*_test_metrics.csv` - итоговые test-метрики;
- `*_thresholds.csv` - пороги, подобранные на validation по максимуму F1;
- `*_history.json` - train/validation loss по эпохам;
- `scores_*.csv` - block-level anomaly scores.

## Что хранится в figures

Здесь лежат графики из notebooks:

- confusion matrices;
- precision-recall curves;
- score distributions;
- сравнение метрик;
- training curves;
- ошибки FP/FN.
