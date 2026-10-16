"""Persistent provenance-aware cache for validated live evidence."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from config import CACHE_DIR


class ExtractionCache:
    def __init__(self, cache_file: str):
        self.path = Path(CACHE_DIR) / cache_file
        self.data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[WARN] Ignoring unreadable extraction cache {self.path}: {exc}")
            self.data = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary_path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary_path.replace(self.path)

    def get(self, key: str) -> Optional[Any]:
        return self.data.get(key)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def has(self, key: str) -> bool:
        return key in self.data
