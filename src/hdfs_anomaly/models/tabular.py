from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TABULAR_MODEL_NAMES = ("logistic_regression", "isolation_forest", "random_forest")


def build_logistic_regression(
    random_state: int = 42,
    max_iter: int = 2000,
    class_weight: str | dict | None = "balanced",
) -> Pipeline:
    return Pipeline(
        steps=[
            ("scaler", StandardScaler(with_mean=False)),
            (
                "classifier",
                LogisticRegression(
                    max_iter=max_iter,
                    random_state=random_state,
                    class_weight=class_weight,
                ),
            ),
        ]
    )


def build_isolation_forest(
    random_state: int = 42,
    n_estimators: int = 300,
) -> IsolationForest:
    return IsolationForest(
        n_estimators=n_estimators,
        n_jobs=-1,
        random_state=random_state,
    )


def build_random_forest(
    random_state: int = 42,
    n_estimators: int = 300,
    class_weight: str | dict | None = "balanced_subsample",
) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=n_estimators,
        n_jobs=-1,
        random_state=random_state,
        class_weight=class_weight,
    )


def build_tabular_model(name: str, random_state: int = 42, **params):
    params = {
        key: value
        for key, value in params.items()
        if key not in {"enabled", "train_on_normal_only"}
    }
    if name == "logistic_regression":
        return build_logistic_regression(random_state=random_state, **params)
    if name == "isolation_forest":
        return build_isolation_forest(random_state=random_state, **params)
    if name == "random_forest":
        return build_random_forest(random_state=random_state, **params)
    raise ValueError(f"Unknown tabular model: {name}")
