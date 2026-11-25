from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"
CONFIG_FILE = DATA_DIR / "guild_config.json"


def _load_all() -> dict[str, dict[str, Any]]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        raw = CONFIG_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(data: dict[str, dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file = CONFIG_FILE.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_file.replace(CONFIG_FILE)


def get_guild_config(guild_id: int) -> dict[str, Any]:
    return _load_all().get(str(guild_id), {})


def set_guild_channel(guild_id: int, key: str, channel_id: int) -> None:
    data = _load_all()
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {}
    data[gid][key] = channel_id
    _save_all(data)
