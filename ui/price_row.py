"""单行饰品价格组件：[名称] [×数量徽章] [在售价/涨跌] [求购价/涨跌]。"""

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
COLOR_QTY_BADGE = "#74c7ec"

BASE_FONT = 12     # 紧凑后的默认正文字号
SMALL_FONT = 10    # 涨跌幅/数量徽章用的小字号
NAME_MIN_W = 160   # 行内"名称"列最小宽度（@scale=1.0）
PRICE_MIN_W = 100  # 行内"价格 + 涨跌"列最小宽度（@scale=1.0）


class PriceRow(QWidget):
    right_clicked = pyqtSignal(str)  # marketHashName

    def __init__(self, item: WatchItem, scale: float = 1.0, parent: QWidget | None = None):
        super().__init__(parent)
        self.item = item
        self._scale = scale
        self.setObjectName("PriceRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._prev_sell: float | None = None
        self._prev_bid: float | None = None

        # 名称 + 数量徽章
        self.name_label = QLabel(item.label())
        self.name_label.setObjectName("RowName")
        self.name_label.setToolTip(item.marketHashName)

        self.qty_badge = QLabel("")
        self.qty_badge.setObjectName("QtyBadge")
        self.qty_badge.setVisible(item.quantity > 0)
        self.refresh_quantity()

        name_box = QHBoxLayout()
        name_box.setContentsMargins(0, 0, 0, 0)
        name_box.setSpacing(4)
        name_box.addWidget(self.name_label)
        name_box.addWidget(self.qty_badge)
        name_box.addStretch(1)
        name_wrap = QWidget()
        name_wrap.setLayout(name_box)

        # 在售
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
        self.sell_wrap = QWidget()
        self.sell_wrap.setLayout(sell_box)

        # 求购
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
        self.bid_wrap = QWidget()
        self.bid_wrap.setLayout(bid_box)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)
        layout.addWidget(name_wrap, stretch=1)
        layout.addWidget(self.sell_wrap)
        layout.addWidget(self.bid_wrap)

        self.apply_scale(scale)

    # ----- 价格更新 -----

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
        small = SMALL_FONT  # 涨跌幅小字
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
            diff_label.setText("—")
            diff_label.setStyleSheet(f"color: {COLOR_FLAT}; font-size: {small}px;")
        elif delta > 0:
            val_label.setStyleSheet(f"color: {COLOR_UP}; font-weight: 600;")
            diff_label.setText(f"▲ {delta:+.2f}  {pct:+.2f}%")
            diff_label.setStyleSheet(f"color: {COLOR_UP}; font-size: {small}px; font-weight: 600;")
        else:
            val_label.setStyleSheet(f"color: {COLOR_DOWN}; font-weight: 600;")
            diff_label.setText(f"▼ {delta:+.2f}  {pct:+.2f}%")
            diff_label.setStyleSheet(f"color: {COLOR_DOWN}; font-size: {small}px; font-weight: 600;")

    # ----- 求购列显隐 -----

    def set_bid_visible(self, visible: bool) -> None:
        self.bid_wrap.setVisible(visible)

    # ----- 持仓徽章 -----

    def refresh_quantity(self) -> None:
        if self.item.quantity > 0:
            self.qty_badge.setText(f"×{self.item.quantity}")
            self.qty_badge.setVisible(True)
            self.qty_badge.setStyleSheet(
                f"color: {COLOR_QTY_BADGE}; font-size: {SMALL_FONT}px; "
                f"background: rgba(116, 199, 236, 30); border-radius: 4px; padding: 1px 5px;"
            )
        else:
            self.qty_badge.setVisible(False)

    # ----- 缩放 -----

    def apply_scale(self, scale: float) -> None:
        self._scale = scale
        self.name_label.setMinimumWidth(int(NAME_MIN_W * scale))
        self.sell_wrap.setMinimumWidth(int(PRICE_MIN_W * scale))
        self.bid_wrap.setMinimumWidth(int(PRICE_MIN_W * scale))
        # 内边距随缩放：scale=1.0 时 (8,2,8,2)
        m = max(1, int(2 * scale))
        side = max(4, int(8 * scale))
        self.layout().setContentsMargins(side, m, side, m)
        self.layout().setSpacing(max(3, int(6 * scale)))

    def contextMenuEvent(self, event):  # noqa: N802
        self.right_clicked.emit(self.item.marketHashName)
        event.accept()
