"""后台刷新线程：每 3 分钟拉取一次大盘指数和收藏价格。"""

from __future__ import annotations

from PyQt6.QtCore import QMetaObject, QObject, Qt, QThread, QTimer, pyqtSignal, pyqtSlot

from steamdt_client import SteamDTClient, SteamDTError


class PriceWorker(QObject):
    """运行在独立 QThread 中，对外暴露 fetch_once 槽。"""

    index_ready = pyqtSignal(object)   # BroadIndex
    prices_ready = pyqtSignal(dict)    # {marketHashName: YouPinPrice}
    error = pyqtSignal(str)

    def __init__(self, client: SteamDTClient):
        super().__init__()
        self._client = client
        self._names: list[str] = []

    def set_names(self, names: list) -> None:
        # 直接从主线程调用即可：替换整个 list 引用在 CPython 下是 GIL 原子操作，
        # 下一次 fetch_once 自然读到新值。
        self._names = list(names)

    @pyqtSlot()
    def fetch_once(self) -> None:
        try:
            idx = self._client.get_broad_index()
            self.index_ready.emit(idx)
        except SteamDTError as e:
            self.error.emit(f"大盘指数获取失败：{e}")
        except Exception as e:  # noqa: BLE001
            self.error.emit(f"大盘指数网络错误：{e}")

        if not self._names:
            self.prices_ready.emit({})
            return

        try:
            prices = self._client.batch_price(self._names)
            self.prices_ready.emit(prices)
        except SteamDTError as e:
            self.error.emit(f"价格获取失败：{e}")
        except Exception as e:  # noqa: BLE001
            self.error.emit(f"价格网络错误：{e}")


class PriceWorkerController:
    """主线程帮手：管理 QThread + worker + 周期定时器。"""

    def __init__(self, client: SteamDTClient, interval_sec: int = 180):
        self.thread = QThread()
        self.worker = PriceWorker(client)
        self.worker.moveToThread(self.thread)
        self.thread.start()

        self.timer = QTimer()
        self.timer.setInterval(interval_sec * 1000)
        self.timer.timeout.connect(self.trigger_now)

    def start(self) -> None:
        self.timer.start()
        self.trigger_now()

    def trigger_now(self) -> None:
        QMetaObject.invokeMethod(
            self.worker, "fetch_once", Qt.ConnectionType.QueuedConnection
        )

    def set_names(self, names: list[str]) -> None:
        self.worker.set_names(names)

    def stop(self) -> None:
        self.timer.stop()
        self.thread.quit()
        self.thread.wait(2000)
