"""单行饰品价格组件：[名称] [在售价 + ▲▼涨跌幅] [求购价 + ▲▼涨跌幅]。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from steamdt_client import YouPinPrice
from watchlist import WatchItem


# 国内行情习惯：红涨 / 绿跌
COLOR_UP = "#ff5a5f"
COLOR_DOWN = "#2ecc71"
COLOR_FLAT = "#9aa0a6"
COLOR_PRICE_NEUTRAL = "#e6e6e6"


class PriceRow(QWidget):
    right_clicked = pyqtSignal(str)  # marketHashName

    def __init__(self, item: WatchItem, parent: QWidget | None = None):
        super().__init__(parent)
        self.item = item
        self.setObjectName("PriceRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._prev_sell: float | None = None
        self._prev_bid: float | None = None

        self.name_label = QLabel(item.label())
        self.name_label.setObjectName("RowName")
        self.name_label.setToolTip(item.marketHashName)
        self.name_label.setMinimumWidth(180)

        self.sell_label = QLabel("—")
        self.sell_label.setObjectName("SellPrice")
        self.sell_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.sell_diff = QLabel("")
        self.sell_diff.setObjectName("RowDiff")
        self.sell_diff.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sell_box = QVBoxLayout()
        sell_box.setContentsMargins(0, 0, 0, 0)
        sell_box.setSpacing(0)
        sell_box.addWidget(self.sell_label)
        sell_box.addWidget(self.sell_diff)
        sell_wrap = QWidget()
        sell_wrap.setLayout(sell_box)
        sell_wrap.setMinimumWidth(120)

        self.bid_label = QLabel("—")
        self.bid_label.setObjectName("BidPrice")
        self.bid_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.bid_diff = QLabel("")
        self.bid_diff.setObjectName("RowDiff")
        self.bid_diff.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bid_box = QVBoxLayout()
        bid_box.setContentsMargins(0, 0, 0, 0)
        bid_box.setSpacing(0)
        bid_box.addWidget(self.bid_label)
        bid_box.addWidget(self.bid_diff)
        bid_wrap = QWidget()
        bid_wrap.setLayout(bid_box)
        bid_wrap.setMinimumWidth(120)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)
        layout.addWidget(self.name_label, stretch=1)
        layout.addWidget(sell_wrap)
        layout.addWidget(bid_wrap)

    def set_price(self, price: YouPinPrice | None) -> None:
        new_sell = price.sell_price if price else None
        new_bid = price.bidding_price if price else None
        self._apply(self.sell_label, self.sell_diff, new_sell, self._prev_sell)
        self._apply(self.bid_label, self.bid_diff, new_bid, self._prev_bid)
        if new_sell is not None:
            self._prev_sell = new_sell
        if new_bid is not None:
            self._prev_bid = new_bid

    @staticmethod
    def _apply(val_label: QLabel, diff_label: QLabel, new: float | None, prev: float | None) -> None:
        if new is None:
            val_label.setText("—")
            val_label.setStyleSheet(f"color: {COLOR_FLAT}; font-weight: 600;")
            diff_label.setText("")
            return

        val_label.setText(f"¥{new:.2f}")

        if prev is None:
            val_label.setStyleSheet(f"color: {COLOR_PRICE_NEUTRAL}; font-weight: 600;")
            diff_label.setText("")
            return

        delta = new - prev
        pct = (delta / prev * 100) if prev else 0.0

        if abs(delta) < 0.005:
            val_label.setStyleSheet(f"color: {COLOR_PRICE_NEUTRAL}; font-weight: 600;")
            diff_label.setText("— 持平")
            diff_label.setStyleSheet(f"color: {COLOR_FLAT}; font-size: 10px;")
        elif delta > 0:
            val_label.setStyleSheet(f"color: {COLOR_UP}; font-weight: 600;")
            diff_label.setText(f"▲ {delta:+.2f}  {pct:+.2f}%")
            diff_label.setStyleSheet(f"color: {COLOR_UP}; font-size: 10px; font-weight: 600;")
        else:
            val_label.setStyleSheet(f"color: {COLOR_DOWN}; font-weight: 600;")
            diff_label.setText(f"▼ {delta:+.2f}  {pct:+.2f}%")
            diff_label.setStyleSheet(f"color: {COLOR_DOWN}; font-size: 10px; font-weight: 600;")

    def contextMenuEvent(self, event):  # noqa: N802
        self.right_clicked.emit(self.item.marketHashName)
        event.accept()
