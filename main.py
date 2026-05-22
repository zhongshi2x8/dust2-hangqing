"""CS2 行情悬浮窗入口。"""

from __future__ import annotations

import sys
import traceback

from PyQt6.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

from price_worker import PriceWorkerController
from steamdt_client import SteamDTClient, SteamDTError
from ui.add_dialog import AddDialog
from ui.floating_window import FloatingWindow
from watchlist import (
    WatchItem,
    add_item,
    load_config,
    load_watchlist,
    remove_item,
    update_config,
)


REFRESH_INTERVAL_SEC = 180


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
        self.window = FloatingWindow(self.items)
        self.window.restore_position(load_config().get("window_pos"))

        self.worker = PriceWorkerController(client, interval_sec=REFRESH_INTERVAL_SEC)
        self.worker.set_names([i.marketHashName for i in self.items])
        self.worker.worker.index_ready.connect(self.window.set_index)
        self.worker.worker.prices_ready.connect(self.window.set_prices)
        self.worker.worker.error.connect(lambda msg: self.window.show_status(msg, is_error=True))

        self.window.request_refresh.connect(self._on_refresh)
        self.window.request_add.connect(self._on_add)
        self.window.request_remove.connect(self._on_remove)

        app = QApplication.instance()
        app.aboutToQuit.connect(self._on_quit)

    def start(self) -> None:
        self.window.show()
        self.worker.start()

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

    def _on_quit(self) -> None:
        update_config(window_pos=self.window.current_position())
        self.worker.stop()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

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
