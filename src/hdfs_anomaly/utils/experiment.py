import random
from pathlib import Path

import numpy as np
import torch
import yaml


def load_config(config_path: Path) -> dict:
    """Load a YAML experiment config."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def resolve_project_path(value: str | Path, root: Path) -> Path:
    """Resolve a config path relative to the project root."""
    path = Path(value)
    return path if path.is_absolute() else root / path


def set_seed(seed: int) -> None:
    """Seed Python, NumPy, and Torch random generators."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def select_device(requested_device: str) -> str:
    """Return an available torch device from a requested device string."""
    if requested_device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested_device.startswith("cuda") and not torch.cuda.is_available():
        return "cpu"
    return requested_device
