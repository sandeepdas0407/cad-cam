from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "index.db"
PAGE_CACHE_DIR = DATA_DIR / "page_cache"


class Secrets(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8"
    )

    voyage_api_key: str = ""


def load_yaml_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_settings() -> dict:
    """Returns merged runtime config: yaml settings + secrets. Re-read fresh each call
    so watched_folders/params can change without restarting the server."""
    cfg = load_yaml_config()
    secrets = Secrets()
    cfg["voyage_api_key"] = secrets.voyage_api_key
    watched = cfg.get("watched_folders", [])
    resolved = []
    for folder in watched:
        p = Path(folder)
        if not p.is_absolute():
            p = (BASE_DIR / p).resolve()
        resolved.append(p)
    cfg["watched_folders_resolved"] = resolved
    return cfg


DATA_DIR.mkdir(exist_ok=True)
PAGE_CACHE_DIR.mkdir(exist_ok=True)
