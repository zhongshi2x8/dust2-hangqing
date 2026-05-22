"""本地持久化：API_KEY、窗口位置、收藏饰品列表。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

CONFIG_DIR = Path.home() / ".steamdt"
CONFIG_PATH = CONFIG_DIR / "config.json"
WATCHLIST_PATH = CONFIG_DIR / "watchlist.json"


@dataclass
class WatchItem:
    marketHashName: str
    displayName: str = ""

    def label(self) -> str:
        return self.displayName or self.marketHashName


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    _ensure_dir()
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def update_config(**kwargs) -> dict:
    cfg = load_config()
    cfg.update(kwargs)
    save_config(cfg)
    return cfg


def load_watchlist() -> list[WatchItem]:
    if not WATCHLIST_PATH.exists():
        return []
    try:
        raw = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = []
    for entry in raw or []:
        if isinstance(entry, str):
            items.append(WatchItem(marketHashName=entry))
        elif isinstance(entry, dict) and entry.get("marketHashName"):
            items.append(
                WatchItem(
                    marketHashName=entry["marketHashName"],
                    displayName=entry.get("displayName", ""),
                )
            )
    return items


def save_watchlist(items: list[WatchItem]) -> None:
    _ensure_dir()
    WATCHLIST_PATH.write_text(
        json.dumps([asdict(i) for i in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_item(items: list[WatchItem], new: WatchItem) -> list[WatchItem]:
    if any(i.marketHashName == new.marketHashName for i in items):
        return items
    items.append(new)
    save_watchlist(items)
    return items


def remove_item(items: list[WatchItem], market_hash_name: str) -> list[WatchItem]:
    items = [i for i in items if i.marketHashName != market_hash_name]
    save_watchlist(items)
    return items
