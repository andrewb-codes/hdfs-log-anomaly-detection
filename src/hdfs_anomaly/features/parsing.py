import pandas as pd


def parse_event_sequence(value: str) -> list[str]:
    """Parse a LogHub event sequence string like '[E5,E22,E5]'."""
    if pd.isna(value):
        return []

    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    if not text:
        return []

    return [event_id.strip() for event_id in text.split(",") if event_id.strip()]


def parse_time_intervals(value: str) -> list[float]:
    """Parse a TimeInterval string like '[0.0, 1.0, 0.0]'."""
    if pd.isna(value):
        return []

    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    if not text:
        return []

    return [float(item.strip()) for item in text.split(",") if item.strip()]
