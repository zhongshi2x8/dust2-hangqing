"""SteamDT 开放平台 REST 客户端。

文档：https://doc.steamdt.com/
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests


BASE_URL = "https://open.steamdt.com"
BASE_CACHE_PATH = Path.home() / ".steamdt" / "base_cache.json"


def _resource_path(name: str) -> Path:
    """打包后 PyInstaller 把资源解到 sys._MEIPASS；源码运行时退回到本文件同目录。"""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / name


# 项目内打包的永久字典副本（39k+ 饰品，约 10MB）
BUNDLED_BASE_DICT = _resource_path("base_dict.json")


class SteamDTError(RuntimeError):
    def __init__(self, code: int, msg: str):
        super().__init__(f"[{code}] {msg}")
        self.code = code
        self.msg = msg


@dataclass
class YouPinPrice:
    market_hash_name: str
    sell_price: float | None
    sell_count: int | None
    bidding_price: float | None
    bidding_count: int | None
    update_time: int | None


@dataclass
class BroadIndex:
    value: float
    diff_yesterday: float
    diff_yesterday_ratio: float
    update_time: int


class SteamDTClient:
    def __init__(self, api_key: str, timeout: float = 8.0):
        self._api_key = api_key
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    # ----- HTTP helpers -----

    def _request(self, method: str, path: str, *, params=None, json_body=None) -> dict:
        url = f"{BASE_URL}{path}"
        resp = self._session.request(
            method,
            url,
            params=params,
            json=json_body,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success", False):
            raise SteamDTError(
                int(body.get("errorCode") or -1),
                str(body.get("errorMsg") or body.get("errorCodeStr") or "unknown"),
            )
        return body.get("data") or {}

    # ----- Endpoints -----

    def get_broad_index(self) -> BroadIndex:
        data = self._request("GET", "/open/cs2/broad/v1/index")
        return BroadIndex(
            value=float(data.get("broadMarketIndex") or 0.0),
            diff_yesterday=float(data.get("diffYesterday") or 0.0),
            diff_yesterday_ratio=float(data.get("diffYesterdayRatio") or 0.0),
            update_time=int(data.get("updateTime") or 0),
        )

    def batch_price(self, names: Iterable[str]) -> dict[str, YouPinPrice]:
        """批量查询多个 marketHashName 的 YOUPIN 价格。

        返回 {marketHashName: YouPinPrice}，没有 YOUPIN 数据的条目仍会出现但字段为 None。
        """
        result: dict[str, YouPinPrice] = {}
        names = [n for n in names if n]
        if not names:
            return result

        # 100 条一批
        for i in range(0, len(names), 100):
            chunk = names[i : i + 100]
            data = self._request(
                "POST",
                "/open/cs2/v1/price/batch",
                json_body={"marketHashNames": chunk},
            )
            for item in data or []:
                name = item.get("marketHashName")
                if not name:
                    continue
                youpin = next(
                    (d for d in (item.get("dataList") or []) if d.get("platform") == "YOUPIN"),
                    None,
                )
                if youpin:
                    result[name] = YouPinPrice(
                        market_hash_name=name,
                        sell_price=_as_float(youpin.get("sellPrice")),
                        sell_count=_as_int(youpin.get("sellCount")),
                        bidding_price=_as_float(youpin.get("biddingPrice")),
                        bidding_count=_as_int(youpin.get("biddingCount")),
                        update_time=_as_int(youpin.get("updateTime")),
                    )
                else:
                    result[name] = YouPinPrice(name, None, None, None, None, None)

            # 占位：未返回的也写空
            for n in chunk:
                result.setdefault(n, YouPinPrice(n, None, None, None, None, None))
        return result

    def get_base_dict(self, force_refresh: bool = False) -> list[dict]:
        """返回 [{name, marketHashName, platformList:[...]}, ...]。

        /open/cs2/v1/base 每个 API_KEY 每天只能调一次（错误码 4005），太脆弱。
        项目内已经打包了一份完整副本 base_dict.json（约 39k 饰品），优先读它。
        force_refresh=True 时才会真的发请求（基本不需要用到）。
        """
        # 优先级 1：项目内打包的永久副本
        if not force_refresh and BUNDLED_BASE_DICT.exists():
            try:
                return json.loads(BUNDLED_BASE_DICT.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass

        # 优先级 2：运行时缓存
        if not force_refresh and BASE_CACHE_PATH.exists():
            try:
                return json.loads(BASE_CACHE_PATH.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass

        # 优先级 3：实在没有时才发请求（注意会消耗当日唯一额度）
        data = self._request("GET", "/open/cs2/v1/base")
        items = data if isinstance(data, list) else []
        BASE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASE_CACHE_PATH.write_text(
            json.dumps(items, ensure_ascii=False), encoding="utf-8"
        )
        return items


def _as_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _as_int(v) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
