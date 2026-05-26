"""CS2 行情悬浮窗入口。"""

from __future__ import annotations

import sys
import traceback

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

from price_worker import PriceWorkerController
from steamdt_client import SteamDTClient, SteamDTError, YouPinPrice, _resource_path
from ui.add_dialog import AddDialog
from ui.floating_window import DEFAULT_BG_ALPHA, DEFAULT_REFRESH_SEC, FloatingWindow
from watchlist import (
    WatchItem,
    add_item,
    load_config,
    load_watchlist,
    remove_item,
    update_config,
    update_quantity,
)


def ensure_api_key() -> str:
    cfg = load_config()
    key = (cfg.get("api_key") or "").strip()
    if key:
        return key
    text, ok = QInputDialog.getText(
        None,
        "SteamDT API Key",
        "请输入 SteamDT 的 API_KEY（保存到 ~/.steamdt/config.json）：",
        QLineEdit.EchoMode.Normal,
    )
    if not ok or not text.strip():
        QMessageBox.critical(None, "缺少 API_KEY", "未提供 API_KEY，程序退出。")
        sys.exit(1)
    update_config(api_key=text.strip())
    return text.strip()


class AppController:
    def __init__(self, client: SteamDTClient):
        self.client = client
        self.items: list[WatchItem] = load_watchlist()
        self._latest_prices: dict[str, YouPinPrice] = {}

        cfg = load_config()
        show_bid = bool(cfg.get("show_bid", True))
        ui_scale = float(cfg.get("ui_scale", 1.0))
        bg_alpha = int(cfg.get("bg_alpha", DEFAULT_BG_ALPHA))
        refresh_sec = int(cfg.get("refresh_sec", DEFAULT_REFRESH_SEC))

        self.window = FloatingWindow(
            self.items,
            show_bid=show_bid,
            ui_scale=ui_scale,
            bg_alpha=bg_alpha,
            refresh_sec=refresh_sec,
        )
        self.window.restore_position(cfg.get("window_pos"))

        self.worker = PriceWorkerController(client, interval_sec=refresh_sec)
        self.worker.set_names([i.marketHashName for i in self.items])
        self.worker.worker.index_ready.connect(self.window.set_index)
        self.worker.worker.prices_ready.connect(self._on_prices_ready)
        self.worker.worker.error.connect(lambda msg: self.window.show_status(msg, is_error=True))

        self.window.request_refresh.connect(self._on_refresh)
        self.window.request_add.connect(self._on_add)
        self.window.request_remove.connect(self._on_remove)
        self.window.request_set_quantity.connect(self._on_set_quantity)
        self.window.request_interval_change.connect(self.worker.set_interval_sec)
        self.window.settings_changed.connect(self._on_settings_changed)

        app = QApplication.instance()
        app.aboutToQuit.connect(self._on_quit)

    def start(self) -> None:
        self.window.show()
        self.worker.start()

    # ---- 信号回调 ----

    def _on_prices_ready(self, prices: dict[str, YouPinPrice]) -> None:
        # 合并保留旧值，防止个别字段缺失时持仓总价闪烁为 0
        for name, p in prices.items():
            if p is not None:
                self._latest_prices[name] = p
        self.window.set_prices(prices)
        self.window.set_portfolio_value(self._compute_portfolio())

    def _compute_portfolio(self) -> float:
        total = 0.0
        for it in self.items:
            if it.quantity <= 0:
                continue
            p = self._latest_prices.get(it.marketHashName)
            if p and p.sell_price is not None:
                total += p.sell_price * it.quantity
        return total

    def _on_refresh(self) -> None:
        self.window.show_status("刷新中…", is_error=False, timeout_ms=2000)
        self.worker.trigger_now()

    def _on_add(self) -> None:
        base: list[dict] = []
        dict_error = ""
        try:
            base = self.client.get_base_dict()
        except Exception as e:  # noqa: BLE001
            dict_error = str(e)
            self.window.show_status(f"加载饰品字典失败：{e}", is_error=True)

        dlg = AddDialog(base, parent=self.window, dict_error=dict_error)
        dlg.item_chosen.connect(self._add_chosen)
        dlg.exec()

    def _add_chosen(self, market_hash_name: str, display_name: str) -> None:
        self.items = add_item(self.items, WatchItem(market_hash_name, display_name))
        self.window.rebuild_rows(self.items)
        self.worker.set_names([i.marketHashName for i in self.items])
        self.worker.trigger_now()

    def _on_remove(self, market_hash_name: str) -> None:
        self.items = remove_item(self.items, market_hash_name)
        self.window.rebuild_rows(self.items)
        self.worker.set_names([i.marketHashName for i in self.items])
        self.window.set_portfolio_value(self._compute_portfolio())

    def _on_set_quantity(self, market_hash_name: str) -> None:
        current = next(
            (it.quantity for it in self.items if it.marketHashName == market_hash_name),
            0,
        )
        label = next(
            (it.label() for it in self.items if it.marketHashName == market_hash_name),
            market_hash_name,
        )
        qty, ok = QInputDialog.getInt(
            self.window,
            "持仓数量",
            f"{label}\n\n持有数量（0 表示仅关注、不计入持仓总价）：",
            value=int(current),
            min=0,
            max=99999,
            step=1,
        )
        if not ok:
            return
        self.items = update_quantity(self.items, market_hash_name, qty)
        self.window.refresh_row_quantity(market_hash_name)
        self.window.set_portfolio_value(self._compute_portfolio())

    def _on_settings_changed(self) -> None:
        update_config(
            show_bid=self.window.show_bid_enabled(),
            ui_scale=self.window.current_scale(),
            bg_alpha=self.window.current_bg_alpha(),
            refresh_sec=self.window.current_refresh_sec(),
        )

    def _on_quit(self) -> None:
        update_config(
            window_pos=self.window.current_position(),
            show_bid=self.window.show_bid_enabled(),
            ui_scale=self.window.current_scale(),
            bg_alpha=self.window.current_bg_alpha(),
            refresh_sec=self.window.current_refresh_sec(),
        )
        self.worker.stop()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 应用图标（Dock / 任务栏 / 标题栏）
    icon_path = _resource_path("assets/icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    try:
        api_key = ensure_api_key()
        client = SteamDTClient(api_key)
        controller = AppController(client)
        controller.start()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        QMessageBox.critical(None, "启动失败", traceback.format_exc())
        return 1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
