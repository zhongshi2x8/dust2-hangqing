"""单行饰品价格组件。

布局：[名称 + ×数量徽章]  [在售价 (+ 涨跌)]  [求购价 (+ 涨跌)]

- 求购列显示时：在售/求购价分两列，价格下方是涨跌幅小字
- 求购列隐藏时（inline_delta 模式）：在售价旁直接内联显示涨跌幅，节省空间
"""

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

BASE_FONT = 12
SMALL_FONT = 10
NAME_MIN_W = 160
PRICE_MIN_W = 100
PRICE_INLINE_MIN_W = 210  # 求购列隐藏 + 内联涨跌时，给在售列预留的宽度


class PriceRow(QWidget):
    right_clicked = pyqtSignal(str)  # marketHashName

    def __init__(self, item: WatchItem, scale: float = 1.0, parent: QWidget | None = None):
        super().__init__(parent)
        self.item = item
        self._scale = scale
        self._inline_delta = False  # 求购列隐藏时切到内联模式
        self.setObjectName("PriceRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # 最新一次拉到的价格 + 上一次显示过的价格（用来算 delta）
        self._latest_sell: float | None = None
        self._latest_bid: float | None = None
        self._prev_sell: float | None = None
        self._prev_bid: float | None = None

        # 名称 + 数量徽章
        self.name_label = QLabel(item.label())
        self.name_label.setObjectName("RowName")
        self.name_label.setToolTip(item.marketHashName)

        self.qty_badge = QLabel("")
        self.qty_badge.setObjectName("QtyBadge")
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
        self.sell_label.setTextFormat(Qt.TextFormat.RichText)
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
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)
        layout.addWidget(name_wrap, stretch=1)
        layout.addWidget(self.sell_wrap)
        layout.addWidget(self.bid_wrap)

        self.apply_scale(scale)

    # ----- 价格更新 -----

    def set_price(self, price: YouPinPrice | None) -> None:
        new_sell = price.sell_price if price else None
        new_bid = price.bidding_price if price else None
        # 滚动 latest → prev
        if new_sell is not None and self._latest_sell is not None:
            self._prev_sell = self._latest_sell
        if new_sell is not None:
            self._latest_sell = new_sell
        if new_bid is not None and self._latest_bid is not None:
            self._prev_bid = self._latest_bid
        if new_bid is not None:
            self._latest_bid = new_bid
        self._render_prices()

    def _render_prices(self) -> None:
        self._render_one(
            self.sell_label,
            self.sell_diff,
            self._latest_sell,
            self._prev_sell,
            inline=self._inline_delta,
        )
        # 求购列永远走分行模式（被隐藏时这俩 label 不可见也没关系）
        self._render_one(
            self.bid_label,
            self.bid_diff,
            self._latest_bid,
            self._prev_bid,
            inline=False,
        )

    @staticmethod
    def _render_one(
        val_label: QLabel,
        diff_label: QLabel,
        new: float | None,
        prev: float | None,
        inline: bool,
    ) -> None:
        if new is None:
            val_label.setText("—")
            val_label.setStyleSheet(f"color: {COLOR_FLAT}; font-weight: 600;")
            diff_label.setText("")
            return

        if prev is None:
            # 首次拿到价格
            val_label.setText(f"¥{new:.2f}")
            val_label.setStyleSheet(f"color: {COLOR_PRICE_NEUTRAL}; font-weight: 600;")
            diff_label.setText("")
            return

        delta = new - prev
        pct = (delta / prev * 100) if prev else 0.0

        # 持平：不再显示 "—" 占位，只保留价格本身，让视觉聚焦在真正变动的行
        if abs(delta) < 0.005:
            val_label.setText(f"¥{new:.2f}")
            val_label.setStyleSheet(f"color: {COLOR_PRICE_NEUTRAL}; font-weight: 600;")
            diff_label.setText("")
            diff_label.setStyleSheet("")
            return

        if delta > 0:
            color = COLOR_UP
            arrow_text = f"▲ {delta:+.2f} {pct:+.2f}%"
        else:
            color = COLOR_DOWN
            arrow_text = f"▼ {delta:+.2f} {pct:+.2f}%"

        if inline:
            # 单行：价格 + 涨跌幅小字 内联
            val_label.setText(
                f'<span style="color:{color};font-weight:600;">¥{new:.2f}</span>'
                f' <span style="color:{color};font-size:{SMALL_FONT}px;font-weight:600;">'
                f'{arrow_text}</span>'
            )
            val_label.setStyleSheet("")  # 让 rich text 自己控
            diff_label.setText("")
        else:
            val_label.setText(f"¥{new:.2f}")
            val_label.setStyleSheet(f"color: {color}; font-weight: 600;")
            diff_label.setText(arrow_text)
            diff_label.setStyleSheet(
                f"color: {color}; font-size: {SMALL_FONT}px; font-weight: 600;"
            )

    # ----- 求购列显隐 / 内联模式 -----

    def set_bid_visible(self, visible: bool) -> None:
        self.bid_wrap.setVisible(visible)
        self._inline_delta = not visible
        self.sell_diff.setVisible(visible)
        self._apply_widths()
        self._render_prices()

    def _apply_widths(self) -> None:
        sell_min = PRICE_INLINE_MIN_W if self._inline_delta else PRICE_MIN_W
        self.sell_wrap.setMinimumWidth(int(sell_min * self._scale))
        self.bid_wrap.setMinimumWidth(int(PRICE_MIN_W * self._scale))

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
        self._apply_widths()
        m = max(3, int(6 * scale))
        side = max(6, int(10 * scale))
        self.layout().setContentsMargins(side, m, side, m)
        self.layout().setSpacing(max(5, int(10 * scale)))

    def contextMenuEvent(self, event):  # noqa: N802
        self.right_clicked.emit(self.item.marketHashName)
        event.accept()
