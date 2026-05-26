"""桌面常驻悬浮主窗口。

- 紧凑模式：默认更小的字号 / 行距
- 缩放：右键菜单 + Ctrl/Cmd ± / 0 快捷键，缩放 0.8x~1.5x，写入 config
- 持仓总价显示在大盘指数右侧
- 求购列可一键隐藏
"""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QCursor, QGuiApplication, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from steamdt_client import BroadIndex, YouPinPrice
from ui.price_row import PRICE_INLINE_MIN_W, PRICE_MIN_W, PriceRow
from watchlist import WatchItem


# 缩放范围
SCALE_MIN = 0.8
SCALE_MAX = 1.6
SCALE_STEP = 0.1

# 透明度档位（背景 alpha 0-255 + 显示名）
OPACITY_PRESETS: list[tuple[int, str]] = [
    (255, "不透明 100%"),
    (220, "高 85%"),
    (180, "中 70%"),
    (140, "低 55%"),
    (100, "极低 40%"),
]
DEFAULT_BG_ALPHA = 220

# 刷新间隔档位（秒 + 显示名）。最低 60s 受 SteamDT /price/batch 每分钟 1 次限制约束
REFRESH_PRESETS: list[tuple[int, str]] = [
    (60, "1 分钟"),
    (180, "3 分钟"),
    (300, "5 分钟"),
    (600, "10 分钟"),
    (1800, "30 分钟"),
]
DEFAULT_REFRESH_SEC = 180


def _build_style(s: float, bg_alpha: int = DEFAULT_BG_ALPHA) -> str:
    """根据 scale 生成 QSS。s=1.0 是紧凑默认尺寸；放大缩小线性插值。"""
    f_base = int(12 * s)
    f_small = int(10 * s)
    f_title = int(11 * s)
    f_idx = int(20 * s)
    f_idx_diff = int(12 * s)
    f_btn = int(13 * s)
    radius = max(6, int(10 * s))
    return f"""
QWidget#Root {{
    background-color: rgba(20, 22, 28, {bg_alpha});
    border-radius: {radius}px;
}}
QLabel {{
    color: #e6e6e6;
    font-size: {f_base}px;
}}
QLabel#Title {{
    font-size: {f_title}px;
    color: #9aa0a6;
    letter-spacing: 1px;
}}
QLabel#RefreshClock {{
    font-size: {f_small}px;
    color: #6b7280;
}}
QLabel#IndexValue {{
    font-size: {f_idx}px;
    font-weight: 600;
    color: #e6e6e6;
}}
QLabel#PortfolioValue {{
    font-size: {f_idx_diff}px;
    color: #d4af37;
    padding: 1px 6px;
    background: rgba(212, 175, 55, 25);
    border-radius: 4px;
}}
/* 国内习惯：红涨 / 绿跌 */
QLabel#IndexDiffUp {{
    font-size: {f_idx_diff}px;
    color: #ff5a5f;
}}
QLabel#IndexDiffDown {{
    font-size: {f_idx_diff}px;
    color: #2ecc71;
}}
QLabel#IndexDiffFlat {{
    font-size: {f_idx_diff}px;
    color: #9aa0a6;
}}
QFrame#Separator {{
    background-color: rgba(255, 255, 255, 30);
    max-height: 1px;
    min-height: 1px;
}}
QLabel#StatusError {{
    color: #ff5a5f;
    font-size: {f_small}px;
}}
QLabel#StatusOK {{
    color: #6b7280;
    font-size: {f_small}px;
}}
QLabel#ColHeader {{
    color: #6b7280;
    font-size: {f_small}px;
}}
QWidget#PriceRow:hover {{
    background-color: rgba(255, 255, 255, 16);
    border-radius: 5px;
}}
QPushButton#CloseBtn, QPushButton#RefreshBtn {{
    background-color: transparent;
    color: #9aa0a6;
    border: none;
    font-size: {f_btn}px;
    padding: 0 3px;
}}
QPushButton#CloseBtn:hover {{
    color: #ff5a5f;
}}
QPushButton#RefreshBtn:hover {{
    color: #74c7ec;
}}
"""


class FloatingWindow(QWidget):
    request_refresh = pyqtSignal()
    request_add = pyqtSignal()
    request_remove = pyqtSignal(str)         # marketHashName
    request_set_quantity = pyqtSignal(str)   # marketHashName
    request_interval_change = pyqtSignal(int)  # 新刷新间隔（秒）
    settings_changed = pyqtSignal()          # show_bid / ui_scale / bg_alpha 变更后持久化

    def __init__(
        self,
        items: list[WatchItem],
        *,
        show_bid: bool = True,
        ui_scale: float = 1.0,
        bg_alpha: int = DEFAULT_BG_ALPHA,
        refresh_sec: int = DEFAULT_REFRESH_SEC,
    ):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._show_bid = show_bid
        self._scale = max(SCALE_MIN, min(SCALE_MAX, ui_scale))
        self._bg_alpha = max(60, min(255, int(bg_alpha)))
        self._refresh_sec = max(60, int(refresh_sec))
        self._drag_offset: QPoint | None = None
        self._rows: dict[str, PriceRow] = {}

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(lambda: self.status_label.setText(""))

        self._build_ui()
        self._register_shortcuts()
        self.rebuild_rows(items)
        self._apply_scale()
        self._apply_bid_visibility()

    # ----- UI construction -----

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        root = QWidget(self)
        root.setObjectName("Root")
        outer.addWidget(root)

        v = QVBoxLayout(root)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)

        # 顶栏
        header = QHBoxLayout()
        header.setSpacing(4)
        title = QLabel("dust2.cc")
        title.setObjectName("Title")
        header.addWidget(title)
        self.last_refresh_label = QLabel("")
        self.last_refresh_label.setObjectName("RefreshClock")
        header.addWidget(self.last_refresh_label)
        header.addStretch(1)

        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setObjectName("RefreshBtn")
        self.refresh_btn.setFixedSize(20, 20)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setToolTip("立即刷新")
        self.refresh_btn.clicked.connect(self.request_refresh.emit)
        header.addWidget(self.refresh_btn)

        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(QApplication.instance().quit)
        header.addWidget(self.close_btn)
        v.addLayout(header)

        # 大盘指数 + 持仓
        idx_row = QHBoxLayout()
        idx_row.setSpacing(8)
        self.index_label = QLabel("--")
        self.index_label.setObjectName("IndexValue")
        idx_row.addWidget(self.index_label)
        self.index_diff_label = QLabel("")
        self.index_diff_label.setObjectName("IndexDiffFlat")
        idx_row.addWidget(self.index_diff_label)
        self.portfolio_label = QLabel("")
        self.portfolio_label.setObjectName("PortfolioValue")
        self.portfolio_label.setVisible(False)
        self.portfolio_label.setToolTip("持仓总价值 = Σ 在售价 × 持仓数量")
        idx_row.addWidget(self.portfolio_label)
        idx_row.addStretch(1)
        v.addLayout(idx_row)

        sep = QFrame()
        sep.setObjectName("Separator")
        sep.setFrameShape(QFrame.Shape.NoFrame)
        sep.setFixedHeight(1)
        v.addWidget(sep)

        # 列头
        head_row = QHBoxLayout()
        head_row.setContentsMargins(8, 0, 8, 0)
        head_row.setSpacing(6)
        self.col_name = QLabel("收藏饰品")
        self.col_name.setObjectName("ColHeader")
        self.col_sell = QLabel("在售")
        self.col_sell.setObjectName("ColHeader")
        self.col_sell.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.col_bid = QLabel("求购")
        self.col_bid.setObjectName("ColHeader")
        self.col_bid.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        head_row.addWidget(self.col_name, stretch=1)
        head_row.addWidget(self.col_sell)
        head_row.addWidget(self.col_bid)
        v.addLayout(head_row)

        # 饰品行
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(0)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        v.addLayout(self.rows_layout)

        self.empty_label = QLabel("右键 → 添加饰品")
        self.empty_label.setObjectName("StatusOK")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setContentsMargins(0, 4, 0, 4)
        v.addWidget(self.empty_label)

        # 状态栏
        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusOK")
        v.addWidget(self.status_label)

    def _register_shortcuts(self) -> None:
        # 跨平台：Qt 自动把 Ctrl 映射成 macOS 的 Cmd
        QShortcut(QKeySequence.StandardKey.ZoomIn, self).activated.connect(self.zoom_in)
        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(self.zoom_in)  # 防止 +/- 键位差异
        QShortcut(QKeySequence.StandardKey.ZoomOut, self).activated.connect(self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(self.zoom_reset)

    # ----- Public update API -----

    def set_index(self, idx: BroadIndex) -> None:
        self.index_label.setText(f"{idx.value:,.2f}")
        ratio_pct = (
            idx.diff_yesterday_ratio * 100
            if abs(idx.diff_yesterday_ratio) < 1
            else idx.diff_yesterday_ratio
        )
        if idx.diff_yesterday > 0:
            self.index_diff_label.setObjectName("IndexDiffUp")
            text = f"▲ {idx.diff_yesterday:+.2f}  {ratio_pct:+.2f}%"
        elif idx.diff_yesterday < 0:
            self.index_diff_label.setObjectName("IndexDiffDown")
            text = f"▼ {idx.diff_yesterday:+.2f}  {ratio_pct:+.2f}%"
        else:
            self.index_diff_label.setObjectName("IndexDiffFlat")
            text = "— 0.00  0.00%"
        self.index_diff_label.setText(text)
        self.index_diff_label.style().unpolish(self.index_diff_label)
        self.index_diff_label.style().polish(self.index_diff_label)

    def set_prices(self, prices: dict[str, YouPinPrice]) -> None:
        for name, row in self._rows.items():
            row.set_price(prices.get(name))
        self.last_refresh_label.setText(f"· {datetime.now().strftime('%H:%M:%S')}")

    def set_portfolio_value(self, total: float | None) -> None:
        if total is None or total <= 0:
            self.portfolio_label.setText("")
            self.portfolio_label.setVisible(False)
        else:
            self.portfolio_label.setText(f"持仓 ¥{total:,.2f}")
            self.portfolio_label.setVisible(True)

    def refresh_row_quantity(self, market_hash_name: str) -> None:
        row = self._rows.get(market_hash_name)
        if row is not None:
            row.refresh_quantity()

    def rebuild_rows(self, items: list[WatchItem]) -> None:
        while self.rows_layout.count():
            child = self.rows_layout.takeAt(0)
            w = child.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._rows.clear()

        for it in items:
            row = PriceRow(it, scale=self._scale)
            row.set_bid_visible(self._show_bid)
            row.right_clicked.connect(self._on_row_right_clicked)
            self.rows_layout.addWidget(row)
            self._rows[it.marketHashName] = row

        self.empty_label.setVisible(not items)
        self.adjustSize()

    def show_status(self, text: str, *, is_error: bool = False, timeout_ms: int = 5000) -> None:
        self.status_label.setText(text)
        self.status_label.setObjectName("StatusError" if is_error else "StatusOK")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        if timeout_ms > 0:
            self._status_timer.start(timeout_ms)

    # ----- 缩放 -----

    def zoom_in(self) -> None:
        self._set_scale(self._scale + SCALE_STEP)

    def zoom_out(self) -> None:
        self._set_scale(self._scale - SCALE_STEP)

    def zoom_reset(self) -> None:
        self._set_scale(1.0)

    def current_scale(self) -> float:
        return self._scale

    def _set_scale(self, scale: float) -> None:
        scale = round(max(SCALE_MIN, min(SCALE_MAX, scale)), 2)
        if abs(scale - self._scale) < 0.005:
            return
        self._scale = scale
        self._apply_scale()
        self.settings_changed.emit()

    def _apply_scale(self) -> None:
        self.setStyleSheet(_build_style(self._scale, self._bg_alpha))
        # 全窗最小宽度按 scale 伸缩
        self.setMinimumWidth(int(380 * self._scale))
        for row in self._rows.values():
            row.apply_scale(self._scale)
        self._apply_header_widths()
        self.adjustSize()

    def _apply_header_widths(self) -> None:
        """列头宽度跟随 PriceRow 的 sell_wrap / bid_wrap 同步，避免 在售/求购 标签挤一起。"""
        sell_w = (PRICE_INLINE_MIN_W if not self._show_bid else PRICE_MIN_W) * self._scale
        bid_w = PRICE_MIN_W * self._scale
        self.col_sell.setMinimumWidth(int(sell_w))
        self.col_bid.setMinimumWidth(int(bid_w))

    # ----- 求购列开关 -----

    def show_bid_enabled(self) -> bool:
        return self._show_bid

    def set_show_bid(self, show: bool) -> None:
        if show == self._show_bid:
            return
        self._show_bid = show
        self._apply_bid_visibility()
        self.settings_changed.emit()

    def _apply_bid_visibility(self) -> None:
        self.col_bid.setVisible(self._show_bid)
        for row in self._rows.values():
            row.set_bid_visible(self._show_bid)
        self._apply_header_widths()
        self.adjustSize()

    # ----- 透明度 -----

    def current_bg_alpha(self) -> int:
        return self._bg_alpha

    def set_bg_alpha(self, alpha: int) -> None:
        alpha = max(60, min(255, int(alpha)))
        if alpha == self._bg_alpha:
            return
        self._bg_alpha = alpha
        self.setStyleSheet(_build_style(self._scale, self._bg_alpha))
        self.settings_changed.emit()

    # ----- 刷新间隔 -----

    def current_refresh_sec(self) -> int:
        return self._refresh_sec

    def set_refresh_sec(self, sec: int) -> None:
        sec = max(60, int(sec))
        if sec == self._refresh_sec:
            return
        self._refresh_sec = sec
        self.request_interval_change.emit(sec)
        self.settings_changed.emit()

    # ----- 拖动 -----

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._drag_offset is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):  # noqa: N802
        self._drag_offset = None

    # ----- 右键菜单 -----

    def contextMenuEvent(self, event):  # noqa: N802
        self._open_menu(event.globalPos(), hovered_name=None)

    def _on_row_right_clicked(self, market_hash_name: str) -> None:
        self._open_menu(QCursor.pos(), hovered_name=market_hash_name)

    def _open_menu(self, pos, *, hovered_name: str | None) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #2a2d35; color: #e6e6e6; border-radius: 6px; padding: 4px; }"
            "QMenu::item { padding: 5px 18px; border-radius: 4px; }"
            "QMenu::item:selected { background: #3a3e48; }"
            "QMenu::separator { height: 1px; background: rgba(255,255,255,30); margin: 3px 6px; }"
        )

        add_action = QAction("添加饰品…", self)
        add_action.triggered.connect(self.request_add.emit)
        menu.addAction(add_action)

        if hovered_name:
            row = self._rows.get(hovered_name)
            label = row.item.label() if row is not None else hovered_name
            qty = row.item.quantity if row is not None else 0

            qty_action = QAction(f"持仓数量…（当前 {qty}）", self)
            qty_action.triggered.connect(lambda: self.request_set_quantity.emit(hovered_name))
            menu.addAction(qty_action)

            rm = QAction(f"删除：{label}", self)
            rm.triggered.connect(lambda: self.request_remove.emit(hovered_name))
            menu.addAction(rm)

        menu.addSeparator()

        # 显示求购价 开关
        bid_action = QAction("显示求购价", self)
        bid_action.setCheckable(True)
        bid_action.setChecked(self._show_bid)
        bid_action.triggered.connect(self.set_show_bid)
        menu.addAction(bid_action)

        # 透明度子菜单
        opacity_menu = menu.addMenu("透明度")
        for alpha, label in OPACITY_PRESETS:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(self._bg_alpha == alpha)
            act.triggered.connect(lambda _checked=False, a=alpha: self.set_bg_alpha(a))
            opacity_menu.addAction(act)

        # 刷新间隔 子菜单
        interval_menu = menu.addMenu(f"刷新间隔  ({self._format_interval(self._refresh_sec)})")
        for sec, label in REFRESH_PRESETS:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(self._refresh_sec == sec)
            act.triggered.connect(lambda _checked=False, s=sec: self.set_refresh_sec(s))
            interval_menu.addAction(act)

        # 缩放子菜单
        zoom_menu = menu.addMenu(f"窗口缩放  ({int(self._scale * 100)}%)")
        zoom_in_action = QAction("放大  (Cmd +)", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        zoom_menu.addAction(zoom_in_action)
        zoom_out_action = QAction("缩小  (Cmd −)", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        zoom_menu.addAction(zoom_out_action)
        zoom_reset_action = QAction("重置 100%", self)
        zoom_reset_action.triggered.connect(self.zoom_reset)
        zoom_menu.addAction(zoom_reset_action)

        menu.addSeparator()

        refresh = QAction("立即刷新", self)
        refresh.triggered.connect(self.request_refresh.emit)
        menu.addAction(refresh)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)

        menu.exec(pos)

    @staticmethod
    def _format_interval(sec: int) -> str:
        if sec % 60 == 0:
            return f"{sec // 60} 分钟"
        return f"{sec} 秒"

    # ----- 位置持久化 -----

    def restore_position(self, pos: dict | None) -> None:
        if not pos:
            screen = QGuiApplication.primaryScreen().availableGeometry()
            self.move(screen.right() - self.width() - 40, screen.top() + 60)
            return
        self.move(int(pos.get("x", 100)), int(pos.get("y", 100)))

    def current_position(self) -> dict:
        p = self.pos()
        return {"x": p.x(), "y": p.y()}
