"""桌面常驻悬浮主窗口。"""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QCursor, QGuiApplication
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
from ui.price_row import PriceRow
from watchlist import WatchItem


STYLE = """
QWidget#Root {
    background-color: rgba(20, 22, 28, 220);
    border-radius: 12px;
}
QLabel {
    color: #e6e6e6;
    font-size: 13px;
}
QLabel#Title {
    font-size: 12px;
    color: #9aa0a6;
    letter-spacing: 1px;
}
QLabel#IndexValue {
    font-size: 22px;
    font-weight: 600;
    color: #e6e6e6;
}
/* 国内习惯：红涨 / 绿跌 */
QLabel#IndexDiffUp {
    font-size: 13px;
    color: #ff5a5f;
}
QLabel#IndexDiffDown {
    font-size: 13px;
    color: #2ecc71;
}
QLabel#IndexDiffFlat {
    font-size: 13px;
    color: #9aa0a6;
}
QFrame#Separator {
    background-color: rgba(255, 255, 255, 30);
    max-height: 1px;
    min-height: 1px;
}
QLabel#StatusError {
    color: #ff5a5f;
    font-size: 11px;
}
QLabel#StatusOK {
    color: #6b7280;
    font-size: 11px;
}
QWidget#PriceRow:hover {
    background-color: rgba(255, 255, 255, 16);
    border-radius: 6px;
}
QLabel#SellPrice {
    color: #ffb86b;
    font-weight: 600;
}
QLabel#BidPrice {
    color: #74c7ec;
}
QLabel#ColHeader {
    color: #6b7280;
    font-size: 11px;
}
QPushButton#CloseBtn, QPushButton#RefreshBtn {
    background-color: transparent;
    color: #9aa0a6;
    border: none;
    font-size: 14px;
    padding: 0 4px;
}
QPushButton#CloseBtn:hover {
    color: #ff5a5f;
}
QPushButton#RefreshBtn:hover {
    color: #74c7ec;
}
QPushButton#RefreshBtn:disabled {
    color: #4b5563;
}
"""


class FloatingWindow(QWidget):
    request_refresh = pyqtSignal()
    request_add = pyqtSignal()
    request_remove = pyqtSignal(str)  # marketHashName

    def __init__(self, items: list[WatchItem]):
        super().__init__()
        # 注意：故意不加 Qt.Tool —— 在 macOS 上 Tool 会被映射为 NSPanel，
        # NSPanel 默认 hidesOnDeactivate=YES，导致切换到别的 App 时悬浮窗自动隐藏。
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(420)

        self._drag_offset: QPoint | None = None
        self._rows: dict[str, PriceRow] = {}
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(lambda: self.status_label.setText(""))

        self._build_ui()
        self.setStyleSheet(STYLE)
        self.rebuild_rows(items)

    # ----- UI construction -----

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        root = QWidget(self)
        root.setObjectName("Root")
        outer.addWidget(root)

        v = QVBoxLayout(root)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(6)

        # 顶栏：标题 + 刷新按钮 + 关闭按钮
        header = QHBoxLayout()
        header.setSpacing(4)
        title = QLabel("dust2.cc")
        title.setObjectName("Title")
        header.addWidget(title)
        self.last_refresh_label = QLabel("")
        self.last_refresh_label.setObjectName("StatusOK")
        header.addWidget(self.last_refresh_label)
        header.addStretch(1)

        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setObjectName("RefreshBtn")
        self.refresh_btn.setFixedSize(22, 22)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setToolTip("立即刷新")
        self.refresh_btn.clicked.connect(self.request_refresh.emit)
        header.addWidget(self.refresh_btn)

        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(QApplication.instance().quit)
        header.addWidget(self.close_btn)
        v.addLayout(header)

        # 大盘指数行
        idx_row = QHBoxLayout()
        idx_row.setSpacing(10)
        self.index_label = QLabel("--")
        self.index_label.setObjectName("IndexValue")
        idx_row.addWidget(self.index_label)
        self.index_diff_label = QLabel("")
        self.index_diff_label.setObjectName("IndexDiffFlat")
        idx_row.addWidget(self.index_diff_label)
        idx_row.addStretch(1)
        v.addLayout(idx_row)

        sep = QFrame()
        sep.setObjectName("Separator")
        sep.setFrameShape(QFrame.Shape.NoFrame)
        sep.setFixedHeight(1)
        v.addWidget(sep)

        # 列表表头
        head_row = QHBoxLayout()
        head_row.setContentsMargins(10, 2, 10, 2)
        head_row.setSpacing(8)
        col_name = QLabel("收藏饰品")
        col_name.setObjectName("ColHeader")
        col_sell = QLabel("在售")
        col_sell.setObjectName("ColHeader")
        col_sell.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        col_sell.setMinimumWidth(110)
        col_bid = QLabel("求购")
        col_bid.setObjectName("ColHeader")
        col_bid.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        col_bid.setMinimumWidth(110)
        head_row.addWidget(col_name, stretch=1)
        head_row.addWidget(col_sell)
        head_row.addWidget(col_bid)
        v.addLayout(head_row)

        # 饰品行容器
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(0)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        v.addLayout(self.rows_layout)

        self.empty_label = QLabel("右键 → 添加饰品")
        self.empty_label.setObjectName("StatusOK")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setContentsMargins(0, 6, 0, 6)
        v.addWidget(self.empty_label)

        # 状态栏
        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusOK")
        v.addWidget(self.status_label)

    # ----- Public update API -----

    def set_index(self, idx: BroadIndex) -> None:
        self.index_label.setText(f"{idx.value:,.2f}")
        ratio_pct = idx.diff_yesterday_ratio * 100 if abs(idx.diff_yesterday_ratio) < 1 else idx.diff_yesterday_ratio
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
        # 强制重新应用 QSS（objectName 变化）
        self.index_diff_label.style().unpolish(self.index_diff_label)
        self.index_diff_label.style().polish(self.index_diff_label)

    def set_prices(self, prices: dict[str, YouPinPrice]) -> None:
        for name, row in self._rows.items():
            row.set_price(prices.get(name))
        self.last_refresh_label.setText(f"  · {datetime.now().strftime('%H:%M:%S')}")

    def rebuild_rows(self, items: list[WatchItem]) -> None:
        # 清空旧行
        while self.rows_layout.count():
            child = self.rows_layout.takeAt(0)
            w = child.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._rows.clear()

        for it in items:
            row = PriceRow(it)
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

    # ----- Drag to move -----

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

    # ----- Context menu -----

    def contextMenuEvent(self, event):  # noqa: N802
        self._open_menu(event.globalPos(), hovered_name=None)

    def _on_row_right_clicked(self, market_hash_name: str) -> None:
        self._open_menu(QCursor.pos(), hovered_name=market_hash_name)

    def _open_menu(self, pos, *, hovered_name: str | None) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #2a2d35; color: #e6e6e6; border-radius: 6px; padding: 4px; }"
            "QMenu::item { padding: 6px 18px; border-radius: 4px; }"
            "QMenu::item:selected { background: #3a3e48; }"
        )

        add_action = QAction("添加饰品…", self)
        add_action.triggered.connect(self.request_add.emit)
        menu.addAction(add_action)

        if hovered_name:
            label = hovered_name
            row = self._rows.get(hovered_name)
            if row is not None:
                label = row.item.label()
            rm = QAction(f"删除：{label}", self)
            rm.triggered.connect(lambda: self.request_remove.emit(hovered_name))
            menu.addAction(rm)

        menu.addSeparator()
        refresh = QAction("立即刷新", self)
        refresh.triggered.connect(self.request_refresh.emit)
        menu.addAction(refresh)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)

        menu.exec(pos)

    # ----- Geometry persistence helpers -----

    def restore_position(self, pos: dict | None) -> None:
        if not pos:
            screen = QGuiApplication.primaryScreen().availableGeometry()
            self.move(screen.right() - self.width() - 40, screen.top() + 60)
            return
        self.move(int(pos.get("x", 100)), int(pos.get("y", 100)))

    def current_position(self) -> dict:
        p = self.pos()
        return {"x": p.x(), "y": p.y()}
